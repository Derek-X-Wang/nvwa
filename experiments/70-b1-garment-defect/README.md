# One sportsuit shoulder defect — issue80

This experiment diagnoses garment display triangle200 / ordered source IDs
`[246,244,182]` at torso+1, jaw0, arm rehearsal2s. It changes no garment, weight,
bone, runtime, source asset, camera, material, deletion policy or threshold.
There is **no candidate correction**. Garment quality remains **HOLD**.

The retained shoulder stretches geometrically: its fitted-rest area is
`1.884345974e-5 m²`, versus actual arm2s area `4.146623111e-4 m²`, a22.0056× ratio.
Arm0 and knee2 controls are near1×. This is one geometry witness, not a complete
classifier of the visible shoulder/waist poke-through. Waist and the other
neutral8-vertex fold region are outside this experiment.

## Independent replay

`diagnose.py` uses only Python's standard library. It authenticates the admitted
manifest and every payload, validates the request and actual held sample against
independently supplied recipe/clip/time, and matches exact source/render topology.
It reconstructs all1,797 fitted garment vertices from that same frame's fitted
19,158-point body cage and the original normalized **signed** MHCLO coefficients
and offsets. It independently transfers source bone weights, retains **every
positive final aggregate**, normalizes, and evaluates actual53-bone matrices.
The unchanged experiment60 independent authored-FK/gauge/rigidity/IBM guard is
reused and its two Python source hashes are recorded. Changing a record's time
labels while retaining the wrong actual bone pose is rejected. The new fit and
weight/LBS reconstruction does not call product math. The selected triangle
and16-vertex/52-incident-triangle neighborhood are scored
without replacing the original source data or clipping helper coefficients.

```sh
python3 -B experiments/70-b1-garment-defect/diagnose.py \
  --asset-root assets/characters/mpfb-b1-v1 \
  --captures /PATH/TO/RETAINED60/keyframes --out /NEW/REPORT/DIRECTORY

python3 -B experiments/70-b1-garment-defect/diagnose.py \
  --asset-root assets/characters/mpfb-b1-v1 --frame /PATH/TO/ACTUAL-FRAME.json \
  --torso 1 --jaw 0 --clip b1_arm_rehearsal_v1 --seconds 2 \
  --fail-on-shoulder-stretch --out /ANOTHER/NEW/DIRECTORY
```

Without the optional diagnostic flag, exit0 means complete source/upload
reconstruction, **not repaired geometry or quality acceptance**. The flag returns
exit3 when any selected triangle area/rest exceeds the historical fixed10×
symptom selector. That selector is not an artistic or collision acceptance
threshold. Input/reconstruction failures return exit2 and remain in the new
report's failures; incomplete input cannot become verified. JSON must be finite
and duplicate-free. Existing outputs cannot be overwritten. Compressed and
decoded inputs are bounded64MiB. Output contains only compact metrics and the
three selected point traces per frame, not full private arrays.

The30-frame mode requires torso−1/0/+1 × jaw0 × both clips × source0/1/2/3/4.
It checks the complete cohort and retains every failure. It does not fill jaw±1
coverage. Single-frame mode requires expected torso/jaw/clip/seconds separately;
matching two mislabeled records is not a valid check.

### Explicit68 full-base input (bounded shoulder supplement)

The68 shoulder Work's actual timeline entry is `arms`, not `probe-entry`.
Specify it independently; never rewrite a captured sample to fit the analyzer:

```sh
python3 -B experiments/70-b1-garment-defect/diagnose.py \
  --asset-root assets/characters/mpfb-b1-v1 \
  --frame /ACTUAL68/frame.json --input-format bridge68 --timeline-id arms \
  --torso 1 --jaw 0 --clip b1_arm_rehearsal_v1 --seconds 2 \
  --out /NEW/68-SHOULDER-REPORT

python3 -B experiments/70-b1-garment-defect/compare.py \
  --asset-root assets/characters/mpfb-b1-v1 \
  --left /NATIVE68/frame.json --right /WEB68/frame.json \
  --input-format bridge68 --timeline-id arms \
  --torso 1 --jaw 0 --clip b1_arm_rehearsal_v1 --seconds 2 \
  --out /NEW/68-PAIR.json
```

Use seconds0 for the neutral control. The adapter selects the existing
`full_base` object by reference, or `frame.full_base` in a68 download envelope.
It does not manufacture an experiment60 request, replace timeline identity or
modify any captured field. Actual shape/time/entry/FK/source/upload guards still
run. Raw frame input explicitly reports acknowledgement **NOT-CHECKED**: root
must separately retain and verify the exact matching ready68 report/request.
With an envelope, matching ready/acknowledged/succeeded/current, IDs, compact/full
base identity, runtime/error state and Work hash are checked. Even that is a
historical capture acknowledgement, not a live-current promise or GPU claim.

For historical60 versus actual68 comparison, use `--left-format experiment60
--right-format bridge68 --left-timeline-id probe-entry --right-timeline-id arms`.
The shared `--input-format` and `--timeline-id` defaults remain experiment60 and
probe-entry, preserving historical invocation semantics. Per-side overrides
permit real entry IDs to differ; geometry/clip/source time must still match.

The18 current controls include five new **synthetic adapter controls**, not
actual68 runtime evidence. Original13-control source copies are retained under
`evidence/pre-interop-source/` for the already frozen reports. Actual long-torso
jaw0 arm0/2 native/Web captures are root's bounded supplement. The54-case matrix
below is a complete later plan and is **not this round's minimum gate**.

```sh
python3 -B experiments/70-b1-garment-defect/test_controls.py \
  --asset-root assets/characters/mpfb-b1-v1 --frame /ACTUAL/TORSO+1-JAW0-ARM2.json.gz
python3 -B -O experiments/70-b1-garment-defect/test_controls.py \
  --asset-root assets/characters/mpfb-b1-v1 --frame /ACTUAL/TORSO+1-JAW0-ARM2.json.gz
```

The controls mutate real retained input through the same analyzer. They cover
stale actual time, relabeled shape, changed upload, top-four truncation, changed
source coefficients, time metadata relabeling with stale bones, two identically
stale comparison records, invalid source
manifest, nonfinite/duplicate JSON, and explicit synthetic signed aggregation
and column-major placement. A passing control suite does not run production or
prove visible quality. See [RESULTS.md](RESULTS.md) for actual execution limits.

## Root-owned current native/Web comparison

No new renderer or Cargo package is added. Use the existing
[experiment60 actual production Studio probe](../60-b1-continuous-motion/README.md)
on root's exact current source snapshot, with its normal B1 motion Work and
unmodified baseline materials/camera. Root owns any compilation, app, browser,
server, GPU and output directories. Existing historical compiled binaries or
captures must retain their historical identity; they are not current-head proof.

1. Open a task-owned current motion Work with saved appearance None. Keep the
   camera and material policy fixed and retain the exact Work bytes and hashes.
2. `python3 -B experiments/70-b1-garment-defect/requests.py` prints54 held
   requests/platform: torso−1/0/+1 × jaw−1/0/+1 × both existing clips ×0/2/4s.
   Native uses60's command-file protocol. Web uses the visible **Test-only B1
   diagnostics** fields, **Sample exact frame**, then **Store exact capture**.
   Both paths use60's shared commands and actual production mesh readback.
3. Require the exact request ID and requested shape/clip/time in the acknowledged
   captured record; errors/timeouts remain failures. The Web sink's32-record cap
   requires two new capture directories/batches of27. Never overwrite old data.
   A capture for the previous request cannot fill the next case.
4. For a minimal visual witness, retain held arm0, arm2 and knee2 at torso+1/jaw0
   on each platform, with the same camera and normal baseline materials. Also
   retain torso−1/0 controls and jaw endpoints. Screenshots are separate from CPU
   storage receipts; none have been newly captured by this worker.
5. Run the single-frame analyzer on each actual record with independently
   specified values. Compare each corresponding native/Web pair and optionally
   current versus historical same-case records:

   ```sh
   python3 -B experiments/70-b1-garment-defect/compare.py \
     --asset-root assets/characters/mpfb-b1-v1 \
     --left /NATIVE/EXACT-ID.json --right /WEB/EXACT-ID.json \
     --torso 1 --jaw 0 --clip b1_arm_rehearsal_v1 --seconds 2 \
     --out /NEW/PAIR-REPORT.json
   ```

`compare.py` independently validates/reconstructs both records first, then
compares all1,797 garment local/rest/stage points and actual skin matrices.
Local/rest/stage tolerance1e-5m and matrix1e-4 preserve experiment60's independent
numeric bounds. No threshold is tuned to garment appearance. Historical labels,
current compiled source/served bytes, observed GUI actions, screenshots and GPU
results must remain separate. A planned54 matrix is not54 executed cases.

## Correction gate

A source/runtime implementation mismatch would justify a narrowly specified
correction followed by unchanged-cohort replay, boundary controls, current native
and Web evidence, independent review and CI. This replay instead reproduces the
fit/weights/upload. It does not supply the intended authoring body recipe or an
authoritative improved garment mapping. Prior61 smoothing and offset-retention
recipes are rejected controls, not new candidates for tuning.

No body deletion, four-weight workaround, source coefficient clipping, offset
removal, pose removal, material/camera concealment, collision depth claim or
appearance-quality waiver is permitted. Local signed triangle projections, if
collected by60, describe only a local triangle side on an open surface. They are
not global inside/outside or true collision penetration depth.
