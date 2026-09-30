"""Engine-bay exploded assembly sequence: 12 ordered steps.

The sequence is an **assembly** order (bottom-up, exactly how a KA24DE is
built): bare block -> crankshaft -> pistons -> cylinder head -> camshafts ->
timing set -> intake side -> exhaust side -> cooling -> accessory drive ->
transaxle -> engine-bay completion.

Playing the steps forward explodes the engine bay in assembly order; playing
them in reverse reassembles it.  Each step owns one named empty
(``ALTIMA2000_SEQ_StepNN_<Name>``) which is both an animation target and an
optional parent for the step's parts.

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
]

STEP_COUNT = len(STEPS)


def step_empty_name(index):
    """``ALTIMA2000_SEQ_StepNN_<Key>`` for a 1-based step index."""
    s = STEPS[index - 1]
    return "%s_Step%02d_%s" % (SEQ_PREFIX, index, s["key"])


def step_names():
    return [step_empty_name(i + 1) for i in range(STEP_COUNT)]


def resolve(part_names):
    """Map every part name to the 1-based step index that claims it.

    A part is claimed by the first step whose ``exact`` list contains it or
    whose ``prefixes`` match its name.  Returns ``(mapping, unclaimed)``.
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
    unclaimed = [nm for nm in part_names if nm not in mapping]
    return mapping, unclaimed


def unit(direction):
    x, y, z = direction
    n = math.sqrt(x * x + y * y + z * z)
    if n < 1e-9:
        return (0.0, 0.0, 1.0)
    return (x / n, y / n, z / n)
