# Actual GUI session — integration checkpoint

Native and Web observations were made through Codex CUA on the local M2 Pro. Native dev Metal and browser dev WebGPU ran sequentially. These interactions overlapped release compilation and are functional evidence, not formal performance.

## Native Studio

- Real continuous humanoid: nine mesh/skin components, 18 joints, four morphs, one animation player. Idle and wave both actually played; wave raised the arm.
- While wave played, clicks changed jaw_width=.82, nose_width=.91, smile=.79, shoulder_width=.99 with visible geometry changes. Revision5.
- Save to an absolute path succeeded. Undo restored shoulder0 at revision6; redo restored.99 at revision7. Save again produced edited-from-native.nvwa.json, independently CLI-validated against actual assets.
- Pause and deselection were visible. App was quit before browser rendering.
- Normal direct file-field typing worked. Native CUA drag and modifier/clipboard attempts did not establish a successful drag or paste; these remain unverified native interactions.

## Browser dev Studio

- Static loopback server and real WebGPU character started. Browser warnings/errors snapshot was empty.
- File chooser imported edited-from-native.nvwa.json. Revision7, all four parameter values, visible geometry and wave reference survived.
- This actual import exposed a new-player playback initialization defect: wave selected, Players1 active0. Source repair is reviewed; release rebuild and GUI retest pending.
- A track click set shoulder.49 at revision8. A real drag set.79 at revision9. Undo restored.49 at revision10; redo restored.79 at revision11. Each drag committed once.
- Browser Save downloaded scene.nvwa.json, copied to edited-from-web.nvwa.json and independently CLI-validated. Native reopen pending.
- Clipboard paste accepted nvwa-角色.nvwa.json, and Save downloaded that exact Unicode filename. Default egui font displayed Chinese as missing-glyph squares. Chinese rendering is a known limitation; IME composition not tested.
- Changing browser viewport/DPR while the Wasm app was running caused stale input scaling. Resetting the temporary override restored correct input. Fresh viewport-before-reload test pending.

Actual dev runtime PNG: native/dev-smoke.png. No generated or Blender source image is being used as Studio evidence.

## Browser release functional retest

The actual new-player defect is resolved in the fresh release bundle. Opening the native revision7 document now yields Players1 active1 with wave selected, all four parameters intact and visible animated geometry. Play/Pause works. Selecting and playing turn changes the body orientation. During turn playback, an actual shoulder drag changes.99 to.68 with exactly one revision (8→9). Switching back to wave and saving produces edited-from-web-release.nvwa.json at revision10. Native reverse-open remains pending.

Viewport emulation before reload still produces the staleDPR input/display mismatch in IAB; ordinary unoverridden viewport works correctly. No product scaling pass is inferred from the emulated1280×720 page. Formal benchmark uses the explicit physical-buffer mode without emulation.

## Browser release errors and recovery

Unsupported schema999 was rejected with an explicit red unsupported_schema_version message; revision0 and the active real character remained. A valid document referring to fixtures/missing.glb produced Load error, zero mesh/skin/player counts and an explicit Asset byte load failed message. Opening the saved valid revision10 document then restored all real component counts, four parameters, wave and active1, and cleared the error. These observations used real asset fetches, not mock readiness.

## Native release reverse exchange and seeking

After quitting the earlier native process and replacing the generated bundle with a release binary, a new native process loaded the original character from bundled Resources/assets. Opening edited-from-web-release.nvwa.json restored revision10, jaw.82, nose.91, smile.79, shoulder.68, wave and active1, with a visibly raised arm. Saving as native/reopened-from-web.nvwa.json preserves the entire parsed JSON document, verified by exchange-result.json and CLI asset validation. Thus both actual UI exchange directions are complete.

Pause and seek to.75seconds showed Play and a fixed corresponding wave pose. Native CUA drag still did not change the value; native drag automation and native clipboard remain unverified, though native track clicks and sharedWebdrag/coretransaction tests work. Browser file-field Space did not pause animation; after clicking the viewport, Space did pause it. Bulk browser CUA typeText inserted only the first character; paste and single-key input worked. Human typing and IME need hand testing.

The native compiler was interrupted intentionally after a final style-only clippy repair made its source snapshot obsolete. First release build passed; final-source rebuild waits for strict checks. No measurements have used an interrupted/competing compiler run.

## Final Web benchmark evidence

The physical1280×720 release surface is confirmed by DOMbuffer dimensions, Rustwindow evidence and a visually inspected1280×720 actual PNG. Three isolated warm runs emit600samples each: p50=8.3ms, p95=10.4/10.7/11.2ms. Nativecompiler was stopped during each run; one renderer was active. Console tracing uses console.log for alllevels, so earlier filteredemptylogs did not establish a lack ofwarnings. Bindless texture-array warnings use the supported fallback; deliberatelymissingassets loggedexpectederrors.

Bevy automatic screenshot callbacks succeeded, but no file/download was delivered in IAB. A benchmark-only browseradapter with an explicit user-activated realcanvas.toBlob PNG button succeeded. release-canvas.png shows the baseline, exchanged-release-canvas.png shows revision10/fourmorphs/pausedwave. It is neither an offline render nor a generated image. No Rustbusinesslogic was moved to JS.

Exact firstpresentation, GPUtimestamps and browsermemory were not measured. WebGPUadapter name is hidden; the backend BrowserWebGpu is observed. No hardwareGPUmodel is inferred from its emptyname. Native formal measurement subsequently passed; see the final section below.


## Final native measurement and CLI parity

With both builds complete and the browser blank, the final native executable ran two isolated release probes. A 1-second-request startup probe produced an actual 1280×720 PNG and exit0; process-relative capture completion upper bound8.52s. Its five slow startup intervals are not steady performance. A later 15-second probe produced a Ready PNG, exit0 and600samples: p50=8.34ms, p95=8.65ms, peak child RSS237.05MiB. Exact first presentation/GPU timestamps remain unmeasured. Logs/JSON/PNGs are under performance/ and interpreted in ../PERFORMANCE.md.

The actual release CLI applied command sequences reconstructed from these GUI operations. Starting from default revision0 it reproduced the actual native revision7 document; starting from7 it reproduced the actual Web revision10 document. Whole-document semantic equality passed twice. cli-gui-parity.json records the limited reconstruction scope; commands and CLI output documents are retained in native/ and web/. This is additional shared-core evidence, not an instrumented GUI eventtrace.

PARTIAL — Actual native/Web character editing and full cross-end exchange verified, along with CLI document parity and isolated release cadence. Font/IME/input and exact-presentation limits remain explicit.
