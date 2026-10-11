# Bounded M1 contract

The accepted kickoff and user-approved issues define three authored actions over 5–10 seconds, play/pause/seek, one character click interaction and a static Player. Keep existing Rust core/runtime and schema fields. No second frontend, renderer, model service or general scripting system.

## Sequence semantics

- A timeline segment has a stable ID, authored action reference, wall-time start and duration, positive speed, and per-action looping. Its end is start + duration; speed maps segment elapsed wall time into authored local pose time.
- A 9-second demo is idle0–3, wave3–6, turn6–9. Segment boundaries select the next action; seeking is global and deterministic, including repeated action references.
- Multi-entry finite spans cannot overlap. Reject overlap atomically with a structured core error; this refines previously unsupported multi-entry playback. Existing M0 single-entry works remain valid. Gaps hold the preceding endpoint; pre-first time holds the first pose.
- Nonloop actions shorter than their segment hold their end pose. Looping actions repeat within the finite segment. A finite sequence stops at its total end; Play after completion restarts. The existing start-zero single looping action retains M0 continuous looping behavior.
- Pause holds the pose. Seek works while paused and after completion. Open, undo and redo derive playback consistently from the authoritative document, including newly replaced animation players.
- A sequence edit uses existing SetTimeline and forms one transaction. Appearance and all segment data survive CLI/GUI save/exchange. Cursor and play/pause remain session state.

## Interaction and Player

Click one real character target to play wave once, suspend the sequence cursor, then restore its position and prior play/pause state. Ignore repeated clicks while active. Background/editor clicks do not trigger it. The interaction never changes the stored work, revision or history. Exact hit-testing geometry/fidelity will be documented before integration.

Player hides editor panels but uses the same renderer, timeline and interaction. Keep minimal open, play/pause/seek controls and clear errors. Native launch flags and Web query mode must remain narrow platform adapters. An ordinary static bundle can load a published work without a model/API service.

## Verification seam

Prefer externally observed document/CLI outcomes and actual Bevy AnimationPlayer/pose behavior over implementation-mirroring tests. Cover segment boundaries, backward seeks, same-action segments, nonunit speed, gaps, overlap rejection, completion/restart, reload, interaction restoration and input guards. Root owns actual native/Web GUI acceptance and final release builds/measurements. All remaining M0 limitations retain their own GitHub issues; they are not converted into passes.
