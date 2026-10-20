# 73: isolated high-poly eyes A/B

This experiment compares existing approved local high-poly eyes with the retained low-poly production eyes. It does not change a product crate, admitted asset set, material policy or Work format. Higher polygon count is not quality clearance. Intended eyelid fit remains **UNKNOWN** without an authenticated anatomical/authoring reference.

## Frozen comparison contract

Main observations per endpoint are **four existing short/long × front/quarter Works × source0/source2 × A/B =16 normal combined/textured captures**. Use `works/{short-front,long-front,short-quarter,long-quarter}.nvwa.json`. These preserve retained65 recipe, diagnostic pose, timeline, stage, camera and lights exactly. Only canonical saved appearance and revision+1 differ. The long recipe retains its original jaw1. It is not the later jaw0 shoulder witness.

A is `a_original`: the current original production low-poly eyes, with no buffer replacement. B is `b_high`: the original authenticated high-poly source, fitted to the same complete current19158 helper cage, all53 current bones, full final-positive influences and original eye entity placement. Original UV corners and fan triangle order are retained. A replay must match actual production positions, normals, UVs and indices exactly before either variant can publish evidence.

Body-only, eyes-only and unlit-textured controls are bounded to a representative case when needed. The optional complete diagnostic set is12 controls: A/B × combined/body_only/eye_only × textured/unlit_textured for one case/pose. Normal combined/textured evidence remains mandatory. The four historical recipes do not constitute eight-parameter cohort acceptance. The neutral eight-parameter compatibility observation is NOT-RUN; this experiment's strict capture gate currently accepts only the four historical Works.

The independently checked CPU source evidence is `CPU-REPLAY.json`: actual retained68 native/Web A replay has zero maximum position/normal/UV error; eight retained65 cage replays cover the four matched recipes on both endpoints. Earlier65 used a different accessory renderer, so those eight records establish cage arithmetic only. B has1064 source positions,808 UV rows,1020 faces,1076 uploaded UV-corner vertices and2040 triangles. Its mapping retains102 negative coefficients. These current eye rows have one final-positive bone; the retained numeric synthetic regression separately checks more-than-four preservation.

## Source authentication and limits

The portable source gate keeps the complete309-entry `FROZEN-INPUTS.json`
unchanged. `frozen_context.py` authenticates that original manifest and
`source-context-closeout-v1.json` with code-pinned hashes. It admits exactly two
complete source contexts: the original frozen309 inputs, or the reviewed stage
closeout with four exact overrides. Those overrides are the Core version-error
diagnostic, its Core/CLI tests, and the runtime CPU-feedback test helper. The
other305 input hashes and byte counts remain exact. Mixed contexts, unreviewed
source edits, missing or symlinked files, and missing, empty or altered manifests
reject. The CI-called gate retains its hash, byte-count and manifest-shape
checks. Disposable-copy controls test both complete contexts and all fourteen
mixed combinations without needing Git history.

This admits source compatibility for the portable checks. It does not rerun or
relabel historical eye captures, build receipts or quality results. Original
frozen records keep their original source identities; current eye rendering and
quality acceptance remain separate evidence.

`SOURCE.json` pins the original280737770B system archive and exact785436B four-file subset. `source/` preserves original OBJ/MHCLO/MHMAT/PNG bytes. Selected ZIP decompression/CRC, SHA256 and sizes were checked against the replacement plan. Pack metadata and existing CC0 legal text are retained under `source/provenance/`; OBJ/MHCLO/MHMAT original headers name Data Collection AB, Joel Palmius and Jonas Hauquier. No bytes were downloaded. This is a selected-member CRC pass, not an all-member archive CRC pass.

```sh
python3 -B experiments/73-high-poly-eyes/authenticate.py --archive EXISTING_APPROVED_SYSTEM_ZIP
python3 -B -m unittest discover -s experiments/73-high-poly-eyes -p 'test_*.py'
```

The brown material and PNG match A's original bytes. B binds the exact existing production material/image handles and decoded pixels, preserving `simple-srgb-mask-v1`, Mask0.5, back-face culling, single-sided eyes, roughness0.7 and every other material field. Unlit only changes `unlit` for body/eyes. The original MHMAT references absent legacy litsphere shader and skinmat_eye.png. They remain absent. This is not MakeHuman reference-shader parity.

`src/geometry.rs` mirrors the production numeric fitter. `NUMERIC-SOURCE.json` pins its source; tests compare the numeric function bodies. Raw MHCLO scale-reference distances and offsets are converted decimetres→metres once inside its parser. The actual fitted body cage is already metres. OBJ position bytes authenticate source topology but are not multiplied into fitting. Coefficients remain signed, normalized by their signed sum; transfer retains every strictly positive final aggregate before normalization. No capped influences, extra position offsets, synthetic lids, body deletion, second scale, second skin or extra placement is used. Source helper declarations still do not identify the author's intended body recipe.

## Publication and epoch guard (review before runtime)

The app calls `nvwa_studio::build_app()` with the production appearance controller enabled. The same existing eye entity, Mesh3d handle, material/image and transform are used; there is no second eye entity or overlapping A/B draw.

1. `PreUpdate` restores the exact original eye Mesh and original Aabb, then restores diagnostic materials/visibility before production runs.
2. `PostUpdate`, explicitly after `RuntimeSystems::Appearance` and before both `VisibilitySystems::CalculateBounds` and `CheckVisibility`, validates current production A, evaluates the chosen source against actual current bones and publishes B into that actual eye Mesh asset. B gets `compute_aabb()` from its exact current positions; no inflation, disabled culling or relaxed bound is introduced.
3. That publication records variant, actual positions/normals hashes, current Work hash, generation, placement and actual camera as a culling witness. The normal visibility systems then run on those buffers/bounds.
4. `Last` temporarily restores A for production snapshots, repeats exact A replay, and republishes the same chosen arrays. A capture requires equality with the pre-visibility publication witness for **two consecutive stable updates**, current typed Work/sample/bones, and the retained camera gate. Therefore a first transition frame is pending; a stale A culling result cannot certify B readiness. Render extraction follows Last. Only the selected variant is published for that extraction.
5. Every subsequent candidate frame revalidates production A before B. Work/generation/entity/mesh/material/image/pixel/placement changes fail closed. Source maps validate the actual bound Mesh buffer lengths, UVs and indices. Errors restore A and invalidate capture evidence. The Last full frame is CPU readback, not GPU attachment readback.

`src/candidate.rs` owns the fit/cache/binding/publication guard. `src/lib.rs` owns schedule order and the correlated request protocol. `src/diagnostic.rs` preserves isolation/material controls. Independent review must inspect the admission/epoch/culling guard before root executes UI observations. No GPU-ready assertion is made from a CPU-ready acknowledgement; root must allow normal render updates and retain screenshots separately.

## Root-scheduled build (no app/server launch)

The root grants one heavy CPU slot, jobs1. Use a distinct target directory owned only by this run. `build.py` runs Python source tests, Rust format check, native unit tests, native bin build, Wasm library build and existing wasm-bindgen export serially, offline and locked. It records checks, source closure and exported file hashes, and emits a receipt only if every step passes and the source closure remains unchanged. It starts no window/server/browser.

```sh
/opt/homebrew/bin/python3 -B /ABS/OWNED/nvwa/experiments/73-high-poly-eyes/build.py \
  --out /ABS/OWNED/nvwa/.work/eyes73/export-r1 \
  --target-dir /ABS/OWNED/nvwa/.work/eyes73/target-r1 \
  --bindgen /ABS/EXISTING/wasm-bindgen
```

Use `wefty exec --detach --max-runtime 90m` for the long job. The authorized run uses the stable absolute live source path and makes no edits during execution. Wefty's frozen checkout and the build's actual live source closure are distinct identities; only the latter identifies the compiled source. Ignored target/output directories are not snapshot inputs. Do not reuse a target containing deleted ephemeral source paths.

## Runtime protocol (root sole GPU/UI controller)

Native launch after build/review and root's GPU token:

```sh
NVWA_ASSET_ROOT=/ABS/EXPORT/web/assets \
B1_73_COMMAND_FILE=/ABS/OWNED/command.json \
B1_73_REPORT_FILE=/ABS/OWNED/report.json \
B1_73_FRAME_FILE=/ABS/OWNED/frame.json \
B1_73_MOTION_FILE=/ABS/OWNED/motion.json \
/ABS/EXPORT/native/studio73 --benchmark --player --work /ABS/EXPORT/web/works/short-front.nvwa.json
```

Write each native command atomically with a fresh request ID. First startup may fail; retain it and use a new request. Wait for that exact ID in both report/frame. Current capture requires ready/acknowledged/request_succeeded/current=true and matching IDs. Export envelope is `{"report":...,"frame":...}`. Individual atomic files are not a multi-file transaction.

```json
{"request_id":"n73-hold0","action":"playback","seek_seconds":0,"playing":false}
{"request_id":"n73-A0","action":"diagnostic","mode":"combined","palette":"textured","variant":"a_original"}
{"request_id":"n73-B0","action":"diagnostic","mode":"combined","palette":"textured","variant":"b_high"}
{"request_id":"n73-hold2","action":"playback","seek_seconds":2,"playing":false}
{"request_id":"n73-A2","action":"diagnostic","mode":"combined","palette":"textured","variant":"a_original"}
{"request_id":"n73-B2","action":"diagnostic","mode":"combined","palette":"textured","variant":"b_high"}
```

Open each next exact Work with `{"request_id":"...","action":"open","work_json":"<exact JSON text>"}`. Retain16 combined captures and16 screenshots per endpoint. Restart endpoint between separate sessions rather than exceeding the128 distinct request limit. No arbitrary body parameter/camera sweep is authorized.

Serve only the owned exported Web site on the root-assigned free Nvwa port. Open `?work=works/short-front.nvwa.json&benchmark=1&player=1`. Browser API `window.b1_73` exposes `b1_73_command(JSON text)`, `b1_73_report()`, `b1_73_frame()`, `b1_73_work()` and `b1_73_motion()`. The panel is collapsed by default. It offers the same typed controls and correlated export. Original current UI and normal combined rendering remain the comparison surface.

```sh
python3 -B experiments/73-high-poly-eyes/check_captures.py SIXTEEN_ENDPOINT_ENVELOPES
# Only if the representative diagnostic matrix is needed:
python3 -B experiments/73-high-poly-eyes/check_captures.py --diagnostic-case short-front --seconds 2 TWELVE_ENDPOINT_ENVELOPES
```

Pass flag values with spaces: `--seconds 2`, `--max-runtime 90m`. Native and Web sets are checked separately. The checker requires the complete bounded matrix, two stable publication epochs, exact current Work/bones/sample/body/material/image/placement, fixed camera, unchanged non-eye arrays, independent full signed/source replay within the original1e-6 limit, full weight rows, exact mesh bounds and explicit actual bindings. It does not score pixels or establish GPU visibility/depth winners.

For a continuous observation, first make the current variant's normal combined/textured capture ready. Then issue `playback` with seek0/playing=true; the controller clears that run's bounded motion journal. Retain a root-observed continuous video and the CPU journal separately for each variant/endpoint, then pause and recapture. Motion publication remains tied to actual current bones and validates A before every B upload. The512-record limit is bounded witness storage, not a frame-rate benchmark or proof of complete head/eye motion. The authored arm clip does not establish eye/blink animation. A CPU witness cannot substitute for the observed normal combined motion result.

## Interpretation and stop rule

Report normal combined appearance, isolated eye silhouette/faceting and cross-endpoint differences separately. Keep original67 body-first candidates and68 faceting observations unchanged. Sparse CPU body-first rays do not identify anatomical eyelids or intended occlusion. A smoother eye-only silhouette is not evidence that normal combined lid fit is correct. Intended lid fit remains UNKNOWN without the missing authoring reference. Performance, GPU depth/object-ID readback, generated motion quality, shader parity, product asset admission and full eight-parameter acceptance are separate NOT-RUN categories unless newly observed and specifically authorized.

Appearance/garment and generated-motion quality HOLDs remain. No asset promotion, production repair, #3 acceptance or #4 performance closure follows from this experiment.

## R2 preparation correction and retained R1 failure

The immutable R1 build compiled native tests, then failed12/13: the mirrored low-poly OBJ parser rejected standalone `vn` records in the authenticated high-poly OBJ. R1 logs and its full source snapshot remain under the root-owned `.work/eyes73/`; `FROZEN-SOURCE-r1.json`/`FROZEN-INPUTS-r1.json`/`PREPARATION-r1.json` retain its public source identities. There was no successful R1 native bin/Wasm export receipt.

The original B OBJ has1064 finite standalone `vn` rows, but all faces reference only `v/vt`. R2 validates these unused source normals without changing source bytes or topology. A/B still use the identical fitted-source normal recomputation. A face normal-index grammar is not silently accepted. New regressions reject nonfinite or malformed normal rows. The numeric-mirror comparison excludes only this explicitly declared OBJ grammar extension; all fit/weight/skin bodies remain identical.

Independent R2 review also found two verifier gaps: the first checker trusted a boolean pre-visibility witness, and it could accept a complete matrix with wrong Work/source-time body data under coherent labels. `source_binding.py` now connects the raw serialized Work hash, current report/frame identities, compact/full base, typed backend/profile/parameters/pose/revision/generation, timeline/clip/source/cursor, appearance sample serial, actual Mesh3d body/garment buffers, original source-ID/index correspondence and complete current53 bones. It reuses unchanged71 raw-source rest-cage and full-positive LBS arithmetic, with the other six source parameters set to zero only for these legacy two-parameter Works. Retained60 authored FK/gauge checks bind current observed bones to source0/source2. The existing numeric bounds remain unchanged. The eye replay remains independently source-derived. The original R1 positive/negative controls are retained alongside the added controls.

Actual published eye POSITION/NORMAL hashes and the complete pre-visibility witness are independently verified. Original body/garment source correspondence is pinned by `BODY-CORRESPONDENCE.json`; its retained68 source capture SHA is explicit. Current complete arrays are connected to compact summaries and actual bound buffers. This verifies the claimed current recipe/body/eye evidence; it is not an anatomical or authoring-cage reference.

### Exact Web wire codec

R6 preserves the original raw Rust JSON strings in a prepared transfer, outside the DOM. Use **Prepare exact CPU record**, retain the small `#wire-status` manifest, then **Download prepared CPU record**. The envelope remains a textual concatenation of `{"report":` + raw report + `,"frame":` + raw frame + `}`. Verify downloaded byte length and all SHA256 values, and supply the expected request ID retained independently from the issued command, before the unchanged strict capture validator. The collector binds that ID to the manifest and original raw report/frame, checks the token/hash relationship, and rejects ready:false or stale/correlated-header mismatches. A fallback visible chunk-index input and **Show prepared chunk** button expose one32768-byte base64 chunk in `#wire-chunk`; no hidden bridge calls are needed. Complete length/hash/token checks reject incomplete or mixed transfers. See `COLLECTION-R6.md` for the bounded root UI plan. Parsing for correlation checks does not rewrite any exported witness; never parse numeric arrays and re-stringify them for evidence.

The pinned codec is serde_json1.0.152/zmij1.0.23: original f32 arrays are promoted to f64 `Value` numbers, signed zero is retained, float integral values retain `.0`, and Value object keys are sorted. Unchanged71 `hash_encoding.py` supplies the float token policy;73 extends it to the complete bone Value object. Field coverage includes actual eye POSITION/NORMAL, body/garment position/rest/normal/index compact summaries, source IDs/indices, compact53bone digest, serialized Work bytes and the complete variant/positions/normals/placement/camera/Work/generation publication witness.

The specific retained `web68-2.json` producer bone hash is **NOT-VERIFIED** from its parsed/re-stringified envelope. Its original producer digest cannot be reconstructed from the retained numeric record; that record contains no negative zeros. The matched retained native68 bone digest reproduces exactly and contains307 negative zeros. This limit is separate from the verified independent numerical rest/LBS/eye replay. No old capture is rewritten, repaired or granted new exact-hash acceptance. The73 exporter preserves the raw wire bytes to avoid this loss.

The complete synthetic16-case checker controls require existing local source captures. They are tool regressions, not endpoint observations:

```sh
python3 -B experiments/73-high-poly-eyes/checker_controls.py \
  --legacy-capture-root EXISTING_APPEARANCE79_DIRECTORY \
  --actual68 EXISTING_RETAINED68_COMBINED_ENVELOPE \
  --historical-r1-checker OWNED_RETAINED_R1_CHECKER \
  --out OWNED_CONTROL_REPORT
```

A valid full16 synthetic matrix must pass. Missing/contradictory witness fields, publication hashes, wrong Work/sample/current records and actual body buffer mismatches must reject. Two coherent complete16 forgeries are retained as red/green comparisons: reusing a short cage for long Work labels, and labeling source2 body/bones as source0. R1 accepts each with zero eye replay error; R2 rejects them through the raw rest-cage and authored FK guards. R2 needs a new source freeze, binary identity and independent re-review. The root's forthcoming reviewed runtime update and final native/Wasm export remain separate pending work.

| Authentic source property | A low-poly | B high-poly |
| --- | --- | --- |
| Source positions / uploaded corners / triangles | 96 / 96 / 172 | 1064 / 1076 / 2040 |
| Raw x/y/z scale references (dm) | 1.7412 / 2.7409 / 2.2613 | 1.6482 / 2.7213 / 2.2795 |
| Negative coefficients retained | 0 | 102 |
| Original authored offsets | unchanged | unchanged |

B has different authored mapping/scale references/offsets and checked fitted extent. It is not a subdivision-only intervention. No alignment, rescale or post-offset is applied to make it pass. Any later smoother/different silhouette describes the whole alternate asset at the observed samples; polygon count causation and intended eyelid fit remain unproved.

## Issue #93 manifest gate checkpoint

`test_prepare.py` requires a nonempty, valid `FROZEN-INPUTS.json` object. Each
entry must contain a nonnegative integer byte count and a lowercase SHA256;
the named file must exist and match both. Missing, empty or corrupt manifests
fail the source test, including under `python -O`. Preparation before a freeze
exists is no longer a passing source-check state.

`test_frozen_inputs.py` runs the actual
`SourceContract.test_frozen_source_inputs` entry in disposable repository copies.
It accepts the unchanged current manifest and rejects missing/empty manifests,
corrupt JSON/entries, incorrect digests/byte counts and changed file bytes.
The normal CI discovery command includes these controls in both normal and
optimized Python. All original 29 Python/Node tests remain; the five new tests
bring the total to 34. Rust and its 16 tests are unchanged. They were not rerun
locally for this Python-only repair; the unchanged standard PR and main CI
will run those 16 tests.

`FROZEN-SOURCE-issue93-manifest-gate.json` and canonical `FROZEN-SOURCE.json`
identify this source-check repair. The former canonical bytes remain unchanged
as `FROZEN-SOURCE-r6-identity.json` (SHA256
`2160b3cd40ae059ac4f8fd50ea472e07b664f28c16ae0bf8702f84ec97bcf811`).
All historical R1–R6 source/input snapshots, preparation records and evidence
remain unchanged. `FROZEN-INPUTS.json` still contains the same 309 entries and
has SHA256 `66f024238ef009d0544d617251c46754b202b3069254ce5df47dc6dfc6debc33`.

The source freeze records byte counts and SHA256 for the prior canonical
membership, the retained R6 identity snapshot and the new regression test;
it excludes itself and its identical canonical alias to avoid self-reference.
No existing script writes a source freeze: `authenticate.py` verifies the
retained archive subset, while `build.py` records a build-time source closure.
The issue #93 freeze is a separately verified inventory, not a new build,
export or endpoint observation. Existing compiled/captured R5/R6 evidence keeps
its original source identity. Issue #3 remains blocked, issue #4 gaps remain,
and issue #79 quality admission stays **HOLD**.
