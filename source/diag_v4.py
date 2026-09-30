"""Diagnostics for the v4 fixes: wheel orientation + panel gaps + harness list."""
import os
import sys
import bpy
from mathutils import Vector

BLEND = os.environ.get("ALTIMA_DIAG_BLEND",
                       "/workspace/documents/altima2000_v4/altima2000_assembly.blend")
bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene


def bbox(ob):
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    zs = [p.z for p in pts]
    return (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs),
            (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2)


print("=== WHEEL PARTS (dx,dy,dz, cx,cy,cz) ===")
for ob in sorted(sc.objects, key=lambda o: o.name):
    if ob.type != "MESH":
        continue
    if not (ob.name.startswith("ALTIMA2000_WHL_") or "LugNut" in ob.name):
        continue
    dx, dy, dz, cx, cy, cz = bbox(ob)
    print("%-46s dx=%.3f dy=%.3f dz=%.3f  c=(%.3f,%.3f,%.3f)"
          % (ob.name, dx, dy, dz, cx, cy, cz))

print("")
print("=== BODY PANEL PARTS (dx,dy,dz, cx,cy,cz) ===")
for ob in sorted(sc.objects, key=lambda o: o.name):
    if ob.type != "MESH":
        continue
    if not ob.name.startswith("ALTIMA2000_BD_"):
        continue
    dx, dy, dz, cx, cy, cz = bbox(ob)
    print("%-46s dx=%.3f dy=%.3f dz=%.3f  c=(%.3f,%.3f,%.3f)"
          % (ob.name, dx, dy, dz, cx, cy, cz))

print("")
print("=== HARNESSES ===")
harn = {}
for ob in sc.objects:
    if ob.type != "MESH":
        continue
    info = ob.get("asmb", {})
    h = info.get("harness")
    if h:
        harn[h] = harn.get(h, 0) + 1
for k in sorted(harn):
    print("HARNESS %-16s %4d" % (k, harn[k]))
print("HARNESS_COUNT", len(harn))

print("")
print("=== HOSE / STRAP PARTS ===")
n = 0
for ob in sorted(sc.objects, key=lambda o: o.name):
    if ob.type != "MESH":
        continue
    if "Hose" in ob.name or "Strap" in ob.name:
        n += 1
        if n <= 40:
            dx, dy, dz, cx, cy, cz = bbox(ob)
            print("%-46s dx=%.3f dy=%.3f dz=%.3f" % (ob.name, dx, dy, dz))
print("HOSE_STRAP_TOTAL", n)

print("")
print("=== TRACE MATERIALS ===")
tm = [m.name for m in bpy.data.materials
      if m.use_nodes and m.node_tree and m.node_tree.nodes.get("TraceProgress")]
print("TRACE_MATERIALS", len(tm), tm[:12])
print("DIAG_DONE")
