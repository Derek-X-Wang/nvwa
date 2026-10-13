#!/usr/bin/env python3
"""Root-leased bounded adapter; reuse unchanged experiment24 HTTP machinery."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import socket
import threading
import time
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
EXPECTED = {
    'nvwa_studio_bg.wasm': 'd890dfee73e9eeeee6ce3d82f255c79979e8c8b6bed90243c6101f8e1c1763a8',
    'assets/fixtures/nvwa-humanoid.glb': 'f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6',
}
WORK_MEMBER = 'works/perf-character-loop.nvwa.json'
WORK_SHA = 'ff0b8e36adfc3ebadc5fc700a4c760f6f551273b56e85bf336563e18b63eb445'


def load_http():
    source = HERE.parent / '24-http-cold-startup/server.py'
    spec = importlib.util.spec_from_file_location('nvwa_web_perf_http', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, source


def prepare(evidence, port, runs, variant=False):
    if port not in (9201, 9205) or runs not in (1, 2, 3):
        raise ValueError('only root-leased9201/9205 and max3 prefixes')
    http, source = load_http()
    root = REPO / 'dist/web'
    for member, expected in EXPECTED.items():
        if http.sha(root / member) != expected:
            raise ValueError('root-assigned artifact identity changed: ' + member)
    if (root / 'assets/fixtures/nvwa-humanoid.glb').stat().st_size != 3827840:
        raise ValueError('real-character size changed')
    http.PORT = port
    experiment = http.Experiment(root, evidence, runs=runs)
    # Preserve base collector source and append separate diagnostic wrappers.
    base = (HERE / 'collector.js').read_bytes()
    if base != experiment.collector:
        raise ValueError('retained base collector differs from experiment24')
    experiment.collector = base + b'\n' + (HERE / 'gpu-boundaries.js').read_bytes()
    if variant:
        experiment.collector += b'\n' + (HERE / 'timestamp-variant.js').read_bytes()
    experiment.export_diagnostics = {}  # no unrelated export routes in this batch
    work_path = REPO / '.work/m11-perf/input/character-loop.nvwa.json'
    work_bytes = work_path.read_bytes()
    if len(work_bytes) != 1624 or http.digest(work_bytes) != WORK_SHA:
        raise ValueError('root-frozen common Work identity mismatch')
    experiment.files[WORK_MEMBER] = {'sha256': WORK_SHA, 'bytes': 1624}
    experiment.manifest['commonWork'] = {'member': WORK_MEMBER, 'sha256': WORK_SHA, 'bytes': 1624,
        'revision': 0, 'timeline': 'natural idle loop; same exact frozen document as native'}
    experiment.manifest['diagnostics']['collectorSha256'] = http.digest(experiment.collector)
    experiment.manifest['diagnostics']['exportDiagnostics'] = {}
    experiment.manifest['adapter'] = {'sourceSha256': http.sha(HERE / 'server.py'),
        'gpuBoundariesSha256': http.sha(HERE / 'gpu-boundaries.js'),
        'baseServerSha256': http.sha(source),
        'baseCollectorSha256': http.sha(source.parent / 'collector.js'),
        'change': 'same production bytes; append bounded production-call WebGPU/JS-heap observations',
        'runProtocol': 'at most2 HTTP-cold attempts plus1 same-process contrast; no full-cold claim'}
    experiment.manifest['adapter']['timestampVariant'] = variant
    experiment.attempts = {}
    base_response, base_log = experiment.response, experiment.log

    def response(method, target, encoding):
        try:
            run, member = experiment.route(target)
        except (ValueError, LookupError, UnicodeError):
            return base_response(method, target, encoding)
        if member == WORK_MEMBER and method in ('GET', 'HEAD'):
            if http.sha(work_path) != WORK_SHA:
                return 409, b'frozen Work changed\n', 'text/plain', 'identity', run, member
            return 200, work_bytes, 'application/json', 'identity', run, member
        if method == 'GET' and member == 'index.html':
            with experiment.lock:
                count = experiment.attempts.get(run, 0)
                # Only first prefix may be repeated once for explicit contrast.
                maximum = 2 if run == experiment.run_ids[0] and not variant else 1
                if count >= maximum or sum(experiment.attempts.values()) >= 3:
                    return 409, b'bounded attempts exhausted\n', 'text/plain', 'identity', run, member
                experiment.attempts[run] = count + 1
                experiment.started.discard(run)
        return base_response(method, target, encoding)

    def log(row):
        row['attempt'] = experiment.attempts.get(row.get('runId'), 0)
        base_log(row)

    experiment.response, experiment.log = response, log

    def log_receiver(row):
        with experiment.lock, (experiment.evidence / 'receiver.jsonl').open('a') as output:
            output.write(json.dumps(row, allow_nan=False) + '\n')

    experiment.log_receiver = log_receiver
    (experiment.evidence / 'collector.js').write_bytes(experiment.collector)
    (experiment.evidence / 'manifest.json').write_text(json.dumps(experiment.manifest, indent=2) + '\n')
    return http, experiment


def handler_for(http, experiment):
    base = http.handler_for(experiment)

    class Handler(base):
        def setup(self):
            # Applies before BaseHTTPRequestHandler reads headers or body.
            self.request.settimeout(5.0)
            self.deadline_expired = False

            def deadline():
                self.deadline_expired = True
                try:
                    self.request.shutdown(socket.SHUT_RD)
                except OSError:
                    pass  # already closed request; no persistent socket to close

            # A total request deadline also bounds slow trickled headers/bodies.
            self.deadline_timer = threading.Timer(5.0, deadline)
            self.deadline_timer.daemon = True
            self.deadline_timer.start()
            super().setup()

        def finish(self):
            try:
                super().finish()
            finally:
                self.deadline_timer.cancel()
                self.deadline_timer.join(timeout=1)

        def do_POST(self):
            # Private bounded same-origin capture receiver; no arbitrary paths.
            run, member, size = None, None, None
            started = time.perf_counter()
            reason = None
            try:
                run, member = experiment.route(self.path)
                if member != 'capture.json' or not experiment.attempts.get(run):
                    raise ValueError('not an active capture route')
                expected_origin = f'http://127.0.0.1:{experiment.manifest["port"]}'
                if self.headers.get_all('Origin') != [expected_origin]:
                    raise ValueError('same-origin browser capture required')
                if len(self.headers.get_all('Content-Length', [])) != 1:
                    raise ValueError('one explicit Content-Length required')
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 512000 or self.headers.get('Transfer-Encoding'):
                    raise ValueError('bounded Content-Length required')
                payload = self.rfile.read(size)
                if len(payload) != size:
                    if self.deadline_expired:
                        raise TimeoutError('total five-second request deadline')
                    raise ValueError('incomplete capture')
                capture = json.loads(payload)
                if capture.get('schema') != 'nvwa-web-perf-browser-v1' or capture.get('startup', {}).get('runId') != run:
                    raise ValueError('capture identity mismatch')
                path = experiment.evidence / f'{run}-attempt{experiment.attempts[run]}-browser.json'
                with path.open('xb') as out:
                    out.write(payload)
                body, status = b'capture retained\n', 201
            except (TimeoutError, socket.timeout):
                body, status, reason = b'capture body timeout\n', 408, 'five-second socket-read deadline'
            except (ValueError, LookupError, UnicodeError, KeyError, TypeError, FileExistsError) as error:
                body, status, reason = b'capture rejected\n', 409, str(error)
            except Exception as error:
                # Unknown failures remain visible and propagate to server stderr.
                experiment.log_receiver({'status': 'ERROR', 'runId': run,
                    'exception': type(error).__name__, 'elapsedMs': (time.perf_counter() - started) * 1000})
                raise
            self.close_connection = True
            disconnected = None
            try:
                self.send_response(status)
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Connection', 'close')
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                disconnected = True
            finally:
                experiment.log_receiver({'status': status, 'runId': run, 'member': member,
                    'attempt': experiment.attempts.get(run, 0), 'declaredBytes': size,
                    'reason': reason, 'disconnected': disconnected,
                    'elapsedMs': (time.perf_counter() - started) * 1000,
                    'socketReadTimeoutSeconds': 5})

        def log_error(self, format, *args):
            experiment.log_receiver({'status': 'HTTP_ERROR', 'message': format % args,
                'socketReadTimeoutSeconds': 5})

    return Handler


def bounded_server(http, address, handler):
    class Server(http.ThreadingHTTPServer):
        daemon_threads = False
        block_on_close = True

        def __init__(self, *args):
            self.slots = threading.BoundedSemaphore(16)
            self.request_lock = threading.Lock()
            self.accepted_requests = 0
            super().__init__(*args)

        def process_request(self, request, client_address):
            with self.request_lock:
                if self.accepted_requests >= 256:
                    self.shutdown_request(request)
                    return
                self.accepted_requests += 1
            if not self.slots.acquire(blocking=False):
                self.shutdown_request(request)
                return
            try:
                super().process_request(request, client_address)
            except Exception:
                self.slots.release()
                raise

        def process_request_thread(self, request, client_address):
            try:
                super().process_request_thread(request, client_address)
            finally:
                self.slots.release()

    return Server(address, handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--port', type=int, choices=(9201, 9205), required=True)
    parser.add_argument('--runs', type=int, choices=(1, 2, 3), default=3)
    parser.add_argument('--timestamp-variant', action='store_true')
    args = parser.parse_args()
    http, experiment = prepare(args.evidence, args.port, args.runs, args.timestamp_variant)
    server = bounded_server(http, ('127.0.0.1', args.port), handler_for(http, experiment))
    print(json.dumps({'ownedPid': os.getpid(), 'port': args.port,
        'urls': [f'http://127.0.0.1:{args.port}/run/{r}/index.html?benchmark=1&work={WORK_MEMBER}' for r in experiment.run_ids]}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
