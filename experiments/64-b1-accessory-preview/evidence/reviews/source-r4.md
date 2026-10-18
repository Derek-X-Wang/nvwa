# Independent targeted source re-review — experiment 64, r4

Verdict: **CLEAR at the source-review stage** for the remaining r3 P2 and the related guards changed in r4. No further actionable finding in this narrow change. Rust compilation, execution of the new test, native/Web launch, and GPU/pixel acceptance remain **NOT-RUN**. Root may proceed to the separately owned cold-build gate; this report does not claim that gate passed.

## Exact frozen identity

- All 13 file hashes match `.work/appearance64/source-freeze-r4.json`.
- Canonical map SHA-256 (`json.dumps(map, sort_keys=True).encode()`): `e36e167caf490369e0d9584101ecf92825b61a7ab5853a18f8500a23c174b52d`.
- Only `experiments/64-b1-accessory-preview/src/accessory.rs` changed from r3. Its SHA-256 is `efc28c28c623fe594a9c5a87e8fe96cfce0bb3c32883717df1fdd58d342c82ae`.
- The other 12 paths retain their r3 hashes. Parser, command controller, docs, geometry contract, and dependency lock were not reopened as a new general review.

## Remaining P2 resolved at source level

`accessory.rs:662-668` now uses `get_entity_mut(...).map_err(...)?` before inserting the transform. A disappeared accessory entity therefore returns `Err` through the existing `update` call. `sync` (`:500-503`) and `stream` (`:733-736`) route that error through `dispose`, preserving the intended recoverable-error cleanup path. There is no remaining direct `World::entity_mut` call in the production update/stream path; occurrences below the test module are fixture setup/mutations on known existing entities.

The neighboring guards are coherent:

- `update` begins with `require_asset_resources` (`:515`), checking the three typed asset stores before the later infallible resource accesses (`:800-807`). The exclusive mutable `World` access keeps those stores stable during the function's ordinary sequential execution.
- `observe_material` calls the same presence guard (`:810-811`) before reading its material/image stores.
- `stream_current` uses a fallible `Playback` lookup (`:773-775`). Existing character/body entity and component lookups propagate missing-state errors.
- `dispose` (`:462-476`) drains all live records, tolerates already-despawned entities and absent typed asset stores, removes owned mesh/material/image entries from stores that still exist, and clears the binding key and frame. Thus the new missing-store error cannot itself force another infallible typed-store lookup during cleanup.

These observations are scoped to the accessory lifecycle paths changed and reviewed. They are not a claim that arbitrary corruption of every unchanged upstream runtime resource can never panic.

## The new control reaches the original production seam

`missing_attachment_entity_reaches_update_error_and_disposes_sibling_assets` (`accessory.rs:1042-1113`) constructs real `World`, mesh, material, and image entries. It supplies a valid three-vertex mesh, normals, weights, a 53-matrix snapshot, matching key, and exactly two live entries. The matching key and two-entry state bypass the refit branch at `:545`, so the test cannot pass merely by stopping on an incomplete cage before reaching the old failure point.

It then:

1. Despawns the first actual accessory entity at `:1088` and explicitly confirms that its mesh/material/image assets still exist (`:1089-1096`).
2. Calls the actual production `sync -> update` path inside `catch_unwind` (`:1097-1099`).
3. Requires no panic, an `Err` containing the exact missing-entity message from `:664`, empty live state, null frame, and a recorded error (`:1100-1104`).
4. Checks sibling entity removal and removal of the retained asset handles (`:1105-1113`).

This is a valid source-level negative control for the original seam. Reverting the fallible lookup to the previous `entity_mut` would reach that missing entity before the later guard and cause the `catch_unwind` assertion to fail. That mutation-red expectation is derived from the inspected control flow; neither the test nor an actual mutation run was executed here. The sibling intentionally shares handles in this small fixture; this proves disposal of the sibling entity and shared owned asset set, while distinct production eye/hair lifecycle behavior remains part of runtime verification.

## Verification and cleanup

VERIFIED — frozen 13-file r4 hashes and the targeted source/control-flow review.

NOT-RUN — Rust compilation/tests, mutation execution, complete native/Web lifecycle checks, actual live rendering, GPU/pixel evidence, and the shape/sample acceptance matrix. The prior five Python parser controls were not rerun because their files are unchanged from the independently verified r3 result.

Only this report was written. No source, prior report, Git state, asset, dependency, process, server, GUI session, or temporary artifact was created or changed. Root retains build and final integration ownership. #3 blocked, #4 gap, clothes/M2 HOLD remain unchanged.
