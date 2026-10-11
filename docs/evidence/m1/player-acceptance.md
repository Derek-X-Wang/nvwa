# Actual static Player acceptance

Environment: local macOS 27.0.1 arm64, Apple M2 Pro, 16 GiB; pinned Rust 1.95.0, Bevy 0.19.1, bevy_egui 0.42.0. All images are unedited captures from the real Rust app. The original GLB hash remains `f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6`.

## Web release run

The actual IAB/WebGPU Player loaded `?player=1&work=works/m1-sequence.nvwa.json` from the ordinary loopback static server on 9201. It hid all editing/Save controls. The real character reached turn at 9s and held its final pose ([complete](player-web-complete.png)). Replay returned to idle ([replay](player-web-replay.png)); Pause held wave at 4.966s ([paused](player-web-paused.png)). A background click did not trigger an action. A chest double click played one real wave with transport disabled and cursor held ([interaction](player-web-interaction.png)), then restored the exact paused wave pose and 4.966s ([restored](player-web-restored.png)). Refresh loaded the same static work and resumed its sequence ([refresh](player-web-refreshed.png)).

The same bundle ran from `/published/` on the independent test server on 9202 ([subdirectory](player-web-subdirectory.png)). Root observed actual HTTP 200 requests for `/published/nvwa_studio.js`, `/published/nvwa_studio_bg.wasm`, `/published/works/m1-sequence.nvwa.json` and `/published/assets/fixtures/nvwa-humanoid.glb`. Requests for the optional `.glb.meta` returned 404, then the real GLB loaded. Two GLB transfers remain the known #6 issue.

## Actual Web failures and recovery

Each failed initial work left the scene without a fallback character. Open remained available after terminal errors.

| Test | Observed result | Evidence |
| --- | --- | --- |
| Missing JSON | HTTP 404 shown | [screen](player-error-missing-work.png) |
| Truncated JSON | `invalid_json` with parse location | [screen](player-error-invalid-json.png) |
| Invalid UTF-8 | UTF-8 error shown | [screen](player-error-invalid-utf8.png) |
| 2 MiB + 1 byte, no Content-Length | Cumulative size limit rejected response | [screen](player-error-oversized.png) |
| 302 redirect | Fetch rejected redirect; readable error after repair | [final screen](player-error-redirect-final.png) |
| Wrong GLB SHA-256 | Asset hash mismatch shown; no character | [screen](player-error-wrong-asset-hash.png) |
| Missing GLB | Asset path error shown; no character | [screen](player-error-missing-glb.png) |
| Stalled response body | Busy initially; request aborted and timeout shown | [pending](player-error-stalled-pending.png), [timeout](player-error-timeout-final.png), [console event](player-timeout-console.json) |

The stalled request began navigation at `2026-10-11T05:10:36.083Z`; the real AbortError console event was timestamped `05:11:06.534Z`, approximately 30.45s later including navigation/initialization. The server withheld its body for 35 seconds. The UI error was observed at `05:11:31.352Z`; this is a later observation, not a measurement of the instant the message appeared.

After missing-asset failure, manual Open loaded the actual Web revision-6 exchanged file and restored the real character ([recovery](player-web-recovery-exchanged.png)). After the timeout, the same Player page accepted that file through Open and began idle playback ([timeout recovery](player-web-timeout-recovered.png)). Those runs include the saved jaw/smile edits and all three timeline segments. The exchange file itself and CLI reproduction are in the separate sequence/equivalence evidence.

The first redirect test exposed a full JS/WASM stack in the UI ([original](player-error-redirect.png)). The original owner repaired message display, retained full diagnostics in the console, added a formatter regression and obtained targeted R2 acceptance. Final source passed 57 workspace tests, fmt and strict native/Wasm clippy. The actual repaired Web release screen above confirms that Open and the compact panel remain visible. Other failure screens and positive transport screens preceded this Web-only display repair; their functional paths were unchanged.

## Native release run

The final release bundle was copied to `.work/m1-relocated/Nvwa.app`, then its executable was launched from `/tmp` with the work copied into its own Resources directory. The actual Metal window was titled `Nvwa · Player`; it loaded the real rig and played turn at 7.499s ([relocated](player-native-relocated.png)), completed at 9s ([complete](player-native-complete.png)), and Replay returned to idle ([replay](player-native-replay.png)). This validates executable-relative packaged assets and work loading away from the repository cwd.

Restart, Pause and global seek held a real wave pose at 5.3s ([paused](player-native-paused-final.png)). A background click did not trigger the wave; head double click did ([interaction](player-native-interaction.png)). The final pose and exact paused 5.3s returned ([restored](player-native-restored.png)). Manual Open then loaded the same revision-6 Web file with its edited jaw/smile and 9.5s arrangement ([exchanged](player-native-exchanged.png)). The earlier `player-native-paused.png` captured a still-playing seek after an automatically completed replay; the final paused screen supersedes it.

A fresh native launch with an absent explicit work showed a file error and no fallback character ([missing work](player-native-missing-work.png)). Its GUI manual recovery is **NOT-RUN to completion**: the desktop automation adapter lost coordinate input (`noWindowsAvailable`), then reported duplicate app identifiers and ScreenCaptureKit capture failure while the actual process remained alive. No app crash or recovery pass is inferred from that. The duplicate generated bundle was stopped and removed after verifying binary/GLB equality with the retained `dist/Nvwa.app`; logs/screens remain. A second ordinary-bundle recovery attempt met the same adapter limit and was stopped. Normal native Open above, headless native missing-work recovery, and actual Web negative recovery remain separate positive evidence. This additional hand-test gap is tracked under issue #2.

A further fresh final executable launch opened revision6 directly for formal measurement. Its real screenshot and runtime record confirmed ready=true, mode=player, revision6, timeline_count3, four morph weights, completed=true and held cursor9.5. See [native record](../performance/m1-player-native-release.json) and [actual capture](../performance/m1-player-native-release.png). This validates restarting directly with the saved work; it does not replace the uncompleted negative-startup GUI recovery check.

## Final release and measurement evidence

Final 57-test run: [tests](player-tests-complete.log). Strict [native clippy](player-native-clippy-complete.log), [Wasm clippy](player-wasm-clippy-complete.log) and [fmt](player-fmt.log) passed. Final [native release build](player-native-release-build-complete.log) and [Web release build](player-web-release-build-complete.log) exited 0. The [manifest](build-manifest.json) verifies the packaged/native binary and all fixture copies by SHA-256.

Both final measurements used the exact revision6 work at physical1280×720, one real actor, no competing task-owned compiler/Nvwa renderer, and 600 recent samples. Native main-loop p50/p95 was8.327/8.924ms, child peak RSS240,599,040bytes (~229.5MiB). Web was8.300/9.500ms ([exact console record](player-web-benchmark-console.json), [parsed report](../performance/m1-player-web-release.json), [actual canvas download](../performance/m1-player-web-release.png)). Both reported completed=true, playing=false, cursor9.5: the sampled finite work held its last pose. These are cadence samples after completion, not GPU timings or a claim of continuous-animation performance. M0 continuous-idle measurements remain in PERFORMANCE.md.

The actual gzip sum for HTML/generatedJS/Wasm/uniqueGLB plus the measured work is14,179,929bytes ([size report](web-size-report.json)); the shipped9s demo total is14,179,914bytes. This is a unique-file transfer-size sum, not a cold network measurement. Known duplicate GLB transfer can add bytes. First presentation, cold Web startup and browser/GPU memory remain NOT-RUN.

## Verification limits

This is one original rig and authored actions, with conservative chest/head targets. It is not exact deformed-mesh picking or AI generation. Source R2, compilation, graphical behavior and performance are distinct evidence. Public hosting, signing/notarization, other OS/browser coverage, exact first presentation and GPU timestamps remain outside this local acceptance. Known M0 issues remain tracked independently.
