# 45 — Genuine sample numerical admission study

**HOLD genuine playable admission.** The successful CPU trial in experiment 44
produced genuine raw output. This report studies only that one 90-frame clip.
Applying experiment 43 unchanged does not establish a valid SOMA30-to-Nvwa18
mapping. It adds a second hip-height offset and leaves substantial differences
between named source and target endpoints. These numbers are observations of
this particular attempted mapping, not a general retargeting error benchmark.

This is a report-only standard-library calculation. No model, backend, weights,
network access, build, normalizer, exporter, Work, renderer, or product code is
needed or run. The mapped poses exist only in memory for numerical comparison.
`provenance_kind=generated` describes the original sample; no authored relabeling
or producer-acceptance bypass occurs. Experiment 42 still rejects generated
playable admission. Experiment 43 and the target fixture remain unchanged.

## Reproduce from public inputs

From the repository root, Python 3.9+ with standard library only:

```sh
python3 -B experiments/45-genuine-rig-admission/probe.py
python3 -B experiments/45-genuine-rig-admission/test_controls.py
```

Both commands default to JSON on stdout. To retain a result, supply
`--out path/to/new-result.json`; its parent must exist. Existing identical bytes
are accepted without rewriting. Existing different bytes and output symlinks are
rejected. A fresh private path is appropriate for another reproduction.

`results.json` and `verification.json` retain actual Python 3.14.7 invocations.
`portability.json` records successful probe/control invocations on Python 3.9.6,
3.12.11, and 3.14.7. Float results can differ in the last bits between runtimes;
the output files are not claimed byte-identical across runtimes. Use a fresh
output path when reproducing with another runtime.
All eight input hashes are checked before experiment 43 definitions load. Its
hash-checked source bytes are executed with a non-main module name, so its
authored experiment does not run. The target fixture is read and checked by its
existing extractor. No absolute private path is needed by the current scripts.


Pinned inputs are the two public 44 raw files, public generation/process/stdout
receipts, 41 `source-skeleton.json`, frozen 43 `spike.py`, and the exact fixture
GLB. The successful trial receipt binds its request and both raw hashes. This
study checks those identities; it does not rerun the provider or independently
recreate all process evidence. Experiment 44 owns that evidence.

Raw hashes:

| File | Bytes | SHA-256 |
|---|---:|---|
| root_positions.f32 | 1080 | `dcc221d506999a803b1d0fddef87abc0131b1e8f4e64187bc57fde3a63c204af` |
| local_rotations_xyzw.f32 | 43200 | `67914c5d72c54429bf8a70d3f9ef43157fb5181fa36ab2c5f8ce7f9dc69d3a55` |

All sampled floats are finite. The maximum quaternion norm error is
`8.412634311394385e-8`. The trial specifies 30 fps; sample times are `i/30`, ending
at `89/30` seconds. Timing is not stored in the raw binaries themselves.

## Actual root-position failure and bounded algebraic correction

The source C++ skeleton has Hips rest translation zero. Its sampled Hips Y ranges
from `0.9940531254` to `0.9962186813` m. The frozen target has a separate scene
root at rest Y `0.0799999982` m and a pelvis child at local Y `0.7499999404` m.
Target pelvis rest world Y is therefore `0.8299999386` m.

43's authored-source rule was:

```text
target_root = target_rest_root + (source_root - source_rest_root)
```

Its authored Hips rest was deliberately aligned with the target pelvis. That
anchor does not transfer to the actual source's zero Hips offset. Applying the
rule unchanged puts the target pelvis at Y `1.823558187–1.826174534` m.

For the explicit, narrow policy of matching target pelvis world position to the
source Hips trajectory `h(t)`, the necessary scene-root translation is:

```text
target_scene_root_translation(t) =
  h(t) - R_target_root(t) * S_target_root * target_pelvis_rest_local_translation
```

`R` is the animated root rotation and `S` is its exact rest scale. This derivation
uses the observed target hierarchy: identity nonjoint ancestor and pelvis
directly under the root. It does not generalize this formula to arbitrary rigs.
A future signed coordinate conversion must also transform `h(t)` consistently.
The returned scene-root translation is absolute and replaces the target root's
translation once. Do not add target rest-root translation or exporter height.

The oracle is generic affine forward kinematics (FK): calculate target pelvis
**world position**, then compare it with source Hips. Rotating the root also
rotates the pelvis offset. Merely subtracting a fixed 0.75 m height is insufficient.

| Actual 90-frame root policy/control | Maximum pelvis world mismatch (m) |
|---|---:|
| Unmodified 43 with source rest Hips=zero | **0.8299999133** |
| Subtract unrotated pelvis offset | **0.0282249801** |
| Rotation-and-scale affine subtraction above | **1.7347e-18** |
| Add target root rest again after affine subtraction | **0.0799999982** |

The corrected diagnostic scene-root XZ path is `0.1676906921` m, while the source
Hips XZ path is `0.0734929272` m. This difference is expected compensation for the
rotating pelvis offset. Scene-root trajectory equality would be the wrong test.
Hip-world equality proves this declared algebraic root policy; it does not prove
ground fitting, target scale selection, contact, or a correct pose mapping.

## Actual semantic and neutral-pose mismatch remains unresolved

43 accumulates source rotations through removed spine/neck/shoulder links and
uses `G_source_animated * inverse(G_source_rest) * G_target_rest`. Its authored
sources deliberately aligned geometric rest positions. Actual SOMA30 and target
bind positions do not have that property. For example:

| Named correspondence | Source rest relative to zero Hips (m) | Target bind world (m) |
|---|---|---|
| LeftHand / hand.L | `(0.723611, 0.429163, -0.012884)` | `(-0.570000, 0.940000, 0.010000)` |
| LeftLeg / thigh.L | `(0.100432, -0.084345, 0.025957)` | `(-0.125000, 0.860000, 0)` |

Source left limbs occupy +X and target `.L` limbs occupy −X. Source identity rest
offsets spread the arms horizontally; target bind arms angle downward. These
are exact source/asset observations. They do not choose an adopted reflection,
180-degree turn, side swap, fixture fix, or anatomical basis. In particular,
reversing X alone and rotating 180 degrees about Y also differ in forward-axis
behavior. Labels and quaternion norms cannot resolve that choice.

After the diagnostic root correction, blindly retaining the rest of 43's
rotation rule gives these maximum named endpoint differences on this clip:

| Endpoint | Difference (m) |
|---|---:|
| LeftHand / hand.L | 1.288952516 |
| RightHand / hand.R | 1.325937493 |
| LeftFoot / foot.L | 0.361757228 |
| RightFoot / foot.R | 0.357092260 |

These combine proportions, removed positional offsets, different neutral poses,
and unresolved semantic/basis choices. This study does not isolate their causes.
They are not upper bounds for a future corrected mapper. The prior 0.277119 m
authored-control result was not a bound on genuine output. Even a corrected
rotation-only method cannot preserve every moving offset of removed links.

## Signed axes: algebraic invariance is not semantic evidence

The probe checks all 48 signed permutation bases on actual frame index 47:
24 determinant +1 and 24 determinant −1 bases. Consistently transform positions
and offsets by `B` and rotations by `B*R*B^-1`. The largest FK difference from
`B*original_position` is `1.1444e-16` m. This is the expected coordinate-change
invariance. Even an improper basis conjugates a proper rotation to another proper
rotation. The invariant therefore cannot distinguish a global mirror, front,
left/right anatomy, or trained-data axis semantics. Claiming semantic acceptance
from that result is explicitly rejected by the controls.

Representation controls use all 90 actual frames:

| Control | Maximum source FK position change (m) |
|---|---:|
| Negate all four quaternion components | 0 |
| Conjugate XYZ signs | 1.386387009 |
| Misread XYZW as XYWZ | 1.145016661 |
| Localize already-parent-local channels again | 0.732777111 |

These controls expose convention errors. They do not identify the intended
semantic mapping or prove the requested action was performed correctly.

## Pinned source algebra: static evidence only

The read-only source study inspected kimodo.cpp revision
`5679ff19ba0a522c0b0516e9a9d402fe1af2c027`. These references preserve its exact
critical hashes without copying the provider source into this report:

| Pinned file and lines | SHA-256 | Static conclusion |
|---|---|---|
| `src/motion_decode.cpp:7–12` | `d9f0076d3254cd6d89719a0097c09aa265fea8ad3404bf303d527b90ce5714ff` | Row-major matrices acting on column vectors; 6D columns built with cross products; XYZW output; parent-local `transpose(parent_global)*joint_global`; absolute root `(f0+f5,f6,f2+f7)`. |
| `src/skeleton.hpp:45–67,91` | `6c1e1d98170a99105bd325c32caff5421bfb20d1e16160980a9f2c3258e244a3` | Exact SOMA30 graph and offsets; Hips offset zero; +X left offsets, +Y upright offsets, +Z toe offsets. |
| `src/sequence.cpp:23–32` | `1b099faabcfa7a9e179bbfb0a1adbe1d9976b8bd9fc83e1b56a6c118c4236808` | Static FK corroboration: root posed position is decoded root; child uses rotated parent-local offset. This continuation code was not invoked as an additional trial. |
| `src/model.cpp:94–109` | `366fb57a715536dd02182d1756022b656c99caec920e0f38be1f30280ae01d7a` | Sampled state passes to this decoder. |
| `src/generate.cpp:16–27` | `7c4a301666566b29aa042a00bfbdee7aeaa92bd40ed62c9585200c0c2be75b88` | Returned vectors are written directly as native floats. |
| `scripts/export_glb.py:20–21,102–115,148,197–206,227–229` | `574a5f1f20476268e33b0007aa2ec212eb5f28767895d810130cc7a639b0cabb` | 0.988 m is an exporter rest/bind height; the raw root channel replaces translation without adding that height. Exporter was read, not run. |

For nondegenerate 6D inputs the cross-product construction gives orthonormal,
determinant +1 rotation matrices. The quaternion conversion stores **XYZW**.
The decoder emits absolute parent-local rotations, not rotation deltas. Its root
positions are not velocity samples needing integration, and a second root
orientation/heading application is not part of the inspected decoder.

Six tiny Python algebra controls mirror the construction at ±90 degrees about
X/Y/Z, with zero measured matrix difference. They execute no C++ and no trained
model. The decoder's handling of degenerate 6D vectors is not validated by these
nondegenerate controls. Source algebra and exporter intent establish neither
trained-data axis semantics nor official NVIDIA decoder parity.

The source snapshot hashes were checked during the original private inspection.
Public reproduction consumes the pinned extracted skeleton and public raw data;
it does not require the private C++ checkout or claim to re-inspect absent source.
41's pinned source receipts retain corresponding source identities.

## Source trajectory observations only

With the declared conventional quaternion/FK interpretation:

| Source named joint | Y range (m) | XZ joint path length (m) |
|---|---:|---:|
| LeftHand | 0.838279–0.868489 | 0.312935 |
| RightHand | 0.841497–1.711810 | 1.970131 |
| LeftFoot | 0.065609–0.067996 | 0.021352 |
| RightFoot | 0.064447–0.067143 | 0.019817 |

The named RightHand rises higher in this calculation. This is not prompt-quality
acceptance or verified right-hand-wave playback. Foot-joint XZ travel is not
called foot slide: there are no contact labels, sole/floor geometry, or planted
foot ground truth. No visual motion quality judgment was made.

## Retention, verification, and next gate

`historical/` preserves the original private `probe.py`, `numeric-proof.json`,
and `PROOF-NOTES.md` byte-for-byte with their original absolute paths. They are
historical attribution, not runnable public entry points. The current public
probe replaces those dependencies with pinned public inputs, adds strict
mathematical/input/output checks, and retains the same calculations. All 17
shared fields match under the typed float-comparison policy below.
`historical/README.md` identifies the
original files and hashes. `SHA256SUMS.json` inventories this retained study.

The original `test_controls.py` required exact nested float equality. Review
reproduced a real portability failure: Python 3.9.6 ran the probe successfully
but controls failed at `historical numeric drift: all_signed_bases`. The original
script and failure stdout/stderr were preserved privately before correction.
No historical data was rebaselined. The fixed comparator requires exact dictionary
keys, list shapes, scalar types, integer counts, booleans, strings, and nulls.
Only finite float leaves use:

```text
abs(actual - historical) <= 1e-13 + 1e-13 * max(abs(actual), abs(historical))
```

NaN and infinity on either side are rejected. The tolerance accommodates runtime
arithmetic differences far below the probe's existing physical-error controls;
it does not relax the probe's root, quaternion, representation, or basis checks.
Python 3.9.6 differs in 80 of 257 compared float leaves, with maximum absolute
difference `9.992007221626409e-16`. Python 3.12.11 and 3.14.7 match those numeric
leaves exactly. Historical file hashes remain exact in every runtime. Comparison
metadata records each runtime's actual differences rather than claiming identical
result bytes.

`review-history/` retains the exact initial independent publication review and
the worker's before-fix red receipt with source attribution. That review covered
the earlier file inventory and found this one P2 portability issue; it separately
corroborated the root/endpoint calculations. It is not approval of this repaired
cohort. A final publication review remains open.

Actual `test_controls.py` preserves the original 15 rejection controls: eight corrupted input
hashes; the three wrong root policies above; semantic-axis acceptance from basis
invariance; missing improper bases; different existing output; and output symlink.
It adds 16 comparison rejections: a material change to the actual root data,
missing/extra keys, changed list length/type, changed integer values/types,
boolean/integer substitutions, changed identity/null values, and nonfinite floats
on either comparison side. A positive nested last-bit float case passes. All 31
rejection controls pass under each of the three tested runtimes. The controls also
verify historical file hashes, shared fields under the declared policy, unchanged
public inputs before/after, and owned temporary-resource removal. Positive math
checks remain required inside the unmodified public probe.

The next authorized work remains a bounded calibration investigation using this
one source and fixture: declare signed semantic correspondence and anatomical
neutral-pose frames with an explicit twist rule, then test geometric segment
directions as well as rotation matrices. Keep the pelvis-world root oracle and
the failing controls. Any later normalized schema, genuine evidence admission,
serialized export, or native/Web playback requires its own concrete gate.
This report adopts no new mapper or semantic side policy.

VERIFIED — Public-input stdlib probe and all 31 rejection controls exit 0 on
Python 3.9.6, 3.12.11, and 3.14.7; original private evidence hashes remain exact;
shared fields match the strict typed finite-float policy.
NOT-RUN — Normalized schema, genuine playable admission, exporter, Work,
native/Web playback, official decoder parity, anatomical calibration, prompt or
contact quality, arbitrary-rig retargeting, additional model inference.
