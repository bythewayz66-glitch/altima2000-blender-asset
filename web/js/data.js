/* ============================================================
   data.js — manifest loading + indexing
   ------------------------------------------------------------
   Loads altima2000_manifest.json (2,130 parts) and the seven
   per-module manifests, then builds the lookup indexes the UI
   and the 3D layer need:
     partsByName, byGroup, byCollection, byModule,
     harnesses (31), hoses (15 systems), tieStraps,
     sequence steps, and the trace polylines for every wire.
   ============================================================ */

export const MODULE_KEYS = [
  'engine', 'drivetrain', 'suspension', 'wheels', 'brakes', 'exhaust', 'doors',
];

/* ---------- source definitions ----------
   `local`  : served from the repo checkout (web/ sits next to the assets)
   `github` : the published repo — LFS binaries via media.githubusercontent,
              text/JSON via raw.githubusercontent
*/
const GH = 'bythewayz66-glitch/altima2000-blender-asset';
const GH_BRANCH = 'main';

export const SOURCES = {
  local: {
    label: 'Local (web/data/)',
    manifest: './data/altima2000_manifest.json',
    glb: './data/altima2000.glb',
    gltf: './data/altima2000.gltf',
    moduleManifest: (k) => `./data/altima2000_module_${k}_manifest.json`,
  },
  github: {
    label: 'GitHub (published)',
    manifest: `https://raw.githubusercontent.com/${GH}/${GH_BRANCH}/altima2000_manifest.json`,
    glb: `https://media.githubusercontent.com/media/${GH}/${GH_BRANCH}/altima2000.glb`,
    gltf: `https://raw.githubusercontent.com/${GH}/${GH_BRANCH}/altima2000.gltf`,
    moduleManifest: (k) =>
      `https://raw.githubusercontent.com/${GH}/${GH_BRANCH}/altima2000_module_${k}_manifest.json`,
  },
};

/* ---------- tiny fetch helper with progress ---------- */
export async function fetchJSON(url) {
  const res = await fetch(url, { cache: 'no-cache' });
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
  return res.json();
}

/* ============================================================
   Manifest
   ============================================================ */
export class AssetData {
  constructor(manifest, sourceKey) {
    this.raw = manifest;
    this.sourceKey = sourceKey;

    this.parts = manifest.parts || [];
    this.partCount = manifest.part_count ?? this.parts.length;
    this.collectionCount = manifest.collection_count ?? 0;
    this.materialCount = manifest.material_count ?? 0;

    this.wiring = manifest.wiring || {};
    this.hoses = manifest.hoses || {};
    this.modules = manifest.modules || {};
    this.sequence = manifest.sequence || {};

    this._buildIndexes();
  }

  _buildIndexes() {
    /* ---- parts ---- */
    this.partsByName = new Map();
    this.byGroup = new Map();
    this.byCollection = new Map();
    this.bySub = new Map();

    for (const p of this.parts) {
      this.partsByName.set(p.name, p);
      push(this.byGroup, p.group, p);
      push(this.byCollection, p.collection, p);
      push(this.bySub, `${p.collection}/${p.sub}`, p);
    }

    /* ---- module membership (name -> module key) ---- */
    this.moduleOfPart = new Map();
    this.moduleList = [];
    for (const key of MODULE_KEYS) {
      const m = this.modules[key];
      if (!m) continue;
      const entry = {
        key,
        file: m.file,
        rootCollections: m.root_collections || [],
        collections: m.collections || [],
        partCount: m.part_count ?? (m.parts || []).length,
        parts: m.parts || [],
      };
      this.moduleList.push(entry);
      for (const n of entry.parts) this.moduleOfPart.set(n, key);
    }

    /* ---- wiring: harness -> wires ---- */
    this.harnesses = new Map();          // harness name -> {name, wires[], circuits, length}
    for (const w of this.wiring.wires || []) {
      let h = this.harnesses.get(w.harness);
      if (!h) {
        h = { name: w.harness, wires: [], circuits: new Set(), length: 0 };
        this.harnesses.set(w.harness, h);
      }
      h.wires.push(w);
      h.circuits.add(w.circuit);
      h.length += w.length_m || 0;
    }
    for (const h of this.harnesses.values()) {
      h.circuits = [...h.circuits].sort();
      h.count = h.wires.length;
    }
    this.harnessList = [...this.harnesses.values()]
      .sort((a, b) => a.name.localeCompare(b.name));

    /* ---- hoses + tie straps ---- */
    this.hoseSystems = new Map();
    for (const h of this.hoses.hoses || []) {
      let s = this.hoseSystems.get(h.hose);
      if (!s) { s = { name: h.hose, hoses: [], straps: [], length: 0 }; this.hoseSystems.set(h.hose, s); }
      s.hoses.push(h);
      s.length += h.length_m || 0;
    }
    for (const t of this.hoses.tie_straps || []) {
      let s = this.hoseSystems.get(t.hose);
      if (!s) { s = { name: t.hose, hoses: [], straps: [], length: 0 }; this.hoseSystems.set(t.hose, s); }
      s.straps.push(t);
    }
    this.hoseSystemList = [...this.hoseSystems.values()]
      .sort((a, b) => a.name.localeCompare(b.name));

    /* ---- trace polylines: name -> flat [x,y,z,...] ----
       The manifest is authored in Blender's Z-up frame, but the glTF
       export is Y-up. Convert once here so every polyline is in the same
       space as the loaded geometry:  (x, y, z)_blender -> (x, z, -y)_gltf */
    this.tracePolylines = new Map();
    for (const w of this.wiring.wires || []) {
      if (w.trace_points && w.trace_points.length >= 6) {
        this.tracePolylines.set(w.name, blenderToGltf(w.trace_points));
      }
    }
    for (const h of this.hoses.hoses || []) {
      if (h.trace_points && h.trace_points.length >= 6) {
        this.tracePolylines.set(h.name, blenderToGltf(h.trace_points));
      }
    }

    /* ---- every trace-capable object (wires + hoses + tie straps) ----
       Tie straps carry no polyline in the manifest, so they are listed
       separately and get a geometry-derived arc length in the viewer. */
    this.traceNames = new Set(this.tracePolylines.keys());
    this.traceNoPolyline = new Set();
    for (const t of this.hoses.tie_straps || []) {
      this.traceNames.add(t.name);
      this.traceNoPolyline.add(t.name);
    }

    /* ---- sequence: part name -> step ---- */
    this.stepOfPart = new Map();
    this.steps = (this.sequence.steps || []).map((s) => {
      for (const n of s.parts || []) this.stepOfPart.set(n, s);
      return {
        step: s.step,
        key: s.key,
        title: s.title,
        empty: s.empty,
        dir: s.explode_dir || [0, 0, 1],
        distance: s.explode_distance_m || 0,
        partCount: s.part_count ?? (s.parts || []).length,
        parts: s.parts || [],
        note: s.note || '',
      };
    });
    this.stepCount = this.sequence.step_count ?? this.steps.length;

    /* ---- group / collection option lists ---- */
    this.groupCodes = this.raw.group_codes || {};
    this.groupDocs = this.raw.group_codes_doc || {};
    this.groupList = [...this.byGroup.keys()].sort();
    this.collectionList = [...this.byCollection.keys()].sort();
  }

  /* ---------- lookups ---------- */
  part(name) { return this.partsByName.get(name) || null; }

  moduleFor(name) {
    const k = this.moduleOfPart.get(name);
    return k ? this.modules[k] : null;
  }

  stepFor(name) { return this.stepOfPart.get(name) || null; }

  harnessFor(name) {
    const p = this.partsByName.get(name);
    if (!p) return null;
    const w = (this.wiring.wires || []).find((x) => x.name === name);
    return w ? this.harnesses.get(w.harness) : null;
  }

  /** Human label for a group code, e.g. "EL" -> "EL — Electrical" */
  groupLabel(code) {
    const doc = this.groupDocs[code];
    return doc ? `${code} — ${doc}` : code;
  }

  /** Colour used for a group in the legend / swatches. */
  groupColor(code) {
    return GROUP_COLORS[code] || '#8a97a8';
  }

  /** All parts belonging to a module key. */
  partsOfModule(key) {
    const m = this.modules[key];
    if (!m) return [];
    return (m.parts || []).map((n) => this.partsByName.get(n)).filter(Boolean);
  }

  /** Summary stats for the header. */
  stats() {
    return {
      parts: this.partCount,
      steps: this.stepCount,
      harnesses: this.harnessList.length,
      modules: this.moduleList.length,
      wires: this.wiring.wire_segment_count ?? (this.wiring.wires || []).length,
      hoses: this.hoses.hose_segment_count ?? 0,
      straps: this.hoses.tie_strap_count ?? 0,
      collections: this.collectionCount,
      materials: this.materialCount,
    };
  }
}

function push(map, key, val) {
  let a = map.get(key);
  if (!a) { a = []; map.set(key, a); }
  a.push(val);
}

/**
 * Blender (Z-up, right-handed) -> glTF (Y-up, right-handed).
 * The exporter rotates -90° about X, i.e. (x, y, z) -> (x, z, -y).
 * Manifest trace polylines are authored in the Blender frame, so they
 * must be converted before being compared against exported geometry.
 */
function blenderToGltf(flat) {
  const out = new Array(flat.length);
  for (let i = 0; i + 2 < flat.length; i += 3) {
    out[i] = flat[i];
    out[i + 1] = flat[i + 2];
    out[i + 2] = -flat[i + 1];
  }
  return out;
}

/* ---------- group palette (matches the Blender viewport legend) ---------- */
export const GROUP_COLORS = {
  BD: '#c9a227', SH: '#8d99ae', DR: '#6c8ebf', DRM: '#5b7fa6', GL: '#7fd4e8',
  MI: '#9bb1c9', MD: '#b08968', SL: '#4a4e57', IN: '#a98467', ST: '#8f6f4e',
  LM: '#ffe066', EL: '#ffb020', EN: '#e05c3a', EX: '#a0522d', TR: '#4aa3ff',
  EM: '#7a9e5b', SU: '#3ddc84', SR: '#ff5c5c', WH: '#2f2f33', FT: '#b8b8b8',
  BR: '#d94f4f', FL: '#3fa9f5', BA: '#f2c14e', SF: '#ff8c42', CL: '#6b7280',
};

/* ============================================================
   Loader
   ============================================================ */
export async function loadAsset(sourceKey, onProgress = () => {}) {
  const src = SOURCES[sourceKey];
  if (!src) throw new Error(`Unknown source "${sourceKey}"`);

  onProgress('manifest', 0.05);
  const manifest = await fetchJSON(src.manifest);
  onProgress('manifest', 0.25);

  const data = new AssetData(manifest, sourceKey);

  /* module manifests are optional extras — a failure must not break the app */
  data.moduleManifests = {};
  let done = 0;
  await Promise.all(
    MODULE_KEYS.map(async (k) => {
      try {
        data.moduleManifests[k] = await fetchJSON(src.moduleManifest(k));
      } catch (e) {
        data.moduleManifests[k] = null;
      } finally {
        done += 1;
        onProgress('module manifests', 0.25 + 0.15 * (done / MODULE_KEYS.length));
      }
    })
  );

  return data;
}
