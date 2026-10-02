# ALTIMA2000 — Handoff

**Asset:** a procedurally generated, fully disassemblable 2000 Nissan Altima (L30) sedan
for Blender, built entirely from Python (`bpy`). No downloaded or third-party mesh is
used anywhere — running the build script reproduces the whole car deterministically.

**Repository:** https://github.com/bythewayz66-glitch/altima2000-blender-asset (public, branch `main`)
**Release:** https://github.com/bythewayz66-glitch/altima2000-blender-asset/releases/tag/v1.0.0
**Generator:** `source/build_altima.py` (+ the `source/altima/` package)
**Current build:** 2,130 parts · 57 sub-collections · 81 materials · `ALTIMA_BULK_SCALE = 1.0`

---

## 1. What the asset is

A complete, physically-modelled 2000 Nissan Altima split into **2,130 individually
selectable, separately named parts**, organised into a logical collection tree, with:

- **real routed wiring** — 323 wire segments in 31 harnesses (192.9 m of wire)
- **real routed hoses and tie straps** — 37 hose segments + 38 tie straps (23.7 m)
- a machine-readable **assembly manifest** (JSON + CSV), plus a **per-module manifest**
  for each of the 7 module files
- a working **disassemble / reassemble / exploded** toolkit
- a **27-step full-car exploded sequence** (the original 12 engine-bay steps plus 15 more
  covering body, interior, electrical and suspension)
- a **keyframed teardown animation** exported to glTF
- a **touch-activated wire glow with a progressive trace**, including a **live modal
  operator** and a **per-harness visibility panel**

### Real-world dimensions (metres, +Z up)

| Dimension | Asset | Spec (2000 Altima) |
|---|---|---|
| Length | 4.7197 | 4.720 (185.8 in) |
| Width | 1.7550 | 1.755 (69.1 in) |
| Height | 1.4200 | 1.420 (55.9 in) |
| Wheelbase | 2.6200 | 2.620 (103.1 in) |
| Track (front/rear) | 1.5060 | 1.506 (59.3 in) |

---

## 2. Naming convention

Every part follows one deterministic pattern:

```
ALTIMA2000_<GROUP>_<Tag>_<Detail>[_NNN]
```

Enforced by a single regex in `source/altima/builder.py`:

```python
NAME_RE = re.compile(r"^ALTIMA2000_[A-Z0-9]+_[A-Za-z0-9]+_[A-Za-z0-9_]+$")
```

- `<GROUP>` — uppercase group code (see the table below)
- `<Tag>` — the sub-assembly / system tag, alphanumeric
- `<Detail>` — the specific part, `_`-separated words
- `[_NNN]` — optional zero-padded instance number for repeated parts

Examples: `ALTIMA2000_ENG_Piston_Assembly_001`, `ALTIMA2000_EL_Wire_EngineMain_007`,
`ALTIMA2000_DRM_Skin_FL`, `ALTIMA2000_BODY_Hood_Outer`.

### Group codes

| Code | Group | Code | Group |
|---|---|---|---|
| `ENG` | Engine | `EL` | Electrical / wiring |
| `TRN` | Transmission / driveline | `LM` | Lamps / lighting |
| `SUS` | Suspension | `IN` | Interior |
| `BRK` | Brakes | `GL` | Glass / glazing |
| `WHL` | Wheels / tyres | `SL` | Seals / weatherstrip |
| `EXH` | Exhaust | `MD` | Exterior trim / mouldings |
| `FUE` | Fuel system | `SH` | Body structure / shell |
| `COO` | Cooling | `BD` | Body panels / closures |
| `CLI` | Climate / HVAC | `DR` | Door internals |
| `STR` | Steering | `DRM` | Door module (standalone) |
| `SAFE` | Safety / restraints | `SCRE` | Screws / studs |
| `FAS` | Fasteners | `SEQ` | Sequence step empties |

---

## 3. Collection structure

16 top-level categories, 57 sub-collections. The main ones:

| Collection | Contents |
|---|---|
| `Engine_*` | Long block, head, intake, fuel, cooling, emission, exhaust side |
| `Drivetrain_*` | Transaxle, final drive, driveshafts, CV joints |
| `Suspension_*` | Front struts, rear multi-link, steering gear |
| `Brakes_*` | Discs, calipers, pads, lines, ABS |
| `Wheels` | 4 tyres, 4 rims, lug nuts, valve stems |
| `Exhaust_*` | Manifold, downpipe, cat, muffler, tailpipe |
| `Body_Panels` | Hood, fenders, doors, quarters, trunk, bumpers, roof |
| `Body_Structure` | Floor, rails, wheel houses, strut towers, parcel shelf |
| `Electrical_*` | **Wiring** (6 sub-collections), lighting, modules, battery |
| `Interior_*` | Dash, console, seats, trim, insulation |
| `Glass_*` | Windshield, backlight, door glass, quarter glass, mirrors |
| `Trim_*` | Exterior mouldings, seals |
| `Fasteners_*` | Bolts, clips, nuts |
| `Fluids_*` | Engine and body fluids |
| `Safety` | Restraints, airbags |
| `Door_Module_*` | The standalone door module (skin, frame, hardware, glazing) |

---

## 4. Wiring systems and wire count

**323 wire segments · 31 harnesses · 192.9 m of wire.**

Every wire is a **real swept tube with its own mesh, object, name and manifest row** —
nothing is a texture or a painted line. A harness is a bundle of circuits sharing a
route; each circuit is split into segments at the route's waypoints, so a segment is a
removable piece of the run, exactly like a real harness section.

Routing follows the actual component-to-component paths and is smoothed with
Catmull-Rom, so runs bend around structure instead of running point-to-point. Along each
route the build places the hardware a real loom has: **15 bulkhead grommets, 168
P-clips/retainers, 62 connector shells**.

### Harnesses by system

| System | Harnesses |
|---|---|
| Engine bay | EngineMain, Injector, Ignition, EngineSensors, Charging, Starting, EngineGround, Cooling, Horn, WiperWasher |
| Chassis / ABS | ABS, ChassisFront, ChassisRear |
| Lighting | Headlamp, SignalFront, TailLamp, PlateLamp |
| Dash | DashMain, Instrument, DashSwitch |
| Cabin | CabinFloor, Console, HVAC, SeatPower, AudioRear |
| Body | BodyRear, FuelPump, Roof |
| Doors | DoorFL, DoorFR, DoorRL, DoorRR |

Wires live in six `Electrical_*` sub-collections, so they appear in the manifest, the
disassembly round trip and the exploded view with no special handling.

> **Note:** the 32 legacy straight "bulk wire" runs from the earlier build were removed —
> they were superseded by the real routed wiring, and leaving them would have
> double-counted the electrical system.

---

## 5. Hoses and tie straps

The remaining legacy bulk hoses and tie straps were converted to **real swept tube
geometry**, routed the same way the wires are (Catmull-Rom smoothed paths along plausible
real runs), with the same naming pattern, sub-collections, manifest rows and
trace/glow compatibility.

**37 hose segments across 15 systems + 38 tie straps · 23.7 m total.**

The superseded straight geometry was removed, so nothing is double-counted. Hoses and
straps carry the same `trace_t` attribute as the wires, so the glow/trace works on them
too.

---

## 6. The 12-step engine-bay sequence

The original engine-bay teardown, unchanged in ordering and explode directions. Each step
is a named empty parented to the sequence root, carrying `step_index`, `step_key`,
`step_title`, `explode_dir`, `explode_distance`, `part_count` and the explicit list of
part names it moves.

| # | Empty name | Parts |
|---|---|---|
| 01 | `ALTIMA2000_SEQ_Step01_EngineBlock` | 33 |
| 02 | `ALTIMA2000_SEQ_Step02_IntakeManifold` | 2 |
| 03 | `ALTIMA2000_SEQ_Step03_ExhaustManifold` | 4 |
| 04 | `ALTIMA2000_SEQ_Step04_ValveCover` | 12 |
| 05 | `ALTIMA2000_SEQ_Step05_TimingBelt` | 22 |
| 06 | `ALTIMA2000_SEQ_Step06_AccessoryDrive` | 17 |
| 07 | `ALTIMA2000_SEQ_Step07_CoolingSystem` | 31 |
| 08 | `ALTIMA2000_SEQ_Step08_FuelSystem` | 15 |
| 09 | `ALTIMA2000_SEQ_Step09_IgnitionSystem` | 19 |
| 10 | `ALTIMA2000_SEQ_Step10_EngineHarness` | 19 |
| 11 | `ALTIMA2000_SEQ_Step11_Transaxle` | 41 |
| 12 | `ALTIMA2000_SEQ_Step12_EngineBayComplete` | 15 |

---

## 7. Full-car sequence (27 steps)

The sequence was extended beyond the engine bay so that **all 2,130 parts are sequenced**
— not just the 230 engine-bay parts. Steps 13–27 cover body panels, interior, electrical
and suspension, following the same conventions (one named empty per step, same custom
properties, mapping by explicit name/prefix rather than heuristic).

| # | Step key | Covers |
|---|---|---|
| 13 | `BodyPanels` | hood, fenders, doors, quarters, trunk, roof |
| 14 | `Bumpers` | front/rear covers, beams, absorbers, brackets |
| 15 | `Glass` | windshield, backlight, door and quarter glass |
| 16 | `InteriorDash` | dash, console, instruments |
| 17 | `InteriorSeats` | seats, trim, insulation |
| 18 | `ElectricalWiring` | the routed wiring set |
| 19 | `ElectricalModules` | ECU, TCM, BCM, fuse/relay boxes, battery |
| 20 | `Lighting` | headlamps, tail lamps, signals |
| 21 | `SuspensionFront` | front struts, arms, steering |
| 22 | `SuspensionRear` | rear multi-link |
| 23 | `Brakes` | discs, calipers, lines, ABS |
| 24 | `Wheels` | tyres, rims, lug nuts |
| 25 | `Exhaust` | manifold, cat, muffler, tailpipe |
| 26 | `DrivetrainRemainder` | driveshafts, CV joints, boots |
| 27 | `RemainingHardware` | safety, screws/studs, **catch-all** |

Step 27 is a **catch-all**: it claims every part no earlier step matched. That is the
guarantee the sequence is total — if a new part group is ever added to the generator
without a step of its own, it lands here instead of silently falling out of the sequence.
The build reports `unclaimed=0`.

---

## 8. The standalone door module

Each door is built as a self-contained module with its own sub-collections
(`Door_Module_Skin`, `Door_Module_Frame`, `Door_Module_Hardware`,
`Door_Module_Glazing`), so a door can be removed, inspected and reassembled on its own.

Serviceable parts per door: outer skin, inner panel, window frame, side impact beam,
2 hinges, check strap, latch, outer handle, key cylinder (front doors), window regulator,
window motor, interior trim panel, door glass, belt seal, glass run channel.

The `doors` module file (`altima2000_module_doors.blend`) holds all four doors — 28 parts.

---

## 9. The 7 modules and the linked assembly

| Module | File | Parts |
|---|---|---|
| engine | `altima2000_module_engine.blend` | 195 |
| suspension | `altima2000_module_suspension.blend` | 112 |
| drivetrain | `altima2000_module_drivetrain.blend` | 82 |
| brakes | `altima2000_module_brakes.blend` | 61 |
| wheels | `altima2000_module_wheels.blend` | 44 |
| doors | `altima2000_module_doors.blend` | 28 |
| exhaust | `altima2000_module_exhaust.blend` | 21 |

`altima2000_assembly_linked.blend` is the **top-level linked assembly**: it links the
seven module files as Blender libraries and resolves all 2,130 parts, so the car can be
worked on module-by-module while the assembly stays live. Editing a module file updates
the linked assembly on reload.

### Per-module manifests

Each module has its own manifest in **both JSON and CSV**, using exactly the same row
schema as the master:

```
altima2000_module_<key>_manifest.json
altima2000_module_<key>_manifest.csv
```

Each row carries the master fields (`name`, `collection`, `count`, `position`) **plus**
`master_index` — the part's 1-based index in the master manifest. That is how a
module-level name maps back to the master: `row["name"]` is identical in both files,
`row["collection"]` is the same sub-collection name, and `row["master_index"]` gives the
master position.

**A module reassembles standalone.** Every row carries the part's assembled world
position in `offset_m`, so the disassemble / reassemble operators shipped in
`altima2000_assembly_tools.py` work on a module file unchanged. Verified: the engine
module round-trips to 6.8e-07 m.

---

## 10. Teardown animation

The 27 sequence steps are keyframed as a teardown: each step empty's location is
keyframed over one frame per step, in the established assembly order, so the animation
reads as **forward teardown / reverse reassembly**.

- Frame 1 = assembled, frame 28 = fully exploded (27 steps + 1).
- The animation uses the same step ordering and the same `explode_dir` /
  `explode_distance` values already stored on the step empties.
- Exported to glTF: `altima2000.glb` and `altima2000.gltf` carry **27 animations**, one
  per step, so the teardown plays back in any glTF viewer.

> FBX animation baking is deliberately **off** (`bake_anim=False`). Baking 2,130 objects
> is prohibitively slow and was killing the build; the glTF export carries the animation,
> which is what the deliverable requires.

---

## 11. Touch-activated glow and progressive trace

Each wire (and hose/strap) mesh carries a baked `trace_t` float attribute on the POINT
domain = the normalised arc length along the run. The wire materials read it through a
Map Range driven by three named Value nodes:

- `TraceProgress` — 0→1 sweep position
- `TraceWidth` — width of the lit band
- `GlowStrength` — emission intensity

Sweeping `TraceProgress` from 0 to 1 makes the lit band **travel from one end of the wire
to the other**. Because the mask is computed per vertex, the leading edge is a real
gradient, not a whole-object switch.

Because it is a mesh attribute plus node values — not a modifier or a driver — it
survives disassemble / reassemble / explode and is regenerated by every build.

### Operators

| Operator | What it does |
|---|---|
| `altima.trace_wire` | Trace the selected wires |
| `altima.trace_all` | Trace every wire |
| `altima.trace_clear` | Clear the glow |
| `altima.trace_modal` | **Live modal trace** — see below |

### Live modal trace

`altima.trace_modal` runs a modal operator so the trace animates **live in the viewport**
on hover/selection, instead of only running once when an operator is invoked. Hovering or
selecting a wire starts the trace sweeping along that wire's run in real time; moving off
it clears or reverses it. It drives the same `TraceProgress` / `TraceWidth` /
`GlowStrength` node values as the static operators, so it is fully compatible with them
and with the deterministic build.

---

## 12. Per-harness visibility panel

The **Altima 2000** sidebar tab (View3D → N-panel) has a harness panel listing all **31
harnesses**, each with an individual visibility toggle, so any single harness can be
isolated for inspection.

| Control | What it does |
|---|---|
| Per-harness toggle | Show/hide that harness's objects |
| `altima.harness_show_all` | Show every harness |
| `altima.harness_hide_all` | Hide every harness |
| `altima.harness_refresh` | Rebuild the list from the scene |

The panel state works with the existing collections and operators — toggling a harness
hides exactly the objects whose `asmb.harness` matches, and restores them on toggle back.

---

## 13. Fastener counts at `ALTIMA_BULK_SCALE = 1.0`

| Fastener | Count |
|---|---|
| Bolts | 136 |
| Clips | 186 |
| Nuts | 26 |
| **Total** | **348** |

---

## 14. How to regenerate from script

```bash
blender -b --factory-startup --python source/build_altima.py
```

One run regenerates everything: the car, the full 27-step sequence, the wiring and hose
sets, the module manifests, the teardown animation, and all exports. The build takes
~50 s and prints a summary:

```
BUILD_DONE part_count=2130 collections=57 materials=81 bulk_scale=1.00
BUILD_SEQUENCE steps=27 parts_moved=2130 unclaimed=0
BUILD_WIRING harnesses=31 wire_segments=323 total_length_m=192.9
BUILD_HOSES systems=15 hose_segments=37 tie_straps=38 total_length_m=23.7
```

Set `ALTIMA_OUT` to change the output directory. There are **no manual edits** to the
built files — everything is regenerable.

### Verification

```bash
blender -b --factory-startup --python source/verify_v6.py
```

Reports `VERIFY_RESULT ALL_PASS` (76 checks) covering naming, duplicates, manifest
completeness in JSON and CSV, collections, module opens, per-module manifests, module
standalone reassembly, linked assembly, glTF integrity, wiring/hose counts, the trace
shader, wheel orientation, panel shut lines, the disassemble/reassemble round trip, the
full-car sequence round trip, and animation playback.

### CI

`.github/workflows/asset-check.yml` opens `altima2000_assembly.blend` headless on every
push and asserts the part count, the naming regex and module link integrity
(`ci/verify_asset.py`). It fails the job loudly if any assertion breaks.

---

## 15. How to load and use

1. **Open the assembly.** `altima2000_assembly.blend` is the main deliverable — the
   complete car, fully assembled. For module-by-module work open
   `altima2000_assembly_linked.blend` instead.
2. **Install the operators.** The toolkit ships as `altima2000_assembly_tools.py`. In
   Blender: *Edit → Preferences → Add-ons → Install…* and pick the file, then enable
   **Altima 2000 Assembly Tools**. The **Altima 2000** tab appears in the 3D viewport
   N-panel.
3. **Run the operators** from that panel:
   - `altima.disassemble` — explode every part outward
   - `altima.reassemble` — return every part to its assembly position
   - `altima.verify_assembly` — check the round trip
   - `altima.sequence_step` / `altima.sequence_all` — run the 27-step sequence
     (`sequence_all` takes `reverse=True` to reassemble)
   - `altima.trace_modal` — live hover/selection trace
   - the harness panel — isolate any of the 31 harnesses
4. **Where the manifest lives.** `altima2000_manifest.json` (full detail) and
   `altima2000_manifest.csv` (spreadsheet-friendly) sit next to the .blend files. Each
   module has its own pair: `altima2000_module_<key>_manifest.json` / `.csv`.
5. **Play the teardown.** Open `altima2000.glb` in any glTF viewer and play the
   animation — 27 channels, one per step.

---

## 16. Visual QA

Renders were inspected with a vision model, before and after the fixes.

**Before:** the vision model reported the assembled car reading as a "single smooth
blob" / "seamless shell" with no visible panel separation, and flagged jagged dark
patterns on the painted surfaces.

**What was actually wrong (measured, not guessed):** a bounding-box gap test is the wrong
measure for a shut line, so the geometry was probed directly with a BVH triangle-overlap
test. It found **three pairs of painted body panels genuinely interpenetrating** —
quarter-inner vs quarter-outer (267 faces), rocker vs side-body (54 faces), cowl vs
side-body (2 faces). That interpenetration is what produced the jagged z-fighting the
vision model saw.

**Fixes:**
- rocker sill now stops at ring index 1.35, where the side-body panel starts, instead of
  sharing a band of the same body surface
- quarter inner structure is pushed inboard (|y| × 0.90) and stops short of the trunk
  lid, so it no longer interpenetrates the outer skin or the trunk-lid inner panel
- cowl panel pulled inboard 20 mm off the side-body surface

**After:** the BVH probe reports **0 intersecting pairs** among the painted body panels,
and the shut lines measure as real gaps (hood→fender 0.174 m, trunk→quarter 0.052 m,
fender→side-body 0.019 m). The vision model confirms the wiring reads as **real 3D tubes**
with thickness and volume, organised into looms with visible cable ties, and that the
wheels are oriented correctly with the circular face pointing sideways.

**Wheel orientation:** verified both geometrically (all four tyres are thin in Y and round
in X/Z — i.e. the axle points sideways, as it should) and visually.

---

## 17. Known limitations

- **The glow/trace is a viewport-and-render shader effect, not a game-engine
  interaction.** It is driven by a baked mesh attribute plus material node values, so it
  survives the assembly operators and regenerates every build — but a runtime engine would
  need to re-implement the same attribute-driven emission.
- **Wire and hose routing is plausible, not factory-exact.** Runs follow the real
  component-to-component paths and use realistic grommets, clips and connectors, but they
  are not traced from a factory wiring diagram.
- **Wire gauges are representative per circuit type**, not per-circuit specifications.
- **The teardown animation is exported to glTF only.** FBX animation baking is off
  because baking 2,130 objects is prohibitively slow; the FBX carries geometry and
  transforms but not the keyframed teardown.
- **The sequence catch-all (step 27) is a safety net.** Parts that no specific step claims
  land there. It guarantees totality, but a newly added part group would be better served
  by its own step.
- **Panel gaps are uniform** (11 mm nominal) rather than varying per shut line as on a
  real car.

---

## 18. Repository, Release and CI

- **URL:** https://github.com/bythewayz66-glitch/altima2000-blender-asset (**public**)
- **Branch:** `main`
- **LFS:** `.blend`, `.glb`, `.fbx`, `.bin` are tracked with Git LFS. The patterns in
  `.gitattributes` are committed **before** the binaries.

### Release

- **Release:** https://github.com/bythewayz66-glitch/altima2000-blender-asset/releases/tag/v1.0.0
- **Tag:** `v1.0.0` (targets `main`)
- **Attached assets (12, all downloadable):** `altima2000_assembly.blend`,
  `altima2000_assembly_linked.blend`, `altima2000_exploded.blend`, the 7 module files
  (`altima2000_module_{engine,drivetrain,suspension,wheels,brakes,exhaust,doors}.blend`),
  `altima2000.glb` and `altima2000.fbx`.
- The assets are attached by `.github/workflows/attach-release-assets.yml`, which runs on
  GitHub's own runners (they hold the repo token and can pull the Git LFS objects), so the
  release assets are produced from the exact committed binaries.

### Access / pushing

- **Deploy key:** a write-enabled deploy key (`altima2000-blender-asset-deploy`, installed
  in the sandbox at `~/.ssh/altima_asset_deploy`) is registered on the repo.
- **Important:** the sandbox `~/.ssh/config` pins a *different* key (`altima_deploy`, scoped
  to the `altima2000` repo), so a plain `git push` fails with `Repository not found`. Force
  the correct key per repo:

  ```bash
  git config core.sshCommand "ssh -i $HOME/.ssh/altima_asset_deploy -o IdentitiesOnly=yes"
  ```

- **PAT (open):** a repo-scoped personal access token stored as a sandbox secret is **not
  yet configured** — see issue #1. Once it exists, plain
  `git clone https://github.com/bythewayz66-glitch/altima2000-blender-asset.git` +
  `git lfs push` will work over HTTPS with no SSH key.

### CI

- **Workflow:** `.github/workflows/asset-check.yml` (`ALTIMA2000 asset check`) — opens
  `altima2000_assembly.blend` headless in Blender on every push to `main` and asserts the
  part count, the naming regex and module link integrity via `ci/verify_asset.py`
  (greps for `CI_RESULT ALL_PASS`).
- **Workflow:** `.github/workflows/attach-release-assets.yml` — attaches the binaries to
  the `v1.0.0` release.
- **Open:** the green/red result of the asset check on the latest push has not been
  confirmed from the repo — see issue #2.

### Open follow-up issues

| # | Title | Labels |
|---|---|---|
| 1 | Add a repo-scoped PAT as a sandbox secret so future pushes use plain git clone + git lfs push | tooling, enhancement |
| 2 | Verify the CI asset-check workflow runs green on the latest push | ci |
| 3 | Add per-harness visibility toggles for the 37 hoses and 38 tie straps | enhancement |
| 4 | Audit remaining legacy geometry and manifest gaps | enhancement, tooling |
| 5 | Re-validate wheel orientation and assembly seams with the vision model and record the verdict | enhancement, documentation |

---

## 19. Interactive web frontend (`web/`)

The asset is usable **in a browser with no Blender installed**. `web/` is a plain static
site — no build step, no npm install — that loads the same `altima2000.glb` and the same
manifest JSON that ship in this repo.

### Layout

```
web/
  index.html              the viewer shell (header / sidebar / viewport / bottom bar)
  css/app.css             all styling
  js/app.js               controller: boots the data layer, viewer and UI
  js/data.js              manifest loading + indexing (parts, harnesses, modules, steps)
  js/viewer.js            three.js scene, picking, explode, animation, visibility
  js/trace.js             trace shader + arc-length baking + TraceController
  js/ui.js                panels, virtualised parts list, legend, info card, bottom bar
  vendor/three/           three.js 0.169.0 + GLTFLoader + OrbitControls (vendored)
  data/                   copy of the glb/gltf/bin + master and per-module manifests
  verify_frontend.js      headless verification harness (36 assertions)
```

### Run it

```bash
cd web
python3 -m http.server 8080     # then open http://localhost:8080
```

A server is required — `file://` blocks ES modules and `fetch`.

### Deploy

`.github/workflows/pages.yml` publishes `web/` to GitHub Pages on every push to `main`.
Enable once under **Settings → Pages → Source: GitHub Actions**. Live at
`https://bythewayz66-glitch.github.io/altima2000-blender-asset/`.

### Data sources

The viewer has two, selectable in the header (or with `?source=local` / `?source=github`):

| Source | Manifest | Model |
|---|---|---|
| `local` | `./data/altima2000_manifest.json` | `./data/altima2000.glb` |
| `github` | `raw.githubusercontent.com/…` | `media.githubusercontent.com/media/…` |

The GitHub source is needed on Pages because the `.glb` is a **Git LFS object** and
`raw.githubusercontent.com` returns only the 132-byte LFS pointer. The LFS media host
serves the real bytes and is CORS-enabled (`access-control-allow-origin: *`), so no
proxy is required. The page auto-selects `github` when served from `*.github.io`.

### Feature map

| Requested feature | Where it lives |
|---|---|
| 3D load + orbit (rotate / zoom / pan) | `viewer.js` — `GLTFLoader`, `OrbitControls` |
| Exploded / disassembly view | `viewer.js` `setExplode()`; bottom-bar **Explode** + **Step** sliders |
| "Pull this part off" | `viewer.js` `eject()` / `uneject()`; info-card button |
| Part picking + manifest record | `viewer.js` `pick()`; `ui.js` `showInfo()` |
| Searchable / filterable 2,130-part list | `ui.js` `refreshParts()` / `_renderParts()` (virtualised) |
| Wiring view, 31 harness toggles | `ui.js` `refreshHarnesses()`; `viewer.js` `setHarnessVisible()` / `isolateHarness()` |
| Hoses + tie straps | `ui.js` hose list; `viewer.js` `setHoseSystemVisible()` |
| Glow + progressive trace | `trace.js` — `buildTraceAttribute()`, `makeTraceMaterial()`, `TraceController` |
| Teardown animation playback | `viewer.js` `_setupAnimation()` / `setAnimTime()`; bottom-bar transport |
| Module view (7 modules) | `ui.js` `refreshModules()`; `viewer.js` `isolateModule()` |
| Legend | `ui.js` `_buildLegend()` |

### How the trace is rebuilt in the browser

Blender drives the trace from a `trace_t` mesh attribute plus material node values.
glTF does not export custom attributes, so the frontend reconstructs the same value:

1. Each wire/hose has a `trace_points` polyline in `altima2000_manifest.json`.
2. Those points are authored in Blender's **Z-up** frame; the glTF is **Y-up**. They are
   converted with `(x, y, z) → (x, z, −y)` in `data.js` (`blenderToGltf`), then into each
   mesh's local frame via the inverse of its world matrix (`trace.js` `polylineToLocal`).
3. Every vertex is projected onto the polyline; the normalised arc length becomes the
   `aTraceT` attribute (`buildTraceAttribute`).
4. `makeTraceMaterial()` sweeps `uProgress` 0 → 1, drawing a bright travelling head with
   a lit trail behind it, faded in/out by `uGlow`.

Tie straps carry no polyline in the manifest, so `buildTraceAttributeFromGeometry()`
derives an arc length from the geometry's principal axis — the sweep still runs end to end.

### Verification

`web/verify_frontend.js` drives a real headless Chromium (WebGL via SwiftShader) against
a local server and asserts 36 behaviours: model load, part count vs. manifest, picking,
the info card, harness toggles and isolation, the trace attribute and its sweep, live
hover tracing, explode, step control, part ejection, module isolation, animation playback
and scrubbing, the parts list, search, and the panels.

```bash
cd web && python3 -m http.server 8099 &
npm i puppeteer-core
CHROME=/path/to/chrome node verify_frontend.js
```

### Known limitations

- **Four parts have no geometry in the export.** `ALTIMA2000_SHEL_RoofBow_001…004` are in
  the manifest but authored as non-mesh objects, so they cannot be drawn. They stay
  searchable and the info card says so. Hence **2,126 meshes** for a **2,130-part**
  manifest — the viewer reports both numbers rather than hiding the gap.
- The trace shader is a custom `ShaderMaterial`, so it does not receive scene shadows.
- Desktop-oriented; the layout is responsive but not touch-optimised.
- First load is a few seconds (≈4.7 MB glTF + 1.8 MB manifest); both are cached after.
