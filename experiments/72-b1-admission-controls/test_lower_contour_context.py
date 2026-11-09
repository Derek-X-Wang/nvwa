"""Bounded actual-current admission and representative real-gate failure/recovery."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location('lower72_runner', HERE / 'run.py')
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)
CURRENT = 'b1-lower-face-squareness-product-v1'

class LowerContourContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pins = json.loads((HERE / 'pins.json').read_bytes())
        cls.old = runner.admitted_source_contexts(cls.pins)
        cls.contexts = runner.current_source_contexts(cls.pins)
        cls.maps = dict(cls.contexts)
        global ROOT
        live = ROOT
        cls.temporary = tempfile.TemporaryDirectory(prefix='nvwa72-pre-running-')
        cls.addClassCleanup(cls.temporary.cleanup)
        ROOT = Path(cls.temporary.name)
        cls.addClassCleanup(lambda: globals().__setitem__('ROOT', live))
        retained = runner.pre_cpu_sources(cls.pins) | runner.pre_motion_query_sources(cls.pins) | runner.pre_running_sources(cls.pins)
        for name in cls.pins['files']:
            path = ROOT / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(retained[name] if name in retained else (live / name).read_bytes())

    def test_actual_current_complete17_and_preserved_five_context_fixture(self):
        self.assertEqual(len(self.old), 5)
        self.assertEqual(self.contexts[:-1], self.old)
        self.assertEqual(len(self.contexts), 6)
        result = runner.check_inputs(ROOT)['checked_input_context']
        self.assertEqual(result['id'], CURRENT)
        self.assertEqual(result['files'], self.maps[CURRENT])
        self.assertEqual(len(result['files']), 17)
        self.assertEqual(result['execution_source'], 'immutable baseline581 archive only')
        with self.assertRaisesRegex(ValueError, 'source input context mismatch'):
            runner.check_source_context(ROOT, self.pins, historical_only=True)
        historical = runner.pre_lower_contour_root(self.pins)
        self.assertEqual(runner.check_inputs(historical)['checked_input_context']['id'], 'b1-cheek-fullness-product-v1')

    def test_representative_actual_production_gate_faults_and_exact_restore(self):
        with tempfile.TemporaryDirectory(prefix='nvwa72-lower-') as directory:
            root = Path(directory) / 'source'
            for name in self.pins['files']:
                dest = root / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, dest)
            changed = runner.RUNTIME
            unchanged = 'crates/nvwa-b1-adapter/src/lib.rs'
            cases = [(changed, 'missing'), (changed, 'corrupt'), (changed, 'symlink'),
                     (unchanged, 'corrupt'), (changed, 'mixed')]
            for name, fault in cases:
                path = root / name
                original = path.read_bytes()
                target = Path(directory) / 'original'
                target.write_bytes(original)
                path.unlink()
                try:
                    if fault == 'corrupt': path.write_bytes(original + b'\nchanged\n')
                    elif fault == 'symlink': path.symlink_to(target)
                    elif fault == 'mixed': path.write_bytes((runner.pre_lower_contour_root(self.pins) / name).read_bytes())
                    with self.assertRaisesRegex(ValueError, 'source input'):
                        runner.check_inputs(root)
                finally:
                    if path.exists() or path.is_symlink(): path.unlink()
                    path.write_bytes(original)
                self.assertEqual(path.read_bytes(), original)
                self.assertEqual(runner.check_inputs(root)['checked_input_context']['id'], CURRENT)
            material = Path(directory) / 'controls'
            material.mkdir()
            for name in runner.PACKAGE: shutil.copyfile(HERE / name, material / name)
            manifest = material / 'input-context-v5.json'
            original = manifest.read_bytes()
            for fault in ['missing', 'corrupt', 'extra', 'mixed', 'symlink']:
                manifest.unlink()
                try:
                    if fault == 'corrupt': manifest.write_bytes(original + b' ')
                    elif fault == 'symlink': manifest.symlink_to(HERE / 'input-context-v5.json')
                    elif fault in ['extra', 'mixed']:
                        changed = json.loads(original)
                        if fault == 'extra': changed['overrides']['unreviewed'] = '0' * 64
                        else: changed['overrides'][runner.RUNTIME] = self.pins['files'][runner.RUNTIME]
                        manifest.write_text(json.dumps(changed))
                    with patch.object(runner, 'HERE', material):
                        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
                            runner.check_inputs(root)
                finally:
                    if manifest.exists() or manifest.is_symlink(): manifest.unlink()
                    manifest.write_bytes(original)
                with patch.object(runner, 'HERE', material):
                    self.assertEqual(runner.check_inputs(root)['checked_input_context']['id'], CURRENT)

    def test_cheap_bidirectional_per_path_crossovers_preserve_old_selector(self):
        count = 0
        for historical, _ in self.old:
            for left, right in [(CURRENT, historical), (historical, CURRENT)]:
                for name in self.maps[left]:
                    if self.maps[left][name] == self.maps[right][name]: continue
                    actual = dict(self.maps[left], **{name: self.maps[right][name]})
                    matches = [n for n, expected in self.contexts if expected == actual]
                    if matches: self.assertEqual(runner.select_source_context(actual, self.contexts), matches[0])
                    else:
                        with self.assertRaisesRegex(ValueError, 'source input context mismatch'):
                            runner.select_source_context(actual, self.contexts)
                    count += 1
        self.assertGreater(count, 0)
        with self.assertRaisesRegex(ValueError, 'source input context mismatch'):
            runner.select_source_context(dict(self.maps[CURRENT], unreviewed='0' * 64), self.contexts)

if __name__ == '__main__':
    unittest.main()
