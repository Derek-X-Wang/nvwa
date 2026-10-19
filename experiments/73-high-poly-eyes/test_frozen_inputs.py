"""Exercise the CI-called source gate in disposable repository copies."""
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
        for name in ['test_prepare.py', 'cpu_probe.py']:
            shutil.copyfile(EXP / name, cls.exp / name)

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
