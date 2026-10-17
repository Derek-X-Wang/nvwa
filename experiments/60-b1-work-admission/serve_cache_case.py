#!/usr/bin/env python3
"""Loopback HTTP-cache test harness; never changes the input Web bundle."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path, PurePosixPath
import shutil
import threading
from urllib.parse import unquote, urlsplit

B1_PREFIX = "/assets/characters/mpfb-b1-v1/"
FAULT_PATH = B1_PREFIX + "rig.game_engine.json"
ASSET_ID = "mpfb-hm08-game-engine-female-sportsuit01-v1"
CACHEABLE = "public, max-age=3600"
NO_STORE = "no-store"

PROBE_HTML = rb'''<!doctype html>
<html lang="en"><meta charset="utf-8"><title>B1 HTTP cache probe</title>
<style>body{font:16px system-ui;max-width:52rem;margin:3rem auto;padding:1rem}button{font:inherit;padding:.7rem}pre{white-space:pre-wrap}</style>
<h1>B1 HTTP cache probe</h1>
<p>This page warms input bytes only. It does not render or test the Nvwa application.</p>
<button id="warm">Warm approved assets</button>
<pre id="status" role="status">Ready. Set fault mode to none. Click twice, then inspect the server log.</pre>
<script>
const prefix = '/assets/characters/mpfb-b1-v1/';
const assetId = 'mpfb-hm08-game-engine-female-sportsuit01-v1';
const status = document.getElementById('status');
const button = document.getElementById('warm');
let completedBatches = 0;
async function ordinaryFetch(path) {
  // Deliberately use the browser's ordinary HTTP cache. No busting or custom headers.
  const response = await fetch(path, {cache: 'default'});
  if (!response.ok) throw new Error(`HTTP ${response.status} for ${path}`);
  return response;
}
button.addEventListener('click', async () => {
  button.disabled = true;
  status.textContent = 'Warming approved input bytes with default-cache fetch...';
  try {
    const response = await ordinaryFetch(prefix + 'manifest.json');
    const manifest = await response.json();
    if (manifest.format !== 'nvwa-b1-assets' || manifest.schema_version !== 1 ||
        manifest.asset_id !== assetId || !Array.isArray(manifest.files) || manifest.files.length !== 13) {
      throw new Error('Unexpected approved asset manifest identity or file count');
    }
    const seen = new Set();
    for (const file of manifest.files) {
      if (typeof file.path !== 'string' || !file.path || file.path.startsWith('/') ||
          file.path.includes('\\') || file.path.split('/').some(part => part === '..' || part === '.' || !part) ||
          seen.has(file.path)) throw new Error('Unsafe or duplicate manifest path');
      seen.add(file.path);
      const data = await (await ordinaryFetch(prefix + file.path)).arrayBuffer();
      if (data.byteLength !== file.bytes) throw new Error('Unexpected input byte length: ' + file.path);
    }
    completedBatches += 1;
    status.textContent = `PASS: 14 responses consumed (manifest + 13 files). Completed batches: ${completedBatches}.\n` +
      'HTTP-cache reuse requires server-log evidence; this page does not infer network freshness or Nvwa acceptance.';
  } catch (error) {
    status.textContent = 'FAILED: ' + String(error);
  } finally { button.disabled = false; }
});
</script></html>'''


class FaultStateError(ValueError):
    """The root-controlled fault file cannot safely select a response mode."""


def read_fault_state(path: Path) -> str:
    try:
        with path.open("rb") as stream:
            data = stream.read(4097)
        if len(data) > 4096:
            raise FaultStateError("fault state exceeds 4096 bytes")
        state = json.loads(data)
        if not isinstance(state, dict) or set(state) != {"mode", "path"}:
            raise FaultStateError("fault state requires exactly mode and path")
        if state["mode"] not in ("none", "missing", "corrupt") or state["path"] != FAULT_PATH.removeprefix("/"):
            raise FaultStateError("unsupported fault state")
        return state["mode"]
    except (OSError, ValueError, TypeError) as error:
        raise FaultStateError("invalid or unavailable fault state") from error


@dataclass(frozen=True)
class Response:
    status: int
    cache_control: str
    content_type: str
    body: bytes | Path


def response_for(root: Path, request_target: str, mode: str) -> Response:
    """Select bytes for a request without binding a socket or changing a file."""
    if mode not in ("none", "missing", "corrupt"):
        raise FaultStateError("unsupported mode")
    path = unquote(urlsplit(request_target).path)
    cache = CACHEABLE if path.startswith(B1_PREFIX) else NO_STORE
    if len(path) > 4096 or not path.startswith("/") or "\\" in path or "\0" in path or ".." in path.split("/"):
        return Response(400, NO_STORE, "text/plain; charset=utf-8", b"Unsafe request path\n")
    if path == "/cache-probe.html":
        return Response(200, NO_STORE, "text/html; charset=utf-8", PROBE_HTML)
    if path == FAULT_PATH and mode == "missing":
        return Response(404, cache, "text/plain; charset=utf-8", b"B1 cache harness: missing input\n")
    if path == FAULT_PATH and mode == "corrupt":
        return Response(200, cache, "application/json", b"NVWA_B1_CACHE_PROBE_CORRUPT\n")
    relative = "index.html" if path == "/" else str(PurePosixPath(path).relative_to("/"))
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root.resolve()) or not candidate.is_file():
        return Response(404, cache, "text/plain; charset=utf-8", b"Not found\n")
    mime = "application/wasm" if candidate.suffix == ".wasm" else mimetypes.guess_type(candidate.name)[0]
    return Response(200, cache, mime or "application/octet-stream", candidate)


class CacheHarnessHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_args):
        # BaseHTTPRequestHandler otherwise prints client addresses to stderr.
        pass

    def do_GET(self):
        mode = "invalid"
        try:
            mode = read_fault_state(self.server.fault_state)
            response = response_for(self.server.bundle_root, self.path, mode)
        except (FaultStateError, OSError, ValueError):
            response = Response(503, NO_STORE, "text/plain; charset=utf-8", b"Cache harness configuration unavailable\n")
        path = unquote(urlsplit(self.path).path)
        row = {
            "time": datetime.now(timezone.utc).isoformat(),
            "path": path[:4096],
            "status": response.status,
            "requestCacheControl": self.headers.get("Cache-Control", "")[:256],
            "mutationMode": mode,
        }
        with self.server.log_lock:
            with self.server.log_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, separators=(",", ":")) + "\n")
        self.send_response(response.status)
        self.send_header("Cache-Control", response.cache_control)
        self.send_header("Content-Type", response.content_type)
        size = response.body.stat().st_size if isinstance(response.body, Path) else len(response.body)
        self.send_header("Content-Length", str(size))
        self.end_headers()
        if isinstance(response.body, Path):
            with response.body.open("rb") as stream:
                shutil.copyfileobj(stream, self.wfile)
        else:
            self.wfile.write(response.body)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--port", type=int, default=9275)
    parser.add_argument("--fault-state", required=True, type=Path)
    parser.add_argument("--log", required=True, type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    state = args.fault_state.resolve()
    log = args.log.resolve()
    if not root.is_dir() or not (root / "index.html").is_file():
        parser.error("--root must be an existing Web bundle containing index.html")
    if not 1024 <= args.port <= 65535:
        parser.error("--port must be between 1024 and 65535")
    if not log.parent.is_dir() or log.is_relative_to(root) or state.is_relative_to(root):
        parser.error("fault state and log must be outside the input bundle, with an existing log parent")
    try:
        read_fault_state(state)
    except FaultStateError as error:
        parser.error(str(error))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), CacheHarnessHandler)
    server.daemon_threads = True
    server.bundle_root = root
    server.fault_state = state
    server.log_path = log
    server.log_lock = threading.Lock()
    print(f"Loopback cache harness ready: http://127.0.0.1:{args.port}/cache-probe.html", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
