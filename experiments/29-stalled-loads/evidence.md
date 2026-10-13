# Fresh #23 CPU evidence

**VERIFIED — two genuine pre-fix capacity failures, named transport mutation red /
positive green, and 18/18 final production-called loading regressions.**
Native/Web whole-document acceptance, actual browser transport, GPU lifetime,
exact byte budgets and global loader-task caps remain **NOT-RUN** here.

Host `MacBook-Pro.local`; checkout
`/Users/derekxwang/.codex/worktrees/m11-stalled-loads/nvwa`, branch
`codex/m11-stalled-loads`, base `045d8abc685760d09ba05afec0e40a811a282d1f`.
Every Cargo invocation used `CARGO_BUILD_JOBS=1`, `--locked`, the existing target,
and the default test profile. No dependency, lockfile, asset or core/Studio file
changed. No cache deletion, global setting, external write or renderer run.

## Results

| Stage | Actual matched result | Meaning |
|---|---|---|
| First attempt | Build exit 101; no executable | `bevy_asset` ENOSPC. Original failure preserved. |
| Controlled pre-fix retry | 0 passed / 2 failed, 37 filtered | Both capacity assertions fail against unchanged base production `lib.rs`; retained candidate test adapters were present. |
| Initial candidate | 17 passed / 1 failed | Bound holds; test HTTP recovery returns truncated bytes, and unchanged production hash validation rejects them. |
| Blocking transport repair | 18 passed / 0 failed | Production guard/verifier unchanged; adapter sockets explicitly blocking and incomplete HTTP body rejected. |
| Named old-transport mutation | 0 passed / 1 failed, 38 filtered | Skipping accepted-socket blocking setup reproduces exact original truncated digest and WouldBlock. |
| Named corrected HTTP transport | 1 passed / 0 failed, 38 filtered | Five complete source retrievals, latest path ready, stale scene fingerprint unchanged. |
| Final source / cleanup counters | 18 passed / 0 failed, 21 filtered | All existing and new loading cases; explicit gate/thread cleanup counters. |

Pre-fix filter `stalled_distinct_paths` discovers exactly two named tests.
Final `loading_tests` discovery has exactly 18 named tests, zero benchmarks.
The 30-second waiting/error branch is exercised by injecting elapsed=31 into
CharacterAsset and running the production loading system; a real 30-second
native/Web wall-clock dwell is not claimed.
Private discovery logs and each original test log/JSON receipt remain under
`.work/m11-asset/`; `manifests.json` records all source/executable identities.

## Retention counters

Each reproduction attempts twelve distinct-path document opens. While stalled:

| Actual production-called workload | Pre-fix roots / Loading roots / reads / held readers or responses | Candidate |
|---|---|---|
| Memory reader snapshots | 12 / 12 / 12 / 12 | 4 / 4 / 4 / 4 |
| Real loopback HTTP | 12 / 12 / 12 / 12 | 4 / 4 / 4 / 4 |

Loaded CharacterGlb roots and loaded GLTF assets were both zero while the source
responses were held. Candidate recovery admits only the latest pending path:
five total reads, zero retiring root entries, `ready=true`. At that exact sample,
loaded CharacterGlb count was one and loaded GLTF count was four. The latter is
observed transient asset storage, not a dependency-retention budget or proof of
GPU release. No exact memory-exhaustion event is claimed.

## Exact HTTP boundary failure and repair

The server attempted the original fixture body: **3,827,840 bytes**, SHA-256
`f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6`.
The old accepted-socket behavior produced `WouldBlock` during the body write.
Read five accepted/sent and received **327,149 bytes**, both SHA-256
`febf08318739d1afd8a168c20dea3445053075a9bb28d5042afd479034d1cf07`.
That is exactly the received digest from the initial failed recovery run.
The sent and received body files match byte for byte, and match the fixture's
327,149-byte prefix. The old test server ignored the incomplete `write_all`.
Production hash validation correctly rejected those truncated bytes.

The test adapter now explicitly puts accepted sockets in blocking mode, keeps
its existing socket deadlines, and requires exact Content-Length before
returning a reader. Bounded diagnostic writes report bytes accepted and errors;
optional private receipts retain attempted, sent and received bodies. The
mutation skips only socket blocking setup. The named positive test uses the same
source/executable as its mutation and passes. All five sent/received bodies in
the positive and final suite equal the full fixture, with the full digest above.
No production validation, expected hash, admission guard or timing assertion
was changed to repair the transport. A private adapter diff from the initial
draft includes counter/formatting changes and is not labeled exact baseline.

Final HTTP cleanup reports:
`server_joined=1 response_threads_joined=5 reader_threads_joined=5 held_gates=0 panics=0`.
The socket binds only `127.0.0.1:0`. Test threads have finite IO/server deadlines;
all gates release and threads join in Drop, including failed assertions.

## Fresh identities and storage

Base production `lib.rs` SHA-256:
`bd6da4b2212a6bec251ad8ae4ca7b8fbca1038b383a6031cec1b9c0fa1b8ce72`.
Only that file was restored for the controlled pre-fix retry; candidate test
modules were retained and hashed separately. Finally restoration verified the
candidate production source byte for byte. The first ENOSPC log was preserved.
A fresh >32 GiB gate passed at 79.75 GiB; the controlled retry's minimum was
63.96 GiB. The final run's minimum was 57.33 GiB. No new ENOSPC occurred. The
reason free space changed before retry remains unknown; this worker did no cleanup.

Final executable SHA-256:
`f496d231b39951ab01dcdc252b62f25cd0e05a68c10cc1354bdcd8adc5396e73`.
Final source SHA-256 values:

```text
548e40cc7c60b6f26f214c58e8520a67477d2965de151ae04689532b21aeba73  crates/nvwa-runtime/src/lib.rs
fd6ecb9039ddcaeb3caa4da38a985f7b904d06bdd75bf9624d5a074b4b472804  crates/nvwa-runtime/src/loading_tests.rs
7fa3c0055bc39e04f47f3f3f2cb532f4d2aac9945a89c5dcc625fc3feebe9b55  crates/nvwa-runtime/src/stalled_http_tests.rs
```

`rustfmt` and `git diff --check` pass. No worker-owned build/test process or
socket remains; the exclusive compile lease was returned to root. The target
and historical protected receipts remain under root ownership.

## Independent review and retained raw output

Fresh read-only R2 review found no actionable admission or cleanup defect.
It independently replayed all18 loading tests, the named transport mutation and
the restored positive case from the unchanged final executable. Its fresh
mutation truncated at327,182bytes; the archived failing attempt truncated
at327,149bytes. The precise socket prefix length depends on scheduling.
Both fail the unchanged complete-body/integrity boundary; only the archived
attempt is claimed to reproduce the original exact failing digest.

[Original logs and manifests](../../docs/evidence/m1-1-final/loading/raw-manifest.json)
retain all21 bounded author receipts, including the first ENOSPC and initial
HTTP recovery failure. [Independent review](../../docs/evidence/m1-1-final/loading/review/review.json)
and its replay/body-verification receipts are retained separately. Private body
files remain local; their byte identities are recorded, without adding repeated
multi-megabyte fixtures to Git. Raw logs preserve original EOF whitespace.
Source whitespace checks pass; publication ignores only Git's `blank-at-eof`
diagnostic for raw receipts. Integrated native/Web acceptance remains pending.
