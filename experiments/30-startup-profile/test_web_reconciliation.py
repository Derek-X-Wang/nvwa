#!/usr/bin/env python3
"""Bounded pure-data red/green controls on the actual retained Web packet."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

import reconcile_web_baseline as adapter

PACKET = adapter.REPO / '.work/m11-startup/captures/web-baseline'
RECEIPTS = adapter.HERE / 'WEB-RECONCILIATION-CONTROLS.json'


class ActualPacketControls(unittest.TestCase):
    results = []

    def setUp(self):
        capture, manifest, requests, packet, receipt = adapter.load_packet(PACKET)
        self.args = [deepcopy(capture), deepcopy(manifest), deepcopy(requests), packet, deepcopy(receipt)]

    def row(self, name):
        if name == 'favicon.ico':
            return next(x for x in self.args[2] if x['target'] == '/favicon.ico')
        return next(x for x in self.args[2] if x['member'] == name)

    def reject(self, label, mutate):
        mutate()
        start = time.monotonic()
        with self.assertRaises((ValueError, KeyError, TypeError)) as caught:
            adapter.verify(*self.args)
        self.results.append({'case': label, 'expected': 'FAIL', 'actual': 'FAIL',
                             'reason': str(caught.exception), 'elapsedSeconds': time.monotonic() - start})

    def test_actual_green(self):
        result = adapter.verify(*self.args)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['ledgerGetCount'], 8)
        self.assertEqual(result['successfulRunGetCount'], 6)
        self.assertEqual(result['browserTimingEntryCount'], 7)
        self.assertEqual([x['bodyBytes'] for x in result['explicit404Dispositions']], [19, 28])
        self.results.append({'case': 'unchanged actual packet', 'expected': 'PASS', 'actual': 'PASS', 'result': result})

    def test_wrong_response_hash(self):
        self.reject('GLB response hash mismatch', lambda: self.row('assets/fixtures/nvwa-humanoid.glb').update(responseBodySha256='0' * 64))

    def test_wrong_success_status(self):
        self.reject('Wasm response status500', lambda: self.row('nvwa_studio_bg.wasm').update(status=500))

    def test_wrong_request_run(self):
        self.reject('canonical Work request run mismatch', lambda: self.row(adapter.WORK).update(runId='0' * 32))

    def test_wrong_browser_run(self):
        self.reject('browser run mismatch', lambda: self.args[0].update(runId='0' * 32))

    def test_wrong_work_url(self):
        self.reject('browser Work URL replacement', lambda: self.args[0].update(url=self.args[0]['url'].replace(adapter.WORK, 'works/m1-sequence.nvwa.json')))

    def test_wrong_work_manifest_hash(self):
        self.reject('canonical Work manifest hash mismatch', lambda: self.args[1]['frozenFiles'][adapter.WORK].update(sha256='0' * 64))

    def test_work_missing(self):
        self.reject('canonical Work request missing', lambda: self.args[2].remove(self.row(adapter.WORK)))

    def test_work_response_wrong_member(self):
        self.reject('canonical Work request target replacement', lambda: self.row(adapter.WORK).update(target=self.row(adapter.WORK)['target'].replace(adapter.WORK, 'works/m1-sequence.nvwa.json')))

    def test_favicon_wrong_hash(self):
        self.reject('favicon404 wrong bytes hash', lambda: self.row('favicon.ico').update(responseBodySha256='0' * 64))

    def test_favicon_wrong_status(self):
        self.reject('favicon status500', lambda: self.row('favicon.ico').update(status=500))

    def test_favicon_wrong_run(self):
        self.reject('favicon404 assigned run', lambda: self.row('favicon.ico').update(runId=self.args[0]['runId']))

    def test_favicon_wrong_location(self):
        self.reject('favicon404 arbitrary location', lambda: self.row('favicon.ico').update(target='/other.ico'))

    def test_favicon_incomplete(self):
        self.reject('favicon404 incomplete writes', lambda: self.row('favicon.ico').update(bodyBytesWritten=0))

    def test_extra_failed_request(self):
        self.reject('extra arbitrary failed response', lambda: self.args[2].append({**self.row('favicon.ico'), 'target': '/unexpected', 'member': None}))

    def test_missing_browser_work(self):
        self.reject('canonical Work browser timing missing', lambda: self.args[0]['resources'].__setitem__(slice(None), [x for x in self.args[0]['resources'] if not x['name'].endswith(adapter.WORK)]))

    def test_browser_status_mismatch(self):
        self.reject('browser favicon status mismatch', lambda: next(x for x in self.args[0]['resources'] if x['name'].endswith('/favicon.ico')).update(responseStatus=200))

    def test_meta_hash_mismatch(self):
        self.reject('optional metadata404 hash mismatch', lambda: self.row(adapter.META).update(responseBodySha256='0' * 64))

    def test_port_mismatch(self):
        self.reject('wrong9201 browser origin', lambda: self.args[0].update(url=self.args[0]['url'].replace(':9203', ':9201')))


def snapshot24():
    return {str(p.relative_to(adapter.E24)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(adapter.E24.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def original_red():
    # Run original validator against raw packet, then an owned in-memory9201
    # fixture to expose its unchanged favicon restriction. No archive rewrite.
    source = adapter.E24 / 'verify_capture.py'
    raw = subprocess.run([sys.executable, '-B', str(source), '--capture', str(PACKET / 'browser.json'),
                          '--manifest', str(PACKET / 'manifest.json'), '--requests', str(PACKET / 'requests.jsonl'),
                          '--run', json.loads((PACKET / 'browser.json').read_text())['runId']],
                         capture_output=True, text=True, timeout=5)
    require_red = {'raw9203': {'returncode': raw.returncode, 'stderr': raw.stderr}}
    with tempfile.TemporaryDirectory(prefix='web-red-', dir=adapter.REPO / '.work/m11-startup') as directory:
        path = Path(directory)
        capture, manifest, rows, _, _ = adapter.load_packet(PACKET)
        capture['url'] = capture['url'].replace(':9203', ':9201')
        for x in capture['navigation'] + capture['resources']:
            x['name'] = x['name'].replace(':9203', ':9201')
        manifest['port'] = 9201
        for name, obj in [('browser.json', capture), ('manifest.json', manifest)]:
            (path / name).write_text(json.dumps(obj))
        red = subprocess.run([sys.executable, '-B', str(source), '--capture', str(path / 'browser.json'),
                              '--manifest', str(path / 'manifest.json'), '--requests', str(PACKET / 'requests.jsonl'),
                              '--run', capture['runId']], capture_output=True, text=True, timeout=5)
        require_red['normalized9201StillRejectsFavicon'] = {'returncode': red.returncode, 'stderr': red.stderr,
            'normalization': 'owned temporary fixture origin/manifest port only; original source/raw records unchanged'}
    if raw.returncode == 0 or red.returncode == 0:
        raise AssertionError('original mismatch control unexpectedly green')
    return require_red


if __name__ == '__main__':
    before = snapshot24()
    reds = original_red()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ActualPacketControls)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    after = snapshot24()
    receipt = {'status': 'PASS' if result.wasSuccessful() and before == after else 'FAIL',
               'testCount': result.testsRun, 'actualRendererRunByTests': False,
               'sourceSha256': hashlib.sha256(Path(adapter.__file__).read_bytes()).hexdigest(),
               'testSourceSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'originalValidatorRedControls': reds, 'controls': ActualPacketControls.results,
               'experiment24Unchanged': before == after, 'experiment24HashesBefore': before, 'experiment24HashesAfter': after}
    RECEIPTS.write_text(json.dumps(receipt, indent=2) + '\n')
    sys.exit(0 if receipt['status'] == 'PASS' else 1)
