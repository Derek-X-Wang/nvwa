# 04 — Rest-basis retargeting on the real humanoid

## Outcome

**Adopt rest-basis correction for this controlled case. Reject direct copying of
local rotation channels across changed joint bases.** This proves the coordinate
basis issue on the actual Nvwa skeleton and wave clip. It does not prove a general
retargeter for different anatomy, topology, proportions, or semantic joint maps.

No AI target or AI motion was used. Both target GLBs are **controlled derivatives**
of the original humanoid. Runtime and main source remain unchanged.

## Question and hypothesis

Question: When the source and target describe the same skinned humanoid in different
joint coordinate bases, does direct copying of animation rotations preserve motion?

Hypothesis: Direct copy causes large target errors. Mapping rotations through the
parent and child coordinate bases restores the original motion while preserving the
rest skinned geometry.

## Control and method

Read the actual exported `assets/fixtures/nvwa-humanoid.glb`: 18 skin joints,
24,736 evaluated skinned vertices, and the named `wave` animation. Resolve `wave`
by name (the current GLB order is idle, turn, wave). Use the original animation
samplers, joint hierarchy, skin weights, inverse-bind matrices, and meshes.
No toy mesh or external replacement rig is involved.

The controlled target rotates the local coordinate frames of chest by +90 degrees
about Y, right upper arm by +90 degrees about Z, right forearm by +90 degrees
about X, and right hand by +90 degrees about Y. These are signed-axis permutations,
so the actual small nonuniform scale terms can also be converted exactly without
introducing shear. This bounded implementation rejects unsupported animation forms.

Let `C_i` rotate joint i's new coordinate basis, `L_i` be its original local
transform, and `G_i` its original global transform. The equivalent target has:

```text
L_target_i = inverse(C_parent) * L_source_i * C_i
G_target_i = G_source_i * C_i
IBM_target_i = inverse(C_i) * IBM_source_i
G_target_i * IBM_target_i = G_source_i * IBM_source_i
```

The last identity preserves the rest skinned geometry. Child translations and scale
axis order, node rest rotations, and inverse-bind matrices are consistently changed.

A (naive): Copy each original local animation rotation unchanged into that target.
B (corrected): Map each animated quaternion with
`q_target = inverse(q_C_parent) * q_source * q_C_i`.
Both variants use identical converted translations/scales and inverse-bind matrices;
only the handling of animation rotations differs.

Export both actual target GLBs, reload their float32 accessors, sample the original
wave at 19 times from 0 to 3 seconds, and compare to the original target positions.
Six sample times lie between exported keyframes. Use linear translation/scale
interpolation and shortest-path quaternion spherical interpolation, matching the
source's LINEAR channels. Compare right-hand joint position, all 18 joint positions,
and all 24,736 skinned vertex positions in world space. Base morph weights are used.

## Acceptance and exits

Accept correction if maximum corrected hand, joint, and vertex error is below
`1e-5 m`, the rest and identity controls are below `1e-5 m`, and the naive control
has at least `0.05 m` hand error. Explicitly reject zero/nonfinite quaternions and
singular scales. Also corrupt a real rig joint quaternion and confirm an error.

Exit inconclusive if source decoding, required joint names, or the named wave is
unavailable. Exit reject on failed numeric thresholds. Abort explicitly for sparse
accessors, matrix nodes, unsupported channels/interpolation, nonfinite values,
degenerate/non-increasing sample times, cyclic hierarchy, multiple node parents,
external buffers, invalid indices, or out-of-bounds accessors. Do not install tools,
run GPU tasks, change root dependencies, or expand into IK/framework work.

## Actual evidence

Commands executed from the repository root (Python CPU only, no installs):

```sh
python3 experiments/04-retarget-basis/spike.py > experiments/04-retarget-basis/run-output.json
```

The final run exited 0, including identity, changed-basis acceptance thresholds,
unchanged source-byte assertion, and four explicit degenerate-input checks. It used
local numpy version 2.0.2. `run-output.json` is the exact stdout; `metrics.json`
contains the same measurements. The two exported GLBs were reloaded before measuring.

| Measurement | Maximum error (m) |
|---|---:|
| Naive right-hand target | 0.800824139986 |
| Corrected right-hand target | 2.16774327513e-08 |
| Naive all-joint target | 0.800824139986 |
| Corrected all-joint target | 2.16774327513e-08 |
| Naive skinned vertices | 0.868395833353 |
| Corrected skinned vertices | 3.08111128912e-08 |
| Rest geometry control | 1.39111871227e-15 |
| Identity mapping control | 1.51404659356e-08 |

Per-sample raw errors (full precision remains in the JSON artifacts):

| Time (s) | Naive hand (m) | Corrected hand (m) | Naive max joint (m) | Corrected max joint (m) | Naive max vertex (m) | Corrected max vertex (m) |
|---:|---:|---:|---:|---:|---:|---:|
| 0.000 | 0.786683664 | 2.16774328e-08 | 0.786683664 | 2.16774328e-08 | 0.856463785 | 3.08111129e-08 |
| 0.123 | 0.80082414 | 5.64991025e-09 | 0.80082414 | 1.81816526e-08 | 0.868395833 | 2.49785366e-08 |
| 0.250 | 0.797029364 | 1.00948104e-08 | 0.797029364 | 1.81816526e-08 | 0.863502076 | 2.49785366e-08 |
| 0.500 | 0.701818853 | 1.19497705e-08 | 0.701818853 | 1.81816526e-08 | 0.765718532 | 2.49785366e-08 |
| 0.567 | 0.663034788 | 2.75825262e-09 | 0.663034788 | 1.81816515e-08 | 0.718267128 | 2.49785354e-08 |
| 0.750 | 0.606945686 | 7.47451619e-09 | 0.606945686 | 1.81816526e-08 | 0.657915501 | 2.49785366e-08 |
| 1.000 | 0.606945686 | 7.47451619e-09 | 0.606945686 | 1.81816526e-08 | 0.669247877 | 2.49785366e-08 |
| 1.111 | 0.606945686 | 7.47451633e-09 | 0.606945686 | 1.81816514e-08 | 0.654028434 | 2.49785352e-08 |
| 1.250 | 0.606945686 | 7.47451619e-09 | 0.606945686 | 1.81816526e-08 | 0.657915501 | 2.49785366e-08 |
| 1.500 | 0.606945686 | 7.47451619e-09 | 0.606945686 | 1.81816526e-08 | 0.669247877 | 2.49785366e-08 |
| 1.750 | 0.606945686 | 7.47451619e-09 | 0.606945686 | 1.81816526e-08 | 0.657915501 | 2.49785366e-08 |
| 1.789 | 0.60694569 | 7.47451619e-09 | 0.60694569 | 1.81816526e-08 | 0.663315367 | 2.49785366e-08 |
| 2.000 | 0.606945686 | 7.47451619e-09 | 0.606945686 | 1.81816526e-08 | 0.669247877 | 2.49785366e-08 |
| 2.250 | 0.606945686 | 7.47451619e-09 | 0.606945686 | 1.81816526e-08 | 0.657915501 | 2.49785366e-08 |
| 2.345 | 0.606945687 | 7.47451585e-09 | 0.606945687 | 1.81816514e-08 | 0.670759238 | 2.49785352e-08 |
| 2.500 | 0.65426249 | 1.74851753e-09 | 0.65426249 | 1.81816526e-08 | 0.718073126 | 2.49785366e-08 |
| 2.750 | 0.777577849 | 4.30887533e-09 | 0.777577849 | 1.81816526e-08 | 0.839819736 | 2.49785366e-08 |
| 2.987 | 0.797601616 | 3.09330724e-09 | 0.797601616 | 1.81816514e-08 | 0.868258008 | 2.49785352e-08 |
| 3.000 | 0.795528091 | 3.31471948e-09 | 0.795528091 | 1.81816526e-08 | 0.865993521 | 2.49785366e-08 |

Degenerate-input regressions returned explicit `InputError` messages:

- `zero_quaternion`: `invalid/degenerate quaternion`.
- `nonfinite_quaternion`: `invalid/degenerate quaternion`.
- `singular_scale`: `invalid/degenerate transform`.
- `actual_rig_zero_joint_quaternion`: `invalid/degenerate quaternion`.

## Provenance and artifacts

Original source SHA-256:

```text
f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6
```

`target-naive.glb` SHA-256:

```text
3b0cb7255c2ac5586b9925860956a126882dd789717ea3e19f278c3a2f39c2f3
```

`target-corrected.glb` SHA-256:

```text
425d1628dd3805fb37bbe1b2bbc8ba3cfcab2dd6ae610a59c652a7445c0a7d56
```

- `spike.py`: executable standalone Python experiment, all numeric regression checks.
- `metrics.json` and `run-output.json`: actual sampled numeric evidence.
- `target-naive.glb`: controlled derivative with deliberately naive copied rotations.
- `target-corrected.glb`: equivalent derivative with converted animation channels.
- `SOURCE-LICENSE.txt`: unchanged original fixture license; the derivatives retain
  its CC0 fixture provenance. GLB extras record source hash and derivative status.

## Limits and next decision

The numerical result is decisive for coordinate-equivalent rigs. It measures the
actual source animation and exported target data, but no target was visually played
in a renderer in this experiment. This is math/serialization evidence, not GPU,
viewer, Bevy, animation-player, lighting, or visual-quality validation.

The rig has identical bone lengths, topology, joint identities, and original
animation semantics. It does not cover differing limb proportions, missing joints,
rest-pose differences that cannot be expressed as basis changes, arbitrary shear,
root-motion policy, contact preservation, joint constraints, or IK. Signed-axis
basis changes were chosen so glTF TRS representation remains exact with the source's
small nonuniform scale terms. A broader change can require matrix/shear handling.

Adopt the narrow basis-conversion rule if a later retargeting feature transfers
motion between compatible named rigs. Keep these derivative assets and experiment
outside runtime. A future unrelated target rig requires a separate experiment and
semantic/proportion decisions before claiming general retargeting support.

VERIFIED — Script exited 0; 19 actual-wave samples, 18 joints, 24,736 vertices,
identity/rest controls and degenerate checks passed. NOT-RUN — Visual playback.
