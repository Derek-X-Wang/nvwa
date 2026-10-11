# Final local handoff

The M0 functional loop works on actual native Metal and browser WebGPU: load the original skinned humanoid, change four real morphs during skeletal playback, select clips, use shared commands and undo/redo, save, open on the other target and retain the complete document. Native revision 7 was edited/exported as Web revision 10, then opened and saved by a fresh native process with whole-document semantic equality. Actual CLI replays reproduce both GUI-produced documents.

Work is local in `/Users/derekxwang/Development/incubator/Nvwa/nvwa`. At the verified M0 snapshot, Git was on unborn `main` and implementation/setup files were untracked. The user subsequently authorized committing/pushing this M0 and tracking the remaining work in GitHub Issues. Origin is `git@github.com:Derek-X-Wang/nvwa.git`. The M0 measurement/build round used no CI, cloud deployment, paid API or model-weight download. Git publication is a subsequent authorized step; see EXECUTION.md and the current Git history for its state. `CLAUDE.md` remains exactly `@AGENTS.md` followed by a newline.

## Start the existing artifacts

```sh
cd /Users/derekxwang/Development/incubator/Nvwa/nvwa
open dist/Nvwa.app
```

In the native File field use an absolute writable JSON path. Open `docs/evidence/web/edited-from-web-release.nvwa.json` using its absolute path to inspect exchanged revision 10. Save uses an atomic file replacement. In Web, Open uses a local picker and Save downloads JSON.

```sh
cd /Users/derekxwang/Development/incubator/Nvwa/nvwa
python3 scripts/serve-web.py
```

Open `http://127.0.0.1:9201` in a WebGPU-capable browser. The server is loopback-only and serves `dist/web`. A preview server may still be running from this session; if port 9201 is already occupied by that server, use it instead of starting a second one. No background continuation after this session is promised.

## Rebuild and verify

```sh
cargo test --workspace --locked
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --locked -- -D warnings
cargo clippy -p nvwa-studio --lib --target wasm32-unknown-unknown --locked -- -D warnings
python3 tools/blender/validate_fixture.py
cargo build -p nvwa-studio -p nvwa-cli --release --locked
python3 scripts/package-native.py
python3 scripts/install-web-tools.py
bash scripts/build-web.sh
```

The pinned installer currently supports macOS arm64. Build output is ignored by Git; source, scripts, assets and evidence are present locally. App/CLI, Wasm/JS/HTML and source hashes are in [build-manifest.json](evidence/build-manifest.json). The unsigned app includes bundled assets. Signing/notarization is untested.

For agent use, [README](../README.md) gives runnable capability discovery → parameter/clip batch → validation → save commands. CLI edits an offline file; reopen it in Studio. It does not control an existing GUI process.

## Results and decisions

- Final checks: **33 Rust tests passed** (core 13, CLI 4, runtime 10, Studio/platform 6); fmt and strict native/Wasm clippy passed; both final release builds passed.
- [Performance](PERFORMANCE.md): physical 1280×720, 600 steady cadence samples. Native p50/p95 8.34/8.65 ms and peak child RSS 237 MiB; Web 8.30/11.20 ms. Unique first-screen gzip bundle 14,113,867 bytes. These are cadence/size observations, not GPU timestamps or cold-network measurements.
- [Experiments](EXPERIMENTS.md): adopt the original asset, atomic core and shared Bevy/egui runtime. A/B rejects naive rotation copying for changed joint bases; corrected exported/reloaded controlled derivatives pass numerical thresholds. This is not a general retargeter.
- AI generation is **NOT-RUN**: no usable runtime/authorized weights found in checked local locations. Nine isolated authored-preset import tests passed; those files say ai_generated=false and never enter normal Studio dependencies.
- Real runs exposed and fixed new-player playback after reload. Earlier egui/API, reflection and tone-mapping failures were fixed and rerun. No requirement or failing test was removed. Automatic Web screenshot downloading remained unsuccessful in IAB; the explicit benchmark-only canvas button produced actual pixels.

## Remaining work and blockers

Known limitations are CJK missing glyphs, unverified IME/native clipboard/native continuous drag, browser CUA bulk typing and IAB viewport-emulation scaling. Other operating systems/browsers, GPU timestamps, exact first presentation, cold Web startup and browser memory are unverified. Export byte identity, production skin weighting and bounded history need further work. [GUI evidence](evidence/GUI-SESSION.md) and [test matrix](TEST-MATRIX.md) distinguish these limits from completed functionality.

All dispatched workers and reviews finished. At M0 integration there was no unmerged branch or PR; the complete integration was in this single working tree. No thin M1, arbitrary-rig import, VaM inspector, IK or genuine model inference was added. These optional areas did not block M0.

The next three useful actions are:

1. Add a CJK font and hand-test IME, native drag/clipboard, continuous browser typing and focus/zoom on supported browsers.
2. Profile renderer/startup and measure cold Web first presentation/GPU time, then decide whether Wasm size or first-launch latency needs optimization.
3. After those acceptance gaps, implement bounded thin M1: three clips over 5–10 seconds and one interaction in a static Player, reusing this core/runtime.

PARTIAL — Actual M0 exchange and both release runtimes verified; 33 tests, fmt and dual-target clippy passed. Product/input and measurement limits above remain open.
