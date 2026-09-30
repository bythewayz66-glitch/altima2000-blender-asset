"""Broader overlap probe: roof, hood ribs, wheels vs body, and the full painted set."""
import itertools

import bpy
from mathutils.bvhtree import BVHTree

bpy.ops.wm.open_mainfile(
    filepath="/workspace/documents/altima2000_v6/altima2000_assembly.blend")
sc = bpy.context.scene

GROUPS = {
    "roof": ["ALTIMA2000_BODY_Roof_Outer", "ALTIMA2000_SHEL_RoofBow_001",
             "ALTIMA2000_SHEL_RoofBow_002", "ALTIMA2000_SHEL_RoofBow_003",
             "ALTIMA2000_SHEL_RoofBow_004", "ALTIMA2000_GLZ_Backlight_Tempered",
             "ALTIMA2000_GLZ_Windshield_Laminated"],
    "hood": ["ALTIMA2000_BODY_Hood_Outer", "ALTIMA2000_BODY_Hood_Inner",
             "ALTIMA2000_BODY_HoodRib_Cross_A", "ALTIMA2000_BODY_HoodRib_Cross_B",
             "ALTIMA2000_BODY_Cowl_Panel"],
    "wheels": ["ALTIMA2000_WHL_Tire_Road_FL", "ALTIMA2000_WHL_Tire_Road_FR",
               "ALTIMA2000_WHL_Tire_Road_RL", "ALTIMA2000_WHL_Tire_Road_RR",
               "ALTIMA2000_WHL_Rim_Alloy_FL", "ALTIMA2000_WHL_Rim_Alloy_FR",
               "ALTIMA2000_WHL_Rim_Alloy_RL", "ALTIMA2000_WHL_Rim_Alloy_RR"],
    "body": ["ALTIMA2000_BODY_Fender_Front_L", "ALTIMA2000_BODY_Fender_Front_R",
             "ALTIMA2000_BODY_Side_Body_L", "ALTIMA2000_BODY_Side_Body_R",
             "ALTIMA2000_BODY_Quarter_Rear_L", "ALTIMA2000_BODY_Quarter_Rear_R",
             "ALTIMA2000_BODY_Rocker_Sill_L", "ALTIMA2000_BODY_Rocker_Sill_R",
             "ALTIMA2000_BODY_Valance_Front", "ALTIMA2000_BODY_Valance_Rear",
             "ALTIMA2000_BODY_BumperCover_Front", "ALTIMA2000_BODY_BumperCover_Rear"],
}

objs = {}
for grp, names in GROUPS.items():
    for nm in names:
        ob = sc.objects.get(nm)
        if ob is not None and ob.type == "MESH":
            objs[nm] = ob
print("LOADED", len(objs), "objects")


def tree_of(ob):
    mw = ob.matrix_world
    verts = [mw @ v.co for v in ob.data.vertices]
    polys = [tuple(p.vertices) for p in ob.data.polygons]
    return BVHTree.FromPolygons(verts, polys, all_triangles=False)


trees = {nm: tree_of(ob) for nm, ob in objs.items()}

# within-group overlaps (roof vs roof, hood vs hood, wheel vs wheel)
for grp, names in GROUPS.items():
    present = [n for n in names if n in trees]
    hits = []
    for a, b in itertools.combinations(sorted(present), 2):
        ov = trees[a].overlap(trees[b])
        if ov:
            hits.append((a, b, len(ov)))
    print("GROUP %-8s pairs=%d intersecting=%d" % (grp, len(present) * (len(present) - 1) // 2, len(hits)))
    for a, b, n in sorted(hits, key=lambda h: -h[2])[:8]:
        print("    %-40s %-40s faces=%d" % (a.split("ALTIMA2000_")[1],
                                            b.split("ALTIMA2000_")[1], n))

# wheels vs body
print("--- wheels vs body ---")
wh = [n for n in GROUPS["wheels"] if n in trees]
bd = [n for n in GROUPS["body"] if n in trees]
n_hit = 0
for a in sorted(wh):
    for b in sorted(bd):
        ov = trees[a].overlap(trees[b])
        if ov:
            n_hit += 1
            print("    %-34s %-34s faces=%d" % (a.split("ALTIMA2000_")[1],
                                                b.split("ALTIMA2000_")[1], len(ov)))
print("WHEEL_BODY_INTERSECTIONS", n_hit)
print("PROBE3_DONE")
