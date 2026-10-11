#!/usr/bin/env python3
"""Test-only loopback server for static Player fetch/error checks."""

import copy
import json
import mimetypes
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

HOST = "127.0.0.1"
PORT = 9202
STALL_SECONDS = 35
MAX_BODY_BYTES = 2 * 1024 * 1024 + 1
ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = (ROOT / "dist" / "web").resolve()
WORK_PATH = ROOT / "examples" / "m1-sequence.nvwa.json"
WORK_BYTES = WORK_PATH.read_bytes()
WORK = json.loads(WORK_BYTES)
if len(WORK_BYTES) >= MAX_BODY_BYTES:
    raise RuntimeError("M1 work fixture must be smaller than the oversized body limit")

INVALID_JSON = b'{"schema_version":1,"revision":'
INVALID_UTF8 = b'{"schema_version":1,"revision":1,"profile":\xff}'
OVERSIZED = WORK_BYTES + b" " * (MAX_BODY_BYTES - len(WORK_BYTES))
WRONG_HASH_WORK = copy.deepcopy(WORK)
WRONG_HASH_WORK["profile"]["asset_sha256"] = "0" * 64
WRONG_HASH = json.dumps(WRONG_HASH_WORK, separators=(",", ":")).encode()
MISSING_ASSET_WORK = copy.deepcopy(WORK)
MISSING_ASSET_WORK["profile"]["asset_path"] = "fixtures/__m1_missing_asset__.glb"
MISSING_ASSET = json.dumps(MISSING_ASSET_WORK, separators=(",", ":")).encode()
NEGATIVE_FIXTURES = {
    "/fixtures/invalid-json.nvwa.json": INVALID_JSON,
    "/fixtures/invalid-utf8.nvwa.json": INVALID_UTF8,
    "/fixtures/oversized.nvwa.json": OVERSIZED,
    "/fixtures/wrong-asset-sha256.nvwa.json": WRONG_HASH,
    "/fixtures/missing-glb.nvwa.json": MISSING_ASSET,
}
VALID_WORK_ROUTE = "/examples/m1-sequence.nvwa.json"
REDIRECT_ROUTE = "/fixtures/redirect.nvwa.json"
STALLED_ROUTE = "/fixtures/stalled.nvwa.json"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"
    def do_GET(self) -> None:
        self.serve(False)

    def do_HEAD(self) -> None:
        self.serve(True)

    def serve(self, head_only: bool) -> None:
        path = unquote(urlsplit(self.path).path)
        prefix = ""
        if path == "/published" or path.startswith("/published/"):
            prefix, path = "/published", path[len("/published") :] or "/"

        if path == VALID_WORK_ROUTE:
            self.send_body(200, WORK_BYTES, "application/json", head_only)
            return
        if path == REDIRECT_ROUTE:
            self.send_response(302)
            self.send_header("Location", prefix + VALID_WORK_ROUTE)
            self.send_header("Content-Length", "0")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return
        if path == STALLED_ROUTE:
            self.send_stalled(head_only)
            return
        if path in NEGATIVE_FIXTURES:
            body = NEGATIVE_FIXTURES[path]
            if path == "/fixtures/oversized.nvwa.json":
                self.send_body(200, body, "application/json", head_only, False)
            else:
                self.send_body(200, body, "application/json", head_only)
            return

        relative = "index.html" if path in ("", "/") else path.lstrip("/")
        target = (WEB_ROOT / relative).resolve()
        try:
            target.relative_to(WEB_ROOT)
        except ValueError:
            self.send_body(403, b"Forbidden\n", "text/plain", head_only)
            return
        if target.is_dir(): target = target / "index.html"
        if not target.is_file():
            self.send_body(404, b"Not found\n", "text/plain", head_only)
            return
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if target.suffix == ".wasm": content_type = "application/wasm"
        self.send_body(200, target.read_bytes(), content_type, head_only)

    def send_body(self, status, body, content_type, head_only, content_length=True):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if content_length:
            self.send_header("Content-Length", str(len(body)))
        else:
            self.send_header("Connection", "close")
            self.close_connection = True
        self.end_headers()
        if not head_only:
            try:
                self.wfile.write(body)
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass

    def send_stalled(self, head_only: bool) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(WORK_BYTES)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if head_only:
            return
        try:
            self.wfile.flush()
            time.sleep(STALL_SECONDS)
            self.wfile.write(WORK_BYTES)
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass


class LoopbackServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main() -> None:
    if not WEB_ROOT.is_dir():
        raise SystemExit(f"Missing static Web bundle: {WEB_ROOT}")
    server = LoopbackServer((HOST, PORT), Handler)
    print(f"Test-only Player fixtures: http://{HOST}:{PORT}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping test server")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
