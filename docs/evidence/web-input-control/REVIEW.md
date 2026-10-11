# PR18 Control shortcut R2 rereview

Outcome: prior P2 accepted as repaired at source level. No unresolved actionable finding in this targeted diff.

Frozen `crates/nvwa-studio/src/web_input.rs` SHA-256: `30ee884731913c0d65bbaccb9e29b06e5681d82e25a8a95c4337fa9a043cb2d7`, independently matched before and after inspection.
`crates/nvwa-studio/src/lib.rs` remains `4e00f2d61a9f44439616f31c65dfca125908f29a346aca0dcfba000b0f6b5181`.

## Source findings

- Lines94–127 forward H/K/U/W with Control, and A/E/B/F/P/N with macOS Control and no Shift. This matches the pinned egui editing/navigation guards. Command+A and existing command shortcuts remain available. Key pressed/released, repeat and per-event modifiers remain preserved; the browser default is prevented for handled editing events.
- Lines437–477 retain the accepting/composition/isComposing/229 early return before key translation. Ordinary printable keys still use DOM input, and Command+V still allows the browser ClipboardEvent. No composition, paste reducer, canonical Work string or selection algorithm changed.
- Lines277–279 put `initialize_context_os` after context creation and before WriteEguiEvents. Pinned bevy_egui0.42.0 chains InitContexts → ProcessInput → BeginPass, with WriteEguiEvents inside ProcessInput. Its InitContexts ends with applied deferred context creation. Therefore OS metadata is initialized before the first editor pass and before event consumption. Drain has no OS-dependent interpretation, so its lack of an explicit order against this initializer is harmless.
- Lines371–379 use Added<EguiContext>: initial contexts created in PreStartup and later contexts created by the normal InitContexts route are initialized once. The initializer requires the desktop Agent resource. Mobile returns before creating that resource, so this system performs no mobile mutation. Browser code remains wasm-only; native construction remains unchanged. The initialization sets context platform metadata for shared egui behavior, not custom editing logic.
- Tests exercise the actual shared Work helper and egui string/cursor state, including deletion variants, selected-word deletion, Mac cursor navigation, repeat/release, unsupported platform/Shift guards and Command paste. Fixtures use the same configure_web_os helper as production. The tests do not execute the browser-only scheduling system; its wiring was inspected against pinned source.

## Evidence inspected

Actual production-prefix diff was generated with Python difflib against retained `experiments/08-web-ime/control-shortcuts-red-source.rs` (no Git command). It contains key transport/platform initialization changes only. The original inspected source from44b0ec3 provides additional review context. All ten other production/build/asset entries checked against the existing Web manifest matched; no broad claim about unlisted files is made.

Recorded red runner:8 passing /3 failing, including Ctrl+H deletion and Ctrl+A navigation. Recorded green runner:12 passing /0 failing, exit0. Green manifest source hash exactly matches the frozen source; pinned versions are bevy_egui0.42.0 and egui0.36.2. These executions belong to the implementer, not this reviewer. The runner compiles native tests against cached libraries, so it cannot establish browser callbacks or wasm scheduling execution.

NOT-RUN — Reviewer tests, builds, Rust replay, browser callbacks, UI/GPU, clipboard and physical IME. No browser-green claim is made for the rebuilt artifact; root owns that outstanding check. No Git/remote actions or production writes occurred. This report is the only write. Acceptance is limited to resolving the P2 transport defect and the necessary desktop OS metadata wiring; broader browser/mobile/zoom/DPR limits remain unchanged.
