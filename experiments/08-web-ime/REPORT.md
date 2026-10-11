# Desktop Web Chinese input boundary

Current accepted adapter sends confirmed commit only. Browser/OS IME owns uncommitted preedit; the canvas displays committed text. All inline-preview snapshots and canonical rollback logic below are historical rejected checkpoints. The final committed-only section at the end records the current source and green tests.

The downstream pinned Bevy-to-egui translator and focused TextEdit accept `女娲`. The pinned desktop Web boundary lacks the helper's DOM composition callbacks and activation path. This source finding is consistent with the coordinator's actual installed-callback browser replay and the user's physical failure. The worker did not perform browser or physical input.

## Feedback seam and limits

The executable invokes the real `write_modifiers_keys_state_system`, `write_keyboard_input_messages_system`, and `write_ime_messages_system` in a Bevy World/Schedule. Their emitted egui events go to a real focused TextEdit. It supplies synthetic Bevy messages; it does not execute cfg(wasm32) DOM callbacks in native cached rlibs.

Already-run red command:

```sh
python3 experiments/08-web-ime/run_probe.py --target-dir target --red-only
```

Actual `red-output.txt`: `FAIL synthetic_missing_commit_requires_女娲: expected="女娲" actual="nv"`; exit 1. This intentionally omits Commit and proves downstream sensitivity to that loss. It is not a captured Web trace and is not advertised as reproduction of physical browser delivery.

After that run, ranked hypotheses were sent to the coordinator before the control probes: (1) desktop helper activation/listener gate; (2) missing Winit composition route; (3) widget focus lost before Commit; (4) committed text arrives only in `KeyboardInput.text`. Predictions compared activation/source path, complete Commit, retained versus surrendered focus, and logical text versus text-only messages.

The coordinator subsequently performed the actual installed-callback red seam: on the pinned published revision-6 Web path with the Work field focused, a source-defined button dispatched compositionstart, update(data `nv`), end(data `女娲`), and noncomposing input(insertFromComposition) on `egui_text_agent`. The real rendered Work path remained `works/exchanged.nvwa.json`; DOM remained active `nvwa`, helper hidden. Preserved coordinator-owned evidence: `docs/evidence/web-input/browser-probe.js`, `before-fix-composition.jpg`, and `ACCEPTANCE.md`; preparation command is `python3 scripts/prepare-web-input-probe.py`. This is installed browser callback replay, still not physical IME.

## Actual downstream results

```sh
python3 experiments/08-web-ime/run_probe.py --target-dir target
```

Final `run-output.txt` ends `EXIT 0`. The diagnostic missing-Commit assertion is intentionally red within this suite; the suite requires that sensitivity and separately checks all expected outputs.

| Synthetic real-library input | Actual final text | Result |
| --- | --- | --- |
| ASCII logical Character `a` | `a` | PASS |
| Unicode logical Character `女娲` | `女娲` | PASS |
| Enabled → Preedit `nv` → Commit `女娲` → Disabled | `女娲` | PASS |
| Same composition without Commit | `nv` | Required symptom assertion is red |
| Unidentified logical key; only KeyboardInput.text=`女娲` | empty | PASS expected ignored-text behavior |
| Commit followed by ordinary Unicode text | `女娲女娲` | PASS expected duplication behavior |
| Explicitly surrender widget focus before Commit | `nv` | PASS expected lost-commit behavior |
| RawInput.focused=false but retain widget focus/selection | `女娲` | PASS; selection also remains intact |
| Space after Commit, widget still focused | `女娲 ` | PASS; egui retains keyboard interest |

Enabled/Disabled translate to no event in this version; Preedit/Commit carry the actual composition. Production playback itself was not executed by this harness.

## Exact source path

Cached source root: `/Users/derekxwang/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/`.

- `bevy_egui-0.42.0/src/text_agent.rs:181,185–394`: helper starts hidden; input/composition/keyboard callbacks are installed only under `if let Some(true) = is_mobile()`. The mobile UA predicate is lines 461–466. Composition update sends Preedit at 239–250; end sends Commit at 265–274. There is no corresponding desktop listener installation in this function.
- `bevy_egui-0.42.0/src/input.rs:1165–1170`: activation calls `update_text_agent` from touch-ended handling. This is not desktop mouse text-focus activation. `text_agent.rs:400–445` reveals/focuses or blurs/hides the element when explicitly called.
- `winit-0.30.13/src/platform_impl/web/web_sys/canvas.rs:272–315`: canvas-bound keyup/keydown route. Searching the exact Web backend found no compositionstart/update/end listener. `platform_impl/web/window.rs:328–339`: IME cursor, allowed and purpose methods are no-ops.
- `bevy_winit-0.19.1/src/state.rs:264–282,387–403`: ordinary KeyboardInput and any supplied Winit IME events can be translated to Bevy. This does not create missing Web DOM events.
- `bevy_egui-0.42.0/src/input.rs:699–704,773–835`: logical Character produces Text; IME Preedit/Commit produce egui IME events. KeyboardInput.text is not read in the keyboard translator.
- Canvas blur and egui focus distinction are traced and tested in the separate `ADAPTER-CONTRACT.md`. A canvas blur is not proof that egui cleared the text selection.

Correct missing path: desktop editable-text focus → focusable DOM input → compositionupdate/end or committed input → context-owned EguiInputEvent queue → focused TextEdit. The existing native path succeeds downstream; the desktop helper currently cannot supply the middle DOM→event segment.

## Version evidence and errors

`linked-artifacts.json` records the exact rustc command, compiler version, coherent Cargo fingerprints, artifact SHA-256 hashes, and versions checked from cached dependency paths: bevy_egui 0.42.0; bevy_ecs/bevy_input/bevy_window 0.19.1; egui 0.36.2. Only this tiny Rust probe is compiled; no Cargo dependency rebuild or network request occurs. `/probe` is ignored locally.

`compile-first-attempt.txt` retains the initial tuple-constructor error for `Key::Unidentified`. It was corrected to `Key::Unidentified(NativeKey::Unidentified)` without changing the expected assertion.

`ADAPTER-CONTRACT.md` proposes the minimal production boundary and lists duplicate text, navigation/Command/paste, internal/external focus, candidate rectangle, and DOM lifecycle requirements. The initial experiment made no production edit. The coordinator subsequently authorized the bounded implementation checkpoint below.

VERIFIED — Real pinned-library ASCII/Unicode/IME and focus/duplicate/Space controls; suite exit 0; synthetic missing-Commit symptom assertion exit 1.

PARTIAL — Coordinator reports a failing installed-callback browser replay and exact live focus/hidden state; source identifies the desktop wiring gap. Worker did not independently operate that browser.

NOT-RUN — Complete wasm library execution inside this native harness, physical Chinese IME retest, physical clipboard and candidate positioning. User's physical report is evidence of failure, not worker acceptance evidence.

## Subsequent implementation checkpoint

After the diagnosis, the coordinator authorized a desktop-only Rust/wasm DOM adapter in `crates/nvwa-studio/src/web_input.rs`, registered by two cfg-gated additions in `lib.rs`. It owns a transparent `textarea#nvwa_text_input` and delivers composition/input/control keys through a context-and-widget-bound EguiInputEvent queue. It requests Winit WakeUp, positions the proxy from the actual egui cursor rectangle/canvas scaling, preserves context-local focus during internal DOM transfer, and removes its listeners/element on Drop. Mobile routing remains upstream-owned.

The module contains reducer and real-egui regressions for committed Unicode, canceled preedit, followup-input dedupe, repeated composition, paste dedupe, ordinary-text ownership and per-event command modifiers. Root owns all Cargo feature/lock changes, builds, browser callback replay, GUI, acceptance, and publication.

The coordinator's first workspace run passed 63 tests, zero failed/ignored (`docs/evidence/web-input/tests-first.log`), and native strict clippy/fmt passed. First strict Wasm clippy reported seven warnings-as-errors, preserved in `clippy-wasm-first.log`: deprecated insertion API plus nested-if style. These were repaired without allowances. The subsequent strict Wasm run completed successfully (`clippy-wasm.log`). Post-repair module SHA-256: `98689ffea662b6632de41774f94c4b55f32ee57c56c7ee46ac2466dee11d366e`. No physical acceptance or repaired browser runtime is inferred from those build gates; the coordinator owns their separate evidence.

## Accepted rework checkpoint

The independent review identified two defects in the first adapter: paste emitted Text instead of Paste, and cancellation queued after widget focus changed could be dropped while egui's temporary preedit remained in the canonical path. The already-run real-egui red regression is preserved unchanged in `rework-before-fix.txt`: four tests passed, two failed, exit 101. The focus test drew two real widgets, moved focus to the new widget, and applied the production drain predicate, which dropped the old target's cancel. The old path remained `pathnv`, expected `path`. This is a library/focus replay, not browser or physical IME acceptance.

The original paste assertion expected removal of line breaks, but the owning pinned implementation (`egui-0.36.2/src/widgets/text_edit/builder.rs:1130–1139`) replaces **each** CR/LF with a space. The preserved first red actual value contained literal line breaks, proving the substantive defect. A subsequent fixed adapter run reached `one  two three` but failed the mistaken `onetwothree` exact expectation; that error is preserved as `rework-paste-expectation-error.txt`. The final assertion requires the exact source-defined `one  two three` and no CR/LF; it has not been relaxed.

`rework-wrapper-compile-error.txt` preserves the tiny harness's initial module-scope error and production CharIndex/usize compile error. The runner now wraps the unmodified production source in a module, and production clamps with typed `egui::text::CharIndex`. The coordinator separately preserved its interrupted first release Web compile at `docs/evidence/web-input/build-web-first.log`.

The coordinator authorized a small Work-field hook rather than an ineffective late event. `work_text_edit` (`web_input.rs:85`) captures only an active uncommitted composition's baseline String and an isolated cursor/undo state. `finish_work_text` (`:141`) rolls it back only after this widget loses focus and the same String still equals that session's last preview; a different loaded path or ordinary/committed edit is preserved. Cursor endpoints are clamped at `:157`. Studio calls cleanup before Open/Save captures its one canonical `StudioUi.file_path` (`lib.rs:760`). Native uses the original TextEdit draw. Web Player still has its existing UI, without a new path field.

Desktop proxy activation is explicitly limited to the Work field (`web_input.rs:639`); numeric slider text keeps its existing canvas keyboard route and is not advertised as fixed Chinese composition. Paste uses Event::Paste (`:51`). An external page blur retains the transparent proxy element for natural focus recovery (`:674–684`), without forcing focus. The upstream document-wide clipboard queue is discarded while another DOM control owns focus (`:576`). These wasm callback/focus changes still require the coordinator's actual browser checks.

Reproducible tiny command:

```sh
python3 experiments/08-web-ime/run_rework_regressions.py
```

Actual final `rework-output.txt`: **10 passed, 0 failed, 0 ignored; exit 0**. Eight tests live in the production module, including real Work TextEdit/focus/cursor/commit/ordinary/new-path and Command+A multiline-paste cases. Two independent experiment tests retain the old-target dropped-cancel seam and singleline clipboard assertions. `rework-linked-artifacts.json` records the exact compiler/version, compile/run commands, production source hashes and freshly read coherent library artifact hashes. No Cargo dependency build or network request was made. `/rework-tests` and `/rework-source.rs` are ignored.

Stable production hashes: web_input.rs `cc263794e446ab466da8f1c0d9f010279da2442cb6115b9cf9d93ebcbcb645d2`; lib.rs `8dca0482f4ef87c94376b6199e11a7ae7215511386ac3da7fb8ee04a22315c7e`. Earlier 63-test/strict gate results above are historical and do not validate this later rework.

VERIFIED — Tiny real-library rework suite exit 0, all 10 meaningful assertions pass; first failure logs retained.

NOT-RUN — Current rework workspace/strict/native/Wasm release gates and browser/physical acceptance are coordinator-owned and pending at this checkpoint.

## Ordered composition rework

A targeted independent rereview found that frame-wide `any(Commit/Text/Paste/Key)` incorrectly finalized a later preedit in the same callback batch. The exact new regression uses an existing `nv` preedit, then concatenates actual reducer `end("女娲")` and new-session `preedit("hao")` into one Work frame. The next frame surrenders focus. Before the fix the canonical path remained `path女娲hao`, required `path女娲`; `batched-composition-before-fix.txt` preserves this first red (10 passed, 1 failed, exit 101). Its exact source/compiler/rlib/command metadata is separately retained in `batched-composition-before-fix-artifacts.json`.

The narrow fix follows event order (`web_input.rs:91–117`). A terminal followed by new preedit rebases the snapshot using the real TextEdit output's selected composing range and public `TextBuffer` character-range methods (`:150–172`). The baseline removes only the latest uncommitted region and retains intermediate committed/ordinary text. It keeps the isolated pre-session undo state, feeds the committed baseline, and restores its cursor when canceled. Pinned egui's actual Preedit/Commit handling and composing cursor range are defined in `egui-0.36.2/src/widgets/text_edit/builder.rs:1250–1398`; singleline CR/LF IME payloads are ignored consistently. The Copy cursor assignment (`web_input.rs:127`) fixes the strict `clone_on_copy` failure without an allowance.

Same tiny command now passes **11 tests, 0 failed, 0 ignored, exit 0**. Existing meaningful assertions remain. `rework-output.txt` and `rework-linked-artifacts.json` describe the final run; initial failure evidence is not overwritten. Final module hash: `4db492ca19e7755a8849a1dd8a8146351afa57d37d718a95ac22e3a2462b24b5`; lib.rs is unchanged at `8dca0482f4ef87c94376b6199e11a7ae7215511386ac3da7fb8ee04a22315c7e`. These replace the earlier checkpoint hashes, not its preserved historical results.

VERIFIED — Exact real-library batched-commit/new-preedit assertion red before fix and green after; final suite 11 passed.

NOT-RUN — Fresh strict/release/browser gates and physical IME acceptance remain coordinator-owned. The coordinator relayed that the user's physical failure showed no candidate box; this worker has not observed or accepted physical candidate rendering.

## Final committed-only adapter checkpoint

The second event-order rereview found another canonical text-loss defect: Cmd+A followed by new preedit could make the reconstructed rollback baseline delete the original selection; a preceding confirmed commit was also lost in that sequence. Both exact outcome regressions were run red before any routing change (`selection-composition-before-fix.txt`, 11 passed/2 failed). The coordinator authorized removing inline preview delivery entirely.

Final production `TextDelivery::preedit` (`web_input.rs:16`) retains composing state but emits no egui event. Browser textarea and OS candidate UI own uncommitted text. Nonempty `end` (`:22`) emits one confirmed ImeCommit and tracks only its immediate duplicate final input. `cancel` (`:60`) emits no canonical text event. No CompositionSnapshot, range reconstruction, finish_work_text or lib cleanup hook remains. The Work helper (`:74`, lib.rs:889) only renders the original singleline TextEdit with a stable target ID. The canvas displays committed text; no inline egui preedit display is claimed. The canonical Work String and shared Rust editing/command path remain unchanged. Candidate/composing-key/Space suppression, target binding, Paste semantics, per-event modifiers, focus/error/lifecycle handling remain in the DOM adapter.

The frozen rejected adapter and corresponding lib are preserved under `rejected-preview/` at exact 4db/8d hashes. Its bounded runnable probe appends the omitted selection regressions without modifying frozen source:

```sh
python3 experiments/08-web-ime/rejected-preview/run_probe.py
```

Actual expected-red exit101: **9 frozen tests pass; 2 new selection assertions fail**. The original selected path and intermediate committed path both become empty. `rejected-preview/run-output.txt` and `linked-artifacts.json` preserve exact commands, source hashes, compiler/version and freshly hashed coherent rlibs. Its README explains why the coordinator's prior 68-test result did not cover this defect. Earlier raw-egui preview mutation controls remain isolated historical risk evidence; no failure is silently dropped or advertised as fixed by weakening canonical outcome requirements.

The final actual adapter-event suite is:

```sh
python3 experiments/08-web-ime/run_rework_regressions.py
```

Actual final result: **10 passed, 0 failed, 0 ignored, exit0**. Eight production tests and two independent experiment tests verify canceled preedit leaves canonical path/cursor unchanged; commit plus new preedit/cancel preserves the intermediate commit; select-all plus canceled preedit retains original text and selection; commit/select-all/new preedit/cancel retains committed text and selection; confirmed selected text replaces exactly once; ordinary Space retains keyboard interest; Paste normalizes CR/LF and deduplicates followup; composing input is suppressed; repeated commits and per-event command modifiers work. Assertions now exercise the actual committed-only production reducer emissions rather than requiring obsolete inline-preview events.

A first tiny compile used an obsolete keyboard-interest API name; `committed-only-first-compile-error.txt` preserves the error. It was corrected to pinned `egui_wants_keyboard_input` without changing the assertion. Final metadata is `rework-linked-artifacts.json`. Stable final production hashes: web_input.rs `58655287ca544b330ecb4f1e55a36d9fc23caaee452d2e3ea3df628c39e68824`; lib.rs `4e00f2d61a9f44439616f31c65dfca125908f29a346aca0dcfba000b0f6b5181`.

VERIFIED — Rejected exact-source selection red is reproducible; final committed-only actual reducer/real-egui suite passes all 10 tests.

NOT-RUN — Final fresh strict/release/browser/physical IME and candidate positioning gates remain coordinator-owned. The prior 4db native/Web release artifacts are historical, not this final checkpoint.

## Coordinator integration and acceptance

The initial committed-only suite above had10 assertions. Two experiment-only toolbar/multipass controls were later added without changing production source; the current runner and root rerun pass **12 assertions**. Root's final workspace result is **67 passed, zero failed/ignored**, with fmt, strict native/Wasm clippy, both release builds, native packaging and actual native/Web runs each successful. The native smoke loads the newly saved Web Unicode file and exits0; complete saved JSON equals baseline revision6.

The first live repaired callback diagnostic used an unsupported constructor inputType that this browser normalized to empty. The preserved failure and decisive supported-type control are in [BROWSER-DEDUPE-DIAGNOSIS](BROWSER-DEDUPE-DIAGNOSIS.md). Corrected actual four-callback delivery appends exactly one Chinese commit on unchanged production code. Root also observed cancellation/selection preservation, actual Command+A/V, external DOM clipboard isolation, ordinary Space playback protection and Unicode GUI Save/Open.

Derek then physically tested the updated production preview and replied **“全部正常”** for candidates/Space, Command+A/V and cross-app continued input. [Current acceptance](../../docs/evidence/web-input/ACCEPTANCE.md), [human attribution](../../docs/evidence/web-input/WEB-HAND-TEST.md), [independent final review](../../docs/evidence/web-input/REVIEW.md) and [source/artifact manifest](../../docs/evidence/web-input/build-manifest.json) separate these results from the worker's narrower tests. Current performance, browser zoom/DPR, mobile and other browser/OS coverage remain unverified. PR #18 is pending merge; no shared dependency version or Cargo.lock changed.

PARTIAL — Adopt the committed-only desktop Work adapter for the verified native/current-Web scope. Physical repaired Web checks have user acceptance. Preserve rejected preview/rollback source and failed diagnostics; additional platform and performance coverage remains open.
