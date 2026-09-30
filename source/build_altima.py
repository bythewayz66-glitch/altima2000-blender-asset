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
from altima.parts import wiring as WR
from altima.parts import hoses as HS

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
    """Create the sequence step empties and parent each step's parts to them.

    Every step owns one empty (``ALTIMA2000_SEQ_StepNN_<Key>``) which is both
    the animation target and the PARENT of that step's parts.  Parenting uses
    an identity parent-inverse, so a part's ``location`` stays its world-space
    assembly position and the disassemble / reassemble operators keep working
    unchanged - while moving the empty moves exactly that step's parts.

    Each empty carries the step index, title, explode vector, distance and the
    explicit list of part names it moves, so the sequence is fully
    self-describing inside the .blend.
    """
    part_names = [r["name"] for r in reg.parts]
    mapping, unclaimed = SQ.resolve(part_names)
    by_name = {r["name"]: r["object"] for r in reg.parts}

    root = reg.add_empty("ALTIMA2000_SEQ_Root", "Sequence", loc=(0.0, 0.0, 0.0),
                         display="CUBE", size=0.45,
                         meta={"kind": "sequence_root", "step_count": SQ.STEP_COUNT,
                               "note": "parent of the %d sequence steps" % SQ.STEP_COUNT})
    bpy.context.view_layer.update()
    root_inv = root.matrix_world.inverted()

    empties = []
    for i, s in enumerate(SQ.STEPS):
        idx = i + 1
        name = SQ.step_empty_name(idx)
        d = SQ.unit(s["direction"])
        loc = s.get("loc", SQ.BAY_CENTRE)
        members = sorted(nm for nm, k in mapping.items() if k == idx)
        ob = reg.add_empty(
            name, "Sequence", loc=loc, display="ARROWS", size=0.30,
            meta={"kind": "sequence_step", "step_index": idx,
                  "step_key": s["key"], "step_title": s["title"],
                  "explode_dir": [round(v, 6) for v in d],
                  "explode_distance": s["distance"],
                  "part_count": len(members),
                  "parts": ",".join(members),
                  "note": s["note"]})
        ob.parent = root
        ob.matrix_parent_inverse = root_inv
        empties.append(ob)

    # parent each step's parts to its empty.  The depsgraph must be current so
    # matrix_world is valid before we invert it.
    bpy.context.view_layer.update()
    for i, ob in enumerate(empties):
        idx = i + 1
        inv = ob.matrix_world.inverted()
        for nm in sorted(nm for nm, k in mapping.items() if k == idx):
            p = by_name.get(nm)
            if p is None:
                continue
            p.parent = ob
            p.matrix_parent_inverse = inv
    bpy.context.view_layer.update()

    log("sequence: %d step empties, %d parts mapped, %d unclaimed"
        % (SQ.STEP_COUNT, len(mapping), len(unclaimed)))
    return mapping, unclaimed, root


def add_teardown_animation(scene, empties):
    """Keyframe the sequence empties: one frame per step, in assembly order.

    Frame 1 is the assembled car.  Step ``i`` starts moving at frame ``i`` and
    is fully exploded at frame ``i+1``, so playing 1 -> N+1 is a forward
    teardown and playing N+1 -> 1 is the reassembly.  Each empty is keyframed
    with the explode direction and distance already stored on it, so the
    animation and the interactive ``altima.sequence_step`` operator can never
    disagree.
    """
    n = len(empties)
    for i, ob in enumerate(empties):
        idx = i + 1
        info = ob.get("asmb", {})
        home = Vector(info.get("loc", (0.0, 0.0, 0.0)))
        d = Vector(info.get("explode_dir", (0.0, 0.0, 1.0)))
        dist = float(info.get("explode_distance", 0.5))
        ob.location = home
        ob.keyframe_insert("location", frame=idx)
        ob.location = home + d * dist
        ob.keyframe_insert("location", frame=idx + 1)
        ob.location = home
    # linear interpolation: a teardown should read as a mechanical slide, not
    # an ease-in/ease-out drift
    for ob in empties:
        ad = ob.animation_data
        if not ad or not ad.action:
            continue
        for fc in ad.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
    scene.frame_start = 1
    scene.frame_end = n + 1
    scene.frame_set(1)
    log("teardown animation: %d steps, frames 1..%d" % (n, n + 1))
    return n + 1


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
    WR.build_wiring(reg, mats, surf, M)
    log("wiring done ->", len(reg.parts), M.get("wiring"))
    HS.build_hoses(reg, mats, surf, M)
    log("hoses done ->", len(reg.parts), M.get("hoses"))
    IN.build_bulk(reg, mats, surf, M)
    log("bulk done ->", len(reg.parts))

    reg.sync_manifest()
    add_metadata_objects(scene, reg, mats)
    seq_map, seq_unclaimed, seq_root = add_sequence_objects(scene, reg)
    seq_empties = [o for o in scene.objects
                   if o.type == "EMPTY" and o.get("asmb", {}).get("kind") == "sequence_step"]
    seq_empties.sort(key=lambda o: int(o.get("asmb", {}).get("step_index", 0)))
    add_teardown_animation(scene, seq_empties)
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
        layout.separator()
        layout.label(text="Wire Glow / Trace", icon="OUTLINER_OB_LIGHT")
        layout.operator("altima.trace_wire", icon="TRACKER")
        layout.operator("altima.trace_all", icon="SEQUENCE_COLOR_04")
        layout.operator("altima.trace_clear", icon="X")
        layout.label(text="Select a wire, then Trace Wire:")
        layout.label(text="the glow runs end to end.")
        layout.operator("altima.trace_modal", icon="PLAY")
        layout.label(text="Live Trace: hover a wire to sweep")
        layout.label(text="the glow along it; ESC to stop.")


# ---------------------------------------------------------------------------
# touch-activated glow / progressive trace
# ---------------------------------------------------------------------------

TRACE_PROGRESS = "TraceProgress"
TRACE_WIDTH = "TraceWidth"
TRACE_STRENGTH = "GlowStrength"


def _trace_materials():
    """Every material carrying the trace shader (i.e. every wire material)."""
    out = []
    for mat in bpy.data.materials:
        if not mat.use_nodes or mat.node_tree is None:
            continue
        if mat.node_tree.nodes.get(TRACE_PROGRESS) is not None:
            out.append(mat)
    return out


def _trace_nodes(mat):
    nt = mat.node_tree
    return (nt.nodes.get(TRACE_PROGRESS), nt.nodes.get(TRACE_WIDTH),
            nt.nodes.get(TRACE_STRENGTH))


def trace_set(progress, strength=6.0, width=0.12):
    """Set the glow state on every wire material; returns the material count."""
    n = 0
    for mat in _trace_materials():
        prog, wid, st = _trace_nodes(mat)
        if prog is None:
            continue
        prog.outputs[0].default_value = float(progress)
        if wid is not None:
            wid.outputs[0].default_value = float(width)
        if st is not None:
            st.outputs[0].default_value = float(strength)
        n += 1
    return n


def trace_clear():
    return trace_set(0.0, 0.0)


def trace_wire_impl(ob, strength=6.0, width=0.12, steps=24, delay=0.0):
    """Light one wire progressively from its start to its end.

    The wire mesh carries a baked ``trace_t`` attribute (normalised arc length
    along the run).  Sweeping ``TraceProgress`` from 0 to 1 on the wire's
    material makes the glow travel along the run.  Because the attribute is
    per-vertex, the leading edge is a real gradient along the wire rather than
    a whole-object switch.
    """
    import time
    mats = []
    for slot in ob.material_slots:
        m = slot.material
        if m is not None and m.node_tree is not None \
                and m.node_tree.nodes.get(TRACE_PROGRESS) is not None:
            mats.append(m)
    if not mats:
        return 0
    if delay:
        time.sleep(delay)
    for i in range(steps + 1):
        p = i / float(steps)
        for m in mats:
            prog, wid, st = _trace_nodes(m)
            prog.outputs[0].default_value = p
            if wid is not None:
                wid.outputs[0].default_value = width
            if st is not None:
                st.outputs[0].default_value = strength
        bpy.context.view_layer.update()
        time.sleep(0.012)
    return len(mats)


class ALTIMA_OT_trace_wire(bpy.types.Operator):
    """Touch a wire: it glows and the light travels along its run"""
    bl_idname = "altima.trace_wire"
    bl_label = "Trace Wire (Touch Glow)"
    bl_options = {"REGISTER", "UNDO"}

    strength: bpy.props.FloatProperty(name="Glow Strength", default=6.0, min=0.0, max=50.0)
    width: bpy.props.FloatProperty(name="Trace Width", default=0.12, min=0.01, max=1.0)
    steps: bpy.props.IntProperty(name="Steps", default=24, min=2, max=200)
    delay: bpy.props.FloatProperty(name="Delay (s)", default=0.0, min=0.0, max=5.0)

    def execute(self, context):
        obs = [o for o in context.selected_objects
               if o.type == "MESH" and o.name.startswith("ALTIMA2000_")]
        if not obs:
            self.report({"WARNING"}, "Select one or more ALTIMA2000 wires first")
            return {"CANCELLED"}
        n = 0
        for ob in obs:
            n += trace_wire_impl(ob, self.strength, self.width, self.steps, self.delay)
        if not n:
            self.report({"WARNING"}, "Selection has no traceable wire material")
            return {"CANCELLED"}
        self.report({"INFO"}, "Traced %d wire(s)" % len(obs))
        return {"FINISHED"}


class ALTIMA_OT_trace_all(bpy.types.Operator):
    """Trace every wire in the scene, one after another"""
    bl_idname = "altima.trace_all"
    bl_label = "Trace All Wires"
    bl_options = {"REGISTER", "UNDO"}

    strength: bpy.props.FloatProperty(name="Glow Strength", default=6.0, min=0.0, max=50.0)
    width: bpy.props.FloatProperty(name="Trace Width", default=0.12, min=0.01, max=1.0)
    steps: bpy.props.IntProperty(name="Steps", default=16, min=2, max=200)
    delay: bpy.props.FloatProperty(name="Delay (s)", default=0.0, min=0.0, max=5.0)

    def execute(self, context):
        obs = [o for o in context.scene.objects
               if o.type == "MESH" and o.name.startswith("ALTIMA2000_ELEC_Wire_")]
        obs.sort(key=lambda o: o.name)
        for ob in obs:
            trace_wire_impl(ob, self.strength, self.width, self.steps, self.delay)
        self.report({"INFO"}, "Traced %d wire segments" % len(obs))
        return {"FINISHED"}


class ALTIMA_OT_trace_clear(bpy.types.Operator):
    """Switch every wire glow off"""
    bl_idname = "altima.trace_clear"
    bl_label = "Clear Wire Glow"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        n = trace_clear()
        self.report({"INFO"}, "Cleared glow on %d wire materials" % n)
        return {"FINISHED"}


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
    """Move one step's parts along its explode vector (or back, if reverse).

    The step's parts are PARENTED to the step empty, so moving the empty moves
    the whole step in a single transform - which is exactly what the teardown
    animation keyframes.  The parts' own ``location`` values are left untouched,
    so the disassemble / reassemble operators keep working unchanged.
    """
    steps = dict(_seq_steps())
    if index not in steps:
        return 0
    ob = steps[index]
    info = ob.get("asmb", {})
    d = Vector(info.get("explode_dir", (0.0, 0.0, 1.0)))
    dist = float(info.get("explode_distance", 0.5)) * distance_scale
    home = Vector(info.get("loc", (0.0, 0.0, 0.0)))
    # forward: displace the step empty along its vector.
    # reverse: return the empty to its stored assembly position exactly, so
    # playing the steps backwards reassembles the car.
    ob.location = home if reverse else home + d * dist
    return len(_seq_parts(ob))


def sequence_apply_all(reverse=False, distance_scale=1.0):
    """Apply every step in order (reverse=True plays the sequence backwards)."""
    total = 0
    for idx, _ in _seq_steps():
        total += sequence_apply_step(idx, reverse=reverse, distance_scale=distance_scale)
    return total


def sequence_reset():
    """Return every step empty to its assembly position (its parts follow)."""
    n = 0
    for idx, ob in _seq_steps():
        info = ob.get("asmb", {})
        if "loc" in info:
            ob.location = info["loc"]
            n += 1
    return n


class ALTIMA_OT_sequence_step(bpy.types.Operator):
    """Explode (or restore) one assembly step"""
    bl_idname = "altima.sequence_step"
    bl_label = "Apply Sequence Step"
    bl_options = {"REGISTER", "UNDO"}

    step: bpy.props.IntProperty(name="Step", default=1, min=1, max=64)
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
    bl_label = "Assembly Sequence"
    bl_idname = "ALTIMA_PT_sequence"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Altima 2000"

    def draw(self, context):
        layout = self.layout
        steps = _seq_steps()
        n = len(steps)
        layout.label(text="Teardown in assembly order (%d steps)" % n, icon="SEQUENCE")
        layout.label(text="Steps 01-12 = engine bay", icon="INFO")
        col = layout.column(align=True)
        for idx, ob in steps:
            info = ob.get("asmb", {})
            row = col.row(align=True)
            op = row.operator("altima.sequence_step",
                              text="%02d %s" % (idx, info.get("step_key", "")))
            op.step = idx
            op.reverse = False
            back = row.operator("altima.sequence_step", text="", icon="LOOP_BACK")
            back.step = idx
            back.reverse = True
        layout.separator()
        layout.operator("altima.sequence_all", text="Explode All %d Steps" % n,
                        icon="FULLSCREEN_EXIT")
        rev = layout.operator("altima.sequence_all", text="Reassemble All %d Steps" % n,
                              icon="FULLSCREEN_ENTER")
        rev.reverse = True
        layout.operator("altima.sequence_reset", icon="LOOP_BACK")


# ---------------------------------------------------------------------------
# per-harness visibility panel
# ---------------------------------------------------------------------------

def harness_names():
    """Every harness tag present in the scene, sorted."""
    out = set()
    for ob in bpy.context.scene.objects:
        if ob.type != "MESH":
            continue
        h = ob.get("asmb", {}).get("harness")
        if h:
            out.add(h)
    return sorted(out)


def harness_objects(name):
    """Every object belonging to one harness."""
    return [ob for ob in bpy.context.scene.objects
            if ob.type == "MESH" and ob.get("asmb", {}).get("harness") == name]


def _harness_toggle_update(self, context):
    """Show / hide every object belonging to this harness."""
    for ob in harness_objects(self.name):
        ob.hide_viewport = not self.visible
        ob.hide_render = not self.visible


class ALTIMA_HarnessItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()
    visible: bpy.props.BoolProperty(default=True, update=_harness_toggle_update)


def refresh_harnesses(scene=None):
    """Rebuild the harness list from the scene (idempotent)."""
    scene = scene or bpy.context.scene
    names = harness_names()
    have = [it.name for it in scene.altima_harnesses]
    if have == names:
        return len(names)
    scene.altima_harnesses.clear()
    for n in names:
        it = scene.altima_harnesses.add()
        it.name = n
        it.visible = True
    return len(names)


class ALTIMA_OT_harness_refresh(bpy.types.Operator):
    """Re-scan the scene for harnesses"""
    bl_idname = "altima.harness_refresh"
    bl_label = "Refresh Harness List"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        n = refresh_harnesses(context.scene)
        self.report({"INFO"}, "Found %d harnesses" % n)
        return {"FINISHED"}


class ALTIMA_OT_harness_show_all(bpy.types.Operator):
    """Show every harness"""
    bl_idname = "altima.harness_show_all"
    bl_label = "Show All Harnesses"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        refresh_harnesses(context.scene)
        n = 0
        for it in context.scene.altima_harnesses:
            it.visible = True
            n += 1
        self.report({"INFO"}, "Showing %d harnesses" % n)
        return {"FINISHED"}


class ALTIMA_OT_harness_hide_all(bpy.types.Operator):
    """Hide every harness"""
    bl_idname = "altima.harness_hide_all"
    bl_label = "Hide All Harnesses"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        refresh_harnesses(context.scene)
        n = 0
        for it in context.scene.altima_harnesses:
            it.visible = False
            n += 1
        self.report({"INFO"}, "Hiding %d harnesses" % n)
        return {"FINISHED"}


class ALTIMA_PT_harness(bpy.types.Panel):
    bl_label = "Wiring Harnesses"
    bl_idname = "ALTIMA_PT_harness"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Altima 2000"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        if len(scene.altima_harnesses) == 0:
            refresh_harnesses(scene)
        row = layout.row(align=True)
        row.operator("altima.harness_show_all", icon="HIDE_OFF")
        row.operator("altima.harness_hide_all", icon="HIDE_ON")
        layout.operator("altima.harness_refresh", icon="FILE_REFRESH")
        layout.separator()
        col = layout.column(align=True)
        for it in scene.altima_harnesses:
            col.prop(it, "visible", text=it.name, icon="OUTLINER_OB_CURVE")


# ---------------------------------------------------------------------------
# live modal trace: hover / select a wire -> the glow sweeps along its run
# ---------------------------------------------------------------------------

class ALTIMA_OT_trace_modal(bpy.types.Operator):
    """Live wire trace: hover or select a wire and the glow sweeps along it.

    Runs as a modal operator so the trace animates in the viewport in real
    time.  Hovering a wire (or selecting one) drives its material's
    ``TraceProgress`` node value up, so the glow travels from one end of the
    run to the other; moving off the wire lets it fade back out.  ESC or
    right-click stops the operator.
    """
    bl_idname = "altima.trace_modal"
    bl_label = "Live Wire Trace (Modal)"
    bl_options = {"REGISTER", "UNDO"}

    strength: bpy.props.FloatProperty(name="Glow Strength", default=6.0,
                                      min=0.0, max=50.0)
    width: bpy.props.FloatProperty(name="Trace Width", default=0.12,
                                   min=0.01, max=1.0)
    speed: bpy.props.FloatProperty(name="Sweep Speed", default=1.8,
                                   min=0.05, max=20.0)
    fade: bpy.props.FloatProperty(name="Fade Rate", default=2.6,
                                  min=0.05, max=20.0)
    interval: bpy.props.FloatProperty(name="Interval (s)", default=0.02,
                                      min=0.005, max=0.5)

    def _wire_under_mouse(self, context, event):
        """The wire object under the pointer, or None."""
        try:
            from bpy_extras import view3d_utils
        except Exception:
            return None
        region = context.region
        rv3d = context.region_data
        if region is None or rv3d is None:
            return None
        coord = (event.mouse_region_x, event.mouse_region_y)
        origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
        deps = context.evaluated_depsgraph_get()
        hit, loc, nrm, idx, ob, mat = context.scene.ray_cast(deps, origin, direction)
        if hit and ob is not None and ob.type == "MESH":
            if ob.get("asmb", {}).get("harness") or "Wire" in ob.name:
                return ob
        return None

    def _set_progress(self, ob, p, strength, width):
        for slot in ob.material_slots:
            m = slot.material
            if m is None or m.node_tree is None:
                continue
            prog = m.node_tree.nodes.get(TRACE_PROGRESS)
            if prog is None:
                continue
            prog.outputs[0].default_value = p
            wid = m.node_tree.nodes.get(TRACE_WIDTH)
            if wid is not None:
                wid.outputs[0].default_value = width
            st = m.node_tree.nodes.get(TRACE_STRENGTH)
            if st is not None:
                st.outputs[0].default_value = strength if p > 0.0 else 0.0

    def invoke(self, context, event):
        if context.area is None or context.area.type != "VIEW_3D":
            self.report({"WARNING"}, "Run this from the 3D Viewport")
            return {"CANCELLED"}
        self._timer = context.window_manager.event_timer_add(
            self.interval, window=context.window)
        self._state = {}
        self._target = None
        self._last = time.time()
        context.window_manager.modal_handler_add(self)
        self.report({"INFO"}, "Live trace running - hover a wire, ESC to stop")
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type in {"ESC", "RIGHTMOUSE"}:
            self._finish(context)
            return {"CANCELLED"}
        if event.type == "TIMER":
            now = time.time()
            dt = max(1e-4, now - self._last)
            self._last = now
            ob = self._wire_under_mouse(context, event)
            if ob is None:
                sel = [o for o in context.selected_objects
                       if o.type == "MESH" and o.get("asmb", {}).get("harness")]
                ob = sel[0] if sel else None
            self._target = ob.name if ob is not None else None
            for name in list(self._state):
                if name == self._target:
                    continue
                p = self._state[name] - self.fade * dt
                if p <= 0.0:
                    del self._state[name]
                    p = 0.0
                else:
                    self._state[name] = p
                o = bpy.data.objects.get(name)
                if o is not None:
                    self._set_progress(o, p, self.strength, self.width)
            if self._target is not None:
                p = min(1.0, self._state.get(self._target, 0.0) + self.speed * dt)
                self._state[self._target] = p
                o = bpy.data.objects.get(self._target)
                if o is not None:
                    self._set_progress(o, p, self.strength, self.width)
            context.view_layer.update()
            context.area.tag_redraw()
        return {"PASS_THROUGH"}

    def _finish(self, context):
        try:
            context.window_manager.event_timer_remove(self._timer)
        except Exception:
            pass
        for name in list(self._state):
            o = bpy.data.objects.get(name)
            if o is not None:
                self._set_progress(o, 0.0, 0.0, self.width)
        self._state = {}
        context.view_layer.update()


def register():
    bpy.utils.register_class(ALTIMA_OT_disassemble)
    bpy.utils.register_class(ALTIMA_OT_reassemble)
    bpy.utils.register_class(ALTIMA_OT_verify_assembly)
    bpy.utils.register_class(ALTIMA_OT_sequence_step)
    bpy.utils.register_class(ALTIMA_OT_sequence_all)
    bpy.utils.register_class(ALTIMA_OT_sequence_reset)
    bpy.utils.register_class(ALTIMA_OT_trace_wire)
    bpy.utils.register_class(ALTIMA_OT_trace_all)
    bpy.utils.register_class(ALTIMA_OT_trace_clear)
    bpy.utils.register_class(ALTIMA_PT_panel)
    bpy.utils.register_class(ALTIMA_PT_sequence)
    bpy.utils.register_class(ALTIMA_HarnessItem)
    bpy.utils.register_class(ALTIMA_OT_harness_refresh)
    bpy.utils.register_class(ALTIMA_OT_harness_show_all)
    bpy.utils.register_class(ALTIMA_OT_harness_hide_all)
    bpy.utils.register_class(ALTIMA_PT_harness)
    bpy.utils.register_class(ALTIMA_OT_trace_modal)
    bpy.types.Scene.altima_harnesses = bpy.props.CollectionProperty(
        type=ALTIMA_HarnessItem)


def unregister():
    try:
        del bpy.types.Scene.altima_harnesses
    except Exception:
        pass
    bpy.utils.unregister_class(ALTIMA_OT_trace_modal)
    bpy.utils.unregister_class(ALTIMA_PT_harness)
    bpy.utils.unregister_class(ALTIMA_OT_harness_hide_all)
    bpy.utils.unregister_class(ALTIMA_OT_harness_show_all)
    bpy.utils.unregister_class(ALTIMA_OT_harness_refresh)
    bpy.utils.unregister_class(ALTIMA_HarnessItem)
    bpy.utils.unregister_class(ALTIMA_PT_sequence)
    bpy.utils.unregister_class(ALTIMA_PT_panel)
    bpy.utils.unregister_class(ALTIMA_OT_trace_clear)
    bpy.utils.unregister_class(ALTIMA_OT_trace_all)
    bpy.utils.unregister_class(ALTIMA_OT_trace_wire)
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
              'the full-car exploded assembly sequence, the per-harness visibility '
              'panel, the live modal wire trace and the touch-activated glow",\n'
              '}\n\n'
              'import bpy\n'
              'import json\n')
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
        "wiring": build_wiring_block(),
        "hoses": build_hose_block(),
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


def build_wiring_block():
    """Manifest block describing the real wiring: systems, counts, trace data."""
    systems = {}
    wires = []
    bulk_runs = 0
    for ob in bpy.data.objects:
        if not ob.name.startswith("ALTIMA2000_ELEC_Wire_"):
            continue
        info = ob.get("asmb", {})
        if not info.get("harness"):
            # a legacy bulk wire run from the fastener population, not a
            # routed harness wire - counted separately, not as a harness
            bulk_runs += 1
            continue
        wires.append({
            "name": ob.name,
            "harness": info.get("harness", ""),
            "circuit": info.get("circuit", ""),
            "segment": info.get("segment", 0),
            "segments": info.get("segments", 0),
            "material": ob.data.materials[0].name if ob.data.materials else "",
            "radius_m": ob.get("wire_radius", 0.0),
            "length_m": ob.get("trace_len", 0.0),
            "trace_attr": ob.get("trace_attr", ""),
            "trace_points": [round(float(c), 5) for c in ob.get("trace_pts", [])],
        })
    wires.sort(key=lambda w: w["name"])
    for w in wires:
        s = systems.setdefault(w["harness"], {
            "circuits": set(), "segments": 0, "wires": 0, "length_m": 0.0})
        s["circuits"].add(w["circuit"])
        s["segments"] = max(s["segments"], w["segments"])
        s["wires"] += 1
        s["length_m"] = round(s["length_m"] + w["length_m"], 4)
    out_systems = {}
    for k, v in sorted(systems.items()):
        out_systems[k] = {"circuits": sorted(v["circuits"]),
                          "circuit_count": len(v["circuits"]),
                          "segments_per_circuit": v["segments"],
                          "wire_segments": v["wires"],
                          "total_length_m": v["length_m"]}
    total_len = round(sum(w["length_m"] for w in wires), 3)
    return {
        "description": "Real, physically modelled wiring - every wire is its own "
                       "selectable object with a baked trace coordinate",
        "wire_segment_count": len(wires),
        "legacy_bulk_wire_runs": bulk_runs,
        "harness_count": len(out_systems),
        "total_wire_length_m": total_len,
        "trace": {
            "mesh_attribute": "trace_t",
            "domain": "POINT",
            "meaning": "normalised arc length along the run (0.0 start, 1.0 end)",
            "material_nodes": ["TraceProgress", "TraceWidth", "GlowStrength"],
            "operator": "altima.trace_wire",
            "note": "sweeping TraceProgress 0->1 lights the wire progressively "
                    "from one end to the other",
        },
        "systems": out_systems,
        "wires": wires,
    }


def build_hose_block():
    """Manifest block describing the routed hoses and tie straps."""
    hoses = []
    straps = []
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        info = ob.get("asmb", {})
        if info.get("hose") and ob.name.startswith("ALTIMA2000_") and "_Hose_" in ob.name:
            hoses.append({
                "name": ob.name,
                "hose": info.get("hose", ""),
                "segment": info.get("segment", 0),
                "segments": info.get("segments", 0),
                "material": ob.data.materials[0].name if ob.data.materials else "",
                "radius_m": ob.get("hose_radius", 0.0),
                "length_m": ob.get("trace_len", 0.0),
                "trace_attr": ob.get("trace_attr", ""),
                "trace_points": [round(float(c), 5) for c in ob.get("trace_pts", [])],
            })
        elif "_TieStrap_" in ob.name:
            straps.append({
                "name": ob.name,
                "hose": info.get("hose", ""),
                "material": ob.data.materials[0].name if ob.data.materials else "",
                "length_m": ob.get("trace_len", 0.0),
                "trace_attr": ob.get("trace_attr", ""),
            })
    hoses.sort(key=lambda w: w["name"])
    straps.sort(key=lambda w: w["name"])
    systems = {}
    for w in hoses:
        s = systems.setdefault(w["hose"], {"segments": 0, "hose_segments": 0,
                                             "length_m": 0.0, "straps": 0})
        s["segments"] = max(s["segments"], w["segments"])
        s["hose_segments"] += 1
        s["length_m"] = round(s["length_m"] + w["length_m"], 4)
    for w in straps:
        s = systems.setdefault(w["hose"], {"segments": 0, "hose_segments": 0,
                                            "length_m": 0.0, "straps": 0})
        s["straps"] += 1
    return {
        "description": "Real, physically modelled hoses and tie straps - every hose "
                       "is a swept tube along its actual run, every strap a swept "
                       "band wrapping it",
        "hose_segment_count": len(hoses),
        "tie_strap_count": len(straps),
        "hose_system_count": len(systems),
        "total_hose_length_m": round(sum(w["length_m"] for w in hoses), 3),
        "trace": {
            "mesh_attribute": "trace_t",
            "domain": "POINT",
            "meaning": "normalised arc length along the run (0.0 start, 1.0 end)",
            "material_nodes": ["TraceProgress", "TraceWidth", "GlowStrength"],
            "note": "hoses and straps carry the same trace shader as the wiring",
        },
        "systems": systems,
        "hoses": hoses,
        "tie_straps": straps,
    }


def write_module_manifests(module_report, master_json):
    """Write a standalone manifest (JSON + CSV) for every module .blend.

    Each module manifest uses exactly the same row schema as the master, so a
    module can be validated and round-tripped on its own.  ``master_index``
    records the part's 1-based position in the master manifest, which is how a
    module-level name maps back to the master assembly.
    """
    with open(master_json) as fh:
        mdoc = json.load(fh)
    by_name = {r["name"]: r for r in mdoc["parts"]}
    written = {}
    for key, rep in sorted(module_report.items()):
        rows = []
        for nm in rep["parts"]:
            src = by_name.get(nm)
            if src is None:
                continue
            row = dict(src)
            row["master_index"] = src["part_index"]
            row["module"] = key
            rows.append(row)
        rows.sort(key=lambda r: r["name"])
        for i, r in enumerate(rows):
            r["part_index"] = i + 1
        doc = {
            "asset": mdoc["asset"],
            "module": key,
            "module_file": rep["file"],
            "generator": mdoc["generator"],
            "bulk_scale": mdoc["bulk_scale"],
            "units": mdoc["units"],
            "coordinate_system": mdoc["coordinate_system"],
            "naming_convention": mdoc["naming_convention"],
            "root_collections": rep["root_collections"],
            "collections": rep["collections"],
            "part_count": len(rows),
            "master_manifest": os.path.basename(master_json),
            "master_part_count": mdoc["part_count"],
            "standalone_reassembly": {
                "note": "This module reassembles on its own: every row carries the "
                        "part's assembled world position in offset_m, so the "
                        "disassemble / reassemble operators shipped in "
                        "altima2000_assembly_tools.py work on this file unchanged.",
                "operators": ["altima.disassemble", "altima.reassemble",
                              "altima.verify_assembly"],
                "mapping_to_master": "row['master_index'] is the part's 1-based "
                                     "index in the master manifest; row['name'] is "
                                     "identical in both, and row['collection'] is "
                                     "the same sub-collection name.",
            },
            "parts": rows,
        }
        jp = os.path.join(OUT_DIR, "altima2000_module_%s_manifest.json" % key)
        with open(jp, "w") as fh:
            json.dump(doc, fh, indent=1)
        cp = os.path.join(OUT_DIR, "altima2000_module_%s_manifest.csv" % key)
        with open(cp, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["part_index", "master_index", "name", "collection",
                        "group", "sub", "part", "material", "instance_of",
                        "x", "y", "z", "notes"])
            for r in rows:
                p = r["position"]
                w.writerow([r["part_index"], r["master_index"], r["name"],
                            r["collection"], r["group"], r["sub"], r["part"],
                            r["material"], r["instance_of"],
                            p["x"], p["y"], p["z"], r.get("notes", "")])
        written[key] = {"json": os.path.basename(jp), "csv": os.path.basename(cp),
                        "part_count": len(rows)}
        log("module manifest %-11s -> %d parts" % (key, len(rows)))
    return written


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

    # The teardown animation lives on the sequence step empties, so every
    # export below must carry animations or the keyframed teardown is lost.
    glb = os.path.join(OUT_DIR, "altima2000.glb")
    try:
        bpy.ops.export_scene.gltf(
            filepath=glb, export_format="GLB", use_selection=False,
            export_apply=False, export_yup=True,
            export_materials="EXPORT", export_cameras=False, export_lights=False,
            export_extras=True, export_texcoords=True, export_normals=True,
            export_animations=True, export_animation_mode="ACTIONS",
            export_frame_range=False, export_optimize_animation_size=False)
        log("glTF glb ->", "%.1f MB" % (os.path.getsize(glb) / 1e6))
    except Exception as e:  # pragma: no cover
        log("glTF GLB export FAILED:", e)
        glb = None
    gltf = os.path.join(OUT_DIR, "altima2000.gltf")
    try:
        bpy.ops.export_scene.gltf(filepath=gltf, export_format="GLTF_SEPARATE",
                                  use_selection=False, export_extras=True,
                                  export_animations=True,
                                  export_animation_mode="ACTIONS",
                                  export_frame_range=False,
                                  export_optimize_animation_size=False)
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
            mesh_smooth_type="FACE", path_mode="AUTO", bake_anim=False)
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
    mod_manifests = write_module_manifests(
        module_report, os.path.join(OUT_DIR, "altima2000_manifest.json"))
    # patch the manifest with the post-export verification results
    with open(os.path.join(OUT_DIR, "altima2000_manifest.json")) as fh:
        mdoc = json.load(fh)
    for key, res in verification["modules"].items():
        mdoc["modules"][key].update(res)
    for key, res in mod_manifests.items():
        mdoc["modules"][key]["manifest_json"] = res["json"]
        mdoc["modules"][key]["manifest_csv"] = res["csv"]
        mdoc["modules"][key]["manifest_part_count"] = res["part_count"]
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
    for key in sorted(mod_manifests):
        print("BUILD_MODULE_MANIFEST %-11s %s (%d parts)"
              % (key, mod_manifests[key]["json"], mod_manifests[key]["part_count"]))
    print("BUILD_SEQUENCE steps=%d parts_moved=%d unclaimed=%d"
          % (SQ.STEP_COUNT, len(seq_map), len(seq_unclaimed)))
    wb = doc.get("wiring", {})
    print("BUILD_WIRING harnesses=%d wire_segments=%d total_length_m=%.1f"
          % (wb.get("harness_count", 0), wb.get("wire_segment_count", 0),
             wb.get("total_wire_length_m", 0.0)))
    hb = doc.get("hoses", {})
    print("BUILD_HOSES systems=%d hose_segments=%d tie_straps=%d total_length_m=%.1f"
          % (hb.get("hose_system_count", 0), hb.get("hose_segment_count", 0),
             hb.get("tie_strap_count", 0), hb.get("total_hose_length_m", 0.0)))
    for k in sorted(wb.get("systems", {})):
        s = wb["systems"][k]
        print("BUILD_HARNESS %-14s circuits=%d segments=%d wires=%3d len=%6.2fm"
              % (k, s["circuit_count"], s["segments_per_circuit"],
                 s["wire_segments"], s["total_length_m"]))
    for i, s in enumerate(SQ.STEPS):
        n = len([1 for nm, k in seq_map.items() if k == i + 1])
        print("BUILD_STEP %02d %-34s %-22s parts=%3d"
              % (i + 1, SQ.step_empty_name(i + 1), s["title"], n))
    for k in sorted(counts):
        print("BUILD_COLL %-24s %4d" % (k, counts[k]))
    log("ALL DONE")


if __name__ == "__main__":
    main()
