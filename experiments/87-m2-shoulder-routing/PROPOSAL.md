# One construction proposal — source-routing blend

UNEXECUTED: no new influence values or correction have been constructed/evaluated.

## Frozen source region

Control is saved candidate50 GLB SHA256 `2779b012405a915cbc84b38dc18e5eb7a91215661b54ac0c7753ecebb49feae7`.
Only mesh-node22 / primitive1 (teal tunic), physical-left / +X shoulder. Select original serialized POSITION vertices satisfying `.265 < x < .305` and `1.28 < y < 1.40` metres. These coordinates are glTF rest coordinates; y is height. This gives96 source vertices,259 incident source triangle indices,139 triangles wholly inside. Actual selected height bounds are1.2804066–1.3656586m. `proposed-region.json` freezes their indices and bounds. The old cap examples at rest height≈1.31–1.36m are inside. The x band is a symmetric20mm feather on each side of the original .285m author boundary. The y range bounds only this shoulder, with20mm edge feathers below/above. These are one fixed local pilot dimensions chosen from the known routing boundary and observed cap region, not inferred anatomy or parameters fitted to motion keys.

Only selected `JOINTS_0` and `WEIGHTS_0` element bytes may change. All other BIN bytes, whole GLB JSON, animation90keys, hierarchy/TRS/binds, geometry/normals/morphs/indices/materials, other primitives and opposite shoulder remain exact. New Work identity/asset path/hash may change only as needed for the derivative. No iteration, new topology, Blender or rest/source alteration.

## Operation (one application, mix fixed by source position)

Reuse the original authoring rule directly. Source generator SHA256 is `bc54eec314ccba2ca2a77499b03d96b1ec9afb8c38cfbb9ac9e1fb04f5736f0e`; lines168–191 define route support, point-to-bone-segment distance and normalized compact Gaussian. Before construction, require that the same source rule reproduces the selected saved original route weights within the existing2e-6 weight tolerance, using bind/rest vertices and source-defined segments transformed to glTF axes (x,y,z)=(author x,author z,-author y). If not, STOP; do not change the reconstruction or tolerance.

For each selected vertex compute the two original route distributions independently:

- T: `{pelvis,spine,chest,neck}`.
- A: `{upper_arm.R,forearm.R,hand.R,chest}`.

For each route, sort distance to source-defined bone segments, take the existing4 names, compute `exp(-((distance-min_distance)/.070)^2)`, normalize, remove normalized weights<=.0001, then normalize again exactly as author code. Bone segments and .070/.0001 are reused source constants, never estimated from this motion. No anatomical twist inference.

Define `s(t)=clamp(t,0,1)^2*(3-2*clamp(t,0,1))`.

`a=s((x-.265)/.040)`

`m=s((y-1.28)/.020)*s((1.40-y)/.020)`

`W_union=(1-m)*W_saved + m*((1-a)*T + a*A)`.

This is one fixed spatial routing feather; no graph smoothing or per-key data enters construction. No passes/iterations. Interior y1.30–1.38 uses full mix1; edge mix smoothly reaches0. At x boundary the T/A blend is50/50. Source vertices outside the open region remain byte exact.

## Explicit original-fixture four-slot scope

The original GLB fixture has exactly four serialized skin slots. The construction may produce a union of more than4 influences. For THIS isolated original GLB derivative only: sort positive union weights descending, ties by actual node index ascending; retain4; record every discarded influence and mass per vertex; renormalize retained mass; serialize existing joint-slot format and float32 weights. Pad unused slots with zero weights. Reject if any vertex discards more than.01 total normalized mass (1%), or if any value is invalid/negative, a joint index is invalid, or serialized sum differs from1 by more than existing2e-6. Report maximum/sum discarded mass and number of pruned vertices, even if zero. No change to B1 full-positive aggregate influence policy, GPU influence policy, importer or renderer. The1% limit is a new pilot construction stop, not a relaxed existing gate or proof of anatomical quality. If exceeded, stop rather than changing the band/support/mass limit.

## Acceptance and stop

1. Preserve full GLB JSON and every BIN byte outside the96 allowed joint/weight records. All90 local poses and candidate50 source-direction agreement remain exact. Existing independent parser/FK/skin assertions, glTF normalization tolerance and runtime comparison thresholds remain unchanged. Keep old50's exact-byte identity predicate attached to old50; do not weaken it for this new identity.
2. Compare the unchanged39 source boundary edges (from prior retained inspection) and259 original incident source faces. Record their exact IDs and deformed coordinates; use existing skin evaluator. The old edge6497→6508 and8998→9001 must have shorter deformed lengths at key89, and the maximum over the SAME39 edges must decrease there. These are falsifiable mechanism diagnostics, not replacement quality gates. Other six held keys provide fixed observations. No new collision/evaluator framework or threshold fitting.
3. Run the unchanged original surface analysis as supplemental evidence, including triangle membership counts and changed source-face IDs. Any count decrease after membership changes is explicitly noncomparable coverage, not penetration improvement. Do not remove failures or make old count threshold easier. Fixed original edge/face scope remains the pilot domain.
4. Actual CLI validate/save/reload must succeed using the existing importer/core. Offline invalidity,1% discard stop, preservation failure, failed mechanism prediction or unavailable required cache ends this candidate; no second parameter choice.
5. Only after valid offline, actual Web control/candidate at held key89 and key0 through existing probe/runtime, same declared camera/stage. Root/reviewer judge whether the physical-left cap notch improves on original images and whether the259-face band introduces a new crease/volume loss or other visible defect. Lower counts or edge stretch alone cannot admit quality. No visible improvement or a new defect means NO-ADOPT/HOLD, no retry.
6. No new download/inference/host/native UI/human trial. Current-main Web is separate from historical50. Unavailable worker adapter is reported once. Anatomy/roll/hidden surface/contact/semantic limitations remain. All existing broader HOLD/FAIL/blocked/gaps remain.

PARTIAL —96-vertex/259-face region and source constants authenticated; exact construction proposed. Candidate, new tests, CLI, build and Web NOT-RUN pending root/Astra scope gate.
