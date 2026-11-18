"""Exact v10 source admission with immutable v9 predecessor bytes."""
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
SPEC = importlib.util.spec_from_file_location('chest_72_context', HERE / 'run.py')
CONTEXT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTEXT)


class ChestPlacementSourceContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pins = json.loads((HERE / 'pins.json').read_bytes())
        cpu = CONTEXT.cpu_source_context(cls.pins)
        combined = CONTEXT._combined_context(HERE, cpu)
        leg = CONTEXT._leg_context(HERE, combined)
        upper = CONTEXT._upper_context(HERE, leg)
        hip = CONTEXT._hip_context(HERE, upper)
        cls.predecessor = CONTEXT._arm_context(HERE, hip)
        cls.current = CONTEXT._chest_context(HERE, cls.predecessor)

    def test_exact_union_preserves_v9(self):
        self.assertEqual(self.predecessor[0], CONTEXT.ARM_CONTEXT_ID)
        self.assertEqual(len(self.predecessor[1]), 524)
        self.assertEqual(CONTEXT.check_inputs(ROOT)['checked_input_context']['id'], CONTEXT.CHEST_CONTEXT_ID)
        self.assertEqual({name for name in self.predecessor[1]
                          if self.current[1][name] != self.predecessor[1][name]},
                         set(CONTEXT.CHEST_CHANGED))
        with self.assertRaisesRegex(ValueError, 'not historical'):
            CONTEXT.check_source_context(ROOT, self.pins, historical_only=True)

    def test_changed_source_asset_and_predecessor_pin_reject(self):
        with tempfile.TemporaryDirectory(prefix='nvwa-chest-context-') as directory:
            root = Path(directory)
            for name in self.current[1]:
                destination = root / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, destination)
            self.assertEqual(CONTEXT.check_source_context(root, self.pins)['id'], CONTEXT.CHEST_CONTEXT_ID)
            for name in ('crates/nvwa-core/src/b1.rs',
                         'assets/characters/mpfb-b1-v10/manifest.json',
                         'assets/characters/mpfb-b1-v10/targets/breast-trans-up.target'):
                path = root / name
                original = path.read_bytes()
                with self.subTest(path=name):
                    path.write_bytes(original + b' ')
                    with self.assertRaisesRegex(ValueError, 'byte count mismatch'):
                        CONTEXT.check_source_context(root, self.pins)
                    path.write_bytes(original)
            extra = root / CONTEXT.CHEST_ASSET_PREFIX / 'unreviewed.target'
            extra.write_bytes(b'unreviewed')
            with self.assertRaisesRegex(ValueError, 'chest source asset inventory mismatch'):
                CONTEXT.check_source_context(root, self.pins)

    def test_fixed_cc0_gzip_targets_expand_exactly(self):
        root = ROOT / CONTEXT.CHEST_ASSET_PREFIX
        receipt = json.loads((root / 'provenance/chest-placement-target-source.json').read_bytes())
        self.assertEqual(receipt['source_commit'], 'd0a32e57a7f915cb2f2b95410e2117648c7bbb7e')
        self.assertEqual(len(receipt['files']), 4)
        for item in receipt['files']:
            folder = 'breast'
            compressed = (root / 'provenance/source/data/targets' / folder / f"{item['name']}.target.gz").read_bytes()
            expanded = gzip.decompress(compressed)
            self.assertEqual(hashlib.sha256(compressed).hexdigest(), item['source_sha256'])
            self.assertEqual(len(compressed), item['source_bytes'])
            self.assertEqual(hashlib.sha256(expanded).hexdigest(), item['expanded_sha256'])
            self.assertEqual(len(expanded), item['expanded_bytes'])
            self.assertEqual((root / 'targets' / f"{item['name']}.target").read_bytes(), expanded)



if __name__ == '__main__':
    unittest.main()
