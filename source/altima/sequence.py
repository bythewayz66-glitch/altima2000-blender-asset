"""Exploded assembly sequence: 25 ordered steps covering the whole car.

Steps 01-12 are the **engine bay**, in assembly order (bottom-up, exactly how a
KA24DE is built): bare block -> crankshaft -> pistons -> cylinder head ->
camshafts -> timing set -> intake side -> exhaust side -> cooling -> accessory
drive -> transaxle -> engine-bay completion.

Steps 13-25 extend the same sequence to every remaining system so that all
parts are sequenced: engine-bay completion, interior, electrical harness, body
panels, glazing/lighting, doors, wheels/brakes, suspension/steering, exhaust,
fluids/fuel, structural fasteners and clips.

Playing the steps forward explodes the car in assembly order; playing them in
reverse reassembles it.  Each step owns one named empty
(``ALTIMA2000_SEQ_StepNN_<Name>``) which is both an animation target and the
PARENT of the step's parts - moving the empty moves exactly that step's parts.

Every step lists its parts by **explicit name** (or by a deterministic name
prefix), so the mapping is documented and reproducible rather than heuristic.
"""

import math

PREFIX = "ALTIMA2000"
SEQ_PREFIX = "ALTIMA2000_SEQ"

#: engine-bay centre used as the radial origin for the step explode vectors
BAY_CENTRE = (1.020, 0.0, 0.545)

# ---------------------------------------------------------------------------
# step definitions
# ---------------------------------------------------------------------------
# Each entry:
#   key        short identifier used in the empty name
#   title      human-readable step title
#   direction  nominal explode direction (unit-ish; normalised at build time)
#   distance   nominal explode distance in metres
#   exact      explicit part names moved by this step
#   prefixes   name prefixes; every part whose name starts with one is moved
#   note       what the step represents in the build
#
# ``exact`` and ``prefixes`` are combined; a part is moved by the FIRST step
# that claims it, so the order below is also the precedence order.

STEPS = [
    dict(
        key="EngineBlock", title="Bare engine block and lower end",
        direction=(0.0, 0.0, -1.0), distance=0.90,
        exact=[
            "ALTIMA2000_ENG_Block_Cylinder",
            "ALTIMA2000_ENG_Crankcase_Lower",
            "ALTIMA2000_ENG_OilPan_Sump",
            "ALTIMA2000_ENG_OilDrain_Plug",
            "ALTIMA2000_ENG_Dipstick_Tube",
        ],
        prefixes=["ALTIMA2000_ENG_HexBolt_OilPan", "ALTIMA2000_ENG_HexBolt_Crankcase"],
        note="cylinder block, crankcase girdle, oil pan and block hardware",
    ),
    dict(
        key="Crankshaft", title="Crankshaft and drive plate",
        direction=(0.0, 0.0, -1.0), distance=0.72,
        exact=[
            "ALTIMA2000_ENG_Crankshaft_Forged",
            "ALTIMA2000_ENG_Flywheel_Driveplate",
        ],
        prefixes=[],
        note="crankshaft and flex plate, lifted out of the block",
    ),
    dict(
        key="Pistons", title="Pistons and connecting rods",
        direction=(0.0, 0.0, 1.0), distance=0.62,
        exact=[],
        prefixes=["ALTIMA2000_ENG_Cylinder_BoreSleeve"],
        note="four piston / connecting-rod assemblies, drawn up out of the bores",
    ),
    dict(
        key="CylinderHead", title="Cylinder head and gasket",
        direction=(0.0, 0.0, 1.0), distance=0.50,
        exact=[
            "ALTIMA2000_ENG_Head_Cylinder",
            "ALTIMA2000_ENG_Gasket_Head",
        ],
        prefixes=["ALTIMA2000_ENG_HexBolt_CylinderHead"],
        note="cylinder head, multi-layer steel gasket and head bolts",
    ),
    dict(
        key="Camshafts", title="Camshafts, valve cover and ignition",
        direction=(0.0, 0.0, 1.0), distance=0.40,
        exact=[
            "ALTIMA2000_ENG_Camshaft_DOHC_001",
            "ALTIMA2000_ENG_Camshaft_DOHC_002",
            "ALTIMA2000_ENG_ValveCover_Cam",
            "ALTIMA2000_ENG_SparkPlug_NGK",
        ],
        prefixes=["ALTIMA2000_ENG_HexBolt_CamCap", "ALTIMA2000_ENG_CoverBolt_Perimeter",
                  "ALTIMA2000_ENG_SparkPlug_NGK"],
        note="both DOHC camshafts, cam bearing caps, valve cover and spark plugs",
    ),
    dict(
        key="TimingSet", title="Timing chain set and front cover",
        direction=(1.0, 0.0, 0.0), distance=0.46,
        exact=[
            "ALTIMA2000_ENG_TimingCover_Front",
            "ALTIMA2000_ENG_TimingGear_Crank",
            "ALTIMA2000_ENG_TimingGear_Cam",
            "ALTIMA2000_ENG_TimingChain_Roller",
            "ALTIMA2000_ENG_Tensioner_Chain",
        ],
        prefixes=["ALTIMA2000_ENG_HexBolt_TimingCover"],
        note="timing chain cover, crank and cam sprockets, chain and tensioner",
    ),
    dict(
        key="IntakeSide", title="Intake side and fuel injection",
        direction=(0.0, 1.0, 0.35), distance=0.58,
        exact=[
            "ALTIMA2000_ENG_IntakeManifold_Alu",
            "ALTIMA2000_ENG_ThrottleBody_Assembly",
            "ALTIMA2000_ENG_ThrottlePosition_Sensor",
            "ALTIMA2000_ENG_IdleControl_Valve",
            "ALTIMA2000_ENG_AirIntakeDuct_Rubber",
            "ALTIMA2000_ENG_AirBox_Lower",
            "ALTIMA2000_ENG_AirBox_Upper",
            "ALTIMA2000_ENG_AirFilter_Element",
            "ALTIMA2000_ENG_MassAirFlow_Sensor",
            "ALTIMA2000_ENG_Resonator_Intake",
            "ALTIMA2000_ENG_FuelRail_Stainless",
        ],
        prefixes=["ALTIMA2000_ENG_IntakeRunner_Primary", "ALTIMA2000_ENG_Injector_Fuel",
                  "ALTIMA2000_ENG_HexBolt_IntakeManifold", "ALTIMA2000_ENG_HexBolt_Injector"],
        note="intake manifold, runners, throttle body, air box and fuel rail/injectors",
    ),
    dict(
        key="ExhaustSide", title="Exhaust side and manifold",
        direction=(0.0, -1.0, 0.35), distance=0.58,
        exact=[
            "ALTIMA2000_ENG_ExhaustManifold_Cast",
            "ALTIMA2000_ENG_HeatShield_Manifold",
            "ALTIMA2000_ENG_OxygenSensor_Upstream",
        ],
        prefixes=["ALTIMA2000_ENG_ManifoldRunner_Cast", "ALTIMA2000_EXH_Stud_Manifold"],
        note="exhaust manifold, runners, heat shield, upstream O2 sensor and studs",
    ),
    dict(
        key="CoolingSystem", title="Cooling system",
        direction=(1.0, 0.0, 0.30), distance=0.66,
        exact=[
            "ALTIMA2000_ENG_WaterPump_Assembly",
            "ALTIMA2000_ENG_Thermostat_Housing",
            "ALTIMA2000_ENG_Radiator_Core",
            "ALTIMA2000_ENG_RadiatorCap_Pressure",
            "ALTIMA2000_ENG_RadiatorHose_Upper",
            "ALTIMA2000_ENG_RadiatorHose_Lower",
            "ALTIMA2000_ENG_CoolantReservoir_Tank",
            "ALTIMA2000_ENG_FanShroud_Plastic",
            "ALTIMA2000_ENG_FanMotor_Electric",
        ],
        prefixes=["ALTIMA2000_ENG_RadiatorTank_Plastic", "ALTIMA2000_ENG_CoolingFan_Blade",
                  "ALTIMA2000_ENG_HexBolt_WaterPump"],
        note="water pump, thermostat, radiator, hoses, reservoir and cooling fans",
    ),
    dict(
        key="AccessoryDrive", title="Accessory drive",
        direction=(0.0, -1.0, -0.20), distance=0.60,
        exact=[
            "ALTIMA2000_ENG_Alternator_Assembly",
            "ALTIMA2000_ENG_PowerSteeringPump_Assembly",
            "ALTIMA2000_ENG_ACCompressor_Assembly",
            "ALTIMA2000_ENG_Tensioner_Belt",
            "ALTIMA2000_ENG_IdlerPulley_Belt",
        ],
        prefixes=["ALTIMA2000_ENG_SerpentineBelt", "ALTIMA2000_ENG_HexBolt_Alternator",
                  "ALTIMA2000_ENG_HexBolt_Compressor", "ALTIMA2000_ENG_HexBolt_BeltTensioner"],
        note="alternator, power steering pump, A/C compressor, tensioner and belts",
    ),
    dict(
        key="Transaxle", title="Transaxle and driveline",
        direction=(-1.0, 0.0, -0.25), distance=0.80,
        exact=[
            "ALTIMA2000_TRN_Transaxle_Case",
            "ALTIMA2000_TRN_TorqueConverter_Housing",
            "ALTIMA2000_TRN_TorqueConverter_Assembly",
            "ALTIMA2000_TRN_ValveBody_Assembly",
            "ALTIMA2000_TRN_Transaxle_OilPan",
            "ALTIMA2000_TRN_Transaxle_Filter",
            "ALTIMA2000_TRN_Transaxle_Dipstick",
            "ALTIMA2000_TRN_Differential_Carrier",
            "ALTIMA2000_TRN_Output_SpeedSensor",
        ],
        prefixes=["ALTIMA2000_TRN_TransaxleMount_Insulator", "ALTIMA2000_TRN_HexBolt_Bellhousing",
                  "ALTIMA2000_TRN_HexBolt_ValveBody", "ALTIMA2000_TRN_HexBolt_OilPanTransaxle"],
        note="transaxle case, torque converter, valve body, final drive and mounts",
    ),
    dict(
        key="EngineBayComplete", title="Engine-bay completion",
        direction=(0.0, 0.0, 1.0), distance=0.34,
        exact=[
            "ALTIMA2000_ENG_EngineCover_Plastic",
            "ALTIMA2000_ENG_Emission_EGRValve",
            "ALTIMA2000_ENG_Emission_CharcoalCanister",
            "ALTIMA2000_ENG_EngineMount_Bracket_001",
            "ALTIMA2000_ENG_EngineMount_Insulator_001",
            "ALTIMA2000_ENG_EngineMount_Bracket_002",
            "ALTIMA2000_ENG_EngineMount_Insulator_002",
        ],
        prefixes=["ALTIMA2000_TRN_HexBolt_EngineMount"],
        note="engine cover, EGR/EVAP hardware, engine mounts and remaining bay fasteners",
    ),
    # -----------------------------------------------------------------------
    # full-car steps (13-25)
    # -----------------------------------------------------------------------
    # Steps 01-12 above cover the engine bay (230 parts).  The steps below take
    # the sequence to the WHOLE car.  ``resolve()`` gives a part to the FIRST
    # step that claims it, so these prefix buckets only pick up what the
    # engine-bay steps never claimed - the membership of steps 01-12 is
    # therefore bit-for-bit unchanged no matter how these are edited.
    #
    # Directions are deliberately layered along Z (interior/electrical highest,
    # body panels below them, running gear and structure dropping away) so the
    # full-car explode reads as a stack of systems rather than a jumble.
    dict(
        key="EngineBayCompletion", title="Remaining engine-bay hardware",
        direction=(0.0, 0.0, 1.0), distance=0.20, loc=(1.020, 0.0, 0.545),
        exact=[],
        prefixes=["ALTIMA2000_ENG_", "ALTIMA2000_EMIS_", "ALTIMA2000_BATT_"],
        note="engine parts not owned by steps 01-12, plus emission control and battery",
    ),
    dict(
        key="InteriorCabin", title="Interior cabin trim and seating",
        direction=(0.0, 0.0, 1.0), distance=1.45, loc=(0.0, 0.0, 0.70),
        exact=[],
        prefixes=["ALTIMA2000_INTR_"],
        note="dashboard, seats, console, carpet, headliner, door cards and cabin trim",
    ),
    dict(
        key="ElectricalHarness", title="Electrical harness and modules",
        direction=(0.0, 0.0, 1.0), distance=1.70, loc=(0.0, 0.0, 0.70),
        exact=[],
        prefixes=["ALTIMA2000_ELEC_", "ALTIMA2000_EL_"],
        note="every routed wire segment, connector, grommet, clip, module, fuse, relay and the antenna",
    ),
    dict(
        key="BodyPanels", title="Exterior body panels and moldings",
        direction=(0.0, 0.0, 1.0), distance=1.05, loc=(0.0, 0.0, 0.70),
        exact=[],
        prefixes=["ALTIMA2000_BODY_", "ALTIMA2000_MLDG_", "ALTIMA2000_MD_"],
        note="hood, trunk lid, fenders, bumper covers, grille, fuel door, moldings, badges and emblems",
    ),
    dict(
        key="GlazingAndLighting", title="Glazing, lamps and mirrors",
        direction=(0.0, 0.0, 1.0), distance=0.80, loc=(0.0, 0.0, 0.70),
        exact=[],
        prefixes=["ALTIMA2000_LAMP_", "ALTIMA2000_MIRR_", "ALTIMA2000_GLAZ_", "ALTIMA2000_GLZ_"],
        note="windscreen, backlight, quarter glass, door glass, all lamp assemblies and mirrors",
    ),
    dict(
        key="DoorAssemblies", title="Door assemblies and seals",
        direction=(0.0, 0.0, 1.0), distance=0.62, loc=(0.0, 0.0, 0.70),
        exact=[],
        prefixes=["ALTIMA2000_DOOR_", "ALTIMA2000_DRM_", "ALTIMA2000_SEAL_"],
        note="the four door shells and hardware, the standalone door module parts, and all weatherstrip",
    ),
    dict(
        key="WheelsAndBrakes", title="Wheels, tyres and brakes",
        direction=(0.0, 0.0, -1.0), distance=0.60, loc=(0.0, 0.0, 0.70),
        exact=[],
        prefixes=["ALTIMA2000_WHL_", "ALTIMA2000_BRAK_"],
        note="rims, tyres, hub caps, valve stems, lug nuts, discs, calipers, pads and hydraulic parts",
    ),
    dict(
        key="SuspensionAndSteering", title="Suspension and steering",
        direction=(0.0, 0.0, -1.0), distance=0.48, loc=(0.0, 0.0, 0.70),
        exact=[],
        prefixes=["ALTIMA2000_SUSP_", "ALTIMA2000_STR_"],
        note="struts, springs, control arms, knuckles, hubs, beam axle, stabiliser bars, rack and column",
    ),
    dict(
        key="ExhaustSystem", title="Exhaust system",
        direction=(0.0, 0.0, -1.0), distance=1.05, loc=(0.0, 0.0, 0.70),
        exact=[],
        prefixes=["ALTIMA2000_EXH_"],
        note="manifold heat shield, downpipe, catalyst, midpipe, resonator, muffler, tailpipe and sensors",
    ),
    dict(
        key="FluidsAndFuel", title="Fluids, tanks and fuel system",
        direction=(0.0, -1.0, -0.30), distance=0.75, loc=(0.0, 0.0, 0.70),
        exact=[],
        prefixes=["ALTIMA2000_FLD_", "ALTIMA2000_FLUD_"],
        note="fuel tank, pump, filler neck, feed and return lines, washer reservoir, oil and power-steering fluid",
    ),
    dict(
        key="StructuralFasteners", title="Structural fasteners",
        direction=(0.0, 0.0, -1.0), distance=0.26, loc=(0.0, 0.0, 0.70),
        exact=[],
        prefixes=["ALTIMA2000_FAST_"],
        note="the general bolt, washer, nut and lug-nut population across the whole car",
    ),
    dict(
        key="ClipsAndFixings", title="Clips, retainers and fixings",
        direction=(0.0, 0.0, 1.0), distance=0.24, loc=(0.0, 0.0, 0.70),
        exact=[],
        prefixes=["ALTIMA2000_CLIP_"],
        note="trim clips, retainers, hose clamps and tie straps",
    ),
    dict(
        key="StructuralShell", title="Body shell and structure",
        direction=(0.0, 0.0, -1.0), distance=0.16, loc=(0.0, 0.0, 0.70),
        exact=[],
        prefixes=["ALTIMA2000_SHEL_"],
        note="floor, roof bows, wheel houses, strut towers, radiator support, parcel shelf, "
             "spare well, ribs, braces and shell hardware - the reference hull, so it "
             "barely moves while every other system lifts away from it",
    ),
    dict(
        key="DrivetrainRemainder", title="Remaining driveline",
        direction=(0.0, 0.0, -1.0), distance=0.42, loc=(0.0, 0.0, 0.70),
        exact=[],
        prefixes=["ALTIMA2000_TRN_"],
        note="drive shafts, CV joints and boots, shift cable and transaxle hardware "
             "not owned by step 11",
    ),
    # -----------------------------------------------------------------------
    # catch-all (last step)
    # -----------------------------------------------------------------------
    # ``catch_all`` claims every part no earlier step matched.  It is the
    # guarantee that the sequence covers 100% of the car: if a new part group
    # is ever added to the generator without a step of its own, it lands here
    # instead of silently falling out of the sequence.
    dict(
        key="RemainingHardware", title="Remaining hardware and safety systems",
        direction=(0.0, 0.0, 1.0), distance=0.30, loc=(0.0, 0.0, 0.70),
        exact=[],
        prefixes=["ALTIMA2000_SAFE_", "ALTIMA2000_SCRE_"],
        catch_all=True,
        note="safety restraints, screws and studs, and any part not claimed by an "
             "earlier step - the catch-all that makes the sequence total",
    ),
]

STEP_COUNT = len(STEPS)

#: steps 01-12 are the engine-bay sequence; 13-25 extend it to the whole car
ENGINE_BAY_STEPS = 12


def step_empty_name(index):
    """``ALTIMA2000_SEQ_StepNN_<Key>`` for a 1-based step index."""
    s = STEPS[index - 1]
    return "%s_Step%02d_%s" % (SEQ_PREFIX, index, s["key"])


def step_names():
    return [step_empty_name(i + 1) for i in range(STEP_COUNT)]


def resolve(part_names):
    """Map every part name to the 1-based step index that claims it.

    A part is claimed by the first step whose ``exact`` list contains it or
    whose ``prefixes`` match its name.  A step flagged ``catch_all`` claims
    every part no earlier step matched, so the mapping is always total.
    Returns ``(mapping, unclaimed)``.
    """
    mapping = {}
    for i, s in enumerate(STEPS):
        idx = i + 1
        for nm in s["exact"]:
            mapping.setdefault(nm, idx)
        for pre in s["prefixes"]:
            for nm in part_names:
                if nm.startswith(pre):
                    mapping.setdefault(nm, idx)
    for i, s in enumerate(STEPS):
        if s.get("catch_all"):
            idx = i + 1
            for nm in part_names:
                mapping.setdefault(nm, idx)
    unclaimed = [nm for nm in part_names if nm not in mapping]
    return mapping, unclaimed


def unit(direction):
    x, y, z = direction
    n = math.sqrt(x * x + y * y + z * z)
    if n < 1e-9:
        return (0.0, 0.0, 1.0)
    return (x / n, y / n, z / n)
