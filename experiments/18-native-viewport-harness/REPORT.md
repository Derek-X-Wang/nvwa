# Native target-size validation

Decision: retain this isolated validation helper. It does not change the product
entry point, source, dependencies, commands, Work schema or layout behavior.
Its actual1024×768 GUI result resolves the production native UI size/control
check without requiring the human to resize a window to an exact pixel count.

The helper calls production `nvwa_studio::build_app()`, requires exactly one
primary window, sets its initial logical resolution to1024×768 and runs it.
It builds offline with its own workspace and lock. All389 Studio dependency
identities, edges and enabled features match production. All31 frozen production
inputs remain unchanged. Independent review checked this method before launch.

The release build passed in254.428 seconds. Its separate arm64 executable is
103,090,096 bytes, SHA256
`6d011dcddb4828bd0245665d17292666af76b68e69726df7a2a22375e1efd037`.
This is a helper build record, not a performance comparison or the packaged
Studio executable identity.

Root ran the real native application and rig, then operated Shape/Profile,
lock, reset retaining lock, unlock, the horizontal scrollbar in both directions,
play/pause and seek. The saved Work matches the human handback in every field,
including revision8. See [actual captures and complete Works](../../docs/evidence/m1-1-ui/gui/followup/README.md).

The interactive CUA capture buffers are2048×1600 including chrome. To verify
the application geometry separately, root ran the existing production smoke
observer. A focused15-second observation reports physical1024×768 at scale1,
which gives logical1024×768. It is ready with9 meshes,9 skins,18 joints and
morph weights. The source Work is revision8; there is no reported runtime error.
[Raw runtime evidence](evidence/interactive-geometry-evidence.json) retains
cadence numbers, but this short functional run is not a performance benchmark.
Capture-buffer dimensions do not establish runtime DPI.

The first smoke exited0, but the default WARN logger omitted the INFO geometry
line. A repeat with task-local `RUST_LOG=info` also exited0. Its post-run check
incorrectly required scale2 and failed when the application reported scale1.
The corrected check uses physical dimensions divided by the reported scale;
the requested logical viewport is1024×768. Both raw logs are retained. A later
focused run independently confirmed this logical size and exited0. No product
error or failed product test was removed.

Exact packaged-binary1024 startup, a native resize transition to that exact size,
physical IME, DPI/zoom and other platforms remain NOT-RUN. Packaged native
startup1280×720, human resize1175×704, native exchange/reload/Player and human
gestures are separately evidenced. The helper was stopped, and the unchanged
packaged Studio was restored with the saved0.73/revision8 Work.

Build and launch reproduction are in [README.md](README.md). For geometry:

```sh
NVWA_VIEWPORT_PROJECT="$PWD"
cp examples/m1-sequence.nvwa.json /tmp/nvwa-viewport-work.nvwa.json
RUST_LOG=info NVWA_ASSET_ROOT="$NVWA_VIEWPORT_PROJECT/assets" \
  target/release/nvwa-native-viewport-harness \
  --work /tmp/nvwa-viewport-work.nvwa.json \
  --smoke --smoke-seconds 15 --timeout 30 \
  --capture /tmp/nvwa-viewport.png
```

Read `NVWA_EVIDENCE` and compute logical dimensions from `physical_window`.
Open a normal helper run without `--smoke` for actual interaction. Save before
and after layout/transport actions and compare complete JSON including revision.
Commands are reproduction instructions, not new evidence of another machine.

[Evidence inventory](evidence/MANIFEST.json) records original/copy hashes and
exact worktree-prefix replacement counts. Full Cargo metadata, private process
records, captures containing private paths and executable copies remain private.

VERIFIED — isolated release build, unchanged production inputs/dependencies,
actual native1024×768 UI controls and complete Work invariance; listed packaged
geometry, physical-input/platform and performance limits remain explicit.
