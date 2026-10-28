# Nvwa B1 adapter

This production-owned crate preserves the admitted authored pose, canonical frame gauge and CPU deformation bridge over the vendored Humentity ECS skeleton and mesh. `PROVENANCE.json` binds the original and promoted library identities. It contains no reference output or baked character frames.

Call `apply_pose_canonical`, run actual Bevy transform propagation, then call `skin_mesh_frame_full_weights` with the actual mesh-to-source vertex map. Apply the returned `model_to_world` once when uploading a CPU-deformed display mesh and remove skinning/morph components from that display mesh. The CPU policy aggregates signed helper contributions per bone, retains positive final aggregates without a four-influence cap, and normalizes the retained row. It is not raw signed full-influence transfer. The separate legacy four-slot API remains available for diagnostics and has no product quality admission.

Motion callers use `PreparedRig::new` for each fitted shape, then `apply`, actual Bevy transform propagation and `frames`. Preparation verifies the full53-bone unit-scale B1 source construction and exact original inverse binds. It retains the original f32 rest and gauge operands. Each completed f32 moved rotation receives one final f64 normalization and one cast to f32 before the actual ECS write. Neutral copies a separately cached, once-corrected rest rotation. Corrected outputs never feed composition or refitting: this handoff is not bitwise idempotent. All output rows and destinations validate before any local Transform write. Translations, unit internal scale, inverse binds, propagation, readback and skin arithmetic retain their existing ownership.

This handoff is a numerical representation policy, not numerical or motion-quality admission. Saved scalar predictions cannot replace actual native and Web checks. Any original numerical gate failure stops the candidate; historical failures and quality HOLD remain intact. See [the motion contract](../../docs/implementation/b1-motion-contract.md).

`poses::diagnostic_pose(id)` returns one of the exact approved authored `neutral`, `shoulder`, `elbow`, `knee` and `combined` poses. Unknown IDs return errors. `poses::DIAGNOSTIC_POSES_JSON` is the unchanged authored input encoding. These are static diagnostics, not continuous motion or generated animation.

Matrices are column-major. Vertex arrays are MakeHuman Y-up metres with the skeleton display-root transform removed. The crate does not load a Work, locate assets, choose a fallback backend or define product persistence. The existing product layers own those policies.

Humentity is separately offered under MIT or Apache-2.0; its original and complete supplemental license texts are under `vendor/humentity`. The authored Nvwa bridge retains the repository's existing first-party license status, which is not yet specified for public redistribution.
