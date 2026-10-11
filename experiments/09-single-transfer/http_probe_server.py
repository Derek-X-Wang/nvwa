#!/usr/bin/env python3
"""Loopback static probe: log response bytes actually written, with no-store cache."""
import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import urlsplit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--log', required=True, type=Path)
    parser.add_argument('--port', type=int, default=9202)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    log = args.log.resolve()
    log.parent.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *arguments, **keywords):
            self.sent_bytes = 0
            self.response_status = None
            self.encoding = None
            self.declared_bytes = None
            self.body_started = False
            super().__init__(*arguments, directory=str(root), **keywords)

        def setup(self):
            super().setup()
            original = self.wfile
            owner = self

            class BodyWriter:
                def write(self, data):
                    result = original.write(data)
                    if owner.body_started:
                        owner.sent_bytes += len(data)
                    return result

                def __getattr__(self, name):
                    return getattr(original, name)

            self.wfile = BodyWriter()

        def send_response(self, code, message=None):
            self.response_status = code
            super().send_response(code, message)

        def end_headers(self):
            self.send_header('Cache-Control', 'no-store')
            super().end_headers()
            self.body_started = True

        def send_head(self):
            original = Path(self.translate_path(self.path))
            compressed = Path(str(original) + '.gz')
            if 'gzip' in self.headers.get('Accept-Encoding', '') and original.is_file() and compressed.is_file():
                self.encoding = 'gzip'
                self.declared_bytes = compressed.stat().st_size
                source = compressed.open('rb')
                self.send_response(200)
                self.send_header('Content-Type', self.guess_type(str(original)))
                self.send_header('Content-Encoding', 'gzip')
                self.send_header('Content-Length', str(self.declared_bytes))
                self.send_header('Vary', 'Accept-Encoding')
                self.end_headers()
                return source
            return super().send_head()

        def copyfile(self, source, destination):
            while chunk := source.read(64 * 1024):
                destination.write(chunk)

        def do_GET(self):
            interrupted = None
            try:
                super().do_GET()
            except (BrokenPipeError, ConnectionResetError) as error:
                interrupted = type(error).__name__
            finally:
                record = {'method': 'GET', 'path': urlsplit(self.path).path,
                          'status': self.response_status, 'content_encoding': self.encoding,
                          'declared_bytes': self.declared_bytes, 'body_bytes_written': self.sent_bytes,
                          'interrupted': interrupted}
                with lock, log.open('a') as output:
                    output.write(json.dumps(record) + '\n')

    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Nvwa byte probe: http://127.0.0.1:{args.port}; root={root}; log={log}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
