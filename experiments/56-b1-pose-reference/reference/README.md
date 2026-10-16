# Actual MPFB pose reference

The original `pose_reference.py` evaluates the approved MPFB 2.0.18 addon in
Blender 5.2.2 background/offline mode. It creates and refits the real `game_engine`
rig and real sportsuit with MPFB-interpolated weights. It applies the frozen
diagnostic quaternions to Blender pose bones and captures CPU depsgraph output.
No expected geometry or matrices are used to generate the result.

## Frozen measurement conventions

These declarations precede the full 40-case run. OBJ to Blender metres is
`(x,y,z) -> (.1*x,-.1*z,.1*y)`, as independently verified in experiment 53.
The eight body recipes and five authored poses remain unchanged. Matrices are
row-major arrays multiplying column vectors, in Blender Z-up metres. Rest
matrices are armature-local `Bone.matrix_local`; posed matrices are
armature-local `PoseBone.matrix`; `matrix_basis` is the bone-local rest-frame
postrotation. For ordinary inherited bones the recurrence is
`pose(parent) * inverse(rest(parent)) * rest(bone) * basis(bone)`.
The per-bone deformation is `pose(bone) * inverse(rest(bone))`.
Mesh-local positions first enter the rig space through
`inverse(rig_world) * mesh_world`, and return through its inverse.

The original, untruncated, unnormalized vertex-group deform weights are
recorded as per-source-vertex `[[bone_index, weight], ...]`, with actual Blender
bone ordering. Vertices without deform weights remain in the capture. The
full body source cage, including helpers, is captured before active clothing
MASK modifiers; those modifiers are restored. Equality of every source polygon
and loop vertex index is checked to establish source-order correspondence.
Normals are actual evaluated vertex normals. Tangents are actual evaluated
Blender UV corner tangent xyz plus bitangent sign. World normals require the
inverse-transpose linear transform and normalization; tangents require the
linear transform and normalization, with handedness adjusted for determinant.
No normal or tangent appearance threshold is implied by finite values.

Predeclared downstream gates from the shared contract: rigid matrix component
`1e-4`, joint-head metres `1e-5`, candidate CPU vs independent candidate-weight
skinning metres `1e-5`, full MPFB body maximum component metres `1e-3`, full MPFB
garment maximum component metres `3e-3`, over all source IDs. RMS and coverage
must also be reported. The reference checks local basis recurrence at `1e-5`
and reproduces experiment 53's unposed body/garment at `1e-5` metres. Full-weight
normalized LBS vs actual Blender output is diagnostic only: actual modifier
flags remain unchanged and any mismatch stays visible.

## Reproduce

Run from the research checkout, using a new output directory. No download,
preferences save, render, or graphics context is needed. The setup is private
to this task and the original addon remains read-only.

```sh
python3 experiments/56-b1-pose-reference/reference/prepare_resources.py
BLENDER_USER_RESOURCES="$PWD/.work/b1-pose-reference/blender-user" \
  /opt/homebrew/bin/blender --background --factory-startup --offline-mode \
  --python-exit-code 7 \
  --python experiments/56-b1-pose-reference/reference/pose_reference.py -- \
  --sample "$PWD/.work/character-approved-20261016" \
  --out "$PWD/.work/b1-pose-reference/run1"
```

`--recipes neutral` runs the five-pose convention probe only. Large case arrays
remain ignored in `.work/b1-pose-reference/`; tracked compact summaries freeze
their SHA256 identities. Candidate runtime output must be computed from the
approved original inputs and compared with these outputs afterward.

After a full run, freeze into a new compact output directory:

```sh
python3 experiments/56-b1-pose-reference/reference/freeze_reference.py \
  --run .work/b1-pose-reference/run1 \
  --out experiments/56-b1-pose-reference/reference/frozen-reproduction
```

## Executed result

`frozen/manifest.json` binds all 40 executed case hashes, original source
identities, command arguments, and pose/driver hashes. `frozen/summary.json`
records aggregate verification. The retained `.work/b1-pose-reference/run1`
contains the large actual case arrays and original summary; `run1.log` contains
Blender's original log. A separate five-case `probe1` and log retain the prior
local-axis check. Both Blender commands exited zero; full evaluation took
45.93 seconds, below the five-minute wefty threshold. No render ran.

All 19,158 body vertices, 1,797 garment vertices, 53 bones, 73,944 body UV corner
tangents and 6,872 garment UV corner tangents are present per case. Every source
vertex has deform weights. Body weights retain up to seven influences, garment
weights up to six. Their original weight sums differ from one by up to
`0.0001000207` and `0.002174832`, respectively. Export never truncates or
normalizes them. The separate LBS diagnostic normalizes the full sum, matching
Blender's actual ordinary armature blending. Both real armature modifiers have
`use_deform_preserve_volume=false`, no bone envelopes, and no modifier mask.

Original experiment 53 body and fitted garment rest positions reproduce
exactly for every recipe. Maximum matrix recurrence error is `1.78814e-7`.
Full-weight diagnostic LBS differs from actual Blender evaluation by at most
`2.14408e-7` metres body and `1.48818e-7` metres garment. Every captured normal
and tangent is finite and nonzero; maximum unit-length errors are `1.26942e-7`
and `1.57910e-7`. The manifest includes all per-case displacement/hash checks.

The lower-arm local Z axis is oblique in rig rest space, approximately
`(-0.5465,-0.6962,0.4655)`. This is the frozen authored elbow diagnostic and
does not establish anatomical motion quality. Upper-arm local Z is approximately
`(0.0667,-0.9967,0.0473)`; calf local X is `(0.9854,-0.0700,0.1553)`.
The source rolls, frozen poses, weights, and modifier policies remain unchanged.

**VERIFIED — 40 actual MPFB pose references, full source IDs and deform weights,
rig matrices, fitted/skinned garment, finite normals and UV corner tangents.**
Candidate comparison, GPU rendering and normal/tangent appearance acceptance
are NOT-RUN by this reference worker and retain their separate downstream gates.
