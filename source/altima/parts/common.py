"""Shared helpers for every part module: grid mirroring, prisms, fasteners."""

import math
from mathutils import Vector
from .. import meshutils as mu
from .. import spec

TAU = math.pi * 2.0

# ---------------------------------------------------------------------------
# ring indices (0 = underbody centre, 8 = RIGHT belt line, 22 = top centre,
#               36 = LEFT belt line, 44 = underbody centre)
# ---------------------------------------------------------------------------
RI_UNDER = 0.0
RI_ROCK = 1.9
RI_SIDE = 5.2
RI_BELT = 8.0
RI_DRIP = 10.9
RI_ROOF = 12.6
RI_CENTRE = 22.0

# ---------------------------------------------------------------------------
# longitudinal landmarks, design space (use spec.wmap() for world)
# ---------------------------------------------------------------------------
XR = dict(
    nose=2.330, hood_f=1.900, hood_r=0.800, cowl=0.660, ws_base=0.625,
    ws_top=0.060, roof_r=-0.860, bl_base=-1.520, trunk_f=-1.560,
    trunk_r=-2.060, tail=-2.330, bump_f=1.900, bump_r=-2.000,
    dr_f_front=0.600, dr_f_rear=-0.240, dr_r_front=-0.290, dr_r_rear=-0.875,
    fender_f=1.990, fender_r=1.115, arch_f=1.380, arch_r=-1.240,
    dash=0.540, seat_f=-0.150, engine=1.020, trans=0.130,
)

# ---------------------------------------------------------------------------
# grid helpers
# ---------------------------------------------------------------------------


def side_grid(surf, x0, x1, ri0, ri1, nx, nr, side, world=True):
    """Surface grid for one side.  ``ri`` values are always given for the
    RIGHT side; 'L' mirrors across the car centreline."""
    pts = surf.surface_grid(x0, x1, ri0, ri1, nx=nx, nr=nr, world=world)
    if side == "L":
        pts = [[(p[0], -p[1], p[2]) for p in row] for row in pts]
    return pts


def side_point(surf, x, ri, side, world=True):
    p = surf.point(x, ri, world=world)
    return (p[0], -p[1], p[2]) if side == "L" else p


def loc_side(x, y, z, side):
    return (x, -y if side == "L" else y, z)


SIDE_LABEL = {"R": "R", "L": "L"}
SIDE_COLL = {"R": "R", "L": "L"}


def other(side):
    return "L" if side == "R" else "R"


# ---------------------------------------------------------------------------
# generic prisms / plates in an arbitrary orientation
# ---------------------------------------------------------------------------


def frame(dir_vec, up_hint=(0, 0, 1)):
    """Right-handed orthonormal frame with +Z along ``dir_vec``."""
    d = Vector(dir_vec)
    if d.length < 1e-12:
        d = Vector((0, 0, 1))
    d = d.normalized()
    up = Vector(up_hint)
    if abs(d.dot(up)) > 0.985:
        up = Vector((1, 0, 0))
    x = up.cross(d).normalized()
    y = d.cross(x).normalized()
    return x, y, d


def prism_poly(poly2d, centre, direction, depth, coll, name, reg, mat,
               meta=None, world=True, smooth=False):
    """Extrude a 2-D polygon (in the frame plane) along ``direction``."""
    ex, ey, ez = frame(direction)
    c = Vector(centre)
    n = len(poly2d)
    verts = []
    for sgn in (-depth * 0.5, depth * 0.5):
        for (px, py) in poly2d:
            p = c + ex * px + ey * py + ez * sgn
            verts.append((p.x, p.y, p.z))
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    faces.append(tuple(range(n - 1, -1, -1)))
    faces.append(tuple(range(n, 2 * n)))
    m = dict(meta or {})
    m.setdefault("asmb", True)
    return reg.add(name, verts, faces, coll, mat, meta=m, smooth=smooth,
                   loc=(centre[0], centre[1], centre[2]))


def hex_poly(r):
    return [(r * math.cos(TAU * i / 6 + math.pi / 6),
             r * math.sin(TAU * i / 6 + math.pi / 6)) for i in range(6)]


def circle_poly(r, n=12):
    return [(r * math.cos(TAU * i / n), r * math.sin(TAU * i / n)) for i in range(n)]


def ring_poly(r_out, r_in, n=12):
    """Closed polygon with a hole approximated by an annulus strip outline."""
    pts = []
    for i in range(n):
        a = TAU * i / n
        pts.append((r_out * math.cos(a), r_out * math.sin(a)))
    for i in range(n - 1, -1, -1):
        a = TAU * i / n
        pts.append((r_in * math.cos(a), r_in * math.sin(a)))
    return pts


# ---------------------------------------------------------------------------
# fasteners
# ---------------------------------------------------------------------------
BOLT_SPEC = {
    "M5":  (0.0045, 0.0030),
    "M6":  (0.0055, 0.0040),
    "M8":  (0.0072, 0.0052),
    "M10": (0.0090, 0.0064),
    "M12": (0.0108, 0.0075),
    "M14": (0.0125, 0.0087),
    "M16": (0.0140, 0.0100),
}
NUT_SPEC = {
    "M5":  (0.0050, 0.0040),
    "M6":  (0.0060, 0.0050),
    "M8":  (0.0078, 0.0065),
    "M10": (0.0095, 0.0080),
    "M11": (0.0102, 0.0090),
    "M12": (0.0112, 0.0095),
    "M14": (0.0128, 0.0108),
}


def bolt(reg, mats, pos, direction, size="M6", tag="HexBolt", detail=None,
         length=0.020, seq=None, blk=None, note=""):
    """Hex-head bolt: head + washer face + threaded shank."""
    r, h = BOLT_SPEC[size]
    d = Vector(direction).normalized()
    if seq is None:
        seq = reg.next_seq("FT", tag, detail or size)
    name = reg.make_name("FT", tag, detail or size, seq)
    ex, ey, ez = frame(d)
    base = Vector(pos)
    hd = hex_poly(r)
    v = []
    for zz in (0.0, h):
        for (px, py) in hd:
            p = base + ex * px + ey * py + ez * zz
            v.append((p.x, p.y, p.z))
    sh = circle_poly(r * 0.52, 10)
    for zz in (-length, 0.0):
        for (px, py) in sh:
            p = base + ex * px + ey * py + ez * zz
            v.append((p.x, p.y, p.z))
    faces = []
    for i in range(6):
        j = (i + 1) % 6
        faces.append((i, j, 6 + j, 6 + i))
        faces.append((12 + i, 12 + j, 22 + j, 22 + i))
    faces.append(tuple(range(5, -1, -1)))
    faces.append(tuple(range(6, 12)))
    for i in range(10):
        j = (i + 1) % 10
        faces.append((6 + (i % 6 if False else 0) * 0, 0, 0, 0)) if False else None
    # washer face ring (head underside) + shank transition
    for i in range(6):
        j = (i + 1) % 6
        faces.append((i, i, i, i)) if False else None
    # connect head underside hexagon to shank circle via a simple fan
    for i in range(6):
        faces.append((i, (i + 1) % 6, 12 + (i % 10), 12 + (i % 10)))
    faces = [f for f in faces if len(set(f)) >= 3]
    faces.append(tuple(range(22, 32)))
    m = {"group": "FT", "sub": tag, "kind": "fastener", "mat_key": "steel_phos",
         "asmb": True, "notes": note or ("%s fastener" % size)}
    if blk:
        m["assembly_block"] = blk
    return reg.add(name, v, [f for f in faces if len(set(f)) >= 3],
                   "Fasteners_Bolts", mats["steel_phos"], meta=m, loc=pos)


def nut(reg, mats, pos, direction, size="M6", tag="HexNut", detail=None, seq=None,
        blk=None):
    r, h = NUT_SPEC[size]
    if seq is None:
        seq = reg.next_seq("FT", tag, detail or size)
    name = reg.make_name("FT", tag, detail or size, seq)
    m = {"group": "FT", "sub": tag, "kind": "fastener", "mat_key": "steel_phos",
         "asmb": True, "notes": "%s nut" % size}
    if blk:
        m["assembly_block"] = blk
    return prism_poly(hex_poly(r), pos, direction, h, "Fasteners_Nuts", name,
                      reg, mats["steel_phos"], meta=m)


def clip(reg, mats, pos, direction, tag="TrimClip", detail=None, seq=None,
         blk=None, size=1.0, note=""):
    """Push-in trim clip / panel retainer."""
    if seq is None:
        seq = reg.next_seq("FT", tag, detail or "Push")
    name = reg.make_name("FT", tag, detail or "Push", seq)
    r = 0.0060 * size
    poly = []
    for i in range(8):
        a = TAU * i / 8
        rr = r * (1.0 if i % 2 == 0 else 0.72)
        poly.append((rr * math.cos(a), rr * math.sin(a)))
    m = {"group": "FT", "sub": tag, "kind": "fastener", "mat_key": "plastic_blk_m",
         "asmb": True, "notes": note or "trim retainer clip"}
    if blk:
        m["assembly_block"] = blk
    return prism_poly(poly, pos, direction, 0.0075 * size, "Fasteners_Clips", name,
                      reg, mats["plastic_blk_m"], meta=m)


def bolt_circle(reg, mats, centre, direction, radius, count, size="M6",
                tag="HexBolt", detail="Flange", axis_frame=None, blk=None,
                phase=0.0):
    """A ring of bolts (e.g. a wheel hub, a diff cover, a flange)."""
    ex, ey, ez = frame(direction)
    c = Vector(centre)
    out = []
    for i in range(count):
        a = TAU * i / count + phase
        p = c + ex * (radius * math.cos(a)) + ey * (radius * math.sin(a))
        out.append(bolt(reg, mats, (p.x, p.y, p.z), direction, size=size, tag=tag,
                        detail=detail, blk=blk))
    return out
