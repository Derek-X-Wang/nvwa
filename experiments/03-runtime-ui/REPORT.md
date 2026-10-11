# Runtime and Rust Studio experiment

## Hypothesis

One Bevy 0.19.1 event loop can render a skinned GLB with skeletal animation and independent recipe morph weights while egui 0.42.0 edits a validated portable document on native macOS and Wasm.

## Control and fixture

The document remains authoritative. During a slider drag, only a validated clone changes. On release, one `SetParameters` transaction enters editor history. Animation evaluation precedes recipe morph application in `PostUpdate`.

Fixture: `assets/fixtures/nvwa-humanoid.glb`; frozen SHA-256 `f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6`; profile: `assets/character.profile.json`. Runtime independently loads the raw bytes and verifies the profile SHA-256 and GLB references before spawning. Profile mappings are consumed from the published file; they are not hardcoded.

## Implementation

- `nvwa_runtime::NvwaRuntimePlugin` loads the GLB asynchronously and observes `WorldInstanceReady`, the actual Bevy 0.19 API.
- `EditorState` wraps the core editor, a separate preview clone, and typed command application.
- `RuntimeStatus` counts actual spawned mesh, skin, joint, morph, animation-player, and active/paused-animation components.
- `Playback` exposes play/pause, selected document clip, and seek requests. Undo and open restore the persisted clip; an empty timeline explicitly stops and clears playback. This M0 UI renders one selected first timeline entry rather than sequencing multiple entries.
- Studio uses egui panels in the Bevy event loop, four profile parameter sliders, object selection, undo/redo, load/save, playback and seeking.
- The initial camera is fixed. Pointer drags in egui cannot rotate it. Keyboard playback shortcuts are guarded by egui focus.
- Native assets resolve `NVWA_ASSET_ROOT`, then bundle `../Resources/assets`, then workspace development assets. Web expects canvas `#nvwa` and `assets/`.
- `--smoke --smoke-seconds N --capture PATH --timeout N` bounds the runtime run and prints `NVWA_EVIDENCE`. Screenshot success requires both the real capture callback and a nonempty native output file. Frame-time samples use at most 600 main-loop cadence observations after asset readiness plus one second of warmup, and report their build profile. They are not GPU timestamps. Evidence includes actual physical dimensions, adapter/backend, first asset readiness, and a screenshot-callback upper bound on visibility. Native `--benchmark` and Web `?benchmark=1` request physical 1280×720 with scale override 1. Web benchmark disables parent fitting, requests a real downloadable PNG after 15 seconds of readiness, and remains open. Normal Web mode retains responsive parent fitting.
- Every replacement `AnimationPlayer` initializes the selected node even when shared playback state already records that clip. This preserves playback after document import and scene reload.
- Benchmark mode explicitly uses `WinitSettings::continuous()` for focused and unfocused windows. Exact Bevy 0.19.1 defaults use continuous focused updates but reactive unfocused updates with an approximately 16.67 ms wait; this focus-dependent throttle must not determine the measured animation cadence. Normal application scheduling remains unchanged.

## Actual observations

The exact published Bevy 0.19.1 and bevy_egui 0.42.0 sources were consulted, and the integration owner ran native and browser applications on the local Apple M2 Pro. Functional evidence is recorded in [GUI-SESSION.md](../../docs/evidence/GUI-SESSION.md); executed test results are in [workspace-tests.log](../../docs/evidence/workspace-tests.log). Earlier observations below retain their checkpoint context; the final integration results are included explicitly.

Native dev Metal smoke passed with a real renderer PNG: [native/dev-smoke.png](../../docs/evidence/native/dev-smoke.png). The Studio displayed a continuous humanoid with nine mesh/skin components, 18 joints, four morphs, one animation player, and actual idle/wave playback. During wave, all four parameters changed with visible geometry changes: jaw .82, nose .91, smile .79, shoulder .99. Undo restored shoulder 0; redo restored .99 at revision 7. Save produced `edited-from-native.nvwa.json`, independently validated by the CLI against the actual assets. Pause and deselection were visible; direct file-field typing worked. Native drag and clipboard attempts did not establish successful interactions.

Web dev imported the native revision 7 document with all four parameters, geometry, and wave reference intact. This exposed a real replacement-player defect: the selected wave had zero active animations after reload. The per-player initialization repair was subsequently verified in the fresh Web release bundle: opening that document now reports Players 1, active 1 and visibly plays wave. Play/Pause works, and selecting turn changes body orientation. Together with native idle/wave, all three fixture clips have actual playback observations.

Web drag/history evidence includes a real dev shoulder drag .49→.79 with exactly one revision (8→9), followed by undo and redo. In the release retest, shoulder .99→.68 during turn playback also committed exactly once (8→9). Switching back to wave and saving produced `edited-from-web-release.nvwa.json` at revision 10. Native→Web transfer is verified. A fresh native release process subsequently opened revision 10, restored all four parameters/wave/active playback, and saved the entire semantically identical document; see exchange-result.json.

Web release rejected unsupported schema 999 with an explicit `unsupported_schema_version` error while retaining the revision 0 real character. A valid document pointing at `fixtures/missing.glb` produced an explicit asset-byte load error and zero mesh/skin/player counts. Opening the valid saved revision 10 document restored real component counts, all four parameters, wave and active 1, and cleared the error. These were real fetches and real scene components.

The full workspace test run passed **33 tests: core 13, offline CLI 4, runtime 10, Studio/platform 6**, with zero failures. Runtime regressions include a real asynchronous corrupted-to-correct asset reload, actual replacement-player initialization and animation advancement, empty-timeline stopping, completed nonloop replay/seek, fresh GLTF completion error consistency, and preview transaction/history behavior. Studio/platform tests cover typed save/open completion, invalid empty imports, bounded regular-file reads, FIFO rejection, and exclusive save temporary files. These are native test-profile results; they do not establish browser unit-test execution or formal performance.

Earlier build failures informed the implementation: exact egui panel APIs and typed platform completion were repaired; scene reflection registration and Reinhard tone mapping resolved the first native graphical startup failures. The later native PNG and fresh Web release observations supersede the earlier unverified source-only checkpoint.

After the recorded 33-test run, strict Wasm clippy found oversized Bevy system signatures. Assets/events, scene evidence queries, Studio session state, and render-surface evidence now use meaningful `SystemParam` groups without lint suppression or behavior changes. `rustfmt` passed. The integration owner subsequently reran the complete final checks: 33 tests, strict native/Wasm clippy and both release builds passed on the final source. Final source/artifact hashes are retained in docs/evidence/build-manifest.json.

## Final measurement and remaining limits

- Final isolated release measurements ran at physical 1280×720 with one real character and continuous scheduling. Native 600 samples: p50 8.34 ms, p95 8.65 ms, peak child RSS 237.05 MiB. Web 600 samples: p50 8.30 ms, p95 11.20 ms. Compilers were stopped for Web; native ran after builds with browser blank. These are main-loop cadence, not GPU timestamps. Full conditions and actual PNGs: [PERFORMANCE.md](../../docs/PERFORMANCE.md). Exact first presentation/cold Web startup/browser memory remain NOT-RUN.
- Web→native reverse-open passed in the actual native release GUI; saving after open matches the entire Web revision 10 document. Actual CLI replay also matches actual GUI documents, with reconstructed command sequences explicitly identified.
- Browser clipboard paste and the Unicode download filename `nvwa-角色.nvwa.json` worked. Default egui fonts displayed CJK text as missing-glyph squares. CJK rendering is a known product limitation; IME composition and native clipboard remain unverified.
- IAB viewport/DPR emulation caused stale display/input scaling, including when emulation was set before reload. Ordinary unoverridden browser viewport input worked. No scaling pass is claimed for the emulated 1280×720 page. The explicit benchmark physical-buffer mode was verified using DOM dimensions, Rust evidence and an actual 1280×720 PNG; at DPR 2 the CSS canvas was 640×360. Use no viewport emulation.
- M0 uses one selected first timeline entry; multi-entry timeline sequencing and camera orbit are outside this experiment.

## Decision

**Adopt the shared Bevy runtime and Rust egui Studio for M0.** Real native Metal and Web release WebGPU execution demonstrate the skinned/morphable character, animation, document editing, history, native→Web transfer, and browser error recovery through one shared application loop. Bidirectional exchange and isolated release cadence now have actual evidence. Acceptance remains partial for text/input coverage and exact GPU/first-frame measurements, as listed above.

## Reproduction

Run from the repository root with the pinned toolchain and fixture. Reserve graphics and compiler slots through the integration owner; render only one application during formal measurement.

```sh
cargo test --workspace --locked
CARGO_BUILD_JOBS=3 cargo build -p nvwa-studio --locked
cargo run -p nvwa-studio --locked -- --smoke --smoke-seconds 3 --capture /absolute/existing-directory/nvwa.png --timeout 45
CARGO_BUILD_JOBS=2 cargo build -p nvwa-studio --release --target wasm32-unknown-unknown --locked
```

The commands above are reproduction instructions, not additional runs made while writing this report. The shared library exports `build_app() -> App`, `run() -> AppExit`, and the Wasm start function; native `main` returns `run()`'s exit status. Bundle and serve the Web build with the integration-owned tooling and load the ordinary viewport without emulation for interaction checks. Use `?benchmark=1` separately for a physical-buffer screenshot/cadence run. Those reverse-open and isolated release checks were completed by the integration owner; reproduction should retain the same fixture and resource conditions.


The Web automatic Bevy screenshot callback did not produce a persistent file in IAB. An explicit benchmark-only canvas.toBlob button with a user-activated download produced independently inspected real pixels. No character/editor business logic moved to JS. Unique first-screen gzip bytes total 14,113,867; duplicate asset transfers and cold-network limitations are recorded separately in PERFORMANCE.md.

PARTIAL — Both release runtimes, real four-morph/skeletal editing, bidirectional exchange, 33 tests, strict dual-target clippy and cadence measurements passed. Chinese glyphs/IME, some input/scaling cases and exact GPU/first-frame timing remain open.
