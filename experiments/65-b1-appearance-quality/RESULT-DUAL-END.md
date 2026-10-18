# Dual-end quality65 comparison

**Control isolation verified; visual quality remains HOLD.** Actual native and
Web runs each supplied 16 held four-control captures plus two Low reference/
recovery captures. This is an isolated experiment. The production appearance
policy remains `simple-srgb-mask-v1`; no material, normal, geometry or asset
identity change is admitted by this comparison. #3 remains blocked, #4 retains
its measurement gaps, and clothing/M2 quality remains HOLD.

## Scope and controls

The same approved skin, low-poly eyes and short04 bytes are used throughout.
Experiment65 disables only the production appearance controller and keeps the
Work selection at `none`. The production B1 body, authored action and frame
publication remain active. The temporary overlay is not saved. Normal
production Studio/Player and experiment66 retain the production controller.

All four regular groups hold `b1_arm_rehearsal_v1` at source2 seconds with
playback paused. They cover **two shapes and two camera views**, not a broad
motion/pose matrix:

| Group | Torso / jaw | Actual camera yaw | Actual viewport / MSAA |
| --- | --- | --- | --- |
| `sf` | −1 / 0 | 8° front | 1280×720 / Sample4 |
| `lf` | +1 / 1 | 8° front | 1280×720 / Sample4 |
| `sq` | −1 / 0 | 45° quarter | 1280×720 / Sample4 |
| `lq` | +1 / 1 | 45° quarter | 1280×720 / Sample4 |

Within each platform/group, all four complete production base snapshots and
actual camera records are identical, including held shape/sample, bones, body
and clothes arrays. The observed projection has a 30° field of view. Work
framing is presentation only; it is not an eye/hair fit offset. Actual light
buffers and GPU buffers are not independently exported by these CPU records.

| Control | Actual isolated change from Frozen64 |
| --- | --- |
| `reference` / Frozen64 | White textured material, roughness0.7, Mask(0.5); original fan-derived normals |
| A / `hair` | Hair alpha only: `AlphaToCoverage` with actual Sample4; eye normals/material unchanged |
| B / `eye` | Eye rest/posed normals only: source-polygon Newell/corner-angle smoothing; hair and all materials unchanged |
| C / `unlit` | Eye `unlit:true` only; a diagnostic, not a proposed final material |

All accessory positions/rest positions, full positive normalized weights, UV
pairs, UVs, indices, source coverage and decoded image hashes remain exact
within each group. Hair source vertices82 and195 retain five influences; eyes
retain head-only weights. Independent reconstruction of the source fan and
polygon rest-normal policies differs by at most3.33e−16 per component. This
does not establish Blender/MPFB shader or normal parity. The producer's
`actual_cpu_upload_sha256` hashes positions only; the retained normal arrays
provide the separate normal evidence.

## Actual paired images

Root observed these captures and their held states. Agent review of the paired
images retains HOLD. The screenshots support comparison, not a declaration
that hairline/crown cards, eye/eyelid boundaries, clothes or overall appearance
are accepted. An unlit eye is only a lighting diagnostic. No gaze, blink, head
motion, geometry displacement, arbitrary asset import or hair physics is added.

On both ends, review found fine hairline jaggies still present and only a small
coverage improvement. Eye polygon normals show no clear lid-fit or occlusion
repair; unlit changes light and shade only. Next compare the original eyelid/
helper geometry and occlusion, and the hair source cards/sampling, before
choosing another change. The evidence does not justify guessed fit offsets.

| Platform/group | Frozen64 | A hair coverage | B eye normals | C eye unlit |
| --- | --- | --- | --- | --- |
| Native sf | [reference](evidence/screens/native/n65-sf-reference.jpg) | [A](evidence/screens/native/n65-sf-hair.jpg) | [B](evidence/screens/native/n65-sf-eye.jpg) | [C](evidence/screens/native/n65-sf-unlit.jpg) |
| Native lf | [reference](evidence/screens/native/n65-lf-reference.jpg) | [A](evidence/screens/native/n65-lf-hair.jpg) | [B](evidence/screens/native/n65-lf-eye.jpg) | [C](evidence/screens/native/n65-lf-unlit.jpg) |
| Native sq | [reference](evidence/screens/native/n65-sq-reference.jpg) | [A](evidence/screens/native/n65-sq-hair.jpg) | [B](evidence/screens/native/n65-sq-eye.jpg) | [C](evidence/screens/native/n65-sq-unlit.jpg) |
| Native lq | [reference](evidence/screens/native/n65-lq-reference.jpg) | [A](evidence/screens/native/n65-lq-hair.jpg) | [B](evidence/screens/native/n65-lq-eye.jpg) | [C](evidence/screens/native/n65-lq-unlit.jpg) |
| Web sf | [reference](evidence/screens/web/w65-sf-reference.jpg) | [A](evidence/screens/web/w65-sf-hair.jpg) | [B](evidence/screens/web/w65-sf-eye.jpg) | [C](evidence/screens/web/w65-sf-unlit.jpg) |
| Web lf | [reference](evidence/screens/web/w65-lf-reference.jpg) | [A](evidence/screens/web/w65-lf-hair.jpg) | [B](evidence/screens/web/w65-lf-eye.jpg) | [C](evidence/screens/web/w65-lf-unlit.jpg) |
| Web sq | [reference](evidence/screens/web/w65-sq-reference.jpg) | [A](evidence/screens/web/w65-sq-hair.jpg) | [B](evidence/screens/web/w65-sq-eye.jpg) | [C](evidence/screens/web/w65-sq-unlit.jpg) |
| Web lq | [reference](evidence/screens/web/w65-lq-reference.jpg) | [A](evidence/screens/web/w65-lq-hair.jpg) | [B](evidence/screens/web/w65-lq-eye.jpg) | [C](evidence/screens/web/w65-lq-unlit.jpg) |

Native image height is784 pixels, including a64-pixel window title. Web image
height is720. Both camera records report1280×720 viewports. Images are exact
original JPEG bytes with paired receipts; no cropping, re-encoding or pixel
parity claim is made. Sizes and dimensions are inventories, not startup,
transfer or performance measurements. See the [native screen inventory](evidence/screens/native/inventory.json)
and [Web screen inventory](evidence/screens/web/inventory.json).

## Low: visible error, incomplete request correlation, recovery

The Low reference and recovered captures on each platform are correlated
Frozen64 captures at actual `Off` / one sample, neutral shape and arm source2.
Their complete base snapshots, camera, accessory numeric arrays and material
properties match; rebuilt binding handles may differ. See native
[reference](evidence/screens/native/n65-low-reference.jpg) /
[recovered](evidence/screens/native/n65-low-recovered.jpg) and Web
[reference](evidence/screens/web/w65-low-reference.jpg) /
[recovered](evidence/screens/web/w65-low-recovered.jpg).

During each intended HairCoverage trial the observed error was
`hair coverage comparison requires actual scene camera MSAA > 1`.
**Both expected-negative observations remain PARTIAL:** the error report has
no matching request identity. They are not counted as passing correlated
rejection tests. The [native screenshot](evidence/screens/native/n65-low-uncorrelated-error.jpg)
shows the actual error text. The [Web screenshot](evidence/screens/web/w65-low-uncorrelated-error.jpg)
shows a collapsed error-state label, not the rejection text itself.

The error path tears down the temporary overlay. It does **not** promise to
retain the prior skin/eyes/hair overlay; the error images show its absence.
Selecting Frozen64 rebuilds the overlay. Pre-error and recovered base snapshots
match, but this public subset has no complete error-time base snapshot. The
guard before material selection must not be described as preservation of the
whole previous overlay. Clean observations and limits are retained in the
[native Low record](evidence/native/observations/low-summary.json) and
[Web Low record](evidence/web/observations/low-summary.json). A private native
failure summary containing a local-path traceback was omitted.

The [early Web request observation](evidence/web/observations/early-request-observation.json)
also remains separate: the sender requested a sample before asynchronous Work
startup completed. It then used a fresh request ID after startup. This is a
harness timing failure, not evidence of a product defect or a successful
recovery assertion for that failed request.

## Derived public records and reproduction limits

The [native audit](evidence/native/audit.json) and [Web audit](evidence/web/audit.json)
inventory18 derived captures each. Four regular groups isolate the controls;
the fifth group is Low Frozen64 reference/recovery. No unexpected semantic
delta was found after excluding only declared handle/control metadata and the
expected eye-normal/hair-alpha/eye-unlit differences.

The36 private envelopes total410,116,780 bytes. Their public derived records
total17,292,799 bytes. Each retains its original envelope basename, exact byte
SHA256/size, request/quality/camera/sample, full accessory numeric arrays and
materials, actual bone records, skin image/UV metadata, screenshot receipt,
producer full-snapshot hash and independently computed semantic hashes.
Full body/clothes arrays and repeated body UV arrays are omitted. These are
**derived records**, not exact copies of the original envelopes or a new
independent-world oracle. The omitted arrays cannot be reconstructed or their
hashes recomputed from this public subset alone.

The [reviewed extraction template](evidence/inputs/audit_dual.py) is copied
unchanged from the independently reviewed private-work helper. Run it from the
repository root with retained raw inputs in `.work/appearance79/quality-native`
or `.work/appearance79/quality-web`; it writes ignored candidates under
`.work/appearance79/quality-audit`, not this public evidence:

```sh
python3 -B experiments/65-b1-appearance-quality/evidence/inputs/audit_dual.py --platform native
python3 -B experiments/65-b1-appearance-quality/evidence/inputs/audit_dual.py --platform web
```

The original large envelopes are intentionally not bundled. Public readers can
inspect retained accessory/material arrays, relative byte inventories and
paired images; reproducing extraction requires the retained original inputs.
Raw source SHA256 and Python canonical-JSON semantic SHA256 are labeled
separately; the latter does not pretend to reproduce Rust float formatting.

Five exact synthetic framed Works, their shared `SetStage` commands and original
receipt are in the [input inventory](evidence/inputs/inventory.json). The same
Work bytes were used on both ends. Commands target the recorded pre-framing
revision, not the already framed revision6 files. Presentation framing did not
change asset, fit or geometry. The root-owned Web site-extension receipt records
its served inputs separately. All text was screened for private paths and
common credential patterns before publication.

**VERIFIED —**36 held CPU records and36 paired image receipts, regular control
isolation, Low Frozen64 recovery equality, pinned image identity and independent
rest-normal reconstruction. **PARTIAL —**both Low error/request associations.
**NOT-RUN —**GPU buffer readback, pixel parity, performance, shader parity,
continuous head/eye behavior and full visual-quality admission.
