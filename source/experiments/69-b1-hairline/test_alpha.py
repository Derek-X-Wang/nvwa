"""Hand controls and independent enumeration of the retained histogram evidence."""
import copy
from fractions import Fraction
import json
from pathlib import Path
import unittest
import check_alpha as tool
import png_alpha


def verify_report(report):
    def check(ok):
        if not ok:
            raise ValueError('inconsistent frozen evidence')
    check(report['status'] == 'CPU_REJECTED')
    check(report['source']['png_sha256'] == tool.PNG_SHA)
    check(report['source']['decoded_rgba_sha256'] == tool.RGBA_SHA)
    check(report['policy'] == dict(algorithm='short04-coverage-mips-v1', shader_mask_cutoff=0.5,
          alpha8_pass_minimum=128, maximum_guarded_error_numerator=1,
          maximum_guarded_error_denominator=1000, guard_minimum_width=64))
    check(report['target_pass_texels'] == 2201816 and report['source_texels'] == 4194304)
    check(len(report['levels']) == 11)
    guards = []
    for index, row in enumerate(report['levels'], 1):
        width = 2048//2**index
        h = row['raw_alpha_histogram']
        check(row['index'] == index and row['width'] == width and row['texels'] == width*width)
        check(len(h) == 256 and all(type(n) is int and n >= 0 for n in h) and sum(h) == width*width)
        # Independent enumeration applies the rounded output to each histogram bin.
        choices = []
        for c in range(1, 256):
            count = sum(n for value, n in enumerate(h) if min(255, (128*value+c//2)//c) >= 128)
            choices.append((abs(Fraction(count, width*width)-Fraction(2201816, 4194304)),
                            abs(Fraction(128, c)-1), c, 128, c, count))
        choices.append((Fraction(2201816, 4194304), Fraction(1), 256, 0, 1, 0))
        error, _, _, numerator, denominator, count = min(choices)
        check((row['alpha_scale_numerator'], row['alpha_scale_denominator'], row['corrected_pass_texels']) ==
              (numerator, denominator, count))
        check(row['raw_pass_texels'] == sum(h[128:]))
        check(Fraction(row['coverage_error_numerator'], row['coverage_error_denominator']) == error)
        check(row['coverage_error_denominator'] == 4194304*width*width)
        check(row['signed_coverage_difference'] == float(Fraction(count, width*width)-Fraction(2201816, 4194304)))
        guard = width < 64 or error <= Fraction(1, 1000)
        check(row['frozen_guard_pass'] is guard)
        guards.append(guard)
    check(report['all_frozen_guards_pass'] is all(guards))
    check([row['index'] for row in report['levels'] if not row['frozen_guard_pass']] == [1])


class AlphaControls(unittest.TestCase):
    def test_all_five_png_filters_hand_control(self):
        original = bytes([10,20,30,40,50,60,70,80])
        previous = bytes([3,5,7,11,13,17,19,23])
        encoded = [original, bytes([10,20,30,40,40,40,40,40]), bytes([7,15,23,29,37,43,51,57]),
                   bytes([9,18,27,35,39,42,46,49]), bytes([7,15,23,29,37,40,40,40])]
        for kind, row in enumerate(encoded):
            self.assertEqual(png_alpha.unfilter_row(kind, row, previous), original)

    def test_invalid_png_filter_size_and_identity(self):
        for args in [(5, bytes(4), bytes(4)), (0, bytes(3), bytes(4))]:
            with self.assertRaises(ValueError):
                png_alpha.unfilter_row(*args)
        with self.assertRaises(ValueError):
            png_alpha.rgba_png(b'not PNG')
        with self.assertRaisesRegex(ValueError, 'source PNG hash mismatch'):
            tool.analyze_source(b'not approved bytes')

    def test_checker_hand_mean_and_unavoidable_small_level_error(self):
        row = tool.analyze_alpha([0,255,255,0], 2)['levels'][0]
        self.assertEqual(row['raw_alpha_histogram'][128], 1)
        self.assertEqual((row['alpha_scale_numerator'], row['alpha_scale_denominator']), (128,128))
        self.assertEqual(Fraction(row['coverage_error_numerator'],row['coverage_error_denominator']), Fraction(1,2))
        self.assertTrue(row['frozen_guard_pass'])  # Width1 explicitly not guarded.

    def test_nontrivial_scale_and_zero_opaque_controls(self):
        self.assertEqual(tool.best_scale([0,100,100,255], 3, 4)[:4], (128,100,3,0))
        self.assertEqual(tool.best_scale([0]*4, 0, 4)[:4], (128,128,0,0))
        self.assertEqual(tool.best_scale([255]*4, 4, 4)[:4], (128,128,4,0))

    def test_raw_sums_not_quantized_feedback(self):
        # Three block sums2 and one0 round to mip1 [1,1,1,0].
        # Feeding those rounded means back would yield1; original6/16 rounds0.
        alpha = [0]*16
        for i in (0,2,8):
            alpha[i] = 2
        rows = tool.analyze_alpha(alpha,4)['levels']
        self.assertEqual(rows[0]['raw_alpha_histogram'][1], 3)
        self.assertEqual(rows[0]['raw_alpha_histogram'][0], 1)
        self.assertEqual(rows[1]['raw_alpha_histogram'][0], 1)

    def test_bad_dimensions_and_domain(self):
        for alpha, width in [([0]*9,3), ([0]*3,2), ([0,0,0,256],2), ([0],1)]:
            with self.assertRaises(ValueError):
                tool.analyze_alpha(alpha,width)

    def test_retained_evidence_independent_optimum_and_guard(self):
        verify_report(json.loads((Path(__file__).parent/'alpha-reference.json').read_text()))

    def test_mutations_fail_instead_of_weakening_selection_or_guard(self):
        original = json.loads((Path(__file__).parent/'alpha-reference.json').read_text())
        mutations = [lambda r:r['levels'].pop(),
                     lambda r:r['levels'][0].update(frozen_guard_pass=True),
                     lambda r:r['policy'].update(maximum_guarded_error_denominator=100),
                     lambda r:r['levels'][0].update(alpha_scale_denominator=129),
                     lambda r:r['levels'][0].update(width=512),
                     lambda r:r['source'].update(png_sha256='0'*64),
                     lambda r:r['levels'][0]['raw_alpha_histogram'].__setitem__(0,0)]
        for mutate in mutations:
            report = copy.deepcopy(original)
            mutate(report)
            with self.assertRaises(ValueError):
                verify_report(report)


if __name__ == '__main__':
    unittest.main()
