# 46 — Signed references, frame conditioning and conditional root arithmetic

**HOLD anatomical and target playable admission.** Existing inputs constrain
coordinate conventions and support a precise conditional root calculation.
They do not establish common anatomical side/parity, trusted neutral frames or
target palm/sole twist. This report adopts no pose mapper or side policy.

## Reproduce and retained inputs

Run the two commands in [README.md](README.md). They use only the standard
library, with no model or other process invoked by the analyzer. JSON goes to
stdout; there is no output-file option. `results.json` records the full signed
candidate table, per-joint frames, all90 root residuals and diagnostic controls.
`verification.json` records 27 positive and 48 rejection checks.

Ten exact pins bind source41 skeleton metadata, frozen43 mapping definitions,
the fixture GLB, its generator and provenance manifest, public44 generation/
process/stdout receipts, and both raw arrays. The manifest binds generator and
GLB identities. The generation receipt binds the same raw hashes and 90 frames
at 30 fps. Public44 owns the original generation/process evidence; this report
checks those identities rather than recreating the process evidence. The
analyzer parses the GLB and performs its own matrix/affine math; it executes no
frozen43 code. The historical correspondence is retained only for controls.

All 270 root and 10,800 quaternion floats are finite. Maximum raw quaternion norm
error is `8.412634311394385e-8`. Raw provenance stays **generated**. Every
transformed value here is a diagnostic quantity, not a product artifact.

## Independent signed anchors expose a conditional parity conflict

Source41 declares +Y up and +Z front. Source named-left hip/arm offsets have +X
sign. Target generator choices and actual bind geometry give +Y up and −X for
`.L`. Target front is +Z from generator eye/face placement, corroborated by the
actual GLB POSITION eye landmarks: pupil centroid Z≈0.172 m, white Z≈0.148 m.
Metadata intent, geometric observations, named labels and trained-data/anatomical
authority are separate claims in the JSON. Eye centroids are approximate geometry,
not a new anatomical reference. Trained-data/export semantic parity is unverified.

Each candidate transforms only the source side of these independent anchors:

| Constraints imposed | Signed-permutation candidates |
|---|---:|
| None | 48 |
| Common declared up | 8 |
| Common declared up and front | 2: identity and X reflection |
| Also current named-left signs | 1: X reflection, determinant −1 |

The last row is conditional on treating both name-side signs as correspondence
authority. It does not adopt a reflection or resolve anatomical labels. A proper
180° Y rotation also reverses front. Reversing the independent front annotation
changes that decision; changing the independent side annotation favors identity.
No label swap, asset edit or endpoint-fit selection occurs. All48 consistently
transformed bases still satisfy source FK equivariance at actual frame47, with
maximum error below `1e-12` m. That is numerical consistency only.

## Geometric rest frames do not certify anatomical twist

Every source and target joint has an intended longitudinal segment, secondary
landmark if present, projection length, normalized projection sine, inverse-sine
sensitivity and explicit anatomical HOLD. A geometric frame uses primary X,
projected secondary Y and `Z=cross(X,Y)`. The oracle checks signed segment and
secondary directions as well as proper orthonormal matrices. A reversed
secondary gives a 180° twist: primary direction still passes, secondary fails.

Source elbow sine is about `1.8634e-4` on the left and `1.8667e-4` on the right;
inverse-sine sensitivity is about 5,366 and 5,357. These nearly straight segments
are poorly conditioned for roll. Numerical rank is not trusted anatomy. The
`1e-12` rank tolerance only handles numerical degeneracy; no anatomical trust
threshold is invented. Source thumb/middle landmarks define conditional hand
geometry. Target hand/foot joints are leaves: incoming position alone gives no
distal palm/sole reference or skeleton-only twist. They retain missing-secondary
HOLD with no fallback axis. Bind frames or projected torso front could be an
explicit authored gauge; this report adopts neither as empirical anatomy.

Geometric rest directions differ independently of segment length:

| Left segment | Identity direction gap | X-reflection direction gap | Source / target length (m) |
|---|---:|---:|---:|
| Upper arm → forearm | 134.275° | 45.725° | 0.287393 / 0.279330 |
| Forearm → hand | 126.346° | 53.653° | 0.270940 / 0.236220 |
| Thigh → shin | 3.353° | 3.353° | 0.432292 / 0.360555 |
| Shin → foot | 4.982° | 4.982° | 0.422986 / 0.360139 |

The JSON includes both sides. Source static rest is T-like; target bind is
A-like. The first generated frame is animated and supplies no independent
neutral reference. No absolute-anatomical or neutral-relative transfer is
selected, and no twist distribution through removed chains is chosen.

Historical43 rest-delta orientations after the conditional root fix still give
maximum identity-basis hand gaps of 1.289/1.326 m and foot gaps of 0.362/0.357 m.
X reflection reduces those observed gaps to 0.452/0.472 m and 0.255/0.255 m.
These mix lengths, rest directions and omitted moving translations. They are
neither a quality bound nor authority to choose reflection.

## Conditional pelvis-world arithmetic succeeds across all90 frames

For each of the two common-up/front candidates, the declared root-rotation
convention is `R=(B*R_source_Hips(t)*B^-1)*R_target_root_bind`. The equation does
not choose or independently justify this animated target orientation. Scale is
the exact target root rest scale `[1,1,1]`, with 1 metre/metre and no actor-height
fit. The checked nonjoint ancestor is identity and pelvis is directly under
joint root. Unsupported hierarchy is rejected.

The absolute scene translation replaces the root channel once:

```text
t_scene = B*h_source_Hips - R*S*target_pelvis_local_rest
```

The oracle composes generic 4×4 affine transforms and tests target pelvis **world
position** against `B*h` at every frame. Both conditional bases give maximum
error `1.734723475976807e-18` m, below the declared `1e-12` m tolerance.

| Actual failing policy/control | Maximum world-pelvis error (m) |
|---|---:|
| Unchanged43 root addition | 0.8299999133 |
| Unrotated pelvis subtraction | 0.0282249801 |
| Add target root rest again | 0.0799999982 |
| Apply source trajectory twice | 0.9962255991 |
| Add exporter height | 0.988 |
| Transpose root rotation for subtraction | 0.0563151204 |
| Reflect rotations without trajectory | 0.0282614082 |

The compensated scene-root XZ path is about 0.167691 m, while the matching pelvis
path is about 0.073493 m. Scene-root/source-Hips equality would reject this valid
conditional policy and is explicitly exposed as a false oracle. There is no
target-neutral-relative displacement or height policy hidden in this equation.
The fixed unit-root-scale fixture does not establish nonunit root-scale support,
general hierarchy support, floor fitting, foot contact or anatomical quality.

## Falsification, portability and remaining gate

Controls call the actual loaders, analyzer, affine/root oracle, geometric frame
oracle and strict result comparator. They reject ten corrupted pins, missing
identity, all seven root policies above, representation mistakes, signed-frame
mistakes, unsupported hierarchy, nonfinite/type-invalid inputs, altered
discrete identities and false semantic promotion from either root success or
48-basis invariance. Actual q/−q FK difference is zero. Conjugated XYZ, misread
XYWZ order and double localization change source FK by about 1.386, 1.145 and
0.733 m. Validation uses explicit exceptions and remains active under `-O`.

Python3.9 initially exposed cancellation in a near-collinear frame projection;
cross-cross projection repaired arithmetic without relaxing the finite-float
comparator (`1e-13` absolute and relative). An earlier control also exposed the
wrong secondary landmark at the forearm. The [development record](development-history/README.md)
distinguishes observed output transcriptions from retrospective explanations;
unretained failing source/log files are not represented as originals.

The missing gate is independent signed anatomical side/front/parity authority,
plus trusted neutral/twist references or an explicitly reviewed authored gauge,
especially for target leaf hands/feet. No numeric pass changes this gate.

VERIFIED — Both conditional pelvis oracles pass all90 samples; 27 positive and
48 rejection checks pass on Python3.9.23/3.12.11/3.14.7, normal and `-O`; all ten
public inputs remain exact. No temporary resources or child processes remain.
NOT-RUN — Anatomical or playable admission, pose-transfer adoption, normalized
motion, exporter, generated Work, native/Web playback, trained-data semantic
parity, arbitrary rigs, contact/quality/scale fitting, or new inference.
