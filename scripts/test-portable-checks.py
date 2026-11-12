"""Frozen extraction inventory and subprocess controls for the production runner."""
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from portable_catalog_v14 import UPPER_ARM_CHECKS, predecessor_bytes, predecessor_catalog

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "scripts/check-portable.py"
CHEEK_INPUT_CHECKS = (
    "python3 -B scripts/derive-cheek-volume.py\n"
    "python3 -B -O scripts/derive-cheek-volume.py\n"
    "python3 -B scripts/tests/test_derive_cheek_volume.py\n"
    "python3 -B -O scripts/tests/test_derive_cheek_volume.py\n"
)


def historical_input_catalog(catalog):
    """Verify the exact additive asset commands before the old body hashes."""
    selected = [group for group in catalog if group['name'] == 'b1-inputs']
    if len(selected) != 1 or not selected[0]['run'].endswith(CHEEK_INPUT_CHECKS):
        raise ValueError('required exact cheek input commands at end of b1-inputs')
    if selected[0]['run'].count(CHEEK_INPUT_CHECKS) != 1:
        raise ValueError('duplicate cheek input commands')
    return [dict(group, run=group['run'][:-len(CHEEK_INPUT_CHECKS)])
            if group['name'] == 'b1-inputs' else dict(group) for group in catalog]


CURRENT_CATALOG = json.loads((ROOT / "scripts/portable-checks.json").read_text())
PRE_UPPER_ARM_CATALOG = predecessor_catalog(CURRENT_CATALOG)
CATALOG = historical_input_catalog(PRE_UPPER_ARM_CATALOG)
# SHA-256 of the exact run bodies in the portable job at b03e7a345f01f6f6e940a19cf63906bff807e719.
# Keep this independent of the catalog: a removed mode, argument or command fails.
BASELINE = {
    "source-cli": "edff5938fe77c44a43c3d950055c6820ae1db009280e4afdcc5447a0d53c4529",
    "cli-distribution": "2df083091c4ed42b4641f713a24a07aaa2eecfb14b0444685fbc18f9ebe593eb",
    "b1-inputs": "3774edece15a3e06a63533dae7fd2fa8f269de4c26606ed8bdea23772a5da5f9",
    "motion-comparator": "42e4d257568e6ce317cedf0fb345cc3d64f1e1f85b48d800454be758a61b38dc",
    "diagnostics": "a01087665cb2997e7729228523aa5e50e6e1615a64d4bfb66097720429872dd4",
    "appearance": "6f0751d18b2abccf7467efaa1023f3d540de8e6c9b18d8baf999d492b419e6a9",
    "eye-hair-parameters": "886991f86aa4653e49130cb0e78a707cd9fa7de7c3f1353919f3280b0b4cf75d",
    "authenticated-source": "16ed8dcfd404a549882172394676d01ee0b7398c37e859105bbff3b83d8b3c84",
    "offline-motion": "a9d1e57a0f33194cb29498e09d1c088a2de4f32a579666eec4355793267050eb",
    "frozen-upper-arm": "1cdddaad8dcc99a78b91ca9c5369f14a6217eb7aa0d4f38255124dfe162cd0fd",
}


PORTABLE30_HEADER = """  portable:
    name: Core, CLI, and diagnostic controls
    runs-on: ubuntu-24.04
    timeout-minutes: 30
"""


# eye20: reverse only the exact named portable step before retained assertions.
EYE20_STEP = """      - name: Check eye, hair, and character parameter controls
        timeout-minutes: 20
        run: python3 -B scripts/check-portable.py eye-hair-parameters
"""


# ci-tiering-v1: this consumer independently verifies every additive lane before
# reversing only the approved topology edits. Original assertions below remain.
TIER_JOB_SHA256 = {'classify': 'b545979be6d56537b3f73eb75774c94c86c9c9d2ad0b09519762fdc66c968d34', 'mac-smoke': '29ffe1a4249b96d7ba7f143f6def594acb14fa4726c0bd984b9939d37b1b6989', 'linux-shared': '034f1b2fce7288f3b30aad9f8984a71c82dd35ed17e0bcdb49881512cc475f3a', 'required-gate': '50ed96092cabb707aaa06a72eb623cc2ba1b34d4b11e3ac98544a3ebb9958633', 'full-mac-report': '4e95b6ea70c091b988def140bb16dc36b8174d9b2ebc6155336812f50f313d23'}


TIER_INPUT_SHA256 = {'scripts/ci-tiering/policy.py': '8fe23dc381aca8eac8bf87aa7062aaa3c37199ff94f55e4016eadabd630360f7', 'scripts/ci-tiering/mac_smoke.py': '5ade91fa94ea313aebbfef793c4c2809c015a32da791efbfd40144062a6f3235', 'scripts/ci-tiering/linux-shared.sh': '94fd448e8e2018f4f9e70f1a9d8d5a759a771cd1ecd6c9cb7bf781ffc442ec88', 'scripts/ci-tiering/linux_mutations.py': 'bc4d945fa8c33e983fa5c2d3898651aebd9c8809871c97604fb119001cf4b19c', 'scripts/ci-tiering/test_policy.py': '085a6664172deb05efaef19eab912504e067b21fe59ff08ba72af4e76669a92f', '.github/workflows/ci-mac-report.yml': '5d35fadac433d125bbd8942d422dcb84d30ca37aab38429f2b7e5c1ff5257b7a'}


# linux-garment-v2: authenticate the exact upgrade before projecting v1 bytes.
LINUX_GARMENT_V2_SHA256 = {'scripts/ci-tiering/linux-shared.sh': '1450941e42b88c8c502da07759820e08baebf360b95230703d0757f099b6dc8a', 'scripts/ci-tiering/test_policy.py': '9a8d854d5ba7c2c223eac15b7a14ebe38b65e4ce7b08d5128de94bd195bcbc19', 'scripts/ci-tiering/linux_garment_controls.py': '14483090281c488d7fa6efc0fbf4823c873745c970b043957cc90a56761941e1'}
LINUX_GARMENT_NORMALIZE = b"        linux_entry = 'scripts/ci-tiering/linux_garment_controls.py'\n        self.assertEqual(linux.count(linux_entry), 2)\n        linux = linux.replace(linux_entry, 'experiments/70-b1-garment-defect/test_controls.py')\n"


# portable-split-v3: verify the new topology, then retain all older contracts.
PORTABLE_SPLIT_JOB_SHA256 = {'portable-eye': '0965819815391bac3e0911ecc5e0d85e5e200b2b1151bf9159356b1eb6734cfb', 'classify': '7c7209ae7649e37dcf7cfa28415978c60fe726d12a4f549729fce6419835dc0f'}
PORTABLE_SPLIT_INPUT_SHA256 = {'scripts/ci-tiering/policy.py': 'd9e3d8faaf48a45d2758e9de3159171f6c55f02434db1f27967515549ef4ae85', 'scripts/ci-tiering/test_policy.py': '464bb421984cbef27d76263a1a4e4b5d6b01c7c031f7ab99200f329189d124f2', 'scripts/ci-tiering/test_portable_split.py': '134e510608c6afe932aa085187102656b46911733abf75e2c478e16a6b51ed44'}
PORTABLE_SPLIT_NORMALIZE = b"        self.assertEqual(new.count('    needs: [classify, portable, portable-eye]\\n'), 2)\n        new = new.replace('    needs: [classify, portable, portable-eye]\\n', '    needs: [classify, portable]\\n')\n"


def historical_portable_split_input(name, checks, data):
    split_spec = importlib.util.spec_from_file_location('mac_split_contract', ROOT/'scripts/ci-tiering/mac_split_contract.py')
    split_module = importlib.util.module_from_spec(split_spec)
    split_spec.loader.exec_module(split_module)
    data = split_module.project_input(name, checks, data)
    if name in PORTABLE_SPLIT_INPUT_SHA256:
        checks.assertEqual(hashlib.sha256(data).hexdigest(), PORTABLE_SPLIT_INPUT_SHA256[name], name)
    if name == 'scripts/ci-tiering/policy.py':
        current = b"REQUIRED = ('classify', 'portable', 'portable-eye', 'linux-shared', 'mac-smoke', 'b1-source-regression')"
        checks.assertEqual(data.count(current), 1)
        data = data.replace(current, current.replace(b"'portable', 'portable-eye',", b"'portable',"), 1)
    if name == 'scripts/ci-tiering/test_policy.py':
        checks.assertEqual(data.count(PORTABLE_SPLIT_NORMALIZE), 1)
        data = data.replace(PORTABLE_SPLIT_NORMALIZE, b'', 1)
    return data


def historical_portable_split_workflow(workflow, checks):
    split_spec = importlib.util.spec_from_file_location('mac_split_contract', ROOT/'scripts/ci-tiering/mac_split_contract.py')
    split_module = importlib.util.module_from_spec(split_spec)
    split_spec.loader.exec_module(split_module)
    workflow = split_module.project(workflow, checks)
    def block(name):
        matches = re.findall(r'(?ms)^  '+re.escape(name)+r':\n.*?(?=^  [a-z][a-z0-9-]*:\n|\Z)', workflow)
        checks.assertEqual(len(matches), 1, 'required exactly one portable split job: '+name)
        return matches[0]
    for name, digest in PORTABLE_SPLIT_JOB_SHA256.items():
        checks.assertEqual(hashlib.sha256(block(name).encode()).hexdigest(), digest, name)
    # These are authenticated additions, not new values for historical hashes.
    for name in PORTABLE_SPLIT_INPUT_SHA256:
        historical_portable_split_input(name, checks, (ROOT/name).read_bytes())
    eye = block('portable-eye')
    checks.assertEqual(eye.count(EYE20_STEP), 1)
    core = block('portable')
    checks.assertTrue(core.startswith(PORTABLE30_HEADER), 'required original portable header')
    checks.assertNotIn('continue-on-error', core)
    checks.assertNotIn('eye-hair-parameters', core)
    following = '      - name: Check authenticated B1 source bundle and rejection controls\n'
    checks.assertEqual(core.count(following), 1)
    workflow = workflow.replace(core, core.replace(following, EYE20_STEP+following, 1), 1)
    workflow = workflow.replace(eye, '', 1)
    addition = ('          python3 -B scripts/ci-tiering/test_portable_split.py\n'
                '          python3 -B -O scripts/ci-tiering/test_portable_split.py\n')
    checks.assertEqual(workflow.count(addition), 1)
    workflow = workflow.replace(addition, '', 1)
    for name, current, previous in [
        ('native-and-wasm', '    needs: [classify, portable, portable-eye]\n', '    needs: [classify, portable]\n'),
        ('mac-full-background', '    needs: [classify, portable, portable-eye]\n', '    needs: [classify, portable]\n'),
        ('b1-source-regression', '    needs: [portable, portable-eye]\n', '    needs: portable\n'),
        ('required-gate', '    needs: [classify, portable, portable-eye, linux-shared, mac-smoke, b1-source-regression, native-and-wasm]\n',
         '    needs: [classify, portable, linux-shared, mac-smoke, b1-source-regression, native-and-wasm]\n')]:
        body = block(name)
        checks.assertEqual(body.count(current), 1, name+' must await both portable groups')
        workflow = workflow.replace(body, body.replace(current, previous, 1), 1)
    return workflow


def historical_tiering_input(name, checks, data=None):
    data = (ROOT/name).read_bytes() if data is None else data
    data = historical_portable_split_input(name, checks, data)
    if name in LINUX_GARMENT_V2_SHA256:
        checks.assertEqual(hashlib.sha256(data).hexdigest(), LINUX_GARMENT_V2_SHA256[name], name)
    if name == 'scripts/ci-tiering/linux-shared.sh':
        entry = b'scripts/ci-tiering/linux_garment_controls.py'
        checks.assertEqual(data.count(entry), 2)
        data = data.replace(entry, b'experiments/70-b1-garment-defect/test_controls.py')
    if name == 'scripts/ci-tiering/test_policy.py':
        blocks = re.findall(rb'(?ms)^# linux-garment-v2 begin\n.*?^# linux-garment-v2 end\n\n', data)
        checks.assertEqual(len(blocks), 1)
        checks.assertEqual(data.count(LINUX_GARMENT_NORMALIZE), 1)
        data = data.replace(blocks[0], b'', 1).replace(LINUX_GARMENT_NORMALIZE, b'', 1)
    return data


def historical_tiering_workflow(workflow, checks):
    workflow = historical_portable_split_workflow(workflow, checks)
    def block(name):
        matches = re.findall(r'(?ms)^  '+re.escape(name)+r':\n.*?(?=^  [a-z][a-z0-9-]*:\n|\Z)', workflow)
        checks.assertEqual(len(matches), 1, 'required exactly one tier job: '+name)
        return matches[0]
    for name, digest in TIER_JOB_SHA256.items():
        checks.assertEqual(hashlib.sha256(block(name).encode()).hexdigest(), digest,
                           'exact tier job contract: '+name)
    native = block('native-and-wasm')
    condition = "    needs: [classify, portable]\n    if: ${{ needs.classify.outputs.full_required == 'true' }}\n"
    checks.assertEqual(native.count(condition), 1, 'exact required Mac selector')
    background = block('mac-full-background')
    restored_background = background.replace('  mac-full-background:\n', '  native-and-wasm:\n', 1).replace(
        '    name: Complete Mac background evidence\n', '    name: macOS CPU tests and Wasm compile check\n', 1).replace(
        "    needs: [classify, portable]\n    if: ${{ needs.classify.outputs.full_required == 'false' }}\n", condition, 1)
    checks.assertEqual(restored_background, native, 'complete background must retain exact full native job')
    # Remove verified additions, preserving all original run bodies and order.
    for name in TIER_JOB_SHA256:
        workflow = workflow.replace(block(name), '', 1)
    workflow = workflow.replace(background, '', 1)
    workflow = workflow.replace(native, native.replace(condition, '    needs: portable\n', 1), 1)
    additions = [
        ('  workflow_dispatch:\n  release:\n    types: [published]\n', ''),
        ("    tags: ['*']\n", ''),
        ('# Existing complete-Mac main-only cache policy is retained; PRs stay cold.\n', '# No cache restore/save steps; no cache token overrides.\n'),
    ]
    for current, previous in additions:
        checks.assertEqual(workflow.count(current), 1, 'exact tier trigger/comment addition')
        workflow = workflow.replace(current, previous, 1)
    checks.assertTrue(workflow.endswith('  # native-cache-trial end\n\n'), 'exact tier tail separator')
    return workflow[:-1]


def historical_eye_budget_workflow(workflow, checks):
    workflow = historical_tiering_workflow(workflow, checks)
    jobs = {}
    for name, cap in [('portable', '30'), ('native-and-wasm', '75'),
                      ('b1-source-regression', '60'), ('native-cache-warm', '60')]:
        blocks = re.findall(r'(?ms)^  '+name+r':\n.*?(?=^  [a-z][a-z0-9-]*:\n|\Z)', workflow)
        checks.assertEqual(len(blocks), 1, 'required one '+name+' job')
        checks.assertEqual(re.findall(r'^    timeout-minutes:.*$', blocks[0], re.M),
                           ['    timeout-minutes: '+cap], 'required unchanged '+name+' cap')
        jobs[name] = blocks[0]
    portable = jobs['portable']
    checks.assertTrue(portable.startswith(PORTABLE30_HEADER), 'required exact portable job header')
    checks.assertEqual(workflow.count(EYE20_STEP.splitlines(keepends=True)[0]), 1,
                       'required one named eye/hair step')
    checks.assertEqual(portable.count(EYE20_STEP), 1, 'required exact eye/hair 20-minute step')
    preceding = ('      - name: Check bounded appearance diagnostic controls\n'
                 '        run: python3 -B scripts/check-portable.py appearance\n')
    following = ('      - name: Check authenticated B1 source bundle and rejection controls\n'
                 '        timeout-minutes: 3\n'
                 '        run: python3 -B scripts/check-portable.py authenticated-source\n')
    checks.assertIn(preceding+EYE20_STEP+following, portable, 'required eye/hair step position')
    for name, cap, group in [
            ('Check authenticated B1 source bundle and rejection controls', '3', 'authenticated-source'),
            ('Prepare locked importer dependencies and check offline motion controls', '6', 'offline-motion'),
            ('Check frozen upper-arm comparison and retained runtime captures', '5', 'frozen-upper-arm')]:
        step = '      - name: '+name+'\n        timeout-minutes: '+cap+'\n'
        step += '        run: python3 -B scripts/check-portable.py '+group+'\n'
        checks.assertEqual(portable.count(step), 1, 'required unchanged '+group+' step')
    restored = portable.replace(EYE20_STEP, EYE20_STEP.replace('timeout-minutes: 20', 'timeout-minutes: 3'), 1)
    return workflow.replace(portable, restored, 1)


class PortableChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="nvwa-check-runner-test-")
        self.addCleanup(self.temporary.cleanup)
        self.temp = Path(self.temporary.name).resolve()
        self.bin = self.temp / "bin"
        self.bin.mkdir()
        self.log = self.temp / "commands.log"
        self.env = os.environ.copy()
        for name in ["RUNNER_TEMP", "CARGO_TERM_COLOR", "CARGO_INCREMENTAL",
                     "CARGO_PROFILE_DEV_DEBUG", "CARGO_PROFILE_TEST_DEBUG", "CARGO_BUILD_JOBS"]:
            self.env.pop(name, None)
        self.env.update(PATH=str(self.bin), CHECK_LOG=str(self.log))
        (self.bin / "git").symlink_to(shutil.which("git"))
        # These replace external command boundaries, not the runner or its shell.
        # The production runner reads the real catalog and executes real Bash loops.
        shim = '''#!/bin/bash
tool=${0##*/}
if [[ "$tool" == bash && "$1" == --noprofile ]]; then exec /bin/bash "$@"; fi
printf '%s|%s|%s|%s|%s|%s|%s|%s|%s\\n' "$tool" "$*" "$PWD" "$RUNNER_TEMP" "$CARGO_BUILD_JOBS" "$CARGO_INCREMENTAL" "$CARGO_PROFILE_DEV_DEBUG" "$CARGO_PROFILE_TEST_DEBUG" "$CARGO_TERM_COLOR" >> "$CHECK_LOG"
if [[ "$tool" == "${FAIL_TOOL:-}" && "$*" == *"${FAIL_MATCH:-}"* ]]; then exit 79; fi
'''
        for name in ["bash", "cargo", "python3", "node", "mkdir"]:
            path = self.bin / name
            path.write_text(shim)
            path.chmod(0o755)

    def call(self, *groups, cwd=None, runner=RUNNER):
        return subprocess.run([sys.executable, "-B", str(runner), *groups],
                              cwd=cwd or ROOT, env=self.env, capture_output=True, text=True)

    def records(self):
        return [line.split("|") for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_portable30_exact_budget_rejects_stale_types_and_other_jobs(self):
        original = (ROOT / '.github/workflows/ci.yml').read_text()
        historical_eye_budget_workflow(original, self)
        for cap in ['25', '29', '31', '30.0', '"30"', "'30'", '${{ 30 }}', 'true']:
            mutant = original.replace(PORTABLE30_HEADER, PORTABLE30_HEADER.replace(
                '    timeout-minutes: 30\n', '    timeout-minutes: '+cap+'\n'))
            self.assertNotEqual(mutant, original)
            with self.subTest(portable_cap=cap), self.assertRaises(AssertionError):
                historical_eye_budget_workflow(mutant, self)
        for name, cap in [('native-and-wasm', '75'), ('b1-source-regression', '60'),
                          ('native-cache-warm', '60')]:
            block = re.search(r'(?ms)^  '+name+r':\n.*?(?=^  [a-z][a-z0-9-]*:\n|\Z)', original).group()
            mutant = original.replace(block, block.replace(
                '    timeout-minutes: '+cap+'\n', '    timeout-minutes: 30\n', 1), 1)
            self.assertNotEqual(mutant, original)
            with self.subTest(wrong_job=name), self.assertRaises(AssertionError):
                historical_eye_budget_workflow(mutant, self)
        mutant = original.replace(EYE20_STEP, EYE20_STEP.replace(
            '        timeout-minutes: 20\n', '        timeout-minutes: 30\n'))
        self.assertNotEqual(mutant, original)
        with self.assertRaises(AssertionError):
            historical_eye_budget_workflow(mutant, self)

    def test_cheek_asset_checks_are_additive_and_run_in_both_modes(self):
        result = self.call('b1-inputs')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([row[:2] for row in self.records()][-6:-2], [
            ['python3', '-B scripts/derive-cheek-volume.py'],
            ['python3', '-B -O scripts/derive-cheek-volume.py'],
            ['python3', '-B scripts/tests/test_derive_cheek_volume.py'],
            ['python3', '-B -O scripts/tests/test_derive_cheek_volume.py'],
        ])
        self.assertEqual(len(self.records()), 10)
        for group in PRE_UPPER_ARM_CATALOG:
            if group['name'] == 'b1-inputs':
                old = next(item for item in CATALOG if item['name'] == 'b1-inputs')
                self.assertEqual(group['run'], old['run'] + CHEEK_INPUT_CHECKS)

    def test_cheek_asset_command_mutations_reject_and_failures_propagate(self):
        for old, new in [('-B -O scripts/derive', '-B scripts/derive'),
                         ('scripts/tests/test_derive_cheek_volume.py', 'scripts/tests/other.py'),
                         (CHEEK_INPUT_CHECKS, ''),
                         (CHEEK_INPUT_CHECKS, CHEEK_INPUT_CHECKS * 2)]:
            changed = [dict(group, run=group['run'].replace(old, new)) for group in PRE_UPPER_ARM_CATALOG]
            with self.subTest(mutation=(old, new)), self.assertRaises(ValueError):
                historical_input_catalog(changed)
        self.env.update(FAIL_TOOL='python3', FAIL_MATCH='scripts/derive-cheek-volume.py')
        result = self.call('b1-inputs', 'motion-comparator')
        self.assertEqual(result.returncode, 79, result.stderr)
        self.assertEqual(len(self.records()), 5)
        self.assertEqual(self.records()[-1][:2], ['python3', '-B scripts/derive-cheek-volume.py'])

    def test_upper_arm_asset_checks_are_additive_in_both_modes_and_fail_closed(self):
        result = self.call('b1-inputs')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([row[:2] for row in self.records()][-2:], [
            ['python3', '-B scripts/test-upper-arm-muscle-v14.py'],
            ['python3', '-B -O scripts/test-upper-arm-muscle-v14.py'],
        ])
        original = (ROOT / 'scripts/portable-checks.json').read_bytes()
        self.assertEqual(hashlib.sha256(predecessor_bytes(original)).hexdigest(),
                         '1a2719b28dad9a288f28e0ff5ba793120e6108217c564099d662fc1b104d7f14')
        for old, new in [(UPPER_ARM_CHECKS, ''),
                         (UPPER_ARM_CHECKS, UPPER_ARM_CHECKS * 2),
                         ('-B -O scripts/test-upper-arm-muscle-v14.py', '-B scripts/test-upper-arm-muscle-v14.py'),
                         ('test-upper-arm-muscle-v14.py', 'other-script.py')]:
            changed = [dict(group, run=group['run'].replace(old, new)) for group in CURRENT_CATALOG]
            with self.subTest(mutation=(old, new)), self.assertRaises(ValueError):
                predecessor_catalog(changed)
        self.log.unlink()
        self.env.update(FAIL_TOOL='python3', FAIL_MATCH='scripts/test-upper-arm-muscle-v14.py')
        result = self.call('b1-inputs', 'motion-comparator')
        self.assertEqual(result.returncode, 79, result.stderr)
        self.assertEqual(len(self.records()), 9)
        self.assertEqual(self.records()[-1][:2], ['python3', '-B scripts/test-upper-arm-muscle-v14.py'])

    def test_exact_original_command_inventory_and_order(self):
        self.assertEqual([group["name"] for group in CATALOG], ["runner-contract", "ci-timing-contract", *list(BASELINE)[:-1], "native-cache-contract", "native-main-cache-contract", "shoulder-rest-refit", "current19-shoulder-refit", "frozen-upper-arm"])
        self.assertEqual(CATALOG[0]["run"], "python3 -B scripts/test-portable-checks.py\npython3 -B -O scripts/test-portable-checks.py\n")
        self.assertEqual(CATALOG[1]["run"], "python3 -B scripts/test-ci-timing.py\npython3 -B -O scripts/test-ci-timing.py\n")
        self.assertEqual(CATALOG[-5]["run"],
                         "python3 -B -m unittest discover -s experiments/83-native-cache-trial -p 'test_*.py' -v\n"
                         "python3 -B -O -m unittest discover -s experiments/83-native-cache-trial -p 'test_*.py' -v\n")
        self.assertEqual(CATALOG[-4]["run"], "python3 -B experiments/83-native-cache-trial/main_policy/test_policy.py\npython3 -B -O experiments/83-native-cache-trial/main_policy/test_policy.py\n")
        for group in [*CATALOG[2:-5], CATALOG[-1]]:
            self.assertEqual(hashlib.sha256(group["run"].encode()).hexdigest(), BASELINE[group["name"]])

    def test_rest_refit_controls_retain_both_modes(self):
        self.assertEqual(CATALOG[-3]["run"], 'cargo fmt --manifest-path experiments/84-shoulder-rest-refit/replay/Cargo.toml --package nvwa-shoulder-rest-replay --check\ncargo fmt --manifest-path experiments/84-shoulder-rest-refit/wasm-replay/Cargo.toml --package nvwa-shoulder-wasm-replay --check\nfor part in replay evaluation authoring wasm-replay; do\n  python3 -B -m unittest discover -s "experiments/84-shoulder-rest-refit/$part" -p \'test_*.py\' -v\n  python3 -B -O -m unittest discover -s "experiments/84-shoulder-rest-refit/$part" -p \'test_*.py\' -v\ndone\n')

    def test_current19_controls_retain_exact_commands_and_both_modes(self):
        self.assertEqual(CATALOG[-2]["run"], "cargo fmt --manifest-path experiments/85-current19-shoulder-refit/replay/Cargo.toml --package nvwa-current19-replay --check\npython3 -B -m unittest discover -s experiments/85-current19-shoulder-refit -p 'test_*.py' -v\npython3 -B -O -m unittest discover -s experiments/85-current19-shoulder-refit -p 'test_*.py' -v\n")

    def test_workflow_uses_every_group_once_and_preserves_timeouts(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        original = workflow
        workflow = historical_eye_budget_workflow(workflow, self)
        # The current cap was checked above. Restore only that job header before
        # retained prefix-count assertions, where "3" would otherwise include30.
        workflow = workflow.replace(PORTABLE30_HEADER, PORTABLE30_HEADER.replace(
            '    timeout-minutes: 30\n', '    timeout-minutes: 25\n'), 1)
        portable = workflow.split("  portable:\n", 1)[1].split("  native-and-wasm:\n", 1)[0]
        calls = [line.strip().removeprefix("run: ") for line in portable.splitlines()
                 if "python3 -B scripts/check-portable.py " in line]
        self.assertEqual(calls, [f"python3 -B scripts/check-portable.py {name}" for name in ["runner-contract", "ci-timing-contract", *list(BASELINE)[:-1], "native-cache-contract", "native-main-cache-contract", "shoulder-rest-refit", "current19-shoulder-refit", "frozen-upper-arm"]])
        self.assertEqual(portable.count("timeout-minutes: 3"), 2)
        self.assertIn("timeout-minutes: 6", portable)
        self.assertIn("timeout-minutes: 5", portable)
        self.assertIn("python3 -B scripts/check-portable.py runner-contract", portable)

        eye_mutations = []
        for cap in ['3', '4', '6', '0', '-1', '5.0', '"5"', "'5'", '${{ 5 }}',
                    '5', '8.0', '"8"', "'8'", '${{ 8 }}',
                    '8', '10.0', '"10"', "'10'", '${{ 10 }}',
                    '10', '20.0', '"20"', "'20'", '${{ 20 }}']:
            eye_mutations.append(('eye-cap-'+cap, original.replace(EYE20_STEP, EYE20_STEP.replace(
                '        timeout-minutes: 20\n', '        timeout-minutes: '+cap+'\n'))))
        eye_mutations.extend([
            ('missing-eye-step', original.replace(EYE20_STEP, '')),
            ('duplicate-eye-step', original.replace(EYE20_STEP, EYE20_STEP*2)),
            ('renamed-eye-step', original.replace(EYE20_STEP, EYE20_STEP.replace('Check eye, hair, and character parameter controls', 'Other controls'))),
            ('missing-eye-cap', original.replace(EYE20_STEP, EYE20_STEP.replace('        timeout-minutes: 20\n', ''))),
            ('duplicate-eye-cap', original.replace(EYE20_STEP, EYE20_STEP.replace('        timeout-minutes: 20\n', '        timeout-minutes: 20\n'*2))),
            ('misplaced-eye-cap', original.replace(EYE20_STEP, EYE20_STEP.replace('        timeout-minutes: 20\n', '    timeout-minutes: 20\n'))),
            ('wrong-eye-run', original.replace(EYE20_STEP, EYE20_STEP.replace('eye-hair-parameters\n', 'appearance\n'))),
            ('changed-eye-run-mode', original.replace(EYE20_STEP, EYE20_STEP.replace('python3 -B ', 'python3 -B -O '))),
            ('changed-step-order', original.replace(EYE20_STEP, '').replace('      - name: Check bounded appearance diagnostic controls\n', EYE20_STEP+'      - name: Check bounded appearance diagnostic controls\n')),
            ('eye-moved-to-native', original.replace(EYE20_STEP, '').replace('  native-and-wasm:\n', '  native-and-wasm:\n'+EYE20_STEP)),
            ('duplicate-portable-job', original.replace(PORTABLE30_HEADER, PORTABLE30_HEADER*2)),
            ('portable-cap', original.replace(PORTABLE30_HEADER, PORTABLE30_HEADER.replace('timeout-minutes: 30', 'timeout-minutes: 20'))),
        ])
        for cap in ['15', '19', '21', '0', '-1', '20.0', '"20"',
                    '24', '26', '25.0', '"25"', "'25'", '${{ 25 }}']:
            eye_mutations.append(('portable-cap-'+cap, original.replace(
                PORTABLE30_HEADER, PORTABLE30_HEADER.replace(
                    'timeout-minutes: 30', 'timeout-minutes: '+cap))))
        for name, old, new in [
                ('authenticated-source', '        timeout-minutes: 3\n        run: python3 -B scripts/check-portable.py authenticated-source\n', '5'),
                ('offline-motion', '        timeout-minutes: 6\n        run: python3 -B scripts/check-portable.py offline-motion\n', '5'),
                ('frozen-upper-arm', '        timeout-minutes: 5\n        run: python3 -B scripts/check-portable.py frozen-upper-arm\n', '6')]:
            changed = old.replace(old.splitlines()[0], '        timeout-minutes: '+new, 1)
            eye_mutations.append(('other-step-'+name, original.replace(old, changed)))
        eye_mutations.append(('five-moved-to-authenticated-source', original.replace(
            EYE20_STEP, EYE20_STEP.replace('timeout-minutes: 20', 'timeout-minutes: 3')).replace(
                'timeout-minutes: 3\n        run: python3 -B scripts/check-portable.py authenticated-source',
                'timeout-minutes: 5\n        run: python3 -B scripts/check-portable.py authenticated-source')))
        eye_mutations.append(('eight-moved-to-authenticated-source', original.replace(
            EYE20_STEP, EYE20_STEP.replace('timeout-minutes: 20', 'timeout-minutes: 3')).replace(
                'timeout-minutes: 3\n        run: python3 -B scripts/check-portable.py authenticated-source',
                'timeout-minutes: 8\n        run: python3 -B scripts/check-portable.py authenticated-source')))
        eye_mutations.append(('ten-moved-to-authenticated-source', original.replace(
            EYE20_STEP, EYE20_STEP.replace('timeout-minutes: 20', 'timeout-minutes: 3')).replace(
                'timeout-minutes: 3\n        run: python3 -B scripts/check-portable.py authenticated-source',
                'timeout-minutes: 10\n        run: python3 -B scripts/check-portable.py authenticated-source')))
        eye_mutations.append(('twenty-moved-to-authenticated-source', original.replace(
            EYE20_STEP, EYE20_STEP.replace('timeout-minutes: 20', 'timeout-minutes: 3')).replace(
                'timeout-minutes: 3\n        run: python3 -B scripts/check-portable.py authenticated-source',
                'timeout-minutes: 20\n        run: python3 -B scripts/check-portable.py authenticated-source')))
        for name, old, new in [('native-and-wasm', '75', '76'), ('b1-source-regression', '60', '61'), ('native-cache-warm', '60', '61')]:
            job = re.search(r'(?ms)^  '+name+r':\n.*?(?=^  [a-z][a-z0-9-]*:\n|\Z)', original).group()
            eye_mutations.append(('other-job-'+name, original.replace(job, job.replace(
                '    timeout-minutes: '+old+'\n', '    timeout-minutes: '+new+'\n', 1))))
        for name, mutant in eye_mutations:
            self.assertNotEqual(mutant, original, name)
            with self.subTest(mutation=name), self.assertRaises(AssertionError):
                historical_eye_budget_workflow(mutant, self)

    def test_all_real_shell_groups_order_modes_defaults_and_local_temp_cleanup(self):
        result = self.call("all")
        self.assertEqual(result.returncode, 0, result.stderr)
        headings = [line.split("]", 1)[0][1:] for line in result.stdout.splitlines() if line.startswith("[")]
        self.assertEqual(headings, ["runner-contract", "ci-timing-contract", *list(BASELINE)[:-1], "native-cache-contract", "native-main-cache-contract", "shoulder-rest-refit", "current19-shoulder-refit", "frozen-upper-arm"])
        records = self.records()
        self.assertEqual(records[0][:2], ["python3", "-B scripts/test-portable-checks.py"])
        self.assertEqual(records[1][:2], ["python3", "-B -O scripts/test-portable-checks.py"])
        self.assertEqual(records[4][:2], ["bash", "experiments/27-ci-baseline/check.sh portable"])
        self.assertEqual(records[5][:2], ["cargo", "build -p nvwa-cli --locked --offline"])
        self.assertTrue(all(row[2] == str(ROOT) for row in records))
        self.assertEqual({tuple(row[4:]) for row in records}, {("2", "0", "0", "0", "always")})
        temps = {row[3] for row in records}
        self.assertEqual(len(temps), 1)
        self.assertFalse(Path(temps.pop()).exists())
        for experiment in ["72-b1-admission-controls", "73-high-poly-eyes"]:
            for mode in ["-B", "-B -O"]:
                command = f"{mode} -m unittest discover -s experiments/{experiment} -p test_*.py -v"
                self.assertIn(["python3", command], [row[:2] for row in records])

    def test_selection_uses_catalog_order_and_preserves_inherited_environment_and_temp(self):
        self.env.update(RUNNER_TEMP=str(self.temp), CARGO_BUILD_JOBS="7")
        result = self.call("diagnostics", "cli-distribution", "diagnostics")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([row[0] for row in self.records()], ["cargo", "python3", "python3", "bash"])
        self.assertTrue(all(row[3:5] == [str(self.temp), "7"] for row in self.records()))
        self.assertTrue(self.temp.is_dir())

    def test_fresh_temp_uses_physical_path_through_symlinked_tmpdir_and_cleans_only_itself(self):
        parent = self.temp / "physical-parent"
        parent.mkdir()
        alias = self.temp / "logical-parent"
        alias.symlink_to(parent, target_is_directory=True)
        self.env["TMPDIR"] = str(alias)
        result = self.call("diagnostics")
        self.assertEqual(result.returncode, 0, result.stderr)
        temporary = Path(self.records()[0][3])
        self.assertEqual(temporary.parent, parent)
        self.assertEqual(temporary, temporary.resolve())
        self.assertFalse(temporary.exists())
        self.assertTrue(parent.is_dir())
        self.assertTrue(alias.is_symlink())
        self.assertEqual(alias.resolve(), parent)
        self.assertEqual(list(parent.iterdir()), [])

    def test_inherited_temp_with_symlink_is_preserved_verbatim(self):
        parent = self.temp / "physical-parent"
        parent.mkdir()
        alias = self.temp / "logical-parent"
        alias.symlink_to(parent, target_is_directory=True)
        self.env["RUNNER_TEMP"] = str(alias)
        result = self.call("diagnostics")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.records()[0][3], str(alias))
        self.assertTrue(parent.is_dir())
        self.assertTrue(alias.is_symlink())

    def test_unknown_group_fails_before_any_command(self):
        for groups in [("typo",), (), ("all", "diagnostics")]:
            result = self.call(*groups)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertFalse(self.log.exists())

    def test_failure_stops_group_and_later_groups_with_original_status(self):
        self.env.update(FAIL_TOOL="python3", FAIL_MATCH="scripts/test-cli-package.py")
        result = self.call("cli-distribution", "b1-inputs")
        self.assertEqual(result.returncode, 79, result.stderr)
        self.assertEqual(len(self.records()), 2)
        self.assertNotIn("-O", self.records()[-1][1])

    def test_missing_node_and_python_are_errors_never_skipped(self):
        for tool in ["node", "python3"]:
            with self.subTest(tool=tool):
                original = (self.bin / tool).read_text()
                (self.bin / tool).unlink()
                if self.log.exists():
                    self.log.unlink()
                result = self.call("eye-hair-parameters")
                self.assertEqual(result.returncode, 127, result.stderr)
                self.assertIn(f"{tool}: command not found", result.stderr)
                self.assertEqual(len(self.records()), 0 if tool == "node" else 1)
                (self.bin / tool).write_text(original)
                (self.bin / tool).chmod(0o755)

    def test_missing_bash_fails(self):
        (self.bin / "bash").unlink()
        result = self.call("diagnostics")
        self.assertEqual(result.returncode, 1)
        self.assertIn("bash", result.stderr)

    def test_nested_and_outside_invocation_use_script_checkout(self):
        for cwd in [ROOT / "scripts", self.temp]:
            result = self.call("diagnostics", cwd=cwd)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"Invocation cwd: {cwd}", result.stdout)
            self.assertIn(f"checkout={ROOT}", result.stdout)
            self.assertEqual(self.records()[-1][2], str(ROOT))

    def test_detached_clean_and_dirty_identity_without_changing_checkout(self):
        repo = self.temp / "fixture"
        (repo / "scripts").mkdir(parents=True)
        for name in ["check-portable.py", "portable-checks.json"]:
            shutil.copy2(ROOT / "scripts" / name, repo / "scripts" / name)
        def git(*args):
            return subprocess.check_output([shutil.which("git"), "-C", str(repo), *args], text=True).strip()
        git("init", "-q")
        git("add", ".")
        git("-c", "user.name=Runner test", "-c", "user.email=runner@example.invalid",
            "-c", "commit.gpgsign=false", "commit", "-qm", "fixture")
        git("checkout", "--detach", "-q")
        head = git("rev-parse", "HEAD")
        for dirty in [False, True]:
            if dirty:
                (repo / "untracked").write_text("control")
            result = self.call("diagnostics", cwd=self.temp, runner=repo / "scripts/check-portable.py")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"HEAD: {head}; branch: (detached); dirty: {'yes' if dirty else 'no'}", result.stdout)
            self.assertEqual(git("rev-parse", "HEAD"), head)
            self.assertEqual(self.records()[-1][2], str(repo))

    def test_runner_outside_git_checkout_fails_before_commands(self):
        scripts = self.temp / "scripts"
        scripts.mkdir()
        for name in ["check-portable.py", "portable-checks.json"]:
            shutil.copy2(ROOT / "scripts" / name, scripts / name)
        result = self.call("diagnostics", runner=scripts / "check-portable.py")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.log.exists())

    def test_invalid_catalog_cannot_turn_all_into_a_green_noop(self):
        repo = self.temp / "fixture"
        scripts = repo / "scripts"
        scripts.mkdir(parents=True)
        shutil.copy2(RUNNER, scripts / RUNNER.name)
        valid = {"name": "control", "title": "Control", "run": "node --version\n"}
        (scripts / "portable-checks.json").write_text(json.dumps([valid]))
        def git(*args):
            subprocess.run([shutil.which("git"), "-C", str(repo), *args], check=True)
        git("init", "-q")
        git("add", ".")
        git("-c", "user.name=Runner test", "-c", "user.email=runner@example.invalid",
            "-c", "commit.gpgsign=false", "commit", "-qm", "fixture")
        # Prove this copied runner and checkout actually pass before mutations.
        result = self.call("all", runner=scripts / RUNNER.name)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.records()[0][0], "node")
        self.log.unlink()
        invalid = ["{", "[]", "{}", "null", json.dumps([valid, valid])]
        for field in ["name", "title", "run"]:
            for value in ["", "  ", None, 1]:
                invalid.append(json.dumps([{**valid, field: value}]))
            invalid.append(json.dumps([{key: value for key, value in valid.items() if key != field}]))
        for catalog in invalid:
            with self.subTest(catalog=catalog):
                (scripts / "portable-checks.json").write_text(catalog)
                result = self.call("all", runner=scripts / RUNNER.name)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn("FAIL:", result.stderr)
                self.assertFalse(self.log.exists())



class TieringContract(unittest.TestCase):
    def test_exact_predecessor_and_new_entrypoints(self):
        split_source = (ROOT/'.github/workflows/ci.yml').read_text()
        self.assertEqual(hashlib.sha256(historical_portable_split_workflow(split_source, self).encode()).hexdigest(),
                         'cc3fb61238de685a84562122914dee10ec854112a2f810fa92339dff531d0196',
                         'exact a7773e9 workflow after portable split projection')
        predecessor = (ROOT/'scripts/ci-tiering/predecessor-ci.yml').read_bytes()
        self.assertEqual(hashlib.sha256(predecessor).hexdigest(), '4f9213643d24c3e67e3f059fbb28f8563531d37999834982f9b3e5c549c2fb4f')
        current = (ROOT/'.github/workflows/ci.yml').read_text()
        self.assertEqual(historical_tiering_workflow(current, self), predecessor.decode())
        self.assertEqual(len(re.findall(r'^        run: ', predecessor.decode(), re.M)), 48)
        self.assertEqual(hashlib.sha256(predecessor_bytes((ROOT/'scripts/portable-checks.json').read_bytes())).hexdigest(), '1a2719b28dad9a288f28e0ff5ba793120e6108217c564099d662fc1b104d7f14')
        for name, digest in TIER_INPUT_SHA256.items():
            self.assertEqual(hashlib.sha256(historical_tiering_input(name, self)).hexdigest(), digest, name)
        for name in LINUX_GARMENT_V2_SHA256:
            historical_tiering_input(name, self)
        # Exact v2 validation must reject altered or removed controls before projection.
        for name, old, new in [
                ('scripts/ci-tiering/linux-shared.sh', b'python3 -B -O ', b'python3 -B '),
                ('scripts/ci-tiering/linux_garment_controls.py', b'places=6', b'places=5'),
                ('scripts/ci-tiering/linux_garment_controls.py', b'22.005667838827247', b'22.0056'),
                ('scripts/ci-tiering/linux_garment_controls.py', b"platform.machine() != 'x86_64'", b'False'),
                ('scripts/ci-tiering/test_policy.py', b'self.assertEqual(retained(linux), original)', b'pass')]:
            original_input = (ROOT/name).read_bytes()
            mutant = original_input.replace(old, new, 1)
            self.assertNotEqual(mutant, original_input)
            with self.subTest(input=name, mutation=old), self.assertRaises(AssertionError):
                historical_tiering_input(name, self, mutant)

    def test_new_jobs_and_selectors_reject_changes(self):
        original = (ROOT/'.github/workflows/ci.yml').read_text()
        for name in [*TIER_JOB_SHA256, 'mac-full-background', 'portable-eye', 'portable']:
            block = re.search(r'(?ms)^  '+re.escape(name)+r':\n.*?(?=^  [a-z][a-z0-9-]*:\n|\Z)', original)[0]
            for replacement in ['', block*2, block.replace('    timeout-minutes:', '    timeout-minutes: 1 #'),
                                block.replace('    runs-on:', '    continue-on-error: true\n    runs-on:')]:
                mutant = original.replace(block, replacement, 1)
                self.assertNotEqual(mutant, original)
                with self.subTest(job=name), self.assertRaises(AssertionError):
                    historical_tiering_workflow(mutant, self)
        for old, new in [
            ("needs.classify.outputs.full_required == 'true'", "needs.classify.outputs.full_required == 'false'"),
            ("needs.classify.outputs.full_required == 'false'", "true"),
            ("    tags: ['*']\n", ''),
            ('  workflow_dispatch:\n', ''),
            ('    types: [published]\n', '    types: [created]\n')]:
            mutant = original.replace(old, new, 1)
            self.assertNotEqual(mutant, original)
            with self.subTest(selector=old), self.assertRaises(AssertionError):
                historical_tiering_workflow(mutant, self)

if __name__ == "__main__":
    unittest.main(verbosity=2)
