Root owns all native launches and GUI/GPU actions. The launcher source is an additional artifact; the original reviewed candidate freeze, Rust wrapper, vendor patch, and Cargo files remain unchanged.

Preflight checks the frozen candidate and baseline binaries, proc-memory helper, source hashes, all 524 accepted-main product/build blob identities, exact work hash, bundle resource hashes, and bundle identifier/executable. Baseline and diagnostic identifiers are `dev.nvwa.studio` and `dev.nvwa.perf.native-diagnostic`. Their Info.plist hashes are in the additional freeze and per-run prelaunch receipts. Strict signature verification failures remain retained; the helper makes no signing, permission, Gatekeeper, or system changes.

Run these commands only after root's measurement/review gate:

```sh
python3 experiments/33-native-present-metrics/launch_owned_native.py --variant baseline --run-name baseline-1 --hold-seconds 30 --deadline 40
python3 experiments/33-native-present-metrics/launch_owned_native.py --variant diagnostic --run-name diagnostic-1 --hold-seconds 30 --deadline 40
python3 experiments/33-native-present-metrics/launch_owned_native.py --variant diagnostic --run-name diagnostic-warm --hold-seconds 30 --deadline 40
```

The root should start each through a nonblocking tool call, retain its returned session ID, then use the sole GUI controller to verify/select the existing exact app and capture foreground pixels while it remains live. Do not launch another copy through GUI selection. The helper prints the exact owned PID and writes `pid.json` and `identity.json` promptly. UI availability remains NOT-RUN until observed. Each run retains logs under `.work/m11-perf/native/runs/<run-name>/`, and captures/prelaunch receipts under `.work/m11-perf/native/captures/<run-name>/`. There are at most three actual native launch receipts. Run names cannot overwrite existing artifacts.

Normal argv is the selected bundle executable plus frozen `--work`, `--benchmark`, `--smoke`, `--smoke-seconds 30`, `--timeout 38`, and an absolute production capture path. Explicit environment overrides are only `NVWA_METAL_PROBE=0|1` and `NVWA_PROBE_CAPTURE_DIR`. Other environment values are inherited and are never printed. The diagnostic variant enables observers; baseline does not. The screenshot requested by production is delayed until the hold boundary; earlier diagnostic screenshot observations and root foreground screenshots establish separate content observations.

Each Popen starts a new session/process group. The launcher owns a direct Popen object before optional inspection. Stdout/stderr remain ordinary persistent files until all callback-bearing app execution ends. Memory samples call the exact frozen helper for PID/birth-qualified RSS, physical footprint, and separately labeled kernel lifetime maximum footprint. Sampling errors are recorded as unknown, never absence, and cannot bypass the external deadline. No external/background sampler process remains; each helper subprocess has a bounded timeout and is reaped.

At timeout or interruption, cleanup verifies the live direct child, session/group, executable, and microsecond kernel birth; registered descendants require stable identities. Only that exact owned group receives TERM and, if required, KILL. The group must be kernel-observed absent and the direct child reaped before EXIT-VERIFIED. Unknown identity blocks signaling and is reported. Group inspection is bounded to eight members; Nvwa is expected to have one process with worker threads. A blocked cleanup is not success.

Raw launch anchors use Python `time.clock_gettime_ns(time.CLOCK_MONOTONIC)`, which is verified against the actual C helper's clock_gettime sample bracket. Python `time.monotonic_ns()` uses a different clock on this Mac and must not be labeled CLOCK_MONOTONIC. The first CPU control receipts exposed that error and remain in `launcher-controls/`; corrected receipts are in `launcher-controls-2/`. No Nvwa/GPU run occurred in either control pass. The root must use the corrected launcher source. Wall UTC ISO timestamps aid observation matching and remain separate from CPU/Metal clocks.

Actual CPU controls exercised empty successful child, failing child, 4MiB each on stdout/stderr without pipe blockage, TERM-ignoring child requiring KILL and waitpid/group-absence proof, real self-PID birth mismatch rejection, and the C/Python CLOCK_MONOTONIC bracket. The child-executable guard and eight-member bound were added after those controls and must be checked before runtime use; root paused further control execution during formal Web measurement.

Start/end inventories retain only selected executable basenames or CPU>=50%, PID, PPID, CPU percent, and RSS. They read no unrelated arguments or environment. This is an observed contention inventory, not proof that all competing GPU jobs are quiet. Root decides readiness and must pause task-owned heavy builders before formal measurements.
