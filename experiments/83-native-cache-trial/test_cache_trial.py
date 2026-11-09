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
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'experiments/83-native-cache-trial/cache_trial.py'
spec = importlib.util.spec_from_file_location('cache_trial', SCRIPT)
trial = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trial)


WORKFLOW_ADDITIONS = (
    ('      - name: Check isolated shoulder rest-refit controls\n'
     '        run: python3 -B scripts/check-portable.py shoulder-rest-refit\n',
     'required exact shoulder rest-refit addition'),
    ('      - name: Check current nineteen-case shoulder controls\n'
     '        run: python3 -B scripts/check-portable.py current19-shoulder-refit\n',
     'required exact current19 shoulder addition'),
)


# Admit only the reviewed portable job cap before historical comparison.
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


def portable_split_dependency_header(header):
    return header.replace('    needs: portable\n', '    needs: [portable, portable-eye]\n').replace(
        '    needs: [classify, portable]\n', '    needs: [classify, portable, portable-eye]\n')


def historical_portable_split_input(name, checks, data):
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


# macos15-arm64-v1: admit only the paired retained-job image replacement.
MACOS15_HEADERS = (
    """  native-and-wasm:
    name: macOS CPU tests and Wasm compile check
    # Reject cheap portable failures before spending a cold graphical compile.
    needs: portable
    runs-on: macos-15
""",
    """  native-cache-warm:
    name: macOS native target cache warm trial
    # Reject cheap portable failures before spending a cold graphical compile.
    if: ${{ needs.native-and-wasm.outputs.trial_enabled == 'true' }}
    needs: [native-and-wasm, b1-source-regression]
    runs-on: macos-15
""",
)


# native75: admit only the producer allowance; warm keeps its real 60-minute cap.
NATIVE75_BUDGET = """    # The measured original lane already takes about 30 minutes cold. Keep a
    # finite bound for native tests, mutation witnesses and continuous motion.
    timeout-minutes: 75
"""
NATIVE75_MATRIX_COMMENT = '        #20minute step within the existing75minute job, including probe linking.\n'


def historical_native_budget_workflow(workflow, checks):
    jobs = []
    for name, header, cap in [('native-and-wasm', MACOS15_HEADERS[0], '75'),
                              ('native-cache-warm', MACOS15_HEADERS[1], '60')]:
        blocks = re.findall(r'(?ms)^  '+name+r':\n.*?(?=^  [a-z][a-z0-9-]*:\n|\Z)', workflow)
        checks.assertEqual(len(blocks), 1, 'required one '+name+' job')
        block = blocks[0]
        checks.assertTrue(block.startswith(header), 'required exact '+name+' header')
        checks.assertEqual(re.findall(r'^    timeout-minutes:.*$', block, re.M),
                           ['    timeout-minutes: '+cap], 'required exact current '+name+' cap')
        jobs.append(block)
    native = jobs[0]
    checks.assertTrue(native.startswith(MACOS15_HEADERS[0]+NATIVE75_BUDGET),
                      'required exact producer budget placement')
    checks.assertEqual(native.count(NATIVE75_MATRIX_COMMENT), 1,
                       'required exact producer matrix budget comment')
    restored = native.replace(NATIVE75_BUDGET, NATIVE75_BUDGET.replace('75', '60'), 1)
    restored = restored.replace(NATIVE75_MATRIX_COMMENT,
                                NATIVE75_MATRIX_COMMENT.replace('75', '60'), 1)
    return workflow.replace(native, restored, 1)


def historical_macos_workflow(workflow, checks):
    workflow = historical_eye_budget_workflow(workflow, checks)
    workflow = historical_native_budget_workflow(workflow, checks)
    checks.assertEqual(workflow.count('  portable:\n'), 1, 'required one portable job')
    checks.assertEqual(workflow.count(PORTABLE30_HEADER), 1,
                       'required exact portable job with 30-minute cap')
    workflow = workflow.replace(PORTABLE30_HEADER, PORTABLE30_HEADER.replace(
        '    timeout-minutes: 30\n', '    timeout-minutes: 15\n'), 1)
    checks.assertEqual(workflow.count('    runs-on: macos-15\n'), 2,
                       'required paired standard ARM64 macos-15 migration')
    for header in MACOS15_HEADERS:
        checks.assertEqual(workflow.count(header), 1, 'required exact retained Mac job policy')
        workflow = workflow.replace(header, header.replace('macos-15', 'macos-14'))
    # Preserve the existing exact addition diagnostics before the stronger digest.
    for addition, message in WORKFLOW_ADDITIONS:
        checks.assertEqual(workflow.count(addition), 1, message)
    # Keep the entire reviewed 2e6dc2e workflow, including optional warm/cache
    # policy blocks which the older historical comparisons deliberately remove.
    checks.assertEqual(hashlib.sha256(workflow.encode()).hexdigest(),
                       'de16867ec382bb3915ce676ec5bddd68aaf239f51808663650e0b9d805181757',
                       'runner migration must be exactly the paired label replacement')
    return workflow


# linux-b1-v2: validate the complete approved addition before historical comparison.
B1_LINUX_HEADER = """  b1-source-regression:
    name: Linux B1 source regression and viewer checks
    # Keep the independent cold B1 build and Web checks inside a finite budget.
    needs: portable
    runs-on: ubuntu-24.04
"""
B1_MACOS_HEADER = """  b1-source-regression:
    name: macOS B1 source regression and viewer checks
    # Keep the independent cold B1 build and Web checks inside a finite budget.
    needs: portable
    runs-on: macos-14
"""
B1_FETCH_STEP = """      - name: Fetch locked dependencies for Linux B1 checks
        run: |
          cargo fetch --locked --manifest-path Cargo.toml
          cargo fetch --locked --manifest-path experiments/49-runtime-pose-parity/probe/Cargo.toml
          cargo fetch --locked --manifest-path experiments/50-upper-arm-neutral-ab/probe/Cargo.toml
          cargo fetch --locked --manifest-path experiments/60-b1-continuous-motion/Cargo.toml
          cargo fetch --locked --manifest-path experiments/65-b1-appearance-quality/preview/Cargo.toml
          cargo fetch --locked --manifest-path experiments/66-b1-appearance-work/Cargo.toml
          cargo fetch --locked --manifest-path experiments/68-b1-eye-render-diagnosis/Cargo.toml
          cargo fetch --locked --manifest-path experiments/71-b1-character-parameters/Cargo.toml
          cargo fetch --locked --manifest-path experiments/79-shoulder-pose-corrective/Cargo.toml
"""
B1_PREPARE_STEP = """      - name: Prepare pinned B1 inputs without asset or tool downloads
"""


def historical_b1_workflow(workflow, checks):
    checks.assertEqual(workflow.count(B1_LINUX_HEADER), 1, 'required exact Linux B1 policy')
    checks.assertEqual(workflow.count(B1_FETCH_STEP), 1, 'required exact Linux B1 fetch step')
    before, b1_and_warm = workflow.split(B1_LINUX_HEADER)
    b1, separator, warm = b1_and_warm.partition('  # native-cache-trial begin\n')
    install = ('      - name: Install repository Rust version\n'
               '        run: rustup toolchain install 1.95.0 --profile minimal --component rustfmt '
               '--component clippy --target wasm32-unknown-unknown\n')
    checks.assertEqual(b1.count(install+B1_FETCH_STEP+B1_PREPARE_STEP), 1,
                       'Linux B1 fetch must follow Rust installation and precede preparation')
    return before+B1_MACOS_HEADER+b1.replace(B1_FETCH_STEP, '')+separator+warm


def without_trial(text):
    # Exact indentation disambiguates the whole optional warm job from its steps.
    text = re.sub(r'(?ms)^  # native-cache-trial begin\n.*?^  # native-cache-trial end\n', '', text)
    text = re.sub(r'(?ms)^ +# native-cache-trial begin\n.*?^ +# native-cache-trial end\n', '', text)
    return re.sub(r'(?ms)^ +# native-main-cache begin\n.*?^ +# native-main-cache end\n', '', text)


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
        return subprocess.run([sys.executable, '-B', *(['-O'] if sys.flags.optimize else []), str(self.script), stage, '--lane', lane],
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

    def cold_lookup(self, key, response=None, fault=None, status=200, redirect=False, raw=None):
        # Invoke the actual production __main__ CLI in a fresh process. Only the
        # HTTP transport is replaced; production exposes no alternate URL switch.
        payload = json.dumps({'response': response if response is not None else
                              {'total_count': 0, 'actions_caches': []},
                              'fault': fault, 'status': status, 'redirect': redirect, 'raw': raw})
        launcher = r'''import io,json,runpy,sys,urllib.error,urllib.request
settings=json.loads(sys.argv[1]); script=sys.argv[2]; key=sys.argv[3]
class Response(io.BytesIO):
    status=settings['status']
    def geturl(self):
        return 'https://example.invalid/redirect' if settings['redirect'] else expected
expected='https://api.github.com/repos/Derek-X-Wang/nvwa/actions/caches?key='+key
def boundary(request,timeout):
    if request.full_url!=expected or timeout!=30 or request.has_header('Authorization'):
        raise ValueError('unexpected endpoint/query/timeout/credential')
    if settings['fault']=='network': raise urllib.error.URLError('fixture unavailable')
    if settings['fault']=='http': raise urllib.error.HTTPError(expected,429,'fixture rate limit',{},None)
    if settings['fault']=='oversize': return Response(b'x'*65537)
    return Response(settings['raw'].encode() if settings['raw'] is not None else json.dumps(settings['response']).encode())
urllib.request.urlopen=boundary
sys.argv=[script,'cold-miss','--lane','cold']
runpy.run_path(script,run_name='__main__')
'''
        return subprocess.run([sys.executable, '-B', *(['-O'] if sys.flags.optimize else []), '-c', launcher, payload, str(self.script), key],
                              cwd=self.root, env=self.env, capture_output=True, text=True)

    def finish_with_test_cap(self, cap):
        # Test-only constant injection: no production argument/environment can
        # change the 4GiB cap. Execute the actual parser/main and serialization.
        launcher = r'''import runpy,subprocess,sys
script=sys.argv[1]; cap=int(sys.argv[2])
module=runpy.run_path(script,run_name='cache_cap_fixture')
module['main'].__globals__['CAP']=cap
sys.argv=[script,'finish','--lane','cold']
try:
    module['main']()
except (OSError,ValueError,KeyError,subprocess.CalledProcessError) as error:
    print('FAIL: '+str(error),file=sys.stderr)
    sys.exit(1)
'''
        return subprocess.run([sys.executable, '-B', *(['-O'] if sys.flags.optimize else []),
                               '-c', launcher, str(self.script), str(cap)],
                              cwd=self.root, env=self.env, capture_output=True, text=True)

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
        matrix = json.loads((ROOT / 'experiments/83-native-cache-trial/fixtures/motion-summary-run39518452707.json').read_text())
        for name, value in [('nvwa-b1-motion-mutations', mutation), ('nvwa-b1-motion-matrix', matrix)]:
            path = self.temp / name
            path.mkdir(exist_ok=True)
            (path / 'summary.json').write_text(json.dumps(value))
        return mutation, matrix


    def test_real_cli_same_source_pair_integrity_and_source_mtimes(self):
        before = (self.root / 'source.rs').stat().st_mtime_ns
        key = self.prepare()
        self.assertEqual(self.cold_lookup(key).returncode, 0)
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

    def test_macos15_cannot_consume_old_image_trial_key(self):
        old_key = self.prepare()  # Historical macos14 fixture, same source/run.
        for changes in [{'ImageOS': 'macos15'}, {'ImageOS': 'macos15', 'ImageVersion': 'new-image'}]:
            with self.subTest(changes=changes):
                result = self.call('prepare', **changes)
                self.assertEqual(result.returncode, 0, result.stderr)
                rows = [json.loads(line.removeprefix('NVWA_NATIVE_CACHE ')) for line in result.stdout.splitlines()]
                new_key = next(row['key'] for row in rows if row['stage'] == 'prepare')
                self.assertNotEqual(new_key, old_key)
                warm = self.call('prepare', 'warm', TRIAL_EXPECTED_KEY=old_key, **changes)
                self.assertNotEqual(warm.returncode, 0)
                self.assertIn('producer source/toolchain/image/config differs', warm.stderr)
                hit = self.receipt(old_key, 'warm', TRIAL_HIT='true', TRIAL_MATCHED=old_key, **changes)
                self.assertNotEqual(hit.returncode, 0)
                self.assertIn('cache primary key mismatch', hit.stderr)

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

    def test_actual_cli_cold_lookup_requires_unambiguous_repository_wide_absence(self):
        key = self.prepare()
        valid = self.cold_lookup(key)
        self.assertEqual(valid.returncode, 0, valid.stderr)
        receipt = next(json.loads(line.removeprefix('NVWA_NATIVE_CACHE ')) for line in valid.stdout.splitlines()
                       if '"stage": "cold-miss"' in line)
        self.assertEqual(receipt['query_key'], key)
        self.assertTrue(receipt['miss_verified'])
        self.assertEqual(receipt['total_count'], 0)
        failures = [
            {'fault': 'network'}, {'fault': 'http'}, {'status': 500}, {'status': 206},
            {'redirect': True}, {'fault': 'oversize'}, {'raw': '{'},
            {'response': {'total_count': 1, 'actions_caches': [{'key': key}]}},
            {'response': {'total_count': 0, 'actions_caches': [{'key': key}]}},
            {'response': {'total_count': 1, 'actions_caches': []}},
            {'response': {'total_count': False, 'actions_caches': []}},
            {'response': {'total_count': '0', 'actions_caches': []}},
            {'response': {'total_count': 0.0, 'actions_caches': []}},
            {'response': {'total_count': 0}}, {'response': []},
            {'response': {'total_count': 0, 'actions_caches': None}},
            {'response': {'total_count': 0, 'actions_caches': [], 'partial': True}},
        ]
        for change in failures:
            with self.subTest(change=change):
                result = self.cold_lookup(key, **change)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('"miss_verified": true', result.stdout)
                self.assertFalse(self.target.exists())
        self.assertNotEqual(self.receipt(key).returncode, 0,
                            'empty action outputs can never establish a cold miss')

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

    def test_actual_retained_matrix_summary_and_strict_event_coverage_contract(self):
        self.prepare()
        _, actual = self.gate_fixtures()
        self.target.mkdir()
        (self.target / 'compiled').write_bytes(b'tiny fixture; no native build')
        path = self.temp / 'nvwa-b1-motion-matrix/summary.json'
        accepted = self.call('finish')
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        finish = next(json.loads(line.removeprefix('NVWA_NATIVE_CACHE '))
                      for line in accepted.stdout.splitlines() if '"stage": "finish"' in line)
        self.assertEqual(finish['gates']['matrix'], actual)
        retained = ROOT / 'experiments/83-native-cache-trial/fixtures/motion-summary-run39518452707.json'
        manifest = json.loads(retained.with_suffix('.manifest.json').read_text())
        self.assertEqual(manifest['source_run'], 39518452707)
        self.assertEqual(manifest['source_job'], 118960012261)
        self.assertEqual(manifest['run_attempt'], 1)
        self.assertEqual(manifest['retained_fixture_sha256'], trial.sha(retained.read_bytes()))
        self.assertEqual(finish['target_size']['logical_bytes'], len(b'tiny fixture; no native build'))
        self.assertEqual(finish['target_size']['files'], 1)
        self.assertEqual(finish['marker_bytes'], (self.target / trial.MARKER).stat().st_size)
        self.assertEqual(finish['full_saved_logical_bytes'],
                         finish['target_size']['logical_bytes']+finish['marker_bytes'])
        self.assertIs(finish['target_size']['complete'], True)
        (self.target / trial.MARKER).unlink()
        invalid = []
        for field in ['records', 'passing_records', 'probe_exit', 'probe_complete_marker', 'passed', 'coverage', 'failures']:
            value = copy.deepcopy(actual)
            value.pop(field)
            invalid.append(value)
        # Missing/extra event and successful-check counts, including the former
        # incorrect fixture that mistook all events for just the matrix grid.
        for changes in [{'records':612}, {'records':614}, {'passing_records':611},
                        {'passing_records':613}, {'records':594, 'passing_records':594},
                        {'probe_exit':False}, {'probe_exit':1}, {'records':613.0},
                        {'passing_records':612.0}, {'passed':1}, {'probe_complete_marker':1},
                        {'failures':[{'technical_pass':False}]}]:
            invalid.append({**copy.deepcopy(actual), **changes})
        expected = {'expected':594, 'observed':594, 'deep_keyframes_expected':30,
                    'deep_keyframes_observed':30, 'body_variants':3, 'face_settings':3}
        for field, count in expected.items():
            for replacement in [count-1, count+1, float(count), True, None]:
                value = copy.deepcopy(actual)
                value['coverage'][field] = replacement
                invalid.append(value)
            value = copy.deepcopy(actual)
            value['coverage'].pop(field)
            invalid.append(value)
        for changes in [{'complete':False}, {'complete':1}, {'missing':[['missing-grid-cell']]},
                        {'missing':None}, {'unexpected_partial_schema':True}]:
            value = copy.deepcopy(actual)
            value['coverage'].update(changes)
            invalid.append(value)
        # Exhaustive coercion/schema vectors exercise the real validation seam
        # called by finish, without repeating Git/toolchain subprocesses for
        # each equivalent boundary. Keep representative failure families through
        # the complete production CLI and its pre-rejection size receipt too.
        for value in invalid:
            with self.subTest(summary=value):
                with self.assertRaises(ValueError):
                    trial.validate_matrix(value)
        cli_invalid = []
        for changes in [{'records':612}, {'records':614}, {'passing_records':611},
                        {'passing_records':613}, {'records':594, 'passing_records':594}]:
            cli_invalid.append({**copy.deepcopy(actual), **changes})
        for field in ['records', 'passing_records', 'coverage']:
            value = copy.deepcopy(actual)
            value.pop(field)
            cli_invalid.append(value)
        for field, count in expected.items():
            value = copy.deepcopy(actual)
            value['coverage'][field] = count-1
            cli_invalid.append(value)
        for changes in [{'complete':False}, {'missing':[['missing-grid-cell']]},
                        {'unexpected_partial_schema':True}]:
            value = copy.deepcopy(actual)
            value['coverage'].update(changes)
            cli_invalid.append(value)
        for value in cli_invalid:
            with self.subTest(cli_summary=value):
                path.write_text(json.dumps(value))
                rejected = self.call('finish')
                self.assertNotEqual(rejected.returncode, 0)
                size = next(json.loads(line.removeprefix('NVWA_NATIVE_CACHE '))
                            for line in rejected.stdout.splitlines() if '"stage": "target-size"' in line)
                self.assertEqual(size['logical_bytes'], len(b'tiny fixture; no native build'))
                self.assertEqual(size['files'], 1)
                self.assertIs(size['complete'], True)
                self.assertFalse((self.target / trial.MARKER).exists(), 'failed evidence must not prepare cache save')

    def test_oversize_sparse_target_and_escaping_symlink_reject_before_save(self):
        self.prepare()
        self.gate_fixtures()
        self.target.mkdir()
        path = self.target / 'oversize'
        with path.open('wb') as stream:
            stream.truncate(trial.CAP+1)
        (self.target / 'tail').write_bytes(b'1234567')
        rejected = self.call('finish')
        self.assertNotEqual(rejected.returncode, 0)
        size = next(json.loads(line.removeprefix('NVWA_NATIVE_CACHE '))
                    for line in rejected.stdout.splitlines() if '"stage": "target-size"' in line)
        self.assertEqual(size['logical_bytes'], trial.CAP+8, 'retain full total after crossing the cap')
        self.assertEqual(size['files'], 2)
        self.assertIs(size['complete'], True)
        self.assertNotIn('"stage": "finish"', rejected.stdout)
        self.assertFalse((self.target / trial.MARKER).exists())
        path.unlink()
        path.symlink_to(self.root / 'source.rs')
        self.assertNotEqual(self.call('finish').returncode, 0)

        # The former 64KiB regular-file reserve misses links that consume that
        # margin, and receipts larger than the reserve. Both real-filesystem
        # cases must fail before writing the exact serialized marker.
        for scenario in ['symlink-margin', 'large-receipt']:
            shutil.rmtree(self.target)
            self.target.mkdir()
            with (self.target / 'compiled').open('wb') as stream:
                stream.truncate(65536)
            if scenario == 'symlink-margin':
                for number in range(315):
                    (self.target / f'link-{number:03}').symlink_to('./'*100+'compiled')
            else:
                rustc = self.bin / 'rustc'
                text = 'rustc 1.95.0 (fixture)\nhost: aarch64-apple-darwin\n'+'x'*70000
                rustc.write_text('#!/bin/sh\nprintf "%s\\n" '+repr(text)+'\n')
                rustc.chmod(0o755)
            rejected = self.finish_with_test_cap(131072)
            self.assertNotEqual(rejected.returncode, 0, scenario)
            rows = [json.loads(line.removeprefix('NVWA_NATIVE_CACHE ')) for line in rejected.stdout.splitlines()]
            measured = next(row for row in rows if row['stage'] == 'target-size')
            projected = next(row for row in rows if row['stage'] == 'target-save-size')
            self.assertTrue(measured['complete'])
            self.assertLessEqual(measured['logical_bytes'], 131072)
            self.assertGreater(projected['full_saved_logical_bytes'], 131072)
            self.assertEqual(projected['full_saved_logical_bytes'],
                             measured['logical_bytes']+projected['marker_bytes'])
            self.assertFalse((self.target / trial.MARKER).exists())
            self.assertNotIn('"stage": "finish"', rejected.stdout)
        marker = self.target / trial.MARKER
        marker.write_bytes(b'prior-receipt-must-not-be-overwritten')
        self.assertNotEqual(self.call('finish').returncode, 0)
        self.assertEqual(marker.read_bytes(), b'prior-receipt-must-not-be-overwritten')

    def test_missing_or_duplicate_shoulder_step_rejects_existing_workflow_contract(self):
        workflow_path = ROOT / '.github/workflows/ci.yml'
        original = workflow_path.read_text()
        read_text = Path.read_text
        for addition, message in WORKFLOW_ADDITIONS:
            for replacement in ('', addition + addition):
                mutant = original.replace(addition, replacement)
                def read(path, *args, **kwargs):
                    return mutant if path == workflow_path else read_text(path, *args, **kwargs)
                with self.subTest(addition=message, step_count=mutant.count(addition)), patch.object(Path, 'read_text', read):
                    with self.assertRaisesRegex(AssertionError, message):
                        self.test_exact_original_workflow_and_full_warm_step_policy_parity()

    def test_linux_b1_overlay_rejects_unapproved_policy_and_fetch_changes(self):
        workflow_path = ROOT / '.github/workflows/ci.yml'
        original = workflow_path.read_text()
        read_text = Path.read_text
        # Keep every historical header mutation; translate both source and
        # replacement dependencies to this exact topology before applying it.
        def replace_header(old, new):
            return original.replace(portable_split_dependency_header(old),
                                    portable_split_dependency_header(new))
        commands = B1_FETCH_STEP.splitlines(keepends=True)[2:]
        mutations = [replace_header(B1_LINUX_HEADER, B1_MACOS_HEADER),
                     original.replace('name: Linux B1 source', 'name: Other B1 source'),
                     replace_header(B1_LINUX_HEADER, B1_LINUX_HEADER.replace('ubuntu-24.04', 'ubuntu-latest')),
                     replace_header(B1_LINUX_HEADER, B1_LINUX_HEADER.replace('needs: portable', 'needs: native-and-wasm')),
                     original.replace(B1_FETCH_STEP, ''),
                     original.replace(B1_FETCH_STEP, B1_FETCH_STEP*2),
                     original.replace(B1_FETCH_STEP+B1_PREPARE_STEP, B1_PREPARE_STEP+B1_FETCH_STEP),
                     original.replace(B1_FETCH_STEP, B1_FETCH_STEP.replace('        run: |', '        shell: bash\n        run: |'))]
        mutations.extend([
            replace_header(B1_LINUX_HEADER, B1_LINUX_HEADER.replace('Linux B1', 'macOS B1')),
            replace_header(B1_LINUX_HEADER, B1_LINUX_HEADER.replace('ubuntu-24.04', 'macos-14')),
            replace_header(B1_LINUX_HEADER, B1_LINUX_HEADER*2),
            original.replace(B1_FETCH_STEP, B1_FETCH_STEP+'          true\n'),
            original.replace(B1_FETCH_STEP, B1_FETCH_STEP.replace('        run: |', '        if: true\n        run: |')),
            original.replace(B1_FETCH_STEP, B1_FETCH_STEP.replace('        run: |', '        continue-on-error: true\n        run: |')),
            original.replace(B1_FETCH_STEP, B1_FETCH_STEP.replace('        run: |', '        env:\n          CARGO_BUILD_JOBS: 2\n        run: |')),
        ])
        for command in commands:
            for replacement in ('', command*2, command.replace('--locked', '--offline'),
                                command.replace('--locked', '--locked --offline'),
                                command.replace('--locked', '--locked --features extra'),
                                command.replace('Cargo.toml', 'Other.toml')):
                mutations.append(original.replace(B1_FETCH_STEP, B1_FETCH_STEP.replace(command, replacement)))
        mutations.append(original.replace(B1_FETCH_STEP, B1_FETCH_STEP.replace(
            commands[0]+commands[1], commands[1]+commands[0])))
        mutations.extend([original.replace('-- --nocapture', '-- --exact'),
                          original.replace('python3 -B -O experiments/58-b1-desktop-web/verify_native.py',
                                           'python3 -B experiments/58-b1-desktop-web/verify_native.py'),
                          original.replace(' --lib --locked --offline', ' --lib --locked'),
                          original.replace('bash experiments/27-ci-baseline/check.sh wasm',
                                           'bash experiments/27-ci-baseline/check.sh wasm --offline'),
                          original.replace(B1_PREPARE_STEP, '      - name: Unsupported extra command\n        run: true\n'+B1_PREPARE_STEP)])
        for index, mutant in enumerate(mutations):
            self.assertNotEqual(mutant, original)
            def read(path, *args, **kwargs):
                return mutant if path == workflow_path else read_text(path, *args, **kwargs)
            with self.subTest(mutation=index), patch.object(Path, 'read_text', read):
                with self.assertRaises(AssertionError):
                    self.test_exact_original_workflow_and_full_warm_step_policy_parity()

    def test_macos15_overlay_rejects_partial_mixed_and_unrelated_changes(self):
        workflow_path = ROOT / '.github/workflows/ci.yml'
        original = workflow_path.read_text()
        read_text = Path.read_text
        mutations = []
        for cap in ['15', '19', '21', '20', '0', '-1', '20.0', '"20"',
                    '24', '26', '25.0', '"25"', "'25'", '${{ 25 }}']:
            mutations.append(original.replace(PORTABLE30_HEADER, PORTABLE30_HEADER.replace(
                'timeout-minutes: 30', 'timeout-minutes: '+cap)))
        native_matrix = (
            '      - name: Execute the actual B1 continuous motion matrix\n'
            '        # Independent full-weight Python checks stream594frames; retain a finite\n'
            '        #20minute step within the existing75minute job, including probe linking.\n'
            '        timeout-minutes: 20\n')
        self.assertEqual(historical_tiering_workflow(original, self).count(native_matrix), 1)
        mutations.extend([
            original.replace(PORTABLE30_HEADER, PORTABLE30_HEADER.replace('    timeout-minutes: 30\n', '')),
            original.replace(PORTABLE30_HEADER, PORTABLE30_HEADER+'    timeout-minutes: 30\n'),
            original.replace(PORTABLE30_HEADER, PORTABLE30_HEADER*2),
            original.replace(PORTABLE30_HEADER, PORTABLE30_HEADER.replace('  portable:', '  other:')),
            original.replace('    timeout-minutes: 60\n', '    timeout-minutes: 20\n', 1),
            original.replace('        timeout-minutes: 3\n', '        timeout-minutes: 4\n', 1),
            original.replace(PORTABLE30_HEADER, PORTABLE30_HEADER.replace(
                'timeout-minutes: 30', 'timeout-minutes: 15')).replace(
                    '    timeout-minutes: 60\n', '    timeout-minutes: 20\n', 1),
            original.replace(PORTABLE30_HEADER, PORTABLE30_HEADER.replace(
                'timeout-minutes: 30', 'timeout-minutes: 15')).replace(
                    native_matrix, native_matrix.replace('timeout-minutes: 20', 'timeout-minutes: 25'), 1),
        ])
        for header in (MACOS15_HEADERS[0].replace('    needs: portable\n',
                "    needs: [classify, portable]\n    if: ${{ needs.classify.outputs.full_required == 'true' }}\n"), MACOS15_HEADERS[1]):
            header = portable_split_dependency_header(header)
            for label in ['macos-14', 'macos-latest', 'macos-26', 'macos-15-intel',
                          'macos-15-large', 'macos-15-xlarge', 'unknown']:
                mutations.append(original.replace(header, header.replace('macos-15', label)))
            mutations.append(original.replace(header, header+'    continue-on-error: true\n'))
            mutations.append(original.replace(header, header*2))
            mutations.append(original.replace(header, header.replace('needs:', 'extra:')))
        for label in ['macos-14', 'macos-latest', 'macos-15-intel', 'macos-15-xlarge']:
            mutations.append(original.replace('runs-on: macos-15', 'runs-on: '+label))
        mutations.extend([original.replace("CARGO_BUILD_JOBS: '1'", "CARGO_BUILD_JOBS: '2'"),
                          original.replace('timeout-minutes: 60', 'timeout-minutes: 61'),
                          original.replace('cargo test --manifest-path', 'cargo check --manifest-path'),
                          original.replace('runs-on: ubuntu-24.04', 'runs-on: macos-15')])
        native = re.search(r'(?ms)^  native-and-wasm:\n.*?(?=^  [a-z][a-z0-9-]*:\n|\Z)', original).group()
        b1 = re.search(r'(?ms)^  b1-source-regression:\n.*?(?=^  [a-z][a-z0-9-]*:\n|\Z)', original).group()
        warm = re.search(r'(?ms)^  native-cache-warm:\n.*?(?=^  [a-z][a-z0-9-]*:\n|\Z)', original).group()
        budget_mutations = []
        for cap in ['60', '74', '76', '0', '-1', '75.0', '"75"', "'75'"]:
            budget_mutations.append(('native-cap-'+cap, original.replace(native, native.replace(
                '    timeout-minutes: 75\n', '    timeout-minutes: '+cap+'\n', 1))))
        budget_mutations.extend([
            ('missing-native-cap', original.replace(native, native.replace('    timeout-minutes: 75\n', '', 1))),
            ('duplicate-native-cap', original.replace(native, native.replace('    timeout-minutes: 75\n', '    timeout-minutes: 75\n'*2, 1))),
            ('missing-native-job', original.replace(native, '')),
            ('duplicate-native-job', original.replace(native, native*2)),
            ('renamed-native-job', original.replace(native, native.replace('  native-and-wasm:', '  other:', 1))),
            ('misplaced-native-cap', original.replace(native, native.replace('    timeout-minutes: 75\n', '', 1)+'    timeout-minutes: 75\n')),
            ('missing-native-comment', original.replace(native, native.replace(NATIVE75_MATRIX_COMMENT, ''))),
            ('duplicate-native-comment', original.replace(native, native.replace(NATIVE75_MATRIX_COMMENT, NATIVE75_MATRIX_COMMENT*2))),
            ('stale-native-comment', original.replace(native, native.replace(NATIVE75_MATRIX_COMMENT, NATIVE75_MATRIX_COMMENT.replace('75', '60')))),
            ('matrix-cap', original.replace(native, native.replace('        timeout-minutes: 20\n', '        timeout-minutes: 21\n', 1))),
            ('mutation-cap', original.replace(native, native.replace('        timeout-minutes: 12\n', '        timeout-minutes: 13\n', 1))),
            ('portable-cap', original.replace(PORTABLE30_HEADER, PORTABLE30_HEADER.replace('timeout-minutes: 30', 'timeout-minutes: 21'))),
            ('b1-cap', original.replace(b1, b1.replace('    timeout-minutes: 60\n', '    timeout-minutes: 61\n', 1))),
            ('warm-cap', original.replace(warm, warm.replace('    timeout-minutes: 60\n', '    timeout-minutes: 61\n', 1))),
            ('cache-action-cap', original.replace(native, native.replace('        timeout-minutes: 4\n', '        timeout-minutes: 5\n', 1))),
        ])
        native60 = native.replace('    timeout-minutes: 75\n', '    timeout-minutes: 60\n', 1)
        for name, job in [('b1', b1), ('warm', warm)]:
            budget_mutations.append(('75-moved-to-'+name, original.replace(native, native60).replace(
                job, job.replace('    timeout-minutes: 60\n', '    timeout-minutes: 75\n', 1))))
        for name, mutant in budget_mutations:
            self.assertNotEqual(mutant, original, name)
            mutations.append(mutant)
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
            mutations.append(mutant)
        for index, mutant in enumerate(mutations):
            self.assertNotEqual(mutant, original)
            def read(path, *args, **kwargs):
                return mutant if path == workflow_path else read_text(path, *args, **kwargs)
            with self.subTest(mutation=index), patch.object(Path, 'read_text', read):
                with self.assertRaises(AssertionError):
                    self.test_exact_original_workflow_and_full_warm_step_policy_parity()

    def test_exact_original_workflow_and_full_warm_step_policy_parity(self):
        workflow = (ROOT / '.github/workflows/ci.yml').read_text()
        workflow = historical_macos_workflow(workflow, self)
        baseline = historical_b1_workflow(workflow, self)
        for addition, message in WORKFLOW_ADDITIONS:
            self.assertEqual(workflow.count(addition), 1, message)
            baseline = baseline.replace(addition, '')
        baseline = without_trial(baseline)
        workflow = re.sub(r'(?ms)^ +# native-main-cache begin\n.*?^ +# native-main-cache end\n', '', workflow)
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
        self.assertEqual(workflow.count('actions/cache/restore@55cc8345863c7cc4c66a329aec7e433d2d1c52a9'), 2)
        self.assertEqual(workflow.count('actions/cache/save@55cc8345863c7cc4c66a329aec7e433d2d1c52a9'), 1)
        for forbidden in ['restore-keys:', 'ACTIONS_CACHE_SERVICE_V2', 'ACTIONS_RUNTIME_TOKEN:', 'pull_request_target:', 'workflow_run:']:
            self.assertNotIn(forbidden, workflow)
        self.assertIn('run: python3 -B experiments/83-native-cache-trial/cache_trial.py cold-miss --lane cold', native)
        self.assertEqual(native.count('lookup-only: true'), 1)
        self.assertNotIn('actions/cache/save@', warm)
        self.assertLess(native.index('Report existing command timing'), native.index('compression and save'))
        self.assertLess(native.index('compression and save'), native.index('Verify remote exact-key persistence'))
        self.assertLess(warm.index('verify restored target bytes'), warm.index('Run workspace CPU tests'))

        # portable30 rejection cases extend the existing contract; retain13 tests.
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
        self.assertEqual(hashlib.sha256((ROOT/'scripts/portable-checks.json').read_bytes()).hexdigest(), '1a2719b28dad9a288f28e0ff5ba793120e6108217c564099d662fc1b104d7f14')
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

if __name__ == '__main__':
    unittest.main(verbosity=2)
