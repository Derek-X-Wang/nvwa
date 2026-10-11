# Native startup and memory — actual release probes

Later matched continuous-idle follow-up is separately recorded in [actual evidence](../continuous-idle.md). Earlier unfavorable/nonisolated results below remain retained.

Both captures show the real rigged humanoid. The binary is the93-test release from PR21; no build was run for these probes. Work revision9 is the same exchanged9.5-second, three-action document.

| Probe | Process→capture evidence receipt | Sampled maximum child RSS | Bevy asset ready | Recent cadence p50/p95 | Samples | State at capture |
|---|---:|---:|---:|---:|---:|---|
| [native-1s](native-1s/report.json) | 4.010s | 193.84MiB | 0.534s | 8.068/8.507ms | 4 | playing idle |
| [native-15s](native-15s/report.json) | 16.735s | 187.89MiB | 0.189s | 8.609/39.026ms | 600 | completed, final turn pose |

The1s cadence has only4 samples. The15s capture is after the finite work ends; its recent600 samples are not a continuous-animation benchmark. The measured39.026ms p95 is retained as an unfavorable observation, without claiming a30fps pass. RSS sampling can perturb scheduling.

At the initial process inventory no Nvwa renderer or cargo/rustc/clang task was present. After the15s run, independent GMM compilation processes were found; their start within the measured interval was not recorded. They were outside this task and were not stopped. See [later process inventory](later-competing-compilers.json). Thus stable isolated performance comparison is **NOT-RUN**. The isolation-note string records the start condition only.

The evidence receipt includes requested readiness warmup, capture completion and pipe delay. It bounds the reviewed capture, not the first screen presentation. Bevy times start at the first update and omit earlier process startup. Fresh processes used existing OS/shader caches. Sampled RSS omits missed peaks, descendants and GPU/unified allocations.

VERIFIED — Both exact children exited0; inputs were unchanged,18 joints/4 morph weights/3 timeline items loaded; new1280×720 PNGs passed validity/freshness/black checks and root visual inspection. Raw streams, RSS samples, failure fields and visual reviews remain beside each capture.

NOT-RUN — Exact first presentation, cold OS/compiler/GPU caches, GPU duration, true peak memory and an isolated stable performance verdict.
