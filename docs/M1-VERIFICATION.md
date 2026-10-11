# Thin M1 verification checkpoint

Evidence recorded 2026-10-11 UTC for the thin M1 work on `feat/thin-m1`. This is an evidence register, not a full source-correctness review.

| Issue | Checkpoint status | Evidence boundary |
| --- | --- | --- |
| [#14 Compose and exchange a three-action work](https://github.com/Derek-X-Wang/nvwa/issues/14) | Complete for the documented sequence and exchange acceptance | Actual native and Web GUI runs with the fixture GLB, 41 workspace tests, and native/Web development builds passed. Final 57-test checks and release evidence are recorded below. |
| [#15 Character-click interaction](https://github.com/Derek-X-Wang/nvwa/issues/15) | Completed in native/Web dev builds | [Actual hit, restore and unchanged document](evidence/m1/interaction-acceptance.md),48 tests and independent R2 repair acceptance. |
| [#16 Static Player](https://github.com/Derek-X-Wang/nvwa/issues/16) | Complete for documented local acceptance | Native/Web release runs, finite transport, click restore, static subdirectory, negative Web responses and timeout recovery; one extra native negative-startup GUI recovery remains a hand-test gap. |

## #14 actual GUI and file exchange

The native GUI loaded the actual fixture GLB with 9 meshes, 9 skins, 18 joints, and 4 morph targets. Creating the sequence produced idle 0–3s, wave 3–6s, and turn 6–9s. Playback reached 9s, stopped, and held the turn pose. A paused seek to 4.6s showed the raised-arm wave pose. The recorded native GUI evidence is [sequence complete](evidence/m1/native-sequence-complete.png), [paused wave pose](evidence/m1/native-wave-paused.png), and [native save](evidence/m1/native-save.png).

The accepted native 5 → Web 6 → fresh native 6 exchange was:

| Step | Observed result | Evidence |
| --- | --- | --- |
| Native save | Revision 5; `smile = 0.34`; segments idle 0–3.5s, wave 3.5–6.5s, turn 6.5–9.5s. | [Native work](evidence/m1/native-sequence.nvwa.json), [native save screen](evidence/m1/native-save.png) |
| Web import and edit | Web opened that saved file. One real slider drag set `jaw_width = 0.53` in one edit and advanced to revision 6. Web downloaded the result. | [Web screen](evidence/m1/web-wave-edited.png), [Web download](evidence/m1/web-sequence.nvwa.json) |
| Fresh native reopen and save | A new native process reopened the Web file with both morph values, all three spans, and revision 6. Its re-save matched the entire Web download JSON. | [Reopened native screen](evidence/m1/native-web-reopened.png), [native round-trip file](evidence/m1/native-roundtrip.nvwa.json) |

The native and Web screenshots document GUI observations. The JSON files document portable data equality. Together they support the stated exchange result; they do not establish Player behavior or character-click interaction.

## Automated and build evidence

The [test log](evidence/m1/sequence-tests.log) records 41 passing workspace tests. The acceptance record identifies actual Bevy animation-graph/joint transport tests and actual CLI-binary apply, validate, and save coverage. The [native build log](evidence/m1/sequence-native-build.log) and [Web build log](evidence/m1/sequence-web-build.log) record passing development builds. These are development builds, not final release builds.

The [sequence review record](evidence/m1/review-sequence.md) says an independent cross-model R2 review accepted the repaired pause path with no new findings, followed by the 41-test rerun and GUI exchange acceptance. This is scoped review evidence; it is not a full application correctness review.

## Not yet verified

- Full hotspot containment across every pose/morph extreme; current scope is conservative original-fixture chest/head targets.
- Broader platform/browser coverage and the M0 hand-test scope.

## Existing M0 issues remain separate

These 13 known M0 limitations remain tracked independently. The M1 evidence above does not close them, and the issue index says they do not all gate thin M1.

- [#1 CJK font rendering](https://github.com/Derek-X-Wang/nvwa/issues/1)
- [#2 Native/Web text, drag, clipboard, and focus hand tests](https://github.com/Derek-X-Wang/nvwa/issues/2)
- [#3 IAB viewport/DPR input scaling](https://github.com/Derek-X-Wang/nvwa/issues/3)
- [#4 First presentation, cold Web startup, and GPU/browser memory measurements](https://github.com/Derek-X-Wang/nvwa/issues/4)
- [#5 Screenshot export persistence in embedded browsers](https://github.com/Derek-X-Wang/nvwa/issues/5)
- [#6 Duplicate GLB transfers](https://github.com/Derek-X-Wang/nvwa/issues/6)
- [#7 Blender fixture export byte drift](https://github.com/Derek-X-Wang/nvwa/issues/7)
- [#8 Editing-history and command-retry memory bounds](https://github.com/Derek-X-Wang/nvwa/issues/8)
- [#9 Additional native platforms and WebGPU browsers](https://github.com/Derek-X-Wang/nvwa/issues/9)
- [#10 Dependency notices and signed distribution validation](https://github.com/Derek-X-Wang/nvwa/issues/10)
- [#11 Humanoid hand shape and skin weighting](https://github.com/Derek-X-Wang/nvwa/issues/11)
- [#12 Genuine local AI motion readiness and output compatibility](https://github.com/Derek-X-Wang/nvwa/issues/12)
- [#13 Controlled retarget derivative visual verification](https://github.com/Derek-X-Wang/nvwa/issues/13)

## #15 actual interaction

See [actual acceptance](evidence/m1/interaction-acceptance.md), [48-test repaired run](evidence/m1/interaction-tests-final.log) and [independent review](evidence/m1/review-interaction.md). Native paused2.815 and Web paused0.104 returned exactly after real wave. Web running cursor0.303 resumed to turn8.105. Both real post-interaction saved files equal the entire pre-interaction revision6 document. [CLI reproduction](evidence/m1/cli-gui-equivalence.md) also equals the GUI exchange document.

## Final thin M1 checkpoint

[Player acceptance](evidence/m1/player-acceptance.md) distinguishes compiled, native-ran, Web-ran, validated and measured claims. Final source: **57 tests passed**, core13/CLI6/runtime21/Studio-platform17; zero failed/ignored. [Native](evidence/m1/player-native-clippy-complete.log) and [Wasm](evidence/m1/player-wasm-clippy-complete.log) strict clippy and [fmt](evidence/m1/player-fmt.log) passed. Both [native](evidence/m1/player-native-release-build-complete.log) and [Web](evidence/m1/player-web-release-build-complete.log) final release builds passed. Fresh cross-model R2 review accepted sequence, interaction and Player, including targeted repairs; review logs are in evidence/m1.

Actual Player: packaged macOS app copied and launched from /tmp, native pause/seek/head click/exact5.3s restoration/Open of Web6, missing-work error with no fixture fallback; static Web direct load/refresh/subdirectory, pause/chest click/exact4.966s restoration, HTTP404/JSON/UTF8/oversize/redirect/hash/missingGLB errors, 30-second stalled-body abort and actual manual recovery. A fresh final native measurement process reopened revision6 directly.

Formal physical1280×720,600recent samples, one actor, no competing task-owned heavy jobs: native cadence p50/p95=8.327/8.924ms,RSS~229.5MiB; Web8.300/9.500ms. Both finite9.5s works had completed and held the final pose. This is not GPU timing or continuous-animation measurement. Unique gzip total for the measured work=14,179,929bytes; duplicate GLB requests remain #6. [Exact source/artifact hashes](evidence/m1/build-manifest.json) preserve the final release identity; the older M0 manifest remains unchanged.

**NOT-RUN:** native negative-startup manual-recovery GUI check could not finish because the desktop automation adapter lost its window binding while the process stayed alive. This is separate from successful normal native Open, actual Web recovery and headless native recovery. It is recorded under #2. Public hosting, signing/notarization, other OS/browsers, full hotspot containment across all poses/scales, cold Web/first presentation, browser/GPU memory and true model inference remain unverified.

PARTIAL — Thin M1 local function/release acceptance,57tests,dual-target strict checks and actual cadence measurements verified; the listed hand-test/platform/measurement scope remains open.
