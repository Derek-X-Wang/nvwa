# Parameter acceptance71

This probe wraps unchanged `nvwa_studio::build_app()` and the actual production
appearance controller. It adds one read-only Last observer and strict typed
request transport. It does not implement rendering, fitting, materials,
visibility overrides, animation, generation or the file toolbar. Its complete
held CPU cohort is separate from ordinary UI, live motion, screenshots, quality
and performance acceptance.

The linked candidate is backend3/basev2/profilev2/appearancev2. The frozen
`inputs/cases.json` has SHA256
`7abedf9e9c46245d7c9cf0aaeab77e716fb37dd538aa76cccdae935e6fda9185`:
21 recipes,69 held samples per endpoint, plus three separately required live
recipes. Existing eyelid, hair and clothing quality HOLDs remain open.

## Inputs and independent expectations

`inputs/raw/` contains original approved CC0 HM08 base text and16 original
expanded sparse target texts. Their exact hashes and original relative paths
are in `inputs/oracle-sources.json`. MPFB source commit is
`d0a32e57a7f915cb2f2b95410e2117648c7bbb7e`. These are data, not copied MPFB
program logic. The base source hash is
`8e761e6624b8f54536409135d1636da63b32486a90d4897f84e121d144f6fb4c`.
The included CC0 license applies to these data.

`oracle.py` does not import or call production math or target catalogues. It
parses unique original source IDs and computes raw base plus selected signed
sparse deltas, with exactly0.1 conversion once. It requires actual body rest
records to cover all19158 source vertices and verifies duplicate render/source
correspondence. It also computes scalar normalized full-positive linear blend
skinning from each part's observed rest points, complete positive rows and all53
observed skin matrices. It uses every provided influence; it never truncates to4
or reapplies model_to_world, display, facing, scale or skinning. The component
limit stays1e-6 metres, matching the existing fitted/display correspondence
limit. These checks do not independently derive bones, proxy influence transfer,
anatomical semantics, lighting or GPU visibility.

`prepare_works.py` requires the integrated canonical
`examples/b1-character.nvwa.json` and authenticates the linked base/appearance
manifests. It creates69 synthetic Works and an explicit request plan in
`works/plan.json`. Each Work uses one finite, nonloop clip of length4, so source4
cannot silently sample the next entry. It changes only the predeclared recipe,
saved selection, finite timeline and synthetic revision. It sends normal typed
Open/playback; it does not bypass candidate admission. Preparing files is not
runtime or ordinary-UI proof. If #85 is absent, preparation fails NOT-LINKED.

## Build/export: root scheduled only

Use an existing Python3.11+ (tomllib), the root's isolated job checkout/target,
locked offline dependencies, and jobs1. No worker build, app, server, browser or
GPU launch is authorized by this README. Root schedules the single combined
workspace/probe/native/Web validation and wraps long checks with wefty.

```sh
/absolute/existing/python3.11-or-newer -B experiments/71-b1-character-parameters/build.py \
  --out /absolute/owned/export71 \
  --target-dir /absolute/isolated-job/target \
  --bindgen /absolute/existing/wasm-bindgen
```

The script prepares linked Works before freezing its actual source closure,
then runs source tests, formatting, native Rust unit tests, native bin build,
Wasm lib build and wasm-bindgen export sequentially. It retains per-step logs,
exit/timing receipts, source hashes, `native/studio71` and
`web/{index.html,pkg,assets,works}`. A successful export receipt requires all
checks to pass and an unchanged source closure. No dependencies are added or
fetched. Compilation/export does not establish actual launch or GUI quality.

## Shared request and evidence contract

Only these mutually exclusive actions are accepted:

```json
{"request_id":"open-case","action":"open","work_json":"<exact Work JSON text>"}
{"request_id":"command","action":"command","command":{"type":"undo"}}
{"request_id":"held-case","action":"playback","seek_seconds":2,"playing":false}
{"request_id":"fresh-capture","action":"capture"}
```

Shared Core parsers and normal editor transaction/candidate Open own all Work
changes. Unknown, duplicate, null, irrelevant or incompatible fields reject.
IDs are1..64 ASCII letters/digits/underscore/hyphen. A512-entry digest ledger
stores IDs and request digests, not Work history. Wait for the matching terminal
acknowledgement before the next request. Identical replay retains its current
acknowledgement/frame; it cannot yield ready/current with an empty export.
Different content under a reused ID rejects. Fresh requests replace prior
pending evidence. Current Work/generation/revision/body/preview/pending-Open,
transport, camera/environment and runtime/appearance/stage/playback errors
invalidate current evidence. A failure remains failed until a fresh request.
A failed Open must be cleared by a successful normal Open before capture can
certify a current state. Timeout is45 actual app-clock seconds, including stability waits. Held captures
require two consecutive Last observations with identical actual Work/generation/
transport/camera/environment identity after readiness. Camera/body-fit changes
reset that count. Live requests are explicitly labeled live-transient and
naturally stale on the next advancing frame; they are not held acceptance.

Only ready+acknowledged+request_succeeded+current, all true, with matching report
and frame IDs is successful current CPU evidence. Each full frame retains the
unmodified production `b1_frame_snapshot` as `full_base`: all body/garment
arrays, source IDs, rest points/normals, full positive rows,53 bones, tangents,
indices, placements, sample and contact data. Exact production
`appearance_snapshot` is retained separately. `observed` follows the exact
current entity→Mesh3d/StandardMaterial/Image handles and exports actual mesh
positions/normals/tangents/UV/indices/globals plus full material Debug records.
It validates base arrays against the full snapshot and accessory upload hashes
against the production snapshot. Actual CPU image bytes are rehashed through
the bound image handle; width/height/format/sampler/count/hash are retained.
Repeated multi-MiB immutable RGBA arrays are omitted explicitly. There is no
GPU texel/depth/object-ID readback. Accessory fitted rest/influence rows are not
public production data and are not relabeled as observed or reconstructed.

`ViewVisibility` is CPU camera culling. Actual viewport, global camera matrix,
projection and subcamera are exported; no second transform is applied to the
already posed metre-space arrays. A ready CPU report is not a same-frame GPU
material-ready signal, screenshot receipt or quality decision.

## Native files and Web visible DOM

Root owns launches and the one GPU controller. Create the native command file
before launch; retain any startup-before-ready failure and then use a fresh ID.
The ordinary production asset resolver and launch flags remain unchanged.

```sh
NVWA_ASSET_ROOT=/absolute/owned/export71/web/assets \
B1_71_COMMAND_FILE=/absolute/owned/command.json \
B1_71_REPORT_FILE=/absolute/owned/report.json \
B1_71_FRAME_FILE=/absolute/owned/frame.json \
/absolute/owned/export71/native/studio71 --benchmark --player \
  --work /absolute/owned/export71/web/works/zero-b1_arm_rehearsal_v1-0.nvwa.json
```

Replace command JSON atomically. Report/frame files are atomic individually,
not a two-file transaction. Match both IDs before retaining evidence. A report
error invalidates any leftover file; an inaccessible channel cannot be assumed
cleared. Source plan requests give Open then held playback; each successful
held acknowledgement already contains the complete frame, so an extra capture
is optional. The69 pairs need138 unique IDs within the512 bound.

Root serves the exported Web site on its assigned free port and opens
`?work=works/zero-b1_arm_rehearsal_v1-0.nvwa.json&benchmark=1&player=1`.
The visible JSON form sends the same typed protocol. Read-only textareas
`acceptance-report`, `acceptance-frame` and `acceptance-work` expose complete
current JSON for root's read-only DOM export into task-owned files. No mass
Downloads, hidden external endpoint, arbitrary asset URL or host-file reader
is installed. `window.b1_71` exports command/report/frame/work functions for
this visible bridge. Collapse the panel for separate screenshots.

Retained envelopes have this explicit wrapper:

```json
{"case_id":"<frozen held case ID>","report":{},"frame":{}}
```

Root supplies case_id from the frozen plan. It does not substitute a case label
for actual current Work/sample verification. Native/Web endpoints are checked
separately; neither is filtered out after a failure.

```sh
python3 -B experiments/71-b1-character-parameters/verify.py \
  --plan experiments/71-b1-character-parameters/works/plan.json \
  --out /absolute/owned/native71-check.json /absolute/owned/native71-cases/*.json
```

The verifier requires exactly all69 unique frozen cases, distinct request IDs,
one endpoint, current correlated state, exact frozen recipe/appearance and
finite held Work/sample identity, complete named body/garment data,53 bones,
actual current accessory buffers/material/image bindings, raw rest-cage oracle
and full-positive LBS. Missing/duplicate/unknown/stale/invalid cases fail.
It streams full snapshots rather than retaining69 in memory. Long complete
cohort checks use the root's normal wefty scheduling rule.

The ordinary Studio New character/eight controls/Undo/Redo/Reset/Save/Open and
native→Web→native file exchange remain separate mandatory root actions. The
zero/face-wide/lower-body live runs remain separate from these69 held records.
This probe does not certify ordinary UI, endpoint quality, rendered visibility,
physics, AI generation or performance. All existing quality HOLDs remain.

## R2 verifier correction

The gate now recomputes actual accessory POSITION/NORMAL/UV/index hashes and
body POSITION/skin UV hashes using the pinned production encoding, then binds
the result to observer and production snapshot digests. It also cross-checks
actual Work/body/transport/serial/character/base identities. See [ENCODING.md](ENCODING.md)
for exact bytes, retained actual68 production goldens and raw frame retention.
R1's13 green Python tests were insufficient for the eight retained malformed
records; the historical freeze and failure reproducer remain preserved. This
is a Python/tests/docs repair. Rust and all fixed Works remain unchanged.
