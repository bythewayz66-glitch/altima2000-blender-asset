"""Interior, electrical harness, and the parametric bulk generator.

``build_bulk`` is the volume driver: it distributes a fixed number of real,
individually named service parts (bolts, clips, hoses, wire runs, relays,
brackets, damping pads) using deterministic, documented placement patterns.
Each instance is a separate selectable object; the mesh data is shared per
template so the file stays small.
"""

import math
import os
from mathutils import Vector
from .. import meshutils as mu
from .. import spec
from . import common as C
from . import templates as T

W = spec.wmap
AXF, AXR = spec.AXLE_F, spec.AXLE_R
TR = spec.TRACK_F * 0.5

#: Global scale applied to every bulk block count so the assembled vehicle
#: lands on the documented ~1000-part target (override with ALTIMA_BULK_SCALE).
#: v4 ships at FULL density (1.0) - the fastener set is generated complete.
BULK_SCALE = float(os.environ.get("ALTIMA_BULK_SCALE", "1.0"))


def place(reg, pos, rot=None, scale=None):
    row = reg.parts[-1]
    ob = row["object"]
    ob.location = pos
    row["offset"] = [round(float(pos[0]), 6), round(float(pos[1]), 6),
                     round(float(pos[2]), 6)]
    info = dict(ob.get("asmb", {}))
    info["loc"] = row["offset"]
    if rot is not None:
        ob.rotation_euler = rot
        row["rotation"] = [round(float(rot[0]), 6), round(float(rot[1]), 6),
                           round(float(rot[2]), 6)]
        info["rot"] = row["rotation"]
    if scale is not None:
        ob.scale = scale
    ob["asmb"] = info
    return ob


def _add(reg, name, vf, coll, mat, grp, sub, part, note="", mat_key=""):
    v, f = vf
    loc = (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v),
           sum(p[2] for p in v) / len(v))
    return reg.add(name, v, f, coll, mat,
                   meta={"group": grp, "sub": sub, "part": part,
                         "mat_key": mat_key, "notes": note}, loc=loc)


# ---------------------------------------------------------------------------
# INTERIOR
# ---------------------------------------------------------------------------

def build_interior(reg, mats, surf, M):
    p = mats
    N = lambda *a: reg.make_name("IN", *a)
    # ---- instrument panel / dash -------------------------------------------
    rows = []
    for i in range(9):
        xd = 0.640 - 0.520 * i / 8.0
        row = []
        for j in range(9):
            t = -1.0 + 2.0 * j / 8.0
            y = 0.760 * t
            z = 0.980 - 0.180 * (i / 8.0) + 0.070 * (1.0 - abs(t) ** 2)
            row.append((W(xd), y, z))
        rows.append(row)
    reg.add_grid(N("Dashboard", "Pad"), rows, "Interior_Dash", p["vinyl_dash"], 0.012,
                 meta={"group": "IN", "sub": "Dash", "part": "Dashboard",
                       "mat_key": "vinyl_dash", "notes": "instrument panel pad"})
    reg.add_grid(N("Dashboard", "Substrate"),
                 mu.offset_grid(rows, 0.060), "Interior_Dash", p["plastic_dk"], 0.010,
                 meta={"group": "IN", "sub": "Dash", "part": "DashSub",
                       "mat_key": "plastic_dk", "notes": "instrument panel substrate"})
    _add(reg, N("Dash", "Reinforcement"), T.tube_template(1.320, 0.026, 0.020, 10, "Y"),
         "Interior_Dash", p["steel"], "IN", "Dash", "DashBeam",
         "instrument panel reinforcement beam", "steel")
    place(reg, (W(0.430), 0.0, 0.880))
    _add(reg, N("KneeBolster", "Driver"), T.box_vf((0.140, 0.420, 0.130),
                                                    (W(0.200), -0.470, 0.700)),
         "Interior_Dash", p["plastic_dk"], "IN", "Dash", "KneeBolster",
         "driver knee bolster", "plastic_dk")
    _add(reg, N("GloveBox", "Assembly"), T.box_vf((0.190, 0.440, 0.180),
                                                  (W(0.180), 0.420, 0.720)),
         "Interior_Dash", p["plastic_dk"], "IN", "Dash", "GloveBox",
         "glove box assembly", "plastic_dk")
    _add(reg, N("GloveBox", "Latch"), T.box_vf((0.030, 0.070, 0.030),
                                               (W(0.100), 0.420, 0.800)),
         "Interior_Dash", p["plastic_blk_m"], "IN", "Dash", "GloveLatch",
         "glove box latch", "plastic_blk_m")
    _add(reg, N("CentreVent", "Bezel"), T.box_vf((0.070, 0.420, 0.110),
                                                 (W(0.520), 0.0, 0.870)),
         "Interior_Dash", p["plastic_dk"], "IN", "Dash", "CentreVent",
         "centre air vent bezel", "plastic_dk")
    for k in range(4):
        _add(reg, N("Vent", "Louver", k + 1),
             T.box_vf((0.024, 0.070, 0.085),
                      (W(0.540), -0.300 + 0.200 * k, 0.870)),
             "Interior_Dash", p["plastic_blk_m"], "IN", "Dash", "VentLouver",
             "air vent louver", "plastic_blk_m")
    # ---- instrument cluster ------------------------------------------------
    _add(reg, N("Cluster", "Housing"), T.box_vf((0.130, 0.400, 0.165),
                                                (W(0.430), -0.360, 0.940)),
         "Interior_Dash", p["plastic_dk"], "IN", "Cluster", "ClusterHousing",
         "instrument cluster housing", "plastic_dk")
    _add(reg, N("Cluster", "Face"), T.box_vf((0.008, 0.380, 0.155),
                                             (W(0.375), -0.360, 0.940)),
         "Interior_Dash", p["gauge_face"], "IN", "Cluster", "ClusterFace",
         "instrument cluster face", "gauge_face")
    for k, (dy, r) in enumerate(((-0.130, 0.058), (0.0, 0.050), (0.130, 0.046))):
        C.prism_poly(C.circle_poly(r, 16), (W(0.370), -0.360 + dy, 0.940),
                     (1, 0, 0), 0.004, "Interior_Dash",
                     N("Cluster", "Gauge", k + 1), reg, p["label_white"],
                     meta={"group": "IN", "sub": "Cluster", "part": "Gauge",
                           "mat_key": "label_white", "notes": "gauge face"})
        C.prism_poly([(0.040, -0.004), (-0.020, -0.004), (-0.020, 0.004), (0.040, 0.004)],
                     (W(0.368), -0.360 + dy, 0.940), (1, 0, 0), 0.002,
                     "Interior_Dash", N("Cluster", "Needle", k + 1), reg,
                     p["gauge_needle"],
                     meta={"group": "IN", "sub": "Cluster", "part": "Needle",
                           "mat_key": "gauge_needle", "notes": "gauge needle"})
    _add(reg, N("Cluster", "Lens"), T.box_vf((0.006, 0.390, 0.160),
                                             (W(0.362), -0.360, 0.940)),
         "Interior_Dash", p["glass_clear"], "IN", "Cluster", "ClusterLens",
         "instrument cluster lens", "glass_clear")
    # ---- centre console ----------------------------------------------------
    _add(reg, N("Console", "Body"), T.box_vf((0.520, 0.280, 0.240),
                                             (W(0.030), -0.020, 0.420)),
         "Interior_Console", p["plastic_dk"], "IN", "Console", "ConsoleBody",
         "centre console body", "plastic_dk")
    _add(reg, N("Console", "Lid"), T.box_vf((0.240, 0.250, 0.040),
                                            (W(-0.130), -0.020, 0.550)),
         "Interior_Console", p["seat_leather"], "IN", "Console", "ConsoleLid",
         "console armrest lid", "seat_leather")
    _add(reg, N("Console", "ShiftBezel"), T.box_vf((0.170, 0.240, 0.030),
                                                   (W(0.230), -0.020, 0.545)),
         "Interior_Console", p["abs_wood"], "IN", "Console", "ShiftBezel",
         "gear selector bezel", "abs_wood")
    _add(reg, N("Shift", "Lever"), T.cyl_template(0.011, 0.230, 10, "Z"),
         "Interior_Console", p["steel"], "IN", "Console", "ShiftLever",
         "gear selector lever", "steel")
    place(reg, (W(0.230), -0.020, 0.620), rot=(0.26, 0.0, 0.0))
    _add(reg, N("Shift", "Knob"), T.cyl_template(0.026, 0.060, 12, "Z"),
         "Interior_Console", p["plastic_blk_g"], "IN", "Console", "ShiftKnob",
         "gear selector knob", "plastic_blk_g")
    place(reg, (W(0.180), -0.020, 0.730))
    _add(reg, N("ParkingBrake", "Boot"), T.cyl_template(0.030, 0.100, 10, "Z"),
         "Interior_Console", p["seat_leather"], "IN", "Console", "ParkBoot",
         "parking brake lever boot", "seat_leather")
    place(reg, (W(0.020), -0.160, 0.470))
    _add(reg, N("CupHolder", "Insert"), T.box_vf((0.150, 0.220, 0.080),
                                                 (W(-0.060), -0.020, 0.480)),
         "Interior_Console", p["plastic_dk"], "IN", "Console", "CupHolder",
         "cupholder insert", "plastic_dk")
    # ---- seats -------------------------------------------------------------
    for (tag, sx, sy) in (("FL", 0.320, 0.380), ("FR", 0.320, -0.380),
                          ("RL", -0.980, 0.400), ("RR", -0.980, -0.400)):
        sub = "Seats"
        # cushion
        _add(reg, N("Seat", "Cushion_%s" % tag),
             T.box_vf((0.440 if tag[0] == "F" else 0.430, 0.480, 0.110),
                      (W(sx), sy, 0.470)),
             "Interior_Seats", p["fabric_grey"], "ST", sub, "Cushion_" + tag,
             "seat cushion", "fabric_grey")
        _add(reg, N("Seat", "Back_%s" % tag),
             T.box_vf((0.130, 0.470, 0.590), (W(sx - 0.300), sy, 0.740)),
             "Interior_Seats", p["fabric_grey"], "ST", sub, "Back_" + tag,
             "seat back", "fabric_grey")
        _add(reg, N("Seat", "Headrest_%s" % tag),
             T.box_vf((0.110, 0.270, 0.170), (W(sx - 0.330), sy, 1.120)),
             "Interior_Seats", p["fabric_grey"], "ST", sub, "Headrest_" + tag,
             "seat head restraint", "fabric_grey")
        _add(reg, N("Seat", "Frame_%s" % tag),
             T.box_vf((0.480, 0.470, 0.070), (W(sx - 0.030), sy, 0.395)),
             "Interior_Seats", p["steel"], "ST", sub, "Frame_" + tag,
             "seat frame", "steel")
        for k in range(4):
            dy = 0.190 * (1 if k % 2 else -1)
            dx = 0.170 * (1 if k < 2 else -1)
            _add(reg, N("Seat", "Rail_%s_%02d" % (tag, k + 1)),
                 T.box_vf((0.400, 0.045, 0.045), (W(sx - 0.030 + dx * 0.5), sy + dy, 0.350)),
                 "Interior_Seats", p["steel"], "ST", sub, "Rail_" + tag,
                 "seat adjustment rail", "steel")
        if tag[0] == "F":
            _add(reg, N("Seat", "Recliner_%s" % tag),
                 T.cyl_template(0.028, 0.040, 10, "Y"),
                 "Interior_Seats", p["plastic_dk"], "ST", sub, "Recliner_" + tag,
                 "recliner mechanism knob", "plastic_dk")
            place(reg, (W(sx - 0.300), sy + 0.250, 0.560))
    # rear bench base
    _add(reg, N("Seat", "BenchBase_Rear"),
         T.box_vf((0.430, 1.040, 0.110), (W(-0.980), 0.0, 0.470)),
         "Interior_Seats", p["fabric_grey"], "ST", "Seats", "BenchBase",
         "rear seat bench cushion", "fabric_grey")
    # ---- interior trim -----------------------------------------------------
    rows = []
    for i in range(7):
        z = 1.360 - 0.060 * i
        row = []
        for j in range(9):
            y = -0.720 + 1.440 * j / 8.0
            row.append((W(0.020 - 0.100 * i), y, z - 0.004 * abs(j - 4)))
        rows.append(row)
    reg.add_grid(N("Headliner", "Roof"), rows, "Interior_Trim", p["headliner"], 0.008,
                 meta={"group": "IN", "sub": "Headliner", "part": "Headliner",
                       "mat_key": "headliner", "notes": "roof headliner"})
    for side in ("R", "L"):
        s = 1 if side == "L" else -1
        rows = []
        for i in range(6):
            xd = 0.600 - 0.760 * i / 5.0
            row = []
            for j in range(4):
                z = 0.396 - 0.088 * j
                row.append((W(xd), s * (0.740 - 0.006 * j), z))
            rows.append(row)
        reg.add_grid(N("Carpet", "Floor_%s" % side), rows, "Interior_Trim",
                     p["carpet"], 0.007,
                     meta={"group": "IN", "sub": "Carpet", "part": "Carpet_" + side,
                           "mat_key": "carpet", "notes": "floor carpet"})
        # A / B / C pillar trims
        for k, (tag2, xd, z0, z1) in enumerate((
                ("A", 0.520, 1.000, 1.340), ("B", -0.300, 0.990, 1.390),
                ("C", -1.180, 0.980, 1.330))):
            rows = []
            for i in range(3):
                row = []
                for j in range(3):
                    z = z0 + (z1 - z0) * j / 2
                    row.append((W(xd + 0.045 * (i - 1)), s * (0.760 - 0.030 * j), z))
                rows.append(row)
            reg.add_grid(N("PillarTrim", "%s_%s" % (tag2, side)), rows,
                         "Interior_Trim", p["plastic_light"], 0.006,
                         meta={"group": "IN", "sub": "Pillar", "part": "Pillar" + tag2 + "_" + side,
                               "mat_key": "plastic_light", "notes": "pillar trim"})
        # door sill scuff plate
        _add(reg, N("SillPlate", "Scuff_%s" % side),
             T.box_vf((0.760, 0.070, 0.020), (W(0.020), s * 0.730, 0.395)),
             "Interior_Trim", p["plastic_light"], "IN", "Sill", "Scuff_" + side,
             "door sill scuff plate", "plastic_light")
    # sun visors + dome lamp + mirrors
    for side in ("R", "L"):
        s = 1 if side == "L" else -1
        v, f = T.box_vf((0.380, 0.150, 0.012), (W(0.360), s * 0.330, 1.310))
        reg.add(N("SunVisor", "Assembly_%s" % side), v, f, "Interior_Trim",
                p["headliner"], meta={"group": "IN", "sub": "Visor", "part": "SunVisor_" + side,
                                      "mat_key": "headliner", "notes": "sun visor"},
                loc=(W(0.360), s * 0.330, 1.310))
        _add(reg, N("GrabHandle", "Roof_%s" % side),
             T.cyl_template(0.014, 0.200, 10, "Y"), "Interior_Trim",
             p["plastic_light"], "IN", "Visor", "GrabHandle_" + side,
             "roof grab handle", "plastic_light")
        place(reg, (W(-0.100), s * 0.680, 1.290))
    # floor mats
    for side in ("R", "L"):
        s = 1 if side == "L" else -1
        _add(reg, N("FloorMat", "Carpet_%s" % side),
             T.box_vf((0.520, 0.380, 0.014), (W(0.300), s * 0.380, 0.400)),
             "Interior_Trim", p["carpet"], "IN", "Carpet", "FloorMat_" + side,
             "floor mat", "carpet")
    return M


# ---------------------------------------------------------------------------
# ELECTRICAL
# ---------------------------------------------------------------------------

def build_electrical(reg, mats, surf, M):
    p = mats
    N = lambda *a: reg.make_name("EL", *a)
    # ---- battery -----------------------------------------------------------
    _add(reg, N("Battery", "Case"), T.box_vf((0.200, 0.260, 0.180),
                                             (W(1.860), 0.360, 0.700)),
         "Electrical_Battery", p["battery_case"], "BA", "Battery", "Case",
         "battery case (Group 24F)", "battery_case")
    _add(reg, N("Battery", "NegativeTerminal"), T.cyl_template(0.011, 0.030, 10, "Z"),
         "Electrical_Battery", p["battery_post"], "BA", "Battery", "NegTerminal",
         "battery negative terminal", "battery_post")
    place(reg, (W(1.760), 0.470, 0.805))
    _add(reg, N("Battery", "PositiveTerminal"), T.cyl_template(0.013, 0.030, 10, "Z"),
         "Electrical_Battery", p["battery_post"], "BA", "Battery", "PosTerminal",
         "battery positive terminal", "battery_post")
    place(reg, (W(1.760), 0.250, 0.805))
    _add(reg, N("Battery", "HoldDown"), T.box_vf((0.240, 0.030, 0.050),
                                                 (W(1.860), 0.360, 0.800)),
         "Electrical_Battery", p["steel"], "BA", "Battery", "HoldDown",
         "battery hold-down clamp", "steel")
    _add(reg, N("Battery", "Tray"), T.box_vf((0.240, 0.300, 0.020),
                                             (W(1.860), 0.360, 0.600)),
         "Electrical_Battery", p["plastic_blk_m"], "BA", "Battery", "Tray",
         "battery tray", "plastic_blk_m")
    # ---- main harness ------------------------------------------------------
    harness = [
        (("Engine", "Main"), [(W(2.20), 0.44, 0.86), (W(1.80), 0.40, 0.80),
                              (W(1.20), 0.30, 0.74), (W(0.70), 0.10, 0.72)]),
        (("Dash", "Instrument"), [(W(0.68), -0.10, 0.72), (W(0.40), -0.40, 0.80),
                                  (W(0.10), -0.42, 0.66)]),
        (("Cabin", "Floor"), [(W(0.30), -0.44, 0.62), (W(-0.60), -0.60, 0.42),
                              (W(-1.60), -0.50, 0.42)]),
        (("Body", "Rear"), [(W(-1.60), -0.50, 0.42), (W(-2.10), -0.20, 0.60),
                            (W(-2.16), 0.30, 0.72)]),
        (("Door", "FrontLeft"), [(W(0.55), 0.72, 0.70), (W(0.10), 0.74, 0.62),
                                 (W(-0.18), 0.72, 0.56)]),
        (("Door", "FrontRight"), [(W(0.55), -0.72, 0.70), (W(0.10), -0.74, 0.62),
                                  (W(-0.18), -0.72, 0.56)]),
        (("Door", "RearLeft"), [(W(-0.34), 0.72, 0.56), (W(-0.62), 0.72, 0.50),
                                (W(-0.84), 0.70, 0.46)]),
        (("Door", "RearRight"), [(W(-0.34), -0.72, 0.56), (W(-0.62), -0.72, 0.50),
                                 (W(-0.84), -0.70, 0.46)]),
        (("Roof", "Headliner"), [(W(0.30), 0.66, 1.34), (W(-0.30), 0.68, 1.36),
                                 (W(-0.90), 0.60, 1.30)]),
    ]
    n = 0
    for (sub, path) in harness:
        sub = sub[0] if isinstance(sub, tuple) else sub
        for k in range(5):
            a = path[k % len(path)]
            b = path[min(k % len(path) + 1, len(path) - 1)]
            if a == b:
                b = (a[0] - 0.12, a[1], a[2])
            for sgn in (1, -1):
                n += 1
                reg.add_seal(N("Harness", "Segment_%03d" % n),
                             [a, ((a[0] + b[0]) / 2 + 0.02 * sgn, (a[1] + b[1]) / 2,
                                  (a[2] + b[2]) / 2), b],
                             0.0060, "Electrical_Harness",
                             p["wire_blk"] if sgn > 0 else p["wire_red"],
                             meta={"group": "EL", "sub": "Harness_" + sub,
                                   "part": "Harness",
                                   "mat_key": "wire_blk",
                                   "notes": "wiring harness segment (%s)" % sub})
    for k in range(14):
        sub = ("Engine", "Dash", "Cabin", "Body", "Door", "Roof")[k % 6]
        reg.add_seal(N("Conduit", "Loom_%03d" % (k + 1)),
                     [(W(1.9 - 0.30 * k), -0.40 + 0.08 * (k % 5), 0.80 - 0.02 * (k % 4)),
                      (W(1.6 - 0.30 * k), -0.36 + 0.08 * (k % 5), 0.76 - 0.02 * (k % 4))],
                     0.0090, "Electrical_Harness", p["plastic_blk_m"],
                     meta={"group": "EL", "sub": "Harness", "part": "Conduit",
                           "mat_key": "plastic_blk_m", "notes": "corrugated wire loom conduit"})
    # connectors
    for k in range(18):
        _add(reg, N("Connector", "Pair_%03d" % (k + 1)),
             T.box_vf((0.030, 0.020, 0.016),
                      (W(1.80 - 0.22 * k), -0.30 + 0.10 * (k % 4), 0.70 - 0.03 * (k % 3))),
             "Electrical_Harness", p["connector"], "EL", "Harness", "Connector",
             "multi-pin electrical connector", "connector")
    # ---- modules -----------------------------------------------------------
    _add(reg, N("ECU", "EngineControl"), T.box_vf((0.180, 0.140, 0.040),
                                                  (W(0.520), -0.420, 0.840)),
         "Electrical_Modules", p["aluminium"], "EL", "Modules", "ECU",
         "engine control module (ECM)", "aluminium")
    _add(reg, N("TCU", "Transmission"), T.box_vf((0.150, 0.120, 0.035),
                                                 (W(0.540), -0.100, 0.780)),
         "Electrical_Modules", p["aluminium"], "EL", "Modules", "TCU",
         "transmission control module", "aluminium")
    _add(reg, N("Module", "BodyControl"), T.box_vf((0.120, 0.100, 0.035),
                                                    (W(0.240), 0.420, 0.740)),
         "Electrical_Modules", p["plastic_blk_m"], "EL", "Modules", "BCM",
         "body control module", "plastic_blk_m")
    _add(reg, N("Module", "ABS"), T.box_vf((0.130, 0.110, 0.100),
                                            (W(1.950), 0.240, 0.880)),
         "Electrical_Modules", p["aluminium"], "EL", "Modules", "ABSModule",
         "ABS control module", "aluminium")
    _add(reg, N("Fuse", "BoxEngine"), T.box_vf((0.200, 0.150, 0.080),
                                               (W(2.000), 0.340, 0.860)),
         "Electrical_Modules", p["plastic_blk_m"], "EL", "Modules", "FuseBoxEng",
         "engine compartment fuse box", "plastic_blk_m")
    _add(reg, N("Fuse", "BoxInterior"), T.box_vf((0.180, 0.130, 0.060),
                                                 (W(0.500), -0.460, 0.700)),
         "Electrical_Modules", p["plastic_blk_m"], "EL", "Modules", "FuseBoxInt",
         "interior fuse box", "plastic_blk_m")
    for k in range(18):
        C.prism_poly([(-0.007, -0.009), (0.007, -0.009), (0.007, 0.009), (-0.007, 0.009)],
                     (W(2.000), 0.300 + 0.030 * (k % 5), 0.880 - 0.024 * (k // 5)),
                     (0, 0, 1), 0.022, "Electrical_Modules",
                     N("Fuse", "Blade_%03d" % (k + 1)), reg, p["wire_red"],
                     meta={"group": "EL", "sub": "Modules", "part": "Fuse",
                           "mat_key": "wire_red", "notes": "blade fuse"})
    for k in range(10):
        _add(reg, N("Relay", "Box_%03d" % (k + 1)),
             T.box_vf((0.028, 0.028, 0.028),
                      (W(2.020), 0.280 + 0.030 * (k % 4), 0.940 - 0.032 * (k // 4))),
             "Electrical_Modules", p["plastic_blk_m"], "EL", "Modules", "Relay",
             "electrical relay", "plastic_blk_m")
    # alternator lead, grounds, speakers, switches
    reg.add_seal(N("Alternator", "Lead"), [(W(1.120), -0.235, 0.405),
                                          (W(1.600), 0.200, 0.740),
                                          (W(1.820), 0.400, 0.860)],
                 0.0065, "Electrical_Harness", p["wire_red"],
                 meta={"group": "EL", "sub": "Harness", "part": "AltLead",
                       "mat_key": "wire_red", "notes": "alternator output cable"})
    for k in range(6):
        reg.add_seal(N("Ground", "Strap_%03d" % (k + 1)),
                     [(W(1.60 - 0.55 * k), -0.30 + 0.14 * (k % 3), 0.62),
                      (W(1.56 - 0.55 * k), -0.28 + 0.14 * (k % 3), 0.44)],
                     0.0050, "Electrical_Harness", p["wire_blk"],
                     meta={"group": "EL", "sub": "Harness", "part": "Ground",
                           "mat_key": "wire_blk", "notes": "ground strap"})
    for k, (xd, yy, r) in enumerate(((0.480, 0.640, 0.065), (0.480, -0.640, 0.065),
                                     (-0.560, 0.640, 0.042), (-0.560, -0.640, 0.042),
                                     (-1.360, 0.520, 0.080), (-1.360, -0.520, 0.080))):
        sub = "Audio"
        C.prism_poly(C.circle_poly(r, 12), (W(xd), yy, 0.860 if k < 2 else 0.520),
                     (0, 1, 0), 0.030, "Electrical_Modules",
                     N("Speaker", "%s_%02d" % ("Door" if k < 4 else "Rear", k + 1)), reg,
                     p["plastic_blk_m"],
                     meta={"group": "EL", "sub": sub, "part": "Speaker",
                           "mat_key": "plastic_blk_m", "notes": "audio speaker"})
    for k, (nm, xd, yy, zz) in enumerate((
            ("Headlamp", 0.600, -0.360, 0.945), ("Wiper", 0.640, -0.200, 0.930),
            ("Hazard", 0.640, 0.0, 0.945), ("Ignition", 0.700, -0.360, 0.700),
            ("WindowFL", 0.560, 0.560, 0.560), ("WindowFR", 0.560, -0.560, 0.560),
            ("Mirror", 0.600, -0.420, 0.700), ("Dimmer", 0.660, -0.180, 0.930),
            ("WiperIntermittent", 0.680, -0.140, 0.940), ("Defog", 0.560, 0.200, 0.690))):
        _add(reg, N("Switch", nm), T.box_vf((0.024, 0.028, 0.026), (W(xd), yy, zz)),
             "Electrical_Modules", p["plastic_blk_m"], "EL", "Switches", "Switch",
             "electrical switch - %s" % nm, "plastic_blk_m")
    for k, (nm, yy) in enumerate((("Dome", 0.0), ("MapFL", 0.240), ("MapFR", -0.240))):
        _add(reg, N("Lamp", "%s_Interior" % nm),
             T.cyl_template(0.026, 0.014, 12, "Z"), "Electrical_Lighting",
             p["lamp_clear"], "LM", "Interior", "Lamp_" + nm,
             "interior lamp - %s" % nm, "lamp_clear")
        place(reg, (W(-0.120), yy, 1.330))
    _add(reg, N("Horn", "Disc"), T.cyl_template(0.045, 0.032, 14, "X"),
         "Electrical_Modules", p["plastic_blk_m"], "EL", "Modules", "Horn",
         "horn (high note)", "plastic_blk_m")
    place(reg, (W(2.300), 0.330, 0.740), rot=(0.0, math.pi / 2, 0.0))
    _add(reg, N("Horn", "DiscLow"), T.cyl_template(0.045, 0.032, 14, "X"),
         "Electrical_Modules", p["plastic_blk_m"], "EL", "Modules", "HornLow",
         "horn (low note)", "plastic_blk_m")
    place(reg, (W(2.300), 0.430, 0.740), rot=(0.0, math.pi / 2, 0.0))
    # wiper system
    _add(reg, N("Wiper", "Motor"), T.cyl_template(0.032, 0.090, 12, "X"),
         "Electrical_Modules", p["steel"], "EL", "Modules", "WiperMotor",
         "windshield wiper motor", "steel")
    place(reg, (W(0.560), -0.180, 0.860))
    _add(reg, N("Wiper", "Linkage"), T.cyl_template(0.008, 0.760, 8, "Y"),
         "Electrical_Modules", p["steel"], "EL", "Modules", "WiperLinkage",
         "wiper linkage", "steel")
    place(reg, (W(0.560), 0.050, 0.870))
    for k in range(2):
        _add(reg, N("Wiper", "Arm_%02d" % (k + 1)),
             T.box_vf((0.560, 0.014, 0.014), (W(0.240), 0.340 - 0.680 * k, 0.960)),
             "Electrical_Modules", p["plastic_blk_m"], "EL", "Modules", "WiperArm",
             "wiper arm", "plastic_blk_m")
        _add(reg, N("Wiper", "Blade_%02d" % (k + 1)),
             T.box_vf((0.520, 0.022, 0.010), (W(0.180), 0.340 - 0.680 * k, 0.945)),
             "Electrical_Modules", p["rubber"], "EL", "Modules", "WiperBlade",
             "wiper blade", "rubber")
    # safety systems
    for k in range(2):
        _add(reg, N("Airbag", "Module_%02d" % (k + 1)),
             T.box_vf((0.150, 0.260, 0.100),
                      (W(0.400 - 0.250 * k), -0.360 if k == 0 else 0.360, 0.760)),
             "Safety", p["plastic_blk_m"], "SF", "Airbag", "AirbagModule",
             "airbag module", "plastic_blk_m")
    _add(reg, N("Seatbelt", "Pretensioner_Left"), T.cyl_template(0.024, 0.110, 10, "Z"),
         "Safety", p["steel"], "SF", "Belt", "Pretensioner",
         "seat belt pretensioner", "steel")
    place(reg, (W(-0.260), 0.660, 0.900))
    _add(reg, N("Seatbelt", "Pretensioner_Right"), T.cyl_template(0.024, 0.110, 10, "Z"),
         "Safety", p["steel"], "SF", "Belt", "Pretensioner",
         "seat belt pretensioner", "steel")
    place(reg, (W(-0.260), -0.660, 0.900))
    return M


# ---------------------------------------------------------------------------
# BULK: fasteners, clips, hoses, wiring, damping - the part-count volume driver
# ---------------------------------------------------------------------------

# (sub-collection, group code, tag, detail, count, size, note)
BOLT_BLOCKS = [
    ("Engine_LongBlock", "EN", "HexBolt", "OilPan", 18, "M6",
     "oil pan bolt (M6 x 20)"),
    ("Engine_LongBlock", "EN", "HexBolt", "TimingCover", 12, "M6",
     "timing cover bolt (M6 x 25)"),
    ("Engine_LongBlock", "EN", "HexBolt", "Crankcase", 10, "M8",
     "main bearing cap bolt (M8)"),
    ("Engine_Head", "EN", "HexBolt", "CylinderHead", 10, "M10",
     "cylinder head bolt (M10, torque-to-yield)"),
    ("Engine_Head", "EN", "HexBolt", "CamCap", 10, "M6",
     "camshaft bearing cap bolt (M6)"),
    ("Engine_Head", "EN", "HexBolt", "IntakeManifold", 8, "M8",
     "intake manifold bolt (M8)"),
    ("Engine_ExhaustSide", "EX", "Stud", "Manifold", 8, "M10",
     "exhaust manifold stud (M10)"),
    ("Engine_Cooling", "EN", "HexBolt", "WaterPump", 6, "M6",
     "water pump bolt (M6)"),
    ("Engine_Fuel", "EN", "HexBolt", "Injector", 4, "M5",
     "fuel injector retainer bolt (M5)"),
    ("Engine_Accessory", "EN", "HexBolt", "Alternator", 3, "M8",
     "alternator mounting bolt (M8)"),
    ("Engine_Accessory", "EN", "HexBolt", "Compressor", 4, "M8",
     "A/C compressor bolt (M8)"),
    ("Engine_Accessory", "EN", "HexBolt", "BeltTensioner", 3, "M8",
     "belt tensioner bolt (M8)"),
    ("Drivetrain_Transaxle", "TR", "HexBolt", "Bellhousing", 8, "M12",
     "transaxle bellhousing bolt (M12)"),
    ("Drivetrain_Transaxle", "TR", "HexBolt", "ValveBody", 10, "M6",
     "valve body bolt (M6)"),
    ("Drivetrain_Transaxle", "TR", "HexBolt", "OilPanTransaxle", 12, "M6",
     "transaxle oil pan bolt (M6)"),
    ("Drivetrain_Mount", "TR", "HexBolt", "EngineMount", 8, "M10",
     "engine mount bolt (M10)"),
    ("Drivetrain_Mount", "TR", "HexBolt", "TransMount", 6, "M10",
     "transaxle mount bolt (M10)"),
    ("Drivetrain_Drive", "TR", "HexBolt", "CVJoint", 12, "M8",
     "CV joint flange bolt (M8)"),
    ("Suspension_Front", "SU", "HexBolt", "StrutMount", 6, "M10",
     "strut upper mount nut/bolt (M10)"),
    ("Suspension_Front", "SU", "HexBolt", "StrutClamp", 4, "M12",
     "strut to knuckle clamp bolt (M12)"),
    ("Suspension_Front", "SU", "HexBolt", "BallJoint", 6, "M10",
     "ball joint bolt (M10)"),
    ("Suspension_Front", "SU", "HexBolt", "ControlArm", 4, "M12",
     "lower control arm pivot bolt (M12)"),
    ("Suspension_Front", "SU", "HexBolt", "SwayBar", 6, "M8",
     "stabiliser bar bracket bolt (M8)"),
    ("Suspension_Rear", "SU", "HexBolt", "BeamAxle", 10, "M12",
     "rear beam axle bolt (M12)"),
    ("Suspension_Rear", "SU", "HexBolt", "TrailingArm", 8, "M10",
     "trailing arm bolt (M10)"),
    ("Suspension_Steering", "SR", "HexBolt", "SteeringRack", 4, "M10",
     "steering rack bolt (M10)"),
    ("Suspension_Steering", "SR", "HexBolt", "Column", 4, "M8",
     "steering column bolt (M8)"),
    ("Brakes_Front", "BR", "HexBolt", "Caliper", 8, "M14",
     "front caliper mounting bolt (M14)"),
    ("Brakes_Rear", "BR", "HexBolt", "CaliperRear", 8, "M12",
     "rear caliper mounting bolt (M12)"),
    ("Brakes_Hydraulics", "BR", "HexBolt", "MasterCylinder", 4, "M8",
     "master cylinder nut (M8)"),
    ("Brakes_Hydraulics", "BR", "HexBolt", "Booster", 4, "M8",
     "brake booster nut (M8)"),
    ("Body_Panels", "BD", "HexBolt", "Fender", 20, "M6",
     "fender / bolt-on panel bolt (M6)"),
    ("Body_Panels", "BD", "HexBolt", "HoodHinge", 8, "M8",
     "hood hinge bolt (M8)"),
    ("Body_Panels", "BD", "HexBolt", "TrunkHinge", 8, "M8",
     "trunk hinge bolt (M8)"),
    ("Body_Panels", "BD", "HexBolt", "BumperFront", 10, "M8",
     "front bumper fastener (M8)"),
    ("Body_Panels", "BD", "HexBolt", "BumperRear", 10, "M8",
     "rear bumper fastener (M8)"),
    ("Body_Panels", "BD", "HexBolt", "Bracket", 22, "M6",
     "general body bracket bolt (M6)"),
    ("Body_Structure", "SH", "HexBolt", "Subframe", 24, "M12",
     "front crossmember / subframe bolt (M12)"),
    ("Body_Structure", "SH", "HexBolt", "SeatRiser", 16, "M10",
     "seat riser to floor bolt (M10)"),
    ("Body_Structure", "SH", "HexBolt", "SeatBelt", 12, "M11",
     "seat belt anchor bolt (M11)"),
    ("Interior_Dash", "IN", "HexBolt", "DashBeam", 8, "M8",
     "instrument panel beam bolt (M8)"),
    ("Interior_Console", "IN", "HexBolt", "Console", 6, "M6",
     "console mounting screw (M6)"),
    ("Electrical_Harness", "EL", "HexBolt", "Ground", 10, "M6",
     "ground strap bolt (M6)"),
    ("Electrical_Battery", "BA", "HexBolt", "Terminal", 4, "M6",
     "battery terminal bolt (M6)"),
    ("Fasteners_Bolts", "FT", "HexBolt", "BodyMisc", 40, "M6",
     "body hardware bolt (M6)"),
    ("Fasteners_Bolts", "FT", "HexBolt", "TrimMisc", 40, "M5",
     "trim fastener bolt (M5)"),
]

NUT_BLOCKS = [
    ("Fasteners_Nuts", "FT", "HexNut", "BodyPanel", 12, "M6", "body panel nut (M6)"),
    ("Fasteners_Nuts", "FT", "HexNut", "HeadStud", 8, "M10", "exhaust stud nut (M10)"),
    ("Fasteners_Nuts", "FT", "HexNut", "StrutTop", 6, "M10", "strut top nut (M10)"),
    ("Suspension_Front", "SU", "HexNut", "BallJointCastle", 4, "M10",
     "ball joint castle nut (M10)"),
    ("Suspension_Steering", "SR", "HexNut", "TieRod", 4, "M12", "tie rod end nut (M12)"),
    ("Wheels", "WH", "HexNut", "SpindleNut", 4, "M14", "front spindle nut (M14)"),
]

CLIP_BLOCKS = [
    ("Fasteners_Clips", "CL", "TrimClip", "Door", 24, "", "door trim panel push clip"),
    ("Fasteners_Clips", "CL", "TrimClip", "Bumper", 20, "", "bumper cover push clip"),
    ("Fasteners_Clips", "CL", "TrimClip", "WheelArch", 16, "", "wheel arch liner clip"),
    ("Fasteners_Clips", "CL", "TrimClip", "Underbody", 18, "", "underbody shield clip"),
    ("Fasteners_Clips", "CL", "TrimClip", "Headliner", 14, "", "headliner retaining clip"),
    ("Fasteners_Clips", "CL", "TrimClip", "Carpet", 12, "", "carpet retaining clip"),
    ("Fasteners_Clips", "CL", "HoseClamp", "Coolant", 8, "", "spring hose clamp"),
    ("Fasteners_Clips", "CL", "HoseClamp", "Fuel", 6, "", "fuel line spring clamp"),
    ("Fasteners_Clips", "CL", "Retainer", "Harness", 20, "", "wire harness retainer"),
    ("Fasteners_Clips", "CL", "Retainer", "BrakeLine", 10, "", "brake line retaining clip"),
]

# NOTE: the legacy HOSE_BLOCKS straight-tube population was removed in v4.
# It is superseded by the real routed hoses in altima/parts/hoses.py, which
# model every hose as a swept tube along its actual run (Catmull-Rom smoothed,
# split into removable segments) with a baked trace coordinate, plus the tie
# straps that secure it.  Keeping both would double-count the hose system.

WIRE_BLOCKS = [
    # NOTE: the two legacy "Wire" bulk blocks (16 power + 16 signal straight
    # runs) were removed in v3.  They are superseded by the real routed wiring
    # in altima/parts/wiring.py, which models every wire as a swept tube along
    # its actual route with a baked trace coordinate.
    ("Electrical_Modules", "EL", "Bracket", "Module", 12, "", "module mounting bracket"),
    ("Interior_Insulation", "IN", "Damper", "Floor", 14, "", "sound deadening pad"),
    ("Interior_Insulation", "IN", "Damper", "Door", 8, "", "door sound deadening pad"),
    ("Body_Structure", "SH", "Brace", "Gusset", 10, "", "body gusset brace"),
    ("Body_Structure", "SH", "Rib", "Floor", 12, "", "floor pan reinforcement rib"),
    ("Fasteners_Bolts", "FT", "Washer", "Flat", 40, "", "flat washer"),
]


def build_bulk(reg, mats, surf, M):
    p = mats
    tpl = {
        "M5": reg.template("TPL_Bolt_M5", *T.bolt_template("M5"), mat=p["steel_phos"]),
        "M6": reg.template("TPL_Bolt_M6", *T.bolt_template("M6"), mat=p["steel_phos"]),
        "M8": reg.template("TPL_Bolt_M8", *T.bolt_template("M8"), mat=p["steel_phos"]),
        "M10": reg.template("TPL_Bolt_M10", *T.bolt_template("M10"), mat=p["steel_phos"]),
        "M12": reg.template("TPL_Bolt_M12", *T.bolt_template("M12"), mat=p["steel_phos"]),
        "M14": reg.template("TPL_Bolt_M14", *T.bolt_template("M14"), mat=p["steel_phos"]),
        "M11": reg.template("TPL_Bolt_M11", *T.bolt_template("M12", 0.030), mat=p["steel_phos"]),
        "nutM6": reg.template("TPL_Nut_M6", *T.nut_template("M6"), mat=p["steel_phos"]),
        "nutM10": reg.template("TPL_Nut_M10", *T.nut_template("M10"), mat=p["steel_phos"]),
        "nutM12": reg.template("TPL_Nut_M12", *T.nut_template("M12"), mat=p["steel_phos"]),
        "nutM14": reg.template("TPL_Nut_M14", *T.nut_template("M14"), mat=p["steel_phos"]),
        "clip": reg.template("TPL_TrimClip", *T.clip_template(1.0), mat=p["plastic_blk_m"]),
        "clipL": reg.template("TPL_TrimClip_Large", *T.clip_template(1.4), mat=p["plastic_blk_m"]),
        "hose": reg.template("TPL_Hose_Tube", *T.tube_template(0.180, 0.016, 0.011, 10, "X"),
                             mat=p["rubber_hose"], smooth=True),
        "wire": reg.template("TPL_Wire_Run", *T.tube_template(0.220, 0.0045, 0.0030, 8, "X"),
                             mat=p["wire_blk"], smooth=True),
        "wireR": reg.template("TPL_Wire_Run_Red", *T.tube_template(0.220, 0.0045, 0.0030, 8, "X"),
                              mat=p["wire_red"], smooth=True),
        "wirG": reg.template("TPL_Wire_Run_Green", *T.tube_template(0.220, 0.0045, 0.0030, 8, "X"),
                             mat=p["wire_grn"], smooth=True),
        "wireY": reg.template("TPL_Wire_Run_Yellow", *T.tube_template(0.220, 0.0045, 0.0030, 8, "X"),
                              mat=p["wire_ylw"], smooth=True),
        "bras": reg.template("TPL_Bracket", *T.box_vf((0.030, 0.060, 0.014)), mat=p["steel"]),
        "damp": reg.template("TPL_Damper_Pad", *T.box_vf((0.140, 0.110, 0.006)),
                             mat=p["insulation"]),
        "rib": reg.template("TPL_Floor_Rib", *T.box_vf((0.400, 0.014, 0.010)),
                            mat=p["paint_under"]),
        "wsh": reg.template("TPL_Washer", *T.cyl_template(0.0085, 0.0016, 12, "Z"),
                            mat=p["steel_phos"], smooth=True),
    }

    def pat(i, n, x0, x1, y0, y1, z0, z1):
        """Deterministic low-discrepancy placement inside a service envelope."""
        u = ((i * 0.61803398875) % 1.0)
        v = ((i * 0.75487766625 + 0.31) % 1.0)
        w = ((i * 0.56984029099 + 0.67) % 1.0)
        return (x0 + (x1 - x0) * u, y0 + (y1 - y0) * v, z0 + (z1 - z0) * w)

    counter = {"n": 0}
    counts = {}

    def n_of(n):
        """Scale each bulk block so the whole family lands on the documented
        ~1000-part target.  ALTIMA_BULK_SCALE tunes it without editing tables."""
        return max(1, int(round(n * BULK_SCALE)))

    def emit(coll, grp, tag, detail, i, pos, rot=None, tpl_key="M6", mat_key="steel_phos",
             sub=None, note=""):
        counter["n"] += 1
        nm = reg.make_name(grp, tag, detail, i)
        reg.instanced(nm, tpl[tpl_key], pos, coll,
                      meta={"group": grp, "sub": sub or detail, "part": tag + "_" + detail,
                            "mat_key": mat_key, "notes": note}, rot=rot or (0, 0, 0))
        counts[coll] = counts.get(coll, 0) + 1

    # ---- bolts -------------------------------------------------------------
    for (coll, grp, tag, detail, n, size, note) in BOLT_BLOCKS:
        key = size if size in tpl else "M6"
        for i in range(n_of(n)):
            pos = pat(i, n, W(2.30), W(-2.20), -0.74, 0.74, 0.30, 1.30)
            a = (i * 0.7) % 3.14
            emit(coll, grp, tag, detail, i + 1, pos, rot=(0.0, 0.0, a), tpl_key=key,
                 note=note)
    # ---- nuts --------------------------------------------------------------
    for (coll, grp, tag, detail, n, size, note) in NUT_BLOCKS:
        key = "nut" + size
        key = key if key in tpl else "nutM6"
        for i in range(n_of(n)):
            pos = pat(i, n, W(2.20), W(-2.10), -0.70, 0.70, 0.30, 1.20)
            emit(coll, grp, tag, detail, i + 1, pos, tpl_key=key, note=note)
    # ---- clips -------------------------------------------------------------
    for (coll, grp, tag, detail, n, size, note) in CLIP_BLOCKS:
        for i in range(n_of(n)):
            if detail in ("Coolant", "Fuel", "BrakeLine"):
                pos = pat(i, n, W(2.00), W(-2.00), -0.70, 0.70, 0.30, 0.95)
            elif detail in ("Headliner", "Carpet"):
                pos = pat(i, n, W(0.60), W(-1.90), -0.66, 0.66, 0.36, 1.36)
            else:
                pos = pat(i, n, W(2.20), W(-2.10), -0.84, 0.84, 0.16, 1.36)
            emit(coll, grp, tag, detail, i + 1, pos,
                 tpl_key="clip" if detail != "Underbody" else "clipL",
                 mat_key="plastic_blk_m", note=note)
    # ---- wiring ------------------------------------------------------------
    for (coll, grp, tag, detail, n, size, note) in WIRE_BLOCKS:
        for i in range(n_of(n)):
            if detail == "Damper":
                pos = pat(i, n, W(0.55), W(-1.80), -0.70, 0.70, 0.30, 0.60)
            elif detail in ("Brace", "Rib"):
                pos = pat(i, n, W(2.00), W(-2.00), -0.80, 0.80, 0.20, 0.45)
            else:
                pos = pat(i, n, W(2.10), W(-2.10), -0.74, 0.74, 0.32, 1.34)
            if tag == "Wire":
                key = ("wireR", "wirG", "wireY", "wire")[i % 4]
                mk = ("wire_red", "wire_grn", "wire_ylw", "wire_blk")[i % 4]
                rot = (0.0, 0.0, 1.57 * (i % 4))
            elif tag == "Washer":
                key, mk, rot = "wsh", "steel_phos", (0.0, 0.0, 0.0)
            elif tag == "Damper":
                key, mk, rot = "damp", "insulation", (0.0, 0.0, 0.0)
            elif tag == "Rib":
                key, mk, rot = "rib", "paint_under", (0.0, 0.0, 0.0)
            else:
                key, mk, rot = "bras", "steel", (0.0, 0.0, 0.0)
            emit(coll, grp, tag, detail, i + 1, pos, rot=rot, tpl_key=key,
                 mat_key=mk, note=note)
    M["bulk_counts"] = counts
    return M
