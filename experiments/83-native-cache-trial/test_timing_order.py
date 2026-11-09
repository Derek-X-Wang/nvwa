"""Keep new observers before legacy retained-evidence generation changes bytes."""
from collections import Counter
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SELF = Path(__file__).resolve().relative_to(ROOT).as_posix()
GENERATED = 'experiments/50-upper-arm-neutral-ab/results/runtime-directions.json'
BINDING = ('GITHUB_WORKFLOW', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'GITHUB_JOB',
           'GITHUB_SHA', 'NVWA_CI_HEAD_SHA')


# Preserve the exact thirteen historical controls, not just their aggregate count.
# The two CI-tiering controls are additive and must also pass in both modes.
LEGACY_CACHE_TESTS = (
    'test_real_cli_same_source_pair_integrity_and_source_mtimes',
    'test_off_untrusted_main_and_adopted_never_enable_trial',
    'test_dirty_lock_source_wrong_target_nonempty_and_toolchain_fail_closed',
    'test_macos15_cannot_consume_old_image_trial_key',
    'test_receipts_cannot_convert_unavailable_or_warning_save_into_warm_hit',
    'test_actual_cli_cold_lookup_requires_unambiguous_repository_wide_absence',
    'test_all_semantic_reds_and_restored_greens_and_actual_matrix_required',
    'test_actual_retained_matrix_summary_and_strict_event_coverage_contract',
    'test_oversize_sparse_target_and_escaping_symlink_reject_before_save',
    'test_missing_or_duplicate_shoulder_step_rejects_existing_workflow_contract',
    'test_linux_b1_overlay_rejects_unapproved_policy_and_fetch_changes',
    'test_macos15_overlay_rejects_partial_mixed_and_unrelated_changes',
    'test_exact_original_workflow_and_full_warm_step_policy_parity',
)
TIERING_CACHE_TESTS = ('test_exact_predecessor_and_new_entrypoints',
                       'test_new_jobs_and_selectors_reject_changes')


def check_nested_cache_controls(checks, stderr):
    checks.assertEqual(len(set(LEGACY_CACHE_TESTS)), 13)
    expected = Counter({(name, 'CacheTrial'): 2 for name in LEGACY_CACHE_TESTS})
    expected.update({(name, 'TieringContract'): 2 for name in TIERING_CACHE_TESTS})
    observed = Counter(re.findall(
        r'^(test_\w+) \(test_cache_trial\.(\w+)\.\1\) \.\.\. ok$', stderr, re.M))
    checks.assertEqual(observed, expected, stderr[-4000:])
    checks.assertEqual(len(re.findall(r'^Ran 15 tests in [0-9.]+s$', stderr, re.M)), 2)


class TimingOrder(unittest.TestCase):
    def test_nested_cache_report_requires_every_original_and_added_control(self):
        rows = [f'{name} (test_cache_trial.{kind}.{name}) ... ok'
                for kind, names in [('CacheTrial', LEGACY_CACHE_TESTS),
                                    ('TieringContract', TIERING_CACHE_TESTS)]
                for name in names]
        report = '\n'.join(rows+['Ran 15 tests in 1.000s', 'OK', ''])*2
        check_nested_cache_controls(self, report)
        for row in rows:
            for replacement in ['', row.replace(' ... ok', ' ... FAIL'),
                                row.replace('test_', 'test_missing_', 1), row+'\n'+row]:
                with self.subTest(row=row, replacement=replacement), self.assertRaises(AssertionError):
                    check_nested_cache_controls(self, report.replace(row, replacement, 1))
        for mutant in [report.replace('Ran 15 tests', 'Ran 13 tests'),
                       report.split('OK')[0], report.replace('TieringContract', 'OtherContract')]:
            with self.assertRaises(AssertionError):
                check_nested_cache_controls(self, mutant)

    def test_real_catalog_groups_and_timing_report_preserve_one_source_identity(self):
        with tempfile.TemporaryDirectory(prefix='nvwa-cache-timing-order-') as directory:
            temporary = Path(directory).resolve()
            root = temporary / 'checkout'
            root.mkdir()
            tracked = subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', '-z']).decode().split('\0')
            copied = set()
            for relative in tracked:
                # Nested native-cache-contract runs nine original boundary
                # controls plus shoulder, Linux and Mac policy guards and image controls.
                # Omit only this recursive regression.
                if not relative or relative == SELF:
                    continue
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, destination)
                copied.add(relative)
            self.assertEqual(copied, set(filter(None, tracked)) - {SELF})
            self.assertFalse((root / SELF).exists(), 'only the recursive regression is omitted')
            # Controlled retained-output variation: the real legacy generator
            # rewrites this harmless whitespace. No production source is edited,
            # no math/gate is stubbed, and no Ubuntu byte difference is claimed.
            output = root / GENERATED
            output.write_bytes(output.read_bytes()+b'\n')
            def git(*args):
                return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()
            git('init', '-q')
            git('add', '.')
            git('-c', 'user.name=Control', '-c', 'user.email=control@example.invalid', 'commit', '-qm', 'owned timing fixture')
            head = git('rev-parse', 'HEAD')
            # This fixture deliberately has its own source/run identity. Its
            # nested production observers must never write to the enclosing CI
            # observer's directory or inherit its parent/source attribution.
            environment = {k:v for k,v in os.environ.items()
                           if not k.startswith('NVWA_TIMING_') and k not in BINDING
                           and k != 'GITHUB_STEP_SUMMARY'}
            runner = temporary / 'runner'
            runner.mkdir()
            records = temporary / 'records'
            environment.update(NVWA_TIMING_DIR=str(records), RUNNER_TEMP=str(runner),
                               GITHUB_WORKFLOW='Bounded CI', GITHUB_RUN_ID='900001',
                               GITHUB_RUN_ATTEMPT='1', GITHUB_JOB='portable',
                               GITHUB_SHA=head, NVWA_CI_HEAD_SHA=head)
            catalog = json.loads((root / 'scripts/portable-checks.json').read_text())
            selected = [group['name'] for group in catalog
                        if group['name'] in ['frozen-upper-arm', 'native-cache-contract', 'shoulder-rest-refit', 'current19-shoulder-refit']]
            self.assertEqual(set(selected), {'frozen-upper-arm', 'native-cache-contract', 'shoulder-rest-refit', 'current19-shoulder-refit'})
            self.assertLess(selected.index('shoulder-rest-refit'), selected.index('frozen-upper-arm'))
            self.assertLess(selected.index('shoulder-rest-refit'), selected.index('current19-shoulder-refit'))
            self.assertLess(selected.index('current19-shoulder-refit'), selected.index('frozen-upper-arm'))
            command = [sys.executable, '-B', *(['-O'] if sys.flags.optimize else []),
                       str(root / 'scripts/ci-timing.py')]
            states = []
            for group in selected:
                step = temporary / (group+'.sh')
                step.write_text('python3 -B scripts/check-portable.py '+group+'\n')
                result = subprocess.run([*command, 'shell', str(step)], cwd=root,
                                        env=environment, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout[-4000:]+result.stderr[-4000:])
                if group == 'native-cache-contract':
                    check_nested_cache_controls(self, result.stderr)
                states.append({'group': group, 'status_after': git('status', '--porcelain')})
            self.assertEqual(git('diff', '--name-only'), GENERATED)
            self.assertTrue(states[-1]['status_after'], 'actual legacy generation must change its retained fixture')
            report = subprocess.run([*command, 'report'], cwd=root, env=environment,
                                    capture_output=True, text=True)
            self.assertEqual(report.returncode, 0, report.stdout+report.stderr+json.dumps(states))
            rows = [json.loads(path.read_text()) for path in records.glob('*.json')]
            self.assertEqual(len([row for row in rows if row['tool']=='bash']), 4)
            self.assertEqual(len([row for row in rows if row['parent'] is None]), 4)
            self.assertGreaterEqual(len([row for row in rows if row['tool']=='cargo']), 3)
            self.assertEqual({row['source']['head'] for row in rows}, {head})
            self.assertEqual({row['source']['dirty'] for row in rows}, {False})
            self.assertEqual({row['binding']['GITHUB_RUN_ID'] for row in rows}, {'900001'})


if __name__ == '__main__':
    unittest.main(verbosity=2)
