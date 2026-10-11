# M1.1 editor components — final experiment report

Verdict: **ADOPT the narrow tab/split pattern for separate integration; actual native/Web behavior passes within the recorded scope.** Root production source, dependencies and lock remain unchanged. Native1024×768 GUI and new physical IME/DPR still require validation before production acceptance.

## Scope and provenance

Frozen Nvwa base `11fc789e898119e0ed2b423f8a909dacb547f772`. Only generated `crates/nvwa-studio/src/lib.rs` and new `editor_layout.rs` change. Core/runtime, command handlers, schema, original GLB/profile/fonts, and Web input adapter remain frozen. Original file hashes and overlays are recorded by `prepare.py` in `.work/m11-ui/generated-manifest.json`.

Dependency: `storytold/craft-libs` git revision `5c874d51eeb3de70e735c8ce87a59a7dedd47675`, package `craft-ui`. PhotoCraft uses this actual pin. Production dependencies are egui `^0.36` (default features disabled), optional serde disabled. Current Nvwa egui is 0.36.2 through bevy_egui 0.42.0. Version overlap is source evidence; compilation still must verify a single egui instance.

Source read at exact revision: root `Cargo.toml`, `crates/ui/Cargo.toml`, `crates/ui/README.md`, `crates/ui/src/lib.rs`, `crates/ui/src/tabs/mod.rs`, `crates/ui/src/layout/{mod,geometry,resize}.rs`, and `LICENSE-MIT`. Raw files and GitHub recursive tree identity are retained in `.work/m11-ui/source/`. FSKit mount was attempted once, failed with `file system extension not registered`, and no extension/security configuration changed. Source fallback used exact GitHub raw/API reads.

Select upstream MIT terms; preserve its full copyright and permission notice in `licenses/craft-ui-MIT.txt`. The dependency imports no PhotoCraft app code, fonts, icons, brand assets, or engine.

## Candidate behavior

A uses existing inspector/timeline bodies. B adds craft-ui Shape/Profile tabs and a timeline ResizeHandle, using original editing controls and commands. The user can always return to Shape, and Reset layout selects Shape. B timeline scrolling retains access to existing sequence/transport controls at narrower widths. Lock/reset/cancel and variant/tab selection change session layout only. The application, rather than the library, owns layout state. The prototype uses the same Bevy/egui loop, fixed viewport camera and current-frame pointer/keyboard guards.

Layout changes are staged on a clone and installed only on the final egui pass. Reset/cancel during a split drag suppress further deltas from that drag. Lock during a drag cancels it. Preferred timeline height survives a temporary small window through bounded visible geometry. Work save path is task-specific.

## Verification status

- Prepared fresh generated workspace, retained 681 original file hashes, applied exactly 2 Studio source overlays: PASS (preparation only).
- Python entry syntax and rustfmt source parsing: PASS.
- Full workspace Rust tests: PASS, 99 tests (93 existing plus 6 experimental), `cargo test --workspace --locked --offline`, jobs2; current-source reviewed run8.38s. Log `.work/m11-ui/logs/workspace-tests-reviewed.log`; JSON includes exact source/manifest/lock hashes.
- New tests: PASS for complete Work/history preservation, reset/cancel/lock/switch/tab semantics; actual craft Tab click and ResizeHandle Escape; actual Studio A/B pointer and Space guards at both required sizes; actual idle draw_resize window shrink/recovery.
- Native release compile: PASS280.34s under root lease UI-2026-10-11-1, jobs2, offline/locked. `native.log` and `native.json` record command, source hashes and preserved artifact103,041,200 bytes, SHA256ae66f6854ee845265d4e11c57ad711ace0124718e23a6c5677efe88e00c25f5f.
- Wasm release compile and packaging: PASS, Cargo19.58s / total32.20s under the same root lease. `wasm.log` / `wasm.json` retain exact command/source hashes. Raw Wasm85,589,065 bytes, SHA25698763bf27983a249d77f2827616791856effe9ecdc6ce774fa8ef12fa02563f8; packaged Wasm85,610,102 bytes, SHA25609f62cbf4de9338f1e452f11c5e15bc1cbce674e156ae8e564ba5f72b34a5fc8.
- Actual native acceptance: PASS within1280×720 logical /2560×1440 content scale2. A/B/Profile/lock/reset preserve complete Work at revision0. Derek physically confirmed continuous jaw drag followed by one Undo returns0.71, and split resize/Escape restores the prior height. Root saved before/after manual states, rev3→5 with all nonrevision fields equal, then Redo6 and Save/Open/Save with full JSON equality. Worker launched no GUI. Native1024×768 actual GUI remains NOT-RUN.
- Actual candidate Web: PASS, root operated the real rig at1280×720 and1024×768. Tabs/split/lock/reset preserve full Work; real jaw drag makes one revision0→1, Undo2 restores all content, Redo3 restores edited content. Small-window timeline scroll exposes seek and sequence rows; a9-second idle/wave/turn Work was saved at rev8. Native→Web rev6 and Web→native rev8 are complete JSON equal. See root evidence. Physical IME/DPR were not repeated.
- Performance: NOT-RUN; no timing conclusions.
- Physical Chinese IME/preedit/candidate window, real OS clipboard, unsupported DPR actions: NOT-RUN.

Root integrates approved dependency/lock in the generated workspace and reviews actual evidence before deciding adoption. Preparation success alone does not establish usability or readiness.

## Review repair and red/green evidence

Independent root review found zero-delta idle resize calls could replace preferred height422.40002 with396 while shrinking768→720. Added a real draw_resize768→720→768 regression. It failed at720 with exactly those values (`resize-window-red.log`,7.04s), then passed in the99-test current-source run after guarding resize on a nonzero delta. Actual resize proposals still clamp. This proves stored preferred-height recovery at the production-called boundary.

Earlier failed checks are retained: first test compilation used four old CentralPanel test calls; fixed them for egui0.36's root Ui API. A subsequent exact f32 dimension expectation failed422.40002 vs422.4; changed that geometry-only assertion to a0.001-point tolerance. These failures did not require product semantics changes.

## Build-helper verification

The stage helper derives the primary checkout from Git's common directory and accepts explicit target/tool paths. Preparation always archives exact frozen11fc and overlays reviewed source, independent of current HEAD. Fresh reproducibility preparation preserved all681 original hashes and final reviewed overlays.

Helper checks use lightweight owned process stubs, with no Cargo/GPU/network. Timeout, KeyboardInterrupt, handled termination signal and ordinary exception all reclaim the owned process group. Terminal metadata retains each error and exact source hashes. A source change detected after execution fails before artifact preservation. Python syntax checks and6 strengthened checks pass (`helper-checks.json`). Actual elapsed timeout, delivered SIGTERM, delivered SIGINT, and normal parent failure use a real TERM-ignoring descendant and verify complete group absence in2.32–2.59s. A real post-Popen log exception also reclaims its group; a source-change case fails before artifact preservation. Initial simulated checks are retained separately and do not substitute for descendant evidence.

## Handoff status

Sole build lease UI-2026-10-11-1 is released. All build/packaging processes ended; Cargo and wasm-bindgen owned groups are absent. The preserved native/Web artifacts, current99-tested Rust source, generated manifest and lock remain unchanged after helper repairs. Root completed available GUI/input acceptance and chose the narrow pattern for a separately reviewed production slice; remaining native small-window/IME/DPR scope stays explicit.

`generated-manifests/` retains the exact root-generated Studio Cargo.toml and Cargo.lock for repeatable offline builds. `evidence/` retains complete test/build results, the resize regression red/green logs, current source hashes, original source/asset manifest, and strengthened helper checks. Tracked logs replace host paths with labels; original exact local invocations remain in task-owned `.work/m11-ui/logs`.

## Root integration decision and evidence

Use app-owned session layout and a narrow wrapper around the pinned tab/resize controls. Keep the existing Bevy loop, commands, input adapter and Work schema. Do not import an upstream application, add general docking or promise persistence. The six new tests include actual controls and red/green preferred-height recovery. Independent reviews repaired idle-height clamping and bounded helper cleanup; final source/evidence audit has no unresolved finding.

The component Web bundle's first-screen gzip is20,564,901 bytes,25,705 more than the frozen accepted bundle (~0.125%). It is a separate artifact from Web profile B. No component performance improvement is claimed. Available text focus/Space guards have real egui tests on both sizes; tool typing alone does not establish physical IME, clipboard or focus-restoration acceptance.

Durable root records: [acceptance](../../docs/evidence/m1-1/ACCEPTANCE.md), [native state proof](../../docs/evidence/m1-1/ui-native-checks.json), [Web state proof](../../docs/evidence/m1-1/ui-web-checks.json), and actual native/Web screenshots there. Work revision is monotonic through Undo/Redo; the equality checks exclude only revision for history restoration and compare full JSON for reload/exchange. Experimental A/B toolbar and session controls are evaluation aids, not a production design commitment.
