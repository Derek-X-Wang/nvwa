# One connected shoulder patch

This isolated experiment tests issue80 without changing product assets, weights, materials, body deletion, thresholds, or previous experiments. It authored and evaluated exactly one candidate. The candidate is **REJECTED**.

The reviewed authoring policy is `policy.json`. `topology-freeze.json` names every affected source vertex/triangle and the complete normal accumulation closure. `input-hashes.json` pins the same eighteen historical actual captures and one newer default actual capture. The baseline geometry came from actual captures. Applying the new candidate and its normals in this experiment is analytical. No new candidate runtime was built or uploaded.

The patch contains seven connected position source IDs, twenty-six incident triangles, twenty-one normal source IDs, and sixty-one triangles used to accumulate those normals. Seven vectors were frozen before evaluation. Only source212,830,847 have nonzero vectors. The remaining four vectors are exact zero. Full positive joint influences and all non-position/non-normal garment data remain unchanged.

## Result

All nineteen fixed cases completed. Six cases reject: torso−1/0/+1 at arm1 and arm3. Each introduces two proper transverse cloth/body pairs: cloth240/body13661 and cloth1577/body13661. All nine neutral/knee/end cases retain exact position and normal bytes. No case introduces a winding inversion, degeneracy, nonadjacent local cloth crossing, outside-support mutation, or increased fixed body probe exposure.

The default arm2 analytical ROI body-first samples decrease44→0. Body crossing pairs in this experiment's twenty-six-triangle universe decrease9→0 there. The earlier single-vertex experiment used a smaller universe, so its8→4 counts must not be compared directly with these totals. Default improvement does not override the six rejected intermediate poses.

`verify_result.py` independently reconstructs the fixed rejected triangles from retained actual positions and the recorded delta. It uses a different plane/segment/barycentric predicate and confirms all twelve new-pair instances. `replay_prior.py` first reproduces the previous single-point crossing and fails when its crossing predicate is disabled.

## Replay

Keep source captures, gzip history, raw reports, and the target in ignored local storage. Supply their existing locations as arguments. Do not download replacement inputs.

```sh
python3 experiments/81-shoulder-patch-corrective/replay_prior.py --retained "$RETAINED" --out .work/shoulder-patch80/prior-red-replay.json
python3 experiments/81-shoulder-patch-corrective/author_patch.py --retained "$RETAINED" --out .work/shoulder-patch80/one-target-v1
python3 experiments/81-shoulder-patch-corrective/evaluate_patch.py --target .work/shoulder-patch80/one-target-v1/target.json --history "$HISTORY" --fresh "$RETAINED/h80proof-v1/combined/capture.json" --out .work/shoulder-patch80/evaluation-v1
NVWA_SHOULDER_RETAINED="$RETAINED" python3 -m unittest discover -s experiments/81-shoulder-patch-corrective -p 'test_*.py' -v
python3 experiments/81-shoulder-patch-corrective/verify_result.py --report .work/shoulder-patch80/evaluation-v1/report.json --out .work/shoulder-patch80/independent-audit.json
```

Outputs refuse overwrite. An exact replay requires new empty output locations; do not run authoring again as a tuning loop. Evaluation exits3 for this expected rejection. Authoring, source proof controls, independent audit, and prior rejection replay exit0.

Target SHA256: `fe1a413e2c46fbc82083f2f96e163407a5657ac8dec179a3e1eb9b7a97eb678b`.
Evaluator SHA256: `38fa51cb3be5940a301fef741550546c7f5c3d84797f636c5c12c9dc43217d2b`.

NOT-RUN — actual patch upload, actual normal-vector export, Web visual improvement, Rust/Wasm builds, and desktop GUI. Offline rejection stops runtime work. Existing actual source proof, prior corrected upload, and original failures remain unchanged. Full collision, coplanar/tangent contacts, and unsampled motion remain unverified.

## Source-authoring assessment

The result does not prove all bounded pose corrections are impossible or establish a bad source mesh as the cause. It does reject this one fixed rule. The frozen vector orientation and activation across poses remain possible limits of this rule. Its default8-parameter neutral baseline already has signed nearest-body local sides of source212≈−3.661mm, source847≈−0.226mm, and nearby source583≈−7.732mm. These are local triangle-plane descriptors, not global containment or penetration depth. Neutral activation is exactly zero, so this rule preserves those pre-existing conditions.

At arm1, half activation moves source847 from≈−0.269mm to+0.345mm relative to its nearest triangle, while source212 stays≈−1.480mm. Cloth240 connects source841/847/212. The other new crossing, cloth1577, connects570/847/841: all three are in the frozen position support, and only847 moves on that face. Therefore support-boundary discontinuity alone does not explain the rejection. Vertex nearest-plane clearance does not ensure a triangle clears the curved body surface during partial activation. The61-triangle neighborhood has no new degeneracy or winding inversion, so those gates do not explain the failure either.

Recommended next comparison: a separately identified, manually refitted **rest-shape shoulder panel** versus the unchanged garment. Preserve vertex/face IDs, full weights, materials, and body deletion. The source-author should inspect the connected panel around quad131 and the already negative neighboring source583, fitting triangle surfaces and edges against the body rather than fitting only vertices. Evaluate this single alternate source asset over the same nineteen cases, including neutral. This is source-asset repair with a new asset identity and a deliberate neutral geometry change; it is not an enlarged pose-corrective target. No alternate source asset was authored here, and success remains unknown.
