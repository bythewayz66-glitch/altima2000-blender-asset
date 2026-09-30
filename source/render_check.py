"""Validation renders for the ALTIMA2000 asset (assembled + exploded)."""

import math
import os
import sys

import bpy
from mathutils import Vector

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

OUT = os.environ.get("ALTIMA_RENDER_OUT", "/workspace/deliverables/renders")
BLEND = os.environ.get("ALTIMA_RENDER_BLEND",
                       "/workspace/deliverables/altima2000_assembly.blend")
TAG = os.environ.get("ALTIMA_RENDER_TAG", "assembled")
EXPLODE = float(os.environ.get("ALTIMA_RENDER_EXPLODE", "0.0"))

os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
scene = bpy.context.scene

if EXPLODE > 0.0:
    NS = {"bpy": bpy, "__name__": "altima_explode_run"}
    src = open(os.path.join(os.path.dirname(BLEND),
                            "altima2000_assembly_tools.py")).read()
    exec(src, NS)
    NS["explode_impl"](EXPLODE)

# ---------------------------------------------------------------- ground plane
bpy.ops.mesh.primitive_plane_add(size=40.0, location=(0.0, 0.0, 0.0))
ground = bpy.context.active_object
ground.name = "ALTIMA2000_REF_Ground"
gm = bpy.data.materials.new("RENDER_Ground")
gm.use_nodes = True
bsdf = gm.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.028, 0.029, 0.032, 1.0)
bsdf.inputs["Roughness"].default_value = 0.42
bsdf.inputs["Metallic"].default_value = 0.0
ground.data.materials.append(gm)

# ---------------------------------------------------------------- lighting
world = scene.world or bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.045, 0.055, 0.075, 1.0)
bg.inputs[1].default_value = 1.0


def add_area(name, loc, rot, size, energy, colour=(1.0, 1.0, 1.0)):
    d = bpy.data.lights.new(name, type="AREA")
    d.energy = energy
    d.size = size
    d.color = colour
    o = bpy.data.objects.new(name, d)
    o.location = loc
    o.rotation_euler = rot
    scene.collection.objects.link(o)
    return o


add_area("RENDER_Key", (3.2, -4.6, 3.4), (math.radians(52), 0.0, math.radians(35)),
         6.0, 900.0, (1.0, 0.96, 0.90))
add_area("RENDER_Fill", (-4.4, -2.6, 2.4), (math.radians(66), 0.0, math.radians(-55)),
         7.0, 260.0, (0.72, 0.82, 1.0))
add_area("RENDER_Rim", (-1.6, 5.2, 2.9), (math.radians(70), 0.0, math.radians(190)),
         6.0, 420.0, (0.86, 0.90, 1.0))
add_area("RENDER_Top", (0.0, 0.0, 7.4), (0.0, 0.0, 0.0), 9.0, 260.0)


def add_cam(name, loc, look=(0.0, 0.0, 0.72), lens=72.0, ortho=None):
    c = bpy.data.cameras.new(name)
    c.lens = lens
    if ortho:
        c.type = "ORTHO"
        c.ortho_scale = ortho
    o = bpy.data.objects.new(name, c)
    o.location = loc
    tgt = Vector(look) - Vector(loc)
    o.rotation_euler = tgt.to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(o)
    return o


# ---------------------------------------------------------------------------
# Camera rig.
#
# AXIS CONVENTION: +X = forward (nose), +Y = left, +Z = up, Z = 0 is the ground.
# The car is 4.72 m long, so the nose sits at x = +2.36 and the tail at x = -2.36.
#
# The earlier rig had the labels swapped: the camera called "side_view" was
# actually a NOSE-ON view (it sat on +X), and "front_view" was a SIDE view (it
# sat on -Y).  That is why a vision-model QA pass read the wheels as "rotated
# the wrong way" - it was looking at the tread band head-on and taking it for
# the wheel face.  The rig below is corrected and each label now matches the
# direction the camera actually looks from.
# ---------------------------------------------------------------------------
AXLE_F = 1.380          # front axle x
AXLE_R = -1.240         # rear axle x
TRACK_H = 0.753         # half track (wheel centre |y|)
WHEEL_R = 0.3135        # wheel radius

views = [
    # --- overall views -----------------------------------------------------
    ("hero_3q", add_cam("C_hero", (4.9, -4.9, 2.30), (0.0, 0.0, 0.70), 78.0)),
    # TRUE side view: camera on -Y, looking along +Y at the car's left flank.
    # The wheel faces (discs) point at the camera; the tyres read as thin.
    ("side_view", add_cam("C_side", (0.0, -7.6, 0.72), (0.0, 0.0, 0.72), 100.0)),
    # TRUE front view: camera on +X (ahead of the nose), looking back along -X.
    ("front_view", add_cam("C_front", (7.6, 0.0, 1.05), (0.0, 0.0, 0.70), 95.0)),
    # TRUE rear view: camera on -X (behind the tail), looking forward along +X.
    ("rear_view", add_cam("C_rear", (-7.6, 0.0, 1.05), (0.0, 0.0, 0.70), 95.0)),
    ("top_view", add_cam("C_top", (0.0, -0.02, 8.0), (0.0, 0.0, 0.60), 78.0)),
    ("engine_bay", add_cam("C_eng", (0.55, -1.85, 1.42), (0.52, 0.0, 0.72), 62.0)),
    # --- wiring close-ups: the engine-bay loom and the under-dash loom ------
    ("wiring_engine", add_cam("C_weng", (1.30, -1.30, 1.30), (1.30, 0.10, 0.78), 55.0)),
    ("wiring_dash", add_cam("C_wdash", (0.30, -1.05, 1.05), (0.45, 0.05, 0.78), 55.0)),
    # --- QA close-ups ------------------------------------------------------
    # Wheel orientation, straight on: camera outboard of the front-left wheel,
    # level with the axle, looking inboard.  A correctly oriented wheel shows
    # its circular face (rim + spokes + centre cap) filling the frame.
    ("wheel_closeup", add_cam("C_wheel", (AXLE_F, -3.05, WHEEL_R),
                              (AXLE_F, -TRACK_H, WHEEL_R), 90.0)),
    # Wheel orientation, three-quarter: shows the round face AND the tread band
    # together, so "face points sideways" is unambiguous.
    ("wheel_3q", add_cam("C_wheel3q", (AXLE_F + 1.15, -2.35, 0.95),
                         (AXLE_F, -TRACK_H, WHEEL_R), 85.0)),
    # Hood / fender / door shut lines, three-quarter from above the front-left.
    ("seam_closeup", add_cam("C_seam", (2.55, -1.35, 1.55), (1.45, -0.72, 0.95), 95.0)),
    # Door / quarter / rocker shut lines along the left flank.
    ("seam_side", add_cam("C_seam2", (0.10, -3.30, 1.05), (0.10, -0.80, 0.72), 95.0)),
]

# optionally light the wires up so the glow / trace is visible in the render
trace_on = os.environ.get("ALTIMA_RENDER_TRACE", "")
if trace_on:
    NS = {"bpy": bpy, "__name__": "altima_trace_run"}
    exec(open(os.path.join(os.path.dirname(BLEND),
                           "altima2000_assembly_tools.py")).read(), NS)
    NS["trace_set"](float(trace_on), 9.0, 0.35)
    print("[ALTIMA-RENDER] trace glow set to %s" % trace_on)

scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 28
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 6
scene.cycles.transparent_max_bounces = 6
scene.cycles.transmission_bounces = 6
scene.render.resolution_x = 1000
scene.render.resolution_y = 660
scene.render.film_transparent = False
scene.view_settings.view_transform = "Filmic"
scene.view_settings.look = "Medium High Contrast"

only = os.environ.get("ALTIMA_RENDER_VIEWS", "")
if only:
    keep = set(only.split(","))
    views = [v for v in views if v[0] in keep]

for label, cam in views:
    try:
        scene.camera = cam
        scene.render.filepath = os.path.join(OUT, "%s_%s.png" % (TAG, label))
        bpy.ops.render.render(write_still=True)
    except Exception as exc:  # keep going: one bad view must not lose the batch
        print("[ALTIMA-RENDER] FAILED %s_%s: %r" % (TAG, label, exc))

print("RENDER_DONE", TAG)
