# Browser duplicate commit diagnosis (checkpoint 586552)

Coordinator observation: one installed diagnostic-button replay dispatches exactly four DOM events (compositionstart/update/end and final noncomposing input), yet the rendered Work field gains `女娲女娲`. A second replay also adds two copies. Preserved root-owned screenshot: `docs/evidence/web-input/duplicate-commit-before-fix.jpg`. This is browser callback replay, not physical IME acceptance. The committed-only source remains unchanged at 58655287/4e00f2d6 during this diagnosis.

The initial pure reducer/egui tests used literal final `inputType="insertFromComposition"`. They validate that event payload contract, not the browser's constructor normalization, actual listener count, or callback scheduling.

## Source-supported boundaries

- Current adapter TextDelivery.input checks an allowlist of composition/paste input types before suppressing matching data. An actual final event with matching data but unrecognized/empty type emits Text again.
- Current update cancels on target change or `ime.should_interrupt_composition`, which clears both composing state and followup marker. An intervening cancellation can destroy dedupe. This source behavior is a robustness risk; it is not yet proven to occur between the coordinator's four synchronous callbacks.
- Pinned `egui-0.36.2/src/widgets/text_edit/builder.rs:960` initializes `should_interrupt_composition=false`; `context.rs:2688–2691` sets it from Memory's requested interrupt. `memory/mod.rs:917–921` request_focus sets that request. Selection cursor purpose alone does not set it every frame.
- Winit `platform_impl/web/event_loop/proxy.rs:18–21` wakes its runner; `async/waker.rs:45–49` invokes the handler with local=true. `event_loop/runner.rs:454–480` normally schedules local user events on the next microtask when the runner is available. This source does not prove Bevy updates synchronously between externally dispatched DOM events.
- `bevy_egui-0.42.0/src/lib.rs:1882–1899` takes context input and executes ctx.run_ui; egui `context.rs:855` takes input for each pass; `data/input/raw_input.rs:137` moves events out. Repeated layout passes do not automatically reuse the same RawInput events.

## Actual library differentials

`python3 experiments/08-web-ime/run_rework_regressions.py` now includes two additional experiment-only controls, leaving production unchanged. A Studio-shaped Panel::top plus horizontal toolbar receives exactly one reducer ImeCommit and appends it once; both its warmup and commit output are one pass with interrupt=false. An explicitly requested second discarded render pass also appends one commit exactly once. Actual log: `browser-duplicate-library-differential.txt`; exact commands/compiler/library/source metadata: corresponding `-artifacts.json`. All 12 assertions pass.

These controls reduce support for ordinary toolbar layout or egui multipass as the duplicate source. They do not execute the wasm callbacks and cannot rule out live scheduling or listener duplication.

## Coordinator's decisive actual callback observation

Root extended the installed diagnostic trace to capture event type, target, composing flag and `inputType`, without user text or clipboard contents. The original `new InputEvent(... inputType:'insertFromComposition')` actually produces **empty inputType** in this browser. [Actual trace](../../docs/evidence/web-input/duplicate-input-type.jpg) and [unsupported constructor source](../../docs/evidence/web-input/browser-probe-unsupported.js) are retained. Commit-only delivery adds exactly one copy. Thus the earlier pure tests' literal type did not match the real constructor result; the diagnostic sent an unsupported final-event type.

Root corrected the diagnostic to the supported `insertText` type. Actual trace confirms `inputType=insertText`; all four installed callbacks now append exactly one `女娲` on the **unchanged production Wasm/source**. [Passing replay](../../docs/evidence/web-input/after-fix-composition.jpg). No cause-specific production workaround, listener rewrite or rollback was added to satisfy the incorrect constructor expectation. Empty/unrecognized input types on other real engines remain unverified; the interruption branch was not proven to cause this observation.

Derek subsequently reports **“全部正常”** for the repaired production page's physical candidates/Space, Command+A/V and app-switch editing. [Attribution](../../docs/evidence/web-input/WEB-HAND-TEST.md) keeps this distinct from synthetic callback checks.

VERIFIED — Source boundaries and real-egui toolbar/multipass differentials; 12-test suite exit0.

VERIFIED (coordinator/user-attributed) — Actual constructor normalization and supported-type callback control; Derek's bounded physical retest passed. The worker itself did not operate the browser or physical IME.
