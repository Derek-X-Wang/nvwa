"""Exercise the CI-called source gate in disposable repository copies."""
import hashlib
import importlib.util
import itertools
import math
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

EXP = Path(__file__).resolve().parent
ROOT = EXP.parents[1]
SPEC = importlib.util.spec_from_file_location('eye73_frozen_gate_controls', EXP / 'frozen_context.py')
CONTEXT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTEXT)
PRODUCT = 'hair79-short01-product-v1'
SELECTOR = 'hair79-selector-product-v1'
ORIGINAL = 'original-frozen309'
CLOSEOUT = 'character-stage-closeout-v1'


class FrozenInputGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory(prefix='nvwa73-freeze-')
        cls.addClassCleanup(cls.scratch.cleanup)
        cls.root = Path(cls.scratch.name)
        cls.exp = cls.root / 'experiments/73-high-poly-eyes'
        cls.exp.mkdir(parents=True)
        cls.raw = (EXP / 'FROZEN-INPUTS.json').read_bytes()
        cls.inputs = json.loads(cls.raw)
        # Copy the real inputs, never link them: mutations must not reach the repo.
        for name in cls.inputs:
            destination = cls.root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, destination)
        for name in ['test_prepare.py', 'cpu_probe.py', 'frozen_context.py',
                     'source-context-closeout-v1.json', 'source-context-hair79-short01-v1.json',
                     'source-context-hair79-selector-v1.json']:
            shutil.copyfile(EXP / name, cls.exp / name)
        shutil.copytree(EXP / 'fixtures', cls.exp / 'fixtures')
        cls.contexts = CONTEXT.source_contexts(EXP, cls.raw, cls.inputs)
        cls.old_contexts = [(name, files) for name, files in cls.contexts if name != SELECTOR]
        cls.maps = dict(cls.contexts)
        historical = CONTEXT.historical_sources(EXP, cls.contexts)
        cls.original = historical[ORIGINAL]
        cls.selector = {name: (cls.root / name).read_bytes() for name in cls.original}
        # The old product is reconstructed from authenticated pre-selector UI bytes.
        # All other product bytes remain identical; never reverse changed live UI.
        cls.current = dict(cls.selector)
        cls.current.update(historical[PRODUCT])
        cls.closeout = dict(cls.original)
        closeout = json.loads((EXP / 'source-context-closeout-v1.json').read_bytes())
        for name, item in closeout['overrides'].items():
            raw = historical[CLOSEOUT].get(name, (cls.root / name).read_bytes())
            if {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} != item:
                raise ValueError('archived closeout fixture does not match old pin: ' + name)
            cls.closeout[name] = raw
        cls.snapshots = {ORIGINAL: cls.original, CLOSEOUT: cls.closeout, PRODUCT: cls.current,
                         SELECTOR: cls.selector}
        for context, snapshot in cls.snapshots.items():
            for name, raw in snapshot.items():
                if {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} != cls.maps[context][name]:
                    raise ValueError('complete source fixture mismatch: ' + context + ' ' + name)

    def write_context(self, name):
        for relative, raw in self.snapshots[name].items():
            (self.root / relative).write_bytes(raw)

    def gate(self, raw, rejects):
        manifest = self.exp / 'FROZEN-INPUTS.json'
        if raw is None:
            manifest.unlink(missing_ok=True)
        else:
            manifest.write_bytes(raw)
        command = [sys.executable, '-B']
        if sys.flags.optimize:
            command.append('-O')
        command += [str(self.exp / 'test_prepare.py'),
                    'SourceContract.test_frozen_source_inputs', '-v']
        result = subprocess.run(command, cwd=self.root, capture_output=True,
                                text=True, timeout=30)
        output = result.stdout + result.stderr
        self.assertIn('Ran 1 test', output, output)
        self.assertNotIn('skipped', output, output)
        self.assertNotIn('ERROR', output, output)
        if rejects:
            self.assertNotEqual(result.returncode, 0, output)
            self.assertIn('FAILED (failures=1)', output, output)
            self.assertIn('FROZEN-INPUTS.json', output, output)
        else:
            self.assertEqual(result.returncode, 0, output)
            self.assertIn('\nOK\n', output, output)

    def test_valid_current_manifest(self):
        self.gate(self.raw, rejects=False)

    def test_exact_original_context_accepts_at_actual_called_gate_without_git_history(self):
        try:
            self.write_context(ORIGINAL)
            self.gate(self.raw, rejects=False)
        finally:
            self.write_context(SELECTOR)

    def test_exact_closeout_context_accepts_at_actual_called_gate_without_git_history(self):
        try:
            self.write_context(CLOSEOUT)
            self.gate(self.raw, rejects=False)
        finally:
            self.write_context(SELECTOR)

    def test_all_fourteen_mixed_contexts_reject_at_actual_called_gate(self):
        names = list(json.loads((EXP / 'source-context-closeout-v1.json').read_bytes())['overrides'])
        try:
            self.write_context(ORIGINAL)
            for choices in itertools.product((False, True), repeat=4):
                if all(choices) or not any(choices):
                    continue
                with self.subTest(closeout_files=choices):
                    for name, closeout in zip(names, choices):
                        (self.root / name).write_bytes((self.closeout if closeout else self.original)[name])
                    self.gate(self.raw, rejects=True)
        finally:
            self.write_context(SELECTOR)

    def test_every_product_single_path_crossover_rejects_at_actual_called_gate(self):
        try:
            for historical in (ORIGINAL, CLOSEOUT):
                for left, right in ((PRODUCT, historical), (historical, PRODUCT)):
                    self.write_context(left)
                    for name, raw in self.snapshots[left].items():
                        other = self.snapshots[right][name]
                        if raw == other:
                            continue
                        with self.subTest(context=left, substituted=right, source=name):
                            (self.root / name).write_bytes(other)
                            self.gate(self.raw, rejects=True)
                            (self.root / name).write_bytes(raw)
        finally:
            self.write_context(SELECTOR)

    def test_all_complete_context_maps_and_every_mixture_reject_except_three_admitted(self):
        changing = list(self.original)
        variants = [sorted({json.dumps(files[name], sort_keys=True) for _, files in self.old_contexts})
                    for name in changing]
        accepted = rejected = 0
        for values in itertools.product(*variants):
            actual = dict(self.inputs)
            actual.update({name: json.loads(value) for name, value in zip(changing, values)})
            matching = [name for name, expected in self.old_contexts if actual == expected]
            if matching:
                self.assertEqual(CONTEXT.select_context(actual, self.old_contexts)[0], matching[0])
                accepted += 1
            else:
                with self.assertRaisesRegex(ValueError, 'source context'):
                    CONTEXT.select_context(actual, self.old_contexts)
                rejected += 1
        self.assertEqual((accepted, rejected), (3, 12285))
        for context, expected in self.old_contexts:
            for name in expected:
                actual = dict(expected)
                actual.pop(name)
                with self.assertRaisesRegex(ValueError, 'source context'):
                    CONTEXT.select_context(actual, self.old_contexts)
            for actual in ({}, dict(expected, unreviewed={'bytes': 0, 'sha256': '0' * 64})):
                with self.assertRaisesRegex(ValueError, 'source context'):
                    CONTEXT.select_context(actual, self.old_contexts)

    def test_exact_old_product_and_selector_accept_at_actual_called_gate(self):
        try:
            for context in (PRODUCT, SELECTOR):
                with self.subTest(context=context):
                    self.write_context(context)
                    self.gate(self.raw, rejects=False)
        finally:
            self.write_context(SELECTOR)

    def test_selector_bidirectional_single_path_crossovers_at_actual_called_gate(self):
        try:
            for historical in (ORIGINAL, CLOSEOUT, PRODUCT):
                for left, right in ((SELECTOR, historical), (historical, SELECTOR)):
                    self.write_context(left)
                    for name, raw in self.snapshots[left].items():
                        other = self.snapshots[right][name]
                        if raw == other:
                            continue
                        actual = dict(self.maps[left])
                        actual[name] = self.maps[right][name]
                        # A crossover equal to a complete reviewed map must accept.
                        matching = [context for context, expected in self.contexts if actual == expected]
                        with self.subTest(context=left, substituted=right, source=name,
                                          complete_match=matching):
                            (self.root / name).write_bytes(other)
                            self.gate(self.raw, rejects=not matching)
                            (self.root / name).write_bytes(raw)
        finally:
            self.write_context(SELECTOR)

    def test_old_subspace_forbidden_mixtures_still_reject_with_four_contexts(self):
        changing = list(self.original)
        variants = [sorted({json.dumps(files[name], sort_keys=True) for _, files in self.old_contexts})
                    for name in changing]
        accepted = rejected = 0
        for values in itertools.product(*variants):
            actual = dict(self.inputs)
            actual.update({name: json.loads(value) for name, value in zip(changing, values)})
            old_match = [name for name, expected in self.old_contexts if actual == expected]
            if old_match:
                self.assertEqual(CONTEXT.select_context(actual, self.contexts)[0], old_match[0])
                accepted += 1
            else:
                with self.assertRaisesRegex(ValueError, 'source context'):
                    CONTEXT.select_context(actual, self.contexts)
                rejected += 1
        self.assertEqual((accepted, rejected), (3, 12285))

    def test_expanded_four_context_matrix_has_only_four_complete_admissions(self):
        changing = list(self.original)
        variants = [sorted({json.dumps(files[name], sort_keys=True) for _, files in self.contexts})
                    for name in changing]
        # The reviewed maps have ten binary paths and three ternary paths:
        # runtime/b1.rs plus the two newly archived/reviewed UI paths.
        self.assertEqual(sorted(map(len, variants)), [2] * 10 + [3] * 3)
        self.assertEqual(math.prod(map(len, variants)), 27648)
        accepted = rejected = 0
        for values in itertools.product(*variants):
            actual = dict(self.inputs)
            actual.update({name: json.loads(value) for name, value in zip(changing, values)})
            matching = [name for name, expected in self.contexts if actual == expected]
            if matching:
                self.assertEqual(CONTEXT.select_context(actual, self.contexts)[0], matching[0])
                accepted += 1
            else:
                with self.assertRaisesRegex(ValueError, 'source context'):
                    CONTEXT.select_context(actual, self.contexts)
                rejected += 1
        self.assertEqual((accepted, rejected), (4, 27644))
        for context, expected in self.contexts:
            for name in expected:
                actual = dict(expected)
                actual.pop(name)
                with self.assertRaisesRegex(ValueError, 'source context'):
                    CONTEXT.select_context(actual, self.contexts)
            for actual in ({}, dict(expected, unreviewed={'bytes': 0, 'sha256': '0' * 64})):
                with self.assertRaisesRegex(ValueError, 'source context'):
                    CONTEXT.select_context(actual, self.contexts)

    def test_selector_ui_missing_symlink_and_changed_hash_size_reject_at_actual_called_gate(self):
        self.write_context(SELECTOR)
        for name in ('crates/nvwa-studio/src/appearance_ui.rs',
                     'crates/nvwa-studio/src/appearance_ui_tests.rs'):
            path = self.root / name
            original = path.read_bytes()
            target = self.root / 'selector-ui-source'
            target.write_bytes(original)
            for fault in ('missing', 'symlink', 'hash', 'size'):
                with self.subTest(source=name, fault=fault):
                    path.unlink()
                    try:
                        if fault == 'symlink':
                            path.symlink_to(target)
                        elif fault == 'hash':
                            path.write_bytes(bytes([original[0] ^ 1]) + original[1:])
                        elif fault == 'size':
                            path.write_bytes(original[:-1])
                        self.gate(self.raw, rejects=True)
                    finally:
                        if path.exists() or path.is_symlink():
                            path.unlink()
                        path.write_bytes(original)
        self.gate(self.raw, rejects=False)

    def corrupt_required_file(self, relative, label):
        path = self.exp / relative
        original = path.read_bytes()
        target = self.root / 'original-context-or-fixture'
        target.write_bytes(original)
        faults = ['missing', 'empty', 'corrupt', 'tampered', 'symlink']
        if relative.endswith('.json'):
            faults += ['empty-object', 'invalid-json']
        for fault in faults:
            with self.subTest(file=label, fault=fault):
                path.unlink()
                try:
                    if fault == 'symlink':
                        path.symlink_to(target)
                    elif fault != 'missing':
                        path.write_bytes({'empty': b'', 'corrupt': bytes([original[0] ^ 1]) + original[1:],
                                          'empty-object': b'{}', 'invalid-json': b'{',
                                          'tampered': original + b' '}[fault])
                    self.gate(self.raw, rejects=True)
                finally:
                    if path.exists() or path.is_symlink():
                        path.unlink()
                    path.write_bytes(original)
        self.gate(self.raw, rejects=False)

    def test_context_manifest_missing_empty_corrupt_tampered_and_symlink_reject(self):
        for relative in (CONTEXT.CONTEXT_NAME, CONTEXT.SHORT01_CONTEXT_NAME,
                         CONTEXT.SELECTOR_CONTEXT_NAME):
            self.corrupt_required_file(relative, relative)

    def test_historical_fixture_manifest_and_every_blob_fail_closed_at_actual_called_gate(self):
        self.corrupt_required_file(CONTEXT.FIXTURES_NAME, 'historical fixture manifest')
        manifest = json.loads((EXP / CONTEXT.FIXTURES_NAME).read_bytes())
        for context, items in manifest['contexts'].items():
            for name, item in items.items():
                self.corrupt_required_file(item['fixture'], context + ' ' + name)

    def test_undeclared_historical_fixture_rejects_at_actual_called_gate(self):
        path = self.exp / 'fixtures/source-contexts/unreviewed-source'
        try:
            path.write_bytes(b'unreviewed')
            self.gate(self.raw, rejects=True)
        finally:
            path.unlink()
        self.gate(self.raw, rejects=False)

    def test_original_manifest_cannot_be_replaced_with_complete_current_hashes(self):
        current = dict(self.inputs)
        for name, raw in self.current.items():
            current[name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        self.gate(json.dumps(current).encode(), rejects=True)

    def test_original_manifest_symlink_rejects_at_actual_called_gate(self):
        path = self.exp / 'FROZEN-INPUTS.json'
        target = self.root / 'original-inputs.json'
        target.write_bytes(self.raw)
        path.unlink(missing_ok=True)
        try:
            path.symlink_to(target)
            self.gate(self.raw, rejects=True)
        finally:
            path.unlink()
            path.write_bytes(self.raw)

    def test_missing_and_symlink_source_inputs_reject_at_actual_called_gate(self):
        name = next(iter(self.current))
        path = self.root / name
        original = path.read_bytes()
        target = self.root / 'original-source.txt'
        target.write_bytes(original)
        try:
            path.unlink()
            self.gate(self.raw, rejects=True)
            path.symlink_to(target)
            self.gate(self.raw, rejects=True)
        finally:
            if path.exists() or path.is_symlink():
                path.unlink()
            path.write_bytes(original)

    def test_missing_manifest_rejects_without_skip(self):
        self.gate(None, rejects=True)

    def test_empty_manifest_rejects(self):
        self.gate(b'{}', rejects=True)

    def test_corrupt_manifest_rejects(self):
        name = next(iter(self.inputs))
        item = self.inputs[name]
        for raw in [b'', b'{', b'[]', b'null', b'{"input": null}',
                    json.dumps({name: {}}).encode(),
                    json.dumps({name: {'bytes': -1, 'sha256': 'bad'}}).encode(),
                    json.dumps({name: {'bytes': True, 'sha256': '0' * 64}}).encode(),
                    json.dumps({name: {**item, 'sha256': 'bad'}}).encode(),
                    json.dumps({name: {**item, 'sha256': '0' * 64}}).encode(),
                    json.dumps({name: {**item, 'bytes': item['bytes'] + 1}}).encode()]:
            with self.subTest(raw=raw):
                self.gate(raw, rejects=True)

    def test_changed_file_hash_and_size_reject(self):
        # Same-size corruption exercises SHA; truncation also exercises bytes.
        name = min(self.inputs, key=lambda key: self.inputs[key]['bytes'])
        path = self.root / name
        original = path.read_bytes()
        self.assertGreater(len(original), 0)
        try:
            for raw in [bytes([original[0] ^ 1]) + original[1:], original[:-1]]:
                with self.subTest(size=len(raw)):
                    path.write_bytes(raw)
                    self.gate(self.raw, rejects=True)
        finally:
            path.write_bytes(original)


if __name__ == '__main__':
    unittest.main()
