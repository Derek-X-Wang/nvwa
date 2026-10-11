# M1 sequence actual acceptance

Source: uncommitted feat/thin-m1 on M0 d74493d. 2026-10-11 UTC. Debug/dev builds, macOS arm64 native Metal and Codex IAB WebGPU. This is slice #14 acceptance, not final release/performance proof.

- Native: actual 9-mesh/9-skin/18-joint/4-morph GLB loaded. Create 9s sequence produced idle0–3, wave3–6, turn6–9. Actual playback reached9s, stopped and held the turned pose. Paused seek4.6s displayed raised-arm wave pose.
- Native: smile0.34, first-segment+0.5s, Undo and Redo produced revision5, contiguous spans0–3.5/3.5–6.5/6.5–9.5. Saved native-sequence.nvwa.json.
- Web: imported that saved file through real chooser; revision5, smile0.34, all three9.5s spans present. Paused seek4.6s displayed real raised-arm pose. Real slider drag set jaw_width0.53 in one edit, revision6. Real download saved web-sequence.nvwa.json.
- Entire Web document equals Native document plus the one jaw edit/revision. New native process reopened Web work with both morphs, all three spans and revision6. Native re-save is entire-JSON-equal to Web download.
- 41 workspace tests passed, including actual Bevy graph/joint transport tests and actual CLI binary apply/validate/save. Native and Web dev builds passed.
- Independent cross-model R2 accepted the pause repair. Release builds, final Player/interaction and final M1 measurements remain later stages. Native continuous drag, IME and broader browser/OS coverage remain tracked known limitations.

Evidence: native-sequence-complete.png, native-wave-paused.png, native-save.png, web-wave-edited.png, native-web-reopened.png; three JSON files; sequence-tests.log, sequence-native-build.log and sequence-web-build.log.
