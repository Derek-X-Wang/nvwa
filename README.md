# Nvwa

Nvwa is a character creation and animation sandbox with three supported entrypoints: native macOS Studio/Player, Web Studio/Player and a source-built offline CLI. Studio and Web share one Rust document, command core, Bevy runtime and egui UI; the CLI uses the same typed command core to edit portable Work files. The original clothed humanoid has a continuous skinned body, four real morph targets and authored idle, wave and turn animations. These animations are presets, not AI generation.

The repository implements M0 editing/exchange plus thin M1: a three-action 5–10 second work, transport, a chest/head click that plays one wave and restores the work, and an editor-free static Player. See the [roadmap](docs/ROADMAP.md), [M1 evidence](docs/M1-VERIFICATION.md), [verification matrix](docs/TEST-MATRIX.md) and [known issues](docs/ISSUES.md). Arbitrary character imports remain outside this prototype.

## Run

Rust 1.95.0 is pinned in `rust-toolchain.toml`. Use the repository root:

```sh
cargo run -p nvwa-studio --locked
```

The toolbar File field names the local JSON file on native. In the packaged app, enter an absolute writable path such as /Users/your-name/Downloads/scene.nvwa.json. Open reads that path; Save writes it atomically. After an accepted New, the first native Save asks you to confirm the destination and any replacement. Cancel or a failed write keeps this protection active; later successful repeated saves use the ordinary flow. In the browser, Open invokes a local file picker and Save downloads JSON using the basename in that field. No account, model service or network command bridge is needed.

Select the character, drag the available Shape sliders, choose a clip, and use Play/Pause or the seek slider. One completed parameter drag commits one undoable command. A saved document includes all parameter values, scale, asset hash, B1 skin/eyes/hair selection, animation settings and rehearsal stage settings. Playback cursor and undo history are session state.

The inspector separates editable **Shape** parameters from read-only **Profile** details. Drag the thin separator above Animation to change the timeline height; Escape cancels a current separator drag. **Lock timeline height** prevents resizing and **Reset layout** restores Shape and the initial height while retaining the lock. Layout changes belong to this session and do not change the saved work or Undo/Redo history. The timeline scrolls when its content does not fit.

Open **Stage / 试演舞台** in the toolbar to adjust the key and fill lights, ambient light, background, floor, camera and requested quality. White studio and Black space provide starting points; Full body and Detail change framing. Right-drag the canvas to orbit, and use the wheel to change camera distance. In Studio, one completed stage gesture creates one Undo step; Escape cancels the current gesture. Player camera changes are temporary; reopen the Work to restore its saved view.

Stage settings travel with the Work through native, Web and CLI. New saves use schema 4, with an explicit character backend, diagnostic-pose field and appearance selection. Exact schema 1/2 Works open as the original GLB character; schema 3 keeps its declared backend. They keep their timeline and revision and receive no appearance; schema 1 receives the default white stage. Saving writes schema 4, which earlier Nvwa versions cannot read. Keep a copy when exchanging with older builds. Room import and physics are later stages.

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

The original B1 motion profile uses the admitted MakeHuman body and sportsuit through the full-influence CPU bridge. That legacy profile exposes `torso_length`, `jaw_drop`, two Nvwa-authored four-second rehearsal clips and five fixed diagnostic poses. Use the shared timeline transport to play, pause or seek; choosing a diagnostic pose clears the timeline in one undoable edit. Existing static B1 Works keep their static profile. B1 has no click-to-wave interaction. Appearance quality, clothing contact, arbitrary imports and generated actions remain separate gates. Assets are verified before a B1 Open replaces the current Work; rejected candidates leave the current Work and its history available. See [static integration evidence](docs/evidence/b1-work/) and [continuous-motion acceptance](docs/evidence/b1-motion/ACCEPTANCE.md).

B1's Shape inspector has independent **皮肤 / Skin**, **眼睛 / Eyes**, and **头发 / Hair** checkboxes. Each edit uses the shared Undo/Redo path and travels with the Work. The approved fixed CC0 bundle is included in native and Web builds; this does not add arbitrary skins/hair imports, gaze, blink or hair physics. Full visual quality remains a separate gate.

Open the [appearance demonstration](examples/b1-appearance.nvwa.json) to see all three selections with two continuous four-second authored actions:

```sh
cargo run -p nvwa-studio --locked -- --work "$PWD/examples/b1-appearance.nvwa.json"
```

After a Web build, the same example is at `http://127.0.0.1:9201/?work=works/b1-appearance.nvwa.json`. CLI agents can inspect it, discover `set_appearance` with `describe-capabilities`, and use `apply` without a graphical window.

The [B1 diagnostic Work](examples/b1-diagnostic.nvwa.json) was created and saved by the actual CLI. It contains torso length 0.35, jaw drop −0.5 and the combined static pose. Open it through Studio's file controls, or from the repository root:

```sh
cargo run -p nvwa-studio --locked -- --work "$PWD/examples/b1-diagnostic.nvwa.json"
```

For the original GLB character, **Create 9s sequence** creates idle → wave → turn. The sequence rows change action, duration and order; each completed edit uses the same undoable command contract. The global transport can pause and seek across the whole work. Finite works stop and hold their final pose; Play/Replay restarts a completed work. The M0 single looping clip retains its previous behavior.

Click the original character's chest or head to play one authored wave. The interaction holds the sequence cursor, then restores its pose and playing/paused state. It does not change the saved document or undo history. Targets are conservative joint-following hotspots; this does not claim exact deformed-surface picking for arbitrary rigs.

Launch the same Rust app as a Player with a saved work:

```sh
NVWA_PROJECT="$PWD"
"$NVWA_PROJECT/dist/Nvwa.app/Contents/MacOS/Nvwa" --player --work "$NVWA_PROJECT/examples/m1-sequence.nvwa.json"
```

`--work` requires an absolute path and also works without `--player`. Player without a work waits for Open. Failed explicit startup shows an error and allows Open recovery. Asset paths resolve against the bundled asset directory.

For Web, build and serve as above, then open `http://127.0.0.1:9201/?player=1&work=works/m1-sequence.nvwa.json`. The Player has Open, transport and the same character interaction. It hides editing and Save. The URL loads a static same-origin relative work; refresh loads it again. Publish `dist/web` together, including `works/` and `assets/`. Static work requests reject redirects, traversal, invalid UTF-8, files above 2 MiB and requests longer than 30 seconds. No account or model service is required. Public hosting itself has not been tested.

The exchanged [revision 6 work](docs/evidence/m1/web-sequence.nvwa.json) contains both edited appearance values and a 9.5-second timeline. Open it in either Studio or Player. To publish it, copy the file into the static bundle's `works/` directory and use its relative path in the URL.

## Programmatic edits with the native CLI

The CLI is the third supported entrypoint. It uses the same typed core commands as Studio and edits portable Work files offline. Open its saved output in native Studio or Web Studio to render and continue editing. The CLI does not control an already-open window. See [CLI support](docs/CLI-SUPPORT.md) for scope and platform evidence, and the [CLI authoring guide](docs/agents/cli-authoring.md) for command and error contracts.

The eight-parameter character candidate adds head, nose, mouth, chin, neck and hip widths to torso length and jaw opening. It is available in this branch. Actual native/Web editing and file exchange, both69-case held CPU gates and both18-step playback sequences have passed independent runtime review. The retained evidence is a pre-merge checkpoint; [PR #88](https://github.com/Derek-X-Wang/nvwa/pull/88) records final publication and CI status. Appearance/clothing quality remains HOLD. See the [current evidence and limitations](docs/evidence/b1-character-quality/RESULTS.md). To create a separate candidate Work without changing an existing file:

```sh
cargo build --locked -p nvwa-cli
mkdir -p .work
CHARACTER_OUT="$(mktemp -d .work/nvwa-character.XXXXXX)"
target/debug/nvwa-cli new-character assets "$CHARACTER_OUT/character.nvwa.json"
target/debug/nvwa-cli describe-capabilities "$CHARACTER_OUT/character.nvwa.json"
target/debug/nvwa-cli validate "$CHARACTER_OUT/character.nvwa.json" assets
cargo run -p nvwa-studio --locked -- --work "$CHARACTER_OUT/character.nvwa.json"
```

Studio's **New character…** creates the same profile. Fresh characters start with Skin, Eyes and Hair off; the checked-in `examples/b1-character.nvwa.json` selects all three. `new-b1`, `new-b1-motion` and existing Works retain their original profiles. Use `describe-capabilities` for the selected Work before sending commands; old Works do not gain the new parameters automatically.

This quickstart builds the CLI, creates a fresh ignored `.work` directory, and writes every Work and command file there. It leaves the checked-in examples and existing Works untouched. The command values below come from the current bundled profile's `describe-capabilities` response; read that response before adapting the commands to another profile.

```sh
cargo build --locked -p nvwa-cli
mkdir -p .work
CLI_OUT="$(mktemp -d .work/nvwa-cli.XXXXXX)"
CLI="$PWD/target/debug/nvwa-cli"

"$CLI" new assets/character.profile.json "$CLI_OUT/work.nvwa.json"
"$CLI" describe-capabilities "$CLI_OUT/work.nvwa.json" > "$CLI_OUT/capabilities.json"

cat > "$CLI_OUT/commands.json" <<'JSON'
[
  {
    "command_id": "quickstart-parameter-1",
    "expected_revision": 0,
    "command": {
      "type": "set_parameters",
      "character_id": "character-1",
      "values": { "jaw_width": 0.5 }
    }
  },
  {
    "command_id": "quickstart-authored-clip-2",
    "expected_revision": 1,
    "command": {
      "type": "set_timeline",
      "clips": [
        {
          "id": "quickstart-clip-1",
          "clip_id": "idle",
          "start_seconds": 0.0,
          "duration_seconds": 3.0416667,
          "speed": 1.0,
          "looping": false
        }
      ]
    }
  }
]
JSON

"$CLI" apply "$CLI_OUT/work.nvwa.json" "$CLI_OUT/commands.json" "$CLI_OUT/edited.nvwa.json"
"$CLI" validate "$CLI_OUT/edited.nvwa.json" assets
"$CLI" save "$CLI_OUT/edited.nvwa.json" "$CLI_OUT/saved.nvwa.json"
"$CLI" inspect "$CLI_OUT/saved.nvwa.json"
```

`idle` is an authored action from the bundled profile. This example edits a Work; it does not generate motion. For the full revision, session-history, file-safety and response-delivery rules, follow the [CLI authoring guide](docs/agents/cli-authoring.md).

### Standalone offline CLI distribution

Package a locally built CLI with a complete filesystem asset root:

```sh
cargo build -p nvwa-cli --release --locked --offline
python3 -B scripts/package-cli.py
python3 -B scripts/test-cli-package.py --binary target/release/nvwa-cli
```

The package builder writes a new `dist/nvwa-cli/` directory and
`dist/nvwa-cli.tar.gz`; it refuses existing destinations. Use `--binary PATH`
for another build location, `--profile debug` for the default debug binary,
or `--output NEW_DIRECTORY` for another package destination. Packaging uses
Python's standard library and downloads nothing. The extracted package needs
only the binary's build platform and local files. Use its `assets/` as the
explicit CLI root from any working directory:

```sh
NVWA_CLI_HOME="/absolute/path/to/extracted/nvwa-cli"
"$NVWA_CLI_HOME/bin/nvwa-cli" validate \
  "$NVWA_CLI_HOME/works/b1-character.nvwa.json" "$NVWA_CLI_HOME/assets"
```

Both B1 base versions, both Skin/Eyes/Hair payload bundles, the original GLB,
examples, asset licenses and provenance travel together. Native Studio and
Web export asset directories are rendering resources and omit filesystem
appearance payloads; use the standalone package for CLI authentication.
Missing or corrupted payloads still reject. The check extracts and relocates
the actual archive, runs its CLI against all supplied Works, creates and edits
new Works, and exercises missing/corrupt payload failures. See the included
[standalone usage and distribution contract](docs/CLI-STANDALONE.md).
This is a local source-built package. First-party licensing and dependency
notice coverage remain open before public binary release; signing and
clean-machine installation are separate acceptance gates.

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
