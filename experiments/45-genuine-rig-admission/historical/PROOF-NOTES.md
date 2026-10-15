# Genuine sample mapping feasibility — private, bounded, no admission

Decision: **GO for one new isolated numerical mapping candidate using only the exact two genuine raw files. HOLD playable admission/export.** The current 43 mapping must not be copied unchanged or called genuine calibration. A new admission experiment can be proposed, but its pass conditions require a declared source/target semantic and neutral-pose alignment plus the root correction below. This does not block publication of the independently completed CPU trial.

No model/build/GPU/UI/network/Git operation was performed. Only private stdlib calculations and notes were written here. Experiments 41/42/43, target assets, and raw files were read unchanged. `python3 -B probe.py` completed exit 0 in about 0.18 s. `numeric-proof.json` retains hashes and exact numbers. It contains no exported animation.

## What the actual pinned C++ establishes

All C++ paths below are relative to `.work/m2-provider/runtime/kimodo/`, revision `5679ff19ba0a522c0b0516e9a9d402fe1af2c027`.

* `src/motion_decode.cpp:7-10`, SHA256 `d9f0076d3254cd6d89719a0097c09aa265fea8ad3404bf303d527b90ce5714ff`: conventional row-major multiplication acting on column vectors. `six` uses a=normalize(first vector), z=normalize(a cross second vector), b=z cross a; columns are (a,b,z). For nondegenerate inputs this is an orthonormal determinant +1 rotation. Quaternion conversion writes **X,Y,Z,W**, not X,Y,W,Z. Positive axis rotations follow the ordinary right-hand matrix convention. Tiny private Python mirrors of this exact six algebra exercise +/-90 degrees about each axis; these are mathematical controls, not execution of C++ and not trained-data-axis controls. The decoder lacks a zero-vector/parallel-vector guard; this clip's finite normalized quaternion outputs exclude observed nonfinite output, but do not validate all inputs.
* `src/motion_decode.cpp:12`: unnormalizes model features, creates per-joint global rotation g from 6D, then emits l[j]=transpose(g[parent])*g[j], root l=g[root]. Therefore the emitted channels are absolute parent-local rotations. Re-localizing them or applying a rest-delta interpretation again is wrong. Raw roots are `(f[0]+f[5], f[6], f[2]+f[7])`; there is no velocity integration, extra heading multiplication, or 0.988 addition in this decoder. Heading is already represented in the emitted global/body rotation state. Neither root orientation nor root height should be applied a second time.
* `src/sequence.cpp:23-32`, SHA256 `1b099faabcfa7a9e179bbfb0a1adbe1d9976b8bd9fc83e1b56a6c118c4236808`: confirms local/global algebra and FK. Root posed position is the decoded root; child position is parent posed position + parent global rotation * child fixed offset. This is static corroboration from sequence conditioning code; it was not run in the successful single prompt trial and does not make this decoded output official-parity evidence.
* `src/skeleton.hpp:45-67,91`, SHA256 `6c1e1d98170a99105bd325c32caff5421bfb20d1e16160980a9f2c3258e244a3`: exact SOMA30 names/parents/offsets. Hips offset is **zero**. Left limb offsets are +X, upright offsets +Y, toes +Z. The data supplies a useful conventional Y-up/+Z-facing rest-layout interpretation. It does not independently measure trained-data semantics. The source comment says offsets were extracted in a trusted reference container; this task does not independently validate that claim or execute official SOMA assets.
* `src/model.cpp:94-109`, SHA256 `366fb57a715536dd02182d1756022b656c99caec920e0f38be1f30280ae01d7a`, and `src/generate.cpp:16-27`, SHA256 `7c4a301666566b29aa042a00bfbdee7aeaa92bd40ed62c9585200c0c2be75b88`: sampling result passes to this decoder, then the vectors are written directly as native floats.
* Cached pinned `sources/cpp-scripts__export_glb.py:20-21,40-48,102-115,148,197-206,227-229`, SHA256 `574a5f1f20476268e33b0007aa2ec212eb5f28767895d810130cc7a639b0cabb`: exporter rest Hips translation is 0.988m for rest mesh/inverse binds, but root animation directly replaces its node translation with the raw root vector. It does **not** add 0.988m to the animation. Identity rest rotations are consistent with exporter nodes. This exporter was read, not executed, and its intent is not renderer or official decoder parity.

## Actual raw observations and limits

Before any numeric inspection, the exact raw files were hash checked:

* root SHA256 `dcc221d506999a803b1d0fddef87abc0131b1e8f4e64187bc57fde3a63c204af`, 1080 bytes.
* rotation SHA256 `67914c5d72c54429bf8a70d3f9ef43157fb5181fa36ab2c5f8ce7f9dc69d3a55`, 43200 bytes.

90x30 quaternion samples are finite. Maximum norm error = 8.412634311394385e-8. Root Y ranges 0.9940531254–0.9962186813m. Root XZ path length is 0.0734929272m. Sample times are i/30 by the run contract, last 89/30 seconds; these raw files do not store timing internally.

Using the exact C++ parent graph/offsets and conventional quaternion matrix FK:

| Source named joint | Y range (m) | XZ joint path length (m) |
|---|---:|---:|
| LeftHand | 0.838279–0.868489 | 0.312935 |
| RightHand | 0.841497–1.711810 | 1.970131 |
| LeftFoot | 0.065609–0.067996 | 0.021352 |
| RightFoot | 0.064447–0.067143 | 0.019817 |

These are source FK observations under a declared algebra, not visual motion quality, contact, foot-slide, floor, or a verified semantic right-hand wave. There are no contact labels. No target or source rendered playback ran.

Negative controls on the actual source bytes: q versus -q gives zero FK difference; conjugating XYZ signs changes positions by up to 1.386387009m; misreading XYZW as XYWZ changes them by 1.145016661m; localizing the already-local channels again changes them by 0.732777111m. These establish that conventions matter for this clip. They do not establish which semantic mapping is artistically correct.

All 48 signed permutation coordinate bases (24 proper, 24 improper) are numerically FK-equivariant when roots, offsets, and rotations are consistently transformed, max error 1.1444e-16m. Thus norm, determinant, and FK self-consistency cannot distinguish a globally mirrored/reoriented convention or prove trained-data axis labels. An improper basis still maps a proper rotation to a proper rotation through B*R*B^-1. The semantic question remains outside this algebra test.

## Root world-position proof and necessary correction

Frozen target GLB hash `f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6`. Actual rest scene-root translation is (0,0.0799999982,0); pelvis is its child at local (0,0.7499999404,0), rest pelvis world Y 0.8299999386m. Target root scale is retained exactly.

43 `spike.py:190-211` uses `target_rest_root + (source_absolute_root - source_rest_root)`. This was valid only for its deliberately authored root anchor. Substituting actual C++ source rest Hips=zero leaves the full approximately 0.995m source hip height above the target's approximately 0.83m hip rest offset. **Actual FK** puts target pelvis Y at 1.823558187–1.826174534m, maximum source Hips world mismatch 0.8299999133m.

For a declared policy that matches target pelvis world position to source Hips trajectory h(t), set:

```
target_scene_root_translation(t) = h(t) - R_target_root(t) * S_target_root * target_pelvis_rest_translation
```

This assumes the observed exact target hierarchy: identity nonjoint ancestor, pelvis directly under scene root, target local translations/scales fixed, and target root animated rotation already calculated. For a declared coordinate conversion h(t)=B*source_Hips(t), use B consistently for roots, offsets and rotation calibration. For other hierarchies derive the complete affine parent contribution rather than reuse this formula.

On all 90 actual frames, this formula gives maximum target pelvis/source Hips error 1.7347e-18m. Simply subtracting the unrotated pelvis offset still causes up to **0.0282249801m** error because the animated root rotates that offset. Adding target root rest again causes **0.0799999982m** error. The exact rebased scene-root Y is 0.2445480623–0.2462628266m; its XZ path is 0.1676906921m because it compensates for rotating pelvis offset. Therefore testing scene-root path equality to source Hips is the wrong oracle: test target pelvis world trajectory instead. If a future product chooses ground/height normalization rather than hip-world matching, that must be a distinct declared policy with its own oracle, not an inference from 0.988 or from the first generated frame.

## Genuine rest/semantic mapping is still a gate

43's rule D[j]=G_source_anim[s]*inverse(G_source_rest[s])*G_target_rest[j] conserves its declared global rotational deltas, with removed links accumulated in order. Source has identity local rest rotations, so transplanting this rule reduces to G_source_anim[s]*G_target_rest[j]. Passing that rotational oracle does not establish a neutral-pose/anatomical frame calibration on the actual source and target.

Actual rest FK shows a direct mismatch that 43's authored sources did not contain: source LeftHand is (+0.723611,+0.429163,-0.012884)m relative to zero Hips; target hand.L rests at (-0.570000,+0.940000,+0.010000)m world with pelvis Y~0.83. Source LeftLeg is +X; target thigh.L is -X. Target arms are angled down in bind rest while source identity offsets spread arms horizontally. Naming-to-lateral-side and neutral-pose correspondence must be explicitly resolved. A rotation of 180 degrees about Y would reverse both X and Z; flipping X alone is a reflection. Neither choice follows from quaternion norms. The exact target construction source `tools/blender/generate_fixture.py:144-162` authors target L on negative X and forward-facing details at negative Blender Y (`:64-75`), which needs an explicit coordinate interpretation before a semantic claim. This is current source/asset inspection, not project-history inference.

After exact hip-world matching, **blindly retaining 43's existing calibration** still causes maximum source/target named endpoint errors: LeftHand 1.288952516m, RightHand 1.325937493m, LeftFoot 0.361757228m, RightFoot 0.357092260m. These differences combine proportions, omitted positional offsets, neutral-pose differences, and semantic/basis choices. They do not individually identify the cause and must not be presented as an error bound on a corrected future method. They are sufficient evidence against promoting 43 unchanged. The existing 0.277119m authored endpoint loss was not a genuine-data upper bound.

No arbitrary rig is needed for the next candidate: freeze this one SOMA30 source definition and this one Nvwa18 asset, derive declared anatomical joint frames from rest geometry with an explicit secondary-axis/twist rule, and test orientation/segment-direction outcomes independently. Bones with only one outgoing direction leave twist underdetermined; hierarchy names do not fix it. Preserve that limitation. Neutral target bind pose and source model neutral pose are not automatically the same physical pose.

## Minimum next-experiment gates

1. Bind both raw hashes, actual successful process/run receipt, exact code/model identities, skeleton/asset hashes, mapping implementation hash, and conversion policy. Preserve `provenance_kind=generated`; derived mapping must retain raw provenance. Do not rewrite this output as authored or synthesize a receipt that claims an inference rerun.
2. New isolated experiment/output only. Leave 42's unconditional generated rejection (`src/lib.rs:251-266`, SHA256 `c3b990a4d33cf7942b25655e3cb9ee5a463123c4325f935abb64b895cda184a2`) and frozen contract hash `74bb268930428195242a99cffe6fd3307338be2dbd435583212607185a6bb257` intact. A new admission layer must explicitly review real evidence; changing 42 or relabelling input is not admission.
3. Declare signed source/target basis and semantic left/right policy; positive/negative +/-X/Y/Z noncommuting controls must fail under wrong signs/order/swapped sides. Retain q/-q equivalence. Source-trained axis semantics and official parity stay unverified unless separately observed.
4. Root oracle must compare target pelvis world trajectory, not target scene root. Retain the three failing controls measured here: old43 zero-source-rest policy, subtracting unrotated pelvis offset, and adding target rest/0.988 again. Test parent/root rotation only and translation only, with exact fixed target scales.
5. Calibrate actual neutral-pose/anatomical frames. Test source and target geometric segment directions in addition to joint global orientations. Include asymmetric articulated controls, omitted shoulder/spine/neck rotation controls, and left/right-negative controls. An oracle restating the mapper is insufficient.
6. Label endpoint/proportion/contact limitations; rotation-only collapsed chains cannot preserve all removed moving offsets. Preserve all original target rest/binds/scales and independently reload any future serialized channels for affine FK; compare against pre-export matrices and hip world positions under f32 rounding.
7. Genuine playable admission and actual native/Web playback remain separate gates. No generated action or visual success is proved by this note. Continue-gate recommendation: first fix/root-test and resolve actual semantic/rest calibration in a numeric candidate; only then request a concrete isolated generated export/playback gate.

VERIFIED — Exact raw hashes, C++ algebra/source hash inspection, one tiny stdlib FK calculation, root/representation negative controls, all signed-basis equivariance. NOT-RUN — C++ control execution, official decoder parity, anatomical calibration, generated importer/export, Work, native/Web playback, semantic quality, contacts, arbitrary rigs.
