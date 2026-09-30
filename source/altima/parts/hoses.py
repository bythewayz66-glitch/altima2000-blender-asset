"""Real, physically modelled hoses and tie straps for the ALTIMA2000 asset.

This module replaces the legacy "bulk hose" population - straight tube
primitives dropped into a service envelope - with real routed geometry:

* every **hose** is a swept tube following a Catmull-Rom smoothed path between
  the components it actually connects, split into removable segments at its
  waypoints (exactly how the wiring is built), and
* every **tie strap** is a swept band wrapping the hose it secures.

Each part is its own object with its own name, its own sub-collection and its
own manifest row, and carries the same baked ``trace_t`` arc-length attribute
as the wiring, so the touch-activated glow / progressive trace works on hoses
and straps too.

The legacy straight-geometry hose blocks in ``interior.build_bulk`` are removed
so nothing is double-counted.
"""

import math

from mathutils import Vector

from .. import meshutils as mu
from . import common as C
from . import wiring as WR

TAU = math.pi * 2.0

# ---------------------------------------------------------------------------
# routing nodes - real component positions (world metres, +X forward, +Y left)
# ---------------------------------------------------------------------------
NODES = {
    # cooling circuit
    "RadiatorTop":   (1.500, 0.250, 0.930),
    "RadiatorBot":   (1.500, -0.250, 0.560),
    "Thermostat":    (1.050, 0.200, 0.900),
    "WaterPump":     (0.950, 0.150, 0.620),
    "HeaterCore":    (0.620, 0.300, 0.800),
    "CoolantRes":    (1.540, 0.400, 0.760),
    "FirewallL":     (0.660, 0.300, 0.720),
    "FirewallR":     (0.660, -0.300, 0.720),
    # intake / emission
    "IntakeManifold": (1.000, 0.200, 0.780),
    "ThrottleBody":  (0.940, 0.430, 0.730),
    "AirBox":        (1.380, 0.050, 0.720),
    "EVAPCanister":  (1.300, -0.350, 0.450),
    "PurgeValve":    (1.120, 0.180, 0.800),
    # accessories
    "PSPump":        (0.900, -0.300, 0.550),
    "PSRack":        (1.480, 0.330, 0.400),
    "ACCompressor":  (0.880, -0.280, 0.420),
    "ACCondenser":   (1.900, 0.000, 0.600),
    "ACDrier":       (1.960, -0.300, 0.560),
    # brakes / fluids
    "BrakeBooster":  (0.720, -0.300, 0.720),
    "WasherBottle":  (2.115, -0.330, 0.630),
    "HoodNozzleL":   (1.700, 0.400, 0.960),
    "HoodNozzleR":   (1.700, -0.400, 0.960),
    "FuelTank":      (-0.700, 0.020, 0.400),
    "FillerNeck":    (-1.700, 0.700, 0.620),
    "FuelRail":      (1.020, 0.120, 0.760),
    # routing waypoints
    "BayTopL":       (1.500, 0.560, 0.900),
    "BayTopR":       (1.500, -0.560, 0.900),
    "BayFrontL":     (2.150, 0.520, 0.760),
    "BayFrontR":     (2.150, -0.520, 0.760),
    "SillL":         (0.000, 0.700, 0.300),
    "SillR":         (0.000, -0.700, 0.300),
    "SillRearL":     (-1.200, 0.700, 0.300),
    "UnderFloorL":   (-0.400, 0.500, 0.240),
    "UnderFloorR":   (-0.400, -0.500, 0.240),
    "RearBulkL":     (-1.500, 0.400, 0.600),
}


def N(key):
    """World position of a routing node."""
    return NODES[key]


# ---------------------------------------------------------------------------
# hose table
#
#   tag      - component family (goes into the part name)
#   sub      - sub-collection (an existing one - no tree change needed)
#   grp      - group code
#   mat      - material key (carries the trace shader)
#   radius   - hose outside radius, metres
#   route    - [node key, ...] the physical run, in order
#   straps   - how many tie straps secure the run
#   note     - manifest note
# ---------------------------------------------------------------------------
HOSES = [
    # ---------------------------------------------------------------- cooling
    dict(tag="RadiatorUpper", sub="Engine_Cooling", grp="EN", mat="hose_routed",
         radius=0.017, straps=2,
         route=["RadiatorTop", "BayTopL", "Thermostat"],
         note="upper radiator hose, radiator to thermostat housing"),
    dict(tag="RadiatorLower", sub="Engine_Cooling", grp="EN", mat="hose_routed",
         radius=0.017, straps=2,
         route=["RadiatorBot", "BayFrontR", "WaterPump"],
         note="lower radiator hose, radiator to water pump"),
    dict(tag="HeaterInlet", sub="Engine_Cooling", grp="EN", mat="hose_routed",
         radius=0.013, straps=3,
         route=["WaterPump", "FirewallL", "HeaterCore"],
         note="heater inlet hose, water pump through the firewall to the heater core"),
    dict(tag="HeaterOutlet", sub="Engine_Cooling", grp="EN", mat="hose_routed",
         radius=0.013, straps=3,
         route=["HeaterCore", "FirewallR", "Thermostat"],
         note="heater outlet hose, heater core back to the thermostat housing"),
    dict(tag="Bypass", sub="Engine_Cooling", grp="EN", mat="hose_routed",
         radius=0.011, straps=1,
         route=["Thermostat", "WaterPump"],
         note="coolant bypass hose, thermostat to water pump"),
    dict(tag="Reservoir", sub="Engine_Cooling", grp="EN", mat="hose_routed",
         radius=0.009, straps=2,
         route=["CoolantRes", "BayTopL", "RadiatorTop"],
         note="coolant reservoir overflow hose"),
    # ---------------------------------------------------------------- intake / emission
    dict(tag="VacuumBooster", sub="Brakes_Hydraulics", grp="BR", mat="hose_routed",
         radius=0.010, straps=2,
         route=["IntakeManifold", "FirewallR", "BrakeBooster"],
         note="brake booster vacuum hose, intake manifold to the booster"),
    dict(tag="VacuumLine", sub="Engine_Intake", grp="EN", mat="hose_routed",
         radius=0.006, straps=3,
         route=["IntakeManifold", "ThrottleBody", "PurgeValve", "BayTopR"],
         note="intake vacuum line, manifold to throttle body and purge valve"),
    dict(tag="EVAP", sub="Engine_Emission", grp="EM", mat="hose_routed",
         radius=0.008, straps=3,
         route=["EVAPCanister", "BayFrontR", "PurgeValve", "IntakeManifold"],
         note="EVAP purge hose, canister to purge valve and intake"),
    dict(tag="AirIntake", sub="Engine_Intake", grp="EN", mat="hose_routed",
         radius=0.032, straps=2,
         route=["AirBox", "BayTopL", "ThrottleBody"],
         note="air intake duct, air cleaner to throttle body"),
    # ---------------------------------------------------------------- accessories
    dict(tag="PowerSteering", sub="Engine_Accessory", grp="EN", mat="hose_routed",
         radius=0.010, straps=3,
         route=["PSPump", "BayFrontR", "PSRack"],
         note="power steering pressure hose, pump to rack"),
    dict(tag="ACRefrigerant", sub="Engine_Accessory", grp="EN", mat="hose_routed",
         radius=0.009, straps=3,
         route=["ACCompressor", "BayFrontR", "ACCondenser", "ACDrier", "FirewallR"],
         note="A/C refrigerant line, compressor to condenser, drier and evaporator"),
    # ---------------------------------------------------------------- fluids
    dict(tag="Washer", sub="Fluids_Body", grp="FL", mat="hose_routed",
         radius=0.005, straps=3,
         route=["WasherBottle", "BayTopR", "HoodNozzleR", "HoodNozzleL"],
         note="washer fluid hose, bottle to the hood nozzles"),
    dict(tag="FuelFiller", sub="Fluids_Body", grp="FL", mat="hose_routed",
         radius=0.024, straps=2,
         route=["FillerNeck", "SillRearL", "UnderFloorL", "FuelTank"],
         note="fuel filler hose, filler neck to the tank"),
    dict(tag="FuelFeed", sub="Fluids_Body", grp="FL", mat="hose_routed",
         radius=0.008, straps=4,
         route=["FuelTank", "UnderFloorR", "SillR", "FirewallR", "FuelRail"],
         note="fuel feed line, tank to the fuel rail"),
]


# ---------------------------------------------------------------------------
# geometry helpers
# ---------------------------------------------------------------------------

def _swept(reg, mats, name, poly, radius, mat_key, coll, meta, seg=10):
    """One swept tube with a baked trace coordinate (same contract as a wire)."""
    verts, faces, trace = WR._sweep(poly, radius, seg=seg)
    loc = (poly[0][0], poly[0][1], poly[0][2])
    ob = reg.add(name, verts, faces, coll, mats[mat_key], meta=meta,
                 smooth=True, loc=loc)
    me = ob.data
    try:
        attr = me.attributes.new(name="trace_t", type="FLOAT", domain="POINT")
        for i, t in enumerate(trace):
            attr.data[i].value = float(t)
    except Exception:
        pass
    ob["trace_len"] = round(sum((C.Vector(poly[i + 1]) - C.Vector(poly[i])).length
                                for i in range(len(poly) - 1)), 6)
    ob["trace_pts"] = [round(c, 5) for p in poly for c in p]
    ob["trace_attr"] = "trace_t"
    ob["hose_radius"] = radius
    ob["hose_material"] = mat_key
    return ob


def _strap(reg, mats, name, pos, direction, radius, coll, meta):
    """A tie strap: a swept band wrapping the hose at ``pos``."""
    d = C.Vector(direction)
    if d.length < 1e-9:
        d = C.Vector((1.0, 0.0, 0.0))
    d.normalize()
    up = C.Vector((0.0, 0.0, 1.0))
    ref = up if abs(d.dot(up)) < 0.9 else C.Vector((1.0, 0.0, 0.0))
    n1 = d.cross(ref)
    if n1.length < 1e-9:
        n1 = C.Vector((0.0, 1.0, 0.0))
    n1.normalize()
    n2 = d.cross(n1).normalized()
    c = C.Vector(pos)
    r = radius + 0.0035
    steps = 20
    poly = []
    for k in range(steps + 1):
        a = TAU * k / steps
        p = c + n1 * (r * math.cos(a)) + n2 * (r * math.sin(a))
        poly.append((p.x, p.y, p.z))
    return _swept(reg, mats, name, poly, 0.0022, "strap_nylon", coll, meta, seg=6)


# ---------------------------------------------------------------------------
# main entry point
# ---------------------------------------------------------------------------

def build_hoses(reg, mats, surf, M):
    """Build every routed hose and its tie straps."""
    stats = {"hoses": 0, "straps": 0, "length_m": 0.0, "systems": {}}
    for h in HOSES:
        tag = h["tag"]
        sub = h["sub"]
        grp = h["grp"]
        waypoints = [N(k) for k in h["route"]]
        centre = WR._resample(WR._catmull_rom(waypoints, 6), 0.040)
        pieces = WR._split_at_waypoints(centre, waypoints, tol=0.06)

        for si, piece in enumerate(pieces):
            if len(piece) < 2:
                continue
            seq = reg.next_seq(grp, "Hose", tag)
            name = reg.make_name(grp, "Hose", tag, seq)
            meta = {"group": grp, "sub": sub, "part": "Hose_" + tag,
                    "mat_key": h["mat"], "asmb": True, "hose": tag,
                    "segment": si + 1, "segments": len(pieces),
                    "notes": "%s, segment %d/%d" % (h["note"], si + 1, len(pieces))}
            _swept(reg, mats, name, piece, h["radius"], h["mat"], sub, meta, seg=10)
            stats["hoses"] += 1
            stats["length_m"] += sum(
                (C.Vector(piece[i + 1]) - C.Vector(piece[i])).length
                for i in range(len(piece) - 1))

        n_strap = int(h.get("straps", 0))
        if n_strap > 0 and len(centre) > 2:
            for k in range(n_strap):
                t = (k + 1) / float(n_strap + 1)
                i = min(len(centre) - 1,
                        max(1, int(round(t * (len(centre) - 1)))))
                pos = centre[i]
                d = (C.Vector(centre[min(i + 1, len(centre) - 1)])
                     - C.Vector(centre[i - 1]))
                seq = reg.next_seq("CL", "TieStrap", tag)
                name = reg.make_name("CL", "TieStrap", tag, seq)
                meta = {"group": "CL", "sub": "TieStrap", "part": "TieStrap_" + tag,
                        "mat_key": "strap_nylon", "asmb": True, "hose": tag,
                        "notes": "%s tie strap" % tag}
                _strap(reg, mats, name, pos, tuple(d), h["radius"],
                       "Fasteners_Clips", meta)
                stats["straps"] += 1

        stats["systems"][tag] = {
            "sub": sub, "group": grp, "radius_m": h["radius"],
            "segments": len(pieces), "straps": n_strap,
            "route": h["route"], "note": h["note"],
        }

    M["hoses"] = stats
    return stats
