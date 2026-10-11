# Web startup bootstrap boundary

This diagnostic runs the existing release JavaScript and Wasm files. It adds a
separate HTML bootstrap. It does not change Rust, generated JS, Wasm, fixtures,
the document, or the app's benchmark logic. It provides read-only DOM evidence
for a browser controller that cannot evaluate Performance APIs directly.

The source inspection at `4b9ba411b88d2f6f6dba90bba1c2760bface2237` confirms:

- `benchmark=1` sets physical 1280×720, scale factor 1, and continuous updates.
- `player=1&work=works/m1-sequence.nvwa.json` opens the existing one-character
  sequence, rather than the Studio empty state. Confirm the actual fixture and
  document hash in the selected served bundle before running.
- The benchmark waits 15 seconds after Rust readiness, requests a screenshot,
  then logs `NVWA_EVIDENCE` through `console.log`. Its clock is Bevy
  `Time<Real>` since the first update. It times out after 60 seconds of that
  clock. The Web screenshot callback does not verify a saved download file.
- The probe checks the same WebGPU capability before dynamic import. The
  original HTML uses a static import, so import ordering differs. This probe
  measures its own bootstrap boundary; it is not untouched `index.html` timing.

## Prepare without a build

The integration owner controls browser/GPU use. Pause other GPU-heavy work and
reserve that slot before opening the page. Set `nvwa_bundle` to the already
verified release bundle. Do not rebuild to add this diagnostic.

```sh
nvwa_probe=/Users/derekxwang/Development/incubator/Nvwa/nvwa/experiments/14-web-startup
nvwa_bundle=/absolute/path/to/verified/dist/web
shasum -a 256 "$nvwa_bundle/nvwa_studio_bg.wasm"
# Required current SHA: 0d8e1b7907d82f1b6d7fbd9799d54bb90e2bdce9797979a4df06fdd9801cc93c
shasum -a 256 "$nvwa_bundle/nvwa_studio.js" "$nvwa_bundle/assets/fixtures/nvwa-humanoid.glb" "$nvwa_bundle/works/m1-sequence.nvwa.json"
cp "$nvwa_probe/startup-probe.html" "$nvwa_bundle/startup-probe.html"
shasum -a 256 "$nvwa_bundle/startup-probe.html"
```

Preserve the exact hashes and the full fixture hash beginning `f13e0189` from
the integration owner's verified fixture. Stop if any required input differs.
Copying the HTML must not alter or replace `index.html` or the current bundle.
For a standalone copy into the integration checkout, copy the whole
`experiments/14-web-startup` directory; no root file/dependency changes apply.

Use the existing experiment 9 loopback server for no-store responses and
compressed-body byte evidence. Root selects a free assigned port and a new log
file. The following `9202` is only an example; avoid a running experiment's port.

```sh
nvwa_repo=/absolute/path/to/integration/nvwa
nvwa_output=/absolute/path/to/new/run-evidence
mkdir -p "$nvwa_output"
python3 "$nvwa_repo/experiments/09-single-transfer/http_probe_server.py" \
  --root "$nvwa_bundle" --port 9202 --log "$nvwa_output/http.jsonl"
```

Run in a managed foreground terminal, or keep the exact PID if backgrounded.
The server binds only `127.0.0.1`. It has no app control endpoint. Before opening
the browser, inspect both identity and gzip-request headers. A HEAD request
without `Accept-Encoding: gzip` does not test the sidecar response branch:

```sh
curl -I http://127.0.0.1:9202/startup-probe.html
curl -I http://127.0.0.1:9202/nvwa_studio_bg.wasm
curl -I http://127.0.0.1:9202/assets/fixtures/nvwa-humanoid.glb
curl -I -H 'Accept-Encoding: gzip' http://127.0.0.1:9202/startup-probe.html
curl -I -H 'Accept-Encoding: gzip' http://127.0.0.1:9202/nvwa_studio.js
curl -I -H 'Accept-Encoding: gzip' http://127.0.0.1:9202/nvwa_studio_bg.wasm
curl -I -H 'Accept-Encoding: gzip' http://127.0.0.1:9202/assets/fixtures/nvwa-humanoid.glb
curl -I -H 'Accept-Encoding: gzip' http://127.0.0.1:9202/works/m1-sequence.nvwa.json
```

Require `Cache-Control: no-store` on each. For each existing sidecar, require
`Content-Encoding: gzip`, `Vary: Accept-Encoding`, and compressed `Content-Length`.
Preserve these headers. The Wasm input hash is the raw file hash. The server may
execute bytes decoded from a `.gz` sidecar, so raw-file hashes alone do not bind
the browser to the selected build. Reject every stale or mismatched sidecar.

Run this transport preflight before browser navigation. It checks **all** `.gz`
sidecars in the served bundle, not only Wasm. It binds each sidecar's decoded
SHA-256 and byte count to its raw file, then requests the raw URL with gzip
accepted. It checks HEAD/GET response headers and hashes the actual encoded GET
body, then decodes that body and verifies its raw identity again. For required
files without sidecars, it checks the identity response. The JSON preserves the
local raw/encoded hashes, actual response hashes, byte counts, and both headers.
It runs no app, compiler, or GPU work.

```sh
python3 - "$nvwa_bundle" "$nvwa_output/transport-preflight.json" http://127.0.0.1:9202 <<'PY'
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from urllib.parse import quote
from urllib.request import Request, urlopen

root = Path(sys.argv[1]).resolve(strict=True)
output = Path(sys.argv[2])
base = sys.argv[3].rstrip('/')
required = {'startup-probe.html', 'nvwa_studio.js', 'nvwa_studio_bg.wasm',
            'assets/fixtures/nvwa-humanoid.glb', 'works/m1-sequence.nvwa.json'}
sidecars = sorted(root.rglob('*.gz'))
paths = sorted(required | {str(p.relative_to(root))[:-3] for p in sidecars})
checks = []

def digest(stream):
    sha = hashlib.sha256()
    size = 0
    while chunk := stream.read(1024 * 1024):
        sha.update(chunk)
        size += len(chunk)
    return {'sha256': sha.hexdigest(), 'bytes': size}

def file_digest(path):
    with path.open('rb') as stream:
        return digest(stream)

def verify_headers(response, compressed, expected_bytes):
    assert response.status == 200, f'HTTP {response.status}'
    assert 'no-store' in response.headers.get('Cache-Control', '').lower(), 'Missing no-store'
    assert int(response.headers['Content-Length']) == expected_bytes, 'Content-Length mismatch'
    encoding = response.headers.get('Content-Encoding', '').lower()
    assert encoding == ('gzip' if compressed else ''), f'Unexpected encoding: {encoding}'
    if compressed:
        assert 'accept-encoding' in response.headers.get('Vary', '').lower(), 'Missing Vary'

for relative in paths:
    record = {'path': relative}
    checks.append(record)
    try:
        raw = root / relative
        sidecar = Path(str(raw) + '.gz')
        record['raw'] = file_digest(raw)
        compressed = sidecar.is_file()
        record['compressed'] = compressed
        expected_encoded = record['raw']
        if compressed:
            record['sidecar'] = file_digest(sidecar)
            with gzip.open(sidecar, 'rb') as stream:
                record['sidecar_decoded'] = digest(stream)
            assert record['sidecar_decoded'] == record['raw'], 'Sidecar/raw mismatch'
            expected_encoded = record['sidecar']
        url = base + '/' + quote(relative, safe='/')
        request_headers = {'Accept-Encoding': 'gzip'}
        with urlopen(Request(url, headers=request_headers, method='HEAD'), timeout=60) as response:
            record['head_headers'] = dict(response.headers.items())
            verify_headers(response, compressed, expected_encoded['bytes'])
        with tempfile.TemporaryFile() as body:
            with urlopen(Request(url, headers=request_headers), timeout=60) as response:
                record['get_headers'] = dict(response.headers.items())
                verify_headers(response, compressed, expected_encoded['bytes'])
                while chunk := response.read(1024 * 1024):
                    body.write(chunk)
            body.seek(0)
            record['served_encoded'] = digest(body)
            assert record['served_encoded'] == expected_encoded, 'Served encoded identity mismatch'
            body.seek(0)
            if compressed:
                with gzip.GzipFile(fileobj=body, mode='rb') as decoded:
                    record['served_decoded'] = digest(decoded)
            else:
                record['served_decoded'] = digest(body)
            assert record['served_decoded'] == record['raw'], 'Served decoded identity mismatch'
        record['status'] = 'passed'
    except Exception as error:
        record.update(status='failed', error=f'{type(error).__name__}: {error}')

failed = [record['path'] for record in checks if record['status'] != 'passed']
output.write_text(json.dumps({'bundle': str(root), 'base_url': base, 'checks': checks,
                              'failed': failed}, indent=2) + '\n')
if failed:
    raise SystemExit('Transport preflight failed: ' + ', '.join(failed))
print(f'Transport identities passed: {len(checks)} paths; {len(sidecars)} sidecars')
PY
```

Stop if this preflight fails. Freeze the bundle after it passes, including all
sidecars. Recheck raw/sidecar hashes against `transport-preflight.json` after the
measured run. A changed input invalidates the run's build identity.

These preflight GETs intentionally appear in the server log. Before browser
navigation, with no pending HTTP requests and no browser page open, move that
log to a separate file in the fresh run-evidence directory:

```sh
mv "$nvwa_output/http.jsonl" "$nvwa_output/http-preflight.jsonl"
```

The server opens its log path on each completed GET, so the next browser GET
creates a new `http.jsonl`. Do not overwrite an existing preflight log; each run
uses a new output directory. Only the new browser log enters measured transfer
counts. Preserve `http-preflight.jsonl` alongside the transport manifest. The
server log records response status, compression, and bytes written, not proof
of bytes received by the browser. Tie browser `content_encoding` and declared
compressed bytes to the validated manifest; resource metrics alone do not prove
an executable byte identity. Header-only checks use HEAD and add no GET count.

## One measured page load

Choose a unique `startup_probe_run` string, then navigate once to:

```text
http://127.0.0.1:9202/startup-probe.html?player=1&work=works%2Fm1-sequence.nvwa.json&benchmark=1&startup_probe_run=RUN_UNIQUE&startup_probe_cache=no-store-server-fresh-document-and-module-url
```

The run query makes this document and the dynamic JS import URL fresh. The
generated JS still locates the unchanged Wasm URL. The work/GLB URLs remain
unchanged and receive the server's no-store policy. Do not claim that these
conditions clear pre-existing browser, compiler, driver, or GPU caches. Do not
add cache-busting arguments to `work`: that query value is a validated static
document path, not an arbitrary URL. Repeating a run uses a new log and run ID.

Keep the page visible and focused until evidence arrives. Do not open a second
Nvwa/GPU page. The root browser controller may use its documented read-only DOM
evaluation to read the text of `#startup-probe-report`, not application globals.
The report is already computed by this page's own module. Preserve it as JSON
using root's normal local evidence-writing tools. This path remains usable if
the embedded browser does not save downloads.

Observe these UI elements:

- `#probe-summary`: evidence count, Rust readiness/mesh count, physical size,
  or recorded errors. Readiness text is still not character pixel proof.
- `#startup-probe-report`: full JSON, refreshed every 2 seconds for 75 seconds.
  It is in a collapsed `<details>` element and remains DOM-readable.
- **Download boundary JSON**: explicit export of the current report.
- **Download actual benchmark canvas PNG**: one user-activated `canvas.toBlob`
  capture. It reads the actual canvas. The page records request/callback times
  and Blob size, and attempts a download. It does not prove file persistence.

Wait for the existing Rust evidence and visually verify a real character. Read
the report and browser logs. Click the PNG button once, preserve the downloaded
PNG if the browser supports it, and inspect the pixels. Preserve a browser
screenshot through the controller's documented screenshot method as additional
visible evidence. Then read the report again to include the explicit capture.
Click JSON export if helpful, but do not rely on automatic download persistence
(issue #5). The boundary report retains raw and parsed `NVWA_EVIDENCE`.

Failure is evidence: preserve JSON, console logs, and server logs if capability
check, import, init, loading, screenshot, or evidence collection fails. A probe
that reaches the 75-second observation deadline without evidence is incomplete;
it is not a ready character result. Do not retry hidden expensive work in a loop.

## Metrics and claims

| Field | What it measures | Limit |
| --- | --- | --- |
| `navigation[]` | Browser navigation timing, document request/response, DOM events and size fields when exposed | Standard browser entries; no Rust/GPU clock alignment |
| `resources[]` | Resource start, response end, duration, sizes and exposed transport/cache fields | Delivery fields vary; zero transfer size alone does not prove a cache hit; observer capped at 512 entries |
| `paints[]` | Browser HTML first-paint/FCP when supported | Overlay text can produce FCP before character pixels |
| `probeScriptStartMs` | Instrumentation begins | Relative to document navigation `timeOrigin`, not OS process start |
| `capabilityAdapterRequestStartMs/EndMs` | Existing capability preflight adapter request | Does not measure the app's own device/queue/init or GPU work |
| `moduleImportStartMs/EndMs`, `moduleImportDurationMs` | Dynamic-import fetch, parse, evaluation and promise resolution | This is JS import, not Wasm compile or asset readiness |
| `initCalledMs/initResolvedMs`, `initDurationMs` | wasm-bindgen init promise wall duration, including its start entry | Includes multiple stages; no isolated Wasm compile or first frame claim |
| `firstCallbackAfterProbeScript` / `firstCallbackAfterInitResolved` | One `requestAnimationFrame` callback after each named boundary | No rendered pixels, GPU completion, or compositor presentation proof |
| `evidence[].observedAtMs` / `firstEvidenceObservedMs` | Console-log arrival on document clock | Delayed by the benchmark's 15-second warmup; not first readiness/pixels |
| Parsed `first_asset_ready_seconds` | Rust asset readiness on Bevy clock | Do not subtract directly from document-clock marks |
| Parsed `frame_ms_p50/p95` | Bevy main-loop cadence for recent ≤600 frames after readiness + 1 second | Not GPU duration or all-run frames; retained unchanged from existing evidence |
| Parsed `capture_callback_seconds` / `first_visible_upper_bound_seconds` | Existing screenshot callback after the requested 15-second warmup | Not first-presented frame; valid character-pixel upper bound only after its actual screenshot is preserved and inspected |
| `captures[].requestedAtMs/callbackAtMs/bytes` | Explicit one-shot PNG request/callback/Blob bytes | Pixel readback availability alone does not prove screen presentation or saved-file persistence |
| `visibility[]` | Focus and visibility at observed events | Background conditions can affect cadence; inspect before comparing runs |
| `canvas` and parsed `physical_window` | Canvas backing/CSS dimensions and Rust physical size | Require backing and Rust 1280×720, scale 1; CSS may differ |
| `serviceWorkerController` | Current page controller URL, if any | Active controller invalidates a simple direct-server assumption; check before treating HTTP counts as complete |

No automatic canvas readback runs during the benchmark. The page performs only
two diagnostic animation-frame callbacks. Passive observer, console interception,
and JSON refresh overhead exists and must be disclosed when comparing timings.
The renderer itself continues to run under the existing app benchmark policy.

Exact first screen presentation, isolated Wasm compilation, cold compiler/GPU
state, peak process/JS/GPU memory, and GPU timestamps are **NOT-RUN**. The probe
exports no application command/control/debug API. Do not add a placeholder
memory number or infer presentation from `getImageData`/`toBlob` readability.

## Cleanup and verification boundary

The observation timer disconnects observers, restores the original console.log
hook, removes diagnostic listeners, and stops JSON refresh at 75 seconds. Export
buttons still work. It does not stop the Rust renderer. Close the probe tab to
release its app resources. Stop only the exact server process for this run, and
remove the copied `startup-probe.html` from the served bundle. Preserve collected
evidence and input hashes. No files in the original bundle were replaced.

Worker validation is limited to source inspection and a JavaScript syntax
check. A real browser, WebGPU, Wasm initialization, document loading, character
pixels, measurements, and download persistence must be verified by the root's
reserved run. No build or GUI execution is part of this worker deliverable.
