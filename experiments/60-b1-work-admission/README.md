# Loopback B1 HTTP-cache harness

This harness serves an existing actual Nvwa Web bundle. It does not build, start or validate the Rust application, and it creates no character graphics or substitute evidence. The root task controls the browser, server process and fault-state file. The harness never changes the input bundle and has no HTTP mutation API.

Run from the repository root, substituting existing task-owned paths. Keep fault state and log outside the bundle. The file must have exactly these two fields; the only allowed target is the approved rig input:

```sh
printf '%s\n' '{"mode":"none","path":"assets/characters/mpfb-b1-v1/rig.game_engine.json"}' > TASK_FAULT_JSON
python3 -B experiments/60-b1-work-admission/serve_cache_case.py \
  --root EXISTING_WEB_BUNDLE --port 9275 \
  --fault-state TASK_FAULT_JSON --log TASK_HTTP_JSONL
```

The server binds only `127.0.0.1`. Stop it with Ctrl-C when the bounded check ends. It prints no client addresses and logs no hostnames or query strings. Every GET appends a JSON line with `time`, `path`, `status`, `requestCacheControl` and `mutationMode`. The passed log is the only file the server writes. Invalid/unavailable fault state returns HTTP503 with `Cache-Control: no-store`; it never silently selects normal mode. Use an atomic root-controlled file replacement when changing state.

All responses beneath `/assets/characters/mpfb-b1-v1/`, including the manifest and injected404/corrupt responses, have `Cache-Control: public, max-age=3600`. Index, code, Wasm, the probe page and other files have `Cache-Control: no-store`. No cache-busting URL, service worker, JavaScript cache store or custom warmup request header is used. Default browser HTTP-cache behavior is the subject of this check.

1. With mode `none`, open [the cache probe](http://127.0.0.1:9275/cache-probe.html). Do not enable DevTools “Disable cache” or force reload during the cache test. Click **Warm approved assets** once. The page consumes the manifest and thirteen raw files using `fetch(..., {cache:'default'})`. It validates the fixed asset ID/count and byte lengths, then reports **14 responses consumed** in the status DOM.
2. Record the log boundary, then click the same button a second time. Require another fourteen successful browser responses and **zero new GET rows for the manifest/thirteen raw inputs**. Other requests such as favicon are separate. The DOM message alone does not prove cache reuse; use the server log to establish that this browser cached the actual approved inputs. If the second batch reaches the server, warm-cache acceptance is unproven and must be reported as such.
3. Keep that browser/origin and warm cache. Change only the root-owned fault JSON to mode `missing`; keep the exact path. The target now returns404 with explicit public/max-age headers. Use the actual Nvwa Rust app to Open/New the B1 Work through its production no-store reader. Require a fresh target GET in the log and visible failure/preservation behavior in the actual app. A probe-page failure is not application proof.
4. Restore mode `none` through the root-owned file. Use the actual app's explicit retry/Open flow. Require a fresh target GET and successful real B1 fitting/upload/commit. Repeat the warmup and fault sequence with mode `corrupt` if separate corruption evidence is needed: this mode returns HTTP200 and deterministic wrong bytes. Retain app observations, server rows and Work preservation/recovery evidence together.
5. Stop the server. Restore mode `none` in the task file and retain the bounded log with the task's runtime evidence.

The warmup button performs one batch per click, so the operator's two clicks exercise the same ordinary HTTP-cache calls twice. It never states that a browser response came from memory/disk cache; the absence of corresponding server requests is the evidence. The actual app must still use its own no-store fetch, byte verification and failure path.

This proves behavior only for this loopback origin, browser session and served build. It does not establish CDN/production-origin freshness, proxy policy, service-worker behavior, clean-machine acceptance, GPU quality or model output.

Implementation verification is bounded to Python standard-library response selection, fault-file parsing, path containment, cache headers and syntax. The implementation worker does not start a socket server, UI, browser or renderer. Actual warm-cache and Nvwa runtime acceptance remain NOT-RUN until the root controller performs the steps above.

VERIFIED — Nineteen in-memory route/fault/actual HTTP-handler checks passed, including all three modes, cache headers, traversal rejection, invalid configuration rejection and GET log fields/query omission. Python parsing and the generated probe JavaScript's `node --check` passed. These checks did not bind a socket or start the application. Browser cache reuse and actual Nvwa recovery remain NOT-RUN.

A socket-free syntax check can be repeated with:

```sh
python3 -B - <<'PY'
from pathlib import Path
import ast, importlib.util, re, subprocess, sys
path = Path('experiments/60-b1-work-admission/serve_cache_case.py')
ast.parse(path.read_text())
spec = importlib.util.spec_from_file_location('cache_case', path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
script = re.search(rb'<script>(.*?)</script>', module.PROBE_HTML, re.S).group(1)
subprocess.run(['node', '--check'], input=script, check=True)
print('PASS: Python and generated probe JavaScript syntax; no server started')
PY
```
