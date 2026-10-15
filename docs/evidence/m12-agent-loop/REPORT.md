# M1.2 — Real agent Work reload and continued GUI editing

The exact agent-created Work loads and plays in native Studio and Web Studio. Both interfaces accept one further jaw edit, save the complete Work, undo that edit, save the restored Work, and reopen it. Native and Web saved outputs are byte-identical at each accepted edit/undo stage. Both Players also play the same original nine-second Work and restore the held sequence after a real character-triggered wave.

This is actual functional acceptance on the retained `bf6a834fa0eddf05cc15c4215ae3febe1bcdeb0e` GUI artifact cohort. It is not a new GUI build or a performance result.

| Stage | Native | Web |
|---|---|---|
| Open exact original Work | Revision 2, real skin/morph/motion | Revision 2, real WebGPU character; first Save byte-identical to input |
| Pause/seek authored wave | 4.5 seconds, `agent-wave` | 4.5 seconds, `agent-wave` |
| One jaw pointer edit | `.42 → .71`, revision 3 | `.42 → .71`, revision 3 |
| Save entire edited Work | Passed whole-document comparison | Same bytes as native edited Work |
| One Undo and Save | Jaw `.42`, revision 4 | Same bytes as native restored Work |
| Reopen saved Work | Actual Open path; revision 4 and playback restored | Actual file chooser; revision 4 and playback restored; subsequent Save matches restored bytes |
| Player character interaction | Chest click waves; held idle cursor 2.0 seconds restored paused | Head click waves; held idle cursor 2.0 seconds restored paused |

Native accepted edit: [actual screenshot](native-jaw-edited.png). Web accepted edit: [actual screenshot crop](web-jaw-edited-crop.png). Native reopen: [actual screenshot](native-reloaded.png). Web reopen: [actual screenshot crop](web-reloaded-crop.png). Player before/busy/restored images are retained separately for each platform.

## Exact input and complete-document checks

The input came from the real agent CLI run at `/Users/derekxwang/.codex/worktrees/m12-agent-cli/nvwa/experiments/38-agent-cli/agent-nine-second.nvwa.json`. Its exact bytes are retained as [agent-input.nvwa.json](agent-input.nvwa.json), SHA-256 `e33356b490cb8d6c01118958c3d22409f4546cfa6164a7d69d496be292eb25cc`.

It starts at revision 2, with jaw width `.42`, smile `.2`, nose/shoulder `0`, and scale `1`. The original profile is embedded in full. Its authored timeline contains `agent-idle` 0–3 seconds, `agent-wave` 3–6 seconds, and `agent-turn` 6–9 seconds, all nonlooping. Speeds remain exactly `1.013889`, `1.013889`, and `1.3472222` in the serialized Work.

`verify.py` compares each entire decoded document against an expected clone of the original. It changes only the explicitly expected revision and jaw value. This compares every profile field, asset hash, clip specification, character field, parameter, entry ID, timeline order, start/duration/speed/looping value, and schema field. A screenshot or renderer log is not used in place of that comparison.

| Saved document state | SHA-256 |
|---|---|
| Original and Web initial export, revision 2 | `e33356b490cb8d6c01118958c3d22409f4546cfa6164a7d69d496be292eb25cc` |
| Native and Web edited, revision 3 / jaw `.71` | `795c184c58cd3a86ec2d4045ce047d7a31d51f8c5af6018406acf9f41e32e54e` |
| Native and Web undone, revision 4 / jaw `.42`; Web reload-save | `9aa3e14c53915fd04d6072d204ffd945fc1edbbab071c0455660d8549badb446` |

Actual JSON outputs are `native-edited.nvwa.json`, `native-undone.nvwa.json`, `web-initial-saved.nvwa.json`, `web-edited.nvwa.json`, `web-undone.nvwa.json`, and `web-reloaded-saved.nvwa.json`. `verification.json` retains all seven complete-document comparisons, including one harmless extra initial export. The accepted revision progression is 2 → 3 → 4 on both platforms. Undo restores content while preserving monotonic revision.

## Artifact and source proof

Before launch, actual artifact bytes were checked against [the retained build identity record](../m1-1-final/build/artifact-identities.json). Every selected Studio/runtime/core source, root Cargo manifest/lock/toolchain, Web bootstrap, profile, fixture, and font was checked against [the build input manifest](../m1-1-final/build/build-inputs-after-lint-fix.json). All selected hashes matched; the per-file expected and actual hashes are retained in `input-identities.json`.

| Actual GUI artifact | SHA-256 |
|---|---|
| Native `dist/Nvwa.app/Contents/MacOS/Nvwa` | `72d3df8cfdeea062282c8731b0a95cb971f90976fe881772f3e3c24afe76973a` |
| Web `nvwa_studio_bg.wasm` | `d890dfee73e9eeeee6ce3d82f255c79979e8c8b6bed90243c6101f8e1c1763a8` |
| Web `nvwa_studio.js` | `9ff532cbedc6a814c4b8337c4b82f436de452e7b7fbc8c9e58bfda2e90ad6c5c` |

The app and Web files were copied into `.work/m12-gui/`; the published `dist` trees and original fixture were not changed. CLI-only changes in the separate agent worktree do not change the verified GUI/core/runtime input set. No native, shader, or Wasm compilation was needed or run.

Two native `NVWA_EVIDENCE` receipts report release mode, `ready:true`, `error:null`, revision 2, three timeline entries, 18 joints, nine meshes/skins, four morph weights, and one active real animation. They identify Metal on Apple M2 Pro and a 1280×720 physical benchmark surface. The actual UI screenshots independently show those loaded character counts and subsequent edits. Incidental timing fields in these raw receipts are not benchmark results.

The Web acceptance used the ordinary responsive Web build. The loaded page visibly reports Ready, 18 joints, nine meshes/skins, four morphs, and one active player, and displays real motion and deformation. Native Chrome CUA supplied the observation and input. Browser console, Web adapter diagnostics, and GPU timestamps were not inspected. `web-http.log` records actual delivery of the exact JS/Wasm, Work, and GLB. Optional `.glb.meta` lookups returned 404; the fixture itself returned 200 and reached Ready. No fallback renderer is claimed.

## Actual UI and file boundaries

This worker revalidated its own native CUA tools and target. A supported fresh IAB creation failed with `Browser is not available: iab`. The native Chrome app was available, so the Web work used a fresh owned tab there through CUA. No CDP, Playwright side channel, OS scripting, secret storage, or unrelated browser state was used to operate the page. No new browser permission prompt occurred.

The Web file picker was opened by Studio's actual Open button. Its native Go to Folder field selected the owned `web-undone.nvwa.json`, and the chooser preview showed the exact revision-4 JSON. Clicking Open reloaded the actual file. A new real Save then exported the same complete restored bytes. This was not a static URL swap used as a substitute for manual reload.

An early native numeric-text jaw attempt committed once per keystroke, producing revision 5 / jaw `.7`. That full saved attempt is preserved as `native-typing-attempt-rev5.nvwa.json`. It is not counted as the accepted one-edit cycle. The exact original was recopied only to its private task-owned path, and GUI Open restored revision 2 before the successful pointer edit. Transport coordinates were reobserved after Pause changed button widths. Failed focus/coordinate attempts are described in [UI-REPLAY.md](UI-REPLAY.md), not counted as successful actions.

Native Chrome CUA screenshots include white padding outside the visible window and require twice the visible-content coordinates for input. The returned screenshot bytes are preserved unchanged. File-signature inspection found 20 JPEG-encoded raw CUA captures with legacy `.png` filenames and 13 actual PNG files: two renderer captures and 11 convenience crops. The filename extensions do not identify the raw CUA encoding correctly. [screenshot-formats.json](screenshot-formats.json) records every filename and actual format. No raw capture was transcoded or renamed. `*-crop.png` convenience images remove only the white padding, without changing the rendered scene. The Chrome window was temporarily zoomed through its exposed window action to expose controls, then restored. No browser zoom/DPR emulation, scaling acceptance, IME, clipboard, drag atomicity, startup latency, first-frame, memory, or GPU performance claim follows from these runs.

All downloaded files were new owned exports of project data. They were identified by exact filename and full content, then moved from Downloads into this evidence directory. Unrelated files were untouched. The native original agent Work, public fixture, old experiments, and frozen experiment 40 evidence remain unchanged.

## Replay, cleanup, and limits

[UI-REPLAY.md](UI-REPLAY.md) records material actual CUA calls and the corresponding screenshots/JSON outputs. [lifecycle.json](lifecycle.json) records exact owned process/session IDs and tab closure. Native Studio PID 15523 and Player PID 20383 were stopped/reaped before Web started. The private 127.0.0.1:9201 server PID 21854 was stopped/reaped; the port was then verified free. The sole owned Chrome tab was closed, the prior New Tab preserved, and the prior window zoom restored. The GPU/UI token was returned before CPU-only reporting.

Recheck the saved documents and native receipts without starting a renderer:

```sh
python3 -B docs/evidence/m12-agent-loop/verify.py
```

`SHA256SUMS.json` records all retained files except itself. The exact source/artifact proof remains in `input-identities.json`. `verification.json` records the complete-document results. The original app/Web artifact cohort remains reusable for replay only while its source and byte identities are rechecked.

VERIFIED — Actual native/Web reload, one pointer edit and one Undo with complete saved-Work comparisons; real nine-second Player playback and character-wave restoration on both platforms. NOT-RUN — New compilation, browser-console diagnostics, performance, and broader input-method acceptance.
