# Independent R1 review — experiment62 native visual subset

Reviewer: Codex Astra/high, independent read-only evidence review, except this report. This review is separate from PR81/#78 and does not revisit their source or CI.

**Decision: acceptable for bounded isolated native visual archival. No new P1/P2 findings. This is not full native appearance acceptance, a delivered user entry, or #79 mainline admission.**

## Checks performed

Read `NATIVE-VISUAL.md`, the native updates in `README.md` and `RESULTS.md`, `evidence/native-observations.json`, `native-launch.json`, and `native-build-receipt.json`. Personally opened and inspected all six original native screenshots. Independently rehashed the receipt's 206 source files, the native binary, its copied app executable, the six screenshot files, and the retained Work copy. No build, test, old Web checker/capture rerun, live GUI/GPU action, or modification of review subjects was performed.

All 206 source hashes match. `src/lib.rs` remains `7720a9957d4d58db325a038cb685629b4c03501ca48a94441af47d64c9e9232b`, the previously reviewed compiled source. Both `.work/appearance62/build-r2/native/studio` and the copied app's `Contents/MacOS/NvwaSkinPreview` are 140,831,152 bytes and SHA256 `74106adbcb1ca7fd6b61f361c967e73c04c5aa3fee17e826d3efda57519fc5c8`. The receipt itself is `c670bc3bfdfe98b4c7de8e6ed9d0bc646c1bb351514ff80acdb0c65f819cf48e`. Every screenshot SHA and byte count matches `native-observations.json`.

The retained `preview-work.nvwa.json` hashes to `92ab229ada8b521d912dab5ae85dbb439538eb262ca3a8d10dbdef93809cba77`, matching the starting Work identity. This supports unchanged disk Work at review time; it is not a native Save/persistence test.

## Actual visual evidence

- `01-plain.jpg`: ordinary Studio, revision7, torso0.75/jaw1, time0, original brown body material and blue clothes.
- `02-skin.jpg`: same visible revision, recipe, time and pose; lighter skin texture, facial features and body details are visible.
- `03-skin-paused-arm.jpg`: time2.240 and raised bent arm with visible skin, consistent with the recorded Restart/Pause operation. I reviewed the retained still and observations, not live playback; smoothness/performance are not established.
- `04-skin-refit-knee.jpg`: revision8, torso0/jaw1, time7, knee pose, shorter torso and visible skin. This supports a visible retained skin result after ordinary seek/refit, not an exact numeric UV/geometry invariant.
- `05-plain-restored.jpg`: same visible revision8/time7/recipe/pose with brown body material again. This supports visual plain restoration, not an exact material/UV handle readback.
- `06-skin-reapplied.jpg`: same visible state with skin texture again.

All six are actual nonblack character renders. The screenshots do not contain a dedicated experimental toggle, status, or not-saved panel. The changed visible appearance is evidence; writing command files and launch exit0 alone would not be. Native request acknowledgement/report/frame export was not produced and is correctly marked NOT-RUN. The historical compilation receipt's NOT-RUN launch wording describes its compilation-only checkpoint; the separate later native observation record supplies the visual evidence.

## Boundaries and reporting

`NATIVE-VISUAL.md` and the native status rows correctly confine the result to this screenshot subset. They explicitly preserve missing native report/frame export, exact UV/image and geometry before/after diagnostics, invalid-command and missing-asset recovery, dedicated experiment UI, Save/appearance identity and exchange, close-up quality, GPU readback, pixel metrics, and performance. Eyes and hair remain unrendered; cloth/M2 quality remains HOLD. The review does not transfer the old Web numerical results into a new native numerical pass.

One nonblocking wording cleanup was sent to root: the README sentence “The visible experiment label states …” and RESULTS sentence “临时皮肤明确显示 …” should explicitly say **Web**. In isolation they sound platform-wide, whereas the new native document correctly states that the native not-saved panel is absent. Likewise, the old introductory #78-pending wording should be framed as the experiment's starting context; this review does not determine #78 status. These are publication clarity issues, not P1/P2 blockers to the explicitly limited archive.

Reviewed evidence hashes:

| File | SHA256 |
|---|---|
| NATIVE-VISUAL.md | `5d05f95f66ef0322384a6c9e4b8d1295fa5f1dc5af8fc60e2f65023d8182b860` |
| evidence/native-observations.json | `d8e85051c5259073ee544497574f9042d86ed14ba493e60fb94c197b2ebcf377` |
| evidence/native-launch.json | `ab907d0ad61132c978c4525630acd6c1a75fca7be719765f2e3069d41977553a` |

**VERIFIED — compiled identity and six bounded native visual observations. PARTIAL — native full functionality/diagnostics/user entry and appearance quality/admission remain unverified.**
