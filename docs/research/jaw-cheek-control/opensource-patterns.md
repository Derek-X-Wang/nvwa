# Independent jaw and cheek controls: open-source patterns

Research date: 2026-11-03. Design research only. No application code, schema, parameters, meshes, targets, or acceptance gates were changed. No model, package, or executable was downloaded or run.

## Recommendation

Use MPFB/MakeHuman as the anatomical reference and Blender as the target-authoring reference. Treat Three.js as a rendering reference. Borrow the separation of anatomical controls, opposed target pairs, explicit dependencies, and fitting checks. A renderer change does not create missing jaw or cheek anatomy.

For a future bounded slice, retain the current meaning of `chin_width` and `head_width`. Investigate independent **jaw/lower-face width**, **cheekbone prominence/width**, and **cheek fullness**. These are candidate meanings, not three admitted assets. Expose only the controls whose actual target support and appearance pass inspection. A target name alone does not prove its anatomical footprint.

The existing fixed-view `chin_width = -1` / nose maximum trial remaining on visual HOLD is a symptom of that trial. It does not prove that every combination of the existing eight parameters is impossible. This research does not repeat or overturn that trial.

## 1. Three.js: blending supplied geometry

**Verified source facts.** `BufferGeometry.morphAttributes` holds morph attributes. `morphTargetsRelative = true` means offsets; the default `false` means absolute positions/normals. Once rendered, the morph data cannot be replaced in place under the documented contract: dispose and create a new geometry. [`BufferGeometry`, current documentation](https://threejs.org/docs/pages/BufferGeometry.html)

For base position `p`, offset target `dᵢ`, absolute target `tᵢ`, and weight `wᵢ`, the inspected WebGL implementation gives:

```text
relative: p′ = p + Σ(wᵢ dᵢ)
absolute: p′ = (1 − Σwᵢ)p + Σ(wᵢ tᵢ)
```

The renderer computes the base influence and forwards the influence array; it does not normalize that array. Several targets can therefore contribute at once. `Mesh.morphTargetInfluences` documents weights as *typically* `[0, 1]`, not as an anatomical validity guarantee. [`WebGLMorphtargets`, inspected `dev` source](https://github.com/mrdoob/three.js/blob/dev/src/renderers/webgl/WebGLMorphtargets.js), [`morphtarget_vertex` shader](https://github.com/mrdoob/three.js/blob/dev/src/renderers/shaders/ShaderChunk/morphtarget_vertex.glsl.js), [`Mesh` documentation](https://threejs.org/docs/pages/Mesh.html)

The implementation addresses target values by base-vertex index. It allocates target texture data from the base position count. Its material shader applies morph displacement before skeletal skinning. Thus target correspondence and the rig remain separate compatibility obligations. There is no useful fixed “eight morph targets” budget to infer from this inspected implementation; actual memory and device limits require measurement. [`WebGLMorphtargets`](https://github.com/mrdoob/three.js/blob/dev/src/renderers/webgl/WebGLMorphtargets.js), [`meshphysical` vertex shader](https://github.com/mrdoob/three.js/blob/dev/src/renderers/shaders/ShaderLib/meshphysical.glsl.js)

**Design inference.** Additive offsets are a suitable representation for independently authored controls and smooth slider transitions. They do not determine which vertices constitute a jaw, prevent two targets from doubling a deformation, preserve a mouth, refit a rig, or solve skin/clothing contact. This is not a recommendation to replace Nvwa's renderer or its existing deformation path. Three.js is MIT licensed. [`Three.js license`](https://github.com/mrdoob/three.js/blob/dev/LICENSE)

Version boundary: Three.js links above are current documentation and moving `dev` source read on the research date, not the version installed by Nvwa. No Three.js integration or device behavior was tested.

## 2. MPFB/MakeHuman: anatomical vocabulary and explicit coupling

The fixed **MPFB v2.0.18** catalogue distinguishes these groups:

| Region | Separate catalogue controls | Lesson |
| --- | --- | --- |
| Chin | `chin-width`, `chin-height`, `chin-prominent`, `chin-bones`, `chin-jaw-drop`, `chin-prognathism` | Chin width is one local dimension, not a synonym for the entire lower face. |
| Cheek | `cheek-bones`, `cheek-volume`, `cheek-inner`, `cheek-trans-down-up`; left/right variants | Bone prominence, fullness, inner cheek, and vertical position deserve distinct meanings. |
| Head | Horizontal/depth scale, fat, square, rectangular, triangular and other shape targets | Broad silhouette controls are separate from local face details. |

These are catalogue facts, not measured influence regions. In particular, the catalogue does **not** establish a clean symmetric `jaw-width` target. `chin-bones`, `chin-jaw-drop`, and broad head shapes are candidates to inspect, not automatic replacements for jaw width. [`v2.0.18 target catalogue`](https://github.com/makehumancommunity/mpfb2/blob/v2.0.18/src/mpfb/data/targets/target.json)

A target is a sparse list of vertex indices and XYZ displacements, represented in Blender by a shape key. Macro controls combine multiple targets; MPFB recalculates a target stack from macro components. This separates local target authoring from phenotype composition. [`v2.0.18 TargetService`](https://github.com/makehumancommunity/mpfb2/blob/v2.0.18/src/mpfb/services/targetservice.py), [official target concepts](https://static.makehumancommunity.org/mpfb/docs/assets/concept_targets.html)

For opposed controls, MPFB v2.0.18 selects the positive or negative target and uses the absolute slider magnitude as that target's nonnegative weight. It clears the opposite side's target. Symmetry can apply the same value to both anatomical sides. These are authored endpoint pairs, not a promise that one endpoint is the geometric negative of the other. [`v2.0.18 model control source`](https://github.com/makehumancommunity/mpfb2/blob/v2.0.18/src/mpfb/ui/model/_modelsubpanels.py)

MakeHuman's separate modifier implementation supports factor dependencies, propagates dependent updates, and calculates target weights as products of factors. This demonstrates explicit coupling where required. It is **not** evidence of a general collision solver or that every pair of local face targets needs a dependency. [`MakeHuman humanmodifier.py`, moving `master`](https://github.com/makehumancommunity/makehuman/blob/master/makehuman/apps/humanmodifier.py)

Fitting is another operation. MPFB's `refit` sends related mesh assets through clothes fitting and asks the rig service to refit the armature. Its target-authoring instructions require moving helper geometry and joint cubes when large edits affect clothing or rigging. Some rig configurations can reject refitting. None of this proves that a particular Nvwa asset remains fitted. [`v2.0.18 HumanService.refit`](https://github.com/makehumancommunity/mpfb2/blob/v2.0.18/src/mpfb/services/humanservice.py), [official target-authoring guide](https://static.makehumancommunity.org/mpfb/docs/assets/creating_a_target.html)

**License boundary.** MPFB v2.0.18 explicitly places program logic, including Python, shell scripts, and configuration files, under GPLv3. It identifies bundled graphical assets—including targets, modifiers, meshes, rigs, and mesh-information JSON—as CC0. MakeHuman code is AGPL. Do not treat all files in a data directory, configuration, or copied implementation as CC0. Record provenance and classification for each reused asset; third-party assets need their own license check. This note copies no implementation or configuration. [`v2.0.18 license`](https://github.com/makehumancommunity/mpfb2/blob/v2.0.18/LICENSE.md), [official project license overview](https://www.makehumancommunity.org/about/license.html)

## 3. Blender: stable topology, regional keys, demonstrated corrections

Blender's documented relative shape-key mix adds weighted offsets from reference keys. Shape keys preserve the mesh's vertex correspondence. Its manual recommends stable topology before authoring keys and describes breaking a complex facial key into regional components to reduce double effects. The panel can limit a key through a vertex group and choose its reference key. These are authoring tools, not automatic anatomy extraction. [Blender 4.4 introduction](https://docs.blender.org/manual/id/4.4/animation/shape_keys/introduction.html), [Blender 4.4 shape-key panel](https://docs.blender.org/manual/en/4.4/animation/shape_keys/shape_keys_panel.html)

Do not confuse Blender's **absolute shape-key mode**—a sequence evaluated over time—with Three.js's **absolute morph coordinates**. They describe different contracts. Blender also documents pose-driven corrective shape keys. That teaches a useful escalation path: first demonstrate a bad combination or pose; then author a correction for that known failure. It does not justify importing a general solver. [Blender 4.4 introduction](https://docs.blender.org/manual/id/4.4/animation/shape_keys/introduction.html), [official driver/corrective example](https://docs.staging.blender.org/manual/en/latest/animation/drivers/workflow_examples.html)

Retrieval limit: several full Blender manual opens returned access errors. The Blender claims above were available in the hosted search service's indexed official-page text. Corrective behavior was not executed. The optional community Corrective Shape Keys extension is GPL and described as having limited support; installing it is unnecessary for this design. [Official extension listing](https://extensions.blender.org/add-ons/corrective-shape-keys/)

## Future acceptance and stop conditions

These are borrowed design considerations, not completed acceptance or a separate execution budget. The staged, one-control budget and stop conditions in the [bounded design](README.md) are authoritative. The first proposed reference comparison is one control, one baseline and two endpoints in two fixed views, at most six images. No second control, intermediate sweep, combination matrix or extra view is automatically authorized.

1. **Admit material first.** Confirm each local asset's version, license, base-mesh identity, vertex order, coordinate conversion, actual nonzero support, and helper/joint effects. Availability of MPFB material is not established by this public research. Stop if provenance or topology cannot be proved. Do not repair by silent nearest-vertex transfer.
2. **Prove meaning independently.** In the initial reference comparison, inspect neutral and both endpoints only in the frozen front and three-quarter views. Record which jaw, chin, cheek, mouth, nose, ear, neck, and visible body regions move. A proposed jaw control must visibly change the lower-face contour beyond the chin tip. Stop or rename if the actual effect does not match the label. Any later intermediate or profile view needs a separately bounded question and budget.
3. **Treat transitions and combinations as later questions.** After one control has clear benefit, scope only the interactions actually implicated by its sparse support or observed defects. Consider smooth falloff, symmetry, neutral return and composition without automatically running every old/new parameter pair. Declare expected mouth/neck behavior before formal admission. Do not force all mouth vertices to zero if that merely creates a visible seam.
4. **Check fitting and motion separately.** Before formal release, inspect teeth, eyes, hair, neck and affected clothing interfaces using the available diagnostic poses and authored actions; do not assume the current product has a facial/head-pose catalogue. Preserve current mouth/body checks. A demonstrated defect may motivate a separately authorized small corrective target; it does not authorize sculpting or another loop from this research. Required rig/asset redesign stops the slice.
5. **Keep compatibility explicit.** New values need neutral defaults and versioned persistence, while existing parameter meanings and old saved appearances remain stable. Before formal release, prove Web Save/Open, CLI round-trip, Web→CLI→Web exchange, existing animation playback, and the repository's required automated/native/Wasm/CI gates. This research supplies none of that runtime evidence.

The design keeps at most two candidate anatomical meanings for investigation, but initially admits neither. Prove one supplied control before proposing the next; no new endpoint authoring is authorized. GPU morphing is optional; dense target storage costs approximately `vertex count × 3 × 4 bytes × target count` for Float32 positions before normals, copies, and GPU overhead. Sparse source targets can remain sparse in the authoring pipeline. Actual admission, fitting and corrective work—not slider UI—is the major unknown cost.

Reject a generic sculpting UI, learned shape solver, renderer replacement, whole character-generator port, and broad preset search for this slice. Each expands the product or evidence burden before establishing whether the available anatomical targets solve the observed contour problem.

**PARTIAL — primary official documentation and maintainer source inspected; local asset admission, target geometry, visual acceptance, fitting, runtime integration, and release gates NOT-RUN.**
