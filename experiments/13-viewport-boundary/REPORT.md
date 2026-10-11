# Viewport boundary preparation

Conclusion: adopt the disposable diagnostic; inconclusive for actual browser zoom/DPR. Root verified live1600×900 and1024×768 drag/one Undo with whole saved documents, focused caret and restoration; native scale2 track-click/Undo passed. See [actual acceptance](../../docs/evidence/viewport-boundary/ACCEPTANCE.md).

Outcome: **PARTIAL**. A bounded DOM collector and installer are ready for the integration owner's actual unchanged Web bundle. The original simulated-DPR input failure remains **UNREPRODUCED**. This workstream did not run the app, browser, GPU, native regression, resize case, real scale change, zoom, or real tab hide/show. It proposes no workaround or causal diagnosis.

Managed source checkout: `/Users/derekxwang/.codex/worktrees/viewport-diagnosis/nvwa` at `4b9ba411b88d2f6f6dba90bba1c2760bface2237`. Pinned lock versions: Bevy Window/Winit 0.19.1, bevy_egui 0.42.0, egui 0.36.2, winit 0.30.13. The existing experiment 11 report supplies prior size-only passing evidence and current DPR-interface limits; it is not a new measurement made here.

## Actual source boundary

These facts describe the exact owning source. They do not establish that every stage received fresh values in a running browser. `source-evidence.json` preserves each absolute source path, SHA256, and numbered excerpts, including the project code, Cargo files, and experiment 09 gzip-preferring server. Registry paths below start with `/Users/derekxwang/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/`.

| Boundary | Exact source location | Behavior |
| --- | --- | --- |
| Page CSS and chosen canvas | Project `web/index.html:5–15`; `crates/nvwa-studio/src/lib.rs:94–119` | Canvas `#nvwa` is borderless, block, 100% width/height under a full-size body. Ordinary Studio starts with requested 1280×720 and parent fitting. Benchmark mode overrides scale 1 and disables parent fitting. |
| Parent fitting | `bevy_winit-0.19.1/src/system.rs:101–112` | Parent fitting sets canvas inline width/height to `100%`. This is CSS sizing, separate from backing-buffer dimensions. |
| Browser scale | `winit-0.30.13/src/platform_impl/web/web_sys/mod.rs:52–54` | Winit's Web scale function reads `window.device_pixel_ratio()`. |
| Browser physical size | `winit-0.30.13/src/platform_impl/web/web_sys/resize_scaling.rs:87–100,136–150,227–268` | ResizeObserver supplies device-pixel content size where supported. Otherwise content rectangle is converted to physical size using current DPR. Scale and resize callbacks have separate paths. |
| Scale notification | `winit-0.30.13/src/platform_impl/web/web_sys/canvas.rs:460–491` | Winit sends `ScaleFactorChanged`, then can resize the canvas when an inner-size writer requests a changed size. |
| Browser pointer to Winit | `winit-0.30.13/src/platform_impl/web/web_sys/event.rs:83–98`; `pointer.rs:78–96` | Pointer offset X/Y are read as logical coordinates and converted to physical coordinates using the Web scale function. No experiment replaces this algorithm. |
| Winit to Bevy | `bevy_winit-0.19.1/src/state.rs:285–300,914–928,938–958`; `bevy_window-0.19.1/src/window.rs:935–947,971–987` | Cursor physical position is divided by the Bevy resolution scale factor. Resize updates physical resolution. A scale event updates backend scale. An override changes the effective scale factor; logical width/height are physical dimensions divided by effective scale. |
| Bevy to egui pointer | `bevy_egui-0.42.0/src/input.rs:475–484` | Bevy logical pointer position is divided by egui zoom factor. |
| egui scale and viewport | `bevy_egui-0.42.0/src/input.rs:1510–1516`; `lib.rs:1777–1796`; `bevy_camera-0.19.1/src/camera.rs:520–525`; `egui-0.36.2/src/context.rs:450–455` | Egui native pixels per point comes from the camera target scale. Egui pixels per point is zoom×native pixels per point. Egui screen rectangle comes from camera physical viewport divided by output pixels per point. These are not directly exposed by the DOM collector. |
| Text proxy placement | Project `crates/nvwa-studio/src/web_input.rs:316–342,644–670` | A fixed, transparent 1×1 textarea is positioned using egui cursor points→backing pixels→canvas CSS rectangle. The collector reads generic input geometry only; it does not call this Rust code or read input values. |

The normal source path intends agreement between browser CSS coordinates, browser physical sizes, Bevy logical coordinates, and egui points. A mismatched ratio can identify a DOM-boundary inconsistency worth investigating. A matching DOM ratio cannot prove downstream input correctness. Saved-document edits and actual caret/pointer interaction must remain the acceptance signal.

## Delivered scope and checks

- `diagnostic-panel.html`: appended diagnostic UI; fixed collapsed overlay, outside canvas layout.
- `collector.js`: actual DOM snapshots, reported DPR and visual viewport, canvas CSS/client/buffer geometry, supported device-pixel observer boxes, generic input geometry, and resize/focus/visibility events. Bounded 180-record ring and 180-second, 1 Hz sampling windows. No text, pointer, keyboard, clipboard, app-state, or runtime API observation.
- `install.py`: copies a supplied current dist into a new path, appends diagnostics, regenerates an existing HTML gzip sidecar with timestamp zero, and verifies every source file other than those two intentional changes stays byte-identical. No dependency installation/build.
- `README.md`: collection sequence, expected observations, unavailable-case handling, and cleanup.
- `source-evidence.json`: 18 exact source/code paths and hashes plus relevant source excerpts.
- `checks.json` and `checked-dist-manifest.json`: actual lightweight verification records.
- `packaging-failure-evidence.json` and the two `*-before-sidecar-fix.json` files: stale-sidecar reproduction and preserved initial checks.
- `python39-failure-evidence.json` and the two `*-before-python39-fix.json` files: actual Python 3.9.5 traceback before destination creation and preserved checks before the portability correction.
- `artifact-sha256.json`: frozen final artifact hashes, excluding the hash manifest itself.

The initial installer preserved `index.html.gz` while patching `index.html`. That is a real packaging defect: experiment 09's `http_probe_server.py:57–71` serves the gzip sidecar when an explicit file request accepts gzip. The preserved sidecar lacked the diagnostic node and differed from the patched HTML. The initial check's 20 unchanged non-index files therefore gave insufficient serving assurance. `packaging-failure-evidence.json` records the red byte comparison; the original checks are retained without alteration. No HTTP/browser reproduction is claimed.

The corrected installer regenerates an existing `index.html.gz` deterministically with `mtime=0` and records both HTML files as intentional changes in manifest schema 2. Fresh lightweight checks against `/Users/derekxwang/Development/incubator/Nvwa/nvwa/dist/web` verified exact insertion, gzip decompression equals patched HTML, zero gzip timestamp, identical gzip bytes across two separate installs, and byte equality for all 19 other source files. JS syntax and Python AST parse also passed. The checked Wasm SHA256 stayed `0d8e1b7907d82f1b6d7fbd9799d54bb90e2bdce9797979a4df06fdd9801cc93c`. Diagnostic index SHA256: `ec92d96547b4bebbdd48b04f21a55f38cd3f11ecbc8de18ae3b154cd00fce52e`; diagnostic gzip SHA256: `c38ac6cc6b84c7f713163038eaf044a87559e13a10e77202962864100b7896da`.

Both temporary dist copies and Python import cache were removed. The integration owner must retain the manifest from the actual served diagnostic copy; this disk check is not proof that its source bundle was run. If source HTML differs, diagnostic HTML/gzip hashes will also differ as expected.

The earlier SHA256 helper used `hashlib.file_digest`, which requires Python 3.11 or later. Actual Python 3.9.5 execution failed with `AttributeError` before creating the destination; the exact traceback is preserved. The helper now hashes portable 1 MiB chunks. Fresh checks ran the corrected installer twice under `/Users/derekxwang/.pyenv/versions/3.9.5/bin/python3`, verified independent whole-byte SHA256 identity, all 19 unchanged files, exact HTML insertion, gzip equivalence, zero timestamp, and repeatable gzip bytes. Diagnostic HTML/gzip and Wasm hashes stayed identical to the values above. Temporary copies/cache were removed. No server/browser/app/GPU was run.

No repository files outside `experiments/13-viewport-boundary/` were changed. No production/dependency/lock/shared-document/shared-evidence write, commit, push, PR, remote write, machine setting, browser extension, or persistent process was created.

Remaining unknowns: actual propagated Rust scales, original simulated-DPR failure, real browser DPR/zoom changes, real hide/show recovery, ordinary native scale-2 interaction, and fresh browser measurement records. Current width/height-only viewport capabilities must not be described as working DPR emulation. Keep issue #3 open unless the original symptom and its acceptance cases are actually reproduced and resolved.

PARTIAL — syntax and actual-dist byte preservation pass; all GUI, scale-change, and input-regression collection is integration-owned and NOT-RUN in this workstream.
