# Nvwa M0 and thin M1 handoff

Latest continuous-idle follow-up: identical revision0 Work and Studio1280×720 on both targets, still playing at capture;600 samples each. Native p50/p95 8.304/9.366ms;Web16.600/18.000ms. Native sampledRSS216.77MiB. No compiler/Nvwa competitor detected at start/end. This resolves the narrow continuous-idle baseline only; prior unfavorable39.026ms finite-run result is retained, exact presentation/GPU/full-workload verdict stays open. [Actual evidence](evidence/continuous-idle.md).

Current main: `571604f4f5caaa67b4a0af792860261cd8262cfb`. PR17,18,20,21 are merged. Issues1,6,8,19 are closed. The merged tree equals the locally accepted PR21 tree; no production change was made by the new experiments. Current release evidence is the93-test integration snapshot, not the older33/57/59/67/71/79-test checkpoints.

## What works

The same Rust core and Bevy runtime run Studio and Player on native Metal and WebGPU. The real original CC0 humanoid has18 joints,4 morphs and3 authored actions. Studio supports shape editing, shared commands, Undo/Redo, Save/Open and portable cross-target Work JSON. Thin M1 supports a5–10s three-action sequence, playback/pause/seek and a character click that plays one wave then restores the work. These authored animations are not AI generation.

PR18 adds Chinese font fallback and repaired desktop Web IME/clipboard/focus input; physical native and repaired Web checks have Derek's acceptance. PR20 bounds session history to128 total Undo/Redo snapshots/16MiB and retries to1024/8MiB compact JSON content. These are content budgets, not exact heap/RSS. PR21 validates and loads each character GLB from one retrieved byte sequence; actual Web GLB traffic falls2→1 requests, saving1,129,081 compressed-body bytes. Missing/hash-damaged same-path rejection and recovery passed. Never-terminal same-path requests remain fenced rather than claiming cancellation.

[Current93-test acceptance](evidence/single-transfer/ACCEPTANCE.md), [exact build identities](evidence/single-transfer/build-manifest.json), [history acceptance](evidence/bounded-history/ACCEPTANCE.md), [input acceptance](evidence/web-input-control/ACCEPTANCE.md), [physical retest](evidence/web-input/WEB-HAND-TEST.md).

## Run and test

```sh
cd /Users/derekxwang/Development/incubator/Nvwa/nvwa
./dist/Nvwa.app/Contents/MacOS/Nvwa --work "$PWD/examples/m1-sequence.nvwa.json"
# Add --player for the editor-free Player.
python3 scripts/serve-web.py
# http://127.0.0.1:9201/?player=1&work=works/m1-sequence.nvwa.json
cargo test --workspace --locked
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --locked -- -D warnings
cargo clippy -p nvwa-studio --lib --target wasm32-unknown-unknown --locked -- -D warnings
```

The current native app and `dist/web` are already built. Production preview9201 remains running. To recreate packages, see [build commands](evidence/single-transfer/ACCEPTANCE.md) and `scripts/package-native.py`, `scripts/build-web.sh`; do not run duplicate compilers during measurements. Native Work paths must be absolute. CLI operates on offline files, not a live network bridge.

## New actual experiments

| Evidence | Actual result | Limit |
|---|---|---|
| [Native startup/RSS](evidence/native-startup/ACCEPTANCE.md) |Fresh release processes; reviewed real PNG;1s-delay probe capture evidence received4.010s after spawn; sampled child RSS maximum193.84MiB|Warmup/buffering included; not exact first frame or cold cache.15s p95 cadence39.026ms retained; competing compilers detected later, no isolated stable verdict|
| [Web bootstrap](evidence/web-startup/ACCEPTANCE.md) |Init promise848.1ms; actual rendered character; identical revision9 Work; one GLB GET; persisted explicit canvas PNG|Separate bootstrap, Player versus native Studio; compiler/GPU caches uncontrolled; exact presentation and browser/GPU memory unmeasured|
| [Viewport/HiDPI](evidence/viewport-boundary/ACCEPTANCE.md) |Live1600×900 and1024×768 atDPR1: text/caret, real drag, one Undo and whole saved documents; restored1280×720; native scale2 click/Undo/Save|Actual browser zoom/DPR change and real tab hide/show unavailable; native automated drag not claimed|

[Independent R2 review and repairs](evidence/startup-viewport-review.md) accepted diagnostic gzip packaging, served-byte provenance and Python3.9 portability fixes. No product dependency, source or Cargo.lock change. Failed attempts remain retained. Experimental helpers stay in experiments12–14 and do not enter the product bootstrap.

## Remaining scope

#2/#3 remain open for browser zoom/DPR, real tab transitions and broader platform/input coverage. #4 remains open for isolated continuous-animation performance, exact first presentation, cold caches and browser/GPU memory. OtherOS/browser, signed/notarized distribution and public hosting are unverified (#9/#10). Character visual extremes, exporter byte drift, controlled retarget visual playback and general rigs remain bounded gaps (#7/#13).

M2 real model inference needs separate scope, exact authorized weights/runtime and rig mapping. No model inference, paid API/cloud, machine-wide change or unrestricted CI was used. See [roadmap](ROADMAP.md), [issue index](ISSUES.md) and original [kickoff](specs/Nvwa_Codex_Kickoff_Parallel_Spikes.md).

PARTIAL — M0/thin M1 plus PR18/20/21 merged;93-test dual-release integration, actual native/Web acceptance and new reviewed captures/input checks recorded. New experiments reuse unchanged release bytes. Remaining performance/platform/DPR/AI items are explicitly unverified.
