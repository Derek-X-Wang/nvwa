"""Real child-process protocol/lifecycle controls; no WebGPU or image-quality claim."""
import contextlib
import copy
import errno
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('review_motion', Path(__file__).with_name('review-motion.py'))
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)

FAKE_PREVIEW = r'''
import argparse, hashlib, json, os, signal, sys, time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
p = argparse.ArgumentParser()
for name in ('work','seconds','output','preview-root','assets','cli','port','timeout'):
    p.add_argument('--'+name, required=True)
a = p.parse_args()
mode = os.environ.get('NVWA_REVIEW_TEST_MODE','')
if mode == 'early-preview':
    print(json.dumps({'status':'failed','error':'controlled early exit'}),file=sys.stderr,flush=True)
    sys.exit(3)
if mode == 'hang':
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    while True: time.sleep(.05)
out = Path(a.output)
out.mkdir()
work = Path(a.work).read_bytes()
doc = json.loads(work)
(out/'work.nvwa.json').write_bytes(work)
result = {}
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_GET(self):
        if mode == 'second-fail' and float(a.seconds) == 1:
            result.update(status='failed',error='controlled render failure')
        else:
            # Deliberately synthetic bytes. These tests verify orchestration only.
            image = b'controlled child payload '+a.seconds.encode()+work
            (out/'actual.png').write_bytes(image)
            request = {'work_sha256':hashlib.sha256(work).hexdigest(),
                       'document_revision':doc['revision'],'camera':doc['stage']['camera'],
                       'seconds':float(a.seconds),'effective_seconds':float(a.seconds)}
            if mode == 'wrong-identity': request['work_sha256'] = 'old-work'
            seconds = float(a.seconds)
            runtime = {'seconds':seconds}
            if mode == 'range-clearance':
                left = {0:.1, .3:.6, .6:.4, .9:.00004, 1:.00004}[seconds]
                runtime['foot_clearance'] = {'unit':'cm','left_cm':left,'right_cm':2.0}
            result.update(status='rendered', request=request,
                          runtime=runtime,
                          image=str(out/'actual.png'),work=str(out/'work.nvwa.json'),
                          png_sha256=hashlib.sha256(image).hexdigest())
            if mode == 'stale-image': result['image'] = str(out.parent.parent/'previous-actual.png')
        (out/'receipt.json').write_text(json.dumps(result))
        self.send_response(200); self.end_headers(); self.wfile.write(b'controlled')
server = HTTPServer(('127.0.0.1',int(a.port)),Handler)
server.timeout=.05
url=f'http://127.0.0.1:{server.server_port}/controlled-token/preview.html?player=1'
print('ordinary child log before event',file=sys.stderr,flush=True)
print(json.dumps({'event':'open_browser','url':url,'output':str(out)}),file=sys.stderr,flush=True)
while not result: server.handle_request()
server.server_close()
print(json.dumps(result),flush=True)
sys.exit(0 if result['status']=='rendered' else 1)
'''

FAKE_CHROME = r'''
import os, signal, subprocess, sys, time
from urllib.request import urlopen
mode = os.environ.get('NVWA_REVIEW_TEST_MODE','')
if mode == 'early-chrome': sys.exit(7)
if mode == 'ignore-term': signal.signal(signal.SIGTERM, signal.SIG_IGN)
if mode == 'browser-child':
    child = subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])
    print(child.pid,flush=True)
    def stop(signum,frame):
        child.wait(timeout=2)
        sys.exit(0)
    signal.signal(signal.SIGTERM,stop)
with urlopen(sys.argv[-1],timeout=3) as response: response.read()
while True: time.sleep(.05)
'''


class ReviewControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='nvwa-review-controls-')
        self.root = Path(self.temporary.name)
        self.preview = self.root/'controlled-preview.py'
        self.preview.write_text(FAKE_PREVIEW)
        self.chrome = self.root/'controlled-chrome'
        self.chrome.write_text('#!'+sys.executable+'\n'+FAKE_CHROME)
        self.chrome.chmod(0o700)
        self.cli = self.root/'controlled-cli'
        self.cli.write_text('#!'+sys.executable+'\nimport os,signal,sys,time\n'
                            'if os.environ.get("NVWA_REVIEW_TEST_MODE")=="validator-ignore-term":\n'
                            '    signal.signal(signal.SIGTERM,signal.SIG_IGN)\n'
                            '    while True: time.sleep(.05)\n'
                            'print("controlled base validation")\n'
                            'sys.exit(2 if os.environ.get("NVWA_REVIEW_TEST_MODE")=="base-invalid" else 0)\n')
        self.cli.chmod(0o700)
        self.assets = self.root/'assets'
        self.site = self.root/'site'
        self.assets.mkdir(); self.site.mkdir()
        build_hashes = {}
        for name in ('preview.html', 'nvwa_preview.js', 'nvwa_preview_bg.wasm'):
            data = ('synthetic preflight fixture ' + name).encode()
            (self.site/name).write_bytes(data)
            build_hashes[name] = hashlib.sha256(data).hexdigest()
        (self.site/'build-receipt.json').write_text(json.dumps({
            'source_sha256': {}, 'output_sha256': build_hashes,
        }))
        example = Path(__file__).resolve().parent.parent/'examples/agent-visual-preview/full-body.nvwa.json'
        self.base = self.root/'base.nvwa.json'
        self.base.write_bytes(example.read_bytes())
        self.views = {}
        for name, azimuth in [('front',0),('side',90)]:
            work = json.loads(self.base.read_bytes())
            work['revision'] += 1
            work['stage']['camera']['azimuth_degrees'] = azimuth
            path = self.root/(name+'.nvwa.json')
            path.write_text(json.dumps(work))
            self.views[name] = path
        self.output = self.root/'result'
        self.patches = [patch.object(review,'PREVIEW',self.preview),
                        patch.object(review,'TERM_GRACE',.15), patch.object(review,'KILL_GRACE',.5)]
        for item in self.patches: item.start()

    def tearDown(self):
        result = self._outcome.result if self._outcome is not None else None
        if result is not None and any(test is self or getattr(test,'test_case',None) is self
                                      for test,_ in result.failures+result.errors):
            print('\nCONTROLLED FAILURE EVIDENCE\n'+self.diagnostics(),file=sys.stderr)
        for item in reversed(self.patches): item.stop()
        self.temporary.cleanup()

    def diagnostics(self, result=None):
        evidence = {'result':getattr(self,'last_result',None) if result is None else result,'logs':{}}
        for path in self.output.rglob('*'):
            if path.is_file() and (path.suffix == '.log' or 'cleanup' in path.name
                                   or path.name in ('base-validation.json','frame.json')):
                evidence['logs'][str(path.relative_to(self.output))] = path.read_text(errors='replace')
        return json.dumps(evidence,indent=2)

    def command(self, seconds=(0,1), views=('front','side')):
        args = ['--chrome',str(self.chrome),'--work',str(self.base),'--output',str(self.output),
                '--preview-root',str(self.site),'--assets',str(self.assets),'--cli',str(self.cli),
                '--port','0','--timeout','2','--total-timeout','15']
        for view in views: args += ['--view',view+'='+str(self.views[view])]
        for seconds_value in seconds: args += ['--seconds',str(seconds_value)]
        return args

    def run_review(self, mode='', args=None):
        stdout = io.StringIO()
        with patch.dict(os.environ, {'NVWA_REVIEW_TEST_MODE':mode}), contextlib.redirect_stdout(stdout):
            code = review.main(self.command() if args is None else args)
        result = json.loads(stdout.getvalue())
        self.last_result = result
        return code, result

    def assert_cleanup(self, result):
        for frame in result['frames']:
            self.assertTrue(frame['chrome_profile_removed'],self.diagnostics(result))
            for owned in frame['cleanup'].values():
                self.assertTrue(owned['process_group_absent'],self.diagnostics(result))
                with self.assertRaises(ProcessLookupError,msg=self.diagnostics(result)): os.killpg(owned['pid'],0)

    def test_build_mismatch_fails_before_any_child_starts(self):
        receipt_path = self.site/'build-receipt.json'
        receipt = json.loads(receipt_path.read_bytes())
        receipt['source_sha256'] = {'web/preview.html': '0' * 64}
        receipt_path.write_text(json.dumps(receipt))
        with patch.object(review.subprocess, 'Popen', side_effect=AssertionError('child started')):
            code, result = self.run_review()
        self.assertEqual(code, 1)
        self.assertEqual(result['frames'], [])
        self.assertIn('Preview build source changed: web/preview.html', result['error'])
        self.assertIn('scripts/build-preview-web.sh <new-preview-root>', result['error'])
        self.assertFalse((self.output/'base-validation.json').exists())

    def test_presets_render_ordered_camera_only_copies_without_editing_input(self):
        original = self.base.read_bytes()
        args = self.command(seconds=(0,), views=())
        args += ['--camera', 'side', '--camera', 'front', '--elevation', '5', '--distance', '7.45']
        code, result = self.run_review(args=args)
        self.assertEqual(code, 0, self.diagnostics(result))
        self.assertEqual(self.base.read_bytes(), original)
        self.assertEqual([frame['view'] for frame in result['frames']], ['side', 'front'])
        for frame, angle in zip(result['frames'], (90, 0), strict=True):
            rendered = json.loads(Path(frame['capture']['work']).read_bytes())
            expected = json.loads(original)
            expected['stage']['camera'].update(azimuth_degrees=angle, elevation_degrees=5, distance=7.45)
            self.assertEqual(rendered, expected)
        self.assert_cleanup(result)

    def test_serial_order_distinct_frames_exact_inputs_and_clean_owned_processes(self):
        before = {path:path.read_bytes() for path in [self.base,*self.views.values()]}
        code, result = self.run_review()
        self.assertEqual(code,0,self.diagnostics(result))
        self.assertEqual(result['status'],'rendered')
        self.assertEqual([(frame['view'],frame['requested_seconds']) for frame in result['frames']],
                         [('front',0),('front',1),('side',0),('side',1)])
        self.assertEqual([frame['index'] for frame in result['frames']],list(range(4)))
        for view in result['views']:
            self.assertEqual(Path(view['snapshot']).read_bytes(),before[self.views[view['name']]])
        self.assertEqual(Path(result['base_work']['snapshot']).read_bytes(),before[self.base])
        self.assertEqual({path:path.read_bytes() for path in before},before)
        self.assertEqual(len({frame['capture']['image'] for frame in result['frames']}),4)
        self.assertEqual(len({frame['cleanup']['chrome']['pid'] for frame in result['frames']}),4)
        self.assert_cleanup(result)
        self.assertEqual(json.loads((self.output/'receipt.json').read_bytes()),result)
        validation = json.loads((self.output/'base-validation.json').read_bytes())
        self.assertEqual(validation['exit_code'],0)
        self.assertEqual(validation['command'][1],'validate')

    def test_partial_failure_keeps_first_image_and_never_reports_batch_success(self):
        code, result = self.run_review('second-fail')
        self.assertEqual(code,1,self.diagnostics())
        self.assertEqual(result['status'],'failed')
        self.assertEqual([frame['status'] for frame in result['frames']],['rendered','failed'])
        self.assertTrue(Path(result['frames'][0]['capture']['image']).is_file())
        self.assertEqual(result['expected_frame_count'],4)
        self.assert_cleanup(result)

    def test_range_writes_curves_and_brackets_after_temporary_near_floor_visit(self):
        args = self.command(seconds=(), views=('side',))
        args += ['--start', '0', '--end', '1', '--step', '0.3']
        code, result = self.run_review('range-clearance', args)
        self.assertEqual(code, 0, self.diagnostics(result))
        self.assertEqual(result['requested_seconds'], [0, .3, .6, .9, 1])
        paths = result['foot_clearance']
        side = json.loads(Path(paths['summary']).read_bytes())['views']['side']
        left = side['feet']['left']
        self.assertEqual(left['near_floor']['previous_sample']['requested_seconds'], .3)
        self.assertEqual(left['near_floor']['first_sample']['requested_seconds'], .6)
        self.assertEqual(left['stable_near_floor']['previous_sample']['requested_seconds'], .6)
        self.assertEqual(left['stable_near_floor']['first_sample']['requested_seconds'], .9)
        self.assertIsNone(side['feet']['right']['near_floor'])
        self.assertIsNone(side['feet']['right']['stable_near_floor'])
        self.assertTrue(Path(side['curve']).is_file())
        self.assertEqual(len(Path(paths['csv']).read_text().splitlines()), 6)
        self.assert_cleanup(result)

    def test_range_rejects_oversampling_and_duplicate_preview_times_before_children(self):
        for name, bounds, message in (
            ('cap', ('0','1','.05'), '24 total frames'),
            ('duplicate', ('1','1.1','.000000001'), 'duplicate'),
        ):
            with self.subTest(name=name):
                self.output = self.root / name
                args = self.command(seconds=())
                args += [flag for pair in zip(('--start','--end','--step'), bounds) for flag in pair]
                code, result = self.run_review(args=args)
                self.assertEqual(code, 1, self.diagnostics(result))
                self.assertIn(message, result['error'])
                self.assertFalse((self.output/'base-validation.json').exists())

    def test_mismatched_child_work_is_rejected(self):
        code, result = self.run_review('wrong-identity',self.command(seconds=(0,),views=('front',)))
        self.assertEqual(code,1,self.diagnostics())
        self.assertIn('differs from this frame',result['error'])
        self.assert_cleanup(result)

    def test_receipt_cannot_reuse_an_image_path_from_another_frame(self):
        code, result = self.run_review('stale-image',self.command(seconds=(0,),views=('front',)))
        self.assertEqual(code,1,self.diagnostics())
        self.assertIn('files or hashes differ',result['error'])
        self.assert_cleanup(result)

    def test_outside_camera_revision_change_is_rejected_before_children(self):
        changed = json.loads(self.views['side'].read_bytes())
        changed['stage']['quality'] = 'low'
        self.views['side'].write_text(json.dumps(changed))
        code, result = self.run_review()
        self.assertEqual(code,1,self.diagnostics())
        self.assertIn('outside camera/revision',result['error'])
        self.assertEqual(result['frames'],[])
        self.assertFalse((self.output/'frames').exists())

    def test_bool_number_crossover_does_not_pass_camera_only_comparison(self):
        base = {'revision':1,'stage':{'camera':{},'value':0}}
        changed = copy.deepcopy(base)
        changed['stage']['value'] = False
        self.assertNotEqual(review.camera_independent_work(base),review.camera_independent_work(changed))

    def test_original_base_validation_failure_stops_before_browser(self):
        code, result = self.run_review('base-invalid')
        self.assertEqual(code,1,self.diagnostics())
        self.assertIn('Original base Work CLI validation failed',result['error'])
        self.assertEqual(json.loads((self.output/'base-validation.json').read_bytes())['exit_code'],2)
        self.assertEqual(result['frames'],[])
        self.assertFalse((self.output/'frames').exists())

    def test_early_preview_and_chrome_exits_are_explicit_and_clean(self):
        for mode, text in [('early-preview','Preview exited 3'),('early-chrome','Chrome exited')]:
            with self.subTest(mode=mode):
                self.output = self.root/mode
                code, result = self.run_review(mode,self.command(seconds=(0,),views=('front',)))
                self.assertEqual(code,1,self.diagnostics())
                self.assertIn(text,result['error'])
                self.assert_cleanup(result)

    def test_total_timeout_kills_even_a_term_ignoring_child(self):
        args = self.command(seconds=(0,),views=('front',))
        args[args.index('--total-timeout')+1] = '.2'
        started = time.monotonic()
        code, result = self.run_review('hang',args)
        self.assertEqual(code,1,self.diagnostics())
        self.assertIn('Total review deadline',result['error'])
        self.assertLess(time.monotonic()-started,2)
        self.assert_cleanup(result)

    def test_chrome_term_escalation_reaps_process_before_profile_removal(self):
        code, result = self.run_review('ignore-term',self.command(seconds=(0,),views=('front',)))
        self.assertEqual(code,0,self.diagnostics())
        self.assert_cleanup(result)

    def test_cancellation_during_frame_cleanup_finishes_owned_group(self):
        original = os.killpg
        observed = []
        fired = False
        def interrupt_after_term(pgid, signum):
            nonlocal fired
            returned = original(pgid,signum)
            marker = self.output/'frames/00-front/processes.json'
            chrome = json.loads(marker.read_bytes()).get('chrome') if marker.exists() else None
            if pgid == chrome and signum == signal.SIGTERM and not fired:
                observed.append(pgid)
                fired = True
                os.kill(os.getpid(),signal.SIGINT)
            return returned
        try:
            with patch.object(review.os,'killpg',interrupt_after_term):
                code, result = self.run_review('ignore-term',self.command(seconds=(0,),views=('front',)))
            self.assertTrue(fired,self.diagnostics(result))
            self.assertEqual(code,1,self.diagnostics(result))
            self.assertIn('interrupted by signal',result['error'],self.diagnostics(result))
            self.assert_cleanup(result)
        finally:
            for pgid in observed:
                try: original(pgid,signal.SIGKILL)
                except ProcessLookupError: pass
                try: os.waitpid(pgid,0)
                except ChildProcessError: pass

    def test_cancellation_during_base_validator_cleanup_finishes_owned_group(self):
        original = os.killpg
        observed = []
        def interrupt_after_term(pgid, signum):
            returned = original(pgid,signum)
            if signum == signal.SIGTERM and not observed:
                observed.append(pgid)
                os.kill(os.getpid(),signal.SIGTERM)
            return returned
        args = self.command(seconds=(0,),views=('front',))
        args[args.index('--total-timeout')+1] = '.2'
        try:
            with patch.object(review.os,'killpg',interrupt_after_term):
                code, result = self.run_review('validator-ignore-term',args)
            self.assertTrue(observed,self.diagnostics(result))
            self.assertEqual(code,1,self.diagnostics(result))
            for pgid in observed:
                with self.assertRaises(ProcessLookupError,msg=self.diagnostics(result)): original(pgid,0)
            validation = json.loads((self.output/'base-validation.json').read_bytes())
            self.assertTrue(validation['process_group_absent'],self.diagnostics(result))
        finally:
            for pgid in observed:
                try: original(pgid,signal.SIGKILL)
                except ProcessLookupError: pass
                try: os.waitpid(pgid,0)
                except ChildProcessError: pass

    def test_permission_unknown_and_denied_term_require_eventual_real_esrch(self):
        original = os.killpg
        denied_probes = 0
        def transient_denial(pgid, signum):
            nonlocal denied_probes
            marker = self.output/'frames/00-front/processes.json'
            chrome = json.loads(marker.read_bytes()).get('chrome') if marker.exists() else None
            if pgid == chrome:
                if signum == 0 and denied_probes < 2:
                    denied_probes += 1
                    raise PermissionError(errno.EPERM,'controlled unknown group absence')
                if signum == signal.SIGTERM:
                    raise PermissionError(errno.EPERM,'controlled undelivered TERM')
            return original(pgid,signum)
        with patch.object(review.os,'killpg',transient_denial):
            code, result = self.run_review(args=self.command(seconds=(0,),views=('front',)))
        self.assertEqual(code,0,self.diagnostics(result))
        self.assertEqual(denied_probes,2,self.diagnostics(result))
        chrome = result['frames'][0]['cleanup']['chrome']
        events = [json.loads(line) for line in Path(chrome['audit']).read_text().splitlines()]
        events = [event for event in events if event['pgid'] == chrome['pgid']]
        self.assertTrue(any(event['operation']=='signal0' and event['errno']==errno.EPERM
                            and event['state']=='unknown' for event in events),self.diagnostics(result))
        self.assertTrue(any(event['operation']=='SIGTERM' and event['errno']==errno.EPERM
                            and event['signal_delivered'] is False for event in events),self.diagnostics(result))
        self.assertEqual(events[-1]['errno'],errno.ESRCH,self.diagnostics(result))
        self.assertTrue(all({'phase','pgid','operation','errno','elapsed_seconds','direct_child_returncode'}
                            <= set(event) for event in events),self.diagnostics(result))
        self.assert_cleanup(result)

    def test_persistent_permission_unknown_fails_and_retains_profile(self):
        original = os.killpg
        original_popen = subprocess.Popen
        processes = []
        observed = []
        def remember_process(*args, **kwargs):
            process = original_popen(*args,**kwargs)
            processes.append(process)
            return process
        def persistent_denial(pgid, signum):
            marker = self.output/'frames/00-front/processes.json'
            chrome = json.loads(marker.read_bytes()).get('chrome') if marker.exists() else None
            if pgid == chrome:
                if pgid not in observed: observed.append(pgid)
                raise PermissionError(errno.EPERM,'controlled persistent unknown absence')
            return original(pgid,signum)
        try:
            with (patch.object(review.os,'killpg',persistent_denial),
                  patch.object(review.subprocess,'Popen',remember_process)):
                code, result = self.run_review(args=self.command(seconds=(0,),views=('front',)))
            self.assertEqual(code,1,self.diagnostics(result))
            self.assertIn('Cannot prove owned process group',result['error'],self.diagnostics(result))
            frame = result['frames'][0]
            self.assertFalse(frame['chrome_profile_removed'],self.diagnostics(result))
            self.assertFalse(frame['cleanup']['chrome']['process_group_absent'],self.diagnostics(result))
            original(observed[0],0)  # Our controlled process really remains; no absence was invented.
            events = [json.loads(line) for line in Path(frame['cleanup']['chrome']['audit']).read_text().splitlines()]
            self.assertTrue(any(event['phase']=='kill-wait' and event['errno']==errno.EPERM
                                for event in events),self.diagnostics(result))
            self.assertTrue(frame['cleanup']['preview']['process_group_absent'],self.diagnostics(result))
        finally:
            for pgid in observed:
                try: original(pgid,signal.SIGKILL)
                except ProcessLookupError: pass
            for process in processes:
                process.wait(timeout=1)

    def test_owned_browser_descendant_is_stopped_with_its_process_group(self):
        code, result = self.run_review('browser-child',self.command(seconds=(0,),views=('front',)))
        self.assertEqual(code,0,self.diagnostics())
        self.assert_cleanup(result)
        child_pid = int((Path(result['frames'][0]['directory'])/'chrome.stdout.log').read_text())
        with self.assertRaises(ProcessLookupError): os.kill(child_pid,0)

    def test_interrupts_stop_owned_preview_and_publish_failure_receipt(self):
        bootstrap = '''
import importlib.util,sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]).parent))
spec=importlib.util.spec_from_file_location('review_motion',sys.argv[1])
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.PREVIEW=Path(sys.argv[2]);module.TERM_GRACE=.15;module.KILL_GRACE=.5
raise SystemExit(module.main(sys.argv[3:]))
'''
        for signum in (signal.SIGTERM,signal.SIGINT):
            with self.subTest(signal=signum):
                self.output = self.root/('interrupt-'+str(signum))
                environment = dict(os.environ,NVWA_REVIEW_TEST_MODE='hang')
                process = subprocess.Popen([sys.executable,'-B','-c',bootstrap,str(Path(review.__file__)),
                                            str(self.preview),*self.command(seconds=(0,),views=('front',))],
                                           stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=environment,
                                           start_new_session=True)
                marker = self.output/'frames/00-front/processes.json'
                try:
                    deadline = time.monotonic()+3
                    while not marker.exists() and process.poll() is None and time.monotonic()<deadline:
                        time.sleep(.02)
                    self.assertTrue(marker.exists(),'known child-start lifecycle seam was not reached')
                    process.send_signal(signum)
                    stdout, stderr = process.communicate(timeout=3)
                    self.assertEqual(process.returncode,1,stderr.decode())
                    result = json.loads(stdout)
                    self.assertIn('interrupted by signal',result['error'])
                    self.assertEqual(json.loads((self.output/'receipt.json').read_bytes()),result)
                    self.assert_cleanup(result)
                finally:
                    if process.poll() is None:
                        process.kill();process.wait(timeout=1)
                    for pipe in (process.stdout,process.stderr): pipe.close()
                    if marker.exists():
                        for pid in json.loads(marker.read_bytes()).values():
                            try: os.killpg(pid,signal.SIGKILL)
                            except ProcessLookupError: pass

    def test_busy_port_fails_without_starting_browser(self):
        with socket.socket() as occupied:
            occupied.bind(('127.0.0.1',0)); occupied.listen()
            args = self.command(seconds=(0,),views=('front',))
            args[args.index('--port')+1] = str(occupied.getsockname()[1])
            code, result = self.run_review(args=args)
        self.assertEqual(code,1,self.diagnostics())
        self.assertEqual(set(result['frames'][0]['cleanup']),{'preview'})
        self.assert_cleanup(result)

    def test_existing_output_is_unchanged_and_missing_browser_leaves_failure_receipt(self):
        self.output.mkdir()
        marker = self.output/'receipt.json'
        marker.write_text('previous result')
        code, result = self.run_review()
        self.assertEqual(code,1,self.diagnostics())
        self.assertEqual(marker.read_text(),'previous result')
        self.output = self.root/'missing-browser'
        args = self.command()
        args[args.index('--chrome')+1] = str(self.root/'absent-chrome')
        code, result = self.run_review(args=args)
        self.assertEqual(code,1,self.diagnostics())
        self.assertEqual(json.loads((self.output/'receipt.json').read_bytes()),result)
        self.assertEqual(result['frames'],[])

    def test_invalid_request_bounds_fail_before_children(self):
        for option, value in [('--timeout','nan'),('--total-timeout','601'),('--seconds','nan')]:
            with self.subTest(option=option):
                self.output = self.root/('invalid-'+option[2:])
                args = self.command()
                args[args.index(option)+1] = value
                code, result = self.run_review(args=args)
                self.assertEqual(code,1,self.diagnostics())
                self.assertEqual(result['frames'],[])
        self.output = self.root/'too-many-frames'
        code, result = self.run_review(args=self.command(seconds=tuple(range(13))))
        self.assertEqual(code,1,self.diagnostics())
        self.assertIn('24 total frames',result['error'])

    def test_second_run_uses_new_output_and_processes(self):
        code, first = self.run_review(args=self.command(seconds=(0,),views=('front',)))
        self.assertEqual(code,0,self.diagnostics())
        self.output = self.root/'second-result'
        code, second = self.run_review(args=self.command(seconds=(0,),views=('front',)))
        self.assertEqual(code,0,self.diagnostics())
        self.assertNotEqual(first['frames'][0]['capture']['image'],second['frames'][0]['capture']['image'])
        self.assertNotEqual(first['frames'][0]['cleanup']['chrome']['pid'],second['frames'][0]['cleanup']['chrome']['pid'])
        self.assert_cleanup(first); self.assert_cleanup(second)


if __name__ == '__main__':
    unittest.main()
