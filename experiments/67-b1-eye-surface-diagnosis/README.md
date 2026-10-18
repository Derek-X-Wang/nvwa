# B1 eye surface diagnosis — bounded CPU ray candidates

This experiment uses eight existing experiment65 `reference` captures. It does
not run a renderer, alter geometry, or establish GPU pixel ownership or a cause
of the observed eye appearance. Production and earlier experiments are unchanged.

## Method fixed before running

- Use `sf`, `lf`, `sq`, `lq` on native and Web, held arm source time 2 seconds.
- Verify exact raw envelope SHA256, source triangle correspondence, helper fit,
  finite arrays and captured transforms before constructing probes.
- Transform actual CPU `positions` once by the actual entity
  `display_transform`. Do **not** apply `model_to_world` again. The latter is a
  separate recorded skeleton frame, already accounted for by the display route.
- Obtain ray origin from the actual camera global matrix translation. Aim each
  normalized world ray at its selected actual eye point. Camera view coordinates
  use the inverse captured camera matrix; Bevy 0.19.1 defines forward as local
  negative Z. No guessed axis flip or guessed camera orbit is used.
- Split the fixed eye source triangle sequence by helper side, preserving order.
  For each side select local triangle ordinals **0, 28, 56, 85** (of 86), at the
  triangle centroid. Also probe the source vertices with the minimum and maximum
  selected helper ID for that side. Selection is independent of camera, pose,
  computed depth and visual judgment: 12 rays/capture, 96 total. These sparse
  probes are not an image-wide estimate or a representative anatomical sample.
- Intersect every actual indexed visible body triangle and every actual indexed
  eye triangle. Retain nearest positive hits in two-sided mode and separately
  the subset whose winding normal points toward the camera. The latter is a
  geometric culling sensitivity check, not a claim about actual rasterizer state.
- Predeclared contact band: **0.0001 m (0.1 mm)** for nearest body minus nearest
  eye ray distance. Negative outside band means `body_first`; positive outside
  band means `eye_first`; inside band means `within_contact_band`. Preserve raw
  distances, barycentrics, hit points and signed deltas. This band is a diagnostic
  classification choice, not a measured GPU depth precision or product tolerance.
- Numeric policies: reject triangle doubled area <=1e-14 m²; parallel tolerance
  `abs(det) <= 1e-12 * |edge1| * |edge2|`; barycentric tolerance 1e-9;
  positive-ray distance >1e-9 m; tie group <=1e-8 m; boundary label when the
  minimum barycentric coordinate <=1e-7. Boundary hits remain explicitly labeled.
- No texture alpha test, MSAA, normal/shadow/light shading, hair, garment, floor,
  clipping-plane rasterization or GPU readback is simulated. No GPU quality pass
  can follow from these CPU intersections. Source body labels do not identify an
  anatomical eyelid or prove that an overlapping surface is erroneous.

## Reproduce

From the repository root, with the original eight private captures available in
the capture repository's `.work/appearance79/quality-{native,web}/captures/`:

```sh
python3 -B -m unittest discover -s experiments/67-b1-eye-surface-diagnosis -p 'test_*.py'
python3 -O -B -m unittest discover -s experiments/67-b1-eye-surface-diagnosis -p 'test_*.py'
python3 -B experiments/67-b1-eye-surface-diagnosis/probe.py --capture-root CAPTURE_REPOSITORY --output experiments/67-b1-eye-surface-diagnosis/evidence
```

`CAPTURE_REPOSITORY` is a local argument, never embedded in generated evidence.
The default source repository is this script's repository. No large envelope is
copied. Public results retain only hashes and small derived probes. The full raw
data is required to reproduce intersection results; the small public output
cannot reconstruct omitted body arrays by itself. See `RESULTS.md` for actual
outcomes and `evidence/manifest.json` for exact input/source/tool identities.
