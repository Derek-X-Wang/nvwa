# Fresh #23 CPU and Web evidence

**VERIFIED — two genuine pre-fix capacity failures, named transport mutation red /
positive green, and 18/18 final production-called loading regressions.**
Root subsequently ran the fresh candidate in one actual Web app. The durable
archive verifies startup Work01 plus eleven completed GUI chooser selections,
four blocked transfers, latest Work12 recovery and the whole saved document.
Native stalled-load visual acceptance, exact byte/global-task/GPU-lifetime caps,
and a reproducibly archived timeout-UI observation remain **NOT-RUN** here.

Host `MacBook-Pro.local`; checkout
`/Users/derekxwang/.codex/worktrees/m11-stalled-loads/nvwa`, branch
`codex/m11-stalled-loads`, base `045d8abc685760d09ba05afec0e40a811a282d1f`.
Every Cargo invocation used `CARGO_BUILD_JOBS=1`, `--locked`, the existing target,
and the default test profile. This worker changed no dependency, lockfile, asset or core/Studio file and
performed no cache deletion, global setting or external publication. The CPU
worker did not run a renderer; the later actual Web run belongs to root.

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
The CPU 30-second waiting/error branch is exercised by injecting elapsed=31
into CharacterAsset and running the production loading system. The successful
Web capacity wait was under 30 seconds. The separate failed path-edit attempt
held startup Work01 for more than 30 real seconds; root observed `Asset
verification exceeded 30 seconds` in conversation-only Cua output, but saved no
image bytes for that observation. Durable timeout-UI acceptance remains
NOT-RUN. Do not equate this with the injected CPU timer branch.
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

## Actual fresh Web picker case

Root's final artifact identity is `bf6a834fa0eddf05cc15c4215ae3febe1bcdeb0e`.
The frozen Wasm was rehashed read-only and equals
`d890dfee73e9eeeee6ce3d82f255c79979e8c8b6bed90243c6101f8e1c1763a8`
(85,605,719 bytes). The server source is
`f2724fd7d667c4511835e3d4235de055d0505219d583a7f5ea321e228c6128f7`.
This case used hold=105 seconds and overall watchdog=120 seconds; these are
configuration limits, not actual watchdog dwell acceptance.

The durable [raw server log](web-acceptance/web-stall-picker-case.jsonl),
[actual Cua transcript](web-acceptance/web-stall-cua-exact-trace.jsonl), its
[line/call manifest](web-acceptance/web-stall-cua-exact-trace-manifest.json), and
[selected files](web-acceptance/selected-works/) establish the following:

- One startup URL created tab52 bound as `nvwaPickerTab`; no additional app
  navigation or Wasm startup appears in this case. Four actual calls completed
  with matching completion/output IDs and `isError=false`.
- Work02 used one awaited real file chooser. The exact loop03–12 registers
  the chooser wait, clicks Open, awaits the chooser, then awaits `setFiles`; it
  has no catch or
  early exit. Work02's compact action timestamp is receipt initialization after
  selection. Its authoritative completion is in the exact transcript.
- At 42.7954 seconds, four responses were simultaneously held. Exactly one GLB
  request each existed for 01–04. There was no earlier release, held connection
  closure, extra fifth GET, watchdog, budget rejection or exception. Only the
  startup Work01 was an HTTP Work GET; the other eleven Works came from the GUI
  chooser. Do not count twelve HTTP Work GETs.
- Root released **all four together** through stdin at 47.7098–47.7101 seconds.
  Only the latest pending path12 was requested afterward, at 47.8475 seconds.
  All five fixture responses completed with 3,827,840 body bytes each. One-slot
  release remains a CPU regression result, not a result of this Web case.
- The [pre-release image](web-acceptance/picker-12.jpg) shows `Waiting for earlier
  character loads (4/4)…`; the [recovered image](web-acceptance/web-stall-recovered.jpg)
  shows the real character ready. All paths intentionally use identical rig
  bytes, so these screenshots do not identify a publication generation by
  appearance. CPU fingerprint tests supply the stronger stale-publication
  evidence.
- An actual Save/download completed. The [entire saved document](web-acceptance/web-stall-saved-work.nvwa.json)
  equals canonical variant12 semantically, including revision, profile, recipe
  and complete timeline. Its serialized hash is
  `8097148bd4229da93718d7e6c1d7e072e5debb2dd637c7af1b6a085a9a71eae4`;
  selected variant12 is `3913eb164dc758b8e3478683b83adc262379dc355c99652948f718f3da1364fa`.
  Different number/object serialization explains different bytes; whole-Doc
  semantic equality is checked rather than falsely asserting byte identity.
- Cleanup at 85.8951 seconds records 14 accepted/14 closed sockets, zero active
  connections/held bodies/response threads, clean stdin quit, no invalid or
  secondary reasons, and no exception. Root closed the tab and reset its
  browser viewport. The archived console has one window/BrowserWebGpu startup
  and no error records; its unsupported texture-array warning is retained.

The first [path-edit attempt](web-acceptance/failed-path-attempt/web-stall-first-attempt.json)
is preserved separately with its raw log and attempted GUI action list. It
fetched only startup01/GLB01 and selected no further Works. Its twelve attempted
click/path edits are **not** twelve accepted GUI Opens. It is NOT-RUN for the
capacity/recovery case and is excluded by the archive checker.

## Portable checker and adapter repair archives

Run without a server, browser, Cargo, GPU, or root-private paths:

```sh
python3 -B experiments/29-stalled-loads/check_web_archive.py --self-test
```

Optional `--frozen-web /path/to/frozen-web` rehashes the actual Wasm. Input count,
file size and total archive size are bounded. The checker verifies exact
transcript/line identity, completed call provenance, chooser endpoints/binding,
all selected Work hashes, observed HTTP order/release/cleanup, whole-Doc equality
and declared fresh artifact identity. It checks archived receipt consistency;
it does not replay or independently recreate the GUI observation.

Ten negative semantic controls reject fifth-before-release, incorrect entire
saved Doc, missing chooser, unclean sockets, failed Cua completion, wrong output
ID, a Cua error, wrong Wasm, counting a failed path edit, and removing awaited
file selection. These operate on in-memory copies after the real archive's
hash checks, so rejection is not only a file-hash mismatch. The immutable
archive bytes remain untouched.

[Adapter repair index](adapter-repair/archive-index.json) provides portable
receipt/raw links for both nine-record cohorts. Original manifests and their
raw failed controls remain preserved. Socket-free method-family records are
explicitly labeled and are not presented as runtime JSONL. The final repair
cohort contains actual-loop late exception after real stdin quit, monotonic
status controls, and bounded direct-HTTP controls. These validate the evidence
adapter, not product Web behavior.

Native stalled-load visual acceptance remains pending root. Exact browser
retiring-root counts, byte/task/GPU-memory caps, and actual 90/105/120-second
watchdog dwell remain NOT-RUN. The source admission policy and CPU counters are
stronger than the browser's HTTP observables; keep those limits separate.


The repair inventory checker also fails closed on archive truncation. It
requires exactly both original manifest entries, exactly `previous_nine` and
`new_nine`, each complete canonical receipt-name set from those manifests, and
exactly 18 validated receipts. Six additional inventory controls reject missing
one cohort, missing both cohorts, a missing receipt, a missing original manifest
entry, an extra cohort and an extra original manifest entry.

The retained [actual CLI red receipt](adapter-repair/inventory-controls/archive-inventory-pre-red-inventory-controls.receipt.json)
shows the prior checker incorrectly returned PASS with 9, 0, or 18 records when
one cohort, both cohorts, or an original-manifest entry was omitted. A missing
single receipt and extra entries already rejected before this repair; those
boundaries were kept. The [actual CLI green receipt](adapter-repair/inventory-controls/archive-inventory-final-green-inventory-controls.receipt.json)
rejects all six cases. Mutations were made only to private copies of the index;
original archive files and failure receipts remained unchanged.
