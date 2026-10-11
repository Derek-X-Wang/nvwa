# Live viewport input validation

Outcome: **PARTIAL**, no production sizing change adopted. Issue3 originally concerns stale input scaling during IAB viewport/DPR emulation. The currently exposed viewport capability permits width/height only; it exposes no DPR override. This session does not reproduce or explain the original DPR failure.

## Source and conditions

Source checkpoint `44b0ec3b129a1e19f5c8c3598f88de1e50e4e826`, served Wasm SHA256 `94c808dff3494647a76ccf76313368ddba64aa6e170a32c80c6e3d5bdcd72c36`. M2 Pro/16GiB/macOS27.0.1, Codex in-app Browser. Current observed DPR=1 and visual viewport scale=1. Exact installed browser engine is unknown; Chrome155 is a User-Agent observation only. One root owns all UI actions. These are input checks, not formal performance measurements.

## Actual controlled checks

| Condition | Observed canvas/viewport | Actual result |
| --- | --- | --- |
| Default hidden test surface | CSS1280x720, buffer1280x720, DPR1 | Real rig/morph/animation at revision6; click Work activates textarea; appended ASCII appears. |
| Live size1600x900 | CSS1600x900, buffer1600x900, DPR1 | Work text remains correctly aligned; caret proxy anchored inside field. Actual jaw drag0.53→0.85 produces revision7; one Undo produces revision8 and restores the complete original document except monotonic revision. |
| Live size1024x768 | CSS1024x768, buffer1024x768, DPR1 | Work can still be clicked and appended with `-small`; textarea caret CSS left439.34375/top21.5. Narrow transport labels are clipped; this is not a complete small-window usability acceptance. |
| Reset explicit override | CSS1280x720, buffer1280x720, DPR1 | Ordinary sizing restored. |
| Command+plus attempt outside text field | No measured viewport/DPR/scale change | Does not establish actual browser zoom; no blind repetition or alternate settings change. |

[Saved evidence](../../docs/evidence/viewport/) includes resized drag/Undo screens, ordinary/small input, small metrics and full saved documents. `document-comparison.json` records baseline exact equality with revision6, revisions6→7→8, and whole Undo equality except revision. No user test input or clipboard was read; only task-owned saved fixture files were compared.

A separate final PR18 review found dropped Control editing keys. The initial `ctrl+h` tool attempt left `abc` unchanged, but later event tracing proved that this API sent Meta+H. `control-h-before-fix.jpg` is retained as an invalid Control-key diagnostic, not a reproduction of the reviewed defect or a viewport bug. Actual Control events on the rebuilt release pass; see [callback acceptance](../../docs/evidence/web-input-control/ACCEPTANCE.md).

## Reproduction

1. Build and serve the release with docs/HANDOFF.md. Reuse loopback9201 if already running.
2. Open a fresh Studio with `?work=works/exchanged.nvwa.json`; leave existing user preview/input untouched.
3. Record canvas CSS/buffer, inner viewport, DPR and visual viewport dimensions with read-only DOM inspection.
4. Set live viewport1600x900 using the documented viewport capability. Click Work, type a task-owned ASCII name, Save baseline. Drag jaw once, Save, Undo once, Save. Compare whole parsed documents with revision excluded only for Undo equivalence.
5. Set1024x768, click/type Work and inspect caret geometry. Reset viewport before handoff.
6. Run `python3 experiments/11-viewport-input/compare_saved.py` against the checked-in actual documents; the script is red-capable for the saved-document invariants, but does not drive the GUI or reproduce the DPR defect.

## Remaining gate

Actual browser-tab hide/show/refocus, browser zoom, physical display scale/DPR changes, and candidate placement after real scaling are NOT-RUN. The same-browser API manages independent task surfaces; no real browser-tab transition is inferred from tab creation or binding. Need an eligible actual browser/OS surface or a physical hand-test to expand this claim. Do not ship a speculative scale workaround without a red-capable reproduction of the original boundary. Keep #2/#3 open.
