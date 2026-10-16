"""Portable reproduction controls. Never edits protected inputs or goldens."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import directions


class PortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native = directions.evaluate('native')
        cls.golden = json.loads((directions.HERE/'retained-native-directions.json').read_text())
        cls.temporary_parent = directions.ROOT/'.work/runtime-pose-attribution-check'
        cls.temporary_parent.mkdir(parents=True, exist_ok=True)

    def test_same_native_sample_values_as_retained_record(self):
        self.assertEqual(self.native['samples'], self.golden['samples'])
        self.assertEqual(self.native['numerical_controls'], self.golden['numerical_controls'])
        self.assertEqual(self.native['verified_url_byte_receipts'], self.golden['verified_url_byte_receipts'])

    def test_web_same_sample_direction_values(self):
        web = directions.evaluate('web')
        self.assertEqual(web['samples'], self.native['samples'])
        self.assertEqual(web['source_text_audit']['status'], 'NOT-RUN')

    def test_default_does_not_claim_fresh_source_text_inspection(self):
        self.assertEqual(self.native['source_text_audit']['status'], 'NOT-RUN')
        self.assertEqual(len(self.native['recorded_source_hashes']), 6)
        self.assertTrue(all(name.startswith('cached-original-source/') for name in self.native['recorded_source_hashes']))

    def test_original_four_numeric_controls_pass(self):
        self.assertEqual(len(self.native['numerical_controls']), 4)
        self.assertTrue(all(self.native['numerical_controls'].values()))

    def test_retained_output_directory_rejected(self):
        with self.assertRaisesRegex(ValueError, 'fresh and outside retained'):
            directions.output_target(directions.HERE/'new-golden.json')

    def test_existing_output_file_rejected(self):
        with tempfile.TemporaryDirectory(dir=self.temporary_parent) as directory:
            path = Path(directory)/'existing.json'
            path.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'fresh and outside retained'):
                directions.output_target(path)

    def test_missing_source_cache_fails_without_fetch(self):
        with tempfile.TemporaryDirectory(dir=self.temporary_parent) as directory:
            with self.assertRaisesRegex(ValueError, 'cache pin mismatch'):
                directions.evaluate('native', Path(directory))

    def test_wrong_input_pin_fails(self):
        with tempfile.TemporaryDirectory(dir=self.temporary_parent) as directory:
            path = Path(directory)
            (path/'input-pins.json').write_text(json.dumps({'experiments/41-real-short-motion/source-skeleton.json': '0'*64}))
            with patch.object(directions, 'HERE', path):
                with self.assertRaisesRegex(ValueError, 'repository input pin mismatch'):
                    directions.verify_inputs()

    def test_partial_capture_rejected(self):
        capture = directions.read('experiments/49-runtime-pose-parity/probe/results/native.json')
        capture['samples'].pop()
        with self.assertRaisesRegex(ValueError, 'complete fixed-seven'):
            directions.validate_capture(capture, 'native')

    def test_boolean_key_rejected(self):
        capture = directions.read('experiments/49-runtime-pose-parity/probe/results/native.json')
        capture['samples'][0]['source_key_index'] = False
        with self.assertRaisesRegex(ValueError, 'complete fixed-seven'):
            directions.validate_capture(capture, 'native')

    def test_wrong_platform_rejected(self):
        capture = directions.read('experiments/49-runtime-pose-parity/probe/results/native.json')
        with self.assertRaisesRegex(ValueError, 'complete fixed-seven'):
            directions.validate_capture(capture, 'web')


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(PortTests)
    names = [test.id() for test in suite]
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({'status': 'PASS' if result.wasSuccessful() else 'FAIL', 'tests': result.testsRun, 'names': names}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
