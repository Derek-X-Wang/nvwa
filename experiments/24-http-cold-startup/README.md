# Bounded HTTP-cache startup experiment (#4)

This experiment serves frozen `dist/web` bytes on loopback port9201, with
`Cache-Control: no-store` on every response and a fresh URL prefix per startup.
It does not change production code or production `index.html`. The diagnostic
wrapper inserts one classic collector script into the frozen HTML head before
the original module. This adds measurable diagnostic startup overhead.

Only the frozen index, JS, Wasm, assets, works and licenses are eligible. The
index response is the injected wrapper. The collector is task-owned. The two
optional export routes read only `screenshot.html` and `export-probe.js` from
experiment25 at server creation; no other experiment file is exposed. Wasm/JS/
asset gzip responses use the existing `.gz` bytes, verified to decompress to
the exact identity hash. Changed files after freezing fail with409. No directory
listing, traversal, symlink escape, `.gz` direct route or general file endpoint
is provided. Evidence must be outside the HTTP root and must start empty.

From the integration checkout, first verify reserved port9201 is free using the
parent's process inventory. Preserve its before/after inventory with results.
Use a new private evidence directory chosen by the parent. To reserve six
prefixes (two startup cases and up to four export cases):

```sh
python3 experiments/24-http-cold-startup/server.py --runs 6 --evidence .work/bounded-startup-capture/http
```

The default is two prefixes. The hard maximum is six. The server prints exact
URLs and stores `manifest.json`, injected `wrapper.html`, collector bytes and
`requests.jsonl`. It binds only `127.0.0.1:9201`. Each `index.html` prefix accepts
one GET; a repeat returns409, so a reload cannot silently count as a new startup.
HEAD does not start a run. Server stop is Ctrl-C; keep the evidence directory.
Index response hashes and all frozen production source hashes are in the
manifest. Hashes of server source, collector and optional export files are also
recorded. Root must preserve its source/build cohort and process inventory
separately; these records do not prove which source produced Wasm.

The parent owns all browser/GPU operations. Use exactly two startup URLs, each
with `?benchmark=1` when collecting the frozen benchmark log. Measure the browser
viewport as1280x720 CSS pixels if supported; preserve the collector geometry
without equating canvas backing pixels to CSS size. Wait for actual resource
completion. When available, preserve the existing `NVWA_EVIDENCE` console
record (fixed15-second benchmark in the frozen build) for internal Bevy timing.
Startup1's saved developer-log result is empty despite the parent observing
actual Ready UI and character pixels. Startup2's saved console contains a real
`NVWA_EVIDENCE` record: `first_asset_ready_seconds=0.4248`,
`capture_callback=true`, `capture_callback_seconds=15.4457`, `ready=true`,
`error=null` and `timeout=false`. These seconds use
`bevy_TimeReal_since_first_update`; keep them separate from the navigation
monotonic clock. The screenshot callback follows the requested warmup and does
not identify first presentation or prove browser download/file presence.
Startup1's unavailable Bevy AssetReady and callback fields remain NOT-RUN.
The HTTP boundary
checker supports the no-store transfer result; independently inspected actual
screenshots support the visible Ready UI and rendered-pixel observation. Keep
those observations separate. Unavailable console evidence leaves Bevy
AssetReady clock and screenshot callback fields NOT-RUN for that run. It does not establish
their values or prove absence. Hidden boot status alone cannot authorize an
asset-complete capture or substitute for actual Ready pixels. Use a fresh prefix
for each startup.
Stop the performance phase after two actual startups. Run optional export cases
after that through `/run/<id>/screenshot.html?case=A` etc. Those cases do not count
as additional startup performance evidence. They are owned by experiment25.

Read-only browser export:

```js
JSON.stringify(window.nvwaStartupDiagnostics.snapshot())
// Or read DOM text; updated every250ms for120seconds:
document.getElementById('nvwa-startup-json').textContent
```

Save the actual result as `<run>-browser.json`. The collector records Navigation
and Resource Timing, transfer/encoded/decoded sizes, supported entry types,
optional paint entries, measured geometry and observation of hidden boot status.
It does not wrap `fetch`, console, WebGPU or Wasm. It does not write canvas,
input or production state. Reads of the snapshot API do not publish a new DOM
state. Timer sampling and passive observation add diagnostic overhead.

Validate each actual startup (replace RUN with the exact32hex token):

```sh
python3 experiments/24-http-cold-startup/verify_capture.py --capture .work/bounded-startup-capture/http/RUN-browser.json --manifest .work/bounded-startup-capture/http/manifest.json --requests .work/bounded-startup-capture/http/requests.jsonl --run RUN
```

The checker requires one actual200 GET and one positive-transfer timing entry
for index, collector, JS, Wasm and GLB. Every matched GET must have no-store,
complete body writes and the frozen identity/compressed body hash. It rejects
missing or duplicated critical entries,304, interrupted/failed bodies, zero
transfer timing, wrong size/hash, malformed timing and mixed clocks. PASS only
supports this HTTP boundary. No cached fallback is accepted as proof. Server
body bytes mean successful socket writes, exclude headers and do not alone
prove client receipt. The browser timing and exact body match provide the
separate client observation. Source31match and independent actual PNG presence
checks belong to the parent report.

One exact optional missing response is explicit in verifier output:
`assets/fixtures/nvwa-humanoid.glb.meta`404. Installed `bevy_asset0.19.1`
primary source constructs this metadata URL, maps404 to `NotFound`, selects
the loader's default metadata and then reads the actual GLB. The exception
requires absence from the frozen manifest, no-store and the complete exact
28-byte missing response. The GLB still requires actual200 and matching timing.
Unexpected404, GLB404, metadata500 and missing frozen metadata remain failures.
`optionalMissingSidecars` lists this response separately; its body is included
in total server bytes. It has no resource-timing transfer claim. See
`bevy-meta-source-evidence.json` for installed source hashes and line boundaries.

AssetReady uses `bevy_TimeReal_since_first_update` in the existing benchmark
evidence. Navigation timing uses monotonic milliseconds since `timeOrigin`.
Keep both clocks separate. Neither boot-status hiding nor Paint Timing proves
the first WebGPU frame. A screenshot completed at T may prove that actual
pixels were visible by T; it is a visible upper bound, not first presentation.
Exact first presentation remains NOT-RUN. No browser/GPU/OS/shader cold claim
is supported by no-store plus fresh URL prefixes.

CPU verification (fixtures only; the temporary HTTP test binds an ephemeral
loopback port and closes it; it never starts the experiment listener):

```sh
python3 -m unittest discover -s experiments/24-http-cold-startup -p 'test_*.py' -v
```

Keep captures private until the parent sanitizes publication. Do not publish
unrelated `dist/web` files, private process details or captured browser data.
