"""Exact v7 product admission while retaining v6 predecessor bytes."""
import importlib.util
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location('upper_72_context', HERE / 'run.py')
CONTEXT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTEXT)


class UpperBodySourceContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pins = json.loads((HERE / 'pins.json').read_bytes())
        cpu = CONTEXT.cpu_source_context(cls.pins)
        combined = CONTEXT._combined_context(HERE, cpu)
        cls.predecessor = CONTEXT._leg_context(HERE, combined)
        cls.current = CONTEXT._upper_context(HERE, cls.predecessor)
        cls.legacy_dir = tempfile.TemporaryDirectory(prefix='nvwa-upper-historical-')
        cls.legacy_root = Path(cls.legacy_dir.name)
        for name in cls.current[1]:
            source = HERE / CONTEXT.HIP_FIXTURES / name if name in CONTEXT.HIP_CHANGED else ROOT / name
            destination = cls.legacy_root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)

    @classmethod
    def tearDownClass(cls):
        cls.legacy_dir.cleanup()

    def test_exact_union_preserves_v6(self):
        self.assertEqual(self.predecessor[0], CONTEXT.LEG_CONTEXT_ID)
        self.assertEqual(len(self.predecessor[1]), 194)
        self.assertEqual(cls_id := CONTEXT.check_inputs(self.legacy_root)['checked_input_context']['id'], CONTEXT.UPPER_CONTEXT_ID)
        self.assertEqual(cls_id, self.current[0])
        self.assertEqual({name for name in self.predecessor[1]
                          if self.current[1][name] != self.predecessor[1][name]},
                         set(CONTEXT.UPPER_CHANGED))
        with self.assertRaisesRegex(ValueError, 'not historical'):
            CONTEXT.check_source_context(ROOT, self.pins, historical_only=True)

    def test_changed_code_assets_and_predecessor_pin_reject(self):
        with tempfile.TemporaryDirectory(prefix='nvwa-upper-context-') as directory:
            root = Path(directory)
            for name in self.current[1]:
                destination = root / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(self.legacy_root / name, destination)
            self.assertEqual(CONTEXT.check_source_context(root, self.pins)['id'], CONTEXT.UPPER_CONTEXT_ID)
            for name in ('crates/nvwa-core/src/b1.rs',
                         'assets/characters/mpfb-b1-v7/manifest.json',
                         'assets/characters/mpfb-b1-v7/targets/measure-bust-circ-incr.target'):
                path = root / name; original = path.read_bytes()
                with self.subTest(path=name):
                    path.write_bytes(original + b' ')
                    with self.assertRaisesRegex(ValueError, 'byte count mismatch'):
                        CONTEXT.check_source_context(root, self.pins)
                    path.write_bytes(original)
            extra = root / CONTEXT.UPPER_ASSET_PREFIX / 'unreviewed.target'
            extra.write_bytes(b'unreviewed')
            with self.assertRaisesRegex(ValueError, 'upper source asset inventory mismatch'):
                CONTEXT.check_source_context(root, self.pins)

    def test_fixed_cc0_gzip_targets_expand_exactly_to_runtime_payloads(self):
        root = ROOT / CONTEXT.UPPER_ASSET_PREFIX
        receipt = json.loads((root / 'provenance/upper-body-target-source.json').read_bytes())
        self.assertEqual(receipt['source_commit'], 'd0a32e57a7f915cb2f2b95410e2117648c7bbb7e')
        self.assertEqual(len(receipt['files']), 6)
        for item in receipt['files']:
            folder = 'arms' if item['parameter'] == 'upper_arm_girth' else 'torso'
            compressed = (root / 'provenance/source/data/targets' / folder / f"{item['name']}.target.gz").read_bytes()
            expanded = gzip.decompress(compressed)
            self.assertEqual(hashlib.sha256(compressed).hexdigest(), item['source_sha256'])
            self.assertEqual(len(compressed), item['source_bytes'])
            self.assertEqual(hashlib.sha256(expanded).hexdigest(), item['expanded_sha256'])
            self.assertEqual(len(expanded), item['expanded_bytes'])
            self.assertEqual((root / 'targets' / f"{item['name']}.target").read_bytes(), expanded)


if __name__ == '__main__': unittest.main()
