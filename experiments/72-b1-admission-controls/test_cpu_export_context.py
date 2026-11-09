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
        cls.files = json.loads((HERE / CONTEXT.CPU_CONTEXT_NAME).read_bytes())['files']
        cls.retained = json.loads((HERE / 'fixtures/pre-cpu-export/manifest.json').read_bytes())['files']
        cls.reference_files = json.loads((HERE / CONTEXT.REFERENCE_MOTION_CONTEXT_NAME).read_bytes())['files']
        pins = json.loads((HERE / 'pins.json').read_bytes())
        retained = CONTEXT.pre_reference_motion_sources(pins)
        # Replay every original CPU control against its exact predecessor.
        temporary = tempfile.TemporaryDirectory(prefix='nvwa-pre-reference-motion-')
        cls.addClassCleanup(temporary.cleanup)
        cls.cpu_root = Path(temporary.name)
        for name in cls.files:
            dest = cls.cpu_root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if name in retained:
                dest.write_bytes(retained[name])
            else:
                shutil.copyfile(ROOT / name, dest)

    def invoke_gate(self, root=ROOT, exp=HERE):
        with patch.object(CONTEXT, 'HERE', exp):
            result = CONTEXT.check_inputs(root)['checked_input_context']
        return result

    def gate(self, root=None, exp=HERE, cpu=True):
        root = self.cpu_root if root is None else root
        result = self.invoke_gate(root, exp)
        self.assertEqual(result['id'], CONTEXT.CPU_CONTEXT_ID if cpu else 'b1-motion-query-product-v1')
        self.assertEqual(len(result['files']), 39 if cpu else 31)

    def copied(self, root, reference_motion=False):
        files = self.reference_files if reference_motion else self.files
        source = ROOT if reference_motion else self.cpu_root
        for name in files:
            dest = root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / name, dest)
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
            CONTEXT.check_source_context(self.cpu_root, pins, historical_only=True)
        self.assertEqual(set(CONTEXT.CPU_NEW_FILES), set(PRODUCT) - set(self.retained))
        self.assertEqual(set(self.files), set(previous) | set(CONTEXT.CPU_ADDITIONS))
        for name in set(previous) - set(PRODUCT):
            self.assertEqual(self.files[name], previous[name], name)
        # Real CI wiring: the opt-in integration target must run on the native path.
        script = (self.cpu_root / 'experiments/27-ci-baseline/check.sh').read_text()
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


    def reference_gate(self, root=ROOT, exp=HERE):
        result = self.invoke_gate(root, exp)
        self.assertEqual(result['id'], CONTEXT.REFERENCE_MOTION_CONTEXT_ID)
        self.assertEqual(result['files'], {n: p['sha256'] for n, p in self.reference_files.items()})
        self.assertEqual(result['current_rust_execution'], 'NOT-RUN')
        self.assertEqual(result['execution_source'], 'immutable baseline581 archive only')

    def test_reference_motion_exact_current_union_and_cpu_predecessor(self):
        self.reference_gate()
        self.gate()
        self.assertEqual(len(self.reference_files), 42)
        self.assertEqual(set(self.reference_files), set(self.files) | set(CONTEXT.REFERENCE_MOTION_ADDITIONS))
        self.assertEqual({name for name in self.files if self.reference_files[name] != self.files[name]},
                         set(CONTEXT.REFERENCE_MOTION_CHANGED))
        pins = json.loads((HERE / 'pins.json').read_bytes())
        with self.assertRaisesRegex(ValueError, 'source input context mismatch'):
            CONTEXT.check_source_context(ROOT, pins, historical_only=True)

    def test_reference_motion_bidirectional_mixtures_and_whole_extension_removal_reject(self):
        with tempfile.TemporaryDirectory(prefix='nvwa-reference-motion-mix-') as directory:
            current = Path(directory) / 'current'
            previous = Path(directory) / 'previous'
            exp = self.copied(current, reference_motion=True)
            cpu_exp = self.copied(previous)
            self.reference_gate(current, exp)
            self.gate(previous, cpu_exp)
            for root, source, material, green in ((current, previous, exp, self.reference_gate),
                                                  (previous, current, cpu_exp, self.gate)):
                for name in CONTEXT.REFERENCE_MOTION_CHANGED:
                    path = root / name
                    original = path.read_bytes()
                    with self.subTest(root=root.name, crossover=name):
                        try:
                            shutil.copyfile(source / name, path)
                            with self.assertRaises((ValueError, AssertionError)):
                                self.invoke_gate(root, material)
                        finally:
                            path.write_bytes(original)
                        self.assertEqual(path.read_bytes(), original)
                        green(root, material)
            additions = {n: (current / n).read_bytes() for n in CONTEXT.REFERENCE_MOTION_ADDITIONS}
            for name, raw in additions.items():
                path = previous / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
                try:
                    with self.assertRaises((ValueError, AssertionError)):
                        self.invoke_gate(previous, cpu_exp)
                finally:
                    path.unlink()
                self.gate(previous, cpu_exp)
            try:
                for name in additions:
                    (current / name).unlink()
                with self.assertRaises((ValueError, AssertionError)):
                    self.invoke_gate(current, exp)
            finally:
                for name, raw in additions.items():
                    (current / name).write_bytes(raw)
            self.reference_gate(current, exp)

    def test_reference_motion_file_and_inventory_faults_reject_and_restore(self):
        with tempfile.TemporaryDirectory(prefix='nvwa-reference-motion-files-') as directory:
            root = Path(directory) / 'source'
            exp = self.copied(root, reference_motion=True)
            manifest = exp / CONTEXT.REFERENCE_MOTION_CONTEXT_NAME
            fixtures = exp / CONTEXT.REFERENCE_MOTION_FIXTURES
            paths = [root / n for n in (*CONTEXT.REFERENCE_MOTION_CHANGED, *CONTEXT.REFERENCE_MOTION_ADDITIONS)]
            paths += [manifest, *(fixtures / n for n in CONTEXT.REFERENCE_MOTION_CHANGED)]
            target = Path(directory) / 'original'
            for path in paths:
                original = path.read_bytes()
                target.write_bytes(original)
                for fault in ('missing', 'same-size', 'symlink'):
                    with self.subTest(path=path.relative_to(root), fault=fault):
                        path.unlink()
                        try:
                            if fault == 'same-size':
                                path.write_bytes(bytes([original[0] ^ 1]) + original[1:])
                            elif fault == 'symlink':
                                path.symlink_to(target)
                            with self.assertRaises((ValueError, AssertionError)):
                                self.invoke_gate(root, exp)
                        finally:
                            path.unlink(missing_ok=True)
                            path.write_bytes(original)
                        self.assertEqual(path.read_bytes(), original)
                        self.reference_gate(root, exp)
            extra = fixtures / 'unreviewed'
            original = manifest.read_bytes()
            value = json.loads(original)
            value['files']['unreviewed'] = {'bytes': 0, 'sha256': '0' * 64}
            for path, raw in ((extra, b'unreviewed'), (manifest, json.dumps(value).encode())):
                with self.subTest(extra=path.name):
                    try:
                        path.write_bytes(raw)
                        with self.assertRaises((ValueError, AssertionError)):
                            self.invoke_gate(root, exp)
                    finally:
                        if path == manifest:
                            path.write_bytes(original)
                        else:
                            path.unlink()
                    self.reference_gate(root, exp)


if __name__ == '__main__':
    unittest.main()
