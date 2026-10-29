# Native compiled-target cache trial (#106)

Status: **ADOPTED — MAIN PUSH ONLY**, after the reviewed fixed-source trial
passed every predeclared threshold. See [actual results and limits](RESULTS.md).
Production-main seed/reuse remain NOT-RUN until ordinary main pushes execute.
`phase.json` admits `trial`, `off`, or `adopted`. Adopted enables the separate
[main policy](main_policy/policy.py) only for validated pushes to this repository's
`main`. Every PR/fork, other branch/event and the optional trial pair are disabled
for production caching. Trial and main use different namespaces and receipts.

The completed trial, retained here for reproduction, behaved as follows in
`trial` phase (inactive in the adopted configuration).

Only a same-repository pull request whose head is `codex/native-cache-trial` may
produce this experiment. Main, fork PRs and unrelated branches run their existing
native checks without a cache action. The cold producer is the original required
native job. The optional warm job waits for **both** original macOS jobs, keeping
the original maximum of two heavy compiles. Each native job retained 60 minutes
in that historical trial. The current producer-only exception is described below.
No extra runner type, permission, token, repository setting or paid storage is used.

Cold starts with an absent/empty owned root target and requires a unique exact-key
miss. The cold lookup uses one bounded anonymous public GitHub REST request,
without a ref filter, and requires HTTP 200 with integer total_count=0 and an empty
actions_caches array. This proves repository-wide key-prefix absence; network,
HTTP, redirect, size or schema failures stop before compiling. A cache action
warning cannot masquerade as a verified miss. No token or permission is added.
The key includes source SHA/tree, toolchain, native build environment, full
manifest/lock/config/workflow/catalog digest, OS/architecture, image version, run
ID and attempt. It has no restore prefixes. Checkout and Cargo mtimes/fingerprints
are read, never normalized or modified by this experiment. Normal mutation tests
still restore source bytes using their original behavior.

The original native commands, order, environment, profiles, flags, step budgets and
reports are preserved. Both lanes run all workspace, probe, appearance, formatting,
three production semantic mutation-red/restored-green and 594-frame motion gates.
Nothing skips on a hit. A complete byte hash of the saved target is verified after
warm restore, before any native command. This detects accidental corruption;
producer trust still depends on the same-repository branch and ordinary PR scope.
The fixture tests exercise the actual CI-called boundary implementation, with tiny
Git checkouts and stub toolchain executables. They do not establish Rust/GPU or
hosted cache behavior.

Only after every gate and the existing timing report pass does the producer check
restored sources, mutation/motion receipts, target integrity and the 4 GiB logical
cap. It uses split official cache v6.1.0 actions pinned to
`55cc8345863c7cc4c66a329aec7e433d2d1c52a9`. The cold REST step and each cache action have a four-minute
limit within the existing job limit. Green save alone is insufficient: a second
lookup-only exact hit must succeed before the producer is green. Warm restore also
requires literal `cache-hit=true`, equal primary/matched keys, and verified saved
bytes. Missing receipts, an unavailable service, partial restore, wrong image/key,
size breach or corrupt target stops the pair before a fallback cold warm build.
Warm never saves a second entry.

`NVWA_NATIVE_CACHE` JSON lines retain source/config/toolchain/image identity,
logical bytes, integrity digest, gate receipts, cache outputs and helper wall time.
Semantic receipts reread the actual retained red/green logs, verify their recorded
hashes, intended assertion/test, one-test failure and restored pass; each emitted
receipt contains only allowlisted semantic fields and hashes.
Existing `NVWA_CI_TIMING` records retain every command and exit. GitHub step start/
end timestamps measure whole lookup/restore/compress/save/verify steps; do not add
nested helper observations to enclosing durations. Preserve raw logs and external
cache API receipts (ID/key/ref/version/size) before deleting exactly the owned
entry. A green action or lagging repository usage counter is not a storage receipt.
The original timing queue validator intentionally accepts only its three original
jobs. The external trial observer must validate the full four-job inventory and
both warm prerequisites, then pass only original jobs to that unchanged validator.

For cold no-cache work `C0`, cold miss lookup `Rc`, save plus cold verification `S`,
and total warm work `W` including restore/integrity verification:

- Warm gain = `C0 - W`; percentage = `(C0 - W) / C0`.
- One-reuse net gain = `C0 - W - Rc - S`.
- Require warm gain at least 20% **and** 600 seconds, plus one-reuse net gain at
  least 600 seconds. All identity, storage and correctness guards must pass.

Report raw job work, original-command wall and cache overhead separately. Keep
queue and dependency waits separate. Include the conservative complete cache
boundary overhead (cold preparation, lookups, source/target verification and save)
in the net calculation; do not hide observer/setup costs in a favorable baseline.
One pair establishes bounded feasibility only. It cannot establish ordinary
changed-source reuse, statistical speedup, or equal whole-workflow gains.

Execution budget: one cold/warm pair; at most one final revised PR run if a
conclusion changes source; then natural main CI. No retry, second cache save,
profile change, asset/model download or unbounded experiment is authorized here.
Root must obtain independent review before publication and decide adoption from
receipts. If thresholds/guards fail or evidence is incomplete, use phase `off` and
record NO-ADOPT or INCONCLUSIVE without enabling default caching.

Focused portable controls (no Cargo compile):

```sh
python3 -B scripts/check-portable.py native-cache-contract
python3 -B scripts/check-portable.py runner-contract ci-timing-contract
```

The tests freeze the whole original workflow after explicit trial additions are
removed, retain the original run-body hashes and three-job policy counts, and
require exact original native step-body/configuration parity in the warm lane.

The new portable cache controls run before the existing final `frozen-upper-arm`
group. That legacy group regenerates three tracked retained reports:
`results/runtime-directions.json`, `results/native-skeletons.svg`, and
`results/web-skeletons.svg` under experiment50. Generated bytes can differ across
platforms. Its original terminal position and the original observer boundaries
remain intact; the timing report still rejects mixed source identities.

The ordering regression runs the actual frozen group, actual nine cache controls
in both Python modes, production timing shells and the real report in a disposable
checkout. A harmless retained-JSON whitespace difference emulates generated-byte
variance: the actual generator removes it and leaves the fixture dirty. The old
trailing-control order fails the identity report; the shipping order passes with
all observations made before the final regeneration. This is controlled causal
evidence; the exact generated Ubuntu bytes from the failed initial run are
UNKNOWN. No generator, retained artifact or identity assertion is changed.

The retained [hosted motion summary](fixtures/motion-summary-run39518452707.json)
and its [provenance manifest](fixtures/motion-summary-run39518452707.manifest.json)
come from run39518452707/job118960012261. The producer emits 594 matrix samples
(3 body settings ×3 face settings ×2 clips ×33 times), plus 16 seek and 2 pause
checks for the neutral recipe, then one complete marker. `run_matrix.py` therefore
reports **613 total events and 612 successful checks**, while checker coverage
separately requires exactly **594 expected/observed samples, 30 expected/observed
deep keyframes, 3 body variants, 3 face settings, and no missing samples**. The
trial validates all of these with strict integer/boolean/list types. Missing,
extra, partially passing or inconsistent evidence cannot prepare a cache save.
The original probe, checker and native commands remain unchanged.

Every authorized finish attempt first emits a `target-size` receipt from a stat-only scan of
the complete owned target. It counts regular file bytes and symlink payload bytes,
regular files, links, directories and entries without following links or reading
file contents. The scan is bounded to 30seconds and one million entries; scan
failure is explicitly `complete=false` and never presented as the full size. A
complete receipt precedes source, gate or cap rejection. Oversize receipts retain
the full total rather than stopping at the first file above 4GiB. Hashing runs
only after a complete scan fits the unchanged cap and all gate receipts pass.
A measurement does not authorize saving a failed or oversized target.

Cold finish also requires its receipt marker to be absent. It encodes the exact
marker payload and verifies `measured logical bytes + actual marker bytes` against
4GiB before writing. This includes symlink payload bytes and does not rely on the
older regular-file reserve alone. `target-save-size` and successful `finish`
receipts retain `marker_bytes`, `marker_added_bytes`, and
`full_saved_logical_bytes`; warm adds zero marker bytes and never saves again.
Near-cap filesystem controls cover sparse files, internal symlink payloads and a
large receipt, with a test-only small cap injected into the production CLI entry.
Production has no cap override and retains the exact 4GiB bound.

## Main-only immutable seed policy

Main admission checks the actual push payload repository, fork=false, ref, deleted
flag and after-SHA against the clean immutable checkout. Compatibility binds
all tracked manifests/locks/toolchain/config/build scripts; native non-Rust
embedded inputs, vendor inputs, assets and examples; workflow, script/catalog,
checker/mutation and helper code; actual compiler/linker/SDK metadata, runner
image, Rust toolchain, build environment, and archive runtime. Ordinary Rust
source is excluded from the compatibility key, while build scripts and the
matrix gate producer remain included. Current and stored producer SHA/tree/run
identities are separate receipts. Original source mtimes remain natural; Cargo
rechecks source changes and every original gate executes on both dispositions.

The one fixed key is `nvwa-native-main-seed-v1-<compatibility-SHA256>`. There are no
restore prefixes or latest searches. An exact restored action key, bounded main
marker, full inventory and exact main-ref API ID/key/version/stored-byte receipt
are required for `VERIFIED_RESTORE`. A PR trial entry cannot satisfy these checks.
Unknown/partial/corrupt/nonexact restore becomes `CLEAN_FALLBACK` only after safe,
owned-target-only, descriptor-relative deletion and an empty-target assertion.
Unsafe cleanup stops before original gates. Stock empty hit outputs do not prove
an ordinary miss; the precise action outcome/outputs remain in the receipt.

Only an independently absent immutable seed can be saved, after every original
gate, restored sources, complete target sizing and exact marker-byte cap proof.
Consumed seeds never save again. Unknown service state or an existing but
unusable entry cannot authorize a replacement. Every activated final path still
validates full target size, source restoration and actual mutation/matrix gates.
Save plus lookup-only and exact main API proof produces `VERIFIED_PERSISTED`;
cache-only failures produce explicit `NOT_PERSISTED_UNKNOWN` while product gates
keep their real result. A persistence lookup proves existence, not that this
run authored the blob; remote producer stays UNKNOWN until its marker is
verified on restore. No permission, token, settings or paid-storage changes.

The main policy captures SDK/compiler identity once per job and checks the same
consumer, key/version, owned checkout and build environment at later boundaries.
Known SDK selection is recorded and checked: absolute SDKROOT must resolve to
the queried macOS SDK; absolute DEVELOPER_DIR must resolve to a Developer root
containing the actual selected toolchain and SDK; MACOSX_DEPLOYMENT_TARGET must
be a strict numeric version. These checks change no selection, default or flag.
Unsupported or missing identity disables caching honestly. Each action retains
4minutes; the full logical cap remains4GiB. The accepted 2026-10-29 exception
raises only the current `native-and-wasm` producer to75minutes; the inactive
optional warm trial remains60minutes. Mutation and full matrix steps retain12
and20minutes. All commands, assertions, one-worker settings, phase, cache
selection, trust and key algorithms remain unchanged. The three independent
workflow contracts admit the exact current75/60 producer/warm pair, then reverse
only the producer cap and matching matrix comment to historical60 for the
original hashes and full-step parity checks. Changed compatibility inputs can
require a new cold main seed; old-seed reuse or a speedup is not established.
A75-minute cap is not a completion guarantee or authority for another increase.
`NVWA_NATIVE_MAIN_CACHE` lines retain policy state, API/action receipts, target
size, gate results and complete helper wall. Use enclosing GitHub step timings
for total cost, without double-counting nested receipts.

Unknown main API receipts retain a safe error category. HTTP failures also retain
an integer status and, when strictly valid, the GitHub request ID, remaining rate
count, reset epoch and retry delay in seconds. A 403 means `http_forbidden` here;
it does not establish rate limiting. Error response bodies, URLs, exception text
and other headers are never included. Error bodies are not read, and responses
are closed. Missing, duplicate, malformed or oversized diagnostic values are
omitted. Transport timeout, TLS, DNS and response-validation failures have fixed
categories. All remain `known=false`, authorize no save and introduce no retry.
Restore fallback keeps its original `api` admission snapshot and adds
`recheck_api` only when the post-restore lookup ran. The exact HTTP status and
cause of historical run39546704999 remain UNKNOWN; these diagnostics apply to
future observations and do not revise retained evidence.

The separate `native-main-cache-contract` portable group runs normal/-O controls
before the legacy final report generator. It does not amplify the retained trial
ordering regression. Its tiny offline Cargo control compiles and runs actual
changed source with natural mtimes in its own temporary target, with no packages
or downloads. This proves source invalidation behavior only, not cache speed.

```sh
python3 -B scripts/check-portable.py native-main-cache-contract
```

One immutable seed can grow old as ordinary sources change. Cross-commit main
reuse, future hit rate and whole-workflow savings remain unmeasured. Image or
compatibility-input changes create a new seed; repository eviction may also
remove a seed. There is no refresh-on-hit, fallback-key search or benchmark loop.

Restore inventory admits only strictly resolved internal regular-file links;
dangling, looping, directory or escaping links cannot qualify as a verified
restore. Python versions that report symlink loops differently fail the same
closed check. After descriptor-relative target deletion, no-follow checks reject
any replacement, including a link to an empty outside directory. Local controls
inject both failures into the actual restore boundary and preserve outside
sentinels. Fixtures live in owned neutral physical temporary directories, while
an explicit owned ancestor-config fixture must still disable production caching.
