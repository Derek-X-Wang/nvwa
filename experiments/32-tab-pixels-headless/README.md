# Throwaway headless tab raster experiment (#40)

VERIFIED — one root-approved actual Metal/Image-target GPU run completed in
7.300 seconds and the unchanged literal checker returned 0/0/1. Both normal
images passed exactly; the held-Profile paint mutant was rejected. Images were
independently inspected, owned target/guard exited, and GPU lease returned.
See REPORT.md and RUNTIME-RESULT.json; build/control provenance is preserved.

Question: can unchanged production `EditorLayout::draw_tabs` produce actual GPU
Image-target PNGs that an independent literal reference accepts for Shape and
Profile, then rejects after a paint-only wrong-color mutation while Profile
selection stays held?

This is baseline045d8ab code in a standalone workspace. The extracted1393-byte
`draw_tabs` method is exactly byte-equal to the current root candidate method,
SHA256`8f68b6617dbbf8bba64c389c320ea48e62dbf33c60f9e7db1e34c7ecf1abad5b`.
It includes the unchanged production module directly. It does not render a
character or test the later full application. Original fixture/Work identities
are references in SOURCE-MANIFEST.json; they are not loaded for this UI-only case.

Installed primary source supports the proposed path: Bevy0.19.1 headless renderer
example uses `WindowPlugin { primary_window: None, exit_condition: DontExit }`,
disables `WinitPlugin`, and runs with `ScheduleRunnerPlugin`. Its externally
driven example uses `Screenshot::image`; installed screenshot code has a real
Image-target renderer/readback path. Bevy Image constructor supports
`Rgba8UnormSrgb`, MAIN_WORLD+RENDER_WORLD and RENDER_ATTACHMENT. bevy_egui0.42
has explicit PrimaryEguiContext on an Image-target camera and derives its screen
size from the camera. Exact local paths, line ranges and file hashes are retained.

The experiment uses one Camera2d and 1280 × 720 SRGB Image target, no native Window
entity, explicit Egui context, scale1, Dark theme, raw input time1, no pointer
and the unchanged experiment31 palette. Thirty scheduled frames settle each
case before one real Bevy screenshot request. Sequential cases are normalShape,
normalProfile and mutantProfile. The mutation changes only active fill to
RGB(199,13,151); selection stays Profile. No software raster, mock pixels,
custom output conversion, pixel recoloring or derived expectation is used.
Bevy's unchanged save_to_disk helper saves actual readback as RGB8, dropping
alpha exactly as the original experiment31 path does.

Run the existing unmodified experiment31 `verify_pixels.py` against actual PNGs,
expecting exit 0 for normal-shape/normal-profile and exit1 for mutant-profile
against normal-profile. Its literal colors, ROIs and tolerance2 remain fixed.
Also inspect images independently, verify actual case markers/selection,
adapter/backend/device type, dimensions and native_window_count0. A CPU adapter
is rejected; missing identity/capture or unsupported renderer fails. Actual
offscreen hardware rendering passed; native lock state at its callback was not
queried and is not inferred from this result.

Package identities/checksums 524 and all 521 external resolved feature sets match
the current root graph exactly. Own Cargo.lock is offline-generated. Root and
baseline lock hashes remain unchanged. See PARITY.json and private metadata logs.

## Reproduction (new run requires a fresh root lease)

One sole-writer compile cycle, initially>32GiB free and abort<8GiB, max15minutes,
offline/locked/release/jobs1 against existing shared target:

```sh
CARGO_TARGET_DIR=/Users/derekxwang/Development/incubator/Nvwa/nvwa/target \
  cargo build --offline --locked --release --jobs 1 \
  --manifest-path experiments/32-tab-pixels-headless/Cargo.toml
```

After success, copy the exact binary into private
`.work/m11-startup/headless32/frozen/nvwa-tab-pixels-headless-experiment`, record
SHA256/bytes/source graph and have root approve its final freeze. No compile
may overlap the later exclusive GPU run.

One owned renderer process, one run, three sequential captures, no GUI/server.
Root creates an empty private evidence directory and sets freeze approval/GPU
booleans. `run_owned.py` pins the unchanged reviewed experiment30 guard helpers
bySHA, rehashes source/binary inputs before Popen, captures exact PID/kernel birth
and binary identity, and guarantees final receipt/owned-child cleanup. It has
an external50-second deadline, with up to two2-second exact-identity TERM/KILL
grace periods, bounded0.3-second inspections and direct Popen waitpid exit proof.
Identity-unknown cleanup is blocked/no arbitrary signal; record it and report to
root immediately. The scheduled Rust30-second timeout is additional protection,
not the only guard against pre-schedule renderer stalls. No profiler is spawned.

```sh
python3 -B experiments/32-tab-pixels-headless/run_owned.py \
  --freeze .work/m11-startup/headless32/freeze.json \
  --evidence .work/m11-startup/headless32/run-1
```

Installed API compilation and actual GPU/SRGB/readback controls passed. These
commands document the already completed run; do not reuse old output or rerun
without new authorization. This scoped result cannot establish
native-window or character startup, physical presentation, GPU performance,
IME/browser acceptance or permanent CI adoption. Experiment30/31 frozen
sources/locks/guards and old failed captures remain unchanged.

The copied initial compile guard inherited an I/O exception cleanup gap. Root's
actual post-Popen storage-failure control reproduced a surviving dummy process,
then reaped it. Attempt1 completed naturally before any repair; its exact guard,
proposal and manifest are preserved. Only experiment32 was repaired to guarantee
mandatory finally cleanup across storage/log/receipt I/O, KeyboardInterrupt and
signal cancellation. Ten controls cover normal exit, matching I/O fault, real
started/log/final-receipt failures, timeout, TERM-to-KILL, interruption, actual
SIGTERM cancellation and unknown inspection. Unknown remains blocked, never
false exit proof. Both actual Cargo groups are confirmed absent by kernel ESRCH.
