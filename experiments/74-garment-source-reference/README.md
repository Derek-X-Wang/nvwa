# Bounded original-tool shoulder reference — issue80

**HOLD. No correction selected.** This experiment retains the actual shoulder
triangle200/source IDs `[246,244,182]`, torso+1/jaw0, arm2 witness and arm0/knee2
controls. It changes no production code, assets, weights, camera, material,
threshold, dependency or root lockfile. Prior smoothing/offset candidates remain
rejected. The original garment author's body recipe remains **UNKNOWN**.

The new preparation and retained-reference comparisons use standard-library
Python. The proposed reference driver calls the existing MPFB2.0.18 APIs and
actual Blender armature. It does not reproduce those APIs with copied code,
fabricate a rig, import captured skin matrices into Blender, or render images.
The driver has only been parsed. Its Blender execution is **NOT-RUN** because
the installed executable stalled on `--version` before it printed any output.

## Observed results

The unchanged experiment70 diagnostic was executed on the three historical
actual r4 CPU captures. Arm2 returns exit3 with area/rest22.0056357384; arm0 and
knee2 return exit0 with1.00001407557. Exit3 uses the existing fixed10× symptom
selector. It is not an artistic or collision acceptance threshold.

The already retained experiment53 **actual MPFB static** `body-positive` output
was authenticated against its public summary and unchanged original driver.
It is the same explicit raw-hm08 torso+1/jaw0 recipe, without macros or grounding.
The complete19,158-point cage agrees with the historical actual Nvwa cage within
`3.5762786865e-7m`. All1,797 garment positions agree within`7.5697898865e-6m`,
inside the original experiment53 numeric tolerance1e-5m.

| Selected triangle fitted rest | Area m² |
| --- | ---: |
| Historical actual MPFB static reference | `1.8834991180905933e-5` |
| Historical actual Nvwa fitted rest | `1.884345974021258e-5` |

Their area ratio is`0.999550583628304` (about−0.04494%). This is an executed,
retained static-reference comparison, not a newly executed Blender result or
the earlier coefficient-only analytical substitution. The already narrow rest
triangle also occurs in this explicit MPFB recipe. This does not authenticate
the author's recipe, establish a complete visible cause, or compute an MPFB
posed shoulder. In particular, the MPFB cutoff and Blender armature policy
effects on the arm2 numerator remain **UNKNOWN**. The current Rust all-positive
contract stays unchanged.

## Reproduce preparation and historical comparison

Supply the retained approved stage and experiment60 r4 keyframes; every output
path must be new. Full private arrays remain under `.work/garment74/`.

```sh
python3 -B experiments/74-garment-source-reference/prepare.py \
  --stage /PATH/TO/character-approved-20261016 \
  --captures /PATH/TO/build-r4-logs/cpu-matrix/keyframes \
  --out .work/garment74/NEW-preparation

python3 -B experiments/74-garment-source-reference/historical_reference.py \
  --reference /PATH/TO/character-approved-20261016/reference-full-run3 \
  --prepared .work/garment74/NEW-preparation/inputs.json \
  --out .work/garment74/NEW-historical-static-reference.json
```

Preparation authenticates the product descriptor, all2,422 retained extraction
receipt files, five fixed fit/import/garment source identities and each actual
capture. It calls experiment70's same all-source fit/weight/upload/FK guards.
No source data or historical result is edited. The historical comparison
authenticates the retained output against the unchanged public reference
summary and driver, then verifies its exact recipe and identity placement.

Three controls run through that same comparison CLI: the authenticated actual
static reference succeeds; a changed selected reference coordinate fails its
frozen output hash; a changed prepared actual-capture coordinate fails its
prepared-input hash. All three passed in normal and Python `-O` modes:

```sh
python3 -B experiments/74-garment-source-reference/test_controls.py \
  --reference /PATH/TO/character-approved-20261016/reference-full-run3 \
  --prepared .work/garment74/NEW-preparation/inputs.json \
  --scratch .work/garment74
```

These provenance controls do not exercise the unrun Blender driver.

## Proposed original-tool run — NOT-RUN

Root approved one offline no-render CPU reference after source freezing, with
one thread and a120s timeout. Root also required stopping if the initial
`--version` startup probes stayed blocked. Two task-owned version probes stayed
silent and were terminated. No further reference attempt or host repair was
made; the approved original-tool reference run was not spent.

After root resolves that prerequisite, the exact bounded wrapper is:

```sh
python3 -B experiments/74-garment-source-reference/run_reference.py \
  --executable /Applications/Blender.app/Contents/MacOS/Blender \
  --stage /PATH/TO/character-approved-20261016 \
  --inputs .work/garment74/NEW-preparation/inputs.json \
  --out .work/garment74/NEW-original-tool-run
```

The wrapper uses `--background --factory-startup --offline-mode --threads 1`,
isolated `BLENDER_USER_RESOURCES`, existing approved addon/garment files, and a
120s process timeout. It creates no user project, downloads, addons in the real
user environment, renders or GPU sessions. Its output is separate from every
historical capture. Expected resource use was estimated as one CPU thread,
under60s and under1GB; these estimates are **NOT-MEASURED**.

The unexecuted driver creates the actual MPFB base, torso target, official
53-bone game_engine rig and sportsuit, then refits them with original APIs.
It applies the explicit Nvwa-authored arm/knee rotations in the actual source
armature. Every source bone name/hierarchy, complete helper cage, canonical
rest matrix and resulting skin matrix must match the independently guarded
actual captures within existing numeric tolerances. A mismatch stops instead
of substituting captured matrices or claiming equivalent poses. Actual Blender
modifier evaluation would supply the proposed posed garment output.

## Missing relation and decision

No freshly executed original MPFB/Blender **arm2** output with a validated
53-bone rest/pose/skin relation exists from this round. Thus there is no actual
matched original-tool posed triangle to separate fit, weight cutoff and Blender
modifier contributions. Source reading and retained static geometry cannot
supply that missing relation. No minimum justified fix follows. Issue80 stays
open/HOLD; eight-parameter cohorts, fresh native/Web captures, render quality,
GPU/performance and the original author's reference remain outside this result.

PARTIAL — authenticated historical arm0/arm2/knee2 replay and actual historical
MPFB static-reference comparison; syntax and negative provenance controls.
NOT-RUN — new MPFB/Blender fit/pose/armature execution; executable runtime
version; policy attribution; repair or quality admission.
