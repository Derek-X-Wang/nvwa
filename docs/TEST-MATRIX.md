# Actual verification matrix

Current thin M1 evidence is recorded separately in [M1 verification](M1-VERIFICATION.md). The table below is the archived M0 acceptance: M0 was subsequently committed/pushed as `d74493d`, and the user approved bounded thin M1. The M0 build manifest describes that earlier source/artifact snapshot.

The later font/input PR #18 has a separate [current acceptance](evidence/web-input/ACCEPTANCE.md) and [manifest](evidence/web-input/build-manifest.json): 67 workspace tests, strict checks, both release builds and actual native/Web runs. Repaired Web physical candidates/Space, Command+A/V and app-return editing have [Derek's acceptance](evidence/web-input/WEB-HAND-TEST.md). The earlier font-only59-test manifest remains historical. Web zoom/DPR and current-artifact performance remain unverified.

## M0 acceptance

M0 snapshot: 2026-10-10 PDT / 2026-10-11 UTC. Build, execution, interaction and measurement are separate claims. All final Rust checks use pinned Rust 1.95.0 and Cargo.lock; no check was disabled to obtain a pass.

| Area | Docs/source | Compiled | Native ran | Web ran | Validated evidence |
|---|---|---|---|---|---|
| Pure Rust commands/storage schema | complete | yes | CPU tests/CLI | shared Wasm core | 13 core tests: atomic failures, revisions, retries, strict JSON, undo/redo, previews and asset integrity |
| Offline CLI | complete | release | actual binary | n/a | 4 CLI tests; actual CLI replay equals GUI-produced documents at revisions 7 and 10 |
| Runtime/Studio regressions | complete | native/Wasm | CPU tests | actual release app | 10 runtime + 6 Studio/platform tests, including real async asset recovery and replacement animation players |
| Native Studio | complete | dev/release | Metal, Apple M2 Pro | n/a | Actual character, four visible morph edits, idle/wave, history, save/open, pause/seek, restart; real PNGs |
| Web Studio | complete | dev/release | n/a | IAB, Chrome/155 UA, WebGPU | Four morphs, idle/wave/turn, one command per drag, history, open/download, refresh/reopen, errors and recovery |
| Original humanoid | complete | Blender export | real renderer | real renderer | Continuous body, 18 joints, 4 nonzero morphs, 3 authored skeletal clips; independent fixture/hash validation |
| Native↔Web exchange | complete | adapters | open/save | open/export | Native revision 7 → Web revision 10 → fresh native open/save; entire parsed JSON matches |
| Release performance | complete | release | one renderer | one renderer | Physical 1280×720, 600 steady cadence samples; native p95 8.65 ms, Web p95 11.20 ms; limits below |
| Build hygiene | complete | both targets | checks | Wasm checks | 33 Rust tests, fmt, strict native/Wasm clippy passed; final release logs retained |
| Rest-basis A/B | complete | Python CPU | exported/reloaded GLBs | n/a | 19 actual-wave samples; corrected max vertex error 3.08e-8 m vs naive 0.868 m; visual derivative playback NOT-RUN |
| Optional AI motion | primary research + isolated seam | Python CPU | 9 import tests | n/a | Authored preset is ai_generated=false; genuine inference NOT-RUN, runtime/weights absent in checked locations |

Evidence: [workspace tests](evidence/workspace-tests.log), [native clippy](evidence/native/clippy.log), [Wasm clippy](evidence/web/clippy.log), [native release build](evidence/native/release-build.log), [Wasm release build](evidence/web/release-build.log), [GUI session](evidence/GUI-SESSION.md), [exchange equality](evidence/exchange-result.json), [CLI/GUI parity](evidence/cli-gui-parity.json), [performance](PERFORMANCE.md) and [source/artifact hashes](evidence/build-manifest.json). The empty fmt log records a successful quiet check; EXECUTION.md preserves its exit status.

## Input and display observations

| Check | Actual result | Remaining scope |
|---|---|---|
| Native parameter input | Track clicks changed all four morphs; undo/redo restored geometry | CUA drag did not change values; native continuous drag needs hand testing |
| Web parameter drag | Actual drag committed once; geometry and undo/redo matched | Other browsers/input devices untested |
| File field/clipboard | Native direct typing and Web paste worked; Unicode filename downloaded correctly | Native clipboard and human continuous browser typing not established; CUA bulk typeText inserted one character |
| Chinese text/IME | Unicode data roundtrips; default fonts show missing CJK glyphs | Chinese display is a known limitation; IME composition NOT-RUN |
| Focus/shortcuts | Web file-field Space did not pause; viewport Space did; pause/resume and selection worked | OS-level blur/refocus combinations need hand testing |
| HiDPI | Native normal HiDPI and ordinary Web viewport worked | IAB viewport/DPR emulation caused stale input scaling; zoom/other DPR combinations unverified |
| Screenshot export | Native callback produced PNG; explicit Web benchmark canvas button produced PNG | Automatic Bevy callback succeeded but no persistent IAB download appeared |

## Explicit limits

- Measurements are real main-loop cadence, not GPU timestamps or exact presented FPS. Native startup screenshot completion was an 8.52-second process-relative upper bound; Web cold startup/exact first presentation and browser RSS/VRAM are NOT-RUN. See PERFORMANCE.md.
- Windows/Linux, Safari/Firefox and external Chrome, signing/notarization and public hosting are NOT-RUN. The native artifact is a local unsigned macOS arm64 bundle.
- M0 supports one fixed rig and one selected timeline entry. Arbitrary rigs, cloth/physics, IK, root-motion policy, general retargeting, VaM compatibility, live remote GUI control and thin M1 sequencing/Player were not implemented or claimed.
- Asset reexports preserve measured structure/morph data but are not byte-identical. Session undo/retry history has no eviction cap and is not saved in documents.

PARTIAL — M0 functional loop, both release builds/runs, 33 Rust tests and isolated cadence measurements verified. Input/font coverage, exact GPU/first-frame timing, other platforms and real AI inference remain limited as listed.

## Thin M1 final acceptance

| Area | Compiled | Actual run / validated | Limits |
| --- | --- | --- | --- |
| Three-action work | native/Wasm release | actual native/Web sequence, pause/seek, undo/redo and revision5→Web6→freshnative6 whole-JSON equality | one fixed original rig, authored clips |
| Character click | native/Wasm release | real chest/head targets, wave once, exact paused/running restore and unchanged saved document | conservative hotspots; no exact GPU-deformed silhouette claim |
| Native Player | release packaged | copied bundle from /tmp, real9s completion/replay, paused5.3s restore, Web6 Open, missing-work error; fresh final process direct-reopened6 | negative-startup manual-recovery GUI blocked by desktop adapter; headless path tested |
| Static Web Player | release | ordinary static server, subdirectory, refresh, portable-work Open, all documented negative responses, actual30sabort and manual recovery | IAB WebGPU only; no public hosting validation |
| Checks/review | exact selected features |57tests,fmt,strictnative/Wasmclippy,fixturehash; independent cross-model R2 plus repair rereviews | no hosted CI |
| Performance | final release | physical1280×720,600cadence samples; native8.327/8.924ms,p50/p95,Web8.300/9.500ms; native~229.5MiB RSS; uniquegzip14,179,929bytes | finite work completed/held pose; not GPU timestamps or cold launch |

[Player evidence](evidence/m1/player-acceptance.md), [M1 register](M1-VERIFICATION.md) and [known issues](ISSUES.md) are the current checkpoint. M0 experiment conclusions and earlier measurements above remain valid for their recorded snapshot.
