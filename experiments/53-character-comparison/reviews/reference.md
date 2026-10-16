# Independent reference audit — run 3

**PASS for the bounded geometry reference. No actionable blocking finding in the reviewed snapshot.** This is an audit of existing files and numeric receipts. I did not download, build, run Blender/MPFB, render, or change the reference/common manifest. Only this review file was written during the audit.

## Frozen reviewed identities

Workspace: `/Users/derekxwang/.codex/worktrees/character-foundation-research/nvwa`.

| Reviewed file | SHA256 |
|---|---|
| `experiments/53-character-comparison/reference/core_smoke.py` | `f3cef6aa9d7cd2c9610d3332260835a2cdfee8ef293b7d0c3a118c141cb2321c` |
| `.work/character-approved-20261016/reference-full-run3/summary.json` | `65bf0da652df743614cd6ec04c8eb5d2bc52869876819b4cc5f4ae2393021302` |
| `.work/character-approved-20261016/common-sample.json` | `2e8566a4f12de710ead88f6aa2d71fc44e0680761a4f2fdc48a844b6f3534ab7` |
| Approved `female_sportsuit01.mhclo` | `6df057d3116db93afbbbb6d692f92cce84aa16db699f47dd14e825d07c6fd42f` |

The summary driver digest matches the current reviewed driver. All eight case JSON hashes match the summary. The common manifest's reference-summary digest matches the completed run-3 summary. Every one of its 23 listed files has the recorded actual hash; the 14 non-reference files also match the earlier delivery receipts. The inspected run log ends with `NVWA_MPFB_CORE` for eight cases, 19,158 vertices and 53 bones; this audit did not independently launch that process or observe its exit status.

## Checked behavior

### Raw baseline, target sign, axis and units — PASS

Driver lines 39–54 use `ObjectService.load_base_mesh(scale_factor=0.1)`, read the actual raw OBJ, fit its affine transform and separately assert the declared transform against every imported vertex. They do not call `HumanService.create_human`, apply phenotype defaults, or ground the body. The corresponding installed source is `mpfb-addon/services/objectservice.py:774–849`: OBJ import, applied import rotation, then applied requested scale.

Driver lines 55–63 load four actual approved targets through MPFB. Lines 97–100 select a positive decr weight for a negative recipe and a positive incr weight for a positive recipe. The target parser in `mpfb-addon/services/targetservice.py:415–439` converts `(x,y,z)` source offsets to `(x,-z,y)`; lines 358–379 multiply by the stored object scale. This agrees with the driver's declared raw-OBJ transform `(0.1*x,-0.1*z,0.1*y)`.

I separately parsed the raw OBJ and gzip target files with Python's standard library, then calculated each recorded case from those original data files. Across every body vertex in all eight cases, maximum component error was **3.807830809554602e-7 metres**, below the common numeric tolerance `1e-5`. Target files have 13,196/12,865 body decr/incr rows and 60/46 face decr/incr rows. The half and combination cases use actual continuous weights, not model switches.

Metres are supported by the installed upstream UI definition: `ui/new_human/newhuman/properties/scale_factor.json:7–11` defines `METER` as one Blender unit per metre, and `operators/createhuman.py:30–36` maps it to scale `0.1` (decimetres use `1.0`, centimetres `10.0`). This is a coordinate convention for numeric comparison, not a claim that the driver configures a rendering scene's displayed unit labels.

The baseline is the raw common mesh, about 1.69455 metres in Z extent under this convention. It is not an assertion about a default adult phenotype. Negative/positive labels denote the chosen data pair, not a universal anatomical parameter scale.

### Real 53-bone refit — PASS for rest endpoints

Driver lines 64–65 construct the actual `game_engine` rig. Lines 101–103 call `HumanService.refit()` after each recipe and update the view layer. The installed call chain is `services/humanservice.py:1691–1738` → `services/rigservice.py:1423–1476,1530–1565` → `entities/rig.py:53–90,376–398`. It refits the existing skeleton rather than recreating a fixed rig for each case.

`entities/rig.py:864–940` computes source-cage positions from the current shape-key mix, without evaluating visibility masks; `get_best_location_from_strategy()` at lines 272–304 resolves the source rig strategies. This approved rig contains 53 bones, using CUBE and MEAN endpoints, with no endpoint offsets. The vertex-group range expansion is explicitly inclusive in `services/objectservice.py:886–892`.

I separately expanded the approved vertex groups and evaluated every source CUBE/MEAN head and tail against each case's recorded body coordinates. All 53 bone names and parents match the source definition in every case. Maximum endpoint discrepancy is **1.1920928955078125e-7 metres**. Body-negative moves 42 bones by more than `1e-6` metres; body-half, body-positive and combined move 41. Body-positive's maximum endpoint change from neutral is about `0.102800012` metres. This provides direct evidence that the rig does change with the body recipe.

Face-only cases do not move this rig's endpoints. That is consistent with this small local surface-target fixture and this simple GameEngine skeleton. It must not be presented as proof of a jaw bone, face rig, facial animation or expression system.

### Garment identity and refit — PASS for geometry

Driver lines 67–89 import the approved MHCLO directly, with subdivision disabled, `material_type="NONE"`, actual rigging and interpolated weights, and no custom subrig/weights import. Lines 72–85 register the same source files under isolated user resources so MPFB can resolve the same asset on refit. I inspected the actual registered directory at `.work/character-approved-20261016/blender-user/extensions/.user/user_default/mpfb/data/clothes/female_sportsuit01/`; it contains exactly the six approved files, and each hash matches the original selected garment file. The summary's MHCLO hash matches the delivery receipt.

The installed import/refit chain is `services/humanservice.py:481–526,1691–1722` and `services/clothesservice.py:121–258`. MHCLO vertices are resolved from a temporary current shape-key mix, and offsets use the MHCLO's actual three scale references. I independently parsed the original 1,797-row MHCLO and recomputed the weighted body positions and scaled offsets for every case. Maximum discrepancy from the recorded evaluated garment positions is **1.2746108768446618e-7 metres**. Body-positive changes garment coordinates by about `0.102801144` metres. The garment therefore tracks the current body in this reference; the outputs are not a fixed pre-fitted copy.

The original MHCLO/OBJ/MHMAT explicitly declare CC0, and the three texture references exist in the approved six-file delivery. The two absent legacy MakeHuman GLSL/litsphere references remain a documented appearance limitation. The driver intentionally does not execute those materials. No material parity is admitted by this PASS.

### Complete cage capture before visibility MASK — PASS for declared scope

Clothing creates the real `Delete.female_sportsuit01` body MASK in every case. Driver lines 104–120 temporarily disable only the currently visible body MASK modifiers, capture the evaluated complete cage, then restore the masks in `finally` before garment evaluation. Each receipt explicitly names `body_capture` and records the mask state at lines 124–130. Recorded body, rig and garment world matrices are all identity in all eight cases, so these particular comparisons do not mix local and world coordinates.

This is a declared numeric-source-cage policy, not an attempt to report the displayed masked mesh as 19,158 vertices. Raw correspondence is checked against the source coordinates and independently reproduced targets. Keeping helper vertices is necessary for the actual rig's joint-cube strategies. The common manifest repeats the policy. Displayed topology after masking, helper removal, skin deformation under poses and hidden geometry are outside this comparison and remain unverified.

### No copied reference outputs as source inputs — PASS

The common manifest contains 14 source files and nine explicitly marked reference files. `source_paths` points only to original delivered OBJ/groups/rig/weights and garment sources. Each target and every other non-reference entry matches its delivery receipt and original data hash. Reference JSON exists only under `role="reference"` / `reference_path`; it is not relabeled as an upstream target, joint definition, garment mapping, or runtime input.

`reference/freeze_sample.py:43–67` freezes approved original sources; lines 68–78 add the executed oracle files as separate reference roles. This structure supports an honest source-vs-oracle comparison. This review does not certify how a future A/B adapter uses those paths; a separate adapter review must ensure it does not read expected coordinates as its produced answer.

## Verification limits

- This audit ran read-only standard-library checks against existing source/data/receipts. No independent Blender rerun, build, download, graphics task or new test harness was executed.
- The source/reference numeric fixture passes. Shoulder/elbow/knee poses, pose matrices, inverse-bind correctness, normalized skinning behavior, animation, GLB export, masking/deleted topology, shading, clothing penetration, native/Web rendering and whole-Work exchange remain outside this PASS.
- The common tolerance explicitly covers metre component numeric parity only. Bone rest matrices are captured, but this audit independently checked endpoints/parent identity, not the complete roll/rest/inverse-bind contract.
- The driver trusts its supplied source directory during the run; its summary directly hashes the base mesh and MHCLO, while the frozen common manifest and delivery receipts establish the current target/rig/weight identities. For later runs against mutable files, freeze and check the same manifest before execution rather than treating this snapshot audit as a permanent admission check.
- The original `macro.json` classification and broader parameter-system capability remain unresolved; this paired local-target reference does not implement or admit that whole system.

**VERIFIED — Reviewed run-3 identities, all eight target/body cases, 53-bone source strategies, 1,797-row garment mapping, pre-MASK scope and source/oracle separation agree within the stated numeric contract. Broader runtime and visual acceptance remain NOT-RUN by this audit.**
