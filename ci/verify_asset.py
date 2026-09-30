"""CI check for the ALTIMA2000 asset.

Opens the built assembly headless and asserts the invariants the handoff
depends on:

  * the part count matches the manifest
  * every part name matches the documented naming regex
  * there are no duplicate object names
  * the linked assembly file resolves every module (no missing libraries)
  * the linked assembly holds the same number of parts as the master

Exits non-zero (and prints CI_RESULT FAIL) if any assertion fails, so the
GitHub Actions job fails loudly rather than silently passing.

Run locally with:
    blender -b --factory-startup --python ci/verify_asset.py
"""
import json
import os
import re
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

MASTER = os.path.join(ROOT, "altima2000_assembly.blend")
LINKED = os.path.join(ROOT, "altima2000_assembly_linked.blend")
MANIFEST = os.path.join(ROOT, "altima2000_manifest.json")
BUILDER = os.path.join(ROOT, "source", "altima", "builder.py")

FAIL = []
PASS = []


def check(label, ok, detail=""):
    (PASS if ok else FAIL).append(label)
    print("%-4s %-52s %s" % ("PASS" if ok else "FAIL", label, detail))


def fail_fast(msg):
    print("CI_ERROR", msg)
    print("CI_RESULT FAIL")
    sys.exit(1)


for path in (MASTER, LINKED, MANIFEST, BUILDER):
    if not os.path.exists(path):
        fail_fast("missing required file: %s" % path)

# ---- the naming regex is read from the generator, never duplicated here ----
src = open(BUILDER).read()
m = re.search(r"NAME_RE\s*=\s*re\.compile\(\s*r?[\"']([^\"']+)[\"']", src)
if not m:
    fail_fast("could not read NAME_RE out of %s" % BUILDER)
NAME_RE = re.compile(m.group(1))
print("NAME_RE =", NAME_RE.pattern)

doc = json.load(open(MANIFEST))
expected = doc["part_count"]
print("MANIFEST_PART_COUNT", expected)

# ---- master assembly ------------------------------------------------------
bpy.ops.wm.open_mainfile(filepath=MASTER)
sc = bpy.context.scene
parts = [o for o in sc.objects
         if o.type == "MESH" and o.name.startswith("ALTIMA2000_")]
print("MASTER_PART_COUNT", len(parts))

check("part count matches the manifest", len(parts) == expected,
      "built=%d manifest=%d" % (len(parts), expected))

bad = [o.name for o in parts if not NAME_RE.match(o.name)]
check("every part name matches the naming regex", len(bad) == 0,
      "bad=%d %s" % (len(bad), bad[:5]))

names = [o.name for o in sc.objects]
dupes = len(names) - len(set(names))
check("no duplicate object names", dupes == 0, "dupes=%d" % dupes)

# ---- linked assembly ------------------------------------------------------
bpy.ops.wm.open_mainfile(filepath=LINKED)
sc2 = bpy.context.scene
libs = [c for c in bpy.data.collections if c.library is not None]
missing = [c.name for c in libs if c.library.is_missing]
check("linked assembly resolves every module", len(missing) == 0,
      "linked=%d missing=%d" % (len(libs), len(missing)))

linked_parts = [o for o in sc2.objects
                if o.type == "MESH" and o.name.startswith("ALTIMA2000_")]
check("linked assembly part count matches the master",
      len(linked_parts) == len(parts),
      "linked=%d master=%d" % (len(linked_parts), len(parts)))

# ---- module link integrity: every module .blend is present and non-empty ---
MODS = ["engine", "drivetrain", "suspension", "wheels", "brakes", "exhaust", "doors"]
for mod in MODS:
    p = os.path.join(ROOT, "altima2000_module_%s.blend" % mod)
    ok = os.path.exists(p) and os.path.getsize(p) > 1000
    check("module %s present" % mod, ok,
          "%d bytes" % (os.path.getsize(p) if os.path.exists(p) else 0))

print("")
print("CI_SUMMARY pass=%d fail=%d" % (len(PASS), len(FAIL)))
if FAIL:
    print("CI_FAILED:", FAIL)
    print("CI_RESULT FAIL")
    sys.exit(1)
print("CI_RESULT ALL_PASS")
