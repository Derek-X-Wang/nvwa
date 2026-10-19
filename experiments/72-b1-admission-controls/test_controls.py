"""Runner tooling controls; synthetic logs below are NEVER runtime evidence."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('admission72_runner', HERE / 'run.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
ROOT = HERE.parents[1]


def log(test=runner.ENDPOINT, failed=False, marker=''):
    if failed:
        return (f'running 1 test\ntest {test} ... \nthread test panicked at source:\n'
                + marker + '\nFAILED\n\ntest result: FAILED. 0 passed; 1 failed; 0 ignored\n')
    return f'running 1 test\ntest {test} ... ok\n\ntest result: ok. 1 passed; 0 failed; 0 ignored\n'


class ToolingControls(unittest.TestCase):
    def input_copy(self, directory):
        root = Path(directory) / 'source'
        pins = json.loads((HERE / 'pins.json').read_text())
        for relative in pins['files']:
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)
        return root, pins

    def test_exact_current_context_is_explicit_and_execution_stays_historical(self):
        pins = runner.check_inputs(ROOT)
        context = pins['checked_input_context']
        self.assertEqual(context['id'], 'issue86-runtime-retention-v1')
        self.assertEqual(context['current_rust_execution'], 'NOT-RUN')
        self.assertEqual(context['execution_source'], 'immutable baseline581 archive only')
        self.assertEqual(pins['files'][runner.RUNTIME], runner.RUNTIME_SHA)
        self.assertNotEqual(context['files'][runner.RUNTIME], runner.RUNTIME_SHA)
        with self.assertRaisesRegex(ValueError, 'source input context mismatch'):
            runner.check_source_context(ROOT, pins, historical_only=True)

    def test_every_pinned_input_mutation_rejects_and_restores(self):
        with tempfile.TemporaryDirectory(prefix='nvwa72-input-control-') as directory:
            root, pins = self.input_copy(directory)
            for relative in pins['files']:
                with self.subTest(relative=relative):
                    path = root / relative
                    original = path.read_bytes()
                    try:
                        path.write_bytes(original + b'\nchanged\n')
                        with self.assertRaisesRegex(ValueError, 'source input context mismatch'):
                            runner.check_inputs(root)
                    finally:
                        path.write_bytes(original)
                    runner.check_inputs(root)

    def test_missing_and_symlink_source_rejects(self):
        with tempfile.TemporaryDirectory(prefix='nvwa72-input-control-') as directory:
            root, _ = self.input_copy(directory)
            path = root / runner.RUNTIME
            original = path.read_bytes()
            path.unlink()
            with self.assertRaisesRegex(ValueError, 'source input missing'):
                runner.check_inputs(root)
            target = Path(directory) / 'runtime-original'
            target.write_bytes(original)
            path.symlink_to(target)
            with self.assertRaisesRegex(ValueError, 'source input symlink'):
                runner.check_inputs(root)

    def test_bridge_and_original_pins_cannot_be_rewritten(self):
        with tempfile.TemporaryDirectory(prefix='nvwa72-material-control-') as directory:
            material = Path(directory)
            for name in runner.PACKAGE:
                shutil.copyfile(HERE / name, material / name)
            for name, error in [('pins.json', 'immutable baseline pins identity mismatch'),
                                ('input-context-v1.json', 'input context manifest identity mismatch')]:
                path = material / name
                original = path.read_bytes()
                try:
                    path.write_bytes(original + b' ')
                    with patch.object(runner, 'HERE', material):
                        with self.assertRaisesRegex(ValueError, error):
                            runner.check_inputs(ROOT)
                finally:
                    path.write_bytes(original)
                with patch.object(runner, 'HERE', material):
                    runner.check_inputs(ROOT)

    def test_original_coverage_bounds_and_zero_fields_cannot_be_rewritten(self):
        with tempfile.TemporaryDirectory(prefix='nvwa72-case-control-') as directory:
            material = Path(directory)
            for name in runner.PACKAGE:
                shutil.copyfile(HERE / name, material / name)
            path = material / 'cases.json'
            original = path.read_bytes()
            for change, error in [('bounds', 'original numeric bounds changed'),
                                  ('zero', 'zero extension fields changed'),
                                  ('case', 'original40 case/recipe/pose drift')]:
                plan = json.loads(original)
                if change == 'bounds':
                    plan['bounds']['body_position_m'] *= 10
                elif change == 'zero':
                    plan['zero_extension'].pop()
                else:
                    plan['cases'].pop()
                try:
                    path.write_text(json.dumps(plan))
                    with patch.object(runner, 'HERE', material):
                        with self.assertRaisesRegex(ValueError, error):
                            runner.check_inputs(ROOT)
                finally:
                    path.write_bytes(original)
                with patch.object(runner, 'HERE', material):
                    runner.check_inputs(ROOT)

    def test_five_exact_mapping_faults_reject_context_and_numeric_witness(self):
        bridge = json.loads((HERE / 'input-context-v1.json').read_text())
        with tempfile.TemporaryDirectory(prefix='nvwa72-mapping-control-') as directory:
            root, _ = self.input_copy(directory)
            path = root / runner.RUNTIME
            original = path.read_text()
            for fault in runner.FAULTS:
                with self.subTest(fault=fault['id']):
                    changed = runner.mutate(original, fault)
                    try:
                        path.write_text(changed)
                        with self.assertRaisesRegex(ValueError, 'source input context mismatch'):
                            runner.check_inputs(root)
                        with self.assertRaisesRegex(ValueError, 'unchanged numeric section mismatch: signed_target_mapping'):
                            runner.check_unchanged_sections(changed, bridge)
                    finally:
                        path.write_text(original)
                    runner.check_inputs(root)

    def test_original_40_coverage_and_immutable_source(self):
        pins = runner.check_inputs(ROOT)
        self.assertEqual(pins['files'][runner.RUNTIME], runner.RUNTIME_SHA)
        plan = json.loads((HERE / 'cases.json').read_text())
        self.assertEqual(len(plan['cases']), 40)
        recipes = {row['recipe_id'] for row in plan['cases']}
        for recipe in recipes:
            self.assertEqual({row['pose_id'] for row in plan['cases'] if row['recipe_id'] == recipe},
                             {'neutral', 'shoulder', 'elbow', 'knee', 'combined'})

    def test_five_faults_patch_real_mapping_only_and_restore_exactly(self):
        original = (ROOT / runner.RUNTIME).read_bytes()
        text = original.decode()
        start = text.index('        let values = &c.document.character.parameters;')
        end = text.index('        let resolved = morphs', start)
        mutations = set()
        with tempfile.TemporaryDirectory(prefix='nvwa72-control-') as directory:
            path = Path(directory) / 'b1.rs'
            for fault in runner.FAULTS:
                changed = runner.mutate(text, fault)
                self.assertEqual(changed[:start], text[:start])
                self.assertTrue(changed.endswith(text[end:]))
                self.assertIn('head_width', changed[start:])
                mutations.add(runner.sha(changed.encode()))
                try:
                    path.write_text(changed)
                    self.assertNotEqual(path.read_bytes(), original)
                finally:
                    path.write_bytes(original)
                self.assertEqual(path.read_bytes(), original)
        self.assertEqual(len(mutations), 5)
        self.assertEqual((ROOT / runner.RUNTIME).read_bytes(), original)

    def test_include_is_only_inside_existing_cfg_test_module(self):
        original = (ROOT / runner.RUNTIME).read_text()
        injected = runner.inject(original)
        self.assertEqual(injected.count('include!("admission72_tests.rs")'), 1)
        self.assertEqual(injected.replace(runner.INCLUDE, ''), original)
        self.assertLess(injected.index('#[cfg(test)]\nmod tests'), injected.index(runner.INCLUDE))
        self.assertLess(injected.index(runner.INCLUDE), injected.index('struct FrameSample'))

    def test_missing_or_duplicated_patch_seam_rejected(self):
        for text in ('none', runner.VALUE_SEAM * 2):
            with self.assertRaisesRegex(ValueError, 'exactly once'):
                runner.mutate(text, runner.FAULTS[2])

    def test_named_green_accepted(self):
        self.assertTrue(runner.verdict(0, log(), runner.ENDPOINT))

    def test_every_intended_semantic_red_shape_accepted(self):
        for fault in runner.FAULTS:
            text = log(failed=True, marker=fault['marker'] + fault.get('marker2', ''))
            self.assertTrue(runner.verdict(101, text, runner.ENDPOINT, fault))

    def test_compile_failure_cannot_count_as_red(self):
        fault = runner.FAULTS[0]
        text = log(failed=True, marker=fault['marker'])
        for bad in ('error[E0063]: missing field', 'could not compile nvwa-runtime'):
            with self.assertRaisesRegex(ValueError, 'compilation failed'):
                runner.verdict(101, text + bad, runner.ENDPOINT, fault)

    def test_unrelated_panic_wrong_sign_or_wrong_test_cannot_count_as_red(self):
        fault = runner.FAULTS[0]
        for text in (log(failed=True, marker='source authentication failed'),
                     log(test='b1::tests::decoy', failed=True, marker=fault['marker']),
                     log(failed=True, marker='head_width 1 must reach actual Mesh POSITION')):
            with self.assertRaises(ValueError):
                runner.verdict(101, text, runner.ENDPOINT, fault)

    def test_no_test_success_or_unexpected_green_cannot_count_as_red(self):
        fault = runner.FAULTS[0]
        for code, text in ((101, 'running 0 tests\ntest result: ok. 0 passed; 0 failed'),
                           (0, log()), (124, log(failed=True, marker=fault['marker']))):
            with self.assertRaises(ValueError):
                runner.verdict(code, text, runner.ENDPOINT, fault)

    def test_existing_output_is_never_reused(self):
        with tempfile.TemporaryDirectory(prefix='nvwa72-output-control-') as directory:
            out = Path(directory) / 'already-owned'
            out.mkdir()
            sentinel = out / 'sentinel'
            sentinel.write_bytes(b'preserve')
            args = argparse.Namespace(source_root=ROOT, check_inputs=False, out=out, command_timeout=1)
            with self.assertRaises(FileExistsError):
                runner.run(args)
            self.assertEqual(sentinel.read_bytes(), b'preserve')
            self.assertEqual(list(out.iterdir()), [sentinel])


if __name__ == '__main__':
    unittest.main()
