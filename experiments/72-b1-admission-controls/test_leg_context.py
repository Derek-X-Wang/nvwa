"""Exact leg-product source admission while retaining the waist predecessor."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location('leg_72_context', HERE / 'run.py')
CONTEXT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTEXT)


class LegSourceContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pins = json.loads((HERE / 'pins.json').read_bytes())
        cpu = CONTEXT.cpu_source_context(cls.pins)
        cls.predecessor = CONTEXT._combined_context(HERE, cpu)
        cls.current = CONTEXT._leg_context(HERE, cls.predecessor)
        cls.legacy_dir = tempfile.TemporaryDirectory(prefix='nvwa-leg-historical-')
        cls.legacy_root = Path(cls.legacy_dir.name)
        for name in cls.current[1]:
            source = HERE / CONTEXT.UPPER_FIXTURES / name if name in CONTEXT.UPPER_CHANGED else CONTEXT.pre_body_reference_file(name)
            destination = cls.legacy_root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)

    @classmethod
    def tearDownClass(cls):
        cls.legacy_dir.cleanup()

    def test_exact_new_union_keeps_immutable_predecessor(self):
        self.assertEqual(self.predecessor[0], CONTEXT.COMBINED_CONTEXT_ID)
        self.assertEqual(len(self.predecessor[1]), 112)
        self.assertEqual(self.current[0], CONTEXT.LEG_CONTEXT_ID)
        self.assertEqual(len(self.current[1]), 194)
        self.assertEqual(CONTEXT.check_inputs(self.legacy_root)['checked_input_context']['id'],
                         CONTEXT.LEG_CONTEXT_ID)
        self.assertEqual({name for name in self.predecessor[1]
                          if self.current[1][name] != self.predecessor[1][name]},
                         set(CONTEXT.LEG_CHANGED))
        with self.assertRaisesRegex(ValueError, 'not historical'):
            CONTEXT.check_source_context(ROOT, self.pins, historical_only=True)

    def test_changed_code_and_assets_reject_then_restore(self):
        with tempfile.TemporaryDirectory(prefix='nvwa-leg-context-') as directory:
            root = Path(directory)
            for name in self.current[1]:
                destination = root / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(self.legacy_root / name, destination)
            self.assertEqual(CONTEXT.check_source_context(root, self.pins)['id'],
                             CONTEXT.LEG_CONTEXT_ID)
            for name in ('crates/nvwa-core/src/b1.rs',
                         'assets/characters/mpfb-b1-v6/manifest.json',
                         'assets/characters/mpfb-b1-v6/targets/measure-upperleg-height-incr.target',
                         'assets/characters/mpfb-b1-v6/provenance/leg-target-source.json'):
                path = root / name
                original = path.read_bytes()
                with self.subTest(path=name):
                    path.write_bytes(original + b' ')
                    with self.assertRaisesRegex(ValueError, 'byte count mismatch'):
                        CONTEXT.check_source_context(root, self.pins)
                    path.write_bytes(original)
                    self.assertEqual(CONTEXT.check_source_context(root, self.pins)['id'],
                                     CONTEXT.LEG_CONTEXT_ID)
            extra = root / CONTEXT.LEG_ASSET_PREFIX / 'unreviewed.target'
            extra.write_bytes(b'unreviewed')
            with self.assertRaisesRegex(ValueError, 'leg source asset inventory mismatch'):
                CONTEXT.check_source_context(root, self.pins)
            extra.unlink()
            self.assertEqual(CONTEXT.check_source_context(root, self.pins)['id'],
                             CONTEXT.LEG_CONTEXT_ID)

    def test_predecessor_fixture_and_new_manifest_are_pinned(self):
        with tempfile.TemporaryDirectory(prefix='nvwa-leg-controls-') as directory:
            exp = Path(directory) / 'experiments/72-b1-admission-controls'
            shutil.copytree(HERE, exp)
            for name, error in ((CONTEXT.LEG_CONTEXT_NAME, 'leg source context manifest identity'),
                                (f'{CONTEXT.LEG_FIXTURES}/manifest.json', 'leg predecessor manifest identity'),
                                (f'{CONTEXT.LEG_FIXTURES}/{CONTEXT.LEG_CHANGED[0]}', 'leg predecessor bytes mismatch')):
                path = exp / name
                original = path.read_bytes()
                with self.subTest(path=name):
                    path.write_bytes(original + b' ')
                    with patch.object(CONTEXT, 'HERE', exp):
                        with self.assertRaisesRegex(ValueError, error):
                            CONTEXT.check_source_context(self.legacy_root, self.pins)
                    path.write_bytes(original)
                    with patch.object(CONTEXT, 'HERE', exp):
                        self.assertEqual(CONTEXT.check_source_context(self.legacy_root, self.pins)['id'],
                                         CONTEXT.LEG_CONTEXT_ID)


if __name__ == '__main__':
    unittest.main()
