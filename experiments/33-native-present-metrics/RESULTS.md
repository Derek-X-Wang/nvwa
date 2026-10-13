PARTIAL — Three actual native release launches completed on 2026-10-13. The diagnostic variant records actual Metal drawable display times, completed command-buffer GPU durations, and device allocations. Exact PID/birth memory samples and inspected real-character pixels are retained. Fully cold state, startup-stall causes, exact first character presentation, and production main-loop percentiles remain unverified. Issue #4 remains open.

The accepted baseline executable is SHA256 `72d3df8cfdeea062282c8731b0a95cb971f90976fe881772f3e3c24afe76973a`. Both diagnostic launches use SHA256 `31999ece7a4b74875ac254eb15ebb8fad08e73e8880ca8a3fbd68c5026af8a6c`. The unchanged production `nvwa_studio::build_app()` loads the same revision-zero looping real humanoid work: input SHA256 `ff0b8e36adfc3ebadc5fc700a4c760f6f551273b56e85bf336563e18b63eb445`, GLB SHA256 `f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6`, 18 joints and four morph weights. Content is physical 1280×720 at scale 1. Host-window JPEGs are 1280×784 because they include a 64-pixel title bar.

| Actual launch | PID | First valid reported surface display after external launch | Earliest sampled character-containing readback callback | Owned exit |
|---|---:|---:|---:|---|
| Accepted baseline | 68805 | NOT-RUN; no observer | Delayed production PNG exists; its callback time was not logged | Exit 0; 31.883 s |
| Diagnostic startup | 70636 | 9.963883–9.967385 s, callback index 5 | 9.947958–9.951460 s | Exit 0; 34.718 s |
| Diagnostic process-warm contrast | 72779 | 1.745521–1.749544 s, callback index 2 | 1.786588–1.790610 s | Exit 0; 32.128 s |

The first diagnostic surface callback returned `presentedTime=0` in both runs. Startup indices 1–4 and warm index 1 all returned zero. All earlier dense callbacks are present in the retained trace. They provide no valid onscreen time and are excluded. The table reports the earliest nonzero Metal-reported surface display, with complete earlier callback states. It does not assert that this surface contained the character. The separate readback callback establishes an observation of a character-containing image; it is not the time that image appeared on the display.

Each diagnostic run retained 138 drawable callbacks and 138 completed command-buffer samples. GPU spans use the existing Metal command buffer's `GPUStartTime` and `GPUEndTime` inside its completion handler, with Completed status and nonzero ordered endpoints. Zero durations are retained. No GPU timestamp queries were inserted or Bevy's macOS timestamp workaround bypassed.

| Selected completed command buffers | Diagnostic startup | Process-warm contrast |
|---|---:|---:|
| Submitted buffer count | 134 | 134 |
| Submitted buffer p95, nearest rank | 0.537750 ms | 0.381750 ms |
| Submitted buffer maximum | 14.777833 ms | 9.128875 ms |
| Internal presentation buffer samples | 4 | 4 |
| Zero-duration samples across both kinds | 23 | 28 |
| Invalid completion spans | 0 | 0 |

These are bounded samples of existing submitted command buffers. They can include render, upload, or other encoded work. They are not whole-frame or per-character GPU times. Do not sum them, infer frame latency, or use their duration to explain the startup delay. All groups and raw endpoints are in [ACTUAL-RESULTS.json](ACTUAL-RESULTS.json).

| Exact PID/birth memory observation, MiB | Baseline | Diagnostic startup | Process-warm contrast |
|---|---:|---:|---:|
| Samples | 115 | 126 | 104 |
| Largest sampled RSS | 200.25 | 188.22 | 217.16 |
| Largest sampled physical footprint | 282.08 | 302.49 | 303.27 |
| Kernel-reported lifetime maximum physical footprint | 283.06 | 312.08 | 312.22 |
| Largest sampled Metal device `currentAllocatedSize` | NOT-RUN | 127.77 | 124.62 |

RSS and physical footprint use different accounting and overlap. Metal allocation is a separate device-resource metric. Do not add them. Sample maxima are not continuous peaks; the separately named lifetime footprint maximum is a value reported by the kernel, not a sampler estimate. Memory samples all match the owned PID and microsecond kernel birth before and after each read.

All nine PNGs and all three original host-window JPEGs were independently inspected with `tools.view_image` after the runs. Both `first-main-update.png` images are blank. Both `first-runtime-ready.png` images contain the real humanoid while the UI still says Preparing. Both `ready-plus-2s.png` images and all three `production-final.png` images show the humanoid and Ready UI. Hashes, dimensions, callbacks, and filesystem timestamps are retained in [ACTUAL-RESULTS.json](ACTUAL-RESULTS.json); filesystem times are not display boundaries.

The host-window observations are exact emitted JPEG bytes with successful tool-call/output provenance. Their UTC request brackets are separate from the native/Metal clocks and do not establish first presentation or independently prove keyboard focus:

| Original host-window capture | UTC observation bracket | SHA256 |
|---|---|---|
| [Baseline](../../docs/evidence/bounded-perf-20261013/visual/native-baseline-1-original.jpg) | 21:29:38.297–38.948 | `0b5adcfcb51bd1b5d943050b367b76a3fd11cdb9c2398dafda55bd76843d0311` |
| [Diagnostic startup](../../docs/evidence/bounded-perf-20261013/visual/native-diagnostic-1-original.jpg) | 21:30:05.390–06.407 | `3c1f321c54052b1abc2682b5dac6b4c0b5874e1f4cbecf194aa270fd01dde4d6` |
| [Process-warm contrast](../../docs/evidence/bounded-perf-20261013/visual/native-diagnostic-warm-original.jpg) | 21:30:47.025–47.566 | `8ca7ada083b77fea0725efefd3201ce16a46e7b744435ac424683a5d01627980` |

Raw process lifecycle/logs and readbacks are available in the public mirrors: [baseline receipt](../../docs/evidence/bounded-perf-20261013/native/runs/baseline-1/process-receipt.json), [startup receipt](../../docs/evidence/bounded-perf-20261013/native/runs/diagnostic-1/process-receipt.json), [warm receipt](../../docs/evidence/bounded-perf-20261013/native/runs/diagnostic-warm/process-receipt.json), [startup Metal log](../../docs/evidence/bounded-perf-20261013/native/runs/diagnostic-1/stderr.log), [warm Metal log](../../docs/evidence/bounded-perf-20261013/native/runs/diagnostic-warm/stderr.log), [first sampled startup character](../../docs/evidence/bounded-perf-20261013/native/captures/diagnostic-1/first-runtime-ready.png), and [first sampled warm character](../../docs/evidence/bounded-perf-20261013/native/captures/diagnostic-warm/first-runtime-ready.png).

Raw clock domains remain separate. Metal and Core Animation provide host seconds. Each callback's Core Animation read is bracketed by actual `CLOCK_MONOTONIC` reads. The displayed time is converted with that local calibration, then bounded against the external Popen launch-before/after interval. The startup/warm launch brackets are 3.498/4.018 ms wide. Reported `CLOCK_MONOTONIC` resolution is 1 μs; table bounds add two such ticks plus 2 ns for logged-double quantization. These bounds describe measurement brackets, not undocumented driver timestamp accuracy. Callback delivery time and process-relative Rust `Instant` are not substituted for displayed time. Per-callback offsets vary, so one global offset is not assumed.

The same workload remained playing at the readiness-plus-two-second CPU observations: startup position 2.1063 s and warm position 2.3948 s, both `playing=true`, `completed=false`. Startup runtime readiness was observed at process `Instant` 8.207355 s with Bevy's `first_ready_seconds=1.838827209`; warm readiness was process 1.725516709 s with Bevy 0.207402959 s. Those are different clocks and readiness boundaries. Production `NVWA_EVIDENCE` INFO records are absent from captured stdout/stderr in all three launches, so production p50/p95 main-loop cadence is NOT-RUN for this packet.

Task-owned heavy builds were held during native acquisition. The whole host was not quiet. Retained inventories include Browser Helper Renderer PID 59010 at 101.9% CPU before diagnostic startup, Codex Renderer at 68.9% before warm startup, `claude bg-spare` at 71.6% after baseline, and `node` at 135.3% after warm startup. Launcher Python itself appears near 50% at startup. These snapshots do not establish continuous contention or a cause, but they prevent an uncontended whole-machine benchmark claim. Unrelated apps were not stopped.

The warm contrast is another fresh process in an already used OS/Metal environment. There was no reboot, purge, driver reset, shader-cache clearing, install, or permission change. Fully cold OS/file/Metal/shader state and attribution of the startup difference remain NOT-RUN. Diagnostic callbacks, sampling, and three readbacks also add overhead; accepted baseline and diagnostic timing are not equivalent variants.

Five original reconciliation controls and the real libproc PID/birth/memory-growth controls passed after acquisition. Ten CPU mutations of actual recorded rows were rejected, with restored actual rows accepted: failed GPU status, zero GPU start, zero presentation time, reversed calibration, and mixed PID, for both diagnostic runs. This is verifier evidence using actual logs, not additional GPU execution. The earlier clock-label and Homebrew interpreter-trampoline failures remain preserved; final launcher controls supersede the stale prelaunch-check wording in `LAUNCHER.md` without changing that original freeze.

The [original source freeze](../../docs/evidence/bounded-perf-20261013/native/preparation/candidate-freeze.json) and [dependency comparison](../../docs/evidence/bounded-perf-20261013/native/preparation/dependency-comparison.json) remain unchanged. The original 524 accepted product/build inputs match accepted main; all 524 common dependency versions/features match. The only dependency origin change is the isolated wgpu-hal patch. No observer/source/binary rebuild or fourth native launch followed measurement. All owned app PIDs were observed absent after their successful exits, and root's servers were also removed.

VERIFIED — Actual native Metal display/completion callbacks, exact PID/birth memory, nine real readback artifacts, three original host-window captures, finite successful process cleanup, and retained raw clocks/hashes. PARTIAL — Whole-host isolation, exact first-character display, fully cold state, CPU cadence, and startup cause remain unverified.
