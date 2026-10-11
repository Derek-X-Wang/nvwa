# Native startup viewport harness

This throwaway executable requests a 1024 × 768 logical-pixel startup viewport for native validation. It is not the packaged app. It calls the public production `nvwa_studio::build_app()`, sets only the single `PrimaryWindow` resolution, and calls `app.run()`. All plugins, assets, commands, Work loading, and editor UI come from production. It does not parse or rewrite process arguments, so `--work` reaches the original production argument parser.

The helper has its own workspace and lockfile. Its direct Bevy dependency is exactly `0.19.1`, with default features disabled. Studio supplies the enabled features. Resolver and release settings match the root workspace: resolver 3, optimization level 3, thin LTO, and eight codegen units.

From the repository root, build without changing the production lockfile:

```sh
CARGO_BUILD_JOBS=3 CARGO_TARGET_DIR="$PWD/target" \
  cargo build --release --locked --offline \
  --manifest-path experiments/18-native-viewport-harness/Cargo.toml
```

For the authorized native validation owner, launch with an absolute path to the intended Work file:

```sh
target/release/nvwa-native-viewport-harness --work /absolute/path/to/scene.nvwa.json
```

No asset-root override is needed while this source checkout and its `assets/` directory remain available. Production embeds its own crate's asset fallback at compile time. If the executable is moved away from that checkout, set `NVWA_ASSET_ROOT` to the absolute production `assets/` directory; this is the existing production mechanism.

Bevy's `WindowPlugin::build` inserts the primary window component synchronously. The helper fails loudly unless exactly one `PrimaryWindow` exists after `build_app()`. `WindowResolution::set` requests logical dimensions. Winit's event-loop object is constructed during `build_app()`, but native-window creation occurs in the runner after the helper changes the component. This helper cannot guarantee the operating system's eventual client size, scaling, or available display area. Confirm those in the actual native session.

The isolated lock was seeded from the frozen production lock, then resolved using offline Cargo metadata. For `aarch64-apple-darwin`, all 389 packages in the Studio dependency graph retain the same identities and enabled features. The lock adds only this path helper and removes the unused workspace CLI; it introduces no registry or Git packages. Bevy is `0.19.1`, bevy_egui is `0.42.0`, egui is `0.36.2`, and craft-ui is pinned to `5c874d51eeb3de70e735c8ce87a59a7dedd47675`.

Build logs, dependency comparison, binary identity, and the 31 frozen-input checks are retained under `.work/ui26/native-viewport-harness/`. The implementation worker did not launch the app. Root subsequently ran the actual GUI and geometry observer; see [REPORT.md](REPORT.md) for results, exact copied evidence and the distinction from packaged-binary geometry.
