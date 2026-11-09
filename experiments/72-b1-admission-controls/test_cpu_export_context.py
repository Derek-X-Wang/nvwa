"""Actual CPU source admission, historical crossovers and strict refusal/recovery."""
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
SPEC = importlib.util.spec_from_file_location('cpu_72_context', HERE / 'run.py')
CONTEXT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTEXT)

PRODUCT = ('Cargo.lock', 'crates/nvwa-cli/Cargo.toml', 'crates/nvwa-cli/src/cpu_render.rs',
           'crates/nvwa-cli/src/main.rs', 'crates/nvwa-cli/tests/cpu_render.rs',
           'crates/nvwa-runtime/Cargo.toml', 'crates/nvwa-runtime/src/b1.rs',
           'crates/nvwa-runtime/src/b1/cpu_render.rs', 'crates/nvwa-runtime/src/lib.rs',
           'crates/nvwa-runtime/src/stage.rs', 'docs/agents/cli-authoring.md',
           'docs/agents/cpu-render.md', 'experiments/27-ci-baseline/check.sh')


class CpuSourceContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global ROOT
        live = ROOT
        temporary = tempfile.TemporaryDirectory(prefix='nvwa72-pre-waist-')
        cls.addClassCleanup(temporary.cleanup)
        ROOT = Path(temporary.name)
        cls.addClassCleanup(lambda: globals().__setitem__('ROOT', live))
        retained_waist = CONTEXT.pre_waist_sources(json.loads((HERE / 'pins.json').read_bytes()))
        previous_files = json.loads((HERE / CONTEXT.CPU_CONTEXT_NAME).read_bytes())['files']
        for name in previous_files.keys() | retained_waist.keys():
            path = ROOT / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(retained_waist[name] if name in retained_waist else (live / name).read_bytes())
        cls.files = json.loads((HERE / CONTEXT.CPU_CONTEXT_NAME).read_bytes())['files']
        cls.retained = json.loads((HERE / 'fixtures/pre-cpu-export/manifest.json').read_bytes())['files']

    def invoke_gate(self, root=None, exp=HERE):
        root = ROOT if root is None else root
        with patch.object(CONTEXT, 'HERE', exp):
            result = CONTEXT.check_inputs(root)['checked_input_context']
        return result

    def gate(self, root=None, exp=HERE, cpu=True):
        root = ROOT if root is None else root
        result = self.invoke_gate(root, exp)
        self.assertEqual(result['id'], CONTEXT.CPU_CONTEXT_ID if cpu else 'b1-motion-query-product-v1')
        self.assertEqual(len(result['files']), 39 if cpu else 31)

    def copied(self, root):
        for name in self.files:
            dest = root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dest)
        exp = root / 'experiments' / HERE.name
        exp.mkdir(parents=True, exist_ok=True)
        for path in HERE.iterdir():
            if path.is_file():
                shutil.copyfile(path, exp / path.name)
        shutil.copytree(HERE / 'fixtures', exp / 'fixtures')
        return exp

    def test_actual_current_union_and_unchanged_historical_cohorts(self):
        self.gate()
        self.assertEqual(len(self.files), 39)
        pins = json.loads((HERE / 'pins.json').read_bytes())
        self.assertEqual(len(pins['files']), 17)
        self.assertEqual(len(CONTEXT.source_contexts(pins)), 4)
        self.assertEqual(len(CONTEXT.admitted_source_contexts(pins)), 5)
        self.assertEqual(len(CONTEXT.current_source_contexts(pins)), 6)
        _, previous = CONTEXT._motion_query_source_context(CONTEXT.running_source_context(pins))
        self.assertEqual(len(previous), 31)
        with self.assertRaises(ValueError):
            CONTEXT.check_source_context(ROOT, pins, historical_only=True)
        self.assertEqual(set(CONTEXT.CPU_NEW_FILES), set(PRODUCT) - set(self.retained))
        self.assertEqual(set(self.files), set(previous) | set(CONTEXT.CPU_ADDITIONS))
        for name in set(previous) - set(PRODUCT):
            self.assertEqual(self.files[name], previous[name], name)
        # Real CI wiring: the opt-in integration target must run on the native path.
        script = (ROOT / 'experiments/27-ci-baseline/check.sh').read_text()
        command = 'cargo test -p nvwa-cli --features cpu-render,motion-query --test cpu_render --locked --offline -- --test-threads=1'
        self.assertEqual(script.count(command), 1)
        self.assertIn(command, script.split('  native)\n', 1)[1].split('    ;;', 1)[0])
        self.assertNotIn(command, script.split('  portable)\n', 1)[1].split('    ;;', 1)[0])

    def test_every_product_manifest_and_retained_file_rejects_and_recovers(self):
        with tempfile.TemporaryDirectory(prefix='nvwa-cpu-context-') as directory:
            root = Path(directory) / 'source'
            exp = self.copied(root)
            self.gate(root, exp)
            paths = [root / n for n in PRODUCT]
            paths += [exp / CONTEXT.CPU_CONTEXT_NAME, exp / 'fixtures/pre-cpu-export/manifest.json']
            paths += [exp / item['fixture'] for item in self.retained.values()]
            target = Path(directory) / 'original'
            for path in paths:
                raw = path.read_bytes()
                target.write_bytes(raw)
                for fault in ('missing', 'hash', 'size', 'symlink'):
                    with self.subTest(path=path.relative_to(root), fault=fault):
                        path.unlink()
                        try:
                            if fault == 'hash': path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
                            elif fault == 'size': path.write_bytes(raw + b'\n')
                            elif fault == 'symlink': path.symlink_to(target)
                            with self.assertRaises((ValueError, AssertionError)):
                                self.invoke_gate(root, exp)
                        finally:
                            if path.exists() or path.is_symlink(): path.unlink()
                            path.write_bytes(raw)
                        self.assertEqual(path.read_bytes(), raw)
                        self.gate(root, exp)
            extra = exp / 'fixtures/pre-cpu-export/unreviewed'
            try:
                extra.write_bytes(b'unreviewed')
                with self.assertRaises((ValueError, AssertionError)):
                    self.invoke_gate(root, exp)
            finally:
                extra.unlink()
            self.gate(root, exp)

    def test_bidirectional_actual_gate_crossovers_and_missing_whole_extension(self):
        with tempfile.TemporaryDirectory(prefix='nvwa-cpu-crossover-') as directory:
            root = Path(directory)
            exp = self.copied(root)
            current = {n: (root / n).read_bytes() for n in PRODUCT}
            retained = {n: (exp / item['fixture']).read_bytes() for n, item in self.retained.items()}
            for name in PRODUCT:
                path = root / name
                try:
                    if name in retained: path.write_bytes(retained[name])
                    else: path.unlink()
                    with self.assertRaises((ValueError, AssertionError)):
                        self.invoke_gate(root, exp)
                finally:
                    path.write_bytes(current[name])
                self.gate(root, exp)
            for name in CONTEXT.CPU_NEW_FILES:
                (root / name).unlink()
            with self.assertRaises((ValueError, AssertionError)):
                self.invoke_gate(root, exp)
            for name, data in retained.items():
                (root / name).write_bytes(data)
            self.gate(root, exp, cpu=False)
            for name in PRODUCT:
                path = root / name
                try:
                    path.write_bytes(current[name])
                    with self.assertRaises((ValueError, AssertionError)):
                        self.invoke_gate(root, exp)
                finally:
                    if name in retained: path.write_bytes(retained[name])
                    else: path.unlink()
                self.gate(root, exp, cpu=False)


if __name__ == '__main__':
    unittest.main()
