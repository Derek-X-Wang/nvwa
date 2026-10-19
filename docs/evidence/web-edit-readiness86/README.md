# B1 Web edit readiness evidence

Partial correction for [issue 86](https://github.com/Derek-X-Wang/nvwa/issues/86), based on `f0572e5f620da8ed31898e2d8165f7472b689837`. Keep the issue open. The demonstrated stale phase and appearance disposal paths are corrected at the shared CPU runtime boundary. Entirely absent rendered bodies, first present and GPU continuity remain separate unresolved questions.

## Correction and scope

A requested shape that is not yet published no longer leaves the previous Ready phase visible. Preparation, cancellation and rejection have explicit feedback. Successful B1 feedback identifies CPU body and appearance binding and says that presentation is unconfirmed.

While a shape candidate is pending, the last validated CPU body can retain its skin, eyes and hair. The existing appearance stream still checks the actual generation, body, mesh, material, image and accessory bindings. The strict requested-frame guard is unchanged. Retained resources are never returned as current or applied appearance evidence: `AppearanceStatus.ready=false`, `applied=None`, and `retained=true` describe this state. A pending snapshot refuses current evidence without stripping that valid display.

Actual material, image or structural failures still invalidate bindings. A shared projection updates readiness, errors and phase at both scheduled-update and snapshot boundaries, so disposed appearance cannot keep a retained or bound caption. A real retained-binding error remains visible while preparation continues, including after resource disposal. A candidate timeout keeps its error and the last valid display; cancellation can return to the already published selection. Open still keeps its candidate outside committed Work/history until successful publication. During Open, appearance readiness can describe the still-current committed Work while the phase separately identifies candidate preparation.

No Work schema, profile/base/appearance identity, command, save, history, source authentication, material policy, geometry, influence count, quality gate or dependency changes are included. None appearance remains a valid brown baseline.

## Red and green evidence

All regressions use the production B1 plugin, shipped authenticated raw inputs, actual CPU mesh/material/image resources and production controller/snapshot functions. Time is pinned for ordinary edits. Timeout tests advance the real production timeout clock by 31 seconds.

```sh
cargo test -p nvwa-runtime --locked --offline issue86_ -- --test-threads=1
cargo test -p nvwa-runtime --locked --offline -- --test-threads=1
```

Local runs use one compiler job and a dedicated target. The cold frozen baseline and the later stable live checkout builds have separate targets. Live runs use an absolute manifest path and byte-identical source/asset inventories before and after each run. A wefty frozen snapshot identifier is not substituted for that live source identity. Full logs, source inventories and failed runs remain under the local ignored `.work/issue86/` directory.

| Probe | Result | Meaning |
| --- | --- | --- |
| Frozen unchanged baseline, two original regressions | 0 passed, 2 failed; 4.06 seconds of tests | Pending requested shape retained Ready text and changed the skin material to baseline brown. Cold compilation is separate from test duration. |
| Phase-only correction | 2 passed, 3 failed; 35.31 seconds | Phase regression passed while retained skin still failed. Settled legacy/new lifecycle matrix passed. Label correction alone did not preserve appearance. |
| Retention and binding negatives | 6 passed; 36.77 seconds | Retained resources, timeout/cancel recovery and actual material/pixel corruption checks passed. |
| Feedback and retention focused run | 8 passed; 38.03 seconds | Also rejects old runtime readiness when snapshot runs before drive, and removes Preparing feedback after cancelled/rejected Open. |
| Advancing playback pending shape | 1 passed; 2.26 seconds | Positive elapsed time holds all 53 bones, both body/garment buffers, frame serial and cursor; retained role readback stays coherent, then cancellation resumes actual geometry updates. |
| Full runtime suite before atomic phase correction | 83 passed; 127.90 seconds | Includes existing structure, authentication, generation fencing, transport, recovery, stage and GLB tests. |
| Atomic snapshot phase correction | 8 passed and 2 failed before correction; 10 passed after correction in 42.28 seconds | Immediate pending and settled snapshot errors update the phase at the rejection boundary; a real candidate timeout keeps its specific error and phase. |
| Full runtime suite after atomic phase correction | 84 passed; 130.43 seconds | Source and asset inventories match before/after the run. |
| Before-drive B1 to GLB snapshot refusal | 0 passed and 1 failed before correction; 11 focused tests passed after correction in 45.00 seconds | A real `request_open(original())` replacement followed by an immediate refused snapshot clears previous runtime readiness. Scheduled GLB pending handling is unchanged. |

The matched lifecycle test uses the same stage and paused frame for legacy two-parameter and new eight-parameter Works: torso 0 to 0.42, commit, Undo, Redo, exact save/reopen, preview cancellation, then rapid -0.4 to 0.2 latest-wins. It verifies actual uploaded geometry changes/recovery, all selected roles and exact saved Work identity. It does not measure rendering or active-playback presentation continuity. A separate full-schedule test starts playback, advances by 0.25 seconds, then advances by another 0.25 seconds with a pending shape. `update_motion_transport` refuses to advance a noncurrent shape and `animate_active` skips it. The test proves that the old CPU frame is held as a whole, verifies retained appearance against its actual bones, and verifies that cancelling the preview resumes playback with changed uploaded positions.

An added timeout feedback test first failed because its first Bevy time update had zero delta. The failed run is retained. The setup now seeds a zero-time tick, as the existing production timeout regression does, and asserts the later delta is exactly 31 seconds. The production timeout and its failure assertions are unchanged.

## Remaining body handoff investigation

The separate read-only source trace confirms that B1 creates replacement CPU mesh/material handles and retires old display entities without a render acknowledgement. Bevy 0.19.1 performs asset extraction, visibility, render preparation, queueing and drawing separately. This is a missing continuity guarantee, not a demonstrated cause of a presented blank frame. In particular, Bevy ignores `AssetEvent::Removed` in render-asset extraction; `Unused` handles removal there. CPU asset removal alone must not be described as immediate GPU buffer deletion.

No explicit B1 ordering edge to asset-event publication or computed visibility was found. Fresh computed visibility starts false. Both body displays use `NoFrustumCulling`, which weakens an ordinary AABB/frustum explanation. The actual schedule order and rendering mode were not measured.

| Possible mechanism | Prediction for an actually captured blank frame |
| --- | --- |
| New-session visibility handoff | Old display IDs are retired while new IDs are not yet included in the scene camera; later inclusion occurs at the same selection. |
| Asset preparation or draw prerequisites | New CPU IDs exist while a matching render mesh/material, allocator slice, instance or ready pipeline is absent; a later update admits them. |
| Camera or presentation timing | Draw prerequisites are present, but the camera/target/subview excludes the body or no new canvas frame is presented. |

NOT-RUN — red-capable rendered body-absence reproduction, realized schedule order, render-world prerequisites, first present, worst-case recovery, flicker-free operation and GPU presentation continuity. No renderer correction was selected. Root's unchanged R4 sparse baseline did not reproduce body absence; its viewport changed, so it is not a pixel A/B.

## Ordinary UI acceptance boundary

The predeclared recovery condition is all requested roles and committed values/revision present in a sparse observation within 10 seconds after an action API returns, followed by a consistent observation at least 5 seconds later without another app action. Record input start, API return and capture times; preserve late or failed trials. API return is not publication or first-present time. Sparse screenshots cannot prove no interruption between captures.

This CPU report does not establish ordinary UI acceptance. See [issue 86](https://github.com/Derek-X-Wang/nvwa/issues/86) and its linked PR for final Web/native build and ordinary UI run receipts. Native acceptance remains NOT-RUN when the desktop is locked or unavailable. Existing appearance, clothing, generated-motion and performance holds remain unchanged.
