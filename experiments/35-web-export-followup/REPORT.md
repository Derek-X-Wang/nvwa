# Issue 5: two bounded supported-observation controls

**INCONCLUSIVE — cause remains unknown; no product fix selected.** The
document-scoped automatic control and the original explicit button each
produced a current actual 1280×720 RGB PNG. A listener armed before navigation
did not observe an automatic event in its 30-second window. That first result
does not establish missing file durability: no download path was returned,
and no broad Downloads scan was performed.

## Actual outcome

| Boundary | Case 1: listener spans navigation | Case 2: listener in loaded document |
|---|---|---|
| Actual Rust callback | `true`, 15.428 s | `true`, 15.3988 s |
| Runtime state | Ready, idle, revision 0 | Ready, idle, revision 0 |
| Automatic download event | No event observed in 30 s | Event and exact path observed in 21.059 s of a 30 s window |
| Automatic durable file | NOT-VERIFIED; no path returned | 306354 bytes, original rendered character/UI PNG |
| Original explicit button | Event/path observed; 326061-byte rendered PNG | NOT-RUN; further trigger unnecessary |

The exact callback clock is `bevy_TimeReal_since_first_update`. Its Web
`capture_file_bytes` remains zero in both real callback records. These are
actual console `NVWA_EVIDENCE` events, not observer-created callbacks.
[Case 1 callback](evidence/case-1-runtime-event.json) and
[case 2 callback](evidence/case-2-runtime-event.json) preserve attribution to
their raw tool outputs.

Case 1's event listener began at `2026-10-13T22:31:31.187Z`, before navigation
at `22:31:31.196Z`. It ended at `22:32:01.204Z` without an event. The actual
Rust callback was separately captured by the adapter at `22:31:47.456Z`.
This is a listener-spanning-navigation non-observation, not a 30-second period
measured from the callback. [Original receipt](evidence/case-1-auto-wait.raw.json).

The original explicit button's listener began at `22:32:28.146Z`; its event
and path returned by `22:32:28.480Z`. The exact returned file was born at
`22:32:28.340859Z` and modified at `22:32:28.342030Z`.
[Original event](evidence/case-1-explicit-wait.raw.json),
[file receipt](evidence/case-1-file.json),
[original PNG](evidence/case-1-explicit.png).
This was a supported tool UI click. Actual `isTrusted`/activation fields for
this first button remain unverified because the adapter's read-only scope did
not expose the observer's custom Window field. No human-origin click is claimed.

Case 2 loaded a top-level wrapper with a fixed 5-second pre-init delay. Its
listener began after navigation returned at `22:34:21.043Z`. The actual callback
was retained by the browser observer at `22:34:41.985Z`, and by the adapter at
`22:34:42.038Z`; these are separate timestamp sources. The event and exact path
returned by `22:34:42.102Z`. The actual automatic file was born at
`22:34:41.988376Z` and modified at `22:34:41.990503Z`.
[Original event](evidence/case-2-auto-wait.raw.json),
[observer/context](evidence/case-2-context.raw.json),
[file receipt](evidence/case-2-file.json),
[original automatic PNG](evidence/case-2-auto.png).
The bootstrap delay does not alter Bevy's warmup or character/editor logic.
No UI activation starts case 2. It is an observation control, not a selected fix.

## File and pixel verification

Both files have valid PNG signatures, all chunk CRCs, complete IEND, decodable
IDAT data and 1280×720, 8-bit RGB headers. I independently opened both exact
downloaded-byte copies and saw the actual fixed humanoid and Nvwa editor UI,
including idle timeline and revision 0. They are different animation instants.
No rendering or fallback PNG was fabricated.

| Original file | SHA-256 |
|---|---|
| Case 1 explicit, 326061 bytes | `1c7cb42f5b606f5c201161e9f675c79e226180952a7bbe80197bc73b6357342b` |
| Case 2 automatic, 306354 bytes | `e62a9bb7ca0de1332ed84b8ea0624af53561d9252f44aa1b132955ee505fe581` |

The separate original adapter screenshots are JPEGs, preserved by decoding
their own tool output data URLs without re-encoding. They show the live browser
control and are not the downloaded PNGs. Exact session/call/content-index/time
and byte hashes are in [screenshot provenance](evidence/screenshot-provenance.json).

## Source, network and clock boundary

All 32 accepted source-cohort members matched the final build input manifest
before running. Both runs served the same accepted 85605719-byte Wasm SHA-256
`d890dfee73e9eeeee6ce3d82f255c79979e8c8b6bed90243c6101f8e1c1763a8`, unchanged
JavaScript, GLB `f13e0189…` and the 1624-byte common `character-loop.nvwa.json`
SHA-256 `ff0b8e36…`. [Source/context](evidence/source-context.json) and
[network body records](evidence/network.jsonl) retain exact hashes and sizes.
No rebuild was needed. Root branch head at intake was
`7851c2e74f757f93774f2d5fa05151562c393012`.

Each critical resource had one actual successful GET per case. Optional GLB
metadata and favicon requests returned explicit 404s; the GLB itself returned
200. No critical failure or app error was captured. One read-only adapter query
failed because its scope lacked `performance`; the raw error is retained as an
adapter read limitation, not a runtime failure. A second query found the actual
canvas and captured Rust logs. Case 2 used supported hidden DOM-journal text
instead of the unavailable custom Window field.

Observation clocks are separate: Rust callback seconds since Bevy's first
update; browser observer `performance.now()`/`timeOrigin` plus its own UTC;
adapter log receipt UTC; worker event-listener UTC; server socket-write UTC;
and filesystem birth/modification UTC. No exact conversion, latency attribution,
GPU timing, first-presentation claim, or cold-start measurement is made. The
console wrapper changes the adapter's caller URL to `observer.js`; preserved
message text identifies the real Rust event. Its original arguments, receiver,
return and exceptions are forwarded unchanged. Observer calls add overhead.

## Interpretation and limits

This experiment does not repeat the prior iframe A/B/D/C attachment and revoke
tests. It makes no anchor, Blob, revoke, or canvas-encoding intervention. The
second case improves supported listener setup by using a loaded document and
an early bootstrap gap. It also changes observer storage and startup timing;
those changes prevent assigning the case difference solely to the adapter's
navigation subscription lifetime. The historical top-level missing-file
condition remains unproven. The current successful automatic control supports
stopping at the bounded result and retaining issue 5's unknown cause.

NOT-RUN — original M0 exact condition/cause, broad filesystem absence for case 1,
physical-human activation, iframe event routing, external browsers, permission
policy, product fix, native export, GPU performance, and further loads/triggers.

## Verification and cleanup

VERIFIED — two actual callbacks, two independently inspected durable PNGs,
nine CPU controls (two Node and seven Python), immutable packet hash checks,
and a retained 30-second automatic non-observation. Corrupt/truncated actual
PNG negative controls fail as required. The source/network cohort and clocks
remain separately attributed.

Only two Nvwa loads and three total download triggers ran. The two server
incarnations were sequential, never concurrent: PID 45164/session 84034 then
PID 52635/session 44426. Both exited 0. Fresh exact checks found neither PID nor
port 9206 listening. Owned tabs 1 and 2 closed, IAB browser 2 had no remaining
tabs, and the viewport override reset. The UI/GPU lease was released to root.
Only the two exact fresh `Download.path` files were removed after matching
birth times, original/copy hashes, complete PNG validation, and fsync of the
retained copies. Existing download files were not scanned, moved, or deleted.
[Resource cleanup](evidence/cleanup.json),
[exact download cleanup](evidence/downloads-cleanup.json).

**QUIESCENT.** Root owns independent R2 review, archive copying, integration,
and GitHub publication. This worker changed only experiment 35 and its private
packet. No product, old experiment, shared docs, dependencies, Git state,
settings, profile, or external service changed.

## CPU-only observer hardening after R2 finding 3

Independent review found that the historical DOM journal returned before
publishing its overflow count. A synthetic 100-error control forwarded all
100 originals and retained 64 records, while its DOM `dropped` remained zero
and the in-memory count was 37. Actual case 2 had only two records, so that
finding does not invalidate its callback, download, inspected PNG or conclusion.

The current future helper publishes the journal on every overflow. DOM-backed
controls now check every intermediate count, the 64-record bound and unchanged
console arguments, receiver and return. Initialization and write exceptions
are contained; original console exceptions remain unchanged. Subsequent
successful publication includes `journalFailures` and the current drop count.
Repeated failed writes leave the last successful DOM snapshot stale, and failed
initialization provides no supported DOM journal. These failure paths are CPU
controls, not newly observed browser behavior.

VERIFIED — six Node and seven Python controls; offline historical packet
verifier remains green. Three isolated source mutations each fail (exit 1):
early return on overflow, throwing a DOM update error before forwarding, and
raising the record bound to 65. Restoring the current source makes all six
Node controls pass for each copy (exit 0). Private red/restored-green receipts:
`.work/issue5-export-followup/rework/mutant-controls.json` and named logs.

All 36 historical evidence files, including both observer snapshots, manifest,
raw packets, downloaded PNGs and original screenshots, retained their exact
pre-rework hashes. The current `observer.js` is future tooling, explicitly
separate from the historical actual-run case-2 source. No browser, GPU, server,
download, native run or build occurred during rework. Resource state remains
QUIESCENT; original issue 5 cause remains unknown and no product fix is selected.
