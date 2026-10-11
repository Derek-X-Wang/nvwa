"""Loopback-only static preview. No remote command or document control endpoint."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from pathlib import Path
import argparse
import os
from urllib.parse import urlsplit

parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=9201)
args = parser.parse_args()
root = Path(__file__).resolve().parent.parent / 'dist/web'
if not (root / 'index.html').is_file():
    raise SystemExit('Build Web first: bash scripts/build-web.sh')
class StaticHandler(SimpleHTTPRequestHandler):
    def send_head(self):
        if urlsplit(self.path).path in ('/', '/index.html'):
            # Record the actual browser build for reproducible local measurements.
            # Manual Open uses picker data; published Player works are static files.
            print('NVWA_BROWSER ' + self.headers.get('User-Agent', 'unavailable'), flush=True)
        original = Path(self.translate_path(self.path))
        compressed = Path(str(original) + '.gz')
        if 'gzip' in self.headers.get('Accept-Encoding', '') and original.is_file() and compressed.is_file():
            source = compressed.open('rb')
            size = os.fstat(source.fileno()).st_size
            self.send_response(200)
            self.send_header('Content-Type', self.guess_type(str(original)))
            self.send_header('Content-Encoding', 'gzip')
            self.send_header('Content-Length', str(size))
            self.send_header('Vary', 'Accept-Encoding')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            return source
        return super().send_head()

handler = partial(StaticHandler, directory=str(root))
server = ThreadingHTTPServer(('127.0.0.1', args.port), handler)
print(f'Nvwa static preview: http://127.0.0.1:{args.port}', flush=True)
try:
    server.serve_forever()
except KeyboardInterrupt:
    server.server_close()
