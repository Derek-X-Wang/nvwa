"""CPU-only fixture tests. No browser, GPU, build or experiment listener."""
import copy
import gzip
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer

from server import Experiment, digest, handler_for
from verify_capture import CRITICAL, verify

RUN = 'a' * 32
OTHER = 'b' * 32


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'web'
        self.root.mkdir()
        fixture = {'index.html': b'<html><head></head><body><script type="module">PRODUCTION</script></body></html>',
                   'nvwa_studio.js': b'export default 123;', 'nvwa_studio_bg.wasm': b'\x00asm' * 100,
                   'assets/fixtures/nvwa-humanoid.glb': b'glTF' * 100,
                   'works/example.nvwa.json': b'{"profile":{}}'}
        for name, data in fixture.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            if name != 'works/example.nvwa.json':
                Path(str(path) + '.gz').write_bytes(gzip.compress(data, mtime=0))
        (self.root / 'private.txt').write_text('never serve')
        self.exp = Experiment(self.root, Path(self.temp.name) / 'evidence', [RUN, OTHER])

    def request(self, name, run=RUN, encoding='gzip', method='GET'):
        return self.exp.response(method, f'/run/{run}/{name}', encoding)

    def test_each_startup_has_fresh_single_use_prefix_and_identical_wrapper(self):
        first = self.request('index.html')
        second = self.request('index.html', OTHER)
        self.assertEqual(first[:4], second[:4])
        self.assertIn(b'PRODUCTION', first[1])
        self.assertIn(b'startup-diagnostics.js', first[1])
        self.assertEqual(self.request('index.html')[0], 409)
        self.assertEqual(self.request('index.html', 'c' * 32)[0], 404)

    def test_frozen_gzip_and_identity_exact_bytes_and_q_zero(self):
        name = 'nvwa_studio_bg.wasm'
        compressed = self.request(name)
        self.assertEqual(compressed[3], 'gzip')
        self.assertEqual(compressed[1], (self.root / (name + '.gz')).read_bytes())
        for header in ('gzip;q=0', 'gzip;q=0, *;q=1', 'br', 'gzip;q=wrong'):
            identity = self.request(name, encoding=header)
            self.assertEqual(identity[3], 'identity')
            self.assertEqual(gzip.decompress(compressed[1]), identity[1])

    def test_rejects_corrupt_gzip_at_freeze_and_changed_response_after_freeze(self):
        path = self.root / 'nvwa_studio.js.gz'
        path.write_bytes(gzip.compress(b'different production', mtime=0))
        with self.assertRaisesRegex(ValueError, 'not exact frozen'):
            Experiment(self.root, Path(self.temp.name) / 'bad')
        self.assertEqual(self.request('nvwa_studio.js')[0], 409)

    def test_traversal_private_files_and_directory_listing_are_unavailable(self):
        for name in ('../private.txt', '%2e%2e/private.txt', '%252e%252e/private.txt',
                     'assets/../../private.txt', 'assets\\..\\private.txt', 'assets//a'):
            self.assertEqual(self.request(name)[0], 400, name)
        for name in ('private.txt', 'assets', 'assets/', 'nvwa_studio.js.gz'):
            self.assertNotEqual(self.request(name)[0], 200, name)
        outside = Path(self.temp.name) / 'outside'
        outside.write_text('private')
        (self.root / 'assets/secret').symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'escapes frozen root'):
            Experiment(self.root, Path(self.temp.name) / 'symlink')

    def test_actual_http_has_no_store_ignores_conditional_cache_and_logs_body(self):
        # Temporary ephemeral fixture listener only; never reserved port9201.
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(self.exp))
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            conn = http.client.HTTPConnection(*server.server_address)
            name = 'nvwa_studio_bg.wasm'
            target = f'/run/{RUN}/{name}'
            for method in ('GET', 'GET', 'HEAD', 'TRACE'):
                conn.request(method, target, headers={'Accept-Encoding': 'gzip',
                    'If-None-Match': '*', 'If-Modified-Since': 'Wed, 31 Dec 2099 00:00:00 GMT'})
                response = conn.getresponse()
                body = response.read()
                self.assertEqual(response.getheader('Cache-Control'), 'no-store')
                self.assertEqual(response.status, 405 if method == 'TRACE' else 200)
                if method == 'GET':
                    self.assertEqual(body, (self.root / (name + '.gz')).read_bytes())
            conn.close()
        finally:
            server.shutdown()
            server.server_close()
            worker.join()
        rows = [json.loads(line) for line in (self.exp.evidence / 'requests.jsonl').read_text().splitlines()]
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]['bodyBytesWritten'], (self.root / (name + '.gz')).stat().st_size)
        self.assertEqual(rows[0]['responseBodySha256'], digest((self.root / (name + '.gz')).read_bytes()))
        self.assertEqual(rows[2]['bodyBytesWritten'], 0)
        self.assertTrue(all(row['elapsedMs'] >= 0 and row['cacheControl'] == 'no-store' for row in rows))

    def fixture_capture(self):
        requests, timing = [], []
        for index, name in enumerate(CRITICAL):
            status, body, _mime, encoding, _run, _name = self.request(name)
            self.assertEqual(status, 200)
            requests.append({'method': 'GET', 'target': f'/run/{RUN}/{name}', 'runId': RUN,
                'member': name, 'status': status, 'cacheControl': 'no-store', 'contentEncoding': encoding,
                'responseBodySha256': digest(body), 'declaredBodyBytes': len(body), 'bodyBytesWritten': len(body), 'interrupted': None})
            decoded = len(gzip.decompress(body)) if encoding == 'gzip' else len(body)
            timing.append({'name': f'http://127.0.0.1:9201/run/{RUN}/{name}',
                'entryType': 'navigation' if index == 0 else 'resource', 'startTime': index,
                'duration': 10, 'responseEnd': index + 10, 'transferSize': len(body) + 300,
                'encodedBodySize': len(body), 'decodedBodySize': decoded})
        capture = {'schema': 'nvwa-http-startup-browser-v1', 'runId': RUN,
            'url': timing[0]['name'], 'clock': 'Performance monotonic milliseconds since navigation timeOrigin',
            'timeOriginEpochMs': 1234, 'snapshotAtMs': 100, 'installedAtMs': 1,
            'navigation': timing[:1], 'resources': timing[1:], 'milestones': []}
        return capture, requests

    def test_reconciliation_accepts_complete_fixture_not_browser_proof(self):
        capture, requests = self.fixture_capture()
        result = verify(capture, self.exp.manifest, requests, RUN)
        self.assertEqual(result['actualGetRequests'], 5)
        self.assertEqual(result['exactFirstPresentation'], 'NOT-RUN')

    def test_cold_claim_rejects_missing_wasm_glb_cached_forged_and_failed_records(self):
        capture, requests = self.fixture_capture()
        for name in ('nvwa_studio_bg.wasm', 'assets/fixtures/nvwa-humanoid.glb'):
            with self.subTest(missing=name), self.assertRaises(ValueError):
                verify(capture, self.exp.manifest, [row for row in requests if row['member'] != name], RUN)
        for field, value in (('status', 304), ('cacheControl', 'max-age=3600'),
                             ('responseBodySha256', '0' * 64), ('bodyBytesWritten', 0)):
            broken = copy.deepcopy(requests)
            broken[3][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                verify(capture, self.exp.manifest, broken, RUN)
        cached = copy.deepcopy(capture)
        cached['resources'][2]['transferSize'] = 0
        with self.assertRaisesRegex(ValueError, 'cached transfer'):
            verify(cached, self.exp.manifest, requests, RUN)
        missing = copy.deepcopy(capture)
        missing['resources'].pop()
        with self.assertRaisesRegex(ValueError, 'critical resource timing'):
            verify(missing, self.exp.manifest, requests, RUN)

    def test_malformed_timing_and_mixed_clock_never_pass(self):
        capture, requests = self.fixture_capture()
        for field, value in (('responseEnd', -1), ('duration', float('nan')),
                             ('transferSize', True), ('encodedBodySize', 1.5), ('responseEnd', 1000)):
            broken = copy.deepcopy(capture)
            broken['resources'][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                verify(broken, self.exp.manifest, requests, RUN)
        capture['clock'] = 'bevy_TimeReal_since_first_update'
        with self.assertRaisesRegex(ValueError, 'clock'):
            verify(capture, self.exp.manifest, requests, RUN)


class ActualStartupTests(unittest.TestCase):
    def setUp(self):
        self.actual = json.loads((Path(__file__).parent / 'fixtures/actual-startup-1.json').read_text())

    def verify_actual(self):
        actual = self.actual
        return verify(actual['capture'], actual['manifest'], actual['requests'], actual['capture']['runId'])

    def test_actual_optional_metadata_fallback_is_explicit_and_critical_bodies_match(self):
        result = self.verify_actual()
        self.assertEqual(result['actualGetRequests'], 5)
        self.assertEqual(len(result['optionalMissingSidecars']), 1)
        self.assertEqual(result['optionalMissingSidecars'][0]['status'], 404)
        self.assertEqual(result['optionalMissingSidecars'][0]['member'], 'assets/fixtures/nvwa-humanoid.glb.meta')

    def test_actual_critical_glb_404_and_unexpected_404_remain_red(self):
        for member in ('assets/fixtures/nvwa-humanoid.glb', 'assets/fixtures/unexpected.meta'):
            self.setUp()
            rows = self.actual['requests']
            if member.endswith('glb'):
                next(row for row in rows if row['member'] == member)['status'] = 404
            else:
                optional = copy.deepcopy(next(row for row in rows if row['status'] == 404))
                optional['member'] = member
                optional['target'] = f'/run/{self.actual["capture"]["runId"]}/{member}'
                rows.append(optional)
            with self.subTest(member=member), self.assertRaises(ValueError):
                self.verify_actual()

    def test_optional_sidecar_exception_does_not_accept_failed_or_frozen_metadata(self):
        for field, value in (('status', 500), ('cacheControl', 'max-age=3600'),
                             ('bodyBytesWritten', 0), ('responseBodySha256', '0' * 64)):
            self.setUp()
            next(row for row in self.actual['requests'] if row['status'] == 404)[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.verify_actual()
        self.setUp()
        self.actual['manifest']['frozenFiles']['assets/fixtures/nvwa-humanoid.glb.meta'] = {'bytes': 28, 'sha256': '0' * 64}
        with self.assertRaises(ValueError):
            self.verify_actual()


if __name__ == '__main__':
    unittest.main()
