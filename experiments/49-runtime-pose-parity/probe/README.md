# Runtime pose probe

This standalone nested crate calls `nvwa_studio::build_app()` and adds only
capture/seek systems. The scene loader, Work open, authored transport, Bevy
animation graph and transform propagation are the product path. It cannot
load expected poses. The `manual-start` Studio feature suppresses only the
library's Web auto-entrypoint, so the probe can start one instrumented app.
Normal Studio builds keep their existing default entrypoint.

`SCHEMA.md` defines raw results. The collector waits for actual readiness,
requests each exact paused seek before transport, and captures after animation
and global propagation for two matching passes. It exits on any missing state,
observed clip/time mismatch, or 60-second runtime deadline. A native process
holds its final pose for ten seconds after writing JSON, then exits. Web publishes raw JSON in `#nvwa-pose-result`.
Neither bones nor an image establish anatomical motion quality.

Use cached dependencies only. A nested Cargo.lock pins this crate separately;
the root lock and dependency definitions are unchanged. Build output belongs
under the ignored root `.work/runtime-pose-build` directory. Long builds use
the installed local Wefty node, after the owning session grants a build slot.
For example (CARGO_TARGET_DIR must be an absolute owned output path):

```sh
wefty exec --detach --json --max-runtime 40m -- python3 experiments/49-runtime-pose-parity/probe/build.py --platform native --target-dir /absolute/owned/target --receipt /absolute/owned/native-build.json
```

Use `--platform web` for the separately granted Web build. `build.py` hashes
its actual Wefty snapshot inputs before compilation and retains the outcome
and artifact hash. `record_cohort.py` compares those snapshot hashes against
the current source and executable before accepting a final cohort receipt.
A generator that only hashes the current checkout is insufficient.

After build, `python3 experiments/49-runtime-pose-parity/probe/prepare_native.py`
packages `dev.nvwa.pose-probe` under ignored `.work`. It does not launch.
Launch that exact app through the approved UI adapter only. The wrapper makes hash-checked byte copies of the experiment48 Work and GLB
under an owned `/tmp/nvwa-pose-native-*` directory, opens that staged Work, and writes
`probe/results/native.json`. Inspect the returned status and compare offline.
GPU launch, Web compilation, WebGPU run, capture and comparison are separate
evidence gates. Do not run both renderers simultaneously.

`prepare_negative.py` packages a separate diagnostic app that opens the normal
default fixture. The collector must reject its different profile. Its raw failed
result and child process exit code are retained separately; no user Work is read
or saved. Native launchers record the actual child OS exit code under ignored
`.work/runtime-pose-logs`. Packaging controls use a clearly fake executable and
do not count as runtime evidence.

Web preparation requires an explicit existing tool, pinned to `wasm-bindgen
0.2.129`. No machine-specific path is embedded. Supply the installed tool and
owned artifact/stage paths; no install or download is attempted:

```sh
python3 experiments/49-runtime-pose-parity/probe/prepare_web.py --wasm-bindgen "$WASM_BINDGEN" --wasm "$PROBE_WASM" --stage "$PROBE_STAGE"
```

`WASM_BINDGEN` names the existing executable, `PROBE_WASM` names the already-built
Cargo Wasm artifact, and `PROBE_STAGE` names an owned static-site directory.
Missing executables, failed version probes, versions other than exactly
0.2.129, and missing Wasm inputs fail before creating the stage. Fake-tool
packaging controls test those boundaries and explicit paths containing spaces.

After serving the owned stage on the reserved free diagnostic port9204, open
this exact entry URL so the production loader opens the staged genuine Work:

```text
http://127.0.0.1:9204/?work=works/genuine44-calibrated47.nvwa.json
```

The `?work=` query is required for this narrow stage. A bare URL selects the
normal default fixture, whose GLB is deliberately absent from this stage.
That operator entrypoint error is not generated-motion evidence.
