# Targeted R2 acceptance — committed-only checkpoint 58655287

**Accepted for the revised source-level contract. No unresolved actionable findings in the targeted rereview.** Browser callback acceptance and physical Chinese IME acceptance remain separate gates owned by root.

Verified dispatch hashes for frozen web_input.rs `58655287ca544b330ecb4f1e55a36d9fc23caaee452d2e3ea3df628c39e68824`, lib.rs `4e00f2d61a9f44439616f31c65dfca125908f29a346aca0dcfba000b0f6b5181`, Cargo.toml `7532429f4e3ebf34bea8bfb5a52c99ed02bae6714ac33a59fcf897252bb74050`, and rework-regressions.rs `c9110cf5b70ca6fe3bfc58f9bae5f71692f622d5f705d0c8149c5b2873fa3a69`.

## Reviewed outcome

- `TextDelivery::preedit` emits no egui events (`web_input.rs:16–20`); composition input is suppressed (`31–34`); cancellation emits no events (`60–63`). No uncommitted browser composition can enter the canonical Work string through these paths. The canvas intentionally displays committed text; the browser/OS owns the unfinished composition and candidate UI.
- Nonempty compositionend produces one `ImeEvent::Commit` (`22–29`) and immediate matching final input is deduplicated (`35–45`). Empty compositionend changes no canonical text or selection. Pinned egui 0.36.2 handles a nonempty Commit without requiring preceding Preedit, as exercised by the real-egui regressions.
- The three accepted P1 classes are removed at their cause: abandoned preedit never needs old-target cleanup; batched commit plus new preedit retains only the preceding commit; selecting existing text before new preedit no longer loses that selection or canonical text on cancellation. All CompositionSnapshot, rebase, rollback, and finish_work_text hooks are absent from the frozen source.
- Work's Wasm helper now adds only a stable ID to the original TextEdit (`74–78`). Native draw_work_path still executes the original TextEdit expression. The shared Work string, command/document schema, and existing Web Player UI boundary are unchanged.
- Paste remains `Event::Paste` (`54–57`) with followup deduplication. Pinned single-line normalization is correctly tested as `one\r\ntwo\nthree` → `one  two three`.
- The browser listener/focus/clipboard code is unchanged from the prior ordered checkpoint. Existing protections remain: Work-only target selection, per-key modifiers, browser-owned paste delivery, target check before queue dispatch, internal focus preservation, no external-control focus stealing, and external DOM clipboard queue filtering. This is a source comparison, not a claim of browser execution.

## Evidence and limits

Inspected current `experiments/08-web-ime/rework-output.txt`: exact standalone rustc command links the pinned existing bevy_egui rlib; 10 tests pass, zero fail/ignored, exit 0. Tests now feed actual production reducer emissions into real egui. They cover canceled composition/cursor preservation, confirmed replacement, followup deduplication, repeated composition, append batching, select-all batching, intermediate commit plus select-all plus canceled preedit, old-target focus transfer, and single-line paste. These are implementer-run results inspected by the reviewer; the reviewer did not independently rerun them.

PARTIAL — source-level targeted R2 accepted; actual DOM callback sequencing, focus recovery, clipboard behavior, candidate positioning, scene shortcuts under browser input, and physical Chinese IME remain unverified by this reviewer. No browser, Cargo/GPU, clipboard access, production edits, or historical evidence changes. Only this report was created; root owns retention.
