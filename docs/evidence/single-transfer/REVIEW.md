# Independent R2 review: single GLB transfer

Reviewed checkout: `/Users/derekxwang/.codex/worktrees/single-glb-transfer/nvwa`.
Base and observed HEAD: `44b0ec3b129a1e19f5c8c3598f88de1e50e4e826`.
Scope: uncommitted `crates/nvwa-runtime/src/lib.rs`, new `loading_tests.rs`, and experiment 09 evidence. Read-only source review; this report is the only write.

## Findings

### P1 — Fence superseded loads before they overwrite the current scene

Location: `crates/nvwa-runtime/src/lib.rs:448–466`, with completion handling at `489–509` and nested publication at `265–272`.

Reopening the same path while its previous request is still loading makes `reload` true: the condition excludes only `Failed`, not `Loading`. `server.load` returns the same typed handle, and `server.reload` starts an independent forced request. The completion filter contains only asset IDs. Draining already-delivered events before the reopen does not exclude an earlier request that completes afterward.

Pinned Bevy confirms this is not a generation-safe replacement: `bevy_asset-0.19.1/src/server/mod.rs:955–1013` launches a detached reload and calls `load_internal` with the existing handle; `774–782` uses that same ID; `932–935` publishes it without a request identity. `server/info.rs:397–429` installs all labeled assets into their existing IDs before installing the root. No generation comparison rejects an old result.

Concrete failing schedule: start a slow same-path load of parseable bytes A; replace the source with fixture B and explicitly reopen with B's profile; let B finish and spawn; then release A. A's `Scene0`, meshes, skin and animation labels overwrite the labels referenced by B's already-spawned character. The subsequent hash error only returns from `load_character`; it does not despawn or hide that root. Bevy's world spawner also reacts to modified scene assets independently (`bevy_world_serialization-0.19.1/src/world_asset_spawner.rs:593–600, 629–641`). Thus bytes rejected by the current profile can affect the exposed character. With the opposite completion order, an earlier successful completion can authorize the newer document while its requested retrieval remains pending.

Violated invariant: the exposed scene and its subassets must derive only from the exact bytes accepted for the current work/load. A shared path handle and event-draining boolean are insufficient request identity. The generation-fencing weakness also existed in the baseline; the unified root removes the two-reader problem but does not establish the claimed invariant under overlapping opens.

Required verification: a barrier-controlled reader test with two same-path requests, two parseable byte snapshots, opposite completion orders, and an assertion that rejected/superseded scene, mesh and animation data never replace the current character. Serialize or isolate requests/subassets so stale results cannot publish into active handles; merely checking the root generation after publication is too late for already-live labels.

### P2 — Preserve the real reader error after a long-lived Ready session

Location: `crates/nvwa-runtime/src/lib.rs:494–508`, interacting with `638–643`.

The new reader-failure branch clears `asset.verified` and records `Asset byte load failed`, then immediately calls `verify_byte_generation`. `asset.elapsed` counts all time since open, including time spent Ready (`488`); it is not reset for an asynchronous reload. After the work has been open for more than 30 seconds, the verification function immediately overwrites the real I/O error with `Asset verification exceeded 30 seconds` in the same update. This happens even when the reload fails immediately. The new async-failure test completes in well under 30 seconds and therefore misses this path.

Violated invariant: current load failures must remain visible, with meaningful failure priority, until recovery. Clearing verification is appropriate; replacing a known failure with a timeout for an old elapsed timer is not.

Required verification: make the production loading harness Ready, advance/set the elapsed load age beyond 30 seconds, remove the source, reload, and assert that the specific reader failure persists over later updates until a successful explicit reopen. Timeouts should apply to a pending attempt and must not replace an already-recorded terminal failure.

## Confirmed source properties

- Reader delegation is correct on the non-overlapping load path: `load_value_from_reader::<Gltf>` selects the registered typed loader and uses the supplied reader (`bevy_asset/src/loader_builders.rs:176–187, 279–300`); the GLTF loader reads those bytes (`bevy_gltf/src/loader/mod.rs:1166–1175`). There is no second GLB source read in this path.
- `add_loaded_labeled_asset` retains the nested `LoadedAsset` rather than extracting only its value. Recursive installation preserves scene, mesh, skin, morph and animation assets. The root's dependency attribute retains the GLTF dependency.
- Profile validation remains in the runtime system, independent of cached loader settings. Sequential cold loads, completed-state reopens, wrong-profile recovery and parse-error priority are represented in the new production-loader CPU tests.
- Parse errors are retained explicitly and checked after core validation. Reader errors propagate through the typed root. No new swallowed error or disabled failing test was found.
- Changed scope stays in runtime/test/experiment files. No core/schema/asset/manifest/dependency/root-lock edits were present in the inspected status. No applicable documented-standard or ADR violation was found separately from the invariant findings.

## Evidence and verification limits

Read the applicable AGENTS.md, all three docs/agents files, glossary, relevant ADRs, full runtime diff, new tests, experiment report/reproducer and final log. `verification.log` records 28 passed / 0 failed / 0 ignored and a successful clippy workload. These are existing implementer execution records, not independent test executions. The report records earlier failed attempts and their corrections rather than hiding them.

The CPU harness invokes production `load_character`, the real registered Bevy GLTF loader, scene spawning and `collect_evidence`; it does not install the full rendering/Studio pipeline. It counts source-reader calls, not HTTP transfers, and mostly waits for terminal states between opens. It does not prove overlapping-generation safety or GPU/Web behavior. The reported two failing reader attempts on forced reload are consistent with Bevy's fallback; they are not two successful payload retrievals.

No build, test execution, UI action, HTTP measurement, source mutation, external write or delegation was performed in this review. WASM, native graphical behavior, browser HTTP traffic and downstream linkage remain unverified. The two findings above are source-supported control-flow/lifecycle findings, not newly executed reproductions.

PARTIAL — Independent source review complete; two findings (P1, P2). Existing 28-test/clippy evidence inspected; new race and long-lived-error regressions, GUI, WASM and HTTP acceptance remain NOT-RUN.
