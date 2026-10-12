#!/usr/bin/env python3
"""Two-startup loopback HTTP-cache experiment. Python standard library only."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import re
import threading
import time
from urllib.parse import unquote, urlsplit
import uuid

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PORT = 9201


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def accepts_gzip(value):
    # An explicit gzip exclusion takes priority over wildcard support.
    choices = {}
    for item in value.lower().split(','):
        parts = item.strip().split(';')
        if not parts[0]:
            continue
        quality = 1.0
        try:
            for parameter in parts[1:]:
                if parameter.strip().startswith('q='):
                    quality = float(parameter.strip()[2:])
            if not 0 <= quality <= 1:
                return False
        except ValueError:
            return False
        choices[parts[0]] = quality
    return choices.get('gzip', choices.get('*', 0)) > 0


class Experiment:
    def __init__(self, root, evidence, run_ids=None, runs=2):
        self.root = Path(root).resolve(strict=True)
        self.evidence = Path(evidence).resolve()
        if self.evidence == self.root or self.evidence.is_relative_to(self.root):
            raise ValueError('evidence must be outside served root')
        self.evidence.mkdir(parents=True, exist_ok=True)
        if any(self.evidence.iterdir()):
            raise ValueError('evidence directory must be empty; preserve earlier captures')
        self.lock = threading.Lock()
        if not 1 <= runs <= 6:
            raise ValueError('runs must be bounded between 1 and 6')
        self.run_ids = run_ids or [uuid.uuid4().hex for _ in range(runs)]
        if len(self.run_ids) != runs or len(set(self.run_ids)) != runs or any(
                not re.fullmatch(r'[0-9a-f]{32}', value) for value in self.run_ids):
            raise ValueError('distinct UUID hex run IDs required for each bounded run')
        self.started = set()
        self.files = {}
        for path in sorted(self.root.rglob('*')):
            if not path.is_file():
                continue
            name = path.relative_to(self.root).as_posix()
            base = name.removesuffix('.gz')
            allowed = base in ('index.html', 'nvwa_studio.js', 'nvwa_studio_bg.wasm') or base.startswith(('assets/', 'works/', 'licenses/'))
            if not allowed:
                continue
            if path.is_symlink() or not path.resolve().is_relative_to(self.root):
                raise ValueError('served member escapes frozen root: ' + name)
            self.files[name] = {'sha256': sha(path), 'bytes': path.stat().st_size}
        for name in ('index.html', 'nvwa_studio.js', 'nvwa_studio_bg.wasm'):
            if name not in self.files:
                raise ValueError('missing production member: ' + name)
        for name in self.files:
            if name.endswith('.gz'):
                base = name[:-3]
                if base not in self.files or sha_decompressed(self.root / name) != self.files[base]['sha256']:
                    raise ValueError('gzip is not exact frozen identity bytes: ' + name)
        source = (self.root / 'index.html').read_text()
        if source.count('<head>') != 1 or source.count('<script type="module">') != 1:
            raise ValueError('unexpected frozen index structure')
        self.collector = (HERE / 'collector.js').read_bytes()
        self.export_diagnostics = {}
        for name in ('screenshot.html', 'export-probe.js'):
            path = HERE.parent / '25-screenshot-export' / name
            if path.exists():
                if path.is_symlink():
                    raise ValueError('export diagnostic cannot be a symlink')
                self.export_diagnostics[name] = path.read_bytes()
        self.wrapper = source.replace('<head>', '<head>\n  <script src="./startup-diagnostics.js"></script>', 1).encode()
        self.manifest = {
            'schema': 'nvwa-http-startup-manifest-v1', 'root': str(self.root),
            'bind': '127.0.0.1', 'port': PORT, 'runLimit': runs,
            'runIds': self.run_ids, 'cacheControl': 'no-store', 'frozenFiles': self.files,
            'diagnostics': {'wrapperSha256': digest(self.wrapper), 'collectorSha256': digest(self.collector),
                            'serverSourceSha256': sha(HERE / 'server.py'),
                            'exportDiagnostics': {name: digest(data) for name, data in self.export_diagnostics.items()}},
            'wrapperChange': 'classic read-only collector inserted into head; production module unchanged',
            'scope': 'fresh URL prefix plus no-store HTTP responses; no browser/GPU/OS/shader cold claim',
        }
        (self.evidence / 'manifest.json').write_text(json.dumps(self.manifest, indent=2) + '\n')
        (self.evidence / 'wrapper.html').write_bytes(self.wrapper)
        (self.evidence / 'collector.js').write_bytes(self.collector)

    def route(self, target):
        path = urlsplit(target).path
        # Decode once and reject percent residue, dot segments and Windows separators.
        path = unquote(path, errors='strict')
        if '%' in path or '\\' in path or any(part in ('.', '..', '') for part in path.split('/')[1:]):
            raise ValueError('unsafe path')
        parts = path.split('/')
        if len(parts) < 4 or parts[1] != 'run' or parts[2] not in self.run_ids:
            raise LookupError('unknown run prefix')
        return parts[2], '/'.join(parts[3:])

    def response(self, method, target, accept_encoding):
        try:
            run, name = self.route(target)
        except (ValueError, UnicodeError):
            return 400, b'unsafe path\n', 'text/plain', 'identity', None, None
        except LookupError:
            return 404, b'unknown run prefix\n', 'text/plain', 'identity', None, None
        if method not in ('GET', 'HEAD'):
            return 405, b'GET and HEAD only\n', 'text/plain', 'identity', run, name
        if name == 'index.html':
            if method == 'GET':
                with self.lock:
                    if run in self.started:
                        return 409, b'run already started; use the other fresh prefix\n', 'text/plain', 'identity', run, name
                    self.started.add(run)
            return 200, self.wrapper, 'text/html; charset=utf-8', 'identity', run, name
        if name == 'startup-diagnostics.js':
            return 200, self.collector, 'text/javascript; charset=utf-8', 'identity', run, name
        if name in self.export_diagnostics:
            mime = 'text/html; charset=utf-8' if name.endswith('.html') else 'text/javascript; charset=utf-8'
            return 200, self.export_diagnostics[name], mime, 'identity', run, name
        if name not in self.files or name.endswith('.gz') or name == 'index.html.gz':
            return 404, b'not a served runtime member\n', 'text/plain', 'identity', run, name
        selected = name + '.gz' if accepts_gzip(accept_encoding) and name + '.gz' in self.files else name
        path = self.root / selected
        if not path.resolve().is_relative_to(self.root) or path.is_symlink():
            return 409, b'frozen member changed\n', 'text/plain', 'identity', run, name
        try:
            data = path.read_bytes()
        except OSError:
            return 409, b'frozen member unavailable\n', 'text/plain', 'identity', run, name
        if digest(data) != self.files[selected]['sha256']:
            return 409, b'frozen member changed\n', 'text/plain', 'identity', run, name
        mime = 'application/wasm' if name.endswith('.wasm') else mimetypes.guess_type(name)[0] or 'application/octet-stream'
        return 200, data, mime, 'gzip' if selected.endswith('.gz') else 'identity', run, name

    def log(self, row):
        with self.lock, (self.evidence / 'requests.jsonl').open('a') as output:
            output.write(json.dumps(row, allow_nan=False) + '\n')


def sha_decompressed(path):
    with gzip.open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def handler_for(experiment):
    class Handler(BaseHTTPRequestHandler):
        def serve(self):
            start = time.perf_counter_ns()
            stamp = datetime.now(timezone.utc).isoformat()
            status, data, mime, encoding, run, name = experiment.response(self.command, self.path, self.headers.get('Accept-Encoding', ''))
            sent = 0
            interrupted = None
            try:
                self.send_response(status)
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Vary', 'Accept-Encoding')
                self.send_header('Content-Type', mime)
                self.send_header('Content-Length', str(len(data)))
                if encoding == 'gzip':
                    self.send_header('Content-Encoding', encoding)
                self.end_headers()
                if self.command != 'HEAD':
                    for offset in range(0, len(data), 64 * 1024):
                        chunk = data[offset:offset + 64 * 1024]
                        self.wfile.write(chunk)
                        sent += len(chunk)
            except (BrokenPipeError, ConnectionResetError) as error:
                interrupted = type(error).__name__
            finally:
                experiment.log({'schema': 'nvwa-http-request-v1', 'utcStart': stamp,
                    'serverMonotonicStartNs': start, 'elapsedMs': (time.perf_counter_ns() - start) / 1e6,
                    'method': self.command, 'target': self.path, 'runId': run, 'member': name,
                    'status': status, 'contentEncoding': encoding, 'responseBodySha256': digest(data),
                    'cacheControl': 'no-store',
                    'declaredBodyBytes': len(data), 'bodyBytesWritten': sent, 'interrupted': interrupted,
                    'byteMeaning': 'successful socket writes of response body; excludes HTTP headers; not client receipt'})

        do_GET = do_HEAD = do_POST = do_PUT = do_DELETE = do_OPTIONS = do_PATCH = serve

        def __getattr__(self, name):
            if name.startswith('do_'):
                return self.serve
            raise AttributeError(name)

        def log_message(self, *_arguments):
            pass
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=REPO / 'dist/web')
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--runs', type=int, default=2, help='bounded fresh prefixes, 1..6 (startup protocol uses 2)')
    args = parser.parse_args()
    if args.root.resolve() != (REPO / 'dist/web').resolve():
        parser.error('CLI serves only this checkout dist/web')
    experiment = Experiment(args.root, args.evidence, runs=args.runs)
    server = ThreadingHTTPServer(('127.0.0.1', PORT), handler_for(experiment))
    print(json.dumps({'evidence': str(experiment.evidence), 'urls': [
        f'http://127.0.0.1:{PORT}/run/{run}/index.html' for run in experiment.run_ids]}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
