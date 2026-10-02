/* ============================================================
   trace.js — touch/selection glow + progressive trace
   ------------------------------------------------------------
   Every wire, hose and tie strap in the asset carries a baked
   trace coordinate in the Blender build (mesh attribute
   `trace_t`, normalised arc length 0..1 along the run).  glTF
   does not export custom attributes, so we rebuild the same
   value here from the manifest's `trace_points` polyline:

     for each vertex -> nearest point on the polyline
                     -> normalised arc length  -> aTraceT

   The shader then lights the run progressively:
     * uProgress sweeps 0 -> 1 and a bright head travels with it
     * everything behind the head stays lit (the "trail")
     * uGlow fades the whole effect in/out on hover or selection
   ============================================================ */

import * as THREE from 'three';

/* ------------------------------------------------------------
   Arc-length attribute
   ------------------------------------------------------------ */

/**
 * Build a per-vertex normalised arc-length attribute for a mesh
 * whose geometry follows `polyline` (flat [x,y,z, x,y,z, ...]).
 * Returns a Float32Array of length vertexCount.
 */
export function buildTraceAttribute(geometry, polyline) {
  const pos = geometry.getAttribute('position');
  const n = pos.count;
  const out = new Float32Array(n);

  if (!polyline || polyline.length < 6) {
    // no polyline: fall back to a straight 0..1 ramp on Y so the
    // shader still has something monotonic to sweep
    for (let i = 0; i < n; i++) out[i] = i / Math.max(1, n - 1);
    return out;
  }

  const pts = [];
  for (let i = 0; i + 2 < polyline.length; i += 3) {
    pts.push(new THREE.Vector3(polyline[i], polyline[i + 1], polyline[i + 2]));
  }

  // cumulative arc length at each polyline point
  const cum = [0];
  for (let i = 1; i < pts.length; i++) {
    cum.push(cum[i - 1] + pts[i].distanceTo(pts[i - 1]));
  }
  const total = cum[cum.length - 1] || 1;

  const v = new THREE.Vector3();
  const ab = new THREE.Vector3();
  const ap = new THREE.Vector3();
  const proj = new THREE.Vector3();

  for (let i = 0; i < n; i++) {
    v.fromBufferAttribute(pos, i);

    let best = Infinity;
    let bestT = 0;

    for (let s = 0; s < pts.length - 1; s++) {
      const a = pts[s];
      const b = pts[s + 1];
      ab.subVectors(b, a);
      ap.subVectors(v, a);
      const len2 = ab.lengthSq();
      let t = len2 > 1e-12 ? ap.dot(ab) / len2 : 0;
      t = t < 0 ? 0 : t > 1 ? 1 : t;
      proj.copy(a).addScaledVector(ab, t);
      const d = proj.distanceToSquared(v);
      if (d < best) {
        best = d;
        bestT = (cum[s] + t * (cum[s + 1] - cum[s])) / total;
      }
    }
    out[i] = bestT;
  }
  return out;
}

/**
 * Fallback arc-length for meshes that have no manifest polyline
 * (tie straps carry only `trace_attr`, not `trace_points`).
 * Projects every vertex onto the geometry's principal axis, so the
 * sweep still runs end to end along the strap's long dimension.
 */
export function buildTraceAttributeFromGeometry(geometry) {
  const pos = geometry.getAttribute('position');
  const n = pos.count;
  const out = new Float32Array(n);
  if (!n) return out;

  geometry.computeBoundingBox();
  const bb = geometry.boundingBox;
  const size = new THREE.Vector3();
  bb.getSize(size);

  // principal axis = longest bounding-box dimension
  let axis = new THREE.Vector3(1, 0, 0);
  if (size.y >= size.x && size.y >= size.z) axis.set(0, 1, 0);
  else if (size.z >= size.x && size.z >= size.y) axis.set(0, 0, 1);

  let min = Infinity;
  let max = -Infinity;
  const v = new THREE.Vector3();
  const proj = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    v.fromBufferAttribute(pos, i);
    const p = v.dot(axis);
    proj[i] = p;
    if (p < min) min = p;
    if (p > max) max = p;
  }
  const span = max - min || 1;
  for (let i = 0; i < n; i++) out[i] = (proj[i] - min) / span;
  return out;
}

/**
 * Manifest `trace_points` are authored in WORLD space, but a mesh's
 * position attribute is in its own LOCAL space. Convert the polyline
 * into the mesh's local frame before measuring distances, otherwise
 * every vertex collapses onto the same polyline endpoint.
 */
export function polylineToLocal(polyline, matrixWorld) {
  const inv = new THREE.Matrix4().copy(matrixWorld).invert();
  const out = new Array(polyline.length);
  const v = new THREE.Vector3();
  for (let i = 0; i + 2 < polyline.length; i += 3) {
    v.set(polyline[i], polyline[i + 1], polyline[i + 2]).applyMatrix4(inv);
    out[i] = v.x; out[i + 1] = v.y; out[i + 2] = v.z;
  }
  return out;
}

/* ------------------------------------------------------------
   Shader
   ------------------------------------------------------------ */

const VERT = /* glsl */ `
  attribute float aTraceT;
  varying float vT;
  varying vec3 vNormalW;
  varying vec3 vViewDir;
  varying vec3 vPosW;

  void main() {
    vT = aTraceT;
    vec4 world = modelMatrix * vec4(position, 1.0);
    vPosW = world.xyz;
    vNormalW = normalize(mat3(modelMatrix) * normal);
    vViewDir = normalize(cameraPosition - world.xyz);
    gl_Position = projectionMatrix * viewMatrix * world;
  }
`;

const FRAG = /* glsl */ `
  precision highp float;

  uniform vec3  uBase;        // base (unlit) colour
  uniform vec3  uGlowColor;   // trace colour
  uniform float uProgress;    // 0..1 head position along the run
  uniform float uGlow;        // 0..1 overall effect strength
  uniform float uWidth;       // head half-width in trace units
  uniform float uTrail;       // 0..1 how much of the passed run stays lit
  uniform float uTime;
  uniform float uOpacity;

  varying float vT;
  varying vec3  vNormalW;
  varying vec3  vViewDir;
  varying vec3  vPosW;

  void main() {
    // ---- simple two-light shading so the tube still reads as 3D ----
    vec3 N = normalize(vNormalW);
    vec3 V = normalize(vViewDir);
    vec3 L1 = normalize(vec3(0.55, 0.75, 0.35));
    vec3 L2 = normalize(vec3(-0.5, 0.25, -0.6));
    float d1 = max(dot(N, L1), 0.0);
    float d2 = max(dot(N, L2), 0.0);
    float rim = pow(1.0 - max(dot(N, V), 0.0), 2.5);

    vec3 col = uBase * (0.30 + 0.62 * d1 + 0.22 * d2);
    col += uBase * rim * 0.35;

    // ---- progressive trace ----
    float head = uProgress;
    float dist = vT - head;

    // bright travelling head
    float band = 1.0 - smoothstep(0.0, uWidth, abs(dist));
    band = pow(band, 1.6);

    // everything already swept stays lit (the trail)
    float passed = smoothstep(0.0, 0.02, -dist) * uTrail;

    // gentle pulse so the head reads as "live"
    float pulse = 0.82 + 0.18 * sin(uTime * 7.0);

    float lit = clamp(band * 1.35 + passed * 0.55, 0.0, 1.6) * uGlow;

    col += uGlowColor * lit * pulse * 1.9;

    // a soft halo just ahead of the head
    float halo = exp(-abs(dist) * 9.0) * uGlow * 0.5;
    col += uGlowColor * halo;

    gl_FragColor = vec4(col, uOpacity);
    #include <colorspace_fragment>
  }
`;

/**
 * Create a trace-capable material.
 * @param {THREE.Color|number|string} baseColor
 * @param {object} opts
 */
export function makeTraceMaterial(baseColor, opts = {}) {
  const base = new THREE.Color(baseColor);
  return new THREE.ShaderMaterial({
    uniforms: {
      uBase:      { value: base },
      uGlowColor: { value: new THREE.Color(opts.glowColor ?? 0xffc247) },
      uProgress:  { value: 0 },
      uGlow:      { value: 0 },
      uWidth:     { value: opts.width ?? 0.055 },
      uTrail:     { value: opts.trail ?? 0.55 },
      uTime:      { value: 0 },
      uOpacity:   { value: opts.opacity ?? 1 },
    },
    vertexShader: VERT,
    fragmentShader: FRAG,
    transparent: (opts.opacity ?? 1) < 1,
    side: THREE.DoubleSide,
  });
}

/* ------------------------------------------------------------
   Controller — drives hover / selection / operator-run traces
   ------------------------------------------------------------ */

export class TraceController {
  /**
   * @param {object} opts
   * @param {number} opts.duration  seconds for a full end-to-end sweep
   * @param {number} opts.hold      seconds the finished trace stays lit
   */
  constructor(opts = {}) {
    this.duration = opts.duration ?? 1.6;
    this.hold = opts.hold ?? 1.1;
    this.live = true;                 // hover-driven tracing on/off
    this.entries = new Map();         // mesh.uuid -> entry
    this.active = null;               // currently tracing entry
    this._t = 0;
    this._phase = 'idle';             // idle | sweep | hold | fade
  }

  /** Register a mesh as trace-capable. */
  register(mesh, material) {
    this.entries.set(mesh.uuid, {
      mesh,
      material,
      progress: 0,
      glow: 0,
      targetGlow: 0,
      sweeping: false,
    });
  }

  unregister(mesh) { this.entries.delete(mesh.uuid); }

  /** Start a full end-to-end sweep on a mesh (hover, click, or operator). */
  run(mesh, { restart = true } = {}) {
    const e = this.entries.get(mesh.uuid);
    if (!e) return;
    if (this.active && this.active !== e && restart) {
      this.active.targetGlow = 0;
      this.active.sweeping = false;
    }
    this.active = e;
    if (restart) e.progress = 0;
    e.sweeping = true;
    e.targetGlow = 1;
    this._t = 0;
    this._phase = 'sweep';
  }

  /** Stop tracing (mouse left the wire). */
  release(mesh) {
    const e = this.entries.get(mesh.uuid);
    if (!e) return;
    e.targetGlow = 0;
    e.sweeping = false;
    if (this.active === e) this.active = null;
  }

  /** Keep a wire lit without sweeping (selection). */
  pin(mesh) {
    const e = this.entries.get(mesh.uuid);
    if (!e) return;
    e.targetGlow = 1;
    e.progress = 1;
    e.sweeping = false;
  }

  clearAll() {
    for (const e of this.entries.values()) {
      e.targetGlow = 0;
      e.sweeping = false;
      e.progress = 0;
    }
    this.active = null;
  }

  /** Advance the animation. Call once per frame. */
  update(dt) {
    for (const e of this.entries.values()) {
      // glow fade in/out
      const gTarget = e.targetGlow;
      const rate = gTarget > e.glow ? 6.5 : 3.2;
      e.glow += (gTarget - e.glow) * Math.min(1, rate * dt);
      if (e.glow < 0.002 && gTarget === 0) e.glow = 0;

      // sweep
      if (e.sweeping) {
        e.progress += dt / this.duration;
        if (e.progress >= 1) {
          e.progress = 1;
          e.sweeping = false;
        }
      } else if (e.targetGlow === 0 && e.glow < 0.02) {
        e.progress = 0;
      }

      const u = e.material.uniforms;
      u.uProgress.value = e.progress;
      u.uGlow.value = e.glow;
      u.uTime.value += dt;
    }
  }

  /** True while any wire is lit — lets the render loop idle cheaply. */
  get busy() {
    for (const e of this.entries.values()) {
      if (e.glow > 0.002 || e.sweeping) return true;
    }
    return false;
  }
}
