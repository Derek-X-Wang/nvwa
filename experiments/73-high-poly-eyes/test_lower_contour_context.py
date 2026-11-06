"""One new current context; old six/seven cohorts and expensive matrices stay fixed."""
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

EXP = Path(__file__).resolve().parent
ROOT = EXP.parents[1]
CURRENT = 'b1-lower-face-squareness-product-v1'
SPEC = importlib.util.spec_from_file_location('lower73_context', EXP / 'frozen_context.py')
CONTEXT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTEXT)
# Import the actual called production gate once; no per-fault child interpreter.
sys.path.insert(0, str(EXP))
try:
    SPEC = importlib.util.spec_from_file_location('lower73_actual_gate', EXP / 'test_prepare.py')
    GATE = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(GATE)
finally:
    sys.path.pop(0)

class LowerContourContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (EXP / 'FROZEN-INPUTS.json').read_bytes()
        cls.original = json.loads(cls.raw)
        cls.old = CONTEXT.admitted_source_contexts(EXP, cls.raw, cls.original)
        cls.contexts = CONTEXT.current_source_contexts(EXP, cls.raw, cls.original)
        cls.maps = dict(cls.contexts)
        global ROOT
        live = ROOT
        cls.temporary = tempfile.TemporaryDirectory(prefix='nvwa73-pre-running-')
        cls.addClassCleanup(cls.temporary.cleanup)
        ROOT = Path(cls.temporary.name)
        cls.addClassCleanup(lambda: globals().__setitem__('ROOT', live))
        retained = CONTEXT.pre_running_sources(EXP, cls.contexts)
        for name in cls.original:
            path = ROOT / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(retained[name] if name in retained else (live / name).read_bytes())

    def gate(self, root=None, exp=EXP):
        root = ROOT if root is None else root
        with patch.object(GATE, 'ROOT', root), patch.object(GATE, 'EXP', exp):
            GATE.SourceContract('test_frozen_source_inputs').test_frozen_source_inputs()

    def test_actual_current_gate_complete309_and_old_seven_cohort_preserved(self):
        self.assertEqual(len(self.old), 7)
        self.assertEqual(self.contexts[:-1], self.old)
        self.assertEqual(len(self.contexts), 8)
        self.assertEqual(len(self.maps[CURRENT]), 309)
        actual = {n: {'bytes': (ROOT / n).stat().st_size, 'sha256': GATE.digest(ROOT / n)} for n in self.original}
        self.assertEqual(CONTEXT.select_context(actual, self.contexts)[0], CURRENT)
        self.gate()  # Real checkout, actual method used by normal portable discovery.
        self.assertEqual(len(CONTEXT.pre_lower_contour_baselines(EXP, self.old)), 54)

    def test_representative_actual_gate_rejections_and_exact_restore(self):
        with tempfile.TemporaryDirectory(prefix='nvwa73-lower-') as directory:
            root = Path(directory)
            exp = root / 'experiments/73-high-poly-eyes'
            exp.mkdir(parents=True)
            for name in self.original:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, path)
            for name in ['FROZEN-INPUTS.json', CONTEXT.CONTEXT_NAME, CONTEXT.SHORT01_CONTEXT_NAME,
                         CONTEXT.SELECTOR_CONTEXT_NAME, CONTEXT.AUTHORING_CONTEXT_NAME,
                         CONTEXT.MULTISEGMENT_CONTEXT_NAME, CONTEXT.CHEEK_CONTEXT_NAME,
                         CONTEXT.LOWER_CONTEXT_NAME]:
                shutil.copyfile(EXP / name, exp / name)
            shutil.copytree(EXP / 'fixtures', exp / 'fixtures')
            changed = 'crates/nvwa-core/src/b1.rs'
            unchanged = 'crates/nvwa-b1-adapter/src/lib.rs'
            cases = [(changed, 'missing'), (changed, 'corrupt'), (changed, 'symlink'),
                     (unchanged, 'corrupt'), (changed, 'mixed')]
            for name, fault in cases:
                path = root / name
                raw = path.read_bytes()
                target = root / 'original-source'
                target.write_bytes(raw)
                path.unlink()
                try:
                    if fault == 'corrupt': path.write_bytes(raw + b'\nchanged\n')
                    elif fault == 'symlink': path.symlink_to(target)
                    elif fault == 'mixed': path.write_bytes(CONTEXT.pre_lower_contour_baselines(EXP, self.old)[name])
                    with self.assertRaisesRegex(AssertionError, 'FROZEN-INPUTS.json'):
                        self.gate(root, exp)
                finally:
                    if path.exists() or path.is_symlink(): path.unlink()
                    path.write_bytes(raw)
                self.assertEqual(path.read_bytes(), raw)
                self.gate(root, exp)
            manifest = exp / CONTEXT.LOWER_CONTEXT_NAME
            raw = manifest.read_bytes()
            for fault in ['missing', 'corrupt', 'extra', 'mixed', 'symlink']:
                manifest.unlink()
                try:
                    if fault == 'corrupt': manifest.write_bytes(raw + b' ')
                    elif fault == 'symlink': manifest.symlink_to(EXP / CONTEXT.LOWER_CONTEXT_NAME)
                    elif fault in ['extra', 'mixed']:
                        value = json.loads(raw)
                        if fault == 'extra': value['overrides']['unreviewed'] = {'bytes': 0, 'sha256': '0' * 64}
                        else: value['overrides'][changed] = self.original[changed]
                        manifest.write_text(json.dumps(value))
                    with self.assertRaisesRegex(AssertionError, 'FROZEN-INPUTS.json'):
                        self.gate(root, exp)
                finally:
                    if manifest.exists() or manifest.is_symlink(): manifest.unlink()
                    manifest.write_bytes(raw)
                self.gate(root, exp)

    def test_cheap_bidirectional_per_path_crossovers_with_old_seven(self):
        count = 0
        for historical, _ in self.old:
            for left, right in [(CURRENT, historical), (historical, CURRENT)]:
                for name in self.maps[left]:
                    if self.maps[left][name] == self.maps[right][name]: continue
                    actual = dict(self.maps[left], **{name: self.maps[right][name]})
                    matches = [n for n, expected in self.contexts if actual == expected]
                    if matches: self.assertEqual(CONTEXT.select_context(actual, self.contexts)[0], matches[0])
                    else:
                        with self.assertRaisesRegex(ValueError, 'FROZEN-INPUTS.json'):
                            CONTEXT.select_context(actual, self.contexts)
                    count += 1
        self.assertGreater(count, 0)
        with self.assertRaisesRegex(ValueError, 'FROZEN-INPUTS.json'):
            CONTEXT.select_context(dict(self.maps[CURRENT], unreviewed={'bytes': 0, 'sha256': '0' * 64}), self.contexts)

if __name__ == '__main__':
    unittest.main()
