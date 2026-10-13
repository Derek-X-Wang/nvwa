# Frozen baseline native startup result — 2026-10-13

PARTIAL — two actual bounded native launches collected runtime, callback, CPU
diagnostic and process evidence. Both failed the actual character/UI visibility
check. No exact physical first presentation was measured. The GPU/UI lease was
released to root; no pixel app or Web server was started by this worker.

The unchanged baseline is `045d8abc685760d09ba05afec0e40a811a282d1f`.
This report concerns the standalone instrumented wrapper around baseline
`nvwa_studio::build_app()`, not the later integrated UI/runtime commits or the
root's separate product control. The wrapper adds CPU diagnostics in both runs,
sparse render markers and a previous-submission GPU completion callback. Run2
also adds stack sampling and one memory-map snapshot. These add overhead.

## Actual visibility failure

Both actual Bevy readback PNGs are RGB8, 1280 × 720, 15057 bytes and entirely
black: all 921600 pixels are `(0,0,0)`. They were independently viewed and
decoded. Neither contains the character or editor UI. The saved images are:

- `.work/m11-startup/captures/native-1/character.png`
- `.work/m11-startup/captures/native-2/character.png`

Native1's exact Cua app returned a real titled window. Its later screenshot
request failed `procNotFound` after the finite app exited. Native2 used the
root-approved extended warmup and fresh advertised window `Raise` action,
followed by AX inspection and an immediate in-lifetime Cua screenshot. That
image showed titlebar/traffic lights and blank dark content, with no character
or editor UI. The Cua screenshot is retained as a tool image in the conversation;
the current API advertised no local screenshot-file persistence operation.
`captures/native-2/cua-observation.json` records its wall-clock request bounds.
There is no invented local Cua PNG path.

The black image does not prove that macOS was locked. The actual adapter
inventory had no explicit lock/unavailable reason. Lock state remains UNKNOWN.
Root is handling the separate noninstrumented product control and any next
decision. These attempts do not establish a cause for the blank output.

Subsequent root evidence: its separate fresh integrated product control also
showed blank content. A later fresh root Cua AX query explicitly reported
`The Mac is locked and automatic unlock could not...`. This establishes a
later availability blocker. It does not establish lock state at either native
measurement or explain their blank images. Root verified and stopped its own
product-control process. Pixel execution remains held until a human unlock or
other verified availability change; this worker initiated no further launch.

## Measured boundaries

The following seconds are from the experiment's own process `Instant` origin,
immediately before `build_app`. They are not launcher, compositor, GPU-clock
or browser-clock times.

| Boundary | Native1 | Native2 | Meaning |
| --- | ---: | ---: | --- |
| App construction returned | 0.391636 | 0.123961 | CPU construction |
| Startup system | 1.000616 | 2.701490 | Scheduled CPU observation |
| First render system returned | 2.304978 | 2.837977 | CPU render/present-enqueue operations returned |
| Previous submissions GPU callback | 2.336112 | 2.871238 | Completion callback delivery, including polling delay |
| Runtime ready observed | 2.347883 | 3.018241 | Loaded runtime state; 9 meshes, 9 skins, 18 joints |
| Playback completed observed | 14.522582 | 11.941079 | Finite timeline at 9 seconds, playing=false |
| Screenshot readback callback | 14.513850 | 37.890567 | Actual image received; image was black |
| App run returned | 14.570948 | 37.959136 | Rust AppExit::Success |

Native1 requested12 seconds of readiness warmup. Native2 requested 35 seconds
under a root-recorded protocol change, with the same frozen binary and 50-second
external guard. Native2 also received foreground `Raise` and profiling. Thus
the two capture times are not directly comparable. Native2's observed completed
hold before capture was about 25.95 seconds. Native1 observed completion after
its callback; no three-second hold is inferred. Neither run measures sustained
animation performance.

Production `NVWA_EVIDENCE` uses Bevy `Time<Real>` since first update, a different
origin. Its asset-ready/capture-callback seconds were 1.303554/13.510730 in run1
and 0.163030/35.187948 in run2. Its fields named `first_visible_*` are raw
callback fields; their name does not make a black readback a visibility bound.
Main-loop cadence p50/p95 was 1.511625/1.759500 ms and 1.544209/1.747042 ms over the
recent 600 samples. These describe the failed-content process loop, not display
FPS or accepted character performance.

The bundle launcher records host monotonic and wall timestamps before exec,
exact PID, kernel birth identity, binary hash, argv, cwd and bundle. Cua launch
request bounds are separate wall-clock observations. Do not subtract these
from the process `Instant` or Bevy origins without a verified alignment.
The derived `NATIVE-RESULT.json` retains all markers and raw evidence by domain.

## Actual device and profiler capability

Both runs used Apple M2 Pro / Metal, physical viewport1280 × 720 atscale1.
Actual enabled device features included `TIMESTAMP_QUERY` and
`TIMESTAMP_QUERY_INSIDE_ENCODERS`; queue timestamp period was 1 ns. Run1's one
diagnostic observation contained CPU entries only. Run2 contained CPU entries
plus `render/clustering/elapsed_gpu = 0.0ms`. The installed diagnostics docs
describe Metal CPU-only behavior, while the implementation gates queries on
actual enabled device features. Preserve the observed zero entry; it is not
a useful timing of the rendered character. Exact GPU pass timing remains
unverified.

Native2's `/usr/bin/sample` attached to exact target PID1327. Its header says
`live task`, ARM64, launchd parent, Date/Time 02:52:51.693 and LaunchTime
02:52:51.105 on 2026-10-13 (-0700). The command log confirms sampling completed
for requested 4 seconds at 1 ms; owned child waitpid exit was 0. The main-thread
call graph has 871 samples, including 770 under `NSApplication run`, 228 under a
parking branch, 131 under one pipeline-queue branch and 39 under its ShaderCache
branch. These are nested observations, not additive durations. They do not
attribute native1 delays, historical startup stalls, or blank output to shaders.
Run2 followed run1 with caches preserved; neither is fully cold OS/shader/GPU.

The `sample` header reports footprint 153.5M, peak 157.4M in provider units. The
early `vmmap` snapshot ofPID1327 reports 27.7M, peak 27.8M, Date/Time 02:52:51.886.
Its target type is `corpse`; that snapshot label is not crash evidence. Later
live Cua observation and Rust success are retained. Its graphics region rows
show IOAccelerator graphics virtual 1024K/resident 176K, owned unmapped graphics
virtual 528K/resident 16K, IOSurface virtual 16K/resident 0. These are partial region
observations, not total or peak GPU memory. Process RSS sampling observed
maximum 206944 KiB over 141 samples in run1 and 225136 KiB over 345 in run2; these
sampled maxima are not physical-footprint or GPU-memory totals.

## Frozen inputs, build and cleanup

Startup binary SHA256:
`6a49bc165991bc6353f69074e225a8b9644aa86154f48df7055f793ef0a3605f`.
Pixel binary SHA256:
`504c4bb90125b103df0d4d49148d0597226790ad9a18e9f663f8107b3e1e55fd`.
Canonical actual GUI Work SHA256:
`cacf849f0918648a1a970452d0c33f195c5ad89fd7f6d9e58669d587d0789768`.
It is schema1/revision3, zero parameters and idle/wave/turn 3+3+3 seconds.
CC0 fixture GLB SHA256:
`f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6`.
Profile SHA256:
`b7604ebdfb8b090073adead456f78fbf09779c23823b419986e57159bd9e0353`.

The 42-input root-approved freeze pins exact baseline source, experiment source,
locks, dependencies, Work, fonts and asset profile. Both candidate dependency
graphs match all 521 root external dependency feature sets and 524 package
identities/checksums. Builds used offline/locked release/jobs1 under an exclusive
writer lease, initial storage >32 GiB and bounded 30-minute/watchdog controls.
Startup and repaired pixel builds passed in 521.94 and 433.54 seconds. The first
pixel E0308 API compile failure is retained; repair changed only experiment
root-Ui use for installed egui0.36. Root Cargo.lock remained unchanged.

The final lifecycle source pins launcher SHA`d26780c09dc00bb01b30c05b2dcdb741faf344eb43142182d49124f0d0831f40`
and guard SHA`83185b1713123a203b38de42477d10b44d6a440a8cd93a14498842cabe6cafda`.
Nine real owned headless controls passed; earlier false-exit/partial-marker and
profiler cleanup failures remain archived. These controls are lifecycle proof,
not renderer proof. Both native targets exited within their guard deadlines,
without TERM/KILL, and both receipts say `exit_verified`, no unknown inspection,
owned profiler cleanup verified. Native2 sample and vmmap exited 0 by owned-child
waitpid. Final bounded ps inspections found no owned target/guard/profiler PIDs
85149,85152,1327,1364,1366,1369. Native1 and2 compile/launch/resource inventories
are retained in their raw receipts. No owned tabs/server remain; pixel app was
never launched.

NOT-RUN — exact character first physical presentation, successful actual native
character/UI pixels, useful GPU pass timing, total GPU memory, fully cold state,
native stall attribution, browser memory, and independent tab raster controls.
The one matched frozen Web control subsequently passed exact HTTP reconciliation
and actual character/UI image inspection; see WEB-REPORT.md and WEB-RESULT.json.
Any later integrated product/control result remains a distinct source/build cohort.
