"""Portable reproduction controls. Never edits protected inputs or goldens."""
import copy
import json
import math
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import directions
from reproduction_comparison import (ReproductionMismatch, assert_exact_samples,
                                    assert_retained_samples, bits)


class PortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native = directions.evaluate('native')
        cls.golden = json.loads((directions.HERE/'retained-native-directions.json').read_text())
        cls.temporary_parent = directions.ROOT/'.work/runtime-pose-attribution-check'
        cls.temporary_parent.mkdir(parents=True, exist_ok=True)

    def test_same_native_sample_values_as_retained_record(self):
        assert_retained_samples(self.golden['samples'], self.native['samples'])
        self.assertEqual(self.native['numerical_controls'], self.golden['numerical_controls'])
        self.assertEqual(self.native['verified_url_byte_receipts'], self.golden['verified_url_byte_receipts'])

    def test_web_same_sample_direction_values(self):
        web = directions.evaluate('web')
        assert_exact_samples(self.native['samples'], web['samples'])
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

    def test_retained_angle_two_ulps_allowed_three_rejected(self):
        expected = self.golden['samples']
        actual = copy.deepcopy(expected)
        row = actual[0]['directions']['upper_arm.L']
        field = 'raw_world_angle_deg'
        row[field] = math.nextafter(math.nextafter(row[field], math.inf), math.inf)
        assert_retained_samples(expected, actual)
        with self.assertRaises(ReproductionMismatch):
            assert_exact_samples(expected, actual)
        row[field] = math.nextafter(row[field], math.inf)
        with self.assertRaisesRegex(ReproductionMismatch, 'distance 3 ULP'):
            assert_retained_samples(expected, actual)

    def test_actual_ubuntu_measurement_replayed_through_retained_comparison(self):
        record = json.loads((directions.HERE/'portable-ubuntu-measurement.json').read_text())
        expected = self.golden['samples']
        actual = copy.deepcopy(expected)
        differences = record['native_vs_retained']['float_differences']
        self.assertEqual(len(differences), 55)
        for difference in differences:
            parts = difference['path'].split('/')[1:]
            cursor = actual
            for part in parts[:-1]:
                cursor = cursor[int(part)] if type(cursor) is list else cursor[part]
            leaf = int(parts[-1]) if type(cursor) is list else parts[-1]
            self.assertEqual('%016x' % bits(cursor[leaf]), difference['expected_binary64_hex'])
            cursor[leaf] = struct.unpack('>d', bytes.fromhex(difference['actual_binary64_hex']))[0]
        assert_retained_samples(expected, actual)
        with self.assertRaises(ReproductionMismatch):
            assert_exact_samples(expected, actual)

    def test_direction_one_ulp_and_position_mutation_rejected(self):
        expected = self.golden['samples']
        for position in (False, True):
            actual = copy.deepcopy(expected)
            vector = (actual[0]['elbow_and_reach']['Right']['target_hand_minus_shoulder_m'] if position
                      else actual[0]['directions']['upper_arm.L']['target_actual_world'])
            vector[0] = vector[0]+.01 if position else math.nextafter(vector[0], math.inf)
            with self.assertRaisesRegex(ReproductionMismatch, 'binary64 value differs'):
                assert_retained_samples(expected, actual)

    def test_new_missing_and_reordered_keys_rejected(self):
        expected = self.golden['samples']
        for change in ('new', 'missing', 'reorder'):
            actual = copy.deepcopy(expected)
            row = actual[0]['directions']['root']
            if change == 'new':
                row['new_angle_deg'] = 1.
            elif change == 'missing':
                del row['raw_world_angle_deg']
            else:
                row['source_joint'] = row.pop('source_joint')
            with self.assertRaisesRegex(ReproductionMismatch, 'keys/order differ'):
                assert_retained_samples(expected, actual)

    def test_unknown_angle_field_never_inherits_suffix_tolerance(self):
        expected = copy.deepcopy(self.golden['samples'])
        expected[0]['directions']['root']['new_angle_deg'] = 1.
        with self.assertRaisesRegex(ReproductionMismatch, 'unrecognized angle scalar path'):
            assert_retained_samples(expected, copy.deepcopy(expected))

    def test_types_discrete_key_time_and_list_order_exact(self):
        expected = self.golden['samples']
        for change in ('bool_key', 'float_key', 'key_value', 'time', 'list_order', 'angle_type'):
            actual = copy.deepcopy(expected)
            if change == 'bool_key':
                actual[0]['key_index'] = False
            elif change == 'float_key':
                actual[0]['key_index'] = 0.
            elif change == 'key_value':
                actual[0]['key_index'] = 1
            elif change == 'time':
                actual[1]['time_seconds'] = math.nextafter(actual[1]['time_seconds'], math.inf)
            elif change == 'list_order':
                actual[0], actual[1] = actual[1], actual[0]
            else:
                actual[0]['directions']['root']['raw_world_angle_deg'] = 1
            with self.assertRaises(ReproductionMismatch):
                assert_retained_samples(expected, actual)

    def test_nonfinite_expected_or_actual_and_signed_zero_rejected(self):
        for value in (float('nan'), float('inf'), -float('inf')):
            for side in ('expected', 'actual'):
                expected = copy.deepcopy(self.golden['samples'])
                actual = copy.deepcopy(expected)
                target = expected if side == 'expected' else actual
                target[0]['directions']['root']['raw_world_angle_deg'] = value
                with self.assertRaisesRegex(ReproductionMismatch, 'nonfinite'):
                    assert_retained_samples(expected, actual)
        expected = copy.deepcopy(self.golden['samples'])
        expected[0]['directions']['root']['raw_world_angle_deg'] = 0.
        actual = copy.deepcopy(expected)
        actual[0]['directions']['root']['raw_world_angle_deg'] = -0.
        with self.assertRaisesRegex(ReproductionMismatch, 'signed zero'):
            assert_retained_samples(expected, actual)
        actual[0]['directions']['root']['raw_world_angle_deg'] = -math.ulp(0.)
        with self.assertRaisesRegex(ReproductionMismatch, 'angle outside'):
            assert_retained_samples(expected, actual)

    def test_known_angle_range_checked_before_ulp_or_exact_equality(self):
        for value in (-math.ulp(0.), math.nextafter(180., math.inf)):
            for side in ('expected', 'actual', 'both'):
                expected = copy.deepcopy(self.golden['samples'])
                actual = copy.deepcopy(expected)
                for label, target in (('expected', expected), ('actual', actual)):
                    target[0]['directions']['root']['raw_world_angle_deg'] = value if side in (label, 'both') else (0. if value < 0 else 180.)
                with self.assertRaisesRegex(ReproductionMismatch, 'angle outside'):
                    assert_retained_samples(expected, actual)

    def test_native_web_exact_mode_rejects_even_one_angle_ulp(self):
        expected = self.golden['samples']
        actual = copy.deepcopy(expected)
        row = actual[0]['directions']['upper_arm.L']
        row['raw_world_angle_deg'] = math.nextafter(row['raw_world_angle_deg'], math.inf)
        with self.assertRaisesRegex(ReproductionMismatch, 'distance 1 ULP'):
            assert_exact_samples(expected, actual)

    def test_unmeasured_neutral_elbow_angle_remains_exact(self):
        expected = self.golden['samples']
        actual = copy.deepcopy(expected)
        row = actual[0]['elbow_and_reach']['Right']
        field = 'source_neutral_elbow_deflection_deg'
        row[field] = math.nextafter(row[field], math.inf)
        with self.assertRaisesRegex(ReproductionMismatch, 'binary64 value differs'):
            assert_retained_samples(expected, actual)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(PortTests)
    names = [test.id() for test in suite]
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({'status': 'PASS' if result.wasSuccessful() else 'FAIL', 'tests': result.testsRun, 'names': names}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
