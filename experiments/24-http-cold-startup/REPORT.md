# Bounded HTTP-cache startup result (#4)

Both startup HTTP reconciliations passed against the parent-owned actual browser
captures and server log. Process inventory and independent screenshots
remain parent-owned. The
prepared experiment does not modify production HTML, JS, Wasm or assets.

VERIFIED — 11 CPU tests passed. The tests exercise actual temporary
loopback HTTP responses and response logs, conditional-cache bypass, exact
gzip/identity bytes, unique startup prefixes, traversal/private/symlink refusal,
changed frozen bodies and rejection of malformed timing, missing Wasm/GLB,
failed/304/cached responses and wrong hashes. They are fixture evidence, not
browser or GPU evidence. Three additional tests use a sanitized actual startup1
timing/request fixture. The acceptance test failed before the narrow metadata
exception and passed after it. Mutating actualGLB status to404 or adding an
unexpected404 remains a failure. Failed/cached/corrupt metadata also fails.
`actual-metadata-fixture-red.log` and `cpu-tests.log` retain the red/green evidence.

VERIFIED — Each startup has five exact200 no-store critical response bodies,
one navigation entry and four positive-transfer resource entries. Critical
response bodies total20,564,428bytes. One optional metadata404 adds28bytes,
for total20,564,456server body bytes. Actual startup1 geometry reports1280x720
CSS viewport and canvas with DPR1; startup2 reports the same geometry.
Boot-status hidden was observed at517.5ms in startup1 and634.4ms in startup2
on their separate navigation clocks; GLB response completion is936.6ms and
1100.8ms respectively. These are observed
boundaries, not first presentation or AssetReady. Raw initial verifier exit2
is preserved in `actual-startup-1-verifier-red.log`; corrected reconciliation
is in `actual-startup-1-verifier-green.log` and
`actual-startup-2-verifier-green.log`.

NOT-RUN — Parent process inventory and actual
screenshot pixel visibility by this worker. Root owns the remaining actual
capture results. No compile, actual9201 listener,
browser operation, install or paid call was performed by this worker.

The initial failure was the optional
`assets/fixtures/nvwa-humanoid.glb.meta`404. Installed `bevy_asset0.19.1`
`src/io/wasm.rs:115,127-129` maps its404 to `NotFound`;
`src/server/mod.rs:1616-1628` selects loader default metadata, then1645 reads
the actual asset. Source hashes are in `bevy-meta-source-evidence.json`.
The checker permits only this exact absent sidecar with complete no-store
28-byte error body, and reports it in `optionalMissingSidecars`. ActualGLB200
remains required. No server or collector source changed during the actual run.
Startup1's saved console result is empty; its internal Bevy AssetReady and
screenshot callback fields remain NOT-RUN. Startup2's saved console contains
an actual `NVWA_EVIDENCE` record with `clock=bevy_TimeReal_since_first_update`,
`first_asset_ready_seconds=0.4248`, `capture_callback=true` and
`capture_callback_seconds=15.4457`. It reports `ready=true`, `error=null` and
`timeout=false`. These are internal Bevy observations, separate from the
navigation timings above. The callback follows the requested warmup; it is not
first presentation and does not establish browser download or file presence.
The raw console files remain unchanged.

The server records UTC and server monotonic request times, status, identity/
gzip encoding, declared size, body bytes written, exact body hash, no-store
header and interruptions. The read-only collector records navigation/resource
times and three browser size fields, observed hidden boot status and supported
milestone visibility. Frozen index hash and injected wrapper hash are recorded
separately in each server manifest. The original module body remains intact.

AssetReady remains the existing Bevy TimeReal clock since first update. It is
separate from navigation monotonic timing. Hidden boot status means production
init returned; it is not asset readiness or first presentation. Exact first
presentation is NOT-RUN. Screenshot completion at T is only a visible upper
bound. HTTP no-store with fresh prefixes does not prove browser, GPU, OS or
shader cold state. Browser timing entries with unavailable/zero transfer cannot
authorize the no-store transfer claim.
