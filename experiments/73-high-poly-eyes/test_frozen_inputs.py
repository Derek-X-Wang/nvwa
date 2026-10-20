"""Exercise the CI-called source gate in disposable repository copies."""
import hashlib
import itertools
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

EXP = Path(__file__).resolve().parent
ROOT = EXP.parents[1]


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
        for name in ['test_prepare.py', 'cpu_probe.py', 'frozen_context.py', 'source-context-closeout-v1.json']:
            shutil.copyfile(EXP / name, cls.exp / name)
        context = json.loads((EXP / 'source-context-closeout-v1.json').read_text())
        cls.current = {name: (cls.root / name).read_bytes() for name in context['overrides']}
        cls.original = {}
        for name, raw in cls.current.items():
            text = raw.decode()
            if name == 'crates/nvwa-core/src/b1.rs':
                before = 'character backend version {version} is unsupported"'
                if text.count(before) != 1:
                    raise ValueError('historical diagnostic fixture seam must occur once')
                text = text.replace(before, 'character backend version {version} is unsupported; expected 1"')
            else:
                if name == 'crates/nvwa-cli/tests/b1.rs':
                    start = '#[test]\nfn unsupported_backend_version_reports_accurate_error_and_preserves_files()'
                    end = '#[test]\nfn no_window_new_discover_apply_validate_save_and_inspect_share_full_work()'
                elif name == 'crates/nvwa-core/tests/b1.rs':
                    start = '#[test]\nfn unsupported_backend_versions_report_rejection_without_claiming_expected_version_one()'
                    end = '#[test]\nfn canonical_b1_defaults_roundtrip_and_reject_modified_profile_identity_or_bindings()'
                else:
                    start = '        // Check scheduled feedback before explicit readback can repair it.'
                    end = '        let snapshot = crate::appearance_snapshot(app.world_mut()).unwrap();'
                if text.count(start) != 1 or end not in text[text.index(start):]:
                    raise ValueError('historical source fixture seams missing/duplicated: ' + name)
                text = text[:text.index(start)] + text[text.index(end, text.index(start)):]
            old = text.encode()
            if hashlib.sha256(old).hexdigest() != cls.inputs[name]['sha256'] or len(old) != cls.inputs[name]['bytes']:
                raise ValueError('historical fixture must reconstruct exact original bytes: ' + name)
            cls.original[name] = old

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
            for name, raw in self.original.items():
                (self.root / name).write_bytes(raw)
            self.gate(self.raw, rejects=False)
        finally:
            for name, raw in self.current.items():
                (self.root / name).write_bytes(raw)

    def test_all_fourteen_mixed_contexts_reject_at_actual_called_gate(self):
        names = list(self.current)
        try:
            for choices in itertools.product((False, True), repeat=4):
                if all(choices) or not any(choices):
                    continue
                with self.subTest(current_files=choices):
                    for name, current in zip(names, choices):
                        (self.root / name).write_bytes((self.current if current else self.original)[name])
                    self.gate(self.raw, rejects=True)
        finally:
            for name, raw in self.current.items():
                (self.root / name).write_bytes(raw)

    def test_context_manifest_missing_empty_corrupt_tampered_and_symlink_reject(self):
        path = self.exp / 'source-context-closeout-v1.json'
        original = path.read_bytes()
        target = self.root / 'original-context.json'
        target.write_bytes(original)
        for fault in ('missing', 'empty', 'corrupt', 'tampered', 'symlink'):
            with self.subTest(fault=fault):
                path.unlink()
                try:
                    if fault == 'symlink':
                        path.symlink_to(target)
                    elif fault != 'missing':
                        path.write_bytes({'empty': b'{}', 'corrupt': b'{', 'tampered': original + b' '}[fault])
                    self.gate(self.raw, rejects=True)
                finally:
                    if path.exists() or path.is_symlink():
                        path.unlink()
                    path.write_bytes(original)
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
