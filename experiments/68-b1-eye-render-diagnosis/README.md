# Actual production eye diagnostic68

Prepared for one bounded root-controlled render comparison. **No build, launch,
screenshot or GPU observation has been run by the implementation worker.** The
cause of the eye/eyelid appearance remains **UNKNOWN**. Experiment67 remains a
frozen CPU candidate set. No anatomical eyelid classification is introduced.

## Actual route and controls

This standalone wrapper calls `nvwa_studio::build_app()`, exactly as66 does. It
keeps the production saved appearance controller enabled. The production
`appearance_snapshot` verifies its current body/eye/hair bindings and their
full-positive skinning before a diagnostic capture. There is no65 accessory
renderer, substitute scene, copied fit, geometry displacement, repeated skin,
normal change, guessed offset, deletion or production change in68.

| `mode` | Actual character visibility |
| --- | --- |
| `combined` | Original production visibility for every character role. With `textured`, this is the unchanged formal production baseline. |
| `body_only` | Body keeps original visibility; all other character parts/accessories, including eyes, hair and clothes, are Hidden. |
| `eye_only` | Eyes keep original visibility; body, hair, clothes and all other character roles are Hidden. |

Floor, lights, background and non-character entities stay unchanged in all
controls. Isolation removes those character roles from their rendering/shadow
participation; therefore only the unchanged combined control represents the
full original scene. Every target records its original/actual Visibility,
InheritedVisibility and ViewVisibility. ViewVisibility is CPU camera culling,
not a GPU fragment ownership record.

| `palette` | Body and eye material changes |
| --- | --- |
| `textured` | None. |
| `unlit_textured` | `unlit=true` only. |
| `role_tint` | `unlit=true`; body base_color cyan, eyes magenta. |

All palettes retain the actual original texture/image, including texture alpha,
Mask threshold, UV sampling, culling, double-sided flag and every other
StandardMaterial field. No opaque replacement is offered. Hair/clothes
materials stay unchanged even when their visibility is Hidden. Full material
Debug records are exported before/after the override. Diagnostic colors are
visual aids and do not claim GPU attachment/object-ID readback.

Materials restore at PreUpdate, before the production appearance controller
runs and verifies them. Requested visibility is set there and goes through the
normal PostUpdate visibility propagation. Captures wait for the current target
binding epoch to reach that pass. The Last observer validates production
snapshots with restored materials, reads actual mesh buffers, and then applies
the selected material override for rendering. It checks actual handles and
visibility again. Ready capture data separates this production validation from
the render override. Only full capture requests allocate/serialize full mesh
arrays; held frames reuse that export. Errors invalidate the frame and restore
the diagnostic overrides. A later fresh request can recover.

## Fixed inputs and identities

`works/short-front.nvwa.json` derives from65's exact public short-front Work,
SHA256 `2b718c87c2381369b3bed67b38af6d6a7c3d6829e19320ccc6ac940bd9165ec4`.
Only saved appearance changes from None to the canonical production
skin+eyes+hair selection, and revision advances from6 to7. Shape, topology,
original timeline, stage, lights and camera are unchanged. Held playback is
requested separately at arm source2 seconds, paused; no new timeline is made.
The fixed Work comparison rejects any other document content during a
`capture` or `diagnostic` request.

The shipped manifest identity stays `mpfb-b1-cc0-appearance-v1`, SHA256
`c3cf2b1040eed083fb1a328f0494b0c978cec42c71f3b7c826e14992f97cef04`,
policy `simple-srgb-mask-v1`. Production authenticates its payloads. The input
map records the shipped eye OBJ hash, source/UV corner order and indices, and
checks those against the actual production eye upload. Render0 maps to eye
source8. These source records are comparison metadata, never replacement
geometry.

`works/reference-short-front.json` retains the existing65 native/sf camera
observation through frozen67, its source hash and original envelope identity.
Captures require its actual global matrix within1e-6 per component, actual
1280×720 viewport, Sample4 and an exact match of the retained actual projection
Debug record, including on the first capture. Experiment65 did not export
sub-camera state: its value remains UNKNOWN. Actual68 sub-camera state is
mandatory/exported and compared unchanged within each endpoint matrix; no numerical GPU projection/depth
claim follows. Actual globals are exported for every character mesh. Positions
are already posed metres: world = display_transform × positions exactly once.
Do not reapply model_to_world, axis flips, unit scale or skinning.

`FROZEN-INPUTS.json` authenticates unchanged65/66/67 files at preparation time.
The independent transform/source-semantics/review notes supplied to this worker
were read as private context; no private absolute paths are copied here.

## Root-scheduled offline build/export

No build may run until the root grants its heavy slot. Use an isolated job
checkout with its own target directory, not the real checkout's project target.
The script requires an existing Python3.11+ (for tomllib), uses that selected
interpreter for child source tests, and uses the existing locked dependencies, offline, jobs1. The root
wraps the run with `wefty exec` for the over-five-minute check and applies the
90-minute bounded run limit. The script itself starts no app, GUI or server.

```sh
/absolute/existing/python3.11-or-newer -B experiments/68-b1-eye-render-diagnosis/build.py \
  --out /absolute/owned/export68 \
  --target-dir /absolute/isolated-job/target \
  --bindgen /absolute/existing/wasm-bindgen
```

It runs source tests, rustfmt check, native unit tests, native bin compilation,
Wasm library compilation and wasm-bindgen export, sequentially. Outputs:
`native/studio68`, `web/index.html`, `web/pkg/`, `web/assets/`, `web/works/`,
per-check logs, `checks.json` (exit and elapsed time), source closure hashes,
and `export-receipt.json` only if all steps pass and the source closure stayed
unchanged. A failed log/check remains failed. Compilation/export is separate
from launch, rendered observation, performance and cause confirmation.

## Native runtime protocol

The root owns the single GPU launch. CPU ready does not certify that a new
Last material override is already on the GPU in that same frame; allow normal
render updates before taking each separately identified GUI screenshot. Create a native command file before
launch. Its first request may explicitly fail if startup is not ready; retain
that failure and use a fresh request ID after startup. `--benchmark` fixes the
physical viewport at1280×720; `--player` uses the same production Player UI.
Native asset resolution is production's normal resolver; for an isolated
export set `NVWA_ASSET_ROOT` to its exported Web assets.

```sh
NVWA_ASSET_ROOT=/absolute/owned/export68/web/assets \
B1_68_COMMAND_FILE=/absolute/owned/command.json \
B1_68_REPORT_FILE=/absolute/owned/report.json \
B1_68_FRAME_FILE=/absolute/owned/frame.json \
/absolute/owned/export68/native/studio68 --benchmark --player \
  --work /absolute/owned/export68/web/works/short-front.nvwa.json
```

Replace the command file atomically, with a fresh ID per request. Wait for a
terminal response for that same ID before sending another. First hold source2:

```json
{"request_id":"n68-hold","action":"playback","seek_seconds":2,"playing":false}
{"request_id":"n68-combined","action":"diagnostic","mode":"combined","palette":"textured"}
{"request_id":"n68-body","action":"diagnostic","mode":"body_only","palette":"textured"}
{"request_id":"n68-eye","action":"diagnostic","mode":"eye_only","palette":"textured"}
{"request_id":"n68-unlit","action":"diagnostic","mode":"combined","palette":"unlit_textured"}
{"request_id":"n68-tint","action":"diagnostic","mode":"combined","palette":"role_tint"}
```

For each control retain report.json, frame.json and an unmodified GUI screenshot
with the same request ID. Successful capture requires `phase=ready`,
`acknowledged=true`, `request_succeeded=true`, `current=true`, and matching
request_id in both files. Report/frame writes are individually atomic, not a
two-file transaction; never use a frame file until both IDs agree. Envelope
shape for the verifier is `{"report":<report object>,"frame":<frame object>}`.

Ready report preserves Work/appearance/base identity and status. Full frame
exports actual body/clothes/eye/hair arrays through bound Mesh3d handles,
normals/UV/indices/globals, source mapping, actual camera/environment, original
production material records and explicit override/visibility state. It is CPU
readback only. Error/stale states clear the frame channel. Work, generation,
body, transport, camera, environment, preview, pending Open or runtime errors
invalidate current evidence. Invalid commands retain request identity when a
valid JSON request ID is available. Native channel read failures have unknown
request identity and report null explicitly.

Web ingress publishes pending/current=false before delivery and retains its
previous frame channel until the controller updates it. Thus identical replay
retains its usable correlated frame and ready acknowledgement; a new pending
request cannot use that old frame as current evidence. Invalid requests clear
the frame when their error acknowledgement is delivered. A Rust regression
uses the actual shared Web ingress/export seam and dispatch replay branch.

The66 bridge's typed `open`, `command`, `playback` and `capture` requests remain
available. `diagnostic` requires exactly ID/action/mode/palette. Unknown,
duplicate, null or action-irrelevant fields reject. IDs are bounded to64 ASCII
letters/digits/underscore/hyphen; a session admits at most128 distinct IDs.

## Web protocol and comparison

The root serves only its exported site on the assigned free Nvwa port and opens
`?work=works/short-front.nvwa.json&benchmark=1&player=1`. The HTML exports
`window.b1_68`; functions are `b1_68_command(JSON text)`, `b1_68_report()`,
`b1_68_frame()` and `b1_68_work()`. Same typed parser/controller, modes,
palettes, identity and CPU arrays as native. The collapsible HTML panel offers
the same requests and a correlated JSON-envelope download. Collapse it before
screenshots. Its visible report is not a screenshot or GPU measurement.

For each platform separately, verify the held controls before interpreting
screenshots:

```sh
python3 -B experiments/68-b1-eye-render-diagnosis/check_captures.py \
  /absolute/owned/combined-textured.json /absolute/owned/body-textured.json \
  /absolute/owned/eye-textured.json /absolute/owned/combined-unlit.json \
  /absolute/owned/body-unlit.json /absolute/owned/eye-unlit.json \
  /absolute/owned/combined-tint.json /absolute/owned/body-tint.json \
  /absolute/owned/eye-tint.json
```

The verifier requires exactly the complete3×3 mode/palette matrix per endpoint,
including combined/textured. Submit all nine correlated envelopes to the command
above. Native and Web
sets must be checked separately. It rejects missing/duplicate controls or IDs,
unacknowledged or stale records, wrong actual role isolation/palette,
changed geometry/normals/UV/indices,
Work/sample/bones/camera/environment/original materials, unprepared visibility,
or undeclared coverage/culling changes. It does not compare native/Web pixels,
prove draw-order winners or admit quality. Native/Web actual launch and captured
records must each be observed; a successful compile does not establish either.

## Bounded interpretation and stop rule

1. The production combined/textured screenshot establishes the current effect
   under these exact inputs. If the held geometry/camera/material checks fail,
   stop: there is no controlled comparison.
2. Body-only and eye-only screenshots show the actual role surfaces in
   isolation. A feature that remains with only one role supports attribution to
   that rendered role. Removing other surfaces also changes their shadows;
   this alone does not establish erroneous occlusion or an anatomical eyelid.
3. Combined unlit/textured retains geometry/alpha/culling while removing light
   response on body/eyes. A change limited to shading supports a lighting/normal
   explanation. A persistent boundary is not repaired by that control, but does
   not distinguish wrong fit from authored source shape on its own.
4. Combined role tint helps root locate body versus eyes visually without
   dropping texture alpha. It remains a separate diagnostic material; a colored
   screenshot is not a per-pixel GPU object-ID or depth attachment.
5. If visible low-poly silhouette/faceting persists eye-only/unlit, the retained
   source topology is a candidate limitation. No approved alternate source or
   source-authoritative eyelid mesh is available here. Do not guess an offset,
   hide/delete candidate body triangles, or promote a material change from this
   observation alone.

After this one fixed case, report which roles/features actually changed and
which cause remains UNKNOWN. Stop before extra shapes, camera sweeps, geometry
edits or asset replacement unless root explicitly expands the bounded scope.
The default product/asset recommendation remains **no production fix and no
asset replacement yet**. Clothes/M2 quality HOLD and issue79's quality gate
remain open. GPU depth/object-ID readback, anatomical classification, shader
parity, head/eye animation and performance are **NOT-RUN**.

## Separate issue80 shoulder witness (root-authorized extension)

This does not enlarge the eye matrix. `works/long-front-shoulder.nvwa.json`
derives from65 `long-front.nvwa.json`, SHA256
`245c580eb47eae06054a44b71714c27f71ba035090b5925cd54cf3c14a97eab3`
(the machine source test authenticates the actual retained file). The original
65 long Work has torso+1/jaw1; this witness explicitly changes jaw to0, enables
the same canonical saved appearance and advances revision6→7. Original stage,
front camera, lights and timeline are retained. The eye case remains exactly
short-front/source2. R3 selects `works/reference-long-front.json` for the
shoulder flag, authenticated directly from frozen65 native `n65-lf-reference`.
Its actual cameraY is1.6997191905975342; the short referenceY is
1.549719214439392. The source long reference has jaw1 while this witness Work
has jaw0; its saved long-front stage/camera stays unchanged. The same1e-6
global, exact projection, Sample4 and1280×720 gates apply. Reference65
subcamera remains UNKNOWN; actual68 subcamera is still exported/compared.

Open this separate shoulder Work through the existing production `open`
request, or launch it using the same native flags/Web query. Then send only:

```json
{"request_id":"shoulder-neutral","action":"witness","seek_seconds":0}
{"request_id":"shoulder-peak","action":"witness","seek_seconds":2}
```

The `witness` action requires exactly ID/action/seek_seconds, restricts the time
to0 or2, forces paused playback and combined/textured, and rejects any other
Work/shape. It exports the whole untrimmed production `b1_frame_snapshot` as
`frame.full_base`, retaining all body and garment arrays, source IDs, indices,
rest positions/normals, full joint influences, tangents, bones, placement,
contact and sample data. This `full_base` field is also retained for the eye
captures. The explicit actual mesh buffers additionally retain UV arrays and
the production accessory buffers. No ray/penetration/garment-quality inference
is performed by68.

Retain two correlated envelopes and screenshots per platform. Validate the
witness with `check_captures.py --witness neutral.json peak.json`. This mode requires exactly the distinct source0/source2 pair per endpoint,
acknowledged/current records, body and garment identities,53 actual bones and
nonempty/count-consistent complete arrays. It checks the fixed
Work/camera/environment/rest/topology and original materials;
posed positions/normals may differ as requested by the authored motion. It
makes no clothing-quality or GPU-readback claim. Native and Web observations
remain separate. The root/70 worker owns any later garment diagnosis.


## Rework and retained failure

The first frozen68 review found Web identical replay/export loss and acceptance
of arbitrary incomplete control/witness subsets. Both are corrected with
production-called Rust seam regression source and Python acceptance/rejection
regressions. The original preparation/freeze records are retained as historical
`PREPARATION-r1.json` and `FROZEN-SOURCE-r1.json`. `BUILD-ATTEMPTS.json` records
the root-reported failed first build before Rust compilation: its node Python
lacked tomllib. That run remains failed and its original output is untouched.
The new root run must use an existing Python3.11+ and a fresh output/target.
Current worker checks and remaining NOT-RUN limits are in `PREPARATION.json`.


## R3 camera-selector correction

Root actual R2 native observation retained13 passing Rust tests and all9 passing
eye controls, but shoulder0 correctly failed the camera gate: the diagnostic
selected the short reference for every Work. This was a probe selector error,
not a product defect or failed numeric tolerance. The failed shoulder capture
remains failed and root-owned; no Work/camera/gate was loosened. R3 adds a
separately authenticated existing65 native long-front camera and chooses it
only for the shoulder flag. A production-called selector/gate Rust regression
accepts that actual long camera, rejects it against short, and still rejects a
projection change. R2 preparation/source-freeze records are retained unchanged
as `PREPARATION-r2.json` and `FROZEN-SOURCE-r2.json`. Compilation and new actual
shoulder observation require the root combined build and remain NOT-RUN here.

## R4 raw influence acceptance correction

`full_joint_influences` retains raw positive per-bone aggregates. It does not
contain already normalized evaluation weights. In `nvwa-b1-adapter`,
`skin_mesh_frame_full_weights` checks the finite positive sum, divides each
weight by that sum for LBS, then stores the original rows in the frame.
`PreparedSkin::new` keeps a separate normalized cache; `evaluate` clones the
original frame and updates posed buffers. The acceptance gate therefore checks
complete nonempty rows, unique valid bone IDs, finite positive weights and a
finite positive sum. It never normalizes or edits exported arrays.

The prior sum-within1e-5-of-one assertion rejected actual CPU rows: body render
vertex4459 sums to0.999899979273323; garment vertex422 sums to1.0021747723221779.
`raw-influence-golden.json` retains those exact rows and source capture SHA;
regressions insert them unchanged into the full structural fixture and require
acceptance without mutation, while malformed row controls still fail.
`RAW-INFLUENCE-R3-FAILURE.json` preserves the old gate rejection. R3 source and
preparation freezes are retained unchanged. This is a Python/tests/docs gate
repair only; it does not convert the failed R2 shoulder capture into accepted
witness evidence. Existing nine eye controls use a separate comparison path.
Rust, camera gates, fixed Works and actual arrays are unchanged.
