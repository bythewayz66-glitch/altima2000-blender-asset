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


views = [
    ("hero_3q", add_cam("C_hero", (4.9, -4.9, 2.30), (0.0, 0.0, 0.70), 78.0)),
    ("side_view", add_cam("C_side", (7.6, 0.0, 0.72), (0.0, 0.0, 0.72), 100.0)),
    ("front_view", add_cam("C_front", (0.0, -8.2, 1.05), (0.0, 0.0, 0.70), 95.0)),
    ("rear_view", add_cam("C_rear", (0.0, 8.2, 1.05), (0.0, 0.0, 0.70), 95.0)),
    ("top_view", add_cam("C_top", (0.0, -0.02, 8.0), (0.0, 0.0, 0.60), 78.0)),
    ("engine_bay", add_cam("C_eng", (0.55, -1.85, 1.42), (0.52, 0.0, 0.72), 62.0)),
]

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
