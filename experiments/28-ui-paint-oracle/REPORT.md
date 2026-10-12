# CPU UI paint-oracle trial — 2026-10-12

**GO to retain this throwaway prototype.** The current production draw seam emits
unambiguous tab-background paint instructions, and an independent literal table
catches a deliberately inverted paint-style branch that existing state tests
accept. Both requested viewports passed normally. Production source is restored.
Adopting permanent coverage is the parent orchestrator's separate decision.

## Scope and independent oracle

Base `de4ddefab91d21dc6f6d4b81a07b0434fa619273`, branch
`codex/ui-paint-oracle-spike`, reused isolated integration checkout. The parent
explicitly authorized this reversible trial over the draft ticket's proposed-only
status. The temporary candidate changed only the existing test module in
`crates/nvwa-studio/src/editor_layout.rs`: fixed RawInput time and two added tests
plus paint observers. No second tab implementation/reference painter was created.

`StudioHarness.frame` calls `draw_editor_ui`, also called by production Bevy
`draw_studio`. Its Shape/Profile controls use the real `craft_ui::Tab` input and
painter. Input clicks reach actual label locations from `FullOutput`; no tab
selection is assigned directly. The oracle does not read `layout.tab` or the
production `selected` variable for expectations.

The test body supplies a literal palette: active RGB17/61/113, inactive149/37/71,
hovered31/173/89 and panel227/211/163. The explicit state table requires:

| Scripted stage | Shape fill | Profile fill | Present inspector | Absent inspector |
| --- | --- | --- | --- | --- |
| Initial | active literal | inactive literal | `Shape parameters` | fixture Profile text |
| Real Profile click | inactive literal | active literal | `Profile: nvwa-original-humanoid-v1` | Shape text |
| Real Shape click | active literal | inactive literal | `Shape parameters` | fixture Profile text |

The test context fixes logical scale1, input time1, explicit Dark theme and
animation time0. Every settled observation releases the primary pointer, moves
it away and removes it. It asserts no pointer-down state or hover position remains.
A matching text label must be unique. The observer then requires exactly one
clipped, non-text100×26 rectangle behind that label in paint order. Tab rectangles
must not overlap. Missing/ambiguous rectangles fail. At most64 nearby rectangles
are retained per tab; each actual observation retained two. Three observations
and two real clicks use eight scripted frames per viewport, under the12-frame cap.

At1280×720, backgrounds were Shape `[1009,61]–[1109,87]` and Profile
`[1117,61]–[1217,87]`. At1024×768, they were Shape `[753,61]–[853,87]` and Profile
`[861,61]–[961,87]`. `green-paint.log` and `restored-green-paint.log` retain exact
fills, bounds, inspector text and frame/invariance summaries for all stages.

The original fixture initializes both undo and redo histories. Full serialized
Work and complete retained `Editor` debug fingerprints stay byte-for-byte equal
before/after each click and each observation. Positive retention counts ensure
both history directions exist. The empty `FullOutput` negative control produces
`actual control label missing: Shape`; its expected-panic test proves missing
output is rejected rather than treated as an empty comparison.

## Exact mutation and verification

`paint-only-mutation.patch` changes only the painter's `if selected` to
`if !selected`. It leaves `Tab::new` selection/input, click handling,
`layout.tab` and inspector branching untouched. The painter's visual-style
choice is exchanged. The independent expected table stays unchanged.

| Stage | Paint tests | Existing production state/control test | Total execution after compile |
| --- | --- | --- | --- |
| Normal candidate |2 passed |1 passed |0.946s |
| Paint-only mutation |1 passed,1 failed |1 passed |0.885s |
| Restored candidate |2 passed |1 passed |0.872s |

The mutation fails specifically with
`paint-oracle fill mismatch viewport=[1280.0 720.0] stage=initial-shape tab=Shape`:
observed inactive`#95_25_47_FF`, expected active`#11_3D_71_FF`.
It is an actual failing CPU paint assertion, not an expected panic.
The separate existing state test remains green at both viewports under the
mutation. Mutation and restoration source hashes are retained in stage records.

Commands compiled only the studio lib-test target with
`CARGO_BUILD_JOBS=1 cargo test -p nvwa-studio --lib --no-run --locked --message-format=json`.
The emitted executable then ran only filters `ui_paint_oracle` and
`actual_studio_layout_controls_preserve_work_history_and_guard_focused_space`,
with `--nocapture --test-threads=1`. Exact commands, executable/source SHA256,
compile duration and exits are stored in each `*-result.json`. Per-stage compile
has a180-second deadline; named test execution is capped at60 seconds total.
No workspace sweep, dependency installation, renderer or GPU process ran.

Final `run-stage.py` requires the exact candidate/mutant source bytes before any
Cargo command, requires one emitted studio test executable, verifies the exact
named tests using executable `--list`, and requires positive execution/result
counts. The independent R2 reviewer replayed the complete wrapper with this strict driver.
The final raw output shows two paint and one state test normally, one named paint
failure under the mutation, and restored green.
After final product restoration, attempting `green` returns exit1 before Cargo
with `candidate source hash mismatch; refusing missing/stale test run`. This
negative guard is saved in `restored-production-refuses-candidate.log/.exit`.
No-match/zero-test success is not accepted. Stage failures propagate to caller.

Two initial harness failures are retained rather than represented as oracle
results: `first-compile-api-error.*` records the pinned egui API's missing
`style_mut`; the fix uses explicit `style_mut_of(Theme::Dark, ...)`.
`first-output-delta-*` records an unhandled texture-delta drop; retained test
outputs now explicitly clear unused texture deltas. Both changes are test-only.
The subsequent normal, mutation and restored results above completed.

## Restoration, artifacts and limits

Original/final product source SHA256:
`da45cb7183d28e80cf8b15d1f08f8aa06463e0c5fe4af2b9067fbf8737878b5c`.
Normal/restored candidate SHA256:
`f607a40684999161e168f402e811c2c1eaef2fd2ac4cd184e47fddab8c2e9d28`.
Mutant SHA256:
`58cdb9e7738fa893b853ddd3f250360ac9d9197258c9defdbe2bddeec3fa8dc5`.

`protected-inputs-before.json` and `protected-inputs-after.json` contain identical
SHA256 values for all50 tracked protected inputs across crates, assets, scripts,
root manifests/lock/toolchain, Web files and licenses. Product file Git diff is
empty. `cleanup.json` records exact source restoration, no changed protected
paths and no remaining owned processes. Cargo lease was released after tests.
The only retained changed paths are under `experiments/28-ui-paint-oracle/`.
The trial and reviewer replay made no Git/remote/settings writes, additional
worker dispatches, network access or dependency changes.

`candidate.patch` is the reviewable test patch against original source;
`paint-only-mutation.patch` applies against that candidate. Full original and
candidate bytes are retained to make exact restoration and replay reviewable.
The independent reviewer executed `reproduce.py` end-to-end: exit0 and exact
restoration of all50 protected inputs. `review-replay.log` and
`review-verification.json` retain that receipt. Replay replaced12 named stage
logs/results; current timings and raw stage evidence above belong to that replay.
`original-artifact-hashes.json` is the earlier author inventory, independently
verified before replay, rather than an inventory of current files. The replaced
author raw stages were not separately retained; initial API/texture-error logs
remain unchanged. `artifact-hashes.json` inventories the current artifacts.

The wrapper refuses a changed baseline cohort and restores source in `finally`.
Root separately injected a first-child command failure after the candidate was
written: exception37 propagated, later commands did not run, and all50 protected
inputs were restored. This checks Python exception recovery; abrupt process or
machine interruption remains NOT-RUN. This local replay used an existing cache;
clean/cold compilation under the180-second experiment deadline is NOT-RUN.
Root owns retention and any future adoption/publication.

VERIFIED — production-called CPU paint oracle and meaningful paint-only mutation
red/state-green/restored-green, both normal viewports, full Work/history invariance
and exact product-input restoration.

NOT-RUN — rasterized screenshots, GPU/framebuffer pixels, original DPR, native
window/OS focus/physical keyboard/clipboard/IME, Bevy character rendering,
browser/Wasm/WebGPU execution, zoom behavior, cross-GPU golden compatibility,
hosted execution and performance acceptance. This prototype cannot establish
those claims from egui paint instructions.
