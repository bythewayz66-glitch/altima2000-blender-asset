"""Sequence coverage analysis: which parts are still unclaimed, by prefix family."""
import collections
import json
import sys

sys.path.insert(0, "/workspace/documents/altima2000_v5/source")
from altima import sequence as SQ  # noqa: E402

d = json.load(open("/workspace/probe_parts.json"))
parts = d["parts"]
mapping, unclaimed = SQ.resolve(parts)

print("STEP_COUNT", SQ.STEP_COUNT, "mapped", len(mapping), "unclaimed", len(unclaimed))
print()

fam = collections.Counter()
for n in unclaimed:
    t = n[len("ALTIMA2000_"):].split("_")
    fam["_".join(t[:2])] += 1
print("--- UNCLAIMED FAMILIES ---")
for k, v in sorted(fam.items(), key=lambda x: -x[1]):
    print("%-30s %5d" % (k, v))

print()
print("--- UNCLAIMED GROUP CODES ---")
grp = collections.Counter(n.split("_")[1] for n in unclaimed)
for k, v in sorted(grp.items(), key=lambda x: -x[1]):
    print("%-8s %5d" % (k, v))

print()
print("--- SAFETY PART NAMES ---")
for n in unclaimed:
    if "SAFE" in n or "Safety" in n or "Airbag" in n or "Seatbelt" in n:
        print("  ", n)

print()
print("--- NON-PREFIXED (no trailing family token) ---")
odd = [n for n in unclaimed if n.split("_")[1] not in
       ("SHEL", "TRN", "SAFE", "EL")]
print("count", len(odd))
for n in odd[:40]:
    print("  ", n)
