Native display, GPU command duration, and memory experiment for issue #4.

The diagnostic executable calls `nvwa_studio::build_app()` unchanged. Its only engine change is the retained `wgpu-hal-metal-probe.patch`, applied to the exact local wgpu-hal 29.0.4 source. The accepted release executable remains a separate baseline. This variant adds CPU observers and three GPU screenshot readbacks, so timings must be identified as diagnostic measurements.

The root controller owns all app launches, foreground observation, and GPU profiling. No worker launches Nvwa. Maximum three native launches total: one accepted release baseline, one diagnostic startup, and one diagnostic process-warm contrast. The same revision-zero looping real humanoid work is used in each run at physical 1280x720 and scale factor 1. The common contract is `.work/m11-perf/measurement-contract.json`.

Measurement boundaries:

| Event | Exact meaning | Limit |
|---|---|---|
| `before_build_app` | Wrapper CPU marker before the unchanged production builder | Excludes executable loader time; retain external launch clock separately |
| `first_runtime_ready_observation` | Production `RuntimeStatus.ready` observed by a main-world system | Does not establish character pixels |
| `present_registered` | Observer registered on the actual Metal drawable at wgpu's existing presentation seam | Scheduling only |
| `drawable_presented_callback` | Actual `MTLDrawable.addPresentedHandler` delivery and its `presentedTime` | Require nonzero time; a zero time is skipped/unpresented. Surface content still needs pixel observation |
| `command_completed` | Completion of a selected existing Metal command buffer | Require Completed status and nonzero ordered GPU start/end. Duration concerns that command buffer, not frame latency |
| screenshot callback | Actual production Screenshot GPU readback, saved as a PNG | Inspect exact hashed pixels; this is an observation upper bound, not physical display time |
| libproc sample | RSS and physical footprint for an exact PID and kernel birth before and after the read | Samples are not a continuous peak; kernel lifetime max footprint is separately labeled |
| Metal allocated sample | `currentAllocatedSize` from the real device used by the command queue | Device resource allocation metric; not total GPU memory. Do not add it to RSS or footprint |

Raw clocks are preserved. The wrapper brackets its process-relative `Instant` read with `CLOCK_MONOTONIC` nanoseconds. Each Metal callback brackets a `CACurrentMediaTime()` host-clock read with `CLOCK_MONOTONIC`. Metal GPU start/end and drawable presentation use host seconds. Converting a presentation time uses that callback's measured calibration interval. Keep the interval width as uncertainty; do not subtract wall timestamps or process `Instant` directly from Metal times. Callback delivery can lag the displayed time. A callback timestamp is not display latency.

Apple primary sources: [GPUStartTime](https://developer.apple.com/documentation/metal/mtlcommandbuffer/gpustarttime), [GPUEndTime](https://developer.apple.com/documentation/metal/mtlcommandbuffer/gpuendtime), [addCompletedHandler](https://developer.apple.com/documentation/metal/mtlcommandbuffer/addcompletedhandler(_:)), [presentedTime](https://developer.apple.com/documentation/metal/mtldrawable/presentedtime), [addPresentedHandler](https://developer.apple.com/documentation/metal/mtldrawable/addpresentedhandler(_:)), [currentAllocatedSize](https://developer.apple.com/documentation/metal/mtldevice/currentallocatedsize). The installed Apple SDK headers and exact objc2-metal 0.3.2 generated declarations independently confirm return types and zero-state semantics. Host checked: macOS 27.0.1 / build 26A434.

Bevy 0.19.1's `renderer::render_system` runs the graph and submits work before calling `ExtractedWindow::present`. That only schedules presentation. Bevy's diagnostic encoder timestamp writes are disabled on macOS in `diagnostic/internal.rs:750-758`; enabled wgpu TIMESTAMP_QUERY flags alone cannot establish valid native GPU timings. This experiment observes existing Metal completion timestamps without adding GPU queries or bypassing Bevy's workaround.

The patch leaves existing command buffer ownership, fence handlers, commit order, present-with-transaction behavior, return values, and errors intact. Callbacks borrow API-provided live objects; Metal retains the copied callback blocks. They do not retain command buffers or drawables. Observer logging and Metal allocation reads may perturb diagnostic execution. Observers register only when `NVWA_METAL_PROBE=1`, for the first 120 indices and each 60th index through 1200. There is no GPU allocation, explicit synchronization wait, or timestamp query added by the patch. Captures request the first main update, first runtime-ready update, and readiness plus two seconds.

CPU preparation commands, from this worktree:

```sh
python3 experiments/33-native-present-metrics/prepare_vendor.py
xcrun clang -Wall -Wextra -Werror -O2 experiments/33-native-present-metrics/proc_memory.c -o .work/m11-perf/native/proc-memory
python3 experiments/33-native-present-metrics/test_proc_memory.py .work/m11-perf/native/proc-memory
python3 -m unittest discover -s experiments/33-native-present-metrics -p 'test_reconcile_native.py' -v
CARGO_TARGET_DIR=/Users/derekxwang/Development/incubator/Nvwa/nvwa/target cargo build --offline --locked --release --manifest-path experiments/33-native-present-metrics/Cargo.toml --jobs 2
```

`prepare_vendor.py` refuses an existing destination. It hashes all 85 original crate files, copies them privately under `.work/m11-perf/native/vendor/`, and retains a small unified patch. No full vendor tree is intended for publication. Baseline/candidate metadata comparison retains the exact package versions, features, and source origins. No root Cargo, toolchain, asset, product, or workflow file is changed.

The root launch must provide `NVWA_METAL_PROBE=1`, an existing absolute `NVWA_PROBE_CAPTURE_DIR`, the exact frozen work input via normal `--work`, `--benchmark`, and finite smoke/timeout arguments. Identity receipts must include binary SHA256, exact PID/kernel birth, and raw external launch-clock brackets. The root must establish foreground pixels and quiet task-owned heavy jobs before measurement. Unrelated user apps remain uncontrolled and must be reported if they interfere.

CPU controls prove real libproc access and expected-birth rejection, PID1 rejection, and memory growth after 32MiB of actual pages are touched. Reconciliation controls reject zero/failed GPU spans, skipped display times, mixed PIDs, inconsistent flags, negative durations, and invalid calibration. Those controls are CPU evidence. Actual callbacks, screenshots, and native performance acceptance remain NOT-RUN until formal root-controlled launches.

Cold domains: a fresh process establishes process-cold only. Repeated process startup is a process-warm contrast in an already used OS/Metal environment. OS file cache, driver state, shader/pipeline caches, and fully cold first-install state remain NOT-RUN. No cache purge, system reboot, install, privacy permission change, or machine-wide settings change is used to manufacture cold state.
