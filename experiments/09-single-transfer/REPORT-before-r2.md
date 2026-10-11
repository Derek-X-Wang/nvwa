# Single GLB retrieval boundary (issue #6)

Base: `44b0ec3b129a1e19f5c8c3598f88de1e50e4e826`. The patch is uncommitted.
The published fixture, profile, document schema, dependency versions, Cargo.lock,
root manifest, Studio and core are unchanged.

## Adopted boundary

The runtime requests one typed `CharacterGlb` root. Its loader retrieves the
asset bytes once, moves them into Bevy's `VecReader`, and delegates the registered
Bevy 0.19.1 GLTF loader with
`LoadContext::load_builder().load_value_from_reader::<Gltf>`. The result remains a
`LoadedAsset<Gltf>` when installed as `NvwaGltf`, so Bevy retains the nested scene,
mesh, skin, morph, material and animation assets and their dependency tree. The
root keeps the same `VecReader.bytes` for the current document's core validation.

The loader does not apply a character profile or change GLTF defaults. The
runtime still validates the current profile's full frozen hash and structural
constraints before spawning `CharacterRoot` or declaring Ready. Bevy parsing
can precede hash validation, as in the original runtime. A GLTF asset's internal
presence is not authorization to expose its scene. This is not a promise of
validation before parsing or an arbitrary-model compatibility change.

A delegated parse error is retained with the retrieved bytes. Core missing,
hash and container errors retain priority. If those pass, the parse error is
visible as `Character load failed`. Reader errors still fail the typed root and
are visible as `Asset byte load failed`. No parse/reader errors are discarded.

Each explicit work open resets verification and drains earlier completions
before requesting a fresh root completion. Profile checks remain independent
of Bevy's path cache and loader settings. A cached successful root gets a forced
reload. Bevy's `load` already retries a failed root, so the runtime does not also
force that retry. A new path is not forced a second time. A current reader
failure revokes verification; cached scene/dependency success cannot clear it.

## Pinned owning-source evidence

Inspected the installed Cargo registry sources for `bevy_asset-0.19.1` and
`bevy_gltf-0.19.1` (not recollection of older Bevy APIs):

- `bevy_gltf/src/loader/mod.rs:1162–1181`: the normal loader reads the provided
  reader and calls `GltfLoader::load_gltf` with those bytes.
- `bevy_asset/src/loader_builders.rs:176–187, 279–300`: reader delegation chooses
  the registered loader by asset type and uses the supplied reader without
  opening another source reader. GLTF default loader metadata is used.
- `bevy_asset/src/loader.rs:488–522, 670–676`: public nested-load builder and
  installation preserve the `LoadedAsset` tree.
- `bevy_asset/src/server/info.rs:397–429`: recursively installs all labeled
  assets before the parent.
- `bevy_asset/src/server/info.rs:224–249`: failed typed roots retry via `load`;
  live handles retain their existing loader settings.
- `bevy_asset/src/server/mod.rs:952–1006`: forced reload tries typed roots, then
  an untyped fallback after failure while the path/labeled assets remain live.

## Regression evidence

Seven new CPU tests run the production `load_character` system, the registered
pinned Bevy GLTF loader, scene spawning and readiness evidence. They use a counted
in-memory asset source; this counts source-reader calls, not HTTP traffic or GPU
rendering.

- Cold valid fixture: one read. The source is replaced immediately after the
  read, while the retrieved snapshot stays valid. Hash validation and the real
  scene/skin/four morph channels/three authored animations still succeed. A
  second source read would instead receive corrupt replacement bytes.
- Correct profile → wrong hash → correct profile at the same path: three
  reads for three explicit opens. The wrong profile never spawns or becomes
  Ready. Neither cached bytes nor initial loader settings bypass the new check.
- Corrupt, empty and missing → valid at the same path: one initial attempt and
  one successful recovery read for each case; the specific core/reader errors
  remain visible until recovery.
- Ready → corrupt replacement → restored fixture: one read per explicit open,
  with no scene exposed for the bad generation.
- A hash-matching container with an invalid GLTF mesh reference: core validation
  passes, actual Bevy parse failure is visible, and a correct-profile/fixture
  reopen recovers.
- Switching to a new asset path: one read for the new path.
- Async reader failure after Ready: verification is revoked and cached scene
  success cannot clear the error. Explicit recovery retrieves the GLB once.

The existing 21 runtime tests also run, including real animation graph/morph,
interaction, document generation and asynchronous byte-verification tests.

## Rejected approaches and observed limits

- Separate `GlbBytes` and `Gltf` source loads: they retrieve separate snapshots;
  HTTP caching does not prove one transfer or identical bytes.
- Profile injection into loader settings: live same-path handles preserve their
  initial settings. This risks wrong-profile → correct-profile recovery. The
  adopted loader has unit settings and retains system-level current validation.
- Reconstructing or replacing `GltfLoader`: would duplicate its plugin defaults,
  extension handlers, image support and future lifecycle assumptions.
- A cached/memory asset-source adapter: requires broader pre-`AssetPlugin`
  source-registration and invalidation changes. The public nested reader API is
  narrower.
- Taking only the nested GLTF value: would lose labeled subassets/dependency
  metadata. The adopted loader installs the entire `LoadedAsset`.
- Upgrades or a copied GLTF loader: not required and not authorized.

Pinned Bevy's forced-reload failure fallback remains. After a Ready scene's
source disappears, a forced reload makes two failing reader calls (typed then
untyped); both return NotFound and transfer no GLB. This is preserved in a test,
not claimed as one HTTP request. Successful cold loads, successful explicit
reloads and successful recovery retrieve one GLB. Formal browser/network
measurement must distinguish failing requests, metadata probes and payload
transfers. The orchestrator owns that measurement.

Reader delegation uses registered GLTF defaults and the same asset path for
relative labels. The fixture has no `.meta` file or external resources. Core
still rejects external GLTF resource references before scene exposure, but Bevy
can process such references before that check, as it could previously. This
patch does not add an untrusted-asset/network sandbox or adopt different GLTF
settings, supported profiles, asset-processing mode or watch behavior.

## Execution and artifact identity

Local macOS arm64, Rust/Cargo 1.95.0; no window, browser, GPU, release build,
Wasm build, upload, commit, push or PR was performed. A task-specific target
`target-single-transfer` was clone-copied from the primary checkout's existing
`target/debug` to seed dependency artifacts; all writes then stayed isolated.
After completion, the exclusively owned target was moved into the ignored
`target/single-glb-transfer` directory for retention. Log paths show its original
execution location. Cloned pre-patch runtime rlibs are not evidence for the new
patch. No new linked runtime `.rlib` was emitted by these test/clippy commands;
downstream Studio must build/link the patched runtime itself.

The test executable is
`target-single-transfer/debug/deps/nvwa_runtime-74980f9e59502172`, Mach-O arm64.
The retained executable is now under
`target/single-glb-transfer/debug/deps/` with the same basename and bytes.
Its verified SHA-256 after the final 28-test code change was
`186968b0362646c8070ad52b40bc963160f8b27b4a6674c29f0fba0d14d3f56d`.
The unchanged fixture is 3,827,840 bytes, SHA-256
`f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6`.

Initial compile exited 101 due to an incorrect API name (`loader` instead of the
pinned API `load_builder`), then was corrected from source. The first full test
run exited 101 (26 pass, one deterministic malformed test-vector padding
failure), preserved in `native-tests-initial-failure.log`. The corrected run
exited 0 (27/27). The added async failure probe then exited 101 on a total-read
expectation (27 pass, one failure), preserved in
`native-tests-failed-reload-observation.log`; owning source explained the two
failed Bevy fallback attempts. The final test explicitly preserves that limit
and asserts one successful recovery retrieval.

Reproduce sequentially with `./experiments/09-single-transfer/reproduce.sh`.
Set `NVWA_SINGLE_TRANSFER_TARGET_DIR` to another isolated target if needed.
`verification.log` records the final test/clippy workload: exit 0, all 28 runtime
tests pass, and clippy completes with `-D warnings`. Formatting and
`git diff --check` also exit 0. Clippy emitted fresh native library metadata
`libnvwa_runtime-e91db866af5cfb84.rmeta` (198,646 bytes, SHA-256
`9a881fbe4176937f3d90569a45a53e1f05e070ad4b6fa718abd64354a57a142a`);
this is metadata, not a linked renderer library. Graphical/native
rendering, Web compilation/execution, formal HTTP measurements and downstream
Studio artifact linkage remain the orchestrator's acceptance work.

## Cleanup ownership

No service, port, watcher, UI session or subprocess was intentionally left
running. The completed test process removes its filesystem fixture; new tests
use in-memory sources. The worker-created target directory and this dirty
worktree are retained for review/integration. The orchestrator owns their
cleanup after preserving the patch and logs. Native compile/test sessions have completed: `8843` exit 101 (API typo),
`23061` exit 101 (test-vector padding), `12071` exit 0 (27 tests), `45122`
exit 101 (failed-reload observation), `17522` exit 0 (28 tests and clippy).
The target-seeding/fmt session `8335` also completed (exit 1: fmt suggested
changes, later applied and verified). There are no live task-owned PIDs or
Cargo sessions to stop.
