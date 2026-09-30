"""Probe the trunk/quarter shut line to design a correct gap test."""
import bpy
from mathutils import Vector

bpy.ops.wm.open_mainfile(
    filepath="/workspace/documents/altima2000_v6/altima2000_assembly.blend")
sc = bpy.context.scene


def bb(ob):
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (min(p.x for p in pts), max(p.x for p in pts),
            min(p.y for p in pts), max(p.y for p in pts),
            min(p.z for p in pts), max(p.z for p in pts))


for nm in ("ALTIMA2000_BODY_TrunkLid_Outer", "ALTIMA2000_BODY_Quarter_Rear_R",
           "ALTIMA2000_BODY_Quarter_Rear_L", "ALTIMA2000_BODY_Hood_Outer",
           "ALTIMA2000_BODY_Fender_Front_R"):
    ob = sc.objects.get(nm)
    if ob is None:
        print("MISSING", nm)
        continue
    x0, x1, y0, y1, z0, z1 = bb(ob)
    print("%-38s x=[%.3f,%.3f] y=[%.3f,%.3f] z=[%.3f,%.3f]"
          % (nm, x0, x1, y0, y1, z0, z1))

# all BODY_ parts, to see what the trunk/quarter family actually is
print("--- BODY_ parts ---")
for ob in sorted(sc.objects, key=lambda o: o.name):
    if ob.type == "MESH" and ob.name.startswith("ALTIMA2000_BODY_"):
        x0, x1, y0, y1, z0, z1 = bb(ob)
        print("  %-40s x=[%.2f,%.2f] y=[%.2f,%.2f] z=[%.2f,%.2f]"
              % (ob.name, x0, x1, y0, y1, z0, z1))
print("PROBE2_DONE")
