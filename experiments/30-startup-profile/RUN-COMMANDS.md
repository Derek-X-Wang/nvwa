# Exact proposed commands and evidence skeleton

Root owns the lease gates. These commands are not executed merely by documenting
them. Base is `045d8abc685760d09ba05afec0e40a811a282d1f`. The canonical Work
is the root-assigned actual earlier GUI Work copied byte-for-byte to private
`.work/m11-startup/inputs/canonical-work.nvwa.json`, SHA256
`cacf849f0918648a1a970452d0c33f195c5ad89fd7f6d9e58669d587d0789768`.
It is schema1/revision3 with finite idle/wave/turn3+3+3seconds,1280x720/scale1.

After the sole Cargo writer lease, with initial free storage above32GiB,
abort below8GiB, deadline30minutes and no other Cargo writer:

```sh
CARGO_TARGET_DIR=/Users/derekxwang/Development/incubator/Nvwa/nvwa/target cargo build --offline --release --manifest-path experiments/30-startup-profile/Cargo.toml --jobs 1
CARGO_TARGET_DIR=/Users/derekxwang/Development/incubator/Nvwa/nvwa/target cargo build --offline --release --manifest-path experiments/31-ui-pixels/Cargo.toml --jobs 1
python3 -B experiments/30-startup-profile/verify_locked_versions.py --root-lock Cargo.lock --experiment-lock experiments/30-startup-profile/Cargo.lock
python3 -B experiments/30-startup-profile/verify_locked_versions.py --root-lock Cargo.lock --experiment-lock experiments/31-ui-pixels/Cargo.lock
```

Capture actual `cargo metadata --offline --locked --format-version 1` for root
and both experiment manifests within that lease. Compare resolved enabled
dependency feature sets and package versions; lockfile verification alone is
not feature verification. Keep build stdout/stderr, statuses, actual command,
start/end/storage inventory and executable SHA256. Root Cargo.lock must retain
its baseline hash. Any unsupported API repair remains in experiment source.

Root completes `FREEZE-PROPOSAL.json` with real binary hashes, approved Work,
actual resolved-feature comparison and explicit approval, saving a private
`.work/m11-startup/freeze.json`. Then:

```sh
python3 -B experiments/30-startup-profile/prepare_bundles.py --freeze /Users/derekxwang/.codex/worktrees/m11-startup-pixels/nvwa/.work/m11-startup/freeze.json
```

The fixed scripts copy verified binaries into the private `frozen/` directory;
future target-cache changes cannot alter these exact running bytes. Source-only
app scaffolds reject launch. Preparing a freeze does not grant a GPU lease.
After compile processes stop, root grants exclusive native GPU/UI control.
Only these exact path-bound cua calls launch the native apps, one at a time:

```js
var native1 = await cua.getApp("/Users/derekxwang/.codex/worktrees/m11-startup-pixels/nvwa/.work/m11-startup/apps/NvwaStartup1.app");
// Verify first exit, helper exits and exact ownership before native2.
var native2 = await cua.getApp("/Users/derekxwang/.codex/worktrees/m11-startup-pixels/nvwa/.work/m11-startup/apps/NvwaStartup2.app");
// Verify second exit and profiler/helper exits before pixels.
var pixels = await cua.getApp("/Users/derekxwang/.codex/worktrees/m11-startup-pixels/nvwa/.work/m11-startup/apps/NvwaTabPixels.app");
```

Each launcher preserves PID through exec, redirects stdout/stderr to exclusive
private files, records launch wall/monotonic bounds, and accepts fixed arguments
only. The external watchdog covers all three apps without requiring a Rust marker.
Bounded ps inspection has live, kernel-confirmed absence and unknown states.
Unknown inspections never authorize a signal or exit claim. Optional native2
profiling waits for the real Rust marker and cannot abandon the mandatory guard. Sample4seconds at1ms and vmmap apply only to native2. A missed
early stall remains unprofiled; actual coverage/attachment times must be reported.
No stack sample establishes shader attribution without stack evidence. Normal
native runs request12seconds after readiness; frozen Web benchmark requests15.
Those callback delays are not directly comparable startup performance.

Pixel assertions, on actual PNGs after finite app exit:

```sh
python3 -B experiments/31-ui-pixels/verify_pixels.py .work/m11-startup/captures/pixels/normal-shape.png --case normal-shape
python3 -B experiments/31-ui-pixels/verify_pixels.py .work/m11-startup/captures/pixels/normal-profile.png --case normal-profile
python3 -B experiments/31-ui-pixels/verify_pixels.py .work/m11-startup/captures/pixels/mutant-profile.png --case normal-profile
```

Required exits:0,0,1. Preserve raw results and `PIXEL_CASE` state records. Missing
captures fail. Independently inspect each image; never generate a reference
from the observed selected state or captured fills.

After native+pixel cleanup and explicit UI lease release, root owns the single
Web run because the worker's refreshed Cua inventory has no browser adapter.
Do not retry that unchanged worker route. Root has independently verified IAB.
Root assigns frozen Web root/evidence and grants server lifetime before:

```sh
python3 -B experiments/30-startup-profile/web_control_server.py --root ROOT_ASSIGNED_FROZEN_WEB --evidence ROOT_ASSIGNED_EMPTY_WEB_EVIDENCE
```

The adapter binds only127.0.0.1:9203, allows one fresh startup, and reuses the
unchanged experiment24 no-store and exact-body boundary. Root controls the
fresh IAB tab, saves read-only collector+actual pixels, and relays evidence for
reconciliation. Use its supplied actual supported browser documentation.

Private per-run evidence directory skeleton:

- `launcher.json`, stdout/stderr, one-launch guard: identity and command.
- `process-observations.json`: exact-child sampled RSS and helper coverage.
- native2 sample/vmmap outputs and command statuses: profiling observations.
- actual PNG and cua observation bounds: raster/visibility upper-bound evidence.
- source+binary+Work+asset hashes, resolved features, build results.
- before/after compiler/renderer inventory and exact cleanup receipts.

Separate report clocks: host monotonic launch/sampling/observation bounds;
Rust Instant before build_app; Bevy Time<Real> since first update; Web navigation
timeOrigin. Render return, GPU callback, readiness and pixels remain distinct.
Exact first presentation, fully cold OS/GPU/shader state, true peak RSS and
unavailable GPU/browser memory remain NOT-RUN.
