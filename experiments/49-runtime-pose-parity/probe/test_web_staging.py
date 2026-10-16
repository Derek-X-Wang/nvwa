"""Tool-selection controls use fake tools and assets; never renderer evidence."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

PREPARE = Path(__file__).with_name('prepare_web.py')


class PortableWebStaging(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='nvwa-web-staging-test-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.probe = self.root / 'experiments/49-runtime-pose-parity/probe'
        self.probe.mkdir(parents=True)
        self.script = self.probe / PREPARE.name
        shutil.copy2(PREPARE, self.script)
        self.stage = self.root / 'owned-output/site'
        self.wasm = self.root / 'probe.wasm'
        self.wasm.write_bytes(b'fake cargo wasm; packaging only')
        (self.probe / 'index.html').write_text('<title>fake packaging only</title>')
        self.artifact = self.root / 'experiments/48-genuine-fixture-work/artifacts'
        (self.artifact / 'assets/generated').mkdir(parents=True)
        (self.artifact / 'genuine44-calibrated47.nvwa.json').write_bytes(b'{"fake":true}\n')
        (self.artifact / 'assets/generated/genuine44-calibrated47.glb').write_bytes(b'fake glb')

    def tool(self, version, exit_code=0):
        path = self.root / 'tools with spaces/wasm-bindgen'
        path.parent.mkdir()
        path.write_text('#!' + sys.executable + '\n'
                        + 'import pathlib,sys\n'
                        + 'if sys.argv[1:] == ["--version"]:\n'
                        + ' print(' + repr(version) + ')\n'
                        + ' raise SystemExit(' + str(exit_code) + ')\n'
                        + 'out=pathlib.Path(sys.argv[sys.argv.index("--out-dir")+1])\n'
                        + '(out/"tool-call.txt").write_text(repr(sys.argv[1:]))\n')
        path.chmod(0o755)
        return path

    def run_prepare(self, tool=None):
        command = [sys.executable, str(self.script), '--wasm', str(self.wasm), '--stage', str(self.stage)]
        if tool is not None:
            command += ['--wasm-bindgen', str(tool)]
        return subprocess.run(command, capture_output=True, text=True)

    def test_explicit_pinned_tool_and_custom_paths_stage_exact_inputs(self):
        result = self.run_prepare(self.tool('wasm-bindgen 0.2.129'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.stage / 'tool-call.txt').is_file())
        self.assertEqual((self.stage / 'works/genuine44-calibrated47.nvwa.json').read_bytes(), b'{"fake":true}\n')
        self.assertEqual((self.stage / 'assets/generated/genuine44-calibrated47.glb').read_bytes(), b'fake glb')
        self.assertEqual((self.stage / 'index.html').read_bytes(), (self.probe / 'index.html').read_bytes())

    def test_missing_tool_argument_fails_without_staging(self):
        result = self.run_prepare()
        self.assertEqual(result.returncode, 2)
        self.assertIn('--wasm-bindgen', result.stderr)
        self.assertFalse(self.stage.exists())

    def test_missing_executable_fails_without_staging(self):
        result = self.run_prepare(self.root / 'does-not-exist')
        self.assertEqual(result.returncode, 2)
        self.assertIn('existing executable wasm-bindgen tool not found', result.stderr)
        self.assertFalse(self.stage.exists())

    def test_wrong_version_fails_without_staging(self):
        result = self.run_prepare(self.tool('wasm-bindgen 0.2.128'))
        self.assertEqual(result.returncode, 2)
        self.assertIn('must report exactly wasm-bindgen 0.2.129', result.stderr)
        self.assertFalse(self.stage.exists())

    def test_failing_version_probe_fails_without_staging(self):
        result = self.run_prepare(self.tool('wasm-bindgen 0.2.129', 7))
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.stage.exists())

    def test_missing_wasm_fails_without_staging(self):
        self.wasm.unlink()
        result = self.run_prepare(self.tool('wasm-bindgen 0.2.129'))
        self.assertEqual(result.returncode, 2)
        self.assertIn('already-built probe Wasm artifact not found', result.stderr)
        self.assertFalse(self.stage.exists())


if __name__ == '__main__':
    unittest.main()
