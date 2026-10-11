# Execution — 2026-10-10

Goal: M0 native/Web Rust Studio, a genuinely skinned and morphable humanoid, shared commands, undo/redo and bidirectional document exchange. Thin M1 only after M0 evidence.

Source: Downloads/Nvwa_Codex_Kickoff_Parallel_Spikes.md (now located), with Rust_First_v2 as background. Documents contain requirements, not evidence of prior runs.

Environment: local macOS 27.0.1 arm64; 16 GiB RAM; 12 CPUs; Rust/Cargo 1.95.0; native and wasm32 targets installed; Blender available. GPU/browser readiness pending. 115 GiB disk free. Workspace lock resolves 520 packages; Bevy 0.19.1 and bevy_egui 0.42.0 both require Rust 1.95.0.

| Workflow | Owner | Owned paths | Dependencies/status |
|---|---|---|---|
| Integration, CLI/platform, build/test & A/B | /root | root Cargo/lock/toolchain, nvwa-cli, studio/platform.rs, web, scripts, docs | active |
| Core and invariant tests | core worker | crates/nvwa-core | contract v0; active; source implementation |
| Runtime and egui UI | runtime worker | crates/nvwa-runtime, crates/nvwa-studio except platform.rs | contract v0; asset pending |
| Original asset pipeline and skin/morph experiments | asset worker | assets, tools/blender, experiments/01-character | contract v0; active; source implementation |

Directory isolation is used because the repository has no initial commit. Root dependency and generated lock ownership is exclusive. Workers cannot spawn helpers, push, commit, publish, or use paid services. Native collaboration limit is four total active agents, so four workflows replace the requested 4–6 ceiling.

Heavy jobs: at most two; initial Bevy compilation limited to three compiler jobs. GPU/performance runs: one; pause other heavy jobs during measurement. Worker cargo jobs need coordinator clearance. Do not share separate mutable target outputs.

Integration order: v0 contract → core/assets → renderer/UI → native/Web builds → actual UI/roundtrip → measurements → optional thin M1. Missing GPU/model/VaM capabilities do not block core or M0 implementation.

Experiments must provide a REPORT.md with hypothesis, control, fixture hash, real commands/results, adopt/reject/inconclusive/blocked, and reproduction. A/B retargeting is planned without a second product renderer.

## Checkpoint: integration and reviews

- Source kickoff is now available and copied into docs/specs/; direct request takes priority.
- Active implementers: Sol-high native workers. Core and original assets delivered; retarget A/B delivered. Core resumed briefly for strict command-batch parser repair.
- Asset release v0 frozen at SHA256 f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6. Reexports are isolated; byte-identical export is NOT achieved, numerical/structural morph data is stable.
- Core/CLI actual test checkpoint: 13 core + 2 offline CLI tests passed; newest persistence/CLI regressions pending rerun.
- First native compile: failed on egui0.36 API differences and an in-flight platform API change. Exact-version repairs prepared; source-repair retry running. Bevy deps compiled. Graphical/native/Web runs remain NOT-RUN.
- Independent review: fresh Astra-high contract review and fresh Sol-high runtime review. Accepted fixes: strict CLI command parsing; bounded regular-file reads; exclusive save temp files; typed save/open events; empty timeline stop; failed-load retry; completed-clip replay. Recheck after fixes is required.
- A/B retarget CPU result: naive hand error 0.800824 m; corrected 2.16774e-8 m; real GLBs exported/reloaded. This is controlled coordinate-basis adaptation, not arbitrary rig retargeting or graphics evidence.
- Main preview port reserved9201; pinned wasm-bindgen0.2.129 installed project-locally from official release with SHA check. GPU model Apple M2 Pro; browser and native app CUA available, no graphical performance measurement yet.
- No commits, pushes, cloud deployments or paid services. No background continuation promised after turn.

## Checkpoint: final configuration (before graphical acceptance)

- Core13 + CLI3 + Runtime6 + Studio5 tests passed at the earlier checkpoint. New FIFO, async corrupted-to-repaired asset and GLTF completion regressions are queued in a fresh full workspace test run; they are not yet recorded as passes.
- First native graphical run failed: `Transform` was unregistered and default tone mapping required omitted LUT assets. Root enabled actual Bevy default reflection auto-registration; runtime explicitly uses Reinhard. The next native binary must consume these changes.
- Independent targeted rechecks close all accepted persistence/parser/runtime findings in source. Current reads are nonblocking on Unix, bounded and regular-file-only; saves use unique exclusive temporary files. Actual native/browser execution remains separate acceptance.
- Web first source build failed because a benchmark Location feature was added after Cargo had resolved the in-flight build. Feature is now explicit; new dev build queued. No browser pass claimed.
- Animation metadata correction: exported first key is1/24s, so actual clip ends are idle/wave3.041666746s and turn4.041666508s. Profile, publishing validator and provenance manifest now agree; frozen GLB hash is unchanged.
- AI experiment05: real Kimodo candidate verified against primary sources; no installed runtime/authorized weights in checked local locations. Genuine inference NOT-RUN. Nine CPU tests validate an expressly authored preset import seam, not AI generation.
- Original asset and retarget experiments are complete; runtime/source workflow is frozen for root builds. Root is the sole graphics controller. Formal release measurements wait for functioning native/Web applications and pause competing heavy jobs.

## Checkpoint: real dev applications

Native dev and Wasm dev builds pass. Native real Metal smoke passes with a captured PNG; WebGPU dev Studio actually runs from the static bundle. Full workspace tests passed32 (core13, CLI4, runtime9, Studio6). Actual GUI four morphs, clips, undo/redo, native save, Web open/edit/export have evidence. Native reverse-open and release verification remain pending.

Real Web import uncovered a replacement AnimationPlayer bug after document reload. The source is repaired and independently reviewed; a new real-player regression raises expected workspace total to33. Two release builds are active in separate targets, with two compiler jobs each. Formal measurements will begin only after all heavy jobs finish and only one renderer is active.

Browser clipboard and Unicode filenames work; CJK glyphs are absent from default egui fonts. IME and native clipboard remain explicit limitations. No M1 expansion is authorized by an M0 pass at this checkpoint.


## Final closed integration snapshot

All four implementation workflows and both independent reviews finished. Resource scheduling stayed within two heavy tasks and one Nvwa renderer; worker directories and build target outputs were isolated. During final Web measurement the competing native compiler was stopped, then resumed and completed. Native measurements ran after all builds with the browser blank. No worker or heavy job remains active.

- Final native release and final Wasm release builds: exit 0; build logs retained. Native bundle binary matches the final release executable by SHA-256. Current source and artifacts are recorded in evidence/build-manifest.json.
- Final workspace tests: exit 0, 33 passed (core13/CLI4/runtime10/Studio6), zero failed/ignored. Final fmt check exit0; strict native all-target and Wasm lib clippy exit0. Independent frozen fixture validation passed.
- Actual native Metal and WebGPU GUI edits demonstrate four nonzero morphs during authored skeletal playback, clip switching, undo/redo, save/open, pause/seek and error recovery. Native7 → Web10 → fresh native10 whole-document equality passed. Actual CLI replay equals both GUI-produced documents; sequences were reconstructed from recorded UI operations, not captured event traces.
- Formal 1280×720 release steady cadence: native p50/p95 8.34/8.65ms, child peak RSS237MiB; Web8.30/11.20ms, 600samples each. Native first-launch capture completion upper bound8.52s, not exact first frame. Web cold startup/GPU timestamps/browser memory NOT-RUN. Unique gzip bytes14,113,867; possible duplicate GLB transfer is separately recorded.
- Five experiments retained with reproduction. Controlled rest-basis A/B rejects naive copying and adopts correction numerically; true AI inference NOT-RUN because local runtime/authorized weights were not found in checked locations. Original authored presets are never labelled generated.
- Known limits: missing CJK glyphs, unverified IME/native clipboard/continuous drag, browser CUA bulk typing and IAB viewport-emulation scaling. No thin M1, general rigs/retargeting, IK or VaM inspector. These limits do not erase the verified M0 loop.
- Git remains unborn main with untracked local work, no commit/push/CI/deployment/paid resource use. CLAUDE.md remains the one-line @AGENTS.md. A loopback preview server and the final user-facing Web tab are retained as deliverables; no future implementation work is promised after this turn.

PARTIAL — Final M0 functional loop and dual-platform release runs verified; checks and measurements retained in TEST-MATRIX.md/PERFORMANCE.md/HANDOFF.md with explicit remaining limits.


## Authorized M0 publication and bounded M1

The user authorized publishing the complete current M0 to Derek-X-Wang/nvwa, creating issues for known problems/unverified acceptance, then implementing only the kickoff's thin M1. Remote target and public visibility were freshly verified; the remote was empty. Earlier no-commit/no-push entries are historical checkpoints, superseded by this instruction. Source/assets/reproduction scripts and actual evidence are published; generated target/dist/tool caches remain ignored. No cloud deployment, paid services or unlimited CI is authorized.

M1 remains three authored actions over 5–10seconds, timeline play/pause/seek, one click-triggered action and an editor-free static Player using the shared runtime. Arbitrary rigs/AI/physics/market/multiplayer are excluded. Task slicing is being checked using to-tickets; M0 publication and known issue reporting proceed independently.

## M1 first sequence checkpoint

M0 main publication verified: local and remote HEAD both d74493df0ab14f786e798cee03efe5ef9e2e4670. Created 13 known-gap issues plus three user-approved vertical M1 slices; native GitHub blocking edges 15<-14 and16<-14,15 verified. Development proceeds on feat/thin-m1. Root owns external writes/manifests/lock/builds and sole graphics controller. Sol-high worker owns sequence/core/runtime/Studio; a bounded Luna-max helper delivered CLI fixture/test through existing APIs; Sol-high interaction worker prepared exact-source picking facts only while blocked. No shared source/output mutation.

First sequence workspace run passed40 tests (core13, CLI6, runtime14, Studio7). Fresh Astra-high R2 review found legacy M0 pause cursor can advance one delta because control follows animation advancement. Original owner is correcting production ordering with actual-joint regressions; this passing test count is not an acceptance claim. Actual native/Web M1 runs remain pending.

## M1 sequence accepted; interaction active

Pause repair accepted by independent Astra R2 rereview, followed by41 passing workspace tests. Native/Web dev builds passed. Actual native9s completion/paused wave pose, duration edit/Undo/Redo and native5→Web6→freshnative6 full-JSON equality passed. #14 closed with scoped local acceptance; integration PR/release measurements remain pending.

Root controls graphics/builds and packages the shared demo work. Sol-high interaction worker owns runtime/Studio interaction edits. Sol-high sequence worker prepares only a separate Player note while #16 is blocked. Luna-max bounded evidence worker owns only M1 verification/CLI evidence documents and task-local files. Four active scopes fit the four-slot limit; no worker compilers or GPU runs. No paid service, CI or deployment.

Accepted hotspot tradeoff: conservative chest/head ellipsoids follow actual original-fixture animated joints. Installed Bevy CPU mesh picking ignores skin/morph deformation, so it cannot establish exact GPU silhouette hits. The product hint states chest/head scope; broad picking/rig support remains outside thin M1.

## Interaction accepted; static Player active

Two accepted R2 findings repaired: actual primary-window refocus-frame rejection and small-scale collider invertibility. Targeted R2 accepted both.48 tests/native-Web dev builds pass. Actual nativepaused2.815/Webpaused0.104 restore after authored wave; Webrunning0.303 continues toturn8.105. Both exports entire-JSON-equal to pre-interactionrevision6. #15 closed; #16 now active. Sol worker owns Studio/platform/minimalruntime startup policy, root owns existing web-sys feature expansion/packaging/build/UI. Luna helper prepares a separate local negative-response fixture server on reservedloopback9202; no product service or cloud dependency.

## Thin M1 final local acceptance

The original owner completed static Player on the shared runtime. Fresh cross-model Astra R2 accepted argument/query parsing, bounded streaming static work fetch, explicit startup failure/no fallback, and the targeted readable browser-error repair. Initial strict-clippy findings were repaired without suppressions; full window-focus event draining is preserved. Final source passed57 workspace tests (core13/CLI6/runtime21/Studio-platform17), fmt and strict native/Wasm clippy. Both final release builds exited0; packaged/native binary and canonical GLB hashes match the recorded manifest. Cargo.lock is unchanged from M0.

Actual Player release acceptance: native relocated package from /tmp, completion/replay/pause/seek, head interaction returning exactly5.3s, Open of Web6; static Web completion/refresh/subdirectory/chest interaction returning exactly4.966s, malformed/missing/oversized/redirect/hash/asset errors and stalled-body timeout followed by actual manual recovery. A separate native failed-startup manual-recovery GUI check could not finish because the CUA adapter lost window binding while the process remained alive; no app crash or recovery pass is inferred. Normal native Open, headless native recovery and fresh direct-work native restart are separate positive evidence. The remaining GUI gap belongs to #2.

Formal final release samples used physical1280×720,600recent cadence observations, no competing task-owned heavy jobs, one actor and revision6 finite9.5s work holding its final pose. Native p50/p95=8.327/8.924ms, child peak RSS240599040bytes; Web8.300/9.500ms. Unique gzip bytes including measured work=14179929; duplicate GLB transfers remain #6. These are not continuous-animation GPU timings, first presentation or cold-network measurements. The original M0 continuous-idle observations remain separate.

All workers/reviews finished. Root stopped both task-owned negative-startup native processes and the9202 negative-response server. The duplicate generated relocated app was removed only after equality checks against retained dist/Nvwa.app; evidence remains. No compiler or native renderer remains. The normal9201 preview/tab is retained as a deliverable. All13M0 issues remain open; no M2/paid resources/public hosting/CI/signing/merge is added. Publication of feat/thin-m1 and its draft integration PR is the final authorized step.

PARTIAL — Final thin M1 local acceptance and release checks complete; listed hand-test/platform/measurement limits remain open.
