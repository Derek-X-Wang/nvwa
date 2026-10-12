# Issue 5: actual screenshot export boundary results

The current top-level automatic Bevy download and original explicit canvas
Download button both succeeded. The historical
top-level M0 missing-file symptom was not reproduced by that control.
The instrumented iframe runs attempted real exports but produced no observed
download event or newly observed matching file within the recorded bounded
windows. Attaching the automatic anchor and delaying its revocation did not
improve the observed iframe result. No product patch is supported by this
comparison.

These are root-operated actual IAB observations from
[`docs/evidence/bounded-startup-capture`](../../docs/evidence/bounded-startup-capture),
separate from the worker's synthetic adapter tests. The worker performed no
browser/GPU runs. [SOURCE-BOUNDARY.md](SOURCE-BOUNDARY.md) records current source
lines and artifact hashes; [README.md](README.md) records the reproduction setup.
This report supersedes the README's preparation-time runtime NOT-RUN status for
the cases recorded below.

## Actual cases

| Case | Actual export boundary observed | Download observation | Persistent PNG evidence |
|---|---|---|---|
| Top-level automatic baseline, startup 2 | Frozen runtime, no export-probe anchor/revoke intervention | Event observed during 30-second listener window | Current 304648-byte PNG; root verified 1280×720 and visible actual character |
| A, instrumented iframe | Runtime-encoded 304792-byte blob; unattached automatic anchor; URL lifetime 3.1 ms | No event within the recorded 30-second wait | No new matching file observed in the bounded filesystem checks |
| B, instrumented iframe | Runtime-encoded 304852-byte blob; attached automatic anchor; URL lifetime 2.1 ms | No event within the recorded 30-second wait | No new matching file observed in the bounded filesystem checks |
| D, instrumented iframe | Runtime-encoded 304732-byte blob; attached automatic anchor; delayed actual revoke 1001.5 ms after request | No event within the recorded 30-second wait | No new matching file observed in the bounded filesystem checks |
| C, instrumented iframe | Original production button; real canvas `toBlob` returned 325267 bytes with `image/png`; attached explicit anchor; URL lifetime 1004.6 ms | No event within the recorded 15-second wait | No new matching file observed in the bounded filesystem checks |
| Top-level original explicit button | Original production button, no export-probe hooks; passive startup collector only | Event observed in 347 ms of the recorded wait | Current 324903-byte PNG; IHDR verifies 1280×720 RGB; root inspected actual character/UI |

Event waits are the total listener windows recorded in `export-*-download.json`.
They must not be described as 30 or 15 seconds measured from a Rust callback.
These are bounded non-observations, not evidence of permanent global failure.

### Top-level automatic baseline

[`startup-2-auto-download.json`](../../docs/evidence/bounded-startup-capture/startup-2-auto-download.json)
records a listener starting at `2026-10-12T11:02:12.027Z`, with a 30-second window,
and the download event observed by `11:02:20.443Z`.
[`startup-2-observation.json`](../../docs/evidence/bounded-startup-capture/startup-2-observation.json)
records 304648 bytes and modification time `11:02:20.219Z`.
Root retained the actual file as
[`startup-2-auto.png`](../../docs/evidence/bounded-startup-capture/startup-2-auto.png)
and independently verified PNG dimensions and visible character pixels. The
bounded filesystem packet identifies SHA-256
`3b9f64d0a20d8de741f69ee05d01a9550cc99edb2252f872dba73987b2eae54d`.

The current successful automatic file demonstrates an available top-level
export path in this run. It does not retroactively resolve the original M0
observation or establish that all browsers or all later attempts succeed.

[`startup-2-console.json`](../../docs/evidence/bounded-startup-capture/startup-2-console.json)
also retains the actual `NVWA_EVIDENCE` event: `capture_callback:true`,
`first_asset_ready_seconds:0.4248`, and `capture_callback_seconds:15.4457`.
Its clock is `bevy_TimeReal_since_first_update`. These seconds measure from
Bevy's first update, not browser navigation, probe installation, or the download
listener start. No conversion between those clocks is established. The event
records `capture_file_bytes:0`; its screenshot callback still does not by itself
prove durable-file completion. The separately observed download and independently
inspected actual PNG establish the saved-file evidence for this control.

### Top-level original explicit canvas button control

Root loaded the same frozen runtime in a top-level tab, with the passive
experiment-24 collector and no export-probe hooks. Root reports the same frozen
JavaScript, Wasm, and index module hashes. Its original production Download
button produced the event retained in
[`export-top-download.json`](../../docs/evidence/bounded-startup-capture/export-top-download.json):
wait start `2026-10-12T11:10:12.386Z`, event observed by `11:10:12.733Z`.
[`export-top-file-observation.json`](../../docs/evidence/bounded-startup-capture/export-top-file-observation.json)
records 324903 bytes and current modification time `11:10:12.493Z`.

The actual downloaded file is retained as
[`export-top-explicit.png`](../../docs/evidence/bounded-startup-capture/export-top-explicit.png).
Its PNG IHDR records width 1280, height 720, bit depth 8, and color type 2 (RGB,
without an alpha channel). Root independently inspected its actual character/UI
pixels after
the initial metadata packet was written. This was the root's tool-triggered
original button control; no physical-user test or human-origin activation is
claimed. It supports the existing production button in this bounded current
top-level test. It does not identify why the instrumented iframe attempts lacked
observed downloads.

### Automatic A/B/D iframe attempts

Primary packets:
[`export-A-final-records.json`](../../docs/evidence/bounded-startup-capture/export-A-final-records.json),
[`export-B-final-records.json`](../../docs/evidence/bounded-startup-capture/export-B-final-records.json),
[`export-D-final-records.json`](../../docs/evidence/bounded-startup-capture/export-D-final-records.json).

Each packet records `hooks-ready` before a blob, anchor click, revoke request,
and actual revoke. The automatic anchor attempts occurred 15936.8, 15909.4,
and 15949.4 ms after probe installation for A, B, and D respectively. These
are the probe's elapsed times, not Rust readiness or first-presentation times.
Each anchor named `nvwa-web-benchmark.png`; each canvas backing size was
1280×720. Automatic blob MIME type was empty and remains recorded as empty.
No downloaded PNG from those iframe attempts was available for independent
pixel inspection.

The observed automatic click activation was `isActive:false` and
`hasBeenActive:false`. B/D recorded the original unattached state, then the
probe's attached state at click. D's 1001.5 ms actual deferred revoke separates
timing from B's original immediate request. All three records retained
`durableFile:"NOT-VERIFIED"`.

The event packets record these waits:

| Packet | Wait start UTC | Wait completion UTC | Verdict |
|---|---|---|---|
| [`export-A-download.json`](../../docs/evidence/bounded-startup-capture/export-A-download.json) | 11:03:43.311 | 11:04:13.337 | No event within 30 seconds |
| [`export-B-download.json`](../../docs/evidence/bounded-startup-capture/export-B-download.json) | 11:05:48.986 | 11:06:19.018 | No event within 30 seconds |
| [`export-D-download.json`](../../docs/evidence/bounded-startup-capture/export-D-download.json) | 11:07:05.362 | 11:07:35.383 | No event within 30 seconds |

All dates above are `2026-10-12`. A/B/D each retained an actual Stop record;
the probe released its resources. The records do not prove teardown of the
root-owned server or browser.

### Original production explicit canvas button in iframe C

[`export-C-final-before-stop.json`](../../docs/evidence/bounded-startup-capture/export-C-final-before-stop.json)
records the original button event with `isTrusted:true` and active user
activation. The actual canvas request and callback also recorded active
activation. Root used its actual UI tool route; these observed fields do not
establish a human-origin click.

`toBlob` returned a real 325267-byte `image/png` blob. The attempted
`nvwa-web-canvas.png` anchor was originally attached and remained attached at
click; the production button removed it afterward. The production revoke
request followed about 1000 ms later, with actual URL lifetime 1004.6 ms.
No `toBlob-null`, `toBlob-error`, or anchor-click error is recorded for this
attempt. Successful adapter operations still did not establish a persistent
file.

[`export-C-download.json`](../../docs/evidence/bounded-startup-capture/export-C-download.json)
records no event in the 15-second wait from `11:08:19.013Z` through
`11:08:34.188Z`. The C frame also attempted the baseline automatic Bevy export
before the explicit click; that automatic attempt is distinct from C's canvas
attempt and does not share C's activation snapshot.

## Filesystem and console limits

Root's checks were narrowly scoped to `Downloads/nvwa-web*.png`, file metadata,
and current modification times. The root evidence shows the successful startup
2 benchmark PNG unchanged across the iframe observations and no new matching
current file. Earlier matching canvas files were excluded from current evidence
and are not asserted as results of these runs. This scope does not prove that
no file exists anywhere else, no host download-manager state changed, or no
later file could appear.

Console availability differs by run. Startup 2 retains the actual Rust callback
and asset-ready event described above.
[`startup-1-console.json`](../../docs/evidence/bounded-startup-capture/startup-1-console.json)
is empty. Separately captured Rust `ScreenshotCaptured`/`NVWA_EVIDENCE` console
events and exact asset-ready timestamps remain NOT-RUN for startup 1, the export
iframe cases, and the top-level explicit control. Their browser adapter records
and real-file observations must not be reported as additional captured Rust
callback console events. The initial startup-2 observation packet's unavailable
console-clock annotation was corrected, with the original claim retained in its
`reviewReconciliation` field. The raw console packet is unchanged. “Screenshot saved” text, blob bytes, and
anchor records are not persistent-file receipts.

## Interpretation and decision

The top-level baseline and the instrumented iframe cases differ in frame
context, instrumentation, and tool/download observation environment. Those
differences remain confounders. The experiment does not establish an ordinary
browser policy, a host download-manager cause, or a Bevy source defect.

Within the instrumented iframe runs, attaching the anchor alone did not produce
an observed event. Adding a 1000 ms revoke delay also did not produce an observed
event. The original explicit button had active activation and a real canvas
blob but likewise produced no observed iframe event. These bounded results do
not support attachment, immediate revocation, or inactive activation as an
isolated sufficient cause of the observed iframe outcome.

C changes encoding source, trigger, and activation in addition to attachment
and timing; it is not a one-variable comparison with automatic A. The successful
current top-level automatic path prevents claiming that the historical
top-level M0 missing-file fault was reproduced unchanged. Keep issue 5 as
bounded triage and retain the instrumentation separately. No product source,
dependency, or lockfile patch was made.

VERIFIED — root observed current top-level automatic and original explicit
downloads and independently checked their actual 1280×720 character PNGs;
actual iframe adapter records and bounded event timeouts are retained; five
synthetic lifecycle tests passed. Startup 2's Rust callback and asset-ready
event are captured on the stated Bevy clock. Top-level explicit PNG IHDR
verifies 1280×720, 8-bit RGB.
PARTIAL — iframe attempts had no download event/new matching file observed in
the recorded windows; exact cause and broader browser/host behavior remain
unverified.
NOT-RUN — separate Rust callback/asset-ready console events for startup 1,
export iframe cases, and the top-level explicit control; historical M0 fault
reproduction; ordinary-browser generalization; physical-user activation.

The two actual top-level controls succeeded while all four instrumented iframe
cases lacked observed download events in their respective windows. Differences
include iframe context, hooks, and the browser/tool download session or policy
boundary. They do not identify an exact host cause. Do not adopt B or D as a
product fix. Keep issue 5 OPEN for the original top-level missing-file cause;
the current run does not establish that cause or reproduce that fault unchanged.

Root reports all owned test tabs closed, IAB viewport override reset, and the
owned server processes exited with status 0. Retained evidence belongs to root
for review, sanitization, and publication. No worker-owned browser/server
resource remains.
