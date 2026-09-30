# ALTIMA2000 — Handoff

**Asset:** 2000 Nissan Altima (L30) — photorealistic, fully disassemblable Blender asset
**Build:** `ALTIMA_BULK_SCALE=1.0` (full-density fasteners)
**Parts:** **1,539** individually selectable objects · **51** collections · **73** materials
**Generator:** Blender 4.5 LTS + `bpy`, fully procedural — no third-party mesh anywhere

---

## 1. What this asset is

A gold-metallic 2000 Nissan Altima sedan, generated entirely by Python, split into 1,539
separate named objects so the car can be taken apart and put back together like a real
one — just scaled down. Every part is its own object with its own name, its own
collection, and its own row in the manifest.

Real-world dimensions (metres, +Z up, origin at wheelbase mid-point on the ground):

| Dimension | Asset | 2000 Altima spec |
|---|---|---|
| Length | 4.7200 | 4.720 m (185.8 in) |
| Width | 1.7550 | 1.755 m (69.1 in) |
| Height | 1.4200 | 1.420 m (55.9 in) |
| Wheelbase | 2.6200 | 2.620 m (103.1 in) |

Coordinate system: **+X = forward (nose), +Y = left, +Z = up, Z = 0 is the ground.**
1 Blender unit = 1 metre.

---

## 2. Naming convention

```
ALTIMA2000_<GROUP>_<Tag>_<Detail>[_<NNN>]
```

Enforced at build time against a regex; every build reports `bad=0 dupes=0`.

| Field | Meaning | Examples |
|---|---|---|
| `ALTIMA2000` | Fixed asset prefix | |
| `<GROUP>` | 3–4 letter system code | `BODY`, `ENG`, `FAST`, `DRM` |
| `<Tag>` | Component family / assembly | `Door`, `ValveCover`, `Bolt` |
| `<Detail>` | Variant within the family — usually the corner | `FL`, `FR`, `RL`, `RR` |
| `_<NNN>` | Zero-padded sequence, only when a family has >1 instance | `_001` … `_162` |

Corner codes are from the driver's perspective: **F**ront/**R**ear + **L**eft/**R**ight,
so `_FL` is front-left. `_L` / `_R` alone mean "left side / right side".

### Group codes

| Code | System | Code | System |
|---|---|---|---|
| `BD` | Body panels | `SU` | Suspension |
| `SH` | Body structure | `SR` | Steering |
| `DR` | Door hardware | `BR` | Brakes |
| `DRM` | Door module (standalone) | `WH` | Wheels & tyres |
| `GL` | Glazing (glass) | `FT` | Bolts |
| `MI` | Mirrors | `SC` | Screws & studs |
| `MD` | Exterior trim / moldings | `CL` | Clips, retainers, rivets |
| `SL` | Seals & weatherstrip | `FL` | Fluids & reservoirs |
| `IN` | Interior trim | `EM` | Emission control |
| `ST` | Seats | `SF` | Safety & restraints |
| `EL` | Electrical harness | `BA` | Battery & power |
| `LM` | Lighting | `TR` | Transaxle / driveline |
| `EN` | Engine | `EX` | Exhaust |

### Examples straight out of the build

```
ALTIMA2000_BODY_Side_Body_R              body side outer pressing, right
ALTIMA2000_DRM_Skin_FL                   front-left door loose outer skin
ALTIMA2000_DRM_Hinge_FL_001              front-left door hinge, instance 1
ALTIMA2000_ENG_ValveCover_Cam            valve cover, camshaft side
ALTIMA2000_ENG_Crankshaft_Forged         forged crankshaft
ALTIMA2000_SUSP_LowerControlArm_FL       front-left lower control arm
ALTIMA2000_WHL_Tire_FL                   front-left tyre
ALTIMA2000_BRAK_Disc_RL                  rear-left brake disc
ALTIMA2000_FAST_Bolt_M6_001              M6 bolt, instance 1
ALTIMA2000_CLIP_TrimClip_Door_004        door trim clip, instance 4
```

---

## 3. Collection structure

Two-level tree: **16 top-level category collections**, each holding sub-collections.
51 sub-collections in total.

```
ALTIMA2000_Body          → Body_Panels, Body_Shell, Body_Structure
ALTIMA2000_Doors         → Door_FL, Door_FR, Door_RL, Door_RR, Door_Hardware
ALTIMA2000_DoorModule    → Door_Module_Skin, Door_Module_Frame,
                           Door_Module_Hardware, Door_Module_Glazing, Door_Module_Trim
ALTIMA2000_Engine        → Engine_LongBlock, Engine_Head, Engine_Intake, Engine_ExhaustSide,
                           Engine_Cooling, Engine_Fuel, Engine_Accessory, Engine_Emission
ALTIMA2000_Drivetrain    → Drivetrain_Transaxle, Drivetrain_Drive, Drivetrain_Mount
ALTIMA2000_Suspension    → Suspension_Front, Suspension_Rear, Suspension_Steering
ALTIMA2000_Wheels        → Wheel_FL, Wheel_FR, Wheel_RL, Wheel_RR, Wheel_Hardware
ALTIMA2000_Interior      → Interior_Dash, Interior_Seats, Interior_Console,
                           Interior_Trim, Interior_Insulation
ALTIMA2000_Electrical    → Electrical_Harness, Electrical_Battery, Electrical_Modules,
                           Electrical_Lighting
ALTIMA2000_Fasteners     → Fasteners_Bolts, Fasteners_Screws, Fasteners_Nuts, Fasteners_Clips
ALTIMA2000_Glass         → Glass_Glazing, Glass_Mirrors
ALTIMA2000_Trim          → Trim_Exterior, Trim_Seals, Trim_Badges
ALTIMA2000_Brakes        → Brakes_Front, Brakes_Rear, Brakes_Hydraulics
ALTIMA2000_Exhaust       → Exhaust_Manifold, Exhaust_Pipe, Exhaust_Muffler
ALTIMA2000_Fluids        → Fluids_Engine, Fluids_Body
ALTIMA2000_Safety        → Safety_Restraints
ALTIMA2000_Sequence      → (the 12 engine-bay step empties)
ALTIMA2000_Publish       → (reference empties only)
```

### Parts per collection (1,539 total)

| Collection | Parts | Collection | Parts |
|---|---:|---|---:|
| Electrical_Harness | 171 | Interior_Dash | 28 |
| Fasteners_Clips | 148 | Fasteners_Nuts | 26 |
| Fasteners_Bolts | 136 | Brakes_Hydraulics | 24 |
| Body_Panels | 107 | Suspension_Steering | 24 |
| Body_Structure | 101 | Drivetrain_Drive | 23 |
| Engine | 72 | Interior_Insulation | 22 |
| Electrical_Modules | 71 | Drivetrain_Mount | 20 |
| Brakes_Front | 18 | Suspension_Front | 56 |
| Brakes_Rear | 18 | Suspension_Rear | 32 |
| Door_Module_Hardware | 16 | Interior_Trim | 17 |
| Engine_Accessory | 15 | Trim_Exterior | 15 |
| Interior_Console | 13 | Exhaust_Pipe | 12 |
| Fluids_Body | 12 | Engine_Cooling | 11 |
| Glass_Mirrors | 10 | Electrical_Battery | 9 |
| Door_FL / Door_FR | 8 / 8 | Glass_Glazing | 8 |
| Engine_ExhaustSide | 8 | Door_RL / Door_RR | 7 / 7 |
| Exhaust_Manifold | 7 | Trim_Seals | 6 |
| Engine_Emission | 5 | Door_Module_Frame | 4 |
| Door_Module_Glazing | 4 | Door_Module_Skin | 4 |
| Engine_Fuel | 4 | Engine_Intake | 4 |
| Safety | 4 | Fluids_Engine | 3 |
| Exhaust_Muffler | 2 | … | |

By system code: `EL` 242 · `EN` 174 · `FT` 162 · `CL` 148 · `BD` 107 · `SH` 101 ·
`SU` 88 · `IN` 84 · `TR` 82 · `BR` 60 · `WH` 44 · `ST` 35 · `LM` 33 · `EX` 29 ·
`DRM` 28 · `SR` 24 · `DR` 22 · `MD` 15 · `FL` 15 · `MI` 10 · `SL` 10 · `BA` 9 ·
`GL` 8 · `EM` 5 · `SF` 4.

---

## 4. The 12-step engine-bay exploded sequence

The engine bay tears down in **assembly order** (bottom-up, exactly how a KA24DE is
built). Playing the steps forward explodes the bay; playing them in reverse reassembles
it. Each step owns one named empty, which is both an animation target and an optional
parent for that step's parts.

Root empty: **`ALTIMA2000_SEQ_Root`** (parent of all 12). Bay centre: `(1.020, 0.0, 0.545)`.

| # | Empty name | Step | Parts |
|---|---|---|---:|
| 01 | `ALTIMA2000_SEQ_Step01_EngineBlock` | Bare engine block and lower end | 33 |
| 02 | `ALTIMA2000_SEQ_Step02_Crankshaft` | Crankshaft and drive plate | 2 |
| 03 | `ALTIMA2000_SEQ_Step03_Pistons` | Pistons and connecting rods | 4 |
| 04 | `ALTIMA2000_SEQ_Step04_CylinderHead` | Cylinder head and gasket | 12 |
| 05 | `ALTIMA2000_SEQ_Step05_Camshafts` | Camshafts, valve cover and ignition | 22 |
| 06 | `ALTIMA2000_SEQ_Step06_TimingSet` | Timing chain set and front cover | 17 |
| 07 | `ALTIMA2000_SEQ_Step07_IntakeSide` | Intake side and fuel injection | 31 |
| 08 | `ALTIMA2000_SEQ_Step08_ExhaustSide` | Exhaust side and manifold | 15 |
| 09 | `ALTIMA2000_SEQ_Step09_CoolingSystem` | Cooling system | 19 |
| 10 | `ALTIMA2000_SEQ_Step10_AccessoryDrive` | Accessory drive | 19 |
| 11 | `ALTIMA2000_SEQ_Step11_Transaxle` | Transaxle and driveline | 41 |
| 12 | `ALTIMA2000_SEQ_Step12_EngineBayComplete` | Engine-bay completion | 15 |
| | | **Total moved** | **230** |

Each empty carries its step index, title, explode direction, explode distance and the
**explicit list of part names it moves** as custom properties — so the mapping is
documented and reproducible, not heuristic. A part is claimed by the first step that
names it (or whose name prefix matches), which makes the step order the precedence order.

The remaining 1,309 parts (body, interior, electrical, fasteners, …) are not part of the
engine-bay sequence; they are handled by the whole-car Disassemble operator.

---

## 5. The standalone door module

The four doors are also built as a **standalone serviceable module** in
`ALTIMA2000_DoorModule` — 28 parts, exported as its own `.blend` and linked into the
assembly file. This is the "loose door" a technician would pull off the car and work on
at a bench.

| Sub-collection | Parts | Serviceable parts |
|---|---:|---|
| `Door_Module_Skin` | 4 | loose outer skin, one per door (FL/FR/RL/RR) |
| `Door_Module_Frame` | 4 | window frame + belt reinforcement, one per door |
| `Door_Module_Hardware` | 16 | 2 hinges per door (8), latch (4), window regulator (4) |
| `Door_Module_Glazing` | 4 | window glass run channel / bailey channel, one per door |
| **Total** | **28** | |

The door *assemblies* (`ALTIMA2000_Doors` → `Door_FL`/`FR`/`RL`/`RR`, 30 parts) hold the
parts that stay with the body shell: inner panel, impact beam, check strap, handle, key
cylinder, window motor, trim panel, belt seal.

---

## 6. The seven modules and the linked assembly file

Seven module `.blend` files are written, each a real self-contained file holding only that
system's collections — so it can be opened, edited and re-exported on its own:

| Module | File | Parts | Objects | Size |
|---|---|---:|---:|---:|
| engine | `altima2000_module_engine.blend` | 187 | 187 | 1.8 MB |
| suspension | `altima2000_module_suspension.blend` | 112 | 112 | 1.3 MB |
| drivetrain | `altima2000_module_drivetrain.blend` | 82 | 82 | 1.0 MB |
| brakes | `altima2000_module_brakes.blend` | 60 | 60 | 0.9 MB |
| wheels | `altima2000_module_wheels.blend` | 44 | 44 | 0.8 MB |
| doors | `altima2000_module_doors.blend` | 28 | 28 | 0.8 MB |
| exhaust | `altima2000_module_exhaust.blend` | 21 | 21 | 0.7 MB |
| | **Total** | **534** | **534** | |

### How the top-level assembly file links them

`altima2000_assembly_linked.blend` is the top-level file. It does **not** duplicate the
modules — it **library-links** them:

1. The master `.blend` is opened and each module's root collection is removed.
2. Each module `.blend` is loaded with `bpy.data.libraries.load(path, link=True)` and its
   root collection is linked into the scene.

Result: the assembly file holds **one copy** of each system, and any edit to a module
`.blend` propagates into the assembly on reload. Verified at build time — all 7 modules
resolve as linked collections, 1,539 mesh objects present, `all_modules_linked=True`.

> **Note:** because the modules are *linked*, the assembly file depends on the seven
> module `.blend` files sitting next to it. Keep them in the same directory. If you need a
> single self-contained file, use `altima2000_assembly.blend` (everything embedded).

---

## 7. Fastener counts at `ALTIMA_BULK_SCALE = 1.0`

At full density the bulk fastener/harness population is:

| Family | Collection | Count |
|---|---|---:|
| Bolts | `Fasteners_Bolts` | 136 |
| Clips / retainers | `Fasteners_Clips` | 148 |
| Nuts | `Fasteners_Nuts` | 26 |
| **Fastener total** | | **310** |

Plus the bulk electrical/insulation population that scales with the same knob:
`Electrical_Harness` 171 (power + signal wire runs), `Electrical_Modules` 71 (module
brackets), `Interior_Insulation` 22 (sound-deadening pads), `Body_Structure` 101
(gussets + floor ribs), and 40 flat washers inside `Fasteners_Bolts`.

`ALTIMA_BULK_SCALE` multiplies every bulk block linearly. The default in the source is
`0.34` (which lands on the original ~1,000-part target); **this build was made with
`1.0`**, giving 1,539 parts.

---

## 8. How to load and use

### Open the asset

- **`altima2000_assembly.blend`** — the main deliverable. Everything embedded, 1,539 parts.
- **`altima2000_assembly_linked.blend`** — top-level file that links the 7 modules.
- **`altima2000_exploded.blend`** — same asset pre-exploded for a service view.

### Run the operators

Open the `.blend`, then in the **Text Editor** open `altima2000_assembly_tools.py` and
press **Run Script**. The **Altima 2000** tab appears in the 3D Viewport sidebar
(press `N`). (Alternatively: *Edit ▸ Preferences ▸ Add-ons ▸ Install from Disk* → pick the
file → enable "ALTIMA2000 Assembly Tools".)

| Operator | Blender id | What it does |
|---|---|---|
| Disassemble (Explode View) | `altima.disassemble` | Radially displaces every part from the explode centre, storing each part's assembled position first. Params: Distance (0–5), Centre, Selected Only. |
| Reassemble (Assembly View) | `altima.reassemble` | Restores every part's location and rotation from its stored `asmb` transform. |
| Verify Assembly | `altima.verify_assembly` | Checks every part against its stored position within a tolerance. |
| Apply Sequence Step | `altima.sequence_step` | Explodes (or restores) one of the 12 engine-bay steps. |
| Apply Full Sequence | `altima.sequence_all` | Explodes all 12 steps in assembly order; `reverse=True` reassembles. |
| Reset Sequence | `altima.sequence_reset` | Returns every sequence part to its assembly position. |

Typical loop: **Verify Assembly → Disassemble → Reassemble → Verify Assembly**.

### Where the manifest lives

- `altima2000_manifest.json` — full manifest, including the `sequence` block (all 12 steps
  with their part lists) and the `modules` block (per-module contents + verification).
- `altima2000_manifest.csv` — the same part table, spreadsheet-friendly.

Every part also carries its canonical transform in an `asmb` custom property, so
reassembly works **without** the manifest file.

### Reassemble programmatically

```python
import bpy, json

manifest = json.load(open("altima2000_manifest.json"))
for row in manifest["parts"]:
    ob = bpy.data.objects.get(row["name"])
    if ob is None:
        continue
    ob.hide_viewport = ob.hide_render = False
    ob.location       = row["offset_m"]
    ob.rotation_euler = row["rotation_euler_rad"]
    ob.scale          = row["scale"]
```

---

## 9. Regenerating from script

Blender 4.5 LTS, no add-ons, no external assets.

```bash
cd source
export ALTIMA_BULK_SCALE=1.0
export ALTIMA_OUT=/workspace/documents/altima2000_v2
/workspace/tools/blender-4.5.14-linux-x64/blender -b --factory-startup --python build_altima.py
```

A run takes ~25 s and prints a summary ending in
`BUILD_DONE part_count=1539 collections=51 materials=73 bulk_scale=1.00`.

### Generator layout

| File | Role |
|---|---|
| `source/build_altima.py` | Orchestrator: builds, validates, writes manifest, exports, writes operators, writes modules + linked assembly |
| `source/altima/spec.py` | Vehicle dimensions, station/ring tables, coordinate remap |
| `source/altima/meshutils.py` | Super-ellipse section engine, `BodySurface`, lofting, offsetting |
| `source/altima/materials.py` | The 73-material PBR library |
| `source/altima/builder.py` | Collection tree, part registry, naming enforcement, shelling, module map |
| `source/altima/sequence.py` | The 12-step engine-bay sequence definition |
| `source/altima/parts/common.py` | Fastener profiles, prisms, grid mirroring |
| `source/altima/parts/templates.py` | Reusable instanced geometry templates |
| `source/altima/parts/panels.py` | Body, closures, structure, doors + door module, glass, lamps, trim |
| `source/altima/parts/mechanical.py` | Engine, drivetrain, suspension, wheels, brakes, exhaust |
| `source/altima/parts/interior.py` | Interior, electrical, and the bulk fastener generator |
| `source/render_check.py` | Validation renders |

### Environment overrides

| Variable | Default | Effect |
|---|---|---|
| `ALTIMA_OUT` | `../deliverables` | Output directory |
| `ALTIMA_BULK_SCALE` | `0.34` | Multiplier on every bulk fastener/harness block |
| `ALTIMA_SKIP_EXPORT` | — | `1` skips glTF/FBX (fast geometry-only iteration) |
| `ALTIMA_RENDER_*` | — | Render view selection, tag, explode amount |

---

## 10. Known limitations

- **Body panels are surface shells**, not solid stampings: each panel is a correctly
  shaped, correctly placed skin with real thickness, not a modelled inner pressing with
  ribs and flanges. Panel gaps are geometric, not stamped flanges.
- **Fastener and clip positions** are distributed deterministically across each assembly's
  bounding volume rather than derived from real torque-spec locations. They are correctly
  named, grouped, counted and transformable, but a purist concours teardown would want
  them individually placed.
- **Engine internals** (crank, cams, pistons) are representative volumes at correct
  positions and orientations, not dimensioned to factory drawings.
- **Interior** is modelled to the visible surfaces plus seat structures; underside
  bracketry is simplified.
- **1,539 objects share 717 mesh datablocks.** Identical fasteners and clips instance one
  mesh per size — every part is still its own selectable, named, transformable object with
  its own manifest row, but the whole car is 41,632 vertices / 42,743 faces instead of
  ~1 M. The manifest's `instance_of` column tells you which objects share a mesh.
- **The linked assembly file depends on the 7 module `.blend` files** being present in the
  same directory (they are linked, not embedded).
- Renders are Cycles CPU at 28 samples — clean enough for verification, not for marketing.

---

## 11. Attribution

Vehicle dimensions taken from published 2000 Nissan Altima (L30) specifications
(4,720 mm × 1,755 mm × 1,420 mm, 2,620 mm wheelbase, 205/60R15 tyres). All geometry is
generated procedurally by this repository — no third-party model data is included.
