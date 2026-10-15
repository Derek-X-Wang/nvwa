# Experimental motion interchange v1

This is an isolated experiment, not a product schema. JSON uses UTF-8, rejects duplicate keys at every level, unknown fields, nonfinite numbers and trailing content. Limits: 4 MiB JSON, 32 MiB GLB, 151 frames, 5 seconds, 77 joints. No NPZ, BVH, matrix, Euler, left-handed or Z-up adapter is implemented.

```
{
 "schema_version": 1,
 "provenance_kind": "authored_control" | "generated",
 "provenance": {
   "source_id": "nonempty identifier",
   "raw_format": "nvwa.motion.portable.v1",
   "raw_sha256": "64 lowercase hex digits",
   "run_receipt_sha256": null | "64 lowercase hex digits",
   "provider": null | "nonempty identifier",
   "code_revision": null | "nonempty immutable revision",
   "model_sha256": null | "64 lowercase hex digits"
 },
 "skeleton": {
   "identity": "nvwa18" | "soma30" | "soma77",
   "joint_names": ["unique ordered names"],
   "parent_indices": [null, 0, "..."],
   "rest_local_translations_m": [[0,0,0]],
   "rest_local_rotations_xyzw": [[0,0,0,1]],
   "rest_local_scales_xyz": [[1,1,1]]
 },
 "convention": {
   "units": "meters", "handedness": "right", "up_axis": "Y",
   "rotation_order": "xyzw", "transform_space": "local",
   "root_motion_mode": "absolute_translation"
 },
 "sample_times_seconds": [0, 0.0333333333],
 "local_rotations_xyzw": [[[0,0,0,1]]],
 "root_translations_m": [[0,0,0]]
}
```

The illustrative arrays above are shortened. Actual dimensions must match identity count, frame count and joint count exactly. One root may appear at any joint index; every other parent is a valid distinct index, and following parents must reach that root without a cycle. Quaternion norm error must be <=1e-4. Times start at exactly zero, strictly increase after float32 conversion, and end in (0,5]. Rotations are absolute local transforms, not deltas. Root translation replaces that root's local translation once. Nonroot local translations remain the rest values. Rest scale is required, finite and strictly positive per axis. Export requires the exact frozen Nvwa base rig and verifies/preserves its rest scale and inverse binds. No arbitrary scale retargeting support is implied. SOMA identity/count validation is structural only; a canonical SOMA joint registry is not yet enforced, and no SOMA retarget/export is offered.

`raw_sha256` binds a separate immutable raw file passed to the boundary. The raw portable input has the exact same motion fields but no `provenance` object (to avoid a self hash); it retains `provenance_kind`. All motion fields, kind and source identity must equal the normalized envelope. Conversion is currently identity-only: meters, right-handed, Y-up, XYZW, local, absolute translation. Unknown layouts are errors. Generated input additionally requires separate raw run-receipt bytes matching the receipt hash and binding the successful run/raw hash/provider/code/model identity. A caller-created receipt still does not prove real inference: all synthetic tests are labelled synthetic and cannot establish generated acceptance. No generated artifact is admitted as genuine evidence in this experiment without independent real process/run evidence.

Publish is a new output directory only. Existing destinations, unrelated files and symlink input handles are rejected. Inputs are validated and all artifact bytes built before creating output. Failure removes only a directory created by that invocation; it never changes current Work. No path to current Work is accepted.

The narrow raw-F32 adapter accepts two separately bounded binary files plus a strict pinned sidecar: source_format=kimodo.cpp.f32.v1, code_revision, endianness=little, frame_count, joint_count, provenance_kind, skeleton, convention, and explicit sample_times_seconds. Exact file lengths are F*3*4 and F*J*4*4 bytes, respectively; row-major root positions and frame/joint/XYZW quaternion order. Coordinates must match the canonical convention exactly. Sidecar rest root height is independent of each sampled absolute root translation. Only structural conversion is demonstrated using authored byte controls. Actual provider coordinate compatibility and genuine generation remain NOT-RUN until separately observed. Adapter outputs portable raw/envelope and a receipt binding both binaries, sidecar and resulting portable bytes; generated data remains inadmissible to playable export until genuine execution evidence is reviewed.
