# Body control coverage and staged validation

Nvwa's B1 controls are signed MPFB target weights in [-1, 1]. They are not centimetres, measured circumferences, cup sizes, or a guarantee of equal visual steps. Every added batch uses a new immutable asset identity; previous Work files and payloads retain their exact bytes.

| Region | Existing through v7 | Remaining work |
| --- | --- | --- |
| Legs | thigh/lower-leg length and thigh/calf girth | wider poses, garments, asymmetry if needed |
| Torso and chest | torso length, waist circumference, bust circumference; v10 experiment adds breast spacing and vertical placement | chest width/depth and projection; full garment and pose acceptance |
| Shoulder and arms | shoulder span, upper-arm girth; v9 experiment adds upper-/lower-arm length and wrist circumference | shoulder form, forearm girth, wrist shape and pose quality |
| Hip and buttocks | hip width; v8 experiment adds front/back depth and buttocks volume | hips circumference/height and full garment/pose acceptance |
| Hands | none | bilateral hand scale, palm/finger form, gripping and prop tests |
| Elbow | diagnostic flex pose only | elbow shape control, separate from flex pose |

The v8 experiment adds `hip_depth` from the pinned MPFB `hip-scale-depth` pair and `buttocks_volume` from `buttocks-volume`. Its build script authenticates four CC0 gzip source files from commit `d0a32e57a7f915cb2f2b95410e2117648c7bbb7e`. The immediate v7 runtime payloads are copied unchanged. Zero must reproduce v7 geometry and 53 bone frames; signed endpoints must change the actual uploaded mesh and at least one front/side/back silhouette. The pelvis, thigh and calf joints need bilateral and pose inspection. Garment penetration and full animation remain a hold until examined directly.

Later batches should first verify source pairs, bilateral composition where source targets are one-sided, and animation/prop interactions. The [MPFB target catalogue](https://github.com/makehumancommunity/mpfb2/tree/d0a32e57a7f915cb2f2b95410e2117648c7bbb7e/src/mpfb/data/targets) contains upper-/lower-arm length, wrist circumference and separate left/right hand targets. Their presence does not establish safe parameter ranges or garment quality.

The v9 experiment uses the pinned bilateral MPFB `measure-upperarm-length`, `measure-lowerarm-length`, and `measure-wrist-circ` increase/decrease pairs. It preserves all 49 v8 runtime payloads and exposes three more unitless static weights. Acceptance requires exact v8 zero geometry and bone frames, signed endpoint differences in front and side, elbow-pose publication, and direct bilateral shoulder/elbow/hand rest-joint checks. These checks cannot establish unrestricted garment fit or full motion quality. Finger and palm form, elbow shape, shoulder muscle form, breast position/projection, and chest depth are still separate work items.

The v10 experiment adds breast spacing and vertical placement from fixed CC0 MPFB `breast-dist` and `breast-trans` targets. Negative vertical weight selects `down`; positive selects `up`. The 55 v9 runtime payloads remain byte-identical. Core and CLI contracts verify old Work compatibility, bounds, capability discovery, and missing/tampered asset rejection. Actual front/side/back renders and shoulder pose must prove whether these controls are visible through the shipped sportsuit. Their names describe source target intent, not physical measurements or a guarantee of garment fit. Chest width/depth, projection, hand/finger shape, forearm girth, shoulder form, and elbow shape remain separate candidates.
