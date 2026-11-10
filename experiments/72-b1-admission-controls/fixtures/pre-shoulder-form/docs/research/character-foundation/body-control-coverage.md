# Body control coverage and staged validation

Nvwa's B1 controls are signed MPFB target weights in [-1, 1]. They are not centimetres, measured circumferences, cup sizes, or a guarantee of equal visual steps. Every added batch uses a new immutable asset identity; previous Work files and payloads retain their exact bytes.

| Region | Existing through v9, with local v11 hand candidate | Remaining work |
| --- | --- | --- |
| Legs | thigh/lower-leg length and thigh/calf girth | wider poses, garments, asymmetry if needed |
| Torso and chest | torso length, waist circumference, bust circumference | chest width/depth; separate breast spacing, projection and position |
| Shoulder and arms | shoulder span, upper-arm girth, upper-/lower-arm length and wrist circumference | shoulder form, forearm girth, wrist shape and pose quality |
| Hip and buttocks | hip width; v8 experiment adds front/back depth and buttocks volume | hips circumference/height and full garment/pose acceptance |
| Hands | local v11 candidate adds independent left/right whole-hand scale weights | palm/finger form, gripping and prop tests; candidate not artistically accepted |
| Elbow | diagnostic flex pose only | elbow shape control, separate from flex pose |

The v8 experiment adds `hip_depth` from the pinned MPFB `hip-scale-depth` pair and `buttocks_volume` from `buttocks-volume`. Its build script authenticates four CC0 gzip source files from commit `d0a32e57a7f915cb2f2b95410e2117648c7bbb7e`. The immediate v7 runtime payloads are copied unchanged. Zero must reproduce v7 geometry and 53 bone frames; signed endpoints must change the actual uploaded mesh and at least one front/side/back silhouette. The pelvis, thigh and calf joints need bilateral and pose inspection. Garment penetration and full animation remain a hold until examined directly.

Later batches should first verify source pairs, bilateral composition where source targets are one-sided, and animation/prop interactions. The [MPFB target catalogue](https://github.com/makehumancommunity/mpfb2/tree/d0a32e57a7f915cb2f2b95410e2117648c7bbb7e/src/mpfb/data/targets) contains upper-/lower-arm length, wrist circumference and separate left/right hand targets. Their presence does not establish safe parameter ranges or garment quality.

The v9 experiment uses the pinned bilateral MPFB `measure-upperarm-length`, `measure-lowerarm-length`, and `measure-wrist-circ` increase/decrease pairs. It preserves all 49 v8 runtime payloads and exposes three more unitless static weights. Acceptance requires exact v8 zero geometry and bone frames, signed endpoint differences in front and side, elbow-pose publication, and direct bilateral shoulder/elbow/hand rest-joint checks. These checks cannot establish unrestricted garment fit or full motion quality. Finger and palm form, elbow shape, shoulder muscle form, breast position/projection, and chest depth are still separate work items.

The local v11 hand-size candidate pins `l-hand-scale` and `r-hand-scale` decrease/increase pairs at the same MPFB commit. It keeps all 55 v9 runtime payloads unchanged and exposes two independent signed relative weights. Its v11 asset identity and backend schema 13 reserve v10/schema 12 for the separate chest-placement branch currently on visual hold; this candidate branches from v9 and does not inherit unaccepted chest controls. The candidate must show per-hand changes in actual body-only front, quarter and side views at fixed cameras, preserve v9 geometry and bones at zero, and remain finite in the elbow pose. Finger articulation, wrist transitions, hand props, garments and artistic acceptability are separate reviews; a changed image hash alone is insufficient.
