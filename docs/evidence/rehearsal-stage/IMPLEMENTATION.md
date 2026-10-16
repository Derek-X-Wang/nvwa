# Adjustable rehearsal stage — implementation and local checks

Issue: [#69](https://github.com/Derek-X-Wang/nvwa/issues/69), Stage A only.

The shared Rust Work now owns a validated `StageSettings`: explicit key and fill illuminance, color and direction; ambient brightness and color; background and floor color; floor visibility and shadow request; orbit camera, framing and vertical FOV; requested quality. White studio and black space are reproducible constructors. The original character asset, morph recipe and authored animation path stay in use. No imported rooms, collision, physics, network, motion model, inference or asset download is introduced.

Schema 2 requires the stage. The strict schema 1 decoder supplies the default white stage and preserves revision, profile, recipe and timeline. Saving writes schema 2; older applications reject that version. Original fixture bytes remain unchanged. Unknown fields and duplicate typed fields are rejected by direct deserialization; the public JSON entrypoints also reject duplicate map keys through the existing prepass. Invalid values cannot commit a partial stage or alter retained history.

The floor is at world `y=0`. Camera distance and target height use character-relative units; camera transforms and near/far planes multiply by the existing character scale. Full-body and detail presets are therefore stable for scales 0.5, 1 and 2. Camera conversion outside presentation scale `0.001..=100` reports a visible runtime diagnostic and keeps the previous finite camera. It does not change the portable finite-positive scale contract or the saved Work.

| Requested quality | MSAA | Key shadow map | Contact shadows |
| --- | --- | --- | --- |
| Low | Off | Disabled (map setting 1024) | Disabled |
| Balanced | 4× | 2048, if shadow switch is on | Disabled |
| High | 4× | 4096, if shadow switch is on | Disabled after observed Web speckle |

Fill shadows stay off. The key uses a single cascade with near/far distances `0.05×scale` and `40×scale`. Its world-space depth bias is `0.02×scale`; normal bias remains 0.6 shadow texels. Shadow distances use the same character-relative stage units as the camera, including the supported scale boundaries. The floor is a real rough PBR material and is configured to receive the character's shadow. High retains the larger PBR shadow map; the optional screen-space contact pass is disabled after actual Web images showed stable self-shadow speckle. These rows describe applied component settings, not measured native/Web cost or a promise of identical pixels. No image quality or performance conclusion follows from CPU tests.

Studio's bilingual Stage window can be hidden and reopened. Sliders show a validated preview and create one undo step on release; Escape cancels. Right-button viewport drag orbits; a wheel burst zooms and commits once after 220 ms without further wheel input. Editor widgets, focused text/IME and unfocused windows reject new camera gestures. Player uses the same saved stage and rendering systems; its orbit is temporary and opening another Work clears it. Player transport does not edit the Work. Shape, timeline, playback, file operations and the original click-to-wave path remain available.

`NVWA_EVIDENCE` includes the requested stage and any stage conversion error. Native/Web visual acceptance, first-frame timing, memory, controlled quality comparisons and human preference remain separate from these source and CPU checks. Root integration owns those records and final CI.

## Verification receipts

- Direct local `CARGO_BUILD_JOBS=1 cargo test -p nvwa-core -p nvwa-cli --offline --locked`: 36 tests passed after strict decoder and CLI migration checks. Uses the allocated existing native cache.
- A direct `cargo check -p nvwa-runtime -p nvwa-studio --offline --locked` was stopped with TERM when it proved to require a cold metadata dependency pass. It is incomplete, not build evidence.
- Wefty `run_625e028fc52341ac1234b25f2ec047ba`: workspace test compile failed (exit 101, 20 s). Fixed missing mutable binding for Bevy's asset guard. Later passing receipts supersede this compile failure, while retaining it here.

Further workspace, native and Web receipts are appended after execution. GPU, browser/native input and pixel assertions are **NOT-RUN by the implementation worker**; CPU egui tests inspect the real control path, not rendered GPU pixels.

- Wefty `run_651b69b42a5ea16cb8ebab900195e504`: workspace test compile failed (exit 101, 77 s). Production runtime and Studio compiled, but the new test used an older egui IME variant. Fixed the test to the installed egui 0.36.2 struct shape.

- Wefty `run_97b3457aea1b704c19dfab458e537e0e`: compiled all tests; 41/42 runtime tests passed. The production floor mirror test failed because the floor depended on the default camera visibility plugin registration to supply `Visibility`. Added explicit floor visibility in the production spawn; the independent expected color assertion remains unchanged.

- Wefty `run_05139cdce6f9e93eab1b4da89fc14ea4`: workspace test compile failed (exit 101, 60 s). A new wheel test needed the current egui `TouchPhase` field; corrected from cached source.

- Wefty `run_75791b0cd24d23564ada7cdba553795a`: 36 core/CLI + 42 runtime + 56/57 Studio tests passed. The guard test incorrectly expected a secondary light-slider drag to leave its light unchanged; egui accepts that drag as a slider edit. Corrected the oracle to preserve camera, recipe and timeline during the widget edit, then require full Work stability during IME-owned input. Production input behavior was unchanged.

## Initial stable-checkout CPU gate (source fe4afb6)

`CARGO_TARGET_DIR=<allocated existing runtime cache> CARGO_BUILD_JOBS=1 cargo test --workspace --offline --locked` passed **135 tests** on the initial pre-framing-correction implementation source: 36 core/CLI, 42 runtime and 57 Studio. Compilation took 1m51s. The five real-control Stage tests cover slider release and Escape, presets/hide/return, viewport orbit, wheel-burst history, IME/slider ownership and read-only Player orbit. Existing paint, file recovery, playback, interaction, bounded-history and strict-JSON tests pass unchanged, apart from the intentional current-schema expectation and sixth discoverable command.

The production scale test includes `0.001`, `0.5`, `1`, `2` and `100`; it verifies applied camera, cascade bounds, depth bias and contact distances, plus explicit error and Work preservation for extreme finite scale. The independent review identified the original fixed cascade bounds; the runtime now scales every world-space shadow distance with the character.

A direct run before package cleanup failed discovery tests because reused executables referenced a retired wefty snapshot for compile-time fixture paths. A package-scoped Cargo cleanup and rebuild from the stable checkout restored the actual fixture reads, without changing the test assertions or product behavior. The shared dependency cache was retained. Final formatting, whitespace and strict core/CLI Clippy checks passed.

Native/Web build receipts appear below. This source gate does not claim GPU pixels, native or browser input acceptance, performance, memory, first frame or human preference.

## Native artifact

`CARGO_TARGET_DIR=<allocated existing runtime cache> CARGO_BUILD_JOBS=1 cargo build -p nvwa-studio --bin nvwa-studio --offline --locked` completed in **2.91 s**, dev optimized+debuginfo, on stable source after the 135-test gate. Copied artifact: 156,128,016 bytes, SHA-256 `379aa3e290ac049489154bff42cde271faf93da882986275358237ce1ed81921`. Source-file-map SHA-256: `ffecacb5df699d40add6eacd86922d59d2715367207752c49a52ebc4a60b344a` (canonical sorted compact JSON of all Rust crate source/manifests, workspace manifest/lock/toolchain and Web index hashes). The private artifact manifest records every source hash, exact checkout and copy time; root integration owns graphical evidence. The unchanged fixture SHA-256 is `f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6`.

At native copy, HEAD was `9b3fd91615e09397f82836ed5cb6a0219ce39993` plus the implementation changes committed next. The binary must use the production `NVWA_ASSET_ROOT` override when moved away from its source checkout. No GPU launch was performed by this worker.

## Web artifact

`CARGO_TARGET_DIR=<allocated existing runtime cache> CARGO_BUILD_JOBS=1 cargo build -p nvwa-studio --lib --target wasm32-unknown-unknown --offline --locked` completed in **46.71 s**, dev optimized+debuginfo. The existing pinned `wasm-bindgen 0.2.129 --target web` generated the browser bundle successfully. Generated `nvwa_studio_bg.wasm`: 114,613,742 bytes, SHA-256 `070f0314088bc34ac8b9cc23425f944b20254bda7eb7f0e9c455bd8027821b48`. Generated JS: SHA-256 `526b770740bd181d491b5c2688292959f0c74002dc16a2b56544869880a28b8b`. Source is commit `fe4afb6cfcb63d484210bcfccaf40a52ffea436e` and matches the native source-file hashes. Web index, unchanged fixture/profile, example Work and required license files accompany the private bundle.

The raw debug Wasm retains debug information and is larger than the bindgen browser module. No download, new dependency or release graph was used. The implementation worker performed no browser/GPU launch, input test or performance measurement. Root integration owns actual native/Web acceptance.

## Corrections after actual Web acceptance

The initial source/artifacts above are historical. Root's actual Web run found two presentation failures: the full-body view was cropped by the animation panel, and the optional High screen-space contact pass produced stable face/body speckle. Root retained the [cropped white view](runtime/pre-fix-white-cropped.png), [High speckle](runtime/pre-fix-black-high-acne.png) and [Balanced comparison](runtime/pre-fix-black-balanced.png). These are root-owned graphical observations, not implementation-worker GPU tests.

The scene camera now uses the available rectangle from the final production Studio/Player UI pass. Bevy's `SubCameraView` maps that virtual scene frame into the free area while keeping the camera viewport at full-window size for egui. Ratios use consistent logical units, including fractional points, independently of window DPI. The fit runs after UI/runtime mirroring and before Bevy camera update; picking runs after that update and uses the same computed projection. This is session layout state and applies no Work command or revision change. The full-body preset remains distance 3.8, target 0.95 and FOV 36.

Red/green proof uses the production UI draw path, production fit system and real Bevy `camera_system`, then observes public `world_to_viewport` and `viewport_to_world` results:

- Before fitting, fixture foot `(-0.25, 0, -0.2)` projected to `(591.04, 599.11)` outside the actual 1280×720 Studio scene rectangle `[180,26]..[1000,510]`. The new test failed as required (13.63 s compile).
- After fitting, head/feet bounds and picking-ray round trips passed for Studio 1280×720, Studio 1024×768, Player and DPI 2 (11.80 s compile). The camera viewport stays full-window.
- The original Detail target 1.52 still failed after viewport fitting: fixture head bound `(-0.22, 1.89, 0.19)` projected to `(384.43,-35.98)`, above scene top 26 (9.83 s compile). Detail now targets the fixture head center 1.65; distance 1.25 and FOV 30 remain unchanged. Independent fixture head bounds pass in Studio 1280/1024 and Player.

High retains 4× MSAA and the 4096 PBR key-light shadow map. The optional contact pass and its depth prepass are disabled. CLI discovery, the UI hint and production component tests reflect this actual profile. The key shadow maps, fixed ground height and scaled cascade/depth-bias behavior remain intact. This removes an implementation choice that degraded the observed image; it does not remove the user's lighting/shadow or quality controls.

Final stable-checkout `CARGO_BUILD_JOBS=1 cargo test --workspace --offline --locked` passed **137 tests** (36 core/CLI, 42 runtime, 59 Studio), compiling in **54.63 s**. Strict core/CLI Clippy passed in **2.15 s**, and formatting/whitespace checks passed. The standalone Studio+CLI dev build completed in **3.29 s** with `cargo build -p nvwa-studio --bin nvwa-studio -p nvwa-cli --bin nvwa-cli --offline --locked`. The corrected artifact cohort and source hashes follow; root owns the graphical recheck and final CI.

## Corrected artifact cohort: framing-v2

Corrected product source: `db0139e0ffb195abf681620e6f691eb103ce2dd3`. Native and Web manifests verify the same complete Rust/workspace/Web-index source map, canonical SHA-256 `2e7db5c84a81d3152b8a234f5624ce4f6132a8fa7bf654ebe5c35b0863ea6cc7`. Original fixture bytes remain unchanged.

- Native Studio: 156,147,200 bytes, SHA-256 `60e8daf6d7eb4014a5a97e184a671850b67f7b533df3541d8b5fac24c8fb6114`.
- Native CLI: 1,540,088 bytes, SHA-256 `5201bd01c67e9c24f1cc57d81af4ddd649a0981cf31c0c196d3cf36cdd95bbaa`. The CLI artifact is copied separately for root's real file/capability acceptance.
- Web dev build: **27.32 s**, followed by successful pinned `wasm-bindgen 0.2.129 --target web`. Browser module: 114,643,468 bytes, SHA-256 `f98eb1f4f9748918edb8cc26231202a6a13fe3cad2ecad48a0e1c8dd294c2f78`. JS SHA-256 `05c8adc45f6c2a95f833e1a6e81d58c46aa602094b7b308aa3499fe7b2e4c930`.

Corrected artifacts are kept in a distinct private `framing-v2` cohort so the earlier images and artifact hashes remain traceable. All worker build/bindgen processes finished. The worker performed no GPU/browser/native launch; root owns corrected pixel/input acceptance and final CI.

## Final initial-window placement polish

Root's fresh 1024×768 Web observation confirmed the corrected full-body frame, but opening the movable Stage window at its original x=195 covered the character. The sole production change moves the initial Stage window to `(12,72)`, over the left sidebar. Camera, schema, panel layout, quality and file behavior are unchanged. Existing real-control test inputs were translated to the moved sliders; no test that merely mirrors the position constant was added.

All **five focused Stage UI tests** passed (8.37 s compile), including actual slider release/Escape, presets, pointer/IME ownership, wheel history and Player orbit. Formatting and whitespace checks passed. A subsequent cached full-workspace gate passed **137 tests** on source `b43757d` (2.35 s compile); final-head CI and root's actual fresh 1024 view check remain separate. This change does not address or work around the live IAB resize limitation tracked by #3.

## Final artifact cohort: framing-v3

Product source `b43757d87dde8294525769a98db17eab57a886fc` changes only the initial Stage-window x position in production. Native Studio rebuilt in **6.34 s**: SHA-256 `b319f513e31801bef6e007a3a3f642e8abf07ebaff6959ec2386ee787bd21b2a` (156,147,200 bytes). CLI is reused with verified SHA-256 `5201bd01c67e9c24f1cc57d81af4ddd649a0981cf31c0c196d3cf36cdd95bbaa`; CLI/core sources, workspace manifest, lockfile and toolchain hashes are unchanged from its build.

Web dev build completed in **12.07 s**, followed by successful pinned bindgen generation. Browser module SHA-256 `ae1118cc1d35d73b910c693865274b42a8e2fd403b880c764341b6b571545d9d` (114,643,468 bytes); JS SHA-256 `05c8adc45f6c2a95f833e1a6e81d58c46aa602094b7b308aa3499fe7b2e4c930`. Native/Web manifests share canonical source-file-map SHA-256 `1e51c7c192191645552d5fdc5a918bf2e8ae26ced3537c74a0e37eae6a472ce6`. The private `framing-v3` cohort preserves earlier cohorts and includes the unchanged resources/licenses. All worker processes finished, with no GPU/native/browser launch.
