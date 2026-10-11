# Nvwa

Rust character Studio for native macOS and browser WebGPU. One Rust document, command core, Bevy runtime and egui editor serve both targets. The original clothed humanoid has a continuous skinned body, four real morph targets and authored idle, wave and turn animations. These animations are presets, not AI generation.

The repository implements a bounded M0: one fixed character rig, parameter editing, clip playback, undo/redo and portable JSON files. See [verification matrix](docs/TEST-MATRIX.md) for actual build/run evidence and unfinished validation. Multi-clip sequencing and arbitrary character imports are outside the delivered M0.

## Run

Rust 1.95.0 is pinned in `rust-toolchain.toml`. Use the repository root:

```sh
cargo run -p nvwa-studio --locked
```

The toolbar File field names the local JSON file on native. In the packaged app, enter an absolute writable path such as /Users/your-name/Downloads/scene.nvwa.json. Open reads that path; Save writes it atomically. In the browser, Open invokes a local file picker and Save downloads JSON using the basename in that field. No account, model service or network command bridge is needed.

Select the character, drag the four sliders, choose a clip, and use Play/Pause or the seek slider. One completed parameter drag commits one undoable command. A saved document includes all parameter values, scale, asset hash and animation settings. Playback cursor and undo history are session state.

```sh
python3 scripts/install-web-tools.py
bash scripts/build-web.sh
python3 scripts/serve-web.py
```

Open `http://127.0.0.1:9201` in a WebGPU browser. This is an ordinary static bundle at `dist/web`; the development server listens on loopback only. If WebGPU is unavailable, the page displays a boot error. The small HTML/JS bootstrap carries no editor or character business logic. The tool installer currently supports macOS arm64 and downloads the exact official wasm-bindgen release with a pinned SHA-256.

```sh
cargo build -p nvwa-studio --release --locked
python3 scripts/package-native.py
open dist/Nvwa.app
```

The local macOS bundle includes its fixture assets. It is unsigned; distribution signing/notarization and other operating systems need separate validation.

## Programmatic edits

The CLI uses the same typed core commands as the Studio. It edits offline documents; reopen the result in Studio to see it. It does not control an already-open window.

```sh
cargo run -p nvwa-cli --locked -- new assets/character.profile.json examples/default.nvwa.json
cargo run -p nvwa-cli --locked -- describe-capabilities examples/default.nvwa.json
cargo run -p nvwa-cli --locked -- apply examples/default.nvwa.json examples/m0-commands.json examples/edited.nvwa.json
cargo run -p nvwa-cli --locked -- validate examples/edited.nvwa.json assets
cargo run -p nvwa-cli --locked -- save examples/edited.nvwa.json examples/portable.nvwa.json
cargo run -p nvwa-cli --locked -- inspect examples/portable.nvwa.json
```

Commands include expected revision and unique command IDs. Failed edits preserve the original document. Repeating an identical envelope is idempotent within an editor session. Conflicting ID reuse, stale revisions, unknown fields, duplicate JSON keys, invalid ranges, oversized JSON and unsafe asset paths return structured errors.

## Verify and reproduce

```sh
cargo test --workspace --locked
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --locked -- -D warnings
python3 tools/blender/validate_fixture.py
```

For a release native measurement, close other Nvwa renderers and pause heavy tasks, then run `python3 scripts/benchmark-native.py --seconds 15`. For Web, open `http://127.0.0.1:9201/?benchmark=1` without viewport emulation. Read `NVWA_EVIDENCE` in console.log and use the page's PNG button; automatic Bevy downloads did not persist in the tested IAB. These are main-loop cadence samples, not GPU timestamps.

For bounded native startup with a real rendered image, create the capture directory first:

```sh
mkdir -p dist/evidence
cargo run -p nvwa-studio --locked -- --smoke --smoke-seconds 3 --capture "$PWD/dist/evidence/native.png" --timeout 45
```

[Experiments](docs/EXPERIMENTS.md), [performance](docs/PERFORMANCE.md), [contract](docs/implementation/contract.md), [handoff](docs/HANDOFF.md) and [asset authoring](tools/blender/README.md) document decisions, limitations and reproduction. Generated build output lives in ignored `target/`, `.tools/` and `dist/`. No CI, paid resources or cloud deployment is required.
