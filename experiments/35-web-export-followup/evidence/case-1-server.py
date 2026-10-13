"""Exact-file loopback server. No uploads, receiver, filesystem paths or listings."""
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PACKET = ROOT / '.work/issue5-export-followup'
PORT = 9206
ORIGIN = f'http://127.0.0.1:{PORT}'

def utc():
    return datetime.now(timezone.utc).isoformat()

def members():
    dist = ROOT / 'dist/web'
    return {
        '/case-1/index.html': (dist / 'index.html', 'text/html'),
        '/case-1/observer.js': (HERE / 'observer.js', 'text/javascript'),
        '/case-1/nvwa_studio.js': (dist / 'nvwa_studio.js', 'text/javascript'),
        '/case-1/nvwa_studio_bg.wasm': (dist / 'nvwa_studio_bg.wasm', 'application/wasm'),
        '/case-1/assets/fixtures/nvwa-humanoid.glb': (dist / 'assets/fixtures/nvwa-humanoid.glb', 'model/gltf-binary'),
        '/case-1/assets/character.profile.json': (dist / 'assets/character.profile.json', 'application/json'),
        '/case-1/works/character-loop.nvwa.json': (ROOT / 'docs/evidence/bounded-perf-20261013/common/character-loop.nvwa.json', 'application/json'),
    }

def body_for(path):
    member = members().get(path)
    if member is None:
        return None
    filename, mime = member
    body = filename.read_bytes()
    if path.endswith('/index.html'):
        marker = b'  <script type="module">'
        assert body.count(marker) == 1
        body = body.replace(marker, b'  <script src="./observer.js"></script>\n' + marker)
    return body, mime

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        start = utc()
        if self.headers.get('Host') != f'127.0.0.1:{PORT}' or self.headers.get('Origin') not in (None, ORIGIN):
            self.send_error(403)
            return
        path = urlsplit(self.path).path
        result = body_for(path)
        body, mime = result if result else (b'Not found\n', 'text/plain')
        code = 200 if result else 404
        self.send_response(code)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)
        with (PACKET / 'network.jsonl').open('a') as stream:
            stream.write(json.dumps({'start_utc': start, 'end_utc': utc(), 'path': path, 'status': code, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(), 'clock': 'server_utc_socket_write'}) + '\n')

    def log_message(self, *_):
        pass

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serve', action='store_true', required=True)
    parser.parse_args()
    PACKET.mkdir(parents=True, exist_ok=True)
    with HTTPServer(('127.0.0.1', PORT), Handler) as server:
        (PACKET / 'server-identity.json').write_text(json.dumps({'pid': os.getpid(), 'start_utc': utc(), 'port': PORT, 'executable': os.sys.executable, 'argv': os.sys.argv, 'binding': ORIGIN}, indent=2))
        print(f'Owned server PID {os.getpid()} {ORIGIN}', flush=True)
        try:
            server.serve_forever(poll_interval=0.2)
        except KeyboardInterrupt:
            pass
    print('Owned server closed', flush=True)

if __name__ == '__main__':
    main()
