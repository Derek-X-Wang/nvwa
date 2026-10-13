# Bounded Web production-call and timestamp diagnostics (#4)

Prepared for root's exclusive GPU/UI lease. No browser, GPU, formal9201/9205
HTTP listener or new build has run during preparation. The actual ephemeral
CPU HTTP control listener ran, then closed with all owned threads joined. Only experiment34 and private
`.work/m11-perf/web/` are worker-owned. Root owns execution and publication.

The accepted Wasm is `d890dfee73e9eeeee6ce3d82f255c79979e8c8b6bed90243c6101f8e1c1763a8`.
The real humanoid is3,827,840bytes, SHA
`f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6`.
The exact common Work is1,624bytes, SHA
`ff0b8e36adfc3ebadc5fc700a4c760f6f551273b56e85bf336563e18b63eb445`,
revision0 and natural idle loop. The server reads that root-frozen file through
one named route; it never edits `dist/web`. Its response hash, byte count and
browser Resource Timing are reconciled. Runtime Ready/revision/clip confirmation
must come from the separate actual production `NVWA_EVIDENCE` log and pixels.

## Live adapter capability boundary

Worker independently ran `cua.getState()`, `cua.getBrowser({id:'2'})` and
`browser.capabilities.list()` under a read-only root lease, then released it.
Only IAB2 and MCP Apps1 were connected; both had no tabs. IAB browser capabilities
were exactly visibility and viewport. Browser docs support read-only page
evaluation, DOM text, console logs and screenshots. They provide no fresh
browser-process/profile creation, process attribution, tracing, memory or exact
physical presentation API. A running Chrome app does not prove a connected
Chrome adapter. The installed DevTools CLI help describes traces, heap snapshots
and isolated contexts, but no readiness call ran and this runtime prohibits
using a separate browser driver. It is not an available execution route.

Thus fully cold browser/Wasm compiler/shader/driver/OS state, physical first
presentation, browser process RSS and total GPU memory remain NOT-RUN.
Fresh-prefix/no-store proves only the HTTP boundary. One same-URL reload is a
process/cache contrast whose HTTP responses still use no-store; it is not an
HTTP cache-hit benchmark. User apps and OS/driver caches remain uncontrolled.

## Two source variants

Baseline appends `gpu-boundaries.js` to a byte-identical copy of experiment24's
collector. Three hooks observe production `requestDevice`, `queue.submit` and
`getCurrentTexture`. They preserve actual arguments, receiver, return identity,
promise identity and thrown objects. No extra device, adapter or submission is
requested. Device enabled features and first API-return CPU boundaries are
recorded. Queue submit return may describe upload/offscreen commands; texture
acquisition is not presentation. Optional `performance.memory` is only a coarse
or shared JS heap subset. It is not browser RSS, complete Wasm or GPU memory.

Optional `--timestamp-variant` also appends `timestamp-variant.js`. This is an
instrumented device/pass/encoder variant, not unchanged production. If the
production-called adapter supports `timestamp-query`, it clones the device
descriptor to request the feature. It adds `timestampWrites` to up to32 actual
production render/compute passes over up to8 actual encoders, leaving existing
timestamp descriptors alone. It appends resolve/copy commands before production
`finish`, and reads submitted query results using `mapAsync`. There is no dummy
pass or extra queue submission. Results are separate unsigned64-bit nanosecond
timestamps and pass-duration differences; CPU map completion is not GPU duration.
The timestamp clock is not calibrated to navigation or native clocks. Values
have implementation-defined coarse precision, per the current
[WebGPU primary specification](https://gpuweb.github.io/gpuweb/#timestamp).
Raw source identity and bounded excerpts are private in
`.work/m11-perf/web/webgpu-primary-source.json`.

The timestamp feature-unavailable path forwards the original descriptors and
records NOT-RUN. Actual feature support is learned only from the production
request. Validation/device-loss/map errors are retained and prevent a success
status. Diagnostic query/readback objects are destroyed after map completion or
map failure. Each encoder's added buffers are512bytes each, plus its query set;
these allocated bytes do not describe total GPU memory. The variant can perturb
startup and measured workload; compare it separately from baseline.

## Root execution, maximum3 total navigations

Root first stops competing task-owned builds/renderers and grants exact9201 or
9205 ownership. Root inventories the chosen port before and after. Start a
baseline server using a new empty private evidence directory:

```sh
python3 experiments/34-web-cold-metrics/server.py --port 9205 --runs 1 --evidence .work/m11-perf/web/baseline-http
```

The server prints exact PID and URL. Use the printed URL with
`?benchmark=1&work=works/perf-character-loop.nvwa.json`,1280×720/DPR1.
The baseline first prefix permits exactly one same-URL contrast reload. Every
HTTP row has `attempt`1 or2. Preserve baseline pixels/logs/receiver before reload.
The frozen benchmark still requests15s readiness warmup before its screenshot
callback; that callback is not first frame. Root's actual screenshot timing is
an independent visible upper bound, not exact first display.

At30s the collector emits `NVWA_WEB_PERF <raw JSON>` and POSTs the same bounded
payload to its exact same-origin `capture.json` route. The receiver requires
matching Origin, an active prefix, JSON schema/run identity, Content-Length
1..512,000, no chunked body, and an exclusive new evidence file.
Only one Origin and Content-Length header is accepted. A5s socket-read timeout
and total5s request deadline apply before headers/body are read. Partial body
timeouts return408 and are recorded in `receiver.jsonl`; unknown errors remain
visible and propagate. At most16 handlers and256 accepted requests are allowed.
The deadline timer also bounds trickled input; handler and timer threads join
when the exact owned server closes. The receiver saves
`<run>-attempt1-browser.json` or attempt2. No download is used for this collector.
The final hidden DOM record is `#nvwa-web-perf-json`. Its posted snapshot is
captured before the diagnostic POST; calling the snapshot API later includes
that additional resource and is not the canonical HTTP reconciliation input.

After baseline and contrast, root stops the listener and starts at most one
timestamp variant in a new directory, with `--runs 1 --timestamp-variant`.
It does not permit a repeat index GET. Total browser navigations across both
listeners must be at most3; root owns that combined run bound. Never run two
renderers or build during formal measurement.

Reconcile a posted payload:

```sh
python3 experiments/34-web-cold-metrics/check_metrics.py --capture CAPTURE --manifest MANIFEST --requests REQUESTS --run RUN --attempt 1
```

Use attempt2 for the same-URL contrast. Exact input/body/source identities,
actual production hooks/milestones, resource sizes, one actual Work response,
clock domains and geometry are required. The retained experiment24 checker is
reused on a transparent copy with9205 URLs normalized to its fixed9201 port;
the actual origin is checked first and the result reports actualPort.
No cached fallback, missing milestone or claimed physical display is accepted.

Root retains exact screenshot hashes, actual Ready UI/character inspection,
production logs, source/build cohort and app/tab/viewport lifecycle separately.
Root closes created tabs, resets its viewport override and stops only the exact
task-owned server PID. The worker created no tab/process/listener in preparation.

## CPU verification only

```sh
python3 -m unittest discover -s experiments/34-web-cold-metrics -p 'test_*.py' -v
node experiments/34-web-cold-metrics/test_wrappers.mjs
```

Seventeen pure-data/no-socket controls exercise valid frozen-body reconciliation
and reject missing milestones, mixed/future clocks, false display claims,
uninstalled hooks, wrong Wasm/GLB/Work identity/size/body/query, collector source,
origin, physical size and hidden/missing timestamp variants. The Node VM uses
fake API objects to exercise production-call forwarding, return/throw/promise
identity, descriptor immutability, actual-method hook paths, unavailable-feature
fallback, bounded query collection, fake tick arithmetic and resource cleanup.
These are helper controls; they do not prove a browser or GPU measurement.

An eighteenth real ephemeral-loopback HTTP control sends an oversized body
declaration, wrong Origin, empty body, deliberately partial body that reaches408
after5s, truncated EOF body, and then a valid capture that reaches201. Rejected
cases create no capture file. It verifies all owned listener/handler/deadline
threads join. This CPU helper briefly binds an OS-assigned loopback port and
never starts the formal9201/9205 listener, browser or GPU.

VERIFIED — CPU controls and current frozen input hashes; live child Cua inventory.

NOT-RUN — all runtime measurements pending root leases; exact physical display,
fully cold domains, browser process memory and total GPU memory unavailable.
