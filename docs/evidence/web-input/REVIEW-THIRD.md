# Targeted R2 — ordered checkpoint 4db492ca

Frozen SHA-256 matches dispatch for web_input.rs `4db492ca19e7755a8849a1dd8a8146351afa57d37d718a95ac22e3a2462b24b5`; lib.rs, Cargo.toml, and rework-regressions.rs also match their unchanged dispatch hashes.

## Remaining P1: rebase can delete selected canonical text

`web_input.rs:107–114` treats every pressed key as finalization. `151–165` then rebuilds the preceding canonical string by deleting the latest composing range from the final string. This cannot recover canonical text that the new composition replaced.

Concrete sequence using the existing real-egui fixture:

1. Start with committed `path` and focused Work field.
2. Deliver Command+A and `Preedit("nv")` in one frame.
3. egui selects `path` and replaces it with `nv`.
4. The key sets `finalized`; subsequent preedit sets `rebase`. The new rollback baseline is `nv` minus the composing range, i.e. the empty string.
5. Surrender focus in the next frame. Cleanup restores empty text instead of the committed `path`.

This violates the same batched cancellation invariant and uses a required Command+A interaction. Merely excluding selection keys from finalization does not cover an earlier real commit followed by selection and new preedit in the same frame: `Commit("女娲"), Command+A, Preedit("hao")` must retain the intermediate committed value after abandoning `hao`. Capture the actual canonical value before the final composition's replacement rather than inferring it solely from the final text and composing range. Add both selected-replacement cases to the real-egui regressions. Root was notified before this report. Static source proof; new reproducer execution is delegated to the implementer/root.

## Verified review evidence

- The original simple batched `Commit("女娲")` + `Preedit("hao")` failure is fixed for the append case. Inspected preserved `batched-composition-before-fix.txt`: 10 passed, 1 failed, actual `path女娲hao` versus expected `path女娲`, exit 101. Inspected current `rework-output.txt`: 11 passed, zero failed/ignored, exit 0, including that exact regression.
- Earlier single-composition focus rollback, cursor restoration, completed-commit preservation, different externally supplied text preservation, and Paste regressions remain in the passing suite.
- Paste remains `Event::Paste`; exact single-line normalization remains `one\r\ntwo\nthree` → `one  two three`.
- lib.rs is unchanged from the prior rereview: native helper equality, Work-only Wasm binding, and cleanup before path capture remain as previously reviewed.

PARTIAL — targeted source review and inspection of execution logs only. No browser/physical IME, Cargo, GPU, clipboard access, production edits, or independent test execution by reviewer. No initial logs changed. Only this report created; root owns retention. The selected replacement finding prevents acceptance of this checkpoint.
