# Path B — existing source-data runtime preparation

2026-10-16; Nvwa research base `04cb9c8621c723ae31fb315730c7e8aefbcae608`. Candidate: Humentity `286d33124648501535655a0de811cef55152b9fd`. No candidate checkout, asset, add-on, crate archive or tool was downloaded. No compilation, Blender, graphics or inference task ran. Public repository text and JSON metadata were read. This does not select Humentity or prove a mature character works.

## Delivered boundary

`run.py` is a real offline preflight/build gate, not a replacement character generator. It requires the fixed upstream commit/file inventory and approved per-file SHA-256 digests, the exact approved sample-manifest digest, all listed input-file hashes/provenance, coordinate identity and four common cases. It rejects fixture substitution. Candidate files are not read before the approval and sample checks pass. Candidate source symlinks and input paths escaping the approved sample directory are rejected.

`preflight` verifies immutable source identity and sample presence without Cargo. `check-native` and `check-wasm` require a separately approved derived manifest/lock/patch package, invoke Cargo metadata with `--offline --locked`, and then invoke real `cargo check --offline --locked --lib --jobs 1` in an experiment-local target directory. A four-minute subprocess timeout bounds each operation. They require explicit `offline_build_approved`. Cargo cannot install missing crates through its resolver. Source build scripts are not a general network sandbox: review approved source/build scripts before a future build. This preparation runs none.

All character-case receipts remain `status: not_run`, even when preparation succeeds. Separate booleans record actual candidate execution, native graphics, Web graphics and the common reference. `command_exit_code` records Cargo's result separately from the runner's nonzero blocked exit. `run-cli` is deliberately blocked: no real Humentity adapter exists yet. It cannot run a stand-in binary and claim a human-data result.

The source gate now accepts the bill's exact 45 raw files without `.git`, `Cargo.lock` or assets. `upstream-inventory.json` is copied solely from the pending download-bill metadata: paths, Git-reported sizes and Git blob SHA-1 values at the pinned commit. Its fixed SHA-256 is `3c0d8c4d2aac9c398d3b7eb75272ced08f6babafd6bd4577f895e50f10b661ab`. Approval must pin this exact inventory digest and a local SHA-256 for each file. Caller-supplied SHA-256 alone cannot authorize false upstream bytes: Git blob identity and size must match too. The source gate rejects extra/missing files, extra directories, traversal, symlinks, FIFOs and size mismatches before reading oversized content. There are 561,909 expected source bytes.

Upstream files stay immutable. Future build inputs live in a separate derived package with its own approved tree digest, `Cargo.toml`, fresh `Cargo.lock` and `patch.json` naming the upstream inventory digest. This package is absent today; actual builds and CLI remain NOT-RUN. No source or tiny fake Humentity snapshot was created to get a passing preflight.

Receipt and log files use exclusive creation. Existing results and input aliases, including symlinks and hardlinks, are rejected without truncation. Output paths within the source directory or equal to approval/sample manifests are forbidden. The two logs have separate `.metadata.log` and `.build.log` names. Rejection may produce no receipt when its requested path is unsafe; the runner still returns nonzero and preserves all input bytes.

## Current support matrix

| Route/capability | Source-informed expectation | Verified here | Current blocker / next proof |
|---|---|---|---|
| Native library manifest | Same Bevy major/minor as Nvwa reduces one interface risk | Real local optional-workspace-inheritance control fails Cargo parse, exit 101 | Pinned manifest inherits an undefined Jolt workspace entry; source packaging fix needed before dependency resolution |
| Native dependency graph | One CPU character needs mandatory library deps, not ragdoll/UI example deps | Real minimal mandatory-dependency manifest fails offline resolution on `bevy_obj`, exit 101 | Cached graph incomplete; fresh isolated lock and bounded crate bill still needed |
| Native CPU mesh/rig | Existing loaders, morph evaluator, mesh builder and refit event provide seams | Public source inspected; no candidate code executed | Approved source/data, minimal build and adapter required; no mesh/rig/inverse-bind parity measured |
| Native graphics | Bevy plugin could display the approved character | NOT-RUN | Actual renderer/window, pose and continuous edit proof required |
| Wasm compilation | Installed target and matching Bevy version are prerequisites | `wasm32-unknown-unknown` installed; no candidate compile | Manifest/dependency repair, feature audit and actual Wasm compile |
| Browser target loading | Explicit asset list can replace folder discovery without replacing MH parsing | Humentity `MakeHumanMorphs::new` calls `AssetServer::load_folder`; cached Bevy 0.19.1 HTTP reader returns an empty directory stream and logs unsupported directory access | Confirmed static integration gap. Add explicit target handles and readiness checks; compiling alone would miss empty-target success |
| Browser task scheduling | Pinned mesh source uses `AsyncComputeTaskPool`, not direct `std::thread::spawn` | Public source lines inspected, not browser execution | Polling/channel/task lifetime must be tested on actual browser. README background-thread wording alone does not prove browser failure |
| Browser graphics | CPU character route may be adapted; GPU crowd route unnecessary | NOT-RUN | Actual browser asset loads, nonempty targets, mesh/rig edit, pose, WebGPU support and resource cost |
| CLI numeric evaluation | Public synchronous mesh function exists; windowless Bevy app might initialize required asset/mesh stores | Source inspected only | No candidate CLI adapter. Determine minimal plugins/resources; prove no render/window initialization, finite timeout and actual nonempty outputs |
| A/B reference and Work exchange | Both should use the same recipe, basis, input manifest and case IDs | NOT-RUN | Common MPFB reference unavailable; save exchange/product integration outside preparation |

### Concrete source findings

- [Pinned Cargo manifest](https://github.com/emberlightstudios/Humentity/blob/286d33124648501535655a0de811cef55152b9fd/Cargo.toml): package 0.19.0, Bevy 0.19.1, undefined optional workspace Jolt dependency. Optional does not bypass Cargo's inheritance validation, as the local control proves.
- [Pinned lock](https://github.com/emberlightstudios/Humentity/blob/286d33124648501535655a0de811cef55152b9fd/Cargo.lock): package 0.18.0, Bevy 0.18.0 and `bevy_obj` 0.18.2. It is not a reproducible lock for the current manifest. A successful repair must record a new isolated lock digest. Never modify Nvwa's root lock.
- [Mesh build seam](https://github.com/emberlightstudios/Humentity/blob/286d33124648501535655a0de811cef55152b9fd/src/spawn_mesh.rs#L320): `build_single_mesh_direct` accepts loaded Humentity/Bevy data and returns `Mesh`. It does not itself return the complete fitted skeleton or an inverse-bind receipt. Async paths at lines 391/461 and 501/621 use Bevy's task pool. This contradicts a literal reading of the README thread wording; no direct-thread failure is claimed.
- [Morph loader/readiness](https://github.com/emberlightstudios/Humentity/blob/286d33124648501535655a0de811cef55152b9fd/src/morphs.rs#L72): folder load plus readiness by folder load state. The adapter must additionally prove every requested target exists. An empty folder must not become a successful character.
- [Refit event](https://github.com/emberlightstudios/Humentity/blob/286d33124648501535655a0de811cef55152b9fd/src/helpers.rs#L21) is an existing route to refit after parameter changes. [Core loader](https://github.com/emberlightstudios/Humentity/blob/286d33124648501535655a0de811cef55152b9fd/src/lib.rs#L108) takes base mesh, vertex groups, composite target metadata, macro metadata, targets, rig and weights. These candidate-specific schemas are not assumed interchangeable with raw MPFB files.
- Browser reader evidence is installed source `~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/bevy_asset-0.19.1/src/io/wasm.rs:132-144`. It logs unsupported directory reading and returns `EmptyPathStream` / `false`. Corresponding [upstream source](https://github.com/bevyengine/bevy/blob/v0.19.1/crates/bevy_asset/src/io/wasm.rs).

## Adapter and source patch proposal — not implemented

1. Preserve the approved upstream source snapshot and file inventory. Create a separate source copy/manifest under this experiment; record both upstream and patched content hashes. The runner accepts only immutable upstream inventory bytes; record and approve any patch in the separate derived package.
2. In the isolated copy only, remove the three optional physics dependencies, their physics feature activations and corresponding physics-only example declarations. Remove dev dependencies/examples from the probe manifest. Use only the mandatory library graph. Keep physics modules gated off; a probe must reject all physics features rather than expose an empty feature as supported physics. No crowd plugin is added. First keep Bevy's declared features unchanged to separate packaging repair from runtime feature reduction.
3. Generate a fresh lock with offline resolution only. Missing crates become an exact follow-up bill. The current evidence identifies the first missing crate, not the full graph. After the graph is complete, use `--locked --offline`; check native before Web. Do not move the candidate into the root workspace.
4. For explicit file loading, add `MakeHumanMorphs::from_target_paths` (name is a proposal), retain typed `Handle<TargetAsset>` values, load only approved paths, and require every handle loaded plus required target names present. Preserve existing macro/composite/target parsers. Report errors with the failed path rather than waiting forever or accepting an empty set. Existing folder loading can remain a native convenience outside the experiment.
5. Build a windowless adapter around actual candidate APIs: initialize only required Bevy asset/mesh/image/transform/scene/animation resources, load exact sample paths, evaluate named recipes with `compute_target_weights`, build meshes through the existing direct builder or task-pool path, then use existing skeleton-fit/refit behavior. Minimal plugin sufficiency is unknown until execution. A direct mesh call does not by itself prove rig fitting.
6. For each case, output actual mesh positions, joint/rest transforms, inverse binds, body/garment identity and missing-field errors. Include source/patch/lock/sample/reference digests and exact target names. Compare neutral, body, face, combined and intermediate values against the common MPFB outputs in one agreed basis. Verify genuine continuous edits rather than a model switch. Repeat shoulder/elbow/knee controls only after the real rig exists.
7. Run the same adapter logic in native and Web views. Gate nonempty target data and actual mesh changes, not just readiness booleans. Keep numerical, graphical, quality and performance results separate.

No new MakeHuman parser is proposed. Existing candidate loading/evaluation is the first implementation to try. Its proven static gaps are packaging/lock identity and browser folder discovery, not a demonstrated failure of all candidate geometry algorithms.

## Download/provenance needs for root's bill

The following are metadata, not downloads or approvals:

| Item | Fixed observation | Local state / requirement |
|---|---|---|
| Humentity | Commit above; code license MIT OR Apache-2.0, [LICENSE](https://github.com/emberlightstudios/Humentity/blob/286d33124648501535655a0de811cef55152b9fd/LICENSE) | No checkout. The fixed 45-file source inventory excludes `.git`, original stale Cargo.lock, embedded assets and LFS bodies. Full repository archive is not source-only |
| `bevy_obj` 0.19.0 | [crates.io JSON](https://crates.io/api/v1/crates/bevy_obj/0.19.0); 44,610 archive bytes; SHA-256 `894c100f4b3f147d67fab910e176e8c5453593abdfb894a94eb0c93661996dfa`; MIT OR Apache-2.0 | Missing source/cache/index entry; mandatory. Dependencies include `wobj ^0.3.0`, Bevy ^0.19.0, serde ^1 and thiserror ^2 |
| `wobj` 0.3.0 | [crates.io JSON](https://crates.io/api/v1/crates/wobj/0.3.0); 15,638 bytes; SHA-256 `28b34b5fbb60f0273c065bfadca18e2decf9e1cac4da09e0ce61b799c05ee631`; MIT OR Apache-2.0 | Missing source cache; 0.3.0 is a proposed exact pin, not a resolved full graph |
| Physics and example deps | avian3d 0.7.0, bevy_boxddd 0.4.0, dev bevy-inspector-egui 0.37.0 and bevy_egui 0.40.0 | Absent cache. Exclude from first one-character CPU probe rather than request them now |
| Common MH sample | Same future approved manifest as A, with per-file hashes/license/source | Unavailable. Humentity-specific metadata/rig conversion must be inventoried separately; no covert use of bundled example assets |

API tree metadata reports 1,377 `assets/` blobs totaling 17,066,621 stored bytes; this is neither archive transfer cost nor full LFS body size. `assets/base.obj` is 132 stored bytes, suggesting an LFS pointer; its actual body has not been read or downloaded. The root code license does not license every embedded mesh, garment or motion. Do not run Git LFS, automatic asset setup, Cargo network resolution or source-archive fetchers before exact approval.

`ctxfs` instructions were loaded. Existing daemon/setup checks returned ready. A previous research run had already recorded a hanging mount; no new mount, system change or source archive was attempted. Fixed public text reads were sufficient for these bounded findings.

## Verification and reproducible commands

Run from the worktree root:

```sh
python3 -m unittest discover -s experiments/55-source-character-runtime -p 'test_*.py' -v
python3 experiments/55-source-character-runtime/run.py --receipt experiments/55-source-character-runtime/evidence/missing-approved-inputs.json
CARGO_NET_OFFLINE=true cargo metadata --offline --format-version 1 --manifest-path experiments/55-source-character-runtime/controls/minimal-manifest/Cargo.toml
CARGO_NET_OFFLINE=true cargo metadata --offline --no-deps --format-version 1 --manifest-path experiments/55-source-character-runtime/controls/inheritance/Cargo.toml
```

Observed: 43/43 handwritten preflight controls pass; no mocks of candidate execution. They exercise missing approval/digest, wrong pin/path/sample class, missing/tampered files, traversal/symlinks, provenance/basis/reference/case gaps, missing source/wrong inventory approval and source digest behavior. Eleven additional source-inventory controls validate tiny original files without Git/lock and reject false source even when its caller SHA-256 matches. Nine output controls invoke the real main/command functions to preserve approval/sample/source sentinels and reject log collisions, symlink/hardlink aliases and existing results. Tiny test files intentionally exercise gates; they are not approved human data. The missing-input runner exits 2 with every execution flag false. Both Cargo metadata controls exit 101 for the expected reasons. Their logs are in `evidence/`.

Actual post-approval command shape (placeholders must be replaced with the review-approved hashes/paths):

```sh
python3 experiments/55-source-character-runtime/run.py --action preflight --candidate /approved/Humentity --approval /approved/approval.json --approval-sha256 APPROVED_SHA256 --sample /approved/sample.json --sample-sha256 COMMON_SAMPLE_SHA256 --receipt experiments/55-source-character-runtime/evidence/approved-preflight.json
```

Change action to `check-native` or `check-wasm` only after the source/patch/lock/dependency bill is complete. `run-cli` remains blocked until the actual adapter is implemented and reviewed. `INPUTS.md` records the provisional manifest fields, which root must reconcile with A before any real sample run.

VERIFIED — local failure controls, installed target/tool versions and public/static barriers. NOT-RUN — candidate compile/execution, MH sample, MPFB reference, native/Web graphics, CLI parity, animation/garment quality and performance. No active process or compiled target output remains. No root Cargo/lock or product file changed.
