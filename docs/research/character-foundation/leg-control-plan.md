# Versioned body-control plan

## Evidence and meaning

The checked `main` baseline is `e21322c` (#146). B1 v5 has 11 shape parameters; the 53-bone rig already includes thigh, calf, feet, clavicle, upper arm, forearm and hand chains, but the shipped profile has no shape sliders for legs, chest, arms or hands. Pose keys and diagnostic elbow/knee rotations are motion controls, not body dimensions. The pinned [MPFB 2.0.18 catalogue](https://github.com/makehumancommunity/mpfb2/blob/d0a32e57a7f915cb2f2b95410e2117648c7bbb7e/src/mpfb/data/targets/target.json) contains the four selected leg pairs and further upper-body candidates. MPFB distinguishes [CC0 data from GPL program logic](https://github.com/makehumancommunity/mpfb2/blob/d0a32e57a7f915cb2f2b95410e2117648c7bbb7e/LICENSE.md); this change imports target data only, with pinned hashes in `assets/characters/mpfb-b1-v6/provenance/leg-target-source.json`.

The [Character Creator morph catalogue](https://www.reallusion.com/contentstore/iclone/pack/cc_essential_morph_skin/morph-sliders.aspx) is a useful decomposition of leg, chest, arm and hand controls; it is neither a biological norm nor evidence that Nvwa has its proprietary morph assets. [Its slider editor](https://manual.reallusion.com/character-creator-4/content/enu/4.0/06_Customizing_Morphing_Sliders/User_Interface.htm) uses endpoint weights. Nvwa's `[-1,1]` similarly means a signed fraction of an authored target, not centimetres or a uniform perceived change.

## Stage 1: four bilateral leg controls

The separate static B1 v6 profile adds `thigh_length`, `lower_leg_length`, `thigh_girth` and `calf_girth`. Each maps to one original, unsided MPFB decrease/increase pair (`measure-upperleg-height`, `measure-lowerleg-height`, `measure-thigh-circ`, `measure-calf-circ`). The two height sources move lower joint-cube helpers as well as visible body vertices. Runtime still fits the rig after morphing, then evaluates its existing positive full-weight CPU skinning and fitted sportsuit. It does not approximate length by camera scaling or call a mesh displacement a measured segment length. Total standing height can change; there is no height-lock mode.

The v6 asset directory copies v5 payloads byte-for-byte and adds eight pinned CC0 target texts. The canonical profile and manifest are new identities; an existing Work keeps its original version and parameter list. V6 has no appearance set or timeline and is exposed through Studio and CLI as a static trial. Diagnostic poses and the windowless body+garment renderer can be used for examination, but do not establish motion or garment quality acceptance.

Acceptance requires more than compilation: compare zero to v5, fixed-camera front/side at low/zero/high for each control and combinations, bilateral symmetry, knee pose, skeleton hip/knee/ankle travel, feet and clothing at extrema. Reject nonfinite/out-of-range input atomically; preserve old documents, asset validation and packaging. Record observed spans rather than claiming exact source-independent human units. Open controls stay on HOLD if clipping, floating joints or extreme garment intersections appear.

## Later batches

- **Chest:** Separate chest cage width/depth from breast volume, projection, spacing and vertical position. The sportsuit may obscure or fail under larger soft-tissue targets; source targets, fitting and accepted visual span must be checked before public controls.
- **Upper limb:** Candidate shoulder width/shape, upper-arm length/girth, forearm length/girth, elbow girth and wrist shape. Verify each pinned target, the left/right symmetry strategy, clothing sleeves, raised-arm poses, and hand/prop reach. Elbow contour and elbow flexion stay separate.
- **Hand:** Candidate overall hand scale, palm length/width/thickness and grouped finger length/width. Existing finger bones prove a pose chain only. Held-object alignment, texture/mesh detail and hand proxy quality need their own check.
- **Measurements:** If a future UI reports cm, compute them from the final fitted geometry with a defined anatomical landmark method and error bound; do not relabel target weights. Whole-height adjustment and locked-height proportion redistribution need separate semantics.

The current v6 static shape profile is a deliberately bounded step; it does not authorize arbitrary MPFB presets or weaken the existing CI and quality HOLDs.
