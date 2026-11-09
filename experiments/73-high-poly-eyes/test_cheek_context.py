"""Bounded seventh exact-context controls; historical matrices stay unchanged."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

EXP = Path(__file__).resolve().parent
ROOT = EXP.parents[1]
SPEC = importlib.util.spec_from_file_location('cheek73_context', EXP / 'frozen_context.py')
CONTEXT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTEXT)
CHEEK = 'b1-cheek-fullness-product-v1'
PRIOR = 'b1-multisegment-product-v1'
sha = lambda raw: hashlib.sha256(raw).hexdigest()


class CheekSourceContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='nvwa73-cheek-context-')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.exp = cls.root / 'experiments/73-high-poly-eyes'
        cls.exp.mkdir(parents=True)
        cls.raw = (EXP / 'FROZEN-INPUTS.json').read_bytes()
        cls.original = json.loads(cls.raw)
        cls.old = CONTEXT.source_contexts(EXP, cls.raw, cls.original)
        cls.contexts = CONTEXT.admitted_source_contexts(EXP, cls.raw, cls.original)
        cls.maps = dict(cls.contexts)
        cls.pre_contour = CONTEXT.pre_contour_baselines(EXP, cls.old)
        cls.pre_lower = CONTEXT.pre_lower_contour_baselines(EXP, cls.contexts)
        retained_lock = CONTEXT.pre_motion_query_sources(EXP, cls.raw, cls.original)['Cargo.lock']
        retained_cpu = (CONTEXT.pre_waist_sources(EXP, cls.raw, cls.original) | CONTEXT.pre_cpu_sources(EXP, cls.raw, cls.original))
        pool = {}
        for name in cls.original:
            raw = retained_lock if name == 'Cargo.lock' else retained_cpu[name] if name in retained_cpu else (ROOT / name).read_bytes()
            pool[sha(raw)] = raw
            path = cls.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        for name, raw in cls.pre_lower.items():
            (cls.root / name).write_bytes(raw)
            pool[sha(raw)] = raw
        for raw in cls.pre_contour.values():
            pool[sha(raw)] = raw
        for items in CONTEXT.historical_sources(EXP, cls.old).values():
            for raw in items.values():
                pool[sha(raw)] = raw
        for raw in CONTEXT.authoring_baselines(EXP, cls.original).values():
            pool[sha(raw)] = raw
        for raw in CONTEXT.multisegment_baselines(EXP, cls.old).values():
            pool[sha(raw)] = raw
        cls.bytes = {}
        for context, expected in cls.contexts:
            cls.bytes[context] = {}
            for name, pin in expected.items():
                raw = pool[pin['sha256']]
                if {'bytes': len(raw), 'sha256': sha(raw)} != pin:
                    raise ValueError('retained full context bytes mismatch: ' + context + ' ' + name)
                cls.bytes[context][name] = raw
        cls.active = CHEEK
        for name in ['test_prepare.py', 'cpu_probe.py', 'frozen_context.py',
                     CONTEXT.CONTEXT_NAME, CONTEXT.SHORT01_CONTEXT_NAME,
                     CONTEXT.SELECTOR_CONTEXT_NAME, CONTEXT.AUTHORING_CONTEXT_NAME,
                     CONTEXT.MULTISEGMENT_CONTEXT_NAME, CONTEXT.CHEEK_CONTEXT_NAME, CONTEXT.LOWER_CONTEXT_NAME]:
            shutil.copyfile(EXP / name, cls.exp / name)
        shutil.copytree(EXP / 'fixtures', cls.exp / 'fixtures')

    def write_context(self, context):
        current = self.maps[self.__class__.active]
        for name, pin in self.maps[context].items():
            if pin != current[name]:
                (self.root / name).write_bytes(self.bytes[context][name])
        self.__class__.active = context

    def setUp(self):
        self.write_context(CHEEK)

    def gate(self, rejects=False):
        (self.exp / 'FROZEN-INPUTS.json').write_bytes(self.raw)
        command = [sys.executable, '-B'] + (['-O'] if sys.flags.optimize else [])
        command += [str(self.exp / 'test_prepare.py'),
                    'SourceContract.test_frozen_source_inputs', '-v']
        result = subprocess.run(command, cwd=self.root, capture_output=True, text=True, timeout=30)
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

    def test_all_seven_complete_contexts_accept_at_actual_called_gate(self):
        self.assertEqual(self.contexts[:-1], self.old)
        self.assertEqual(len(self.old), 6)
        self.assertEqual(len(self.contexts), 7)
        for context, expected in self.contexts:
            self.write_context(context)
            self.assertEqual(len(expected), 309)
            self.gate()

    def test_bidirectional_per_input_crossovers_with_every_old_context(self):
        count = 0
        for historical, _ in self.old:
            for left, right in ((CHEEK, historical), (historical, CHEEK)):
                self.write_context(left)
                for name, pin in self.maps[left].items():
                    if pin == self.maps[right][name]:
                        continue
                    actual = dict(self.maps[left], **{name: self.maps[right][name]})
                    matching = [context for context, expected in self.contexts if actual == expected]
                    path = self.root / name
                    raw = self.bytes[left][name]
                    with self.subTest(context=left, substitution=right, source=name):
                        try:
                            path.write_bytes(self.bytes[right][name])
                            self.gate(rejects=not matching)
                        finally:
                            path.write_bytes(raw)
                        self.assertEqual(path.read_bytes(), raw)
                    count += 1
                self.gate()
        self.assertGreater(count, 0)

    def test_changed_frozen_inputs_missing_corrupt_symlink_and_exact_restore(self):
        changed = [name for name in self.original
                   if self.maps[CHEEK][name] != self.maps[PRIOR][name]]
        self.assertTrue(changed)
        target = self.root / 'original-source-copy'
        for name in changed:
            path = self.root / name
            raw = self.bytes[CHEEK][name]
            target.write_bytes(raw)
            for fault in ('missing', 'corrupt', 'symlink'):
                with self.subTest(source=name, fault=fault):
                    path.unlink()
                    try:
                        if fault == 'corrupt':
                            path.write_bytes(raw + b'\nchanged\n')
                        elif fault == 'symlink':
                            path.symlink_to(target)
                        self.gate(rejects=True)
                    finally:
                        if path.exists() or path.is_symlink():
                            path.unlink()
                        path.write_bytes(raw)
                    self.assertEqual(path.read_bytes(), raw)
            self.gate()

    def test_new_manifest_missing_corrupt_extra_mixed_symlink_and_restore(self):
        path = self.exp / CONTEXT.CHEEK_CONTEXT_NAME
        raw = path.read_bytes()
        target = self.root / 'original-context-copy'
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
                            changed['overrides']['unreviewed'] = {'bytes': 1, 'sha256': '0' * 64}
                        else:
                            name = next(name for name in self.original
                                        if self.maps[CHEEK][name] != self.maps[PRIOR][name])
                            changed['overrides'][name] = self.maps[PRIOR][name]
                        path.write_text(json.dumps(changed))
                    elif fault == 'symlink':
                        path.symlink_to(target)
                    self.gate(rejects=True)
                finally:
                    if path.exists() or path.is_symlink():
                        path.unlink()
                    path.write_bytes(raw)
                self.gate()

    def test_every_retained_crate_baseline_is_authenticated_and_restored(self):
        manifest = json.loads((self.exp / CONTEXT.CHEEK_BASELINES_NAME).read_bytes())
        for name, item in manifest['files'].items():
            path = self.exp / item['fixture']
            raw = path.read_bytes()
            with self.subTest(source=name):
                try:
                    path.write_bytes(raw + b'\nchanged\n')
                    with self.assertRaisesRegex(ValueError, 'pre-contour baseline bytes mismatch'):
                        CONTEXT.pre_contour_baselines(self.exp, self.old)
                finally:
                    path.write_bytes(raw)
                self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(CONTEXT.pre_contour_baselines(self.exp, self.old), self.pre_contour)
        for relative in [CONTEXT.CHEEK_BASELINES_NAME,
                         next(iter(manifest['files'].values()))['fixture']]:
            path = self.exp / relative
            raw = path.read_bytes()
            target = self.root / 'original-fixture-copy'
            target.write_bytes(raw)
            for fault in ('missing', 'empty', 'symlink'):
                with self.subTest(fixture=relative, fault=fault):
                    path.unlink()
                    try:
                        if fault == 'empty':
                            path.write_bytes(b'')
                        elif fault == 'symlink':
                            path.symlink_to(target)
                        self.gate(rejects=True)
                    finally:
                        if path.exists() or path.is_symlink():
                            path.unlink()
                        path.write_bytes(raw)
                    self.gate()

    def test_original_six_context_mixtures_still_reject_under_full_selector(self):
        rejected = 0
        for left, expected in self.old:
            self.assertEqual(CONTEXT.select_context(expected, self.contexts)[0], left)
            for right, other in self.old:
                if left == right:
                    continue
                for name, pin in expected.items():
                    if pin == other[name]:
                        continue
                    actual = dict(expected, **{name: other[name]})
                    matching = [context for context, files in self.old if actual == files]
                    if not matching:
                        with self.assertRaisesRegex(ValueError, 'source context'):
                            CONTEXT.select_context(actual, self.contexts)
                        rejected += 1
        self.assertGreater(rejected, 0)
        for name in self.original:
            actual = dict(self.maps[CHEEK])
            actual.pop(name)
            with self.assertRaisesRegex(ValueError, 'source context'):
                CONTEXT.select_context(actual, self.contexts)
        for actual in ({}, dict(self.maps[CHEEK], unreviewed={'bytes': 0, 'sha256': '0' * 64})):
            with self.assertRaisesRegex(ValueError, 'source context'):
                CONTEXT.select_context(actual, self.contexts)


if __name__ == '__main__':
    unittest.main()
