"""Keep new observers before legacy retained-evidence generation changes bytes."""
import json
import os
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


class TimingOrder(unittest.TestCase):
    def test_real_catalog_groups_and_timing_report_preserve_one_source_identity(self):
        with tempfile.TemporaryDirectory(prefix='nvwa-cache-timing-order-') as directory:
            temporary = Path(directory).resolve()
            root = temporary / 'checkout'
            root.mkdir()
            tracked = subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', '-z']).decode().split('\0')
            copied = set()
            for relative in tracked:
                # Nested native-cache-contract runs nine original boundary
                # controls plus the new addition guard. Omit only this recursive regression.
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
                        if group['name'] in ['frozen-upper-arm', 'native-cache-contract']]
            self.assertEqual(set(selected), {'frozen-upper-arm', 'native-cache-contract'})
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
                    self.assertEqual(result.stderr.count('Ran 10 tests'), 2, result.stderr[-4000:])
                states.append({'group': group, 'status_after': git('status', '--porcelain')})
            self.assertEqual(git('diff', '--name-only'), GENERATED)
            self.assertTrue(states[-1]['status_after'], 'actual legacy generation must change its retained fixture')
            report = subprocess.run([*command, 'report'], cwd=root, env=environment,
                                    capture_output=True, text=True)
            self.assertEqual(report.returncode, 0, report.stdout+report.stderr+json.dumps(states))
            rows = [json.loads(path.read_text()) for path in records.glob('*.json')]
            self.assertEqual(len(rows), 2)
            self.assertEqual({row['source']['head'] for row in rows}, {head})
            self.assertEqual({row['source']['dirty'] for row in rows}, {False})
            self.assertEqual({row['binding']['GITHUB_RUN_ID'] for row in rows}, {'900001'})


if __name__ == '__main__':
    unittest.main(verbosity=2)
