# Saved B1 appearance: acceptance record

Schema4 now saves independent Skin, Eyes and Hair selections through the shared
editor command and Undo/Redo path. The approved fixed CC0 bundle is embedded for
native and Web use. Production retains `simple-srgb-mask-v1` and the published
asset identity; no experiment65 candidate is promoted by this record.

Actual native and Web CPU acceptance, ordinary Studio/Player launch observations,
and normal toolbar file exchange are recorded below. Their scopes remain
separate from GPU readback, performance and full visual-quality admission.

## Verification layers

| Layer | Recorded result | Evidence and limit |
| --- | --- | --- |
| Workspace CPU tests | PASS:194, zero failures | Includes72 runtime and61 Studio tests; [CPU receipt](CPU-CHECKS.json), no pixel proof |
| Current CLI help/portable gate | PASS:60 tests and strict Core/CLI Clippy | Separate rebuild after two CLI-only files changed; not60 additional unique workspace tests |
| Extra strict whole-workspace Clippy | FAIL:9 baseline warnings | Five B1 nested-if and four stage-signature warnings; [tracked in #84](https://github.com/Derek-X-Wang/nvwa/issues/84), no suppression |
| Product and66 native/Web build/export | PASS for the recorded r4 exports | [Build receipts](BUILD-EXPORTS.json); the joint driver still failed its extra strict lint gate |
| Ordinary production Studio/Player | Actual native and Web launches observed | [Labelled screenshots](screens/README.md); stills corroborate visible state, not uninterrupted motion or measured cadence |
| Native production CPU acceptance |54 held source frames; role/history/lifecycle checks pass | [Native records](native/REPRODUCE.md), actual entity-bound CPU buffers/materials/images |
| Web production CPU acceptance |54 held source frames; role/history/lifecycle checks pass | [Web records](web/REPRODUCE.md), same CPU evidence boundary |
| Normal toolbar Save/Open exchange | Native→Web→native recorded | [Exact files and roundtrip](exchange/README.md); GUI action provenance is root-observed and separately labelled |
| Isolated quality65 comparison | Native/Web16 controls each, plus Low baseline/recovery | [Separate report](../../../experiments/65-b1-appearance-quality/RESULT-DUAL-END.md); no candidate promotion or full visual-quality admission |
| GPU readback and formal performance | NOT-RUN in this record | File sizes, screenshots and paused samples do not establish either |
| Final exact-head PR / merged-main CI | Not established by this record | Must be verified independently on the final reviewed commits |

## Saved files and ordinary controls

The exchange used instrumented66, which calls the unchanged production Studio.
Root used the **normal toolbar Save/Open and browser file chooser**. The bridge
observed resulting production state; its Open commands, JSON exports and
**Export Work** button are not substituted for those GUI actions. Initial native
and Web Studio/Player screenshots use the separate ordinary product entrypoints.

| Exact saved file | Bytes | Revision | Saved appearance |
| --- | ---: | ---: | --- |
| [Native toolbar save](exchange/native-ui-saved.nvwa.json) |2743 |4 | Skin, Eyes, Hair |
| [Web toolbar Save/download](exchange/web-ui-saved.nvwa.json) |2744 |5 | Skin and Eyes; Hair cleared |

The actual native-saved file was selected through the normal Web picker. The
fresh Web observation matches its exact Work bytes/hash and changes generation1
→2. After a normal Hair checkbox edit, root completed the normal Web Save
browser download. Its bytes match the fresh current Web Work observation. Only
`revision` and `character.appearance.hair` differ semantically from the native
input.

The downloaded Web file was then opened through the normal native toolbar.
The [roundtrip record](exchange/ROUNDTRIP.json) and accompanying raw reports
show generation1→2, a fresh native body and exact returned Work bytes, with
Skin/Eyes bound and Hair disabled. Normal malformed file-picker Opens on both
platforms showed an error while retaining the prior Work/body. A fresh retained
state capture is a successful observation of the old valid state, not an error
acknowledgement for a bridge Open command.

The [file inventory](exchange/inventory.json) contains full SHA256 identities.
The [screen inventory](screens/inventory.json) labels ordinary product surfaces
and instrumented66 exchange surfaces. Raw files and CPU reports establish bytes
and state. Root's observed action history supplies Save/download/picker
provenance; stills alone do not prove those operations.

## CPU roles, shape and lifecycle coverage

Each platform covers all eight independent role combinations, paused Undo/Redo,
and nine recipes: torso `-1/0/1` × jaw `0/0.5/1`. With all roles enabled, each
recipe is observed at source times0/2/4 for both authored clips: **54 held source
frames per platform**. These are not uninterrupted playback frames or a full
role × recipe × time factorial test.

The eight-second arms+knee timeline samples global0/2/4/6/8. Global4 is **knee
source0**, so a separate shared arms-only `SetTimeline` sequence supplies the
nine missing arm-source4 endpoints. The original timeline, nominal parameters
and held sample are restored afterward.

The native cohort contains102 correlated requests:99 ready acknowledgements
and three expected rejections, plus a separately recorded boot request. The
Web cohort contains107 pairs:104 ready acknowledgements and three expected
rejections, including five observations around ordinary UI actions. Both
cohorts preserve exact raw request/report bytes and per-file hashes.

Malformed JSON, a forged appearance hash and B1 appearance on the GLB backend
reject explicitly. Separate fresh captures after each rejection retain the
exact held Work, appearance/base CPU state and identity. Actual schema3 Open
migrates to schema4 with explicit None and no current skin/accessory bindings.
Same-content Open publishes a new generation/body. The reports validate current
entity/mesh/material/image bindings and invalidate stale evidence; complete
asset-store disposal is covered separately by runtime tests, not exposed by
these bounded snapshots.

## Source cohorts, builds and retained failures

[BUILD-SOURCES.json](BUILD-SOURCES.json), [BUILD-EXPORTS.json](BUILD-EXPORTS.json)
and [CPU-CHECKS.json](CPU-CHECKS.json) separate the frozen r4 GUI cohort from the
later CLI correction. The recorded comparison finds346 of348 r4 inputs still
matching; only `crates/nvwa-cli/src/main.rs` and its real-process
`tests/appearance.rs` changed later to correct command discovery/help. Those
files are outside GUI dependencies. The separately rebuilt CLI has its own
23-source receipt and binary identity. The r4 GUI artifacts do not claim to
contain that later CLI-only delta, and whole-tree artifact equivalence is not
claimed.

The joint driver retained its failed extra strict workspace Clippy gate and
exited1 despite exporting useful QA artifacts. This is not an all-green joint
run. The nine unchanged baseline warnings are separate debt in #84; required
strict Core/CLI lint and all workspace tests remain enabled.

Earlier failed checks are retained rather than erased: a mistaken expectation
that head-only eyes move during arm rehearsal; CPU-only UI texture-delta
cleanup; and a long-path fixture whose overflow depended on temporary-root
length. The corrected controls retain actual body motion and stable head-bound
eyes, add a labelled synthetic driving/non-driving-bone buffer test, and keep
all path bounds/selection/copy/input assertions. An immutable old/fixed test
pair reproduces exit101/0 in the same26-character temporary root. The initial
native sender's pending-request rejection is also retained as a harness
sequencing failure, outside the successful cohort.

The exporter directly creates QA Web sites; it does not execute the normal
`scripts/build-web.sh` bundle-size helper. Compilation/export, packaging,
actual launch, file bytes, CPU observations and rendered stills each have
separate evidence. Public summaries normalize private log paths without
presenting those summaries as original logs or pixels.

## Review and remaining boundary

[REVIEW.md](REVIEW.md) records independent agent-authored source review and
follow-up corrections. Independent Astra review also checked the public raw
CPU, exchange and screen materials. That review does not convert root-observed
GUI actions into an independent event trace or certify GPU results.

The isolated quality65 evaluation is [reported separately](../../../experiments/65-b1-appearance-quality/RESULT-DUAL-END.md): both platforms retain four groups of four controls, plus Low baseline/recovery. Actual Low rejection reports lack request identity and remain PARTIAL. Hairline improvement is limited; eye normals do not establish repaired lid fit. No candidate is promoted. Production
material policy and asset identity remain unchanged. This slice does not admit
arbitrary assets, gaze/blink, authored head motion, hair physics, clothing
quality or M2 motion quality. #3 remains blocked; #4 retains its measurement
gaps. Quality and final CI gates are not closed by this document.

PARTIAL — recorded CPU tests, r4 builds/exports, scoped actual native/Web CPU
acceptance, ordinary launches and normal file exchange are evidenced. The extra
strict workspace lint remains failed; quality admission, GPU readback, performance and
final PR/merged-main CI remain separate gates.
