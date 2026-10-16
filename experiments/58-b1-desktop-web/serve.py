#!/usr/bin/env python3
"""Root-launched, loopback-only static server; bind fails if exact port occupied."""
import argparse,hashlib,http.server
from pathlib import Path
from functools import partial
parser=argparse.ArgumentParser();parser.add_argument('--port',required=True,type=int);a=parser.parse_args()
if not 9203 <= a.port <= 9299:
    parser.error('Use an unused Nvwa reserved probe port, preserving 9201/9202')
site=Path(__file__).resolve().parents[2]/'.work/b1-pose-viewer/site'
class FreshBuildHandler(http.server.SimpleHTTPRequestHandler):
    """A rebuilt local experiment must never reuse an old module or asset body."""
    def send_head(self):
        # Explicitly return a body even when a previously used URL has a cached
        # Last-Modified value. This helper is a dev server, not a hosting policy.
        if 'If-Modified-Since' in self.headers:
            del self.headers['If-Modified-Since']
        body = super().send_head()
        if body is not None and self.command == 'GET':
            # Hash the same opened body that copyfile will send, then rewind.
            # Diagnostic overhead is intentional; this is not a perf server.
            digest = hashlib.sha256()
            size = 0
            while chunk := body.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
            body.seek(0)
            self.log_message('B1_RESPONSE sha256=%s bytes=%d path=%s', digest.hexdigest(), size, self.path)
        return body

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

server=http.server.ThreadingHTTPServer(('127.0.0.1',a.port),partial(FreshBuildHandler,directory=str(site)))
print(f'B1 viewer http://127.0.0.1:{a.port} — PID owned by invoking root',flush=True)
server.serve_forever()
