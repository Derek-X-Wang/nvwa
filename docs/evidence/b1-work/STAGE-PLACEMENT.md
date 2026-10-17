# B1 placement on the existing rehearsal stage

The first actual production Web build loaded both meshes and the full 53-bone rig, but its lower body was hidden under the stage floor. The default camera saw its back. Neutral failed as well as combined; hiding only the floor revealed the missing lower geometry. The original GLB stood correctly on that same stage. This was a required integration fix, separate from the retained clothing/appearance HOLD.

The uploaded neutral visible body had bounds
`(-0.49627015,-0.8167598,-0.32147008)` to
`(0.49627015,0.84912986,0.09299983)` metres. Its height was 1.66588966 m, but its feet were 0.8167598 m below the fixed stage floor at y=0.

## Reproduce the regression

```sh
cargo test -p nvwa-runtime b1::tests::production_b1_neutral_visible_body_stands_on_stage_floor --locked --offline -- --exact --nocapture
```

Before the placement fix, this actual plugin/load/fit/upload test ran in 1.21 s and failed the specific feet-on-floor assertion: 0 passed / 1 failed, Cargo exit 101. Source SHA256 was `ea8c27eb74f7a21a23cce887fba585d05134b19dccbe4decea5067776ddd6a42`. It measures only final uploaded triangle indices, excluding unindexed helpers and body faces hidden beneath clothing. Readiness counters alone did not catch the defect.

## Bounded correction

The source model is centred around its pelvis. Humentity's display root turns source front +Z toward −Z, while the existing stage's default camera is on +Z. The product backend now composes a common presentation transform for body and garment:

`T(0,-fitted_rest_min_y,0) * Ry(pi) * source_model_to_world`

The minimum comes from unposed fitted body positions restricted to the final visible body triangles. Each shape gets its own rest anchor. A knee/combined pose does not recompute the anchor from posed feet, so changing pose does not make the character bob. The existing Work scale then applies once. Camera, floor, lights and all persisted Work values stay unchanged.

Empty, missing or nonfinite rest bounds reject before new displays are published. Source assets, adapter/vendor geometry, rig fitting, canonical poses, full-positive influences, mesh-local arrays and historical numerical thresholds remain unchanged. The original GLB keeps its existing placement.

The expanded production test checks five pose anchors, signed torso endpoints, model-front orientation, finite indexed geometry, scale 1.2 on both displayed world bounds, unchanged local positions/mesh handles, and unchanged persisted stage. Actual face visibility and viewport framing still require graphical checks; a transform assertion is not a screenshot.

## Execution identity

The bounded local repair run retained the precise red source and then accepted only a root-reviewed, SHA-bound replacement of `b1.rs`. Both phases use that run's own build directory. This is an explicitly mutable diagnostic run; it is not an immutable final-head build claim. Final builds must retain their source/output receipts, and final PR and merged-main CI remain separate.

Source review cleared `b1.rs` SHA256 `f5edb496e98ad7b83b30a66eb0f2f49ef0a468910f0047ac329ae4b1f07f7189` for green execution. Test, package, graphical and hosted results are recorded separately in the [integration record](README.md). No performance, continuous-motion, arbitrary-input or public binary-release acceptance follows from this correction.

The expanded regression then passed as part of 155 successful workspace CPU tests. The complete local repair gate subsequently built and packaged native and Web outputs. Actual corrected Web acceptance showed the full front-facing body above the floor across all five poses; torso/jaw edits, one-step Undo/Redo and complete Web/CLI Work roundtrips also ran. These graphical results are recorded in the [validation record](VALIDATION.md). Native GUI and actual desktop/Web exchange remain NOT-RUN while the Mac is locked. Hosted final-head CI and merged-main CI remain separate gates.
