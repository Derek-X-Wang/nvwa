# 50 — One fixed upper-arm neutral A/B

**The frozen candidate meets its source-direction gate and reduces the measured
inward-arm crossings on this retained sample. Production policy is unchanged.
Motion quality remains HOLD.** This is the bounded comparison requested by
issue #68, not an adoption or a new generation run.

## Frozen intervention and preservation

[CONTRACT.json](CONTRACT.json) was written before candidate evaluation. It fixes
all 90 input keys, runtime keys `0/15/30/45/60/75/89`, lowered-arm comparison keys
`0/75/89`, static neutral, physical sides and tolerances. For exactly the two
upper-arm local rotation channels:

```text
C_j = F_s,j * transpose(F_t,j)
R_candidate,j = C_j * R_baseline,j
```

The constructor rejects a changed pinned hierarchy, static source metadata or
calibration frame. Both upper arms have chest as their immediate parent. The
entire static chest ancestor chain has identity rotation and unit scale. The
source static rest rotations are identity. The source and target static frames
use their pinned +Y up / +Z front conventions and projected-front guide.
This formula is not generalized to an intermediate scaled or sheared parent.
Animated key 0 never supplies neutral.

Source `LeftArm` remains fixture `upper_arm.R` (physical left, positive X).
Source `RightArm` remains fixture `upper_arm.L` (physical right, negative X).
No label renaming, reflection or side swap occurs. The fixture bind pose,
complete GLB JSON, skin data, every other local TRS and root handling remain
exact. Only 2,459 binary bytes differ, all inside the two allowed 90-key
rotation channels (2,880 bytes). Descendants inherit their corrected parent
once through ordinary hierarchy propagation. Experiments 41–49 and the
original assets have no tracked changes.

The isolated [candidate Work](artifacts/genuine44-upper-arm-neutral50.nvwa.json)
uses profile `nvwa-experiment50-upper-arm-neutral-ab`; the retained clip identity
and original provenance stay explicit. Its [GLB](artifacts/assets/generated/genuine44-upper-arm-neutral50.glb)
SHA256 is `2779b012405a915cbc84b38dc18e5eb7a91215661b54ac0c7753ecebb49feae7`.
No per-key fitting, rounded Euler offset, descendant correction, model,
inference, download, new tool, extra machine or paid resource was used.

## Numeric gate and retained controls

Expected upper-arm directions come from the prior independent source quaternion
FK and source joint origins. Actual target directions come from complete glTF
affine FK and actual upper-arm/forearm origins, then the full chest affine
inverse. Neither expected direction uses candidate correction matrices.

| Gate | Limit | Measured maximum |
|---|---:|---:|
| 180 upper-arm unit-vector component errors, all 90 keys | `2e-6` | `2.828015423228525e-7` |
| Same direction angles | `0.001°` | `1.7704227144513012e-5°` |
| Target pelvis versus source Hips world position | `2e-6 m` | `7.375408506149483e-9 m` |
| Actual captured candidate directions, native and Web | same direction limits | `2.2298422014399577e-7`, `1.6221699278780337e-5°` |

Correction matrices are proper rotations. Serialized quaternion norms satisfy
the existing explicit glTF tolerance; all untouched local channels/root are
exact. A final exact candidate-byte check also rejects added per-key roll that
would leave longitudinal direction within tolerance. This tightens the
candidate identity; it does not fit a new candidate.

The two [static-neutral controls](results/numeric.json) are distinct from key 0.
Baseline bind differs from source static upper-arm directions by about
`45.7252°`. Corrected source-rest control residuals are below `0.0000127°`.
Both static-neutral surface controls have zero strict crossings.

Twelve constructor/FK/control tests pass normally and under `-O`. Reversed
multiplication, double correction, descendant correction, wrong physical sides,
duplicated root, animated key0 neutral, changed parent, changed chest frame,
changed static frame and extra per-key roll are all rejected. Restoring the
fixed candidate passes the complete 90-key gate. Five additional runtime
adapter tests reject swapped Work identities, changed descendant/root data and
a changed exact key, normally and under `-O`. Sixteen empty, truncated, failed or wrong-platform
capture mutations are also rejected by the actual runtime summary entrypoint,
with no PASS output written; restored complete pairs pass normally and under
`-O`. Failed GLBs remain privately in
`.work/m2-neutral-ab/failed-controls/`; their hashes and rejection reasons are
retained in [control receipts](results/controls-normal.json).

## Same-key surface and joint observations

The unchanged experiment49 metric counts strict noncoplanar triangle surface
crossings between arm-weighted and torso-weighted partitions. Every triangle
vertex must have at least 0.8 actual total weight in its named node set. Strict
segment/barycentric epsilon is `1e-8`; determinant threshold is `1e-14`.
Containment, coplanarity, transition triangles and lower-weight surfaces remain
excluded. The old metric's `left_arm_weighted` name means nodes `4/3/2` (fixture
`.L`, physical right); `right_arm_weighted` means nodes `7/6/5` (physical left).
No metric or partition was changed to favor the candidate.

| Exact key | Baseline total | Candidate total | Candidate physical right / left |
|---:|---:|---:|---:|
| **0, predeclared lowered** | 397 | 156 | 87 / 69 |
| 15 | 295 | 62 | 0 / 62 |
| 30 | 349 | 69 | 0 / 69 |
| 45 | 356 | 64 | 0 / 64 |
| 60 | 353 | 66 | 0 / 66 |
| **75, predeclared lowered** | 416 | 121 | 57 / 64 |
| **89, predeclared lowered** | 454 | 197 | 130 / 67 |

No sampled side/key has an increased count. Crossings remain on every sampled
key. A lower count is not a claim about penetration depth, contacts, anatomy or
semantic quality. [All 90 numeric samples](results/numeric.json) retain source,
baseline and candidate joint directions, elbow deflections and descriptive
neutral excursions; all 18 signed primary/secondary joint gauges are recorded
at the seven runtime keys. Candidate versus baseline elbow-deflection change
is at most `0.00000628°`; source/target elbow deflections still differ by several
degrees. There are no certified anatomical joint limits, so no joint-limit pass
is claimed. Projected-front roll and leaf markers are authored gauges, not
recovered anatomical twist, palm normals or hand contact planes. Relative-neutral
excursion is descriptive because baseline and candidate have different neutral
objectives. The prompt remains “A person stands in place and waves their right
hand”; a general semantic or human quality pass has not been established.

## Build, launch, numerical replay and visual evidence

Two heavy builds ran sequentially through Wefty on the one existing local owned
node, with installed dependencies and `--offline --locked`. Native took
34.04 seconds; Web took 67.84 seconds. Actual snapshot receipts are
[build-native.json](results/build-native.json) and [build-web.json](results/build-web.json).
These are build results, not performance benchmarks.

The new probe copies experiment49's unchanged production-graph capture logic.
Its only Rust differences accept the explicit baseline/candidate profile IDs
and change the diagnostic window label. Both variants used the same native
binary and the same Web Wasm. Each native and Web run actually loaded its exact
Work and captured all seven post-animation/post-propagation samples. All four
[comparisons](results/) pass the unchanged experiment49 local/global/skin
thresholds through an explicit new-asset identity adapter. Local TRS and inverse
binds match exactly; maximum global residuals are below `1.76e-7`, and CPU-skin
residuals against actual captured matrices are below `1.52e-7 m`. Native and Web
node local TRS/global matrices are typed binary64 bit-exact for each variant.

The initial native CUA screenshots were observed inline. A separate supported
product `--capture` run then saved actual native GPU canvas PNGs, without a
rebuild, OS capture workaround or undocumented CUA filesystem access. Each
visual recapture completed seven keys, reported GPU capture completion and
`animation_seconds=2.9666666984558105` (key89), wrote a fresh nonempty PNG and
exited 0. Web raw JSON and actual canvas PNGs were downloaded through the
advertised page controls. The final native and Web canvases were inspected.
At key89 the candidate's arms are visibly outside the torso; baseline arms are
largely inside it. This does not establish all-pose surface quality.

| Actual final key89 canvas | Baseline | Candidate |
|---|---|---|
| Native GPU export | [PNG](results/native-baseline-canvas.png) | [PNG](results/native-candidate-canvas.png) |
| Web actual canvas | [PNG](results/web-baseline-canvas.png) | [PNG](results/web-candidate-canvas.png) |

[Native](results/native-skeletons.png) and [Web](results/web-skeletons.png)
seven-key skeleton diagrams were inspected for regressions. They are CPU
drawings of actual captured joint origins at one fixed world projection and
scale, not screenshots, mesh renders, alignment fits or replacements for the
actual runtime images. The root/pelvis diagnostic segment is drawn too.
No pixel-equality or formal performance claim is made.

The six existing original source-cache texts were freshly read and matched
pinned SHA256, byte counts and archived URL receipts. This verifies the retained
metadata convention; official decoder execution parity and arbitrary rigs
remain unverified. The [post-build diagnostic record](results/post-build-diagnostics.json)
identifies one Python evaluator tightening after the build. Its exact build-time
bytes are retained and match both actual build receipts. Rust, Cargo, probe,
Work and GLB inputs did not change; no retrospective rebuild is claimed.

These are historical captures of the production-source snapshot at base
`50eae1979cac47c7eb53dada69f06b716436bf92`, before StageA. The capsule does not
claim that later changed Studio/runtime code was launched. Its offline gates
bind retained source, calibration, Work and GLB inputs; actual build receipts
bind historical product sources. Later stage evidence must be reported separately.

## Decision and cleanup

This comparison supports the bounded hypothesis that the fixed neutral objective
contributes to the observed inward-arm result. It does not establish sole
causality or justify production adoption. Keep the candidate isolated, quality
HOLD and production policy unchanged pending separately reviewed adoption and
an authorized human trial. #12/M2 remains open, #3 remains blocked, #4 retains
its gaps, and #49's unassisted trial remains separate.

All four native runs exited 0. Both owned Web tabs closed. The bounded loopback
9204 server stopped and has no listener. Other apps/tabs/servers were not changed.
The two-build limit was respected. Build-cache and graphics leases were returned
to root. Temporary stages, original launchers, logs, failed candidates and build
outputs remain privately available; no renderer or service remains owned here.

**VERIFIED — Frozen 90-key direction/byte gate, mutation-red/restored-green
controls, actual native/Web seven-key playback/skeletons, same-key GPU canvases,
and owned process/tab/server cleanup. Quality HOLD; production adoption and
human semantic validation NOT-RUN.**
