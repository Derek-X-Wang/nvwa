# Local non-gating check-boundary pilot (#112)

This CLI performs historical identity admission and limited current-geometry
reconstruction on existing archived frames. It does not generate a fresh frame,
run Rust, change a required gate, replay the historical controls or certify a
platform. See [CONTRACT.md](CONTRACT.md).

Use an existing Python 3.12+ interpreter. No package, asset or tool download is
needed. The script resolves its source/asset root from its own location. Output
must be a fresh path; existing evidence is never overwritten.

## Historical identity

```sh
python3 -B experiments/88-check-boundary-pilot/pilot.py historical \
  --frame /absolute/path/to/original-historical-frame.json.gz \
  --out /absolute/path/to/new-historical-admission.json
```

The original compressed input must match
`5df0c97e5c51b3e71741e115ca4040d441189dd5853a505c1076d9ed0a53ae5e`.
It is currently unavailable. A missing file returns exit 2 and
`BLOCKED_MISSING_HISTORICAL_INPUT`. A different file is rejected, including the
later Mac frame with the same scalar. No alternate input is selected.

This pilot admits identity only. A real positive admission and historical
replay remain NOT-RUN without the original input. Original historical13 records,
current18 controls and their six-place assertions are preserved separately.

## Available current geometry

```sh
python3 -B experiments/88-check-boundary-pilot/pilot.py geometry \
  --captures /absolute/path/to/existing-linux-matrix/keyframes \
  --out /absolute/path/to/new-current-geometry.json
```

The directory must contain the 30 exact experiment60 frames listed in
`catalogue.json`. The admitted set covers three torso values, jaw0, two clips and
five integer times. Jaw endpoints, intermediate continuous times, seek and pause
do not have complete retained geometry in this set and remain unverified here.
An optional `--case t+1__b1_arm_rehearsal_v1__k16.json.gz` selects one named case.

The adapter reuses authenticated v1 source data and existing experiment84
arithmetic. It excludes experiment85's broader v2 asset constructor. It checks
recipe-derived rest, exact topology/support, weights and upload reconstruction
with the existing limits; it does not replace the original exact scalar check.
The batch also preserves exact captured bone-rest, mesh-rest, rest-normal,
full-weight and placement identity across poses of the same admitted profile
and recipe. This is a consistency check, separate from an absolute source-to-rig
oracle.

`PASS_LIMITED_CURRENT_GEOMETRY` refers only to this offline geometry scope.
`full_current_runtime` remains `NOT_VERIFIED_RIG_ORACLE`, and quality remains
HOLD. The captured-rig consistency check does not independently establish that
the rig was built correctly from its raw source.

## Derived payload controls

For one explicit `--case`, `--control-fault` selects a derived recipe, time,
profile, topology, rest, upload, weights or support fault after authentic input
admission. The receipt distinguishes the original template hash and derived
payload hash. A rejected fault exits nonzero. Run again with no fault and a new
output to verify recovery.

These are payload/admission controls through the local CLI. They are not Rust
production-source mutations. Original captures remain unchanged. All outputs
retain the original Linux normal failure and its optimized-control NOT-RUN gap.
Recipe/time controls must change zero-valued templates too. The focused suite
also exercises same-validator, different-pose invariance faults and restoration;
these controls do not rewrite the authenticated compressed inputs.

## Focused local tests

The two Mac arguments below are individual frame files, used only as historical
substitutes that must be rejected. They are not admitted as experiment60 geometry.

```sh
python3 -B experiments/88-check-boundary-pilot/test_pilot.py \
  --captures /absolute/path/to/existing-linux-matrix/keyframes \
  --mac-v1-frame /absolute/path/to/current19-baseline-v1/keyframes/t+1__b1_arm_rehearsal_v1__k16.json.gz \
  --mac-v2-frame /absolute/path/to/current19-baseline-v2/keyframes/t+1__b1_arm_rehearsal_v1__k16.json.gz \
  --out /absolute/path/to/new-normal-controls
```

Repeat with Python `-O` and a different new output directory for optimized-mode
controls. Each directory retains a test summary, actual failure/recovery receipts
and logs. A passing local suite does not mean historical replay or full runtime
qualification has passed. No command here runs the existing CI workflow.

Measured outcomes, independent-review findings and remaining gaps are recorded
in [RESULTS.md](RESULTS.md).
