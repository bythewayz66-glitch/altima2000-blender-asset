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
    "description": "Disassemble / reassemble / verify the Altima 2000 asset, plus the 12-step engine-bay exploded assembly sequence",
}

import bpy


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
    if reverse:
        d = -d
    n = 0
    for part in _seq_parts(steps[index]):
        pinfo = dict(part.get("asmb", {}))
        pinfo.setdefault("loc", [part.location[0], part.location[1], part.location[2]])
        part["asmb"] = pinfo
        part.location = Vector(pinfo["loc"]) + d * dist
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
