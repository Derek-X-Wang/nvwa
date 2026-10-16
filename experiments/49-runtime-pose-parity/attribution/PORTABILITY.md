# Retained-sample numerical reproduction contract

This contract concerns derived angle calculation across Python hosts.
This changes only the retained-angle reproduction rule. It does not change
pose/skin comparison tolerances or motion-quality gates.
The evaluator, golden record and captured inputs remain unchanged.

## Measured source

The full actual Ubuntu diagnostic stdout is retained byte-for-byte in
`portable-ubuntu-measurement.json`. Its adjacent receipt binds the file SHA256
and source run38855376620, job116825528453, head8853854 and merge
`f6080b726a601c0b7f6982a53d4a91f3b07ada0c`. The host was Ubuntu24.04.5 with
CPython3.12.3. The diagnostic remains a measurement tool with no acceptance
threshold or PASS waiver.

Against the retained Mac golden, native and Web each differ at 55 of 3311 float
leaves. All 55 are derived angle scalars: 52 differ by one binary64 ULP and 3 by
two ULP. Maximum absolute difference is`2.842170943040401e-14` degrees. Vectors,
positions, discrete values and structure have zero differences. Native versus
Web is exact. These facts are measured on that particular host/run, not a
prediction that every future platform will produce the same differences.

An ULP is one step between adjacent IEEE754 binary64 encodings at that value.
The bound uses encoding distance rather than a broad absolute-error floor.
This matters for near-zero angles: the measured differences there are about
`1.7e-21` to`3.4e-21` degrees, not an allowance of`2.84e-14` at every angle.

## Allowed retained-angle paths

`test_port.py` calls `assert_retained_samples` in
`reproduction_comparison.py`. At most two binary64 ULP are permitted only at
these existing float scalar locations in the seven positional samples:

| Location within each sample | Exact enumerated field names |
| --- | --- |
| `directions` for the 18 fixed target joints | `raw_world_angle_deg`, `neutral_world_angle_deg`, `neutral_gauge_direction_error_deg`, `source_excursion_from_declared_neutral_deg`, `target_excursion_from_declared_neutral_deg` |
| `directions` for `upper_arm.L`, `forearm.L`, `upper_arm.R`, `forearm.R` | `marker_vs_actual_child_angle_deg` |
| `directions` for `upper_arm.L`, `upper_arm.R` | `body_relative_world_angle_deg`, `actual_vs_existing_policy_prediction_angle_deg` |
| `elbow_and_reach` for `Left`, `Right` | `source_elbow_deflection_deg`, `target_elbow_deflection_deg` |

The 18 fixed targets are root, pelvis, spine, chest, neck, head, upper arm,
forearm, hand, thigh, shin and foot, with the exact `.L`/`.R` spellings in the
helper. These ten field groups are explicitly enumerated. A `_deg` suffix
does not add a field to the allowance. New/unknown angle paths fail, including
an unknown angle added to both reference and actual comparison arguments.

`source_neutral_elbow_deflection_deg` and
`target_neutral_elbow_deflection_deg` remain exact: they had no observed
cross-host differences. Three ULP at an allowed field fails. Known angles must lie in [0,180] degrees
on both sides before exact or ULP comparison. Tiny negative subnormals and values just above180 therefore fail.
Float sign changes, including positive-zero/negative-zero changes, fail even
within the ULP bound.

## Exact boundaries and controls

Everything else is exact: object key sets **and order**, list length/order,
scalar types, discrete values, source key/time, all vector components and
positions. Every float must be finite on both sides, including the reference.
Native/Web agreement calls `assert_exact_samples`, allowing zero differing
float bits even at the enumerated angle fields. Input pin checks remain the
unchanged evaluator's checks.

The existing CI commands run all 21 tests normally and with`-O`:

```sh
python3 experiments/49-runtime-pose-parity/attribution/test_port.py
python3 -O experiments/49-runtime-pose-parity/attribution/test_port.py
```

The same comparison called by retained-sample verification also receives the
mutation controls. They exercise two-ULP acceptance and three-ULP rejection,
the full 55-difference actual Ubuntu replay, exact native/Web rejection of that
replay, one-ULP direction change, meaningful position change, schema/key order,
unknown angle fields, type flips, discrete/key/time/list changes, nonfinite
reference/actual values, the [0,180] angle range, sign and signed zero, exact
neutral-elbow angles, and one-ULP rejection in exact native/Web mode.
No Python `assert` statement controls acceptance; optimized mode keeps the
checks active.

The Mac currently reproduces the retained golden exactly. Ubuntu's measured
angle-only differences fit this narrowly stated reproducibility contract.
Passing these controls does not clear the motion-quality HOLD, establish
official decoder parity or authorize any mapping/asset change.
