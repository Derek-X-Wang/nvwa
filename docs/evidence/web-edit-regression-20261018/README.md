# Ordinary Web edit regression — 2026-10-18

**PARTIAL.** The original whole-body disappearance was not reproduced in this
bounded ordinary Studio session. This is one functional regression check, not a
renderer fix or a continuous-presentation/performance result. Issue #86 stays open.

The exact reused Web export has Wasm SHA256
`b911f2b3283cd1012cbb34a0ffdca90832069d912b450d8b1a65d592847177be`.
Its 237 receipt-listed non-CLI source files and complete 44-file
backend/core/runtime/Studio directories match main `1c819ea6`. This verifies the
production closure, not whole-tree equality or a fresh main compilation. The URL
was ordinary Studio, with no benchmark query or injected application commands.

| Case | Actual recorded result |
| --- | --- |
| Legacy two-parameter edits | Final r5/torso0.42; Undo r6/0.20; Redo r7/0.42. The first -0.40 edit was separately observed; the final two edits were sent together. |
| Legacy released slider | r8/0.65; one Undo r9/0.42; Redo r10/0.65. |
| Eight-parameter initial burst | Three attempted edits had no visible effect: r4/all zeros. Cause unknown. This attempt is retained, not counted as a passing burst. |
| Eight-parameter focused single edit | r5/0.42; Undo r6/0; Redo r7/0.42. Other seven values remain0. |
| Eight-parameter released slider | r8/0.65; one Undo r9/0.42; Redo r10/0.65. |
| Invalid Open | Explicit invalid_json EOF error; r10/torso0.65, current character and selected roles retained. |
| Valid recovery | r3, torso0.20/jaw0.10/head0.15/hip-0.10, remaining values0; error cleared. |
| Ordinary Save | Actual browser download is byte- and strict-JSON-identical to its input fixture, SHA256 `bee5cccde26dd235e5c3a23fe5ab715ba5bb24febdf5dbb54870dbe0e086fb4d`. |

[Single-Undo result](08-legacy-drag-undo.png), [retained no-effect attempt](11-eight-burst.png),
[invalid Open](18-invalid-open.png), [valid recovery](19-valid-recovery.png),
[Save notification](20-normal-save.png), [actual saved Work](saved-work.nvwa.json)
and [independent audit](REVIEW.md) provide the bounded evidence. All twenty
original screenshots, action receipt, source inventory and test logs remain in
the local work-product archive; eight representative screenshots are published.

Five targeted tests from the existing CPU runtime test executable passed:
latest-wins/edit-history/reload/cancel, last appearance retention, pending phase,
rejected-Open feedback and failed-fit recovery. This was a fresh CPU test run on
an existing binary, separate from the browser session and compilation.

Every saved screenshot shows the body, blue garment, skin and short hair.
Skin/Eyes/Hair are selected. Eye quality cannot be resolved in full-body framing.
The sidebar correctly limits its claim to CPU binding with presentation
unconfirmed. Sparse screenshots do not establish an absence of interruptions.

**NOT-RUN:** held-drag Escape cancellation, continuous event/presentation trace,
first-present time, worst blank interval, GPU time/memory, new native regression
or complete appearance-quality acceptance. No general post-edit time bound is
claimed. #3 stays blocked; #4 and eye/garment/generated-motion HOLDs remain.

To reproduce with an existing reviewed ordinary export, serve it on a free
reserved Nvwa port, open `/?work=works/b1-appearance.nvwa.json`, and follow the
cases above with normal toolbar/shape controls. Use a disposable Work and retain
the actual downloaded bytes. Fresh source builds use the repository's normal
desktop/Web commands; this evidence does not require diagnostic command injection.
