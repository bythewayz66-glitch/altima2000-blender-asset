"""Master build script for the ALTIMA2000 disassemblable Blender asset.

    blender -b --factory-startup --python build_altima.py

Outputs (into OUT_DIR):
    altima2000_assembly.blend       master file, parts in assembled position
    altima2000_exploded.blend       exploded / service view
    altima2000.glb                  glTF 2.0 binary (PBR)
    altima2000.gltf                 glTF 2.0 separate (PBR)
    altima2000.fbx                  FBX 7.4 binary (engine handoff)
    altima2000_manifest.json        full part manifest
    altima2000_manifest.csv         full part manifest (spreadsheet)
    altima2000_readme.md            naming / structure / disassembly docs
"""

import csv
import json
import math
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bpy
from mathutils import Vector

from altima import spec, meshutils as mu, materials as mt, builder as B
from altima import sequence as SQ
from altima.parts import common as C
from altima.parts import templates as T
from altima.parts import panels as PN
from altima.parts import mechanical as MC
from altima.parts import interior as IN

OUT_DIR = os.environ.get("ALTIMA_OUT", os.path.join(os.path.dirname(HERE), "deliverables"))
SKIP_EXPORT = os.environ.get("ALTIMA_SKIP_EXPORT") == "1"
T0 = time.time()


def log(*a):
    print("[ALTIMA %6.1fs]" % (time.time() - T0), *a)
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# scene bootstrap
# ---------------------------------------------------------------------------

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.fps = 24
    scene["asset_name"] = "2000 Nissan Altima (L30) - fully disassemblable"
    scene["asset_prefix"] = B.PREFIX
    scene["unit"] = "metre (1.0 = 1 m)"
    return scene


def add_sequence_objects(scene, reg):
    """Create the 12 named engine-bay sequence step empties.

    Each empty is an animation target and an optional parent for its step's
    parts.  It carries the step index, title, explode vector, distance and the
    explicit list of part names it moves, so the sequence is fully
    self-describing inside the .blend.
    """
    part_names = [r["name"] for r in reg.parts]
    mapping, unclaimed = SQ.resolve(part_names)
    coll = reg.colls["Sequence"]
    empties = []
    for i, s in enumerate(SQ.STEPS):
        idx = i + 1
        name = SQ.step_empty_name(idx)
        d = SQ.unit(s["direction"])
        members = sorted(nm for nm, k in mapping.items() if k == idx)
        ob = reg.add_empty(
            name, "Sequence", loc=SQ.BAY_CENTRE, display="ARROWS", size=0.30,
            meta={"kind": "sequence_step", "step_index": idx,
                  "step_key": s["key"], "step_title": s["title"],
                  "explode_dir": [round(v, 6) for v in d],
                  "explode_distance": s["distance"],
                  "part_count": len(members),
                  "parts": ",".join(members),
                  "note": s["note"]})
        empties.append(ob)
    # a parent empty that owns the whole sequence (handy for animating all 12)
    root = reg.add_empty("ALTIMA2000_SEQ_Root", "Sequence", loc=SQ.BAY_CENTRE,
                         display="CUBE", size=0.45,
                         meta={"kind": "sequence_root", "step_count": SQ.STEP_COUNT,
                               "note": "parent of the 12 engine-bay sequence steps"})
    for ob in empties:
        ob.parent = root
    log("sequence: %d step empties, %d parts mapped, %d unclaimed"
        % (SQ.STEP_COUNT, len(mapping), len(unclaimed)))
    return mapping, unclaimed, root


def add_metadata_objects(scene, reg, mats):
    """Reference empties: origin, axles, assembly blocks, explode centre."""
    # vehicle origin / reference
    em = bpy.data.objects.new("ALTIMA2000_REF_Vehicle_Origin", None)
    em.empty_display_type = "PLAIN_AXES"
    em.empty_display_size = 0.6
    em.location = (0.0, 0.0, 0.0)
    reg.colls["Publish"].objects.link(em)
    em["asmb"] = {"part": "Reference", "notes": "vehicle origin: wheelbase mid-point on ground"}

    ex = bpy.data.objects.new("ALTIMA2000_REF_Explode_Centre", None)
    ex.empty_display_type = "SPHERE"
    ex.empty_display_size = 0.2
    ex.location = (0.0, 0.0, 0.70)
    reg.colls["Publish"].objects.link(ex)
    ex["asmb"] = {"part": "Reference", "notes": "centre used by the explode operator"}

    # named assembly blocks (service grouping aids)
    blocks = [
        ("FrontClip", (2.10, 0.0, 0.62), (1.60, 1.10, 1.10)),
        ("EngineBay", (1.02, 0.0, 0.62), (1.05, 1.20, 1.15)),
        ("Cabin", (0.10, 0.0, 0.90), (1.30, 1.60, 1.05)),
        ("RearClip", (-1.95, 0.0, 0.62), (0.90, 1.20, 1.10)),
        ("Underbody", (-0.10, 0.0, 0.24), (3.40, 1.30, 0.30)),
        ("FrontCornerR", (1.38, -0.75, 0.34), (0.90, 0.46, 0.72)),
        ("FrontCornerL", (1.38, 0.75, 0.34), (0.90, 0.46, 0.72)),
        ("RearCornerR", (-1.24, -0.75, 0.34), (0.90, 0.46, 0.72)),
        ("RearCornerL", (-1.24, 0.75, 0.34), (0.90, 0.46, 0.72)),
    ]
    for name, loc, size in blocks:
        o = bpy.data.objects.new("ALTIMA2000_REF_Block_%s" % name, None)
        o.empty_display_type = "CUBE"
        o.location = loc
        o.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
        reg.colls["Publish"].objects.link(o)
        o["asmb"] = {"part": "AssemblyBlock", "notes": "service assembly block %s" % name}
    return em, ex


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

def build():
    scene = reset_scene()
    mats = mt.build_materials()
    log("materials:", len(mats))

    veh = spec.Vehicle(step=0.020)
    surf = mu.BodySurface(veh)
    log("body surface: %d stations x %d ring points" % (len(surf.xs), surf.n))

    reg = B.Registry(mats)
    reg.build_collections(scene)
    log("collections:", len(reg.colls))

    M = {}
    PN.build_structure(reg, mats, surf, M)
    log("structure done ->", len(reg.parts))
    PN.build_panels(reg, mats, surf, M)
    log("panels done ->", len(reg.parts))
    PN.build_doors(reg, mats, surf, M)
    log("doors done ->", len(reg.parts))
    PN.build_glass(reg, mats, surf, M)
    PN.build_lamps(reg, mats, surf, M)
    PN.build_trim(reg, mats, surf, M)
    log("glass/lamps/trim done ->", len(reg.parts))
    MC.build_all(reg, mats, surf, M)
    log("mechanical done ->", len(reg.parts))
    IN.build_interior(reg, mats, surf, M)
    log("interior done ->", len(reg.parts))
    IN.build_electrical(reg, mats, surf, M)
    log("electrical done ->", len(reg.parts))
    IN.build_bulk(reg, mats, surf, M)
    log("bulk done ->", len(reg.parts))

    reg.sync_manifest()
    add_metadata_objects(scene, reg, mats)
    seq_map, seq_unclaimed, seq_root = add_sequence_objects(scene, reg)
    log("total parts:", len(reg.parts))
    return scene, reg, mats, seq_map, seq_unclaimed


# ---------------------------------------------------------------------------
# explode / reassemble operators (shipped inside the .blend)
# ---------------------------------------------------------------------------

OPERATOR_SRC = '''

def explode_impl(factor, centre=(0.0, 0.0, 0.70), only_selected=False):
    """Radially displace every part from ``centre`` (shared by op + renders)."""
    from mathutils import Vector
    c = Vector(centre)
    n = 0
    for ob in bpy.context.scene.objects:
        if not ob.name.startswith("ALTIMA2000_") or ob.type == "EMPTY":
            continue
        if only_selected and not ob.select_get():
            continue
        info = dict(ob.get("asmb", {}))
        info.setdefault("loc", [ob.location[0], ob.location[1], ob.location[2]])
        ob["asmb"] = info
        d = Vector(info["loc"]) - c
        if d.length < 1e-5:
            d = Vector((0.0, 0.0, 0.05))
        ob.location = Vector(info["loc"]) + d.normalized() * factor
        n += 1
    return n


class ALTIMA_OT_disassemble(bpy.types.Operator):
    """Move every ALTIMA2000 part out of the car along its radial direction"""
    bl_idname = "altima.disassemble"
    bl_label = "Disassemble (Explode View)"
    bl_options = {"REGISTER", "UNDO"}

    factor: bpy.props.FloatProperty(name="Distance", default=1.0, min=0.0, max=5.0)
    centre: bpy.props.FloatVectorProperty(name="Centre", default=(0.0, 0.0, 0.70))
    only_selected: bpy.props.BoolProperty(name="Selected Only", default=False)
    keep_assembled: bpy.props.BoolProperty(name="Store Assembled Position", default=True)

    def execute(self, context):
        n = explode_impl(self.factor, self.centre, self.only_selected)
        self.report({"INFO"}, "Disassembled %d parts" % n)
        return {"FINISHED"}


class ALTIMA_OT_reassemble(bpy.types.Operator):
    """Restore every part to the position stored in its asmb manifest data"""
    bl_idname = "altima.reassemble"
    bl_label = "Reassemble (Assembly View)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        n = 0
        for ob in context.scene.objects:
            if not ob.name.startswith("ALTIMA2000_"):
                continue
            info = ob.get("asmb", {})
            if "loc" in info:
                ob.location = info["loc"]
                ob.rotation_euler = info.get("rot", (0.0, 0.0, 0.0))
                n += 1
        self.report({"INFO"}, "Reassembled %d parts" % n)
        return {"FINISHED"}


class ALTIMA_OT_verify_assembly(bpy.types.Operator):
    """Check every part against its manifest position"""
    bl_idname = "altima.verify_assembly"
    bl_label = "Verify Assembly"
    bl_options = {"REGISTER"}

    tolerance: bpy.props.FloatProperty(name="Tolerance (m)", default=0.0005)
    fail_on_error: bpy.props.BoolProperty(name="Fail On Error", default=False)

    def execute(self, context):
        from mathutils import Vector
        bad = 0
        total = 0
        for ob in context.scene.objects:
            if not ob.name.startswith("ALTIMA2000_") or ob.type == "EMPTY":
                continue
            info = ob.get("asmb", {})
            if "loc" not in info:
                continue
            total += 1
            if (Vector(info["loc"]) - Vector(ob.location)).length > self.tolerance:
                bad += 1
                print("[VERIFY] %s misplaced" % ob.name)
        if bad:
            self.report({"WARNING"}, "%d/%d parts are not in assembly position" % (bad, total))
            return {"CANCELLED"}
        self.report({"INFO"}, "All %d parts verified in assembly position" % total)
        return {"FINISHED"}


class ALTIMA_PT_panel(bpy.types.Panel):
    bl_label = "Altima 2000 Assembly"
    bl_idname = "ALTIMA_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Altima 2000"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Assembly / Service", icon="PACKAGE")
        layout.operator("altima.disassemble", icon="FULLSCREEN_EXIT")
        layout.operator("altima.reassemble", icon="FULLSCREEN_ENTER")
        layout.operator("altima.verify_assembly", icon="CHECKMARK")
        layout.separator()
        layout.label(text="Exploded view: run disassemble,")
        layout.label(text="then reassemble to restore.")


# ---------------------------------------------------------------------------
# engine-bay 12-step exploded assembly sequence
# ---------------------------------------------------------------------------

from mathutils import Vector

SEQ_PREFIX = "ALTIMA2000_SEQ_"


def _seq_steps():
    """Every sequence step empty in the scene, ordered by step index."""
    out = []
    for ob in bpy.context.scene.objects:
        if ob.type != "EMPTY" or not ob.name.startswith(SEQ_PREFIX):
            continue
        info = ob.get("asmb", {})
        if info.get("kind") != "sequence_step":
            continue
        out.append((int(info.get("step_index", 0)), ob))
    out.sort(key=lambda t: t[0])
    return out


def _seq_parts(step_ob):
    """The parts a step empty moves, resolved from its stored name list."""
    info = step_ob.get("asmb", {})
    names = [n for n in str(info.get("parts", "")).split(",") if n]
    return [bpy.data.objects[n] for n in names if n in bpy.data.objects]


def sequence_apply_step(index, reverse=False, distance_scale=1.0):
    """Move one step's parts along its explode vector (or back, if reverse)."""
    steps = dict(_seq_steps())
    if index not in steps:
        return 0
    info = steps[index].get("asmb", {})
    d = Vector(info.get("explode_dir", (0.0, 0.0, 1.0)))
    dist = float(info.get("explode_distance", 0.5)) * distance_scale
    n = 0
    for part in _seq_parts(steps[index]):
        pinfo = dict(part.get("asmb", {}))
        pinfo.setdefault("loc", [part.location[0], part.location[1], part.location[2]])
        part["asmb"] = pinfo
        home = Vector(pinfo["loc"])
        # forward: displace along the step vector.
        # reverse: return the part to its stored assembly position exactly, so
        # playing the 12 steps backwards reassembles the engine bay.
        part.location = home if reverse else home + d * dist
        n += 1
    return n


def sequence_apply_all(reverse=False, distance_scale=1.0):
    """Apply every step in order (reverse=True plays the sequence backwards)."""
    total = 0
    for idx, _ in _seq_steps():
        total += sequence_apply_step(idx, reverse=reverse, distance_scale=distance_scale)
    return total


def sequence_reset():
    """Return every sequence part to its stored assembly position."""
    n = 0
    for idx, ob in _seq_steps():
        for part in _seq_parts(ob):
            info = part.get("asmb", {})
            if "loc" in info:
                part.location = info["loc"]
                n += 1
    return n


class ALTIMA_OT_sequence_step(bpy.types.Operator):
    """Explode (or restore) one engine-bay assembly step"""
    bl_idname = "altima.sequence_step"
    bl_label = "Apply Sequence Step"
    bl_options = {"REGISTER", "UNDO"}

    step: bpy.props.IntProperty(name="Step", default=1, min=1, max=12)
    reverse: bpy.props.BoolProperty(name="Reverse (Reassemble)", default=False)
    distance_scale: bpy.props.FloatProperty(name="Distance Scale", default=1.0,
                                            min=0.0, max=5.0)

    def execute(self, context):
        n = sequence_apply_step(self.step, self.reverse, self.distance_scale)
        self.report({"INFO"}, "Step %02d: %s %d parts"
                    % (self.step, "restored" if self.reverse else "exploded", n))
        return {"FINISHED"}


class ALTIMA_OT_sequence_all(bpy.types.Operator):
    """Explode all 12 engine-bay steps in assembly order (reverse to reassemble)"""
    bl_idname = "altima.sequence_all"
    bl_label = "Apply Full Sequence"
    bl_options = {"REGISTER", "UNDO"}

    reverse: bpy.props.BoolProperty(name="Reverse (Reassemble)", default=False)
    distance_scale: bpy.props.FloatProperty(name="Distance Scale", default=1.0,
                                            min=0.0, max=5.0)

    def execute(self, context):
        n = sequence_apply_all(self.reverse, self.distance_scale)
        self.report({"INFO"}, "%s %d parts across 12 steps"
                    % ("Reassembled" if self.reverse else "Exploded", n))
        return {"FINISHED"}


class ALTIMA_OT_sequence_reset(bpy.types.Operator):
    """Return every engine-bay sequence part to its assembly position"""
    bl_idname = "altima.sequence_reset"
    bl_label = "Reset Sequence"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        n = sequence_reset()
        self.report({"INFO"}, "Reset %d parts" % n)
        return {"FINISHED"}


class ALTIMA_PT_sequence(bpy.types.Panel):
    bl_label = "Engine Bay Sequence (12 steps)"
    bl_idname = "ALTIMA_PT_sequence"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Altima 2000"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Teardown in assembly order", icon="SEQUENCE")
        for i in range(1, 13):
            row = layout.row(align=True)
            op = row.operator("altima.sequence_step", text="Step %02d" % i)
            op.step = i
            op.reverse = False
            back = row.operator("altima.sequence_step", text="", icon="LOOP_BACK")
            back.step = i
            back.reverse = True
        layout.separator()
        layout.operator("altima.sequence_all", text="Explode All 12 Steps",
                        icon="FULLSCREEN_EXIT")
        rev = layout.operator("altima.sequence_all", text="Reassemble All 12 Steps",
                              icon="FULLSCREEN_ENTER")
        rev.reverse = True
        layout.operator("altima.sequence_reset", icon="LOOP_BACK")


def register():
    bpy.utils.register_class(ALTIMA_OT_disassemble)
    bpy.utils.register_class(ALTIMA_OT_reassemble)
    bpy.utils.register_class(ALTIMA_OT_verify_assembly)
    bpy.utils.register_class(ALTIMA_OT_sequence_step)
    bpy.utils.register_class(ALTIMA_OT_sequence_all)
    bpy.utils.register_class(ALTIMA_OT_sequence_reset)
    bpy.utils.register_class(ALTIMA_PT_panel)
    bpy.utils.register_class(ALTIMA_PT_sequence)


def unregister():
    bpy.utils.unregister_class(ALTIMA_PT_sequence)
    bpy.utils.unregister_class(ALTIMA_PT_panel)
    bpy.utils.unregister_class(ALTIMA_OT_sequence_reset)
    bpy.utils.unregister_class(ALTIMA_OT_sequence_all)
    bpy.utils.unregister_class(ALTIMA_OT_sequence_step)
    bpy.utils.unregister_class(ALTIMA_OT_verify_assembly)
    bpy.utils.unregister_class(ALTIMA_OT_reassemble)
    bpy.utils.unregister_class(ALTIMA_OT_disassemble)
'''


def install_operators(reg):
    path = os.path.join(OUT_DIR, "altima2000_assembly_tools.py")
    header = ('"""Assembly / exploded-view tools for the ALTIMA2000 asset.\n\n'
              'Two ways to use them:\n'
              '  * Text Editor -> open this file -> Run Script, then the "Altima 2000"\n'
              '    tab appears in the 3D Viewport sidebar (press N).\n'
              '  * Edit > Preferences > Add-ons > Install from Disk -> pick this file,\n'
              '    then enable "ALTIMA2000 Assembly Tools".\n'
              '"""\n\n'
              'bl_info = {\n'
              '    "name": "ALTIMA2000 Assembly Tools",\n'
              '    "author": "Procedural asset build",\n'
              '    "version": (1, 0, 0),\n'
              '    "blender": (4, 0, 0),\n'
              '    "category": "Object",\n'
              '    "description": "Disassemble / reassemble / verify the Altima 2000 asset, '
              'plus the 12-step engine-bay exploded assembly sequence",\n'
              '}\n\n'
              'import bpy\n')
    with open(path, "w") as fh:
        fh.write(header)
        fh.write(OPERATOR_SRC)
    ns = {"bpy": bpy, "__name__": "altima2000_assembly_tools"}
    exec(header + OPERATOR_SRC, ns)
    ns["register"]()
    log("assembly operators registered ->", os.path.basename(path))
    return path


# ---------------------------------------------------------------------------
# manifest + reports
# ---------------------------------------------------------------------------

def write_manifest(reg, path_json, path_csv, scene, mats, seq_map=None,
                   seq_unclaimed=None, module_report=None):
    rows = []
    for i, r in enumerate(reg.parts):
        rows.append({
            "part_index": i + 1,
            "name": r["name"],
            "collection": r["collection"],
            "group": r["group"],
            "sub": r["sub"],
            "part": r.get("part", ""),
            "object_type": "MESH",
            "material": r["material"],
            "material_key": r.get("material_key", ""),
            "instance_of": r.get("template", ""),
            "position": {"x": r["offset"][0], "y": r["offset"][1], "z": r["offset"][2]},
            "offset_m": r["offset"],
            "rotation_euler_rad": r.get("rotation", [0.0, 0.0, 0.0]),
            "scale": r.get("scale", [1.0, 1.0, 1.0]),
            "assembled": True,
            "notes": r.get("notes", ""),
        })
    counts = {}
    for r in rows:
        counts[r["collection"]] = counts.get(r["collection"], 0) + 1
    group_counts = {}
    for r in rows:
        g = r["group"] or "-"
        group_counts[g] = group_counts.get(g, 0) + 1
    tree = {}
    for r in rows:
        top = B.COLLECTION_OF.get(r["collection"], "Other")
        tree.setdefault(top, {}).setdefault(r["collection"], 0)
        tree[top][r["collection"]] += 1
    families = {}
    for r in rows:
        key = r["instance_of"] or r["name"]
        families[key] = families.get(key, 0) + 1
    doc = {
        "asset": "2000 Nissan Altima (L30) - fully disassemblable Blender asset",
        "generator": "source/build_altima.py (bpy procedural build)",
        "bulk_scale": IN.BULK_SCALE,
        "units": "metre",
        "coordinate_system": {
            "convention": "+X = forward (nose), +Y = left side, +Z = up, Z=0 = ground",
            "origin": "mid-point of the wheelbase, projected to the ground plane",
        },
        "vehicle_envelope_m": {
            "length": round(spec.xmap(2.330) - spec.xmap(-2.330), 4),
            "width": spec.WIDTH, "height": spec.HEIGHT,
            "wheelbase": spec.WHEELBASE,
        },
        "naming_convention": "ALTIMA2000_<GROUP>_<Tag>_<Detail>[_<NNN>]",
        "group_codes": {k: v[0] for k, v in sorted(B.GROUP_CODES.items())},
        "group_codes_doc": {
            "BD": "Body panels", "SH": "Body structure", "DR": "Door hardware",
            "GL": "Glazing", "MI": "Mirrors", "MD": "Exterior trim / moldings",
            "SL": "Seals and weatherstrip", "IN": "Interior trim", "ST": "Seats",
            "EL": "Electrical harness", "LM": "Lighting", "EN": "Engine",
            "TR": "Transaxle / driveline", "EX": "Exhaust", "SU": "Suspension",
            "SR": "Steering", "BR": "Brakes", "WH": "Wheels and tyres",
            "FT": "Bolts", "SC": "Screws and studs", "CL": "Clips, retainers, rivets",
            "FL": "Fluids and reservoirs", "EM": "Emission control",
            "SF": "Safety and restraints", "BA": "Battery and power",
        },
        "part_count": len(rows),
        "collection_count": len(counts),
        "collection_counts": counts,
        "group_counts": group_counts,
        "collection_tree": tree,
        "instance_families": families,
        "material_count": len(mats),
        "sequence": build_sequence_block(seq_map, seq_unclaimed),
        "modules": module_report or {},
        "parts": rows,
    }
    with open(path_json, "w") as fh:
        json.dump(doc, fh, indent=1)
    cols = ["part_index", "name", "collection", "group", "sub", "part", "material",
            "material_key", "instance_of", "ox", "oy", "oz", "rx", "ry", "rz",
            "sx", "sy", "sz", "assembled", "notes"]
    with open(path_csv, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in rows:
            w.writerow([r["part_index"], r["name"], r["collection"], r["group"], r["sub"],
                        r["part"], r["material"], r["material_key"], r["instance_of"],
                        r["offset_m"][0], r["offset_m"][1], r["offset_m"][2],
                        r["rotation_euler_rad"][0], r["rotation_euler_rad"][1],
                        r["rotation_euler_rad"][2],
                        r["scale"][0], r["scale"][1], r["scale"][2],
                        "true", r["notes"]])
    return doc, counts


def build_sequence_block(seq_map, seq_unclaimed):
    """Manifest block describing the 12-step engine-bay sequence."""
    if seq_map is None:
        return {}
    steps = []
    for i, s in enumerate(SQ.STEPS):
        idx = i + 1
        members = sorted(nm for nm, k in seq_map.items() if k == idx)
        steps.append({
            "step": idx,
            "empty": SQ.step_empty_name(idx),
            "key": s["key"],
            "title": s["title"],
            "explode_dir": [round(v, 6) for v in SQ.unit(s["direction"])],
            "explode_distance_m": s["distance"],
            "part_count": len(members),
            "parts": members,
            "note": s["note"],
        })
    return {
        "root_empty": "ALTIMA2000_SEQ_Root",
        "step_count": SQ.STEP_COUNT,
        "order": "assembly order (bottom-up); play in reverse to reassemble",
        "bay_centre": list(SQ.BAY_CENTRE),
        "total_parts_moved": len(seq_map),
        "unclaimed_parts": sorted(seq_unclaimed or []),
        "steps": steps,
    }


def check_names(reg):
    bad = [r["name"] for r in reg.parts if not B.NAME_RE.match(r["name"])]
    dupes = {}
    seen = set()
    for r in reg.parts:
        if r["name"] in seen:
            dupes[r["name"]] = dupes.get(r["name"], 1) + 1
        seen.add(r["name"])
    return bad, dupes


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

def export_all(scene, reg):
    os.makedirs(OUT_DIR, exist_ok=True)
    blend = os.path.join(OUT_DIR, "altima2000_assembly.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend, compress=False)
    log("saved", blend, "%.1f MB" % (os.path.getsize(blend) / 1e6))

    if SKIP_EXPORT:
        return blend, None, None, None

    glb = os.path.join(OUT_DIR, "altima2000.glb")
    try:
        bpy.ops.export_scene.gltf(
            filepath=glb, export_format="GLB", use_selection=False,
            export_apply=False, export_yup=True,
            export_materials="EXPORT", export_cameras=False, export_lights=False,
            export_extras=True, export_texcoords=True, export_normals=True)
        log("glTF glb ->", "%.1f MB" % (os.path.getsize(glb) / 1e6))
    except Exception as e:  # pragma: no cover
        log("glTF GLB export FAILED:", e)
        glb = None
    gltf = os.path.join(OUT_DIR, "altima2000.gltf")
    try:
        bpy.ops.export_scene.gltf(filepath=gltf, export_format="GLTF_SEPARATE",
                                  use_selection=False, export_extras=True)
        log("glTF separate -> %.1f MB" % (os.path.getsize(gltf) / 1e6))
    except Exception as e:  # pragma: no cover
        log("glTF separate export FAILED:", e)
        gltf = None
    fbx = os.path.join(OUT_DIR, "altima2000.fbx")
    try:
        bpy.ops.export_scene.fbx(
            filepath=fbx, use_selection=False, global_scale=1.0,
            apply_unit_scale=True, axis_forward="-Z", axis_up="Y",
            object_types={"MESH", "EMPTY"}, use_custom_props=True,
            mesh_smooth_type="FACE", path_mode="AUTO")
        log("FBX ->", "%.1f MB" % (os.path.getsize(fbx) / 1e6))
    except Exception as e:  # pragma: no cover
        log("FBX export FAILED:", e)
        fbx = None
    return blend, glb, gltf, fbx


def export_exploded(scene, reg, mats):
    """Save a second .blend with every part translated outward."""
    c = Vector((0.0, 0.0, 0.70))
    factors = {
        "Interior": 1.35, "Electrical": 1.55, "Fasteners": 0.85, "Glass": 1.15,
        "Doors": 1.30, "Body": 0.95, "Trim": 1.05, "Engine": 1.10,
        "Drivetrain": 1.20, "Suspension": 0.85, "Wheels": 0.70,
        "Brakes": 0.75, "Exhaust": 0.80, "Fluids": 1.00,
    }
    for r in reg.parts:
        ob = r["object"]
        fam = r["collection"].split("_")[0] if r["collection"].startswith("ALTIMA") else r["collection"]
        fam = {"Body_Panels": "Body", "Body_Shell": "Body", "Body_Structure": "Body",
               "Door_FL": "Doors", "Door_FR": "Doors", "Door_RL": "Doors",
               "Door_RR": "Doors", "Door_Hardware": "Doors",
               "Glass_Glazing": "Glass", "Glass_Mirrors": "Glass"}.get(fam, fam)
        f = 0.0
        for k, v in factors.items():
            if k in r["collection"]:
                f = v
                break
        d = Vector(r["offset"]) - c
        if d.length < 1e-5:
            d = Vector((0.0, 0.0, 0.05))
        ob.location = Vector(r["offset"]) + d.normalized() * f
    path = os.path.join(OUT_DIR, "altima2000_exploded.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=False)
    log("exploded blend -> %.1f MB" % (os.path.getsize(path) / 1e6))
    # restore
    for r in reg.parts:
        r["object"].location = r["offset"]
    return path


def _remove_collection_tree(col):
    """Delete a collection, its children and every object they hold."""
    for child in list(col.children):
        _remove_collection_tree(child)
    for ob in list(col.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.collections.remove(col)


def _purge_orphans():
    """Drop mesh / material / collection datablocks nothing references."""
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    for ma in list(bpy.data.materials):
        if ma.users == 0:
            bpy.data.materials.remove(ma)
    for co in list(bpy.data.collections):
        if co.users == 0:
            bpy.data.collections.remove(co)


def _module_categories(roots):
    """Map a module's root collection DISPLAY names to category keys.

    ``ALL_MODULES`` lists roots by their Blender collection name
    (``ALTIMA2000_Engine``); the registry rows carry the short sub-collection
    name (``Engine_LongBlock``).  ``COLLECTION_TREE`` is the bridge between the
    two, so resolve display name -> category key before comparing.
    """
    disp_to_key = {disp: key for key, disp, _subs in B.COLLECTION_TREE}
    return {disp_to_key.get(x, x) for x in roots}


def module_report_from_registry(reg):
    """Predict each module's contents from the registry (pre-export)."""
    report = {}
    for key, roots in sorted(B.ALL_MODULES.items()):
        cats = _module_categories(roots)
        members = [r for r in reg.parts
                   if B.COLLECTION_OF.get(r["collection"], r["collection"]) in cats
                   or r["collection"] in roots]
        colls = sorted({r["collection"] for r in members})
        report[key] = {
            "file": "altima2000_module_%s.blend" % key,
            "root_collections": list(roots),
            "collections": colls,
            "part_count": len(members),
            "parts": [r["name"] for r in members],
        }
    return report


def export_modules(main_blend, module_report):
    """Write one .blend per module by opening the master and pruning it.

    Each module file is a real, self-contained .blend holding only that
    system's collections - so it can be opened, edited and re-exported on its
    own, and linked into the top-level assembly file.
    """
    paths = {}
    for key, roots in sorted(B.ALL_MODULES.items()):
        bpy.ops.wm.open_mainfile(filepath=main_blend)
        sc = bpy.context.scene
        keep = set(roots)
        for col in list(sc.collection.children):
            if col.name not in keep:
                sc.collection.children.unlink(col)
                _remove_collection_tree(col)
        _purge_orphans()
        path = os.path.join(OUT_DIR, "altima2000_module_%s.blend" % key)
        bpy.ops.wm.save_as_mainfile(filepath=path, compress=False)
        paths[key] = path
        n_obj = len([o for o in sc.objects if o.type == "MESH"])
        module_report[key]["object_count"] = n_obj
        module_report[key]["size_mb"] = round(os.path.getsize(path) / 1e6, 2)
        log("module %-11s -> %-34s %4d objects  %.1f MB"
            % (key, os.path.basename(path), n_obj, module_report[key]["size_mb"]))
    return paths


def build_assembly_file(main_blend, module_paths):
    """Top-level file that LINKS every module instead of duplicating it.

    The module collections are removed from the master and re-added as library
    links, so the assembly file holds one copy of each system and any edit to a
    module .blend propagates into the assembly.
    """
    bpy.ops.wm.open_mainfile(filepath=main_blend)
    sc = bpy.context.scene
    for key, roots in sorted(B.ALL_MODULES.items()):
        for col in list(sc.collection.children):
            if col.name in set(roots):
                sc.collection.children.unlink(col)
                _remove_collection_tree(col)
    _purge_orphans()
    linked = {}
    for key, path in sorted(module_paths.items()):
        roots = set(B.ALL_MODULES[key])
        with bpy.data.libraries.load(path, link=True) as (src, dst):
            dst.collections = [c for c in src.collections if c in roots]
        got = [c for c in dst.collections if c is not None]
        for col in got:
            sc.collection.children.link(col)
        linked[key] = [c.name for c in got]
        log("linked module %-11s -> %s" % (key, ", ".join(linked[key]) or "NONE"))
    path = os.path.join(OUT_DIR, "altima2000_assembly_linked.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=False)
    log("linked assembly -> %.1f MB" % (os.path.getsize(path) / 1e6))
    return path, linked


def verify_modules(module_paths, assembly_path, module_report):
    """Reopen every module and the assembly file and check they resolve."""
    results = {}
    for key, path in sorted(module_paths.items()):
        bpy.ops.wm.open_mainfile(filepath=path)
        sc = bpy.context.scene
        meshes = [o for o in sc.objects if o.type == "MESH"]
        roots = [c.name for c in sc.collection.children]
        ok = (len(meshes) > 0 and set(roots) == set(B.ALL_MODULES[key]))
        results[key] = {"opened": True, "objects": len(meshes),
                        "root_collections": roots, "ok": ok}
        log("verify module %-11s objects=%4d roots=%s ok=%s"
            % (key, len(meshes), roots, ok))
    bpy.ops.wm.open_mainfile(filepath=assembly_path)
    sc = bpy.context.scene
    resolved = {}
    for key, roots in sorted(B.ALL_MODULES.items()):
        found = []
        for col in sc.collection.children:
            if col.name in set(roots):
                found.append({"name": col.name,
                              "linked": col.library is not None,
                              "library": col.library.filepath if col.library else "",
                              "objects": len(col.all_objects)})
        resolved[key] = found
    total = len([o for o in sc.objects if o.type == "MESH"])
    all_linked = all(f and all(x["linked"] for x in f) for f in resolved.values())
    log("verify assembly: %d mesh objects, all modules linked=%s" % (total, all_linked))
    return {"modules": results, "assembly": {
        "file": os.path.basename(assembly_path),
        "mesh_objects": total,
        "resolved": resolved,
        "all_modules_linked": all_linked,
    }}


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    scene, reg, mats, seq_map, seq_unclaimed = build()
    # Capture geometry stats NOW: the module/assembly export below re-opens the
    # master .blend, which frees the objects these registry rows point at.
    tris = sum(len(r["object"].data.polygons) for r in reg.parts)
    verts = sum(len(r["object"].data.vertices) for r in reg.parts)
    meshes = len(set(r["object"].data.name for r in reg.parts))
    bad, dupes = check_names(reg)
    log("name check: bad=%d dupes=%d" % (len(bad), len(dupes)))
    if bad:
        log("BAD NAMES:", bad[:10])
    if dupes:
        log("DUPLICATE NAMES:", list(dupes.items())[:10])
    module_report = module_report_from_registry(reg)
    doc, counts = write_manifest(reg, os.path.join(OUT_DIR, "altima2000_manifest.json"),
                                 os.path.join(OUT_DIR, "altima2000_manifest.csv"),
                                 scene, mats, seq_map, seq_unclaimed, module_report)
    log("manifest written:", doc["part_count"], "parts in", len(counts), "collections")
    install_operators(reg)
    blend, glb, gltf, fbx = export_all(scene, reg)
    exploded = export_exploded(scene, reg, mats)
    module_paths = export_modules(blend, module_report)
    asm_path, linked = build_assembly_file(blend, module_paths)
    verification = verify_modules(module_paths, asm_path, module_report)
    # patch the manifest with the post-export verification results
    with open(os.path.join(OUT_DIR, "altima2000_manifest.json")) as fh:
        mdoc = json.load(fh)
    for key, res in verification["modules"].items():
        mdoc["modules"][key].update(res)
        mdoc["modules"][key]["object_count"] = module_report[key].get("object_count", -1)
        mdoc["modules"][key]["size_mb"] = module_report[key].get("size_mb", 0.0)
    mdoc["modules"]["_assembly"] = verification["assembly"]
    with open(os.path.join(OUT_DIR, "altima2000_manifest.json"), "w") as fh:
        json.dump(mdoc, fh, indent=1)
    print("")
    print("BUILD_DONE part_count=%d collections=%d materials=%d bulk_scale=%.2f" %
          (doc["part_count"], len(counts), doc["material_count"], IN.BULK_SCALE))
    print("BUILD_STATS vertices=%d faces=%d mesh_datablocks=%d" % (verts, tris, meshes))
    print("BUILD_FILES blend=%s glb=%s gltf=%s fbx=%s" % (blend, glb, gltf, fbx))
    print("BUILD_EXPLODED %s" % exploded)
    print("BUILD_ASSEMBLY_LINKED %s" % asm_path)
    for key in sorted(module_paths):
        print("BUILD_MODULE %-11s %s" % (key, module_paths[key]))
    print("BUILD_SEQUENCE steps=%d parts_moved=%d unclaimed=%d"
          % (SQ.STEP_COUNT, len(seq_map), len(seq_unclaimed)))
    for i, s in enumerate(SQ.STEPS):
        n = len([1 for nm, k in seq_map.items() if k == i + 1])
        print("BUILD_STEP %02d %-34s %-22s parts=%3d"
              % (i + 1, SQ.step_empty_name(i + 1), s["title"], n))
    for k in sorted(counts):
        print("BUILD_COLL %-24s %4d" % (k, counts[k]))
    log("ALL DONE")


if __name__ == "__main__":
    main()
