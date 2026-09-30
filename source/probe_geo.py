"""Objective check for overlapping / coplanar body panels (z-fighting source).

Vision inspection of the renders was contradictory, so measure the geometry
directly: for each pair of major painted body panels, count how many triangles
actually intersect.  Two panels that merely sit near each other produce 0
intersections; panels that interpenetrate or share a coplanar face produce
hundreds, which is what produces the jagged z-fighting seen in renders.
"""
import itertools

import bpy
from mathutils.bvhtree import BVHTree
from mathutils import Vector

bpy.ops.wm.open_mainfile(
    filepath="/workspace/documents/altima2000_v6/altima2000_assembly.blend")
sc = bpy.context.scene

PAINTED = [
    "ALTIMA2000_BODY_Hood_Outer", "ALTIMA2000_BODY_Hood_Inner",
    "ALTIMA2000_BODY_Fender_Front_L", "ALTIMA2000_BODY_Fender_Front_R",
    "ALTIMA2000_BODY_Side_Body_L", "ALTIMA2000_BODY_Side_Body_R",
    "ALTIMA2000_BODY_Quarter_Rear_L", "ALTIMA2000_BODY_Quarter_Rear_R",
    "ALTIMA2000_BODY_QuarterInner_Rear_L", "ALTIMA2000_BODY_QuarterInner_Rear_R",
    "ALTIMA2000_BODY_TrunkLid_Outer", "ALTIMA2000_BODY_TrunkLid_Inner",
    "ALTIMA2000_BODY_Roof_Outer", "ALTIMA2000_BODY_Rocker_Sill_L",
    "ALTIMA2000_BODY_Rocker_Sill_R", "ALTIMA2000_BODY_Cowl_Panel",
    "ALTIMA2000_BODY_Valance_Front", "ALTIMA2000_BODY_Valance_Rear",
]

objs = {}
for nm in PAINTED:
    ob = sc.objects.get(nm)
    if ob is not None and ob.type == "MESH":
        objs[nm] = ob
print("CHECKING", len(objs), "panels")


def tree_of(ob):
    mw = ob.matrix_world
    verts = [mw @ v.co for v in ob.data.vertices]
    polys = [tuple(p.vertices) for p in ob.data.polygons]
    return BVHTree.FromPolygons(verts, polys, all_triangles=False)


trees = {nm: tree_of(ob) for nm, ob in objs.items()}

hits = []
for a, b in itertools.combinations(sorted(trees), 2):
    ov = trees[a].overlap(trees[b])
    if ov:
        hits.append((a, b, len(ov)))

print("INTERSECTING_PAIRS", len(hits))
for a, b, n in sorted(hits, key=lambda h: -h[2])[:25]:
    print("  %-40s %-40s faces=%d" % (a, b, n))

if not hits:
    print("NO_INTERSECTIONS among painted body panels")

# also measure the real shut-line gaps for the key seams
def surface_gap(a, b, samples=600):
    import random
    rnd = random.Random(7)
    ob_a, ob_b = objs[a], objs[b]
    verts = [ob_a.matrix_world @ v.co for v in ob_a.data.vertices]
    if len(verts) > samples:
        verts = rnd.sample(verts, samples)
    inv = ob_b.matrix_world.inverted()
    best = 1e9
    for p in verts:
        ok, loc, nrm, idx = ob_b.closest_point_on_mesh(inv @ p)
        if ok:
            best = min(best, (p - (ob_b.matrix_world @ loc)).length)
    return best


for a, b in (("ALTIMA2000_BODY_Hood_Outer", "ALTIMA2000_BODY_Fender_Front_R"),
             ("ALTIMA2000_BODY_TrunkLid_Outer", "ALTIMA2000_BODY_Quarter_Rear_R"),
             ("ALTIMA2000_BODY_Fender_Front_R", "ALTIMA2000_BODY_Side_Body_R"),
             ("ALTIMA2000_BODY_Hood_Outer", "ALTIMA2000_BODY_Hood_Inner"),
             ("ALTIMA2000_BODY_TrunkLid_Outer", "ALTIMA2000_BODY_TrunkLid_Inner")):
    if a in objs and b in objs:
        print("GAP %-34s -> %-34s %.4f m" % (a.split("BODY_")[1],
                                             b.split("BODY_")[1],
                                             surface_gap(a, b)))
print("GEO_PROBE_DONE")
