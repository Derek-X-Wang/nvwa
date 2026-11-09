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
    needs['native-and-wasm'] = {'result': 'success' if full else 'skipped'}
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
    def test_valid_ordinary_does_not_depend_on_background(self):
        needs = complete_gate()
        for status in ['failure', 'cancelled', 'in_progress', 'missing']:
            needs['mac-full-background'] = {'result': status}
            self.assertEqual(policy.check_gate(needs), [])

    def test_report_rejects_missing_cancelled_and_double_execution(self):
        for results in [('success', 'skipped'), ('skipped', 'success'), ('success', 'success'),
                        ('skipped', 'skipped'), ('skipped', 'failure'), ('cancelled', 'skipped'),
                        ('missing', 'skipped')]:
            with self.subTest(results=results), tempfile.TemporaryDirectory() as d:
                needs = dict(zip(('native-and-wasm', 'mac-full-background'),
                                 ({'result': value} for value in results)))
                env = {**os.environ, 'TIER_NEEDS': json.dumps(needs), 'GITHUB_STEP_SUMMARY': d+'/summary'}
                r = subprocess.run([sys.executable, '-B', str(HERE/'policy.py'), 'report'], env=env, capture_output=True)
                self.assertEqual(r.returncode == 0, sorted(results) == ['skipped', 'success'])
                for value in results:
                    self.assertIn(value, Path(d+'/summary').read_text())

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
        for result in ['failure', 'cancelled', 'skipped', '', 'in_progress']:
            needs = complete_gate(True)
            needs['native-and-wasm']['result'] = result
            self.assertTrue(policy.check_gate(needs))
        for value in [None, 'TRUE', '', 'yes']:
            needs = complete_gate()
            needs['classify']['outputs']['full_required'] = value
            self.assertTrue(policy.check_gate(needs))


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
                     for i, (name, state) in enumerate(zip(self.namespace['NAMES'], ['skipped', 'success']))]
        self.assertNotIn('checkout', '\n'.join(line for line in workflow.splitlines() if not line.startswith('#')))
        self.assertNotIn('write', '\n'.join(line for line in workflow.splitlines() if line.strip().startswith(('actions:', 'contents:', 'pull-requests:', 'issues:'))))

    def test_identity_and_complete_paginated_inventory(self):
        event = {'repository': {'full_name': 'Derek-X-Wang/nvwa'}, 'workflow_run': self.run}
        self.assertEqual(self.namespace['identity'](event), self.run)
        for key, value in [('name', 'Other'), ('status', 'in_progress'), ('run_attempt', 0), ('head_sha', 'unknown')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.namespace['identity']({**event, 'workflow_run': {**self.run, key: value}})
        filler = [{**self.jobs[0], 'id': i+10, 'name': 'Other'} for i in range(100)]
        pages = [{'total_count': 102, 'jobs': filler}, {'total_count': 102, 'jobs': self.jobs}]
        urls = []
        def fetch(url):
            urls.append(url)
            return pages.pop(0)
        self.assertEqual(len(self.namespace['collect'](self.run, fetch)), 102)
        self.assertIn('/attempts/2/jobs?per_page=100&page=2', urls[1])
        for jobs in [self.jobs*2, [{**self.jobs[0], 'run_id': 7}], [{**self.jobs[0], 'head_sha': 'b'*40}]]:
            with self.assertRaises(ValueError):
                self.namespace['collect'](self.run, lambda url: {'total_count': len(jobs), 'jobs': jobs})
        with self.assertRaises(ValueError):
            self.namespace['collect'](self.run, lambda url: {'total_count': 3, 'jobs': []})

    def test_failures_cancellation_missing_and_double_success_remain_red(self):
        self.assertTrue(self.namespace['result'](self.jobs)[1])
        for state in ['cancelled', 'failure', 'timed_out', 'skipped', None]:
            self.assertFalse(self.namespace['result']([self.jobs[0], {**self.jobs[1], 'conclusion': state}])[1])
        self.assertFalse(self.namespace['result'](self.jobs[:1])[1])
        self.assertFalse(self.namespace['result'](self.jobs*2)[1])
        self.assertFalse(self.namespace['result']([{**j, 'conclusion': 'success'} for j in self.jobs])[1])


class WorkflowContract(unittest.TestCase):
    def test_original_full_mac_commands_and_budget_remain_exact(self):
        old = (HERE / 'predecessor-ci.yml').read_text()
        new = (ROOT / '.github/workflows/ci.yml').read_text()
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

    def test_linux_preserves_all_shared_commands_with_explicit_backend(self):
        old = job((HERE / 'predecessor-ci.yml').read_text(), 'native-and-wasm')
        linux = (HERE / 'linux-shared.sh').read_text()
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


if __name__ == '__main__':
    unittest.main()
