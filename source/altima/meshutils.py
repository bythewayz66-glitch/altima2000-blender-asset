"""Procedural mesh construction helpers (pure Python -> bpy.data).

Object creation goes through ``bpy.data.meshes.new`` / ``objects.new`` so no
operator or view-layer context is required: the whole model builds with the
scene in any state.
"""

import math
import bpy
from mathutils import Vector, Matrix
from . import spec

TAU = math.pi * 2.0

# ---------------------------------------------------------------------------
# object creation / placement
# ---------------------------------------------------------------------------


def make_object(name, verts, faces, coll, mat=None, smooth=False,
                loc=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0), matrix=None,
                validate=True, meta=None):
    """Create a mesh object from raw vert/face data.

    ``loc`` is the assembly position of the part: verts are authored in the
    car's global space and then re-based so the object origin *is* the part
    position.  That makes the manifest offset directly usable for
    reassembly (``obj.location = offset`` puts the part back exactly).
    """
    fd = {"asmb": {"loc": [float(loc[0]), float(loc[1]), float(loc[2])],
                   "rot": [float(rot[0]), float(rot[1]), float(rot[2])],
                   "matrix": [round(float(v), 8) for v in matrix]
                   if matrix is not None else None}}
    if meta:
        fd["asmb"].update({k: (v if isinstance(v, (int, float, str, bool)) else str(v))
                           for k, v in meta.items()})
    me = bpy.data.meshes.new(name)
    lx, ly, lz = loc
    me.from_pydata([(v[0] - lx, v[1] - ly, v[2] - lz) for v in verts], [], faces)
    if validate:
        me.validate(verbose=False)
    me.update()
    ob = bpy.data.objects.new(name, me)
    ob.location = (lx, ly, lz)
    ob.rotation_euler = rot
    if mat is not None:
        me.materials.append(mat)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    me["asmb"] = fd["asmb"]
    coll.objects.link(ob)
    return ob


# ---------------------------------------------------------------------------
# primitives
# ---------------------------------------------------------------------------


def superellipse_point(t, rx, ry, n=2.4, m=1.0, c=0.0):
    ct, st = math.cos(t), math.sin(t)
    x = rx * math.copysign(abs(ct) ** (2.0 / n), ct)
    y = ry * c + ry * math.copysign(abs(st) ** (2.0 / (n * m)), st)
    return x, y


def _side_profile(s, hw_top, hw_max, hw_low, z_belt, z_low_side, z_bot):
    """Body side curve.  s = 0 at the belt line, s = 1 at the bottom centre.

    Three spans, mirroring a real sill profile:
        belt -> widest point,  widest -> rocker bottom,  rocker -> underbody.
    """
    if s < 0.50:
        u = s / 0.50
        y = hw_top + (hw_max - hw_top) * (u ** 0.8)
        z = z_belt + (z_low_side - z_belt) * (1.0 - (1.0 - u) ** 1.8)
    elif s < 0.85:
        u = (s - 0.50) / 0.35
        y = hw_max + (hw_low - hw_max) * (u ** 0.75)
        z = z_low_side + (z_bot - z_low_side) * (u ** 1.4)
    else:
        u = (s - 0.85) / 0.15
        y = hw_low * (1.0 - u)
        z = z_bot - 0.004 * math.sin(math.pi * u)
    return y, z


def section_ring(x, p, n=None, i0=None, i1=None):
    """Closed cross-section ring in the (Y,Z) plane at station ``x``.

    Ring index layout (N = spec.RING_N):
        0            bottom centre
        1 .. i0-1    right side wall (belt -> rocker -> underbody)
        i0 .. i1     upper surface, super-ellipse crown (right shoulder -> left)
        i1+1 .. N-1  left side wall (belt -> rocker -> underbody)
    """
    from . import spec
    n = spec.RING_N if n is None else n
    i0 = spec.TOP_I0 if i0 is None else i0
    i1 = spec.TOP_I1 if i1 is None else i1
    hw_top = p["hw_top"]
    hw_max = p["hw_max"]
    hw_low = p["hw_low"]
    z_belt = p["z_belt"]
    z_low_side = p["z_low_side"]
    z_bot = p["z_bot"]
    e = 2.0 / p["n_top"]
    ea = e * p["a_top"]
    em = e * p["m_top"]

    out = [None] * n
    out[0] = (x, 0.0, z_bot)
    for i in range(1, i0):
        s = (i0 - i) / float(i0)
        y, z = _side_profile(s, hw_top, hw_max, hw_low, z_belt, z_low_side, z_bot)
        out[i] = (x, -y, z)
    for i in range(i0, i1 + 1):
        ang = (i - i0) / float(i1 - i0) * math.pi
        u = math.cos(ang)
        v = math.sin(ang)
        y = -hw_top * math.copysign(abs(u) ** ea, u)
        z = z_belt + (p["z_top"] - z_belt) * (abs(v) ** em)
        out[i] = (x, y, z)
    for i in range(i1 + 1, n):
        s = (i - i1) / float(n - i1)
        y, z = _side_profile(s, hw_top, hw_max, hw_low, z_belt, z_low_side, z_bot)
        out[i] = (x, y, z)
    return out


def grid_normals(pts, flip_toward=(0.0, 0.0, 0.85)):
    """Per-vertex normals for an open point grid, oriented away from the car."""
    nu = len(pts)
    nv = len(pts[0])
    P = [[Vector(p) for p in row] for row in pts]
    N = [[Vector((0.0, 0.0, 0.0)) for _ in range(nv)] for _ in range(nu)]
    for i in range(nu - 1):
        for j in range(nv - 1):
            a, b, c = P[i][j], P[i + 1][j], P[i][j + 1]
            n = (b - a).cross(c - a)
            if n.length > 1e-12:
                n.normalize()
                for (ii, jj) in ((i, j), (i + 1, j), (i, j + 1), (i + 1, j + 1)):
                    N[ii][jj] += n
    if flip_toward is not None:
        axis = Vector(flip_toward)
        for i in range(nu):
            for j in range(nv):
                v = P[i][j] - axis
                if v.length > 1e-6 and N[i][j].dot(v) < 0:
                    N[i][j] = -N[i][j]
    for i in range(nu):
        for j in range(nv):
            if N[i][j].length < 1e-12:
                N[i][j] = Vector((0.0, 0.0, 1.0))
            else:
                N[i][j].normalize()
    return N


def offset_grid(pts, dist, flip_toward=(0.0, 0.0, 0.85)):
    """Move every grid point ``dist`` along its inward surface normal."""
    N = grid_normals(pts, flip_toward)
    out = []
    for i, row in enumerate(pts):
        out.append([(row[j][0] - N[i][j].x * dist,
                     row[j][1] - N[i][j].y * dist,
                     row[j][2] - N[i][j].z * dist) for j in range(len(row))])
    return out


def loft(rings, close_start=False, close_end=False, close_loop=True):
    """Bridge a list of equal-length rings into a surface."""
    n = len(rings[0])
    verts = []
    for r in rings:
        verts.extend(r)
    faces = []
    for i in range(len(rings) - 1):
        a = i * n
        b = (i + 1) * n
        cnt = n if close_loop else n - 1
        for j in range(cnt):
            j2 = (j + 1) % n
            faces.append((a + j, b + j, b + j2, a + j2))
    if close_start:
        faces.append(tuple(range(n - 1, -1, -1)))
    if close_end:
        o = (len(rings) - 1) * n
        faces.append(tuple(range(o, o + n)))
    return verts, faces


def grid_surface(pts, close_u=False, close_v=False):
    """pts[i][j] -> quads.  rows = i (u), cols = j (v)."""
    nu, nv = len(pts), len(pts[0])
    verts = [v for row in pts for v in row]
    faces = []
    iu = nu if close_u else nu - 1
    iv = nv if close_v else nv - 1
    for i in range(iu):
        i2 = (i + 1) % nu
        for j in range(iv):
            j2 = (j + 1) % nv
            faces.append((i * nv + j, i * nv + j2, i2 * nv + j2, i2 * nv + j))
    return verts, faces


def quad_strip(u_pts, v_pts):
    """Two parallel poly-lines swept into a strip (open)."""
    return grid_surface([u_pts, v_pts], close_u=False, close_v=False)


def box(size, loc, coll, name, mat=None, rot=(0, 0, 0)):
    sx, sy, sz = (s * 0.5 for s in size)
    v = [(-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
         (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
         (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    g = [tuple(c + loc[i] for i in range(3)) for c in v]
    return make_object(name, g, f, coll, mat=mat, rot=rot, loc=loc)


def cylinder(radius, depth, loc, coll, name, mat=None, seg=16, axis="Z",
             radius2=None, cap=True):
    r2 = radius if radius2 is None else radius2
    verts, faces = [], []
    h = depth * 0.5
    for k, (za, rr) in enumerate(((-h, radius), (h, r2))):
        for i in range(seg):
            a = TAU * i / seg
            verts.append((rr * math.cos(a), rr * math.sin(a), za))
    if cap:
        verts.append((0, 0, -h))
        verts.append((0, 0, h))
        cb, ct = 2 * seg, 2 * seg + 1
    for i in range(seg):
        j = (i + 1) % seg
        faces.append((i, j, seg + j, seg + i))
        if cap:
            faces.append((cb, j, i))
            faces.append((ct, seg + i, seg + j))
    if axis == "X":
        verts = [(z, x, y) for (x, y, z) in verts]
    elif axis == "Y":
        verts = [(x, z, y) for (x, y, z) in verts]
    g = [(v[0] + loc[0], v[1] + loc[1], v[2] + loc[2]) for v in verts]
    return make_object(name, g, faces, coll, mat=mat, loc=loc)


def tube(path, radius, coll, name, mat=None, seg=10, cap=True):
    """Sweep a circle along a poly-line (constant radius)."""
    pts = [Vector(p) for p in path]
    rings = []
    up = Vector((0, 0, 1))
    for i, p in enumerate(pts):
        if i == 0:
            d = (pts[1] - pts[0])
        elif i == len(pts) - 1:
            d = (pts[-1] - pts[-2])
        else:
            d = (pts[i + 1] - pts[i - 1])
        d.normalize()
        ref = up if abs(d.z) < 0.9 else Vector((1, 0, 0))
        n1 = d.cross(ref).normalized()
        n2 = d.cross(n1).normalized()
        r = []
        for k in range(seg):
            a = TAU * k / seg
            r.append(tuple(p + n1 * (radius * math.cos(a)) + n2 * (radius * math.sin(a))))
        rings.append(r)
    return make_object(name, *loft(rings, close_start=cap), coll, mat=mat)


BOX_FACES = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]


def plate(size, centre, coll, name, mat=None, rot=None, normal=(0, 0, 1)):
    """A thin flat slab oriented along ``normal``.

    Rotations are baked into vertex positions (rotation_euler = 0) so a part
    can always be restored by ``obj.location = offset`` alone.
    """
    sx, sy, sz = size
    v = [(-sx / 2, -sy / 2, -sz / 2), (sx / 2, -sy / 2, -sz / 2),
         (sx / 2, sy / 2, -sz / 2), (-sx / 2, sy / 2, -sz / 2),
         (-sx / 2, -sy / 2, sz / 2), (sx / 2, -sy / 2, sz / 2),
         (sx / 2, sy / 2, sz / 2), (-sx / 2, sy / 2, sz / 2)]
    n = Vector(normal).normalized()
    up = Vector((0, 0, 1))
    if abs(n.dot(up)) > 0.999:
        M = Matrix.Identity(3)
    else:
        x = up.cross(n).normalized()
        y = n.cross(x).normalized()
        M = Matrix((x, y, n)).transposed()
    if rot is not None:
        M = Matrix.Rotation(rot[0], 3, "X") @ Matrix.Rotation(rot[1], 3, "Y") \
            @ Matrix.Rotation(rot[2], 3, "Z") @ M
    g = []
    for p in v:
        w = M @ Vector(p)
        g.append((w.x + centre[0], w.y + centre[1], w.z + centre[2]))
    return make_object(name, g, BOX_FACES, coll, mat=mat, loc=centre)


def prism_from_section(profile, thickness, axis_dir, coll, name, mat=None,
                       offset=(0, 0, 0)):
    """Extrude a closed 2-D poly-line along a direction to make a slab."""
    d = Vector(axis_dir).normalized() * (thickness * 0.5)
    n = len(profile)
    verts = []
    for p in profile:
        verts.append((p[0] - d.x, p[1] - d.y, p[2] - d.z))
    for p in profile:
        verts.append((p[0] + d.x, p[1] + d.y, p[2] + d.z))
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    faces.append(tuple(range(n - 1, -1, -1)))
    faces.append(tuple(range(n, 2 * n)))
    return make_object(name, verts, faces, coll, mat=mat, loc=offset)


def uv_sphere(radius, loc, coll, name, mat=None, seg=14, rings=8, scale=(1, 1, 1)):
    verts, faces = [], []
    for i in range(rings + 1):
        phi = math.pi * i / rings
        for j in range(seg):
            th = TAU * j / seg
            verts.append((radius * math.sin(phi) * math.cos(th) * scale[0],
                          radius * math.sin(phi) * math.sin(th) * scale[1],
                          radius * math.cos(phi) * scale[2]))
    for i in range(rings):
        for j in range(seg):
            j2 = (j + 1) % seg
            a = i * seg + j
            b = i * seg + j2
            c = (i + 1) * seg + j2
            d = (i + 1) * seg + j
            faces.append((a, b, c, d))
    g = [(v[0] + loc[0], v[1] + loc[1], v[2] + loc[2]) for v in verts]
    return make_object(name, g, faces, coll, mat=mat, loc=loc, smooth=True)


def torus(major, minor, loc, coll, name, mat=None, seg_major=20, seg_minor=10,
          axis="Z", scale=(1, 1, 1)):
    verts, faces = [], []
    for i in range(seg_major):
        a = TAU * i / seg_major
        ca, sa = math.cos(a), math.sin(a)
        for j in range(seg_minor):
            b = TAU * j / seg_minor
            r = major + minor * math.cos(b)
            verts.append((r * ca * scale[0], r * sa * scale[1],
                          minor * math.sin(b) * scale[2]))
    for i in range(seg_major):
        i2 = (i + 1) % seg_major
        for j in range(seg_minor):
            j2 = (j + 1) % seg_minor
            faces.append((i * seg_minor + j, i2 * seg_minor + j,
                          i2 * seg_minor + j2, i * seg_minor + j2))
    if axis == "X":
        verts = [(z, x, y) for (x, y, z) in verts]
    elif axis == "Y":
        verts = [(x, z, y) for (x, y, z) in verts]
    g = [(v[0] + loc[0], v[1] + loc[1], v[2] + loc[2]) for v in verts]
    return make_object(name, g, faces, coll, mat=mat, loc=loc, smooth=True)


# ---------------------------------------------------------------------------
# ring interpolation on the body surface
# ---------------------------------------------------------------------------


class BodySurface:
    """Dense ring table making it cheap to ask for 'the surface point at
    (x, ring-index)'.  Pure Python: ~1400 stations x 45 points."""

    def __init__(self, vehicle):
        from . import spec
        self.spec = spec
        self.vehicle = vehicle
        # samples are world-space stations; parameters are looked up in design space
        self.xs = [spec.xmap(x) for x in vehicle.samples]
        self.rings = [section_ring(spec.xmap(x), vehicle.params(x))
                      for x in vehicle.samples]
        self.n = spec.RING_N

    def idx(self, x):
        xs = self.xs
        if x <= xs[0]:
            return 0
        if x >= xs[-1]:
            return len(xs) - 1  # noqa: E501
        lo, hi = 0, len(xs) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if xs[mid] <= x:
                lo = mid
            else:
                hi = mid
        return lo

    def point(self, x, ri, world=True):
        """Interpolated surface point at station x, ring index ri (float).

        ``x`` is world space by default; pass ``world=False`` for design space.
        """
        x = spec.xmap(x) if world else x
        i = self.idx(x)
        j = min(i + 1, len(self.xs) - 1)
        x0, x1 = self.xs[i], self.xs[j]
        t = 0.0 if x1 == x0 else (x - x0) / (x1 - x0)
        n = self.n
        r0, r1 = self.rings[i], self.rings[j]
        i0 = int(math.floor(ri)) % n
        i1 = (i0 + 1) % n
        f = ri - math.floor(ri)
        a = r0[i0]
        b = r0[i1]
        c = r1[i0]
        d = r1[i1]
        return (
            a[0] * (1 - t) + c[0] * t,
            (a[1] * (1 - f) + b[1] * f) * (1 - t) + (c[1] * (1 - f) + d[1] * f) * t,
            (a[2] * (1 - f) + b[2] * f) * (1 - t) + (c[2] * (1 - f) + d[2] * f) * t,
        )

    def surface_grid(self, x0, x1, ri0, ri1, nx=14, nr=8, blend=0.0, mirror=False,
                     world=True):
        """Grid of points: rows along x, columns across ring indices.

        ``ri0``/``ri1`` are unwrapped ring indices (may run past 0 or 44; they
        wrap automatically).  If ``mirror`` is set the ring indices are
        reflected about index 22 (top-centre) first.
        """
        def iwrap(a):
            if mirror:
                a = 22.0 - a
            return a
        pts = []
        for i in range(nx + 1):
            x = x0 + (x1 - x0) * i / nx
            row = []
            for j in range(nr + 1):
                ri = ri0 + (ri1 - ri0) * j / nr
                row.append(self.point(x, iwrap(ri), world=world))
            pts.append(row)
        return pts

    # ------------------------------------------------------------------ queries
    def top_z(self, x, y):
        """Height of the upper surface at station x and lateral position y."""
        x = spec.xmap(x)
        i = self.idx(x)
        r0, r1 = self.rings[i], self.rings[min(i + 1, len(self.xs) - 1)]
        best = None
        for ring in (r0, r1):
            for k in range(self.spec.TOP_I0, self.spec.TOP_I1):
                a, b = ring[k], ring[k + 1]
                ya, yb = a[1], b[1]
                lo, hi = min(ya, yb), max(ya, yb)
                if lo - 1e-9 <= y <= hi + 1e-9 and abs(yb - ya) > 1e-9:
                    t = (y - ya) / (yb - ya)
                    z = a[2] + (b[2] - a[2]) * t
                    if best is None or z > best:
                        best = z
        if best is None:
            return self.vehicle.params(x)["z_belt"]
        return best

    def sec_line(self, x, z):
        """Half-width of the body at station x and height z.

        Returns (right_y, left_y).  Used to place body-side parts (moldings,
        seals, door handles) exactly on the panel surface.
        """
        p = self.vehicle.params(spec.dxmap(x))
        hw_top, z_belt, z_top = p["hw_top"], p["z_belt"], p["z_top"]
        e = 2.0 / p["n_top"]
        em = e * p["m_top"]
        if z <= z_belt:
            # walk the side profile for this station
            zt, zm, zb = p["z_belt"], p["z_low_side"], p["z_bot"]
            hwp, hwm, hwl = hw_top, p["hw_max"], p["hw_low"]
            for span in range(400):
                s = span / 400.0
                y, zz = _side_profile(s, hwp, hwm, hwl, zt, zm, zb)
                if zz <= z:
                    break
            return (-y, y)
        # upper surface: invert  z = z_belt + (z_top-z_belt)*|sin(ang)|**em
        hw = hw_top
        if z_belt + 1e-6 < z < z_top - 1e-6:
            frac = (z - z_belt) / (z_top - z_belt)
            sv = frac ** (1.0 / em)
            cv = max(0.0, 1.0 - sv * sv) ** 0.5
            ea = e * p["a_top"]
            y = hw * (cv ** ea)
            return (-y, y)
        return (-hw, hw)

    def wl(self, x, z):
        """Half-width at station x and height z (symmetric side)."""
        return self.sec_line(x, z)[1]

    def arch_cut(self, cx, Y, z_ground=0.0):
        """Radius of the wheel-arch opening at station x for wheel centre cx."""
        return math.sqrt(max(0.0, self.spec.ARCH_R ** 2 - (x - cx) ** 2))

    def ri_at_z(self, x, z, ri_lo=2, ri_hi=8):
        """Ring index on the body side whose height equals z (x in world space)."""
        i = self.idx(spec.xmap(x))
        ring = self.rings[i]
        for k in range(ri_lo, ri_hi):
            a, b = ring[k], ring[k + 1]
            za, zb = a[2], b[2]
            lo, hi = min(za, zb), max(za, zb)
            if lo - 1e-9 <= z <= hi + 1e-9 and abs(zb - za) > 1e-12:
                return k + (z - za) / (zb - za)
        if z >= ring[ri_hi][2]:
            return float(ri_hi)
        return float(ri_lo)

    def band_grid(self, xs, ri_hi, ri_lo_fn, nr, side="R", world=True):
        """Rectangular grid whose lower edge follows ``ri_lo_fn(x)``.

        Used for panels with a curved lower boundary (wheel arches).
        """
        pts = []
        for x in xs:
            lo = ri_lo_fn(x) if callable(ri_lo_fn) else ri_lo_fn
            row = []
            for j in range(nr + 1):
                ri = lo + (ri_hi - lo) * j / nr
                p = self.point(x, ri, world=world)
                if side == "L":
                    p = (p[0], -p[1], p[2])
                row.append(p)
            pts.append(row)
        return pts

    def side_glass_grid(self, xs, ri_lo_fn, ri_hi_fn, nr, side="R", inset=0.0):
        """Band on the body side spanning two ring-index curves."""
        pts = []
        for x in xs:
            lo = ri_lo_fn(x) if callable(ri_lo_fn) else ri_lo_fn
            hi = ri_hi_fn(x) if callable(ri_hi_fn) else ri_hi_fn
            row = []
            for j in range(nr + 1):
                ri = lo + (hi - lo) * j / nr
                p = self.point(x, ri, world=True)
                y = -abs(p[1])
                if side == "L":
                    y = -y
                row.append((p[0], y, p[2]))
            pts.append(row)
        return pts

    def outline_grid(self, xs, z_lo_fn, z_hi_fn, nr, side="R", inset=0.0):
        """Band defined by two height curves - for flush glass and moldings."""
        pts = []
        for x in xs:
            z0 = z_lo_fn(x) if callable(z_lo_fn) else z_lo_fn
            z1 = z_hi_fn(x) if callable(z_hi_fn) else z_hi_fn
            row = []
            for j in range(nr + 1):
                z = z0 + (z1 - z0) * j / nr
                y = self.wl(x, z) + inset
                row.append((x, -y if side == "R" else y, z))
            pts.append(row)
        return pts

    def peel_grid(self, pts, dist, top_axis=(0.0, 0.0, 0.85)):
        """Offset a grid inward along its surface normal."""
        return offset_grid(pts, dist, top_axis)

