"""Exact running and motion-query unions at the actual formal gate."""
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
        global ROOT
        live = ROOT
        previous = tempfile.TemporaryDirectory(prefix='nvwa73-pre-cpu-')
        cls.addClassCleanup(previous.cleanup)
        ROOT = Path(previous.name)
        cls.addClassCleanup(lambda: globals().__setitem__('ROOT', live))
        source_raw = (HERE / 'FROZEN-INPUTS.json').read_bytes()
        original = json.loads(source_raw)
        retained_cpu = (CONTEXT.pre_waist_sources(HERE, source_raw, original) | CONTEXT.pre_reference_motion_sources(HERE, source_raw, original)
                        | CONTEXT.pre_cpu_sources(HERE, source_raw, original))
        # CPU-only leaves must not leak into a reconstructed motion-query tree.
        retained_cpu = {name: data for name, data in retained_cpu.items() if name not in CONTEXT.CPU_NEW_FILES}
        previous_files = json.loads((HERE / CONTEXT.MOTION_QUERY_CONTEXT_NAME).read_bytes())['files']
        for name in previous_files.keys() | retained_cpu.keys():
            path = ROOT / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(retained_cpu[name] if name in retained_cpu else (live / name).read_bytes())
        # Historical full-context controls also inspect the retained fixture pool.
        for folder in ('72-b1-admission-controls', '73-high-poly-eyes'):
            shutil.copytree(live / 'experiments' / folder / 'fixtures', ROOT / 'experiments' / folder / 'fixtures')
        cls.context_name = CONTEXT.RUNNING_CONTEXT_NAME
        cls.retention_name = CONTEXT.RUNNING_BASELINES_NAME
        cls.retention_prefix = 'fixtures/b1-running-predecessor-baselines'
        cls.product = PRODUCT
        cls.context_files = ('FROZEN-INPUTS.json', CONTEXT.CONTEXT_NAME, CONTEXT.SHORT01_CONTEXT_NAME,
                             CONTEXT.SELECTOR_CONTEXT_NAME, CONTEXT.AUTHORING_CONTEXT_NAME,
                             CONTEXT.MULTISEGMENT_CONTEXT_NAME, CONTEXT.CHEEK_CONTEXT_NAME,
                             CONTEXT.LOWER_CONTEXT_NAME, cls.context_name, CONTEXT.MOTION_QUERY_CONTEXT_NAME)
        cls.retention = json.loads((HERE / cls.retention_name).read_bytes())
        cls.files = json.loads((HERE / cls.context_name).read_bytes())['files']
        cls.raw = (HERE / 'FROZEN-INPUTS.json').read_bytes()
        cls.original = json.loads(cls.raw)
        temporary = tempfile.TemporaryDirectory(prefix='nvwa73-retained-running-')
        cls.addClassCleanup(temporary.cleanup)
        cls.running_root = Path(temporary.name)
        retained = CONTEXT.pre_motion_query_sources(HERE, cls.raw, cls.original)
        for name in cls.files.keys() | retained.keys():
            path = cls.running_root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(retained[name] if name in retained else (ROOT / name).read_bytes())

    def gate(self, root=None, exp=HERE):
        root = self.running_root if root is None else root
        with patch.object(ENTRY, 'ROOT', root), patch.object(ENTRY, 'EXP', exp):
            ENTRY.SourceContract('test_frozen_source_inputs').test_frozen_source_inputs()

    def test_each_running_gate_authenticates_the_context_chain_once(self):
        # Instrument both the entry alias and the public helper's module global.
        # Real reject/restore controls below remain independent of this count.
        module = sys.modules[ENTRY.source_contexts.__module__]
        authenticate = module.current_source_contexts
        with patch.object(module, 'current_source_contexts', wraps=authenticate) as calls:
            with patch.object(ENTRY, 'source_contexts', calls):
                for invocation in (1, 2):
                    self.gate()
                    self.assertEqual(calls.call_count, invocation)

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
        actual = {n: {'bytes': (self.running_root / n).stat().st_size,
                      'sha256': hashlib.sha256((self.running_root / n).read_bytes()).hexdigest()} for n in files}
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
                shutil.copyfile(self.running_root / name, path)
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

    def test_motion_query_gate_authenticates_once_and_double_hashes_all_318_inputs(self):
        files = json.loads((HERE / CONTEXT.MOTION_QUERY_CONTEXT_NAME).read_bytes())['files']
        self.assertEqual(len(files), 318)
        self.assertEqual(set(files), self.files.keys() | set(CONTEXT.MOTION_QUERY_ADDITIONS))
        module = sys.modules[ENTRY.source_contexts.__module__]
        authenticate = module.current_source_contexts
        with patch.object(module, 'current_source_contexts', wraps=authenticate) as chain, \
                patch.object(module, 'pre_running_sources', wraps=module.pre_running_sources) as historical, \
                patch.object(ENTRY, 'source_contexts', chain), \
                patch.object(ENTRY, 'digest', wraps=ENTRY.digest) as digest:
            for invocation in (1, 2):
                self.gate(ROOT)
                self.assertEqual(chain.call_count, invocation)
                self.assertEqual(historical.call_count, invocation)
                hashed = [call.args[0].relative_to(ROOT).as_posix() for call in digest.call_args_list]
                self.assertCountEqual(hashed, list(files) * 2)
                digest.reset_mock()

    def test_motion_query_inputs_and_predecessor_mix_reject_and_restore(self):
        with tempfile.TemporaryDirectory(prefix='nvwa73-motion-query-') as directory:
            root = Path(directory) / 'source'
            exp = root / 'experiments' / HERE.name
            exp.mkdir(parents=True)
            for name in self.context_files:
                shutil.copyfile(HERE / name, exp / name)
            shutil.copytree(HERE / 'fixtures', exp / 'fixtures')
            files = json.loads((HERE / CONTEXT.MOTION_QUERY_CONTEXT_NAME).read_bytes())['files']
            for name in files:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, path)

            self.gate(root, exp)
            sources = (*CONTEXT.MOTION_QUERY_CHANGED, *CONTEXT.MOTION_QUERY_ADDITIONS)
            paths = [root / name for name in sources]
            paths.append(exp / CONTEXT.MOTION_QUERY_CONTEXT_NAME)
            paths.extend(path for path in (exp / CONTEXT.MOTION_QUERY_FIXTURES).rglob('*') if path.is_file())
            for path in paths:
                raw = path.read_bytes()
                target = Path(directory) / 'preserved-input'
                target.write_bytes(raw)
                for fault in ('missing', 'same-size', 'symlink'):
                    with self.subTest(path=path.relative_to(root), fault=fault):
                        path.unlink()
                        try:
                            if fault == 'same-size':
                                path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
                            elif fault == 'symlink':
                                path.symlink_to(target)
                            with self.assertRaisesRegex(AssertionError, 'FROZEN-INPUTS.json'):
                                self.gate(root, exp)
                        finally:
                            path.unlink(missing_ok=True)
                            path.write_bytes(raw)
                        self.assertEqual(path.read_bytes(), raw)
                        self.gate(root, exp)

            for name in (*CONTEXT.MOTION_QUERY_CHANGED, *CONTEXT.MOTION_QUERY_OUTSIDE):
                path = root / name
                raw = path.read_bytes()
                with self.subTest(stale=name):
                    try:
                        shutil.copyfile(self.running_root / name, path)
                        with self.assertRaisesRegex(AssertionError, 'FROZEN-INPUTS.json'):
                            self.gate(root, exp)
                    finally:
                        path.write_bytes(raw)
                    self.assertEqual(path.read_bytes(), raw)
                    self.gate(root, exp)

            for name in sources:
                path = self.running_root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                previous = path.read_bytes() if path.exists() else None
                with self.subTest(new=name):
                    try:
                        shutil.copyfile(ROOT / name, path)
                        with self.assertRaisesRegex(AssertionError, 'FROZEN-INPUTS.json'):
                            self.gate(self.running_root, exp)
                    finally:
                        if previous is None:
                            path.unlink()
                        else:
                            path.write_bytes(previous)
                            self.assertEqual(path.read_bytes(), previous)
                    self.gate(self.running_root, exp)

if __name__ == '__main__':
    unittest.main()
