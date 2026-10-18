# Independent R1 actual native runtime delta review

**CLEAR for the bounded experiment64 temporary native appearance preview. No P1/P2 rework finding within this scope.** This supplements the earlier Web review: actual native compilation and selected native runtime evidence can now receive credit. Production quality, persistent appearance identity, authored head motion, gaze and hair physics remain unaccepted; #79 stays open.

Only this report was written during the native delta review. No Git, live UI, builds, GPU work, downloads, source changes or external writes. The root remains integration and cleanup owner; this reviewer did not independently inspect process termination.

## Build and source identity

Verified the actual app-bundle executable and the receipt's exported `native/studio` both hash to `983bf59b0e72885715a6ddb8c5c9383f5622b23ff0ee77c8166a252a74af2af7`. Compared all 203 native build-receipt source entries to the assigned checkout: only the declared noncompiled `build/serve.py` and `build/test_serve.py` differ. Rust/HTML/lock and production inputs remain identical. The public verification freeze check still passes canonical r5 `549ba3161723a92db3065fa79edd2d869dc06ea4c809558a8a2c6ef1f71303d4`.

The preserved native build log ends in a successful optimized dev build. `native-unit-tests.log` records **10 passed / 0 failed**, including actual native file ingestion invalid UTF-8/missing/recovery, full-positive weights beyond four, complete cage checks, early stream disposal, missing attachment cleanup and actual material mutation rejection. These are verified preserved build/test outputs, not tests rerun by this reviewer.

## CPU records and cross-platform evidence

Read the separate acceptance worker's matrix summary and verified SHA `63cc2760fd3e284c7c10ff33d1e6e4802aad8ae177159c55cc9749ea7a7b7880`. Verified all six matrix `EVIDENCE-HASHES.json` targets. Recomputed unique manifest coverage: **54 = 3 torso × 3 jaw × 2 clips × 3 source times**. The acceptance worker reports 54/54 public-checker passes and 54 matched native/Web comparisons. That complete numerical run is attributed to that worker; this review did not rerun all 54.

Independently loaded 12 original native collections and verified every recorded artifact and observation byte count/SHA, successful collector status, exact sender/request binding, and equality between separately retained report/frame bytes and the assembled envelope:

`n64-t0-j0-arm-s0`, `n64-t1-j1-knee-s2`, `n64-t2-j2-arm-s4`, `n64-compare-all-01`, `n64-compare-baseline-01`, `n64-compare-skin-01`, `n64-compare-restored-01`, `n64-after-reopen-01`, `n64-asset-recovered-01`, `n64-channel-recovered-02`, `n64-arm-end-01`, `n64-knee-end-02`.

Ran the unchanged public checker on the three named matrix records and `n64-channel-recovered-02`: **4/4 PASS_WITH_LIMITS**. Independently compared those three matrix cases with the matching original Web records: eyes/hair uploaded positions have zero component delta, and source/UV corner pairs and triangle indices match exactly. Also verified these three cases against all raw hashes in the separate helper manifest and its checker-result hashes.

The full matrix worker reports body position maximum difference `3.5762786865234375e-7 m`, garment `2.086162567138672e-7 m`, and maximum bone-frame component difference `4.76837158203125e-7`; eyes/hair position and UV deltas are zero. These are CPU numeric comparisons. Process-local entity handles, revisions and publication serials are not cross-platform semantic identities; command/sample binding must use actual shape/clip/source time.

## Lifecycle and recovery

- Recomputed whole `frame.snapshot` equality across all four native mode captures: **equal**, generation 1 / revision 108 / arm at source time 2. This covers core geometry, bones, transforms, sample and identities. Actual screenshot sequence baseline → skin → all agrees with mode changes.
- Raw reopen/recovery captures progress generation **1 → 2 → 3**, with different character entities and fresh eye/hair entity, mesh, material and image identities at each Open. This is actual runtime rebinding evidence, not an appearance-persistence claim.
- Ordinary native GUI Save is supported by `10-native-saved.png` and exact retained Work bytes: **2295 bytes**, SHA `ae0db372d6f4d0fc91076d98f564126b820f8f2d086f6c879535069cd9886d14`, schema3 / revision117 / torso .8 / jaw1 / knee4 seconds. Inspected the whole document: no temporary appearance or observation-camera override is persisted. The actual snapshot's .800000011920929 torso representation is consistent with the f32 runtime; saved semantic value is .8.
- `11-native-invalid-open-retains.png` visibly reports the malformed JSON Open error while the prior rendered character remains. `12-native-real-missing-asset.png` visibly reports the missing bundle manifest and retained body/garment after temporary appearance removal. The exact owned bundle manifest is restored now and hashes to `abcdbc26e03431c740c5fce98de22902089f985823a3c655db2416d042d62b18`, matching the failure receipt. Failed-interval numeric identity/freshness is not independently established by those screenshots.
- `13-native-invalid-channel.png` visibly shows Proof:error and the native invalid-UTF8 channel message. The retained proof-invalidation observation records `full_frame_file_exists:false`. `n64-channel-recovered-02` contains the exact old error bytes, then a new matching pending request, then captured report/full-frame bytes; this reviewer checked their hashes and reran the public checker successfully.
- The failed `n64-channel-recovered-01` is retained and receives **no acceptance credit**. Its r3 collector immediately rejected the unchanged prior error before the next app update. The private r4 collector hash is `fbed0bb30e0332de052b70053b1d6af1b5cad100765a98a2764b9a311dda1488`, matching the separate targeted CLEAR review. That review records 14 passing synthetic collector controls and explicitly limits waiting to byte-identical pre-send errors; unchanged errors can time out but cannot become success. This review relies on the separate collector code review and independently verifies the actual fresh recovery-02 outputs.
- Terminal arm/knee records hold source time4, completed true, playing false, with serials475/321. These prove endpoints, not smoothness or every frame of playback.

## Actual renderer observations and limits

Inspected 13 original files under `.work/appearance64/native/screenshots/`: `01-native-gui-accessories.png`, `04-native-gui-baseline.png`, `05-native-gui-skin.png`, `06-native-gui-all-restored.png`, `07-native-back.png`, `09-native-live-shape-knee.png`, `n64-arm-live-0.png`, `10-native-saved.png`, `11-native-invalid-open-retains.png`, `12-native-real-missing-asset.png`, `13-native-invalid-channel.png`, `14-native-channel-recovered.png`, and `15-native-final-face-recovered.png`. Root identifies these as actual unmodified GUI captures. This reviewer inspected the files and did not recreate the capture session.

The native screenshots visibly show textured skin, eyes and hair, mode restoration, a held rear view, active arm motion at **1.6997**, and bent knee motion with torso **.8** at **2.3146**. The latter screenshot displays **Pause**, consistent with active playback. The before/after edit sequence itself remains root-observed; a still image cannot independently establish the user's exact interaction timing.

The matrix has **54 CPU records**, not 54 pixel captures. Root retained the first arm neutral view plus nine held knee peaks and additional representative views. No GPU buffer readback, sustained FPS measurement, temporal smoothness acceptance or all-frame visual coverage is claimed.

Visible quality limitations remain: eye/eyelid fit needs judgment; the hairline has cutout edges; the rear crown shows broad light facets/strips. Native and Web numerical agreement cannot establish realistic shading or MPFB shader parity. Finite/unit-normal evidence does not establish smoothing or tangent parity. Current clips do not establish head-driven deformation, gaze, or hair physics.

The expanded native experiment window plainly says **“Temporary preview. Work saves shape and motion only.”** Its collapsed title visibly truncates the not-saved tail. This is a known prototype communication limit, not a persistent-label success claim or production UI admission. Several face-mode captures also have imperfect framing/overlay occlusion; the final recovered face is inspectable but still partially covered by the panel.

VERIFIED — exact native binary/source identity, preserved successful native build and 10 Rust controls, 54-case manifest coverage, 12 raw collection provenance samples, four actual public-checker reruns, three native/Web accessory comparisons, four-mode whole-core equality, native saved bytes, real failure/recovery evidence and 13 original screenshot inspections. PARTIAL — full54 numerical results are the separate acceptance worker's run; visual evidence is selected stills, not a fresh live reviewer run. Production appearance quality/persistence, authored head motion/gaze/hair physics, GPU readback and formal performance remain NOT-RUN. #79 remains open; #3 blocked, #4 gap and clothing/M2 HOLD are unchanged.
