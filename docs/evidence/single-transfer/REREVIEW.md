# Targeted independent R2 rereview

Decision: **accept the P1 and P2 repairs within the runtime-owned explicit-open guarantee for the supported self-contained GLB. No open actionable finding from this targeted rereview.** This is not GUI, network, WASM or integrated-release acceptance.

Checkout: `/Users/derekxwang/.codex/worktrees/single-glb-transfer/nvwa`.
Observed source hashes match the frozen dispatch:

- `crates/nvwa-runtime/src/lib.rs`: `bd6da4b2212a6bec251ad8ae4ca7b8fbca1038b383a6031cec1b9c0fa1b8ce72`
- `crates/nvwa-runtime/src/loading_tests.rs`: `9fec6b200db271117b26db45eef2758820f644a8bbc7ef4e74de4d8cc9a8c26a`

## P1: accepted

`lib.rs:453–502` removes the old visible root, transfers its root handle into retirement, and resets the current generation before advancing any new request. `633–685` waits for an observed completion/failure and terminal recursive state, drops the retained root, and keeps the same-path fence until the old asset ID is absent. Only then does ordinary `server.load` create the replacement. No production `server.reload` remains. This fixes the original failure at the publication boundary rather than trying to reject a stale root after its subassets already changed live handles.

Pinned Bevy source supports the removal condition: `bevy_asset-0.19.1/src/server/info.rs:710–756` removes the tracked task, asset info and path/type mapping when the managed root handle is dropped. The repair waits for actual terminal publication first, so it does not depend on cancellation of an outstanding detached forced reload. Existing nested-loader tree preservation and one-reader behavior remain intact.

Specific lifecycle checks:

- A terminal reader failure can retire: `LoadState::Failed` is an accepted settled state (`644–645`), including an event delivered in the same update as the superseding open. The retained event/`load_completed` state prevents missing an already-observed terminal completion.
- Multiple queued same-path opens preserve existing retirees and replace only the current queued document/profile (`460–475`). A queued intermediate profile does not create its own retrieval.
- Distinct paths can load while earlier requests remain held (`667–679`). Retirement processing runs before the early return for current Ready state, so late completion still releases old resources. A return to a retired path waits for that path's fence.
- The path comparison is appropriate to the current accepted profile grammar: `nvwa-core/src/lib.rs:244–257` rejects empty/dot/parent segments, backslashes, source/label delimiters and URL-like syntax. Bevy asset identities include the path and label. Different supported self-contained GLB paths therefore do not share internal label IDs, even if the filesystem bytes happen to refer to the same underlying file.
- The immediate root/part retirement test checks actual ECS entity absence. The barrier tests use the real registered GLTF loader and independently changed scene, mesh and animation content, not mocked successful completion.

## P2: accepted

The verification timeout now applies only when `status.error.is_none()` (`lib.rs:723–729`). A specific reader/core failure is no longer replaced on later updates. New explicit retrieval resets the attempt timer and clears prior error state (`679–684`). The queued-old-request timeout also requires no existing error (`674–676`), keeps the fence intact and does not pretend to cancel the reader.

The aged-error regression sets the production resource's elapsed age to 31 seconds, causes a real source-reader failure, checks the exact error across 20 updates, then restores and explicitly reopens the fixture (`loading_tests.rs:546–583`). This directly covers the originally reported control flow.

## Evidence inspected

`r2-red-runtime-tests.log` records 28 passing and three failing tests. The failures correspond to both original findings: superseded A surfacing its hash error in B; A overwriting B's scene/mesh/animation fingerprint; and the specific reader error being replaced by the timeout. The B-first red fingerprint changes include head translation 0.100000024 → 5.1, mesh x -0.078 → 4.922, and animation duration 3.0416667 → 6.0833335.

`r2-final-runtime-tests.log` records 35 passing, zero failing and zero ignored tests. `r2-final-clippy.log` records successful native runtime checking; the report and reproducer specify `--lib --tests --locked --offline -- -D warnings`. These are inspected execution records from the implementing worker, not independently rerun commands.

Compared the retained red test source with final tests. The three original failing requirements and their assertions remain. Final changes remove an unfulfilled deprecation lint expectation, extend aged-error recovery, add barrier failure injection, and add four lifecycle regressions. No failing test was disabled or replaced with a mocked success. The attempted B-first green schedule intentionally proves that a second same-path request cannot start; it does not falsely claim two concurrent successful same-path loads.

## Limits and retained tradeoffs

- Acceptance applies to runtime-owned explicit opens using the supported self-contained fixture/default loader. External/manual concurrent forced reloads remain outside the fence. Controlled manual reload error tests establish error ordering only.
- A same-path source that never terminates keeps its queued replacement fenced. The timeout reports the wait; it does not cancel or free that request. Different paths remain available. Multiple permanently pending distinct paths can retain multiple roots and async resources; no memory/GPU bound or cancellation policy is claimed.
- Recursive dependency failure can summarize a failed tree rather than prove every arbitrary external dependency has stopped. The accepted self-contained fixture avoids that broader shared/external-resource case. This rereview does not extend the guarantee to arbitrary external GLTF dependencies or custom loader extensions.
- Source-level reasoning supports return-to-retired-path behavior and queued timeout recovery, but the final suite does not include a separately named A→B→A regression or an actual 30-second held-queue timeout run. These are coverage limits, not observed defects or blockers for the stated bounded guarantee.
- No independent builds/tests, UI activity, browser HTTP measurements, remote operations or delegation occurred. Full-workspace integration, native release, WASM and graphical/network acceptance remain root-owned. Immediate ECS scene retirement does not prove immediate GPU reclamation.

Scope stayed read-only except for this requested report. No source, lockfile, dependency, fixture, schema or manifest was changed by the reviewer; no process/resource was created that needs cleanup.

PARTIAL — Targeted R2 source rereview accepted both fixes with zero open findings; frozen hashes and real red/green/clippy records inspected. Independent execution and product acceptance remain NOT-RUN.
