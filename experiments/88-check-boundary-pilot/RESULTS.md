# #112 local check-boundary pilot

2026-10-22. Local, additive and non-gating. The implementation reuses the
existing independent raw-recipe geometry path for authenticated archived v1
frames. It preserves historical identity admission as a separate contract.
No existing gate, assertion, fixture, workflow or runner frequency changed.

## Decision and remaining scope

The geometry reuse path can be tested without adopting a new runtime contract.
This pilot cannot qualify Linux migration or replace the historical exact
assertion. The absolute source-to-skeleton oracle remains
`NOT_VERIFIED_RIG_ORACLE`; internally consistent captured matrices do not prove
that the skeleton was constructed correctly from its source.

| Evidence | Outcome and limit |
| --- | --- |
| Historical report/source authenticity | Existing historical13 report and pre-interop sources remain pinned and unchanged. |
| Historical original-input admission | `BLOCKED_MISSING_HISTORICAL_INPUT`, exit2. Original gzip `5df0c97e5c51b3e71741e115ca4040d441189dd5853a505c1076d9ed0a53ae5e` is unavailable in the inspected archive. |
| Historical substitutes | Later Mac v1/v2 and retained Linux frames are rejected, exit1. Matching an area ratio does not authenticate an input. |
| Historical positive admission / replay | NOT-RUN. This pilot implements admission only. It does not substitute another frame or execute a replay without the original input. |
| Available current geometry | PASS_LIMITED_CURRENT_GEOMETRY, 30/30 in both normal and optimized Python. Scope is archived jaw0 geometry only. |
| Complete current runtime | NOT-VERIFIED. Independent absolute rig reconstruction and full geometry cohorts remain incomplete. |
| Original Linux controls | Original run39798844545 remains FAIL: two failures in18 normal controls; original optimized garment command remains NOT-RUN. These statuses were not re-executed or rewritten. |
| Quality/platform | #80 and other quality HOLDs remain. #3 stays blocked; #4 retains its gaps. No fresh runtime, GUI, GPU, platform or performance qualification. |

## Inputs and implementation

The independently enumerated retained set has three torso values (-1/0/+1),
jaw0, two clips and source times0/1/2/3/4s. All30 compressed files match their
pinned identities: 99,688,987 bytes in total. All13 v1 source payloads match their
manifest hashes and byte sizes: 5,725,107 bytes. No files were downloaded.

Capture provenance is the existing Linux run
[39798844545](https://github.com/Derek-X-Wang/nvwa/actions/runs/39798844545),
product source `baa0b6bbda0d9709f0fab37c9e7d962fd8d926c1`, tree
`f14ea4fa6ea749fdd06c36e0fca5d622feb5bb95`. These are archived provenance
claims, not a fresh Rust build or execution by this pilot. The local code base
before this experiment was `caf6069ab2ed26a3965cd27ad8f238db0d4a0596`.

`GeometryValidator` uses existing84 arithmetic through an adapter that verifies
the helper's resolved source root is the authenticated v1 directory. It does
not construct85's v2-loading `Baseline`. Imported helper paths, source hashes,
manifest and payloads are authenticated. The complete pinned closure and all
independent expected cases are in [catalogue.json](catalogue.json).

The adapter retains exact topology, bone support/order/parents, render-duplicate
consistency, full-positive influence support and the existing numerical limits:
raw-recipe rest `1e-7 m`, signed source fit `1e-6 m`, normalized weights `1e-6`
dimensionless, and upload reconstruction `1e-5 m`. Existing captured-bone
FK/rigidity/bind checks remain conditional consistency checks. No tolerance was
derived from the observed Linux difference. The old scalar is diagnostic only
in this separate pilot; both original six-place assertions remain unchanged in
their existing suite and gate.

Exact cross-pose identity retains85's bone rest/inverse-bind/canonical/gauge/
local-rest fields and each part's source IDs, topology, rest positions, rest
normals, full weights and placement. It is keyed by authenticated source
closure, profile and the complete supported recipe. Only a successfully
validated frame establishes a deep-copied baseline. This checks consistency
across poses; it does not provide the missing absolute rig oracle.

## Local measurements

Frozen iteration2 uses existing Python3.14.7 / Clang21.0.0 on Darwin arm64,
executable `/opt/homebrew/opt/python@3.14/bin/python3.14`, with `-B` and
optimization0/1. Compilation is N/A: stdlib Python only. All four commands are
local and individually bounded to59 seconds. Wall times are single
observations, not a speed benchmark or an optimization comparison.

| Command | Result | In-command wall time | Whole-process wall time |
| --- | --- | --- | --- |
| Normal focused controls |12 tests,0 failures/errors/skips|37.797s|37.984s|
| Optimized focused controls |12 tests,0 failures/errors/skips|38.416s|38.668s|
| Normal full available geometry |30/30, exit0|37.676s|37.796s|
| Optimized full available geometry |30/30, exit0|37.045s|37.196s|

Maximum component errors over every admitted frame agree between the two
modes:

| Existing reconstruction | Body | Garment | Existing maximum |
| --- | --- | --- | --- |
| Ordered raw-recipe rest |0m|0m|`1e-7 m`|
| Scalar-f32 matrix-blend upload |0m|0m|`1e-5 m`|
| Independent source-weight/FK/f64 upload |`4.54122611487362e-7 m`|`2.993602269685258e-7 m`|`1e-5 m`|

Both batches preserve exact captured rest identity across poses. Jaw endpoints,
non-keyframe continuous times and complete seek/pause geometry are not covered.
All30 frames remain the original Linux-produced bytes; the reconstruction
executed locally on Mac, not on a new Linux runner.

The focused suites call the real CLI `main` in-process, so each suite's Python
optimization mode applies to the actual validator. Both full30 commands run as
external CLI processes. Root independently ran two further external historical
CLI calls: missing input returned2 in0.290s, and the Linux substitute returned1
in0.162s. Both completed zero frames and kept replay NOT-RUN. These are negative
controls, not a successful historical admission.

Final implementation identities:

- `pilot.py`: `c6d73900cbe6423c666fdf3bb85c6bff624375f5e2539bfb177dd3d1b0c32f4d`
- `test_pilot.py`: `cb438760da58ec0495fda26128e227a3a181f234a2686d3e7b5e9f5423da962c`
- `catalogue.json`: `c3f0d91d735b032b4806c87f87f8f0c82965b0cd12abdb5c41ddbebee36648c3`

Earlier iteration1 timings used Python3.12.11 and a superseded implementation.
They are not pooled with the final measurements or used as performance evidence.

## Fault rejection, review and recovery

An independent review rejected the first implementation for two P2 defects:
recipe/time faults were no-ops on zero-valued templates, and exact cross-pose
rest/weight/placement invariance was missing. The reviewer reproduced both
through the actual CLI/validator, including a10m common placement change under
`-O`. That initial green result is preserved as superseded evidence.

The repair chooses a different in-range recipe/time value for zero templates.
It also restores the exact persistent identity comparison above. New controls
exercise different genuine poses on the same validator, then separately alter
sub-bound rest coordinates, both parts' common placement, rest normals, raw
weight scale and bone local rest. Each derived payload must first pass a fresh
validator's numerical checks, then fail the established exact invariant and
allow the original input to pass again. This distinguishes the restored
contract from an unrelated early rejection. Caller mutation cannot change the
frozen baseline. Original compressed frames remain unchanged.

Existing controls retain missing/corrupt/substitute identity, strict bounded
decoding, unsupported/missing/extra cases, recipe/time/profile binding,
topology, rest, upload, normalized weights/support, output preservation and
restoration. Receipts distinguish authentic compressed templates from derived
payload hashes. These are local payload/admission controls, **not** Rust
production-source mutations. The existing production-source mutation gate was
not modified or rerun.

Final independent re-review found no remaining material finding in this
bounded pilot. It independently confirmed zero-case CLI rejection/recovery
(2.947s, normal) and cross-pose rejection/restoration/deep-copy protection
(5.286s, optimized), then verified all55 evidence payload hashes, both30-frame
inventories,12-test summaries and numerical maxima. The implementation changes
were made by the original worker, not the reviewer. The private re-review
record SHA256 is
`0132b3e80610e3b57bab12a723cd235145b9d3ca5b642e0ec6b8ff4a9d0f0bbf`.

## Reproduction and evidence

See [README.md](README.md) for the exact CLI forms for historical admission,
the available30 geometry batch and normal/optimized control suites. Use only
the existing retained inputs named in the catalogue and fresh output paths.
If the original historical frame is absent, preserve the blocked result.
Do not retrieve a replacement to make the historical dimension pass.

Final portable evidence is indexed by [evidence/manifest.json](evidence/manifest.json):
the complete [normal](evidence/geometry-normal.json) and
[optimized](evidence/geometry-optimized.json)30-frame receipts;
normal/optimized [control](evidence/controls-normal/test-summary.json)
[summaries](evidence/controls-optimized/test-summary.json), logs and individual
CLI receipts; and the [input readback](evidence/input-readback.json).
The [cross-pose control record](evidence/controls-normal/cross-pose-payload-controls.json)
records five discriminating faults and same-validator restoration. Their
optimized-mode counterpart is retained separately.

The private dated work-product archive `2026-10-22-112-local-pilot` also retains
exact execution argv, whole-process drivers, initial iteration1 receipts and
rejection/re-review records. Initial evidence is not overwritten. Root readback
confirmed both30-case inventories and every expected case/hash, mode and source
fingerprint against the final files. Original protected files and input hashes
were rechecked separately.

No Rust compile, model run, new runtime capture, download, remote compute, CI
run, gate migration or runner-frequency change was performed. The experiment
stays on `codex/112-local-pilot`; opening a PR or merging main would trigger
existing CI, so neither is part of this local-only pilot.

PARTIAL — local30-frame geometry and12 controls pass in both modes and
independent review has no remaining finding. Historical replay and complete
current-runtime/quality qualification remain unverified.
