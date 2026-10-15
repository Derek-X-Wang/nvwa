# 43 — Authored rig-mapping A/B controls

**Adopt the calibrated rotation rule for these authored controls. Reject naive
local quaternion copy. Defer genuine SOMA-to-Nvwa calibration and positional/contact
retargeting.** Collapsed links preserve the requested global rotational motion;
they do not preserve the moving translations of the removed links. The calibrated
asymmetric control still differs from source hand/foot positions by **0.277119 m**.

This is an isolated CPU experiment. Every motion is `authored_control`. No model,
generated action, official rest calibration, renderer, importer, or Work ran here.
The numerical success measures a declared mapping, not whether this mapping gives
the desired artistic interpretation of a genuine provider output.

## Inputs and fixed scope

- Exact original target GLB: `assets/fixtures/nvwa-humanoid.glb`, SHA-256
  `f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6`.
  All 18 skin joints, actual parent links, local rest translations, XYZW rotations,
  and scales are read from that file. Its nonjoint parent is checked as identity.
- Frozen experimental contract SHA-256:
  `74bb268930428195242a99cffe6fd3307338be2dbd435583212607185a6bb257`.
  Script verifies the unchanged copy at `.work/m2-mapping-inputs/CONTRACT.md`.
- Official 30/77 **names and parents only** are extracted into `source-layouts.json`
  from pinned [NVIDIA definitions.py](https://raw.githubusercontent.com/nv-tlabs/kimodo/58e781898b3d7e328a676a75d3e338c45dce3ad9/kimodo/skeleton/definitions.py).
  Fetched source SHA-256:
  `fafe12b5f82ca24096241932d9773b1d3d8c080da1197e74c77cfce8ce3a19fc`.
- Source rest TRS is deliberately **authored**, with nonidentity, noncommuting
  coordinate bases. Corresponding body joint rest positions match the target.
  Additional links split body offsets asymmetrically. Extra 77 detail joints have
  explicit small authored offsets. Complete TRS for both layouts is retained in
  `mapping-manifest.json`; it is not official SOMA rest data.

The official [SkeletonBase source](https://raw.githubusercontent.com/nv-tlabs/kimodo/58e781898b3d7e328a676a75d3e338c45dce3ad9/kimodo/skeleton/base.py)
loads neutral joints and optional rest/standard-pose offsets from serialized
assets. Hierarchy text alone does not supply those values. No such assets were
loaded or executed here. Genuine provider handedness and rest interpretation stay
unverified. The authored controls explicitly choose meters, right-handed, Y-up.
The 30-to-77 controls share common body inputs; this does not test NVIDIA's
conversion or its relaxed-hand asset.

Experiments 04/40 established equal-topology coordinate-basis correction and
actual native playback of their existing derivatives. This experiment changes
topology and does not inherit their playback or geometry-equivalence result.
Experiment 39's earlier provider readiness report is historical; parent owns the
current provider build/report. No genuine output was supplied to this worker.

## Mapping and controls

Quaternion products compose rotations right-to-left. Inputs and outputs contain
absolute local XYZW rotations. For a mapped target joint `i` and source joint `s`:

```text
S_anim[s] = ordered product of source animated local rotations from root through s
S_rest[s] = ordered product of source rest local rotations from root through s
T_rest[i] = ordered product of target rest local rotations from root through i
D[i] = S_anim[s] * inverse(S_rest[s]) * T_rest[i]
target_local[i] = inverse(D[parent(i)]) * D[i]       # root uses D[i]
target_root = target_rest_root + (source_root - source_rest_root)
```

The last equation is an explicit rest-aligned displacement policy. Source Hips
rest height is approximately 0.83 m; target root rest height is approximately
0.08 m. Source sampled root positions are absolute, not deltas. The output root
translation is absolute and replaces the target root local translation once.
Pelvis stays approximately 0.75 m above that root under its rest local transform.
No hip-height scaling, ground fitting, or duplicated source root rotation is used.

| Target | Source | Removed source links above target joint |
| --- | --- | --- |
| root, pelvis | Hips | Extra target root receives Hips rotation; pelvis local stays rest |
| spine | Spine1 | None |
| chest | Chest | Spine2 |
| neck | Neck1 | None |
| head | Head | Neck2 |
| upper_arm.L / .R | LeftArm / RightArm | LeftShoulder / RightShoulder |
| forearm.L / .R | LeftForeArm / RightForeArm | None |
| hand.L / .R | LeftHand / RightHand | None |
| thigh.L / .R | LeftLeg / RightLeg | None |
| shin.L / .R | LeftShin / RightShin | None |
| foot.L / .R | LeftFoot / RightFoot | None |

Jaw, eyes, fingers, toe detail and end joints are not mapped. Animated omitted
spine, neck and shoulder links still contribute through the ordered source global
rotation. Their varying positional offsets have no channel in the fixed target
contract, whose nonroot local translations stay at rest.

Three 11-frame, one-second cases run for each source layout: neutral rest,
translation-only root trajectory, and asymmetric articulated motion plus that
trajectory. The last rotates hips, parent spine/chest, omitted spine/neck/shoulder
links, both arms and both legs with different angles. Each authored local motion
composes X then Z rotations; parent motion makes copying or reversing products
observable. Frame zero is rest, later frames exercise the noncommuting products.

A naive baseline copies each selected source local quaternion, keeping the extra
target pelvis at rest. The calibrated method uses the formula above. Four
negative controls swap left/right semantic maps, reverse animated/rest product
order, erase only the omitted links' animation, or conjugate XYZ signs. Negating
all four quaternion components is correctly treated as an equivalent rotation.

## Actual CPU results

`run-output.json` is actual successful stdout. `metrics.json` contains all 30
case/method measurements. A second complete invocation reproduced all 38 output
files byte-for-byte; `repro-check.json` records that check and unchanged input
hashes. The matrix oracle separately multiplies 3x3 source
rotations and derives target local matrices from desired global matrices. Its
full 4x4 target FK retains exact scales and translations. The tested mapper uses
quaternion chain multiplication; this catches quaternion order and parent errors.
The oracle verifies the declared orientation policy, not unknown artistic intent.

30 and 77 shared-body results are identical. Maximum values for asymmetric motion:

| Method | Target joint error vs declared oracle (m) | Global rotation error (degrees) |
| --- | ---: | ---: |
| Naive local copy | 1.46484170414 | 179.163681289 |
| Calibrated | 1.44895004482e-15 | 7.26410420194e-14 |
| Left/right swap | 0.786552985431 | 162.548137668 |
| Wrong animated/rest product order | 0.252962890678 | 63.6282807510 |
| Dropped collapsed-link animation | 0.658488063084 | 67.5037795023 |

Additional actual checks:

- Calibrated rest matches full target rest FK within `1e-12 m`; the matrix-oracle
  rest joint error is `8.98672237165e-16 m`. Naive already fails rest by 1.43914 m.
- Root output has zero error against its absolute replacement policy in every
  tested case. Actually adding target root rest a second time in FK causes
  `0.0799999982119 m` error. Both methods preserve the root trajectory when used
  under the declared replacement policy, even though naive joint rotations fail.
- `q` versus `-q` has zero position error. Wrong XYZ sign changes pose by
  `1.16568485935 m`. Shared 30/77 calibrated target poses have zero difference.
- JSON target outputs are reloaded and compared with the exact target skeleton.
  Simulated float32 channel rounding causes at most `3.94640004964e-08 m` joint
  error across both A/B methods. This is numeric float32 evidence, not GLB export.

All exact target local scales are retained in outputs and affine FK. Maximum
scale deviation from one is `2.26497650146e-06`. Dropping scales in a separate
diagnostic changes tested target joint positions by at most approximately
`3.34902069868e-08 m` across the measured methods. The adopted output does **not**
drop them. This small error is specific to these joint positions and controls;
it is not a bound on arbitrary motion or skinned vertex error. Inverse binds and
mesh geometry are untouched and are the import/export worker's responsibility.
Source scales are explicitly unit in these authored controls. Arbitrary nonunit
source scale, shear, or changed target rest/binds is unsupported.

## Positional failure and the foot metric

The calibrated asymmetric source hand/foot comparison still reaches
`0.277118877976 m`. Rest and translation-only correspondence are near machine
precision. The failure appears when rotated removed offsets and different
parent bases give endpoint positions that the target's fixed translations cannot
match. Rotation-only chain collapse is therefore rejected as a general
position-preserving retargeter. No IK or contact correction is implemented.

`horizontal_foot_joint_travel_m_no_contact_labels` sums XZ foot-joint displacement
between frames. It is deliberately **not called foot slide**: there is no contact
label, floor, sole geometry, or planted-foot ground truth. In the calibrated
translation-only control, both feet travel `0.427257701186 m`, exactly the root's
horizontal sampled path length. In the articulated control, left and right travel
`0.560780050502 m` and `0.351813254946 m`. Neither number establishes contact
quality; a large value can be correct locomotion, and a small value can be wrong.

## Reproduction and importer handoff

From the repository root, Python 3.9+ with standard library only, no installs:

```sh
python3 -B experiments/43-rig-mapping/spike.py --out .work/m2-mapping/repro-new
```

Output must be a new directory; choose another new name for another run. The
actual retained worker run used `.work/m2-mapping/final`. The unchanged frozen
contract copy must be present. This experiment never writes current Work.
Read `mapping-manifest.json` for file SHA-256 values, exact source/target rest TRS,
mapping, fixture and contract pins. The script hash binds the implementation.
Large portable arrays stay in private `.work` and regenerate from the command.

For the importer, pass the pair below as independent immutable inputs using its
existing portable route:

```text
30-asymmetric-calibrated.raw.json
30-asymmetric-calibrated.normalized.json
```

Repeat with `30-asymmetric-naive` for A, and `77-*` for the equivalent body-layout
control. Prefixes `30-rest-*` and `30-trajectory-*` provide the other checks.
Each target envelope has `identity=nvwa18`, `provenance_kind=authored_control`, and
raw SHA-256 bound to the separately emitted raw file; provider/model/receipt fields
are null. Six source pairs have `identity=soma30/soma77` for inspection and are
not target export requests. The script emits 12 target raw/envelope pairs and six
source pairs (36 portable JSON files). No absolute cross-worktree dependency
exists. The importer owns GLB serialization, preserved inverse binds, profile and
Work construction; the parent owns actual desktop/Web playback.

## Decision and remaining limits

Adopt rest calibration, hierarchy-ordered rotation collapse, exact target rest
scale retention, and the explicit root displacement rule **for the declared
authored controls only**. Reject naive copy and any claim that this rotation-only
method preserves source endpoint positions. Defer genuine provider mapping until
actual source output, verified coordinate convention, and authorized official
rest calibration are available. Defer arbitrary rigs, proportions, joint limits,
skin deformation, foot contacts, toe motion, IK and artistic quality judgments.

VERIFIED — Standard-library script exited 0; both layouts, three authored cases,
independent matrix/FK checks, four failing controls, sign equivalence, root-once,
exact scales and JSON/float32 checks. NOT-RUN — Genuine inference, importer/GLB,
Work, native/Web playback, contact quality and arbitrary-rig retargeting.
