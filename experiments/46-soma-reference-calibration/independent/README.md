# Portable independent issue59 numerical oracle

Result: report-only **HOLD** for anatomical semantics and target-playable admission.
The one generated wave is input evidence, not external ground truth.

Run `python3 experiments/46-soma-reference-calibration/independent/oracle.py` from this checkout.
The program uses Python's standard library only. It parses the source41 skeleton,
raw public44 90-frame XYZW quaternions/root arrays, and actual frozen target GLB.
It hashes every contract input before computation. It does not import or execute
experiment43, 45, or 46 mathematics. The historical43 name relation and matrix
equation are transcribed explicitly and are one conditional diagnostic.
No experiment46 implementation or output was read before the original
independent freeze.

The stdout JSON and frozen `results.json` contain raw identities, norm diagnostics, all 48
signed permutation candidates, every joint's outgoing geometric frame rank,
source elbow conditioning controls, matched neutral segment measurements,
all-sample falsification summaries, and admission limits. The `pelvis_all90` field records the two conditional placement hypotheses and historical43 values for
every one of the 90 frames. The command writes only JSON to stdout and does not write any file.
`test_controls.py` exercises explicit invariant failures, including with `python -O`.

## Independent facts

- Raw arrays contain 10,800 quaternion floats and 270 root floats, all finite.
  Maximum quaternion norm error is 8.412634311394385e-8. Quaternion unitization
  occurs only inside numerical matrix evaluation; no normalized motion is saved.
- Source metadata declares +Y up/+Z forward and named Left appears at +X.
  The target generator authors +Z up, a front at -Y, and named `.L` at -X.
  With its Y-up export convention `(x,y,z)->(x,z,-y)`, target conventions become
  +Y up/+Z front/-X named left. No proper signed permutation matches all three.
  Three proper rotations each match two anchors; reflection diag(-1,1,1) matches
  all three but has determinant -1. These are declared conventions and name
  assignments. They do not empirically establish anatomical handedness.
- Source elbow incoming/outgoing angles are 0.0106765 degrees (LeftForeArm) and
  0.0106952 degrees (RightForeArm). Their plane-normal inverse-sine amplification
  is about 5,367 and 5,357. A derived 1 micrometer world-Y hand perturbation changes
  those normals by about 1.13 degrees while changing the primary ray by only
  0.000211 degrees. A -0.1 millimeter world-Z perturbation flips the normal by
  about 179.98/179.96 degrees. These perturbations are controls on the same
  neutral skeleton, not another motion sample.
- Actual target joint leaves are head, hand.L, hand.R, foot.L, foot.R. Outgoing
  joint-position geometry gives them rank zero. One-ray joints retain free twist.
  Stored target rest rotations and the pinned generator are authored frame
  conventions; geometric rank does not erase those values or independently prove
  the source's anatomical twist convention.
- Source/target neutral segment directions and lengths differ. Identity-basis
  upper-arm differences are about 134.275 degrees; forearm differences about
  126.346 degrees. The JSON reports all three proper two-anchor candidate
  differences, so these numbers do not silently select a side convention.
- A derived 60-degree twist keeps the source forearm primary ray fixed to
  1.11e-16 while moving a 0.1-meter off-axis marker by 0.1 meter. Matching one
  segment direction cannot identify twist.

## Explicit pelvis placement hypotheses

The actual target root translation is `(0, .0799999982, 0)` and pelvis local
translation is `(0, .7499999404, 0)`. The nonjoint scene ancestor is identity.
The root rest rotation/scale are identity. Exact target scales participate in
4x4 affine FK rather than being replaced by unit scales.

Absolute-pelvis hypothesis A defines target pelvis world position to equal the
raw source root. With root orientation `R_source_Hips * R_target_root_rest`, use
`T_target_root = raw_root - R_target_root * (S_target_root * t_pelvis_local)`.
Independent target 4x4 FK closes for all 90 frames, maximum error
1.734723475976807e-18 meters. This equation is a placement convention. It does not
prove the raw source root is the correct anatomical target pelvis anchor.

Neutral-relative hypothesis B defines target pelvis position as its actual
neutral position plus `raw_root(frame) - raw_root(frame0)`. Removing the same
rotated pelvis offset closes to 8.673617379884035e-19 meters for all 90 frames.
Both hypotheses close numerically. An independent placement reference or an
explicit product policy is needed to choose between them.

The historical43 orientation relation is independently stated as
`R_desired(j)=R_source_global(mapped_j)*transpose(R_source_rest_global(mapped_j))*R_target_rest_global(j)`.
Root and pelvis both map to source Hips. Historical43 root translation is
`target_rest_root + raw_source_root - source_rest_root`. Source41 rest root is
zero. Relative to hypothesis A, the resulting historical pelvis error ranges
from .8299487467 to .8299999133 meters. This is conditional arithmetic, not an
anatomical verdict on either placement policy.

## Falsifications on the same fixed sample

The chosen expected absolute pelvis position is always the raw root. The controls
change candidate root placement but retain the target's actual rotated hierarchy.

| Control | Maximum pelvis error (meters) | Frames above 1e-6 |
|---|---:|---:|
| Subtract unrotated pelvis offset | .0282249801 | 90 |
| Add target rest root twice | .0799999982 | 90 |
| Add root trajectory delta twice | .0126181158 | 89 |
| Add absolute source root twice | .9962255991 | 90 |
| Remove offset with inverse root rotation | .0563151204 | 90 |

Negating all source quaternions changes neither source nor mapped target affine
positions: maximum error zero. The zero trajectory delta at frame zero correctly
does not distinguish the double-delta control there.

Missing references: an independent source/target up/front/anatomical-side
reference; per-limb twist or off-axis references; a chosen source-root to target
pelvis policy; and external pose/motion ground truth. No export, generated Work,
normalization artifact, product/provider changes, playback, model execution,
download, package installation, UI, or GPU work occurred.

VERIFIED — hash-pinned stdlib computation, all90 affine closure, q/-q invariance,
and six nonzero falsification summaries. PARTIAL — anatomical and playback
admission remain HOLD; the postfreeze comparison reproduces five prior45 metrics within 1e-12.
No final experiment46 agreement is claimed before its independent final freeze.

## Publication adaptation

`ADAPTATION.json` records exact original frozen hashes and the adaptation diff
SHA-256. `adaptation.patch` shows changes from the independently frozen script.
Only input pin/path portability, stdout delivery, and explicit invariant checks
changed. The mathematical calculations and frozen inputs are unchanged.

For identity basis B=I, the current primary report declares the same conditional
root orientation used here. This package does not evaluate primary46 reflection
policies or import its math. Derived neutral-relative placement remains a separate
gauge and is never presented as raw absolute-Hips placement.

Run `python3 -B experiments/46-soma-reference-calibration/independent/test_controls.py`
for the six rejection, freshness, and numerical controls. Repeat with `-O` after
`-B` to verify that optimization does not remove checks. Python3.9, 3.12, and 3.14
all passed both modes. Python3.9's float readout differs from 3.12/3.14 by at most
1.726e-9 degrees in the near-collinear controls. Artifact comparisons permit
1e-7 degrees and 1e-12 for other numbers; actual numerical invariant thresholds
remain 1e-12 meters for affine closure.
