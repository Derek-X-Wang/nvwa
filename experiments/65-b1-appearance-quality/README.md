# #79 bounded appearance-quality controls

The completed root-run native/Web A/B is in [RESULT-DUAL-END.md](RESULT-DUAL-END.md). Both platforms retain16 material/normal comparisons plus Low baseline/recovery. Candidates stay experimental; the body/role persistence feature uses the unchanged production material policy. The original planning and worker-only verification notes below describe the earlier source-preparation stage and do not supersede that result record.

This is a source-grounded throwaway module for a root-owned native/Web A/B.
The approved skin, low-poly eyes and short04 assets are the only inputs.
Nothing in frozen experiments 62–64 or production is changed. No geometry
offset, source weight clamp, influence truncation, asset replacement or UV
change is proposed. `quality.rs` is consumed by the standalone `preview` crate.

## Current preview isolation (r2)

The experiment uses the shared production `nvwa_studio::build_app`, then explicitly
configures `RuntimeSystems::Appearance.run_if(|| false)` in `PostUpdate`, before
`app.run`. Only the production appearance controller is disabled. The base B1
runtime, authored playback and actual frame publication remain enabled. Normal
Studio/Player and experiment66 do not call this experimental isolation function.

This boundary is necessary because the production None controller verifies its
plain body material each frame; an independent temporary skin overlay conflicts
with that valid production guard. Experiment65 does not weaken the production
guard. It disables that controller solely for this isolated quality comparison.

The Work guard still forces `appearance: {"type":"none"}`. Capture requires that
selection, a ready/error-free current base B1 binding and actual before/after
`b1_frame_snapshot` equality. Metadata explicitly includes
`production_appearance_controller_disabled: true`, current `work_appearance`,
base binding identity and actual scene-camera/MSAA. It makes no production
appearance `ready`/`applied` claim: that controller does not run. The sink rejects
such inapplicable status claims, a missing/false disabled flag, non-None Work,
or a base binding that is not ready/current. Existing material/image/weight/UV
authentication is unchanged. A Rust control exercises the actual isolation
configuration seam with counters in both system sets: Appearance must stay at
zero while base Mirror advances on two schedules. Rust execution remains
root-owned and NOT-RUN by this worker.

## Diagnosis and evidence

- Original frozen64 Web `08-web-final-face-recovered.png` and retained native
  `16-native-final-face.png` show a comb-like binary hairline, angular crown
  edges and flat-looking eye shading. These are historical pixels, not a new
  rendering of these candidates. Native pixels were inspected in their original
  local file; they are not copied here because they contain local paths.
- short04's authenticated MHMAT says `transparent True`, `alphaToCoverage True`,
  `backfaceCull False`. Frozen64 uses two-sided `AlphaMode::Mask(0.5)` and
  roughness 0.7. The authenticated decoded hair image has **562,370 partial-alpha
  texels (13.4079%)**. Binary rejection removes partial coverage. This grounds
  candidate A; it does not prove that all visible comb-like edges are aliasing.
  The hair texture itself contains individual strands, and the crown silhouette
  also depends on the existing low-poly cards.
- Eyes have **44 partial-alpha texels (0.004196%)**. Changing their alpha policy
  is a weak explanation for their broad shading. Their original material uses
  an unavailable legacy litsphere shader and has `shaderConfig spec False`.
  Simple Bevy PBR with roughness 0.7 is not that shader. There is no source-based
  justification here for a guessed glossy roughness or new cornea.
- Both accessory OBJ files contain quads only: **86 eye faces / 525 hair faces**.
  They supply no `vn` normals. Frozen64 fans each quad into two triangles and
  area-weights those triangle normals at source vertices. Merely cyclically
  rotating each source quad's first corner, without changing its surface,
  changes these normals by up to **16.24° eyes / 36.69° hair**. Candidate B uses
  each source polygon's Newell normal and its corner angles; this removes that
  fan-root bias (<0.000001° in this control). This is a smoothing hypothesis,
  not an MPFB/Blender normal-parity claim. Hair's larger difference warrants a
  separate later trial; the supplied B selection changes **eyes only**.
- Two actual frozen64 Web CPU records were checked at opposite torso/jaw
  settings and source times. Fitting matches the signed source reference within
  3.34e-16 m; posed eye/hair arrays match within 2.99e-8 m. Final-positive source
  joint sets match, including hair source IDs **82 and 195 with five influences**.
  Both eye records use only the `head` joint. This rules out a reproduced fit
  arithmetic/weight-truncation error in these records. It does **not** establish
  correct eyelid occlusion or a visually accepted fit. No lid/eye displacement
  is justified by the available evidence.

The exact numeric results and capture hashes are in `diagnosis.json`. The
stdlib analysis authenticates all 12 pinned output files against their existing
manifest and reads original captures without modifying them.

## Root integration interface

Use `quality.rs` from a new preview crate via a path module. Keep frozen64's
fitting, transferred full-positive weights, skinning, UV pairs and indices.

1. Select one `Control` for the whole capture: `Frozen64`, `HairCoverage`,
   `EyePolygonNormals`, or `EyesUnlitDiagnostic`. Do not combine controls during
   diagnosis. On control changes invalidate/dispose the preview accessories so
   the fitted normal/material cache cannot retain the previous control. Put the
   control in the new preview's cache identity and actual capture metadata.
2. Compute the existing `source_normals(&rest, &obj)` baseline. Pass it to
   `quality::select_normals(p.hair, &rest, &baseline, control)`. Feed its result
   to the unchanged normal skinning and UV-corner expansion. This changes eyes
   only for `EyePolygonNormals`; every other case returns baseline normals.
3. Build the existing white-tinted, textured, roughness-0.7, zero-metallic
   material. Call `quality::apply_material(&mut material, p.hair, control,
   actual_scene_camera_msaa)`. It resets alpha/unlit to frozen64 before each
   successful selection. Candidate A changes **hair alpha only**. Diagnostic C
   changes **eye unlit only**. It does not change the texture, culling, shadow
   components, body material, eye positions or UVs.
4. Replace the copied preview's fixed `observe_material` expectations with the
   selected control's exact observed expectations, including `unlit`. Do not
   weaken texture/handle/pixel authentication. Export actual camera MSAA and
   selected control with observations. Frozen64's checker expects Mask(0.5) and
   baseline normals; it cannot certify these new material/normal policies.

Bevy **0.19.1 cached source**, not a guessed API, confirms ATC behavior:
`bevy_pbr/src/material.rs:612` maps ATC to its multisample pipeline only when
MSAA is enabled; `render/mesh.rs:3421` enables alpha coverage;
`render/pbr_fragment.wgsl:220` sharpens alpha at the 0.5 cutoff;
`pbr_material.rs:1159` supplies that cutoff. With MSAA off, ATC falls back to
binary discard. Current `nvwa-runtime/src/stage.rs:258` uses Off for Low and
Sample4 for Balanced/High. The prototype rejects hair ATC with Off **before
mutating its material**. Keep that explicit instead of claiming an ATC result
from an Off camera.

## Minimal actual A/B recipe (root owns execution)

Build native and Web once with the four controls available. Root schedules all
Cargo/GPU work. This worker has not launched either renderer.

| Control | Purpose | Required unchanged data |
| --- | --- | --- |
| Frozen64 | Current visible baseline | All current arrays/material fields |
| HairCoverage | Test partial hairline coverage at actual Sample4 | All positions, weights, indices, UVs, normals, image bytes, eye material |
| EyePolygonNormals | Test diagonal-biased eye lighting | All positions, weights, indices, UVs, image bytes, materials, hair normals |
| EyesUnlitDiagnostic | Separate eye texture/occlusion from direct PBR lighting | All geometry/normal arrays, UVs, texture bytes and alpha/cull policy |

For each platform use the same held source clip/time and shape, actual stage
light/settings, viewport pixel size/DPI, and camera transform across controls.
Capture front and 45° views at a face-inspection distance that keeps the full
hairline, both lids and crown visible. Camera is an observation control, never
an eye-fit adjustment. Compare torso -1/jaw 0 and torso +1/jaw 1 using the two
retained source cases, then a neutral shape if either difference is material.
Do not infer a visual improvement from CPU equality alone.

For A inspect fine hairline coverage, crown silhouette, distant thinning,
back-card visibility and shadows. Check that Low rejects the ATC trial or is
explicitly labeled baseline fallback. For B inspect sclera/iris lighting and
upper/lower lid boundaries from both views. C is a diagnostic only: if a dark
gap/silhouette persists with the same pixels and unlit eye, lighting alone does
not explain it. Do not promote C as final appearance. If a geometric gap
persists, retain the failed images and investigate the original lid/helper
surface before proposing any offset. Keep both candidate failures and passes.

## Cheap checks and limits

```sh
python3 -B -m unittest discover -s experiments/65-b1-appearance-quality -p 'test_*.py' -v
rustfmt --edition 2024 --check experiments/65-b1-appearance-quality/quality.rs
python3 -B experiments/65-b1-appearance-quality/analyze.py \
  --capture /ABS/ORIGINAL/w64-t0-j0-arm-s0.json \
  --capture /ABS/ORIGINAL/w64-t2-j2-knee-s4.json \
  --out /ABS/NEW/diagnosis.json
```

**VERIFIED —** six Python numerical controls pass; rustfmt parses/checks the
Rust module; two original CPU records reconstruct existing source normals and
signed/all-positive geometry. Controls cover outward/winding normals,
fan-root mutation sensitivity, polygon rotation/translation invariance,
unit/finiteness, unchanged source arrays and degenerate rejection.

**NOT-RUN —** Rust typecheck/tests (three Rust controls supplied for root),
native/Web A/B, new screenshots, visual improvement, GPU readback and all gaze,
blink, head-motion, hair-physics/collision or performance claims. No compiler,
app/server, browser, Blender, downloaded asset, helper agent or machine resource
was created. Only retained source/results and `.work/appearance79-quality`
analysis/log files were created; no artificial fixture files remain.
