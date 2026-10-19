# Matched original-tool shoulder pose — issue80

**HOLD. No correction selected.** Actual offline Blender5.2.2 LTS and the retained
MPFB2.0.18 reproduce the shoulder stretch for explicit raw-hm08 torso+1/jaw0
and the Nvwa-authored arm2 diagnostic pose. Source triangle200 remains
`[246,244,182]`. The original garment author's body recipe remains **UNKNOWN**.
The all-positive final aggregate Rust skinning contract stays unchanged.

Fresh ordinary desktop and Web builds also completed playback, jaw editing,
Undo/Redo and a full native→Web→native saved-file round trip. The final file was
byte-identical after native re-save. This separate [runtime regression](RUNTIME-REGRESSION.md)
uses the old two-parameter profile and does not admit garment quality.

## Actual reference result

The unchanged experiment74 driver and its existing120s wrapper ran successfully
in3.075s after Blender's `--version` returned in0.670s. The reference uses actual
MPFB base/target/rig/garment/refit APIs and actual Blender armature modifier
evaluation. It never imports historical skin matrices as reference output.
No harness/API repair, rendering, download, inference, global addon installation,
GUI/GPU session, product edit, dependency edit or build was needed.

| Case | Historical actual Nvwa area/rest | Actual original-tool area/rest |
| --- | ---: | ---: |
| arm0 | 1.000014075566 | 0.999991330581 |
| arm2 | 22.005635738421 | 22.009337055894 |
| knee2 | 1.000014075566 | 0.999991330581 |

The table uses independent stdlib double-precision areas on actual recorded
vertices. The original Blender driver's mathutils calculation reports
22.009332789655 for arm2 and0.999990972450 for the controls. The small last-digit
difference is geometry arithmetic; both original calculations use the same
actual modifier-evaluated vertices. Neither is an appearance threshold.

All three cases passed the unchanged source driver's complete19,158-point
current helper-cage guard, exact53-bone name/hierarchy guard, canonical-rest
relation and independently authored skin-transform relation. Maximum cage error
is2.9802322388e-7m; maximum canonical-rest matrix component error is3.8743019104e-6;
maximum skin matrix component error is1.2781820260e-6. Existing guard tolerances
remain1e-5m,1e-4 and1e-4 respectively.

The comparison CLI independently derives skin transforms from the recorded
original armature matrices. Those transforms and actual original vertex weights
reconstruct all1,797 modifier-evaluated points within1.2765305102e-7m. It checks
the full fitted-rest/source-ID relation within the existing1e-5m static numeric
bound: observed maximum7.5101852417e-6m. These are fit/rig/pose checks, not exact
posed mesh equality. Maximum original/Nvwa posed component differences are
7.7486038208e-6m at arm0,0.0001408159733m at arm2 and0.0002747178078m at knee2.
The source paths deliberately retain different weight policies.

## What explains the selected numeric symptom

At fitted rest the selected triangle is already narrow in the real original
tool: area1.8835154471e-5m², longest edge41.201mm, and corresponding height0.9143mm.
After arm2 its area is0.0004145492632m², longest edge52.339mm, and height15.841mm.
The narrow denominator plus unequal motion across its corners explains the
large area ratio in this explicit recipe. This is bounded geometric attribution,
not authentication of the original artist's recipe or a complete visual cause.

The actual original normalized upperarm weights at246/244/182 are approximately
71.985%,79.840% and24.558%. The lower-arm rotation is applied to the real rig,
but these three vertices have no lowerarm weight. The shoulder/torso mixture
moves the three corners differently. Rust retains vertex182's small positive
`spine_01` influence, about0.00011839; actual MPFB omits it. Both paths still
produce the same large symptom.

The following are **analytical swaps**, using actual frozen rest/weight arrays
and the same historical Nvwa skin matrices. They are never labeled Blender
outputs or proposed product corrections:

| Fitted rest | Weights | Analytical arm2 area/rest |
| --- | --- | ---: |
| Rust | Rust all-positive | 22.005707414235 |
| Rust | Actual MPFB retained rows | 22.004673278134 |
| Actual MPFB | Rust all-positive | 22.010338239764 |
| Actual MPFB | Actual MPFB retained rows | 22.009303943978 |

These controls bound the observed raw-versus-normalized fit and cutoff effects
for this case. None removes the roughly22× stretch. They do not justify changing
signed coefficients, offsets, thresholds or full-positive Rust weights. Prior
smoothing/offset candidates remain rejected. No source replacement or product
candidate is admitted. A future source/remapping proposal still needs an
identified reference recipe and its own quality evidence.

## Provenance and controls

[evidence/reference-freeze.json](evidence/reference-freeze.json) authenticates
all actual reference JSON files plus raw stdout/stderr and execution receipt.
[evidence/results.json](evidence/results.json) records full comparison numbers
and selected traces. [evidence/provenance.json](evidence/provenance.json) records
runtime/source identities and cleanup. Full arrays and logs stay private in
`.work/garment80-next/`. Every old experiment74 freeze, capture and source remains
unchanged. The approved2,422-file extraction was authenticated before the run
and reverified after it.

The comparison calls experiment70's unchanged source decoder/positive-row math.
All11 CLI controls pass in normal and Python`-O` modes. One authentic baseline
succeeds; frozen output/input tampering fails. Synthetic copies with updated
hash ledgers still reject stale capture IDs, bone names, rest/skin relations,
mesh coverage/source order, modifier policy and changed posed points. These
controls test the comparison seam. They are not additional Blender executions,
new original outputs or visual acceptance tests.

## Reproduce

Use the existing approved stage and retained experiment60 r4 keyframes. Output
paths must be new. Historical references are inputs, never overwritten.

```sh
python3 -B experiments/74-garment-source-reference/prepare.py \
  --stage /PATH/TO/character-approved-20261016 \
  --captures /PATH/TO/build-r4-logs/cpu-matrix/keyframes \
  --out .work/garment80-next/NEW-preparation

python3 -B experiments/74-garment-source-reference/run_reference.py \
  --executable /Applications/Blender.app/Contents/MacOS/Blender \
  --stage /PATH/TO/character-approved-20261016 \
  --inputs .work/garment80-next/NEW-preparation/inputs.json \
  --out .work/garment80-next/NEW-original-tool-run

python3 -B experiments/75-garment-posed-reference/compare.py \
  --prepared .work/garment80-next/preparation/inputs.json \
  --run .work/garment80-next/run1-original74 \
  --freeze experiments/75-garment-posed-reference/evidence/reference-freeze.json \
  --out .work/garment80-next/NEW-comparison.json

python3 -B experiments/75-garment-posed-reference/test_controls.py \
  --prepared .work/garment80-next/preparation/inputs.json \
  --run .work/garment80-next/run1-original74 \
  --freeze experiments/75-garment-posed-reference/evidence/reference-freeze.json \
  --scratch .work/garment80-next/NEW-controls
```

The comparison commands above authenticate this round's frozen original run.
A new Blender execution needs its own newly recorded hash ledger; do not edit
this round's ledger to admit a rerun. The wrapper requests background, factory
startup, offline mode and one thread, isolates Blender user resources, and has
a120s terminate/kill timeout. Task-owned Blender PID98909 exited0 and a fresh
exact-PID check confirms it is gone. No persistent task process remains. The
new scratch is intentionally retained for root review. Memory use was not
measured. No run exceeded five minutes.

PARTIAL — actual offline MPFB fit/53-bone rest/skin/modifier output and all three
historical-pose relations verified;11/11 comparison controls pass normally and
under`-O`. Source recipe remains UNKNOWN and quality HOLD. NOT-RUN — fresh
Nvwa/native/Web captures, rendering/visual acceptance, eight-parameter cohorts,
GPU/performance, source replacement, product correction or admission.
