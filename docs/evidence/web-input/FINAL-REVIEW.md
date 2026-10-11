# PR18 independent final review

Reviewed head: `44b0ec3b129a1e19f5c8c3598f88de1e50e4e826`.
Base: `96c00dedf9a4a74038edb7abf20d99d89871ae6b`.
Comparison: `git diff 96c00dedf9a4a74038edb7abf20d99d89871ae6b...HEAD`.
Head matched both before and after inspection. Primary checkout started clean. This report is the only write.

## Actionable finding

**P2 — Forward existing Control editing shortcuts through the desktop proxy.**
Location: `crates/nvwa-studio/src/web_input.rs:101–107` (the key whitelist and fallthrough).

Once the Work field focuses the sibling textarea, keyboard events no longer reach the canvas/Winit keyboard route. `key_event` returns None for Ctrl+H/K/U/W, and for macOS Ctrl+A/E/B/F/P/N. The input callback only forwards inserted text, so browser editing of the temporary empty textarea cannot implement these operations on the canonical Work string. This silently removes editing behavior supported by the shared editor. The pinned egui0.36.2 `widgets/text_edit/builder.rs:1431–1454` explicitly handles Control+H/K/U/W, while `text_selection/cursor_range.rs:150–152,265–272` handles the macOS navigation forms. Before the proxy, bevy_egui's generic key conversion forwarded such keys (`input.rs:717–739`).

Violated invariant: the adapter is transport only, with ordinary editing/selection retained in the shared egui editor; the adapter contract also requires forwarding supported editor shortcuts.

Focused reproduction: in desktop macOS Web Studio, enter `abc` in Work, put the cursor at its end, then press Ctrl+H. Expected shared-egui result: `ab`. Actual source path: `key_event("h", true, false, Modifiers { ctrl: true, ... })` returns None; no canonical delete event is queued. For Ctrl+K, place the cursor after `a`; expected `a`, but no canonical key event is queued. These are source-derived reproductions, not claimed physical/browser executions. Forward the supported control-key variants with their per-event modifiers and prevent the corresponding temporary-textarea default; retain DOM input ownership for ordinary printable text.

## Bounded accepted scope

- Font installation runs for newly added egui contexts before BeginPass. Both font families append the same embedded bytes after default fonts. The supplied native/Web package scripts include OFL, notice, and provenance. Documented supplementary-Han limits remain explicit.
- Native TextEdit construction remains the same expression through the small helper. Web Player gains no Work input. The adapter's mobile exclusion list matches the pinned upstream mobile list; mobile acceptance is not established.
- Unfinished composition produces no canonical event. Nonempty composition end produces one egui commit; immediate recognized matching input is deduplicated. Selection and undo remain egui-owned; no preview rollback algorithm remains in production.
- Paste enters egui as Paste, queued events retain widget/context identity, and delivery checks memory focus. DOM clipboard listeners stop propagation for the owned textarea; external controls have their upstream clipboard queue discarded.
- No other actionable issue established within this inspection. This is not merge authorization.

## Verification and limits

Executed read-only source inspection, exact-head checks, source/font hash checks, and issue1/19 reads. All 12 checked-in manifest entries checked (excluding target/dist artifacts) matched their SHA-256 values. Font binary and OFL hashes separately matched provenance. Recorded workspace test totals sum to67, and final native/Wasm clippy plus native build logs contain successful completion; these are prior-run records, not reviewer executions.

Browser callback and user physical acceptance are separately attributed in ACCEPTANCE.md and WEB-HAND-TEST.md. I did not read prior review files. The acceptance overview contains references to prior conclusions; those conclusions were not used as evidence for this finding.

NOT-RUN — Reviewer Cargo/tests, native/Web execution, GPU/UI, physical IME, clipboard, zoom/DPR and extra-browser/mobile checks. No user input or clipboard was observed. Remote font origin/license bytes were not independently downloaded; current local hashes/provenance and packaging were inspected. Build artifact hashes and packaging outputs were not rerun or rehashed. Browser-specific final-input variants and focus ordering beyond recorded acceptance remain bounded, not inferred to pass.
