# Shoulder source/upload diagnosis

**Source-limited / HOLD. No candidate correction.** The existing fitted sportsuit
and full-positive CPU skinning faithfully reproduce the selected shoulder
stretch. This experiment does not establish a source/runtime implementation
error or provide an authoritative replacement fit. No production file changed.

The selected witness is garment display triangle200, ordered source IDs
`[246,244,182]`, torso+1/jaw0, `b1_arm_rehearsal_v1` source2s. It is the already
reported shoulder case in [issue80](https://github.com/Derek-X-Wang/nvwa/issues/80#issuecomment-6241186738),
chosen before this experiment's calculations. This iteration does not diagnose
the waist or the separate neutral8-vertex fold region.

## Evidence and reproduced signal

The original actual CPU inputs are the retained experiment60 r4 deep captures
identified in issue80 at product candidate `c655217c0c9c41069b0f45a0d8c2795e455ca6bf`.
Thirty complete inputs cover torso−1/0/+1, jaw0, both admitted clips and
source0/1/2/3/4s. Their compressed-byte hashes, request/sample identities,
three-point traces, all-source reconstruction residuals and neighborhood
metrics are recorded in [the final replay](evidence/final-retained30/report.json).
The selected arm2 input SHA is
`5df0c97e5c51b3e71741e115ca4040d441189dd5853a505c1076d9ed0a53ae5e`.

| Torso, jaw0 | Fitted-rest area / raw OBJ area | Actual arm2 area / fitted-rest area |
| --- | ---: | ---: |
| −1 | 0.33493315 | 5.10750496 |
| 0 | 0.10329916 | 21.32761276 |
| +1 | 0.10026607 | 22.00563574 |

Raw source OBJ area is `1.87934560465e-4 m²`. Long-torso fitted rest is
`1.88434597402e-5 m²`; actual arm2 area is `4.14662311095e-4 m²`.
Long-torso arm0 and knee2 each remain near the same fitted rest
(`1.0000140756×`). Thus the neutral triangle is already narrow relative to the
source OBJ before motion; arm movement adds another large local area change.
These are geometry descriptors, not collision depth or visual acceptance.

The exact diagnostic command with `--fail-on-shoulder-stretch` returns
**exit3** on the actual retained arm2 witness. The corresponding arm0 and knee2
commands return **exit0**. Their reports are retained as
[witness red](evidence/witness-red/report.json),
[arm0 control](evidence/arm0-control/report.json), and
[knee2 control](evidence/knee2-control/report.json).
The fixed10× selector is inherited from the historical symptom identification;
it is not a new product quality threshold. No threshold was tuned to a candidate.

## What the independent source trace establishes

The integration checkout was verified at main
`ab4c16f81deddfc98faa97fcd1a8e7904c5f2f0b` before this new experiment. Source
identities come from the unchanged admitted manifest SHA
`abcdbc26e03431c740c5fce98de22902089f985823a3c655db2416d042d62b18`.
Every descriptor payload is authenticated before analysis. The observed arrays
are historical actual runtime inputs, not a new execution of that main commit.

The source chain is:

1. Actual same-frame fitted body rest supplies the full19,158-point helper cage.
   The garment MHCLO's three helper contributions retain their signed values and
   normalization. Adapted offsets/reference lengths are already metres; no
   second0.1 scaling is applied.
2. The independent formula reconstructs **all1,797** fitted garment source points.
   The maximum component residual against actual fitted rest over all30 frames
   is `1.09593e-7 m`.
3. Original source weights are transferred through the same helper IDs, with
   signed aggregation performed first. Every positive final bone aggregate is
   retained and normalized. Actual normalized rows agree within `3.63248e-8`;
   exact positive support agrees for every point. Some vertices retain6 bones.
4. Independent f64 LBS from actual fitted rest and captured full-positive rows
   reproduces actual upload within `1.64680e-7 m`. Replaying independent source
   fit **and** independently transferred source weights reproduces actual upload
   within `1.82896e-7 m`.
5. The unchanged experiment60 independent authored-FK/gauge/rigidity/IBM guard
   validates actual bones against requested clip/time. Maximum FK component
   residual is `7.75751e-7`; joint-head residual is `4.64505e-7 m`. It rejects a
   relabeled arm2 frame whose metadata says1s. This is not only metadata matching.
6. Actual global placement is checked between body and garment. Stage coordinates
   apply that global matrix once after model-local LBS; recorded source-root
   `model_to_world` is not an extra placement transform.

Current production source paths inspected were Humentity's
`loaders/mhclo.rs` and `assets.rs` (normalized signed helper fit and scaled
offset), adapter `full_proxy_influences` / `PreparedSkin::evaluate` (all positive
final aggregates and LBS), and runtime `b1.rs` upload/publication/readback.
The replay does not call their calculation functions. It reuses only the existing
experiment60 independent FK guard, whose checker/geometry source hashes are
recorded separately in the final report.

| Selected garment source ID | Helper IDs | Normalized upperarm_l weight |
| --- | --- | ---: |
| 246 | 17235,17238,16990 | 0.71984956 |
| 244 | 17238,17235,16971 | 0.79839934 |
| 182 | 17224,17223,16954 | 0.24555052 |

All helper coefficients for these three points are nonnegative; garment source182
retains five positive bone influences. Signed coefficient clipping cannot explain
this local witness. There are30 signed mapping rows elsewhere in the full garment;
the analyzer preserves them and does not generalize this local observation into
a global claim that signed semantics are unnecessary.

The same source triangle's immediate one-ring has16 vertices; all triangles
incident to those vertices give52 faces. The34 mixed boundary faces and35
non-core faces are recorded separately. At long-torso arm2 their baseline max
area/rest is5.31540612, preserving the boundary witness used to reject earlier61
heuristics. No subset is dropped to obtain a better score.

## Platform comparison and provenance limit

The retained r4 native and Web selected records were independently revalidated,
reconstructed and compared across **all1,797** garment source points and actual
skin matrices, using the same requested long-torso arm2 case. See
[the historical platform comparison](evidence/historical-native-web-final.json).
These records establish the historical CPU geometry on both platforms. They are
not a new native/Web launch, current-head proof, GPU readback or screenshot.

The retained original sportsuit source directory contains the OBJ, MHCLO, MHMAT
and diffuse/normal/AO images. It contains no authoring-body Work/MHM recipe or
explicit reference helper cage. Rehashed original source identities agree with
admitted provenance:

| Original retained input | SHA256 |
| --- | --- |
| female_sportsuit01.mhclo | `6df057d3116db93afbbbb6d692f92cce84aa16db699f47dd14e825d07c6fd42f` |
| female_sportsuit01.obj | `fd529bb8dd6a994c1e9a3fb2fd8b236f52c0cc7cebb1f6fd9328953d9df6d6ff` |

The MHCLO explicitly says `basemesh hm08` and has Female/Sport tags. Those tags
are not an exact authoring body recipe and do not prove the current neutral cage
is its intended authored reference. No anatomical or intended-fit conclusion is
inferred from the garment name or coordinates alone.

## Decision and remaining gate

The probes reject a substantial source-fit, signed-transfer, full-weight LBS or
upload mismatch as the explanation for this retained local stretch. They support
a narrow fitted-rest triangle plus differing faithful transferred bone influences
as the observed input to the deformation. This does not prove a unique cause of
the complete visible defect, nor identify an artistically correct replacement.

Prior61 fixed smoothing and offset-retention candidates were already rejected
with boundary regressions in issue80. This experiment does not rerun a parameter
search or promote either candidate. No new local weight or position patch is
proposed without an authoritative intended fit or independently justified boundary
constraint. There is no production correction to build at this point.

[README](README.md) gives an executable comparison protocol and a printed54-case
two-parameter held matrix per platform, split into two fresh Web storage batches
because the existing sink caps32 captures. Those54 cases are **planned**, not
executed here. Current source-bound native/Web captures, both jaw endpoints,
ordinary GUI/save/restore, screenshots, GPU/visual ownership, collision or
self-intersection classification, performance, independent review and CI remain
**NOT-RUN** for experiment70. No heavy compilation token was consumed.

Verification performed:30 retained source/upload replays; one historical complete
garment native/Web comparison;13 analyzer controls under normal Python and
`-O` (26 executions); exact arm2 diagnostic red and arm0/knee2 negative controls.
The source, results and control receipt hashes are in
[inventory.json](evidence/inventory.json).

**VERIFIED —** bounded historical source/upload reconstruction and local shoulder
stretch witness. **PARTIAL —** source-limited diagnosis, no correction; garment,
M2 and existing broader quality HOLDs remain. #3 blocked and #4 measurement gaps
are unchanged.

## Explicit68 interoperability supplement

The analyzer now accepts an independently expected timeline ID (`--timeline-id`,
default `probe-entry`) and explicit `--input-format bridge68`. It selects the
unaltered `frame.full_base` / `full_base`; no request or timeline value is
invented.68's actual shoulder Work uses `arms`. Comparison can independently
specify each side's format and timeline identity, preserving real60 versus68
differences without relabeling source arrays. See README's exact commands.

Raw68 frames provide geometry evidence only; their ready acknowledgement remains
NOT-CHECKED by70 and must be separately retained/verified through68. Envelope
inputs additionally require matching ready acknowledgement, IDs and base/Work/
runtime identity. A file-based acknowledgement cannot certify ongoing current
state. The new18-control suite adds synthetic positive/negative adapter and
immutability controls; those are not actual68 captures. The prior13-control code
is archived with its exact original hashes under `evidence/pre-interop-source/`.

Root's bounded supplement is actual long-torso/jaw0 arm0/2 on native and Web.
The54 planned frames remain NOT-RUN and are not a new minimum gate for this
source-limited iteration. No new68 run or visual result is claimed by this source
update; it requires fresh independent review.

The updated source reran the same30 retained cases in
[interop-retained30](evidence/interop-retained30/report.json), and the same
historical native/Web pair in [interop-historical-pair](evidence/interop-historical-pair.json).
All pass their original numeric checks. The18 controls pass normally and under
`-O`; [interop-verification.json](evidence/interop-verification.json) records
these worker-observed executions. This does not replace root's actual68 captures
or the required new review of this interface change.
