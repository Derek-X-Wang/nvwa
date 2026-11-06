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
SPEC = importlib.util.spec_from_file_location('running72_actual', HERE / 'run.py')
ENTRY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ENTRY)


class RunningContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context_name = 'input-context-v6.json'
        cls.retention_name = 'fixtures/pre-running/manifest.json'
        cls.retention_prefix = 'fixtures/pre-running'
        cls.product = PRODUCT
        cls.context_files = ENTRY.PACKAGE + (cls.context_name,)
        cls.retention = json.loads((HERE / cls.retention_name).read_bytes())
        cls.files = json.loads((HERE / cls.context_name).read_bytes())['files']
        cls.pins = json.loads((HERE / 'pins.json').read_bytes())

    def gate(self, root=ROOT, exp=HERE):
        with patch.object(ENTRY, 'HERE', exp):
            result = ENTRY.check_inputs(root)['checked_input_context']
        self.assertEqual(result['id'], CURRENT)
        self.assertEqual(len(result['files']), 26)
        self.assertEqual(result['files'], {n: p['sha256'] for n, p in self.files.items()})

    def test_current_union_and_preserved_historical_cohorts(self):
        self.gate()
        self.assertEqual(len(self.pins['files']), 17)
        self.assertEqual(len(ENTRY.source_contexts(self.pins)), 4)
        self.assertEqual(len(ENTRY.admitted_source_contexts(self.pins)), 5)
        self.assertEqual(len(ENTRY.current_source_contexts(self.pins)), 6)
        for _, files in ENTRY.current_source_contexts(self.pins):
            self.assertEqual(set(files), set(self.pins['files']))
        name, union = ENTRY.running_source_context(self.pins)
        for _, old in ENTRY.current_source_contexts(self.pins):
            with self.assertRaisesRegex(ValueError, 'source input context mismatch'):
                ENTRY.select_source_context(old, [(name, {n: i['sha256'] for n, i in union.items()})])
        with self.assertRaisesRegex(ValueError, 'source input context mismatch'):
            ENTRY.select_source_context(dict({n: i['sha256'] for n, i in union.items()}, unreviewed='0' * 64), [(name, {n: i['sha256'] for n, i in union.items()})])
        raw = (ROOT / ENTRY.RUNTIME).read_text()
        ENTRY.check_unchanged_sections(raw, json.loads((HERE / 'input-context-v1.json').read_bytes()))

    def test_all_historical_cohorts_with_their_preexisting_outside_sources(self):
        pool = {}
        # Existing retained source is authenticated again against each immutable
        # old17 pin below; no runtime Git or current-byte reversal is used.
        for exp in (HERE, ROOT / 'experiments/73-high-poly-eyes'):
            for path in (exp / 'fixtures').rglob('*'):
                if path.is_file() and not path.is_symlink():
                    raw = path.read_bytes()
                    pool[hashlib.sha256(raw).hexdigest()] = raw
        for name in self.pins['files']:
            raw = (ROOT / name).read_bytes()
            pool[hashlib.sha256(raw).hexdigest()] = raw
        with tempfile.TemporaryDirectory(prefix='nvwa72-historical-complete-') as directory:
            root = Path(directory)
            for context, files in ENTRY.current_source_contexts(self.pins):
                for name, digest in files.items():
                    raw = pool[digest]
                    self.assertEqual(hashlib.sha256(raw).hexdigest(), digest)
                    path = root / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(raw)
                for variant in self.retention['historical_outside'][context]:
                    with self.subTest(context=context, outside=variant['source_context']):
                        for name, item in variant['files'].items():
                            raw = (HERE / item['fixture']).read_bytes()
                            self.assertEqual({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()},
                                             {k: item[k] for k in ('bytes', 'sha256')})
                            path = root / name
                            path.parent.mkdir(parents=True, exist_ok=True)
                            path.write_bytes(raw)
                        self.assertEqual(ENTRY.check_inputs(root)['checked_input_context']['id'], context)
                        if context == 'baseline581':
                            self.assertEqual(ENTRY.check_source_context(root, self.pins, historical_only=True)['id'], context)

    def test_lower_complete_root_with_preexisting_paths_and_strict_mixtures(self):
        with tempfile.TemporaryDirectory(prefix='nvwa72-r2-01-') as directory:
            root = Path(directory)
            retained = ENTRY.pre_running_sources(self.pins)
            for name in self.pins['files']:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(retained[name] if name in retained else (ROOT / name).read_bytes())
            for name in ('crates/nvwa-cli/src/main.rs', 'crates/nvwa-runtime/src/lib.rs',
                         'crates/nvwa-studio/src/appearance_ui_tests.rs', 'crates/nvwa-studio/src/lib.rs'):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                item = self.retention['historical_outside']['b1-lower-face-squareness-product-v1'][0]['files'][name]
                path.write_bytes((HERE / item['fixture']).read_bytes())
            self.assertEqual(ENTRY.check_inputs(root)['checked_input_context']['id'], 'b1-lower-face-squareness-product-v1')
            for name in ENTRY.RUNNING_PREEXISTING:
                path = root / name
                raw = path.read_bytes()
                target = root / 'preserved-outside'
                target.write_bytes(raw)
                for fault in ('current', 'corrupt', 'symlink'):
                    with self.subTest(historical_path=name, fault=fault):
                        path.unlink()
                        try:
                            if fault == 'current': path.write_bytes((ROOT / name).read_bytes())
                            elif fault == 'corrupt': path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
                            else: path.symlink_to(target)
                            with self.assertRaisesRegex(ValueError, 'source input context mismatch'):
                                ENTRY.check_inputs(root)
                        finally:
                            if path.exists() or path.is_symlink(): path.unlink()
                            path.write_bytes(raw)
                        self.assertEqual(path.read_bytes(), raw)
                        self.assertEqual(ENTRY.check_inputs(root)['checked_input_context']['id'], 'b1-lower-face-squareness-product-v1')

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
            retained_items = list(self.retention['files'].values()) + list(self.retention['historical_original'].values())
            retained_items += [item for variants in self.retention['historical_outside'].values()
                               for variant in variants for item in variant['files'].values()]
            paths += [exp / name for name in sorted({i['fixture'] for i in retained_items})]
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
