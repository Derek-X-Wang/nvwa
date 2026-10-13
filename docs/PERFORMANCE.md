# Actual release measurements

## 2026-10-13：首帧、GPU 与内存的有界补测（#4）

同一份 revision0 idle 作品、真实18关节/4形变角色、1280×720/DPR1。已验收 main 为 `d832ef3e044017bddb5a0681ff5ca99256ebaef4`。三个桌面进程与三个 Web 页面依次运行；正式测量期间只有一个任务渲染器，未运行重编译。原生基线与 Web 使用原有 release 产物；独立 Metal 诊断产物另行编译，不进入产品依赖。用户应用和系统缓存未控制。

| 实测边界 | 桌面 Metal | Web IAB / Chrome155 |
| --- | --- | --- |
| 呈现 | 两次诊断的首个有效已记录 surface 呈现约为进程启动后9.963883–9.967385s、1.745521–1.749544s。前面的零值回调全部保留；这些不是角色首帧。 | 三次真实角色画面已观察；没有精确物理呈现接口。首次 submit 返回956.0/1192.1/1188.3ms，均早于 GLB 下载结束，不能作为角色首帧。 |
| 角色像素 | 首个主更新截图为空白；诊断1的实际角色 GPU 读回回调为9.947958–9.951460s。GPU 读回与屏幕显示不同。 | GLB responseEnd 为1158.2/1399.0/2124.3ms；Ready 日志使用独立 Bevy 时钟，页面截图使用独立主机 UTC。 |
| GPU | 两次诊断各134个实际 submitted 命令样本，p95 为0.537750/0.381750ms。零耗时样本保留；不求和，不代表每帧耗时或持续角色渲染预算。 | 时间戳实验实际执行：四个 compute 零值、两条 UI 65,536ns、两个倒序错误。结果不接受，状态仍为 NOT-RUN。 |
| 内存 | 未修改基线的115次 PID/出生时间核对样本：最大 RSS209,977,344bytes；最大 physical footprint295,781,552bytes。两者重叠，不能相加。Metal 资源分配量另记。 | 每次30个 JS heap 估计样本，最大19,292,318 /21,151,025 /20,179,465bytes；不包含完整 Wasm、浏览器 RSS 或 GPU 内存。 |
| 完全冷启动 | 新进程成立；OS 文件、Metal 驱动和 shader 缓存未证明冷态，未重启或清缓存。 | 新导航、完整 no-store HTTP 响应成立；浏览器进程、Wasm 编译器、shader、驱动和 OS 缓存未证明冷态。 |

两次桌面诊断不能归因启动差异。新增读回和观察器会干扰被测程序；不得将诊断值当作未修改产品基线的性能。原生本轮捕获日志缺少 `NVWA_EVIDENCE`，因此本轮原生主循环 cadence 未验证；保留历史结果的原有产物和日期。

[本轮验收与原始数据](evidence/bounded-perf-20261013/ACCEPTANCE.md)、[桌面复现](../experiments/33-native-present-metrics/RESULTS.md)、[Web 复现](../experiments/34-web-cold-metrics/RESULTS.md)。

PARTIAL — 双端实际运行、桌面有效 surface 时间/命令 GPU 样本/PID 内存、Web HTTP/CPU 边界与 JS heap 子集已测。角色首次物理显示、完全冷启动、启动停顿原因、Web 有效角色 GPU 耗时和总 GPU 内存仍未验证；#4 保持开放，#3 保持阻塞。下方旧结果只描述对应历史产物。

## Current bounded startup checkpoint (2026-10-12)

Two actual IAB Web startups used fresh run URL prefixes and no-store responses with the unchanged accepted Rust release artifact. Each transmitted20,564,428bytes across five critical bodies (diagnostic wrapper/collector, JS, Wasm, one GLB), plus an explicit28-byte optional metadata404. Boot-hidden observations were517.5/634.4ms; GLB Resource Timing responseEnd was936.6/1100.8ms, all on the navigation clock. Actual1280×720/DPR1 character pixels and current top-level automatic/explicit PNG downloads were verified. [Raw packet and limits](evidence/bounded-startup-capture/ACCEPTANCE.md), [reproduction](../experiments/24-http-cold-startup/README.md).

Startup2's actual `NVWA_EVIDENCE` records first asset readiness at0.4248s and screenshot callback at15.4457s, on `bevy_TimeReal_since_first_update`. That clock excludes HTML/Wasm initialization before the first Bevy update; the callback includes the requested15s warmup. Startup1's console capture is empty. [Attributed raw extraction](evidence/bounded-startup-capture/startup-2-runtime-evidence.json).

PARTIAL — HTTP-cache resource retransmission verified; boot-hidden is not asset-ready/first presentation. Browser/GPU/OS/shader caches were not cold-proven; startup1 Bevy console timings, exact first presentation, GPU timestamps/memory, browser memory and native stall attribution remain NOT-RUN. No performance or screenshot policy change follows. All measurements below retain their older artifact/date scope.


Recorded 2026-10-10 PDT / 2026-10-11 UTC on macOS 27.0.1 arm64, Apple M2 Pro, 16 GiB unified memory, 12 CPUs. Rust 1.95.0, Bevy 0.19.1 and bevy_egui 0.42.0. Native backend is Metal with observed adapter Apple M2 Pro. Browser is Codex IAB with HTTP User-Agent Chrome/155.0.0.0; BrowserWebGpu is observed, adapter name hidden. No other browser is inferred.

Both used final release artifacts, original GLB `f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6`, one default character playing idle, physical 1280×720 with scale override 1, continuous benchmark scheduling. The scene retained 9 meshes/skins, 18 joints, 4 morph weights and 1 active animation player. Other Nvwa renderers were closed. Compilers were stopped during Web measurement; native measurements followed all builds. No competing heavy task was running.

## Steady cadence and memory

| Actual run | Samples | p50 (ms) | p95 (ms) | Memory observed | Evidence |
|---|---:|---:|---:|---|---|
| Native release, 15-second run | 600 | 8.34 | 8.65 | peak child RSS 248,561,664 bytes / 237.05 MiB | [JSON](evidence/performance/native-release.json), [log](evidence/performance/native-release.log), [actual PNG](evidence/performance/native-release.png) |
| Web release, isolated warm run | 600 | 8.30 | 11.20 | browser RSS/VRAM unavailable | [JSON](evidence/performance/web-release.json), [actual PNG](evidence/web/release-canvas.png) |

Two earlier isolated Web runs also yielded 600 samples each: p50 8.30 ms, p95 10.40/10.70 ms. Native exit code was 0 with a nonempty real screenshot. Web canvas dimensions, Rust window evidence and PNG all confirmed 1280×720. At DPR 2 its CSS canvas is 640×360; viewport emulation was disabled.

Samples use Bevy Time<Real> between main-loop updates after asset readiness plus one second of warmup, retaining the most recent 600. This measures scheduling cadence, not GPU completion, exact presentation intervals or certified displayed FPS. Cadence is below the initial 33.3 ms budget in these steady conditions. Child-process RSS excludes GPU/total unified-memory allocation. Browser memory and GPU timestamps are NOT-RUN.

## Startup and first visible image

The first probe on the final native executable requested capture after one second of asset readiness. It exited 0 and wrote a real 1280×720 PNG. Process start to screenshot-evidence log was **8.52 seconds**; total wall time 8.60 seconds. Completion is an upper bound on visibility, not exact first presentation. [Startup JSON](evidence/performance/native-release-startup.json), [log](evidence/performance/native-release-startup.log), [PNG](evidence/performance/native-release-startup.png).

This probe had only five cadence samples (p50 1373.95 ms, p95 1550.96 ms) during startup. These are startup stalls, not steady performance. The next 15-second run had the stable cadence above. No cache purge occurred and no profiler attributed the delay; shader/renderer initialization is a hypothesis only. The initial PNG has the actual character and a preceding UI Preparing state, while callback runtime counts report active playback.

Native first asset readiness was 0.04–0.05 seconds and Web 0.18 seconds since first Bevy update. Those clocks omit earlier process/HTML/Wasm startup and must not be presented as first-frame latency. Web screenshot callback was at 15.21 seconds and includes requested 15-second warmup. **Cold Web startup and exact first presentation remain NOT-RUN.**

## Download size

Actual files were gzip-compressed with mtime 0. [Size report](evidence/web/release-bundle-size.json):

| File | Raw bytes | Gzip bytes |
|---|---:|---:|
| index.html | 2,690 | 1,438 |
| generated JS | 114,571 | 18,017 |
| Wasm | 74,441,155 | 12,965,331 |
| original GLB | 3,827,840 | 1,129,081 |
| **Unique first-screen files total** | | **14,113,867** |

Profile is embedded in Wasm. Raw-byte integrity and glTF loading were observed to request GLB via two fetch paths. Without cache reuse, a second asset transfer adds 1,129,081 bytes (15,242,948 total). These totals fit the initial 30 MB byte budget. This is measured bundle compression, not a measured cold HTTP transfer or network latency. Static responses supply Content-Encoding gzip and Vary; no model/API service is needed.

## Reproduce

Close other renderers and pause heavy jobs. From the repository root:

```sh
python3 scripts/benchmark-native.py --seconds 1 --label native-startup-repro
python3 scripts/benchmark-native.py --seconds 15 --label native-steady-repro
python3 scripts/serve-web.py
```

Open `http://127.0.0.1:9201/?benchmark=1` without viewport emulation. After 15 seconds read `NVWA_EVIDENCE` from **console.log**. Wasm tracing sends all levels through console.log; filtering only console.info/warn/error misses messages. Use the page's explicit PNG button to download real WebGPU canvas pixels. Bevy's automatic callback succeeded but did not deliver a persistent IAB download. [exchanged-release-canvas.png](evidence/web/exchanged-release-canvas.png) is the independently inspected user-activated export of actual revision 10.

These reproduction instructions are not claims of extra runs. Benchmark scheduling is continuous even unfocused; normal scheduling retains Bevy's default focus behavior. No cache, browser/GPU identity, first-frame or memory result beyond these observations is asserted.

PARTIAL — Isolated 1280×720 release cadence, native child RSS, actual PNGs and compressed bytes measured. Exact presentation/GPU timing, cold Web startup and browser memory are NOT-RUN.

## Thin M1 final release Player

Measured the same actual [revision6 exchange work](evidence/m1/web-sequence.nvwa.json) in both targets. It contains three segments over9.5s and retains appearance edits. Native Metal and IAB WebGPU reported player mode, revision6, timeline_count3,18joints,9skins,4morph weights, ready=true, completed=true,playing=false,cursor9.5.

| Target | Recent samples | Cadence p50 / p95 | Memory | Evidence |
| --- | --- | --- | --- | --- |
| Native Metal |600|8.327 /8.924ms|240,599,040bytes peak child RSS (~229.5MiB)|[JSON](evidence/performance/m1-player-native-release.json),[actual pixels](evidence/performance/m1-player-native-release.png)|
| IAB WebGPU |600|8.300 /9.500ms|NOT-RUN browser/GPU memory|[JSON](evidence/performance/m1-player-web-release.json),[exact console event](evidence/m1/player-web-benchmark-console.json),[actual download](evidence/performance/m1-player-web-release.png)|

Physical1280×720; one actor; task-owned compilers/tests/other Nvwa renderers stopped; native measurement used a blank browser, Web used no native renderer. User applications were not controlled. The recent sample window was after the finite work completed; it measured the held final pose, not continuing animation or GPU/presentation timing. M0's continuous-idle cadence remains the separate animated baseline above. Native capture completion upper bound16.965s includes15s requested warmup and is not exact first presentation.

[Actual gzip report](evidence/m1/web-size-report.json): unique HTML+generatedJS+Wasm+GLB+measured work=14,179,929bytes (shipped9s demo=14,179,914). Raw Wasm74,738,859bytes,gzip13,030,222. These are file-size sums, not a cold-network trace; duplicateGLB transfers remain issue#6. Cold Web first presentation/GPU timestamps/browser memory are still NOT-RUN.

Reproduce native after closing other renderers/heavy tasks:

```sh
python3 scripts/benchmark-native.py --seconds 15 --label m1-player-native-release --player --work docs/evidence/m1/web-sequence.nvwa.json
cp docs/evidence/m1/web-sequence.nvwa.json dist/web/works/exchanged.nvwa.json
```

Then open `http://127.0.0.1:9201/?benchmark=1&player=1&work=works/exchanged.nvwa.json`, read the actual `NVWA_EVIDENCE` console.log record and use the benchmark PNG button. Keep viewport emulation off and only one renderer running.


## Current single-transfer network checkpoint

The current93-test release has an actual loopback HTTP comparison against PR18 `de9dac0`. Both are no-store, fresh task URLs with one renderer and no competing heavy build. Successful GLB GETs are2→1; actual gzip response bodies are2,258,162→1,129,081bytes. All initial response bodies are21,656,114→20,541,440bytes; that also includes bundle-version changes and one fewer404 metadata body. Current unique gzip file sum is20,539,196bytes (demo Player20,539,719). Directory HTML in this trace is uncompressed; response-body sums exclude headers and TCP overhead. [Capture, source identities and limits](evidence/single-transfer/ACCEPTANCE.md) distinguish these quantities. This measures avoided transfer, not cold Wasm compilation, GPU startup, exact first presentation, browser memory or current cadence. Native functional Ready telemetry is not a benchmark; locked-screen black captures do not establish visual presentation. Earlier performance snapshots remain historical.


Later acceptance update: Derek manually unlocked the Mac. The same current native binary (`3be9380f…`) now exits0 with a visually inspected real character playing wave, revision9 and18 joints/4 morphs/3 timeline entries. [Unlocked native evidence](evidence/single-transfer/native-unlocked.png) supersedes only the earlier blocked visual result; both black captures remain retained failures. This is a functional smoke, not a current performance benchmark. PR18 is merged at `07858fe6b5d6062200d28df654c5ce53ad89007b`, with #1/#19 closed; #2/#3 remain open. PR20 remains pending merge; PR21 completes local acceptance and is pending review/merge.
