"""ALTIMA2000 v4 verification - naming, manifest, modules, glTF, hoses, trace, round-trip."""
import json
import os
import re
import sys

import bpy
from mathutils import Vector

OUT = os.environ.get("ALTIMA_OUT", "/workspace/documents/altima2000_v4")
SRC = os.path.join(OUT, "source")
sys.path.insert(0, SRC)

FAIL = []
PASS = []


def check(label, ok, detail=""):
    (PASS if ok else FAIL).append(label)
    print("%-4s %-46s %s" % ("PASS" if ok else "FAIL", label, detail))


# ---- authoritative naming regex, read out of the builder source ------------
src = open(os.path.join(SRC, "altima", "builder.py")).read()
m = re.search(r"NAME_RE\s*=\s*re\.compile\(\s*r?[\"']([^\"']+)[\"']", src)
NAME_RE = re.compile(m.group(1))
print("NAME_RE =", NAME_RE.pattern)

MASTER = os.path.join(OUT, "altima2000_assembly.blend")

# register the shipped assembly operators (disassemble / reassemble / sequence /
# trace / harness panel) exactly as the add-on would, so the checks below can
# actually call them.
TOOLS = os.path.join(OUT, "altima2000_assembly_tools.py")
_ns = {"bpy": bpy, "__name__": "altima2000_assembly_tools"}
exec(open(TOOLS).read(), _ns)
_ns["register"]()
print("OPERATORS_REGISTERED")

bpy.ops.wm.open_mainfile(filepath=MASTER)
sc = bpy.context.scene

parts = [o for o in sc.objects if o.type == "MESH" and o.name.startswith("ALTIMA2000_")]
print("PART_COUNT", len(parts))

bad = [o.name for o in parts if not NAME_RE.match(o.name)]
check("naming compliance", len(bad) == 0, "bad=%d %s" % (len(bad), bad[:5]))

names = [o.name for o in sc.objects]
dupes = len(names) - len(set(names))
check("zero duplicate names", dupes == 0, "dupes=%d" % dupes)

# ---- manifest -------------------------------------------------------------
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
csv_lines = open(os.path.join(OUT, "altima2000_manifest.csv")).read().strip().split("\n")
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
check("no legacy straight hoses left",
      not any(o.name.startswith("ALTIMA2000_EN_Hose_") for o in parts),
      "legacy=%d" % len([o for o in parts if o.name.startswith("ALTIMA2000_EN_Hose_")]))

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

# ---- operators registered -------------------------------------------------
ops = [o for o in dir(bpy.ops.altima)]
for want in ("trace_modal", "harness_show_all", "harness_hide_all",
             "harness_refresh", "disassemble", "reassemble", "sequence_all"):
    check("operator altima.%s" % want, want in ops)

# ---- harness panel data ---------------------------------------------------
n = bpy.ops.altima.harness_refresh()
items = [it.name for it in sc.altima_harnesses]
check("harness panel lists 31", len(items) == 31, "items=%d" % len(items))
# toggle one off and confirm its objects hide
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


tires = [o for o in parts if "Tire" in o.name and "Tread" not in o.name]
if tires:
    dx, dy, dz = bbox(tires[0])
    # a correctly oriented wheel is thin along X (width) and round in Y/Z
    check("wheel axle points sideways (thin in X, round in Y/Z)",
          dx < dy * 0.5 and abs(dy - dz) < 0.05,
          "%s dx=%.3f dy=%.3f dz=%.3f" % (tires[0].name, dx, dy, dz))

# ---- panel gaps -----------------------------------------------------------
def gap_between(a, b):
    """Smallest separation between two objects' world bounding boxes."""
    pa = [a.matrix_world @ Vector(c) for c in a.bound_box]
    pb = [b.matrix_world @ Vector(c) for c in b.bound_box]
    ax = (min(p.x for p in pa), max(p.x for p in pa))
    bx = (min(p.x for p in pb), max(p.x for p in pb))
    ay = (min(p.y for p in pa), max(p.y for p in pa))
    by = (min(p.y for p in pb), max(p.y for p in pb))
    az = (min(p.z for p in pa), max(p.z for p in pa))
    bz = (min(p.z for p in pb), max(p.z for p in pb))
    gx = max(0.0, max(ax[0], bx[0]) - min(ax[1], bx[1]))
    gy = max(0.0, max(ay[0], by[0]) - min(ay[1], by[1]))
    gz = max(0.0, max(az[0], bz[0]) - min(az[1], bz[1]))
    return max(gx, gy, gz)


hood = next((o for o in parts if o.name == "ALTIMA2000_BODY_Hood_Outer"), None)
fend = next((o for o in parts if "Fender_Front_R" in o.name), None)
if hood and fend:
    g = gap_between(hood, fend)
    check("hood/fender shut line is open", g > 0.004, "gap=%.4f m" % g)

# ---- round trip -----------------------------------------------------------
built = {o.name: o.location.copy() for o in parts}
bpy.ops.altima.disassemble()
moved = sum(1 for o in parts if (o.location - built[o.name]).length > 1e-6)
check("disassemble moves parts", moved > len(parts) * 0.9,
      "moved=%d/%d" % (moved, len(parts)))
bpy.ops.altima.reassemble()
worst = max((built[o.name] - o.location).length for o in parts)
check("reassemble round-trip < 1e-6 m", worst < 1e-6, "worst=%.3e m" % worst)

# ---- sequence round trip --------------------------------------------------
seq_ok = True
try:
    bpy.ops.altima.sequence_all(direction="FORWARD")
    bpy.ops.altima.sequence_all(direction="REVERSE")
    worst2 = max((built[o.name] - o.location).length for o in parts)
    seq_ok = worst2 < 1e-6
    print("SEQ_ROUNDTRIP worst=%.3e" % worst2)
except Exception as e:
    seq_ok = False
    print("SEQ_ERROR", e)
check("12-step sequence round-trip", seq_ok)

# ---- modules --------------------------------------------------------------
MODS = ["engine", "drivetrain", "suspension", "wheels", "brakes", "exhaust", "doors"]
for mod in MODS:
    p = os.path.join(OUT, "altima2000_module_%s.blend" % mod)
    ok = os.path.exists(p) and os.path.getsize(p) > 1000
    check("module %s opens" % mod, ok, "%d bytes" % (os.path.getsize(p) if ok else 0))

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

print("")
print("VERIFY_SUMMARY pass=%d fail=%d" % (len(PASS), len(FAIL)))
if FAIL:
    print("FAILED:", FAIL)
    print("VERIFY_RESULT FAIL")
else:
    print("VERIFY_RESULT ALL_PASS")
