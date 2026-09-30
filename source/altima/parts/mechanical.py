"""Powertrain, drivetrain, suspension, wheels, brakes, exhaust and fuel parts."""

import math
from mathutils import Vector
from .. import meshutils as mu
from .. import spec
from . import common as C
from . import templates as T

W = spec.wmap
AXF, AXR = spec.AXLE_F, spec.AXLE_R
ZF = 0.30
TR = spec.TRACK_F * 0.5


def _add(reg, name, vf, coll, mat, grp, sub, part, note="", loc=None, mat_key=""):
    v, f = vf
    if loc is None:
        loc = (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v),
               sum(p[2] for p in v) / len(v))
    return reg.add(name, v, f, coll, mat,
                   meta={"group": grp, "sub": sub, "part": part,
                         "mat_key": mat_key, "notes": note}, loc=loc)


def place(reg, pos, rot=None, scale=None):
    """Move the most recently added part and keep the manifest in step."""
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


# ---------------------------------------------------------------------------
# ENGINE - KA24DE 2.4 L DOHC inline four, transverse FWD installation
# ---------------------------------------------------------------------------

def build_engine(reg, mats, surf, M):
    p = mats
    EX = W(1.020)
    EZ = 0.545
    N = lambda *a: reg.make_name("EN", *a)

    # ---- long block --------------------------------------------------------
    _add(reg, N("Block", "Cylinder"), T.box_vf((0.420, 0.480, 0.300), (EX, 0, EZ - 0.06)),
         "Engine", p["engine_blk"], "EN", "LongBlock", "Block",
         "cylinder block - cast iron, 2.4 L KA24DE")
    _add(reg, N("Crankcase", "Lower"), T.box_vf((0.400, 0.440, 0.095), (EX, 0, EZ - 0.235)),
         "Engine", p["engine_blk"], "EN", "LongBlock", "Crankcase",
         "lower crankcase / main bearing girdle")
    _add(reg, N("OilPan", "Sump"), T.box_vf((0.360, 0.400, 0.130), (EX, 0, EZ - 0.335)),
         "Engine", p["steel"], "EN", "LongBlock", "OilPan", "oil pan / sump")
    _add(reg, N("OilDrain", "Plug"), T.cyl_template(0.011, 0.020, 10, "Z"),
         "Engine", p["zinc"], "EN", "LongBlock", "DrainPlug", "oil drain plug")
    reg.parts[-1]["object"].location = (EX, -0.140, EZ - 0.400)
    _add(reg, N("Head", "Cylinder"), T.box_vf((0.430, 0.460, 0.115), (EX, 0, EZ + 0.190)),
         "Engine", p["engine_alu"], "EN", "Head", "Head",
         "cylinder head - aluminium DOHC 16v")
    _add(reg, N("ValveCover", "Cam"), T.box_vf((0.400, 0.420, 0.085), (EX, 0, EZ + 0.290)),
         "Engine", p["engine_alu_worn"], "EN", "Head", "ValveCover", "camshaft valve cover")
    for k in range(4):
        _add(reg, N("CoverBolt", "Perimeter", k + 1),
             T.bolt_template("M6", 0.028), "Engine", p["steel_phos"],
             "EN", "Head", "CoverBolt", "valve cover bolt")
        reg.parts[-1]["object"].location = (EX - 0.170 + 0.113 * k, -0.185, EZ + 0.330)
    _add(reg, N("Gasket", "Head"), T.box_vf((0.440, 0.470, 0.0025), (EX, 0, EZ + 0.132)),
         "Engine", p["steel"], "EN", "Head", "HeadGasket", "multi-layer steel head gasket")
    _add(reg, N("SparkPlug", "NGK"), T.cyl_template(0.007, 0.030, 8, "Z"),
         "Engine", p["steel"], "EN", "Head", "SparkPlug", "spark plug")
    reg.parts[-1]["object"].location = (EX + 0.05, -0.150, EZ + 0.245)
    for k in range(4):
        sp = T.cyl_template(0.0075, 0.032, 8, "Z")
        _add(reg, N("SparkPlug", "NGK", k + 1), sp, "Engine", p["steel"],
             "EN", "Head", "SparkPlug", "spark plug 1-4 (firing order 1-3-4-2)")
        reg.parts[-1]["object"].location = (EX - 0.150 + 0.100 * k, 0.140, EZ + 0.250)
    for k in range(4):
        C.prism_poly(C.circle_poly(0.030, 10), (EX - 0.150 + 0.100 * k, 0.0, EZ - 0.060),
                     (0, 0, 1), 0.330, "Engine", N("Cylinder", "BoreSleeve", k + 1),
                     reg, p["engine_blk"],
                     meta={"group": "EN", "sub": "LongBlock", "part": "Cylinder_" + str(k + 1),
                           "mat_key": "engine_blk", "notes": "cylinder bore / piston assembly"})
    _add(reg, N("TimingCover", "Front"), T.box_vf((0.060, 0.440, 0.420), (EX - 0.250, 0, EZ - 0.02)),
         "Engine", p["engine_alu"], "EN", "LongBlock", "TimingCover", "timing chain cover")
    _add(reg, N("TimingGear", "Crank"), T.cyl_template(0.045, 0.030, 12, "X"),
         "Engine", p["steel"], "EN", "LongBlock", "CrankGear", "crankshaft timing sprocket")
    reg.parts[-1]["object"].location = (EX - 0.275, 0.0, EZ - 0.130)
    _add(reg, N("TimingGear", "Cam"), T.cyl_template(0.050, 0.026, 12, "X"),
         "Engine", p["steel"], "EN", "Head", "CamGear", "camshaft timing sprocket")
    reg.parts[-1]["object"].location = (EX - 0.275, 0.0, EZ + 0.190)
    _add(reg, N("TimingChain", "Roller"), T.tube_template(0.42, 0.078, 0.062, 4, "Z"),
         "Engine", p["steel"], "EN", "LongBlock", "TimingChain", "timing chain run")
    _add(reg, N("Tensioner", "Chain"), T.cyl_template(0.022, 0.055, 10, "X"),
         "Engine", p["steel"], "EN", "LongBlock", "Tensioner", "timing chain tensioner")
    reg.parts[-1]["object"].location = (EX - 0.180, -0.160, EZ + 0.090)
    _add(reg, N("Crankshaft", "Forged"), T.cyl_template(0.035, 0.430, 12, "X"),
         "Engine", p["steel"], "EN", "LongBlock", "Crankshaft", "crankshaft")
    reg.parts[-1]["object"].location = (EX, 0.0, EZ - 0.150)
    for k in range(2):
        _add(reg, N("Camshaft", "DOHC", k + 1),
             T.cyl_template(0.019, 0.430, 10, "X"), "Engine", p["steel"],
             "EN", "Head", "Camshaft", "camshaft (DOHC)")
        reg.parts[-1]["object"].location = (EX, -0.056 + 0.112 * k, EZ + 0.212)
    _add(reg, N("Flywheel", "Driveplate"), T.cyl_template(0.145, 0.024, 24, "X"),
         "Engine", p["steel"], "EN", "LongBlock", "Driveplate", "flex plate / drive plate")
    reg.parts[-1]["object"].location = (EX - 0.300, 0.0, EZ - 0.020)
    _add(reg, N("Dipstick", "Tube"), T.cyl_template(0.005, 0.320, 8, "Z"),
         "Engine", p["steel"], "EN", "LongBlock", "Dipstick", "oil level dipstick and tube")
    reg.parts[-1]["object"].location = (EX + 0.150, -0.190, EZ - 0.120)

    # ---- intake system -----------------------------------------------------
    _add(reg, N("IntakeManifold", "Alu"), T.box_vf((0.500, 0.280, 0.110), (EX, 0.290, EZ + 0.150)),
         "Engine", p["engine_alu"], "EN", "Intake", "IntakeManifold",
         "intake manifold (aluminium)")
    for k in range(4):
        _add(reg, N("IntakeRunner", "Primary", k + 1),
             T.tube_template(0.115, 0.020, 0.015, 8, "Y"), "Engine", p["engine_alu"],
             "EN", "Intake", "IntakeRunner", "intake runner")
        reg.parts[-1]["object"].location = (EX - 0.150 + 0.100 * k, 0.195, EZ + 0.150)
    _add(reg, N("ThrottleBody", "Assembly"), T.cyl_template(0.052, 0.075, 14, "Y"),
         "Engine", p["engine_alu"], "EN", "Intake", "ThrottleBody", "throttle body")
    reg.parts[-1]["object"].location = (EX - 0.045, 0.395, EZ + 0.150)
    _add(reg, N("ThrottlePosition", "Sensor"), T.cyl_template(0.030, 0.030, 10, "Y"),
         "Engine", p["plastic_blk_m"], "EN", "Intake", "TPSSensor", "throttle position sensor")
    reg.parts[-1]["object"].location = (EX - 0.080, 0.430, EZ + 0.185)
    _add(reg, N("IdleControl", "Valve"), T.cyl_template(0.028, 0.060, 10, "Z"),
         "Engine", p["aluminium"], "EN", "Intake", "IACValve", "idle air control valve")
    reg.parts[-1]["object"].location = (EX + 0.060, 0.430, EZ + 0.185)
    reg.add_seal(N("AirIntakeDuct", "Rubber"), [(EX + 0.040, 0.400, EZ + 0.170),
                                                (EX + 0.180, 0.320, EZ + 0.230),
                                                (EX + 0.310, 0.180, EZ + 0.260)],
                 0.042, "Engine", p["rubber_hose"],
                 meta={"group": "EN", "sub": "Intake", "part": "IntakeDuct",
                       "mat_key": "rubber_hose", "notes": "air intake duct"})
    _add(reg, N("AirBox", "Lower"), T.box_vf((0.240, 0.220, 0.180), (EX + 0.360, 0.050, EZ + 0.200)),
         "Engine", p["plastic_blk_m"], "EN", "Intake", "AirBox", "air cleaner housing lower")
    _add(reg, N("AirBox", "Upper"), T.box_vf((0.240, 0.220, 0.090), (EX + 0.360, 0.050, EZ + 0.335)),
         "Engine", p["plastic_blk_m"], "EN", "Intake", "AirBoxUpper", "air cleaner housing upper")
    _add(reg, N("AirFilter", "Element"), T.box_vf((0.215, 0.195, 0.045), (EX + 0.360, 0.050, EZ + 0.285)),
         "Engine", p["filter_paper"], "EN", "Intake", "AirFilter", "panel air filter element")
    _add(reg, N("MassAirFlow", "Sensor"), T.cyl_template(0.040, 0.060, 12, "Y"),
         "Engine", p["plastic_blk_m"], "EN", "Intake", "MAFSensor", "mass air flow sensor")
    reg.parts[-1]["object"].location = (EX + 0.300, 0.180, EZ + 0.300)
    _add(reg, N("Resonator", "Intake"), T.cyl_template(0.055, 0.170, 12, "X"),
         "Engine", p["plastic_blk_m"], "EN", "Intake", "Resonator", "intake resonator")
    reg.parts[-1]["object"].location = (EX + 0.180, 0.290, EZ + 0.240)
    # fuel rail + injectors
    _add(reg, N("FuelRail", "Stainless"), T.cyl_template(0.014, 0.360, 10, "Y"),
         "Engine", p["stainless"], "EN", "Intake", "FuelRail", "fuel rail")
    reg.parts[-1]["object"].location = (EX + 0.010, 0.120, EZ + 0.235)
    for k in range(4):
        _add(reg, N("Injector", "Fuel", k + 1), T.cyl_template(0.011, 0.060, 10, "Z"),
             "Engine", p["plastic_blk_m"], "EN", "Intake", "Injector",
             "port fuel injector")
        reg.parts[-1]["object"].location = (EX - 0.150 + 0.100 * k, 0.120, EZ + 0.215)

    # ---- cooling -----------------------------------------------------------
    _add(reg, N("WaterPump", "Assembly"), T.cyl_template(0.048, 0.085, 14, "X"),
         "Engine", p["aluminium"], "EN", "Cooling", "WaterPump", "coolant pump")
    reg.parts[-1]["object"].location = (EX - 0.230, 0.150, EZ - 0.050)
    _add(reg, N("Thermostat", "Housing"), T.cyl_template(0.038, 0.055, 12, "Z"),
         "Engine", p["aluminium"], "EN", "Cooling", "Thermostat", "thermostat housing")
    reg.parts[-1]["object"].location = (EX + 0.130, 0.160, EZ + 0.060)
    _add(reg, N("Radiator", "Core"), T.box_vf((0.040, 0.640, 0.380), (EX + 0.520, 0, 0.735)),
         "Engine", p["aluminium"], "EN", "Cooling", "Radiator", "radiator core")
    for k in range(2):
        _add(reg, N("RadiatorTank", "Plastic", k + 1),
             T.box_vf((0.052, 0.050, 0.390), (EX + 0.520, -0.340 + 0.680 * k, 0.735)),
             "Engine", p["plastic_blk_m"], "EN", "Cooling", "RadiatorTank",
             "radiator end tank")
    _add(reg, N("RadiatorCap", "Pressure"), T.cyl_template(0.026, 0.032, 12, "Z"),
         "Engine", p["zinc"], "EN", "Cooling", "RadiatorCap", "pressure cap")
    reg.parts[-1]["object"].location = (EX + 0.520, 0.270, 0.945)
    reg.add_seal(N("RadiatorHose", "Upper"), [(EX + 0.500, 0.250, 0.925),
                                              (EX + 0.330, 0.240, 0.955),
                                              (EX + 0.150, 0.190, 0.905)],
                 0.030, "Engine", p["rubber_hose"],
                 meta={"group": "EN", "sub": "Cooling", "part": "HoseUpper",
                       "mat_key": "rubber_hose", "notes": "upper radiator hose"})
    reg.add_seal(N("RadiatorHose", "Lower"), [(EX + 0.500, -0.250, 0.560),
                                              (EX + 0.300, -0.230, 0.500),
                                              (EX + 0.120, -0.160, 0.480)],
                 0.030, "Engine", p["rubber_hose"],
                 meta={"group": "EN", "sub": "Cooling", "part": "HoseLower",
                       "mat_key": "rubber_hose", "notes": "lower radiator hose"})
    _add(reg, N("CoolantReservoir", "Tank"), T.cyl_template(0.055, 0.150, 12, "X"),
         "Engine", p["plastic_ivory"], "EN", "Cooling", "CoolantTank",
         "coolant overflow reservoir")
    reg.parts[-1]["object"].location = (EX + 0.520, 0.400, 0.760)
    _add(reg, N("FanShroud", "Plastic"), T.cyl_template(0.190, 0.060, 20, "X"),
         "Engine", p["plastic_blk_m"], "EN", "Cooling", "FanShroud", "cooling fan shroud")
    reg.parts[-1]["object"].location = (EX + 0.430, 0.0, 0.700)
    for k in range(2):
        _add(reg, N("CoolingFan", "Blade", k + 1),
             T.cyl_template(0.165, 0.022, 24, "X"), "Engine", p["plastic_blk_m"],
             "EN", "Cooling", "FanBlade", "cooling fan blade")
        reg.parts[-1]["object"].location = (EX + 0.395 + 0.035 * k, 0.0, 0.700)
    _add(reg, N("FanMotor", "Electric"), T.cyl_template(0.050, 0.120, 12, "X"),
         "Engine", p["steel"], "EN", "Cooling", "FanMotor", "fan drive motor")
    reg.parts[-1]["object"].location = (EX + 0.470, 0.0, 0.700)

    # ---- exhaust side ------------------------------------------------------
    _add(reg, N("ExhaustManifold", "Cast"), T.cyl_template(0.040, 0.380, 12, "Y"),
         "Exhaust_Manifold", p["cast_iron"], "EX", "Manifold", "ExhaustManifold",
         "exhaust manifold (cast iron)")
    for k in range(4):
        _add(reg, N("ManifoldRunner", "Cast", k + 1),
             T.tube_template(0.075, 0.019, 0.014, 8, "Y"),
             "Exhaust_Manifold", p["cast_iron"], "EX", "Manifold", "ManifoldRunner",
             "exhaust manifold runner")
        reg.parts[-1]["object"].location = (EX - 0.150 + 0.100 * k, -0.165, EZ + 0.010)
    _add(reg, N("HeatShield", "Manifold"), T.box_vf((0.360, 0.070, 0.140), (EX, -0.215, EZ + 0.030)),
         "Exhaust_Manifold", p["steel"], "EX", "Manifold", "HeatShield",
         "manifold heat shield")
    _add(reg, N("OxygenSensor", "Upstream"), T.cyl_template(0.014, 0.055, 10, "Y"),
         "Exhaust_Manifold", p["zinc"], "EX", "Manifold", "O2Sensor",
         "upstream heated oxygen sensor")
    reg.parts[-1]["object"].location = (EX + 0.020, -0.190, EZ + 0.060)

    # ---- accessory drive ---------------------------------------------------
    for k, (nm, cy, r) in enumerate((("Alternator", -0.235, 0.052),)):
        _add(reg, N(nm, "Assembly"), T.cyl_template(r, 0.140, 14, "X"),
             "Engine", p["aluminium"], "EN", "Accessory", nm, "alternator")
        reg.parts[-1]["object"].location = (EX - 0.130, cy, EZ - 0.140)
    _add(reg, N("PowerSteeringPump", "Assembly"), T.cyl_template(0.048, 0.110, 14, "X"),
         "Engine", p["aluminium"], "EN", "Accessory", "PSPump", "power steering pump")
    reg.parts[-1]["object"].location = (EX + 0.130, -0.235, EZ - 0.120)
    _add(reg, N("ACCompressor", "Assembly"), T.cyl_template(0.055, 0.145, 14, "X"),
         "Engine", p["engine_alu"], "EN", "Accessory", "ACCompressor",
         "air conditioning compressor")
    reg.parts[-1]["object"].location = (EX + 0.010, -0.290, EZ - 0.230)
    _add(reg, N("Tensioner", "Belt"), T.cyl_template(0.032, 0.030, 12, "X"),
         "Engine", p["steel"], "EN", "Accessory", "BeltTensioner", "drive belt tensioner")
    reg.parts[-1]["object"].location = (EX + 0.170, -0.150, EZ - 0.190)
    _add(reg, N("IdlerPulley", "Belt"), T.cyl_template(0.028, 0.026, 12, "X"),
         "Engine", p["steel"], "EN", "Accessory", "IdlerPulley", "idler pulley")
    reg.parts[-1]["object"].location = (EX - 0.200, -0.100, EZ - 0.100)
    for k, nm in enumerate(("WaterPump", "Alternator", "PS", "AC")):
        _add(reg, N("SerpentineBelt", nm), T.tube_template(0.30 - 0.02 * k, 0.011, 0.008, 4, "Z"),
             "Engine", p["belt_rubber"], "EN", "Accessory", "Belt",
             "serpentine accessory drive belt")
        reg.parts[-1]["object"].location = (EX + 0.02 * (k - 2), -0.060 - 0.06 * k, EZ - 0.190)
    for k in range(2):
        _add(reg, N("EngineMount", "Bracket", k + 1),
             T.box_vf((0.080, 0.090, 0.100), (EX, (-0.280 if k == 0 else 0.330), EZ - 0.170)),
             "Drivetrain_Mount", p["steel"], "TR", "Mount", "EngineMount",
             "engine mount bracket")
        _add(reg, N("EngineMount", "Insulator", k + 1),
             T.box_vf((0.090, 0.100, 0.075), (EX, (-0.290 if k == 0 else 0.340), EZ - 0.255)),
             "Drivetrain_Mount", p["bushing"], "TR", "Mount", "EngineMountIns",
             "engine mount insulator")
    _add(reg, N("EngineCover", "Plastic"), T.box_vf((0.380, 0.400, 0.030), (EX, 0, EZ + 0.350)),
         "Engine", p["engine_plastic"], "EN", "Head", "EngineCover",
         "decorative engine cover")
    _add(reg, N("Emission", "EGRValve"), T.cyl_template(0.032, 0.070, 12, "Z"),
         "Engine_Emission", p["aluminium"], "EM", "EGR", "EGRValve", "EGR valve")
    reg.parts[-1]["object"].location = (EX + 0.070, 0.300, EZ + 0.110)
    _add(reg, N("Emission", "CharcoalCanister"), T.box_vf((0.180, 0.140, 0.110),
                                                          (EX + 0.450, -0.300, EZ - 0.050)),
         "Engine_Emission", p["plastic_blk_m"], "EM", "EVAP", "Canister",
         "EVAP charcoal canister")
    return M


# ---------------------------------------------------------------------------
# DRIVETRAIN
# ---------------------------------------------------------------------------

def build_drivetrain(reg, mats, surf, M):
    p = mats
    TX = W(0.130)
    TZ = 0.400
    N = lambda *a: reg.make_name("TR", *a)
    _add(reg, N("Transaxle", "Case"), T.box_vf((0.330, 0.380, 0.290), (TX, 0, TZ)),
         "Drivetrain_Transaxle", p["aluminium"], "TR", "Transaxle", "Case",
         "transaxle case - 4-speed automatic (RE4F04A)")
    _add(reg, N("TorqueConverter", "Housing"), T.cyl_template(0.150, 0.100, 16, "X"),
         "Drivetrain_Transaxle", p["aluminium"], "TR", "Transaxle", "Bellhousing",
         "torque converter housing / bellhousing")
    reg.parts[-1]["object"].location = (W(0.320), 0.0, TZ)
    _add(reg, N("TorqueConverter", "Assembly"), T.cyl_template(0.135, 0.070, 16, "X"),
         "Drivetrain_Transaxle", p["steel"], "TR", "Transaxle", "TorqueConverter",
         "torque converter")
    reg.parts[-1]["object"].location = (W(0.280), 0.0, TZ)
    _add(reg, N("ValveBody", "Assembly"), T.box_vf((0.240, 0.300, 0.060), (TX, 0, TZ - 0.170)),
         "Drivetrain_Transaxle", p["aluminium"], "TR", "Transaxle", "ValveBody", "valve body")
    _add(reg, N("Transaxle", "OilPan"), T.box_vf((0.260, 0.320, 0.055), (TX, 0, TZ - 0.230)),
         "Drivetrain_Transaxle", p["steel"], "TR", "Transaxle", "OilPan", "transaxle oil pan")
    _add(reg, N("Transaxle", "Filter"), T.box_vf((0.200, 0.260, 0.022), (TX, 0, TZ - 0.200)),
         "Drivetrain_Transaxle", p["filter_paper"], "TR", "Transaxle", "Filter",
         "transmission fluid filter")
    _add(reg, N("Transaxle", "Dipstick"), T.cyl_template(0.005, 0.300, 8, "Z"),
         "Drivetrain_Transaxle", p["steel"], "TR", "Transaxle", "Dipstick",
         "automatic transaxle dipstick")
    reg.parts[-1]["object"].location = (W(0.560), -0.130, 0.700)
    _add(reg, N("Differential", "Carrier"), T.box_vf((0.200, 0.240, 0.200), (TX - 0.060, 0, TZ - 0.110)),
         "Drivetrain_Transaxle", p["steel"], "TR", "Transaxle", "Differential",
         "final drive / differential assembly")
    _add(reg, N("Output", "SpeedSensor"), T.cyl_template(0.022, 0.050, 10, "Y"),
         "Drivetrain_Transaxle", p["plastic_blk_m"], "TR", "Transaxle", "VSS",
         "vehicle speed sensor")
    reg.parts[-1]["object"].location = (TX - 0.060, 0.140, TZ - 0.110)
    for k in range(2):
        sgn = 1 if k == 0 else -1
        _add(reg, N("DriveShaft", "Axle", k + 1),
             T.cyl_template(0.020, 0.520, 12, "Y"), "Drivetrain_Drive", p["steel"],
             "TR", "Drive", "Axle", "front drive axle shaft")
        reg.parts[-1]["object"].location = (TX - 0.060, sgn * 0.360, TZ - 0.110)
        for j in range(2):
            _add(reg, N("CVJoint", "ConstantVelocity", k * 2 + j + 1),
                 T.sphere_template(0.046, 12, 8), "Drivetrain_Drive", p["steel"],
                 "TR", "Drive", "CVJoint", "constant velocity joint")
            reg.parts[-1]["object"].location = (TX - 0.060,
                                                sgn * (0.135 + 0.445 * j), TZ - 0.110)
            _add(reg, N("CVBoot", "Rubber", k * 2 + j + 1),
                 T.tube_template(0.090, 0.048, 0.030, 10, "Y"),
                 "Drivetrain_Drive", p["rubber_hose"],
                 "TR", "Drive", "CVBoot", "CV joint rubber boot")
            reg.parts[-1]["object"].location = (TX - 0.060,
                                                sgn * (0.190 + 0.440 * j), TZ - 0.110)
    for k in range(2):
        _add(reg, N("TransaxleMount", "Insulator", k + 1),
             T.box_vf((0.090, 0.100, 0.080), (TX, (-0.270 if k == 0 else 0.300), TZ - 0.220)),
             "Drivetrain_Mount", p["bushing"], "TR", "Mount", "TransMount",
             "transaxle mount insulator")
    _add(reg, N("ShiftCable", "Selector"), T.cyl_template(0.010, 0.700, 8, "X"),
         "Drivetrain_Drive", p["wire_blk"], "TR", "Drive", "ShiftCable",
         "shift selector cable")
    reg.parts[-1]["object"].location = (W(0.300), -0.060, 0.560)
    return M


# ---------------------------------------------------------------------------
# SUSPENSION + STEERING
# ---------------------------------------------------------------------------

def build_suspension(reg, mats, surf, M):
    p = mats
    N = lambda *a: reg.make_name("SU", *a)
    for k, side in enumerate(("R", "L")):
        sgn = -1 if side == "R" else 1
        y = TR * sgn
        # ---- MacPherson strut ----
        _add(reg, N("StrutDamper", "Front_%s" % side),
             T.cyl_template(0.028, 0.300, 12, "Z"), "Suspension_Front", p["shock_body"],
             "SU", "Front", "StrutDamper", "front strut damper body")
        reg.parts[-1]["object"].location = (AXF, y * 0.96, 0.520)
        _add(reg, N("StrutRod", "Front_%s" % side),
             T.cyl_template(0.016, 0.320, 10, "Z"), "Suspension_Front", p["shock_rod"],
             "SU", "Front", "StrutRod", "front strut piston rod")
        reg.parts[-1]["object"].location = (AXF, y * 0.96, 0.720)
        _add(reg, N("CoilSpring", "Front_%s" % side),
             T.tube_template(0.300, 0.070, 0.058, 8, "Z"), "Suspension_Front",
             p["spring_steel"], "SU", "Front", "CoilSpring", "front coil spring")
        reg.parts[-1]["object"].location = (AXF, y * 0.96, 0.600)
        _add(reg, N("StrutMount", "Upper_%s" % side),
             T.cyl_template(0.058, 0.040, 12, "Z"), "Suspension_Front", p["steel"],
             "SU", "Front", "StrutMount", "upper strut mount bearing")
        reg.parts[-1]["object"].location = (AXF, y * 0.96, 0.880)
        _add(reg, N("BumpStop", "Front_%s" % side),
             T.cyl_template(0.038, 0.075, 10, "Z"), "Suspension_Front", p["bushing"],
             "SU", "Front", "BumpStop", "strut bump stop")
        reg.parts[-1]["object"].location = (AXF, y * 0.96, 0.790)
        _add(reg, N("DustBoot", "Front_%s" % side),
             T.tube_template(0.180, 0.050, 0.040, 10, "Z"), "Suspension_Front",
             p["rubber_hose"], "SU", "Front", "DustBoot", "strut dust boot")
        reg.parts[-1]["object"].location = (AXF, y * 0.96, 0.700)
        # ---- lower control arm + knuckle + hub ----
        _add(reg, N("LowerControlArm", "Front_%s" % side),
             T.box_vf((0.090, 0.400, 0.055), (AXF + 0.040, y * 0.60, 0.260)),
             "Suspension_Front", p["steel"], "SU", "Front", "LowerControlArm",
             "front lower control arm (transverse link)")
        _add(reg, N("BallJoint", "Front_%s" % side),
             T.cyl_template(0.024, 0.060, 10, "Z"), "Suspension_Front", p["steel"],
             "SU", "Front", "BallJoint", "lower ball joint")
        reg.parts[-1]["object"].location = (AXF + 0.040, y * 0.98, 0.250)
        _add(reg, N("SteeringKnuckle", "Front_%s" % side),
             T.box_vf((0.110, 0.090, 0.230), (AXF, y * 0.995, 0.320)),
             "Suspension_Front", p["cast_iron"], "SU", "Front", "Knuckle",
             "front steering knuckle")
        _add(reg, N("HubBearing", "Front_%s" % side),
             T.cyl_template(0.040, 0.055, 12, "Y"), "Suspension_Front", p["steel"],
             "SU", "Front", "HubBearing", "front hub bearing assembly")
        reg.parts[-1]["object"].location = (AXF, y, 0.3135)
        # ---- stabiliser bar: one bar, two links, two bushings per side ----
        _add(reg, N("StabilizerBar", "Front_%s" % side),
             T.cyl_template(0.014, 0.480 if side == "R" else 0.540, 10, "Y"),
             "Suspension_Front", p["spring_steel"],
             "SU", "Front", "StabilizerBar_" + side,
             "front stabiliser (anti-roll) bar")
        place(reg, (W(1.760), y * 1.42, 0.420))
        _add(reg, N("StabilizerLink", "Front_%s" % side),
             T.cyl_template(0.009, 0.170, 8, "Z"), "Suspension_Front",
             p["steel"], "SU", "Front", "StabilizerLink_" + side,
             "stabiliser link rod")
        place(reg, (W(1.700), y * 0.92, 0.360))
        _add(reg, N("StabilizerBushing", "Front_%s" % side),
             T.cyl_template(0.020, 0.050, 10, "Y"), "Suspension_Front",
             p["bushing"], "SU", "Front", "StabilizerBush_" + side,
             "stabiliser bar bushing")
        place(reg, (W(1.560), y * 0.30, 0.410))
        # ---- rear: strut + beam ----
    _add(reg, N("BeamAxle", "Rear"), T.cyl_template(0.055, 1.320, 14, "Y"),
         "Suspension_Rear", p["steel"], "SU", "Rear", "BeamAxle",
         "rear torsion beam axle")
    reg.parts[-1]["object"].location = (AXR, 0, 0.300)
    for k, side in enumerate(("R", "L")):
        sgn = -1 if side == "R" else 1
        y = TR * sgn
        _add(reg, N("TrailingArm", "Rear_%s" % side),
             T.box_vf((0.520, 0.075, 0.075), (AXR + 0.250, y * 0.86, 0.290)),
             "Suspension_Rear", p["steel"], "SU", "Rear", "TrailingArm",
             "rear trailing arm")
        _add(reg, N("StrutDamper", "Rear_%s" % side),
             T.cyl_template(0.026, 0.280, 12, "Z"), "Suspension_Rear", p["shock_body"],
             "SU", "Rear", "StrutDamperR", "rear shock absorber")
        place(reg, (AXR, y * 0.95, 0.430))
        _add(reg, N("CoilSpring", "Rear_%s" % side),
             T.tube_template(0.290, 0.068, 0.056, 8, "Z"), "Suspension_Rear",
             p["spring_steel"], "SU", "Rear", "CoilSpringR", "rear coil spring")
        reg.parts[-1]["object"].location = (AXR, y * 0.80, 0.430)
        _add(reg, N("StrutMount", "Rear_%s" % side),
             T.cyl_template(0.050, 0.036, 12, "Z"), "Suspension_Rear", p["steel"],
             "SU", "Rear", "StrutMountR", "rear upper shock mount")
        reg.parts[-1]["object"].location = (AXR, y * 0.95, 0.620)
        _add(reg, N("TrailingArmBushing", "Rear_%s" % side),
             T.cyl_template(0.028, 0.075, 10, "Y"), "Suspension_Rear", p["bushing"],
             "SU", "Rear", "TrailingArmBush", "trailing arm pivot bushing")
        reg.parts[-1]["object"].location = (AXR + 0.500, y * 0.86, 0.290)
        _add(reg, N("HubBearing", "Rear_%s" % side),
             T.cyl_template(0.038, 0.050, 12, "Y"), "Suspension_Rear", p["steel"],
             "SU", "Rear", "HubBearingR", "rear hub bearing assembly")
        reg.parts[-1]["object"].location = (AXR, y, 0.3135)
    _add(reg, N("PanhardRod", "Rear"), T.cyl_template(0.013, 0.760, 10, "Y"),
         "Suspension_Rear", p["steel"], "SU", "Rear", "PanhardRod", "lateral locating rod")
    reg.parts[-1]["object"].location = (AXR + 0.120, 0, 0.330)
    # ---- steering ----
    _add(reg, N("SteeringRack", "Assembly"), T.cyl_template(0.026, 0.900, 12, "Y"),
         "Suspension_Steering", p["aluminium"], "SR", "Steering", "Rack",
         "power steering rack and pinion")
    reg.parts[-1]["object"].location = (W(1.480), 0, 0.400)
    _add(reg, N("PinionHousing", "Steering"), T.cyl_template(0.032, 0.120, 10, "Z"),
         "Suspension_Steering", p["aluminium"], "SR", "Steering", "Pinion",
         "steering pinion housing")
    reg.parts[-1]["object"].location = (W(1.480), -0.130, 0.430)
    for k, side in enumerate(("R", "L")):
        sgn = -1 if side == "R" else 1
        _add(reg, N("TieRod", "Inner_%s" % side), T.cyl_template(0.011, 0.330, 8, "Y"),
             "Suspension_Steering", p["steel"], "SR", "Steering", "TieRod",
             "inner tie rod")
        reg.parts[-1]["object"].location = (W(1.480), sgn * 0.270, 0.390)
        _add(reg, N("TieRodEnd", "Outer_%s" % side), T.cyl_template(0.014, 0.120, 10, "Y"),
             "Suspension_Steering", p["steel"], "SR", "Steering", "TieRodEnd",
             "outer tie rod end")
        reg.parts[-1]["object"].location = (AXF, sgn * 0.640, 0.360)
        _add(reg, N("RackBoot", "Rubber_%s" % side),
             T.tube_template(0.190, 0.030, 0.020, 10, "Y"),
             "Suspension_Steering", p["rubber_hose"], "SR", "Steering", "RackBoot",
             "rack end rubber boot")
        reg.parts[-1]["object"].location = (W(1.480), sgn * 0.330, 0.395)
    _add(reg, N("SteeringColumn", "Assembly"), T.cyl_template(0.024, 0.560, 10, "X"),
         "Suspension_Steering", p["steel"], "SR", "Steering", "Column",
         "collapsible steering column")
    reg.parts[-1]["object"].location = (W(0.400), -0.360, 0.730)
    _add(reg, N("SteeringUJoint", "Lower"), T.cyl_template(0.020, 0.070, 10, "X"),
         "Suspension_Steering", p["steel"], "SR", "Steering", "UJoint",
         "steering intermediate shaft universal joint")
    reg.parts[-1]["object"].location = (W(0.930), -0.220, 0.640)
    _add(reg, N("SteeringWheel", "Rim"), T.torus if False else
         T.tube_template(0.020, 0.185, 0.170, 4, "X"),
         "Suspension_Steering", p["plastic_dk"], "SR", "Steering", "SteeringWheel",
         "steering wheel rim")
    reg.parts[-1]["object"].location = (W(0.360), -0.360, 0.735)
    _add(reg, N("SteeringWheelHub", "Centre"), T.cyl_template(0.070, 0.055, 14, "X"),
         "Suspension_Steering", p["plastic_dk"], "SR", "Steering", "WheelHub",
         "steering wheel hub with airbag")
    reg.parts[-1]["object"].location = (W(0.390), -0.360, 0.735)
    return M


# ---------------------------------------------------------------------------
# WHEELS + BRAKES
# ---------------------------------------------------------------------------

def build_wheels(reg, mats, surf, M):
    p = mats
    R = spec.WHEEL_R
    RW = spec.RIM_D * 0.5
    ww = spec.WHEEL_W * 0.5
    mats_list = [("FL", 1, AXF), ("FR", -1, AXF), ("RL", 1, AXR), ("RR", -1, AXR)]
    tpl_tire = reg.template("TPL_Tire_205_60R15", *T.tire(R, spec.WHEEL_W, RW), mat=p["tire"], smooth=True)
    tpl_rim = reg.template("TPL_Rim_15x6J", *T.road_wheel(spec.RIM_D, spec.WHEEL_W * 0.86),
                           mat=p["alu_brushed"], smooth=True)
    tpl_cap = reg.template("TPL_HubCap_Centre", *T.cyl_template(0.052, 0.016, 16, "Y"),
                           mat=p["chrome"], smooth=True)
    tpl_tread = reg.template("TPL_Tread_Band", *T.tread_ring(R + 0.0015, R - 0.028,
                                                             spec.WHEEL_W * 0.76),
                             mat=p["tire_tread"], smooth=True)
    tpl_spoke = reg.template("TPL_AlloySpoke", *T.wheel_spoke(RW * 0.32, RW * 0.93,
                                                              0.012, 0.020),
                             mat=p["alu_brushed"], smooth=False)
    for (tag, sgn, cx) in mats_list:
        y = TR * sgn
        sub = "Wheel_" + tag
        reg.instanced(reg.make_name("WH", "Tire", "Road_%s" % tag), tpl_tire,
                      (cx, y, R), "Wheels",
                      meta={"group": "WH", "sub": sub, "part": "Tire_" + tag,
                            "mat_key": "tire", "notes": "205/60R15 tire"})
        reg.instanced(reg.make_name("WH", "Rim", "Alloy_%s" % tag), tpl_rim,
                      (cx, y, R), "Wheels",
                      meta={"group": "WH", "sub": sub, "part": "Rim_" + tag,
                            "mat_key": "alu_brushed", "notes": "15x6J alloy wheel"})
        reg.instanced(reg.make_name("WH", "Tread", "Band_%s" % tag), tpl_tread,
                      (cx, y, R), "Wheels",
                      meta={"group": "WH", "sub": sub, "part": "Tread_" + tag,
                            "mat_key": "tire_tread", "notes": "tire tread band"})
        reg.instanced(reg.make_name("WH", "HubCap", "Centre_%s" % tag), tpl_cap,
                      (cx, y * 1.09, R), "Wheels",
                      meta={"group": "WH", "sub": sub, "part": "CentreCap_" + tag,
                            "mat_key": "chrome", "notes": "centre cap"})
        for k in range(5):
            a = mu.TAU * k / 5 + 0.3
            reg.instanced(reg.make_name("WH", "Spoke", "Alloy_%s" % tag, k + 1),
                          tpl_spoke,
                          (cx + RW * 0.60 * math.sin(a), y * 1.055,
                           R + RW * 0.60 * math.cos(a)),
                          "Wheels",
                          meta={"group": "WH", "sub": sub, "part": "Spoke_" + tag,
                                "mat_key": "alu_brushed", "notes": "alloy spoke"},
                          rot=(0.0, 0.0, -a))
        for k in range(4):
            a = mu.TAU * k / 4 + 0.2
            C.prism_poly(C.circle_poly(0.006, 8),
                         (cx, y * 1.10, R),
                         (0, 1, 0), 0.020, "Fasteners_Bolts",
                         reg.make_name("FT", "LugNut", "Wheel_%s" % tag, k + 1), reg,
                         p["steel_phos"],
                         meta={"group": "FT", "sub": "LugNut", "part": "LugNut_" + tag,
                               "mat_key": "steel_phos", "notes": "wheel lug nut"})
            place(reg, (cx + 0.062 * math.sin(a), y * 1.113, R + 0.062 * math.cos(a)))
        for k in range(1):
            C.prism_poly(C.circle_poly(0.006, 8), (cx, y * 1.08, R - RW * 0.72),
                         (0, 1, 0), 0.030, "Wheels",
                         reg.make_name("WH", "ValveStem", "Tire_%s" % tag), reg,
                         p["rubber"],
                         meta={"group": "WH", "sub": sub, "part": "ValveStem_" + tag,
                               "mat_key": "rubber", "notes": "tire valve stem"})
    # ---- brakes -------------------------------------------------------------
    tpl_disc = reg.template("TPL_BrakeDisc", *T.disc(0.128, 0.024, 0.085, 0.055),
                            mat=p["brake_disc"], smooth=True)
    tpl_pad = reg.template("TPL_BrakePad", *T.box_vf((0.048, 0.020, 0.100)),
                           mat=p["brake_pad"])
    tpl_piston = reg.template("TPL_CaliperPiston", *T.cyl_template(0.022, 0.030, 12, "Y"),
                              mat=p["steel"], smooth=True)
    for side in ("R", "L"):
        sgn = -1 if side == "R" else 1
        y = TR * sgn
        for (pos, cx, coll) in (("Front", AXF, "Brakes_Front"), ("Rear", AXR, "Brakes_Rear")):
            reg.instanced(reg.make_name("BR", "Disc", "%s_%s" % (pos, side)), tpl_disc,
                          (cx, y * 0.86, spec.WHEEL_R), coll,
                          meta={"group": "BR", "sub": pos, "part": "Disc_" + pos + side,
                                "mat_key": "brake_disc", "notes": "vented brake disc"})
            for k in range(2):
                reg.instanced(reg.make_name("BR", "Pad", "%s_%s_%s" % (pos, side, k + 1)),
                              tpl_pad, (cx + 0.070, y * 0.90, spec.WHEEL_R + 0.030 - 0.060 * k),
                              coll,
                              meta={"group": "BR", "sub": pos, "part": "Pad_" + pos + side,
                                    "mat_key": "brake_pad", "notes": "brake pad"})
            reg.instanced(reg.make_name("BR", "Piston", "%s_%s" % (pos, side)), tpl_piston,
                          (cx + 0.078, y * 0.90, spec.WHEEL_R), coll,
                          meta={"group": "BR", "sub": pos, "part": "Piston_" + pos + side,
                                "mat_key": "steel", "notes": "caliper piston"})
            _add(reg, reg.make_name("BR", "Caliper", "%s_%s" % (pos, side)),
                 T.box_vf((0.100, 0.070, 0.170), (cx + 0.078, y * 0.91, spec.WHEEL_R)),
                 coll, p["caliper"], "BR", pos, "Caliper_" + pos + side, "brake caliper body")
    # ---- hydraulic system ---------------------------------------------------
    _add(reg, reg.make_name("BR", "MasterCylinder", "Tandem"),
         T.cyl_template(0.026, 0.170, 12, "X"), "Brakes_Hydraulics", p["aluminium"],
         "BR", "Hydraulics", "MasterCylinder", "tandem master cylinder")
    reg.parts[-1]["object"].location = (W(1.870), -0.140, 0.940)
    _add(reg, reg.make_name("BR", "BrakeBooster", "Vacuum"),
         T.cyl_template(0.115, 0.140, 16, "X"), "Brakes_Hydraulics", p["steel"],
         "BR", "Hydraulics", "Booster", "vacuum brake booster")
    reg.parts[-1]["object"].location = (W(1.700), -0.140, 0.900)
    _add(reg, reg.make_name("BR", "ABSModule", "Hydraulic"),
         T.box_vf((0.130, 0.110, 0.100), (W(1.950), 0.240, 0.880)),
         "Brakes_Hydraulics", p["aluminium"], "BR", "Hydraulics", "ABSModule",
         "ABS hydraulic control module")
    _add(reg, reg.make_name("BR", "ProportioningValve", "Rear"),
         T.cyl_template(0.018, 0.080, 10, "X"), "Brakes_Hydraulics", p["brass"],
         "BR", "Hydraulics", "PropValve", "rear proportioning valve")
    reg.parts[-1]["object"].location = (W(1.600), 0.150, 0.740)
    for k, (side, cx) in enumerate((("R", AXF), ("L", AXF), ("R", AXR), ("L", AXR))):
        sgn = -1 if side == "R" else 1
        reg.add_seal(reg.make_name("BR", "BrakeLine", "Rigid_%s_%02d" % (side, k + 1)),
                     [(W(1.700), -0.180 * sgn, 0.860),
                      (W(1.200), -0.300 * sgn, 0.520),
                      (cx, -0.560 * sgn, 0.420)],
                     0.0050, "Brakes_Hydraulics", p["copper"],
                     meta={"group": "BR", "sub": "Hydraulics", "part": "BrakeLine",
                           "mat_key": "copper", "notes": "rigid brake line"})
        reg.add_seal(reg.make_name("BR", "BrakeHose", "Flexible_%s_%02d" % (side, k + 1)),
                     [(cx, -0.560 * sgn, 0.420),
                      (cx, -TR * 0.94 * sgn, 0.400),
                      (cx, -TR * 0.99 * sgn, spec.WHEEL_R + 0.040)],
                     0.0055, "Brakes_Hydraulics", p["rubber_hose"],
                     meta={"group": "BR", "sub": "Hydraulics", "part": "BrakeHose",
                           "mat_key": "rubber_hose", "notes": "flexible brake hose"})
    _add(reg, reg.make_name("BR", "ParkingBrake", "Lever"),
         T.box_vf((0.070, 0.230, 0.055), (W(0.020), -0.150, 0.420)),
         "Brakes_Hydraulics", p["steel"], "BR", "Hydraulics", "ParkBrakeLever",
         "parking brake lever")
    for k, side in enumerate(("R", "L")):
        sgn = -1 if side == "R" else 1
        reg.add_seal(reg.make_name("BR", "ParkingBrake", "Cable_%s" % side),
                     [(W(0.020), -0.180, 0.400),
                      (AXR + 0.600, -0.300 * sgn, 0.330),
                      (AXR, -TR * 0.80 * sgn, 0.320)],
                     0.0045, "Brakes_Hydraulics", p["steel"],
                     meta={"group": "BR", "sub": "Hydraulics", "part": "ParkCable",
                           "mat_key": "steel", "notes": "parking brake cable"})
    return M


# ---------------------------------------------------------------------------
# EXHAUST + FUEL
# ---------------------------------------------------------------------------

def build_exhaust_fuel(reg, mats, surf, M):
    p = mats
    reg.add_seal("ALTIMA2000_EXH_Downpipe_Primary",
                 [(W(1.020), -0.190, 0.400), (W(0.700), -0.150, 0.330),
                  (W(0.300), -0.130, 0.300)],
                 0.025, "Exhaust_Pipe", p["stainless"],
                 meta={"group": "EX", "sub": "Pipe", "part": "Downpipe",
                       "mat_key": "stainless", "notes": "exhaust downpipe"})
    _add(reg, "ALTIMA2000_EXH_Catalyst_Converter",
         T.cyl_template(0.075, 0.360, 14, "X"), "Exhaust_Pipe", p["stainless"],
         "EX", "Pipe", "Catalyst", "catalytic converter")
    reg.parts[-1]["object"].location = (W(0.050), -0.130, 0.290)
    reg.add_seal("ALTIMA2000_EXH_Midpipe_Intermediate",
                 [(W(-0.180), -0.130, 0.290), (W(-0.700), -0.160, 0.270),
                  (W(-1.240), -0.200, 0.265)],
                 0.025, "Exhaust_Pipe", p["stainless"],
                 meta={"group": "EX", "sub": "Pipe", "part": "Midpipe",
                       "mat_key": "stainless", "notes": "intermediate exhaust pipe"})
    _add(reg, "ALTIMA2000_EXH_Resonator_Canister",
         T.cyl_template(0.055, 0.300, 14, "X"), "Exhaust_Pipe", p["stainless"],
         "EX", "Pipe", "Resonator", "exhaust resonator")
    reg.parts[-1]["object"].location = (W(-0.900), -0.180, 0.265)
    _add(reg, "ALTIMA2000_EXH_Muffler_Main", T.box_vf((0.460, 0.300, 0.220),
                                                      (W(-1.740), -0.290, 0.300)),
         "Exhaust_Muffler", p["stainless"], "EX", "Muffler", "Muffler",
         "main exhaust muffler")
    _add(reg, "ALTIMA2000_EXH_Tailpipe_Outlet",
         T.cyl_template(0.030, 0.420, 12, "X"), "Exhaust_Muffler", p["stainless"],
         "EX", "Muffler", "Tailpipe", "exhaust tailpipe")
    reg.parts[-1]["object"].location = (W(-2.030), -0.300, 0.290)
    for k in range(4):
        _add(reg, "ALTIMA2000_EXH_Hanger_Rubber_%03d" % (k + 1),
             T.cyl_template(0.014, 0.045, 8, "Y"), "Exhaust_Pipe", p["rubber"],
             "EX", "Pipe", "Hanger", "exhaust rubber hanger")
        reg.parts[-1]["object"].location = (W(-0.300 - 0.480 * k), -0.240, 0.330)
    for k, (xx, yy) in enumerate(((W(-0.500), -0.250), (W(-1.200), -0.250),
                                  (W(0.320), -0.220))):
        _add(reg, "ALTIMA2000_EXH_HeatShield_Floor_%03d" % (k + 1),
             T.box_vf((0.360, 0.240, 0.006), (xx, yy, 0.290)),
             "Exhaust_Pipe", p["steel"], "EX", "Pipe", "HeatShield",
             "exhaust heat shield")
    _add(reg, "ALTIMA2000_EXH_OxygenSensor_Downstream",
         T.cyl_template(0.014, 0.055, 10, "Z"), "Exhaust_Pipe", p["zinc"],
         "EX", "Pipe", "O2SensorDown", "downstream oxygen sensor")
    reg.parts[-1]["object"].location = (W(-0.060), -0.130, 0.350)
    # ---- fuel system -------------------------------------------------------
    _add(reg, "ALTIMA2000_FLD_FuelTank_Main",
         T.box_vf((0.700, 0.980, 0.180), (W(-0.700), 0.020, 0.300)),
         "Fluids_Body", p["fluid_fuel"], "FL", "Fuel", "Tank", "fuel tank")
    _add(reg, "ALTIMA2000_FLD_FuelPump_Module",
         T.cyl_template(0.075, 0.090, 14, "Z"), "Fluids_Body", p["zinc"],
         "FL", "Fuel", "PumpModule", "in-tank fuel pump module")
    reg.parts[-1]["object"].location = (W(-0.700), 0.020, 0.400)
    for k in range(2):
        _add(reg, "ALTIMA2000_FLD_FuelTankStrap_%03d" % (k + 1),
             T.box_vf((0.060, 1.020, 0.020), (W(-0.700 - 0.180 + 0.360 * k), 0.020, 0.400)),
             "Fluids_Body", p["steel"], "FL", "Fuel", "TankStrap", "fuel tank strap")
    reg.add_seal("ALTIMA2000_FLD_FillerNeck_Pipe",
                 [(W(-1.760), 0.760, 0.880), (W(-1.700), 0.700, 0.620),
                  (W(-1.400), 0.560, 0.420)],
                 0.020, "Fluids_Body", p["steel"],
                 meta={"group": "FL", "sub": "Fuel", "part": "FillerNeck",
                       "mat_key": "steel", "notes": "fuel filler neck"})
    reg.add_seal("ALTIMA2000_FLD_FillerHose_Rubber",
                 [(W(-1.400), 0.560, 0.420), (W(-1.200), 0.400, 0.380),
                  (W(-1.050), 0.180, 0.360)],
                 0.024, "Fluids_Body", p["rubber_hose"],
                 meta={"group": "FL", "sub": "Fuel", "part": "FillerHose",
                       "mat_key": "rubber_hose", "notes": "fuel filler hose"})
    reg.add_seal("ALTIMA2000_FLD_FuelFeedLine_Rigid",
                 [(W(-1.000), -0.100, 0.440), (W(-0.400), -0.240, 0.400),
                  (W(0.400), -0.300, 0.380), (W(0.900), -0.240, 0.420)],
                 0.0055, "Fluids_Body", p["copper"],
                 meta={"group": "FL", "sub": "Fuel", "part": "FeedLine",
                       "mat_key": "copper", "notes": "fuel feed line"})
    reg.add_seal("ALTIMA2000_FLD_FuelReturnLine_Rigid",
                 [(W(-1.000), -0.060, 0.420), (W(-0.300), -0.200, 0.380),
                  (W(0.500), -0.260, 0.360), (W(0.900), -0.200, 0.400)],
                 0.0050, "Fluids_Body", p["copper"],
                 meta={"group": "FL", "sub": "Fuel", "part": "ReturnLine",
                       "mat_key": "copper", "notes": "fuel return line"})
    # ---- fluid service items ----------------------------------------------
    _add(reg, "ALTIMA2000_FLD_EngineOil_Fill", T.cyl_template(0.030, 0.030, 10, "Z"),
         "Fluids_Engine", p["plastic_blk_m"], "FL", "Engine", "OilFill",
         "engine oil filler cap")
    reg.parts[-1]["object"].location = (W(1.020), 0.150, 0.900)
    _add(reg, "ALTIMA2000_FLD_OilFilter_SpinOn", T.cyl_template(0.038, 0.080, 14, "Y"),
         "Fluids_Engine", p["zinc"], "FL", "Engine", "OilFilter", "spin-on oil filter")
    reg.parts[-1]["object"].location = (W(1.150), -0.140, 0.420)
    _add(reg, "ALTIMA2000_FLD_WasherReservoir_Tank",
         T.box_vf((0.140, 0.180, 0.140), (W(2.100), -0.330, 0.700)),
         "Fluids_Body", p["plastic_ivory"], "FL", "Body", "WasherTank",
         "windshield washer reservoir")
    _add(reg, "ALTIMA2000_FLD_WasherPump_Motor",
         T.cyl_template(0.024, 0.060, 10, "Z"), "Fluids_Body", p["plastic_blk_m"],
         "FL", "Body", "WasherPump", "washer pump motor")
    reg.parts[-1]["object"].location = (W(2.100), -0.330, 0.630)
    _add(reg, "ALTIMA2000_FLD_PowerSteeringReservoir_Tank",
         T.cyl_template(0.048, 0.120, 12, "Z"), "Fluids_Engine", p["plastic_blk_m"],
         "FL", "Engine", "PSReservoir", "power steering fluid reservoir")
    reg.parts[-1]["object"].location = (W(1.700), -0.320, 0.980)
    return M


def build_all(reg, mats, surf, M):
    build_engine(reg, mats, surf, M)
    build_drivetrain(reg, mats, surf, M)
    build_suspension(reg, mats, surf, M)
    build_wheels(reg, mats, surf, M)
    build_exhaust_fuel(reg, mats, surf, M)
    return M
