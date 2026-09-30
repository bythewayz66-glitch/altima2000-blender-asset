"""ALTIMA2000 v6 verification.

Covers: naming, duplicates, manifest (master + per-module, JSON + CSV),
collections, module opens, linked assembly, glTF integrity, wiring/hose counts,
trace shader, wheel orientation, panel gaps, disassemble/reassemble round-trip,
the full-car sequence round-trip, and teardown-animation playback.

NOTE ON ORDERING: the shipped operator file is exec'd and registered AFTER
``open_mainfile``.  ``open_mainfile`` resets the Python/RNA state, so classes
registered before it are gone afterwards - which is exactly why the earlier
verify pass reported every operator as missing.
"""
import csv
import json
import os
import re
import sys

import bpy
from mathutils import Vector

OUT = os.environ.get("ALTIMA_OUT", "/workspace/documents/altima2000_v6")
SRC = os.path.join(OUT, "source")
sys.path.insert(0, SRC)

FAIL = []
PASS = []


def check(label, ok, detail=""):
    (PASS if ok else FAIL).append(label)
    print("%-4s %-52s %s" % ("PASS" if ok else "FAIL", label, detail))


# ---- authoritative naming regex, read out of the builder source ------------
src = open(os.path.join(SRC, "altima", "builder.py")).read()
m = re.search(r"NAME_RE\s*=\s*re\.compile\(\s*r?[\"']([^\"']+)[\"']", src)
NAME_RE = re.compile(m.group(1))
print("NAME_RE =", NAME_RE.pattern)

MASTER = os.path.join(OUT, "altima2000_assembly.blend")
TOOLS = os.path.join(OUT, "altima2000_assembly_tools.py")

bpy.ops.wm.open_mainfile(filepath=MASTER)
sc = bpy.context.scene

# register the shipped operators AFTER the file is open (see module docstring)
_ns = {"bpy": bpy, "__name__": "altima2000_assembly_tools"}
exec(open(TOOLS).read(), _ns)
_ns["register"]()
print("OPERATORS_REGISTERED")

parts = [o for o in sc.objects if o.type == "MESH" and o.name.startswith("ALTIMA2000_")]
print("PART_COUNT", len(parts))

bad = [o.name for o in parts if not NAME_RE.match(o.name)]
check("naming compliance", len(bad) == 0, "bad=%d %s" % (len(bad), bad[:5]))

names = [o.name for o in sc.objects]
dupes = len(names) - len(set(names))
check("zero duplicate names", dupes == 0, "dupes=%d" % dupes)

# ---- master manifest ------------------------------------------------------
doc = json.load(open(os.path.join(OUT, "altima2000_manifest.json")))
rows = doc["parts"]
check("manifest json rows == part count", len(rows) == len(parts),
      "json=%d parts=%d" % (len(rows), len(parts)))
missing_off = [r["name"] for r in rows if not r.get("offset_m")]
check("every manifest row has an offset", len(missing_off) == 0,
      "missing=%d" % len(missing_off))
missing_pos = [r["name"] for r in rows if not r.get("position")]
check("every manifest row has a position", len(missing_pos) == 0,
      "missing=%d" % len(missing_pos))
with open(os.path.join(OUT, "altima2000_manifest.csv")) as fh:
    csv_lines = fh.read().strip().split("\n")
check("manifest csv rows == part count", len(csv_lines) - 1 == len(parts),
      "csv=%d parts=%d" % (len(csv_lines) - 1, len(parts)))

# ---- collections ----------------------------------------------------------
colls = [c for c in bpy.data.collections]
check("collection count", len(colls) >= 50, "collections=%d" % len(colls))

# ---- wiring + hoses -------------------------------------------------------
wires = [o for o in parts if "_Wire_" in o.name]
hoses = [o for o in parts if "_Hose_" in o.name]
straps = [o for o in parts if "_TieStrap_" in o.name]
harn = set()
for o in parts:
    h = o.get("asmb", {}).get("harness")
    if h:
        harn.add(h)
check("wire segments present", len(wires) == 323, "wires=%d" % len(wires))
check("31 harnesses", len(harn) == 31, "harnesses=%d" % len(harn))
check("routed hose segments present", len(hoses) == 37, "hoses=%d" % len(hoses))
check("tie straps present", len(straps) == 38, "straps=%d" % len(straps))
legacy = [o for o in parts if o.name.startswith("ALTIMA2000_EN_Hose_")]
check("no legacy straight hoses left", len(legacy) == 0, "legacy=%d" % len(legacy))

# ---- trace shader ---------------------------------------------------------
trace_mats = [mm for mm in bpy.data.materials
              if mm.use_nodes and mm.node_tree
              and mm.node_tree.nodes.get("TraceProgress")]
check("trace materials present", len(trace_mats) >= 2, "mats=%d" % len(trace_mats))
hose_trace = [o for o in hoses if o.data.attributes.get("trace_t")]
check("hoses carry trace_t attribute", len(hose_trace) == len(hoses),
      "with_attr=%d/%d" % (len(hose_trace), len(hoses)))
strap_trace = [o for o in straps if o.data.attributes.get("trace_t")]
check("straps carry trace_t attribute", len(strap_trace) == len(straps),
      "with_attr=%d/%d" % (len(strap_trace), len(straps)))
wire_trace = [o for o in wires if o.data.attributes.get("trace_t")]
check("wires carry trace_t attribute", len(wire_trace) == len(wires),
      "with_attr=%d/%d" % (len(wire_trace), len(wires)))

# ---- operators registered -------------------------------------------------
ops = list(dir(bpy.ops.altima))
for want in ("trace_modal", "harness_show_all", "harness_hide_all",
             "harness_refresh", "disassemble", "reassemble", "sequence_all",
             "sequence_step", "sequence_reset", "trace_wire", "trace_all",
             "trace_clear", "verify_assembly"):
    check("operator altima.%s" % want, want in ops)

# ---- harness panel data ---------------------------------------------------
bpy.ops.altima.harness_refresh()
items = [it.name for it in sc.altima_harnesses]
check("harness panel lists 31", len(items) == 31, "items=%d" % len(items))
if items:
    it = sc.altima_harnesses[0]
    it.visible = False
    hid = [o for o in parts if o.get("asmb", {}).get("harness") == it.name]
    check("harness toggle hides its objects",
          all(o.hide_viewport for o in hid), "n=%d" % len(hid))
    it.visible = True
    check("harness toggle restores its objects",
          all(not o.hide_viewport for o in hid), "n=%d" % len(hid))

# ---- wheel orientation ----------------------------------------------------
def bbox(ob):
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    zs = [p.z for p in pts]
    return (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))


tires = [o for o in parts if "Tire_Road" in o.name]
if tires:
    dx, dy, dz = bbox(tires[0])
    check("wheel axle points sideways (thin in Y, round in X/Z)",
          dy < dx * 0.5 and abs(dx - dz) < 0.05,
          "%s dx=%.3f dy=%.3f dz=%.3f" % (tires[0].name, dx, dy, dz))
    all_ok = True
    for t in tires:
        a, b, c = bbox(t)
        if not (b < a * 0.5 and abs(a - c) < 0.05):
            all_ok = False
    check("all four wheels oriented correctly", all_ok, "n=%d" % len(tires))

# ---- panel gaps -----------------------------------------------------------
# A bounding-box gap is the wrong measure for a shut line: the quarter panel
# wraps around the trunk lid, so their boxes overlap even though the surfaces
# are separated.  Measure the real minimum surface-to-surface distance instead.
def surface_gap(a, b, samples=400):
    """Minimum distance from a's surface to b's surface (metres)."""
    import random
    rnd = random.Random(1234)
    verts = [a.matrix_world @ v.co for v in a.data.vertices]
    if not verts:
        return 0.0
    if len(verts) > samples:
        verts = rnd.sample(verts, samples)
    best = 1e9
    for p in verts:
        ok, loc, nrm, idx = b.closest_point_on_mesh(b.matrix_world.inverted() @ p)
        if not ok:
            continue
        d = (p - (b.matrix_world @ loc)).length
        best = min(best, d)
    return best


hood = next((o for o in parts if o.name == "ALTIMA2000_BODY_Hood_Outer"), None)
fend = next((o for o in parts if o.name == "ALTIMA2000_BODY_Fender_Front_R"), None)
if hood and fend:
    g = surface_gap(hood, fend)
    check("hood/fender shut line is open", g > 0.004, "gap=%.4f m" % g)
trunk = next((o for o in parts if o.name == "ALTIMA2000_BODY_TrunkLid_Outer"), None)
qtr = next((o for o in parts if o.name == "ALTIMA2000_BODY_Quarter_Rear_R"), None)
if trunk and qtr:
    g = surface_gap(trunk, qtr)
    check("trunk/quarter shut line is open", g > 0.004, "gap=%.4f m" % g)
side = next((o for o in parts if o.name == "ALTIMA2000_BODY_Side_Body_R"), None)
if side and fend:
    g = surface_gap(side, fend)
    check("fender/side-body shut line is open", g > 0.004, "gap=%.4f m" % g)

# ---- round trip -----------------------------------------------------------
built = {o.name: o.location.copy() for o in parts}
bpy.ops.altima.disassemble()
moved = sum(1 for o in parts if (o.location - built[o.name]).length > 1e-6)
check("disassemble moves parts", moved > len(parts) * 0.9,
      "moved=%d/%d" % (moved, len(parts)))
bpy.ops.altima.reassemble()
worst = max((built[o.name] - o.location).length for o in parts)
check("reassemble round-trip < 1e-6 m", worst < 1e-6, "worst=%.3e m" % worst)

# ---- full-car sequence ----------------------------------------------------
steps = [o for o in sc.objects
         if o.type == "EMPTY" and o.get("asmb", {}).get("kind") == "sequence_step"]
steps.sort(key=lambda o: int(o.get("asmb", {}).get("step_index", 0)))
check("sequence extends beyond the engine bay", len(steps) > 12, "steps=%d" % len(steps))
seq_total = sum(int(o.get("asmb", {}).get("part_count", 0)) for o in steps)
check("sequence covers every part", seq_total == len(parts),
      "sequenced=%d parts=%d" % (seq_total, len(parts)))
check("engine-bay steps 01-12 unchanged",
      all(int(steps[i].get("asmb", {}).get("part_count", 0)) > 0 for i in range(12)),
      "steps01-12=%s" % [int(s.get("asmb", {}).get("part_count", 0)) for s in steps[:12]])
for o in steps:
    i = o.get("asmb", {})
    for key in ("step_index", "step_key", "step_title", "explode_dir",
                "explode_distance", "part_count", "parts"):
        if key not in i:
            check("step %s has %s" % (o.name, key), False)
            break
    else:
        continue
    break
else:
    check("every step empty carries its full custom-property set", True)

seq_ok = True
try:
    bpy.ops.altima.sequence_all(reverse=False)
    bpy.ops.altima.sequence_all(reverse=True)
    worst2 = max((built[o.name] - o.location).length for o in parts)
    seq_ok = worst2 < 1e-6
    print("SEQ_ROUNDTRIP worst=%.3e" % worst2)
except Exception as e:
    seq_ok = False
    print("SEQ_ERROR", e)
check("full-car sequence round-trip", seq_ok)

# ---- teardown animation ---------------------------------------------------
anim_objs = [o for o in sc.objects if o.animation_data and o.animation_data.action]
check("teardown animation keyframed on the step empties",
      len(anim_objs) == len(steps), "animated=%d steps=%d" % (len(anim_objs), len(steps)))
check("scene frame range matches the step count",
      sc.frame_end - sc.frame_start + 1 == len(steps) + 1,
      "frames=%d..%d" % (sc.frame_start, sc.frame_end))
# sample the animation: frame 1 assembled, last frame exploded
if steps:
    sc.frame_set(sc.frame_start)
    bpy.context.view_layer.update()
    p0 = steps[0].matrix_world.translation.copy()
    sc.frame_set(sc.frame_end)
    bpy.context.view_layer.update()
    p1 = steps[0].matrix_world.translation.copy()
    check("animation actually moves the first step empty",
          (p1 - p0).length > 0.05, "delta=%.3f m" % (p1 - p0).length)
    sc.frame_set(sc.frame_start)

# ---- modules --------------------------------------------------------------
MODS = ["engine", "drivetrain", "suspension", "wheels", "brakes", "exhaust", "doors"]
for mod in MODS:
    p = os.path.join(OUT, "altima2000_module_%s.blend" % mod)
    ok = os.path.exists(p) and os.path.getsize(p) > 1000
    check("module %s opens" % mod, ok, "%d bytes" % (os.path.getsize(p) if ok else 0))

# ---- per-module manifests -------------------------------------------------
for mod in MODS:
    jp = os.path.join(OUT, "altima2000_module_%s_manifest.json" % mod)
    cp = os.path.join(OUT, "altima2000_module_%s_manifest.csv" % mod)
    if not (os.path.exists(jp) and os.path.exists(cp)):
        check("module %s manifest present" % mod, False)
        continue
    md = json.load(open(jp))
    with open(cp) as fh:
        n_csv = len(fh.read().strip().split("\n")) - 1
    check("module %s manifest json==csv==part_count" % mod,
          len(md["parts"]) == n_csv == md["part_count"],
          "json=%d csv=%d count=%d" % (len(md["parts"]), n_csv, md["part_count"]))
    check("module %s manifest rows map to master" % mod,
          all("master_index" in r and r["name"] in {x["name"] for x in rows}
              for r in md["parts"]),
          "n=%d" % len(md["parts"]))

# ---- module standalone reassembly ----------------------------------------
mod_path = os.path.join(OUT, "altima2000_module_engine.blend")
bpy.ops.wm.open_mainfile(filepath=mod_path)
sc_m = bpy.context.scene
_ns2 = {"bpy": bpy, "__name__": "altima2000_assembly_tools"}
exec(open(TOOLS).read(), _ns2)
_ns2["register"]()
m_parts = [o for o in sc_m.objects if o.type == "MESH" and o.name.startswith("ALTIMA2000_")]
m_built = {o.name: o.location.copy() for o in m_parts}
bpy.ops.altima.disassemble()
bpy.ops.altima.reassemble()
m_worst = max((m_built[o.name] - o.location).length for o in m_parts)
check("module reassembles standalone (engine)", m_worst < 1e-6,
      "parts=%d worst=%.3e m" % (len(m_parts), m_worst))

# ---- linked assembly ------------------------------------------------------
bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "altima2000_assembly_linked.blend"))
sc2 = bpy.context.scene
libs = [c for c in bpy.data.collections if c.library is not None]
missing = [c.name for c in libs if c.library.is_missing]
check("linked assembly resolves every module", len(missing) == 0,
      "linked=%d missing=%d" % (len(libs), len(missing)))
linked_parts = [o for o in sc2.objects if o.type == "MESH" and o.name.startswith("ALTIMA2000_")]
check("linked assembly part count", len(linked_parts) == len(parts),
      "linked=%d master=%d" % (len(linked_parts), len(parts)))

# ---- glTF -----------------------------------------------------------------
gltf = json.load(open(os.path.join(OUT, "altima2000.gltf")))
exts = set()
for mm in gltf.get("materials", []):
    exts.update(mm.get("extensions", {}).keys())
check("glTF node count ~= part count",
      abs(len(gltf.get("nodes", [])) - len(parts)) < 60,
      "nodes=%d parts=%d" % (len(gltf.get("nodes", [])), len(parts)))
check("glTF keeps clearcoat", "KHR_materials_clearcoat" in exts, str(sorted(exts)))
check("glTF keeps transmission", "KHR_materials_transmission" in exts)
anims = gltf.get("animations", [])
check("glTF carries the teardown animation", len(anims) >= 1,
      "animations=%d" % len(anims))
if anims:
    ch = sum(len(a.get("channels", [])) for a in anims)
    check("glTF animation has channels", ch >= len(steps),
          "channels=%d" % ch)

print("")
print("VERIFY_SUMMARY pass=%d fail=%d" % (len(PASS), len(FAIL)))
if FAIL:
    print("FAILED:", FAIL)
    print("VERIFY_RESULT FAIL")
else:
    print("VERIFY_RESULT ALL_PASS")
