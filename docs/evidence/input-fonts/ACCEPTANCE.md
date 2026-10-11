# CJK and input acceptance

This checkpoint follows PR17's merge to main `96c00de`. Hardware: Apple M2 Pro, 16 GiB, macOS 27.0.1 arm64. Native Metal and Codex IAB Chrome/155 WebGPU are the tested targets. UI input uses the actual CUA window/tab; no mock, DOM-injected Rust state or remote command bridge is used. Build, execution, input and performance results are recorded separately.

## Font contract and size

The same embedded Nvwa Sans SC Regular bytes serve Studio and Player in native/Web. Default Latin/symbol fallback remains first. The static weight-400 derivative retains the pinned variable source's complete cmap semantics and glyph order, without an additional character subset. [Provenance](../../../assets/fonts/PROVENANCE.json), OFL and notice accompany the font and both package formats. Most supplementary Han remains unsupported; representative simplified/traditional coverage does not mean every Unicode filename renders.

[Actual compression comparison](font-size-impact.json): identical unique HTML/JS/Wasm/GLB files increase from 14,183,418 to 20,497,855 gzip bytes, **+6,314,437 bytes**. Including the same shipped demo work: 20,498,378 bytes. This is a compressed file sum, not a cold-network/startup measurement; duplicate GLB requests can add 1,129,081 bytes. Standalone static font gzip is 6,303,513 versus variable 11,276,563; experiment A/B and exact reproduction are in [report](../../../experiments/06-cjk-fonts/REPORT.md).

## Build and review

Fresh full workspace tests: **59 passed, zero failed/ignored**, including two actual parser/layout/context-lifecycle font tests. [Test log](tests.log), [fmt](fmt.log), strict [native clippy](clippy-native.log), strict [Wasm clippy](clippy-wasm.log). First and second failed test attempts remain linked in [independent R1 review](REVIEW.md); their test-harness repairs preserve the full corpus and every substantive requirement.

Native and Web release builds exited 0: [native build](build-native.log), [native package](package-native.log), [Web build](build-web.log). Both actual packages contain byte-equal OFL/NOTICE/provenance files; the Web license also served successfully over the retained loopback server. Final source/artifact hashes are in [manifest](build-manifest.json). No root dependencies or Cargo.lock changed.

## Actual GUI observations

| Case | Actual result | Evidence / limit |
|---|---|---|
| Native negative-startup recovery, PR17 repaired binary | Passed. Start with missing work → error, no actor → triple-click path field and native `typeText` valid ASCII path → Open → real actor and playing idle. | [Error](native-missing-main.jpg), [recovered](native-recovered-main.jpg). This predates font integration and uses a temporary local copy of the published revision6 work. |
| Web CJK label/name | Passed. `作品 / Work` and `女娲-交换作品-最终版.nvwa.json` are actual egui glyphs beside a live character. | [Chinese screen](web-chinese.jpg). Paste is a clipboard operation, not IME composition. |
| Web Unicode save/open | Passed. Actual Save download has the Chinese basename, its whole JSON equals revision6; local Open picker reloads it and resumes real animation. | [Saved document](web-chinese-saved.nvwa.json), [reloaded screen](web-chinese-reloaded.jpg). Filename is a filesystem/browser property, not encoded in the document. |
| Web one continuous parameter drag / one Undo | Passed. Jaw 0.53 → 0.71, revision6 → 7; exactly one Undo restores the entire baseline at revision8. | [Drag](web-drag.jpg), [Undo](web-undo.jpg), both saved JSON files and [whole-document comparison](web-history.log). |
| Web keyboard focus guard | Passed for CUA key events. Restart, focus file field, press Space then `x`; text edits while transport remains Pause/playing and revision stays8. | [Playing focus screen](web-space-guard.jpg), [typed keys](web-focused-typing.jpg). Bulk `typeText` did not insert text; individual key events did. Neither is physical human typing/IME proof. |
| Native CJK label/name | Passed. Loaded a real Chinese work path, focused the field and pressed End to reveal the basename; both the filename and `作品 / Work` render beside the actual actor. | [Native Chinese screen](native-chinese.jpg). Native bulk CUA `typeText` omitted non-ASCII characters; this is separate from rendering loaded Unicode and is not IME proof. |
| Native Unicode Save/Open | Passed. Native startup loaded the actual Unicode path; GUI Save then GUI Open retained the complete revision6 work and resumed animation. | [Saved JSON](native-chinese-saved.nvwa.json), [reloaded screen](native-chinese-reloaded.jpg). The task-owned input file was first copied from the published baseline; neither GUI operation was replaced with CLI. |
| Native continuous parameter drag | Attempted, not accepted. The first CUA drag left jaw 0.53/revision6 unchanged. A second, longer attempt was blocked before input because the Mac locked. | [Before](native-before-drag.jpg), [attempt](native-drag.jpg). No physical-human defect is inferred, and no successful native drag/Undo is claimed. |
| Native clipboard / Command+A through CUA | Attempted, not accepted as physical-input verification. Chords did not select the field; paste did not replace contents. Triple-click plus `typeText` worked. | [Independent diagnosis](INPUT-DIAGNOSIS.md). Adapter event mapping/batching remains a hypothesis; no human-input defect or app crash is inferred. |
| Physical Chinese IME, physical modifier/clipboard, broader browser/OS input | NOT-RUN. | CUA paste/typeText does not exercise real composition. Issue2 remains open. |

The Mac locked during remaining native input testing. The adapter reported that it could not unlock it; manual unlock was requested. No unlock bypass or machine setting change was attempted. Native continuous drag, physical IME/clipboard/modifier input, OS blur/refocus and zoom remain unaccepted under issue2. New font-build cadence/startup/memory measurements are NOT-RUN; historical M0/M1 measurements describe their own earlier artifacts.

PARTIAL — Font rendering, Unicode GUI save/reload, packaging, 59 tests and dual release builds verified. Web drag/Undo and key-event focus guard verified. Physical input and remaining native drag/focus cases stay open.

## Reproduce

From the repository root, build with the existing handoff commands. For the native recovery case, choose a fresh nonexistent path without removing any user file:

```sh
./dist/Nvwa.app/Contents/MacOS/Nvwa --player --work "$PWD/a-new-nonexistent-work.nvwa.json"
```

Select the path field with three clicks, enter the absolute path to `docs/evidence/m1/web-sequence.nvwa.json`, and click Open. The error must clear and the actual actor/transport must appear.

For Unicode acceptance, start Studio with the published work. Enter an absolute **new writable** Unicode path, Save, and Open that file again. In Web, enter a Chinese basename, Save, then use Open to select the actual downloaded file. Compare complete documents; do not substitute an offline CLI save for GUI input evidence.

```sh
python3 scripts/verify-gui-history.py \
  --after-drag docs/evidence/input-fonts/web-after-drag.nvwa.json \
  --after-undo docs/evidence/input-fonts/web-after-undo.nvwa.json \
  --expected-value 0.71
```

Physical test follow-up for issue2: use a real Chinese input method to enter a filename while composition is visible; confirm Space selects candidates and does not pause the scene. Hold Command before/after A, then test paste with a task-owned sentinel. Exercise OS blur/refocus and zoom, then another drag and Undo. Record the method, device, steps and result. Unavailable cases stay unverified; create a reproducible product defect only when actual behavior establishes one.

[Execution status](execution-status.json) records run/exit separately: the font native GUI processes were intentionally stopped with exact-PID SIGTERM after saving work (exit143), rather than claiming graceful exit0. The pre-font Player recovery process closed normally (exit0).

Cleanup: compiler pipelines exited; task-owned native windows/processes stopped after preserving work and screenshots. Loopback9201 is retained as the user preview. No hosted CI, cloud deployment, paid API, signing, dependency upgrade or machine-wide setting change ran.
