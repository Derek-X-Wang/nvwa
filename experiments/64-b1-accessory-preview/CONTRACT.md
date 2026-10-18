# Experiment 64: live B1 skin + low-poly eyes + short04 hair

This isolated crate wraps the unchanged production Studio/Work runtime. Issue #79 preparation only; #3 blocked, #4 gap, clothes/M2 HOLD remain. No AI generation, gaze, physics, MPFB legacyshader parity, production save support or quality acceptance claim.

## Fixed domains and units

Use authenticated experiment62 fixed assets without copies/downloads. Recover every source ID 0..19157 from the current actual body rest array; duplicate source positions must agree exactly. Keep signed normalized MHCLO coefficients and original ordered scale helpers. Convert accessory reference lengths and offsets ×0.1 to model metres, no axis swap. Final weights sum source positive weights ×signed coefficients by bone; keep ALL strictly positive final aggregates, normalize; no top4, threshold, head substitution. Use all actual 53 named skin matrices. Hair non-head influences are preserved.

Accessory OBJ faces retain each (position, UV, normal) corner. Fixed assets have no supplied normals: calculate area-weighted source normals from fitted triangulated geometry, share by original position across UV seams, then transform by full weighted inverse-transpose skin matrices and normalize. Reject invalid/degenerate geometry, missing UV, invalid indices, nonfinite data and unsupported directives. Fan triangulation preserves original winding; no legacy triangulation parity claim. V flips once from OBJ to Bevy. Upload model-local posed positions; put the actual body display_transform on each unattached accessory entity exactly once. model_to_world is provenance only.

## Material conversion

Decode fixed approved PNG as sRGB RGBA8 with dimensions/hashes checked. Simple white base color ×diffuse RGBA, roughness0.7, metallic0. Hair two-sided; eyes backface culled. Both use AlphaMode::Mask(0.5), an explicit bounded cutout conversion; partial alpha is discarded at cutoff. No alpha-to-coverage, SSS, shininess/litsphere/shader fetch or parity claim. No arbitrary MHMAT execution.

## Runtime and lifecycle

Three modes: baseline / skin / skin+eyes+hair. Skin binding reuses62 correspondence and restoration. Accessory fitting takes current runtime cage, never retained offline frames; skinning follows each actual published authored-motion frame during play. Refit/reopen is keyed to current published generation/revision/character/body mesh. Dispose old accessory entities/meshes/materials on invalidation, mode removal or successful reload; never let extra display meshes pollute body identity. Open failure leaves production Work unchanged; invalid proof clears and temporary attachments hide until a valid frame recovers. Errors remain visible and are not credited as success. Ordinary Work save/open/undo/revision semantics remain unchanged. Appearance is temporary, NOT saved. A persistent native/Web label and controls state this.

## Control and evidence

Shared Rust controller: strict JSON request_id/action; actions baseline,skin,accessories,report,sample,play,pause. sample accepts only authored arm/knee clips, seconds0..4, torso−1..1,jaw0..1; reject extra/inapplicable keys, malformed commands and nonfinite values. Native file channel B1_64_COMMAND_FILE; Wasm b1_64_command/report/frame. Native UI operates same queue; optional B1_64_REPORT_FILE and B1_64_FRAME_FILE emit only requested completed evidence. Reports bind request/revision/generation/sample serial/appearance identity. desired/applied both name baseline, skin, or skin+eyes+hair; the capture sink requires their exact equality and binds accessory identity to the current snapshot. Native explicit command-file read/UTF8 errors invalidate proof and remain visible; a readable valid JSON command recovers. Full frame exports actual rest, full weights, actual mesh CPU upload positions/normals/UV/index arrays, transform/material/image observations and posed bounds. Tangents are NOT-EXPORTED; simple material uses no normal map. Current material flags and the bound image bytes are observed at each requested full capture; image bytes are not rehashed on every live animation tick. These are CPU Assets<Mesh> observations, NOT GPU readback or pixel proof. Root owns native/Web launch, CUA, screenshots and GPU acceptance. Unsupported Work/asset/bones/mapping/NaN command errors are explicit and recoverable.

## Verification boundary

Short Rust controls test signed final aggregation, >4 influences, complete cage, malformed mappings/OBJ, exactly-once placement, commands and current fixed source counts/hashes. Native/Web compilation and actual GUI evidence reported separately. Root samples 3 torso×3 jaw×2 authored clips×neutral/peak/end in accessories mode, plus a small set of same-frame baseline/skin comparisons and continuous play; no static substitute. No changes outside64 and .work/appearance64;62/63/root manifests/production/assets freeze. No commit/push/external writes by worker.
