"""Real, physically modelled wiring for the ALTIMA2000 asset.

Everything here is **real geometry**: every wire is a swept tube with its own
mesh, its own object, its own name and its own manifest row.  Nothing is a
texture, a painted line or a decal.

Design
------
A *harness* is a bundle of *circuits* that share a route.  Each circuit is a
different-coloured insulated wire running in parallel with the others, offset
slightly so the bundle reads as a real loom.  Each circuit is split into
*segments* at the route's waypoints, so a segment is a removable piece of the
run exactly like a real harness section.

Along every route we also place the hardware a real loom has:

* **grommets** where the run passes through a bulkhead / panel,
* **clips** (P-clips and push retainers) that hold the loom to the body,
* **connectors** (plug shells) at each end of the run.

Trace data
----------
Every wire mesh carries a baked ``trace_t`` float attribute (POINT domain) that
is the normalised arc length (0.0 at the start of the run, 1.0 at the end).
The wire materials read that attribute, so the touch-activated glow can light a
wire progressively from one end to the other instead of switching on as a
whole.  See ``altima/materials.py`` (``_wire_trace_nodes``) and the
``altima.trace_wire`` operator in ``build_altima.py``.
"""

import math

from mathutils import Vector

from .. import meshutils as mu
from . import common as C

TAU = math.pi * 2.0

# ---------------------------------------------------------------------------
# routing nodes - real component positions read out of the built asset
# (world metres, +X forward, +Y left, +Z up, Z=0 ground)
# ---------------------------------------------------------------------------
NODES = {
    # power / distribution
    "BatteryPos":   (1.760, 0.250, 0.805),
    "BatteryNeg":   (1.760, 0.470, 0.805),
    "FuseBoxEng":   (2.009, 0.340, 0.860),
    "RelayBox":     (2.030, 0.340, 0.940),
    "FuseBoxInt":   (0.500, -0.460, 0.700),
    "ABSModule":    (1.956, 0.240, 0.880),
    # modules
    "ECU":          (0.520, -0.420, 0.840),
    "TCU":          (0.540, -0.100, 0.780),
    "BCM":          (0.240, 0.420, 0.740),
    # engine bay
    "Alternator":   (0.890, -0.235, 0.405),
    "Starter":      (0.700, -0.300, 0.400),
    "HornR":        (2.328, 0.330, 0.740),
    "HornL":        (2.328, 0.430, 0.740),
    "WiperMotor":   (0.560, -0.180, 0.860),
    "WasherPump":   (2.115, -0.330, 0.630),
    "CoolantRes":   (1.540, 0.400, 0.760),
    "FanMotor":     (1.490, 0.000, 0.700),
    "MAF":          (1.320, 0.180, 0.845),
    "TPS":          (0.940, 0.430, 0.730),
    "O2Up":         (1.040, -0.190, 0.605),
    "Injector1":    (0.870, 0.120, 0.760),
    "Injector4":    (1.170, 0.120, 0.760),
    "CoilPack":     (0.980, 0.300, 0.800),
    # lighting
    "HeadlampR":    (2.690, -0.580, 0.800),
    "HeadlampL":    (2.690, 0.580, 0.800),
    "TailR":        (-2.145, -0.470, 0.760),
    "TailL":        (-2.145, 0.470, 0.760),
    "PlateLamp":    (-2.200, 0.000, 0.700),
    # cabin
    "Cluster":      (0.560, -0.300, 0.900),
    "Radio":        (0.500, 0.000, 0.760),
    "Blower":       (0.300, -0.400, 0.600),
    "SwHeadlamp":   (0.600, -0.360, 0.945),
    "SwWiper":      (0.640, -0.200, 0.930),
    "SwHazard":     (0.640, 0.000, 0.945),
    "SwIgnition":   (0.700, -0.360, 0.700),
    "SwWindowFL":   (0.560, 0.560, 0.560),
    "SwWindowFR":   (0.560, -0.560, 0.560),
    "SwMirror":     (0.600, -0.420, 0.700),
    "SwDefog":      (0.560, 0.200, 0.690),
    "SeatFL":       (-0.150, 0.380, 0.500),
    "SeatFR":       (-0.150, -0.380, 0.500),
    "FuelPump":     (-0.700, 0.020, 0.400),
    "Antenna":      (-1.900, 0.000, 1.000),
    "DomeLamp":     (-0.300, 0.000, 1.360),
    # audio
    "SpkDoorFL":    (0.480, 0.640, 0.860),
    "SpkDoorFR":    (0.480, -0.640, 0.860),
    "SpkDoorRL":    (-0.560, 0.640, 0.520),
    "SpkDoorRR":    (-0.560, -0.640, 0.520),
    "SpkRearL":     (-1.360, 0.520, 0.520),
    "SpkRearR":     (-1.360, -0.520, 0.520),
    # mirrors
    "MirrorL":      (0.600, 0.900, 0.980),
    "MirrorR":      (0.600, -0.900, 0.980),
    # grounds
    "GroundEng":    (1.030, -0.150, 0.530),
    "GroundBody":   (-0.070, -0.290, 0.530),
    "GroundRear":   (-1.170, -0.010, 0.530),
    # routing waypoints (not components - just where the loom physically runs)
    "BulkheadL":    (0.660, 0.300, 0.700),
    "BulkheadR":    (0.660, -0.300, 0.700),
    "BulkheadC":    (0.660, 0.000, 0.720),
    "BayFrontL":    (2.150, 0.520, 0.760),
    "BayFrontR":    (2.150, -0.520, 0.760),
    "BayTopL":      (1.500, 0.560, 0.900),
    "BayTopR":      (1.500, -0.560, 0.900),
    "SillL":        (0.000, 0.700, 0.300),
    "SillR":        (0.000, -0.700, 0.300),
    "SillRearL":    (-1.200, 0.700, 0.300),
    "SillRearR":    (-1.200, -0.700, 0.300),
    "RoofL":        (-0.300, 0.680, 1.360),
    "RoofR":        (-0.300, -0.680, 1.360),
    "RoofFront":    (0.300, 0.000, 1.380),
    "RearBulkL":    (-1.500, 0.400, 0.600),
    "RearBulkR":    (-1.500, -0.400, 0.600),
    "TrunkL":       (-2.000, 0.400, 0.700),
    "TrunkR":       (-2.000, -0.400, 0.700),
    "DoorGromFL":   (0.560, 0.760, 0.700),
    "DoorGromFR":   (0.560, -0.760, 0.700),
    "DoorGromRL":   (-0.400, 0.760, 0.560),
    "DoorGromRR":   (-0.400, -0.760, 0.560),
    "DashL":        (0.500, 0.500, 0.760),
    "DashR":        (0.500, -0.500, 0.760),
    "ConsoleMid":   (0.200, 0.000, 0.560),
    "FloorMid":     (-0.400, 0.000, 0.360),
    "WheelFL":      (1.380, 0.723, 0.340),
    "WheelFR":      (1.380, -0.723, 0.340),
    "WheelRL":      (-1.240, 0.602, 0.340),
    "WheelRR":      (-1.240, -0.602, 0.340),
}


def N(key):
    """World position of a routing node."""
    return NODES[key]


# ---------------------------------------------------------------------------
# harness table
#
#   tag        - component family (goes into the part name)
#   sub        - Electrical sub-collection
#   circuits   - [(detail, material_key, radius_m), ...]  the wires in the bundle
#   route      - [node key, ...]  the physical run, in order
#   grommets   - [(route index, detail), ...]  bulkhead pass-throughs
#   clips      - how many P-clips / retainers to place along the run
#   ends       - [(detail, node key), ...]  connector shells at the run ends
#   note       - manifest note
# ---------------------------------------------------------------------------
HARNESSES = [
    # ---------------------------------------------------------------- engine bay
    dict(tag="EngineMain", sub="Engine", clips=9,
         circuits=[("Power", "wire_red", 0.0038), ("Ground", "wire_blk", 0.0034),
                   ("Signal", "wire_grn", 0.0028), ("Signal2", "wire_ylw", 0.0028)],
         route=["FuseBoxEng", "BayTopL", "BayTopR", "CoilPack", "BulkheadC", "ECU"],
         grommets=[(4, "Bulkhead")],
         ends=[("FuseBox", "FuseBoxEng"), ("ECU", "ECU")],
         note="engine management main harness, fuse box to ECM through the firewall"),

    dict(tag="Injector", sub="Engine", clips=5,
         circuits=[("Power", "wire_red", 0.0030), ("Signal", "wire_grn", 0.0026),
                   ("Signal2", "wire_ylw", 0.0026)],
         route=["Injector1", "Injector4", "CoilPack", "BulkheadC", "ECU"],
         grommets=[(3, "Bulkhead")],
         ends=[("Rail", "Injector1"), ("ECU", "ECU")],
         note="fuel injector sub-harness, rail to ECM"),

    dict(tag="Ignition", sub="Engine", clips=4,
         circuits=[("Power", "wire_red", 0.0030), ("Signal", "wire_ylw", 0.0026)],
         route=["CoilPack", "BayTopL", "BulkheadC", "ECU"],
         grommets=[(2, "Bulkhead")],
         ends=[("Coil", "CoilPack"), ("ECU", "ECU")],
         note="ignition coil primary harness"),

    dict(tag="EngineSensors", sub="Engine", clips=6,
         circuits=[("Signal", "wire_pur", 0.0026), ("Signal2", "wire_gry", 0.0026),
                   ("Ground", "wire_blk", 0.0026)],
         route=["MAF", "TPS", "O2Up", "BulkheadC", "ECU"],
         grommets=[(3, "Bulkhead")],
         ends=[("MAF", "MAF"), ("ECU", "ECU")],
         note="MAF / TPS / oxygen sensor signal harness"),

    dict(tag="Charging", sub="Engine", clips=5,
         circuits=[("Output", "wire_red", 0.0052), ("Sense", "wire_ylw", 0.0028)],
         route=["Alternator", "BayTopR", "BayFrontL", "BatteryPos"],
         grommets=[],
         ends=[("Alternator", "Alternator"), ("Battery", "BatteryPos")],
         note="alternator output cable to battery positive"),

    dict(tag="Starting", sub="Engine", clips=4,
         circuits=[("Feed", "wire_red", 0.0058), ("Signal", "wire_grn", 0.0028)],
         route=["BatteryPos", "BayFrontR", "Starter"],
         grommets=[],
         ends=[("Battery", "BatteryPos"), ("Starter", "Starter")],
         note="starter motor feed and solenoid signal"),

    dict(tag="EngineGround", sub="Engine", clips=4,
         circuits=[("Ground", "wire_blk", 0.0050)],
         route=["BatteryNeg", "BayTopR", "GroundEng", "GroundBody"],
         grommets=[],
         ends=[("Battery", "BatteryNeg"), ("Body", "GroundBody")],
         note="battery negative to engine and body ground"),

    dict(tag="Cooling", sub="Engine", clips=5,
         circuits=[("Power", "wire_red", 0.0032), ("Ground", "wire_blk", 0.0030)],
         route=["FanMotor", "CoolantRes", "BayTopL", "FuseBoxEng"],
         grommets=[],
         ends=[("Fan", "FanMotor"), ("FuseBox", "FuseBoxEng")],
         note="cooling fan and coolant level harness"),

    dict(tag="Horn", sub="Engine", clips=3,
         circuits=[("Power", "wire_red", 0.0030), ("Ground", "wire_blk", 0.0028)],
         route=["HornR", "HornL", "BayFrontL", "FuseBoxEng"],
         grommets=[],
         ends=[("Horn", "HornR"), ("FuseBox", "FuseBoxEng")],
         note="horn pair harness"),

    dict(tag="WiperWasher", sub="Engine", clips=4,
         circuits=[("Power", "wire_red", 0.0030), ("Signal", "wire_grn", 0.0026),
                   ("Ground", "wire_blk", 0.0026)],
         route=["WiperMotor", "BulkheadC", "WasherPump", "BayFrontR", "FuseBoxEng"],
         grommets=[(1, "Bulkhead")],
         ends=[("Wiper", "WiperMotor"), ("FuseBox", "FuseBoxEng")],
         note="wiper motor and washer pump harness"),

    dict(tag="ABS", sub="Chassis", clips=8,
         circuits=[("Power", "wire_red", 0.0034), ("Signal", "wire_pur", 0.0026),
                   ("Signal2", "wire_gry", 0.0026), ("Ground", "wire_blk", 0.0028)],
         route=["ABSModule", "BayTopR", "WheelFR", "WheelFL", "BulkheadR", "ECU"],
         grommets=[(4, "Bulkhead")],
         ends=[("Module", "ABSModule"), ("ECU", "ECU")],
         note="ABS module to wheel speed sensors and ECM"),

    # ---------------------------------------------------------------- lighting
    dict(tag="Headlamp", sub="Lighting", clips=6,
         circuits=[("LowBeam", "wire_wht", 0.0030), ("HighBeam", "wire_blu", 0.0030),
                   ("Ground", "wire_brn", 0.0030)],
         route=["FuseBoxEng", "BayFrontL", "HeadlampL", "HeadlampR", "BayFrontR"],
         grommets=[],
         ends=[("FuseBox", "FuseBoxEng"), ("LampR", "HeadlampR")],
         note="headlamp harness, fuse box to both lamp units"),

    dict(tag="SignalFront", sub="Lighting", clips=5,
         circuits=[("Turn", "wire_org", 0.0028), ("Park", "wire_wht", 0.0028),
                   ("Ground", "wire_brn", 0.0028)],
         route=["FuseBoxEng", "BayFrontL", "HeadlampL", "HeadlampR"],
         grommets=[],
         ends=[("FuseBox", "FuseBoxEng"), ("LampR", "HeadlampR")],
         note="front turn signal and parking lamp harness"),

    dict(tag="TailLamp", sub="Lighting", clips=7,
         circuits=[("Tail", "wire_wht", 0.0028), ("Brake", "wire_red", 0.0028),
                   ("Turn", "wire_org", 0.0028), ("Ground", "wire_brn", 0.0028)],
         route=["BCM", "SillL", "SillRearL", "RearBulkL", "TrunkL", "TailL", "TailR"],
         grommets=[(3, "RearBulkhead")],
         ends=[("BCM", "BCM"), ("LampR", "TailR")],
         note="rear lamp harness, body control module to both tail units"),

    dict(tag="PlateLamp", sub="Lighting", clips=3,
         circuits=[("Power", "wire_wht", 0.0026), ("Ground", "wire_brn", 0.0026)],
         route=["TrunkR", "PlateLamp"],
         grommets=[],
         ends=[("Trunk", "TrunkR"), ("Lamp", "PlateLamp")],
         note="licence plate lamp feed"),

    # ---------------------------------------------------------------- dash / cabin
    dict(tag="DashMain", sub="Dash", clips=7,
         circuits=[("Power", "wire_red", 0.0036), ("Ground", "wire_blk", 0.0032),
                   ("Signal", "wire_grn", 0.0028), ("Signal2", "wire_ylw", 0.0028)],
         route=["BulkheadC", "DashL", "Cluster", "FuseBoxInt", "DashR"],
         grommets=[(0, "Bulkhead")],
         ends=[("Bulkhead", "BulkheadC"), ("FuseBox", "FuseBoxInt")],
         note="dash main harness, firewall to instrument panel fuse box"),

    dict(tag="Instrument", sub="Dash", clips=5,
         circuits=[("Signal", "wire_pur", 0.0026), ("Signal2", "wire_gry", 0.0026),
                   ("Ground", "wire_blk", 0.0026)],
         route=["Cluster", "DashL", "ECU", "TCU"],
         grommets=[],
         ends=[("Cluster", "Cluster"), ("TCU", "TCU")],
         note="instrument cluster to ECM / TCM data harness"),

    dict(tag="DashSwitch", sub="Dash", clips=6,
         circuits=[("Power", "wire_red", 0.0028), ("Signal", "wire_grn", 0.0026),
                   ("Signal2", "wire_ylw", 0.0026)],
         route=["SwHeadlamp", "SwWiper", "SwHazard", "SwIgnition", "FuseBoxInt"],
         grommets=[],
         ends=[("Switch", "SwHeadlamp"), ("FuseBox", "FuseBoxInt")],
         note="dash switch bank harness"),

    dict(tag="CabinFloor", sub="Cabin", clips=9,
         circuits=[("Power", "wire_red", 0.0034), ("Ground", "wire_blk", 0.0030),
                   ("Signal", "wire_grn", 0.0028)],
         route=["FuseBoxInt", "ConsoleMid", "FloorMid", "SillR", "SillRearR", "RearBulkR"],
         grommets=[(5, "RearBulkhead")],
         ends=[("FuseBox", "FuseBoxInt"), ("Rear", "RearBulkR")],
         note="cabin floor harness, front fuse box to rear body"),

    dict(tag="Console", sub="Cabin", clips=4,
         circuits=[("Power", "wire_red", 0.0028), ("Signal", "wire_blu", 0.0026),
                   ("Ground", "wire_blk", 0.0026)],
         route=["Radio", "ConsoleMid", "FuseBoxInt"],
         grommets=[],
         ends=[("Radio", "Radio"), ("FuseBox", "FuseBoxInt")],
         note="centre console and radio harness"),

    dict(tag="HVAC", sub="Cabin", clips=4,
         circuits=[("Power", "wire_blu", 0.0030), ("Ground", "wire_blk", 0.0028)],
         route=["Blower", "DashR", "FuseBoxInt"],
         grommets=[],
         ends=[("Blower", "Blower"), ("FuseBox", "FuseBoxInt")],
         note="heater blower motor harness"),

    dict(tag="SeatPower", sub="Cabin", clips=5,
         circuits=[("Power", "wire_red", 0.0030), ("Ground", "wire_blk", 0.0028)],
         route=["FuseBoxInt", "ConsoleMid", "SeatFL", "SeatFR"],
         grommets=[],
         ends=[("FuseBox", "FuseBoxInt"), ("SeatR", "SeatFR")],
         note="power seat feed harness"),

    dict(tag="AudioRear", sub="Cabin", clips=6,
         circuits=[("Signal", "wire_blu", 0.0026), ("Signal2", "wire_gry", 0.0026)],
         route=["Radio", "SillL", "SillRearL", "SpkRearL", "SpkRearR"],
         grommets=[],
         ends=[("Radio", "Radio"), ("SpeakerR", "SpkRearR")],
         note="rear speaker harness"),

    # ---------------------------------------------------------------- body / rear
    dict(tag="BodyRear", sub="Body", clips=8,
         circuits=[("Power", "wire_red", 0.0032), ("Ground", "wire_blk", 0.0030),
                   ("Signal", "wire_grn", 0.0028)],
         route=["RearBulkR", "TrunkR", "TrunkL", "RearBulkL", "GroundRear"],
         grommets=[(0, "RearBulkhead")],
         ends=[("Bulkhead", "RearBulkR"), ("Ground", "GroundRear")],
         note="rear body harness and ground"),

    dict(tag="FuelPump", sub="Body", clips=5,
         circuits=[("Feed", "wire_red", 0.0032), ("Level", "wire_grn", 0.0026),
                   ("Ground", "wire_blk", 0.0028)],
         route=["FuelPump", "FloorMid", "SillR", "FuseBoxInt"],
         grommets=[(0, "Floor")],
         ends=[("Pump", "FuelPump"), ("FuseBox", "FuseBoxInt")],
         note="fuel pump module feed and level sender"),

    dict(tag="Roof", sub="Body", clips=6,
         circuits=[("Power", "wire_wht", 0.0028), ("Ground", "wire_brn", 0.0026)],
         route=["BCM", "RoofFront", "RoofL", "DomeLamp", "RoofR", "Antenna"],
         grommets=[],
         ends=[("BCM", "BCM"), ("Antenna", "Antenna")],
         note="headliner harness, dome lamp and antenna feed"),

    # ---------------------------------------------------------------- doors
    dict(tag="DoorFL", sub="Door", clips=5,
         circuits=[("Power", "wire_red", 0.0028), ("Signal", "wire_grn", 0.0026),
                   ("Signal2", "wire_ylw", 0.0026), ("Ground", "wire_blk", 0.0026)],
         route=["BulkheadL", "DashL", "DoorGromFL", "SwWindowFL", "SpkDoorFL", "MirrorL"],
         grommets=[(2, "DoorGrommet")],
         ends=[("Body", "BulkheadL"), ("Mirror", "MirrorL")],
         note="front-left door harness, body to door through the A-pillar grommet"),

    dict(tag="DoorFR", sub="Door", clips=5,
         circuits=[("Power", "wire_red", 0.0028), ("Signal", "wire_grn", 0.0026),
                   ("Signal2", "wire_ylw", 0.0026), ("Ground", "wire_blk", 0.0026)],
         route=["BulkheadR", "DashR", "DoorGromFR", "SwWindowFR", "SpkDoorFR", "MirrorR"],
         grommets=[(2, "DoorGrommet")],
         ends=[("Body", "BulkheadR"), ("Mirror", "MirrorR")],
         note="front-right door harness, body to door through the A-pillar grommet"),

    dict(tag="DoorRL", sub="Door", clips=4,
         circuits=[("Power", "wire_red", 0.0028), ("Signal", "wire_blu", 0.0026),
                   ("Ground", "wire_blk", 0.0026)],
         route=["SillL", "DoorGromRL", "SpkDoorRL"],
         grommets=[(1, "DoorGrommet")],
         ends=[("Body", "SillL"), ("Speaker", "SpkDoorRL")],
         note="rear-left door harness through the B-pillar grommet"),

    dict(tag="DoorRR", sub="Door", clips=4,
         circuits=[("Power", "wire_red", 0.0028), ("Signal", "wire_blu", 0.0026),
                   ("Ground", "wire_blk", 0.0026)],
         route=["SillR", "DoorGromRR", "SpkDoorRR"],
         grommets=[(1, "DoorGrommet")],
         ends=[("Body", "SillR"), ("Speaker", "SpkDoorRR")],
         note="rear-right door harness through the B-pillar grommet"),

    # ---------------------------------------------------------------- chassis
    dict(tag="ChassisRear", sub="Chassis", clips=7,
         circuits=[("Power", "wire_red", 0.0032), ("Ground", "wire_blk", 0.0030)],
         route=["GroundBody", "SillR", "SillRearR", "WheelRR", "WheelRL", "GroundRear"],
         grommets=[],
         ends=[("Body", "GroundBody"), ("Ground", "GroundRear")],
         note="underbody chassis harness and rear ground"),
]


# ---------------------------------------------------------------------------
# geometry helpers
# ---------------------------------------------------------------------------

def _catmull_rom(pts, samples_per_span=6):
    """Smooth a poly-line through its waypoints (Catmull-Rom).

    Real looms do not run in straight lines between components - they bend
    around structure.  This gives every run plausible curvature while still
    passing exactly through the waypoints.
    """
    P = [Vector(p) for p in pts]
    if len(P) < 2:
        return [tuple(p) for p in P]
    if len(P) == 2:
        out = []
        for i in range(samples_per_span + 1):
            t = i / float(samples_per_span)
            out.append(tuple(P[0].lerp(P[1], t)))
        return out
    ext = [P[0] + (P[0] - P[1])] + P + [P[-1] + (P[-1] - P[-2])]
    out = []
    for i in range(len(P) - 1):
        p0, p1, p2, p3 = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]
        for s in range(samples_per_span):
            t = s / float(samples_per_span)
            t2, t3 = t * t, t * t * t
            p = 0.5 * ((2 * p1) + (-p0 + p2) * t +
                       (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 +
                       (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
            out.append(tuple(p))
    out.append(tuple(P[-1]))
    return out


def _resample(poly, step):
    """Resample a poly-line to roughly uniform ``step`` spacing."""
    P = [Vector(p) for p in poly]
    if len(P) < 2:
        return [tuple(p) for p in P]
    total = sum((P[i + 1] - P[i]).length for i in range(len(P) - 1))
    n = max(2, int(round(total / step)) + 1)
    segs = [(P[i + 1] - P[i]).length for i in range(len(P) - 1)]
    out = [P[0]]
    acc = 0.0
    target = total / (n - 1)
    want = target
    for i, L in enumerate(segs):
        if L < 1e-12:
            continue
        while want <= acc + L + 1e-12:
            t = (want - acc) / L
            out.append(P[i].lerp(P[i + 1], t))
            want += target
        acc += L
    if (out[-1] - P[-1]).length > 1e-9:
        out.append(P[-1])
    return [tuple(p) for p in out]


def _offset_poly(poly, offset, up=(0, 0, 1)):
    """Shift a poly-line sideways by ``offset`` (used to fan a bundle out)."""
    if abs(offset) < 1e-9:
        return list(poly)
    P = [Vector(p) for p in poly]
    upv = Vector(up)
    out = []
    for i, p in enumerate(P):
        if i == 0:
            d = P[1] - P[0]
        elif i == len(P) - 1:
            d = P[-1] - P[-2]
        else:
            d = P[i + 1] - P[i - 1]
        if d.length < 1e-9:
            d = Vector((1, 0, 0))
        d.normalize()
        ref = upv if abs(d.dot(upv)) < 0.9 else Vector((1, 0, 0))
        side = d.cross(ref)
        if side.length < 1e-9:
            side = Vector((0, 1, 0))
        side.normalize()
        out.append(tuple(p + side * offset))
    return out


def _sweep(poly, radius, seg=8, trace=True):
    """Sweep a circle along ``poly``.

    Returns ``(verts, faces, trace_t)`` where ``trace_t`` is the normalised arc
    length at each vertex - the baked coordinate the glow shader reads.
    """
    P = [Vector(p) for p in poly]
    n = len(P)
    # cumulative arc length -> normalised trace coordinate
    cum = [0.0]
    for i in range(1, n):
        cum.append(cum[-1] + (P[i] - P[i - 1]).length)
    total = cum[-1] if cum[-1] > 1e-9 else 1.0
    tnorm = [c / total for c in cum]

    up = Vector((0, 0, 1))
    rings = []
    for i, p in enumerate(P):
        if i == 0:
            d = P[1] - P[0]
        elif i == n - 1:
            d = P[-1] - P[-2]
        else:
            d = P[i + 1] - P[i - 1]
        if d.length < 1e-9:
            d = Vector((1, 0, 0))
        d.normalize()
        ref = up if abs(d.dot(up)) < 0.9 else Vector((1, 0, 0))
        n1 = d.cross(ref)
        if n1.length < 1e-9:
            n1 = Vector((0, 1, 0))
        n1.normalize()
        n2 = d.cross(n1).normalized()
        ring = []
        for k in range(seg):
            a = TAU * k / seg
            ring.append(tuple(p + n1 * (radius * math.cos(a)) + n2 * (radius * math.sin(a))))
        rings.append(ring)

    verts = []
    trace = []
    for i, ring in enumerate(rings):
        for v in ring:
            verts.append(v)
            trace.append(tnorm[i] if trace else 0.0)
    faces = []
    for i in range(n - 1):
        for k in range(seg):
            k2 = (k + 1) % seg
            a = i * seg + k
            b = i * seg + k2
            c = (i + 1) * seg + k2
            d2 = (i + 1) * seg + k
            faces.append((a, b, c, d2))
    # end caps
    faces.append(tuple(range(seg - 1, -1, -1)))
    base = (n - 1) * seg
    faces.append(tuple(range(base, base + seg)))
    return verts, faces, trace


def _split_at_waypoints(poly, waypoints, tol=0.02):
    """Split a dense poly-line into segments at the given waypoints.

    Each returned piece is a separately removable section of the run, which is
    how a real harness is built (and serviced).
    """
    if not waypoints:
        return [poly]
    P = [Vector(p) for p in poly]
    idxs = []
    for w in waypoints:
        wv = Vector(w)
        best, bd = 0, 1e9
        for i, p in enumerate(P):
            d = (p - wv).length
            if d < bd:
                bd, best = d, i
        if bd <= tol and best not in idxs:
            idxs.append(best)
    idxs = sorted(set([0] + idxs + [len(P) - 1]))
    out = []
    for a, b in zip(idxs[:-1], idxs[1:]):
        if b - a >= 1:
            out.append([tuple(p) for p in P[a:b + 1]])
    return out or [poly]


# ---------------------------------------------------------------------------
# builders
# ---------------------------------------------------------------------------

def _wire(reg, mats, name, poly, radius, mat_key, coll, meta, seg=8):
    """One wire segment: a swept tube with a baked trace coordinate."""
    verts, faces, trace = _sweep(poly, radius, seg=seg)
    # keep the object origin at the run start so the manifest offset is meaningful
    loc = (poly[0][0], poly[0][1], poly[0][2])
    ob = reg.add(name, verts, faces, coll, mats[mat_key], meta=meta,
                 smooth=True, loc=loc)
    # bake the trace coordinate as a mesh attribute (POINT domain, float)
    me = ob.data
    try:
        attr = me.attributes.new(name="trace_t", type="FLOAT", domain="POINT")
        for i, t in enumerate(trace):
            attr.data[i].value = float(t)
    except Exception:
        pass
    # and as object custom properties so the data survives any mesh rebuild
    ob["trace_len"] = round(sum((C.Vector(poly[i + 1]) - C.Vector(poly[i])).length
                                for i in range(len(poly) - 1)), 6)
    ob["trace_pts"] = [round(c, 5) for p in poly for c in p]
    ob["trace_attr"] = "trace_t"
    ob["wire_radius"] = radius
    ob["wire_material"] = mat_key
    return ob


def _grommet(reg, mats, name, pos, direction, radius, coll, meta):
    """A bulkhead grommet: a rubber ring the loom passes through."""
    ex, ey, ez = C.frame(direction)
    c = C.Vector(pos)
    seg = 12
    r_in, r_out = radius, radius * 1.85
    thick = radius * 1.1
    verts = []
    for zz in (-thick * 0.5, thick * 0.5):
        for rr in (r_out, r_in):
            for k in range(seg):
                a = TAU * k / seg
                p = c + ex * (rr * math.cos(a)) + ey * (rr * math.sin(a)) + ez * zz
                verts.append((p.x, p.y, p.z))
    faces = []
    def vi(iz, ir, k):
        return iz * 2 * seg + ir * seg + k
    for k in range(seg):
        k2 = (k + 1) % seg
        faces.append((vi(0, 0, k), vi(0, 0, k2), vi(1, 0, k2), vi(1, 0, k)))
        faces.append((vi(0, 1, k2), vi(0, 1, k), vi(1, 1, k), vi(1, 1, k2)))
        faces.append((vi(0, 0, k), vi(0, 1, k), vi(0, 1, k2), vi(0, 0, k2)))
        faces.append((vi(1, 0, k2), vi(1, 1, k2), vi(1, 1, k), vi(1, 0, k)))
    return reg.add(name, verts, faces, coll, mats["rubber"], meta=meta,
                   smooth=True, loc=pos)


def _wire_clip(reg, mats, name, pos, direction, radius, coll, meta):
    """A P-clip / loom retainer holding the run to the body."""
    ex, ey, ez = C.frame(direction)
    c = C.Vector(pos)
    seg = 8
    r = radius * 1.5
    verts = []
    for zz in (0.0, radius * 0.9):
        for k in range(seg):
            a = TAU * k / seg
            p = c + ex * (r * math.cos(a)) + ey * (r * math.sin(a)) + ez * zz
            verts.append((p.x, p.y, p.z))
    faces = []
    for k in range(seg):
        k2 = (k + 1) % seg
        faces.append((k, k2, seg + k2, seg + k))
    faces.append(tuple(range(seg - 1, -1, -1)))
    faces.append(tuple(range(seg, 2 * seg)))
    return reg.add(name, verts, faces, coll, mats["plastic_blk_m"], meta=meta,
                   smooth=False, loc=pos)


def _connector(reg, mats, name, pos, direction, size, coll, meta):
    """A multi-pin plug shell at the end of a run."""
    ex, ey, ez = C.frame(direction)
    c = C.Vector(pos)
    w, h, d = size
    verts = []
    for zz in (-d * 0.5, d * 0.5):
        for (px, py) in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
            p = c + ex * px + ey * py + ez * zz
            verts.append((p.x, p.y, p.z))
    faces = [(0, 1, 2, 3), (7, 6, 5, 4),
             (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    return reg.add(name, verts, faces, coll, mats["connector"], meta=meta,
                   smooth=False, loc=pos)


# ---------------------------------------------------------------------------
# main entry point
# ---------------------------------------------------------------------------

def build_wiring(reg, mats, surf, M):
    """Build every harness: wires, grommets, clips and connectors."""
    p = mats
    stats = {"wires": 0, "grommets": 0, "clips": 0, "connectors": 0,
             "harnesses": 0, "length_m": 0.0}
    systems = {}

    for h in HARNESSES:
        tag = h["tag"]
        sub = h["sub"]
        coll = "Electrical_" + sub
        route_keys = h["route"]
        waypoints = [N(k) for k in route_keys]
        circuits = h["circuits"]
        n_circ = len(circuits)

        # smooth + resample the centreline once, then fan the bundle out
        centre = _resample(_catmull_rom(waypoints, 6), 0.045)
        # split the run into removable segments at the waypoints
        pieces = _split_at_waypoints(centre, waypoints, tol=0.06)

        # bundle fan-out: spread the circuits around the centreline
        spread = 0.0075
        for ci, (cdetail, mkey, radius) in enumerate(circuits):
            off = (ci - (n_circ - 1) / 2.0) * spread
            for si, piece in enumerate(pieces):
                poly = _offset_poly(piece, off)
                if len(poly) < 2:
                    continue
                seq = reg.next_seq("EL", "Wire", tag)
                name = reg.make_name("EL", "Wire", tag, seq)
                meta = {"group": "EL", "sub": "Wire_" + sub, "part": "Wire",
                        "mat_key": mkey, "asmb": True,
                        "harness": tag, "circuit": cdetail,
                        "segment": si + 1, "segments": len(pieces),
                        "notes": "%s harness, %s circuit, segment %d/%d"
                                 % (tag, cdetail, si + 1, len(pieces))}
                _wire(reg, mats, name, poly, radius, mkey, coll, meta)
                stats["wires"] += 1
                stats["length_m"] += sum(
                    (C.Vector(poly[i + 1]) - C.Vector(poly[i])).length
                    for i in range(len(poly) - 1))

        # ---- grommets where the run passes through a panel -------------------
        for (ri, gdetail) in h.get("grommets", []):
            if ri >= len(route_keys):
                continue
            pos = N(route_keys[ri])
            nxt = N(route_keys[min(ri + 1, len(route_keys) - 1)])
            prv = N(route_keys[max(ri - 1, 0)])
            d = C.Vector(nxt) - C.Vector(prv)
            if d.length < 1e-6:
                d = C.Vector((1, 0, 0))
            seq = reg.next_seq("EL", "Grommet", tag)
            name = reg.make_name("EL", "Grommet", tag, seq)
            meta = {"group": "EL", "sub": "Wire_" + sub, "part": "Grommet",
                    "mat_key": "rubber", "asmb": True, "harness": tag,
                    "notes": "%s %s grommet" % (tag, gdetail)}
            _grommet(reg, mats, name, pos, tuple(d), 0.016, coll, meta)
            stats["grommets"] += 1

        # ---- clips along the run --------------------------------------------
        n_clips = int(h.get("clips", 0))
        if n_clips > 0 and len(centre) > 2:
            for k in range(n_clips):
                t = (k + 1) / float(n_clips + 1)
                i = min(len(centre) - 1, max(1, int(round(t * (len(centre) - 1)))))
                pos = centre[i]
                d = C.Vector(centre[min(i + 1, len(centre) - 1)]) - C.Vector(centre[i - 1])
                if d.length < 1e-6:
                    d = C.Vector((1, 0, 0))
                seq = reg.next_seq("EL", "WireClip", tag)
                name = reg.make_name("EL", "WireClip", tag, seq)
                meta = {"group": "EL", "sub": "Wire_" + sub, "part": "WireClip",
                        "mat_key": "plastic_blk_m", "asmb": True, "harness": tag,
                        "notes": "%s loom retainer clip" % tag}
                _wire_clip(reg, mats, name, pos, tuple(d), 0.010, coll, meta)
                stats["clips"] += 1

        # ---- connectors at the run ends -------------------------------------
        for (cdetail, node) in h.get("ends", []):
            pos = N(node)
            if len(centre) > 1:
                d = C.Vector(centre[1]) - C.Vector(centre[0])
            else:
                d = C.Vector((1, 0, 0))
            if d.length < 1e-6:
                d = C.Vector((1, 0, 0))
            seq = reg.next_seq("EL", "WireConn", tag)
            name = reg.make_name("EL", "WireConn", tag, seq)
            meta = {"group": "EL", "sub": "Wire_" + sub, "part": "WireConn",
                    "mat_key": "connector", "asmb": True, "harness": tag,
                    "notes": "%s %s connector shell" % (tag, cdetail)}
            _connector(reg, mats, name, pos, tuple(d), (0.030, 0.022, 0.018),
                       coll, meta)
            stats["connectors"] += 1

        stats["harnesses"] += 1
        systems[tag] = {"sub": sub, "circuits": n_circ, "segments": len(pieces),
                        "route": route_keys,
                        "wires": n_circ * len(pieces),
                        "clips": n_clips,
                        "grommets": len(h.get("grommets", [])),
                        "connectors": len(h.get("ends", []))}

    M["wiring"] = stats
    M["wiring_systems"] = systems
    return stats
