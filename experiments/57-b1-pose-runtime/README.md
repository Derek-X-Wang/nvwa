# Actual B1 pose runtime experiment

The original four-influence route remains **HOLD**. The additive
`b1-full-weight-cpu` route passes the frozen 40-case numeric gate. This is
an experiment result, not product character admission or graphics acceptance.

| Measurement over 8 recipes × 5 poses | Original B1 + zero padding | Full-weight CPU + source frame gauge |
| --- | ---: | ---: |
| Body maximum component error | 20.99216 mm — FAIL | 0.0008941 mm — PASS |
| Garment maximum component error | 0.340224 mm — PASS | 0.140816 mm — PASS |
| Independent candidate-weight arithmetic | ≤ 1.56e-7 m — PASS | ≤ 1.82e-7 m — PASS |
| Canonical rest / posed matrices | 20/40 pass with raw fixed-frame comparison | 40/40 pass, ≤ 4.24e-6 |
| Joint heads | 40/40 pass | 40/40 pass, ≤ 8.35e-7 m |

The unchanged limits are 1 mm body, 3 mm garment, 1e-5 m arithmetic/heads,
and 1e-4 matrix components. Body comparisons cover all 19,158 source IDs;
garment comparisons cover all 1,797. UV seams produce 22,077 and 1,986 actual
mesh vertices. RMS, coverage, worst IDs, raw frame differences, influence
counts, and weight differences are retained in the comparison receipts.

The original source pads fewer than four influences by repeating the strongest
weight. An actual neutral/combined pose fails by 89.964 mm body and 17.676 mm
cloth. The minimal zero-padding repair reduces these to 20.992 mm and 0.340 mm.
The remaining body error includes the real body group: 2.861 mm at source 7633.
The full-cage worst source 18989 belongs to helper hair. No source group is
excluded from the full gate. Source truncation beyond four remains unchanged.

## Source and frame boundary

`prepare.py` verifies the immutable 55 B1 source tree
`93c9187185c547f33ad0974b5f060ba1d6847af6ecb932781e940cdd3d8a18ba`
and the approved common/pose identities, then copies it to ignored `derived/`.
Four separately recorded patches add explicit typed target paths, repair zero
padding, expose read-only existing rig data, and export the existing proxy map
enum. The original 55 threshold patch is retained separately. No morph,
rig-fitting, target parsing, helper, mesh-fitting, or animation-rest algorithm
is replaced. Preparation and 55 output preservation receipts record identities.

The actual source keeps base reference rotations while fitting joint heads.
MPFB refits rotations from the morphed endpoints. This produces raw rest-frame
component differences up to 0.06014736, although heads agree. The additive
adapter derives endpoint/roll frames `F` using the existing source algorithm
and actual morphed helpers. If the actual fixed rest frame is `C`, the frame
change is `Q = inverse(F) * C`. A canonical local postrotation `R` becomes
`inverse(Q) * R * Q` in the fixed source frame. Actual ECS propagation remains
in use. Canonical output is `C * inverse(Q)` and `P * inverse(Q)`.
Raw matrices, `F`, `Q`, and canonical matrices are all retained. Independent
checks establish the frame identities and physical skin invariance
`P * inverse(C) = (P * inverse(Q)) * inverse(F)`. Expected reference matrices
are never candidate inputs. Wrong-gauge fault injection is detected.

Humentity's CPU path builds meshes and propagates actual ECS bones. Its original
vertex skinning kernel is WGSL. The original Rust adapter evaluates the same
linear blend formulas on CPU; no GPU execution is claimed here. The full-weight
CPU contrast reads the actual source RigWeights and Mhclo mapping and performs
source-derived signed aggregation. It then retains only each final **positive**
per-bone aggregate, applies no four-influence cap, and normalizes the retained
row for blending. Recorded pre-normalization `full_joint_influences` rows are
already positive-filtered. This is a bounded bridge policy, not unchanged signed
source transfer with only its four-slot cap removed. The measured maximum is
seven retained body / six retained garment influences. Reference weights are
only comparator data, never used to compute candidate outputs.

Legacy GPU4 aggregation can retain negative aggregates after its top-four
selection. The garment has five such signed aggregates before selection at
source IDs **486, 685, 792**; negatives survive in two legacy render-vertex rows
(522/source486 and 422/source792). The CPU bridge drops those nonpositive final
aggregates; it does not clamp individual signed interpolation contributions.
MPFB instead retains interpolated garment weights strictly greater than
**0.001**, while this bridge retains weights strictly greater than **0**.
Normalized body weights match the reference exactly. The garment maximum
normalized L1 difference is **0.0034210871 at source ID 198**, where the bridge
retains two small positive influences that MPFB omits.

[API.md](API.md) states the precise portable API policy.
[evidence/policy-clarification.json](evidence/policy-clarification.json) records
source SHA256/line citations and the read-only observations. Preserved source
comments and historical receipt labels that say “every raw influence” or “raw
transfer” are overly broad; this clarification supersedes those descriptions.
The live API comment now states the positive-filter policy; historical snapshot
and actual capture bytes and numeric measurements remain unchanged. The
numeric PASS applies to this explicit positive-filtered CPU policy.

## Public API for 58

Package `adapter/` is `b1-pose-adapter`; Rust crate `b1_pose_adapter`.

- `apply_pose(&mut World, Entity, &DiagnosticPose)` resets all candidate locals
  and applies source-frame diagnostic rotations.
- `apply_pose_canonical(...)` resets and converts canonical rotations through
  source-derived gauges. Run actual Bevy transform propagation afterwards.
- `skin_mesh_frame(&World, Entity, &Mesh)` retains the four-influence route.
- `skin_mesh_frame_canonical(...)` additionally records canonical/gauge matrices.
- `skin_mesh_frame_full_weights(&World, Entity, &Mesh, &MhcloAsset, &[u16])`
  returns the additive full-weight CPU frame. The source IDs must be the actual
  mesh-to-source map used for the built mesh.

`SkinFrame` keeps actual raw bones/IBMs, rest/posed vertex arrays, normals,
tangents, four-slot attributes, and optional pre-normalization
`full_joint_influences` that already exclude nonpositive final aggregates.
`BoneFrame` additionally has optional `canonical_rest`, `canonical_posed`, and
`frame_gauge`. All matrices are column-major; arrays use MakeHuman Y-up metres.
`model_to_world` is the actual skeleton-root global matrix removed during
readback. Apply it **once** to a CPU-upload mesh. Remove skinning and morph
components from that CPU display mesh to prevent double deformation. Normals
use the source linear skin transform and normalization; the display world
normal transform must use inverse transpose if it has nonuniform scale.
Tangents are transformed and normalized with handedness retained. All vectors
are finite; normal/tangent angle and appearance acceptance remain NOT-RUN.

`humentity::load_and_insert_humentity_assets_explicit` mirrors the original
loader but accepts `Vec<String>` target paths. It requests typed target handles
and does not call `load_folder`. The native omission control exits 1 without
creating an output frame. HTTP/browser omission and graphics evidence belong
to 58.

## Reproduce and inspect

Preparation, compilation, execution, and comparison are distinct commands:

```sh
python3 experiments/57-b1-pose-runtime/prepare.py --verify
python3 experiments/57-b1-pose-runtime/build.py --receipt NEW_BUILD_RECEIPT.json
B1_FULL_WEIGHTS=1 python3 experiments/57-b1-pose-runtime/run_all.py --out NEW_RESULTS
/Applications/Blender.app/Contents/Resources/5.2/python/bin/python3.13 \
  experiments/57-b1-pose-runtime/compare_all.py --results NEW_RESULTS --out NEW_COMPARISON.json
```

The comparator uses Blender's already-installed Python/NumPy. No model,
download, extra host, window, GPU, or graphics context was used. Every check
was below five minutes, so no long-running wefty job was needed.

Authoritative receipts are `evidence/post-comment40.json` (post-comment source-binding PASS, including rigid/vector gates),
`evidence/four-slot40-repaired.json` (original four-slot HOLD),
`evidence/padding-red.json`, `evidence/weight-diagnosis.json`,
`evidence/gauge-controls.json`, `evidence/mutation-controls.json`, and
`evidence/sampled-controls-current.json`. Repeated combined → neutral → combined
→ neutral actual frames match exactly in `evidence/idempotence.json`.

The exact full40 adapter source is frozen in `evidence/full40-adapter-source/`,
verified against execution tree SHA
`118d13a5884cd4795c47e68f634a7dc52e9ec9f190d3432750bb594c9b5de549`.
The current adapter was subsequently formatted and its dependency paths made
portable. Full40 arrays and caches remain ignored under `results/` and `target/`.
The pre-padding executable was overwritten before its hash was captured;
its original executed output hashes, build log and source differences remain,
and no original binary identity is claimed. The post-padding four-slot
executable is retained privately with its matching execution SHA.

## Portable sampled CI

```sh
python3 experiments/59-b1-ci-inputs/prepare_ci_inputs.py --out NEW_SEED
python3 experiments/57-b1-pose-runtime/prepare.py --ci-inputs NEW_SEED
B1_CI_INPUTS="$PWD/NEW_SEED" cargo test --locked --jobs 1 \
  --manifest-path experiments/57-b1-pose-runtime/adapter/Cargo.toml \
  --test sampled -- --nocapture
python3 -m unittest discover -s experiments/57-b1-pose-runtime -p test_prepare_ci.py -v
cargo fmt --manifest-path experiments/57-b1-pose-runtime/adapter/Cargo.toml --package b1-pose-adapter -- --check
```

Use an authenticated seed and new outputs. CI preparation pins the exact 59
manifest/archive and verifies every seed file before writing. It replays the
existing packaging/threshold patches plus the four 57 patches. Its `derived/src`
bytes exactly match the full40 source; only dependency paths and packaging
metadata differ. Normal private-source preparation retains its approval gate.

With `B1_CI_INPUTS` set, the Rust integration test launches the actual executable
for all 40 cases. The standard-library checker measures all 53 bone matrices
and heads, 67 body / 42 garment sampled IDs, independent candidate-weight
arithmetic, finite data and full candidate source coverage. It also runs 15
fault controls through the exact comparator and verifies restored green.
The test fails when the seed is absent under `CI=true`; local omission prints
NOT-RUN. Results and faults remain in the printed temporary output directory.
This sampled CI regression does not replace the full local numeric gate.

R2 gate repair: shared `validation.py` rejects malformed dimensions, zero/nonunit
normal/tangent vectors, invalid tangent handedness, singular/nonrigid matrices,
wrong rest/IBM pairs and inconsistent gauges/physical skin. These checks remain
active under `python -O`. `evidence/sampled-controls-current.json` retains 15
red mutations with restored green. The full40 aggregate includes these vector
and matrix checks; appearance acceptance remains separate.

Format scope is the adapter package. `cargo fmt --all` also reaches local
vendored dependencies and changes upstream formatting. Those vendor edits were
restored from verified source; no formatting-only vendor patch was retained.
