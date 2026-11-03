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
