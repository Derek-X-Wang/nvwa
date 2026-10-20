# Native compiled-target cache trial (#106)

Status: **TRIAL / NO ADOPTION DECISION**. Default main caching remains off.
`phase.json` admits `trial`, `off`, or `adopted`; only `trial` has an implementation.
`adopted` deliberately enables nothing until separate authorization and review.

Only a same-repository pull request whose head is `codex/native-cache-trial` may
produce this experiment. Main, fork PRs and unrelated branches run their existing
native checks without a cache action. The cold producer is the original required
native job. The optional warm job waits for **both** original macOS jobs, keeping
the original maximum of two heavy compiles. Each native job retains 60 minutes.
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

The ordering regression runs the actual frozen group, actual eight cache controls
in both Python modes, production timing shells and the real report in a disposable
checkout. A harmless retained-JSON whitespace difference emulates generated-byte
variance: the actual generator removes it and leaves the fixture dirty. The old
trailing-control order fails the identity report; the shipping order passes with
all observations made before the final regeneration. This is controlled causal
evidence; the exact generated Ubuntu bytes from the failed initial run are
UNKNOWN. No generator, retained artifact or identity assertion is changed.
