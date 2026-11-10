#!/usr/bin/env python3
"""Real Git classification, fail-closed aggregate and exact lane-contract tests."""
import hashlib
import importlib.util
import json
import os
import sys
from unittest.mock import patch
from pathlib import Path
import re
import gzip
import shlex
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('tier_policy', HERE / 'policy.py')
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


def job(text, name):
    found = re.search(r'^  ' + re.escape(name) + r':\n(.*?)(?=^  [a-z][a-z0-9-]*:\n|\Z)', text, re.M | re.S)
    if found is None:
        raise ValueError('job absent: ' + name)
    return found[0]


def complete_gate(full=False):
    needs = {name: {'result': 'success'} for name in policy.REQUIRED}
    needs['classify']['outputs'] = {'full_required': str(full).lower()}
    for part in policy.MAC_PARTS:
        needs[f'mac-{part}-required'] = {'result': 'success' if full else 'skipped'}
        needs[f'mac-{part}-background'] = {'result': 'skipped' if full else 'success'}
    return needs


class Classification(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='nvwa-ci-policy-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.invalid')
        self.write('README.md', 'baseline\n')
        self.write('crates/nvwa-core/src/lib.rs', 'fn shared() {}\n')
        self.base = self.commit()

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.root, stderr=subprocess.PIPE).decode().strip()

    def write(self, path, data):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(data)

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-qm', 'test')
        return self.git('rev-parse', 'HEAD')

    def result(self, base=None, head=None, kind='pull_request'):
        return policy.classify(self.root, kind, {'pull_request': {'base': {'sha': base or self.base}, 'head': {'sha': head or self.commit()}}})

    def test_ordinary_shared_and_asset_changes(self):
        self.write('crates/nvwa-core/src/lib.rs', 'fn shared() { let x = 1; }\n#[cfg(test)] mod tests {}\n')
        self.write('assets/shape.json', '{}')
        result = self.result()
        self.assertFalse(result['full_required'])
        self.assertEqual(result['changed_entries'], 2)

    def test_platform_content_deletion_and_addition_are_full(self):
        self.write('crates/nvwa-core/src/lib.rs', '#[cfg(target_os = "macos")] fn platform() {}\n')
        middle = self.commit()
        self.assertTrue(self.result(head=middle)['full_required'])
        self.write('crates/nvwa-core/src/lib.rs', 'fn shared() {}\n')
        self.assertTrue(self.result(base=middle)['full_required'])

    def test_unix_cfg_alias_and_unknown_shared_input_are_full(self):
        for source in ['#[cfg(unix)] fn f() {}', '#[cfg_attr(feature="native", inline)] fn f() {}',
                       '#[cfg(target_vendor = "apple")] fn f() {}']:
            self.write('crates/nvwa-core/src/lib.rs', source)
            self.assertTrue(self.result()['full_required'])
        self.write('crates/nvwa-core/src/lib.rs', 'fn shared() {}')
        self.write('crates/nvwa-core/src/platform.inc', 'platform code')
        self.assertTrue(self.result()['full_required'])

    def test_symlink_and_missing_git_fail_closed(self):
        (self.root / 'assets').mkdir()
        (self.root / 'assets/link.json').symlink_to('../README.md')
        self.assertTrue(self.result()['full_required'])
        with patch.object(policy, 'git', side_effect=OSError('missing Git')):
            self.assertTrue(self.result(head=self.base)['full_required'])
        for event in [None, [], 'bad', 7]:
            self.assertTrue(policy.classify(self.root, 'pull_request', event)['full_required'])

    def test_rename_and_delete_are_full(self):
        (self.root / 'README.md').unlink()
        self.write('docs/new.md', 'baseline\n')
        self.assertTrue(self.result()['full_required'])
        (self.root / 'docs/new.md').unlink()
        self.assertTrue(self.result()['full_required'])

    def test_policy_dependencies_and_unknown_paths_are_full(self):
        for path in ['Cargo.lock', 'crates/nvwa-core/Cargo.toml', 'scripts/helper.py', '.github/workflows/ci.yml', 'docs/agents/verification.md', 'crates/nvwa-studio/src/file_io.rs', 'unknown/file', 'assets/build.sh',
                     'examples/rust-toolchain.toml', 'examples/package.json', 'assets/macos/config.json',
                     'crates/nvwa-core/.cargo/config.toml']:
            with self.subTest(path=path):
                self.assertFalse(policy.ordinary_path(path))

    def test_complete_inventory_not_a_page_limit(self):
        for i in range(320):
            self.write(f'assets/test/{i}.json', '{}')
        self.write('scripts/last-sensitive.py', 'print(1)')
        result = self.result()
        self.assertTrue(result['full_required'])
        self.assertEqual(result['changed_entries'], 321)

    def test_missing_history_empty_diff_and_malformed_event_fail_closed(self):
        for event in [{}, {'pull_request': {}}, {'pull_request': {'base': {'sha': 'a'*40}, 'head': {'sha': self.base}}}]:
            self.assertTrue(policy.classify(self.root, 'pull_request', event)['full_required'])
        self.assertTrue(self.result(head=self.base)['full_required'])
        for event in ['push', 'release', 'workflow_dispatch', 'unknown']:
            self.assertTrue(self.result(head=self.base, kind=event)['full_required'])

    def test_parser_rejects_truncated_and_unsafe_inventory(self):
        for raw in [b'M\0', b'M\0path', b'R100\0one\0', b'?\0file\0', b'M\0../file\0', b'A\0a\nb\0']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                policy.parse_changes(raw)
        self.assertEqual(policy.parse_changes(b'R100\0old\0new\0'), [('R100', ['old', 'new'])])


class Aggregate(unittest.TestCase):
    def test_required_gate_reads_only_its_declared_mac_dependencies(self):
        for full in [False, True]:
            needs = complete_gate(full)
            for part in policy.MAC_PARTS:
                del needs[f'mac-{part}-background']
            self.assertEqual(policy.check_gate(needs), [])

    def test_valid_ordinary_does_not_depend_on_background(self):
        needs = complete_gate()
        for status in ['failure', 'cancelled', 'in_progress', 'missing']:
            needs['mac-workspace-background'] = {'result': status}
            self.assertEqual(policy.check_gate(needs), [])

    def test_report_rejects_missing_cancelled_and_double_execution(self):
        for full in [False, True]:
            for part in policy.MAC_PARTS:
                for status in ['failure', 'cancelled', 'skipped', 'in_progress', 'missing']:
                    needs = complete_gate(full)
                    lane = f'mac-{part}-required' if full else f'mac-{part}-background'
                    needs[lane] = {'result': status}
                    with self.subTest(full=full, lane=lane, status=status), tempfile.TemporaryDirectory() as d:
                        env = {**os.environ, 'TIER_NEEDS': json.dumps(needs), 'GITHUB_STEP_SUMMARY': d+'/summary'}
                        r = subprocess.run([sys.executable, '-B', str(HERE/'policy.py'), 'report'], env=env, capture_output=True)
                        self.assertNotEqual(r.returncode, 0)
                        self.assertIn(status, Path(d+'/summary').read_text())
            with tempfile.TemporaryDirectory() as d:
                needs = complete_gate(full)
                env = {**os.environ, 'TIER_NEEDS': json.dumps(needs), 'GITHUB_STEP_SUMMARY': d+'/summary'}
                r = subprocess.run([sys.executable, '-B', str(HERE/'policy.py'), 'report'], env=env, capture_output=True)
                self.assertEqual(r.returncode, 0)

    def test_all_required_results_fail_closed(self):
        for full in [False, True]:
            self.assertEqual(policy.check_gate(complete_gate(full)), [])
            for name in policy.REQUIRED:
                for result in ['failure', 'cancelled', 'skipped', '', 'in_progress']:
                    needs = complete_gate(full)
                    needs[name]['result'] = result
                    self.assertTrue(policy.check_gate(needs), (name, result))
                needs = complete_gate(full)
                del needs[name]
                self.assertTrue(policy.check_gate(needs))
        for part in policy.MAC_PARTS:
            for result in ['failure', 'cancelled', 'skipped', '', 'in_progress']:
                needs = complete_gate(True)
                needs[f'mac-{part}-required']['result'] = result
                self.assertTrue(policy.check_gate(needs))
            needs = complete_gate(True)
            del needs[f'mac-{part}-required']
            self.assertTrue(policy.check_gate(needs))
        for value in [None, 'TRUE', '', 'yes']:
            needs = complete_gate()
            needs['classify']['outputs']['full_required'] = value
            self.assertTrue(policy.check_gate(needs))


class NativeGarmentWitness(unittest.TestCase):
    def test_exact_single_frame_and_failure_propagation(self):
        spec = importlib.util.spec_from_file_location('mac_witness', HERE/'mac_garment_witness.py')
        witness = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(witness)
        record = {'kind': 'matrix', 'request': witness.EXPECTED, 'snapshot': {}}
        marker = {'kind': 'witness-complete', 'samples': 1}
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            assets = root/'assets'
            assets.mkdir()
            binary = root/'producer'
            frame = root/'frame.json.gz'
            def producer(records, exit_code=0):
                lines = ['#!/bin/sh']
                lines += ['printf "%s\\n" '+shlex.quote('B1_60 '+json.dumps(item)) for item in records]
                lines.append('exit '+str(exit_code))
                binary.write_text('\n'.join(lines)+'\n')
                binary.chmod(0o755)
            with patch.object(witness.platform, 'system', return_value='Darwin'), \
                 patch.object(witness.platform, 'machine', return_value='arm64'):
                producer([record, marker])
                witness.capture(binary, assets, frame)
                with gzip.open(frame, 'rt') as source:
                    self.assertEqual(json.load(source), record)
                frame.unlink()
                for records, code in [([record], 0), ([record, marker, marker], 0),
                                      ([record, marker], 2),
                                      ([{**record, 'request': {**witness.EXPECTED, 'k': 8}}, marker], 0)]:
                    producer(records, code)
                    with self.assertRaises(ValueError):
                        witness.capture(binary, assets, frame)
                    self.assertFalse(frame.exists())
            with self.assertRaisesRegex(ValueError, 'Darwin arm64'):
                witness.capture(binary, assets, frame)


class CompletionReport(unittest.TestCase):
    def setUp(self):
        workflow = (ROOT/'.github/workflows/ci-mac-report.yml').read_text()
        body = workflow.split("          python3 - <<'PY'\n", 1)[1].rsplit('          PY\n', 1)[0]
        self.namespace = {'__name__': 'report_control'}
        exec(compile('\n'.join(line[10:] for line in body.splitlines()), 'ci-mac-report.yml', 'exec'), self.namespace)
        self.run = {'id': 123, 'run_attempt': 2, 'head_sha': 'a'*40, 'name': 'Bounded CI',
                    'path': '.github/workflows/ci.yml', 'status': 'completed'}
        self.jobs = [{'id': i+1, 'run_id': 123, 'head_sha': 'a'*40, 'name': name,
                      'status': 'completed', 'conclusion': state}
                     for i, (name, state) in enumerate(zip(self.namespace['NAMES'], ['skipped']*2+['success']*2))]
        for kind in ('required', 'background'):
            for part in policy.MAC_PARTS:
                lane = job((ROOT/'.github/workflows/ci.yml').read_text(), f'mac-{part}-{kind}')
                title = lane.split('    name: ', 1)[1].split('\n', 1)[0]
                self.assertIn(title, self.namespace['NAMES'])
        self.assertNotIn('checkout', '\n'.join(line for line in workflow.splitlines() if not line.startswith('#')))
        self.assertNotIn('write', '\n'.join(line for line in workflow.splitlines() if line.strip().startswith(('actions:', 'contents:', 'pull-requests:', 'issues:'))))

    def test_identity_and_complete_paginated_inventory(self):
        event = {'repository': {'full_name': 'Derek-X-Wang/nvwa'}, 'workflow_run': self.run}
        self.assertEqual(self.namespace['identity'](event), self.run)
        for key, value in [('name', 'Other'), ('status', 'in_progress'), ('run_attempt', 0), ('head_sha', 'unknown')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.namespace['identity']({**event, 'workflow_run': {**self.run, key: value}})
        filler = [{**self.jobs[0], 'id': i+10, 'name': 'Other'} for i in range(100)]
        pages = [{'total_count': 104, 'jobs': filler}, {'total_count': 104, 'jobs': self.jobs}]
        urls = []
        def fetch(url):
            urls.append(url)
            return pages.pop(0)
        self.assertEqual(len(self.namespace['collect'](self.run, fetch)), 104)
        self.assertIn('/attempts/2/jobs?per_page=100&page=2', urls[1])
        for jobs in [self.jobs*2, [{**self.jobs[0], 'run_id': 7}], [{**self.jobs[0], 'head_sha': 'b'*40}]]:
            with self.assertRaises(ValueError):
                self.namespace['collect'](self.run, lambda url: {'total_count': len(jobs), 'jobs': jobs})
        with self.assertRaises(ValueError):
            self.namespace['collect'](self.run, lambda url: {'total_count': 3, 'jobs': []})

    def test_failures_cancellation_missing_and_double_success_remain_red(self):
        self.assertTrue(self.namespace['result'](self.jobs)[1])
        for index in range(2, 4):
            for state in ['cancelled', 'failure', 'timed_out', 'skipped', None]:
                altered = [{**j} for j in self.jobs]
                altered[index]['conclusion'] = state
                self.assertFalse(self.namespace['result'](altered)[1])
        required_selected = [{**j, 'conclusion': 'success' if i < 2 else 'skipped'}
                             for i, j in enumerate(self.jobs)]
        self.assertTrue(self.namespace['result'](required_selected)[1])
        for index in range(2):
            for state in ['cancelled', 'failure', 'timed_out', 'skipped', None]:
                altered = [{**j} for j in required_selected]
                altered[index]['conclusion'] = state
                self.assertFalse(self.namespace['result'](altered)[1])
        self.assertFalse(self.namespace['result'](self.jobs[:1])[1])
        self.assertFalse(self.namespace['result'](self.jobs*2)[1])
        self.assertFalse(self.namespace['result']([{**j, 'conclusion': 'success'} for j in self.jobs])[1])

    def test_pre_rollout_legacy_requires_exact_inventory_and_success(self):
        names = self.namespace['LEGACY_NAMES']
        old_run = {**self.run, 'created_at': '2026-11-09T22:16:37Z'}
        old_jobs = [{'id': i+1, 'run_id': 123, 'head_sha': 'a'*40, 'name': name,
                     'status': 'completed', 'conclusion': 'success' if name == names[2] else 'skipped'}
                    for i, name in enumerate(names)]
        result = self.namespace['result']
        self.assertTrue(result(old_jobs, old_run)[1])
        for state in ('failure', 'cancelled', 'timed_out', 'skipped', None):
            altered = [{**j} for j in old_jobs]
            altered[2]['conclusion'] = state
            self.assertFalse(result(altered, old_run)[1], state)
        for altered in (old_jobs[:2], old_jobs + [old_jobs[2]],
                        old_jobs + [{**old_jobs[0], 'id': 99, 'name': 'unexpected'}]):
            self.assertFalse(result(altered, old_run)[1])
        for created in ('2026-11-09T22:52:38Z', '2026-11-10T00:00:00Z', 'bad', None):
            self.assertFalse(result(old_jobs, {**old_run, 'created_at': created})[1])
        self.assertFalse(result(old_jobs)[1])
        # A split run begun before rollout still uses the four current results.
        self.assertTrue(result(self.jobs, old_run)[1])


class WorkflowContract(unittest.TestCase):
    def test_original_full_mac_commands_and_budget_remain_exact(self):
        old = (HERE / 'predecessor-ci.yml').read_text()
        new = (ROOT / '.github/workflows/ci.yml').read_text()
        import importlib.util
        split_spec = importlib.util.spec_from_file_location('mac_split_contract', HERE/'mac_split_contract.py')
        split_module = importlib.util.module_from_spec(split_spec)
        split_spec.loader.exec_module(split_module)
        new = split_module.project(new, self)
        self.assertEqual(new.count('    needs: [classify, portable, portable-eye]\n'), 2)
        new = new.replace('    needs: [classify, portable, portable-eye]\n', '    needs: [classify, portable]\n')
        original = job(old, 'native-and-wasm')
        required = job(new, 'native-and-wasm').replace("    needs: [classify, portable]\n    if: ${{ needs.classify.outputs.full_required == 'true' }}\n", '    needs: portable\n', 1)
        self.assertEqual(required, original)
        background = job(new, 'mac-full-background').replace('  mac-full-background:\n', '  native-and-wasm:\n', 1).replace('    name: Complete Mac background evidence\n', '    name: macOS CPU tests and Wasm compile check\n', 1).replace("    needs: [classify, portable]\n    if: ${{ needs.classify.outputs.full_required == 'false' }}\n", '    needs: portable\n', 1)
        self.assertEqual(background, original)
        # The native entrypoint and its real platform guard remain original.
        native = (ROOT / 'experiments/27-ci-baseline/check.sh').read_text()
        self.assertIn('"$(uname -s)" == Darwin && "$(uname -m)" == arm64', native)
        self.assertNotIn('continue-on-error', job(new, 'required-gate'))
        self.assertNotIn('mac-full-background', job(new, 'required-gate'))
        self.assertIn('if: ${{ always() }}', job(new, 'required-gate'))
        self.assertIn('fetch-depth: 0', job(new, 'classify'))
        self.assertIn("tags: ['*']", new)
        self.assertIn('  workflow_dispatch:', new)
        self.assertIn('  release:', new)

    def test_mac_platform_coverage_linux_matrix_and_no_partial_seed(self):
        workflow = (ROOT/'.github/workflows/ci.yml').read_text()
        old = job((HERE/'portable-split-v3-ci.yml').read_text(), 'native-and-wasm')
        def section(start, end):
            return old[old.index('      - name: '+start+'\n'):old.index('      - name: '+end+'\n')]
        expected = {
            'workspace': section('Run workspace CPU tests', 'Check appearance quality and production acceptance bridges'),
            'bridges': section('Check appearance quality and production acceptance bridges', 'Execute the actual B1 continuous motion matrix'),
        }
        matrix = section('Execute the actual B1 continuous motion matrix', 'Report existing command timing')
        for kind in ['required', 'background']:
            for part, body in expected.items():
                lane = job(workflow, f'mac-{part}-{kind}')
                self.assertEqual(lane.count(body), 1)
                self.assertIn('    runs-on: macos-15\n    timeout-minutes: 75\n', lane)
                self.assertIn("    if: ${{ needs.classify.outputs.full_required == '"+('true' if kind=='required' else 'false')+"' }}\n", lane)
                self.assertNotIn('continue-on-error', lane)
                self.assertNotIn('policy.py finish', lane)
                self.assertNotIn('actions/cache/', lane)
                for other, otherbody in expected.items():
                    if other != part:
                        self.assertNotIn(otherbody, lane)
                self.assertNotIn(matrix, lane)
                if part == 'workspace':
                    self.assertIn('Check actual Mac garment numerical witness', lane)
                    self.assertIn('mac_garment_witness.py', lane)
                    self.assertIn('test_controls.py', lane)
                    self.assertIn('python3 -B -O experiments/70-b1-garment-defect/test_controls.py', lane)
                    self.assertIn('timeout-minutes: 20', lane)
                else:
                    self.assertNotIn('mac_garment_witness.py', lane)
        self.assertIn('bash experiments/27-ci-baseline/check.sh native', expected['workspace'])
        self.assertIn('timeout-minutes: 12', expected['bridges'])
        self.assertIn('timeout-minutes: 20', matrix)
        for name in ('mac-matrix-required', 'mac-matrix-background'):
            self.assertNotIn('  '+name+':\n', workflow)
        linux = (HERE/'linux-shared.sh').read_text()
        self.assertIn('run_matrix.py', linux)
        self.assertIn('linux_garment_controls.py', linux)
        gate = job(workflow, 'required-gate')
        self.assertIn('mac-workspace-required, mac-bridges-required]', gate)
        self.assertNotIn('mac-matrix', gate)
        self.assertNotIn('mac-workspace-background', gate)
        report = job(workflow, 'full-mac-report')
        for kind in ['required', 'background']:
            for part in expected:
                self.assertIn('mac-'+part+'-'+kind, report)
        self.assertNotIn('mac-matrix', report)

    def test_linux_preserves_all_shared_commands_with_explicit_backend(self):
        old = job((HERE / 'predecessor-ci.yml').read_text(), 'native-and-wasm')
        linux = (HERE / 'linux-shared.sh').read_text()
        linux_entry = 'scripts/ci-tiering/linux_garment_controls.py'
        self.assertEqual(linux.count(linux_entry), 2)
        linux = linux.replace(linux_entry, 'experiments/70-b1-garment-defect/test_controls.py')
        # Every old Cargo command from workspace-probe/appearance/matrix blocks
        # remains, except the Mac native wrapper replaced by explicit same tests.
        start = old.index('      - name: Run workspace CPU tests')
        end = old.index('      - name: Report existing command timing', start)
        body = old[start:end]
        for line in body.splitlines():
            command = line.strip()
            if command.startswith(('cargo ', 'python3 -B experiments/60-', 'python3 -B experiments/70-', 'python3 -B -O experiments/70-')):
                self.assertIn(command, linux, command)
        self.assertIn('cargo test --workspace --locked --features nvwa-cli/motion-query,bevy/x11', linux)
        self.assertIn('cargo test -p nvwa-cli --features cpu-render,motion-query --test cpu_render --locked --offline -- --test-threads=1', linux)
        self.assertIn('"$(uname -s)" == Linux', linux)
        workflow = job((ROOT / '.github/workflows/ci.yml').read_text(), 'linux-shared')
        self.assertIn('timeout-minutes: 12', workflow)
        self.assertIn('timeout-minutes: 20', workflow)
        self.assertIn('--linux-backend --disposable-checkout', workflow)
        self.assertNotIn('continue-on-error', workflow)

    def test_linux_mutation_copy_preserves_original_source_gate_bytes(self):
        original = (ROOT/'scripts/check-b1-motion-mutations.py').read_text()
        self.assertEqual(hashlib.sha256(original.encode()).hexdigest(),
                         '0ce06d27b941aac799537376378ffd214d1384a571fcf8b1fe657e82846c9a31')
        linux = (HERE/'linux_mutations.py').read_text()
        linux = linux.replace('import platform\n', '', 1).replace('Path(__file__).resolve().parents[2]', 'Path(__file__).resolve().parents[1]', 1)
        for addition in [
            "    parser.add_argument('--linux-backend', action='store_true', help='Linux shared lane: explicitly enable its existing Bevy X11 backend')\n",
            "    if args.linux_backend and platform.system() != 'Linux':\n        raise ValueError('--linux-backend requires Linux')\n",
            "    if args.linux_backend:\n        command_prefix += ['--features', 'bevy/x11']\n",
        ]:
            self.assertEqual(linux.count(addition), 1)
            linux = linux.replace(addition, '', 1)
        self.assertEqual(linux, original)

    def test_smoke_has_real_binary_and_unsupported_claim_boundaries(self):
        text = (HERE / 'mac_smoke.py').read_text()
        for expected in ['subprocess.run', "run('new-character-waist'", "run('validate'", "run('save'", 'Darwin', 'arm64']:
            self.assertIn(expected, text)
        workflow = job((ROOT / '.github/workflows/ci.yml').read_text(), 'mac-smoke')
        self.assertIn('cargo check -p nvwa-studio --locked', workflow)
        self.assertIn('cargo build -p nvwa-cli --locked', workflow)
        self.assertNotIn('cache/', workflow)
        self.assertNotIn('continue-on-error', workflow)


# linux-garment-v2 begin
LINUX_GARMENT_HOST = "# Linux x86_64 has its own measured SSE2 witness; retain the native file unchanged.\n# See docs/agents/ci-tiering.md. This is not a tolerance or runtime math change.\nimport platform\n\n\ndef require_linux_host():\n    if platform.system() != 'Linux' or platform.machine() != 'x86_64':\n        raise SystemExit('Linux garment controls require actual Linux x86_64')\n\n\nrequire_linux_host()\nsys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'experiments/70-b1-garment-defect'))\n"


class LinuxGarmentContract(unittest.TestCase):
    def test_same_eighteen_controls_and_precision_with_explicit_platform_witness(self):
        original = (ROOT/'experiments/70-b1-garment-defect/test_controls.py').read_text()
        self.assertEqual(hashlib.sha256(original.encode()).hexdigest(),
                         '8cd854388f6f5d4411355217e21d97f38303693db2289cf6782e23e8040c728a')
        linux = (HERE/'linux_garment_controls.py').read_text()
        def retained(text):
            self.assertEqual(text.count(LINUX_GARMENT_HOST), 1)
            self.assertEqual(text.count('22.005667838827247'), 2)
            self.assertEqual(text.count('places=6'), 2)
            return text.replace(LINUX_GARMENT_HOST, '', 1).replace('22.005667838827247', '22.0056357384')
        self.assertEqual(retained(linux), original)
        self.assertEqual(len(re.findall(r'^    def test', linux, re.M)), 18)
        for old, replacement in [('places=6', 'places=5'), ('22.005667838827247', '22.0056'),
                                 ('p[0] += 0.01', 'p[0] += 0.00001'),
                                 ('with self.assertRaisesRegex', 'if False'),
                                 (LINUX_GARMENT_HOST, '')]:
            mutant = linux.replace(old, replacement, 1)
            self.assertNotEqual(mutant, linux)
            with self.subTest(mutation=old), self.assertRaises(AssertionError):
                self.assertEqual(retained(mutant), original)
        workflow = (ROOT/'.github/workflows/ci.yml').read_text()
        for name in ['native-and-wasm', 'mac-full-background']:
            body = job(workflow, name)
            self.assertEqual(body.count('experiments/70-b1-garment-defect/test_controls.py'), 2)
            self.assertNotIn('linux_garment_controls', body)

    def test_linux_guard_refuses_other_hosts_before_reading_any_frame(self):
        import ast
        import platform
        source = (HERE/'linux_garment_controls.py').read_text()
        tree = ast.parse(source)
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'require_linux_host')
        namespace = {'platform': platform}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), '<host guard>', 'exec'), namespace)
        for system, machine, accepted in [('Linux', 'x86_64', True), ('Linux', 'aarch64', False),
                                         ('Darwin', 'arm64', False), ('Darwin', 'x86_64', False),
                                         ('Windows', 'AMD64', False)]:
            with self.subTest(system=system, machine=machine), patch.object(platform, 'system', return_value=system), patch.object(platform, 'machine', return_value=machine):
                if accepted:
                    namespace['require_linux_host']()
                else:
                    with self.assertRaisesRegex(SystemExit, 'actual Linux x86_64'):
                        namespace['require_linux_host']()
        self.assertLess(source.index('require_linux_host()\nsys.path'), source.index('parser = argparse.ArgumentParser()'))
# linux-garment-v2 end

if __name__ == '__main__':
    unittest.main()
