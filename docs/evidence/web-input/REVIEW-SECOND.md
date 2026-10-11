# Targeted R2 rereview — checkpoint cc263794

Verified frozen SHA-256 values match the dispatch: web_input.rs `cc263794e446ab466da8f1c0d9f010279da2442cb6115b9cf9d93ebcbcb645d2`; lib.rs `8dca0482f4ef87c94376b6199e11a7ae7215511386ac3da7fb8ee04a22315c7e`; Cargo.toml `7532429f4e3ebf34bea8bfb5a52c99ed02bae6714ac33a59fcf897252bb74050`; rework-regressions.rs `b57069d772d15f0029f4e9961f9a2ff6e1f5daeac5d2f61cd4ffe491b5b074a0`.

## Unresolved finding

**P1 — frame-wide finalization loses a subsequent composition's rollback state.** `web_input.rs:90–101,126–135` classifies the entire input frame with `any(Commit/Text/Paste/Key)` and removes the composition snapshot after TextEdit reports a change. DOM callbacks are queued until the next Bevy frame, so one frame can contain the end of composition A followed by preedit for composition B. Starting from `pathnv`, a frame containing `Commit("女娲")` followed by `Preedit("hao")` leaves egui text `path女娲hao`, then removes the snapshot because that frame contains a Commit. Surrendering focus in the next frame leaves `hao` canonical. The same error occurs with ordinary committed text followed by a new preedit in one frame. Fix transaction boundaries in event order and preserve the committed prefix before the last active composition. Add the exact batched sequence, then focus surrender, asserting `path女娲` and unchanged other field. Root has accepted and dispatched this finding.

## Resolved or supported by this checkpoint

- The original single-composition focus-surrender failure has a direct canonical rollback path independent of the dropped old-target cancellation. Real-egui regressions cover another widget receiving focus, surrender after field drawing, restoring cursor, preserving a completed commit, and leaving a different externally assigned value untouched.
- The clipboard defect is corrected at line 54 by `Event::Paste`. Pinned egui 0.36.2 `text_edit/builder.rs:1138` replaces **each** CR and LF with a space: `one\r\ntwo\nthree` becomes `one  two three`. Both regression checks use this exact normalization and also reject remaining CR/LF.
- The adapter explicitly binds only `work_id()` at lines 638–640. Native `draw_work_path` still executes the original single-line TextEdit construction; the explicit ID/snapshot wrapper is Wasm-only. The Web Player's existing cfg omission of the editable path is preserved.
- Studio cleanup runs after the UI and before either Open or Save reads `state.file_path` (`lib.rs:759–770`). Player cleanup is likewise before Open reads it (`882–886`).
- Snapshot cursor and undoer ownership are isolated: a fresh TextEditState receives copied cursor and cloned undoer. Pinned egui's `undoer()` returns a value clone; `set_undoer()` mutates the fresh owner. Rollback clamps restored cursor indices to the restored text length.
- Different externally assigned canonical strings invalidate the snapshot via equality guard. This does not establish provenance for an external assignment of the exact same bytes as current preedit; current production lib.rs has no post-startup external file_path assignment, so no additional present trigger was established.

## Verification and limits

Inspected `experiments/08-web-ime/rework-output.txt`: exact standalone rustc linkage is recorded, 10 tests passed, zero failed/ignored, exit 0. This is inspected execution evidence from the implementer, not a reviewer rerun. Those tests do not cover multiple composition transactions in one input frame.

No browser, physical IME, Cargo build, GPU, clipboard access, or production edits by this reviewer. Focus recovery, callback ordering, and the newly added clipboard queue filter remain actual-browser acceptance items owned by root. Passing this targeted review cannot be claimed until the new P1 is repaired. Initial evidence logs were not modified. Only this report was created; root owns retention.
