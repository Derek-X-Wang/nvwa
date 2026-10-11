# Issue 2 recovery diagnostic preparation

Checkout verified at `93c77d5d8409a6b142c1aeaa07a50b594bcecb29` on `codex/input-scale-validation`. This worker changed only experiment19 and private `.work/input-scale/issue2/` artifacts. No production defect was reproduced and no product fix was made.

`capture.js` runs passively from a diagnostic wrapper. It captures real DOM event metadata, trust flags, page focus/visibility, active element, proxy ownership/visibility, geometry and scale. It persists the trace to hidden `pre#nvwa-recovery-json` for read-only root extraction. It emits no synthetic events, changes no focus and records no arbitrary text or clipboard contents. `prepare.py` stages a wrapper and observer from the existing bundle; it records bundle hashes and does not build or replace shipped HTML/JS/Wasm.

`check.py` requires actual departure after baseline input, actual return, trusted committed input to one visible active proxy, no intervening canvas click, root-attributed tab activation, and exact observed baseline/final rendered Work values. Save filename can separately corroborate the canonical path: production `platform.rs` derives the anchor filename from `StudioUi.file_path`. The filename is not included inside document JSON. The temporary textarea is not the canonical text, so a trace without rendered Work evidence returns PARTIAL.

Commands actually run:

```sh
python3 experiments/19-input-focus-recovery/prepare.py
node --check experiments/19-input-focus-recovery/capture.js
python3 experiments/19-input-focus-recovery/check.py .work/input-scale/issue2/checker-fixture.json --observation .work/input-scale/issue2/checker-wrong-observation.json
python3 experiments/19-input-focus-recovery/check.py .work/input-scale/issue2/checker-fixture.json --observation .work/input-scale/issue2/checker-good-observation.json
```

Preparation and JS syntax check exited0. Checker fixture with duplicated suffix returned FAIL/exit1. Correct fixture returned PASS/exit0. An import-based fixture check also covered no departure, intervening canvas click, untrusted input and missing canonical observation; each returned PARTIAL. These controls test only the checker. They execute no actual Wasm/adapter/browser input and must never be represented as production regression or browser acceptance evidence. Raw fixture files remain private.

VERIFIED — Passive diagnostic staging, JS syntax and checker failure/incomplete-evidence controls.

NOT-RUN — Real tab-return loop, current-bundle runtime recovery, physical Chinese IME/candidate placement, zoom/DPR acceptance, production-called regression tests. No material reproduced behavior justified a speculative product test/fix. No Cargo/compilation lease was requested or consumed.

Root actions: use README's exact UI sequence; confirm current bundle provenance; copy staged wrapper files into the root-owned served package; operate the actual browser; record baseline/final Work screenshots and Save filename; extract trace; run checker against root observations. Distinct physical candidate and scale checks remain necessary. If the browser API cannot activate and return a tab, preserve that fidelity limit instead of synthesizing visibility/focus events.

Cleanup ownership: root retains/integrates experiment19/private evidence and removes any copied package diagnostics. Reloading/closing the diagnostic tab removes the observer. Worker started no temporary process or server.

## Integrated actual results

Root subsequently ran actual Chrome tab/zoom and physical acceptance. See
[the attributed acceptance packet](../../docs/evidence/input-scale/ACCEPTANCE.md)
for results, exact raw copies, offline commands, review fixes and explicit limits.
Worker-only NOT-RUN statements above describe the preparation stage.
