"""Pure-data controls and no-socket frozen server controls. Not GPU evidence."""
import copy
import json
import hashlib
from http.client import HTTPConnection
import os
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest

from check_metrics import CLOCK, MEANINGS, boundaries, timestamp_variant, verify
from server import prepare, REPO, WORK_MEMBER, bounded_server, handler_for


def diagnostic(startup):
    return {'schema': 'nvwa-web-perf-browser-v1', 'clock': CLOCK, 'snapshotAtMs': 10000,
        'startup': startup, 'eventsDropped': 0,
        'hooks': [{'method': name, 'installed': True} for name in
            ('GPUAdapter.requestDevice', 'GPUQueue.submit', 'GPUCanvasContext.getCurrentTexture')],
        'events': [{'name': name, 'meaning': meaning, 'clock': CLOCK, 'atMs': 1000} for name, meaning in MEANINGS.items()],
        'devices': [{'enabledFeatures': [], 'clock': CLOCK, 'observedAtMs': 1000}],
        'claims': {name: 'NOT-RUN' for name in ('firstPhysicalPresentation', 'gpuTimestampDuration', 'gpuMemory', 'browserProcessMemory', 'fullyCold')},
        'jsHeap': {'status': 'NOT-RUN', 'samples': []}, 'gpuTimestampVariant': None}


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.http, cls.server = prepare(Path(cls.directory.name) / 'evidence', 9205, 2)
        cls.run_id = cls.server.run_ids[0]
        prefix = f'/run/{cls.run_id}/'
        cls.requests, resources = [], []
        for index, name in enumerate(('index.html', 'startup-diagnostics.js', 'nvwa_studio.js', 'nvwa_studio_bg.wasm', 'assets/fixtures/nvwa-humanoid.glb', WORK_MEMBER)):
            status, body, _, encoding, _, _ = cls.server.response('GET', prefix + name, '')
            assert status == 200
            cls.requests.append({'method': 'GET', 'target': prefix + name, 'runId': cls.run_id, 'member': name,
                'status': status, 'contentEncoding': encoding, 'responseBodySha256': cls.http.digest(body),
                'cacheControl': 'no-store', 'bodyBytesWritten': len(body), 'declaredBodyBytes': len(body), 'interrupted': None, 'attempt': 1})
            resources.append({'name': f'http://127.0.0.1:9205{prefix}{name}', 'entryType': 'navigation' if index == 0 else 'resource',
                'startTime': 0, 'duration': 100, 'responseEnd': 100, 'transferSize': len(body) + 300,
                'encodedBodySize': len(body), 'decodedBodySize': len(body)})
        startup = {'schema': 'nvwa-http-startup-browser-v1', 'clock': CLOCK, 'runId': cls.run_id,
            'url': resources[0]['name'] + '?benchmark=1&work=' + WORK_MEMBER, 'installedAtMs': 1, 'snapshotAtMs': 10000, 'timeOriginEpochMs': 123456,
            'geometry': {'viewportCss': {'width': 1280, 'height': 720}, 'devicePixelRatio': 1, 'canvasBacking': {'width': 1280, 'height': 720}},
            'navigation': resources[:1], 'resources': resources[1:], 'milestones': [], 'resourceTimingLimit': {}}
        cls.capture = diagnostic(startup)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_valid_synthetic_body_reconciliation(self):
        result = verify(self.capture, self.server.manifest, self.requests, self.run_id)
        self.assertEqual(result['http']['actualGetRequests'], 6)

    def test_missing_milestone_red(self):
        c = copy.deepcopy(self.capture); c['events'].pop()
        with self.assertRaisesRegex(ValueError, 'missing production milestone'):
            boundaries(c)

    def test_mixed_clock_red(self):
        c = copy.deepcopy(self.capture); c['events'][0]['clock'] = 'bevy_TimeReal_since_first_update'
        with self.assertRaisesRegex(ValueError, 'mixed/future'):
            boundaries(c)

    def test_future_timestamp_red(self):
        c = copy.deepcopy(self.capture); c['events'][0]['atMs'] = 20000
        with self.assertRaisesRegex(ValueError, 'mixed/future'):
            boundaries(c)

    def test_claiming_display_from_submit_red(self):
        c = copy.deepcopy(self.capture); c['claims']['firstPhysicalPresentation'] = 'VERIFIED'
        with self.assertRaisesRegex(ValueError, 'unsupported claim'):
            boundaries(c)

    def test_uninstalled_hook_red(self):
        c = copy.deepcopy(self.capture); c['hooks'][0]['installed'] = False
        with self.assertRaisesRegex(ValueError, 'hooks not installed'):
            boundaries(c)

    def test_wrong_wasm_source_red(self):
        m = copy.deepcopy(self.server.manifest); m['frozenFiles']['nvwa_studio_bg.wasm']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'input identity'):
            verify(self.capture, m, self.requests, self.run_id)

    def test_wrong_glb_size_red(self):
        m = copy.deepcopy(self.server.manifest); m['frozenFiles']['assets/fixtures/nvwa-humanoid.glb']['bytes'] += 1
        with self.assertRaisesRegex(ValueError, 'GLB size'):
            verify(self.capture, m, self.requests, self.run_id)

    def test_unknown_collector_source_red(self):
        m = copy.deepcopy(self.server.manifest); m['diagnostics']['collectorSha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'collector source'):
            verify(self.capture, m, self.requests, self.run_id)

    def test_resource_byte_mismatch_red(self):
        c = copy.deepcopy(self.capture); c['startup']['resources'][-1]['encodedBodySize'] -= 1
        with self.assertRaisesRegex(ValueError, 'encoded bytes'):
            verify(c, self.server.manifest, self.requests, self.run_id)

    def test_outside_origin_red(self):
        c = copy.deepcopy(self.capture); c['startup']['resources'][0]['name'] = 'http://127.0.0.1:9201/other'
        with self.assertRaisesRegex(ValueError, 'scope mismatch'):
            verify(c, self.server.manifest, self.requests, self.run_id)

    def test_wrong_work_query_red(self):
        c = copy.deepcopy(self.capture); c['startup']['url'] = c['startup']['url'].replace(WORK_MEMBER, 'works/other.json')
        with self.assertRaisesRegex(ValueError, 'explicit common Work'):
            verify(c, self.server.manifest, self.requests, self.run_id)

    def test_wrong_physical_geometry_red(self):
        c = copy.deepcopy(self.capture); c['startup']['geometry']['canvasBacking']['width'] = 1279
        with self.assertRaisesRegex(ValueError, 'canvas backing'):
            verify(c, self.server.manifest, self.requests, self.run_id)

    def test_wrong_work_body_red(self):
        r = copy.deepcopy(self.requests); r[-1]['responseBodySha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'response hash'):
            verify(self.capture, self.server.manifest, r, self.run_id)

    def test_same_url_contrast_only_once(self):
        target = f'/run/{self.run_id}/index.html'
        self.assertEqual(self.server.response('GET', target, '')[0], 200)
        self.assertEqual(self.server.response('GET', target, '')[0], 409)

    def test_variant_missing_rejected(self):
        with self.assertRaisesRegex(ValueError, 'variant metadata'):
            timestamp_variant(None, True)

    def test_baseline_cannot_hide_variant(self):
        with self.assertRaisesRegex(ValueError, 'baseline'):
            timestamp_variant({}, False)


class ReceiverControls(unittest.TestCase):
    def test_actual_http_partial_timeout_then_valid_and_rejects(self):
        """Real ephemeral TCP boundary. No app/browser/GPU; all threads joined."""
        initial_threads = {t.ident for t in threading.enumerate()}
        with tempfile.TemporaryDirectory() as directory:
            http, experiment = prepare(Path(directory) / 'evidence', 9205, 1)
            run = experiment.run_ids[0]
            experiment.response('GET', f'/run/{run}/index.html', '')
            server = bounded_server(http, ('127.0.0.1', 0), handler_for(http, experiment))
            thread = threading.Thread(target=server.serve_forever)
            thread.start()
            port = server.server_address[1]
            target = f'/run/{run}/capture.json'
            origin = 'http://127.0.0.1:9205'
            capture_path = experiment.evidence / f'{run}-attempt1-browser.json'
            try:
                for headers, body in [({'Origin': origin, 'Content-Length': '512001'}, b''),
                        ({'Origin': 'http://wrong.invalid', 'Content-Length': '1'}, b'x'),
                        ({'Origin': origin, 'Content-Length': '0'}, b'')]:
                    connection = HTTPConnection('127.0.0.1', port, timeout=2)
                    try:
                        connection.request('POST', target, body, headers)
                        response = connection.getresponse()
                        self.assertEqual(response.status, 409)
                        response.read()
                    finally:
                        connection.close()
                    self.assertFalse(capture_path.exists())
                with socket.create_connection(('127.0.0.1', port), timeout=2) as client:
                    client.settimeout(7)
                    headers = f'POST {target} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nOrigin: {origin}\r\nContent-Length: 100\r\n\r\n'
                    started = time.perf_counter()
                    client.sendall(headers.encode() + b'{')
                    response = client.recv(4096)
                    self.assertIn(b' 408 ', response)
                    self.assertGreaterEqual(time.perf_counter() - started, 4.5)
                    self.assertLess(time.perf_counter() - started, 7)
                self.assertFalse(capture_path.exists())
                # Truncated body with EOF is rejected immediately, no file.
                with socket.create_connection(('127.0.0.1', port), timeout=2) as client:
                    client.sendall(headers.encode() + b'{')
                    client.shutdown(socket.SHUT_WR)
                    self.assertIn(b' 409 ', client.recv(4096))
                self.assertFalse(capture_path.exists())
                payload = json.dumps({'schema': 'nvwa-web-perf-browser-v1', 'startup': {'runId': run}}).encode()
                connection = HTTPConnection('127.0.0.1', port, timeout=2)
                try:
                    connection.request('POST', target, payload, {'Origin': origin, 'Content-Length': str(len(payload))})
                    response = connection.getresponse()
                    self.assertEqual(response.status, 201)
                    response.read()
                finally:
                    connection.close()
                self.assertEqual(capture_path.read_bytes(), payload)
                rows = [json.loads(line) for line in (experiment.evidence / 'receiver.jsonl').read_text().splitlines()]
                self.assertTrue(any(row['status'] == 408 for row in rows))
                self.assertTrue(any(row['status'] == 201 for row in rows))
                self.assertLessEqual(server.accepted_requests, 256)
                evidence = {'kind': 'actual ephemeral TCP receiver control; not browser/GPU',
                    'ownedPid': os.getpid(), 'bind': '127.0.0.1', 'ephemeralPort': port,
                    'acceptedRequests': server.accepted_requests, 'receiverRows': rows,
                    'validPayloadSha256': hashlib.sha256(payload).hexdigest(), 'validPayloadBytes': len(payload)}
            finally:
                server.shutdown(); server.server_close(); thread.join(timeout=2)
            self.assertFalse(thread.is_alive(), 'owned HTTP server thread joined')
            self.assertEqual({t.ident for t in threading.enumerate()}, initial_threads, 'all owned handler/deadline threads joined')
            evidence['lifecycle'] = 'listener closed; server, handler and deadline threads joined'
            destination = os.environ.get('NVWA_WEB_CPU_EVIDENCE')
            if destination:
                path = Path(destination).resolve()
                if not path.is_relative_to(REPO / '.work/m11-perf/web'):
                    raise ValueError('CPU evidence must stay within own private scope')
                with path.open('x') as out:
                    out.write(json.dumps(evidence, indent=2) + '\n')


class ActualFaviconControls(unittest.TestCase):
    """Actual frozen first startup plus narrow semantic mutations; no renderer."""
    @classmethod
    def setUpClass(cls):
        root = REPO / '.work/m11-perf/web/baseline-http'
        cls.run_id = '1c1f52dcadf5449ba40195226e16f287'
        paths = (root / f'{cls.run_id}-attempt1-browser.json', root / 'manifest.json', root / 'requests.jsonl')
        if not all(path.is_file() for path in paths):
            raise unittest.SkipTest('actual private first dataset not supplied; fixture tests remain distinct')
        cls.capture = json.loads(paths[0].read_text())
        cls.manifest = json.loads(paths[1].read_text())
        cls.requests = [json.loads(line) for line in paths[2].read_text().splitlines() if line]

    def mutated(self):
        capture, manifest, requests = copy.deepcopy((self.capture, self.manifest, self.requests))
        timing = next(x for x in capture['startup']['resources'] if x['name'].endswith('/favicon.ico'))
        response = next(x for x in requests if x.get('target') == '/favicon.ico')
        return capture, manifest, requests, timing, response

    def rejected(self, capture, manifest, requests):
        with self.assertRaises(ValueError):
            verify(capture, manifest, requests, self.run_id)

    def test_actual_favicon_restored_green(self):
        result = verify(self.capture, self.manifest, self.requests, self.run_id)
        self.assertEqual(result['optionalFavicon']['bodyBytesWritten'], 19)
        self.assertEqual(result['http']['bodyBytesWrittenIncludingOptionalFavicon'], result['http']['bodyBytesWritten'] + 19)

    def test_favicon_status_red(self):
        c, m, r, t, response = self.mutated(); response['status'] = 500
        self.rejected(c, m, r)

    def test_favicon_timing_status_red(self):
        c, m, r, t, response = self.mutated(); t['responseStatus'] = 500
        self.rejected(c, m, r)

    def test_favicon_hash_red(self):
        c, m, r, t, response = self.mutated(); response['responseBodySha256'] = '0' * 64
        self.rejected(c, m, r)

    def test_favicon_server_size_red(self):
        c, m, r, t, response = self.mutated(); response['bodyBytesWritten'] = 18
        self.rejected(c, m, r)

    def test_favicon_browser_size_red(self):
        c, m, r, t, response = self.mutated(); t['decodedBodySize'] = 18
        self.rejected(c, m, r)

    def test_favicon_zero_transfer_red(self):
        c, m, r, t, response = self.mutated(); t['transferSize'] = 0
        self.rejected(c, m, r)

    def test_favicon_nonzero_transfer20_red(self):
        c, m, r, t, response = self.mutated(); t['transferSize'] = 20
        self.rejected(c, m, r)

    def test_favicon_nonzero_transfer318_red(self):
        c, m, r, t, response = self.mutated(); t['transferSize'] = 318
        self.rejected(c, m, r)

    def test_favicon_nonzero_transfer320_red(self):
        c, m, r, t, response = self.mutated(); t['transferSize'] = 320
        self.rejected(c, m, r)

    def test_favicon_unobserved_producer_red(self):
        c, m, r, t, response = self.mutated()
        c['startup']['userAgent'] = c['startup']['userAgent'].replace('Chrome/155.', 'Chrome/156.')
        self.rejected(c, m, r)

    def test_favicon_origin_red(self):
        c, m, r, t, response = self.mutated(); t['name'] = t['name'].replace(':9205/', ':9201/')
        self.rejected(c, m, r)

    def test_favicon_other_path_red(self):
        c, m, r, t, response = self.mutated(); t['name'] = t['name'].replace('favicon.ico', 'other.ico')
        self.rejected(c, m, r)

    def test_favicon_missing_response_red(self):
        c, m, r, t, response = self.mutated(); r.remove(response)
        self.rejected(c, m, r)

    def test_favicon_duplicate_timing_red(self):
        c, m, r, t, response = self.mutated(); c['startup']['resources'].append(copy.deepcopy(t))
        self.rejected(c, m, r)

    def test_favicon_source_red(self):
        c, m, r, t, response = self.mutated(); m['adapter']['baseServerSha256'] = '0' * 64
        self.rejected(c, m, r)

    def test_favicon_cache_control_red(self):
        c, m, r, t, response = self.mutated(); response['cacheControl'] = 'public'
        self.rejected(c, m, r)

    def test_unexplained_outside_resource_red(self):
        c, m, r, t, response = self.mutated()
        extra = copy.deepcopy(t); extra['name'] = extra['name'].replace('favicon.ico', 'other.ico')
        c['startup']['resources'].append(extra)
        self.rejected(c, m, r)

    def test_unexplained_outside_response_red(self):
        c, m, r, t, response = self.mutated()
        extra = copy.deepcopy(response); extra['target'] = '/other.ico'
        r.append(extra)
        self.rejected(c, m, r)


if __name__ == '__main__':
    unittest.main()
