# Actual release measurements

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
