# Corrected B1 production validation

These are retained results from actual CPU, CLI, package and browser runs. Publication checks independently compared their bytes and receipts. They do not turn source review or screenshots into native application acceptance. The [file manifest](validation/MANIFEST.json) gives relative paths, byte sizes and SHA256 for every published evidence file; binaries and private orchestration receipts are excluded.

## Build and source boundary

The corrected Wasm is `cd401d198c733c91efade939b690f9e950173ba8da2bb509e53a94026384a579` (125,870,064 bytes). [Build receipt](validation/build-receipt.json), [170 selected source hashes](validation/selected-source-sha256.json), and [49 served-output hashes](validation/served-output-sha256.json) bind the retained content. All 170 selected hashes matched the product files at publication; native and Web receipts contain the same selected map. Both packaged B1 trees authenticated the manifest and all 13 files, totaling 5,725,107 raw bytes. The retained native executable and CLI hashes were independently measured against the receipt.

The repair run succeeded after 155 workspace CPU tests, native build/package, Web build and both package input checks. It was an **explicitly mutable diagnostic run**: exact red source was retained, then only `crates/nvwa-runtime/src/b1.rs` was replaced with the root-reviewed green bytes in that run's build directory. [Applied-source receipt](validation/cpu/applied.json) records red `ea8c27eb…` and green `f5edb496…`. This is selected-content evidence, **not** a complete repository/toolchain identity, immutable final-head build or reproducible-build claim. Later served Work fixtures are output files, not compiler inputs.

## CPU and offline CLI

[CPU receipt](validation/cpu/green-cpu-phase.json) and [selected actual test output](validation/cpu/workspace-test-results.log) record 155 passing tests: 49 runtime, 59 Studio and 47 core/CLI. The [actual red regression excerpt](validation/cpu/red-regression.log) records Cargo101, one failed production upload test and visible body minY−0.8167598. The expanded test subsequently passed. It checks indexed body/garment geometry, five pose anchors, torso endpoints, once-only scale and unchanged persisted stage. [Placement details](STAGE-PLACEMENT.md) distinguish these assertions from graphical observation.

The [independent CLI report](validation/cli-independent-review.md) records 36 actual retained-binary invocations across both signed parameters, all five poses, roundtrips and output-preserving failures. That report retains its older renderer/source limits; its actual CLI hash equals the newly retained CLI hash. The separate [fresh CLI receipt](validation/cli-receipt.json) records new-b1, full asset validation, parameter/pose commands and byte-equal save. Apply/save edit Work metadata; they do not authenticate assets or prove a renderer opened the result. Portable source controls have 17 methods with 28 real mutation cases, run normally and with optimized Python; they are distinct from browser evidence.

## Corrected actual Web display and commands

The [neutral view](validation/images/web-grounded-neutral.jpg) shows the full body above the floor, front visible, two display meshes and 53 bones. Pose images retain [shoulder](validation/images/web-grounded-shoulder.jpg), [elbow](validation/images/web-grounded-elbow.jpg), [knee](validation/images/web-grounded-knee.jpg), [combined](validation/images/web-grounded-combined.jpg) and [return to neutral](validation/images/web-grounded-return-neutral.jpg). These are authored fixed diagnostics, not generated or continuous motion.

[Drag](validation/images/web-grounded-torso-drag.jpg), [Undo](validation/images/web-grounded-torso-undo.jpg) and [Redo](validation/images/web-grounded-torso-redo.jpg) show torso0.50 →0.00 →0.50 at revisions6→7→8. [Both parameters](validation/images/web-grounded-both-parameters.jpg) shows torso0.50 and jaw−0.55 at revision9. This accepts the exercised controls and basic placement on this build; it does not accept clothing/appearance quality, every framing/scale condition or performance.

## Full Work exchange and preservation

Every equality below compares complete file bytes, including profile, recipe, stage and timeline. [Computed comparison receipt](validation/work-comparisons.json) lists the raw files and full hashes.

| Exercised boundary | Exact result |
| --- | --- |
| Web save → native offline CLI save → Web reopen/save | All three revision9 files equal SHA256 `129cbdd8b644b2c30912b43c36b80abd1f06b828a685ffdbae009bfa04d433e4`; torso0.50, jaw−0.55, neutral. [Reopened view](validation/images/grounded-cli-roundtrip-opened.jpg). |
| Missing B1 candidate | Revision10 combined Work before/after equals `b1b4b0c370e10f89f46d87219ec54a575e0277dc16fbaa8f555bd93796d71c75`. [Visible404 error and retained render](validation/images/grounded-warm-missing-preserved.jpg). |
| History after rejection | [Undo11](validation/images/grounded-after-reject-undo.jpg) restores neutral; [Redo12](validation/images/grounded-after-reject-redo.jpg) restores combined. |
| Corrupt B1 candidate after history | Complete revision12 Work before/after equals `bc40dccfda6ac6f74b3832b8848a3134b0e518833c3ab801ec0ca1ff02271dff`. [Visible size error and retained render](validation/images/grounded-warm-corrupt-preserved.jpg). |
| Restored source, explicit retry | Recovered revision0 file equals canonical CLI-created zero Work `91e51a4d1c8e80a01a986399ab2eeb54fc303dcf21aaa652931cff007d9538da`. [Ready zero view](validation/images/grounded-recovery-zero-ready.jpg). |
| Legacy GLB rejected B1 replacement | Complete GLB before/after equals `bca06eca06aaf8eeea04cc128fee1637be5c689dbf3ebc46b1b5e551c372bba8`; [default](validation/images/grounded-current-glb-default.jpg) and [rejected-candidate](validation/images/grounded-current-glb-rejected.jpg) views retain the original character and animation readiness. This does not mean an identical frozen animation frame. |

This is **Web ↔ offline CLI** exchange. Native GUI launch and desktop GUI ↔ Web exchange were **NOT-RUN** because the validation Mac was locked.

## Warm-cache rejection and recovery

The [raw HTTP log](validation/network/web-grounded-http.jsonl) contains URL paths/statuses, cache headers and mutation mode, with no host or query. Boundary counters are retained beside it. The same browser tab20 completed two input-only probe batches, each consuming manifest+13 inputs; [first](validation/network/grounded-cache-first.json) and [second](validation/network/grounded-cache-second.json) both record log row23, and the second reports zero additional B1 GETs. The [probe view](validation/images/grounded-cache-two-batches.jpg) explicitly says it is not the application. The earlier rows1–23 include an earlier application load: **do not attribute those14 network requests to the first probe batch**.

After warming, application load added14 fresh B1 GETs before row41. Missing mode rows42–49 then fetched through rig.game_engine.json and received404. Corrupt mode rows50–57 returned200 for that rig but the application rejected its28-byte body against the expected40,936 bytes. The screenshots and full Work equality above establish rejection and preserved state. Restoring the source and explicitly retrying added14 fresh successful GETs in rows58–71 and reached the canonical zero Work. Later rows retain GLB rejection and final successful B1 state. [Final neutral](validation/images/grounded-final-neutral.jpg) records the final display.

## Startup failure and limits

The first corrected-build navigation failed with [WebAssembly response-body loading aborted](validation/images/web-grounded-first-load-network-error.jpg). Explicit reload and later graphical navigations succeeded. A separate [HTTP-only probe](validation/network/grounded-http-wasm-probe.json) received all125,870,064 bytes and the expected Wasm hash; that probe is not rendering evidence. A real server-side [No buffer space available](validation/network/server-transport-observation.json) exception was later observed in the send path, but its output has no request timestamp. It is a transport clue, **not a proven cause** of the earlier abort. No fully cold startup or performance pass is claimed.

Final-head hosted CI and merged-main CI were **NOT-RUN at publication**. No merge claim is made. #3 remains blocked, #4 retains its measurement gaps, M2 action quality and B1 GPU4 remain HOLD. Arbitrary characters, continuous motion, appearance/cloth quality, extreme-fold normals, performance, full public-release notice closure, signing/notarization and clean-machine launch remain unaccepted. Root reported task browser/server/download cleanup; publication created no background resource.
