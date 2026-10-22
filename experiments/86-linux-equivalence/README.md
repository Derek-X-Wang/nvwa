# Linux equivalence pilot

This experiment replays the two existing macOS CPU/source/Wasm inventories on
standard Ubuntu, against one immutable source commit. It does not change the
production workflow or its required checks. See [CONTRACT.md](CONTRACT.md) and
[RESOURCE-REQUEST.md](RESOURCE-REQUEST.md).

The bounded same-source run is complete: **B1 PASS, full native FAIL**. See
[RESULTS.md](RESULTS.md) for measurements, the exact garment assertion failure,
the separate local driver repair, and all unverified scope. No migration adopted.

## Reproduce the local runner controls

No Linux, network or Rust compilation is needed for these harness controls:

```sh
python3 -B -m unittest discover -s experiments/86-linux-equivalence -p test_run.py -v
actionlint .github/workflows/linux-equivalence-pilot.yml
```

## Inspect the exact replay plan

Use a checkout of `baa0b6bbda0d9709f0fab37c9e7d962fd8d926c1` for `--source`.
`plan` only reads it and prints the command inventory. It neither fetches nor
compiles. The output location must be supplied but is not created by `plan`.

```sh
python3 -B experiments/86-linux-equivalence/run.py plan \
  --source /absolute/path/to/frozen-baseline \
  --out /absolute/path/outside-source/unused-plan-location \
  --lane native-and-wasm
```

The second lane is `b1-source-regression`. The plans retain 24 and 23 original
commands respectively, plus 10 and 9 explicit locked dependency fetches. These
fetches separate acquisition from execution; they do not change lockfiles or
versions. The baseline's two B1 fetches remain in their original order after the
derived manifests are prepared.

## Execute on Linux

Actual execution requires Linux, Python 3.12+, repository Rust 1.95.0 and its
Wasm target. The frozen source must be a separate disposable checkout, because
the original mutation witnesses intentionally change and restore real source.
Never use a human editing checkout. Download/resource authorization is separate
from the local controls above.

```sh
python3 -B experiments/86-linux-equivalence/run.py run \
  --source /absolute/path/to/disposable-frozen-baseline \
  --out /absolute/path/outside-source/new-results \
  --lane native-and-wasm --max-seconds 3300
```

Outputs are never overwritten. Any failed command stops the lane; remaining
commands are `NOT-RUN`. Missing runtime receipts or changed tracked source/locks
prevent a pass. The source mutation tests must detect all three real faults and
pass after restoration. The motion matrix must validate 594 matrix samples,
16 seek controls, 2 pause controls, 30 retained deep frames and its completion
marker (612 passing records, 613 total). The source viewer must produce its
actual headless receipt.

The isolated workflow is branch-scoped and limited to two 60-minute jobs. It
records toolchain acquisition, per-command logs/timing, artifact bytes and both
source/harness identities. It uploads evidence, not build targets or caches.
There is no automatic retry or macOS rerun.

## Evidence boundaries

The existing portable job already ran on Ubuntu at this exact baseline; its
successful run is retained as reference. This pilot measures the other two
jobs. The original macOS run is
[39742202675](https://github.com/Derek-X-Wang/nvwa/actions/runs/39742202675).

Cargo test wall time includes compilation; category totals must keep that mixed
time explicit. Do not present it as pure test execution. The machines also have
different CPU architectures, so one cold observation cannot isolate an OS speed
effect or predict future queue delays.

Native/Wasm compilation and CPU/source checks do not validate browser rendering,
Metal, GPU output, real input methods, window/DPI behavior or app packaging.
Those remain separate checks at the relevant platform or version milestones.
No runner migration or macOS-frequency change is adopted by this experiment.
