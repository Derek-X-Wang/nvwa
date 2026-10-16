# Adjustable rehearsal stage — implementation and local checks

Issue: [#69](https://github.com/Derek-X-Wang/nvwa/issues/69), Stage A only.

The shared Rust Work now owns a validated `StageSettings`: explicit key and fill illuminance, color and direction; ambient brightness and color; background and floor color; floor visibility and shadow request; orbit camera, framing and vertical FOV; requested quality. White studio and black space are reproducible constructors. The original character asset, morph recipe and authored animation path stay in use. No imported rooms, collision, physics, network, motion model, inference or asset download is introduced.

Schema 2 requires the stage. The strict schema 1 decoder supplies the default white stage and preserves revision, profile, recipe and timeline. Saving writes schema 2; older applications reject that version. Original fixture bytes remain unchanged. Unknown fields and duplicate typed fields are rejected by direct deserialization; the public JSON entrypoints also reject duplicate map keys through the existing prepass. Invalid values cannot commit a partial stage or alter retained history.

The floor is at world `y=0`. Camera distance and target height use character-relative units; camera transforms and near/far planes multiply by the existing character scale. Full-body and detail presets are therefore stable for scales 0.5, 1 and 2. Camera conversion outside presentation scale `0.001..=100` reports a visible runtime diagnostic and keeps the previous finite camera. It does not change the portable finite-positive scale contract or the saved Work.

| Requested quality | MSAA | Key shadow map | Contact shadows |
| --- | --- | --- | --- |
| Low | Off | Disabled (map setting 1024) | Disabled |
| Balanced | 4× | 2048, if shadow switch is on | Disabled |
| High | 4× | 4096, if shadow switch is on | Enabled with depth prepass if shadow switch is on |

Fill shadows stay off. The key uses a single cascade with near/far distances `0.05×scale` and `40×scale`. Its world-space depth bias is `0.02×scale`; normal bias remains 0.6 shadow texels. High contact-shadow length and thickness are `0.25×scale` and `0.04×scale`. These distances use the same character-relative stage units as the camera, including the supported scale boundaries. The floor is a real rough PBR material and is configured to receive the character's shadow. High adds Bevy screen-space contact shadows. These rows describe applied component settings, not measured native/Web cost or a promise of identical pixels. No image quality or performance conclusion follows from CPU tests.

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

## Final stable-checkout CPU gate

`CARGO_TARGET_DIR=<allocated existing runtime cache> CARGO_BUILD_JOBS=1 cargo test --workspace --offline --locked` passed **135 tests** on the final implementation source: 36 core/CLI, 42 runtime and 57 Studio. Compilation took 1m51s. The five real-control Stage tests cover slider release and Escape, presets/hide/return, viewport orbit, wheel-burst history, IME/slider ownership and read-only Player orbit. Existing paint, file recovery, playback, interaction, bounded-history and strict-JSON tests pass unchanged, apart from the intentional current-schema expectation and sixth discoverable command.

The production scale test includes `0.001`, `0.5`, `1`, `2` and `100`; it verifies applied camera, cascade bounds, depth bias and contact distances, plus explicit error and Work preservation for extreme finite scale. The independent review identified the original fixed cascade bounds; the runtime now scales every world-space shadow distance with the character.

A direct run before package cleanup failed discovery tests because reused executables referenced a retired wefty snapshot for compile-time fixture paths. A package-scoped Cargo cleanup and rebuild from the stable checkout restored the actual fixture reads, without changing the test assertions or product behavior. The shared dependency cache was retained. Final formatting, whitespace and strict core/CLI Clippy checks passed.

Native/Web build receipts follow. This source gate does not claim GPU pixels, native or browser input acceptance, performance, memory, first frame or human preference.

## Native artifact

`CARGO_TARGET_DIR=<allocated existing runtime cache> CARGO_BUILD_JOBS=1 cargo build -p nvwa-studio --bin nvwa-studio --offline --locked` completed in **2.91 s**, dev optimized+debuginfo, on stable source after the 135-test gate. Copied artifact: 156,128,016 bytes, SHA-256 `379aa3e290ac049489154bff42cde271faf93da882986275358237ce1ed81921`. Source-file-map SHA-256: `ffecacb5df699d40add6eacd86922d59d2715367207752c49a52ebc4a60b344a` (canonical sorted compact JSON of all Rust crate source/manifests, workspace manifest/lock/toolchain and Web index hashes). The private artifact manifest records every source hash, exact checkout and copy time; root integration owns graphical evidence. The unchanged fixture SHA-256 is `f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6`.

At native copy, HEAD was `9b3fd91615e09397f82836ed5cb6a0219ce39993` plus the implementation changes committed next. The binary must use the production `NVWA_ASSET_ROOT` override when moved away from its source checkout. No GPU launch was performed by this worker.
