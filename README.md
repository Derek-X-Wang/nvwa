# Nvwa

Rust character Studio and Player for native macOS and browser WebGPU. One Rust document, command core, Bevy runtime and egui UI serve both targets. The original clothed humanoid has a continuous skinned body, four real morph targets and authored idle, wave and turn animations. These animations are presets, not AI generation.

The repository implements M0 editing/exchange plus thin M1: a three-action 5–10 second work, transport, a chest/head click that plays one wave and restores the work, and an editor-free static Player. See [M1 evidence](docs/M1-VERIFICATION.md), [verification matrix](docs/TEST-MATRIX.md) and [known issues](docs/ISSUES.md). Arbitrary character imports remain outside this prototype.

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

The local macOS bundle includes its fixture assets and demonstration work. It is unsigned; distribution signing/notarization and other operating systems need separate validation.

## Compose and play a work

In Studio, **Create 9s sequence** creates idle → wave → turn. The sequence rows change action, duration and order; each completed edit uses the same undoable command contract. The global transport can pause and seek across the whole work. Finite works stop and hold their final pose; Play/Replay restarts a completed work. The M0 single looping clip retains its previous behavior.

Click the original character's chest or head to play one authored wave. The interaction holds the sequence cursor, then restores its pose and playing/paused state. It does not change the saved document or undo history. Targets are conservative joint-following hotspots; this does not claim exact deformed-surface picking for arbitrary rigs.

Launch the same Rust app as a Player with a saved work:

```sh
NVWA_PROJECT="$PWD"
"$NVWA_PROJECT/dist/Nvwa.app/Contents/MacOS/Nvwa" --player --work "$NVWA_PROJECT/examples/m1-sequence.nvwa.json"
```

`--work` requires an absolute path and also works without `--player`. Player without a work waits for Open. Failed explicit startup shows an error and allows Open recovery. Asset paths resolve against the bundled asset directory.

For Web, build and serve as above, then open `http://127.0.0.1:9201/?player=1&work=works/m1-sequence.nvwa.json`. The Player has Open, transport and the same character interaction. It hides editing and Save. The URL loads a static same-origin relative work; refresh loads it again. Publish `dist/web` together, including `works/` and `assets/`. Static work requests reject redirects, traversal, invalid UTF-8, files above 2 MiB and requests longer than 30 seconds. No account or model service is required. Public hosting itself has not been tested.

The exchanged [revision 6 work](docs/evidence/m1/web-sequence.nvwa.json) contains both edited appearance values and a 9.5-second timeline. Open it in either Studio or Player. To publish it, copy the file into the static bundle's `works/` directory and use its relative path in the URL.

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

Recreate the three-action work through shared commands:

```sh
cargo run -p nvwa-cli --locked -- apply examples/default.nvwa.json examples/m1-commands.json /tmp/nvwa-m1.nvwa.json
cargo run -p nvwa-cli --locked -- validate /tmp/nvwa-m1.nvwa.json assets
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
