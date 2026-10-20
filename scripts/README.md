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
| `source-cli` | Existing portable source checks: Rust formatting, strict core/CLI Clippy, core/CLI tests. Requires the pinned Rust toolchain and Cargo dependencies. |
| `cli-distribution` | Offline CLI build and standalone package controls, normal and optimized Python. Uses the dependencies prepared by `source-cli`. |
| `b1-inputs` | Admitted production inputs and source verifier plus rejection controls, normal and optimized Python. |
| `motion-comparator` | Independent B1 motion comparator and server controls, normal and optimized Python. |
| `diagnostics` | Existing bounded diagnostic controls. Requires Node and Python. |
| `appearance` | Appearance diagnostic and preview/build controls, normal and optimized Python. |
| `eye-hair-parameters` | Actual controls for experiments 67, 68, 69, 71, **72**, **73**, 79, 79/browser, 80 and 82, in normal and optimized Python. Starts with `node --version`; missing Node fails. |
| `authenticated-source` | Authenticated source/rejection controls; prepare the pinned seed, pose adapter and viewer; viewer controls. Requires the committed inputs. |
| `offline-motion` | Locked importer dependency fetch, then retained CPU motion/calibration/history controls. |
| `frozen-upper-arm` | Frozen comparison, runtime adapter/measure controls and retained native/Web capture comparisons. |

`python3 -B scripts/check-portable.py --list` lists groups. Pass one or more names
to run a subset; selected groups run once in catalog order. A subset is partial
verification and does not arrange omitted prerequisites. A failed command stops
its group and prevents later selected groups. The original command arguments,
normal/`-O` modes, Bash loops and failure boundaries are retained.

Use Bash, Git, Python 3, Node and the repository's pinned Rust toolchain with
rustfmt and Clippy. Install prerequisites separately. The runner does not install
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
