"""Body panels, closures, structure, glass, lamps, seals and exterior trim."""

import math
from mathutils import Vector
from .. import meshutils as mu
from .. import spec
from . import common as C

W = spec.wmap

# ---------------------------------------------------------------------------
# panel break points (design space)
# ---------------------------------------------------------------------------
X_HOOD_F, X_HOOD_R = 1.900, 0.800
X_FEND_R = 1.115
X_DR_F_F, X_DR_F_R = 0.600, -0.240
X_DR_R_F, X_DR_R_R = -0.290, -0.875
X_TRUNK_F, X_TRUNK_R = -1.560, -2.060
X_BUMP_F, X_BUMP_R = 1.900, -2.000
X_WS_B, X_WS_T = 0.625, 0.060
X_ROOF_R = -0.860
X_BL_B = -1.520

SEAM_ROWS = 3
T_PANEL = 0.010
T_GLASS = 0.005


def _lin(a, b, n):
    return [a + (b - a) * i / n for i in range(n + 1)]


def arch_ri(surf, cx, side, rim=0.020, ri_stop=1.55):
    """Ring index of the wheel-arch lip outline at world station x."""
    def f(xw):
        zc = spec.ARCH_R * 0.75
        z = zc + math.sqrt(max(0.0, (spec.ARCH_R - rim) ** 2 - (xw - cx) ** 2))
        return surf.ri_at_z(xw, z, 2, 8)
    return f


# ---------------------------------------------------------------------------
# 1. main body structure (side rings + underbody -> separate panels)
# ---------------------------------------------------------------------------


def build_structure(reg, mats, surf, M):
    p = mats
    # ---- side body panel (the big unibody side, right + left) --------------
    for side in ("R", "L"):
        xs = [W(x) for x in _lin(X_FEND_R, X_DR_R_R, 16)]
        pts = surf.side_glass_grid(xs, lambda x: 1.35, 8.0, SEAM_ROWS, side)
        reg.add_grid(reg.make_name("BD", "Side", "Body_%s" % side), pts,
                     "Body_Panels", p["paint_gold"], 0.012,
                     meta={"group": "BD", "sub": "Side", "part": "Side_%s" % side,
                           "mat_key": "paint_gold", "flip": False,
                           "notes": "unibody side outer panel (rocker to belt line)"})

    # ---- underbody floor ---------------------------------------------------
    fz = 0.0
    pts = surf.band_grid([W(x) for x in _lin(-1.900, 1.900, 18)], 2.55, 2.55, 1, "R")
    grid = []
    for i, x in enumerate([W(v) for v in _lin(-1.900, 1.900, 18)]):
        row = []
        for j in range(7):
            y = -0.80 + 1.60 * j / 6
            row.append((x, y, fz + 0.215))
        grid.append(row)
    reg.add_grid("ALTIMA2000_SHEL_Floor_Underbody", grid, "Body_Structure",
                 p["underbody"], 0.010,
                 meta={"group": "SH", "sub": "Floor", "part": "Floor",
                       "mat_key": "underbody",
                       "notes": "underbody floor pressing with seam sealer"})
    M["underbody"] = grid

    # ---- sill / rocker panels ---------------------------------------------
    for side in ("R", "L"):
        xs = [W(x) for x in _lin(-0.870, 0.600, 14)]
        pts = surf.band_grid(xs, 1.95, 0.0, 3, side)
        reg.add_grid(reg.make_name("BD", "Rocker", "Sill_%s" % side), pts,
                     "Body_Panels", p["paint_gold"], 0.009,
                     meta={"group": "BD", "sub": "Rocker", "part": "Sill_%s" % side,
                           "mat_key": "paint_gold", "notes": "rocker sill panel"})
    return M


# ---------------------------------------------------------------------------
# 2. hood, trunk lid, fenders, bumpers, roof, closures
# ---------------------------------------------------------------------------


def build_panels(reg, mats, surf, M):
    p = mats
    nx = 14
    # ---- hood --------------------------------------------------------------
    hood = surf.surface_grid(W(X_HOOD_R), W(X_HOOD_F), 14.5, 29.5, nx=nx, nr=6)
    reg.add_grid("ALTIMA2000_BODY_Hood_Outer", hood, "Body_Panels", p["paint_gold"],
                 T_PANEL, meta={"group": "BD", "sub": "Hood", "part": "Hood",
                                "mat_key": "paint_gold", "notes": "hood outer skin"})
    hood_in = mu.offset_grid(hood, 0.048)
    reg.add_grid("ALTIMA2000_BODY_Hood_Inner", hood_in, "Body_Panels", p["paint_under"],
                 0.003, meta={"group": "BD", "sub": "Hood", "part": "Hood",
                              "mat_key": "paint_under",
                              "notes": "hood inner panel (structural)"})
    # hood inner ribs / reinforcements
    for i in range(2):
        x = W(1.05 + 0.45 * i)
        pts = [surf.point(x, 14.5 + 1.2 + 2.2 * j) for j in range(2)]
        rib = []
        for dx in (-0.007, 0.007):
            row = []
            for k in range(5):
                y = -0.52 + 1.04 * k / 4
                row.append((x + dx, y, surf.top_z(x, y) - 0.040))
            rib.append(row)
        reg.add_grid(reg.make_name("BD", "HoodRib", "Cross_%s" % "AB"[i]), rib,
                     "Body_Panels", p["paint_under"], 0.0025,
                     meta={"group": "BD", "sub": "Hood", "part": "HoodRib",
                           "mat_key": "paint_under", "notes": "hood inner rib"})

    # ---- roof --------------------------------------------------------------
    roof = surf.surface_grid(W(X_WS_T), W(X_ROOF_R), 14.5, 29.5, nx=10, nr=6)
    reg.add_grid("ALTIMA2000_BODY_Roof_Outer", roof, "Body_Panels", p["paint_gold"],
                 0.009, meta={"group": "BD", "sub": "Roof", "part": "Roof",
                              "mat_key": "paint_gold", "notes": "roof panel"})
    # roof bows
    for i, xd in enumerate((0.030, -0.230, -0.500, -0.760)):
        y = surf.wl(W(xd), 1.30) - 0.010
        v = []
        for k in range(13):
            yy = -y + 2 * y * k / 12
            v.append((W(xd), yy, surf.top_z(W(xd), yy) - 0.012))
        reg.add("ALTIMA2000_SHEL_RoofBow_%03d" % (i + 1), v,
                [(k, k + 1) for k in range(12)], "Body_Structure",
                p["paint_under"],
                meta={"group": "SH", "sub": "Roof", "part": "RoofBow",
                      "mat_key": "paint_under", "notes": "roof bow reinforcement"})

    # ---- fenders -----------------------------------------------------------
    for side in ("R", "L"):
        f = arch_ri(surf, W(spec.AXLE_F), side)
        xs = ([W(v) for v in _lin(X_FEND_R, X_HOOD_F, 12)]
              + [W(v) for v in _lin(X_HOOD_F, 1.990, 4)])
        pts = surf.band_grid(xs, 9.2, f, SEAM_ROWS, side)
        reg.add_grid(reg.make_name("BD", "Fender", "Front_%s" % side), pts,
                     "Body_Panels", p["paint_gold"], T_PANEL,
                     meta={"group": "BD", "sub": "Fender", "part": "Fender_%s" % side,
                           "mat_key": "paint_gold",
                           "notes": "front fender skin with wheel-arch cut"})
        # fender inner liner
        pts2 = surf.band_grid(xs, 9.0, lambda x: f(x) - 2.6, SEAM_ROWS, side)
        reg.add_grid(reg.make_name("BD", "FenderLiner", "Front_%s" % side),
                     pts2, "Body_Panels", p["plastic_blk_m"], 0.006,
                     meta={"group": "BD", "sub": "Fender", "part": "Liner_%s" % side,
                           "mat_key": "plastic_blk_m",
                           "notes": "front wheel-arch splash liner"})

    # ---- quarter panels (rear fenders) ------------------------------------
    for side in ("R", "L"):
        f = arch_ri(surf, W(spec.AXLE_R), side)
        xs = [W(v) for v in _lin(X_DR_R_R, X_TRUNK_R, 14)]
        pts = surf.band_grid(xs, 9.0, f, SEAM_ROWS, side)
        reg.add_grid(reg.make_name("BD", "Quarter", "Rear_%s" % side), pts,
                     "Body_Panels", p["paint_gold"], T_PANEL,
                     meta={"group": "BD", "sub": "Quarter", "part": "Quarter_%s" % side,
                           "mat_key": "paint_gold", "notes": "rear quarter panel"})
        # quarter inner
        pts2 = surf.band_grid(xs, 8.6, lambda x: max(1.4, f(x) - 2.6), SEAM_ROWS, side)
        reg.add_grid(reg.make_name("BD", "QuarterInner", "Rear_%s" % side), pts2,
                     "Body_Structure", p["paint_under"], 0.006,
                     meta={"group": "SH", "sub": "Quarter", "part": "QuarterInner_%s" % side,
                           "mat_key": "paint_under", "notes": "quarter inner structure"})

    # ---- trunk lid ---------------------------------------------------------
    trunk = surf.surface_grid(W(X_TRUNK_F), W(X_TRUNK_R), 24.0, 22.0, nx=8, nr=4)
    trunk = [[(pp[0], pv[1], pv[2]) for pv in row] for row in trunk for pp in [row[0]]]
    grid = []
    for i, xd in enumerate(_lin(X_TRUNK_F, X_TRUNK_R, 8)):
        row = []
        ymax = surf.wl(W(xd), 1.05) - 0.012
        for j in range(7):
            y = -ymax + 2 * ymax * j / 6
            row.append((W(xd), y, surf.top_z(W(xd), y)))
        grid.append(row)
    reg.add_grid("ALTIMA2000_BODY_TrunkLid_Outer", grid, "Body_Panels",
                 p["paint_gold"], T_PANEL,
                 meta={"group": "BD", "sub": "Trunk", "part": "TrunkLid",
                       "mat_key": "paint_gold", "notes": "trunk lid outer skin"})
    reg.add_grid("ALTIMA2000_BODY_TrunkLid_Inner", mu.offset_grid(grid, 0.055),
                 "Body_Panels", p["paint_under"], 0.003,
                 meta={"group": "BD", "sub": "Trunk", "part": "TrunkLid",
                       "mat_key": "paint_under", "notes": "trunk lid inner panel"})

    # ---- bumpers and valances ---------------------------------------------
    _bumper(reg, p, "F", M)
    _bumper(reg, p, "R", M)

    # ---- cowl, plenum, grille ---------------------------------------------
    reg.add("ALTIMA2000_BODY_Cowl_Panel", _cowl_v(reg, 0.860, 0.625),
            [(0, 1, 2, 3), (0, 3, 2, 1)], "Body_Panels", p["plastic_blk_m"],
            meta={"group": "BD", "sub": "Cowl", "part": "Cowl",
                  "mat_key": "plastic_blk_m", "notes": "cowl top panel"})

    # ---- radiator support / front end -------------------------------------
    v, f = C.box_vf if False else (None, None)
    _front_end(reg, p, M)
    _rear_end(reg, p, M)
    _fuel_doors(reg, p, surf)
    return M


def _cowl_v(reg, y, x):
    return [(W(x), -y, 0.905), (W(x), y, 0.905), (W(x - 0.05), y, 0.830),
            (W(x - 0.05), -y, 0.830)]


def _bumper(reg, p, end, M):
    """Bumper cover + reinforcement beam + energy absorber (+ grille, front)."""
    front = end == "F"
    tag = "Front" if front else "Rear"
    HALF = 0.870
    # front-most x of the fascia at the centreline and at the fender line
    x_out = W(2.960 if front else -2.700)
    x_in = W(2.150 if front else -2.060)
    x_beam = W(2.170 if front else -2.090)
    # ---- cover: rows across the car, columns up the fascia ----------------
    rows = []
    for i in range(15):
        t = -1.0 + 2.0 * i / 14.0
        y = HALF * math.copysign(abs(t) ** 0.85, t)
        reach = (abs(t) ** 1.8)
        xf = x_out + (x_in - x_out) * reach
        z_top = 0.795 - 0.075 * (abs(t) ** 2.0)
        z_bot = 0.185 + 0.055 * (abs(t) ** 2.6)
        row = []
        for j in range(6):
            v = j / 5.0
            z = z_bot + (z_top - z_bot) * v
            bulge = 0.055 * (1.0 - (2.0 * v - 1.0) ** 2)
            row.append((xf - bulge, y, z))
        rows.append(row)
    reg.add_grid(reg.make_name("BD", "BumperCover", tag), rows, "Body_Panels",
                 p["paint_gold"], 0.007,
                 meta={"group": "BD", "sub": "Bumper", "part": "BumperCover_" + tag,
                       "mat_key": "paint_gold",
                       "notes": "%s bumper cover (thermoplastic olefin)" % tag.lower()})
    # lower valance / air dam
    rows2 = []
    for i in range(11):
        t = -1.0 + 2.0 * i / 10.0
        y = (HALF - 0.040) * math.copysign(abs(t) ** 0.85, t)
        xf = x_out + (x_in - x_out) * abs(t) ** 1.8
        rows2.append([(xf - 0.070 + 0.030 * k / 2, y, 0.105 + 0.055 * k / 2)
                      for k in range(3)])
    reg.add_grid(reg.make_name("BD", "Valance", tag), rows2, "Body_Panels",
                 p["plastic_blk_m"], 0.005,
                 meta={"group": "BD", "sub": "Bumper", "part": "Valance_" + tag,
                       "mat_key": "plastic_blk_m",
                       "notes": "%s lower valance / air dam" % tag.lower()})
    # ---- reinforcement beam + energy absorber -----------------------------
    v, f = _beam_v(x_beam, 1.140, 0.135, 0.085, zcentre=0.520)
    reg.add(reg.make_name("BD", "BumperBeam", tag), v, f, "Body_Structure", p["steel"],
            meta={"group": "SH", "sub": "Bumper", "part": "BumperBeam_" + tag,
                  "mat_key": "steel",
                  "notes": "%s bumper reinforcement beam" % tag.lower()})
    v, f = _beam_v(x_beam - 0.070 * (1 if front else -1), 1.060, 0.110, 0.110,
                   zcentre=0.520)
    reg.add(reg.make_name("BD", "BumperAbsorber", tag), v, f, "Body_Panels", p["foam"],
            meta={"group": "BD", "sub": "Bumper", "part": "Absorber_" + tag,
                  "mat_key": "foam",
                  "notes": "%s bumper energy absorber (EA foam)" % tag.lower()})
    # mounting brackets
    for k in range(2):
        y = 0.560 * (1 if k == 0 else -1)
        v, f = _beam_v(x_beam - 0.060 * (1 if front else -1), 0.075, 0.130, 0.075,
                       ycentre=y, zcentre=0.520)
        reg.add(reg.make_name("BD", "BumperBracket", tag, k + 1), v, f,
                "Body_Structure", p["steel"],
                meta={"group": "SH", "sub": "Bumper", "part": "BumperBracket_" + tag,
                      "mat_key": "steel", "notes": "bumper mounting bracket"})
    if not front:
        return
    # ---- grille -----------------------------------------------------------
    rows = []
    for i in range(9):
        y = -0.560 + 1.120 * i / 8.0
        xg = W(2.930)
        rows.append([(xg + 0.020 * k, y, 0.775 + 0.135 * (1 - abs(y / 0.56) ** 2) ** 0.5
                      - 0.026 * k) for k in range(3)])
    reg.add_grid("ALTIMA2000_BODY_Grille_Assembly", rows, "Body_Panels",
                 p["plastic_blk_g"], 0.010,
                 meta={"group": "BD", "sub": "Grille", "part": "Grille",
                       "mat_key": "plastic_blk_g",
                       "notes": "front grille surround and bars"})
    for k in range(4):
        y = -0.495 + 0.330 * k
        v, f = _beam_v(W(2.955), 0.040, 0.145, 0.020, ycentre=y, zcentre=0.850)
        reg.add(reg.make_name("MD", "GrilleBar", "Chrome", k + 1), v, f,
                "Trim_Exterior", p["chrome"],
                meta={"group": "MD", "sub": "Grille", "part": "GrilleBar",
                      "mat_key": "chrome", "notes": "chrome grille bar"})


def _beam_v(x, width, height, depth, ycentre=0.0, zcentre=0.420):
    """Axis-aligned box in the vertex order mu.BOX_FACES expects."""
    v = []
    for dz in (-0.5, 0.5):
        for (dy, dx) in ((-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)):
            v.append((x + dx * depth, ycentre + dy * width, zcentre + dz * height))
    return v, mu.BOX_FACES


def _front_end(reg, p, M):
    """Radiator support, headlamp mounting panel, hood latch panel."""
    v, f = _beam_v(W(2.400), 1.230, 0.520, 0.075, zcentre=0.700)
    reg.add("ALTIMA2000_SHEL_RadiatorSupport_Panel", v, f, "Body_Structure",
            p["steel"],
            meta={"group": "SH", "sub": "FrontEnd", "part": "RadiatorSupport",
                  "mat_key": "steel", "notes": "radiator core support panel"})
    for i, y in enumerate((0.52, -0.52)):
        v, f = _beam_v(W(2.330), 0.060, 0.540, 0.060, ycentre=y, zcentre=0.720)
        reg.add(reg.make_name("SH", "HeadlampPanel", "Side"), v, f, "Body_Structure",
                p["steel"],
                meta={"group": "SH", "sub": "FrontEnd", "part": "HeadlampPanel",
                      "mat_key": "steel", "notes": "headlamp mounting panel"})
        break
    for i in range(2):
        y = 0.50 * (1 if i == 0 else -1)
        v, f = _beam_v(W(2.310), 0.055, 0.480, 0.055, ycentre=y, zcentre=0.720)
        reg.add(reg.make_name("SH", "HeadlampPanel", "Side", i + 1), v, f,
                "Body_Structure", p["steel"],
                meta={"group": "SH", "sub": "FrontEnd", "part": "HeadlampPanel",
                      "mat_key": "steel", "notes": "headlamp mounting panel"})
    v, f = _beam_v(W(2.470), 0.300, 0.060, 0.070, zcentre=0.930)
    reg.add("ALTIMA2000_SHEL_LatchPanel_Upper", v, f, "Body_Structure", p["steel"],
            meta={"group": "SH", "sub": "FrontEnd", "part": "LatchPanel",
                  "mat_key": "steel", "notes": "hood latch striker panel"})
    # front wheel houses
    for side in ("R", "L"):
        rows = []
        for i, xd in enumerate(_lin(1.130, 1.960, 9)):
            row = []
            for j in range(5):
                t = j / 4
                xw = W(xd)
                r = math.sqrt(max(0.0, spec.ARCH_R ** 2 - (xw - spec.AXLE_F) ** 2))
                z = 0.120 + (0.360 + r) * t
                y = (0.560 + 0.170 * t) * (1 if side == "R" else -1)
                row.append((xw, y, z))
            rows.append(row)
        reg.add_grid(reg.make_name("SH", "WheelHouse", "Front_%s" % side), rows,
                     "Body_Structure", p["underbody"], 0.006,
                     meta={"group": "SH", "sub": "WheelHouse", "part": "WheelHouse_F_" + side,
                           "mat_key": "underbody", "notes": "front wheel house (strut tower side)"})
    # strut towers
    for side in ("R", "L"):
        y = 0.520 * (1 if side == "R" else -1)
        v, f = C.prism_poly if False else (None, None)
        rows = []
        for i in range(3):
            row = []
            for j in range(9):
                a = mu.TAU * j / 8
                row.append((W(1.380) + 0.170 * math.cos(a),
                            y + 0.075 * math.sin(a),
                            0.880 + 0.070 * i))
            rows.append(row)
        reg.add_grid(reg.make_name("SH", "StrutTower", "Front_%s" % side), rows,
                     "Body_Structure", p["steel"], 0.004,
                     meta={"group": "SH", "sub": "StrutTower", "part": "StrutTower_" + side,
                           "mat_key": "steel", "notes": "front suspension strut tower"})


def _rear_end(reg, p, M):
    """Rear panel, tail panel, rear wheel houses, parcel shelf, spare well."""
    v, f = _beam_v(W(-2.180), 1.180, 0.480, 0.060, zcentre=0.620)
    reg.add("ALTIMA2000_SHEL_RearPanel_Assembly", v, f, "Body_Structure", p["steel"],
            meta={"group": "SH", "sub": "RearEnd", "part": "RearPanel",
                  "mat_key": "steel", "notes": "rear body panel / tail panel"})
    for side in ("R", "L"):
        rows = []
        for i, xd in enumerate(_lin(-2.040, -1.230, 9)):
            row = []
            for j in range(5):
                t = j / 4
                xw = W(xd)
                r = math.sqrt(max(0.0, spec.ARCH_R ** 2 - (xw - spec.AXLE_R) ** 2))
                z = 0.120 + (0.360 + r) * t
                y = (0.560 + 0.160 * t) * (1 if side == "R" else -1)
                row.append((xw, y, z))
            rows.append(row)
        reg.add_grid(reg.make_name("SH", "WheelHouse", "Rear_%s" % side), rows,
                     "Body_Structure", p["underbody"], 0.006,
                     meta={"group": "SH", "sub": "WheelHouse", "part": "WheelHouse_R_" + side,
                           "mat_key": "underbody", "notes": "rear wheel house"})
    rows = []
    for i, xd in enumerate(_lin(-1.560, -0.900, 7)):
        row = []
        for j in range(7):
            y = -0.800 + 1.600 * j / 6
            row.append((W(xd), y, 0.760 + 0.030 * math.sin(math.pi * j / 6)))
        rows.append(row)
    reg.add_grid("ALTIMA2000_SHEL_ParcelShelf_Panel", rows, "Body_Structure",
                 p["steel"], 0.005,
                 meta={"group": "SH", "sub": "ParcelShelf", "part": "ParcelShelf",
                       "mat_key": "steel", "notes": "rear parcel shelf panel"})
    rows = []
    for i, xd in enumerate(_lin(-1.860, -1.300, 6)):
        row = []
        for j in range(7):
            y = -0.520 + 1.040 * j / 6
            row.append((W(xd), y, 0.320 + 0.030 * (1 - (j - 3) ** 2 / 9.0)))
        rows.append(row)
    reg.add_grid("ALTIMA2000_SHEL_SpareWell_Pan", rows, "Body_Structure", p["steel"],
                 0.004, meta={"group": "SH", "sub": "SpareWell", "part": "SpareWell",
                              "mat_key": "steel", "notes": "spare wheel well pressing"})


def _fuel_doors(reg, p, surf):
    for i, side in enumerate(("R", "L")):
        y = (surf.wl(W(-1.740), 0.900) - 0.004) * (1 if side == "L" else -1)
        poly = [(0.070 * math.cos(mu.TAU * k / 10),
                 0.070 * math.sin(mu.TAU * k / 10)) for k in range(10)]
        C.prism_poly(poly, (W(-1.740), y, 0.900), (0, 1, 0), 0.004,
                     "Body_Panels", reg.make_name("BD", "FuelDoor", "Side", i + 1),
                     reg, p["paint_gold"],
                     meta={"group": "BD", "sub": "Fuel", "part": "FuelDoor",
                           "mat_key": "paint_gold",
                           "notes": "fuel filler door (%s)" % side})
        C.prism_poly(poly, (W(-1.740), y - 0.006 * (1 if side == "L" else -1), 0.900),
                     (0, 1, 0), 0.002, "Body_Panels",
                     reg.make_name("BD", "FuelFiller", "Neck", i + 1),
                     reg, p["steel"],
                     meta={"group": "BD", "sub": "Fuel", "part": "FuelFiller",
                           "mat_key": "steel",
                           "notes": "fuel filler neck sealing disc (%s)" % side})


# ---------------------------------------------------------------------------
# 3. doors
# ---------------------------------------------------------------------------


def build_doors(reg, mats, surf, M):
    p = mats
    doors = [("FL", "L", X_DR_F_F, X_DR_F_R, "Front"),
             ("FR", "R", X_DR_F_F, X_DR_F_R, "Front"),
             ("RL", "L", X_DR_R_F, X_DR_R_R, "Rear"),
             ("RR", "R", X_DR_R_F, X_DR_R_R, "Rear")]
    for (tag, side, x0, x1, kind) in doors:
        sub = "Door_" + tag
        # ---- outer panel ----
        f = arch_ri(surf, W(spec.AXLE_F), side) if kind == "Front" \
            else arch_ri(surf, W(spec.AXLE_R), side)
        lo = (lambda x: max(0.05, min(f(x), 8.0))) if kind == "Front" else \
             (lambda x: max(0.05, min(f(x), 8.0)))
        xs = [W(v) for v in _lin(x1, x0, 10)]
        pts = surf.band_grid(xs, 8.0, lo, SEAM_ROWS, side)
        reg.add_grid(reg.make_name("DRM", "Skin", tag), pts, "Door_Module_Skin",
                     p["paint_gold"], 0.011,
                     meta={"group": "DRM", "sub": "Skin", "part": "Skin_" + tag,
                           "mat_key": "paint_gold",
                           "notes": "%s door loose outer skin (removable)" % kind.lower()})
        # ---- inner panel ----
        inner = surf.band_grid(xs, 7.0, lambda x: max(1.2, lo(x) - 1.0), SEAM_ROWS, side)
        reg.add_grid(reg.make_name("DR", "InnerPanel", tag),
                     mu.offset_grid(inner, 0.075), sub, p["paint_under"], 0.008,
                     meta={"group": "DR", "sub": tag, "part": "InnerPanel_" + tag,
                           "mat_key": "paint_under",
                           "notes": "%s door inner panel" % kind.lower()})
        # ---- window frame: A/B pillar + belt reinforcement ----
        rows = []
        for i, xd in enumerate(_lin(x1, x0, 6)):
            row = []
            top = 10.9
            for j in range(3):
                ri = 8.0 + (top - 8.0) * j / 2
                pt = surf.point(W(xd), ri)
                row.append((pt[0], pt[1] * (1 if side == "R" else -1), pt[2]))
            rows.append(row)
        reg.add_grid(reg.make_name("DRM", "Frame", tag), rows, "Door_Module_Frame",
                     p["paint_gold"], 0.009,
                     meta={"group": "DRM", "sub": "Frame", "part": "Frame_" + tag,
                           "mat_key": "paint_gold",
                           "notes": "%s door frame (window frame + belt reinforcement)"
                                    % kind.lower()})
        # belt line reinforcement bar
        v = []
        for i in range(7):
            xw = W(x1 + (x0 - x1) * i / 6)
            y = surf.wl(xw, 0.945) - 0.020
            v.append((xw, y * (1 if side == "L" else -1), 0.945))
        reg.add_seal(reg.make_name("DR", "ImpactBeam", tag), v, 0.012, sub,
                     p["steel"],
                     meta={"group": "DR", "sub": tag, "part": "ImpactBeam_" + tag,
                           "mat_key": "steel", "notes": "side impact beam"})
        # hinges
        for i in range(2):
            z = 0.560 if i == 0 else 0.930
            y = surf.wl(W(x0), z) - 0.030
            v, f = _beam_v(W(x0) + 0.028, 0.030, 0.055, 0.028, zcentre=z)
            v = [(vv[0], y * (1 if side == "L" else -1), vv[2]) for vv in v]
            reg.add(reg.make_name("DRM", "Hinge", tag, i + 1), v, f,
                    "Door_Module_Hardware", p["steel"],
                    meta={"group": "DRM", "sub": "Hinge", "part": "Hinge_" + tag,
                          "mat_key": "steel", "notes": "door hinge"})
        # check strap
        v, f = _beam_v(W(x0) - 0.050, 0.020, 0.024, 0.130,
                       zcentre=0.700)
        reg.add(reg.make_name("DR", "CheckStrap", tag), v, f, sub, p["steel"],
                meta={"group": "DR", "sub": tag, "part": "CheckStrap_" + tag,
                      "mat_key": "steel", "notes": "door check strap"})
        # latch
        z = 0.760
        y = surf.wl(W(x1 - 0.030), z) - 0.045
        v, f = _beam_v(W(x1 - 0.030), 0.050, 0.075, 0.030, zcentre=z)
        v = [(vv[0], y * (1 if side == "L" else -1), vv[2]) for vv in v]
        reg.add(reg.make_name("DRM", "Latch", tag), v, f, "Door_Module_Hardware",
                p["zinc"],
                meta={"group": "DRM", "sub": "Latch", "part": "Latch_" + tag,
                      "mat_key": "zinc", "notes": "door latch assembly"})
        # ---- outer handle ----
        z = 0.930
        y = surf.wl(W(x0 - 0.11), z) - 0.006
        row = []
        for i in range(5):
            xx = W(x0 - 0.170 + 0.125 * i / 4)
            row.append((xx, y * (1 if side == "L" else -1), z))
        reg.add_seal(reg.make_name("DR", "Handle", tag), row, 0.011, sub,
                     p["chrome"],
                     meta={"group": "DR", "sub": tag, "part": "Handle_" + tag,
                           "mat_key": "chrome", "notes": "exterior door handle"})
        C.prism_poly(C.circle_poly(0.030, 10),
                     (W(x0 - 0.190), y * (1 if side == "L" else -1), 0.930),
                     (0, 1, 0) if side == "R" else (0, -1, 0), 0.008, sub,
                     reg.make_name("DR", "KeyCylinder", tag), reg, p["chrome"],
                     meta={"group": "DR", "sub": tag, "part": "KeyCylinder_" + tag,
                           "mat_key": "chrome", "notes": "front door lock cylinder"}
                     ) if kind == "Front" else None
        # ---- window regulator + motor + glass run channel ----
        reg.add(reg.make_name("DRM", "WindowRegulator", tag),
                [(W(x0 - 0.40), 0.62 * (1 if side == "L" else -1), 0.70),
                 (W(x0 - 0.10), 0.62 * (1 if side == "L" else -1), 0.70),
                 (W(x0 - 0.10), 0.62 * (1 if side == "L" else -1), 0.74),
                 (W(x0 - 0.40), 0.62 * (1 if side == "L" else -1), 0.74)],
                [(0, 1, 2, 3)], "Door_Module_Hardware", p["zinc"],
                meta={"group": "DRM", "sub": "Regulator",
                      "part": "WindowRegulator_" + tag,
                      "mat_key": "zinc", "notes": "window regulator mechanism"})
        C.prism_poly(C.circle_poly(0.038, 10),
                     (W(x0 - 0.42), 0.60 * (1 if side == "L" else -1), 0.66),
                     (0, 1, 0), 0.075, sub,
                     reg.make_name("DR", "WindowMotor", tag), reg, p["zinc"],
                     meta={"group": "DR", "sub": tag, "part": "WindowMotor_" + tag,
                           "mat_key": "zinc", "notes": "power window motor"})
        # ---- trim panel ----
        rows = []
        for i, xd in enumerate(_lin(x1, x0, 6)):
            row = []
            for j in range(4):
                pt = surf.point(W(xd), 5.6 - 3.2 * j / 3)
                row.append((pt[0], (abs(pt[1]) - 0.070) * (1 if side == "L" else -1),
                            pt[2]))
            rows.append(row)
        reg.add_grid(reg.make_name("IN", "DoorTrimPanel", tag), rows, sub,
                     p["plastic_dk"], 0.008,
                     meta={"group": "IN", "sub": tag, "part": "DoorTrim_" + tag,
                           "mat_key": "plastic_dk", "notes": "interior door trim panel"})
        # ---- glass (front door gets a one-piece roll-down) ----
        gtag = "DoorGlass_" + tag
        rows = []
        for i, xd in enumerate(_lin(x1 + 0.030, x0 - 0.040, 6)):
            row = []
            for j in range(4):
                ri = 8.06 + (10.55 - 8.06) * j / 3
                pt = surf.point(W(xd), ri)
                row.append((pt[0], (abs(pt[1]) - 0.004) * (1 if side == "L" else -1),
                            pt[2]))
            rows.append(row)
        reg.add_grid(reg.make_name("GL", "DoorGlass", tag), rows, "Glass_Glazing",
                     p["glass_tint"], T_GLASS,
                     meta={"group": "GL", "sub": tag, "part": gtag,
                           "mat_key": "glass_tint", "notes": "door window glass"})
        # ---- seals ----
        v = [(W(x1 + 0.010), (surf.wl(W(x1 + 0.010), 0.940) - 0.004) * (1 if side == "L" else -1), 0.940)]
        for i in range(6):
            xw = W(x1 + 0.010 + (x0 - x1 - 0.030) * i / 5)
            v.append((xw, (surf.wl(xw, 0.958) - 0.004) * (1 if side == "L" else -1), 0.958))
        v.append((W(x0 - 0.020), (surf.wl(W(x0 - 0.020), 0.940) - 0.004) * (1 if side == "L" else -1), 0.940))
        reg.add_seal(reg.make_name("SL", "BeltSeal", tag), v, 0.008, sub,
                     p["rubber"],
                     meta={"group": "SL", "sub": tag, "part": "BeltSealOuter_" + tag,
                           "mat_key": "rubber", "notes": "outer belt line weatherstrip"})
        # ---- glass run channel (standalone door module: glazing) ----------
        grun = []
        for i in range(7):
            xd = x1 + (x0 - x1) * i / 6.0
            pt = surf.point(W(xd), 10.75)
            grun.append((pt[0], (abs(pt[1]) - 0.012) * (1 if side == "L" else -1), pt[2]))
        for i in range(1, 4):
            pt = surf.point(W(x0), 10.75 - 2.6 * i / 3.0)
            grun.append((pt[0], (abs(pt[1]) - 0.012) * (1 if side == "L" else -1), pt[2]))
        reg.add_seal(reg.make_name("DRM", "GlassRun", tag), grun, 0.009,
                     "Door_Module_Glazing", p["rubber"],
                     meta={"group": "DRM", "sub": "GlassRun",
                           "part": "GlassRun_" + tag, "mat_key": "rubber",
                           "notes": "window glass run channel (bailey channel)"})
    return M


# ---------------------------------------------------------------------------
# 4. glass: windscreen and backlight
# ---------------------------------------------------------------------------


def build_glass(reg, mats, surf, M):
    p = mats
    rows = []
    for i in range(9):
        t = i / 8.0
        xd = X_WS_B + (X_WS_T - X_WS_B) * t
        row = []
        for j in range(7):
            yf = 0.80 * (1.0 - t) + 0.545 * t
            y = -yf + 2 * yf * j / 6
            z = 0.958 + (1.372 - 0.958) * (t ** 0.92)
            row.append((W(xd), y, z))
        rows.append(row)
    reg.add_grid("ALTIMA2000_GLZ_Windshield_Laminated", rows, "Glass_Glazing",
                 p["glass_clear"], 0.0055,
                 meta={"group": "GL", "sub": "Windshield", "part": "Windshield",
                       "mat_key": "glass_clear",
                       "notes": "laminated windscreen, DOT shade band"})
    rows = []
    for i in range(8):
        t = i / 7.0
        xd = X_WS_T + (X_BL_B - X_WS_T) * t
        row = []
        for j in range(7):
            y = (-0.46 + 0.92 * j / 6) * (0.55 + 0.45 * t)
            z = 1.418 - 0.190 * (t ** 1.55)
            row.append((W(xd), y, z))
        rows.append(row)
    reg.add_grid("ALTIMA2000_GLZ_Backlight_Tempered", rows, "Glass_Glazing",
                 p["glass_tint"], T_GLASS,
                 meta={"group": "GL", "sub": "Backlight", "part": "Backlight",
                       "mat_key": "glass_tint", "notes": "rear window glass"})
    # rear quarter windows
    for side in ("R", "L"):
        rows = []
        for i in range(5):
            t = i / 4.0
            xw = W(-0.890 - 0.600 * t)
            row = []
            for j in range(3):
                z = 0.980 + (1.255 - 0.980) * j / 2 * (1.0 - 0.22 * t)
                y = surf.wl(xw, z) - 0.006
                rows_idx = 0
                row.append((xw, y * (1 if side == "L" else -1), z - 0.20 * t))
            rows.append(row)
        reg.add_grid(reg.make_name("GL", "QuarterGlass", "Rear_%s" % side), rows,
                     "Glass_Glazing", p["glass_tint"], T_GLASS,
                     meta={"group": "GL", "sub": "Quarter", "part": "QuarterGlass_" + side,
                           "mat_key": "glass_tint", "notes": "rear quarter window"})
    return M


# ---------------------------------------------------------------------------
# 5. lamps
# ---------------------------------------------------------------------------


def _lamp_shell(reg, mats, name, cx, cy, cz, size, mat, coll, sub, part, note=""):
    sx, sy, sz = size
    v = []
    for dx in (-sx / 2, sx / 2):
        for dy in (-sy / 2, sy / 2):
            for dz in (-sz / 2, sz / 2):
                v.append((cx + dx * (0.72 if dx < 0 else 1.0), cy + dy, cz + dz))
    order = [0, 1, 3, 2, 4, 5, 7, 6]
    v = [v[i] for i in order]
    return reg.add(name, v, mu.BOX_FACES, coll, mat,
                   meta={"group": "LM", "sub": sub, "part": part,
                         "mat_key": mat["asmb_key"] if False else "", "notes": note},
                   loc=(cx, cy, cz))


def build_lamps(reg, mats, surf, M):
    p = mats
    hl_size = (0.170, 0.300, 0.150)
    for side, sy in (("R", -1), ("L", 1)):
        y = 0.500 * sy
        cz = 0.800
        cx = W(2.630)
        # housing (black PP)
        v = []
        for dx in (-0.085, 0.085):
            for dy in (-0.150, 0.150):
                for dz in (-0.075, 0.075):
                    v.append((cx + dx, y + dy, cz + dz))
        v = [v[i] for i in [0, 1, 3, 2, 4, 5, 7, 6]]
        reg.add(reg.make_name("LM", "HeadlampHousing", side), v, mu.BOX_FACES,
                "Electrical_Lighting", p["plastic_blk_m"],
                meta={"group": "LM", "sub": "Headlamp", "part": "Housing_" + side,
                      "mat_key": "plastic_blk_m", "notes": "headlamp housing"})
        # lens
        v, f = _beam_v(cx + 0.092, 0.310, 0.155, 0.014, ycentre=y, zcentre=cz)
        reg.add(reg.make_name("LM", "HeadlampLens", side), v, f,
                "Electrical_Lighting", p["lamp_clear"],
                meta={"group": "LM", "sub": "Headlamp", "part": "Lens_" + side,
                      "mat_key": "lamp_clear", "notes": "headlamp lens"})
        # low / high beam reflectors + bulbs
        for k, dy in enumerate((-0.080, 0.080)):
            C.prism_poly(C.circle_poly(0.058, 14), (cx + 0.030, y + dy, cz),
                         (1, 0, 0), 0.030, "Electrical_Lighting",
                         reg.make_name("LM", "HeadlampReflector", side, k + 1), reg,
                         p["lamp_reflect"],
                         meta={"group": "LM", "sub": "Headlamp", "part": "Reflector_" + side,
                               "mat_key": "lamp_reflect", "notes": "headlamp reflector bowl"})
            C.prism_poly(C.circle_poly(0.013, 10), (cx + 0.012, y + dy, cz),
                         (1, 0, 0), 0.050, "Electrical_Lighting",
                         reg.make_name("LM", "HeadlampBulb", side, k + 1), reg, p["lamp_bulb"],
                         meta={"group": "LM", "sub": "Headlamp", "part": "Bulb_" + side,
                               "mat_key": "lamp_bulb", "notes": "H4 halogen bulb"})
        # park / turn lens
        v, f = _beam_v(cx + 0.070, 0.075, 0.075, 0.020, ycentre=y + 0.185, zcentre=cz - 0.010)
        reg.add(reg.make_name("LM", "TurnLens", side), v, f, "Electrical_Lighting",
                p["lamp_amber"],
                meta={"group": "LM", "sub": "Headlamp", "part": "Turn_" + side,
                      "mat_key": "lamp_amber", "notes": "front turn signal lens"})
        # ---- tail lamps ----
        cxt = W(-2.180)
        czt = 0.760
        yt = 0.545 * sy
        for k, (dy, dz, mat, part, note) in enumerate((
                (0.0, 0.075, "lamp_red", "Tail", "tail lamp lens"),
                (0.0, -0.075, "lamp_amber", "TurnRear", "rear turn signal lens"),
                (0.140, -0.045, "lamp_white", "Reverse", "reverse lamp lens"))):
            v, f = _beam_v(cxt - 0.020, 0.190, 0.100, 0.026, ycentre=yt + dy, zcentre=czt + dz)
            reg.add(reg.make_name("LM", part + "Lens", side), v, f,
                    "Electrical_Lighting", p[mat],
                    meta={"group": "LM", "sub": "Taillamp", "part": part + "_" + side,
                          "mat_key": mat, "notes": note})
        v, f = _beam_v(cxt + 0.020, 0.430, 0.320, 0.070, ycentre=yt, zcentre=czt)
        reg.add(reg.make_name("LM", "TaillampHousing", side), v, f,
                "Electrical_Lighting", p["plastic_blk_m"],
                meta={"group": "LM", "sub": "Taillamp", "part": "HousingT_" + side,
                      "mat_key": "plastic_blk_m", "notes": "tail lamp housing"})
        for k in range(2):
            C.prism_poly(C.circle_poly(0.011, 8),
                         (cxt + 0.055, yt + (0.075 if k == 0 else -0.075), czt),
                         (-1, 0, 0), 0.045, "Electrical_Lighting",
                         reg.make_name("LM", "TaillampBulb", side, k + 1), reg,
                         p["lamp_bulb"],
                         meta={"group": "LM", "sub": "Taillamp", "part": "BulbT_" + side,
                               "mat_key": "lamp_bulb", "notes": "tail lamp bulb"})
        # license plate lamps
        for k in range(2):
            C.prism_poly(C.circle_poly(0.012, 8),
                         (W(-2.170), 0.085 * (1 if k == 0 else -1), 0.620),
                         (-1, 0, 0), 0.020, "Electrical_Lighting",
                         reg.make_name("LM", "PlateLamp", side, k + 1), reg,
                         p["lamp_clear"],
                         meta={"group": "LM", "sub": "Plate", "part": "PlateLamp",
                               "mat_key": "lamp_clear", "notes": "license plate lamp"})
    return M


# ---------------------------------------------------------------------------
# 6. mirrors, seals, badges, moldings
# ---------------------------------------------------------------------------


def build_trim(reg, mats, surf, M):
    p = mats
    # ---- mirrors ----
    for side in ("R", "L"):
        s = 1 if side == "L" else -1
        bx, bz = W(0.560), 0.905
        by = (surf.wl(bx, bz) - 0.010) * s
        # base / triangle
        C.prism_poly([(-0.055, -0.045), (0.055, -0.030), (0.050, 0.050), (-0.055, 0.040)],
                     (bx, by, bz), (0, 1, 0), 0.040, "Glass_Mirrors",
                     reg.make_name("MI", "MirrorBase", side), reg, p["plastic_blk_g"],
                     meta={"group": "MI", "sub": side, "part": "MirrorBase_" + side,
                           "mat_key": "plastic_blk_g", "notes": "mirror mounting base"})
        # arm
        C.prism_poly(C.circle_poly(0.016, 8),
                     (bx - 0.030, by + 0.055 * s, bz + 0.010), (0, 1, 0), 0.070,
                     "Glass_Mirrors", reg.make_name("MI", "MirrorArm", side), reg,
                     p["plastic_blk_m"],
                     meta={"group": "MI", "sub": side, "part": "MirrorArm_" + side,
                           "mat_key": "plastic_blk_m", "notes": "mirror arm"})
        # housing shell
        v, f = _beam_v(bx - 0.075, 0.055, 0.145, 0.095,
                       ycentre=by + 0.105 * s, zcentre=bz + 0.020)
        reg.add(reg.make_name("MI", "MirrorHousing", side), v, f, "Glass_Mirrors",
                p["paint_gold"],
                meta={"group": "MI", "sub": side, "part": "MirrorHousing_" + side,
                      "mat_key": "paint_gold", "notes": "mirror housing shell"})
        v, f = _beam_v(bx - 0.126, 0.130, 0.012, 0.088,
                       ycentre=by + 0.105 * s, zcentre=bz + 0.020)
        reg.add(reg.make_name("MI", "MirrorGlass", side), v, f, "Glass_Mirrors",
                p["lamp_reflect"],
                meta={"group": "MI", "sub": side, "part": "MirrorGlass_" + side,
                      "mat_key": "lamp_reflect", "notes": "mirror glass"})
    # ---- interior mirror ----
    v, f = _beam_v(W(0.560), 0.020, 0.024, 0.100, zcentre=1.290)
    reg.add("ALTIMA2000_MIRR_MirrorStem_Interior", v, f, "Glass_Mirrors",
            p["plastic_blk_m"],
            meta={"group": "MI", "sub": "Interior", "part": "MirrorStem",
                  "mat_key": "plastic_blk_m", "notes": "interior mirror stem"})
    v, f = _beam_v(W(0.545), 0.028, 0.078, 0.265, zcentre=1.290)
    reg.add("ALTIMA2000_MIRR_MirrorGlass_Interior", v, f, "Glass_Mirrors",
            p["lamp_reflect"],
            meta={"group": "MI", "sub": "Interior", "part": "MirrorGlassInt",
                  "mat_key": "lamp_reflect", "notes": "interior day/night mirror"})

    # ---- body side moldings ----
    for side in ("R", "L"):
        rows = []
        for i in range(9):
            xd = _lin(X_DR_R_R, X_DR_F_F, 8)[i]
            row = []
            for j in range(3):
                z = 0.700 + 0.030 * j / 2
                y = surf.wl(W(xd), z) - 0.002
                row.append((W(xd), y * (1 if side == "L" else -1), z))
            rows.append(row)
        reg.add_grid(reg.make_name("MD", "SideMolding", "Body_%s" % side),
                     rows, "Trim_Exterior", p["plastic_dk"], 0.006,
                     meta={"group": "MD", "sub": "Side", "part": "SideMolding_" + side,
                           "mat_key": "plastic_dk", "notes": "body side molding"})

    # ---- window seals ----
    for side in ("R", "L"):
        s = 1 if side == "L" else -1
        # windscreen surround
        path = []
        for i in range(6):
            t = i / 5.0
            xd = X_WS_B - 0.005 + (X_WS_T - X_WS_B) * t
            path.append((W(xd), (0.815 * (1 - t) + 0.555 * t) * s, 0.955 + 0.420 * (t ** 0.9)))
        for i in range(1, 5):
            t = i / 5.0
            xd = X_WS_T + (X_ROOF_R - X_WS_T) * t
            path.append((W(xd), 0.545 * s, 1.372))
        reg.add_seal(reg.make_name("SL", "WindshieldSeal", "Side_%s" % side), path,
                     0.012, "Trim_Seals", p["rubber"],
                     meta={"group": "SL", "sub": "Windshield", "part": "WSeal_" + side,
                           "mat_key": "rubber", "notes": "windscreen surround weatherstrip"})
        # door aperture seals (front + rear)
        for dtag, xa, xb in (("F", X_DR_F_F, X_DR_F_R), ("R", X_DR_R_F, X_DR_R_R)):
            path = [(W(xb), (surf.wl(W(xb), 0.960) - 0.004) * s, 0.960)]
            for i in range(4):
                xw = W(xb + 0.090 * (i + 1))
                path.append((xw, (surf.wl(xw, 0.958) - 0.004) * s, 0.958))
            for i in range(3):
                path.append((W(xb + 0.360), (0.560 + 0.020 * i) * s, 0.940 - 0.150 * i))
            path.append((W(xa), (surf.wl(W(xa), 0.955) - 0.006) * s, 0.955))
            reg.add_seal(reg.make_name("SL", "ApertureSeal", dtag + "_%s" % side), path,
                         0.011, "Trim_Seals", p["rubber"],
                         meta={"group": "SL", "sub": dtag, "part": "APSeal_" + dtag + side,
                               "mat_key": "rubber", "notes": "door aperture seal"})
        # roof drip molding
        path = []
        for i in range(6):
            xd = X_WS_T + (X_ROOF_R - X_WS_T) * i / 5.0
            path.append((W(xd), (surf.wl(W(xd), 1.410) - 0.006) * s, 1.410))
        reg.add_seal(reg.make_name("SL", "DripMolding", "Side_%s" % side), path,
                     0.010, "Trim_Exterior", p["plastic_dk"],
                     meta={"group": "MD", "sub": "Drip", "part": "DripMolding_" + side,
                           "mat_key": "plastic_dk", "notes": "roof drip rail molding"})

    # ---- badges ----
    v, f = _beam_v(W(-2.105), 0.230, 0.048, 0.012, ycentre=0.330, zcentre=0.905)
    reg.add("ALTIMA2000_MD_Badge_Trunk_Nissan", v, f, "Trim_Exterior", p["chrome"],
            meta={"group": "MD", "sub": "Badge", "part": "BadgeTrunk",
                  "mat_key": "chrome", "notes": "NISSAN trunk badge"})
    v, f = _beam_v(W(-2.105), 0.180, 0.040, 0.010, ycentre=-0.330, zcentre=0.905)
    reg.add("ALTIMA2000_MD_Badge_Trunk_Altima", v, f, "Trim_Exterior", p["chrome"],
            meta={"group": "MD", "sub": "Badge", "part": "BadgeAltima",
                  "mat_key": "chrome", "notes": "ALTIMA trunk badge"})
    v, f = _beam_v(W(2.055), 0.150, 0.034, 0.010, zcentre=0.985)
    reg.add("ALTIMA2000_MD_Badge_Hood_Nissan", v, f, "Trim_Exterior", p["chrome"],
            meta={"group": "MD", "sub": "Badge", "part": "BadgeHood",
                  "mat_key": "chrome", "notes": "NISSAN hood badge"})
    v, f = _beam_v(W(-0.560), 0.075, 0.026, 0.008, ycentre=-0.790, zcentre=1.070)
    reg.add("ALTIMA2000_MD_Emblem_GXE_Side", v, f, "Trim_Exterior", p["chrome"],
            meta={"group": "MD", "sub": "Badge", "part": "EmblemGXE",
                  "mat_key": "chrome", "notes": "GXE front fender emblem"})
    v, f = _beam_v(W(-0.740), 0.120, 0.022, 0.008, ycentre=0.800, zcentre=1.040)
    reg.add("ALTIMA2000_MD_Emblem_ABS_Side", v, f, "Trim_Exterior", p["chrome"],
            meta={"group": "MD", "sub": "Badge", "part": "EmblemABS",
                  "mat_key": "chrome", "notes": "rear ABS emblem"})
    # washer nozzles
    for side in ("R", "L"):
        C.prism_poly(C.circle_poly(0.012, 8),
                     (W(0.700), 0.340 * (1 if side == "L" else -1), 0.935),
                     (0, 0, 1), 0.016, "Trim_Exterior",
                     reg.make_name("MD", "WasherNozzle", side), reg, p["plastic_blk_m"],
                     meta={"group": "MD", "sub": "Washer", "part": "WasherNozzle_" + side,
                           "mat_key": "plastic_blk_m", "notes": "windshield washer nozzle"})
    # antenna
    C.prism_poly(C.circle_poly(0.008, 8), (W(-0.960), 0.740, 1.030), (0, 0, 1), 0.120,
                 "Electrical_Modules", "ALTIMA2000_EL_Antenna_Power", reg,
                 p["plastic_blk_m"],
                 meta={"group": "EL", "sub": "Audio", "part": "Antenna",
                       "mat_key": "plastic_blk_m", "notes": "power antenna mast"})
    return M
