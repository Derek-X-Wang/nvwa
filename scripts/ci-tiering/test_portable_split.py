"""Execution and coverage contracts for the separately required portable group."""
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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location('portable_split_policy', HERE/'policy.py')
policy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(policy)


def job(workflow, name):
    matches = re.findall(r'(?ms)^  '+re.escape(name)+r':\n.*?(?=^  [a-z][a-z0-9-]*:\n|\Z)', workflow)
    if len(matches) != 1:
        raise ValueError('required unique job: '+name)
    return matches[0]


class PortableSplitControls(unittest.TestCase):
    def test_complete_catalog_once_with_original_intragroup_order(self):
        workflow = (ROOT/'.github/workflows/ci.yml').read_text()
        catalog = json.loads((ROOT/'scripts/portable-checks.json').read_text())
        names = [group['name'] for group in catalog]
        self.assertEqual(len(names), 16)
        groups = lambda body: re.findall(r'^        run: python3 -B scripts/check-portable.py (\S+)$', body, re.M)
        core, eye = job(workflow, 'portable'), job(workflow, 'portable-eye')
        self.assertEqual(groups(core), [name for name in names if name != 'eye-hair-parameters'])
        self.assertEqual(groups(eye), ['eye-hair-parameters'])
        self.assertCountEqual(groups(workflow), names)
        for body in [core, eye]:
            self.assertIn('    runs-on: ubuntu-24.04\n    timeout-minutes: 30\n', body)
            self.assertNotIn('continue-on-error', body)
            self.assertNotIn('    needs:', body)
        self.assertIn('        timeout-minutes: 20\n        run: python3 -B scripts/check-portable.py eye-hair-parameters\n', eye)
        # The split moves an entire Bash group; all twenty suite invocations and
        # Node's explicit failure boundary remain in the original catalog body.
        run = next(group['run'] for group in catalog if group['name'] == 'eye-hair-parameters')
        self.assertIn('node --version\n', run)
        self.assertIn('python3 -B -m unittest discover', run)
        self.assertIn('python3 -B -O -m unittest discover', run)

    def test_all_downstream_consumers_wait_for_both_groups(self):
        workflow = (ROOT/'.github/workflows/ci.yml').read_text()
        for name in ['native-and-wasm', 'mac-full-background']:
            self.assertIn('    needs: [classify, portable, portable-eye]\n', job(workflow, name))
        self.assertIn('    needs: [portable, portable-eye]\n', job(workflow, 'b1-source-regression'))
        required = ('classify', 'portable', 'portable-eye', 'linux-shared', 'mac-smoke', 'b1-source-regression')
        self.assertEqual(policy.REQUIRED, required)
        gate = job(workflow, 'required-gate')
        self.assertIn('    needs: ['+', '.join(required)+', mac-workspace-required, mac-bridges-required, mac-matrix-required]\n', gate)
        self.assertIn('    if: ${{ always() }}\n', gate)
        self.assertNotIn('continue-on-error', gate)

    def test_real_gate_process_rejects_each_incomplete_group(self):
        for full in ['true', 'false']:
            for lane in ['portable', 'portable-eye']:
                for result in ['success', 'failure', 'cancelled', 'skipped', 'in_progress', '', None]:
                    needs = {name: {'result': 'success'} for name in policy.REQUIRED}
                    needs['classify']['outputs'] = {'full_required': full}
                    for part in policy.MAC_PARTS:
                        needs[f'mac-{part}-required'] = {'result': 'success' if full == 'true' else 'skipped'}
                        needs[f'mac-{part}-background'] = {'result': 'skipped' if full == 'true' else 'success'}
                    if result is None:
                        del needs[lane]
                    else:
                        needs[lane]['result'] = result
                    with self.subTest(full=full, lane=lane, result=result):
                        env = {**os.environ, 'TIER_NEEDS': json.dumps(needs)}
                        call = subprocess.run([sys.executable, '-B', str(HERE/'policy.py'), 'gate'], env=env, capture_output=True, text=True)
                        self.assertEqual(call.returncode == 0, result == 'success', call.stdout+call.stderr)

    def test_isolated_group_missing_node_still_fails_before_tests(self):
        with tempfile.TemporaryDirectory(prefix='nvwa-eye-no-node-') as temporary:
            binary = Path(temporary)
            for name in ['git', 'bash', 'python3']:
                (binary/name).symlink_to(shutil.which(name))
            env = {**os.environ, 'PATH': str(binary)}
            env.pop('RUNNER_TEMP', None)
            call = subprocess.run([sys.executable, '-B', str(ROOT/'scripts/check-portable.py'), 'eye-hair-parameters'], env=env, capture_output=True, text=True)
            self.assertEqual(call.returncode, 127, call.stdout+call.stderr)
            self.assertIn('[eye-hair-parameters]', call.stdout)
            self.assertIn('node: command not found', call.stderr)
            self.assertNotRegex(call.stdout+call.stderr, r'Ran \d+ tests?')


if __name__ == '__main__':
    unittest.main(verbosity=2)
