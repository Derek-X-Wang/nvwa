# Bounded garment A/B, candidate contract1

Throwaway issue80 comparison on candidate c655217c0c9c41069b0f45a0d8c2795e455ca6bf. No production change/admission. Root integrates; weights and rest-fit workers own disjoint directories, same immutable inputs. Two parallel methods are separable; no shared schema/Cargo edits by workers. Native GUI unavailable until user returns. No downloads/model runs/paid compute.

Question: can one fixed local intervention reduce the established arm triangle strain without damaging its incident ring, other body variants or motion controls? Do not optimize thresholds against outcomes. A failed/rejected candidate is useful. One declared rule/method, no parameter sweep or endless correction cycle.

## Frozen inputs and affected region

Use existing original assets/characters/mpfb-b1-v1 and retained r4 keyframes in the ORIGINAL task tree (path passed explicitly, not copied into public source). Retained analysis/report hashes remain unchanged. Three torso fits -1/0/+1, jaw0, both4s authored clips, source0/1/2/3/4 give30 actual retained frames. These are actual source frames; reconstructed intermediate33time samples, if used, must be labeled reconstruction. Full jaw-grid/current candidate actual live matrix NOT-RUN unless separately executed. Preserve old1mm foot/20mm apex requirements, body geometry, skeleton/motion and original signed/final-positive influence policy.

Region core source IDs246,244,182, display triangle200. Derive one topological incident ring from unchanged garment indices; fixed exterior boundary. At most64 affected source IDs; all others exact identity. Keep the independent neutral-fold region281,288,376,485,523,534,599,612 as a safety observation. Angle/local surface signs are descriptors, not physical penetration or collision acceptance.

A: one local weight smoothing pass at fixed strength0.5 on core; transition via one ring if required and declared BEFORE results. Preserve all positive influences, normalize, no top4/no negative-source clamp. Rest geometry unchanged. The diagnostic identical-mean-row control is NOT the production candidate.

B: local original-offset retention0.5 on same core,0.75 on immediate ring,1 outside. This changes fitted rest only via source MHCLO offset deltas scaled by the current actual helper-reference scales; weights unchanged. Do not globally delete offsets. One fixed candidate; if worse, reject, do not tune.

## Portable candidate.json

Required JSON keys:
- schema_version:1, id:weight-local-v1 or rest-local-v1; source_profile:nvwa-mpfb-b1-motion-v1.
- region_source_ids: sorted unique allowed source IDs0..1796 (max64).
- weight_overrides:[{source_id:int, weights:[[bone_name:string,positive_finite_weight:float],...]}]. Each row unique and sum1 within1e-6. Stable53 bone names; no truncation. Empty forB.
- offset_deltas:[{source_id:int,delta:[x,y,z]}]. Delta is in ORIGINAL admitted MHCLO offset units, before current helper scaling; finite. Empty forA.
- offset_scale_rules:[{axis:0|1|2,helper_ids:[a,b],reference:finite_nonzero}]; source MHCLO x/y/z_scale rules; empty forA.
- rule:string (all fixed constants + ring/boundary definition), provenance:{relative_source_path:sha256}.

Candidate spec is an immutable experimental recipe, NOT an asset/Work profile. No savedWork upgrade or production override loader. Empty baseline has no interventions. Root renderer must use actual current bones/rest and identify experimental post-upload buffers separately. It must never present a modified buffer as a successful unmodified b1_frame_snapshot.

## Minimum evidence

Both workers implement build/evaluate CLI using Python stdlib and existing experiment60 geometry/checker only. Explicit --captures and --output paths, no hardcoded machine paths in committedfiles. Emit candidate.json, source hashes and per-frame summary, core+incident-ring area/edge ratios, maxdisplacement, normalized weights/changedIDs, original/altered neutral-fold descriptors, finite arrays. Body/rig untouched. Run once on30 retained frames; deterministic original and no-op/affected-boundary controls. Report negative local signs separately. No blanket pass inferred from area ratio alone. No collision/self-intersection/visual/fullcharacter acceptance.

Root schedules all Rust builds/wefty/GPU/UI/servers/CI/Git/external writes. Workers no root Cargo/Cargo.lock/vendor/assets/production/experiments53-60 changes, no peers or subagents. Root produces Web actual visual comparison after specs freeze, then independent review. Nothing enters production until separately reviewed and admitted.

## Review clarifications (before candidate selection)

Independent contract review requested these clarifications. Preliminary A measurements were already reported when this section was frozen; this is a conservative selection rule, not a claim of a preregistered numerical quality threshold.

- Score EVERY displayed triangle incident to ANY changed source ID, including transition/exterior boundary faces, not only the core triangle or triangles whose vertices are all modified. Compare the same exact triangle set for baseline/A/B and report all changed IDs.
- Retain absolute rest/posed areas and edge lengths, candidate-rest ratios AND original-rest ratios. A lower ratio from a larger rest-area denominator alone is not a demonstrated correction. For a bounded candidate to advance, the core strain witness must improve, the full affected-ring extrema must not regress beyond numerical noise, and no new neutral fold-descriptor IDs may be introduced. Any contrary observation is REJECT/HOLD with raw values. Numerical comparisons use abs/relative1e-4 ratio tolerance only to distinguish f32 rounding; this is not a garment acceptance threshold or a replacement for old product guards. No candidate earns production/cloth/collision acceptance from these metrics.
- All visual variants use the SAME explicit policy: rebuild garment area-weighted smooth normals by source-ID triangle adjacency from current actual variant positions, then project/normalize baseline tangents against those normals with deterministic orthogonal fallback and original handedness. This includes baseline. Body arrays/material/stage/camera unchanged. Report the policy and do not claim original-normal renderer parity. Original untouched buffers remain the independent production source/correctness control.
- Scale is signed axis component: (helper[b][axis]−helper[a][axis])/reference, ordered exactly as original admitted MHCLO x/y/z_scale declarations, using actual BODY FITTED REST helper positions in model metres, never posed/helper world positions or absolute distance.
- Candidate schema rejects unknown top-level keys, duplicate IDs/bones/axes, nonfinite/out-of-range values, unknown bone names, nonpositive weights, nonnormalized rows, ID outside declared region, missing scale rules for offsets, invalid helper/reference mapping, mismatched source profile. Frozen source-provenance must match original files before use. At most64IDs; source IDs0..1796.
- Renderer baseline restoration and capture are bound to current actual mesh handles/source IDs/document generation/sample+recipe and candidate identity/hash. Restore exact original POSITION/NORMAL/TANGENT in First before unchanged runtime validation; do not mutate indices/body/rig. At Last first require a fresh successful unchanged b1_frame_snapshot, then apply a candidate and read ACTUAL Assets<Mesh> arrays for experimental capture. Never label altered arrays as the unchanged product snapshot. Invalidate stale capture/report on failed sample; no previous-green fallback.
- Required live experiment controls: A→B→baseline→A, paused hold, nonmonotonic seek, torso switch; original unchanged snapshot must pass after restoring baseline. Distinguish current baseline original readback, independent candidate expectation, actual uploaded variant buffers and screenshot observations. Dynamic actions are current bone-driven recomputation, never stored-frame animation. Native visual remains NOT-RUN until available.

## Experimental graphical capture envelope

Reuse the unchanged experiment60 same-origin exclusive capture server. Top-level envelope remains kind/request/snapshot/evidence, kind=studio; snapshot is the successful ORIGINAL production b1_frame_snapshot obtained BEFORE the experimental overlay. request retains only existing60 request keys. New candidate information belongs under evidence, never silently substitutes modified positions in snapshot.parts.

Required evidence fields: experiment='61-b1-garment-ab', variant_id, candidate_sha256 (baseline usesnull), normal_policy='source-area-normal+projected-tangent-v1', original_restore_verified=true, actual_garment={mesh_handle,display_entity,source_ids,indices,positions,normals,tangents}, candidate_recipe and capture_identity={parameters,sample,revision}. Actual garment arrays MUST be re-read from Assets<Mesh> AFTER writing the overlay; candidate_recipe is the exact compiled immutable recipe/sha. Root generates variants.json from authenticated candidate source files before build. Runtime accepts only these compiledIDs, not arbitrary overrides/paths. First restoration must enable the unchanged strict snapshot API again; failure cancels current capture/report (no oldgreenreuse).

A sample command may have a variant field for the experimentcontroller; retain full command under evidence.original_request but strip only that field from the outer60-compatible request. DOM store compares captured full command/variant to the visible exact fields, then submits an unmodified capture. Experimental IDs must be visibly labeled; variants are transient and do not save into Work. Current normal Studio/Work operations remain baseline behavior and do not persist variants.
