# Stage A — acceptance record, 2026-10-16

**PARTIAL — actual Web and CLI checks passed. Native Studio compiles; native visual and window-input acceptance is blocked by the locked Mac. Final integration CI and merged-main CI are separate gates.**

Scope: [#70](https://github.com/Derek-X-Wang/nvwa/issues/70), the first stage of [#69](https://github.com/Derek-X-Wang/nvwa/issues/69). The same Rust Work/command/runtime now supports adjustable lights, background/floor, camera and quality. Stage settings save and travel with the character. Room import, physics, networking, model inference and new assets are outside this slice. #69 remains open for later stages; #70 stays open until its actual native acceptance is complete.

## Executed evidence

| Boundary | Result and evidence |
| --- | --- |
| Shared core, CLI and actual egui/runtime control paths | 137 workspace tests passed. Strict core/CLI Clippy and formatting passed. Source/build details and earlier real failures are retained in [IMPLEMENTATION.md](IMPLEMENTATION.md). CPU tests do not prove GPU images or physical input. |
| Actual CLI process and files | [prepare.py](runtime/prepare.py) ran the real binary: discovery, strict schema 1 upgrade, five stage variants, asset validation, one-command Undo/Redo, exact save roundtrip and invalid-stage output preservation. [Full command receipts](runtime/cli-receipts.json). |
| Web startup and real character | Actual WebGPU Studio loaded the real rigged/morphed character and completed the nine-second sequence. Head and feet fit the scene after the framing correction. [Web receipt](runtime/web-v2-receipt.json). |
| Web adjustments | Actual light drag committed once; Undo/Redo restored intensity. One wheel burst committed once; Undo restored distance. White/Black and Full body/Detail presets worked. Background, floor visibility and floor-shadow changes worked and undid independently. Actual chest click waved and returned to the original paused frame without a Work revision change. |
| Web quality | Same-pose Low, Balanced and High images retain the real character and floor. Low omits shadows; Balanced and High use PBR shadows. The optional contact pass caused visible speckle and was disabled; High keeps its larger shadow map. These are functional/visual checks, not cost measurements or a human preference result. |
| Web save/open/recovery | The actual downloaded schema 2 Work retained stage, character and timeline. Invalid camera distance produced a visible error and preserved the current stage/character/revision. Opening the actual good saved file recovered normally. Saving again produced [byte-identical files](runtime/web-v2-roundtrip.nvwa.json). |
| Ordinary Web at fixed 1024×768 | Fresh Studio and Player showed full head/feet. Player wheel changed only its temporary view; reopening the Work restored the saved view. Escape cancels an active gesture, not a previously completed gesture. [Responsive observations](runtime/responsive-observations.json). |
| Native startup versus actual acceptance | The actual smoke process exited 0 but its readback was black while the GUI tool explicitly reported the Mac locked. [Failure receipt](runtime/native-v2-locked.json) and [actual black image](runtime/native-v2-locked-black.png) are retained. They do not establish a displayed frame, working native controls or native visual quality. No repeated native cases were attempted under the same blocked condition. |

## Source and artifact cohorts

The pre-fix images in `runtime/pre-fix-*` are intentional failure evidence. Initial source `fe4afb6` cropped the full-body frame and produced High contact-shadow speckle. The tests reproduced the framing failures before the fix; no failure checks were disabled.

Corrected **framing-v2** source is `db0139e0ffb195abf681620e6f691eb103ce2dd3`. Its complete 34-file source map was checked against both built artifact manifests before Web acceptance. The [public artifact identity record](runtime/artifact-cohorts.json) retains both cohorts' source maps, sizes, hashes and original private-manifest hashes, omitting only private absolute output paths. Native Studio SHA-256 is `60e8daf6d7eb4014a5a97e184a671850b67f7b533df3541d8b5fac24c8fb6114`; browser Wasm is `f98eb1f4f9748918edb8cc26231202a6a13fe3cad2ecad48a0e1c8dd294c2f78`; CLI is `5201bd01c67e9c24f1cc57d81af4ddd649a0981cf31c0c196d3cf36cdd95bbaa`. All are dev builds, not release performance artifacts. V2 is the source of the persisted Web images/save exchange and the blocked native attempt.

Source `b43757d87dde8294525769a98db17eab57a886fc` subsequently changes only the movable Stage window's initial x position from 195 to 12, translates the existing UI test pointer coordinates and records the change. It does not change the camera, schema, quality, layout calculation or CLI. All 137 workspace tests passed again. Its distinct **framing-v3** artifacts passed the [final placement check](runtime/web-v3-receipt.json): fresh ordinary Studio at 1024×768 and fixed Studio at 1280×720 show the full character beside the open Stage window. The [actual V3 canvas](runtime/web-v3-stage.png) is recorded separately rather than relabeling V2 captures as V3. Both paired native/Web 34-file source maps and actual artifact sizes/hashes were checked before this bounded recheck. V3 native Studio is built, not graphically accepted.

## Reproduce from a checkout

```sh
cargo test --workspace --locked
cargo clippy -p nvwa-core -p nvwa-cli --all-targets --locked -- -D warnings
cargo fmt --all --check
cargo build -p nvwa-cli -p nvwa-studio --locked
python3 -B docs/evidence/rehearsal-stage/runtime/prepare.py --cli "$PWD/target/debug/nvwa-cli"
NVWA_ASSET_ROOT="$PWD/assets" cargo run -p nvwa-studio --locked -- --work "$PWD/.work/rehearsal-acceptance/white-balanced.nvwa.json"
```

Use an existing pinned `wasm-bindgen 0.2.129`, then build Web with `bash scripts/build-web.sh dev`. Copy the five `.work/rehearsal-acceptance/*-*.nvwa.json` variant Works to `dist/web/works/` and serve with `python3 scripts/serve-web.py --port 9205`, after checking that port is free. Open `http://127.0.0.1:9205/?work=works/white-high.nvwa.json`; add `&player=1` for Player. The `benchmark=1` UI offers a canvas download for visual evidence and has a fixed 1280×720 canvas; it is not the ordinary responsive layout. A custom `CARGO_TARGET_DIR` requires adjusting the CLI path above. Cached dependencies permit `--offline`; do not download models or run inference for this feature.

## Honest remaining boundaries

- Native displayed character, adjustable stage controls, native save → Web open exchange, and the final V3 native artifact still need an unlocked desktop. Earlier native acceptance from other features does not certify this renderer change.
- Physical right-button drag and mid-drag Escape, physical monitor/DPI migration and human stage preference were not exercised by the UI tool. Actual egui tests cover command grouping, Escape, widget/IME ownership and read-only Player state.
- Changing the IAB viewport live from 1280 to 1024 showed reduced displayed extent until reload, despite DOM CSS/buffer reporting 1024×768. Fresh fixed-size startup worked. No cause is assigned and no product workaround is added; #3 remains blocked.
- First physically displayed frame, cold-start, GPU timestamps, GPU memory, controlled quality cost and a release comparison remain outside this check. #4 keeps its prior gaps. Console main-loop cadence is not GPU frame time.
- Experiment 50's existing motion A/B captures use the explicitly archived pre-stage runtime. Experiment 51 keeps those earlier historical checks strict after schema evolution; it does not turn old captures into proof of the new stage. Production motion mapping and its quality HOLD are unchanged.
