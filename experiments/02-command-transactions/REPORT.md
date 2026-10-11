# 02 — Atomic command transactions

## Decision

Use one pure Rust authoritative scene document. Runtime and CLI consume the same
`CommandEnvelope` API. UI previews clone and validate the document; drag release
submits one command. Keep the command journal and undo/redo stacks in memory for M0.

## Implemented scope

- Portable JSON scene/profile types with explicit String IDs, strict unknown-field
  and duplicate-object-key rejection, version checking, and a 2 MiB JSON limit.
- Finite/range/reference/ID checks and safe relative asset paths. Profiles require
  a SHA-256 and a nonempty license; asset verification consumes bytes from callers.
- Atomic candidate validation before any authoritative state/history mutation.
- Expected-revision conflict checks, checked revision overflow, and monotonic undo/
  redo revisions. A new edit after undo clears redo.
- Retry IDs return the original result only when the entire envelope matches. A
  changed payload or expected revision conflicts. Failed IDs are not committed.
- SHA-256 asset integrity, GLB framing/version/resource containment, and morph/
  animation index existence checks. No Bevy, GPU, filesystem IO, or unsafe code.

`fixture.json` shows a serialized edit, its retry, undo, and redo. It is synthetic
and contains no claim about production asset content.

## Evidence

Executed in the assigned local macOS arm64 checkout with Rust 1.95.0:

```text
CARGO_BUILD_JOBS=2 cargo test -p nvwa-core --locked
11 integration tests passed at the worker checkpoint; 0 failed.
Final integrated workspace: 13 core tests passed; 33 Rust tests total; 0 failed.

CARGO_BUILD_JOBS=2 cargo clippy -p nvwa-core --all-targets --locked -- -D warnings
Passed.

rustfmt --edition 2024 crates/nvwa-core/src/lib.rs crates/nvwa-core/src/asset.rs crates/nvwa-core/tests/transactions.rs
Passed.
```

Tests cover JSON roundtrip, typed/serialized command equivalence, multi-parameter
failure with no partial mutation, failed-ID correction, idempotent retry, ID reuse,
revision conflict and overflow, undo/redo, discarded redo after a new edit,
21 slider previews followed by one committed undoable transaction, unknown fields
(including undo), duplicate JSON keys, unsupported schema, oversized input,
unsafe paths, invalid defaults/references, nonfinite values, invalid timeline,
missing/changed/malformed asset bytes, missing indices, and external GLB resources.

One initial test exposed Serde's internally tagged unit variants accepting extra
fields. A private strict decoding shape fixes this while preserving the public
`Command::Undo` and `Command::Redo` API. The final tests pass.

## Limits

- Undo/redo and command IDs persist only in the current `Editor` session. The JSON
  document persists content and revision, not the in-memory journal.
- In-memory history has no M0 eviction cap; long sessions can increase memory use.
- Retry results carry their original transaction revision. The authoritative
  current revision comes from `Editor::document()`.
- Scale and speed require finite values greater than zero. Time starts require
  finite values at least zero. No arbitrary upper bound is imposed; arithmetic
  overflow for timeline end or playback duration is rejected.
- GLB checks do not replace the runtime loader: binary/accessor validity and actual
  rendered skin, morph, animation/player readiness require runtime evidence.
- Callers own missing-file IO reporting and filesystem root/symlink containment.
  The core rejects traversal/absolute/URL-style asset paths without opening files.
- The worker checkpoint did not test the GUI. The final integrated GUI and CLI evidence below supersedes that scope limit for M0.

## Final integrated evidence

The final workspace test run passed 33 tests, including 13 core tests, with no failures or ignored tests. Native and Wasm strict clippy and fmt passed. Actual native edits saved revision 7; actual Web import/drag/clip edits saved revision 10; a fresh native process reopened and saved revision 10 with whole-document equality. One actual Web slider drag formed one undoable command.

The integration owner reconstructed the command sequences from recorded GUI operations and applied them using the actual release CLI binary. Its outputs were semantically equal to the actual GUI-produced revision 7 and revision 10 documents. This is observed document parity, not an instrumented GUI event trace. Evidence: [GUI session](../../docs/evidence/GUI-SESSION.md), [parity result](../../docs/evidence/cli-gui-parity.json), [exchange result](../../docs/evidence/exchange-result.json), [tests](../../docs/evidence/workspace-tests.log).

Reproduce document parity without overwriting the retained evidence:

```sh
target/release/nvwa-cli apply examples/default.nvwa.json docs/evidence/native/gui-command-replay.json /tmp/nvwa-native-replay.nvwa.json
target/release/nvwa-cli apply /tmp/nvwa-native-replay.nvwa.json docs/evidence/web/gui-command-replay.json /tmp/nvwa-web-replay.nvwa.json
target/release/nvwa-cli validate /tmp/nvwa-web-replay.nvwa.json assets
```

VERIFIED — 13 final core tests; actual release CLI reproduces actual native/Web GUI documents, and real GUI history restores geometry. Session-only history limits remain.
