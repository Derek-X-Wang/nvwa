"""Fast production-entry controls with tiny targets and injected external tools/HTTP."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import socket
import ssl
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.parse
import urllib.error
from email.message import Message

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location('main_native_policy', HERE / 'policy.py')
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


WORKFLOW_ADDITIONS = (
    ('      - name: Check isolated shoulder rest-refit controls\n'
     '        run: python3 -B scripts/check-portable.py shoulder-rest-refit\n',
     'required exact shoulder rest-refit addition'),
    ('      - name: Check current nineteen-case shoulder controls\n'
     '        run: python3 -B scripts/check-portable.py current19-shoulder-refit\n',
     'required exact current19 shoulder addition'),
)


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


def historical_macos_workflow(workflow, checks):
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


class Policy(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='nvwa-main-policy-', dir=Path('/tmp').resolve())
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name).resolve()
        self.assertEqual(self.path.parent,Path('/tmp').resolve(),'fixture physical ancestors must be neutral')
        self.root = self.path / 'checkout'
        self.root.mkdir()
        phase = self.root / 'experiments/83-native-cache-trial/phase.json'
        phase.parent.mkdir(parents=True)
        phase.write_text('{"phase":"adopted"}')
        (self.root / 'Cargo.toml').write_text('fixture manifest')
        (self.root / 'Cargo.lock').write_text('fixture lock')
        (self.root / 'ordinary.rs').write_text('ordinary source')
        (self.root / '.gitignore').write_text('target/\n')
        self.git('init', '-q')
        self.commit()
        self.target = self.root / 'target'
        self.developer = self.path / 'Xcode.app/Contents/Developer'
        self.sdk = self.developer / 'Platforms/MacOSX.platform/Developer/SDKs/MacOSX.fixture.sdk'
        self.sdk.mkdir(parents=True)
        (self.sdk / 'SDKSettings.json').write_text('{"fixture":"sdk"}')
        self.tool = self.developer / 'Toolchains/XcodeDefault.xctoolchain/usr/bin/clang'
        self.tool.parent.mkdir(parents=True)
        self.tool.write_bytes(b'fixture compiler/archive executable')
        self.event = self.path / 'event.json'
        self.env = {**policy.shared.CARGO_ENV, 'PATH': os.environ['PATH'], 'HOME': str(self.path),
                    'GITHUB_OUTPUT': str(self.path / 'output'), 'GITHUB_SHA': self.git('rev-parse', 'HEAD'),
                    'GITHUB_EVENT_NAME': 'push', 'GITHUB_REPOSITORY': policy.REPO, 'GITHUB_REF': policy.REF,
                    'GITHUB_EVENT_PATH': str(self.event), 'GITHUB_WORKSPACE': str(self.root),
                    'GITHUB_RUN_ID': '101', 'GITHUB_RUN_ATTEMPT': '1', 'RUNNER_TEMP': str(self.path),
                    'RUNNER_OS': 'macOS', 'RUNNER_ARCH': 'ARM64', 'ImageOS': 'macos14', 'ImageVersion': 'fixture',
                    'CARGO_HOME': str(self.path / 'cargo'), 'CARGO_TARGET_DIR': str(self.target)}
        self.payload = {'ref': policy.REF, 'after': self.env['GITHUB_SHA'], 'deleted': False,
                        'repository': {'full_name': policy.REPO, 'default_branch': 'main', 'fork': False}}
        self.event.write_text(json.dumps(self.payload))
        self.remote = {'total_count': 0, 'actions_caches': []}
        self.network = False
        self.transport_error = None
        self.requests = 0

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True).strip()

    def commit(self):
        self.git('add', '.')
        self.git('-c', 'user.name=Control', '-c', 'user.email=control@example.invalid', 'commit', '-qm', 'owned fixture')

    def query(self, argv):
        if argv == ['rustc', '-vV']: return 'rustc 1.95.0 (fixture)\nhost: aarch64-apple-darwin'
        if argv == ['cargo', '--version']: return 'cargo 1.95.0 (fixture)'
        if argv == ['rustup', 'show', 'active-toolchain']: return '1.95.0-aarch64-apple-darwin'
        if argv == ['uname', '-s']: return 'Darwin'
        if argv == ['uname', '-m']: return 'arm64'
        if argv == ['uname', '-r']: return 'fixture-kernel'
        if argv == ['sw_vers']: return 'ProductVersion: fixture'
        if argv == ['xcodebuild', '-version']: return 'Xcode fixture'
        if argv == ['xcode-select', '-p']: return '/fixture/Xcode/Developer'
        if argv[:3] == ['xcrun', '--sdk', 'macosx']:
            return str(self.sdk) if argv[3] == '--show-sdk-path' else 'fixture-sdk-version'
        if argv[:2] == ['xcrun', '--find']: return str(self.tool)
        if argv == ['xcrun', 'clang', '--version']: return 'Apple clang fixture target: arm64'
        if argv == ['zstd', '--version']: return 'fixture zstd v1.5.7'
        if argv == ['tar', '--version']: return 'fixture tar'
        raise AssertionError('unexpected external query: '+repr(argv))

    def transport(self, request, timeout):
        self.requests += 1
        self.assertEqual(timeout, 20)
        self.assertFalse(request.has_header('Authorization'))
        url = urllib.parse.urlsplit(request.full_url)
        self.assertEqual(url.scheme+'://'+url.netloc+url.path, 'https://api.github.com/repos/'+policy.REPO+'/actions/caches')
        self.assertEqual(urllib.parse.parse_qs(url.query)['ref'], [policy.REF])
        if self.transport_error is not None:
            raise self.transport_error
        if self.network:
            raise OSError('offline fixture failure')
        body = self.remote if isinstance(self.remote, bytes) else json.dumps(self.remote).encode()
        class Response(io.BytesIO):
            status = 200
            def geturl(response): return request.full_url
        return Response(body)

    def call(self, stage, **extra):
        output = io.StringIO()
        with patch.object(policy, 'ROOT', self.root), patch.object(policy, 'query', self.query), \
             patch.object(policy.shutil, 'which', return_value=str(self.tool)), \
             patch.object(policy.urllib.request, 'urlopen', self.transport), \
             patch.dict(os.environ, {**self.env, **extra}, clear=True), \
             patch.object(sys, 'argv', ['policy.py', stage]), contextlib.redirect_stdout(output):
            policy.main()
        return output.getvalue()

    def state(self):
        return json.loads((self.path / 'nvwa-native-main-seed-state.json').read_text())

    def prepare(self):
        self.call('prepare')
        return self.state()

    def present(self, state):
        row = {'id': 123, 'key': state['key'], 'ref': policy.REF, 'version': state['version'], 'size_in_bytes': 789}
        self.remote = {'total_count': 1, 'actions_caches': [row]}
        return row

    def action(self, key, prefix='MAIN_RESTORE', **changes):
        row = {prefix+'_OUTCOME': 'success', prefix+'_HIT': 'true', prefix+'_PRIMARY': key, prefix+'_MATCHED': key}
        row.update(changes)
        return row

    def restored(self, state):
        self.target.mkdir(exist_ok=True)
        (self.target / 'compiled').write_bytes(b'actual owned target fixture')
        origin = {**state['consumer'], 'sha': 'a'*40, 'tree': 'b'*40, 'run_id': '99'}
        marker = {'schema': 1, 'key': state['key'], 'compatibility': state['compatibility'], 'producer': origin,
                  'inventory': policy.shared.inventory(self.target, marker_name=policy.MARKER)}
        (self.target / policy.MARKER).write_bytes(policy.encoded(marker))
        return marker

    def gate_files(self):
        # Construct the existing semantic-witness schema with actual retained
        # hosted matrix summary. The real shared gates reread every log/hash.
        raw = (self.root / 'ordinary.rs').read_bytes()
        hashes, cases = {}, []
        directory = self.path / 'nvwa-b1-motion-mutations'
        directory.mkdir()
        for name in policy.shared.CASES:
            case = {'name': name, 'source': 'ordinary.rs', 'before_sha256': policy.sha(raw),
                    'mutant_sha256': policy.sha(b'changed'), 'restored_sha256': policy.sha(raw),
                    'semantic_test_failure': True, 'red_exit': 101, 'restored_green': True, 'restored_exit': 0,
                    'command': ['cargo', 'test', '--workspace', '--lib', '--locked', '--offline', policy.shared.TESTS[name], '--', '--exact', '--test-threads=1', '--nocapture'],
                    'intended_assertion': policy.shared.ASSERTIONS[name]}
            cases.append(case)
            for suffix, text in [('red', 'running 1 test\n'+policy.shared.TESTS[name]+'\n'+policy.shared.ASSERTIONS[name]+'\ntest result: FAILED. 0 passed; 1 failed\n'),
                                 ('restored-green', 'test result: ok. 1 passed; 0 failed\n')]:
                name = case['name']+'-'+suffix+'.log'
                (directory / name).write_text(text)
                hashes[name] = policy.sha(text.encode())
        (directory / 'summary.json').write_text(json.dumps({'passed': True, 'cases': cases, 'hashes': hashes}))
        directory = self.path / 'nvwa-b1-motion-matrix'
        directory.mkdir()
        fixture = HERE.parent / 'fixtures/motion-summary-run39518452707.json'
        (directory / 'summary.json').write_bytes(fixture.read_bytes())

    def test_cli_event_and_actual_payload_allowlist(self):
        for name, values in [('GITHUB_EVENT_NAME', ['pull_request', 'pull_request_target', 'workflow_run', 'workflow_dispatch']),
                             ('GITHUB_REPOSITORY', ['fork/nvwa']), ('GITHUB_REF', ['refs/heads/other', 'refs/tags/main'])]:
            for value in values:
                self.assertIn('DISABLED_EVENT_OR_PHASE', self.call('prepare', **{name:value}))
        for path, value in [('ref','refs/heads/other'), ('after','0'*40), ('deleted',True),
                            ('repository', {'full_name':policy.REPO,'default_branch':'main','fork':True})]:
            event = {**self.payload, path:value}
            self.event.write_text(json.dumps(event))
            self.assertIn('DISABLED_EVENT_OR_PHASE', self.call('prepare'))
        self.assertFalse((self.path / 'nvwa-native-main-seed-state.json').exists())
        self.event.write_text(json.dumps(self.payload))
        self.env['GITHUB_SHA'] = '0'*40
        self.payload['after'] = self.env['GITHUB_SHA']
        self.event.write_text(json.dumps(self.payload))
        with self.assertRaisesRegex(ValueError,'immutable workflow SHA'): self.call('prepare')

    def test_compatibility_input_and_runtime_sensitivity_ordinary_source_excluded(self):
        baseline = self.prepare()['compatibility']
        (self.root / 'ordinary.rs').write_text('ordinary change')
        with patch.object(policy,'query',self.query), patch.object(policy.shutil,'which',return_value=str(self.tool)):
            self.assertEqual(policy.compatibility(self.root,self.env), baseline)
            for name in ['Cargo.toml','Cargo.lock','build.rs','new/Cargo.toml','scripts/new.py',
                         'assets/embedded.json','vendor/input.json',policy.GATE_RS,
                         'experiments/83-native-cache-trial/main_policy/policy.py']:
                p=self.root/name; p.parent.mkdir(parents=True,exist_ok=True)
                previous=p.read_bytes() if p.exists() else None
                p.write_bytes(b'changed compatibility input');self.git('add',name)
                self.assertNotEqual(policy.compatibility(self.root,self.env)['inputs_sha256'],baseline['inputs_sha256'],name)
                if previous is None: p.unlink();self.git('rm','--cached',name)
                else: p.write_bytes(previous);self.git('add',name)
            config=self.root/'.cargo/config.toml';config.parent.mkdir();config.write_text('unreviewed config')
            self.git('add','.cargo/config.toml');self.assertIn('.cargo/config.toml',policy.input_paths(self.root))
            with self.assertRaisesRegex(ValueError,'Cargo config'):policy.compatibility(self.root,self.env)
            config.unlink();self.git('rm','--cached','.cargo/config.toml')
            for key in ['ImageVersion','ImageOS']:
                self.assertNotEqual(policy.compatibility(self.root,{**self.env,key:'other'}), baseline)
            (self.sdk/'SDKSettings.json').write_text('changed SDK')
            self.assertNotEqual(policy.compatibility(self.root,self.env),baseline)
            with self.assertRaises(ValueError): policy.compatibility(self.root,{**self.env,'RUSTFLAGS':'unsafe override'})
        (self.root / 'ordinary.rs').write_text('ordinary source')
        self.env['CC']='custom'
        self.assertIn('DISABLED_UNSUPPORTED_IDENTITY',self.call('prepare'))

    def test_macos15_image_sdk_and_xcode_change_seed_identity(self):
        old = self.prepare()  # Historical macos14 fixture, same source and target.
        self.env['ImageOS'] = 'macos15'
        current = self.prepare()
        self.assertNotEqual(current['key'], old['key'])
        self.assertEqual(current['version'], old['version'])  # Archive algorithm unchanged.
        self.env['ImageVersion'] = 'new-image'
        image_update = self.prepare()
        self.assertNotEqual(image_update['key'], current['key'])
        original_query = self.query
        self.query = lambda argv: 'Xcode updated fixture' if argv == ['xcodebuild', '-version'] else original_query(argv)
        xcode_update = self.prepare()
        self.assertNotEqual(xcode_update['key'], image_update['key'])
        (self.sdk/'SDKSettings.json').write_text('{"fixture":"updated-sdk"}')
        sdk_update = self.prepare()
        self.assertNotEqual(sdk_update['key'], xcode_update['key'])

    def test_macos15_old_image_action_or_marker_requires_clean_cold_fallback(self):
        old = self.prepare()
        self.env['ImageOS'] = 'macos15'
        current = self.prepare()
        self.present(current)
        for action_key in [old['key'], current['key']]:
            with self.subTest(action_key=action_key):
                self.prepare()
                self.restored(old)  # Exact old image inventory and marker.
                result = self.call('restore', **self.action(action_key))
                self.assertIn('CLEAN_FALLBACK', result)
                self.assertIn('"warm": false', result)
                self.assertNotIn('VERIFIED_RESTORE', result)
                self.assertEqual(self.state()['status'], 'CLEAN_FALLBACK')
                self.assertFalse(self.target.exists())

    def test_exact_main_restore_keeps_distinct_producer_and_consumer_and_never_resaves(self):
        state=self.prepare();self.present(state);state=self.prepare();marker=self.restored(state)
        text=self.call('restore',**self.action(state['key']))
        self.assertIn('VERIFIED_RESTORE',text)
        self.assertEqual(self.state()['producer'],marker['producer'])
        self.assertNotEqual(marker['producer']['sha'],self.env['GITHUB_SHA'])
        self.gate_files()
        self.assertIn('IMMUTABLE_SEED_CONSUMED_NO_SAVE',self.call('finish'))
        self.assertTrue((self.target/policy.MARKER).is_file())
        version=hashlib.sha256((str(self.target)+'|zstd-without-long|1.0').encode()).hexdigest()
        self.assertEqual(state['version'],version)
        self.assertEqual(hashlib.sha256(b'/Users/runner/work/nvwa/nvwa/target|zstd-without-long|1.0').hexdigest(),
                         'b1f7e60a336e6cc15ef119fbcd901b87f8a6d6834c6a4bed6b63ec88ed080b8f')

    def test_action_prefix_missing_network_partial_and_corrupt_are_clean_fallback_no_save(self):
        state=self.prepare();self.present(state)
        outside=self.path/'outside';outside.write_bytes(b'outside sentinel')
        self.gate_files()
        for scenario in ['prefix','missing','network','partial','corrupt','wrong-provenance']:
            state=self.prepare();marker=self.restored(state)
            if scenario == 'network': (self.target/'outside-link').symlink_to(outside)
            args=self.action(state['key'])
            if scenario=='prefix': args['MAIN_RESTORE_MATCHED']+='-prefix'
            if scenario=='missing': args['MAIN_RESTORE_HIT']=''
            if scenario=='network': args['MAIN_RESTORE_OUTCOME']='failure'
            if scenario=='partial': (self.target/policy.MARKER).unlink()
            if scenario=='corrupt': (self.target/'compiled').write_bytes(b'corrupt')
            if scenario=='wrong-provenance':
                marker['producer']['ref']='refs/pull/107/merge';(self.target/policy.MARKER).write_bytes(policy.encoded(marker))
            text=self.call('restore',**args)
            self.assertIn('CLEAN_FALLBACK',text,scenario)
            self.assertIn('"warm": false',text)
            self.assertFalse(self.target.exists())
            self.assertEqual(outside.read_bytes(),b'outside sentinel')
            self.target.mkdir()
            self.assertIn('NOT_PERSISTED_UNKNOWN_OR_EXISTING',self.call('finish'))
            self.target.rmdir()
        self.network=True
        state=self.prepare();self.assertFalse(state['api']['known'])
        self.call('restore');self.target.mkdir()
        self.assertIn('NOT_PERSISTED_UNKNOWN_OR_EXISTING',self.call('finish'))

    def test_api_scope_version_schema_ambiguity_and_body_rejection(self):
        state=self.prepare();row=self.present(state)
        bad=[{'total_count':True,'actions_caches':[]}, {'total_count':1,'actions_caches':[]},
             {'total_count':2,'actions_caches':[row,row]},b'x'*65537,b'{malformed']
        for field,value in [('ref','refs/pull/107/merge'),('key',state['key']+'-suffix'),('version','other'),('id',True),('size_in_bytes',0)]:
            bad.append({'total_count':1,'actions_caches':[{**row,field:value}]})
        for response in bad:
            self.remote=response
            self.assertFalse(self.prepare()['api']['known'])

    def test_cli_http_error_retains_safe_diagnostics_and_refuses_save(self):
        state=self.prepare();self.call('restore');self.target.mkdir()
        (self.target/'compiled').write_bytes(b'compiled');self.gate_files()
        headers=Message()
        headers['X-GitHub-Request-Id']='AB12:CD34:EF56:7890'
        headers['X-RateLimit-Remaining']='0'
        headers['X-RateLimit-Reset']='1792540800'
        headers['Retry-After']='60'
        headers['Authorization']='Bearer PRIVATE_SENTINEL'
        for status,cause in [(403,'http_forbidden'),(429,'http_rate_limited'),(503,'http_server_error')]:
            with self.subTest(status=status):
                body=io.BytesIO(b'{"message":"PRIVATE_SENTINEL /Users/private https://secret.invalid?token=private"}')
                self.transport_error=urllib.error.HTTPError('https://secret.invalid?token=private',status,
                                                       'PRIVATE_SENTINEL',headers,body)
                before=self.requests
                text=self.call('finish')
                self.assertEqual(self.requests-before,1,'diagnostics must not retry')
                self.assertIn('NOT_PERSISTED_ABSENCE_NOT_RECONFIRMED',text)
                self.assertIn('save=false',(self.path/'output').read_text())
                self.assertFalse(self.state()['save_ready'])
                self.assertFalse((self.target/policy.MARKER).exists())
                self.assertNotIn('PRIVATE_SENTINEL',text)
                receipt=[json.loads(line.split(' ',1)[1]) for line in text.splitlines()
                         if line.startswith('NVWA_NATIVE_MAIN_CACHE ') and '"stage": "finish"' in line][0]['api']
                self.assertFalse(receipt['known'])
                self.assertEqual(receipt.get('http_status'),status)
                self.assertEqual(receipt.get('cause'),cause)
                self.assertEqual(receipt.get('diagnostics'),{'request_id':'AB12:CD34:EF56:7890',
                                 'rate_limit_remaining':0,'rate_limit_reset':1792540800,'retry_after_seconds':60})
                self.assertTrue(body.closed)

    def test_cli_http_diagnostics_reject_malformed_duplicate_and_oversize_values(self):
        class UnreadBody(io.BytesIO):
            def read(self,*args): raise AssertionError('remote error body must never be read')
        bad=['PRIVATE_SENTINEL', 'https://secret.invalid?token=private', '/Users/private',
             '1\nPRIVATE_SENTINEL', '-1', '1.0', ' 0', '0 ', '９', '9'*10000,
             'A:B:C', 'A:B:C:D:E:F', 'A'*17+':B:C:D', ':'.join(['A'*16]*4), 'A:B:C:D:E\n']
        fields=['X-GitHub-Request-Id','X-RateLimit-Remaining','X-RateLimit-Reset','Retry-After']
        cases=[]
        for value in bad:
            headers=Message()
            for field in fields: headers[field]=value
            cases.append(headers)
        headers=Message()
        for field in fields:
            headers[field]='0';headers[field]='0'
        cases += [headers, None, {'Retry-After':'PRIVATE_SENTINEL'}]
        headers=Message()
        for field in fields[1:]: headers[field]=str(2**63)
        cases.append(headers)
        for headers in cases:
            with self.subTest(headers=type(headers).__name__):
                body=UnreadBody(b'PRIVATE_SENTINEL'*100000)
                self.transport_error=urllib.error.HTTPError('https://secret.invalid',403,'PRIVATE_SENTINEL',headers,body)
                before=self.requests;text=self.call('prepare');receipt=self.state()['api']
                self.assertEqual(self.requests-before,1)
                self.assertEqual(receipt,{'known':False,'reason':'HTTPError','http_status':403,'cause':'http_forbidden'})
                self.assertNotIn('PRIVATE_SENTINEL',text)
                self.assertNotIn('https://secret.invalid',text)
                self.assertNotIn('/Users/private',text)
                self.assertTrue(body.closed)
        # Malformed status is not published as a typed HTTP fact.
        for status in [True, '403', 999]:
            self.transport_error=urllib.error.HTTPError('https://secret.invalid',status,'PRIVATE_SENTINEL',None,UnreadBody())
            self.assertEqual(self.prepare()['api'],{'known':False,'reason':'HTTPError','cause':'http_error'})

    def test_cli_http_request_id_accepts_observed_four_and_five_group_formats(self):
        for request_id in ['AB12:CD34:EF56:7890', '4FE8:224A50:28245E:2FBA2E:6AD261CB',
                           ':'.join(['A'*16]*3+['B'*13]), ':'.join(['A'*16]*3+['B'*11,'C'])]:
            with self.subTest(request_id=request_id):
                headers=Message();headers['X-GitHub-Request-Id']=request_id
                body=io.BytesIO(b'PRIVATE_SENTINEL')
                self.transport_error=urllib.error.HTTPError('https://secret.invalid',403,'PRIVATE_SENTINEL',headers,body)
                before=self.requests;text=self.call('prepare')
                self.assertEqual(self.requests-before,1)
                self.assertEqual(self.state()['api'],{'known':False,'reason':'HTTPError','cause':'http_forbidden',
                                 'http_status':403,'diagnostics':{'request_id':request_id}})
                self.assertNotIn('PRIVATE_SENTINEL',text)
                self.assertTrue(body.closed)

    def test_cli_transport_and_schema_failures_are_safe_and_distinct(self):
        secret='PRIVATE_SENTINEL https://secret.invalid?token=private /Users/private'
        cases=[(urllib.error.URLError(TimeoutError(secret)),'URLError','timeout'),
               (urllib.error.URLError(ssl.SSLError(secret)),'URLError','tls_error'),
               (urllib.error.URLError(socket.gaierror(secret)),'URLError','dns_error'),
               (urllib.error.URLError(secret),'URLError','transport_error'),
               (TimeoutError(secret),'OSError','timeout'),(ssl.SSLError(secret),'OSError','tls_error'),
               (OSError(secret),'OSError','transport_error')]
        for error,reason,cause in cases:
            self.transport_error=error;before=self.requests;text=self.call('prepare')
            self.assertEqual(self.requests-before,1)
            self.assertEqual(self.state()['api'],{'known':False,'reason':reason,'cause':cause})
            self.assertNotIn('PRIVATE_SENTINEL',text)
        self.transport_error=None
        for remote,cause in [(b'{PRIVATE_SENTINEL','invalid_json'), ({'message':secret},'response_validation_error'),
                             (b'x'*65537,'response_validation_error')]:
            self.remote=remote;text=self.call('prepare')
            self.assertEqual(self.state()['api'],{'known':False,'reason':'ValueError','cause':cause})
            self.assertNotIn('PRIVATE_SENTINEL',text)

    def test_cli_restore_recheck_keeps_latest_failure_and_close_error_stays_unknown(self):
        state=self.prepare();self.present(state);state=self.prepare();self.restored(state)
        class BrokenClose(io.BytesIO):
            def close(self):
                super().close()
                raise RuntimeError('PRIVATE_SENTINEL')
        body=BrokenClose(b'PRIVATE_SENTINEL')
        self.transport_error=urllib.error.HTTPError('https://secret.invalid',503,'PRIVATE_SENTINEL',None,body)
        before=self.requests;text=self.call('restore',**self.action(state['key']))
        self.assertEqual(self.requests-before,1)
        self.assertIn('CLEAN_FALLBACK',text)
        self.assertIn('"http_status": 503',text)
        self.assertIn('"known": false',text)
        restored=[json.loads(line.split(' ',1)[1]) for line in text.splitlines()
                  if line.startswith('NVWA_NATIVE_MAIN_CACHE ') and '"stage": "restore"' in line][0]
        self.assertEqual(restored['api'],state['api'])
        self.assertEqual(self.state()['api'],state['api'])
        self.assertEqual(restored['recheck_api'],{'known':False,'reason':'HTTPError',
                                                'http_status':503,'cause':'http_server_error'})
        self.assertNotIn('PRIVATE_SENTINEL',text)
        self.assertFalse(self.target.exists())
        self.assertTrue(body.closed)
        self.target.mkdir();self.gate_files()
        self.assertIn('NOT_PERSISTED_UNKNOWN_OR_EXISTING',self.call('finish'))
        self.assertFalse((self.target/policy.MARKER).exists())

    def test_cli_absent_seed_requires_real_shared_gates_full_marker_cap_and_persistence(self):
        state=self.prepare();self.call('restore')
        self.target.mkdir();(self.target/'compiled').write_bytes(b'compiled fixture')
        with self.assertRaises(OSError): self.call('finish')
        self.assertFalse((self.target/policy.MARKER).exists())
        self.gate_files()
        text=self.call('finish');self.assertIn('VERIFIED_ABSENT_SEED_READY',text)
        marker=json.loads((self.target/policy.MARKER).read_text())
        self.assertEqual(marker['producer'],state['consumer'])
        self.assertIn('NOT_PERSISTED_UNKNOWN',self.call('persist',MAIN_SAVE_OUTCOME='success'))
        self.present(state)
        args=self.action(state['key'],'MAIN_PERSIST')
        self.assertIn('VERIFIED_PERSISTED',self.call('persist',MAIN_SAVE_OUTCOME='success',**args))
        self.assertIn('NOT_PERSISTED_UNKNOWN',self.call('persist',MAIN_SAVE_OUTCOME='failure',**args))
        self.network=True
        self.assertIn('NOT_PERSISTED_UNKNOWN',self.call('persist',MAIN_SAVE_OUTCOME='success',**args))

    def test_absence_must_be_reconfirmed_and_every_no_save_path_validates_gates(self):
        state=self.prepare();self.call('restore');self.target.mkdir();(self.target/'compiled').write_bytes(b'compiled')
        self.gate_files();self.present(state)
        self.assertIn('NOT_PERSISTED_ABSENCE_NOT_RECONFIRMED',self.call('finish'))
        self.assertFalse((self.target/policy.MARKER).exists())
        # Existing/unverified immutable seed cannot bypass final real gate proof.
        state=self.state();state['api']={'known':True,'entry':self.remote['actions_caches'][0]}
        (self.path/'nvwa-native-main-seed-state.json').write_text(json.dumps(state))
        summary=self.path/'nvwa-b1-motion-matrix/summary.json'
        bad=json.loads(summary.read_text());bad['coverage']['observed']=593;summary.write_text(json.dumps(bad))
        with self.assertRaisesRegex(ValueError,'coverage contract'):self.call('finish')
        self.assertFalse((self.target/policy.MARKER).exists())

    def test_actual_prepare_accepts_only_valid_recorded_sdk_selection(self):
        baseline=self.prepare()
        selections={'SDKROOT':str(self.sdk),'DEVELOPER_DIR':str(self.developer),'MACOSX_DEPLOYMENT_TARGET':'14.0'}
        for name,value in selections.items():
            self.env[name]=value
            state=self.prepare()
            self.assertEqual(state['compatibility']['native_env'][name],value)
            self.assertNotEqual(state['key'],baseline['key'])
            self.env.pop(name)
        self.env.update(selections);state=self.prepare()
        self.assertEqual(state['compatibility']['environment']['MACOSX_DEPLOYMENT_TARGET'],'14.0')
        with self.assertRaisesRegex(ValueError,'environment'):self.call('restore',MACOSX_DEPLOYMENT_TARGET='13.0')
        for name in selections:self.env.pop(name)
        other=self.path/'Other/Developer';other.mkdir(parents=True)
        bad=[{'SDKROOT':'relative-sdk'},{'SDKROOT':str(self.path)},{'SDKROOT':str(self.path/'missing')},
             {'DEVELOPER_DIR':'relative-developer'},{'DEVELOPER_DIR':str(other)}]
        bad += [{'MACOSX_DEPLOYMENT_TARGET':value} for value in ['14 beta','14.0;exit','-1.0','0.0','14.0.0.1','14e0',' 14.0']]
        for values in bad:
            self.assertIn('DISABLED_UNSUPPORTED_IDENTITY',self.call('prepare',**values),values)
        outside=self.path/'outside-compiler';outside.write_bytes(b'outside tool')
        original_query=self.query
        def wrong_toolchain(argv):
            return str(outside) if argv[:2]==['xcrun','--find'] else original_query(argv)
        with patch.object(self,'query',wrong_toolchain):
            self.assertIn('DISABLED_UNSUPPORTED_IDENTITY',self.call('prepare',DEVELOPER_DIR=str(self.developer)))

    def test_owned_physical_ancestor_config_is_rejected(self):
        config=self.path/'.cargo/config.toml';config.parent.mkdir();config.write_text('[net]\noffline=true\n')
        self.assertNotEqual(config.parent,self.root/'.cargo')
        self.assertNotEqual(config.parent,Path(self.env['CARGO_HOME']))
        self.assertIn('DISABLED_UNSUPPORTED_IDENTITY',self.call('prepare'))
        self.assertFalse((self.path/'nvwa-native-main-seed-state.json').exists())

    def test_actual_restore_rejects_self_referential_target_link(self):
        state=self.prepare();self.present(state)
        for links in [[('loop','loop')],[('a','b'),('b','a')],[('dangling','missing')],[('parent','.')]]:
            state=self.prepare();marker=self.restored(state)
            for name,destination in links:(self.target/name).symlink_to(destination)
            compiled=self.target/'compiled'
            rows=[['compiled',compiled.stat().st_mode & 0o777,compiled.stat().st_size,policy.sha(compiled.read_bytes())]]
            rows += [[name,'link',destination] for name,destination in links]
            # A malformed archive can carry its own matching receipt. Supply
            # the stored format explicitly, not the validator under test.
            marker['inventory']={'logical_bytes':compiled.stat().st_size,'entries':len(rows),
                                 'sha256':policy.sha(policy.encoded(sorted(rows)))}
            (self.target/policy.MARKER).write_bytes(policy.encoded(marker))
            text=self.call('restore',**self.action(state['key']))
            self.assertIn('CLEAN_FALLBACK',text,links)
            self.assertNotIn('VERIFIED_RESTORE',text,links)
            self.assertFalse(self.target.exists())

    def test_actual_restore_stops_on_post_cleanup_target_link_race(self):
        state=self.prepare();self.present(state);state=self.prepare();self.restored(state)
        outside=self.path/'empty-outside';outside.mkdir()
        original=policy.os.rmdir
        def raced(path,*args,**kwargs):
            result=original(path,*args,**kwargs)
            if path=='target' and 'dir_fd' in kwargs:
                self.target.symlink_to(outside,target_is_directory=True)
            return result
        # Preserve the actual dir_fd capability while injecting the one OS
        # boundary race; otherwise the capability guard would stop earlier.
        with patch.object(policy.os,'rmdir',raced), patch.object(policy.os,'supports_dir_fd',{*policy.os.supports_dir_fd,raced}):
            with self.assertRaisesRegex(ValueError,'symlink|reappeared'):
                self.call('restore',MAIN_RESTORE_OUTCOME='failure')
        self.assertTrue(self.target.is_symlink())
        self.assertTrue(outside.is_dir())
        self.assertEqual(list(outside.iterdir()),[])
        self.assertEqual(self.state()['status'],'PREPARED','unsafe cleanup cannot attest fallback')

    def test_real_target_marker_cap_and_unsafe_cleanup_refusal(self):
        state=self.prepare();self.call('restore');self.gate_files()
        self.target.mkdir();(self.target/'compiled').write_bytes(b'x'*65536)
        for index in range(315): (self.target/str(index)).symlink_to('./'*100+'compiled')
        with patch.object(policy.shared,'CAP',131072):
            with self.assertRaisesRegex(ValueError,'exact marker exceeds cap'):self.call('finish')
        self.assertFalse((self.target/policy.MARKER).exists())
        for path in self.target.iterdir(): path.unlink()
        self.target.rmdir()
        outside=self.path/'outside';outside.mkdir();(outside/'sentinel').write_text('preserved')
        self.target.symlink_to(outside,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'symlink'):self.call('restore')
        self.assertEqual((outside/'sentinel').read_text(),'preserved')

    def test_later_build_environment_and_key_coherence_are_required(self):
        state=self.prepare()
        for values in [{'CARGO_BUILD_JOBS':'2'}, {'CC':'other'}, {'ImageVersion':'changed'}, {'RUSTFLAGS':'changed'}]:
            with self.assertRaisesRegex(ValueError,'environment'): self.call('restore',**values)
        path=self.path/'nvwa-native-main-seed-state.json'
        for field in ['key','version']:
            path.write_text(json.dumps({**state,field:'foreign'}))
            with self.assertRaisesRegex(ValueError,'key/archive'):self.call('restore')
        path.write_text(json.dumps(state))
        with self.assertRaisesRegex(ValueError,'no verified save'):self.call('persist')

    def test_real_offline_cargo_rechecks_changed_ordinary_source_with_natural_mtime(self):
        # Real compiler, no dependency downloads or performance assertion. The
        # explicit cargo path bypasses the enclosing CI timing PATH shim so this
        # disposable checkout cannot inject identities into the outer report.
        cargo=subprocess.check_output(['rustup','which','--toolchain','1.95.0','cargo'],text=True).strip()
        package=self.path/'tiny-cargo';(package/'src').mkdir(parents=True)
        (package/'Cargo.toml').write_text('[package]\nname="native-cache-source-control"\nversion="0.0.0"\nedition="2024"\n[workspace]\n')
        source=package/'src/main.rs'
        environment={key:value for key,value in os.environ.items() if not key.startswith(('NVWA_TIMING_','CARGO_', 'RUST'))
                     and key not in ['GITHUB_WORKFLOW','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_JOB','GITHUB_SHA','NVWA_CI_HEAD_SHA']}
        environment.update(CARGO_TARGET_DIR=str(package/'target'),RUSTUP_TOOLCHAIN='1.95.0')
        command=[cargo,'run','--offline','--quiet','--manifest-path',str(package/'Cargo.toml')]
        source.write_text('fn main(){println!("before-source-edit");}\n')
        first=subprocess.run(command,capture_output=True,text=True,env=environment,check=True)
        self.assertEqual(first.stdout.strip(),'before-source-edit')
        before=source.stat().st_mtime_ns
        source.write_text('fn main(){println!("after-source-edit");}\n')
        self.assertGreater(source.stat().st_mtime_ns,before)
        second=subprocess.run(command,capture_output=True,text=True,env=environment,check=True)
        self.assertEqual(second.stdout.strip(),'after-source-edit')
        self.assertEqual(source.read_text(),'fn main(){println!("after-source-edit");}\n')

    def test_missing_or_duplicate_shoulder_step_rejects_existing_workflow_contract(self):
        workflow_path=ROOT/'.github/workflows/ci.yml'
        original=workflow_path.read_text()
        read_text=Path.read_text
        for addition,message in WORKFLOW_ADDITIONS:
            for replacement in ('',addition+addition):
                mutant=original.replace(addition,replacement)
                def read(path,*args,**kwargs):
                    return mutant if path==workflow_path else read_text(path,*args,**kwargs)
                with self.subTest(addition=message,step_count=mutant.count(addition)),patch.object(Path,'read_text',read):
                    with self.assertRaisesRegex(AssertionError,message):
                        self.test_workflow_original_bodies_main_scope_and_trial_phase_policy()

    def test_linux_b1_overlay_rejects_unapproved_policy_and_fetch_changes(self):
        workflow_path = ROOT / '.github/workflows/ci.yml'
        original = workflow_path.read_text()
        read_text = Path.read_text
        commands = B1_FETCH_STEP.splitlines(keepends=True)[2:]
        mutations = [original.replace(B1_LINUX_HEADER, B1_MACOS_HEADER),
                     original.replace('name: Linux B1 source', 'name: Other B1 source'),
                     original.replace(B1_LINUX_HEADER, B1_LINUX_HEADER.replace('ubuntu-24.04', 'ubuntu-latest')),
                     original.replace(B1_LINUX_HEADER, B1_LINUX_HEADER.replace('needs: portable', 'needs: native-and-wasm')),
                     original.replace(B1_FETCH_STEP, ''),
                     original.replace(B1_FETCH_STEP, B1_FETCH_STEP*2),
                     original.replace(B1_FETCH_STEP+B1_PREPARE_STEP, B1_PREPARE_STEP+B1_FETCH_STEP),
                     original.replace(B1_FETCH_STEP, B1_FETCH_STEP.replace('        run: |', '        shell: bash\n        run: |'))]
        mutations.extend([
            original.replace(B1_LINUX_HEADER, B1_LINUX_HEADER.replace('Linux B1', 'macOS B1')),
            original.replace(B1_LINUX_HEADER, B1_LINUX_HEADER.replace('ubuntu-24.04', 'macos-14')),
            original.replace(B1_LINUX_HEADER, B1_LINUX_HEADER*2),
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
                    self.test_workflow_original_bodies_main_scope_and_trial_phase_policy()

    def test_macos15_overlay_rejects_partial_mixed_and_unrelated_changes(self):
        workflow_path = ROOT / '.github/workflows/ci.yml'
        original = workflow_path.read_text()
        read_text = Path.read_text
        mutations = []
        for header in MACOS15_HEADERS:
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
        for index, mutant in enumerate(mutations):
            self.assertNotEqual(mutant, original)
            def read(path, *args, **kwargs):
                return mutant if path == workflow_path else read_text(path, *args, **kwargs)
            with self.subTest(mutation=index), patch.object(Path, 'read_text', read):
                with self.assertRaises(AssertionError):
                    self.test_workflow_original_bodies_main_scope_and_trial_phase_policy()

    def test_workflow_original_bodies_main_scope_and_trial_phase_policy(self):
        text=(ROOT/'.github/workflows/ci.yml').read_text()
        text = historical_macos_workflow(text, self)
        for addition,message in WORKFLOW_ADDITIONS:
            self.assertEqual(text.count(addition),1,message)
        blocks=re.findall(r'(?ms)^ +# native-main-cache begin\n.*?^ +# native-main-cache end\n',text)
        self.assertEqual(len(blocks),3)
        body=''.join(blocks)
        self.assertEqual(body.count('timeout-minutes: 4'),3)
        self.assertEqual(body.count('continue-on-error: true'),3)
        self.assertEqual(body.count('@'+policy.ACTION),3)
        self.assertNotIn('restore-keys:',body)
        self.assertNotIn('ACTIONS_RUNTIME_TOKEN:',body)
        self.assertIn("steps.main-prepare.outputs.restore == 'true'",body)
        self.assertLess(text.index('policy.py restore'),text.index('Run workspace CPU tests'))
        self.assertGreater(text.index('policy.py finish'),text.index('Report existing command timing',text.index('  native-and-wasm:')))
        historical=historical_b1_workflow(text, self)
        stripped=re.sub(r'(?ms)^  # native-cache-trial begin\n.*?^  # native-cache-trial end\n','',historical)
        stripped=re.sub(r'(?ms)^ +# native-cache-trial begin\n.*?^ +# native-cache-trial end\n','',stripped)
        stripped=re.sub(r'(?ms)^ +# native-main-cache begin\n.*?^ +# native-main-cache end\n','',stripped)
        for addition,message in WORKFLOW_ADDITIONS:
            stripped=stripped.replace(addition,'')
        self.assertEqual(hashlib.sha256(stripped.encode()).hexdigest(),'5bdd5efa6b48150c2fbf19eb9cb1b9f1ae64303caea87bfc9c2615b58c201302')
        self.assertEqual(json.loads((ROOT/'experiments/83-native-cache-trial/phase.json').read_text()),{'phase':'adopted'})
        native=text.split('  native-and-wasm:\n',1)[1].split('  b1-source-regression:\n',1)[0]
        self.assertEqual(native.count('timeout-minutes: 4'),6)
        self.assertIn("if: ${{ steps.main-finish.outputs.save == 'true' }}",body)
        self.assertFalse((HERE/'__init__.py').exists(),'new group cannot amplify the recursive trial regression')


if __name__=='__main__':
    unittest.main(verbosity=2)
