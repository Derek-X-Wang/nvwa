# Nvwa B1 adapter

This production-owned crate preserves the admitted authored pose, canonical frame gauge and CPU deformation bridge over the vendored Humentity ECS skeleton and mesh. `PROVENANCE.json` binds the original and promoted library identities. It contains no reference output or baked character frames.

Call `apply_pose_canonical`, run actual Bevy transform propagation, then call `skin_mesh_frame_full_weights` with the actual mesh-to-source vertex map. Apply the returned `model_to_world` once when uploading a CPU-deformed display mesh and remove skinning/morph components from that display mesh. The CPU policy aggregates signed helper contributions per bone, retains positive final aggregates without a four-influence cap, and normalizes the retained row. It is not raw signed full-influence transfer. The separate legacy four-slot API remains available for diagnostics and has no product quality admission.

`poses::diagnostic_pose(id)` returns one of the exact approved authored `neutral`, `shoulder`, `elbow`, `knee` and `combined` poses. Unknown IDs return errors. `poses::DIAGNOSTIC_POSES_JSON` is the unchanged authored input encoding. These are static diagnostics, not continuous motion or generated animation.

Matrices are column-major. Vertex arrays are MakeHuman Y-up metres with the skeleton display-root transform removed. The crate does not load a Work, locate assets, choose a fallback backend or define product persistence. The existing product layers own those policies.

Humentity is separately offered under MIT or Apache-2.0; its original and complete supplemental license texts are under `vendor/humentity`. The authored Nvwa bridge retains the repository's existing first-party license status, which is not yet specified for public redistribution.
