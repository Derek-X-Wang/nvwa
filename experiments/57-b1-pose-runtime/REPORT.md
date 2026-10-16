# B1 pose gate report

Decision: experimental full-weight CPU numeric gate passes; original four-slot
route stays HOLD. Neither route is admitted to product by this report.

## Exact identities

- Common approved input manifest: `2e8566a4f12de710ead88f6aa2d71fc44e0680761a4f2fdc48a844b6f3534ab7`.
- Authored pose file: `8e51c044841eb1c6cb96d583ca927cceb51ddf7d0729f4526f61777c8b7adab2`.
- Frozen full reference manifest: `98ffb4b7947101bdd2107055beed866d7f040b33f699fb859c090c4c03242636`.
- Upstream source commit: `286d33124648501535655a0de811cef55152b9fd`.
- Immutable 55 B1 source tree: `93c9187185c547f33ad0974b5f060ba1d6847af6ecb932781e940cdd3d8a18ba`.
- Final shared 57 source tree: `16988777ebca441dc9c22edeaf230ee3a62555df9942a3901371f763b826801e`.
- Its source-code-only tree: `1c75796828d3af9311ac9bf6f8e8777a77d66838e598544aff7377b908c8a6e8`.
- Pre-comment formatted adapter tree: `61a705705f26aad31470d89e799502e4e1fd67b6a9057e0afda623dfba09b595`.
- Final adapter tree after the one-line policy-comment correction: `5f91da92e274bcee0b67e8237518200f8206f14b68e93aef015de3eb865701af`.
- Final restored-source executable: `878fc73a9d81cad6679aebe8e9f241dd9ba8d1420941646b40957e6a736bcf34`.

`evidence/preparation.json` records all four source patch hashes. The old
threshold patch belongs to 55 and remains separate. The full40 pre-format
adapter source is retained and hash-bound under `evidence/full40-adapter-source/`.
Formatting-only vendor drift was detected, then restored; no fifth vendor patch
was retained. Package-only formatting passes. Both original B0/B1 source trees
and all 16 preserved 55 output/log identities still match their recorded hashes.

## Build, execution, comparison

All commands ran in the isolated research checkout. No root dependency or
product file changed. No network download, model run, graphics context,
additional machine, external write or Git commit was used by this worker.
Every individual check took less than five minutes. Durations are local
observations while other work could compete, not performance acceptance.

Final compilation and real sampled execution are one Cargo invocation, with
separate compile/test output in `evidence/sampled-cargo-test-restored.log`:

```sh
B1_CI_INPUTS="$PWD/.work/b1-pose-runtime/ci-inputs" CI=true \
CARGO_NET_OFFLINE=true CARGO_TARGET_DIR="$PWD/experiments/57-b1-pose-runtime/target" \
cargo test --offline --locked --jobs 1 \
  --manifest-path experiments/57-b1-pose-runtime/adapter/Cargo.toml \
  --test sampled -- --nocapture
```

The restored source compiled in 25.92 seconds. The real sampled test passed
40 cases and 15 comparator fault controls in 127.88 seconds. Its exact
commands, output hashes and binary identity are in `evidence/sampled-restored.json`.
This is local CI-shaped proof; hosted CI is owned by root.

Fresh final full execution uses that same compiled binary, without rebuilding:

```sh
B1_FRAME_GAUGE=1 B1_FULL_WEIGHTS=1 \
python3 experiments/57-b1-pose-runtime/run_all.py \
  --out experiments/57-b1-pose-runtime/results/final-current40
```

Full comparison is separate and keeps critical checks active under optimization:

```sh
/Applications/Blender.app/Contents/Resources/5.2/python/bin/python3.13 -O \
  experiments/57-b1-pose-runtime/compare_all.py \
  --results experiments/57-b1-pose-runtime/results/final-current40 \
  --out experiments/57-b1-pose-runtime/evidence/final-current40.json
```

The final receipt records complete body/garment source coverage, RMS and maximum
errors, all 53 raw/canonical frames and identity checks, independent f64
candidate-weight arithmetic, and nonzero unit normal/tangent validation. The
predeclared limits remain 1 mm body, 3 mm garment, 1e-5 m arithmetic and joint
heads, and 1e-4 rigid frame components. No source ID or helper group is removed
from the full gate. Normal/tangent vector structure is checked; their angle and
appearance acceptance remain NOT-RUN.

## Preserved failures and boundary

The first actual source run failed geometry by 89.964 mm body / 17.676 mm cloth.
Repeating the strongest joint to pad four slots was the isolated cause. The
minimal zero-padding source fix reduces these to 20.992 mm / 0.340 mm. Remaining
four-slot body truncation fails the full cage and real displayed body group
(2.861 mm); it remains HOLD. Raw fixed-animation rest frames differ from MPFB
by up to 0.06014736. The source-derived gauge preserves those raw differences,
uses no expected matrices, and proves physical-skin equivalence. The additive
full-weight CPU route uses original source weights and the actual Mhclo mapping,
then retains only final positive per-bone aggregates, applies no four-influence
cap, and normalizes those retained rows. Its recorded pre-normalization rows
are already positive-filtered. This is an explicit bridge policy beyond removal
of truncation; it never substitutes reference weights.

Recorded red controls include actual missing-target execution, actual original
padding failure and repair, wrong bone order, omitted deformation, tampered
expectation, wrong/zero gauge, missing bone, zero/empty normals and tangents,
nonfinite matrices, wrong rest/IBM and invalid tangent handedness. Restored
captures pass. Invalid vector/matrix controls run through the same shared
`validation.py` used by full local and sampled CI comparators. Admission gates
use explicit exceptions, not removable Python assertions.

The original pre-padding executable was overwritten before hashing. Its original
executed output hashes, build log and minimal source diff are retained; no
original binary identity is claimed. Its post-padding executable is retained
privately and matches the historical four-slot execution receipt.

Build errors and early comparisons attempted before outputs existed remain in
the evidence logs. The final current receipt, not these intermediate attempts,
is authoritative. GPU/native/Web rendering, interaction, state exchange and
HTTP omission evidence belong to 58. A stays the earlier source-compiled numeric
control. Old M2 motion quality HOLD and other backend admission gaps are unchanged.

## Pre-comment current result

Fresh final execution completed all 40 cases in 108.887 seconds with the exact
current adapter/source/binary identities above. The separate optimized full
comparator returns PASS: body maximum component 8.9406967e-7 m; garment
1.4081597e-4 m; candidate-weight arithmetic at most 1.8100214e-7 m; canonical
rest/posed components at most 4.2319298e-6; heads at most 8.3446503e-7 m. All
vector/rigidity/gauge gates pass 40/40. The original four-slot route stays HOLD.

`evidence/final-current40.json` is the preserved pre-comment receipt. Its execution summary is copied
to `evidence/final-current40-execution.json`; both bind the current binary.
The full receipt binds `compare.py`, `compare_all.py` and transitive
`validation.py` SHA256 identities. The unchanged validator used by the restored
seeded test is also bound in `evidence/sampled-restored-binding.json`; the
original seeded receipt remains byte-for-byte in `evidence/sampled-restored.json`.
`evidence/sampled-controls-current.json` records 15 red controls and restored green
under `python -O`. `evidence/gate-freeze.json` binds all authoritative receipts.
No owned computation process remains after the final comparison; arrays, source
materialization, executable and caches are retained for root review.

## Weight-policy clarification

The numeric gate remains valid for the existing positive-filtered CPU bridge.
It does not establish parity with unchanged signed source transfer with only
the four-influence cap removed. Source GPU4 sums signed Mhclo contributions,
selects four aggregates without a final positivity filter, and normalizes that
selection. The CPU bridge sums those contributions first, removes each final
aggregate that is not greater than zero, retains all remaining influences,
then normalizes. It does not clamp individual negative interpolation terms.

Read-only evaluation found five negative garment aggregates before top-four
selection at source IDs 486, 685 and 792. Only IDs 486/792 retain negatives in
the recorded legacy four-slot attributes; ID 685's negative aggregates fall
out during top-four selection. Those legacy arrays are preserved as observed
and are not used by the full CPU deformation.

MPFB's garment interpolation has its own strict >0.001 cutoff. The bridge's
strict >0 cutoff therefore also retains small positive influences MPFB omits.
The maximum normalized garment L1 difference, 0.0034210871, occurs at source 198: pelvis 0.0007222896 and upperarm_l 0.0009882539 are retained by the bridge and
omitted by MPFB. Normalized body L1 remains zero. These differences are explicit;
no reference weights enter candidate deformation.

See [API.md](API.md) and [policy-clarification evidence](evidence/policy-clarification.json).
The evidence binds relevant source SHA256 identities and line ranges. Earlier
“every raw influence”/“raw transfer” descriptions in preserved source comments
and historical evidence are superseded by this note. No deformation algorithm,
numeric gate or actual historical capture bytes changed. The subsequent one-line
live API comment correction and cached rebuild are recorded below.

## Final API-comment source binding

The live API comment now states: “Every positive final aggregate is retained
before normalization; signed nonpositive aggregates are omitted.” This is the
only library source change after the preceding receipts. Reversing that one
comment reproduces the old source SHA256 exactly; no algorithm changed.
`evidence/api-comment-correction.json` records the exact one-line diff and hashes.
The cached CLI rebuilt successfully in 6.52 seconds and remains byte-identical
(SHA256 `878fc73a9d81cad6679aebe8e9f241dd9ba8d1420941646b40957e6a736bcf34`).

The exact cached rebuild, fresh execution, and separate comparison commands are:

```sh
python3 experiments/57-b1-pose-runtime/build.py \
  --receipt experiments/57-b1-pose-runtime/evidence/build-09-api-comment.json
B1_FRAME_GAUGE=1 B1_FULL_WEIGHTS=1 \
python3 experiments/57-b1-pose-runtime/run_all.py \
  --out experiments/57-b1-pose-runtime/results/post-comment40
/Applications/Blender.app/Contents/Resources/5.2/python/bin/python3.13 -O \
  experiments/57-b1-pose-runtime/compare_all.py \
  --results experiments/57-b1-pose-runtime/results/post-comment40 \
  --out experiments/57-b1-pose-runtime/evidence/post-comment40.json
```

These new receipts bind the corrected comment and current adapter source without
rewriting earlier actual captures, source snapshots or binary identities.

Post-comment outcome: PASS40/40 with the same declared tolerances and exact
previous numerical maxima. Actual execution took 104.536 seconds.
The authoritative current-source comparison is `evidence/post-comment40.json`;
its public execution copy is `evidence/post-comment40-execution.json`.
`evidence/gate-freeze-post-comment.json` binds the corrected adapter source,
byte-identical executable, transitive validator, explicit policy clarification
and new receipts. Earlier full40 receipts and pre-comment inventory/policy copies
remain preserved. No GPU, download or algorithm change was used.
