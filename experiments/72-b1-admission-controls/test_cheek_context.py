"""One new exact source context; original four-context controls remain intact."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location('cheek72_runner', HERE / 'run.py')
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)
CHEEK = 'b1-cheek-fullness-product-v1'


class CheekContextControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pins = json.loads((HERE / 'pins.json').read_bytes())
        cls.old = runner.source_contexts(cls.pins)
        cls.contexts = runner.admitted_source_contexts(cls.pins)
        cls.maps = dict(cls.contexts)

    def copied_inputs(self, directory):
        root = Path(directory) / 'source'
        for name in self.pins['files']:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, path)
        return root

    def test_new_exact_current_context_and_historical_only_refusal(self):
        result = runner.check_inputs(ROOT)['checked_input_context']
        self.assertEqual(result['id'], CHEEK)
        self.assertEqual(result['files'], self.maps[CHEEK])
        self.assertEqual(result['current_rust_execution'], 'NOT-RUN')
        self.assertEqual(result['execution_source'], 'immutable baseline581 archive only')
        self.assertEqual(self.contexts[:-1], self.old)
        self.assertEqual(len(self.contexts), 5)
        with self.assertRaisesRegex(ValueError, 'source input context mismatch'):
            runner.check_source_context(ROOT, self.pins, historical_only=True)
        self.assertEqual(runner.select_source_context(self.pins['files'], self.contexts,
                                                    historical_only=True), 'baseline581')
        bridge = json.loads((HERE / 'input-context-v1.json').read_bytes())
        runner.check_unchanged_sections((ROOT / runner.RUNTIME).read_text(), bridge)

    def test_bidirectional_single_input_crossovers_and_old_mixtures(self):
        count = 0
        for historical, _ in self.old:
            for left, right in ((CHEEK, historical), (historical, CHEEK)):
                for name, digest in self.maps[left].items():
                    if digest == self.maps[right][name]:
                        continue
                    actual = dict(self.maps[left], **{name: self.maps[right][name]})
                    matches = [context for context, expected in self.contexts if actual == expected]
                    with self.subTest(left=left, right=right, source=name):
                        if matches:
                            self.assertEqual(runner.select_source_context(actual, self.contexts), matches[0])
                        else:
                            with self.assertRaisesRegex(ValueError, 'source input context mismatch'):
                                runner.select_source_context(actual, self.contexts)
                    count += 1
        self.assertGreater(count, 0)
        # Every formerly forbidden four-context mixture remains forbidden under
        # the complete selector, without adding new Cartesian dimensions.
        import itertools
        changing = [name for name in self.pins['files']
                    if len({files[name] for _, files in self.old}) > 1]
        choices = [sorted({files[name] for _, files in self.old}) for name in changing]
        accepted = rejected = 0
        for combination in itertools.product(*choices):
            actual = dict(self.pins['files'])
            actual.update(zip(changing, combination))
            matches = [name for name, files in self.old if actual == files]
            if matches:
                self.assertEqual(runner.select_source_context(actual, self.contexts), matches[0])
                accepted += 1
            else:
                with self.assertRaisesRegex(ValueError, 'source input context mismatch'):
                    runner.select_source_context(actual, self.contexts)
                rejected += 1
        self.assertEqual((accepted, rejected), (4, 92))
        for actual in ({}, dict(self.maps[CHEEK], unreviewed='0' * 64)):
            with self.assertRaisesRegex(ValueError, 'source input context mismatch'):
                runner.select_source_context(actual, self.contexts)

    def test_every_new_source_input_missing_corrupt_symlink_and_exact_restore(self):
        with tempfile.TemporaryDirectory(prefix='nvwa72-cheek-inputs-') as temporary:
            root = self.copied_inputs(temporary)
            before = {name: (root / name).read_bytes() for name in self.pins['files']}
            for name, raw in before.items():
                path = root / name
                target = Path(temporary) / 'original-copy'
                target.write_bytes(raw)
                for fault in ('missing', 'corrupt', 'symlink'):
                    with self.subTest(source=name, fault=fault):
                        path.unlink()
                        try:
                            if fault == 'corrupt':
                                path.write_bytes(raw + b'\nchanged\n')
                            elif fault == 'symlink':
                                path.symlink_to(target)
                            with self.assertRaisesRegex(ValueError, 'source input'):
                                runner.check_source_context(root, self.pins)
                        finally:
                            if path.exists() or path.is_symlink():
                                path.unlink()
                            path.write_bytes(raw)
                        self.assertEqual(path.read_bytes(), raw)
                        self.assertEqual(runner.check_source_context(root, self.pins)['id'], CHEEK)
            self.assertEqual({name: (root / name).read_bytes() for name in before}, before)

    def test_new_context_manifest_is_mandatory_and_old_manifests_still_pinned(self):
        with tempfile.TemporaryDirectory(prefix='nvwa72-cheek-context-') as temporary:
            material = Path(temporary) / 'material'
            material.mkdir()
            for name in runner.PACKAGE:
                shutil.copyfile(HERE / name, material / name)
            path = material / 'input-context-v4.json'
            raw = path.read_bytes()
            target = Path(temporary) / 'original-context.json'
            target.write_bytes(raw)
            for fault in ('missing', 'empty', 'corrupt', 'extra', 'mixed', 'symlink'):
                with self.subTest(fault=fault):
                    path.unlink()
                    try:
                        if fault == 'empty':
                            path.write_bytes(b'')
                        elif fault == 'corrupt':
                            path.write_bytes(raw + b' ')
                        elif fault in ('extra', 'mixed'):
                            changed = json.loads(raw)
                            if fault == 'extra':
                                changed['overrides']['unreviewed'] = '0' * 64
                            else:
                                changed['overrides'][runner.RUNTIME] = self.pins['files'][runner.RUNTIME]
                            path.write_text(json.dumps(changed))
                        elif fault == 'symlink':
                            path.symlink_to(target)
                        with patch.object(runner, 'HERE', material):
                            with self.assertRaisesRegex(ValueError, 'identity mismatch'):
                                runner.check_source_context(ROOT, self.pins)
                    finally:
                        if path.exists() or path.is_symlink():
                            path.unlink()
                        path.write_bytes(raw)
                    with patch.object(runner, 'HERE', material):
                        self.assertEqual(runner.check_source_context(ROOT, self.pins)['id'], CHEEK)


if __name__ == '__main__':
    unittest.main()
