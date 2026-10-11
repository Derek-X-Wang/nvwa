# Native input after manual unlock

The user manually unlocked the Mac. This checkpoint runs the same font release built and tested at `028e1b6`; every recorded source and release artifact hash was freshly checked against [the build manifest](build-manifest.json). No production code, dependency, font or release artifact changed. Hardware: Apple M2 Pro, 16 GiB, macOS 27.0.1 arm64; native Metal, ordinary window 2560×1504 screenshot pixels including title bar.

Only the task-owned native renderer ran during these input observations. The earlier Web preview tab had already been removed by the browser session. This is input acceptance, not a new performance measurement.

## Actual observations

| Case | Result | Evidence / limit |
|---|---|---|
| Restart and Pause | Passed. The real actor held idle at 1.376 s, jaw 0.53, revision6. | [Baseline](native-unlocked-before-drag.jpg). |
| Native CUA continuous drag | Attempted, unaccepted. Full screenshot coordinates `[2123,265] → [2195,265]` left jaw 0.53/revision6 unchanged and the visible pointer at the starting thumb. The distinct half-coordinate hypothesis `[1061.5,132.5] → [1097.5,132.5]` targeted the viewport and also made no edit. | [Full-pixel attempt](native-unlocked-drag-attempt.jpg), [half-coordinate attempt](native-unlocked-drag-logical-attempt.jpg). Neither establishes delivery of an actual continuous mouse sequence. No physical-input product failure is inferred. |
| Native track click and GUI Save | Passed. Clicking `[2156,265]` changed jaw 0.53 → 0.71 and revision6 → 7. Save wrote the actual Unicode work path. | [Screen](native-unlocked-click-edit.jpg), [saved JSON](native-after-click.nvwa.json). This is a click, not continuous-drag evidence. |
| One native Undo and GUI Save | Passed. One Undo restored jaw 0.53 at revision8. The whole saved document equals the published revision6 baseline, except for revision. | [Screen](native-unlocked-undo.jpg), [saved JSON](native-after-click-undo.nvwa.json), [comparison](native-click-history.log). |
| Native Redo and GUI Save | Passed. Redo restored jaw 0.71 at revision9. The whole saved document equals the edited revision7 document, except for revision. | [Screen](native-unlocked-redo.jpg), [saved JSON](native-after-click-redo.nvwa.json), [comparison](native-redo-zoom-history.log). |
| Native text focus and Space | Passed for actual CUA key events. Restart, click the file field, End, Space, `x`: both characters appeared in the field while the transport remained Pause/playing at 2.739 s and revision9. BackSpace twice removed the test suffix; no file was saved under that altered name. | [Focused playing screen](native-unlocked-space-guard.jpg). This does not exercise physical Chinese composition. |
| Native window zoom and subsequent input | Passed. The exposed macOS `zoom the window` action changed actual screenshot dimensions to 3024×1898. The actor and controls rendered. Restart/Pause, a parameter track click and one Undo remained functional (revision9 → 11). Zoom was restored to the ordinary window; GUI Save wrote revision11 with all document contents equal to revision9 except revision. | [Zoom](native-unlocked-zoom.jpg), [post-zoom input](native-unlocked-zoom-input.jpg), [restored window](native-unlocked-final.jpg), [saved JSON](native-after-zoom.nvwa.json), comparison log. This does not verify Web viewport/DPR issue3. |
| OS minimize / blur / refocus | Attempted, unaccepted. The exposed minimize-button action returned; subsequent target observations showed the window and playing/completed actor. The adapter did not expose independent focus/minimized-state evidence, so a real blur/refocus transition cannot be confirmed. | No OS focus acceptance is inferred from a successful action call or the surviving renderer. |
| Physical drag, Chinese IME, Command+A/V and cross-app focus | Passed, user-performed acceptance. Derek replied “四项都正常” to the four concrete checks. | [Physical hand-test](NATIVE-HAND-TEST.md). Root did not perform these physical steps; no physical-step JSON/revision capture or event trace is claimed. |

## Reproduce the saved-document checks

```sh
python3 scripts/verify-gui-history.py \
  --after-drag docs/evidence/input-fonts/native-after-click.nvwa.json \
  --after-undo docs/evidence/input-fonts/native-after-click-undo.nvwa.json \
  --expected-value 0.71
```

The comparator's historical `--after-drag` flag and output label describe the edit slot; this checkpoint supplies a **track-click** edit. Its whole-document/revision assertions remain unchanged, but it does not prove a continuous drag.

For redo and zoom, compare the complete saved JSON objects after removing only `revision`: revisions7,9,11 must be otherwise identical. [Checkpoint](unlocked-checkpoint.json) and [run log](native-unlocked-run.log) record artifact identity and execution separately. After the user’s hand-test, root closed the task-owned native window; session11150 returned exit0 and PID19740 was absent. [Physical acceptance and lifecycle](NATIVE-HAND-TEST.md) record the later result. No private clipboard contents, machine settings, hosted CI or paid resource was accessed.

PARTIAL — Native click edit, single Undo, Redo, GUI persistence, per-key text-focus guard and actual window zoom/recovery verified. The later user-performed native drag/Undo, IME, Command+A/V and cross-app refocus passed. Issue2 remains open for Web physical input; earlier native CUA failures remain separate observations.
