# Result: reproducible CPU depth candidates; visual cause UNKNOWN

This bounded experiment establishes a small source-face candidate set for a
later surface-ownership diagnostic. It does **not** establish incorrect body
occlusion, an eye fit defect, anatomical eyelid identity, GPU pixel ownership,
or a product fix. No source coordinates, Work, materials, Cargo files, earlier
experiment or production files changed. Base: `ab4c16f81deddfc98faa97fcd1a8e7904c5f2f0b`;
working branch: `codex/b1-eye-depth`. Nothing was committed or pushed.

## What actually ran

Eight exact existing experiment65 reference envelopes were read: native/Web
`sf`, `lf`, `sq`, `lq`, each paused at arm source time2 seconds. Short is
torso−1/jaw0; long is torso+1/jaw1. Front/quarter use their actual captured
8°/45° camera matrices. No new pose, head/eye movement, camera or render was run.
The native inputs here are the `*-reference-envelope.json` files, not the
separately hashed `*-reference-frame.json` files from the independent space note.

The selection and numeric policies in [README.md](README.md) were written before
the first ray run. Every record checks the exact raw envelope hash, current
source quad→triangle sequence, source/UV mapping, full cage correspondence,
held sample, shape and captured body/eye placement. Source face and triangle
ordinals are zero-based; OBJ line numbers are one-based.

The 96 rays each test22,892 actual indexed body triangles and172 actual indexed
eye triangles. Body helpers remain in the capture array but are not admitted
into the visible triangle set. The tool rejects nonfinite inputs, degenerate
triangles, source correspondence errors and changed raw input hashes. It uses
explicit exceptions, including with Python optimization enabled.

Actual execution receipts are in [validation.json](validation.json): 16 tests
passed under ordinary Python and16 under `-O`. The complete eight-capture tool
also passed under both modes, and all10 evidence files matched byte for byte.
Each tool run took about6 seconds locally. These are CPU tool durations, not
rendering performance measurements. No compile, app, GPU, Blender, download or
new dependency was used.

## Space trace and checks

`crates/nvwa-runtime/src/b1.rs:760` uploads the already CPU-skinned positions;
`:795` constructs the final display placement from source root/facing/grounding.
`:3358–3442` observes actual `Assets<Mesh>` arrays and the entity global matrix,
and checks them against the published frame. Thus captured positions need the
captured global `display_transform` exactly once.

Experiment65 `preview/src/accessory.rs:563` copies that body placement;
`:618–649` uploads posed eye arrays in `(source vertex, UV)` render order and
sets the global placement. `:741–750` observes and checks the actual eye global
matrix. Its `model_to_world_record_only` is context, not another transform.
The tool joins eye render vertices through `source_uv_pairs`; render vertex0
maps to eye source8, so it never substitutes `rest_model_m[0]` for render0.

The actual body and eye display matrices in all eight records are
`T(0, 0.8167600035667419, 0)`. The separate `model_to_world` record is
`diag(-1,1,-1,1)` and is **not reapplied**. Full96-vertex eye→body-helper rest
correspondence is exact; the maximum posed component difference is
`5.960464477539063e-8 m`. Recomputing complete eye stage bounds with a single
display placement matches the producer bounds to that same maximum error.

Experiment65 `preview/src/lib.rs:1015–1031` captures actual camera global matrices
as column-major `world_from_view`. The tool obtains the world ray origin from
their translations, aims directly at the actual selected eye point, and uses a
general affine inverse for view coordinates. Bevy0.19.1 cached source
`bevy_transform/src/components/transform.rs:322–325` defines forward as
`-local_z()`. Its camera `projection.rs:335–341` uses right-handed perspective.
The tool does not invent another axis conversion or project to GPU pixels.
The projection remains an observed debug string, not an exported numeric GPU
projection matrix. Source and raw-byte inventories are in
[evidence/manifest.json](evidence/manifest.json).

## Actual sparse ordering results

Every capture has **6 body-first rays and6 eye-first rays** in both comparison
modes. None is missing an intersection or inside the predeclared0.1mm contact
band. The nearest hits and distances are unchanged when restricting to triangles
whose winding normal points toward the camera in these selected rays. That
sensitivity check does not reproduce the actual GPU culling/alpha/depth pipeline.

| Native and Web case | Body minus eye nearest distance range (mm) | Selected target behind nearer eye surface | Selected-nearest triangle-center probes / body-first among them |
| --- | ---: | ---: | ---: |
| short-front | −16.182614 to+31.058581 |4/12 |6/8;2 body-first |
| long-front | −16.168998 to+31.063090 |4/12 |6/8;2 body-first |
| short-quarter | −39.622276 to+24.375031 |4/12 |5/8;1 body-first |
| long-quarter | −39.542622 to+24.392697 |4/12 |5/8;1 body-first |

These are sparse geometric ray distances, not fractions of visible eye pixels.
A negative value means the selected ray meets some body triangle before the
nearest eye triangle. A positive value means the nearest body hit lies behind
the nearest eye hit; that body hit need not be the same skin patch as a negative
candidate. Neither sign proves a surface intersection or incorrect anatomy.

Four targets per capture are self-hidden by a different nearer eye triangle.
The source-vertex probes can also hit exact eye edges and retain their boundary
labels/ties. They must not be treated as directly visible eye pixels. Even the
remaining selected-nearest centroid probes are only geometric candidates:
texture alpha, rasterization and other scene surfaces have not been tested.

Corresponding native/Web **probe records** match exactly for all four cases.
Their entire body-world-position hashes differ; no equality of the complete
body arrays or rendered pixels is claimed. Their complete eye-world arrays
have equal semantic hashes in the corresponding cases.

## Small candidate set for the next diagnostic

[body-first-candidates.json](evidence/body-first-candidates.json) indexes all48
body-first observations: **13 unique source triangles in12 source quads**.
Each keeps the original OBJ line, source corner IDs, capture/probe identity,
raw signed depth and self-visibility/boundary status. The per-capture files
retain actual camera/global matrices, all positive hit distances, nearest-hit
ties/barycentrics/world points and exact raw-envelope hash/size. They omit the
large full mesh arrays, textures and raw envelopes.

For a minimal later rendering comparison, begin with these existing centroid
candidates whose selected target is also the nearest eye hit:

| Existing case/probe | Eye source helper corners | Nearest body source quad / triangle | Body source corner IDs | Body minus eye (mm) |
| --- | --- | --- | --- | ---: |
| short-front, source-left triangle0 |14655,14664,14665 |6671/0 |11745,11507,6832 |−10.910186 |
| short-front, source-right triangle0 |14727,14728,14737 |90/1 |5084,80,142 |−13.880747 |
| short-quarter, source-right triangle0 |14727,14728,14737 |11458/1 |6903,11705,6907 |−37.098863 |

These body triangles have interior barycentric hits for these rays. The table
selects a bounded handoff subset **after** reporting every original fixed probe;
it does not replace the selection or hide the eye-first/self-hidden results.
Left/right are source helper names, not an inferred screen-side or anatomical
skin label. The input OBJ has no semantic visible-eyelid face annotation that
would justify calling any of these triangles an erroneous eyelid/socket cap.

## Failures and limits

No real-input tool failure occurred. Analytic controls exercise hand-calculated
interior/boundary/tied hits, reversed winding, parallel/coplanar/behind-camera
rays, missing hits, explicit contact classification, invalid matrices, invalid
indices/nonfinite vectors, and degenerate triangles. Selection counterexamples
exercise a different chosen ordinal, reordered source triangles, missing source
coverage and mixed helper sides. Their changed identities/rejections are tests
of the tool, not product failure evidence.

The expected source asset hashes are checked by the tests; all eight raw hashes
are checked before geometry is used. This tool does not validate the original
capture producer, reconstruct omitted GPU state, or make the private full arrays
public. Reproduction requires the original raw inputs. Mesh subset coordinates
and source IDs derive from the existing admitted assets; their source/license
notices remain in `assets/characters/mpfb-b1-v1/licenses/` and
`assets/appearances/mpfb-b1-cc0-v1/`.

Eye `Some(Back)` and `Mask(0.5)` are directly captured CPU material fields. Body
culling is source-supported (`b1.rs:783`, plus65 property-preservation checks),
but its exact culling field is not directly exported in these raw frames. The
two-sided mode and normal-facing subset make geometry assumptions explicit.
Neither performs alpha texture sampling, MSAA/sample coverage, clipping,
depth compare/write/bias, shadows, render ordering, garment/hair/floor occlusion,
or numerical GPU projection/readback. No cause, offset, geometry deletion,
normal policy, material promotion or production change is selected.

The next root-scheduled rendering diagnostic can compare body-only, eye-only
and combined surface ownership at one of the exact held cases above, using the
same geometry and camera. If actual GPU depth/object-ID observation is unavailable,
that limit must remain explicit. This offline experiment does not block main CI.

VERIFIED —8 pinned existing captures,96 fixed CPU rays, source correspondence,
space/bounds checks,16 tests in each mode, and ordinary/`-O` exact evidence parity.
NOT-RUN — new rendering, GPU pixel/depth ownership, anatomical classification,
performance, cause confirmation or any fix. Production quality remains unadmitted.
