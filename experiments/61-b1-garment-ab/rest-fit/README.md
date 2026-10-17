# Candidate B: fixed local rest-offset retention

Experimental recipe `rest-local-v1`, for issue80. This is not an asset, saved Work profile, runtime override loader or garment admission.

Retain 0.5 of the original admitted MHCLO offset on source IDs182,244,246; retain0.75 on the immediate incident vertex ring; retain1 outside. The ring is22,29,79,104,110,191,241,255,669,677,691,697,719. The recipe changes16 source vertices. Delta is in original MHCLO units and uses the signed ordered helper-component/reference scale from actual body fitted rest. Original signed helper coefficients and full-positive normalized skin influences remain unchanged.

Build and evaluate once against an explicit directory containing the30 retained r4 keyframes:

```sh
python3 -B experiments/61-b1-garment-ab/rest-fit/test_controls.py
python3 -B experiments/61-b1-garment-ab/rest-fit/compare.py \
  --captures "$CAPTURES" --output "$NEW_OUTPUT"
```

`--mode build` emits only the immutable recipe and input receipt. `--mode evaluate --candidate PATH` requires the exact current fixed recipe and provenance. The output directory must not exist. The candidate contains only repo-relative source provenance; capture hashes are in the separate input receipt. The supplied immutable `candidate.json` is the final frozen recipe; changing source/contract invalidates its provenance rather than silently refreshing it.

The evaluator reconstructs admitted garment rest from actual body helpers and compares independent full-positive LBS against actual uploaded baseline arrays. B applies the linear skin response of the rest delta to that actual baseline. All affected vertices follow the same path for the zero-delta control. Unaffected exterior and the independent eight-vertex neutral-fold region must remain exact. The full52 displayed triangles touching any16 affected source IDs are scored, including transition/exterior faces. Per-frame evidence contains absolute rest/posed triangle areas and unique edge lengths, ratios against both original and altered rest, fixed-boundary lengths, full fold-descriptor IDs, and local nearest-triangle side signs.

**Result: REJECT/HOLD.** At the arm peak, torso0/+1 core absolute posed area increases about0.77%; the lower candidate-rest area ratio mostly reflects a larger rest denominator. Ring area extrema regress6.742745→7.149473 and5.315406→5.697412. Torso−1 has a small core absolute-area improvement, but does not rescue the other fits. No tuning was performed. See `report.md` for the bounded evidence and limits.

Baseline inputs are30 actual retained production captures. Altered arrays are offline f64 rest-delta/LBS replay, not fresh runtime/GPU readback. This evaluator does not rebuild visual normals/tangents. If rendered separately, all variants must use the identical normals/tangents policy in the common contract. Runtime, visual, alpha, collision, self-intersection, full jaw-grid and production acceptance are NOT-RUN here.
