# Thin M1 sequence

Uses the existing `SceneDocument.timeline` and atomic `Command::SetTimeline`.
No stored schema fields, dependencies, assets or platform adapters change.

## Playback bounds

- `duration_seconds` is each entry's wall-time span. `speed` maps elapsed wall time to source pose time.
- Multi-entry timelines play once to the maximum entry end. Exact shared boundaries select the next entry. Source IDs can repeat; stable timeline IDs identify each occurrence.
- Start times, rather than JSON array order, determine playback order.
- Nonlooping source actions hold their final pose when the wall-time span lasts longer than the source. Looping entries repeat the source within their finite span.
- Gaps hold the previous entry's endpoint. Before the first entry, hold its initial pose. Seeking into a gap gives the same pose as playing into it.
- Overlapping spans now fail core validation with `overlapping_timeline`; failed commands leave document content, revision and history unchanged. M0 single-entry documents remain valid.
- The M0 one-entry, start-zero looping preview remains indefinite. Its cursor/seek uses source seconds, as before. Finite works use global wall seconds.
- Empty timelines stop all animations. Finite works stop and hold at the final end; Play/Replay at completion restarts from zero. Restart explicitly seeks zero and plays.
- Timeline edits, undo/redo that change the timeline, and explicit reopen reset the cursor. Appearance-only edits keep it. Timeline edits keep the user's play/pause choice; file-open asset loading starts playing, as in M0.

## Runtime integration

`Playback` keeps `clip_id`, `playing`, `position_seconds`, `seek_request` and adds runtime-only `active_timeline_id: String`, `completed: bool`, `error: Option<String>`. The active clip/entry describes the sampled action, including gap holds. Errors do not modify portable document data.

Finite playback samples a real `AnimationPlayer` after Bevy advances its animations and before `animate_targets` evaluates the skeleton. Each sample sets absolute source pose time and clears stale completion counters. A new player inherits the current cursor and pause state. M0 indefinite preview applies pause, resume, seek and switch intents before `advance_animations`, then mirrors the actual advanced source cursor afterward. A pause holds the last rendered pose exactly; resume advances in the requested frame. This retains Bevy's natural loop progression.

Studio's Create 9s sequence sets idle, wave and turn to three seconds each with one typed command. Row action changes, duration buttons, reorder and removal each commit one command. Duration/order/removal changes compact rows into adjacent spans. The existing egui `will_discard` side-effect guard remains.

## Verification checkpoint

Source formatted with scoped `rustfmt`. No Cargo build/test, GPU/UI run, installs, downloads, commits or external writes were executed by this worker.

Added headless runtime tests use actual Bevy `AnimationClip` translation curves, `AnimationGraph`, `AnimationPlayer` advancement and `animate_targets` to verify a real joint transform. They cover boundary progression, pause/seek hold, backward and repeated-source seeks, completion/restart, speeds, gaps, source endpoint/loop behavior, reordered storage, atomic overlap rejection, undo/redo, portable reopen and replacement players. Existing M0 playback and asset recovery tests remain. Studio's test checks the nine-second atomic edit, save/reopen, reorder, undo and redo.

NOT-RUN — tests await the integration owner's build slot; native/Web graphical acceptance remains the integration owner's task.

## R2 pause repair checkpoint

Fresh review identified a legacy-loop pause drift in the first implementation: applying pause after Bevy advancement held one additional frame of source time. The repair applies M0 intents before advancement while leaving finite sampling after advancement. Shared timeline-reset logic remains in one helper.

Added `m0_loop_pause_holds_rendered_joint_and_resume_advances_in_production_order`, using the actual AnimationPlugin PostUpdate order and a real animated joint. It verifies pause at 1.0s with a 0.25s frame delta, repeated paused frames, nonzero-delta paused seek, immediate resume progression, source looping, paused action switch and resume. The existing replacement-player regression now uses the same pre-control → advance → mirror PostUpdate order.

NOT-RUN — repaired source is formatted and passes `git diff --check`; root owns test execution and targeted R2 rereview.
