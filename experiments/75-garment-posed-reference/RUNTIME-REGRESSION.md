# Ordinary desktop/Web regression — 2026-10-19

**VERIFIED within the scope below.** This ordinary application check is separate
from the original-tool numerical comparison. It does not admit a garment fix.

## Build identity

Both fresh builds use the unchanged product source at
`69176c5dafe2b801c44f80fbb2aec0139cbb7500`. The branch changes only experiments
and documentation. The build helpers checked their complete product-source
closures before and after compilation: 234 files for native, 250 for Web.
Each build used its own exclusive Wefty target, one Cargo job, locked/offline
dependencies and development debug info disabled. No existing export was reused.

| Endpoint | Actual build | Produced payload SHA-256 |
| --- | --- | --- |
| macOS native | `cargo build --locked --offline -j 1 -p nvwa-studio --bin nvwa-studio` | `c8bfa000c3cb21a6912ae4ca58b850f4225d2d8ffdd0aa047ea5be2aa2c91496` |
| Web | `bash scripts/build-web.sh dev` | `d846c824da368990b440a5bcd694ade2c93d2a4059890c5c75124cb624af6f66` |

The native test bundle changes its local display name and bundle ID only; its
executable/resources are the fresh product payload. It is unsigned local test
packaging, not a signed release. Build durations are not startup measurements.

## Actual flow

The Work uses the shipped **old two-parameter B1 profile**, torso length +1,
appearance v1 with skin/eyes/hair enabled, and an authored four-second arm clip
followed by a four-second knee clip. This is not AI-generated motion, an
eight-parameter cohort, or a newly sampled full skeleton matrix.

1. The existing independently delivered CLI package created the initial revision3
   file. Its executable and all 94 listed payloads were rehashed. This is reuse of
   that existing CLI, not a claim that this round rebuilt the CLI.
2. Native Studio opened revision3, rendered the character and played the clips.
   Editing the jaw control, Undo and Redo produced revision6 with `jaw_drop=0.7`.
   Actual Save showed the green lower-right success notice; Open retained the edit.
   The old profile serializes this UI control as `jaw_drop`.
3. Web Studio opened those exact saved bytes. Restart produced moving arm frames;
   the eight-second end state was also observed. A held slider drag, Undo and
   Redo produced revision9 with `jaw_drop=0.25`.
4. Web Save produced one actual download. A structural comparison found only the
   intended revision and jaw changes; timeline, stage, profile and appearance
   remained intact. The existing CLI validated both saved Works with asset checks.
5. Web's actual Open file chooser reopened its downloaded revision9. Native then
   opened that same file and saved it, with a visible success notice. The entire
   file remained byte-identical:
   `e7a78d07b577bc39619da8a23be4f579878f38279bc9507db2232ff866aea43e`.

Full local screenshots, build receipts, source ledgers, Work snapshots and
`ROUNDTRIP.json` are retained in the task's private evidence archive. Screenshots
contain local file paths and are not copied into this public report. The task
download was moved into that archive; the owned server and native app were stopped.

## Reproduce the user flow

Build native and Web with the commands above. Use the shipped
`examples/b1-appearance.nvwa.json`, set `torso_length=1` through the shared CLI or
editor command, and select the existing arm/knee authored clips. Use a new Work
path. In native Studio, Open, play, edit the jaw control, Undo, Redo, Save and Open.
Serve the fresh Web export, open the saved Work, repeat edit/Undo/Redo, Save to
download, then Open that download in Web and native. Compare the downloaded bytes
with native's re-save. No model or additional download is needed.

## Limits and failed attempts

Native modifier-key/paste automation initially failed to replace the Work path;
two actual Open errors are retained. Direct text keys and Tab/Return completed
the same ordinary controls. One ScreenCaptureKit stream error and one
`noWindowsAvailable` after relaunch cleared after refreshing and raising the
owned window. A Web track click initially made no edit; the actual held drag did.
These attempts are not product diagnoses or successful edits.

Native screenshots sometimes included an oversized white capture area. No
physical window size, DPI or IME conclusion follows. Web's save notice was not
captured before it expired; the actual download and bytes are the evidence.

**NOT-RUN:** new original-tool rendered pixels, fresh same-frame 53-bone clothing
readback in these ordinary apps, long-duration playback, full character/garment/
eyelid/hairline quality, physical IME/DPI, startup/GPU/memory performance, signing
and clean-machine release. Issue3 remains blocked; issue4 retains its gaps.
