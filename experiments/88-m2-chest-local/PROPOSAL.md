# One local chest candidate — fixed arm-side mix

**DESIGN ONLY / UNEXECUTED.** No new weight value, candidate, mechanism result or quality result exists. Root must authorize implementation after scope review, and freeze reviewed code hashes before real construction. This is one independent operation on saved candidate50. It is not B1, an old87 retry, or retention of old87's full union.

## Frozen identity and scope

Checkout HEAD: `97f40ecf7ee67003656972ce1cbe233833697fc3`.

| Input | SHA256 |
| --- | --- |
| Saved candidate50 GLB | `2779b012405a915cbc84b38dc18e5eb7a91215661b54ac0c7753ecebb49feae7` |
| Saved candidate50 Work | `033344a831e3a8c6a9bb2fd1e03ce84c78662e568572c528302b86bfaab50fcf` |
| Original87 region.json | `3f1b28f7d75717b961f388479b15e93dbabac973da1acdfbbc7ca202a5729092` |
| Original source generator (context only) | `bc54eec314ccba2ca2a77499b03d96b1ec9afb8c38cfbb9ac9e1fb04f5736f0e` |
| candidate50 loader / construction | `1b014bb943ba5d0701f950ffd230d39903720242730acaa7b46947fc4f4623f2` |
| candidate50 evaluate.py | `ca604662c810986f3dd2bf30d67a5f4fa6e10324834dfa401b3ffc6da3a9d75c` |
| candidate50 CONTRACT.json | `81aa28ca6b5cd1b94dc1fa0cb8f64b9c6d7975043a9a653fc337085cc42d2346` |
| Original49 evaluator.py | `5195632b19607d22d79b6064a38ec47f916bdeea85c552300149eb28e7aefe41` |
| Original49 surface.py | `d4d3ea05e490b9ab16a62f0be3f20248af34fd46a18603b5287c926000102d6c` |
| Source-direction functions | `68e2349d657ae9afac8cc053696f64dd046e041a7945cbbd1e94f531a147ad43` |

The complete dependency, calibration, source-skeleton, raw90-motion, retained old87 failure and unchanged helper hashes are frozen in task `author/input-pins.json`; every consumed input must match before construction/evaluation. Missing input, mismatch or cache means STOP. The source generator is pinned for provenance; this operation does not reconstruct its routes or import/call87.

Maximum domain remains mesh-node22 / primitive1, physical left / +X shoulder, the original96 vertex IDs selected by `.265 < x < .305` and `1.28 < y < 1.40` in glTF rest metres. Original actual POSITION bounds remain `[.2650826573371887,1.2804065942764282,-.07271747291088104]` through `[.30480116605758667,1.3656586408615112,.07271748036146164]`. Frozen region lists remain authoritative:39 seam edges,40 unique endpoints,259 incident source faces (139 wholly inside). No new region or face selection.

Only the42 original vertices whose positive support is exactly `{upper_arm.R, forearm.R}` are eligible. Prior authenticated feasibility records two occupied and two zero slots for each. The54 original `{pelvis,spine,chest,neck}` vertices remain byte exact. All39 seam edges cross these support patterns and have20 arm endpoints and20 torso endpoints. No other support pattern is permitted.

Only eligible vertices' original `JOINTS_0` and `WEIGHTS_0` element bytes may change. Whole GLB JSON and every other BIN byte remain exact, including all54 torso records, vertices outside the42 subset, POSITION/normals/morphs/indices/materials, hierarchy/TRS/binds, all90 animation keys and all other primitives. Preserve original GLB chunk framing and length. Work changes are limited to derivative profile ID, matching character profile ID, asset path and asset hash; all other fields stay exact.

## One fixed spatial field

Select maximum chest fraction **`L = 0.5`**, once. Let `s(t)=clamp(t,0,1)^2 * (3-2*clamp(t,0,1))` and define only on the eligible arm subset:

```
lambda(x,y) = 0.5
              * (1 - s((x - .285) / .020))
              * s((y - 1.28) / .020)
              * s((1.40 - y) / .020)
W_new = (1 - lambda) * W_saved + lambda * chest
```

At the authoring seam `x=.285`, the arm-side limiting chest fraction is0.5 in the y interior1.30–1.38. The two saved arm influences together retain at least half their former mass and keep their original ratio before float32 rounding. The unchanged torso is still its original four-bone mixture. Sharing chest does not imply equal endpoint motion or continuity; the operation intentionally changes only the arm side. Every named seam endpoint uses its own rest position and this same formula. No endpoint-specific strength exists.

The x taper spans the original20mm outer arm half-band and reaches0 at `x=.305`, with zero first derivative there. The y factors reach0 at1.28 and1.40 with zero first derivatives, reaching1 after20mm inward. Thus the continuous field vanishes smoothly at the frozen region's outer x/y selection limits; sampled outermost vertices need not have exactly zero mix. Outside the original open region and throughout the torso subset the operation is exactly the identity. No z cut exists in the original region, so no additional z taper is introduced. The rest mesh's finite triangle discretization can still show a crease; visual inspection remains required.

The50% ceiling is an engineering midpoint: the added shared driver can materially affect the seam while at least50% of each old arm contribution remains. The20mm x taper and20mm y feathers reuse the prior region dimensions. These choices use saved support capacity, the known authoring seam and rest bounds only. They do not use key89 edge vectors, source-motion residuals, intersection counts or images to select or adjust coefficients. No coefficient scan, optimization, fitting, alternate strength, graph pass, retry or later tuning is authorized. Favorable sign and visible benefit are unknown.

## In-place slot and retention policy

Retain each old positive influence in its original slot; multiply its weight by `(1-lambda)`. Put chest in the first original zero-weight slot, replacing only that slot's joint ID. Leave every other zero-weight slot's joint ID and weight bits unchanged. If lambda is exactly0, leave the entire record byte exact. No sorting, pruning, slot compaction, influence merging or mass renormalization. Require exactly four slots, distinct valid original positive bone IDs, two original positives and an available original zero slot before any change.

Serialize each changed weight directly as IEEE float32, read it back, and verify finite nonnegative values; every old positive bone remains strictly positive in its original slot, chest is positive when lambda>0, at most4 positives exist and the sum differs from1 by at most unchanged`2e-6`. Reject underflow, nonfinite values, loss/aliasing of any old positive, bad slot IDs, unexpected supports or normalization failure. Do not repair a failed record. Saved sums can differ slightly from1; float32 readback is required, not an algebraic claim. The original1% discard cap stays`0.01`; no influence is discarded here, so report per-vertex/maximum/sum discarded mass0 and pruned vertex count0. The cap is not relaxed or replaced. This retains original positive bone names and positive contributions, not exact original numeric weights or the old87 union.

## Review, controls and acceptance

1. StageA ends with this proposal and read-only pin receipt. StageB code may be written only after root authorizes implementation. No real constructor invocation until independent code/scope review and root's frozen code-hash release. Synthetic tests use small fabricated inputs only, never real96 inputs as a constructor test. Test actual reject seams for forbidden-byte changes, lost old positive, nonfinite/invalid weights, missing zero slot, invalid slot/support and unchanged2e-6 normalization. Validate in-place slot behavior and zero-field byte identity. No new test framework.
2. Keep old50's exact frozen rotation-byte gate unchanged and attached to old50. Run that old gate on old50 separately. Do not send this weight derivative through a weakened old50 identity check or relabel it as old50. Independently compare derivative JSON and all forbidden bytes to pinned old50, then verify all90 local poses, globals and old source-direction assertions. The derivative's unchanged animation establishes skeleton/source direction preservation, not changed-surface quality.
3. One real construction maximum. Keep candidate and output hashes plus full positive-retention/normalization/byte evidence. Evaluate the same39 named edges and259 incident source faces at fixed keys`[0,15,30,45,60,75,89]`, recording exact source IDs and deformed coordinates. At key89 require **both** edge6497→6508 and edge8998→9001 to shorten and the maximum length over the **same39** edges to decrease. Record the other six keys without selecting a new key or threshold. A failed prediction ends this candidate.
4. Reuse the unchanged original surface analyzer as supplemental evidence with the original fixed seven keys. Record original and derivative weight-partition face IDs/counts, including changed membership. A reduced count after membership changes is noncomparable coverage, not less penetration. Do not weaken/rewrite old surface failures or thresholds. The fixed259 source faces remain the local geometry domain regardless of membership.
5. Only an offline PASS may release actual CLI validate/save/reload, followed by existing same-key Web A/B at key89 and key0 under root's existing runtime/camera/stage. Root owns shared builds/browser resources. Missing cache/evidence, offline invalidity, preservation/retention/normalization/discard failure, either named-edge failure or unchanged/increased39-edge maximum means STOP/HOLD; preserve nonzero exit and all output. No CLI/Web on such a failure. No visible gain, a new crease/volume loss/defect, or unavailable necessary appearance evidence means HOLD / NO-ADOPT, no retry.

## Finite budget and standing limits

Proposed author budget: StageA read/design/write up to20 minutes; StageB code and synthetic controls up to45 minutes after root release; one real construction with30-second hard stop; one offline sequence with240-second overall hard stop (including unchanged old50 gate,90-key comparison, fixed edge/face records and both original surface analyses, each analyzer retaining its60-second own budget). Controls normal plus`-O` each have30-second hard stops. No individual planned command exceeds five minutes. If these bounds are insufficient, stop and report rather than retry, extend, tune or move work to a new host. Root owns any later CLI/Web budget. Missing input/cache, error or overrun stops the phase and retains the receipt.

No download, inference/model, new runtime/verifier framework, CI, shared source/dependency/lock edit, git write, new geometry/region/bone/slot, Blender, native UI or parameter search. Old87 remains STOP / NO-ADOPT / no retry. Original A, #79 acquisition approval boundary, #80 HOLD/99-point backup/full21-before-fit, #112 original FAIL, #3 blocked, #4 gaps, anatomical roll/contact/hidden-surface limits, B1 full-positive aggregate policy and full M2 quality HOLD remain unchanged.

**PARTIAL —** fixed mechanism and permitted scope proposed; source pins read back. **NOT-RUN —** code, synthetic controls, new weights, candidate, offline mechanism/surface, CLI/Web and visual acceptance pending root gates.
