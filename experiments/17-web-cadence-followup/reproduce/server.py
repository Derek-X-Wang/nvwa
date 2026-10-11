#!/usr/bin/env python3
"""Root-owned loopback preview; report server body writes, never browser receipt."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
from urllib.parse import urlsplit

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bundle', required=True)
parser.add_argument('--port', type=int, required=True)
parser.add_argument('--log', required=True)
parser.add_argument('--arm', choices=('A', 'B'), required=True)
args = parser.parse_args()
bundle = Path(args.bundle).resolve()
log = Path(args.log).resolve()
if not (bundle / 'index.html').is_file():
    raise SystemExit('No bundle index.html')
if log.exists():
    raise SystemExit('Use a new request log for each bounded arm/run')
log.parent.mkdir(parents=True, exist_ok=True)
lock = threading.Lock()

class ObservedHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.started = time.monotonic()
        self.written = 0
        self.status = None
        self.response_headers = {}
        self.transfer_error = None
        try:
            super().do_GET()
        except (BrokenPipeError, ConnectionResetError) as exc:
            self.transfer_error = type(exc).__name__
        finally:
            user_agent = self.headers.get('User-Agent', '')
            record = {
                'arm': args.arm,
                'epoch_seconds': time.time(),
                'path': urlsplit(self.path).path,
                'request_target': self.path,
                'user_agent': user_agent,
                'client_kind': 'python-audit' if user_agent == 'Nvwa-M1.1-Audit/1' else 'browser-candidate' if 'Mozilla/' in user_agent else 'other',
                'status': self.status,
                'content_encoding': self.response_headers.get('content-encoding', 'identity'),
                'cache_control': self.response_headers.get('cache-control'),
                'content_length': self.response_headers.get('content-length'),
                'body_bytes_written': self.written,
                'duration_seconds': time.monotonic() - self.started,
                'transfer_error': self.transfer_error,
                'boundary': 'server output.write returned; browser/TCP receipt NOT-RUN',
            }
            with lock, log.open('a') as stream:
                stream.write(json.dumps(record, sort_keys=True) + '\n')

    def send_response(self, code, message=None):
        self.status = code
        super().send_response(code, message)

    def send_header(self, name, value):
        if hasattr(self, 'response_headers'):
            self.response_headers[name.lower()] = value
        super().send_header(name, value)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def send_head(self):
        path = Path(self.translate_path(self.path))
        if path.is_dir():
            path = path / 'index.html'
        sidecar = path.with_name(path.name + '.gz')
        if 'gzip' in self.headers.get('Accept-Encoding', '') and path.is_file() and sidecar.is_file():
            source = sidecar.open('rb')
            self.send_response(200)
            self.send_header('Content-Type', self.guess_type(str(path)))
            self.send_header('Content-Encoding', 'gzip')
            self.send_header('Content-Length', str(sidecar.stat().st_size))
            self.send_header('Vary', 'Accept-Encoding')
            self.end_headers()
            return source
        return super().send_head()

    def copyfile(self, source, outputfile):
        for block in iter(lambda: source.read(1 << 20), b''):
            self.written += outputfile.write(block)

    def log_message(self, format, *items):
        pass

server = ThreadingHTTPServer(('127.0.0.1', args.port), partial(ObservedHandler, directory=str(bundle)))
server.daemon_threads = True
watchdog = threading.Timer(120.0, server.shutdown)
watchdog.daemon = True
watchdog.start()
print(f'Arm {args.arm}: http://127.0.0.1:{args.port}; server body-write log {log}', flush=True)
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    watchdog.cancel()
    server.server_close()
    print('Owned server stopped; automatic lifetime bound120s', flush=True)
