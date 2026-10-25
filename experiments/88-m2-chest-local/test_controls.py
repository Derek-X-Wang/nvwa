#!/usr/bin/env python3
"""Synthetic-only controls of constructor-called seams; unittest survives -O."""
import copy
import json
import math
from pathlib import Path
import signal
import struct
import sys
import time
import unittest
import candidate as c
import evaluate as e


def fixture():
    doc = {'buffers': [{'byteLength': 52}],
           'bufferViews': [{'byteLength': 16, 'byteOffset': 0}, {'byteLength': 32, 'byteOffset': 16}],
           'accessors': [{'bufferView': 0, 'componentType': 5123, 'type': 'VEC4', 'count': 2},
                         {'bufferView': 1, 'componentType': 5126, 'type': 'VEC4', 'count': 2}]}
    attrs = {'JOINTS_0': 0, 'WEIGHTS_0': 1}
    binary = bytearray(52)
    for v in (0, 1):
        c.write_record(doc, binary, 0, v, [0, 3, 1, 2])
        c.write_record(doc, binary, 1, v, [.75, 0., .25, -0.])
    return doc, bytes(binary), attrs, [0, 1], [[.286, 1.32, 0.], [.305, 1.32, 0.]], ['upper_arm.R', 'forearm.R', 'chest', 'neck']


class Controls(unittest.TestCase):
    def setUp(self):
        self.doc, self.before, self.attrs, self.ids, self.positions, self.names = fixture()

    def patch(self):
        return c.patch_binary(self.doc, self.before, self.attrs, self.ids, self.positions, self.names)

    def validate(self, after, doc=None):
        return c.validate_binary(self.doc, self.before, self.doc if doc is None else doc,
                                 after, self.attrs, self.ids, self.positions, self.names)

    def test_fixed_field_and_outer_endpoints(self):
        self.assertEqual(c.field([.285, 1.32, 0]), .5)
        self.assertAlmostEqual(c.field([.295, 1.32, 0]), .25)
        for point in [[.305, 1.32, 0], [.306, 1.32, 0], [.29, 1.28, 0],
                      [.29, 1.40, 0], [.28, 1.32, 0]]:
            self.assertEqual(c.field(point), 0.)
        self.assertAlmostEqual(c.field([.285, 1.29, 0]), .25)
        self.assertAlmostEqual(c.field([.285, 1.39, 0]), .25)
        with self.assertRaisesRegex(ValueError, 'finite rest point'):
            c.field([math.nan, 1.32, 0])

    def test_constructed_readback_and_first_zero_slot_only(self):
        after, proof = self.patch()
        self.assertTrue(proof['original_positive_retention'])
        self.assertEqual(proof['maximum_discarded_mass'], 0.)
        self.assertEqual(proof['pruned_vertices'], 0)
        self.assertEqual(proof['discard_limit'], .01)
        js = c.read_record(self.doc, after, 0, 0)
        ws = c.read_record(self.doc, after, 1, 0)
        self.assertEqual(js, [0, 2, 1, 2])
        self.assertGreater(ws[0], 0)
        self.assertGreater(ws[2], 0)
        self.assertGreater(ws[1], 0)
        # The unused original slot retains its negative-zero bits and joint ID.
        off, _, _ = c.layout(self.doc, 1, 0)
        self.assertEqual(after[off+12:off+16], self.before[off+12:off+16])
        for accessor in (0, 1):
            off, _, size = c.layout(self.doc, accessor, 1)
            self.assertEqual(after[off:off+size], self.before[off:off+size])
        self.assertGreater(proof['changed_binary_bytes'], 0)
        self.assertEqual(c.REAL_CONSTRUCTOR_CALLS, 0)

    def test_actual_forbidden_byte_gate_rejects(self):
        after = bytearray(self.patch()[0]); after[50] = 1
        with self.assertRaisesRegex(ValueError, 'forbidden binary byte changed'):
            self.validate(after)

    def test_actual_old_positive_loss_gate_rejects(self):
        after = bytearray(self.patch()[0])
        ws = c.read_record(self.doc, after, 1, 0)
        ws[1] += ws[0]; ws[0] = 0.
        c.write_record(self.doc, after, 1, 0, ws)
        with self.assertRaisesRegex(ValueError, 'serialized old positive loss'):
            self.validate(after)

    def test_actual_nonfinite_and_normalization_gates_reject(self):
        for value, error in [(math.nan, 'finite nonnegative weights'),
                             (math.inf, 'finite nonnegative weights'),
                             (-.1, 'finite nonnegative weights'),
                             (.9, 'unchanged2e-6 normalization')]:
            with self.subTest(value=value):
                after = bytearray(self.patch()[0])
                ws = c.read_record(self.doc, after, 1, 0); ws[0] = value
                c.write_record(self.doc, after, 1, 0, ws)
                with self.assertRaisesRegex(ValueError, error):
                    self.validate(after)

    def test_actual_fixed_operation_and_remaining_zero_bytes_reject(self):
        after = bytearray(self.patch()[0])
        js = c.read_record(self.doc, after, 0, 0); js[3] = 3
        c.write_record(self.doc, after, 0, 0, js)
        with self.assertRaisesRegex(ValueError, 'exact fixed mix / in-place zero-slot bytes'):
            self.validate(after)
        after = bytearray(self.patch()[0])
        ws = c.read_record(self.doc, after, 1, 0)
        ws[0] += .01; ws[1] -= .01
        c.write_record(self.doc, after, 1, 0, ws)
        with self.assertRaisesRegex(ValueError, 'exact fixed mix / in-place zero-slot bytes'):
            self.validate(after)

    def test_actual_json_and_length_gates_reject(self):
        after = self.patch()[0]
        doc = copy.deepcopy(self.doc); doc['extra'] = 'forbidden'
        with self.assertRaisesRegex(ValueError, 'whole GLB JSON exact'):
            self.validate(after, doc)
        with self.assertRaisesRegex(ValueError, 'binary length exact'):
            self.validate(after+b'\0')

    def test_actual_initial_record_and_capacity_gates_reject(self):
        cases = [([0, 3, 1, 2], [.75, math.nan, .25, 0.], 'finite nonnegative'),
                 ([0, 3, 1, 2], [.75, 0., .20, 0.], 'unchanged2e-6'),
                 ([0, 3, 0, 2], [.75, 0., .25, 0.], 'distinct old positive'),
                 ([0, 3, 2, 1], [.75, 0., .25, 0.], 'exact original arm support'),
                 ([0, 3, 1, 100], [.75, 0., .25, 0.], 'valid serialized joint slot'),
                 ([0, 1, 2, 3], [.25, .25, .25, .25], 'exact original arm support')]
        for js, ws, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    c.mix_record(self.positions[0], js, ws, self.names)
        with self.assertRaisesRegex(ValueError, 'original four slots'):
            c.mix_record(self.positions[0], [0, 1], [.75, .25], self.names)
        with self.assertRaisesRegex(ValueError, 'unique existing chest joint'):
            c.mix_record(self.positions[0], [0, 3, 1, 2], [.75, 0., .25, 0.], self.names+['chest'])

    def test_float32_old_positive_underflow_rejects(self):
        tiny = struct.unpack('<f', struct.pack('<I', 1))[0]
        with self.assertRaisesRegex(ValueError, 'float32 old positive retention'):
            c.mix_record([.285, 1.32, 0.], [0, 3, 1, 2], [tiny, 0., 1., 0.], self.names)

    def test_record_layout_rejects(self):
        for mutation, message in [('normalized', 'plain VEC4'), ('sparse', 'plain VEC4')]:
            doc = copy.deepcopy(self.doc); doc['accessors'][0][mutation] = True
            with self.assertRaisesRegex(ValueError, message):
                c.layout(doc, 0, 0)
        with self.assertRaisesRegex(ValueError, 'record vertex bounds'):
            c.layout(self.doc, 0, 2)

    def test_mechanism_needs_both_named_edges_and_maximum(self):
        edges = [list(edge) for edge in e.NAMED_EDGES]+[[100+i, 101+i] for i in range(37)]
        rows = [{'edge': edge, 'control_length_m': 1., 'candidate_length_m': .9} for edge in edges]
        samples = [{'key_index': key, 'edges': copy.deepcopy(rows),
                    'control_maximum_length_m': 1., 'candidate_maximum_length_m': .9} for key in e.KEYS]
        self.assertEqual(e.mechanism_gate(samples)['status'], 'PASS')
        for index in (0, 1):
            bad = copy.deepcopy(samples); bad[-1]['edges'][index]['candidate_length_m'] = 1.
            self.assertEqual(e.mechanism_gate(bad)['status'], 'FAIL')
        bad = copy.deepcopy(samples); bad[-1]['candidate_maximum_length_m'] = 1.
        self.assertEqual(e.mechanism_gate(bad)['status'], 'FAIL')
        with self.assertRaisesRegex(ValueError, 'fixed seven edge samples'):
            e.mechanism_gate(samples[:-1])
        bad = copy.deepcopy(samples); bad[-1]['edges'].pop()
        with self.assertRaisesRegex(ValueError, 'same39 edge mechanism scope'):
            e.mechanism_gate(bad)


def main():
    c.hard_stop(30)
    started = time.monotonic()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Controls)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    signal.alarm(0)
    c.require(c.REAL_CONSTRUCTOR_CALLS == 0, 'synthetic controls never call real constructor')
    print(json.dumps({'status': 'PASS' if result.wasSuccessful() else 'FAIL', 'tests_run': result.testsRun,
                      'failures': len(result.failures), 'errors': len(result.errors),
                      'python_optimized': bool(sys.flags.optimize), 'synthetic_inputs_only': True,
                      'real_constructor_calls': c.REAL_CONSTRUCTOR_CALLS, 'elapsed_seconds': time.monotonic()-started}))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
