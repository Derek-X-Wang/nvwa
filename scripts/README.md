# Portable checks

Run the complete hosted portable command catalog locally:

```sh
python3 -B scripts/check-portable.py all
```

The runner uses [portable-checks.json](portable-checks.json). Each portable CI
step selects one group from that same file. `all` runs these groups in this order:

| Group | Checks and prerequisites |
| --- | --- |
| `runner-contract` | Shared runner extraction and subprocess controls, normal and optimized Python. |
| `ci-timing-contract` | Observer, stream/failure, queue metadata, and complete workflow inventory controls, normal and optimized Python. |
| `source-cli` | Existing portable source checks: Rust formatting, strict core/CLI Clippy, core/CLI tests. Requires the pinned Rust toolchain and Cargo dependencies. |
| `cli-distribution` | Offline CLI build and standalone package controls, normal and optimized Python. Uses the dependencies prepared by `source-cli`. |
| `b1-inputs` | Admitted production inputs and source verifier plus rejection controls, normal and optimized Python. |
| `motion-comparator` | Independent B1 motion comparator and server controls, normal and optimized Python. |
| `diagnostics` | Existing bounded diagnostic controls. Requires Node and Python. |
| `appearance` | Appearance diagnostic and preview/build controls, normal and optimized Python. |
| `eye-hair-parameters` | Actual controls for experiments 67, 68, 69, 71, **72**, **73**, 79, 79/browser, 80 and 82, in normal and optimized Python. Starts with `node --version`; missing Node fails. |
| `authenticated-source` | Authenticated source/rejection controls; prepare the pinned seed, pose adapter and viewer; viewer controls. Requires the committed inputs. |
| `offline-motion` | Locked importer dependency fetch, then retained CPU motion/calibration/history controls. |
| `shoulder-rest-refit` | Isolated rest-refit controls and Rust host formatting checks. |
| `current19-shoulder-refit` | Current nineteen-case controls and replay-host formatting check, normal and optimized Python. |
| `frozen-upper-arm` | Frozen comparison, runtime adapter/measure controls and retained native/Web capture comparisons. |

`current19-shoulder-refit` runs immediately after `shoulder-rest-refit` and before `frozen-upper-arm`: the latter's legacy generator rewrites tracked evidence, so it must remain the last timing observer. The shoulder group runs the isolated replay/evaluation/authoring/client rejection controls and both Rust hosts’ formatting checks in normal and optimized Python. It does not compile the replay probe or claim private full19 geometry evidence. The retained actual old crossing witness runs locally when `NVWA_SHOULDER_RETAINED` points to its authenticated retained directory; its absence is an explicit skip. The current19 group adds only its isolated formatting and Python controls; it does not compile the host or establish actual nineteen-case capture or candidate evidence.

`python3 -B scripts/check-portable.py --list` lists groups. Pass one or more names
to run a subset; selected groups run once in catalog order. A subset is partial
verification and does not arrange omitted prerequisites. A failed command stops
its group and prevents later selected groups. The original command arguments,
normal/`-O` modes, Bash loops and failure boundaries are retained.

Use Bash, Git, Python 3.12 or newer, Node and the repository's pinned Rust toolchain
with rustfmt and Clippy. The supported Python must be selected as `python3` on
`PATH`: preserved nested commands invoke `python3`, so invoking only the outer
runner through an absolute Python path is insufficient. The CLI distribution
controls require the safe `tarfile.extractall(filter="data")` interface.
Install prerequisites separately. The runner does not install
tools. Existing Cargo commands retain their network behavior: `source-cli` may
resolve/fetch locked dependencies and `offline-motion` explicitly runs
`cargo fetch --locked`. Offline commands still require a prepared dependency cache.
`all` is the hosted portable lane; it can compile the core/CLI and isolated CPU
probes and write their existing `.work` outputs. It is not an instant script-only
check. Follow the repository's compute/resource policy before a full run.

Cargo defaults match the hosted portable environment: two build workers,
incremental compilation off, development/test debug info off, and terminal color
on. Explicit inherited values take precedence. CI retains its existing environment
and step/job timeouts. A local run has no added timeout; stop it using the normal
process controls when needed.

CI's `RUNNER_TEMP` is reused. When absent locally, the runner creates one temporary
directory for the entire invocation and removes it at exit. A supplied
`RUNNER_TEMP` must be an existing absolute directory and is never removed by the
runner. Existing `.work` output and Cargo caches keep their original behavior.

The runner finds its checkout from its own file location and runs every group
there, even when invoked by absolute path from a nested or unrelated directory.
Before running checks it prints that checkout, the invocation directory, full
HEAD, branch (or detached state), and tracked/untracked dirty status. It validates
that the script root is the Git checkout root. This is a read-only observation:
dirty checkouts and detached CI are allowed. It does not switch branches, fetch,
or authenticate ignored caches, installed tools, runtime behavior or a remote
branch. Symlinked invocation paths resolve to the script's physical checkout.

Run the runner's own extraction and subprocess controls separately with:

```sh
python3 -B scripts/test-portable-checks.py
python3 -B -O scripts/test-portable-checks.py
```

These controls freeze the original hosted command bodies and exercise the actual
runner/shell with temporary command shims. The shims test scheduling and failures;
they are not evidence that the underlying product checks passed. CI also runs
the same `runner-contract` group as local `all`, before the original portable groups.

`experiments/27-ci-baseline/check.sh portable|diagnostics|native|wasm` keeps its
existing narrow interface. Its `portable` option covers only the `source-cli`
group. `scripts/check-b1-work.sh` remains the separate scoped native/Web package
helper. Native CPU, source runtime, Wasm compilation and actual Web/native visual
acceptance remain separate gates; portable success does not prove them.

## CI phase observations

`ci-timing.py` observes the existing bounded workflow. The same
`ci-timing-contract` group runs locally in `all` and in CI. The three job names,
runner types, timeouts, dependencies, PR/main triggers, and original command bodies
remain unchanged. Each existing `run` body still executes with Bash `-e`.
A scoped `PATH` directory wraps **Cargo only**, including Cargo launched inside
Python and captured mutation subprocesses. It resolves the original Cargo before
adding that directory, keeps proxy symlink spelling, and adds no Cargo arguments.
Python, Node, the portable runner, and frozen experiment helpers retain their
original code. The catalog gains only the timing-control group. The wrapper
forwards command exit codes and signals to its direct child. A signaled Cargo
shim terminates with the same signal after writing its receipt, so Python callers
retain negative signal return codes and Bash retains its own signal convention.
Process groups and Bash descendant cancellation behavior remain unchanged.
Cancellation can therefore leave descendant observations incomplete. Cargo
streams pass through a byte relay with a 64 KiB line buffer and a 4096-marker
cap; truncated observations become **UNKNOWN**. No telemetry is added to either
child stream.
Within each stream the bytes and order are retained. Cross-stream interleaving,
pipe buffering, terminal detection, and observer startup can differ. CI already
uses pipes and sets Cargo color explicitly; local timing is an instrumented run.

Each command writes an incomplete record before launch and atomically completes
it after exit. Records contain monotonic start/end nanoseconds, a parent ID,
status, command digest, limited Cargo scope, checkout HEAD/tree/dirty, and the
allowlisted workflow/run/attempt/job identifiers. PR event head and checkout SHA
are separate: checkout can be GitHub's synthetic merge commit. The source identity
is observed at the outer command start; deliberate mutation witnesses later
modify source temporarily. The record does not attest those temporary bytes or
ignored caches. A dirty checkout's HEAD tree does not attest uncommitted bytes.
There is no environment dump or general argument dump.

An `always()` step in each job uses the original Bash shell to print JSON records
with the `NVWA_CI_TIMING` prefix and append a table to `GITHUB_STEP_SUMMARY`.
The report excludes itself. It rejects missing, corrupt, incomplete, mixed-source,
mixed-attempt, or mixed-job records and reports **UNKNOWN**, rather than producing
partial phase totals. Cancellation can prevent the report from running; retained
logs are then incomplete. No upload action, new token permission, or network
request is added. Raw records live under `$RUNNER_TEMP/nvwa-ci-timing/$GITHUB_JOB`.

The report distinguishes these observed quantities:

| Observation | Meaning and limit |
| --- | --- |
| Explicit `cargo fetch` command wall | Dependency fetching/resolution in that command only. Implicit fetching inside other Cargo commands is not separately measured. |
| `cargo build/check/clippy` command wall | Compilation command envelope, including orchestration and any implicit dependency work when not offline. Formatting remains unclassified. |
| `cargo test` command wall | Mixed preparation, compilation and execution. Never labeled pure compilation or pure tests. |
| Cargo `Finished` then first `Running` markers | Best effort preparation and execution envelopes. Preparation includes implicit dependency work and launch. Execution can include later doctest compilation. Missing/truncated markers or a failed command leave both envelopes **UNKNOWN**. |
| libtest `test result` durations | Cargo's test binaries report rounded seconds for the lines observed. Partial coverage, including failed tests, not the whole command or a phase total. |
| Toolchain setup | Existing single-command rustup install step wall. |
| Outer shell/control wall | Existing script/runtime/checker work and overhead after removing nested Cargo intervals. The motion-matrix build is therefore separate from its subsequent checker envelope. |

Child interval unions are removed from parent command wall. Concurrent sibling
commands can overlap, so category rows are not an additive job total. Categories
with no command observation say `NOT OBSERVED`, rather than implying that
unmeasured work took zero time. Marker
observations and libtest values are inclusive evidence, not numbers to add to
those rows. Interpreter children using `sys.executable`, shell builtins, tools
other than Cargo, and absolute Cargo paths that bypass `PATH` are not individually
observed. Existing nested importer and mutation Cargo calls use `PATH` and are
covered. These are wall measurements, not CPU, network-transfer, GPU, or product
performance claims. Rust/Cargo behavior references: [cargo test](https://doc.rust-lang.org/cargo/commands/cargo-test.html),
[external tools](https://doc.rust-lang.org/cargo/reference/external-tools.html),
[Cargo timings](https://doc.rust-lang.org/cargo/reference/timings.html).

For a local instrumented invocation, choose a new directory outside the checkout:

```sh
NVWA_TIMING_DIR=/absolute/new/evidence/records python3 -B scripts/ci-timing.py run -- python3 -B scripts/check-portable.py all
python3 -B scripts/ci-timing.py report --directory /absolute/new/evidence/records
```

Use the existing prerequisites and resource policy. Timing does not install them.
A later invocation must not reuse a directory from a different source/run/job.
Run observer controls without compiling product code:

```sh
python3 -B scripts/test-ci-timing.py
python3 -B -O scripts/test-ci-timing.py
```

Queue analysis runs separately on **already retrieved**, attempt-specific GitHub
REST metadata. Supply JSON with `run` (the run object) and `jobs` (the jobs array):

```sh
python3 -B scripts/ci-timing.py queue /absolute/evidence/metadata.json --records /absolute/evidence/portable-records
```

The reader checks event head, run ID, attempt, expected job names and numeric job
IDs, and retains raw job creation/start/completion timestamps. Job names map to
workflow keys unambiguously. Optional repeated `--records` directories join telemetry
to numeric job IDs, checking event head/run/attempt; checkout SHA can differ for PRs.
Repeated directories for one job must agree on the complete source identity and
checkout SHA. Conflicts reject the entire join before any queue row is emitted.
Without `--records`, the output is metadata-only and does not authenticate
telemetry. It reports the portable dependency gate separately
from eligible-to-creation and creation-to-start gaps. A job created before its
dependency becomes ready has that overlap identified separately. None of these
metadata gaps proves a scheduler, provisioning, concurrency, or capacity cause.
Timestamps have GitHub's second precision. For reruns, retrieve the run and jobs
from the [attempt-specific API](https://docs.github.com/en/rest/actions/workflow-jobs#list-jobs-for-a-workflow-run-attempt),
not an all-attempt jobs collection. The timing code performs no API calls.
