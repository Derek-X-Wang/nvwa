# Same-key direction attribution

The declared source T-pose→target A-pose neutral correspondence explains the
measured inward upper-arm **bone directions** in this retained clip. It is a
chosen relative-neutral-motion policy effect, not a proven implementation bug
against experiment47's policy, a sole explanation of the visual HOLD, or an
approved fix. Motion quality remains HOLD.

The direction change exists in actual joint transforms before skin weights
are applied. A weights-only explanation cannot account for it. Fixture
geometry, weights, omitted source translations and terminal roll can still
affect the visible result. This experiment does not rank those remaining
causes or certify source motion quality.

## Portable reproduction

From the repository root, Python3 standard library only:

```sh
python3 experiments/49-runtime-pose-parity/attribution/directions.py
python3 -O experiments/49-runtime-pose-parity/attribution/directions.py
python3 experiments/49-runtime-pose-parity/attribution/directions.py --capture web
python3 experiments/49-runtime-pose-parity/attribution/test_port.py
python3 -O experiments/49-runtime-pose-parity/attribution/test_port.py
```

The default reproduces numerical measurements from pinned repository inputs
and the already-retained native capture. `--capture web` uses the retained Web
capture. It launches no runtime and changes no captured evidence. Each CLI run
creates a fresh directory under ignored `.work/runtime-pose-attribution-check/`
and prints the output path. `--output` accepts a fresh file elsewhere; existing
files and the retained attribution directory are protected from overwrite.
The script resolves repository inputs from its own location, so invocation by
absolute path from another working directory also works.

**Default source-text audit: NOT-RUN.** Numerical mode checks pinned repository
bytes and archived source URL/byte/hash receipts. It does not read upstream
source text or claim that retained source conventions were freshly inspected.
For an optional fresh byte audit of an existing six-file cache:

```sh
python3 experiments/49-runtime-pose-parity/attribution/directions.py --source-cache /existing/pinned/source-cache
```

This only reads those six files and checks their pinned SHA256/length against
archived exact-URL receipts. It never downloads, discovers another cache,
traverses a model directory or executes provider/model code. A missing or
changed cache fails. Source-text audit status is recorded separately from
numeric reproduction. Official decoder/runtime parity remains NOT-RUN even
when this cache audit passes.

## Measurement and existing policy prediction

`directions.py` performs source parent-local quaternion forward kinematics
(FK: compose joint rotations and offsets along the hierarchy) from raw44 and
pinned41 metadata. It imports neither the mapper nor the offline49 evaluator.
Target upper-arm directions use actual captured upper-arm→forearm joint-origin
differences. Forearm→hand directions provide an additional check. The existing47
signed affine markers agree with these28 actual child segments within
`2.52694e-5` degrees.

The comparison removes each actual chest transform. Source uses the transpose
of its global chest rotation. Target uses the full inverse of its captured
chest affine basis, then normalizes the vector. Translation and bone length
do not affect the resulting unit direction. Nothing is fitted from output.

Unchanged static geometric frames from47 are `F_s` and `F_t`. Their upper-arm
longitudinal directions differ by`45.72523°`: horizontal source T-like arms and
downward target A-like arms. The following predicts the **existing mapping**;
it is not an alternative mapping or runtime intervention:

```text
EXISTING_POLICY_PREDICTION = normalize(F_t * transpose(F_s) * source_body_direction)
```

Across all14 upper arms at the seven keys, the prediction matches actual
native body-relative target directions within`2.60020e-7` maximum component
error and`1.81515e-5°`. The retained Web measurements reproduce the same sample
values exactly. After the declared neutral change, upper-arm directions agree.

At key0, source upper arms have moved about70° down from horizontal neutral.
Applying that excursion from a target neutral already about45.7° down puts
the target upper arm past vertical and inward. The existing47 physical-side
decision maps source Right→target `.L` and Left→target `.R`; no side is renamed
or selected here. This accounts for the bounded direction mechanism. It does
not establish that the chosen correspondence is the desired product behavior.

## Same-seven-key body directions

Unit vectors are in each current chest's frame. Negative X is physical right;
positive X is physical left. Source uses raw44 FK; target uses actual49 joints.
Both retained native and Web produce these values.

| Key | Source Right upper arm | Actual target `.L` | Source Left upper arm | Actual target `.R` |
| ---: | --- | --- | --- | --- |
|0 |(-.339,-.941,.004) |(.437,-.900,.004) |(.346,-.938,.014) |(-.430,-.903,.014) |
|15 |(-.839,.105,.534) |(-.661,-.527,.534) |(.392,-.920,.020) |(-.385,-.923,.020) |
|30 |(-.770,.358,.528) |(-.794,-.301,.528) |(.379,-.924,-.047) |(-.397,-.916,-.047) |
|45 |(-.755,.361,.547) |(-.785,-.289,.547) |(.387,-.922,-.017) |(-.389,-.921,-.017) |
|60 |(-.946,-.086,.313) |(-.599,-.737,.313) |(.406,-.914,-.027) |(-.371,-.928,-.027) |
|75 |(-.470,-.883,.001) |(.304,-.953,.001) |(.364,-.931,.042) |(-.413,-.910,.042) |
|89 |(-.348,-.936,-.060) |(.427,-.902,-.060) |(.361,-.933,.013) |(-.416,-.909,.013) |

Source Left X changes sign in all seven target samples. Source Right X changes
sign at0/75/89, when that arm is lowered. These are joint-direction facts, not
a claim that the policy alone causes every visible surface crossing.

Elbow deflection remains descriptive: source Right at key30 is75.31° and
target `.L` is78.07°; at key0 they are34.10° and37.33°. Forearm global neutral-frame
differences are not implementation failures: hierarchical parent-local transfer
does not promise independent global neutral-gauge equality at each descendant.

## Source convention and authority boundary

The [experiment47 source reference](../../47-fixture-rig-calibration/reference/REPORT.md)
binds original-source claims to immutable URLs, SHA256 and original line numbers.
The private predecessor additionally read the six exact cached originals and
verified their hashes and archived receipts. The retained public record preserves
that provenance. Default reproduction does not repeat that source-text reading.

| Retained primary source | Original lines | Established convention or limit |
| --- | --- | --- |
| `cpp-src__motion_decode.cpp` |7–12 | Provider computes child-local orientation as transpose(parent-global) times child-global, and emits XYZW quaternions. |
| `cpp-scripts__export_glb.py` |35–49,117–126,197–206,216 onward | Provider exporter uses translation-only identity-rest nodes/inverse binds and writes raw rotations into local glTF channels. Root rest height differs but does not affect direction measurement. |
| `cpp-src__skeleton.hpp` |45–67 | SOMA30 names, parents and offsets. Original trusted-container bind extraction remains a provider claim. |
| `official-output-formats.md` |26–28 | Internal SOMA zero pose is standard T-pose; public77 export and internal30 layout differ. |
| `cpp-src__motion_rep.cpp`, `official-skeleton.md` |As bound in47 reference | Additional retained source identities; no official decoder execution is implied. |
| `experiments/47-fixture-rig-calibration/calibrate.py` |292–336,377–407 | Source identity rest→exact target bind and static geometric gauges are authored engineering choices. |
| `experiments/48-genuine-fixture-work/export.py` |109–119 | Retained frames call the pinned47 mapper before quaternion sign continuity and binary32 serialization. |

This supports source FK against the actual provider contract. It does not prove
original NVIDIA decoder parity, original official SOMA bind/surface fidelity,
anatomical quality or prompt fulfillment. No new inference, export, reweighting,
rendering, compilation or asset replacement was performed.

## Retained evidence and validation

- `retained-native-directions.json`: adapted native record; all original numeric
  values preserved. Absolute source-cache keys become `cached-original-source/`
  aliases. Prediction-field names now describe the existing policy.
- `adaptation-receipt.json`: private predecessor hashes, exact alias/field-change
  rules and digest of all3330 unchanged numeric leaves.
- `capture-rebind.json`: prior/current capture identities, actual frame counters,
  preserved pre-rebind attribution manifest and exact numerical comparisons. Native
  capture/golden bytes remain unchanged; rebuilt Web capture bytes are newly bound.
- `input-pins.json`: repository input/capture identities.
- `verification.json`: normal/optimized native and Web reproductions, optional
  existing-cache audit and11 port controls. The original four numeric controls
  remain active without Python assertions.
- `SHA256SUMS.json`: public file identities.

Counts per capture:7 keys,126 signed primary directions,28 actual child-segment
checks,14 elbow comparisons and14 upper-arm policy predictions. Source cache
receipt count6 is archived provenance; a fresh six-file byte audit occurs only
when `--source-cache` is supplied. Capture schema/key/type, input pin, missing
cache, output protection and exact retained-sample reproduction controls pass
normally and under`-O`. Numeric matching does not clear quality HOLD or authorize
a correction.

The capture rebind preserves the complete previously reviewed attribution privately.
Current Web source SHA256 is
`161442516dfb5d62476b3f3b2ab52f7b2b9f44a7177bcb2ae5ac978208f52e5f`,
with actual frames10/12/14/16/18/20/22. All3330 numerical leaves retain digest
`c564ad7a421adacc7e18515a5eaf1f1d41d7f992cb874a21dcc083779196d7f4`.
Both fresh reproductions match the preserved sample values exactly. The168
native/Web GLB-node comparisons have zero local/global component difference.
This is a new capture-provenance binding, not a relabeling of old raw observations.
