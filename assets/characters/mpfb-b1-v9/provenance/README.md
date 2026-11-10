# Static arm and wrist target source extension (v9)

`arm-proportion-target-source.json` records six new targets from the pinned MPFB 2.0.18 source. The compressed CC0 source bytes are under `source/data/targets/{arms,hands}/`; each shipped `.target` is its exact gzip expansion. `scripts/build-arm-proportions-v9.py` verifies fixed compressed SHA256 values before expansion. No amplitudes, IDs, signs or zeros were edited. Only CC0 target data was imported, not addon program code. The existing runtime loader converts source coordinates by 0.1 once.

The controls select increase/decrease endpoints with nonnegative magnitude. They are unitless relative weights, not centimetres or measured segment lengths. Fitted skeleton, sleeves, hands and elbow/wrist poses require actual runtime inspection.

`legacy-v8-manifest.json` and `legacy-v8-runtime-payloads.json` preserve the immediate predecessor. All 49 v8 runtime payloads are byte-identical in v9. `runtime-payloads.json` and `../manifest.json` enumerate the current 55-file runtime set. Older provenance files remain historical evidence, not a description of the v9 set.

Prior quality HOLDs remain. A static silhouette or asset check alone does not approve garment fit, hand prop interaction or animation.
