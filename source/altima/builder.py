"""Core assembler: collection tree, part registry, naming rules, shell meshing."""

import math
import re
import bpy
from mathutils import Vector
from . import meshutils as mu
from . import spec

PREFIX = "ALTIMA2000"
NAME_RE = re.compile(r"^ALTIMA2000_[A-Z0-9]+_[A-Za-z0-9]+_[A-Za-z0-9_]+$")

# ---------------------------------------------------------------------------
# collection tree: (root key, display name, [child display names])
# ---------------------------------------------------------------------------
COLLECTION_TREE = [
    ("Body",        "ALTIMA2000_Body",        ["Body_Panels", "Body_Shell", "Body_Structure"]),
    ("Doors",       "ALTIMA2000_Doors",       ["Door_FL", "Door_FR", "Door_RL", "Door_RR", "Door_Hardware"]),
    ("DoorModule",  "ALTIMA2000_DoorModule",  ["Door_Module_Skin", "Door_Module_Frame",
                                               "Door_Module_Hardware", "Door_Module_Glazing",
                                               "Door_Module_Trim"]),
    ("Engine",      "ALTIMA2000_Engine",      ["Engine_LongBlock", "Engine_Head", "Engine_Intake",
                                               "Engine_ExhaustSide", "Engine_Cooling", "Engine_Fuel",
                                               "Engine_Accessory", "Engine_Emission"]),
    ("Drivetrain",  "ALTIMA2000_Drivetrain",  ["Drivetrain_Transaxle", "Drivetrain_Drive", "Drivetrain_Mount"]),
    ("Suspension",  "ALTIMA2000_Suspension",  ["Suspension_Front", "Suspension_Rear", "Suspension_Steering"]),
    ("Wheels",      "ALTIMA2000_Wheels",      ["Wheel_FL", "Wheel_FR", "Wheel_RL", "Wheel_RR", "Wheel_Hardware"]),
    ("Interior",    "ALTIMA2000_Interior",    ["Interior_Dash", "Interior_Seats", "Interior_Console",
                                               "Interior_Trim", "Interior_Insulation"]),
    ("Electrical",  "ALTIMA2000_Electrical",  ["Electrical_Harness", "Electrical_Battery", "Electrical_Modules",
                                               "Electrical_Lighting"]),
    ("Fasteners",   "ALTIMA2000_Fasteners",   ["Fasteners_Bolts", "Fasteners_Screws", "Fasteners_Nuts",
                                               "Fasteners_Clips"]),
    ("Glass",       "ALTIMA2000_Glass",       ["Glass_Glazing", "Glass_Mirrors"]),
    ("Trim",        "ALTIMA2000_Trim",        ["Trim_Exterior", "Trim_Seals", "Trim_Badges"]),
    ("Brakes",      "ALTIMA2000_Brakes",      ["Brakes_Front", "Brakes_Rear", "Brakes_Hydraulics"]),
    ("Exhaust",     "ALTIMA2000_Exhaust",     ["Exhaust_Manifold", "Exhaust_Pipe", "Exhaust_Muffler"]),
    ("Fluids",      "ALTIMA2000_Fluids",      ["Fluids_Engine", "Fluids_Body"]),
    ("Safety",      "ALTIMA2000_Safety",      ["Safety_Restraints"]),
    ("Publish",     "ALTIMA2000_Publish",     []),
    ("Sequence",    "ALTIMA2000_Sequence",    []),
]

#: sub-collection name -> top-level category name
COLLECTION_OF = {}
for _top, _cname, _subs in COLLECTION_TREE:
    for _s in _subs:
        COLLECTION_OF[_s] = _top

#: collections named after their whole system rather than a sub-assembly
COLLECTION_OF.update({
    "Engine": "Engine",
    "Safety": "Safety",
    "Wheels": "Wheels",
    "Brakes": "Brakes",
    "Exhaust": "Exhaust",
    "Fluids": "Fluids",
    "Glass": "Glass",
    "Trim": "Trim",
    "Body": "Body",
    "Interior": "Interior",
    "Electrical": "Electrical",
    "Fasteners": "Fasteners",
    "Suspension": "Suspension",
    "Drivetrain": "Drivetrain",
    "Doors": "Doors",
    "DoorModule": "DoorModule",
    "Sequence": "Sequence",
})

#: module key -> the TOP-LEVEL collection(s) that make up that module.
#: Sub-collections travel with their parent, so only roots are listed here.
MODULE_COLLECTIONS = {
    "engine": ["ALTIMA2000_Engine"],
    "drivetrain": ["ALTIMA2000_Drivetrain"],
    "suspension": ["ALTIMA2000_Suspension"],
    "wheels": ["ALTIMA2000_Wheels"],
    "brakes": ["ALTIMA2000_Brakes"],
    "exhaust": ["ALTIMA2000_Exhaust"],
}

#: the standalone door module (change 2) - exported as its own .blend too
DOOR_MODULE_COLLECTIONS = ["ALTIMA2000_DoorModule"]

#: every module written by the modular export, in report order
ALL_MODULES = dict(MODULE_COLLECTIONS)
ALL_MODULES["doors"] = DOOR_MODULE_COLLECTIONS

# group code -> (collection display name, sub-collection display name)
GROUP_CODES = {
    "BD": ("BODY", "Body_Panels"),
    "SH": ("SHEL", "Body_Structure"),
    "DR": ("DOOR", "Door_Hardware"),
    "DRM": ("DRM", "Door_Module_Skin"),
    "GL": ("GLAZ", "Glass_Glazing"),
    "MI": ("MIRR", "Glass_Mirrors"),
    "MD": ("MLDG", "Trim_Exterior"),
    "SL": ("SEAL", "Trim_Seals"),
    "IN": ("INTR", "Interior_Trim"),
    "ST": ("SEAT", "Interior_Seats"),
    "EL": ("ELEC", "Electrical_Harness"),
    "LM": ("LAMP", "Electrical_Lighting"),
    "EN": ("ENG", "Engine"),
    "TR": ("TRN", "Drivetrain_Transaxle"),
    "EX": ("EXH", "Exhaust"),
    "SU": ("SUSP", "Suspension"),
    "SR": ("STR", "Suspension_Steering"),
    "BR": ("BRAK", "Brakes"),
    "WH": ("WHL", "Wheels"),
    "FT": ("FAST", "Fasteners_Bolts"),
    "SC": ("SCRE", "Fasteners_Screws"),
    "CL": ("CLIP", "Fasteners_Clips"),
    "FL": ("FLUD", "Fluids"),
    "EM": ("EMIS", "Engine_Emission"),
    "SF": ("SAFE", "Safety"),
    "BA": ("BATT", "Electrical_Battery"),
}


class Registry:
    """Owns every created object and the manifest rows describing them."""

    def __init__(self, mats, verbose=True):
        self.mats = mats
        self.colls = {}
        self.parts = []
        self.seq = {}
        self.verbose = verbose
        self._last_coll = None
        self._last_grp = None
        self._last_seq = 0

    # ---------------------------------------------------------------- collections
    def build_collections(self, scene):
        for key, disp, children in COLLECTION_TREE:
            col = bpy.data.collections.new(disp)
            scene.collection.children.link(col)
            self.colls[key] = col
            for c in children:
                sub = bpy.data.collections.new(c)
                col.children.link(sub)
                self.colls[c] = sub
        bpy.context.view_layer.active_layer_collection = \
            bpy.context.view_layer.layer_collection.children[COLLECTION_TREE[0][1]]

    def coll(self, name):
        return self.colls[name]

    # ---------------------------------------------------------------- names
    def make_name(self, group, tag, detail, seq=None):
        """ALTIMA2000_<GROUP>_<Tag>_<Detail>[_<seq>] - all ASCII, no spaces."""
        g = GROUP_CODES[group][0]
        if seq is None:
            name = "%s_%s_%s_%s" % (PREFIX, g, tag, detail)
        else:
            name = "%s_%s_%s_%s_%03d" % (PREFIX, g, tag, detail, seq)
        if not NAME_RE.match(name):
            raise ValueError("bad part name: %r" % name)
        return name

    def next_seq(self, group, tag, detail):
        """Deterministic per-prefix sequence, restarting when the prefix changes."""
        key = (group, tag, detail)
        if key != getattr(self, "_last_key", None):
            self._last_key = key
            self.seq.setdefault(key, 0)
        n = self.seq[key]
        self.seq[key] = n + 1
        return n + 1

    # ---------------------------------------------------------------- add parts
    def add(self, name, verts, faces, coll_name, mat, meta=None, smooth=False,
            loc=(0, 0, 0), matrix=None, rot=(0.0, 0.0, 0.0)):
        coll = self.colls[coll_name]
        ob = mu.make_object(name, verts, faces, coll, mat=mat, smooth=smooth,
                            loc=loc, matrix=matrix, meta=meta, rot=rot)
        self.parts.append({"name": name, "collection": coll_name,
                           "group": (meta or {}).get("group", ""),
                           "sub": (meta or {}).get("sub", ""),
                           "kind": (meta or {}).get("kind", "geometry"),
                           "part": (meta or {}).get("part", ""),
                           "material": mat.name,
                           "material_key": (meta or {}).get("mat_key", ""),
                           "template": "",
                           "offset": [round(float(loc[0]), 6), round(float(loc[1]), 6),
                                      round(float(loc[2]), 6)],
                           "rotation": [round(float(rot[0]), 6), round(float(rot[1]), 6),
                                        round(float(rot[2]), 6)],
                           "assembled": (meta or {}).get("asmb", True),
                           "notes": (meta or {}).get("notes", ""),
                           "object": ob})
        return ob

    def add_grid(self, name, pts, coll_name, mat, thickness, meta=None, smooth=True,
                 flip_if_needed=True):
        """Shelled surface from a point grid: outer skin + inner skin + rim."""
        verts, faces = build_shell(pts, thickness, flip_if_needed=flip_if_needed,
                                   flip_normals=bool((meta or {}).get("flip")))
        loc = centroid(verts)
        return self.add(name, verts, faces, coll_name, mat, meta=meta, smooth=smooth,
                        loc=loc)

    def add_seal(self, name, pts, radius, coll_name, mat, meta=None, tube_seg=8):
        """Round rubber seal swept along a poly-line."""
        loc = centroid([p for p in pts])
        g, f = mu.loft(_tube_rings(pts, radius, tube_seg), close_start=True, close_end=True)
        return self.add(name, g, f, coll_name, mat, meta=meta, smooth=True, loc=loc)

    # ---------------------------------------------------------------- instancing
    def template(self, name, verts, faces, mat, smooth=False):
        """Build a reusable mesh datablock (no object) for instanced parts."""
        me = bpy.data.meshes.new(name)
        me.from_pydata(verts, [], faces)
        me.validate(verbose=False)
        me.update()
        me.materials.append(mat)
        if smooth:
            for p in me.polygons:
                p.use_smooth = True
        return me

    def instanced(self, name, mesh, loc, coll_name, meta=None, rot=(0.0, 0.0, 0.0),
                  scale=(1.0, 1.0, 1.0)):
        """A separate object sharing ``mesh`` - individually selectable and
        named, but one mesh datablock for the whole family."""
        coll = self.colls[coll_name]
        ob = bpy.data.objects.new(name, mesh)
        ob.location = loc
        ob.rotation_euler = rot
        ob.scale = scale
        m = dict(meta or {})
        ob["asmb"] = {
            "loc": [round(float(loc[0]), 6), round(float(loc[1]), 6), round(float(loc[2]), 6)],
            "rot": [round(float(rot[0]), 6), round(float(rot[1]), 6), round(float(rot[2]), 6)],
            "template": mesh.name,
            "asmb": True,
            "part": m.get("part", ""),
            "sub": m.get("sub", ""),
            "kind": m.get("kind", "geometry"),
        }
        coll.objects.link(ob)
        self.parts.append({
            "name": name, "collection": coll_name,
            "group": m.get("group", ""), "sub": m.get("sub", ""),
            "kind": m.get("kind", "geometry"),
            "part": m.get("part", ""),
            "material": mesh.materials[0].name if mesh.materials else "",
            "material_key": m.get("mat_key", ""),
            "template": mesh.name,
            "offset": [round(float(loc[0]), 6), round(float(loc[1]), 6),
                       round(float(loc[2]), 6)],
            "rotation": [round(float(rot[0]), 6), round(float(rot[1]), 6),
                         round(float(rot[2]), 6)],
            "assembled": True,
            "notes": m.get("notes", ""),
            "object": ob,
        })
        return ob

    def add_empty(self, name, coll_name, loc=(0.0, 0.0, 0.0), display="PLAIN_AXES",
                  size=0.25, meta=None):
        """Create a named empty (animation target / parent) in a collection.

        Empties are *not* registered as parts - they carry no geometry and are
        excluded from the part manifest - but they do get an ``asmb`` custom
        property so the assembly tools can find and restore them.
        """
        coll = self.colls[coll_name]
        ob = bpy.data.objects.new(name, None)
        ob.empty_display_type = display
        ob.empty_display_size = size
        ob.location = loc
        info = {"loc": [round(float(loc[0]), 6), round(float(loc[1]), 6),
                        round(float(loc[2]), 6)],
                "rot": [0.0, 0.0, 0.0],
                "kind": "empty"}
        info.update(meta or {})
        ob["asmb"] = info
        coll.objects.link(ob)
        return ob

    def finalize_counts(self):
        return len(self.parts)

    # ---------------------------------------------------------------- manifest sync
    def sync_manifest(self):
        """Re-read every object's real transform into the manifest.

        Parts that were re-positioned after creation (e.g. with ``place()``)
        must not leave a stale offset behind, otherwise the exported manifest
        could not be used to reassemble the car exactly.
        """
        for row in self.parts:
            ob = row["object"]
            loc = [round(float(ob.location[0]), 6), round(float(ob.location[1]), 6),
                   round(float(ob.location[2]), 6)]
            rot = [round(float(ob.rotation_euler[0]), 6),
                   round(float(ob.rotation_euler[1]), 6),
                   round(float(ob.rotation_euler[2]), 6)]
            scl = [round(float(ob.scale[0]), 6), round(float(ob.scale[1]), 6),
                   round(float(ob.scale[2]), 6)]
            row["offset"] = loc
            row["rotation"] = rot
            row["scale"] = scl
            info = dict(ob.get("asmb", {}))
            info["loc"] = loc
            info["rot"] = rot
            info["collection"] = row["collection"]
            info["part"] = row.get("part", "")
            info["group"] = row.get("group", "")
            info["sub"] = row.get("sub", "")
            ob["asmb"] = info


# ---------------------------------------------------------------------------
# geometry helpers used by the registry
# ---------------------------------------------------------------------------


def centroid(verts):
    n = float(len(verts))
    return (sum(v[0] for v in verts) / n,
            sum(v[1] for v in verts) / n,
            sum(v[2] for v in verts) / n)


def _tube_rings(pts, radius, seg=8):
    pts = [Vector(p) for p in pts]
    rings = []
    up = Vector((0, 0, 1))
    for i, p in enumerate(pts):
        if len(pts) < 2:
            d = Vector((1, 0, 0))
        elif i == 0:
            d = pts[1] - pts[0]
        elif i == len(pts) - 1:
            d = pts[-1] - pts[-2]
        else:
            d = pts[i + 1] - pts[i - 1]
        if d.length < 1e-9:
            d = Vector((1, 0, 0))
        d = d.normalized()
        ref = up if abs(d.z) < 0.9 else Vector((1, 0, 0))
        n1 = d.cross(ref).normalized()
        n2 = d.cross(n1).normalized()
        r = []
        for k in range(seg):
            a = mu.TAU * k / seg
            r.append(tuple(p + n1 * (radius * math.cos(a)) + n2 * (radius * math.sin(a))))
        rings.append(r)
    return rings


def build_shell(pts, thickness, flip_if_needed=True, flip_normals=False):
    """Turn an open point grid into a closed, thin-walled shell.

    Outer skin follows ``pts``; the inner skin is offset along the surface
    normal; the four borders are closed with rim quads so every panel is a
    watertight solid - identical to a real pressed steel panel.
    """
    nu = len(pts)
    nv = len(pts[0])
    P = [[Vector(p) for p in row] for row in pts]

    N = [[Vector((0.0, 0.0, 0.0)) for _ in range(nv)] for _ in range(nu)]
    for i in range(nu - 1):
        for j in range(nv - 1):
            a = P[i][j]
            b = P[i + 1][j]
            c = P[i][j + 1]
            n = (b - a).cross(c - a)
            if n.length > 1e-12:
                n.normalize()
                for (ii, jj) in ((i, j), (i + 1, j), (i, j + 1), (i + 1, j + 1)):
                    N[ii][jj] += n
    if flip_if_needed:
        axis = Vector((0.0, 0.0, 0.85))
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
            if flip_normals:
                N[i][j] = -N[i][j]

    outer = []
    inner = []
    for i in range(nu):
        for j in range(nv):
            p = P[i][j]
            q = p - N[i][j] * thickness
            outer.append((p.x, p.y, p.z))
            inner.append((q.x, q.y, q.z))

    def oi(i, j):
        return i * nv + j

    def ii(i, j):
        return nu * nv + i * nv + j

    faces = []
    for i in range(nu - 1):
        for j in range(nv - 1):
            faces.append((oi(i, j), oi(i + 1, j), oi(i + 1, j + 1), oi(i, j + 1)))
            faces.append((ii(i, j), ii(i, j + 1), ii(i + 1, j + 1), ii(i + 1, j)))
    # rim borders
    for i in range(nu - 1):
        faces.append((oi(i, 0), oi(i + 1, 0), ii(i + 1, 0), ii(i, 0)))
        faces.append((oi(i, nv - 1), ii(i, nv - 1), ii(i + 1, nv - 1), oi(i + 1, nv - 1)))
    for j in range(nv - 1):
        faces.append((oi(0, j), ii(0, j), ii(0, j + 1), oi(0, j + 1)))
        faces.append((oi(nu - 1, j), oi(nu - 1, j + 1), ii(nu - 1, j + 1), ii(nu - 1, j)))
    return outer + inner, faces


def hw_at(v, x, side):
    """Half-width helper: returns signed Y for the given side ('L' = +Y)."""
    p = v.params(x)
    return p["hw_max"] if side == "L" else -p["hw_max"]
