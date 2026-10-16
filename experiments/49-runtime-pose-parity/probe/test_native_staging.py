"""Fresh staging control only; the fake executable is never runtime evidence."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile
import unittest

PREPARE = Path(__file__).with_name('prepare_native.py')

class FreshNativeStaging(unittest.TestCase):
    def test_fresh_checkout_creates_log_directory_and_preserves_inputs(self):
        self.exercise_fresh_staging(PREPARE)

    def exercise_fresh_staging(self, prepare):
        with tempfile.TemporaryDirectory(prefix='nvwa-packaging-test-') as temporary:
            root = Path(temporary)
            probe = root / 'experiments/49-runtime-pose-parity/probe'
            probe.mkdir(parents=True)
            shutil.copy2(prepare, probe / PREPARE.name)
            binary = root / '.work/runtime-pose-build/debug/nvwa-runtime-pose-probe'
            binary.parent.mkdir(parents=True)
            binary.write_text('#!/bin/sh\nprintf "fake-packaging-only\\nwork=%s\\nassets=%s\\noutput=%s\\n" "$2" "$NVWA_ASSET_ROOT" "$NVWA_POSE_OUTPUT"\n')
            binary.chmod(0o755)
            artifact = root / 'experiments/48-genuine-fixture-work/artifacts'
            (artifact / 'assets/generated').mkdir(parents=True)
            (artifact / 'genuine44-calibrated47.nvwa.json').write_bytes(b'{"fake_packaging_only":true}\n')
            (artifact / 'assets/generated/genuine44-calibrated47.glb').write_bytes(b'fake packaging bytes')
            self.assertFalse((root / '.work/runtime-pose-logs').exists())
            subprocess.run([sys.executable, str(probe / PREPARE.name)], check=True, capture_output=True)
            receipt = json.loads((root / '.work/runtime-pose-native/staging.json').read_text())
            stage = Path(receipt['stage'])
            try:
                self.assertEqual((stage / 'genuine.nvwa.json').read_bytes(), (artifact / 'genuine44-calibrated47.nvwa.json').read_bytes())
                self.assertEqual((stage / 'assets/generated/genuine44-calibrated47.glb').read_bytes(), b'fake packaging bytes')
                launcher = root / '.work/runtime-pose-native/NvwaPoseProbe.app/Contents/MacOS/NvwaPoseProbe'
                subprocess.run([str(launcher)], check=True)
                text = (root / '.work/runtime-pose-logs/native.log').read_text()
                self.assertIn('fake-packaging-only', text)
                self.assertEqual((root / '.work/runtime-pose-logs/native-exit-code.txt').read_text().strip(), '0')
                self.assertIn('work='+str(stage / 'genuine.nvwa.json'), text)
                self.assertIn('assets='+str(stage / 'assets'), text)
                self.assertIn('output='+str((probe / 'results/native.json').resolve()), text)
            finally:
                shutil.rmtree(stage)

    def test_missing_log_directory_mutation_fails_actual_launcher(self):
        with tempfile.TemporaryDirectory(prefix='nvwa-packaging-mutation-') as temporary:
            mutated = Path(temporary) / 'prepare_native.py'
            source = PREPARE.read_text()
            line = "(ROOT / '.work/runtime-pose-logs').mkdir(parents=True, exist_ok=True)"
            self.assertEqual(source.count(line), 1)
            mutated.write_text(source.replace(line, ''))
            with self.assertRaises(subprocess.CalledProcessError):
                self.exercise_fresh_staging(mutated)

    def test_missing_build_fails_before_app_staging(self):
        with tempfile.TemporaryDirectory(prefix='nvwa-packaging-test-') as temporary:
            root = Path(temporary)
            probe = root / 'experiments/49-runtime-pose-parity/probe'
            probe.mkdir(parents=True)
            shutil.copy2(PREPARE, probe / PREPARE.name)
            result = subprocess.run([sys.executable, str(probe / PREPARE.name)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('diagnostic binary missing', result.stderr)
            self.assertFalse((root / '.work/runtime-pose-native').exists())

if __name__ == '__main__':
    unittest.main()
