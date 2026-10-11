# Desktop Web Chinese input

Issue [19](https://github.com/Derek-X-Wang/nvwa/issues/19), part of input acceptance [2](https://github.com/Derek-X-Wang/nvwa/issues/2). This record separates physical user results, browser callback replay, Rust replay, builds, actual startup and performance.

## Observed failure

Derek reports “无法输入中文” during the Web hand-test, and then clarifies “没有候选框”. The same user's four native input checks passed earlier; [native hand-test attribution](../input-fonts/NATIVE-HAND-TEST.md). The exact Web input-method name was not supplied.

Original Web package: the [font-build manifest](../input-fonts/build-manifest.json), source checkpoint `712a02998189877f8a94ca28a680830469d8d2ef`. Hardware: Apple M2 Pro, 16 GiB, macOS27.0.1. The current Codex in-app Browser engine/DPR were not established. Earlier engine observations do not establish the current hand-test environment.

| Check on original package | Result | Limit |
| --- | --- | --- |
| Physical Chinese input in Work field | FAIL, reported by Derek; no candidate box appears | No OS event trace; exact input method unknown |
| Desktop text target after actual Work-field click | FAIL: canvas remains active, upstream text agent stays hidden | Direct read-only DOM assertion and actual GUI click |
| Composition callback replay on installed upstream agent | FAIL: four composition/input DOM events, no Chinese in real Rust Work field | [Screenshot](before-fix-composition.jpg); synthetic DOM events exercise installed callbacks, not physical IME |
| Direct Unicode tool input in ordinary DOM field | PASS: exactly `女娲` | [Control](before-fix-dom-control.jpg); tool-generated input, not physical IME |
| Direct Unicode tool input in canvas Work field | PARTIAL: only `女` appeared | Separate adapter observation; not substituted for the user's physical report |

The installed `bevy_egui0.42.0` text agent creates a hidden input but installs input/composition callbacks inside a mobile-only condition. Activation follows touch events. Pinned `winit0.30.13` Web IME setters are no-ops. The [isolated Rust replay](../../../experiments/08-web-ime/REPORT.md) distinguishes the missing desktop callback path from a correct downstream Chinese commit.

## Reproduce the browser callback check

Build the package with the handoff commands, serve the loopback preview, then prepare its separate diagnostic page:

```sh
python3 scripts/prepare-web-input-probe.py
python3 scripts/serve-web.py --port 9201
```

Reuse an already-running9201 server instead of starting another. Open the printed `ime-debug.html?work=works/exchanged.nvwa.json` URL. It imports the current package's identical Wasm and assets, without replacing its production index. Click the top Work field, press End, then click **Replay composition 女娲**. The repaired path must gain exactly one `女娲`. The diagnostic button emits composition start/update/end and the following input event, with a task-owned sentinel. Its trace captures event classes/targets/counts only; it never reads clipboard contents. The ordinary DOM control is a differential input target.

The prepared probe files are disposable and are not part of the production entry point. Callback success does not establish real candidate selection, browser compatibility or physical input acceptance.

## Repair and actual verification

The desktop-only Rust/wasm adapter focuses a transparent browser textarea at the Work caret. Browser/OS composition owns unfinished text; the canvas field shows committed text only. Confirmed text enters the existing egui editor once. Selection, ordinary editing, undo and the canonical Work path remain in egui. Mobile still uses the upstream helper and is unverified. The shared command/document schema and native editor behavior are unchanged.

Independent R2 reviews first found focus rollback and Paste defects, then two batched composition/selection defects in the inline-preview approach. Those failures remain in the experiment, including a runnable rejected snapshot. The final adapter removes preview mutation and the rollback algorithm. [Final source review](REVIEW.md) accepts that boundary; [earlier reviews](REVIEW-FIRST.md), [second](REVIEW-SECOND.md) and [third](REVIEW-THIRD.md) preserve why the design changed.

| Check on final source/package | Actual result | Evidence / limit |
| --- | --- | --- |
| Workspace tests, fmt, strict native/Wasm clippy | PASS: 67 tests; zero failed/ignored; all commands exit0 | `tests-final.log`, `fmt-final.log`, `clippy-native-final.log`, `clippy-wasm-final.log` |
| Final native and Web release builds, native packaging | PASS, each exit0 | `build-native-final.log`, `build-web-final.log`, `package-native-final.log`; [source/artifact manifest](build-manifest.json) |
| Native actual startup with the new Web-saved Unicode file | PASS, normal exit0 and real rig/morph/animation render at revision6 | [Actual capture](native-current.png), `native-startup-final.log`. Log filter retained warnings only; screenshot and process completion establish this bounded smoke run. Native physical checks were user-performed on the earlier font build, not repeated here. |
| Web actual startup | PASS, real character and revision6 loaded | [Production page](web-current-input.jpg); no error/warning captured on the isolated test tab |
| Work click activates browser text target | PASS: `active=nvwa_text_input`, `hidden=false` | Actual GUI click plus read-only DOM assertion |
| Composition callback commit + final input | PASS: exactly one `女娲` after four callbacks; actual final `inputType=insertText` | [Actual callback screen](after-fix-composition.jpg). Synthetic DOM callbacks, not physical candidates. |
| Preview then empty cancel | PASS: path unchanged | [Screen](cancel-preserves-path.jpg); browser owns unfinished `nv` |
| Commit then next preview, followed by click-away | PASS: first commit retained, `hao` absent | [Screen](batch-cancel-preserves-commit.jpg). Two successful commits across the recorded session explain two visible copies. |
| Command+A, preview, then cancel | PASS: original selected path retained | [Screen](select-all-cancel-preserves-path.jpg) |
| Actual tool Command+A/V and Unicode paste | PASS: replacement is exactly `女娲.nvwa.json` | [Screen](command-unicode-paste.jpg); task-owned clipboard sentinel, no user clipboard read |
| Multiline paste | PASS for single-line display | [Browser screen](command-paste-normalized.jpg). Exact pinned-egui CR/LF→spaces semantics are separately asserted in the 12-case real-library probe; browser clipboard transport normalization was not traced. |
| Other DOM input clipboard and return to Work | PASS: separate input receives `outside-only`, Work remains unchanged and can be edited again | [Screen](dom-clipboard-isolation.jpg); this is DOM focus, not OS app-switch acceptance |
| Production text Space guard | PASS: text target remains active and animation still shows Pause at0.451s after Restart | [Production screen](web-current-input.jpg); ordinary tool key input, not real IME candidate Space |
| Unicode GUI Save/Open and cross-target startup | PASS: complete saved document equals baseline revision6; GUI reload and native load succeed | [Saved JSON](女娲.nvwa.json), [comparison](document-equality.json), [Web reload](unicode-reload.jpg), native capture |
| Physical IME candidates, candidate Space, physical Command/clipboard, OS blur/refocus | PASS, user-performed | Derek replied “全部正常” on the retained new production preview. [Attribution and steps](WEB-HAND-TEST.md); no OS event trace or physical-step JSON claimed. |
| New performance, additional browser/platform, hosted CI | NOT-RUN | Historical measurements retain their earlier artifact hashes; no CI workflow is configured |

The final source hashes are `web_input.rs=58655287ca544b330ecb4f1e55a36d9fc23caaee452d2e3ea3df628c39e68824` and `lib.rs=4e00f2d61a9f44439616f31c65dfca125908f29a346aca0dcfba000b0f6b5181`. The [root real-library rerun](rework-probe-root.log) has 12 passing assertions, including actual toolbar and forced-discard controls. Experiment runners record exact compiler/rlib/source hashes. Cargo.lock is unchanged.

## Diagnostic correction and retained failures

The first repaired-browser probe duplicated the commit. Its diagnostic constructor requested `inputType=insertFromComposition`; this browser actually normalized that unsupported value to an empty string. The reducer tests had used the literal string, so they did not represent that constructor result. [Actual type trace](duplicate-input-type.jpg), [first duplication](duplicate-commit-before-fix.jpg), [repeat](repeated-commit-failure.jpg), [unsupported source](browser-probe-unsupported.js) and [commit-only control](commit-only-control.jpg) are preserved. Commit-only delivery inserts once. The corrected probe uses `insertText`, verifies its actual type in the visible trace, and inserts once on the unchanged production package. This corrects the diagnostic, not a proven physical duplicate-input bug. Empty/unrecognized browser input types and other engines remain unverified.

Do not infer that egui Selection always interrupts IME or that every Winit wake executes a synchronous frame: owning source and actual toolbar/multipass controls rejected those hypotheses. See [diagnosis](../../../experiments/08-web-ime/BROWSER-DEDUPE-DIAGNOSIS.md).

Earlier strict/build compiler failures and rejected-preview regressions remain in their original logs. One rejected native release compile was intentionally interrupted after its review failed; `build-native-rejected-preview-interrupted.log` is not a successful build. The final release commands completed separately.

## Cleanup and retest

The diagnostic tab is closed. Disposable prepared `dist/web/ime-debug.html` and `ime-instrument.js`, tiny probe binaries and generated probe sources are removed after preserving their reproducible source/logs. Final native smoke exited normally. The existing loopback server on9201 and production preview are retained for Derek. Shared caches, primary checkout, user downloads and task history are retained. The agent control plane exposes no session-disposal tool; workers returned idle, with no remaining mutating dispatch.

PARTIAL — Final 67-test/strict/dual-release checks, actual native/Web startup, installed browser callbacks and Unicode whole-document persistence passed. The repaired Web physical IME/Command/OS focus checks have user acceptance. New performance, browser zoom/DPR recovery and additional platform coverage remain unverified.
