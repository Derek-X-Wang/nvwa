# Root-granted build and lifecycle requirements

Experiment compilation completed under the returned Cargo lease; no app launch is authorized yet. Root retained the sole compile lease elsewhere after storage recovery.
Both candidate manifests match product dev/release profiles and exact installed
Bevy0.19.1/bevy_egui0.42.0 and craft-ui commit. They add no root dependency or
feature. `nvwa-studio` is a path dependency, so Cargo resolves the full existing
production feature graph. Verify actual resolved features against the root
cohort before claiming cache reuse. Each standalone Cargo.lock, if generated,
belongs only to its experiment. Root Cargo.lock remains protected.

Root must assign an exact Cargo target directory, profile, deadline and single
writer lease. Compile commands are proposed, not executed:

```
cargo build --offline --release --manifest-path experiments/30-startup-profile/Cargo.toml --jobs 1
cargo build --offline --release --manifest-path experiments/31-ui-pixels/Cargo.toml --jobs 1
```

Root may choose dev for the tiny pixel case; dev pixels do not supply release
startup measurements. Record a manifest of all product source inputs, root
lock/toolchain/manifests, Work/assets, dependency source identity, candidate
sources, resolved experiment locks, binary hashes and actual build commands.
An old target cache by itself proves no current binary cohort.

Native lifecycle needs the root's decision on exact supported launch route:

1. Preferred cua-only UI route: root creates a uniquely identified task-owned
   app bundle under private `.work/m11-startup/`, with exact frozen executable
   and a fixed task launcher. Cua `getApp(exact_absolute_bundle_path)` launches
   that bundle. The launcher sets only task environment/arguments, redirects
   stdout/stderr to exact empty private files, writes launch monotonic/wall
   bounds, and execs the exact verified binary. It receives the root-assigned
   Work path, `--benchmark --smoke --smoke-seconds 12 --timeout 55 --capture`
   arguments after checking the current product parser. Launch request bounds,
   child main Instant, Bevy Time<Real>, native sample timestamps, and cua
   observation bounds remain separate clocks.
2. If root explicitly permits programmatic process launch for the CLI smoke
   run, use one bounded task launcher with exact executable/arguments/cwd and
   stdout/stderr pipes. Cua remains the sole UI/screenshot controller. This
   choice must be explicit because process spawning launches a native window.

Run1 collects exact child RSS and sparse markers only. Run2 additionally calls
installed `/usr/bin/sample` for at most4seconds with a fixed sample interval,
and one `/usr/bin/vmmap` on the exact task PID. Capture failures are retained;
no permission changes or alternate profiling install is allowed. Do not treat
shared virtual-memory mappings as total GPU allocation. Keep sample overhead,
stack attribution and callback delay explicit. Stop by the task's own finite
smoke exit, otherwise the external identity-safe watchdog deadline cleanup. It begins
cleanup by50seconds, verifies exit after TERM, and rechecks the same frozen
PID/kernel start/binary hash before KILL. Profiler children clean up concurrently
with direct owned waitpid receipts; failures remain blocked.

Pixel lifecycle uses one task bundle/process with `NVWA_PIXEL_OUTPUT` pointing
to an existing empty absolute private directory. The app makes three finite
captures, then exits. The checker commands must pass both normal files and
reject mutant-profile against the unchanged normal-profile reference. Missing
files are errors, not renderer skips. Source inclusion executes unchanged
production `EditorLayout::draw_tabs`, fixed raw egui time1 and no pointer.

Root supplies the matching frozen Web cohort, server owner, exact assigned
free9200–9299 port and one fresh no-store URL if it authorizes the Web control.
Use a new IAB tab through cua only, preserve unrelated tabs, then close only
the created tab. No browser flags, persistent settings, global cache clearing
or permission changes. Browser memory/GPU metrics unavailable to the advertised
adapter remain NOT-RUN.

Process/resource inventory: currently none created. No GPU/UI lease has been
granted. Reinspect exact app state and process inventory before execution;
release the GPU/UI lease explicitly with exact cleanup evidence afterward.
