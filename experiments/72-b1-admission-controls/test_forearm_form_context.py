"""The v13 forearm-form source is admitted without weakening v12 history."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location('forearm_72_context', HERE / 'run.py')
CONTEXT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTEXT)


class ForearmFormSourceContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pins = json.loads((HERE / 'pins.json').read_bytes())
        cpu = CONTEXT.cpu_source_context(cls.pins)
        combined = CONTEXT._combined_context(HERE, cpu)
        leg = CONTEXT._leg_context(HERE, combined)
        upper = CONTEXT._upper_context(HERE, leg)
        hip = CONTEXT._hip_context(HERE, upper)
        arm = CONTEXT._arm_context(HERE, hip)
        body = CONTEXT._body_reference_context(HERE, arm)
        hand = CONTEXT._hand_context(HERE, body)
        cls.previous = CONTEXT._shoulder_context(HERE, hand)
        cls.current = CONTEXT._forearm_context(HERE, cls.previous)

    def test_exact_successor_and_predecessor(self):
        self.assertEqual(self.previous[0], CONTEXT.SHOULDER_CONTEXT_ID)
        self.assertEqual(self.current[0], CONTEXT.FOREARM_CONTEXT_ID)
        self.assertEqual(len(self.current[1]), 960)
        self.assertEqual(CONTEXT.check_source_context(ROOT, self.pins)['id'],
                         CONTEXT.UPPER_ARM_CONTEXT_ID)
        self.assertEqual({p for p in self.previous[1]
                          if self.current[1][p] != self.previous[1][p]},
                         set(CONTEXT.FOREARM_CHANGED))
        with self.assertRaisesRegex(ValueError, 'not historical'):
            CONTEXT.check_source_context(ROOT, self.pins, historical_only=True)

    def test_mutation_missing_and_extra_asset_reject(self):
        with tempfile.TemporaryDirectory(prefix='nvwa-forearm-context-') as directory:
            root = Path(directory)
            for name in self.current[1]:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                source = (HERE / CONTEXT.UPPER_ARM_FIXTURES / name
                          if name in CONTEXT.UPPER_ARM_CHANGED else ROOT / name)
                shutil.copyfile(source, target)
            self.assertEqual(CONTEXT.check_source_context(root, self.pins)['id'],
                             CONTEXT.FOREARM_CONTEXT_ID)
            for name in ('crates/nvwa-core/src/b1.rs',
                         'assets/characters/mpfb-b1-v13/manifest.json',
                         'assets/characters/mpfb-b1-v13/targets/forearm-fat-incr.target'):
                path = root / name
                original = path.read_bytes()
                with self.subTest(path=name):
                    path.write_bytes(original + b' ')
                    with self.assertRaisesRegex(ValueError, 'byte count mismatch'):
                        CONTEXT.check_source_context(root, self.pins)
                    path.write_bytes(original)
            extra = root / CONTEXT.FOREARM_ASSET_PREFIX / 'unreviewed.target'
            extra.write_bytes(b'unreviewed')
            with self.assertRaisesRegex(ValueError, 'forearm source asset inventory mismatch'):
                CONTEXT.check_source_context(root, self.pins)


if __name__ == '__main__':
    unittest.main()
