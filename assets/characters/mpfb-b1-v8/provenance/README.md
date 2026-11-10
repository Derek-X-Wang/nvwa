# Static hip and buttocks target source extension (v8)

`hip-contour-target-source.json` records four new targets from the pinned MPFB 2.0.18 source. The compressed CC0 source bytes are under `source/data/targets/{hip,buttocks}/`; each shipped `.target` is its exact gzip expansion. `scripts/build-hip-contour-v8.py` verifies fixed compressed SHA256 values before expansion. No amplitudes, IDs, signs or zeros were edited. Only CC0 target data was imported, not addon program code. The existing runtime loader converts source coordinates by 0.1 once.

The two new controls select the original increase or decrease endpoint with a nonnegative magnitude. These are unitless, relative shape weights, not centimetres, measured anatomical dimensions or equal perceptual steps. Fitted skeleton, clothing and leg/hip poses need actual runtime examination.

`legacy-v7-manifest.json` and `legacy-v7-runtime-payloads.json` preserve the immediate predecessor. All 45 v7 runtime payloads are byte-identical in v8. `runtime-payloads.json` and `../manifest.json` enumerate the current 49-file runtime set. The older provenance files remain historical evidence for prior extensions; their counts and hashes do not describe the v8 set.

All prior quality HOLDs remain. A static silhouette or successful asset check alone does not approve garment quality, animation or character art.
