# Native physical input acceptance

Recorded at 2026-10-11 06:51:36 UTC (2026-10-10 PDT). Derek performed the four requested checks in the native Nvwa window and replied **“四项都正常”** (“all four are normal”). This is user-performed physical acceptance, distinct from root's earlier CUA observations and the isolated dependency replay.

The window used the unchanged CJK release from `028e1b6`, Apple M2 Pro, 16 GiB, macOS 27.0.1 arm64, native Metal. Before the hand-test, jaw width was 0.71; root's baseline screenshot and saved document are in [unlocked acceptance](UNLOCKED-ACCEPTANCE.md). The hand-test did not supply a new saved-document/revision pair or screenshots; no physical-step whole-document equality is inferred.

| Requested physical check | User-reported result | Evidence boundary |
|---|---|---|
| Continuously drag jaw width, release, then click Undo once; return to 0.71 | Passed | Confirms the requested drag/one-Undo behavior. No frame/event trace or revision count was collected. |
| Enter `女娲` with a real Chinese input method in the work-path field; candidate selection works | Passed | The exact input-method name was not supplied. No exhaustive composition/shortcut matrix is claimed. |
| Command+A and Command+V work in the path field | Passed | Basic physical select-all/paste accepted. No clipboard content was read or published; same-frame event timing was not measured. |
| Switch to another application and return; editing still works | Passed | Basic physical cross-app blur/refocus accepted. No other application identity or OS event trace was collected. |

The requested procedure explicitly said not to click Save/Open after entering test text. Root did not save that text or inspect the field/clipboard contents. Existing CUA Save/Open and full-document checks remain separate evidence.

## Remaining scope and diagnosis

These four results supersede the pending **native physical** cases in issue2. Earlier CUA drag/Command/Unicode-entry failures remain recorded as adapter observations; they are not physical product defects. The [same-frame Command replay](../../../experiments/07-native-input-events/REPORT.md) still demonstrates a dependency-layer conditional behavior. Ordinary physical Command input passing does not establish its OS event sequence or invalidate that replay. No production workaround or dependency change was added.

Web physical continuous typing, Chinese composition and physical clipboard/focus checks are still NOT-RUN. Root opened the same release in the Codex in-app Browser with the published revision6 work and confirmed the live actor. [The ready screen](web-human-test-ready.jpg) shows actual screenshot pixels; no viewport/DPR emulation was applied. The visible tab is retained for the requested three Web hand-test checks; no result is inferred. Browser/DPR coverage remains separate under issue3. Issue2 remains open for the Web scope.

The task-owned run log contains `error messaging the mach port for IMKCFRunLoopWakeUpReliable` during the hand-test. [The raw log](native-unlocked-run.log) is preserved. The cause is uninvestigated; the user reported no functional failure in the four checks. It is not silently removed or declared harmless.

After the hand-test, root used the exposed native window close button. Execution session11150 returned **exit0**; exact PID19740 no longer existed. No replacement application was launched. The existing loopback9201 preview server remains available. No new build or test run was required for this evidence-only update.

VERIFIED — User-performed native drag/Undo, Chinese candidate input, Command+A/V and cross-app refocus passed; normal native close exited0.

PARTIAL — Issue2's native checks have acceptance evidence; remaining Web physical input is unverified. Full event timing, composition coverage and the logged IMK diagnostic cause remain unverified.
