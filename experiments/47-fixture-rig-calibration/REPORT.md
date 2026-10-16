# 47 — Explicit fixture calibration under independent physical references

**Root-selected implementation, pending independent calibration admission.**
The selected policy keeps source and target +Y up, +Z front and bodily left
+X. It maps SOMA `Left*` to fixture `*.R`, and `Right*` to `*.L`. This preserves
the existing asset labels and uses the identity coordinate basis. A named-label
X reflection remains a measured comparator and fails the independent physical
reference subcheck. Numeric closure does not choose either policy.

## Authority and engineering choices

The independent [reference capsule](reference/) derives source documented
axes, source eyes/jaw/toes and target face/eye geometry before candidate
exposure. Its first report SHA-256 is
`9ddd992efb4af47cd524ec55124a28889448208541f4a73ab08f7a74462a19d2`.
The root decision SHA-256 is
`c5c1b0ef3deac7410f0b6da1e05490d347fd0189219b7898a741ac6dcb0f8d67`.
These hashes identify the decision inputs; the public capsule records its
own source receipts and sanitized paths.

Target face geometry points +Z, and its upright body points +Y. Bodily left is
`up × front = +X`. Actual fixture `.L` joints occupy negative X and `.R` joints
positive X. Source `Left*` geometry occupies positive X. This is a real suffix
conflict. Its author's naming intent is unknown. The selected correspondence
acknowledges the conflict; it neither renames joints nor reflects the mesh.

The following remain explicit fixture engineering conventions:

- Neutral correspondence is the pinned source identity-rotation T-like rest
  mapped to the exact target A-like bind. Frame zero is animated and is never
  the neutral reference.
- Each geometric frame uses longitudinal X, a projected guide as Y, and
  `Z = cross(X,Y)`. Source longitudinal references are explicit static joint
  pairs. For `Head`, incoming `Neck2 → Head` supplies the longitudinal reference;
  `Head → Jaw` would follow the face rather than head length.
- Target longitudinal references are the original generator's directed bone
  heads/tails, including terminal hands and feet. The AST reader handles only
  literal coordinates and the explicit side loop; it does not execute Blender
  or import the generator.
- The guide is +Z front, except feet use +Y up. For feet, the negative secondary
  marker is the chosen down reference. These are signed roll gauges, not
  certified palm, volar, sole or contact normals. Source thumb/middle geometry
  exists; this policy deliberately chooses the simpler projected-front hand
  gauge instead of claiming a recovered digital-plane anatomical mapping.
- Frames are built once from static references. Projection sine at or below
  `1e-12` is rejected with no fallback. No frame is rebuilt from animated
  nearly straight elbows. No singularity threshold is called anatomical trust.
- Exact target bind translations and scales remain fixed. Removed source-link
  rotations are collapsed into the next mapped joint. Their moving translations
  are omitted. There is no length, height, floor, contact or endpoint fit.

The first proposal and executable checkpoint retained a named-label reflection
as a provisional option. The independently frozen source audit and root decision
selected physical identity. The original checkpoint is preserved privately.
This version also names the incoming head axis and exact affine markers
explicitly. No sample endpoint score selected these changes.

## Defined rotation transfer and root policy

Let `G_s0,j` and `G_t0,j` be global static rest rotations, `L_t0,j` target local
bind rotations, `F_s,j` and `F_t,j` the proper geometric frames, and `B` the
coordinate basis. The selected `B` is identity. The comparator uses X reflection
and conjugates rotations as matrices; it never pretends a reflection is a
quaternion rotation.

```text
A_s,j = transpose(B * G_s0,j * transpose(B)) * F_s,j
A_t,j = transpose(G_t0,j) * F_t,j
C_j   = A_t,j * transpose(A_s,j)

N_j = transpose(G_s0,mapped_parent) * G_s0,mapped_joint
P_j = transpose(G_s(t),mapped_parent) * G_s(t),mapped_joint
D_j = B * transpose(N_j) * P_j * transpose(B)

L_t,j(t) = L_t0,j * C_j * D_j * transpose(C_j)
```

For the scene root, `N/P` use the source Hips global rotations. The root uses
the same explicit geometric conjugation; its chosen orientation is not inferred
from pelvis closure. The target pelvis retains its bind rotation so Hips is
not applied twice. Collapsed source paths include Spine2→Chest, Neck2→Head and
Shoulder→Arm. Authored controls exercise their actual mapping path.

The source Hips absolute trajectory is applied once, with exact unit root scale:

```text
scene_translation = B * source_Hips_world
                  - target_root_rotation * target_pelvis_bind_translation
```

This replaces the scene translation. It adds neither target root rest position
nor exporter height. The exact fixture has an identity nonjoint ancestor and
pelvis directly beneath root; the loader rejects other hierarchies. Target
pelvis world position, checked by a separate recursive affine oracle, is the
root test. Scene-root/source-Hips equality is not required.

## Exact affine markers and independent expectations

Each joint has two authored 0.1 metre orientation markers. Their neutral world
directions are the signed geometric primary and secondary. The candidate
inverts the **complete exact bind affine transform** to store their local
offsets. Animated directions use the complete affine hierarchy, including the
small nonunit descendant scales in the real GLB. No bind scale is rounded to
one. Leaf markers are authored diagnostics; they are not new finger/heel joints
or measured mesh contact points.

The independent controls transcribe generator heads/tails separately and use
Gram-Schmidt projection and Rodrigues' closed-form vector rotation. They do
not obtain expected vectors from candidate frames. Longitudinal and secondary
axis rotations test 17 mapped joints for each candidate. Separate recursive
point transport checks actual child joint positions. An inverse-quaternion and
scale transport oracle checks all 18 primary/secondary affine markers on all
90 frames: 3,240 signed marker directions per candidate.

The authored diagnostic poses use identity source rest plus one known rotation.
They are labelled authored controls. The genuine generated sample remains the
unchanged 90-frame public44 bytes with its original provenance. The analyzer
checks ten public input hashes, raw shapes, finite floats, quaternion norms,
receipt bindings and fixture/generator provenance. It imports no frozen
experiment or vendor implementation and executes no provider or model code.

## Local results

Both candidate calculations close pelvis-world position with maximum error
`1.734723475976807e-18` metre over all90 frames. Static neutral maps to exact
target bind rotation with maximum matrix error `1.1102230246251565e-15`.
The minimum chosen static guide projection sine is `0.9175556253099241`.
These are numerical properties under declared conventions.

| Observed precision boundary | Maximum residual |
|---|---:|
| Generator decimal head versus exact GLB bind origin | `1.7559006062639675e-7` m |
| Generator tail versus bind rotation longitudinal axis | `2.3588452780283308e-7` |
| Closed-form pure rotation versus exact affine marker direction | `9.441448608482617e-7` |
| Authored child head versus exact affine child position | `7.461144435600048e-7` m |

The last two controls use a predeclared `2e-6` export/scale precision tolerance;
the exact independent affine marker comparison uses `1e-10`, and pelvis world
uses `1e-12` metre. None is a semantic quality or contact tolerance. Float result
reproduction uses `1e-13` absolute/relative; types and identities remain exact.

The genuine quaternion signs remain unchanged in the retained inputs.
Actual q/−q diagnostic FK differences are exactly zero. Actual parent-local
double localization changes target trajectories by `0.45263030663550474` m;
conjugating XYZ by `0.9154438110447959` m; XYWZ misreading by
`1.4999995370380383` m. These are measured control differences, not quality
scores. The physical policy's largest one-frame named hand step is about
`0.0727071` m on `hand.L`, the fixture's bodily right. This is an observation,
not a smoothness pass or a claim that the prompt is fulfilled.

Controls reject reflection against physical-side authority, front reversal,
side exchange, a terminal 180° roll, first-frame neutral, double localization,
quaternion representation mistakes, unchanged43 root addition, unrotated pelvis
subtraction and repeated target/source/exporter offsets. The terminal half-roll
control exercises off-axis rotation: a primary-only check would miss it.
Malformed pins, missing inputs, singular gauges, booleans and nonfinite values
are rejected. Validation uses explicit exceptions and stays active with `-O`.

## Gate and cleanup

The selected calibration is reviewable engineering policy with independently
supported static axes and physical-side correspondence. Its roll and neutral
choices remain authored gauges. `PROPOSED_NOT_ADMITTED` remains in every
candidate/result until the root records independent calibration review.
Passing numeric checks cannot promote that status.

NOT-RUN — Original official SOMA bind/surface verification, runtime decoder-axis
parity, certified anatomical palm/sole calibration, contact/scale/proportion fit,
arbitrary rigs, new inference, normalized/export admission, generated Work,
actual native/Web playback, save/reopen exchange and human motion-quality
assessment. These require separate gates.

Only synchronous standard-library Python processes ran. No worker-owned child
process, server, GPU task, download, package or temporary external resource
remains. Public47 and private primary checkpoints are intentionally retained
under root ownership. Frozen41–46, product, assets, dependencies and Git state
were not edited by this worker.

VERIFIED — 89 positives,43 rejections and8 measured controls pass on
Python3.9.6 and3.14.7, normal and `-O`. All1,952 protected input paths remain
exact. Independent calibration review is pending.
