# Frozen upper-arm neutral A/B

Read [REPORT.md](REPORT.md) for the result and limits. This capsule is an isolated
experiment; it does not change the production mapper or experiments41–49.

The standard-library constructor and offline gate use pinned retained inputs.
The existing independent source FK and glTF affine/skin evaluator remain
unchanged. New-asset adapters declare the candidate Work/GLB identity explicitly;
they do not loosen historical49 numerical thresholds.

Run from the repository root, with a **fresh** owned output directory:

```sh
python3 experiments/50-upper-arm-neutral-ab/reproduce.py --output .work/m2-neutral-ab/reproduction-new
python3 experiments/50-upper-arm-neutral-ab/test_runtime_adapter.py
python3 -O experiments/50-upper-arm-neutral-ab/test_runtime_adapter.py
python3 experiments/50-upper-arm-neutral-ab/test_runtime_measure.py
python3 -O experiments/50-upper-arm-neutral-ab/test_runtime_measure.py
python3 experiments/50-upper-arm-neutral-ab/runtime_evidence.py
```

`reproduce.py` never builds, downloads, runs a model or starts graphics. It checks
all90 keys, creates the deterministic isolated candidate only after the gate,
runs the normal/optimized controls, and measures both animated and static-neutral
surface controls. An optional `--source-cache /absolute/existing/cache` checks
six pinned original-source files and receipts; absence means no fresh source
text audit. It does not fetch a cache. The retained run did supply an existing
cache, and [source-cache-audit.json](results/source-cache-audit.json) records it.

Individual offline entrypoints are also available:

```sh
python3 experiments/50-upper-arm-neutral-ab/test_candidate.py
python3 -O experiments/50-upper-arm-neutral-ab/test_candidate.py
python3 experiments/50-upper-arm-neutral-ab/evaluate.py --output .work/m2-neutral-ab/evaluation-new --surface
```

The runtime captures are historical pre-StageA evidence at base `50eae1979cac47c7eb53dada69f06b716436bf92`; they do not claim replay of later product changes.

The complete raw/runtime receipts and actual PNGs are in [results/](results/).
`runtime_evidence.py` regenerates SVG skeletons and actual seven-key direction /
Native-Web transform checks from those retained raw captures. `--raster` also
writes diagnostic PNG drawings if the **existing** interpreter has Pillow;
Pillow is optional and is not needed for any numeric gate. No dependency is
installed by these commands.

The new probe is an experiment-local copy of49's runtime capture. The two actual
builds used `probe/build.py --platform native|web --target-dir <absolute owned cache>
--receipt <absolute owned receipt>` through `wefty exec` on the single local owned
node. They used the existing lock/dependency cache and no network downloads.
Do not start new builds or renderers without the applicable shared resource
lease. [Build receipts](results/build-native.json) bind actual snapshot inputs;
[post-build-diagnostics.json](results/post-build-diagnostics.json) explains the
later evaluator-only guard and format-only probe edit. Exact build-time evaluator
and `lib.rs` bytes are archived and authenticated against both build receipts;
only whitespace changes in Rust, with no rebuild or runtime recapture claimed.
`cargo fmt --manifest-path experiments/50-upper-arm-neutral-ab/probe/Cargo.toml --all --check` passes.

For an already-built artifact, `probe/prepare.py --variant baseline|candidate
--stage .work/m2-neutral-ab/<fresh stage> --binary /absolute/existing/probe`
creates a private native app without launching it. Alternatively supply
`--wasm /absolute/existing/probe.wasm --wasm-bindgen /absolute/existing/wasm-bindgen`.
The supplied tool must report exactly `wasm-bindgen 0.2.129`. Web stages must be
opened with their explicit `?work=works/<staged Work filename>.nvwa.json` URL,
under a bounded owned loopback server in Nvwa's port range. The root-controlled
trial used port9204, baseline then candidate, closing each renderer first.

`probe/native_visual.py <existing private native stage>` prepares a separate
fresh product `--capture` run using the **same** binary and existing Studio GPU
readback. It preserves the first launcher; visual JSON/log/PNG/exit-code outputs
are separate from the first capture. Launch the exact app through the eligible
UI adapter, sequentially. Require complete seven-key raw capture, actual
`NVWA_EVIDENCE` capture completion at key89's exact time, a fresh nonempty PNG and
OS exit0. Incidental smoke timing is not a formal performance measurement.

Validate a newly collected raw capture through the explicit variant adapter:

```sh
python3 experiments/50-upper-arm-neutral-ab/probe/compare.py /absolute/new-capture.json --variant candidate --output /absolute/new-comparison.json
```

This task did not request production adoption or a human trial. Keep quality
HOLD and preserve failing controls and original assets.
