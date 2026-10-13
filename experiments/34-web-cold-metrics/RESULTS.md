# Actual bounded Web results, 2026-10-13 (#4)

PARTIAL — Three actual IAB Chrome155 loads reconcile frozen release Wasm, the
real humanoid and the same exact revision0 idle-loop Work at1280×720/DPR1.
Production WebGPU CPU boundaries and30 JS heap subset samples per load are
retained. Exact root Cua console and original screenshots prove Ready UI and actual
character pixels; the worker independently inspected the retained images. The diagnostic GPU
timestamp attempt ran but did not produce an accepted GPU timing result.

The timestamp-query attempt actually ran and failed timing acceptance; `NOT-RUN`
labels the unavailable accepted metric, not absence of an attempt. No source,
wrapper, server or raw capture was changed to repair that GPU result.
No additional load ran. Native measurements remain a separate root-owned task.

## Measured boundaries

All values below are browser monotonic milliseconds relative to each separate
navigation `timeOrigin`. Bootstrap status hiding, texture acquisition and submit
return are CPU observations. They do not identify a rendered character or first
physical presentation.

| Boundary | Baseline1 | Same-tab/URL contrast | Timestamp variant |
|---|---:|---:|---:|
| Boot status hidden observed | 684.4 | 909.7 | 895.5 |
| Production device promise observed | 699.9 | 932.8 | 919.5 |
| First production texture acquisition returned | 893.2 | 1126.0 | 1118.6 |
| First production queue submit returned | 956.0 | 1192.1 | 1188.3 |
| Wasm HTTP responseEnd | 412.2 | 588.7 | 518.6 |
| Exact Work HTTP responseEnd | 756.8 | 969.5 | 973.6 |
| Real GLB HTTP responseEnd | 1158.2 | 1399.0 | 2124.3 |
| Server response-body bytes, inclusive | 20,571,754 | 20,571,735 | 20,578,415 |
| JS used-heap estimate minimum bytes | 10,516,084 | 9,668,581 | 9,471,433 |
| JS used-heap estimate maximum bytes | 19,292,318 | 21,151,025 | 20,179,465 |

The first submit precedes real GLB response completion in all three cases.
It can include uploads, offscreen or empty-scene work. Character association is
NOT-RUN. These three results do not establish repeated-run variance, startup
regression, displayed FPS or a steady-state performance budget.

`performance.memory` is a browser-exposed JS heap estimate that may be coarse
or shared. Its30 one-second samples exclude process RSS, complete Wasm memory,
GPU allocations and physical footprint. They cannot be compared to native RSS
as if they measured the same memory domain.

## Actual timestamp attempt

The variant explicitly requests the supported `timestamp-query` feature and
changes production device/pass/finish options. Browser device features contain
`timestamp-query` in all three actual loads. No dummy pass, additional device
or extra queue submission was introduced.

Eight actual startup passes over eight encoders were instrumented. Six mapped
records survive: four compute records (`bin unpacking` and
`early_mesh_preprocessing`) contain zero start/end pairs; two `egui_pass` records
contain differences of65,536ns. Two other results record
`Error: nonmonotonic GPU timestamps`. The retained variant status is `NOT-RUN`.
The zero pairs do not establish zero GPU cost, and the two UI spans do not
establish character or full-frame cost. The cause of the invalid query results
is unprofiled. No shader-compilation or driver attribution follows.

The GPU query clock is unsigned64-bit nanoseconds with implementation-defined
coarse precision. It is uncalibrated to browser/navigation, host screenshot and
Bevy clocks. CPU map callback observations at2112.1–2112.5ms are separate from
the GPU query values. They precede GLB responseEnd2124.3ms on the browser clock;
they provide no post-ready character workload association.

## HTTP, input and source identities

All three canonical checker results are `PASS_BOUNDED`, which means exact
HTTP/body/source/geometry reconciliation and observed CPU-call boundaries. It
does not change the timestamp variant's `NOT-RUN` result.

The same production input bytes were served in every load:

| Input | Identity bytes | SHA256 |
|---|---:|---|
| Wasm | 85,605,719 | `d890dfee73e9eeeee6ce3d82f255c79979e8c8b6bed90243c6101f8e1c1763a8` |
| JavaScript | 123,623 | `9ff532cbedc6a814c4b8337c4b82f436de452e7b7fbc8c9e58bfda2e90ad6c5c` |
| Real humanoid GLB | 3,827,840 | `f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6` |
| Common Work | 1,624 | `ff0b8e36adfc3ebadc5fc700a4c760f6f551273b56e85bf336563e18b63eb445` |

Wasm and GLB transferred as exact verified gzip bodies of19,409,567 and
1,129,081bytes. Work transferred1,624bytes without changing `dist/web`.
The baseline diagnostic collector is9,618bytes; the variant collector is
16,298bytes. Every load has one separately reconciled optional GLB metadata404
of28bytes. Baseline1 additionally has the ordinary same-origin favicon404 of
19bytes. Its exact observed Chrome155 transfer estimate is319bytes, including
300 estimated overhead; that is not a measurement of wire header bytes.

Initial baseline acceptance rejected the favicon. The original CLI2 failure,
independent review's previously accepted incorrect transfer mutations, corrected
20/318/320 mutation rejects, source freezes and unchanged raw first dataset all
remain retained. No arbitrary outside URL or unexplained404 is filtered out.
The correction changed only checker/tests; server, collectors, production code,
old experiment24 and the actual measurements stayed unchanged.

## Cold conditions and visual evidence

Each load has a separate actual navigation clock. All responses use no-store
with positive transfer and exact complete bodies. The contrast uses the same
browser/tab54/URL after an intervening `about:blank` pause. It is not a literal
reload and its body transfers remain no-store. It does not measure an HTTP
cache hit. The final variant uses a fresh URL prefix with changed diagnostics.

The live Cua IAB adapter exposes no isolated fresh browser-process/profile,
compiler cache, shader cache, driver state or OS file-cache control. Those cold
domains remain NOT-RUN. User apps and retained system/browser caches remain
uncontrolled. No alternate browser driver or profile reset was used.

Root's first and second actual Cua screenshot originals and exact provenance
are retained. The host UTC capture brackets are respectively
21:07:29.934–21:07:30.090 and21:21:00.455–21:21:00.724. They are observation
upper bounds only. No clock calibration establishes a conversion to navigation
or Bevy time. Exact first physical presentation remains NOT-RUN.

The timestamp case first shows only loading status at21:27:56.606–56.720UTC,
then the real humanoid and Ready UI at21:28:12.185–21:28:13.435UTC. Original
loading/Ready image SHA256 values are `7db7085901c85cb5927c81996c31931ac162ad9a1a56e01340d0a2e1682ae7e8`
and `35d17805e8858da00fbd764147fd2d7de0f3d91ddd1a75df371c1b0936960851`.
These are separate host observation brackets; no first-display time follows.

The exact three `NVWA_EVIDENCE` console records are bound independently to the
canonical browser capture hashes/run IDs/navigation URLs. They report Ready,
revision0, one idle timeline,18 joints,9 meshes,9 skins and4 morph weights.
All have no error/timeout and use the Bevy clock `bevy_TimeReal_since_first_update`.

| Bevy-clock/runtime boundary | Baseline1 | Contrast | Timestamp variant |
|---|---:|---:|---:|
| First AssetReady seconds | 0.4056 | 0.4240 | 1.1601 |
| Screenshot callback seconds | 15.4356 | 15.4766 | 16.5365 |
| Main-loop cadence p95 ms | 21.0 | 21.1 | 20.0 |
| Retained cadence sample count | 600 | 600 | 600 |

Callbacks include the production-requested15s readiness warmup and GPU readback;
`capture_file_bytes=0` on Wasm does not prove a downloaded file. The legacy log
name `first_visible_upper_bound_seconds` describes that delayed callback, not
actual first character/display time. Cadence is not displayed FPS or GPU time.
Console UTC, browser `timeOrigin` and Bevy elapsed clocks remain separate. The
exact console JSONL SHA256 is `2920e810e9ed3b59e1978b944ec4639ea3bf8d79ab364031bbdb8c6475d86273`.

## Reproduction and retained packets

The commands and API limits are in README.md. The completed protocol used
one baseline server with `--port 9205 --runs 1`, two navigations to its printed
Work URL separated by blank-page quiescence, then a new one-run server with
`--timestamp-variant`. Total Nvwa loads:3. Root stopped builds before formal
measurement and owned the exclusive browser/GPU lease throughout.

Canonical public archive data:

- `docs/evidence/bounded-perf-20261013/web/baseline-http/1c1f52dcadf5449ba40195226e16f287-attempt1-browser.json`
- `docs/evidence/bounded-perf-20261013/web/baseline-http/1c1f52dcadf5449ba40195226e16f287-attempt2-browser.json`
- `docs/evidence/bounded-perf-20261013/web/timestamp-http/73223af7968848068eb57b2768c478eb-attempt1-browser.json`
- Each public archive directory's frozen manifest, request/receiver logs, wrapper, collector and checker result.
- `docs/evidence/bounded-perf-20261013/web/preparation/checker-freeze-favicon319.json` and preserved predecessor freezes.
- `docs/evidence/bounded-perf-20261013/visual/` for root's exact screenshot source packets.

Use `check_metrics.py` with each public archive capture/manifest/request set,
exact run ID and attempt1/2 as applicable. The original reviewed runtime source
freeze is `docs/evidence/bounded-perf-20261013/web/preparation/checker-freeze-favicon319.json`,
SHA256 `5bedb932f5bcab96bb45c7d4038358085b30c1388bc570295e3e2df7b9eb133f`.
Its eight helper/source identities describe what actually ran. This report and
ACTUAL-WEB-RESULT.json are later aggregates and do not replace that source freeze. ACTUAL-WEB-RESULT.json and the private
`.work/m11-perf/web/actual-web-summary.json` include raw hashes, source/body
identities, every Resource Timing size/clock, enabled features and all retained
variant errors. Lightweight reconciliation matched all three stored checker
packets. No CPU tests or builds ran while root's native GPU lease was active.

VERIFIED — All three actual HTTP/CPU boundary packets; frozen input identities;
measured1280×720/DPR1;30 JS heap subset samples per load. Earlier37 Python and
unchanged Node controls are retained.

VERIFIED — Exact three production console sources and original baseline/variant
Ready images plus the earlier variant loading image. Static worker inspection
confirms actual character/Ready pixels. Host screenshot brackets are retained.

PARTIAL — First visible observation upper bounds only; actual timestamp-query
attempt ran but failed valid GPU timing acceptance.

NOT-RUN — Exact first display, fully cold process/compiler/shader/driver/OS
state, accepted GPU timing/character association, browser process RSS and total
GPU memory. The timestamp attempt's invalid results are preserved.

Cleanup: root confirms baseline PID66834 and timestamp PID62645 exited0,
port9205 listeners are absent, tab54 is closed and the viewport override is reset.
The worker started no formal app/browser/server/GPU process.
