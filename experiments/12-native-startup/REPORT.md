# Native startup and sampled RSS probe — issue #4

Conclusion: adopt the bounded collector for diagnostics; inconclusive for isolated stable performance. Root ran both probes, reviewed real character PNGs, and retained measured RSS and clock boundaries. See [actual acceptance](../../docs/evidence/native-startup/ACCEPTANCE.md).

Question: how long does the current release process take to complete a fresh screenshot of the exchanged character, and what exact-child RSS is observed during that process?

This experiment owns only the native collector and its reports. It does not change production, shared evidence, dependencies or the Web helper. No Nvwa process, GPU interaction or build has been run by this worker. The parent owns the GPU slot, artifact, work selection and actual PNG review.

## Measured boundaries

- A parent monotonic clock starts immediately before `Popen`. The report retains that instant, spawn return, every evidence receipt, and exit observation. Exit observation includes the polling delay. It is not the exact kernel exit instant.
- The child emits `NVWA_EVIDENCE` only when capture callback, nonempty capture file, app freshness check and readiness delay succeed, or when an app error/timeout occurs. The collector preserves this event with its parent monotonic receipt and its original stream. Receipt includes pipe buffering. It is a completion upper bound, subject to actual visual review, not exact first presentation.
- `first_asset_ready_seconds`, `capture_callback_seconds` and the app's `first_visible_upper_bound_seconds` start at the first Bevy update. They omit earlier process/renderer startup. They remain raw runtime facts and are never converted to process first-frame latency.
- `--benchmark` requests physical 1280×720, scale override1 and continuous scheduling. `--smoke-seconds` clamps to1..60. The collector permits the requested1s and15s probes only. Frame samples start at readiness plus1s and retain up to600 main-loop samples. They measure scheduling cadence, not GPU completion, exact presentation or displayed FPS.
- RSS samples come from `ps` for the exact `Popen` PID and this collector's PPID, while that child is still alive. Units are KiB converted to bytes. This avoids cumulative `RUSAGE_CHILDREN`, including the sampling subprocesses. The reported maximum is a **sampled maximum**, not a true lifetime peak. Short peaks, descendants, GPU allocations and total unified memory are outside the measurement.
- A unique new output directory prevents stale capture reuse. SHA256, size, inode, device and modification time bind the binary, work, fixture and launch source before/after the run. Fixture SHA256 must match the work profile. `NVWA_ASSET_ROOT` is explicitly set to the measured source checkout's assets directory, so an inherited override/build path cannot silently select another fixture. The collector rejects stale, corrupt, wrong-size and all-black PNGs. Nonblack pixels alone do not establish a real character. Operator PNG review is always required.
- `NVWA_EVIDENCE` verifies release build, Metal identity, dimensions, document revision, timeline count, loaded mesh/skin/joint/player counts and cadence boundary. It preserves adapter name, animation state, all runtime counters and raw flags/error text. Source parser support is checked before launch; an actual binary flag rejection remains a failed attempt. Source support does not prove binary/source provenance.

## Protocol

1. Parent pauses task-owned compilers/heavy jobs, closes every competing Nvwa renderer and parks Web on a blank page. Parent records the actual isolation state and confirms the desktop is unlocked. User applications remain outside this worker's control.
2. Use the existing root release and exchanged revision9 work by absolute path. Do not copy binaries, purge caches or build. Bind inputs by measured hashes. The current dispatch claims binary102,985,296bytes SHA256 `3be9380f1747c8a6266c59e49f73550e180038fb1259187942af16033a2bc929`; each real report measures this anew. Fixture expected SHA256 `f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6`.
3. Run the1s capture probe, review its actual PNG, then run15s against the same artifact/work under the same isolation. Each is a fresh process. OS/shader caches are uncontrolled. The15s capture may show the held final pose after the finite9.5s work completes; inspect `completed`, `playing`, `animation_seconds` and sample count before interpreting cadence.
4. Inspect the new `report.json`, `stdout.log`, `stderr.log`, `events.jsonl` and `capture.png`. Keep failures. Parent timeout is110s by default; child timeout90s uses the supported app clock. Only the exact owned child is terminated on parent timeout/SIGINT/SIGTERM cancellation, with a2s terminate grace then kill. No process-name kill occurs.
5. Parent adds its visual-review result beside the collector report. A black screenshot or locked desktop cannot prove visual presentation even if functional readiness is true. No cold-cache or GPU/first-presentation conclusion is available from this protocol.

## Ready commands (root must hold the GPU slot)

Run from the integration checkout. Replace the isolation note with the actual checked state; these commands have **not** been executed on the product.

```sh
python3 experiments/12-native-startup/measure_native.py \
  --binary /Users/derekxwang/Development/incubator/Nvwa/nvwa/target/release/nvwa-studio \
  --source-root /Users/derekxwang/Development/incubator/Nvwa/nvwa \
  --work /Users/derekxwang/Development/incubator/Nvwa/nvwa/docs/evidence/bounded-history/history-reloaded.json \
  --output experiments/12-native-startup/results/native-1s \
  --seconds 1 \
  --isolation-note 'Parent checked one renderer, Web blank, heavy jobs paused, desktop unlocked' \
  --cache-note 'Fresh process; prior native runs occurred; OS/shader caches not purged or controlled'

python3 experiments/12-native-startup/measure_native.py \
  --binary /Users/derekxwang/Development/incubator/Nvwa/nvwa/target/release/nvwa-studio \
  --source-root /Users/derekxwang/Development/incubator/Nvwa/nvwa \
  --work /Users/derekxwang/Development/incubator/Nvwa/nvwa/docs/evidence/bounded-history/history-reloaded.json \
  --output experiments/12-native-startup/results/native-15s \
  --seconds 15 \
  --isolation-note 'Parent checked one renderer, Web blank, heavy jobs paused, desktop unlocked' \
  --cache-note 'Fresh process after1s probe; OS/shader caches not purged or controlled'
```

Existing output directories are deliberately rejected. A successful collection returns0 with `COLLECTED_REQUIRES_VISUAL_REVIEW`; failed children preserve positive exit code, timeout returns124, cancellation130, and collector/validation failure1. Report status never asserts successful visual character rendering.

## Lightweight checks and resource inventory

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s experiments/12-native-startup -p 'test_*.py' -v
```

All subprocess tests launch Python fake processes only. Mock evidence tests exercise parsing/boundaries and cannot establish real rendering. PNG tests use generated synthetic black/nonblack pixels only. They test stale/corrupt/wrong-size/black capture handling, not character appearance. No product measurement or UI/build command belongs to this check.

Resources: Python stdlib, `ps`, one exact child per probe, two pipe readers, bounded wall timeout,0.1s default RSS interval, input hashes streamed in1MiB blocks, PNG compressed-file bound20MB and fixed1280×720 decode bound. No package install, server, model/API call, renderer, compiler or cache copy is required to prepare the harness. Sampling overhead can perturb cadence and is recorded by interval/timestamps.

NOT-RUN — Product startup/RSS and PNG visual review await the parent's exclusive GPU slot. Collector tests are reported after execution below.

VERIFIED — Python3.14.7 ran13 parser, synthetic PNG and fake-process tests successfully; see `checks.log`. Tests include SIGTERM cancellation of an owned fake child and the explicit asset-root override. No native product rendering, UI action or build was performed.

One intermediate check failed because the test compared macOS's `/var` alias with the collector's resolved `/private/var` identity. The test now compares resolved paths. The actual failed check is retained in `checks-failed-path-alias.log`; no product attempt occurred.

Later root follow-up: same revision0 default Work, both Studio1280×720, continuousidle during capture and600 samples;[actual record](../../docs/evidence/continuous-idle.md). Narrowcadence observed; fullbudget/cold/GPUclaims remainunverified.
