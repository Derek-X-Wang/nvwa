"""Exact running union at the actual formal gate; no motion-quality claim."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CURRENT = 'b1-running-product-v1'
PRODUCT = ('crates/nvwa-cli/src/main.rs', 'crates/nvwa-cli/tests/running.rs',
           'crates/nvwa-core/src/b1.rs', 'crates/nvwa-core/src/lib.rs', 'crates/nvwa-core/src/running.rs',
           'crates/nvwa-runtime/src/appearance/mod.rs', 'crates/nvwa-runtime/src/b1.rs',
           'crates/nvwa-runtime/src/b1_running.rs', 'crates/nvwa-runtime/src/b1_running_controls.json',
           'crates/nvwa-runtime/src/lib.rs', 'crates/nvwa-studio/src/appearance_ui_tests.rs',
           'crates/nvwa-studio/src/lib.rs', 'docs/b1-running-contract.md')
SPEC = importlib.util.spec_from_file_location('running73_context', HERE / 'frozen_context.py')
CONTEXT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTEXT)
sys.path.insert(0, str(HERE))
try:
    SPEC = importlib.util.spec_from_file_location('running73_actual', HERE / 'test_prepare.py')
    ENTRY = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(ENTRY)
finally:
    sys.path.pop(0)


class RunningContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context_name = CONTEXT.RUNNING_CONTEXT_NAME
        cls.retention_name = CONTEXT.RUNNING_BASELINES_NAME
        cls.retention_prefix = 'fixtures/b1-running-predecessor-baselines'
        cls.product = PRODUCT
        cls.context_files = ('FROZEN-INPUTS.json', CONTEXT.CONTEXT_NAME, CONTEXT.SHORT01_CONTEXT_NAME,
                             CONTEXT.SELECTOR_CONTEXT_NAME, CONTEXT.AUTHORING_CONTEXT_NAME,
                             CONTEXT.MULTISEGMENT_CONTEXT_NAME, CONTEXT.CHEEK_CONTEXT_NAME,
                             CONTEXT.LOWER_CONTEXT_NAME, cls.context_name)
        cls.retention = json.loads((HERE / cls.retention_name).read_bytes())
        cls.files = json.loads((HERE / cls.context_name).read_bytes())['files']
        cls.raw = (HERE / 'FROZEN-INPUTS.json').read_bytes()
        cls.original = json.loads(cls.raw)

    def gate(self, root=ROOT, exp=HERE):
        with patch.object(ENTRY, 'ROOT', root), patch.object(ENTRY, 'EXP', exp):
            ENTRY.SourceContract('test_frozen_source_inputs').test_frozen_source_inputs()

    def test_current_union_and_preserved_historical_cohorts(self):
        self.gate()
        self.assertEqual(len(self.original), 309)
        old = CONTEXT.current_source_contexts(HERE, self.raw, self.original)
        self.assertEqual(len(old), 8)
        for _, files in old:
            self.assertEqual(set(files), set(self.original))
        name, files = CONTEXT.running_source_context(HERE, self.raw, self.original)
        self.assertEqual(name, CURRENT)
        self.assertEqual(len(files), 314)
        self.assertEqual(set(files), set(self.original) | set(CONTEXT.RUNNING_ADDITIONS))
        actual = {n: {'bytes': (ROOT / n).stat().st_size,
                      'sha256': hashlib.sha256((ROOT / n).read_bytes()).hexdigest()} for n in files}
        self.assertEqual(CONTEXT.select_context(actual, [(name, files)])[0], CURRENT)
        for historical, expected in old:
            with self.assertRaisesRegex(ValueError, 'source context'):
                CONTEXT.select_context(expected, [(name, files)])
        for historical, expected in old:
            for n in set(files) & set(expected):
                if files[n] == expected[n]: continue
                mixed = dict(files, **{n: expected[n]})
                with self.assertRaisesRegex(ValueError, 'source context'):
                    CONTEXT.select_context(mixed, old + [(name, files)])
        with self.assertRaisesRegex(ValueError, 'source context'):
            CONTEXT.select_context(dict(files, unreviewed={'bytes': 0, 'sha256': '0' * 64}), old + [(name, files)])

    def test_every_new_input_and_manifest_rejects_and_restores_at_formal_gate(self):
        with tempfile.TemporaryDirectory(prefix='nvwa-running-control-') as directory:
            root = Path(directory) / 'source'
            for name in self.files:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, path)
            exp = root / 'experiments' / HERE.name
            exp.mkdir(parents=True, exist_ok=True)
            for name in self.context_files:
                shutil.copyfile(HERE / name, exp / name)
            shutil.copytree(HERE / 'fixtures', exp / 'fixtures')
            self.gate(root, exp)
            # All13 product paths, not only original-set overrides.
            paths = [root / n for n in self.product]
            paths += [exp / self.context_name, exp / self.retention_name]
            paths += [exp / i['fixture'] for i in self.retention['files'].values()]
            for path in paths:
                raw = path.read_bytes()
                target = Path(directory) / 'preserved-source'
                target.write_bytes(raw)
                for fault in ('missing', 'hash', 'size', 'symlink'):
                    with self.subTest(path=str(path.relative_to(root)), fault=fault):
                        path.unlink()
                        try:
                            if fault == 'hash': path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
                            elif fault == 'size': path.write_bytes(raw[:-1])
                            elif fault == 'symlink': path.symlink_to(target)
                            with self.assertRaises((ValueError, AssertionError)):
                                self.gate(root, exp)
                        finally:
                            if path.exists() or path.is_symlink(): path.unlink()
                            path.write_bytes(raw)
                        self.assertEqual(path.read_bytes(), raw)
                        self.gate(root, exp)
            # Dropping every added path cannot downgrade source07 to old17/309.
            additions = set(self.files) - set(self.pins['files'] if hasattr(self, 'pins') else self.original)
            saved = {name: (root / name).read_bytes() for name in additions}
            try:
                for name in saved: (root / name).unlink()
                with self.assertRaises((ValueError, AssertionError)):
                    self.gate(root, exp)
            finally:
                for name, raw in saved.items(): (root / name).write_bytes(raw)
            self.gate(root, exp)
            # A complete old original-set map plus running additions is a mix.
            saved = {name: (root / name).read_bytes() for name in self.retention['files']}
            try:
                for name, item in self.retention['files'].items():
                    (root / name).write_bytes((exp / item['fixture']).read_bytes())
                with self.assertRaises((ValueError, AssertionError)):
                    self.gate(root, exp)
            finally:
                for name, raw in saved.items(): (root / name).write_bytes(raw)
            self.gate(root, exp)
            context = exp / self.context_name
            raw = context.read_bytes()
            value = json.loads(raw)
            value['files']['unreviewed-added-path'] = {'bytes': 0, 'sha256': '0' * 64}
            try:
                context.write_text(json.dumps(value))
                with self.assertRaises((ValueError, AssertionError)):
                    self.gate(root, exp)
            finally:
                context.write_bytes(raw)
            self.gate(root, exp)
            # Replacing each displaced member with the exact predecessor must
            # fail at the updated formal entry, then recover byte-for-byte.
            for name, item in self.retention['files'].items():
                path = root / name
                raw = path.read_bytes()
                try:
                    path.write_bytes((exp / item['fixture']).read_bytes())
                    with self.assertRaises((ValueError, AssertionError)):
                        self.gate(root, exp)
                finally:
                    path.write_bytes(raw)
                self.gate(root, exp)
            extra = exp / self.retention_prefix / 'unreviewed-source'
            try:
                extra.write_bytes(b'unreviewed')
                with self.assertRaises((ValueError, AssertionError)):
                    self.gate(root, exp)
            finally:
                extra.unlink()
            self.gate(root, exp)

if __name__ == '__main__':
    unittest.main()
