# Independent serialized-scene evaluator

This directory evaluates the retained experiment48 GLB independently of Bevy.
It reads serialized animation keys, static TRS, hierarchy, mesh vertices,
weights, ordered skin joints, and inverse bind matrices. No exporter or
experiment48 checker code is imported. The previous independent checker was
read as evidence of its raw44-to-serialized boundary. This evaluator starts at
the serialized-byte boundary; it does not repeat or claim official decoder,
retargeting, anatomical, or semantic validation.

Inputs are pinned to GLB SHA256
`c343f6cf47dc0a7c0b09f13ad7d21cf2706a08fb1cfdaca233f14edab02e44fc`
and Work SHA256
`7668eb7a2a2f87070500cbf49fa27d6794aa1fb83f5392b75a0ff51667cde779`.
Experiments41–48 are read only. Python standard library only. No inference,
downloads, Rust compilation, graphics launch, or model-cache access is used.

## Reproduce

Run from the repository root:

```sh
python3 experiments/49-runtime-pose-parity/offline/run_controls.py
python3 -O experiments/49-runtime-pose-parity/offline/run_controls.py
python3 experiments/49-runtime-pose-parity/offline/evaluator.py --all-keys --output experiments/49-runtime-pose-parity/offline/expected-90.json
python3 experiments/49-runtime-pose-parity/offline/surface.py --output experiments/49-runtime-pose-parity/offline/surface-crossings.json
python3 experiments/49-runtime-pose-parity/offline/compare.py /absolute/path/to/actual-native-or-web.json --output experiments/49-runtime-pose-parity/offline/actual-comparison.json
```

Controls and expectation generation take seconds. Surface analysis has an
explicit 45-second wall budget and fails if exceeded. It checks the fixed
seven keys only. All90 keys are supported for offline expected transforms.
The last key is binary32 `89/30 = 2.9666666984558105`, not3 seconds.

`controls-*.json` contain synthetic comparator controls, never a runtime
capture. No successful native/Web result is implied by a control passing.
`compare.py` follows frozen `probe/SCHEMA.md` v1 and requires all seven keys,
complete actual Work, clip/time bits, propagated hierarchy, and all nine skin
primitive bindings. Missing, failed, partial, nonfinite, wrong-clip, and
wrong-time captures fail. It returns nonzero on failure.

## Expected space and thresholds

`expected-90.json` contains24 GLB nodes at each key in serialized scene space.
Matrices are exported column-major. Internal evaluation uses 64-bit Python
arithmetic on exact decoded glTF binary32 values. Quaternions are not
renormalized. Comparisons take the smaller component error of `q` and `-q`.
No pose alignment, coordinate change, unit fitting, or root removal is used.

Runtime CharacterRoot is independently expected to be identity: the retained
Work has scale1 and production `CharacterRoot` starts at `Transform::default()`;
`apply_recipe` only sets its scale. The comparator verifies local and global
host identity before evaluating GLB globals. It never adopts the observed
root to make expected values match. Every GLB ancestor and static mesh node
is included. Identity scene/primitive helpers and their propagation are
checked explicitly. A changed host policy needs a new declared expectation,
not silent normalization.

Frozen before actual captures:

| Measurement | Maximum absolute component error |
| --- | ---: |
| local translation | `2e-6` metres |
| local quaternion, sign equivalent | `2e-6` |
| local scale | `2e-6` |
| full global matrix, translation and basis | `2e-5` |
| inverse bind matrix | `2e-6` |
| CPU reconstructed skinned vertex | `3e-5` metres |

These cover float operation order and hierarchy accumulation. No threshold
is selected from runtime residuals. Passing results report observed maxima.
Work equality is typed and exact except declared `nvwa-core` f32 leaves,
which compare binary32 bits. Those leaves are profile parameter min/max/default,
profile clip duration, character parameter values/scale, and timeline
start/duration/speed. Bool/int/string types and complete key sets stay exact.

CPU deformation comparison uses serialized GLB positions/weights and the
actual captured ordered joint entities, global matrices, and inverse binds.
Mesh and skin asset handles must resolve to exact GLB primitive/skin indices.
All nine actual skin-component entity IDs must be distinct and cover every
expected primitive binding. A mesh asset handle cannot relabel a different
primitive, and the fixture's shared skin must use one inverse-bind asset handle.
This verifies a CPU reconstruction of the captured bindings and transforms.
GPU vertex-output readback and loaded vertex-buffer inspection are NOT-RUN.
Handle resolution and component enumeration rely on the actual collector;
the adapter cannot authenticate fabricated entity/handle strings independently.

`skin-instance-alias-before-fix.json` retains a synthetic pre-fix vulnerability
reproduction: four primitive entities were removed and five skin records were
aliased to the remaining entity. The old comparator incorrectly returned PASS
with173152 reconstructed vertices. Current controls require that mutation to
fail for duplicated actual skin-component identity. This is comparator evidence,
not a runtime capture.

## Bounded surface evidence

`surface-crossings.json` uses mesh node22's actual positions, triangle indices,
skin weights and inverse binds after CPU linear-blend skinning at each key.
Each retained triangle must have at least0.8 summed weight at **each vertex**
in one of the explicit node sets:

| Partition | GLB joint node indices | Triangles |
| --- | --- | ---: |
| left arm weighted | `4,3,2` |3958 |
| right arm weighted | `7,6,5` |3958 |
| torso weighted | `16,9,8` |8436 |

The metric counts triangle **pairs** with a strict noncoplanar surface crossing.
One triangle edge must intersect the other triangle's strict interior at an
interior edge parameter. Epsilon is `1e-8` for edge/barycentric parameters;
the absolute determinant must exceed`1e-14`. Transition triangles, coplanar
contact, boundary contact, and enclosed-volume tests are excluded. Counts
are not unique intersection points or penetration depth. Winding changes
do not change the criterion. Synthetic known-geometry controls cover strict
crossing, winding, separation, coplanarity and boundary contact.

| Key | Left vs torso pairs | Right vs torso pairs |
| --- | ---: | ---: |
|0 |193 |204 |
|15 |0 |295 |
|30 |0 |349 |
|45 |0 |356 |
|60 |0 |353 |
|75 |215 |201 |
|89 |261 |193 |

The serialized expected skin already has crossings under this criterion.
Joint names select partitions only; they do not establish anatomical quality.
Zero counts cannot prove absence of intersection. Neutral/original-pose
surface crossings were NOT-RUN. A rest-pose inverse-bind reconstruction
control checks numeric skin conventions only, not neutral surface crossings.
These measurements do not assign cause among source motion, transfer,
fixture geometry, or weights. Runtime agreement alone does not improve motion.

## Current boundary

Offline transforms, skin conventions, and synthetic negative controls are
verified. Actual native/Web comparison results are separate artifacts only
after real capture JSON is supplied. Empty future captures cannot pass.
