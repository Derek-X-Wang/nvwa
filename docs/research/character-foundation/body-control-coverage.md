# Body control coverage and staged validation

Nvwa's B1 controls are signed MPFB target weights in [-1, 1]. They are not centimetres, measured circumferences, cup sizes, or a guarantee of equal visual steps. Every added batch uses a new immutable asset identity; previous Work files and payloads retain their exact bytes.

| Region | Existing through v7 | Remaining work |
| --- | --- | --- |
| Legs | thigh/lower-leg length and thigh/calf girth | wider poses, garments, asymmetry if needed |
| Torso and chest | torso length, waist circumference, bust circumference | chest width/depth; separate breast spacing, projection and position |
| Shoulder and arms | shoulder span, upper-arm girth | shoulder form, upper-/lower-arm length and girth, wrist |
| Hip and buttocks | hip width | hip front/back depth and buttocks volume (v8 experiment), later hips circumference/height |
| Hands | none | bilateral hand scale, palm/finger form, gripping and prop tests |
| Elbow | diagnostic flex pose only | elbow shape control, separate from flex pose |

The v8 experiment adds `hip_depth` from the pinned MPFB `hip-scale-depth` pair and `buttocks_volume` from `buttocks-volume`. Its build script authenticates four CC0 gzip source files from commit `d0a32e57a7f915cb2f2b95410e2117648c7bbb7e`. The immediate v7 runtime payloads are copied unchanged. Zero must reproduce v7 geometry and 53 bone frames; signed endpoints must change the actual uploaded mesh and at least one front/side/back silhouette. The pelvis, thigh and calf joints need bilateral and pose inspection. Garment penetration and full animation remain a hold until examined directly.

Later batches should first verify source pairs, bilateral composition where source targets are one-sided, and animation/prop interactions. The [MPFB target catalogue](https://github.com/makehumancommunity/mpfb2/tree/d0a32e57a7f915cb2f2b95410e2117648c7bbb7e/src/mpfb/data/targets) contains upper-/lower-arm length, wrist circumference and separate left/right hand targets. Their presence does not establish safe parameter ranges or garment quality.
