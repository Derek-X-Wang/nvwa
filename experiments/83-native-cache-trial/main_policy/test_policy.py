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
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.parse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location('main_native_policy', HERE / 'policy.py')
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


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
        self.assertEqual(timeout, 20)
        self.assertFalse(request.has_header('Authorization'))
        url = urllib.parse.urlsplit(request.full_url)
        self.assertEqual(url.scheme+'://'+url.netloc+url.path, 'https://api.github.com/repos/'+policy.REPO+'/actions/caches')
        self.assertEqual(urllib.parse.parse_qs(url.query)['ref'], [policy.REF])
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

    def test_workflow_original_bodies_main_scope_and_trial_phase_policy(self):
        text=(ROOT/'.github/workflows/ci.yml').read_text()
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
        stripped=re.sub(r'(?ms)^  # native-cache-trial begin\n.*?^  # native-cache-trial end\n','',text)
        stripped=re.sub(r'(?ms)^ +# native-cache-trial begin\n.*?^ +# native-cache-trial end\n','',stripped)
        stripped=re.sub(r'(?ms)^ +# native-main-cache begin\n.*?^ +# native-main-cache end\n','',stripped)
        self.assertEqual(hashlib.sha256(stripped.encode()).hexdigest(),'5bdd5efa6b48150c2fbf19eb9cb1b9f1ae64303caea87bfc9c2615b58c201302')
        self.assertEqual(json.loads((ROOT/'experiments/83-native-cache-trial/phase.json').read_text()),{'phase':'adopted'})
        native=text.split('  native-and-wasm:\n',1)[1].split('  b1-source-regression:\n',1)[0]
        self.assertEqual(native.count('timeout-minutes: 4'),6)
        self.assertIn("if: ${{ steps.main-finish.outputs.save == 'true' }}",body)
        self.assertFalse((HERE/'__init__.py').exists(),'new group cannot amplify the recursive trial regression')


if __name__=='__main__':
    unittest.main(verbosity=2)
