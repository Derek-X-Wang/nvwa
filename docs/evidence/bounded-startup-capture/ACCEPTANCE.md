# Bounded continuation: issue3 blocker, HTTP startup and screenshot export

2026-10-12, Codex Desktop on the local Mac. Base main `6b5cf8068fe5f859f82a1934bfedc8b224d49e20`. Root operated all browser/GPU cases, one renderer at a time. Two independent Sol workers implemented isolated experiments24/25; root owns integration. No product source, Cargo.lock or dependencies changed.

## What this establishes

- **#3 remains blocked/open.** Current IAB capabilities are visibility and width/height-only viewport. Original DPR emulation remains unavailable; original criteria stay intact. [Exact API](iab-viewport-api.txt), [capability list](iab-capabilities.json), [bounded exit](issue3-blocker.md). Prior accepted ordinary/fixed-CSS controls were not repeated.
- **#4: HTTP-cache boundary verified in two actual startups.** Fresh run-scoped URLs and no-store responses transmitted the frozen JS/Wasm/GLB bytes. Actual character/Ready UI pixels were inspected. These are HTTP-cache controls, not fully cold browser/GPU/OS/shader runs.
- **#5: current top-level automatic and explicit downloads both persist.** Actual1280×720 PNGs contain the rendered character/UI. Instrumented iframe A/B/D/C produced real export attempts but no observed download event/new matching file in the bounded windows. Mounting the anchor and delaying revocation did not improve those iframe results; no product workaround selected. The original top-level M0 failure cause remains unknown.

## Actual startup measurements

| Observation | Startup1 | Startup2 | Meaning |
|---|---:|---:|---|
| Boot status hidden |517.5ms|634.4ms|Navigation clock, observed production init return; not asset readiness or first frame|
| GLB HTTP response end |936.6ms|1100.8ms|Navigation Resource Timing, not GPU upload or presentation|
| Five critical HTTP bodies |20,564,428bytes|20,564,428bytes|Wrapper, passive collector, JS, Wasm and one GLB; excludes HTTP headers|
| Optional missing `.glb.meta` |404,28bytes|404,28bytes|Explicitly reported Bevy default-metadata fallback; critical GLB remains200|
| Actual geometry |1280×720,DPR1|1280×720,DPR1|CSS viewport, canvas CSS and backing1280×720|
| First asset readiness |NOT-RUN console observation|0.4248s|Bevy clock since first update; excludes earlier HTML/Wasm startup|
| Screenshot callback |NOT-RUN console observation|15.4457s|Same Bevy clock; includes requested15s warmup; not exact first presentation|

Both passes reconcile one navigation plus four resource entries, positive transfer sizes, exact response/body hashes and one actual critical GET per member. The verifier initially rejected the optional metadata404; [actual RED and GREEN](../../../experiments/24-http-cold-startup/REPORT.md) are preserved. Installed Bevy source establishes the narrow fallback; unexpected404/critical GLB404 still fail. Browser timing and server socket-write bytes are separately labelled.

The actual IAB user agent reports Chrome155.0.0.0. Installed external Chrome154.0.8037.97 in environment-before.json was not the tested browser. OS is macOS27.0.1/build26A434. No compilers or competing native Nvwa renderer were present in the selected process inventories; other user apps, OS/GPU caches and observer overhead were not controlled. Root kept only one task-owned browser renderer open.

Startup1's initial combined tool call timed out/reset the tool kernel after navigation had landed. Root recovered existing tab43 without replaying the single-use navigation. Its passive timing capture remained available and passed the same reconciliation; its automatic-download observation is NOT-RUN. This tool timeout is not an application startup timeout. Startup1's console capture is empty. Startup2's [raw console](startup-2-console.json) contains an actual `NVWA_EVIDENCE` record, preserved in [an attributed extraction](startup-2-runtime-evidence.json). Its asset readiness and screenshot callback use `bevy_TimeReal_since_first_update`, separate from the navigation clock. Callback success alone does not establish file persistence; the actual download/file evidence does. Independent review caught and corrected the earlier blanket empty-console claim; raw console captures were preserved.

## Actual screenshot outcomes

| Case | Actual observation | Conclusion |
|---|---|---|
| Top-level automatic, startup2 |[PNG](startup-2-auto.png),304648bytes; file modified inside the event wait|Durable real1280×720RGB image verified|
| A iframe: original unattached/immediate revoke |304792-byte runtime blob; no event in30s total listener window|Bounded non-observation|
| B iframe: attached/immediate revoke |304852-byte runtime blob; no event in30s total listener window|Attachment alone did not improve this case|
| D iframe: attached/delayed revoke |304732-byte runtime blob; revoke1001.5ms after request; no event in30s total window|Delay did not improve this case|
| C iframe: original explicit button |325267-byte real canvas PNG blob; attached anchor; active/trusted tool event; no event in15s total window|Export attempt is not durable-file proof|
| Top-level explicit original button |[PNG](export-top-explicit.png),324903bytes; current file/event within recorded wait|Durable real1280×720RGB image verified|

All iframe hooks precede real export attempts. Wait windows start before the trigger; they are **not durations measured from a Rust callback**. Filesystem observations cover only task filename prefixes in Downloads, not global or permanent file absence. No JavaScript or log-only outcome is reported as durable success. Root separately inspected both actual downloaded PNGs; offline verification checks PNG structure and exact bytes.

Iframe, instrumentation, top-level routing and download-session/policy differences remain confounded. The current successful top-level baseline does not reproduce the historical top-level failure. Source points to Bevy's unattached anchor/immediate revoke, but B/D evidence does not support choosing either as a fix. Scope remains [experiment25](../../../experiments/25-screenshot-export/REPORT.md); tool clicks are not physical-user tests.

## Reproduction and current limits

```sh
python3 -B -m unittest discover -s experiments/24-http-cold-startup -p 'test_*.py' -v
node --test experiments/25-screenshot-export/export-probe.test.cjs
python3 -B docs/evidence/bounded-startup-capture/verify.py
```

For fresh actual runs, use [experiment24 README](../../../experiments/24-http-cold-startup/README.md) and [experiment25 README](../../../experiments/25-screenshot-export/README.md). Servers are loopback-only on reserved9201; close other renderers/heavy tasks. These reproduction commands are not claims that more browser runs occurred.

[Artifact reuse](artifact-reuse.json) checks all31 accepted production inputs and retained native/Web identities. Rust tests/builds and native runtime were **not repeated** in this attempt; earlier103-test/dual-target acceptance stays tied to its prior evidence. No inference, paid API/cloud, public deployment or hosted CI ran.

NOT-RUN — original IAB DPR trigger/cause, physical display transition; exact first presentation, fully cold browser/GPU/OS/shader startup, startup1 Bevy console milestones, per-iframe and explicit-button Rust callback console observations, browser/GPU memory/timestamps, native startup attribution and other platforms. #3/#4/#5 stay OPEN.

[Cleanup](cleanup.json) is root-observed: all owned tabs closed, IAB temporary viewport reset, both owned server sessions exited0, port9201 no longer listened. Downloads and private captures retained. Primary checkout and existing cache symlinks preserved.

PARTIAL — two actual no-store Web startups and two durable actual PNG downloads verified; original reproduction, full cold/presentation/memory boundaries and iframe cause remain unverified.
