"""Exact Level 1 successor admission with independently retained v14 history."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location('level1_72_context', HERE / 'run.py')
CONTEXT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTEXT)


class Level1DisplaySourceContext(unittest.TestCase):
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
        shoulder = CONTEXT._shoulder_context(HERE, hand)
        forearm = CONTEXT._forearm_context(HERE, shoulder)
        cls.previous = CONTEXT._upper_arm_context(HERE, forearm)
        cls.current = CONTEXT._level1_context(HERE, cls.previous)

    def test_complete_successor_and_preserved_predecessor(self):
        self.assertEqual(self.previous[0], CONTEXT.UPPER_ARM_CONTEXT_ID)
        self.assertEqual(len(self.previous[1]), 1128)
        self.assertEqual(self.current[0], CONTEXT.LEVEL1_CONTEXT_ID)
        self.assertEqual(len(self.current[1]), 1130)
        self.assertEqual({p for p in self.previous[1]
                          if self.current[1][p] != self.previous[1][p]},
                         set(CONTEXT.LEVEL1_CHANGED))
        self.assertEqual(set(self.current[1]) - set(self.previous[1]),
                         set(CONTEXT.LEVEL1_ADDED))
        self.assertEqual(CONTEXT.check_source_context(ROOT, self.pins)['id'],
                         CONTEXT.LEVEL1_CONTEXT_ID)

    def test_exact_files_reject_mutation_and_old_source_stays_admitted(self):
        with tempfile.TemporaryDirectory(prefix='nvwa-level1-context-') as directory:
            root = Path(directory)
            for name in self.current[1]:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, target)
            self.assertEqual(CONTEXT.check_source_context(root, self.pins)['id'],
                             CONTEXT.LEVEL1_CONTEXT_ID)
            for name in CONTEXT.LEVEL1_CHANGED + CONTEXT.LEVEL1_ADDED:
                path = root / name
                original = path.read_bytes()
                with self.subTest(name=name):
                    path.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
                    with self.assertRaisesRegex(ValueError, 'exact level1 display source required'):
                        CONTEXT.check_source_context(root, self.pins)
                    path.write_bytes(original)
            missing = root / CONTEXT.LEVEL1_ADDED[0]
            missing.unlink()
            with self.assertRaisesRegex(ValueError, 'missing: crates/nvwa-runtime/src/b1_level1_geometry.rs'):
                CONTEXT.check_source_context(root, self.pins)
            (root / CONTEXT.LEVEL1_ADDED[1]).unlink()
            for name in CONTEXT.LEVEL1_CHANGED:
                shutil.copyfile(CONTEXT.pre_level1_file(name), root / name)
            self.assertEqual(CONTEXT.check_source_context(root, self.pins)['id'],
                             CONTEXT.UPPER_ARM_CONTEXT_ID)
            shutil.copyfile(ROOT / CONTEXT.LEVEL1_ADDED[0], missing)
            with self.assertRaisesRegex(ValueError, 'level1 display source context byte count mismatch'):
                CONTEXT.check_source_context(root, self.pins)
            for name in CONTEXT.LEVEL1_CHANGED:
                shutil.copyfile(ROOT / name, root / name)
            with self.assertRaisesRegex(ValueError, 'missing: crates/nvwa-runtime/src/b1_level1_display.rs'):
                CONTEXT.check_source_context(root, self.pins)

    def test_manifest_and_predecessor_fixture_are_separately_pinned(self):
        with tempfile.TemporaryDirectory(prefix='nvwa-level1-manifest-') as directory:
            exp = Path(directory)
            manifest = exp / CONTEXT.LEVEL1_CONTEXT_NAME
            shutil.copyfile(HERE / CONTEXT.LEVEL1_CONTEXT_NAME, manifest)
            for name in CONTEXT.LEVEL1_CHANGED:
                fixture = exp / CONTEXT.LEVEL1_FIXTURES / name
                fixture.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(CONTEXT.pre_level1_file(name), fixture)
            self.assertEqual(CONTEXT._level1_context(exp, self.previous)[0],
                             CONTEXT.LEVEL1_CONTEXT_ID)
            raw = manifest.read_bytes()
            manifest.write_bytes(raw + b' ')
            with self.assertRaisesRegex(ValueError, 'manifest identity mismatch'):
                CONTEXT._level1_context(exp, self.previous)
            manifest.write_bytes(raw)
            fixture = exp / CONTEXT.LEVEL1_FIXTURES / CONTEXT.LEVEL1_CHANGED[0]
            fixture.write_bytes(fixture.read_bytes() + b' ')
            with self.assertRaisesRegex(ValueError, 'predecessor bytes mismatch'):
                CONTEXT._level1_context(exp, self.previous)


if __name__ == '__main__':
    unittest.main()
