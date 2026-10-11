# 10 — Bounded session editing history

The Rust editor now bounds retained undo/redo snapshots and successful retry
records while keeping snapshot undo and atomic typed commands. These limits are
session-local. Saving and reopening still transfers only the scene document and
its revision.

## Policy

`nvwa_core::EDITOR_RETENTION_LIMITS` publicly exposes the fixed defaults.
`Editor::retention_stats()` reports retained counts and serialized payload bytes.
The CLI `describe-capabilities` response preserves the existing character-profile
keys and adds `editor_retention`: numeric budgets, byte accounting, session-local
FIFO retention, retry expiry/reuse, and oversized-entry behavior. `inspect`
continues to return the document alone. ADR0005 records the same accepted policy.
The additive response starts from the existing typed profile JSON serialization
so authored `f32` values retain their previous JSON representation.

| Retained content | Count cap | Byte cap | Byte definition |
| --- | ---: | ---: | --- |
| Combined undo and redo snapshots | 128 | 16 MiB (16,777,216) | Sum of compact JSON encodings of retained `SceneDocument`s |
| Successful retry records | 1,024 | 8 MiB (8,388,608) | Sum of compact JSON encodings of `(CommandEnvelope, CommandResult)` tuples |

The shipped scene is 1,624 bytes as pretty JSON. Its compact snapshots are about
1 KiB. The 16 MiB budget retains all 128 ordinary snapshots and still permits
several snapshots for near-2 MiB imported documents. The 8 MiB retry budget
retains 1,024 ordinary envelopes but limits sessions with large timeline edits or
IDs. These are retained-content budgets, not exact process heap or RSS bounds.
Container, allocator, string capacity, and collection overhead are unmeasured.
The live scene and temporary validation candidates are excluded.

- Successful insertion uses FIFO retention. Reading a duplicate does not extend
  its retention. Retained identical envelopes return the original result with
  `duplicate: true`. Retained IDs with changed payload or revision still produce
  `command_id_conflict`.
- An expired original envelope gets ordinary `revision_conflict`. Every
  successful command, including undo and redo, advances the scene revision.
  Its original expected revision is therefore stale after expiry. An expired ID
  can be reused by a fresh envelope with the current revision and a valid edit.
  Callers must obtain the current revision from the document; a duplicate result
  carries its original transaction revision.
- Snapshot FIFO compares insertion revisions at the two stack fronts. Each
  front is that direction's farthest reachable state. Removal cannot make undo
  or redo jump over a missing adjacent state. The total cap covers both stacks.
- A valid typed edit is never rejected to preserve retention. If its adjacent
  snapshot alone exceeds 16 MiB, that destination history stack is cleared. This
  forms a barrier instead of permitting a jump into older history. For an edit
  this clears undo; for undo it clears redo. The other reachable direction stays
  intact. A new edit also clears redo as before.
- A successful retry record alone larger than 8 MiB expires immediately. FIFO
  first expires all older retry entries, then expires that oversized entry. The
  edit succeeds. Its original envelope remains protected by revision checking.
- Failures, including revision overflow, mutate neither the scene nor retention.
  Failed IDs remain available for corrected commands.

The core retains snapshot documents and typed envelopes, not JSON strings.
Serialization counts stream through a byte counter, which avoids allocating a
second serialized copy of a large payload. No inverse-operation log, persistent
journal, UI notice, or additional scene-size rule was introduced. The existing
2 MiB JSON import/export limit remains independent of typed editing.

## Bound and chain argument

Before pushing a fitting snapshot, eviction continues until the existing count
is below 128 and existing bytes are at most `16 MiB - incoming bytes`. The push
therefore satisfies both limits without arithmetic overflow. Popping undo/redo,
clearing redo on a branch, and clearing an oversized snapshot's destination all
subtract the removed snapshots' recorded sizes. The byte counter equals the sum
of retained compact snapshot sizes by induction from the empty editor.

Every inserted snapshot has the new command's strictly increasing revision as
its insertion age. Each stack appends at its back, pops adjacent states from its
back, and evicts only from its front. Stack fronts are thus the oldest inserted
and farthest reachable states. Choosing the lower front age implements FIFO
across both stacks. Removing farthest states preserves a contiguous reachable
chain; clearing a direction at an oversized adjacent state prevents bridging.

Retry eviction uses the same subtraction-before-addition rule with 1,024 entries
and `8 MiB - incoming bytes`. Oversized entries clear the FIFO instead of being
retained. Duplicate reads and all errors skip mutation. The successful-envelope
revision guard prevents reapplying original envelopes after any expiry, without
retaining an unbounded set of expired IDs.

## Verification

Executed with Rust/Cargo 1.95.0 in the assigned local macOS checkout at base
`44b0ec3b129a1e19f5c8c3598f88de1e50e4e826`. Source hashes and exact exits are in
[`evidence.json`](evidence.json).

```text
CARGO_BUILD_JOBS=2 CARGO_TARGET_DIR=/tmp/nvwa-bounded-history-target cargo test -p nvwa-core --locked -- --nocapture
exit 0: 8 new public-behavior tests + 13 existing integration tests; none ignored.

CARGO_BUILD_JOBS=2 CARGO_TARGET_DIR=/tmp/nvwa-bounded-history-target cargo clippy -p nvwa-core --all-targets --locked -- -D warnings
exit 0.

rustfmt --edition 2024 --check crates/nvwa-core/src/lib.rs crates/nvwa-core/src/bounded_history_tests.rs
exit 0.
```

The new tests use the public editor API and actual production caps. They cover
the 128-snapshot boundary, complete contiguous undo/redo after eviction,
branching, 1,024 retry entries, duplicate reads at capacity, retained conflicts,
expired original envelopes and fresh-ID reuse, exact 16 MiB and 8 MiB byte
boundaries, mixed undo/redo byte eviction, valid oversized snapshot barriers,
oversized retry expiry, failures at full budgets, overflow with already-retained
history/retries, and document-only reopen.

The fixed workload performs 10,000 valid scale edits, 10,000 duplicate reads,
10,000 invalid scale submissions, and 1,000 undo/redo pairs: 12,000 successful
commands in all. It checks both byte/count limits and the expected monotonic
revision after every iteration.

| Edits | Successful commands | Undo / redo snapshots | Snapshot bytes | Retry entries | Retry bytes |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1,000 | 1,200 | 128 / 0 | 133,706 | 1,024 | 181,267 |
| 5,000 | 6,000 | 128 / 0 | 133,706 | 1,024 | 183,938 |
| 10,000 | 12,000 | 128 / 0 | 133,834 | 1,024 | 185,986 |

The byte changes reflect longer revision/command-ID digits. The retained count
does not grow with session length. This is a retained-payload measurement, not a
process-memory benchmark.

The initial regression harness compile failed with mutable/immutable borrow
ordering errors (exit 101). It is preserved in
[`test-first-output.txt`](test-first-output.txt); the test helper argument order
was corrected. The first passing checkpoint (20 tests) is preserved in
[`test-second-output.txt`](test-second-output.txt). Final evidence is in
[`test-final-output.txt`](test-final-output.txt),
[`clippy-output.txt`](clippy-output.txt), and [`fmt-output.txt`](fmt-output.txt).

The follow-up CLI finishing gate passed 27 tests (21 core and 6 CLI), the real
public-output capability assertion, strict core/CLI clippy, and formatting. All
exits are zero in [`additive-final-checks/evidence.json`](additive-final-checks/evidence.json).
The capability probe compares every existing profile key/value, asserts all new
numeric caps and policy fields, confirms unchanged supported commands and
document-only `inspect`, and checks that the source scene is unchanged. The actual
response is preserved in [`capability-output.json`](capability-output.json).

The first additive gate deliberately remains in
[`additive-checks`](additive-checks/evidence.json): core/CLI tests passed, but the
capability assertion failed on clip values (exit 1). `serde_json::to_value`
widened `f32` numbers before output encoding, changing idle duration from
`3.0416667` to `3.0416667461395264`. The rejected source is preserved in
[`rejected-capability-cli-main.rs`](rejected-capability-cli-main.rs), SHA-256
`be678f9530e053b20dbe7194109e469843ab839a94b5da8ff2bbb0e8ba7ca7d7`.
Preserving the typed profile JSON before adding metadata corrected the regression.
Independent R2 review reported the same finding; root owns the review record and
targeted rereview. No retention behavior changed during this repair.

Reproduce without replacing retained logs:

```sh
python3 experiments/10-bounded-history/reproduce.py
```

This runs core/CLI tests, the real CLI capability assertion, clippy, and formatting
sequentially. It creates fresh
temporary evidence and native target directories, prints their paths, records
source hashes and exits, and stops after the first failed check. A caller may
pass `--target-dir` to reuse its own isolated target. Coordinate one native
compile workload per worker; this experiment used two Cargo build jobs.

## Integration and remaining limits

- Narrow follow-up delegation completed additive CLI capability discovery and
  ADR0005 in the same isolated worktree. The `domain-modeling` skill guided the
  ADR update; historical evidence files remain unchanged. Root owns central
  integration and any remaining root documentation. No Studio UI change is needed.
- Retained retry lookup scans at most 1,024 entries. No claim is made about
  workload latency or exact allocator/RSS bounds.
- The current scene and typed envelope may exceed these retention byte caps.
  Typed validity was preserved; existing JSON transport limits still apply.
- GUI, GPU, release, workspace, and Wasm builds were not run by this worker.
  Changed scope is core source, CLI `src/main.rs`, ADR0005, and this experiment.
  No manifest, lockfile, dependency, asset, or historical log was changed. No
  commit, push, publication, or merge was performed.
- Owned cleanup resource: `/tmp/nvwa-bounded-history-target`. All Cargo/test
  processes and exec sessions completed; no owned live PID remains. Root owns
  integration and cleanup of the target and managed worktree. Keep this report
  and the preserved logs as evidence.

VERIFIED — 27 core/CLI tests, actual CLI capability assertions, strict clippy,
formatting; actual count and compact-payload boundaries plus the 10,000-edit
workload. GUI/GPU and exact process-memory usage remain unmeasured.
