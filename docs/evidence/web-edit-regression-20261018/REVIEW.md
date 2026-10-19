# #86 ordinary Web evidence audit

Read-only audit of all twenty saved PNGs, the private action receipt, the private Save verification receipt, the actual saved download copy and its recovery fixture. Only this review file was written. No UI, server, build or native action occurred during the audit.

## Conclusions and findings

No contradiction was found between the screenshot states and the bounded final claims in `observations.json`. The eight-parameter initial attempted burst **did not land visibly**: `11-eight-burst.png` is revision4 with torso0.00 and all other values0.00. The later focused single edit is a separate successful case. Do not report a successful eight-parameter three-edit burst or replace the no-effect result with that single edit. Cause remains unknown; screenshots do not establish whether the intended input reached the application, so this is an unresolved attempted-input result rather than an attributed runtime regression.

The legacy three-edit burst ends at r5/0.42, and Undo restores0.20 at r6. Root reports separately observing its first -0.40 edit at r3. That first intermediate observation is not among these twenty PNGs; this audit independently confirms the final burst and Undo/Redo screenshots, not the separately reported first intermediate view.

Both backends show the expected post-release +0.65 endpoint and a single Undo back to +0.42, followed by Redo to +0.65. These screenshots support end-release/history behavior. They do not show the held-drag interval, pointer path or cancellation. Held-Escape remains NOT-RUN.

## Screenshot-state checks

All twenty screenshots show a present full character/body, blue garment, visible skin rendering and short dark hair. Skin/Eyes/Hair checkboxes are selected in all captures. Eye selection is visible, but eye appearance/quality cannot be resolved at this full-body framing. No eye quality or continuous-role presentation claim is supported. All captures show paused0.00, two finite4s actions and scale1.00. The sidebar explicitly says `CPU body + requested appearance bound · presentation unconfirmed`; the audit does not upgrade it to verified GPU presentation.

| PNGs | Independently visible state |
| --- | --- |
| 01 | Legacy v1 profile, r2, torso0.00/jaw0.00. |
| 02–03 | Legacy r5, torso0.42/jaw0.00. The two files are byte-identical; they contain the same visible state. |
| 04–05 | Legacy Undo r6, torso0.20/jaw0.00. These two files are also byte-identical. |
| 06 | Legacy Redo r7, torso0.42. |
| 07–09 | Legacy drag release r8/0.65; Undo r9/0.42; Redo r10/0.65. Jaw0.00 remains. |
| 10 | Eight-parameter v2 profile, r4, all eight parameters0.00. |
| 11 | Attempted eight-parameter burst retained r4/all zeros; no visible committed edit. |
| 12–14 | Focused single edit r5/torso0.42; Undo r6/0.00; Redo r7/0.42. Other seven values0.00. |
| 15–17 | Eight-parameter drag release r8/0.65; Undo r9/0.42; Redo r10/0.65. Other seven values0.00. |
| 18 | Invalid Open: red `invalid_json: EOF while parsing a value at line 1 column 18`; r10/torso0.65 and other seven zeros remain visible, with character and selected roles retained. |
| 19 | Valid recovery: r3, torso0.20, jaw0.10, head0.15, hip-0.10, remaining four values0.00; invalid-input error cleared, all roles selected. |
| 20 | Same recovery r3/values; green `下载已开始 / Download started` and browser-download instruction visible. |

## Actual Save verification

Independently read the retained actual-download copy at `saved-work.nvwa.json` and the exact input fixture. Parsed both with duplicate-key rejection and nonfinite-number rejection. Both strict JSON objects and complete raw bytes are equal. Both SHA-256 values are:

`bee5cccde26dd235e5c3a23fe5ab715ba5bb24febdf5dbb54870dbe0e086fb4d`

Revision3, entire profile/backend, all eight parameter values, scale, diagnostic pose, all three appearance role booleans and identity, complete stage and timeline match. This independently agrees with the private Save verification receipt. The screenshot notice proves download initiation; the separately inspected retained download bytes prove the saved content. Download provenance is root's recorded browser-download capture, not independently re-observed browser activity in this audit.

## Limits retained

- Root records ordinary Studio/no benchmark/no injected commands. The canvas-only PNGs do not show the URL or input-event trace, so those provenance details rely on root's execution receipt and the earlier exact-export identity verification.
- Do not claim the original ten-step plan passed unchanged: eight-parameter burst was a preserved no-effect attempt; focused single edit was substituted; Escape during held drag was unavailable.
- Later paired screenshots exist only for the legacy burst and its first Undo in this packet. Do not claim every action received a later no-action screenshot or that a general recovery-time bound was established. Timestamp fields are sparse and do not identify exact GPU publication.
- No first-present, flicker-free, continuous GPU presentation, maximum blank interval or performance claim. Whole-body disappearance is not visible in these sparse captures and its original route/cause remains unreproduced.
- Eye, garment and overall appearance quality acceptance, generated-motion quality, #3 blocked and #4 measurement gaps remain outside this evidence.

**PARTIAL — all twenty recorded screenshot states and exact saved Work verified; eight-parameter burst result remains no-effect/unknown cause, and held-cancel/continuous presentation/time bounds are not established.**
