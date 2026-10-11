# Fresh R2 review — Nvwa #8 bounded history

Outcome: one P2 finding in additive CLI discovery. No retention state-machine defect found within the reviewed contract.

## Finding

**[P2] Preserve the existing profile numeric output when adding retention metadata**

- File: `crates/nvwa-cli/src/main.rs`, lines 93–94 (isolated checkout `/Users/derekxwang/.codex/worktrees/bounded-history/nvwa`).
- Trigger: run `describe-capabilities examples/default.nvwa.json` after this change.
- The old path serialized `CharacterProfile` directly. The new `serde_json::to_value(&document.profile)` path first promotes its `f32` fields to `f64` JSON numbers. With locked serde_json 1.0.152 and normal features, the default idle/wave duration changes from `3.0416667` to `3.0416667461395264`, and turn changes from `4.0416665` to `4.041666507720947`. Existing JSON consumers comparing profile values therefore observe changes beyond the additive `editor_retention` key. The supplied `capability_probe.py` equality assertion for `clips` will fail.
- Evidence: locally cached serde_json 1.0.152 `src/value/ser.rs:151` calls `Value::from(float)`; `src/number.rs:323–328` stores f32 as `N::Float(f as f64)` absent arbitrary_precision. Direct serialization instead uses `write_f32` in `src/ser.rs:155–164`. An independent Python `struct.pack/unpack('f')` check reproduced these exact promoted values and confirmed they differ from the fixture JSON numbers.
- Suggested fix: serialize a typed output wrapper with a flattened borrowed `CharacterProfile` plus retention metadata, so original fields still traverse their direct f32 serializer. Run the supplied real-CLI capability probe against the freshly built binary.
- Execution limit: this reviewer did not compile or execute the new CLI. At inspection time `/tmp/nvwa-bounded-history-target/debug/nvwa-cli` did not exist. The finding is source-backed and numerically reproduced; final CLI execution belongs to root integration.

## Bounded acceptance of core retention

Inspected the whole changed core state machine and all eight new tests before reading the implementer report. The accepted design remains snapshot undo. Combined undo/redo limits are 128 snapshots and 16 MiB compact document JSON; successful retry retention is 1,024 entries and 8 MiB compact envelope/result tuple JSON.

The code counts payloads before mutation. Validation, revision overflow, stale revision, retained ID conflict, and unavailable undo/redo return before any session mutation. Snapshot removal subtracts recorded sizes; fitting insertions evict oldest stack fronts until both aggregate limits fit. Each front is the farthest reachable state in its direction. An oversized adjacent state clears its destination direction, preserving the barrier instead of jumping across a missing state. A new edit clears redo. Retry duplicates neither advance revision nor refresh FIFO. Oversized retry insertion clears prior FIFO content then expires. Expired original envelopes are stale because every successful command advances revision; fresh valid reuse of their ID remains possible. Document-only reopen constructs empty retention.

No contradiction with GLOSSARY or ADR0005 was found. No actionable standards finding was found. Skills read: code-review (single-review execution kept per dispatch prohibition on delegation); ctxfs (dependency source already local, so no mount used).

## Exact inspected source hashes (SHA-256)

| Source | SHA-256 |
| --- | --- |
| `crates/nvwa-core/src/lib.rs` | `4c2f06d56b43e3849ee9040c8c5c5f999401816f8b64431d0dbfa240d952b797` |
| `crates/nvwa-core/src/bounded_history_tests.rs` | `4d20f38f8ee7f270a469af64ab0de0c357d8b5e0e6d73a8abd856c3840762e3b` |
| `crates/nvwa-cli/src/main.rs` | `be678f9530e053b20dbe7194109e469843ab839a94b5da8ff2bbb0e8ba7ca7d7` |
| `docs/adr/0005-portable-document-and-commands.md` | `35bb5cd4669adc4d95f406cec446b664adbb229d05c4368c541ef511c7538f4c` |

Base comparison: working tree versus `44b0ec3b129a1e19f5c8c3598f88de1e50e4e826`. All four hashes matched the dispatch freeze.

## Verification and limits

Reviewed preserved `test-final-output.txt`: eight new core tests and 13 existing integration tests passed. Reviewed `evidence.json` linking those results to the inspected core hashes, including the 10,000-edit / 12,000-success workload and boundary counters. These are implementer execution records, not independent reruns. Test coverage includes mixed stacks, exact byte boundaries, oversized barriers, retry expiration/reuse, failures at capacity, overflow, and reopen.

Independent reviewer execution: read-only diff/source/hash inspection and a Python f32 promotion calculation only. No Cargo/build/test/UI/remote actions or repository edits were performed. The only write is this review report. Exact heap/RSS, release/GUI/GPU/Wasm behavior, and fresh CLI execution remain unverified by this review.

PARTIAL — bounded core accepted on source inspection plus matching preserved test evidence; CLI additive output needs the P2 numeric-preservation fix and fresh executable probe.
