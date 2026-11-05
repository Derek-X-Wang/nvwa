# See a Work before revising it

Use the preview adapter to inspect an actual B1 character at a chosen timeline
time. It uses the saved Work camera and the existing Web renderer. Change a
camera through ordinary CLI `set_stage` when the creative task calls for another
view. The preview adapter does not edit the Work or generate motion.

## Prepare once

Build the adapter from the repository root with the existing pinned toolchain
and locked dependencies:

```sh
bash scripts/build-preview-web.sh dist/preview
```

This is an offline build. If dependencies or wasm-bindgen 0.2.129 are missing,
stop and report the prerequisite. `NVWA_WASM_BINDGEN` can select an existing
executable. The output directory must be new. Compilation is separate from
actual rendering; the build receipt identifies sources and generated files.

## Request and inspect a preview

```sh
python3 -B scripts/preview.py \
  --work /absolute/path/character.nvwa.json --seconds 2 \
  --output /absolute/path/new-preview-directory \
  --preview-root dist/preview --assets assets \
  --cli /absolute/path/nvwa-cli
```

1. Keep this command running. Read the `open_browser` JSON event on stderr.
2. Open its exact localhost URL with your browser tool. A browser with WebGPU
   must be available; the command does not launch or automate a browser for you.
3. Wait for the command's terminal result. Exit 0 and `status: rendered` mean
   the Work/camera/time checks and PNG transfer completed. Open `actual.png`
   with your image tool and judge the actual character, pose and framing.
4. Use the normal CLI to revise the Work into a new file. Preview that exact
   new file at the same time and compare. Preserve the earlier Work and image.

The default loopback port is 9208, in Nvwa's assigned range. A busy port fails;
choose another available assigned port with `--port`. The URL serves one
snapshot for at most 90 seconds by default, then the server exits. Close the
task's browser tab after capture. Preview directories are retained results,
not disposable compiler caches.

## Interpret the result

The output preserves the exact input Work, its SHA-256, selected time and saved
camera, the renderer's observed state, a PNG hash and the compiled Wasm identity.
Requests retain their original numeric values and also record `effective_camera`
and `effective_seconds` in the existing Rust API's single precision (`f32`).
The receiver compares the reported effective values exactly. This distinguishes
short saved decimals such as `3.8` from their equivalent promoted `f32` JSON
representation without accepting a different adjacent `f32` value.
The character must finish loading before a paused seek. A render screenshot
callback precedes capture of the held Web canvas. The PNG is that later canvas
frame, not the screenshot callback's own image. No old capture is substituted.

Errors, timeouts, wrong identity/time/camera, corrupt PNGs and wrong dimensions
fail explicitly. A failed result is not visual evidence. The current preview
scope is B1; an empty/static timeline supports time zero. Requested time must
be within the Work timeline. Runtime sampling must reach the requested time;
it cannot silently clamp a request and call it successful.

Data validation proves neither appearance quality nor smooth transitions. Image
inspection must say what is visible and what remains uncertain. A successful
preview does not clear M2, clothing or full appearance HOLDs, prove performance,
or replace normal Web Open/Save and CLI exchange acceptance.

## Inspect several times without opening a browser by hand

`scripts/review-motion.py` wraps the same single-frame preview above. Its supported
path is Python 3.12+ on macOS with an explicitly selected, already installed Chrome
executable and WebGPU. It starts a fresh headless Chrome process and private profile
for each frame. It uses Chrome's normal GPU configuration; it does not install a
browser, select a software renderer, or use an existing browser session. This is
one supported path, not a promise about every browser or host.

Prepare one or two review-camera Work copies with ordinary CLI `apply` and
`set_stage`. Discover current fields with `describe-capabilities`. Each command
must use the source Work's current `expected_revision`. Copy its entire stage,
then change only `stage.camera`, because `set_stage` replaces the entire stage.
Save each result to a separate file. Keep the original Work. The wrapper validates
that original with the existing CLI, then refuses any view that differs from it
outside `revision` and `stage.camera`. Each view is also validated by the unchanged
single-frame preview when captured. Review-camera copies are separate Works with
their own hashes; they do not change the original camera.

```sh
python3.12 -B scripts/review-motion.py \
  --chrome '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  --work /absolute/path/rehearsal.nvwa.json \
  --view front=/absolute/path/front-review.nvwa.json \
  --view side=/absolute/path/side-review.nvwa.json \
  --seconds 0 --seconds 3.9 --seconds 4 --seconds 4.1 --seconds 12 \
  --output /absolute/path/new-motion-review \
  --preview-root dist/preview --assets assets \
  --cli /absolute/path/nvwa-cli
```

Choose times from the actual Work. In particular, include ordered samples before
and after a transition you want to inspect. The example times are command syntax,
not an assertion about any Work's timeline. The wrapper preserves the supplied
view order, then the supplied time order within each view. One view is permitted;
use two repeatable views for a motion review. At most 24 frames are allowed. The
default per-frame deadline is 90 seconds; `--timeout` accepts 1 through 90. The
default total deadline is 600 seconds; `--total-timeout` accepts a positive finite
value up to 600. The normal default port remains 9208; a busy port fails explicitly.
Capture time depends on loading and rendering, so the frame cap does not guarantee
that every request will complete within the total deadline.

The command prints one terminal JSON result. Exit 0 and `status: rendered` mean
every requested frame completed with the existing Work/time/camera and canvas
transfer checks. Read `receipt.json`, then inspect each frame's `capture/actual.png`
with your image tool. The receipt records the base hash, unchanged input snapshots,
each view hash and revision, requested times, actual single-frame receipts, image
hashes, commands, and owned process cleanup. Runtime receipts retain the effective
single-precision sample times described above. The PNG is still the real Web
canvas captured by `preview.html`; this wrapper does not take replacement images.

A failure returns exit 1 and a failed batch receipt. Completed images and child
logs remain available, but they do not mean that the whole request passed. The
wrapper stops at the first failed frame. It stops only process groups it created,
using bounded TERM then KILL waits, and removes a frame's private Chrome profile
only after that Chrome process group is absent. SIGINT and SIGTERM follow this
cleanup path. Cancellation received during cleanup is recorded and reported after
all owned groups and profiles finish their bounded cleanup. Each group has a
two-second TERM grace and a two-second KILL grace; cleanup can extend the capture
deadline by those bounds. `cleanup.jsonl` and `base-cleanup.jsonl` record the exact
group, signal or probe, phase, error number, elapsed time and direct-child exit
state. Permission denial is unknown absence. The wrapper can observe an eventual
`ESRCH` (no such process group) within the existing grace, but persistent denial
fails the review and retains the profile. A denied signal is logged as undelivered.
A hard process kill cannot run cleanup. No existing output directory is overwritten;
if it already exists, the failure is printed without changing it.

For a revision, save a new original Work and new camera copies with the same two
camera settings. Repeat the same time list into a new output directory. The command
opens and closes its own browser processes for both inspection and reinspection.
Keep both result sets and compare the normal images. Local receipts and process
logs contain absolute paths; select and redact the intended Works, commands and
images before publishing evidence. Multiple still frames support observations at
those times. They do not establish smooth playback across the whole timeline.
