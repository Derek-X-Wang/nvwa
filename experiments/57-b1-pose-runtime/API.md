# Portable pose and CPU deformation API

This document describes the existing `b1-pose-adapter` library behavior. It
clarifies the weight policy without changing the source or executable.
The measured route ID remains `b1-full-weight-cpu`; that name does not mean
unchanged signed source transfer.

## Exact influence policy

`full_proxy_influences(&World, &MhcloAsset, &[u16])` reads original source
`RigWeights`, in the actual full reference-rig bone order, and the source-ID
Mhclo helper map. For each bone and proxy vertex it sums positive helper-bone
weights multiplied by the **signed** Mhclo interpolation coefficients. The
existing source loader normalizes those coefficients by their sum and retains
negative coefficients.

After summing all signed contributions for that bone, the bridge retains the
aggregate only if it is **strictly greater than zero**. It applies no
four-influence cap. It does not clamp individual negative terms before summing.
The returned `(bone_index, weight)` rows and `SkinFrame.full_joint_influences`
therefore contain **positive-filtered, pre-normalization aggregates**, not all
raw signed transfer results. Their sums can exceed one after negative aggregates
are omitted. `skin_mesh_frame_full_weights(...)` divides each retained weight
by the retained positive row sum when computing linear blend skinning. A
nonpositive or nonfinite row sum returns an error.

The source GPU4 path differs: it aggregates the signed terms, selects four
aggregates without a final positive-only filter, zero-pads unused slots in this
experiment, then normalizes the selected row. This can preserve negative joint
weights. The full CPU frame retains those four-slot attributes for inspection;
the full CPU deformation uses `full_joint_influences` instead.

MPFB's garment interpolation differs again: it retains interpolated weights
only when they are **strictly greater than 0.001**. This bridge retains every
positive aggregate, including smaller values. The CPU route is thus a bounded,
source-derived positive-influence bridge; it is not an unmodified source full
weighting algorithm or an exact copy of MPFB's filtering policy.

## Measured garment context

Five negative pre-selection aggregates occur at source IDs 486, 685 and 792.
IDs 486/792 produce the two negative legacy render rows, 522 and 422 respectively.
ID 685's negative entries fall outside the selected four. These stored legacy
arrays remain unchanged; the full CPU renderer does not use them for deformation.

The normalized garment L1 difference from MPFB reaches 0.0034210871 at source 198.
The bridge retains normalized pelvis 0.0007222896 and upperarm_l 0.0009882539;
MPFB omits both. The remaining weights are consequently normalized differently.
Normalized body weights match the measured reference exactly. No reference
weight data is used to compute candidate deformation.

## Calling contract

Use `apply_pose_canonical(&mut World, character, &DiagnosticPose)`, then run
actual Bevy transform propagation. Call
`skin_mesh_frame_full_weights(&World, character, &Mesh, &MhcloAsset, &[u16])`
with the actual mesh-to-source vertex map. The result preserves raw candidate
bone frames and inverse bind matrices, source-derived canonical frame gauges,
rest/posed vertex arrays, normals, tangents and the positive-filtered influence
rows described above.

Matrices are column-major. Vertex arrays use MakeHuman Y-up metres with the
skeleton display-root transform removed. Apply `model_to_world` once when
uploading a CPU-deformed display mesh. Remove skinning and morph components to
avoid applying deformation again. The original four-slot API stays separate
and its measured body-quality gate remains HOLD.

## Evidence and preserved descriptions

[policy-clarification.json](evidence/policy-clarification.json) gives source
SHA256 identities, line ranges and read-only observations. The preserved API
source comments in `evidence/full40-adapter-source/src/lib.rs` (“Every raw
influence is retained”) and earlier raw/full-transfer receipt descriptions are
overly broad. This document supplies the qualifier. The live API comment was
subsequently corrected in one line, without an algorithm change; historical
source snapshots and capture bytes remain unchanged. The existing numeric PASS remains valid for the exact
positive-filtered policy measured. It does not upgrade GPU4 quality or establish
product admission.
