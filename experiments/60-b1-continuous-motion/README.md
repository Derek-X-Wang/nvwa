# B1 continuous authored rehearsal probe

Bounded issue78 validation callers for the actual production runtime and Studio. Clips are authored, not AI-generated. This directory does not change product code, source assets, experiments53–59 or the root lockfile. The public product contract is [b1-motion-contract.md](../../docs/implementation/b1-motion-contract.md); actual root results are [tracked separately](../../docs/evidence/b1-motion/ACCEPTANCE.md). The frozen validation contract includes the IBM erratum: rest*IBM≈I, posed*IBM≈independent expectedFK*IBM. Posed skin normally is not identity at a nonneutral frame.

## Evidence boundaries

- `matrix` installs the complete production `NvwaRuntimePlugin`, actual asset loaders, rig fitting and mesh upload. It uses a manual production Time clock, exact Playback seeks and the production `b1_frame_snapshot`; no window, renderer or GPU. The minimal Bevy host matches the existing production-plugin regression harness. This is production-plugin CPU evidence, not Studio GUI evidence.
- `studio` and the Wasm library call exact public `nvwa_studio::build_app()` with its normal startup/Work/controls. Only an additive Last-stage command/snapshot controller is installed. There is no alternate motion evaluator or substitute viewer UI. A custom canvas bootstrap loads this unchanged Studio surface.
- `checker.py` reconstructs canonical FK independently in Python f64 using separately frozen authored amplitude values, source names/parents and fitted rest/gauges. It independently transfers original source weights through signed MHCLO triples, filters positive final aggregates, normalizes and evaluates LBS against actual uploaded positions. It never calls a production sampler to create expectations. Actual display_transform already includes source root, fixed placement and scale; the checker applies it once. model_to_world is only removed when measuring the fixed placement.
- `test_controls.py` controls are explicitly comparator-only known geometry/tampered records. They do not prove an executed compiled-source mutation. Root must schedule at least two actual production Rust mutation-red runs and restoration green separately.

Current worker verification: 15 comparator-only controls pass under normal Python and `-O`; Rust sources format/parse; the experiment lock resolves offline with no extra package/version besides this experiment. The authorized local native all-target metadata check passed in2m33s with no compile correction required. Executable linking, actual matrix, Desktop, Web, GPU, historical58 geometry-control execution and production Rust mutations are NOT-RUN by this worker. Existing sportsuit quality remains HOLD.

## Root-owned build and CPU run

All paths below are from repository root. Builds must use root's single heavy-work lane/wefty policy. Existing dependencies/tools only; no downloads. The independent lockfile's only new package identity is `b1-continuous-probe` itself. Root owns build/output identity binding.

```sh
CARGO_NET_OFFLINE=true CARGO_BUILD_JOBS=1 cargo build --offline --locked \
  --manifest-path experiments/60-b1-continuous-motion/Cargo.toml --bins
python3 -B experiments/60-b1-continuous-motion/run_matrix.py \
  --binary "$PWD/experiments/60-b1-continuous-motion/target/debug/matrix" \
  --asset-root "$PWD/assets" --out "$PWD/.work/b1-continuous/NEW-cpu-results"
```

`--out` must not exist. The native process streams frames through a pipe, one frame at a time. The checker writes compact metrics for every sample, full actual bone/patch data, all failures and coverage. Only the declared30 deep keyframes and first three additional failures get full lossless gzip snapshots. Extra failures retain exact request/error/record digests but not full geometry; this retention limit is explicit. Root may rerun an exact failing request for additional lossless capture. No mesh arrays are retained for all594 frames in memory or as public giant JSON. The summary is nonzero for any failure, missing sample, missing completion marker or missing keyframe; endpoint failures remain in receipts. Partial output from an interrupted child remains partial. `--skip-surfaces` is a diagnostic shortcut explicitly labelled NOT-RUN in metrics; it cannot fill the surface-descriptor gate.

The matrix checker validates `k` as a non-bool integer0..32, requires request.seconds exactly `k/8`, and binds both finite timeline cursor and source time to that request before granting coverage or keyframe credit. A relabelled neutral frame cannot fill the grid; a comparator-only control exercises that rejection through the actual Checker.check entry point. The earlier checker lacked this grid/time binding, so its receipts are provisional until rerun with this version. Rust binaries and source semantics are unchanged by this checker correction.

Matrix: torso[-1,0,1]×jaw[-1,0,1]×2clips×33times k/8=594. These are three body variants with three face settings. It uses finite nonloop timeline entries, so t4 is the real closed endpoint. Neutral-recipe nonmonotonic/off-grid seeks and pause stability are extra records. Loop4→source0, speed/sequence/history/failure/shape-intent cases are owned by product integration tests; this runner does not claim those solely from its finite matrix. Deep30: jaw0, allthree torso settings, both clips, times0/1/2/3/4. Bounded nearest-triangle BVH queries cover all garment source points against genuine full body and displayed body, with256 deterministic displayed-body reverse probes. Strain and adjacent-face angles are descriptors. General triangle intersection/self-intersection classification remains NOT-RUN. Local nearest-face signs do not establish global inside/outside, cloth collision clearance or visual approval. No performance claim follows from runtime durations.

## Actual Studio native and Web selected snapshots

Root alone owns launch, GPU, GUI, ports and servers. Open the normal backendv2 Work first. Native uses its usual `--work` option and `NVWA_ASSET_ROOT`. Create an empty owned absolute capture directory and set command/capture paths before launch:

```sh
NVWA_ASSET_ROOT="$PWD/assets" \
B1_60_COMMAND_FILE="$PWD/.work/b1-continuous/probe-command.json" \
B1_60_CAPTURE_DIR="$PWD/.work/b1-continuous/NEW-native-selected" \
  experiments/60-b1-continuous-motion/target/debug/studio \
  --work "$PWD/ROOT-OWNED-MOTION-WORK.nvwa.json"
python3 -B experiments/60-b1-continuous-motion/selected_commands.py
```

Write one printed command at a time to the command file, atomically if practical. Wait for the corresponding `<request_id>.json` before sending the next. Files use create_new and never overwrite prior evidence. Commands are read only when bytes change; request IDs must be unique. `sample` uses actual shared SetParameters/SetTimeline and Playback seek, selects a finite4s entry, pauses and captures only after a consistent production snapshot matches exact recipe/clip/source time. It can change the active Work through those ordinary commands, so open a task-owned Work. No auto-creation or replacement of another human Work occurs. `play`, `pause` and `snapshot` actions support live checks and arbitrary current-frame captures. The native controller atomically writes compact `probe-status.json` in that same owned capture directory when status changes. It includes pending/captured/rejected/timeout/capture-error with the exact request. The temporary status file is created exclusively, synced, and renamed; snapshot files themselves remain create_new. Status-write errors also go to stderr. Both native/Web sample matching and the independent checker require the exact `probe-entry` timeline ID, not only clip/time.

For Wasm, root builds the library with the already installed target and pinned wasm-bindgen0.2.129, then serves this directory's index.html plus generated `pkg/`, the exact production assets and root-owned Work on root's assigned loopback port. No server is started here:

```sh
CARGO_NET_OFFLINE=true CARGO_BUILD_JOBS=1 cargo build --offline --locked \
  --manifest-path experiments/60-b1-continuous-motion/Cargo.toml \
  --target wasm32-unknown-unknown --lib
# Root runs its existing pinned wasm-bindgen tool on target/.../b1_continuous_probe.wasm.
# --target web --out-dir ROOT_OWNED_SITE/pkg; retain exact output hashes.
```

Open root's site with normal `?work=...`/`?player=1` launch options. Root can use the visible **Test-only B1 diagnostics** disclosure when its browser adapter supports real DOM events but no page-JavaScript mutation calls. This overlay belongs only to the experiment bootstrap; the exact production Studio canvas and compiled Rust/Wasm remain unchanged. It never creates or opens a Work automatically.

Root creates an empty owned capture directory, selects an unused assigned Nvwa probe port and launches the stdlib companion (no launch was performed by this worker):

```sh
python3 -B experiments/60-b1-continuous-motion/serve.py \
  --site "$PWD/.work/b1-continuous/ROOT-EXPORTED-PROBE-SITE" \
  --captures "$PWD/.work/b1-continuous/NEW-web-selected" --port ROOT_ASSIGNED_PORT
```

The server binds only127.0.0.1 and fails on an occupied exact port. The root-owned site must contain index.html, generated pkg/, authenticated assets and the task Work. Both paths must be existing owned directories. Use `http://127.0.0.1:PORT`, not a localhost alias. Static paths are confined to that resolved site; traversal, dotfiles, outside symlinks and directory listings are rejected. Existing cached responses are bypassed. POST `/__b1_capture/ID` additionally requires exact Host and Origin for that same loopback site, JSON Content-Type, one explicit Content-Length<=64MiB, no chunked transfer, finite duplicate-free JSON, a safe1..64character ID, matching record.request.request_id, the actual motion-profile/53-bone/two-part envelope and exact sample request/time/shape binding. It creates capture files exclusively, never overwrites them and stops at32JSON captures. These handler checks validate storage/request identity; the full independent checker still owns FK/LBS/foot/geometry acceptance.

Use real DOM fill/click actions:

1. Expand **Test-only B1 diagnostics**. Fill Request ID, Authored clip, Torso, Jaw and Source seconds. Use a unique safe ID for every capture. **Sample exact frame** invokes the existing compiled bridge and shared commands; **Play**, **Pause** and **Snapshot current frame** invoke their existing actions.
2. Wait until the visible compact report says captured for that exact Request ID. **Store exact capture** re-reads the bridge report and frame, requires their complete requests to match each other and the current Request ID, and POSTs that actual record to the same-origin companion. A successful visible receipt includes stored=true, filename, byte count and SHA256. Server errors, duplicate IDs, missing/mismatched captures and fetch errors remain visible in the storage report.
3. Collapse the disclosure for fixed-camera viewport captures. The request/report controls do not replace observed normal Studio controls or actual play/pause/seek/shape/save checks.

The bootstrap still exposes the underlying module as window.b1_60 for existing authorized tooling, but DOM operation does not require injected JavaScript, permission changes or browser-download workarounds. A retained last completed frame is not a live-current promise; the Store button validates its exact captured request before publication. Fourteen required samples/platform remain: neutral eachclip t0/1/2/3/4, plus both signedtorso endpoints/jaw0 eachclip t2. `selected_commands.py` prints the exact values without sending them. Root separately binds the new bootstrap hash, generated Wasm/build/served identities, stored-record hashes and actual GUI observations. A successful POST is storage evidence, not proof that the viewport displayed that frame.

```sh
python3 -B experiments/60-b1-continuous-motion/check_selected.py \
  --native "$PWD/.work/b1-continuous/NEW-native-selected" \
  --web "$PWD/.work/b1-continuous/NEW-web-selected" \
  --asset-root "$PWD/assets" --out "$PWD/.work/b1-continuous/NEW-platform-comparison"
```

The selected checker requires both platforms separately, performs independent FK/LBS and foot checks first, then numeric parity. It retains missing/failing samples. An aggregate14-count cannot fill a missing requested recipe/time. It does not replace root's fixed-camera visual evidence. Exact screenshots/video and observed folds/poke-through remain separate quality findings.

## Cheap local checks and controls

```sh
python3 -B experiments/60-b1-continuous-motion/test_controls.py
python3 -B -O experiments/60-b1-continuous-motion/test_controls.py
python3 -B experiments/60-b1-continuous-motion/test_serve.py
python3 -B -O experiments/60-b1-continuous-motion/test_serve.py
rustfmt --check --edition 2024 experiments/60-b1-continuous-motion/src/lib.rs \
  experiments/60-b1-continuous-motion/src/bin/matrix.rs \
  experiments/60-b1-continuous-motion/src/bin/studio.rs
```

Known58 shoulder/waist poke-through and combined folded captures remain historical quality HOLD controls (`experiments/58-b1-desktop-web/evidence/STATUS.md`, private root-native10-graphics records). This implementation provides independent known planar/fold geometry controls; it has not executed its new descriptors on those historical captures. Do not imply the15 unit controls verified the appearance of the actual sportsuit. Missing runtime/source-mutation/visual evidence remains NOT-RUN until root produces its distinct receipts.

Browser adapter verification:9 socket-free parser/handler controls pass normally and under `-O`, covering exact origin/host, ID/request binding, finite/duplicate JSON, body/count caps, no overwrite, source-time/shape binding and static path confinement. They start no server and execute no browser. Live DOM/bootstrap/fetch/server operation remains NOT-RUN by this worker. Rust/Cargo/lock and FK/LBS/contact math were not changed for this route enabler.
