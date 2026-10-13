# Independent M1.1 permanent UI paint review

Reviewer: Astra, fresh read-only cross-model session; implementer: Sol6.1 (dispatch identities). Base/HEAD: 045d8abc685760d09ba05afec0e40a811a282d1f. Branch: codex/m11-ui-paint-permanent. Reviewed exact uncommitted editor_layout.rs diff, new editor_layout_paint_tests.rs, and docs/evidence/m1-1-final/ui-paint/. Budget: R1 with cross-model oracle scrutiny.

Outcome: ACCEPT for the bounded permanent CPU paint-test scope. No actionable findings.

- Production is called by Studio and by StudioHarness.frame through draw_editor_ui. Production implementation is unchanged; additions/visibility/time override are cfg(test). Existing callers retain None time (the old RawInput default).
- Expected active/inactive colors and inspector text are literal scripted values, never selected from layout.tab. Pointer press/release reaches actual Profile then Shape controls. Both requested viewport loops ran; independent replay printed all 12 expected tab paint observations and both eight-frame invariance receipts.
- Labels must be unique. Background must contain the label, be exactly 100x26, precede text, and have a clipping rect containing the label. Candidate observation count is capped at 64; Shape/Profile rects cannot overlap. Real output rejection controls delete/duplicate observations, and logs show the expected zero/two versus one failures.
- Complete Work JSON and derived Debug of Editor (including undo/redo Snapshot queues and retry history) are stable after clicks and observations. Fixture proves both history directions nonempty.
- Existing CI macOS native lane invokes cargo test --workspace --locked via experiments/27-ci-baseline/check.sh; cfg(test) module is discovered without a new job or workflow edit. Hosted execution remains unverified.
- Raw private green/mutant/restored Cargo JSON compiler-artifact objects exactly match published metadata and successful build-finished records. All discovery lists and exit receipts agree. In-memory single painter inversion recreates recorded mutant source SHA-256; original/restored/current source hashes agree. Mutation log has only the positive paint test fail with a literal selected fill mismatch; existing state test remains green. Mutation was not replayed by reviewer.

Independent execution (no Cargo/build/source mutation):
- Existing executable SHA-256 8b971a64dd89199a50ea6c36a29a31abf69f81e8df8d0665a0ced903b9d6d702 verified before/after runs.
- Exact six-name paint discovery matched; 6/6 passed, 0.03 seconds.
- Exact existing state-test discovery matched; 1/1 passed, 0.01 seconds.
- All 10 existing editor_layout::tests tests passed, 0.05 seconds, covering original controls, focus guards, shape drag, discarded passes, resize/cancel/lock/reset behavior.
- git diff --check passed. Reviewer did not independently run rustfmt.

Limits: This is egui emitted-shape evidence, not final clipping/occlusion, raster, GPU, native window, browser, DPR, or IME proof. Only background clip coverage is checked; text-count helpers do not assert final text visibility. This is consistent with the explicitly bounded CPU paint contract. Reviewer inspected recorded mutation-red proof but did not rebuild or replay source mutations. Whole workspace, hosted CI, and Web builds were not run. Fixed sentinel styling intentionally removes theme/runtime presentation variance.

Scope and cleanup: Only .work/m11-review/ui/ receipts were written. An initial reviewer discovery command accidentally listed the full executable; its assertion rejected the list before running tests and it was corrected. All test subprocesses exited; no persistent reviewer processes/resources. Reviewed source, evidence, Git, target symlink, caches, and historical experiments were not changed. Root owns retained checkout/evidence.
