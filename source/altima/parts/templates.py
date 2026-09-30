"""Reusable geometry templates for instanced parts.

Every template is built once as a mesh datablock; ``Builder.instanced`` then
creates one individually named and selectable object per real-world instance.
"""

import math
from mathutils import Vector
from .. import meshutils as mu
from .. import spec
from . import common as C


def _loft_closed(profile, seg, axis="Y"):
    """Revolve a (radius, along-axis) profile into a closed solid."""
    rings = []
    for (rr, aa) in profile:
        ring = []
        for k in range(seg):
            a = mu.TAU * k / seg
            p = (rr * math.cos(a), rr * math.sin(a), aa)
            ring.append(p)
        rings.append(ring)
    v, f = mu.loft(rings, close_start=True, close_end=True)
    if axis == "Y":
        v = [(p[2], p[0], p[1]) for p in v]
    elif axis == "X":
        v = [(p[1], p[2], p[0]) for p in v]
    return v, f


def tire(outer_r, width, inner_r, seg=32, tread_bands=5):
    """Tire carcass: revolved cross-section, origin at the wheel centre."""
    hw = width * 0.5
    prof = [
        (inner_r, -hw),
        (outer_r - 0.045, -hw),
        (outer_r - 0.012, -hw * 0.86),
        (outer_r, -hw * 0.60),
        (outer_r, -hw * 0.20),
        (outer_r, hw * 0.20),
        (outer_r, hw * 0.60),
        (outer_r - 0.012, hw * 0.86),
        (outer_r - 0.045, hw),
        (inner_r, hw),
    ]
    return _loft_closed(prof, seg, axis="Y")


def tread_ring(outer_r, inner_r, width, grooves=4, seg=48):
    """Tread band with circumferential grooves cut by geometry separation."""
    v, f = _loft_closed([
        (inner_r, -width * 0.5), (outer_r, -width * 0.46),
        (outer_r, width * 0.46), (inner_r, width * 0.5)], seg, axis="Y")
    return v, f


def road_wheel(rim_d, width, spokes=5, seg=24, dish=0.055):
    """Alloy rim: barrel, face plate, spokes, hub, centre cap."""
    r = rim_d * 0.5
    hw = width * 0.5
    prof = [
        (r * 0.34, -hw * 0.72),
        (r * 0.98, -hw * 0.55),
        (r, -hw * 0.30),
        (r, hw * 0.55),
        (r * 0.985, hw * 0.66),
        (r * 0.30, hw * 0.58),
    ]
    v, f = _loft_closed(prof, seg, axis="Y")
    return v, f


def wheel_spoke(r_in, r_out, half_th, width, seg=8):
    """One tapered alloy spoke."""
    v = []
    for (rr, ww) in ((r_in, 0.026), (r_out, 0.017)):
        for yy in (-width, width):
            for k in range(seg):
                a = -0.055 + 0.110 * k / (seg - 1)
                v.append((rr * math.cos(a), yy, rr * math.sin(a)))
    f = []
    n = seg
    for k in range(seg - 1):
        f.append((k, k + 1, n + k + 1, n + k))
        f.append((2 * n + k, 3 * n + k, 3 * n + k + 1, 2 * n + k + 1))
    for k in range(seg - 1):
        f.append((k, 2 * n + k, 2 * n + k + 1, k + 1))
        f.append((n + k, n + k + 1, 3 * n + k + 1, 3 * n + k))
    f.append(tuple(range(0, n))[::-1])
    f.append(tuple(range(n, 2 * n)))
    return v, f


def disc(outer_r, thickness, face_r, hat_depth, seg=28):
    """Brake disc: friction ring + hat, origin at the wheel centre."""
    hw = thickness * 0.5
    prof = [
        (face_r, -hw),
        (outer_r, -hw),
        (outer_r, hw),
        (face_r, hw),
        (face_r, hw + hat_depth * 0.75),
        (face_r * 0.62, hw + hat_depth),
        (face_r * 0.34, hw + hat_depth),
        (face_r * 0.34, -hw),
    ]
    return _loft_closed(prof, seg, axis="Y")


def torque_convertor_transaxle_body():
    """Very simple transaxle silhouette (bell + main case + end cover)."""
    prof = [
        (0.150, -0.180), (0.185, -0.150), (0.190, -0.020),
        (0.165, 0.120), (0.105, 0.210), (0.055, 0.235), (0.0, 0.240),
    ]
    return _loft_closed(prof, 18, axis="X")


def box_vf(size, centre=(0, 0, 0)):
    sx, sy, sz = (s * 0.5 for s in size)
    v = [(centre[0] - sx, centre[1] - sy, centre[2] - sz),
         (centre[0] + sx, centre[1] - sy, centre[2] - sz),
         (centre[0] + sx, centre[1] + sy, centre[2] - sz),
         (centre[0] - sx, centre[1] + sy, centre[2] - sz),
         (centre[0] - sx, centre[1] - sy, centre[2] + sz),
         (centre[0] + sx, centre[1] - sy, centre[2] + sz),
         (centre[0] + sx, centre[1] + sy, centre[2] + sz),
         (centre[0] - sx, centre[1] + sy, centre[2] + sz)]
    return v, mu.BOX_FACES


def cyl_vf(r, h, seg=12, axis="Z"):
    return mu.cylinder(r, h, (0, 0, 0), None, "tmp", seg=seg, axis=axis)


def cyl_template(r, h, seg=12, axis="Z"):
    """Cylinder geometry with the origin at the centre."""
    verts = []
    hh = h * 0.5
    for za in (-hh, hh):
        for i in range(seg):
            a = mu.TAU * i / seg
            verts.append((r * math.cos(a), r * math.sin(a), za))
    verts.append((0, 0, -hh))
    verts.append((0, 0, hh))
    cb, ct = 2 * seg, 2 * seg + 1
    faces = []
    for i in range(seg):
        j = (i + 1) % seg
        faces.append((i, j, seg + j, seg + i))
        faces.append((cb, j, i))
        faces.append((ct, seg + i, seg + j))
    if axis == "X":
        verts = [(p[2], p[0], p[1]) for p in verts]
    elif axis == "Y":
        verts = [(p[0], p[2], p[1]) for p in verts]
    return verts, faces


def tube_template(length, r_out, r_in, seg=10, axis="X"):
    """Open-ended tube (pipe section) with the origin at the centre."""
    verts = []
    hl = length * 0.5
    for xa in (-hl, hl):
        for rr in (r_out, r_in):
            for i in range(seg):
                a = mu.TAU * i / seg
                verts.append((xa, rr * math.cos(a), rr * math.sin(a)))
    faces = []
    def vi(ix, ir, i):
        return ix * 2 * seg + ir * seg + i
    for i in range(seg):
        j = (i + 1) % seg
        faces.append((vi(0, 0, i), vi(0, 0, j), vi(1, 0, j), vi(1, 0, i)))
        faces.append((vi(0, 1, j), vi(0, 1, i), vi(1, 1, i), vi(1, 1, j)))
        faces.append((vi(0, 0, i), vi(0, 1, i), vi(0, 1, j), vi(0, 0, j)))
        faces.append((vi(1, 0, j), vi(1, 1, j), vi(1, 1, i), vi(1, 0, i)))
    if axis == "Y":
        verts = [(p[1], p[0], p[2]) for p in verts]
    elif axis == "Z":
        verts = [(p[1], p[2], p[0]) for p in verts]
    return verts, faces


def sphere_template(r, seg=12, rings=7):
    verts, faces = [], []
    for i in range(rings + 1):
        phi = math.pi * i / rings
        for j in range(seg):
            th = mu.TAU * j / seg
            verts.append((r * math.sin(phi) * math.cos(th),
                          r * math.sin(phi) * math.sin(th),
                          r * math.cos(phi)))
    for i in range(rings):
        for j in range(seg):
            j2 = (j + 1) % seg
            faces.append((i * seg + j, i * seg + j2, (i + 1) * seg + j2, (i + 1) * seg + j))
    return verts, faces


def bolt_template(size="M6", length=0.022, seg=6):
    r, h = C.BOLT_SPEC[size]
    verts = []
    for zz in (0.0, h):
        for i in range(seg):
            a = mu.TAU * i / seg + math.pi / seg
            verts.append((r * math.cos(a), r * math.sin(a), zz))
    for zz in (-length, 0.0):
        for i in range(seg):
            a = mu.TAU * i / seg
            verts.append((r * 0.52 * math.cos(a), r * 0.52 * math.sin(a), zz))
    verts.append((0, 0, h))
    verts.append((0, 0, -length))
    top, bot = 4 * seg, 4 * seg + 1
    faces = []
    for i in range(seg):
        j = (i + 1) % seg
        faces.append((i, j, seg + j, seg + i))
        faces.append((2 * seg + i, 2 * seg + j, 3 * seg + j, 3 * seg + i))
        faces.append((top, j, i))
        faces.append((bot, 3 * seg + i, 3 * seg + j))
        faces.append((seg + i, seg + j, 3 * seg + j, 3 * seg + i))
    return verts, faces


def nut_template(size="M6", seg=6):
    r, h = C.NUT_SPEC[size]
    verts = []
    for zz in (-h / 2, h / 2):
        for i in range(seg):
            a = mu.TAU * i / seg + math.pi / seg
            verts.append((r * math.cos(a), r * math.sin(a), zz))
    faces = []
    for i in range(seg):
        j = (i + 1) % seg
        faces.append((i, j, seg + j, seg + i))
    faces.append(tuple(range(seg - 1, -1, -1)))
    faces.append(tuple(range(seg, 2 * seg)))
    return verts, faces


def clip_template(scale=1.0, seg=6):
    r = 0.0065 * scale
    h = 0.008 * scale
    verts = []
    for zz, rr in ((-h / 2, r * 0.62), (h / 2 - h * 0.25, r), (h / 2, r * 0.72)):
        for i in range(seg):
            a = mu.TAU * i / seg
            verts.append((rr * math.cos(a), rr * math.sin(a), zz))
    verts.append((0, 0, -h / 2))
    verts.append((0, 0, h / 2))
    cb, ct = 3 * seg, 3 * seg + 1
    faces = []
    for lev in range(2):
        for i in range(seg):
            j = (i + 1) % seg
            faces.append((lev * seg + i, lev * seg + j, (lev + 1) * seg + j, (lev + 1) * seg + i))
    for i in range(seg):
        j = (i + 1) % seg
        faces.append((cb, j, i))
        faces.append((ct, 2 * seg + i, 2 * seg + j))
    return verts, faces
