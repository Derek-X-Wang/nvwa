"""Exercise CI-called cache boundaries with tiny owned targets; no Cargo build."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'experiments/83-native-cache-trial/cache_trial.py'
spec = importlib.util.spec_from_file_location('cache_trial', SCRIPT)
trial = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trial)


def without_trial(text):
    # Exact indentation disambiguates the whole optional warm job from its steps.
    text = re.sub(r'(?ms)^  # native-cache-trial begin\n.*?^  # native-cache-trial end\n', '', text)
    return re.sub(r'(?ms)^ +# native-cache-trial begin\n.*?^ +# native-cache-trial end\n', '', text)


class CacheTrial(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='nvwa-cache-control-')
        self.addCleanup(self.temporary.cleanup)
        self.temp = Path(self.temporary.name).resolve()
        self.root = self.temp / 'checkout'
        self.root.mkdir()
        directory = self.root / 'experiments/83-native-cache-trial'
        directory.mkdir(parents=True)
        shutil.copyfile(SCRIPT, directory / 'cache_trial.py')
        self.script = directory / 'cache_trial.py'
        (directory / 'phase.json').write_text('{"phase":"trial"}\n')
        (self.root / '.gitignore').write_text('target/\n')
        (self.root / 'Cargo.lock').write_text('fixed lock fixture\n')
        (self.root / 'Cargo.toml').write_text('fixed manifest fixture\n')
        (self.root / 'source.rs').write_text('original production seam fixture\n')
        self.git('init', '-q')
        self.git('add', '.')
        self.git('-c', 'user.name=Control', '-c', 'user.email=control@example.invalid', 'commit', '-qm', 'fixture')
        self.bin = self.temp / 'bin'
        self.bin.mkdir()
        for name, text in [('rustc', 'rustc 1.95.0 (fixture)\nhost: aarch64-apple-darwin'), ('cargo', 'cargo 1.95.0 (fixture)')]:
            tool = self.bin / name
            tool.write_text('#!/bin/sh\nprintf "%s\\n" '+repr(text)+'\n')
            tool.chmod(0o755)
        uname = self.bin / 'uname'
        uname.write_text('#!/bin/sh\ncase "$1" in -s) echo Darwin;; -m) echo arm64;; *) exit 1;; esac\n')
        uname.chmod(0o755)
        self.target = self.root / 'target'
        self.env = {k:v for k,v in os.environ.items() if not k.startswith(('CARGO_', 'RUST'))}
        self.env.update(trial.CARGO_ENV)
        self.env.update(PATH=str(self.bin)+os.pathsep+os.environ['PATH'], CARGO_TARGET_DIR=str(self.target),
                        GITHUB_OUTPUT=str(self.temp / 'output'), GITHUB_SHA=self.git('rev-parse', 'HEAD'),
                        GITHUB_EVENT_NAME='pull_request', GITHUB_REPOSITORY='Derek-X-Wang/nvwa',
                        TRIAL_HEAD_REPOSITORY='Derek-X-Wang/nvwa', TRIAL_HEAD_REF='codex/native-cache-trial',
                        GITHUB_RUN_ID='123', GITHUB_RUN_ATTEMPT='1', RUNNER_OS='macOS', RUNNER_ARCH='ARM64',
                        ImageOS='macos14', ImageVersion='fixture-1', RUNNER_TEMP=str(self.temp))

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True).strip()

    def call(self, stage, lane='cold', **env):
        return subprocess.run([sys.executable, '-B', str(self.script), stage, '--lane', lane],
                              cwd=self.root, env={**self.env, **env}, capture_output=True, text=True)

    def prepare(self):
        result = self.call('prepare')
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = [json.loads(line.removeprefix('NVWA_NATIVE_CACHE ')) for line in result.stdout.splitlines()]
        return next(row['key'] for row in rows if row['stage'] == 'prepare')

    def receipt(self, key, lane='cold', **overrides):
        values = dict(TRIAL_HIT='', TRIAL_PRIMARY=key, TRIAL_MATCHED='')
        values.update(overrides)
        return self.call('receipt', lane, **values)

    def gate_fixtures(self):
        original = (self.root / 'source.rs').read_bytes()
        cases = [{'name': name, 'source': 'source.rs', 'before_sha256': trial.sha(original),
                  'mutant_sha256': trial.sha(b'distinct mutant'), 'restored_sha256': trial.sha(original),
                  'semantic_test_failure': True, 'red_exit': 101, 'restored_green': True, 'restored_exit': 0}
                 for name in trial.CASES]
        hashes = {}
        directory = self.temp / 'nvwa-b1-motion-mutations'
        directory.mkdir(exist_ok=True)
        for case in cases:
            name = case['name']
            case.update(command=['cargo', 'test', '--workspace', '--lib', '--locked', '--offline',
                                 trial.TESTS[name], '--', '--exact', '--test-threads=1', '--nocapture'],
                        intended_assertion=trial.ASSERTIONS[name])
            for suffix, text in [('red', 'running 1 test\n'+trial.TESTS[name]+'\n'+trial.ASSERTIONS[name]+
                                  '\ntest result: FAILED. 0 passed; 1 failed\n'),
                                 ('restored-green', 'test result: ok. 1 passed; 0 failed\n')]:
                filename = name+'-'+suffix+'.log'
                (directory / filename).write_text(text)
                hashes[filename] = trial.sha(text.encode())
        mutation = {'passed': True, 'cases': cases, 'hashes': hashes}
        matrix = {'passed': True, 'records': 594, 'passing_records': 594, 'probe_exit': 0,
                  'probe_complete_marker': True, 'coverage': {'complete': True}, 'failures': []}
        for name, value in [('nvwa-b1-motion-mutations', mutation), ('nvwa-b1-motion-matrix', matrix)]:
            path = self.temp / name
            path.mkdir(exist_ok=True)
            (path / 'summary.json').write_text(json.dumps(value))
        return mutation, matrix

    def test_real_cli_same_source_pair_integrity_and_source_mtimes(self):
        before = (self.root / 'source.rs').stat().st_mtime_ns
        key = self.prepare()
        self.assertEqual(self.receipt(key).returncode, 0)
        self.target.mkdir()
        (self.target / 'compiled').write_bytes(b'tiny compiled-target fixture')
        self.gate_fixtures()
        saved = self.call('finish')
        self.assertEqual(saved.returncode, 0, saved.stderr)
        self.assertEqual(self.receipt(key, 'persisted', TRIAL_HIT='true', TRIAL_MATCHED=key).returncode, 0)
        # Fresh-runner shape: move complete saved target out before warm prepare.
        archive = self.root / 'archive'
        self.target.rename(archive)
        self.assertEqual(self.call('prepare', 'warm', TRIAL_EXPECTED_KEY=key).returncode, 0)
        archive.rename(self.target)
        hit = self.receipt(key, 'warm', TRIAL_HIT='true', TRIAL_MATCHED=key)
        self.assertEqual(hit.returncode, 0, hit.stderr)
        self.assertEqual(self.call('finish', 'warm').returncode, 0)
        self.assertEqual((self.root / 'source.rs').stat().st_mtime_ns, before)
        (self.target / 'compiled').write_bytes(b'corrupt fixture')
        self.assertNotEqual(self.receipt(key, 'warm', TRIAL_HIT='true', TRIAL_MATCHED=key).returncode, 0)

    def test_off_untrusted_main_and_adopted_never_enable_trial(self):
        for change in [{'GITHUB_EVENT_NAME':'push'}, {'TRIAL_HEAD_REPOSITORY':'other/fork'},
                       {'TRIAL_HEAD_REF':'feature'}, {'GITHUB_REPOSITORY':'other/repo'}]:
            self.assertEqual(self.call('prepare', **change).returncode, 0)
            self.assertTrue((self.temp / 'output').read_text().endswith('enabled=false\n'))
            self.assertNotEqual(self.call('receipt', **change).returncode, 0)
        for phase in ['off', 'adopted']:
            (self.script.parent / 'phase.json').write_text(json.dumps({'phase':phase}))
            self.assertEqual(self.call('prepare').returncode, 0)
            self.assertTrue((self.temp / 'output').read_text().endswith('enabled=false\n'))

    def test_dirty_lock_source_wrong_target_nonempty_and_toolchain_fail_closed(self):
        self.prepare()
        for name in ['Cargo.lock', 'Cargo.toml', 'source.rs']:
            path = self.root / name
            original = path.read_bytes()
            path.write_bytes(original+b'changed')
            self.assertNotEqual(self.call('prepare').returncode, 0)
            path.write_bytes(original)
        for change in [{'GITHUB_SHA':'a'*40}, {'CARGO_BUILD_JOBS':'2'}, {'RUSTFLAGS':'-O'},
                       {'ImageVersion':''}, {'RUNNER_ARCH':'X64'}, {'CARGO_TARGET_DIR':str(self.temp)}]:
            self.assertNotEqual(self.call('prepare', **change).returncode, 0)
        self.target.mkdir()
        (self.target / 'stale').write_text('old')
        self.assertNotEqual(self.call('prepare').returncode, 0)
        shutil.rmtree(self.target)
        self.target.symlink_to(self.temp, target_is_directory=True)
        self.assertNotEqual(self.call('prepare').returncode, 0)

    def test_receipts_cannot_convert_unavailable_or_warning_save_into_warm_hit(self):
        key = self.prepare()
        for hit, matched in [('true',key), ('false',key), ('',key), ('true','foreign')]:
            self.assertNotEqual(self.receipt(key, TRIAL_HIT=hit, TRIAL_MATCHED=matched).returncode, 0)
        for lane in ['persisted', 'warm']:
            for hit, matched in [('', ''), ('false',''), ('true','foreign'), ('True',key)]:
                self.assertNotEqual(self.receipt(key, lane, TRIAL_HIT=hit, TRIAL_MATCHED=matched).returncode, 0)
        self.assertNotEqual(self.receipt(key, TRIAL_PRIMARY='foreign').returncode, 0)
        for change in [{'ImageVersion':'changed'}, {'GITHUB_RUN_ATTEMPT':'2'}, {'GITHUB_RUN_ID':'124'}]:
            self.assertNotEqual(self.call('prepare', 'warm', TRIAL_EXPECTED_KEY=key, **change).returncode, 0)

    def test_all_semantic_reds_and_restored_greens_and_actual_matrix_required(self):
        self.prepare()
        self.target.mkdir()
        (self.target / 'compiled').write_bytes(b'tiny')
        self.assertNotEqual(self.call('finish').returncode, 0)
        mutations, matrix = self.gate_fixtures()
        bad = [lambda v: v['cases'].pop(), lambda v: v['cases'][0].update(red_exit=0),
               lambda v: v['cases'][1].update(semantic_test_failure=False),
               lambda v: v['cases'][2].update(restored_green=False),
               lambda v: v['cases'][0].update(restored_sha256='foreign'),
               lambda v: v['cases'][0].update(intended_assertion='wrong semantic assertion'),
               lambda v: v.update(hashes={})]
        path = self.temp / 'nvwa-b1-motion-mutations/summary.json'
        for mutate in bad:
            value = copy.deepcopy(mutations)
            mutate(value)
            path.write_text(json.dumps(value))
            self.assertNotEqual(self.call('finish').returncode, 0)
            self.assertFalse((self.target / trial.MARKER).exists())
        path.write_text(json.dumps(mutations))
        red = self.temp / 'nvwa-b1-motion-mutations' / (trial.CASES[0]+'-red.log')
        original = red.read_text()
        red.write_text('running 1 test\ntest result: FAILED. 0 passed; 1 failed\n')
        wrong_semantic = copy.deepcopy(mutations)
        wrong_semantic['hashes'][red.name] = trial.sha(red.read_bytes())
        path.write_text(json.dumps(wrong_semantic))
        self.assertNotEqual(self.call('finish').returncode, 0)
        red.write_text(original)
        path.write_text(json.dumps(mutations))
        for change in [{'records':593}, {'probe_complete_marker':False}, {'passing_records':593}, {'passed':False}]:
            (self.temp / 'nvwa-b1-motion-matrix/summary.json').write_text(json.dumps({**matrix, **change}))
            self.assertNotEqual(self.call('finish').returncode, 0)

    def test_oversize_sparse_target_and_escaping_symlink_reject_before_save(self):
        self.prepare()
        self.gate_fixtures()
        self.target.mkdir()
        path = self.target / 'oversize'
        with path.open('wb') as stream:
            stream.truncate(trial.CAP+1)
        self.assertNotEqual(self.call('finish').returncode, 0)
        self.assertFalse((self.target / trial.MARKER).exists())
        path.unlink()
        path.symlink_to(self.root / 'source.rs')
        self.assertNotEqual(self.call('finish').returncode, 0)

    def test_exact_original_workflow_and_full_warm_step_policy_parity(self):
        workflow = (ROOT / '.github/workflows/ci.yml').read_text()
        baseline = without_trial(workflow)
        self.assertEqual(hashlib.sha256(baseline.encode()).hexdigest(), '5bdd5efa6b48150c2fbf19eb9cb1b9f1ae64303caea87bfc9c2615b58c201302')
        native = workflow.split('  native-and-wasm:\n', 1)[1].split('  b1-source-regression:\n', 1)[0]
        warm = workflow.split('  native-cache-warm:\n', 1)[1].rsplit('  # native-cache-trial end\n', 1)[0]
        self.assertEqual(without_trial(native).split('    steps:\n', 1)[1],
                         without_trial(warm).split('    steps:\n', 1)[1])
        for job in [native, warm]:
            self.assertIn('runs-on: macos-14\n', job)
            self.assertIn('timeout-minutes: 60\n', job)
            self.assertIn("CARGO_BUILD_JOBS: '1'\n", job)
            self.assertIn('CARGO_TARGET_DIR: ${{ github.workspace }}/target\n', job)
        self.assertIn('needs: [native-and-wasm, b1-source-regression]\n', warm)
        self.assertIn("if: ${{ needs.native-and-wasm.outputs.trial_enabled == 'true' }}\n", warm)
        self.assertEqual(native.count('timeout-minutes: 4\n'), 3)
        self.assertEqual(warm.count('timeout-minutes: 4\n'), 1)
        self.assertEqual(workflow.count('actions/cache/restore@55cc8345863c7cc4c66a329aec7e433d2d1c52a9'), 3)
        self.assertEqual(workflow.count('actions/cache/save@55cc8345863c7cc4c66a329aec7e433d2d1c52a9'), 1)
        for forbidden in ['restore-keys:', 'ACTIONS_CACHE_SERVICE_V2', 'ACTIONS_RUNTIME_TOKEN:', 'pull_request_target:', 'workflow_run:']:
            self.assertNotIn(forbidden, workflow)
        self.assertNotIn('actions/cache/save@', warm)
        self.assertLess(native.index('Report existing command timing'), native.index('compression and save'))
        self.assertLess(native.index('compression and save'), native.index('Verify remote exact-key persistence'))
        self.assertLess(warm.index('verify restored target bytes'), warm.index('Run workspace CPU tests'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
