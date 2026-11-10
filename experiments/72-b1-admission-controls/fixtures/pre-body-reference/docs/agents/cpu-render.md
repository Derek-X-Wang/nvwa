# Export a CPU silhouette without a browser

Build the optional renderer with the pinned toolchain and prepared locked cache:

```sh
cargo build --offline --locked -p nvwa-cli --features cpu-render
```

The default CLI remains a lightweight document editor. Without this feature,
`render` returns `feature_unavailable`. The optional build links the existing
Bevy/Humentity dependencies (including a Linux window backend required by the
shared dependency graph), but the exporter never initializes a window,
RenderPlugin, wgpu adapter, browser, or display server. Compilation is separate
from actual CPU export acceptance. It is not a PBR software renderer.

The first supported scope is the **eight-parameter `new-character` profile**, an
empty timeline, any saved supported diagnostic pose, and `appearance: none`.
The explicit static `new-character-waist` profile is also supported; see
[its limits](waist-profile.md). Other profiles remain rejected.
Select a static pose with normal CLI `apply` / `set_diagnostic_pose`; that command
clears the timeline. Use `describe-capabilities` to read the loaded Work's IDs,
revision, parameters and `cpu_render.current_work_supported`. Nonempty timelines,
other profiles and selected skin/eyes/hair reject; they are never silently omitted.

```sh
nvwa-cli render /absolute/front.nvwa.json \
  --assets /absolute/assets --output /absolute/new-front-capture \
  --width 1280 --height 720 --mode silhouette
```

Width and height each range from 64 to 2048; defaults are 1280×720. Output must
be a **new directory with an existing parent**. It contains:

- `actual.png`: actual CPU triangle rasterization of the production visible
  body **and sportsuit**, with dark foreground on white, pixel-center sampling
  and no antialiasing.
- `work.nvwa.json`: exact input bytes, never a rewritten or modified Work.
- `receipt.json`: the completion marker, including Work and asset hashes,
  executable identity, saved camera and effective matrices, geometry and image
  hashes, dimensions, diagnostic pose and explicit exclusions.

The renderer authenticates an immutable, bounded snapshot of the normal asset
root, runs the same B1 fitting, rig, full-positive skinning, garment visibility
and stage placement, then reads its validated published meshes. It does not
consume experimental meshes/oracles or reconstruct morphs in a second code path.
The camera uses the saved **perspective** stage view, character scale and
near/far rules. It does not auto-fit each shape. Create separate front/side Work
copies with ordinary `set_stage`, copying the whole stage and changing only its
camera. Orthographic projection is not supported by this command.

Lighting, floor, materials, textures, hair, eyes and animation are not rendered.
This mode deliberately produces a reference silhouette, not an image of all
saved stage settings. Omitting the garment alone would expose holes in the
production visible-body topology; a complete body-only mode is not provided.
A camera containing no character pixels fails rather than returning a blank
success. Clipped framing is otherwise preserved and requires visual inspection.

A successful response has `status: rendered` and exit 0. Validation, unsupported
input and rendering failures happen before creating output. Filesystem failures
may retain a partial directory; only a complete receipt denotes success. Existing
directories are never overwritten. As with other CLI mutations, stdout delivery
can fail after the output was saved: inspect the receipt before retrying.

The receipt's render time includes runtime preparation and rasterization, not
file snapshotting, PNG encoding or executable hashing. Same-build repeated
outputs can be compared by pixels/PNG hash; cross-platform determinism and PBR
pixel parity are not promised. Inspect actual images before deciding whether
parameter tiers, garment contours or framing are useful. This export does not
release existing clothing, motion or appearance quality HOLDs.

Scoped checks:

```sh
cargo test --offline --locked -p nvwa-cli --features cpu-render
cargo test --offline --locked -p nvwa-runtime --features cpu-render cpu_render
cargo test --offline --locked -p nvwa-runtime --features cpu-render snapshot_
cargo test --offline --locked -p nvwa-runtime --features cpu-render stage::tests
```

The real CLI tests remove DISPLAY/WAYLAND_DISPLAY and use actual admitted assets;
they check saved cameras, shape/pose changes, repeatability, no-overwrite and
failure boundaries. Keep existing core/CLI/runtime and Wasm checks. These scoped
checks are not the complete portable/release CI matrix.
