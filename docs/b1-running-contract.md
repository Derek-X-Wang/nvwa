# Finite authored running with travel

The exact `nvwa-mpfb-b1-running-v1` profile uses `b1_cpu` backend version 6 on the existing admitted V4 character and appearance assets. Its new `b1_run_forward_authored_v1` action is original Nvwa-authored content, not generated motion. Source duration is four seconds and net forward travel is two metres before character scale. The two original rehearsal actions remain unchanged in the new catalogue. Existing versions 1–5 and their saved Works are unchanged; older readers reject version 6.

Create through Studio's **New running character** action or:

```sh
nvwa-cli new-character-running <asset-root> <work.json>
```

The normal `describe-capabilities`, `inspect`, `validate`, `apply` and `save` commands use the same Work and asset validation. CLI operations edit files and do not control a running Studio. Work schema remains unchanged. New running Works start with a finite, nonlooping run. An empty timeline selects the stored diagnostic pose. A single looping entry starting at zero is rejected for this profile; finite loops inside an arrangement remain supported. The legacy singleton indefinite preview is unchanged for old profiles.

## Source and timing

The shipped control JSON fixes 961 source knots at 240 Hz, sixteen named bone-local quaternion rotations and their shared tangents. The runtime evaluates normalized quaternion-component cubic Hermite with tangents measured per **source second**. It does not use SLERP, regenerate tangents, run IK or correct grounding. Shared tangents establish source C1 continuity; the endpoint rotations are neutral and endpoint derivatives are zero. This does not establish visual smoothness or C2 continuity.

Core owns the one analytic displacement declaration: stage +Z forward, +Y up, metres before character scale. The source has a 0–0.4 second onset, four alternating strides over 0.4–3.6 seconds and a 3.6–4 second stop. Vertical bounce is authored source-local content, not a grounding operation. Source and rendering evidence must not be confused: source contact/flight windows are obligations to inspect, not measured contacts.

For an entry, source elapsed is the clamped wall span multiplied by speed. Nonlooping source time clamps to the source endpoint; a finite loop wraps source phase and retains completed horizontal cycle travel. Entry anchors sum preceding entries' actual finite **horizontal X/Z** endpoint contributions in chronological order. They are recomputed from Work and resolved time; they are never integrated from prior frames. Character scale multiplies both the grounded character and its displacement exactly once.

Gaps retain the previous complete endpoint pose and offset, including vertical bounce. A subsequent action uses its own source-local Y relative to the fixed floor and inherits horizontal arrival. An explicit cut out of flight can jump vertically; deterministic resolution does not make that edit a smooth or grounded join. For example, cutting at source 0.672 holds 35 mm bounce through a gap, but a following rehearsal starts at its own zero bounce. Repeated cuts never accumulate permanent elevation.

Pause retains the current published sample. Arbitrary seek order, reopen then seek, timeline edits, Undo and Redo derive placement from the resulting Work. Normal Open resets to zero and paused. A finite arrangement holds its final pose and arrival offset. Replay deliberately resets to the initial anchor; that reset is not a continuous travel join.

## Publication and observation

The new exact-profile path prepares both full-positive body/garment skin buffers, actual placements and every requested appearance role before one exclusive commit. Failed preparation retains the previous complete visible frame, pauses transport and rejects requested evidence. Candidate Open and shape/appearance replacement use the same preparation gate. The legacy appearance updater does not run a second time on a committed running Work. The old fit, canonical gauge, prepared-rig application and skin arithmetic remain unchanged.

`nvwa_runtime::b1_running_observation(&World)` returns a small validated publication header for the running profile. It verifies the bound Work/transport, actual bone matrices, body/garment and accessory buffers/topology, actual placements, appearance-role bindings and matching publication serial without serializing full meshes. It rejects pending, failed, stale or mixed bindings. Fields include `generation`, `revision`, `profile_id`, `work_sha256`, `serial`, `playing`, `completed`, `position_seconds`, `resolved`, `display_transforms`, `control_sha256`, `ready` and `error`. `resolved` includes clip/entry identities, unwrapped elapsed time, source phase, completed cycles, horizontal anchor, source-local offset and total unscaled actor offset. This is an observation of an actual bound frame, not a declared trajectory alone.

`b1_frame_snapshot` retains its original schema-1 output for old profiles. Running output is separately identified as schema 2. It retains the actual body/garment `bones` and `parts` buffers, adds `running_publication`, `resolved_running` and actual validated `appearance` observations. Appearance observations include actual accessory placements and buffers. CPU readback is not GPU readback or visual acceptance. Apply each part's actual `display_transform` once to its model-local positions to obtain stage/world coordinates.

## Evidence boundary

Availability of a profile/action is not acceptance of recognizable or natural running. The source was authored from admitted raw rest data. A small reach margin and raw onset penetration remain quality risks; they do not establish production contact, garment quality or behavior on edited shapes. Actual normal playback/time, independent timed-frame motion recognition, full-positive production contact/flight/penetration, edited shape/scale, normal Web/CLI/file-picker exchange and release checks remain separate gates. Continuous visual quality requires an eligible observer to watch actual complete playback. Existing character, garment and held-foundation quality limits remain in force.
