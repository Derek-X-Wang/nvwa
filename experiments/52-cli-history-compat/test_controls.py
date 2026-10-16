"""Actual adapter CLI refusal/restoration and original assertion-boundary controls."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import audit


class HistoricalCliControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='nvwa-cli-history-controls-')
        cls.base = Path(cls.temporary.name).resolve()
        cls.repo = cls.base/'repo'
        cls.repo.mkdir()
        audit.stage(audit.preflight(audit.HERE.parents[1]), cls.repo)
        cls.material = cls.base/'adapter'
        cls.material.mkdir()
        for name in ['audit.py', 'MANIFEST.json']:
            shutil.copy2(audit.HERE/name, cls.material/name)
        shutil.copytree(audit.HERE/'sources', cls.material/'sources')

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def cli(self, optimized=False, optimize_environment=None):
        env = dict(os.environ)
        env.pop('PYTHONOPTIMIZE', None)
        if optimize_environment is not None:
            env['PYTHONOPTIMIZE'] = optimize_environment
        return subprocess.run([sys.executable, '-B']+(['-O'] if optimized else [])+
                              [str(self.material/'audit.py'), '--repo-root', str(self.repo)],
                              capture_output=True, text=True, env=env, timeout=15, check=False)

    def green(self, **kwargs):
        result = self.cli(**kwargs)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output['status'], 'PASS_HISTORICAL38')
        self.assertEqual(output['current_product_checks'], 'NOT-RUN')
        self.assertEqual(len(output['original_clis']), 2)
        for child in output['original_clis']:
            self.assertEqual(child['child_mode'], 'normal_python_assertions_enforced')
        controls = next(child for child in output['original_clis'] if child['check'] == 'controls')
        self.assertEqual(controls['original_cli']['tamper_rejected_and_restored'], 5)
        return output

    def red(self, expected):
        # Use optimized wrapper and hostile optimize env: refusal checks must persist.
        result = self.cli(optimized=True, optimize_environment='2')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected, result.stderr)
        self.assertEqual(result.stdout, '')

    def mutation(self, root, relative, replacement, expected):
        path = root/relative
        original = path.read_bytes()
        try:
            path.write_bytes(replacement)
            self.red(expected)
        finally:
            path.write_bytes(original)
        self.green()

    def test_normal_baseline_preserves_original_eighteen_receipts_and_five_controls(self):
        output = self.green()
        original = output['original_clis'][0]['original_cli']
        self.assertEqual([r['verified_process_receipts'] for r in original['runs']], [9, 9])
        self.assertEqual(original['transport_probe_calls_checked'], 9)

    def test_optimized_wrapper_and_optimization_environment_keep_original_assertions(self):
        self.green(optimized=True, optimize_environment='2')
        self.green(optimize_environment='2')

    def test_pinned_source_mutation_rejected_and_restored(self):
        name = 'sources/crates/nvwa-cli/src/main.rs.txt'
        self.mutation(self.material, name, (self.material/name).read_bytes()+b'\n', 'input identity changed: crates/nvwa-cli/src/main.rs')

    def test_receipt_mutation_rejected_and_restored(self):
        name = audit.HISTORICAL+'/accepted-run/receipts/04-stale-timeline/stderr.txt'
        self.mutation(self.repo, name, b'{"code":"pretend_success"}\n', 'input identity changed: '+name)

    def test_retained_source_manifest_mutation_rejected_and_restored(self):
        name = audit.HISTORICAL+'/accepted-run/source-manifest.json'
        manifest = json.loads((self.repo/name).read_bytes())
        manifest['sources']['crates/nvwa-cli/src/main.rs'] = '0'*64
        self.mutation(self.repo, name, json.dumps(manifest).encode(), 'input identity changed: '+name)

    def test_adapter_source_pin_manifest_mutation_rejected_and_restored(self):
        manifest = json.loads((self.material/'MANIFEST.json').read_bytes())
        manifest['files']['crates/nvwa-cli/src/main.rs']['sha256'] = '0'*64
        self.mutation(self.material, 'MANIFEST.json', json.dumps(manifest).encode(), 'manifest pin changed')

    def test_duplicate_manifest_keys_rejected_and_restored(self):
        raw = (self.material/'MANIFEST.json').read_bytes()
        self.mutation(self.material, 'MANIFEST.json', raw.replace(b'{', b'{\"files\":{},', 1), 'duplicate JSON key')

    def test_archive_alias_mapping_rejected_and_restored(self):
        manifest = json.loads((self.material/'MANIFEST.json').read_bytes())
        manifest['files']['crates/nvwa-cli/src/main.rs']['archive_path'] = 'sources/crates/nvwa-core/src/lib.rs.txt'
        self.mutation(self.material, 'MANIFEST.json', json.dumps(manifest).encode(), 'archive path mapping changed')

    def test_missing_source_path_rejected_and_restored(self):
        path = self.material/'sources/crates/nvwa-cli/src/main.rs.txt'
        original = path.read_bytes()
        try:
            path.unlink()
            self.red('missing or extra archived source path')
        finally:
            path.write_bytes(original)
        self.green()

    def test_extra_source_path_rejected_and_restored(self):
        path = self.material/'sources/untrusted.rs.txt'
        try:
            path.write_bytes(b'untrusted')
            self.red('missing or extra archived source path')
        finally:
            path.unlink()
        self.green()

    def test_untrusted_source_paths_rejected_and_restored(self):
        for unsafe in ['.', '../outside.rs', '/absolute.rs', 'sources/../outside.rs', 'sources//double.rs', 'sources\\win.rs']:
            with self.subTest(path=unsafe):
                manifest = json.loads((self.material/'MANIFEST.json').read_bytes())
                manifest['files'][unsafe] = manifest['files'].pop('crates/nvwa-cli/src/main.rs')
                self.mutation(self.material, 'MANIFEST.json', json.dumps(manifest).encode(), 'unsafe relative path')

    def test_extra_historical_receipt_rejected_and_restored(self):
        path = self.repo/audit.HISTORICAL/'receipts/untrusted.json'
        try:
            path.write_bytes(b'{}')
            self.red('missing or extra historical input path')
        finally:
            path.unlink()
        self.green()

    def test_symlink_source_and_receipt_rejected_and_restored(self):
        for root, name in [(self.material, 'sources/crates/nvwa-cli/src/main.rs.txt'),
                           (self.repo, audit.HISTORICAL+'/accepted-run/source-manifest.json')]:
            with self.subTest(path=name):
                path = root/name
                original = path.read_bytes()
                target = self.base/'link-target'
                target.write_bytes(original)
                try:
                    path.unlink()
                    path.symlink_to(target)
                    self.red('symlink')
                finally:
                    path.unlink()
                    path.write_bytes(original)
                    target.unlink()
                self.green()

    def test_changed_command_and_historical_source_rejected_and_restored(self):
        for name in [audit.HISTORICAL+'/accepted-run/appearance.commands.json',
                     audit.HISTORICAL+'/historical-source/docs/implementation/contract.md']:
            with self.subTest(path=name):
                self.mutation(self.repo, name, (self.repo/name).read_bytes()+b'\n', 'input identity changed: '+name)

    def test_original_assertion_rejects_receipt_under_hostile_optimization_then_restores(self):
        path = self.repo/audit.HISTORICAL/'accepted-run/receipts/04-stale-timeline/stderr.txt'
        original = path.read_bytes()
        try:
            path.write_bytes(b'{"code":"pretend_success"}\n')
            with patch.dict(os.environ, {'PYTHONOPTIMIZE': '2'}):
                with self.assertRaisesRegex(audit.Rejected, 'original audit CLI exit 1.*'):
                    audit.run_staged(self.repo, 'audit')
        finally:
            path.write_bytes(original)
        with patch.dict(os.environ, {'PYTHONOPTIMIZE': '2'}):
            self.assertEqual(audit.run_staged(self.repo, 'audit')['exit_code'], 0)
        self.green(optimized=True, optimize_environment='2')

    def test_original_source_assertion_rejects_changed_stage_then_restores(self):
        path = self.repo/'crates/nvwa-cli/src/main.rs'
        original = path.read_bytes()
        try:
            path.write_bytes(original+b'\n')
            with self.assertRaisesRegex(audit.Rejected, 'original audit CLI exit 1.*'):
                audit.run_staged(self.repo, 'audit')
        finally:
            path.write_bytes(original)
        self.assertEqual(audit.run_staged(self.repo, 'audit')['exit_code'], 0)

    def test_nested_original_controls_children_keep_assertions_with_optimization_tripwire(self):
        path = self.repo/audit.HISTORICAL/'verify.py'
        original = path.read_bytes()
        tripwire = (b'import sys\nif sys.flags.optimize != 0 or not __debug__:\n'
                    b'    raise SystemExit(\"nested original child assertions disabled\")\n')
        try:
            path.write_bytes(tripwire+original)
            with patch.dict(os.environ, {'PYTHONOPTIMIZE': '2'}):
                result = audit.run_staged(self.repo, 'controls')
            self.assertEqual(result['original_cli']['tamper_rejected_and_restored'], 5)
        finally:
            path.write_bytes(original)
        self.green(optimized=True, optimize_environment='2')

    def test_child_timeout_propagates_as_failure(self):
        with patch.object(audit.subprocess, 'run', side_effect=subprocess.TimeoutExpired('owned-child', 30)):
            with self.assertRaises(subprocess.TimeoutExpired):
                audit.run_staged(self.repo, 'audit')


if __name__ == '__main__':
    unittest.main()
