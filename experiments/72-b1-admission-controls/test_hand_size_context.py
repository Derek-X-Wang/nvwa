"""The exact v11 hand source is admitted without weakening historical contexts."""
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
SPEC = importlib.util.spec_from_file_location('hand_72_context', HERE / 'run.py')
CONTEXT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTEXT)


class HandSizeSourceContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pins = json.loads((HERE / 'pins.json').read_bytes())
        cpu = CONTEXT.cpu_source_context(cls.pins)
        combined = CONTEXT._combined_context(HERE, cpu)
        leg = CONTEXT._leg_context(HERE, combined)
        upper = CONTEXT._upper_context(HERE, leg)
        hip = CONTEXT._hip_context(HERE, upper)
        arm = CONTEXT._arm_context(HERE, hip)
        cls.previous = CONTEXT._body_reference_context(HERE, arm)
        cls.current = CONTEXT._hand_context(HERE, cls.previous)

    def test_exact_successor_and_predecessor(self):
        self.assertEqual(self.previous[0], CONTEXT.BODY_REFERENCE_CONTEXT_ID)
        self.assertEqual(self.current[0], CONTEXT.HAND_CONTEXT_ID)
        self.assertEqual(len(self.current[1]), 661)
        self.assertEqual(CONTEXT.check_source_context(ROOT, self.pins)['id'],
                         CONTEXT.HAND_CONTEXT_ID)
        with self.assertRaisesRegex(ValueError, 'not historical'):
            CONTEXT.check_source_context(ROOT, self.pins, historical_only=True)
        self.assertEqual({p for p in self.previous[1]
                          if self.current[1][p] != self.previous[1][p]},
                         set(CONTEXT.HAND_CHANGED))

    def test_mutation_missing_asset_and_extra_asset_reject(self):
        with tempfile.TemporaryDirectory(prefix='nvwa-hand-context-') as directory:
            root = Path(directory)
            for name in self.current[1]:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, target)
            self.assertEqual(CONTEXT.check_source_context(root, self.pins)['id'],
                             CONTEXT.HAND_CONTEXT_ID)
            for name in ('crates/nvwa-core/src/b1.rs',
                         'assets/characters/mpfb-b1-v11/manifest.json',
                         'assets/characters/mpfb-b1-v11/targets/l-hand-scale-incr.target'):
                path = root / name
                original = path.read_bytes()
                with self.subTest(path=name):
                    path.write_bytes(original + b' ')
                    with self.assertRaisesRegex(ValueError, 'byte count mismatch'):
                        CONTEXT.check_source_context(root, self.pins)
                    path.write_bytes(original)
            extra = root / CONTEXT.HAND_ASSET_PREFIX / 'unreviewed.target'
            extra.write_bytes(b'unreviewed')
            with self.assertRaisesRegex(ValueError, 'hand source asset inventory mismatch'):
                CONTEXT.check_source_context(root, self.pins)

    def test_four_pinned_gzip_targets_and_bilateral_isolation(self):
        root = ROOT / CONTEXT.HAND_ASSET_PREFIX
        receipt = json.loads((root / 'provenance/hand-size-target-source.json').read_bytes())
        self.assertEqual(receipt['source_commit'],
                         'd0a32e57a7f915cb2f2b95410e2117648c7bbb7e')
        self.assertEqual(len(receipt['files']), 4)
        groups = {}
        for item in receipt['files']:
            name = item['name']
            compressed = (root / 'provenance/source/data/targets/hands' /
                          f'{name}.target.gz').read_bytes()
            expanded = gzip.decompress(compressed)
            self.assertEqual(hashlib.sha256(compressed).hexdigest(), item['source_sha256'])
            self.assertEqual(hashlib.sha256(expanded).hexdigest(), item['expanded_sha256'])
            self.assertEqual((root / 'targets' / f'{name}.target').read_bytes(), expanded)
            groups[name] = {int(line.split()[0]) for line in expanded.decode().splitlines()
                            if line and not line.startswith('#')}
        for sign in ('decr', 'incr'):
            self.assertFalse(groups[f'l-hand-scale-{sign}'] &
                             groups[f'r-hand-scale-{sign}'])


if __name__ == '__main__':
    unittest.main()
