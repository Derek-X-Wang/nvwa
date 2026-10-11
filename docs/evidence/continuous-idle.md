# Continuous idle — matched Work, actual release runs

Both runs use identical `examples/default.nvwa.json` SHA256 `ff0b8e36adfc3ebadc5fc700a4c760f6f551273b56e85bf336563e18b63eb445`: revision0, one natural looping idle action, default morph values. Both use Studio, physical1280×720, scale1, the same GLB SHA256f13e0189… and unchanged93-test native/Wasm releases. Runs were sequential with only one task renderer. Start/end inventories detected no compiler or competing Nvwa process. User applications and OS/GPU caches were not controlled; no claim that those inventories cover every instant.

| Actual measure | Native Metal/M2 Pro | WebGPU/IAB |
|---|---:|---:|
| Recent loop cadence p50 |8.304ms|16.600ms|
| Recent loop cadence p95 |9.366ms|18.000ms|
| Samples |600|600|
| Asset readiness, Bevy clock |0.0940s|0.6398s|
| Playing / completed at benchmark capture |true / false|true / false|
| Sampled maximum exact-child RSS |216.77MiB|NOT-RUN|

These specific continuous-idle cadence samples are below33.33ms at p95. They are main-loop scheduling samples, not GPU durations or displayed FPS. Different native/browser scheduling and measurement overhead remain: native samples exact-child RSS about every0.1s; Web uses passive observers and console/DOM reporting. A full performance budget verdict is unavailable.

The earlier finite revision9 native run had39.026ms p95 and is retained. It used different Work/cache conditions, was completed by capture, and outside-project compilers were discovered afterward. This later idle case does not prove the earlier delay's cause or validate all three-action/interactive workloads. Do not cherry-pick it as a universal30fps pass.

The native saved benchmark PNG was visually inspected. Web's earlier Rust callback still has no persisted file proof; the later explicit canvas PNG was saved and inspected at59.2795s on document clock. It shows the real character during the natural idle loop. No earlier first-presentation timestamp is inferred from the later image.

[Native raw report](native-startup/native-continuous-15s/report.json), [native capture](native-startup/native-continuous-15s/capture.png), [Web raw report](web-startup/continuous/report.json), [Web canvas](web-startup/continuous/canvas.png). Web raw/gzip/actualserved identities and post-run freeze passed; one GLB GET wrote1,129,081compressed-body bytes. Diagnostic5 preflight GETs are excluded from6 browser GETs (20,551,876body bytes).

Reproduce native using experiment12 with `--work "$PWD/examples/default.nvwa.json" --seconds15 --output NEW_ABSOLUTE_DIRECTORY` plus the required binary/source/isolation/cache arguments from its REPORT. Reproduce Web using experiment14 protocol in a disposable dist copy with this Work and its deterministic gzip sidecar at `works/default-m0.nvwa.json`; omit `player=1`. Keep exact input hashes, start/end process inventories, visible/focused page and the separate HTTP logs. Close the tab/server after capture.

VERIFIED — Same Work and actual release character continuously playing on both targets;600 cadence samples each, reviewed real PNGs, no runtime error and unchanged inputs.

NOT-RUN — Exact first presentation, cold compiler/GPU state, GPU timing/memory, true peak memory, repeated-run variance, full three-action/interactive workload budget and other platforms. #4 stays open.
