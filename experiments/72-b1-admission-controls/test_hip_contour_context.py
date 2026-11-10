"""Exact v8 source admission with immutable v7 predecessor bytes."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location('hip_72_context', HERE / 'run.py')
CONTEXT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTEXT)


class HipContourSourceContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pins = json.loads((HERE / 'pins.json').read_bytes())
        cpu = CONTEXT.cpu_source_context(cls.pins)
        combined = CONTEXT._combined_context(HERE, cpu)
        leg = CONTEXT._leg_context(HERE, combined)
        cls.predecessor = CONTEXT._upper_context(HERE, leg)
        cls.current = CONTEXT._hip_context(HERE, cls.predecessor)
        if CONTEXT.has_arm_inputs(ROOT):
            CONTEXT._pre_arm_sources(HERE, cls.current)

    def test_exact_union_preserves_v7(self):
        self.assertEqual(self.predecessor[0], CONTEXT.UPPER_CONTEXT_ID)
        self.assertEqual(len(self.predecessor[1]), 292)
        expected = CONTEXT.HAND_CONTEXT_ID if CONTEXT.has_hand_inputs(ROOT) else CONTEXT.BODY_REFERENCE_CONTEXT_ID if CONTEXT.has_body_reference_inputs(ROOT) else CONTEXT.ARM_CONTEXT_ID if CONTEXT.has_arm_inputs(ROOT) else CONTEXT.HIP_CONTEXT_ID
        self.assertEqual(CONTEXT.check_inputs(ROOT)['checked_input_context']['id'], expected)
        self.assertEqual({name for name in self.predecessor[1]
                          if self.current[1][name] != self.predecessor[1][name]},
                         set(CONTEXT.HIP_CHANGED))
        with self.assertRaisesRegex(ValueError, 'not historical'):
            CONTEXT.check_source_context(ROOT, self.pins, historical_only=True)

    def test_changed_source_asset_and_predecessor_pin_reject(self):
        with tempfile.TemporaryDirectory(prefix='nvwa-hip-context-') as directory:
            root = Path(directory)
            for name in self.current[1]:
                destination = root / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                historical = HERE / CONTEXT.ARM_FIXTURES / name
                shutil.copyfile(historical if name in CONTEXT.ARM_CHANGED and historical.is_file()
                                else CONTEXT.pre_body_reference_file(name), destination)
            self.assertEqual(CONTEXT.check_source_context(root, self.pins)['id'], CONTEXT.HIP_CONTEXT_ID)
            for name in ('crates/nvwa-core/src/b1.rs',
                         'assets/characters/mpfb-b1-v8/manifest.json',
                         'assets/characters/mpfb-b1-v8/targets/buttocks-volume-incr.target'):
                path = root / name
                original = path.read_bytes()
                with self.subTest(path=name):
                    path.write_bytes(original + b' ')
                    with self.assertRaisesRegex(ValueError, 'byte count mismatch'):
                        CONTEXT.check_source_context(root, self.pins)
                    path.write_bytes(original)
            extra = root / CONTEXT.HIP_ASSET_PREFIX / 'unreviewed.target'
            extra.write_bytes(b'unreviewed')
            with self.assertRaisesRegex(ValueError, 'hip source asset inventory mismatch'):
                CONTEXT.check_source_context(root, self.pins)

    def test_fixed_cc0_gzip_targets_expand_exactly(self):
        root = ROOT / CONTEXT.HIP_ASSET_PREFIX
        receipt = json.loads((root / 'provenance/hip-contour-target-source.json').read_bytes())
        self.assertEqual(receipt['source_commit'], 'd0a32e57a7f915cb2f2b95410e2117648c7bbb7e')
        self.assertEqual(len(receipt['files']), 4)
        for item in receipt['files']:
            folder = 'hip' if item['parameter'] == 'hip_depth' else 'buttocks'
            compressed = (root / 'provenance/source/data/targets' / folder / f"{item['name']}.target.gz").read_bytes()
            expanded = gzip.decompress(compressed)
            self.assertEqual(hashlib.sha256(compressed).hexdigest(), item['source_sha256'])
            self.assertEqual(len(compressed), item['source_bytes'])
            self.assertEqual(hashlib.sha256(expanded).hexdigest(), item['expanded_sha256'])
            self.assertEqual(len(expanded), item['expanded_bytes'])
            self.assertEqual((root / 'targets' / f"{item['name']}.target").read_bytes(), expanded)


if __name__ == '__main__':
    unittest.main()
