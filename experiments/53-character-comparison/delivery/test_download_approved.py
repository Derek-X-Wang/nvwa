"""Offline controls for the real approved-delivery fetch() seam.

Run in the approved research checkout; module admission reads its fixed local
manifest/authorization metadata. Every fetch output is confined to a temp folder.
"""
from pathlib import Path
from io import BytesIO
import hashlib
import runpy
import tempfile
import unittest
from unittest.mock import patch

MODULE = runpy.run_path(str(Path(__file__).with_name('download_approved.py')), run_name='offline_fetch_controls')
FETCH = MODULE['fetch']
ROOT = MODULE['ROOT']
URL = 'https://example.invalid/approved-control'
GOOD = b'APPROVED-CONTROL'
STALE = b'INTERRUPTED-PART'


def digest(body):
    return hashlib.sha256(body).hexdigest()


def blob(body):
    return hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest()


class Response(BytesIO):
    def __init__(self, body, url=URL):
        super().__init__(body)
        self.url = url
        self.headers = {'Content-Length': str(len(body))}


class FetchControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='fetch-offline-control-', dir=ROOT / '.work')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.destination = self.root / 'approved.bin'
        self.stale = self.root / 'approved.bin.part'
        self.destination.write_bytes(GOOD)
        self.stale.write_bytes(STALE)
        self.network = patch('urllib.request.urlopen', side_effect=AssertionError('unexpected network access'))
        self.transport = self.network.start()
        self.addCleanup(self.network.stop)

    def test_existing_sha_verified_destination_ignores_and_preserves_stale_part(self):
        receipt = FETCH(URL, self.destination, len(GOOD), sha256=digest(GOOD))
        self.assertEqual(self.destination.read_bytes(), GOOD)
        self.assertEqual(self.stale.read_bytes(), STALE)
        self.assertEqual(receipt['sha256'], digest(self.destination.read_bytes()))
        self.assertEqual(receipt['downloaded_bytes'], 0)
        self.transport.assert_not_called()

    def test_existing_git_blob_verified_destination_ignores_and_preserves_stale_part(self):
        receipt = FETCH(URL, self.destination, len(GOOD), git_blob_sha1=blob(GOOD))
        self.assertEqual(self.destination.read_bytes(), GOOD)
        self.assertEqual(self.stale.read_bytes(), STALE)
        self.assertEqual(receipt['git_blob_sha1'], blob(GOOD))
        self.transport.assert_not_called()

    def test_existing_reject_preserves_destination_and_stale_part(self):
        with self.assertRaises(ValueError):
            FETCH(URL, self.destination, len(GOOD), sha256=digest(b'other'))
        self.assertEqual(self.destination.read_bytes(), GOOD)
        self.assertEqual(self.stale.read_bytes(), STALE)
        self.transport.assert_not_called()

    def test_git_blob_reject_preserves_destination_and_stale_part(self):
        with self.assertRaisesRegex(ValueError, 'Git blob SHA1 mismatch'):
            FETCH(URL, self.destination, len(GOOD), git_blob_sha1=blob(b'other'))
        self.assertEqual(self.destination.read_bytes(), GOOD)
        self.assertEqual(self.stale.read_bytes(), STALE)
        self.transport.assert_not_called()

    def test_fresh_mocked_download_promotes_only_verified_current_bytes(self):
        self.destination.unlink()
        self.transport.side_effect = lambda request, timeout: Response(GOOD)
        receipt = FETCH(URL, self.destination, len(GOOD), sha256=digest(GOOD), git_blob_sha1=blob(GOOD))
        self.assertEqual(self.destination.read_bytes(), GOOD)
        self.assertEqual(self.stale.read_bytes(), STALE)
        self.assertEqual(receipt['downloaded_bytes'], len(GOOD))
        self.assertEqual(receipt['sha256'], digest(self.destination.read_bytes()))
        self.assertEqual(self.transport.call_count, 1)

    def test_fresh_hash_reject_preserves_existing_stale_part(self):
        self.destination.unlink()
        self.transport.side_effect = lambda request, timeout: Response(GOOD)
        with self.assertRaises(ValueError):
            FETCH(URL, self.destination, len(GOOD), sha256=digest(b'wrong'))
        self.assertFalse(self.destination.exists())
        self.assertEqual(self.stale.read_bytes(), STALE)
        self.assertEqual(list(self.root.iterdir()), [self.stale])

    def test_mocked_network_failure_preserves_existing_stale_part(self):
        self.destination.unlink()
        self.transport.side_effect = OSError('offline control')
        with self.assertRaisesRegex(OSError, 'offline control'):
            FETCH(URL, self.destination, len(GOOD), sha256=digest(GOOD))
        self.assertFalse(self.destination.exists())
        self.assertEqual(self.stale.read_bytes(), STALE)

    def test_reused_license_is_checked_without_modifying_input_or_stale_part(self):
        self.destination.unlink()
        license_file = self.root / 'review-license.txt'
        license_file.write_bytes(GOOD)
        receipt = FETCH(URL, self.destination, len(GOOD), sha256=digest(GOOD), reuse=license_file)
        self.assertEqual(license_file.read_bytes(), GOOD)
        self.assertEqual(self.destination.read_bytes(), GOOD)
        self.assertEqual(self.stale.read_bytes(), STALE)
        self.assertEqual(receipt['downloaded_bytes'], 0)
        self.transport.assert_not_called()

    def test_reused_license_reject_preserves_input_and_stale_part(self):
        self.destination.unlink()
        license_file = self.root / 'review-license.txt'
        license_file.write_bytes(GOOD)
        with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'):
            FETCH(URL, self.destination, len(GOOD), sha256=digest(b'other'), reuse=license_file)
        self.assertEqual(license_file.read_bytes(), GOOD)
        self.assertFalse(self.destination.exists())
        self.assertEqual(self.stale.read_bytes(), STALE)
        self.assertEqual(set(self.root.iterdir()), {self.stale, license_file})
        self.transport.assert_not_called()

    def test_http_input_and_redirect_are_rejected_even_without_python_assertions(self):
        with self.assertRaises(ValueError):
            FETCH('http://example.invalid/control', self.destination, len(GOOD))
        self.destination.unlink()
        self.transport.side_effect = lambda request, timeout: Response(GOOD, 'http://example.invalid/control')
        with self.assertRaises(ValueError):
            FETCH(URL, self.destination, len(GOOD))
        self.assertFalse(self.destination.exists())
        self.assertEqual(self.stale.read_bytes(), STALE)

    def test_short_and_oversize_body_are_rejected_without_promoting(self):
        self.destination.unlink()
        for body in [b'X', GOOD + b'X']:
            with self.subTest(body=body):
                self.transport.side_effect = lambda request, timeout, body=body: Response(body)
                with self.assertRaises(ValueError):
                    FETCH(URL, self.destination, len(GOOD))
                self.assertFalse(self.destination.exists())
                self.assertEqual(self.stale.read_bytes(), STALE)


if __name__ == '__main__':
    unittest.main()
