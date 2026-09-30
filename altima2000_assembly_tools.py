"""Assembly / exploded-view tools for the ALTIMA2000 asset.

Two ways to use them:
  * Text Editor -> open this file -> Run Script, then the "Altima 2000"
    tab appears in the 3D Viewport sidebar (press N).
  * Edit > Preferences > Add-ons > Install from Disk -> pick this file,
    then enable "ALTIMA2000 Assembly Tools".
"""

bl_info = {
    "name": "ALTIMA2000 Assembly Tools",
    "author": "Procedural asset build",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "category": "Object",
    "description": "Disassemble / reassemble / verify the Altima 2000 asset, the full-car exploded assembly sequence, the per-harness visibility panel, the live modal wire trace and the touch-activated glow",
}

import bpy
import json


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
        if m is not None and m.node_tree is not None                 and m.node_tree.nodes.get(TRACE_PROGRESS) is not None:
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
