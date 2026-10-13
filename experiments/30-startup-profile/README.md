# Bounded native startup profiling (#4)

Both release experiment binaries compiled under the root-granted single Cargo
writer lease. Root package identities/checksums and all521 dependency feature
sets match. Exact frozen binaries and build/API-failure records are retained.
Two actual native launches and native2 profiling completed under the accepted
lifecycle freeze and exclusive GPU/UI lease. Both failed actual character/UI
visibility. The lease was returned to root. The later matching baseline Web
control passed HTTP/image reconciliation; pixel controls remain held. See
REPORT.md, NATIVE-RESULT.json, WEB-REPORT.md and WEB-RESULT.json.

The candidate is a standalone wrapper around the unchanged production
`nvwa_studio::build_app()`. It records a private monotonic clock immediately
before app construction, after construction, first Startup system, first
runtime readiness observation, and the screenshot callback. A render-subapp
hook records return from the installed render system and a bounded GPU queue
completion callback. These are different boundaries. None is a physical
presentation timestamp. A separately inspected actual PNG or cua screenshot
can prove that pixels exist by an observation time only.

Plan: at most two native runs with the same real character Work, release build,
1280x720 physical viewport and scale1. Canonical input is the root-supplied
actual saved Work, revision3, with finite idle/wave/turn3+3+3seconds; preserve
its exact bytes. Run1 requested 12 seconds of readiness warmup. Root approved 35 seconds for
run2 plus a documented foreground Raise action after run1 visibility failed.
They separate finite active sequence from completed hold, where observed. They are not sustained
animation measurements. Run1 has only sparse marker logging and
exact-process RSS sampling. Run2 adds bounded macOS `sample` stack profiling
and one exact-process memory map observation. Sampling overhead is reported.
One matched frozen Web fresh-prefix/no-store run follows if the root provides
the matching web build and exact loopback port. Competing compile and renderer
jobs must stop before each formal run; existing user apps and caches remain.

The root owns the exact executable and launch authority. UI interaction and
window screenshots use the advertised `cua_repl`; no shell UI automation or
alternate screenshot mechanism is permitted. Never launch the older installed
`dev.nvwa.studio` based on its bundle identifier alone.

Installed-source findings (read-only, 2026-10-13):

- Bevy0.19.1 `render_system` runs its RenderGraph, submits screenshot/readback
  commands, calls `window.present()` when needed, then collects screenshots.
  The return boundary says those CPU operations returned; it does not say the
  compositor displayed the character.
- wgpu29.0.4 `Queue::on_submitted_work_done` reports completion of previous
  submissions. Callback delivery depends on later submit/poll/event-loop
  activity. It is neither a GPU timestamp nor a display timestamp.
- Bevy RenderDiagnosticsPlugin's documentation says Metal/WebGPU records CPU
  times only. The implementation allocates timestamp queries only when the
  device has TIMESTAMP_QUERY enabled. Record actual enabled feature evidence
  and actual diagnostics rather than inferring support from the backend name.
- Bevy's current device descriptor has `Trace::Off`. Enabling a trace or other
  renderer configuration would change the candidate and requires a decision.
- `sample`, `vmmap`, `footprint`, and `xctrace` binaries are installed. Actual native2 sample and vmmap headers prove collection of the exact app. No permission or global setting
  change is authorized to make profiling work.

VERIFIED — release compilation, exact dependency/feature comparison, nine real
headless lifecycle controls and frozen artifact identities. These controls prove
no rendered pixels or native character startup.

PARTIAL — actual renderer/readback execution, runtime boundaries, stack sampling
and process memory observations; both actual captures and live native2 surface
failed character/UI visibility.

NOT-RUN — physical first presentation, fully cold OS/shader/GPU state, useful GPU
timing/total memory and native stall attribution.

VERIFIED — root-collected baseline Web HTTP/image reconciliation; 19 pure-data
red/green controls preserve experiment24 archives unchanged.

All exact paths, hashes, invocation, process inventory, source/build inputs,
captured PNG identities and measurement-clock definitions go in this directory
or private `.work/m11-startup/`. Publication belongs to root.
