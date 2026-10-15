#!/usr/bin/env python3
"""Independent report freshness and rejection controls; no external operations."""
import ast
import hashlib
import json
from pathlib import Path
import unittest
from unittest import mock

import oracle

HERE = Path(__file__).resolve().parent


class IndependentControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = oracle.analyze()

    def test_frozen_result_matches_recomputation(self):
        # Python3.12 changed float sum accuracy. acos near 1 amplifies a final
        # bit into tiny angular differences; compare angles separately.
        def compare(actual, expected, path=''):
            if isinstance(actual, dict):
                self.assertEqual(set(actual), set(expected), path)
                for key in actual:
                    compare(actual[key], expected[key], path+'.'+key)
            elif isinstance(actual, list):
                self.assertEqual(len(actual), len(expected), path)
                for i, (a, b) in enumerate(zip(actual, expected)):
                    compare(a, b, path+'['+str(i)+']')
            elif isinstance(actual, float):
                tolerance = 1e-7 if 'degrees' in path else 1e-12
                self.assertAlmostEqual(actual, expected, delta=tolerance, msg=path)
            else:
                self.assertEqual(actual, expected, path)
        compare(self.report, json.loads((HERE/'results.json').read_text()))

    def test_explicit_guards_survive_optimization(self):
        self.assertFalse(any(isinstance(n, ast.Assert) for n in ast.walk(ast.parse((HERE/'oracle.py').read_text()))))
        with self.assertRaisesRegex(ValueError, 'deliberate control'):
            oracle.require(False, 'deliberate control')

    def test_zero_and_nonfinite_rotation_rejected(self):
        for q in ([0,0,0,0], [0,0,float('nan'),1], [0,0,float('inf'),1]):
            with self.subTest(q=q):
                with self.assertRaises(ValueError):
                    oracle.quat_matrix(q)

    def test_wrong_input_identity_rejected_before_math(self):
        altered = dict(oracle.PINS)
        altered[next(iter(altered))] = '0'*64
        with mock.patch.object(oracle, 'PINS', altered):
            with self.assertRaisesRegex(ValueError, 'frozen input SHA-256 mismatch'):
                oracle.analyze()

    def test_same_sample_falsifications_are_observable(self):
        summary = self.report['summary']
        self.assertEqual(len(self.report['pelvis_all90']), 90)
        self.assertLess(summary['pelvis_all90_max_affine_error_m'], 1e-12)
        self.assertEqual(summary['q_negative_q_source_affine_max_error_m'], 0.)
        self.assertEqual(summary['q_negative_q_target_affine_max_error_m'], 0.)
        for name, value in summary['falsifications'].items():
            with self.subTest(control=name):
                self.assertGreater(value['max_error_m'], .001)
                self.assertGreaterEqual(value['frames_above_1e_6'], 89)
        self.assertLess(summary['twist_control']['primary_ray_unit_position_error'], 1e-12)
        self.assertGreater(summary['twist_control']['off_axis_marker_displacement_m'], .09)
        self.assertEqual(summary['admission']['anatomical_semantics'], 'HOLD')

    def test_published_freeze_when_present(self):
        manifest = HERE/'SHA256SUMS.json'
        if manifest.exists():
            for name, expected in json.loads(manifest.read_text())['files'].items():
                with self.subTest(name=name):
                    self.assertEqual(hashlib.sha256((HERE/name).read_bytes()).hexdigest(), expected)


if __name__ == '__main__':
    unittest.main()
