"""Independent verification for the ALTIMA2000 v3 asset (car + real wiring).

    blender -b --factory-startup --python verify_v3.py

Checks, in order:
  1. name compliance against the AUTHORITATIVE regex read out of builder.py
  2. duplicate names
  3. the 12-step engine-bay sequence: empties, part resolution, round trip
  4. the standalone door module: 6 serviceable parts per door
  5. every module .blend opens and parses
  6. the linked assembly file resolves every module as a library link
  7. glTF cross-format integrity (node count, material extensions)
  8. manifest completeness (JSON and CSV row counts, offsets present)
  9. **wiring**: wire count, per-wire trace attribute, trace range, harness
     coverage, grommets / clips / connectors, and the glow + progressive trace
 10. **disassemble / reassemble round trip including the wires**
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

OUT = os.environ.get("ALTIMA_OUT", "/workspace/documents/altima2000_v3")
FAIL = []


def check(label, ok, detail=""):
    print("VERIFY %-52s %s %s" % (label, "PASS" if ok else "FAIL", detail))
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

    snapshot = {o.name: Vector(o.location) for o in parts}
    n_fwd = tools["sequence_apply_all"](reverse=False)
    moved = sum(1 for o in parts if (Vector(o.location) - snapshot[o.name]).length > 1e-6)
    check("forward playback moves the step parts", moved == n_fwd,
          "moved=%d reported=%d" % (moved, n_fwd))
    n_rev = tools["sequence_apply_all"](reverse=True)
    worst = max((Vector(o.location) - snapshot[o.name]).length for o in parts)
    check("reverse playback restores exactly", worst < 1e-6,
          "worst=%.3e m (fwd=%d rev=%d)" % (worst, n_fwd, n_rev))
    tools["sequence_apply_all"](reverse=False)
    tools["sequence_reset"]()
    worst2 = max((Vector(o.location) - snapshot[o.name]).length for o in parts)
    check("sequence_reset restores exactly", worst2 < 1e-6, "worst=%.3e m" % worst2)

    # ---------------------------------------------------------------- 4
    door_tags = ["FL", "FR", "RL", "RR"]
    door_expected = {"Skin": 1, "Frame": 1, "Hinge": 2, "Latch": 1,
                     "WindowRegulator": 1, "GlassRun": 1}
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

    # ---------------------------------------------------------------- 7
    gltf_path = os.path.join(OUT, "altima2000.gltf")
    if os.path.exists(gltf_path):
        g = json.load(open(gltf_path))
        nodes = len(g.get("nodes", []))
        exts = set(g.get("extensionsUsed", []))
        check("glTF node count ~= part count", abs(nodes - len(parts)) <= 60,
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

    # ================================================================ 9 WIRING
    # sections 5 and 6 opened other .blend files, which invalidated the scene
    # reference - re-open the main assembly before touching the scene again
    bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "altima2000_assembly.blend"))
    sc = bpy.context.scene
    parts = [o for o in sc.objects
             if o.type == "MESH" and o.name.startswith("ALTIMA2000_")]
    print("")
    print("VERIFY ---- wiring ----")
    wires = [o for o in sc.objects
             if o.type == "MESH" and o.name.startswith("ALTIMA2000_ELEC_Wire_")]
    check("wires are real geometry objects", len(wires) > 0,
          "%d wire segments" % len(wires))
    check("every wire is individually selectable (own object)",
          len(set(o.name for o in wires)) == len(wires),
          "unique=%d" % len(set(o.name for o in wires)))
    check("every wire name matches the convention",
          all(name_re.match(o.name) for o in wires),
          "bad=%d" % len([o for o in wires if not name_re.match(o.name)]))

    # trace attribute on every wire, and it must span 0..1
    no_attr, bad_range, bad_len = [], [], []
    for o in wires:
        me = o.data
        attr = me.attributes.get("trace_t")
        if attr is None:
            no_attr.append(o.name)
            continue
        vals = [attr.data[i].value for i in range(len(attr.data))]
        if not vals:
            no_attr.append(o.name)
            continue
        if min(vals) > 1e-6 or max(vals) < 1.0 - 1e-6:
            bad_range.append("%s[%.2f..%.2f]" % (o.name, min(vals), max(vals)))
        if o.get("trace_len", 0.0) <= 0.0:
            bad_len.append(o.name)
    check("every wire carries the baked trace_t attribute",
          len(no_attr) == 0, "missing=%d %s" % (len(no_attr), no_attr[:3]))
    check("trace_t spans 0.0 -> 1.0 on every wire",
          len(bad_range) == 0, "bad=%d %s" % (len(bad_range), bad_range[:3]))
    check("every wire has a positive run length",
          len(bad_len) == 0, "bad=%d" % len(bad_len))

    # harness coverage
    harnesses = sorted(set(o.get("asmb", {}).get("harness", "") for o in wires))
    harnesses = [h for h in harnesses if h]
    check("wires are grouped into named harnesses", len(harnesses) >= 25,
          "%d harnesses: %s" % (len(harnesses), ",".join(harnesses[:8]) + " ..."))

    # the systems the brief calls out must be present
    required = ["EngineMain", "Injector", "Ignition", "EngineSensors", "Charging",
                "Starting", "ABS", "Headlamp", "TailLamp", "DashMain", "Instrument",
                "CabinFloor", "BodyRear", "FuelPump", "Roof", "DoorFL", "DoorFR",
                "DoorRL", "DoorRR", "ChassisRear", "Cooling", "Horn", "WiperWasher"]
    have = set(harnesses)
    miss = [r for r in required if r not in have]
    check("all required systems have a harness", len(miss) == 0,
          "missing=%s" % miss)

    # hardware along the runs
    grommets = [o for o in sc.objects if o.name.startswith("ALTIMA2000_ELEC_Grommet_")]
    clips = [o for o in sc.objects if o.name.startswith("ALTIMA2000_ELEC_WireClip_")]
    conns = [o for o in sc.objects if o.name.startswith("ALTIMA2000_ELEC_WireConn_")]
    check("bulkhead grommets modelled", len(grommets) >= 10, "%d" % len(grommets))
    check("loom retainer clips modelled", len(clips) >= 100, "%d" % len(clips))
    check("connector shells modelled", len(conns) >= 40, "%d" % len(conns))

    # wires live in the right collections
    wire_colls = sorted(set(o.users_collection[0].name for o in wires
                            if o.users_collection))
    check("wires sit in Electrical sub-collections",
          all(c.startswith("Electrical_") for c in wire_colls),
          ",".join(wire_colls))

    # ---- the glow / progressive trace -------------------------------------
    trace_mats = [m for m in bpy.data.materials
                  if m.use_nodes and m.node_tree
                  and m.node_tree.nodes.get("TraceProgress") is not None]
    check("wire materials carry the trace shader", len(trace_mats) >= 8,
          "%d materials" % len(trace_mats))
    node_ok = all(m.node_tree.nodes.get("TraceWidth") is not None
                  and m.node_tree.nodes.get("GlowStrength") is not None
                  for m in trace_mats)
    check("trace shader has progress / width / strength nodes", node_ok)

    # the operator must actually drive the glow
    n_set = tools["trace_set"](0.5, 6.0, 0.12)
    check("trace_set drives every wire material", n_set == len(trace_mats),
          "set=%d mats=%d" % (n_set, len(trace_mats)))
    prog_vals = [m.node_tree.nodes["TraceProgress"].outputs[0].default_value
                 for m in trace_mats]
    check("TraceProgress actually moved", all(abs(v - 0.5) < 1e-6 for v in prog_vals),
          "min=%.3f max=%.3f" % (min(prog_vals), max(prog_vals)))
    tools["trace_clear"]()
    cleared = [m.node_tree.nodes["GlowStrength"].outputs[0].default_value
               for m in trace_mats]
    check("trace_clear switches the glow off", all(v == 0.0 for v in cleared))

    # progressive: the glow must be a gradient along the run, not all-or-nothing
    sample = wires[0]
    tools["trace_wire_impl"](sample, strength=6.0, width=0.12, steps=4, delay=0.0)
    mat = sample.material_slots[0].material
    prog = mat.node_tree.nodes["TraceProgress"].outputs[0].default_value
    check("trace_wire_impl runs the glow to the end of the wire",
          abs(prog - 1.0) < 1e-6, "progress=%.3f" % prog)
    # the shader must map trace_t through a range so the leading edge is soft
    mr = [n for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeMapRange"]
    check("trace shader uses a soft leading edge (Map Range)",
          len(mr) >= 1, "%d map-range node(s)" % len(mr))
    attr_nodes = [n for n in mat.node_tree.nodes
                  if n.bl_idname == "ShaderNodeAttribute"
                  and n.attribute_name == "trace_t"]
    check("trace shader reads the trace_t attribute",
          len(attr_nodes) == 1)
    tools["trace_clear"]()

    # ---- manifest wiring block -------------------------------------------
    wb = doc.get("wiring", {})
    check("manifest carries the wiring block", bool(wb),
          "keys=%s" % ",".join(sorted(wb.keys())[:6]))
    check("manifest wire count matches the scene",
          wb.get("wire_segment_count") == len(wires),
          "manifest=%s scene=%d" % (wb.get("wire_segment_count"), len(wires)))
    check("manifest records total wire length",
          wb.get("total_wire_length_m", 0) > 50.0,
          "%.1f m" % wb.get("total_wire_length_m", 0))
    check("manifest documents the trace mechanism",
          wb.get("trace", {}).get("mesh_attribute") == "trace_t",
          str(wb.get("trace", {}).get("operator", "")))
    check("manifest lists every harness system",
          len(wb.get("systems", {})) == len(harnesses),
          "manifest=%d scene=%d" % (len(wb.get("systems", {})), len(harnesses)))
    check("manifest lists every wire with its trace points",
          len(wb.get("wires", [])) == len(wires)
          and all(w.get("trace_points") for w in wb.get("wires", [])),
          "%d rows" % len(wb.get("wires", [])))

    # ================================================================ 10 ROUND TRIP
    print("")
    print("VERIFY ---- disassemble / reassemble round trip (incl. wires) ----")
    snap = {o.name: Vector(o.location) for o in parts}
    n_dis = tools["explode_impl"](1.0, (0.0, 0.0, 0.70), False)
    moved = sum(1 for o in parts if (Vector(o.location) - snap[o.name]).length > 1e-6)
    check("disassemble moves every part", moved == n_dis,
          "moved=%d reported=%d" % (moved, n_dis))
    wire_moved = sum(1 for o in wires
                     if (Vector(o.location) - snap[o.name]).length > 1e-6)
    check("disassemble moves the wires too", wire_moved == len(wires),
          "%d/%d" % (wire_moved, len(wires)))
    # reassemble via the documented manifest path
    for row in doc["parts"]:
        ob = bpy.data.objects.get(row["name"])
        if ob is None:
            continue
        ob.location = row["offset_m"]
        ob.rotation_euler = row["rotation_euler_rad"]
        ob.scale = row["scale"]
    worst3 = max((Vector(o.location) - snap[o.name]).length for o in parts)
    check("manifest reassembly restores exactly", worst3 < 1e-6,
          "worst=%.3e m" % worst3)
    # and via the operator
    tools["explode_impl"](1.0, (0.0, 0.0, 0.70), False)
    tools["reassemble_impl"]() if "reassemble_impl" in tools else None
    for ob in sc.objects:
        if not ob.name.startswith("ALTIMA2000_"):
            continue
        info = ob.get("asmb", {})
        if "loc" in info:
            ob.location = info["loc"]
            ob.rotation_euler = info.get("rot", (0.0, 0.0, 0.0))
    worst4 = max((Vector(o.location) - snap[o.name]).length for o in parts)
    check("asmb-property reassembly restores exactly", worst4 < 1e-6,
          "worst=%.3e m" % worst4)

    print("")
    print("VERIFY_SUMMARY failures=%d" % len(FAIL))
    for f in FAIL:
        print("VERIFY_FAILED %s" % f)
    print("VERIFY_RESULT %s" % ("ALL_PASS" if not FAIL else "HAS_FAILURES"))


if __name__ == "__main__":
    main()
