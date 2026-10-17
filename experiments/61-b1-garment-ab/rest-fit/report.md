# Candidate B bounded comparison

**Verdict: REJECT/HOLD; keep the single frozen recipe unchanged.**

Thirty actual retained r4 baseline captures: torso−1/0/+1, jaw0, both authored clips, source0/1/2/3/4 seconds. Candidate arrays are offline f64 rest-delta/full-positive-LBS replay; no current experimental runtime or visual claim.

## Arm peak (source2 seconds)

| Torso | Core posed area original→B (m²) | Core original-rest ratio→B candidate-rest ratio | B core ratio against ORIGINAL rest | Ring maximum area ratio original→B |
|---|---|---|---|---|
| -1 | 0.0003214945299→0.0003201466543 | 5.107505→3.210359 | 5.086092 | 15.258901→7.709103 |
| +0 | 0.0004140432354→0.0004172218888 | 21.327613→4.001082 | 21.491347 | 6.742745→7.149473 |
| +1 | 0.0004146623111→0.0004178822973 | 22.005636→4.011109 | 22.176517 | 5.315406→5.697412 |

For torso0/+1, the core absolute posed area worsens about0.77%. Its rest area increases from about1.9e−5 to1.04e−4 m², explaining most of the ratio gain. Ring extrema worsen beyond the common1e−4 numerical-noise tolerance. Torso−1 core absolute area improves about0.42%; its original-rest ring maximum nevertheless worsens15.258901→17.324202, while the candidate-rest ratio falls to7.709103. Aggregate maxima alone would hide these regressions. No blanket10x criterion was used.

## Coverage and controls

- Frozen16 changed IDs;52 displayed incident triangles, including transition/exterior faces;34 affected/exterior crossing edges. Each per-frame group reports absolute rest/posed areas and edge lengths, both denominators, extrema, and triangle IDs.
- Maximum candidate posed displacement: 8.115455 mm. Body/rig/motion, original topology and all1797 full-positive normalized influence rows unchanged; no weight overrides.
- Maximum baseline independent LBS component disagreement: 1.6467935e-07 m. Maximum independent fitted-rest reconstruction disagreement: 1.09593036e-07 m. Both satisfy the existing1e−5 controls.
- Same-path zero-delta replay is exact for all30 frames. Exterior and independent eight-vertex safety positions remain exact. No new neutral fold-descriptor edge IDs; global fold count maximum remains5. Existing torso−1 neutral edge112/248 angle decreases about169.46°→158.01° but remains a fold descriptor. Local signs are nearest oriented-triangle projections, not physical penetration/collision.
- Three cheap unit controls pass: same-path no-op; signed scale/all-influence/translation-cancellation/exterior; complete transition/exterior incident-set coverage.

## Evidence and reproducibility

`compare.py --captures "$CAPTURES" --output "$NEW_OUTPUT"` builds twice deterministically then evaluates30 frames. `--mode build` and `--mode evaluate --candidate PATH` are available. Portable `candidate.json` uses only repo-relative actual source provenance. Private capture hashes and literal invocation remain in the separate work evidence `final/inputs.json`; detailed frame records, summary and receipt are `final/frames.jsonl`, `final/summary.json`, `final/SHA256SUMS.json` beneath the assigned work directory.

The first recipe/evidence was preserved in `initial-verification/`. After common-contract clarifications, verification gained explicit all-affected triangles/absolute per-triangle and per-edge data and a shared no-op path. The expanded verification is preserved separately. Final provenance removes logical capture aliases and binds the final common contract and script. Final and expanded frame records are byte-identical; the geometric recipe/deltas never changed. These were verification corrections, not candidate tuning.

NOT-RUN: current candidate actual runtime upload/readback, rebuilt normals/tangents, Web/native visual comparison, full jaw-grid, collision, self-intersection, cloth simulation or production admission. Existing product floor/root/foot/quality gates are unchanged.

## Frozen identities

- `experiments/61-b1-garment-ab/rest-fit/candidate.json`: `c6bbf79553de93c257d07baf306bf296f635f5b351932ee7ae3bd607864711ff`
- `experiments/61-b1-garment-ab/rest-fit/compare.py`: `1af669211ac300c466a3a512258cd16b2511726cfed0f99ee2c17b38f663998e`
- `experiments/61-b1-garment-ab/rest-fit/test_controls.py`: `3a4edf31c176edccc0b9fea18861181011c83785a85a9c7a30145a975db89abc`
- `.work/garment61/rest-fit/final/frames.jsonl`: `ce344142d06b2c3a99d34eb96d30e72c7431510a8bdc37d51f47a9312cbaf5a4`
- `.work/garment61/rest-fit/final/summary.json`: `bb5eda3f30cad5840fbacbb3a4d6543ef05040a01b121d6daa912ebeea418a38`
