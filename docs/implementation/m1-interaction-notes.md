# Thin M1 character-click preparation

Status: #15 source implemented after the orchestrator verified and closed #14, 2026-10-10. The original investigation below explains the approach and its limits. Worker verification is limited to source inspection and formatting; compiler/tests/native/Web acceptance are owned by the orchestrator.

Checked checkout: `/Users/derekxwang/Development/incubator/Nvwa/nvwa`, branch `feat/thin-m1`. M0 reference: `d74493df0ab14f786e798cee03efe5ef9e2e4670`. Exact installed sources: Bevy 0.19.1 and bevy_egui 0.42.0. Runtime and minimal Studio hooks were serialized after the #14 owner released both files.

## Implementation checkpoint

- Runtime provides `SceneCamera`, `CharacterInteraction`, and the `CharacterInteractionInput::click(Ray3d)` system parameter. It checks the original fixture ID/hash, ready verified asset generation, wave availability, and animated chest/head ellipsoid intersections. A pending or active hit is ignored.
- Shared `add_playback_systems` orders wave start/cancellation before animation advancement and completion/restoration before target evaluation. `RuntimeSystems::Transport` lets Studio order current egui intents before transport. Playback remains unchanged during wave; completion reconstructs the exact saved cursor and play/pause/completed state without advancing it on that frame.
- Document generation or revision changes, external transport changes, readiness loss, and missing/replacement players cancel the override. No old snapshot is restored on cancellation. Normal document/transport behavior then applies.
- Studio captures clicks once after current egui layout and transform propagation. It rejects an unfocused window, editor input, inactive camera, and cursor outside the camera viewport. Timeline controls and Space are disabled while the interaction is pending/active; appearance edits, undo/redo and document opening can cancel it.
- The original generic `is_pointer_over_egui` guard needed a narrow repair. In egui 0.36.2 `context.rs:2943–2975`, a Background layer without `run_ui`'s `root_ui_available_rect` is treated as UI. Studio builds its root `Ui` manually. `editor_owns_pointer` therefore checks the actual remaining scene rectangle, active egui pointer capture, and foreground overlay layers. This leaves the scene clickable while panels, sliders and popups remain guarded.
- New CPU regressions use actual Bevy graph/Transform curves and the same transport helper: `character_click_wave_restores_running_sequence_cursor_and_history`, `character_wave_restores_paused_completed_and_m0_loop_samples`, `character_interaction_cancels_on_open_edit_undo_and_player_loss`, and `character_hotspot_rejects_background_stale_clicks_and_tracks_animated_joint`. Studio's `current_egui_frame_guards_panels_and_overlays_but_leaves_scene_clickable` uses real egui CPU passes. These curves are controlled regression fixtures, not evidence that the authored GLB ran.

PARTIAL — Owned Rust files formatted successfully with `rustfmt --edition 2024`. Compiler, tests, real clicks and native/Web visual acceptance have not been run by this worker. Runtime/Studio source and this note are the only worker writes; no dependency, manifest, lockfile, asset, core or platform change.

### Bounded R2 repairs

The orchestrator reported the first frozen source passed 46 workspace tests and a real native paused-cursor chest click triggered the authored wave while a background click did not. That is a checkpoint, not final acceptance of the repaired source or complete native/Web coverage.

Independent R2 review identified two accepted input/geometry defects. The input gate now drains real primary-window `WindowFocused` messages and rejects any frame that restores focus, even when the final `Window.focused` flag is true. The `ScenePointerInput` system parameter is used directly by production scene clicks and by `refocus_press_is_rejected_but_next_focused_press_reaches_scene_input`, which sends real focus/mouse messages through Bevy's `InputPlugin`. It also checks that later ordinary clicks and secondary-window focus events remain valid.

The collider's old absolute `f32::EPSILON` determinant cutoff rejected valid small original-character scales. It now rejects a zero/non-finite determinant, a non-finite inverse, or invalid/non-finite transformed ray data. `chest_and_head_hotspots_accept_small_scale_centers_without_accepting_outside` covers center hits and just-outside misses at scales 0.01, 0.03, 0.1 and 1.0. Singular transforms remain rejected. The core's valid scale range is unchanged.

PARTIAL — Both accepted repairs are implemented and owned files formatted. Repaired-source tests, targeted independent rereview and final actual native/Web acceptance remain with the orchestrator.

## Recommendation and fidelity boundary

Use an actual left-mouse click, the real camera ray, and an explicit collider for the one original fixture. Use small ellipsoids attached to the animated chest/head joints as conservative initial hotspots. They follow the skeleton and document scale. They do not fill a full-character rectangular screen region or allow floor clicks to trigger the action. Existing Bevy math APIs support this without manifest changes.

This is approximate character hit testing, not exact rendered-surface picking. The orchestrator accepted this chest/head boundary during preparation; display the hint **“Click chest/head to wave”**. Candidate hotspots must be visually checked across idle, turn, wave, supported morph extrema, document scale and window scaling. Source geometry alone does not prove containment after weighted skinning. Limbs, silhouette edges, and gaps are not covered. Neither this bounded proxy nor current built-in mesh picking provides full deformed silhouette picking.

| Approach | Exact installed APIs | Fidelity and cost | Dependency effect |
| --- | --- | --- | --- |
| Authored original-fixture collider, recommended for thin M1 | `Camera::viewport_to_world`, `RayCast3d::from_ray`, `RayCast3d::sphere_intersection_at`, `BoundingSphere::new`, joint `GlobalTransform::affine` | Real ray intersection with a deliberately bounded hotspot. Following a joint reflects skeletal motion approximately. It does not reproduce blended skin or morph geometry. Small head/torso ellipsoids avoid most obvious empty AABB space; containment still needs real visual verification. | None; camera/math features already selected. |
| Built-in CPU mesh triangle raycast | `bevy::picking::mesh_picking::ray_cast::{MeshRayCast, MeshRayCastSettings, ray_mesh_intersection, Backfaces}` | Exact intersection with supplied CPU triangles. The system parameter uses undeformed `Mesh::ATTRIBUTE_POSITION`; neither skinning nor morphs are evaluated. Current rendered hands/head/shoulders can disagree. A rest-pose hit and an animated-pose miss are both possible. | Root would enable Bevy `mesh_picking`; feature/version changes belong to root. |

For exact animated geometry, `ray_mesh_intersection` can consume CPU positions deformed with the same morph deltas, weights, joints and inverse bind matrices as rendering. The public function takes a position slice, so it need not mutate the render mesh. That adds fixture data extraction, deformation, timing and validation work. It is not a capability obtained merely by enabling mesh picking. Do not undertake that larger path silently.

## Source evidence

The sources below are already installed under:

`/Users/derekxwang/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/`

The ctxfs skill was read. Its local-source exception applies: no remote mount, daemon, extension, install, or new dependency download was needed.

- `bevy_camera-0.19.1/src/camera.rs:615–676`: `viewport_to_world(&GlobalTransform, Vec2) -> Result<Ray3d, ViewportConversionError>`. The ray begins on the camera near plane. The included example schedules after transform propagation.
- `bevy_camera-0.19.1/src/camera.rs:456–463, 797–814`: `logical_viewport_rect` and `viewport_to_ndc` use logical pixels. Conversion subtracts the viewport origin and flips Y. It does not reject coordinates outside the viewport; check containment first.
- `bevy_window-0.19.1/src/window.rs:613–644`: `Window::cursor_position()` returns logical pixels and `None` outside the window. It divides the physical cursor by the window scale factor.
- `bevy_math-0.19.1/src/bounding/raycast3d.rs:24–91`: `RayCast3d::from_ray(ray, max)`, `aabb_intersection_at(&Aabb3d) -> Option<f32>`, and `sphere_intersection_at(&BoundingSphere) -> Option<f32>` are the supported bounding intersection APIs. `bevy_math/src/lib.rs:31` exports `bounding` without a picking feature.
- `bevy_math-0.19.1/src/bounding/bounded3d/mod.rs:512–525`: `BoundingSphere::new(center, radius)`.
- `bevy_picking-0.19.1/src/mesh_picking/ray_cast/mod.rs:202–320`: `MeshRayCast` first intersects entity AABBs, then fetches `Assets<Mesh>`, applies the entity affine transform, and tests triangles. Its query includes visibility, mesh handles and transforms; it does not include `SkinnedMesh`, joint transforms or morph weights.
- `bevy_picking-0.19.1/src/mesh_picking/ray_cast/intersections.rs:42–107`: triangle-list topology and float3 position data are required. It reads `Mesh::ATTRIBUTE_POSITION`, optional normals/UVs and U16/U32 indices. `ray_mesh_intersection` accepts explicit position and index slices. Transforms are applied to the ray; nearest valid triangle intersection is returned.
- `bevy_pbr-0.19.1/src/render/mesh.wgsl:13–54, 74`: the render vertex shader adds weighted morph positions, then obtains the skin matrix, then transforms the vertex. A raw CPU mesh raycast therefore does not test the currently rendered surface.
- `bevy_camera-0.19.1/src/visibility/mod.rs:320–327`: `DynamicSkinnedMeshBounds` tracks joint transforms but explicitly excludes morph targets and vertex shaders. Even a dynamic AABB is an enclosing volume, not a triangle or silhouette hit.
- `bevy-0.19.1/Cargo.toml:2810` and `bevy_internal-0.19.1/Cargo.toml:303–305`: Bevy's `mesh_picking` feature enables `bevy_picking/mesh_picking`. `bevy_picking/src/lib.rs:163–164` gates the module on that feature.
- `bevy_egui-0.42.0/Cargo.toml:44–68, 201–205`: its default feature set includes picking; Nvwa disables defaults and enables only render/fonts/clipboard. The optional picking dependency enables mesh picking only when selected. Presence in Cargo.lock is not proof that it is enabled.

The root workspace explicitly lists Bevy features and currently omits `mesh_picking`/`bevy_picking`; its listed Bevy feature expansions do not activate mesh picking. No `cargo tree` or compiler was run for this preparation.

## Original-fixture collider facts

The verified profile identifies `nvwa-original-humanoid-v1`, GLB SHA-256 `f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6`. Gate the collider on the original asset identity. Do not apply its dimensions to arbitrary loaded characters.

Authoring geometry is in `tools/blender/generate_fixture.py:59–76`; original skeleton definitions are at lines 150–162. Blender uses Z-up; the exported GLB and Bevy use Y-up. A read-only GLB JSON inspection found these rest joint positions, derived from the exported hierarchy: chest Y=1.19, head Y=1.48. Their inspected nodes have translations and no local rotation. The rig node has no transform. The exported body is split into material primitives, each with CPU accessor bounds; those bounds enclose the rest mesh and are not hit surfaces.

Possible conservative initial ellipsoids, in the named joint's local coordinates:

| Joint | Center | Radii | Rationale |
| --- | --- | --- | --- |
| `chest` | `(0, 0.03, 0)` | `(0.17, 0.18, 0.10)` | Smaller than authoring chest ellipsoid; avoids filling the arm/torso gaps. |
| `head` | `(0, 0.17, 0.015)` | `(0.11, 0.15, 0.09)` | Smaller than the authored head; avoids broad jaw/nose silhouette claims. |

These are starting hypotheses, not visually verified production dimensions. Skin weights blend several joints; following one joint cannot exactly track a surface. Shoulder-width and jaw/nose/smile morphs do not update a fixed collider. Conservative dimensions trade missed edge clicks for fewer background false positives. Missing joints, invalid transforms, mismatched profile/asset identity or non-ready runtime must yield no hit.

For an ellipsoid, compose the joint world affine transform with center translation and radii scale. Invert that affine to transform the world ray into a unit-sphere ray. Normalize the transformed direction with the fallible `Dir3::new`, then call `RayCast3d::from_ray(local_ray, local_max).sphere_intersection_at(&BoundingSphere::new(Vec3::ZERO, 1.0))`. Keep a finite positive world range; convert it to local range by multiplying by the length of the transformed, unnormalized direction. If a hit distance is needed, transform the local point back to world coordinates before comparing world distances. Reject singular/non-finite transforms and nonpositive radii. For a boolean hit, any valid hotspot intersection suffices.

The existing fixed camera is `(3.1, 2.0, 4.8)` looking at `(0, 0.95, 0)` in runtime `setup_environment`. Do not hard-code projected screen rectangles; the ray API handles window resize and pixel scaling. A runtime-owned explicit scene-camera marker is safer than selecting every camera once egui adds its own camera/context entities.

## Input and schedule investigation

Before #15, Studio set `UiInputGuard.pointer` from `egui_wants_pointer_input() || is_pointer_over_egui()` and `UiInputGuard.keyboard` from egui keyboard interest. The implementation checkpoint records the required scene-rectangle correction. `draw_studio` runs in `EguiPrimaryContextPass`; bevy_egui ends that pass in `PostUpdate` (`EguiPostUpdateSet::EndPass`). A handler in ordinary `Update` would see the previous frame's guard. Do not use that stale guard for same-frame scene click acceptance.

Proposed flow:

1. In Studio, run the real pointer handler in `PostUpdate`, after egui `EndPass` and after `TransformSystems::Propagate`. The latter also follows current animation evaluation. Run once outside the multipass egui drawing schedule.
2. Require `ButtonInput<MouseButton>::just_pressed(MouseButton::Left)`, the focused primary window, a cursor inside the scene camera's logical viewport, `!guard.pointer`, runtime readiness and no active interaction. A held button is not a second trigger. No mock action button counts as acceptance.
3. Convert logical cursor with `camera.viewport_to_world(camera_global, cursor)`. Apply the collider test to the loaded original character only. Floor/background and editor panel clicks produce no trigger. Failed conversion produces no trigger.
4. Submit one generation/revision-tagged runtime request. Consume it in the next animation-control pass, before the normal sequence cursor advances. The implemented pass is `PostUpdate` before `advance_animations`, after current egui intents. This adds at most one frame of input latency and keeps Studio out of private animation graph ownership.

The final #14 schedule may use different named sets; inspect its actual owner before writing constraints. Do not create a cycle by putting click handling after transform propagation and before same-frame animation evaluation. Scheduling against current transforms plus next-frame request consumption is a simple boundary.

## Proposed shared runtime interface

Keep Studio dependent on runtime, with no runtime dependency on egui. The future static Player can submit the same request without a UI guard because it has no editor controls.

Minimum interface proposal, not an implemented API:

- Runtime exposes a scene-camera marker and a narrow original-character hit description (two joint entity references plus local centers/radii, with document generation). Alternatively expose a pure `character_hit(ray, ...)` helper/system parameter. Keep `CharacterAsset` and animation node map private.
- Runtime owns a one-slot request resource, for example `CharacterInteraction::request_wave() -> bool`, and a public `active()` query. Return false while active or unavailable; do not queue repeated clicks.
- Runtime owns override start, progress, completion and cleanup. The input layer submits intent only.
- Add small named system sets if #14 does not already expose suitable ordering: consume requests before sequence advancement; apply effective animation through one owner; observe completion after `AnimationSystems`.

The temporary override must not call `EditorState::apply`, modify the timeline, increment revision, or add undo/redo history. Do not implement it by changing the selected document clip; M0 `control_playback` resets a selected clip to the document timeline's first entry. A separate ephemeral override must compose with the verified #14 sequence evaluator.

The orchestrator relayed #14's settled `Playback` fields: `clip_id`, `playing`, `position_seconds`, `seek_request`, `active_timeline_id: String`, `completed: bool`, `error: Option<String>`. For a finite sequence, position/seek are global wall time. M0's single looping action retains a source-time cursor. Preserve those semantics: wave progress belongs to the transient override, not `Playback.position_seconds`. This field list is an integration handoff, not independent proof that #14 has passed verification.

## Wave override state and completion

Recommended state machine:

`inactive → accepted character click → active wave → wave finished → prior sequence state`

At acceptance, record document generation, sequence cursor, selected segment if needed, and prior play/pause state. Freeze the sequence cursor for the entire override. Play the loaded authored `wave` animation from zero at speed 1, `RepeatAnimation::Never`, independently of whether the sequence was paused. Apply recipe morphs through the existing runtime path throughout.

Keep sequence state intact and derive an effective animation selection from the override. One animation-control owner must select the node each frame; competing wave and sequence writers are unsafe. While active, do not copy wave `seek_time` back into sequence position. Ignore further click requests rather than restart or queue them. Disable timeline play/pause/seek/edit controls for this short override, or explicitly reject those intents; otherwise restoring a saved snapshot can erase a newer user request.

`bevy_animation-0.19.1/src/lib.rs:549–562` documents `ActiveAnimation::is_finished()`; `RepeatAnimation::Never` completes after one repetition. `replay()` at lines 594–601 resets completion state. `seek_to()` at lines 707–712 changes seek position without resetting the completion count. The exact API supports the override, but its finished check must run after animation advancement, or accept a documented one-frame observation delay. The profile's actual authored wave duration is `3.0416667461395264` seconds. Do not use a nominal three-second timer that truncates the last frame.

On completion, switch the effective animation back to the segment at the frozen sequence cursor. Set the restored node's local seek time from the sequence evaluator and restore the prior play/pause state. Preserve a paused final pose and correct sequence boundary semantics from #14. If the prior segment also used wave, reset/replay before seeking so the temporary wave's completion count cannot prevent resumption. Prefer reconstructing from retained sequence state over storing Bevy Entity/GPU handles in the document.

Opening/replacing a document, asset reload/failure, empty timeline, lost player or missing wave node cancels the override and clears stale requests. Use document generation so a delayed click cannot affect a replacement character. Do not restore a cursor snapshot from the old document into the new one. Runtime owns failure status; do not wait forever for an absent player.

## Required acceptance after implementation authorization

- Real native and Web scene head/torso click runs authored wave once, then resumes the exact sequence cursor and prior playing state.
- Repeat with a paused sequence: wave runs, then the sequence stays paused at its prior cursor.
- Rapid clicks do not restart/extend wave or create a queue.
- Editor buttons/sliders/text input, empty background, floor and space around the head/torso do not trigger wave. Test the visible outline across original morph extrema and all three authored actions; record supported misses honestly.
- Resize/HiDPI uses current logical coordinates; cursor outside the canvas or unfocused window does not trigger.
- Document revision, timeline, parameters and undo/redo stacks remain unchanged by the interaction.
- Reload during an active override clears it without applying stale state to the replacement player.
- CPU state/geometry tests can verify transitions and known rays, but cannot replace real user-click/native/Web visual evidence.

Historical preparation scope: only this note was written before #14 acceptance. Implementation was subsequently authorized and is recorded in the checkpoint above. No actual execution claim is inferred from source or authored regression tests.
