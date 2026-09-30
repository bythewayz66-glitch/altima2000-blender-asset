"""Ground-truth probe: build the car in memory and dump the part inventory.

Runs :func:`build_altima.build` only -- no exports, no module files, no
assembly file -- so the sequence prefix map can be derived from the real part
names instead of guessed.  Writes JSON to ``ALTIMA_PROBE_OUT`` (default
``/workspace/probe_parts.json``) and prints a compact summary.

Usage:
    blender -b -noaudio --python probe_parts.py
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bpy  # noqa: E402

import build_altima as BA  # noqa: E402
from altima import builder as B, sequence as SQ  # noqa: E402

OUT = os.environ.get("ALTIMA_PROBE_OUT", "/workspace/probe_parts.json")

t0 = time.time()
scene, reg, mats, seq_map, seq_unclaimed = BA.build()
print("[PROBE %5.1fs] built" % (time.time() - t0))

parts = [r["name"] for r in reg.parts]
colls = sorted({r["collection"] for r in reg.parts})

doc = {
    "part_count": len(parts),
    "collection_count": len(colls),
    "parts": parts,
    "collections": colls,
    "collection_counts": {c: sum(1 for r in reg.parts if r["collection"] == c) for c in colls},
    "collection_of": dict(B.COLLECTION_OF),
    "modules": {k: list(v) for k, v in sorted(B.ALL_MODULES.items())},
    "module_categories": {
        k: sorted({B.COLLECTION_OF.get(s, s) for s in v}) for k, v in sorted(B.ALL_MODULES.items())
    },
    "prefixes": sorted({n[len("ALTIMA2000_"):].split("_")[0] + "_" + (
        n[len("ALTIMA2000_"):].split("_")[1] if len(n[len("ALTIMA2000_"):].split("_")) > 1 else "")
        for n in parts}),
    "steps": [
        {
            "step": i + 1,
            "empty": SQ.step_empty_name(i + 1),
            "key": s["key"],
            "title": s["title"],
            "part_count": len([1 for nm, k in seq_map.items() if k == i + 1]),
        }
        for i, s in enumerate(SQ.STEPS)
    ],
    "seq_claimed": len(seq_map),
    "seq_unclaimed": sorted(seq_unclaimed),
    "seq_unclaimed_count": len(seq_unclaimed),
}

with open(OUT, "w") as fh:
    json.dump(doc, fh, indent=1)

print("[PROBE] parts=%d collections=%d unclaimed=%d"
      % (doc["part_count"], doc["collection_count"], doc["seq_unclaimed_count"]))
print("[PROBE] wrote", OUT)
