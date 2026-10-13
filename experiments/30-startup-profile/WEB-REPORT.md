# Actual frozen baseline Web control — 2026-10-13

VERIFIED — the root's one actual browser run displayed the authentic humanoid,
Revision3 canonical Work and all three idle/wave/turn timeline segments. All
eight request-ledger rows reconcile with exact frozen/diagnostic response
hashes. Seven observed browser timing entries reconcile with that ledger.
The independent tab raster positive/mutant controls remain NOT-RUN.

This is baseline `045d8abc685760d09ba05afec0e40a811a282d1f`, Wasm SHA256
`884134fc98d54e3476dbc799ffdd5cc6b88f69121ddfb649ed9ba9be96156dba`.
The frozen Web bytes deliberately exclude the new #23 runtime guard and later
integrated source. They are a matching baseline Work control, not acceptance
of that new source. The root ran the eligible browser/server; this worker only
read the saved packet, inspected images, added the experiment30 reconciliation
adapter and ran pure-data controls. No GUI, listener, renderer or Cargo process
was started by this reconciliation work.

Exact URL:
`http://127.0.0.1:9203/run/a56982422eb74fe1997c0534723cadf4/index.html?benchmark=1&work=works/canonical-work.nvwa.json`.
The adapter strictly requires that origin, single run and canonical query.
The Work SHA256 is
`cacf849f0918648a1a970452d0c33f195c5ad89fd7f6d9e58669d587d0789768`:
schema1/revision3, four parameters at 0, idle/wave/turn at 0/3/6 seconds with
three-second durations. Actual Work identity and every frozen file/gzip pair
were rehashed. Archived experiment24 server, validators, collector and files
remain byte-for-byte unchanged.

## Every request accounted for

All rows are complete GET responses with `Cache-Control: no-store`. Six
successful run responses write 20,564,953 body bytes. The two explicit 404
responses add 47 bytes, for 20,565,000 total ledger body bytes. Successful socket
writes exclude HTTP headers and are not a measurement of client receipt.

| Member | Status | Ledger body bytes | Browser encoded | Browser decoded | Browser transfer |
| --- | ---: | ---: | ---: | ---: | ---: |
| Wrapped index.html | 200 | 2741 | 2741 | 2741 | 3041 |
| startup-diagnostics.js | 200 | 4756 | 4756 | 4756 | 5056 |
| nvwa_studio.js (gzip) | 200 | 19076 | 19076 | 123623 | 19376 |
| nvwa_studio_bg.wasm (gzip) | 200 | 19408774 | 19408774 | 85605074 | 19409074 |
| /favicon.ico | 404 | 19 | 19 | 19 | 319 |
| Canonical Work (gzip) | 200 | 525 | 525 | 1942 | 825 |
| Optional GLB metadata | 404 | 28 | unavailable | unavailable | unavailable |
| GLB (gzip) | 200 | 1129081 | 1129081 | 3827840 | 1129381 |

The seven browser entries report encoded 20,564,972 bytes, decoded 89,565,995
bytes and transfer 20,567,072 bytes. Their encoded sizes match the seven exact
ledger bodies. The 28-byte optional metadata response has no browser timing
entry and remains counted in the ledger; no transfer size is fabricated for it.
Browser `transferSize` is browser-reported and is not wire packet capture.
The resource collector reports zero dropped/over-limit/buffer-full entries.

The sole root-level favicon request is exactly `/favicon.ico`, runId/member
null, status404, identity encoding, no-store, complete19-byte body
`unknown run prefix\n`, SHA256
`653f5a345bb652f55d72b94e1b20fc9f66c765e26fe2d5d1d0a58d0a4ca41d08`.
The adapter invokes the unchanged experiment24 pure response method for this
exact path, without constructing a server or binding a listener. This is a
validated response disposition, not an omitted arbitrary failure.

The optional sidecar is exactly the matching run's
`assets/fixtures/nvwa-humanoid.glb.meta`, absent from the frozen manifest,
status404, identity encoding, no-store, complete28-byte
`not a served runtime member\n`, SHA256
`ba61c833937fda50c6346acd88aea1a26bdf5b45db3561202aa16e4f91bd19a2`.
The existing Bevy0.19.1 metadata fallback rationale is preserved. The actual
GLB200 response remains separately required. Any extra/duplicated request,
other failure, bad hash/status/run/Work, incomplete body, or timing mismatch
fails the new reconciliation.

## Actual pixels and separate clocks

The saved canvas PNG is RGB8, 1280 × 720, 334663 bytes, SHA256
`0699827d34ae7e4db3bdf159dbe174bd85f272d48b5b1fe85a59e06b16a32223`.
Both `canvas-download.png` and root Cua `screen.jpg` were independently viewed.
They show the actual humanoid, editor, Revision3 and three timeline rows. This
positive Web observation does not explain the earlier failed native content,
nor prove an independent tab paint-mutation control.

Browser timing uses Performance milliseconds from navigation timeOrigin.
The collector ended at 120058.7 ms. Boot status hidden was observed at 590.6 ms;
first-paint/contentful-paint entries are 140 ms. Wasm responseEnd is 329.1 ms and
GLB responseEnd 1033.8 ms. These are HTTP/DOM/page observations, not the first
WebGPU character presentation. The raw collector visibility field predates
the later screenshot and says actual pixels NOT-RUN; the separate later images
now establish actual visible content, not exact first presentation.

Console `NVWA_EVIDENCE` uses Bevy `Time<Real>` from first update. It reports
ready/error-null, asset-ready 0.3908 seconds, capture callback 15.416 seconds,
Revision3, timeline3, 9 meshes, 9 skins and 18 joints. The finite timeline completed
at position 9 with playing=false. Its recent 600 main-loop samples show
p50/p95 of 16.6/18.4 ms across 901 total loop frames. These are loop cadence,
not GPU timestamps or display-FPS acceptance. The console's fields named
`first_visible_*` still describe a readback callback; they do not timestamp
physical display.

Root Cua observation bounds are host wall-clock epoch milliseconds
1791886504221–1791886504350. These record a later screenshot request interval.
There is no verified conversion between host, navigation and Bevy origins.
Physical first presentation, browser/GPU/OS/shader cold state and total browser
or GPU memory remain NOT-RUN. Fresh URL prefix/no-store establishes the scoped
HTTP cache boundary only; existing browser/user caches were preserved.

## Reproduction and controls

Run from this isolated checkout, without a browser/server:

```sh
python3 -B experiments/30-startup-profile/reconcile_web_baseline.py \
  --packet .work/m11-startup/captures/web-baseline
python3 -B experiments/30-startup-profile/test_web_reconciliation.py
```

`WEB-RESULT.json` preserves exact packet/image/source hashes, full Bevy evidence,
counts, clocks and resource limits. `WEB-RECONCILIATION-CONTROLS.json` records
19 controls: actual packet green and 18 deliberate mismatches red, including
hash/status/run/Work, favicon hash/status/location/run/body, optional metadata,
missing browser Work and an arbitrary extra failure. The original24 validator
still rejects raw 9203; an owned temporary9201-normalized fixture still exposes
its existing favicon restriction. These original red controls are retained.
The new adapter normalizes only an internal copy of capture URL for the
unchanged finite-number/structure validator after strict 9203/Work checks;
original source and raw evidence are never rewritten.

An initial pure-response fixture omitted `export_diagnostics` and failed 15
controls with AttributeError. Initial source/receipt/failure are retained under
`.work/m11-startup/web-reconcile-initial/`; the repair added that fixture field
only in the new adapter. Final 19 controls passed in 2.814 seconds. No renderer
proof comes from those CPU controls; actual pixel evidence comes from the
root-collected images. Root owns server/tab closure and later #23 control.
