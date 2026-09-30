"""Probe the built v4/v5 blend: wheels, sequence steps, animation, ops-after-open."""
import os
import sys

import bpy
from mathutils import Vector

BLEND = os.environ.get("PROBE_BLEND",
                       "/workspace/documents/altima2000_v6/altima2000_assembly.blend")
TOOLS = os.path.join(os.path.dirname(BLEND), "altima2000_assembly_tools.py")

bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene

# --- operators AFTER open_mainfile (mimics verify_v4 order) -----------------
ns = {"bpy": bpy, "__name__": "altima2000_assembly_tools"}
exec(open(TOOLS).read(), ns)
ns["register"]()
ops = sorted(dir(bpy.ops.altima))
print("OPS_AFTER_OPEN", ops)

parts = [o for o in sc.objects if o.type == "MESH" and o.name.startswith("ALTIMA2000_")]
print("PART_COUNT", len(parts))


def bbox(ob):
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    zs = [p.z for p in pts]
    return (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))


print("--- WHEELS ---")
for ob in sorted(parts, key=lambda o: o.name):
    if "Tire_Road" in ob.name or "Rim_Alloy" in ob.name:
        dx, dy, dz = bbox(ob)
        print("  %-42s dx=%.3f dy=%.3f dz=%.3f" % (ob.name, dx, dy, dz))

print("--- SEQUENCE ---")
steps = [o for o in sc.objects
         if o.type == "EMPTY" and o.get("asmb", {}).get("kind") == "sequence_step"]
steps.sort(key=lambda o: int(o.get("asmb", {}).get("step_index", 0)))
print("STEP_COUNT", len(steps))
for o in steps:
    i = o.get("asmb", {})
    print("  %-40s parts=%4s dist=%.2f" % (o.name, i.get("part_count"),
                                           i.get("explode_distance", 0.0)))

print("--- ANIMATION ---")
n_anim = 0
for o in sc.objects:
    ad = o.animation_data
    if ad and ad.action:
        n_anim += 1
print("OBJECTS_WITH_ACTION", n_anim)
print("FRAME_RANGE", sc.frame_start, sc.frame_end)
print("PROBE_DONE")
