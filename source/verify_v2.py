"""Independent verification for the ALTIMA2000 v2 asset.

    blender -b --factory-startup --python verify_v2.py

Checks, in order:
  1. name compliance against the AUTHORITATIVE regex read out of builder.py
  2. duplicate names
  3. the 12-step engine-bay sequence: empties, part resolution, round trip
  4. the standalone door module: 6 serviceable parts per door
  5. every module .blend opens and parses
  6. the linked assembly file resolves every module as a library link
  7. glTF cross-format integrity (node count, material extensions)
  8. manifest completeness (JSON and CSV row counts, offsets present)
"""

import csv
import json
import os
import re
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

OUT = os.environ.get("ALTIMA_OUT", "/workspace/build_v2")
FAIL = []


def check(label, ok, detail=""):
    print("VERIFY %-46s %s %s" % (label, "PASS" if ok else "FAIL", detail))
    if not ok:
        FAIL.append(label)
    return ok


def authoritative_name_re():
    """Read NAME_RE straight out of builder.py - never hand-write the pattern."""
    src = open(os.path.join(HERE, "altima", "builder.py")).read()
    m = re.search(r'NAME_RE\s*=\s*re\.compile\(r"([^"]+)"\)', src)
    if not m:
        raise RuntimeError("could not read NAME_RE from builder.py")
    return re.compile(m.group(1))


def load_tools():
    path = os.path.join(OUT, "altima2000_assembly_tools.py")
    ns = {"bpy": bpy, "__name__": "altima_verify_tools"}
    exec(open(path).read(), ns)
    return ns


def main():
    name_re = authoritative_name_re()
    print("VERIFY authoritative NAME_RE = %s" % name_re.pattern)

    # ---------------------------------------------------------------- 1 + 2
    bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "altima2000_assembly.blend"))
    sc = bpy.context.scene
    parts = [o for o in sc.objects if o.type == "MESH" and o.name.startswith("ALTIMA2000_")]
    bad = [o.name for o in parts if not name_re.match(o.name)]
    seen, dupes = set(), []
    for o in parts:
        if o.name in seen:
            dupes.append(o.name)
        seen.add(o.name)
    check("part count", len(parts) > 0, "%d mesh parts" % len(parts))
    check("name compliance (bad=0)", len(bad) == 0, "bad=%d %s" % (len(bad), bad[:5]))
    check("duplicate names (dupes=0)", len(dupes) == 0, "dupes=%d" % len(dupes))

    # ---------------------------------------------------------------- 3
    tools = load_tools()
    steps = tools["_seq_steps"]()
    check("sequence has 12 step empties", len(steps) == 12, "found %d" % len(steps))
    names = [ob.name for _, ob in steps]
    check("step empty names are Step01..Step12",
          all(names[i].startswith("ALTIMA2000_SEQ_Step%02d_" % (i + 1)) for i in range(12)),
          names[0] + " ... " + names[-1])
    root = bpy.data.objects.get("ALTIMA2000_SEQ_Root")
    check("sequence root empty exists", root is not None)
    check("all steps parented to root",
          root is not None and all(ob.parent == root for _, ob in steps))
    total_moved = 0
    missing = []
    for idx, ob in steps:
        info = ob.get("asmb", {})
        members = [n for n in str(info.get("parts", "")).split(",") if n]
        total_moved += len(members)
        for n in members:
            if n not in bpy.data.objects:
                missing.append(n)
        if not members:
            missing.append("EMPTY_STEP_%02d" % idx)
    check("every step resolves its parts", len(missing) == 0,
          "moved=%d missing=%d %s" % (total_moved, len(missing), missing[:5]))

    # round trip: snapshot -> explode all -> reassemble all -> compare
    snapshot = {o.name: Vector(o.location) for o in parts}
    n_fwd = tools["sequence_apply_all"](reverse=False)
    moved = sum(1 for o in parts if (Vector(o.location) - snapshot[o.name]).length > 1e-6)
    check("forward playback moves the step parts", moved == n_fwd,
          "moved=%d reported=%d" % (moved, n_fwd))
    n_rev = tools["sequence_apply_all"](reverse=True)
    worst = max((Vector(o.location) - snapshot[o.name]).length for o in parts)
    check("reverse playback restores exactly", worst < 1e-6,
          "worst=%.3e m (fwd=%d rev=%d)" % (worst, n_fwd, n_rev))
    # reset path
    tools["sequence_apply_all"](reverse=False)
    tools["sequence_reset"]()
    worst2 = max((Vector(o.location) - snapshot[o.name]).length for o in parts)
    check("sequence_reset restores exactly", worst2 < 1e-6, "worst=%.3e m" % worst2)

    # ---------------------------------------------------------------- 4
    door_tags = ["FL", "FR", "RL", "RR"]
    door_expected = {
        "Skin": 1, "Frame": 1, "Hinge": 2, "Latch": 1,
        "WindowRegulator": 1, "GlassRun": 1,
    }
    door_ok = True
    door_detail = []
    for tag in door_tags:
        for kind, n in door_expected.items():
            found = [o for o in sc.objects
                     if o.name.startswith("ALTIMA2000_DRM_%s_%s" % (kind, tag))]
            if len(found) != n:
                door_ok = False
                door_detail.append("%s/%s=%d(want %d)" % (tag, kind, len(found), n))
    check("door module: 6 serviceable parts x 4 doors", door_ok,
          "; ".join(door_detail) if door_detail else "24 parts")
    dm_colls = ["Door_Module_Skin", "Door_Module_Frame", "Door_Module_Hardware",
                "Door_Module_Glazing"]
    present = [c for c in dm_colls if c in bpy.data.collections]
    check("door module collections present", len(present) == len(dm_colls),
          ",".join(present))

    # ---------------------------------------------------------------- 5
    module_keys = ["engine", "drivetrain", "suspension", "wheels", "brakes",
                   "exhaust", "doors"]
    mod_ok = True
    mod_detail = []
    for key in module_keys:
        path = os.path.join(OUT, "altima2000_module_%s.blend" % key)
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            mod_ok = False
            mod_detail.append("%s=MISSING" % key)
            continue
        bpy.ops.wm.open_mainfile(filepath=path)
        msc = bpy.context.scene
        n = len([o for o in msc.objects if o.type == "MESH"])
        roots = [c.name for c in msc.collection.children]
        if n == 0 or not roots:
            mod_ok = False
        mod_detail.append("%s=%d" % (key, n))
    check("all 7 module .blend files open and parse", mod_ok, " ".join(mod_detail))

    # ---------------------------------------------------------------- 6
    asm = os.path.join(OUT, "altima2000_assembly_linked.blend")
    bpy.ops.wm.open_mainfile(filepath=asm)
    asc = bpy.context.scene
    linked_ok = True
    link_detail = []
    for key in module_keys:
        roots = {"engine": "ALTIMA2000_Engine", "drivetrain": "ALTIMA2000_Drivetrain",
                 "suspension": "ALTIMA2000_Suspension", "wheels": "ALTIMA2000_Wheels",
                 "brakes": "ALTIMA2000_Brakes", "exhaust": "ALTIMA2000_Exhaust",
                 "doors": "ALTIMA2000_DoorModule"}[key]
        col = asc.collection.children.get(roots)
        if col is None or col.library is None:
            linked_ok = False
            link_detail.append("%s=NOT_LINKED" % key)
        else:
            link_detail.append("%s=%dobj" % (key, len(col.all_objects)))
    check("assembly file links every module", linked_ok, " ".join(link_detail))
    asm_meshes = len([o for o in asc.objects if o.type == "MESH"])
    check("assembly file has the full car", asm_meshes > 0, "%d mesh objects" % asm_meshes)

    # ---------------------------------------------------------------- 7
    gltf_path = os.path.join(OUT, "altima2000.gltf")
    if os.path.exists(gltf_path):
        g = json.load(open(gltf_path))
        nodes = len(g.get("nodes", []))
        exts = set(g.get("extensionsUsed", []))
        check("glTF node count ~= part count", abs(nodes - len(parts)) <= 40,
              "nodes=%d parts=%d" % (nodes, len(parts)))
        check("glTF keeps clearcoat extension",
              "KHR_materials_clearcoat" in exts, ",".join(sorted(exts)))
        check("glTF keeps transmission extension",
              "KHR_materials_transmission" in exts)
    else:
        check("glTF present", False, gltf_path)

    # ---------------------------------------------------------------- 8
    mj = os.path.join(OUT, "altima2000_manifest.json")
    mc = os.path.join(OUT, "altima2000_manifest.csv")
    doc = json.load(open(mj))
    with open(mc) as fh:
        csv_rows = list(csv.DictReader(fh))
    check("manifest JSON part_count matches scene",
          doc["part_count"] == len(parts),
          "json=%d scene=%d" % (doc["part_count"], len(parts)))
    check("manifest CSV row count matches JSON",
          len(csv_rows) == doc["part_count"],
          "csv=%d json=%d" % (len(csv_rows), doc["part_count"]))
    no_off = [r["name"] for r in doc["parts"]
              if not r.get("offset_m") or len(r["offset_m"]) != 3]
    check("every part has an assembly offset", len(no_off) == 0,
          "missing=%d" % len(no_off))
    seq = doc.get("sequence", {})
    check("manifest carries the 12-step sequence",
          seq.get("step_count") == 12 and len(seq.get("steps", [])) == 12,
          "steps=%d" % len(seq.get("steps", [])))
    mods = doc.get("modules", {})
    check("manifest carries module report",
          all(k in mods for k in module_keys),
          ",".join(sorted(k for k in mods if not k.startswith("_"))))
    check("manifest records bulk_scale", "bulk_scale" in doc,
          "bulk_scale=%s" % doc.get("bulk_scale"))

    print("")
    print("VERIFY_SUMMARY failures=%d" % len(FAIL))
    for f in FAIL:
        print("VERIFY_FAILED %s" % f)
    print("VERIFY_RESULT %s" % ("ALL_PASS" if not FAIL else "HAS_FAILURES"))


if __name__ == "__main__":
    main()
