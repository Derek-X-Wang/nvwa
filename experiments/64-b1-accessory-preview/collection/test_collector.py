"""Artificial file-pipeline controls only. No runtime, renderer, GUI or GPU evidence."""
import argparse
import copy
import json
from pathlib import Path
import tempfile
import threading
import time
import types
import unittest

HERE = Path(__file__).resolve().parent
module = types.ModuleType('collector')
exec(compile((HERE/'collect_native.py').read_text(), 'collect_native.py', 'exec'), module.__dict__)


def synthetic(request):
    sample = {'serial': 3, 'clip_id': 'b1_arm_rehearsal_v1', 'timeline_id': 'probe-entry',
              'source_seconds': 2, 'position_seconds': 2, 'playing': False}
    matrix=[1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.]
    bones=[{'name':f'bone-{i}','parent':None,**{key:matrix for key in ['rest','posed','inverse_bind','local_rest','local_posed','skin']}} for i in range(53)]
    part={'display_entity':'body-entity','mesh_handle':'body-mesh','source_ids':[0,1,2],'indices':[0,1,2],
          'positions':[[0,0,0],[1,0,0],[0,1,0]],'normals':[[0,0,1]]*3,'tangents':[[1,0,0,1]]*3,
          'rest_positions':[[0,0,0],[1,0,0],[0,1,0]],'rest_normals':[[0,0,1]]*3,
          'full_joint_influences':[[[0,1]]]*3,'model_to_world':matrix,'display_transform':matrix}
    snapshot = {'schema_version': 1, 'profile_id': 'nvwa-mpfb-b1-motion-v1', 'generation': 2, 'revision': 4,
                'sample': sample, 'parameters': {'torso_length': 0, 'jaw_drop': 0}, 'bones':bones,
                'parts':[{'name':'body',**copy.deepcopy(part)},{'name':'garment',**copy.deepcopy(part)}]}
    common = {'request': request, 'geometry_equal': True, 'geometry_before_sha256': 'a'*64, 'geometry_after_sha256': 'a'*64}
    report = {**common, 'phase': 'captured', 'desired': 'skin', 'applied': 'skin', 'applied_generation': 2,
              'requested_published_generation': 2, 'identity': {'revision': 4}, 'sample': sample, 'parameters': snapshot['parameters']}
    appearance={'state':'skin','body_mesh':'body-mesh','display_entity':'body-entity','material_handle':'fixture-material','not_saved':True,'accessory_runtime':None}
    report['appearance']=copy.deepcopy(appearance)
    frame = {**common, 'snapshot': snapshot, 'appearance': appearance}
    return report, frame


class Controls(unittest.TestCase):
    def test_manifest_domain(self):
        manifest = module.parse((HERE/'cases54.json').read_bytes())
        self.assertEqual(len(manifest['cases']), 54)
        for platform in ['native_request', 'web_request']:
            requests = [case[platform] for case in manifest['cases']]
            self.assertEqual(len({r['request_id'] for r in requests}),54)
            for request in requests: module.validate_request(request)

    def test_identity_mismatch_rejected(self):
        request = {'request_id': 'fixture', 'action': 'report'}
        report, frame = synthetic(request)
        for target, key in [('report','request'), ('frame','geometry_after_sha256'), ('snapshot','revision'), ('snapshot','generation'), ('snapshot','sample')]:
            r, f = copy.deepcopy(report), copy.deepcopy(frame)
            value = r if target=='report' else f if target=='frame' else f['snapshot']
            value[key] = None
            with self.assertRaises(ValueError): module.verify(request,r,f)

    def test_missing_actual_structure_and_appearance_rejected(self):
        request={'request_id':'fixture','action':'report'};report,frame=synthetic(request)
        for key in ['bones','parts','parameters']:
            r,f=copy.deepcopy(report),copy.deepcopy(frame);f['snapshot'].pop(key)
            with self.subTest(key=key),self.assertRaises(ValueError):module.verify(request,r,f)
        for target in ['report','frame']:
            r,f=copy.deepcopy(report),copy.deepcopy(frame);(r if target=='report' else f).pop('appearance')
            with self.subTest(target=target),self.assertRaises(ValueError):module.verify(request,r,f)
        for key in ['positions','full_joint_influences','display_transform']:
            r,f=copy.deepcopy(report),copy.deepcopy(frame);f['snapshot']['parts'][0].pop(key)
            with self.subTest(key=key),self.assertRaises(ValueError):module.verify(request,r,f)
        r,f=copy.deepcopy(report),copy.deepcopy(frame);f['snapshot']['bones'][0].pop('skin')
        with self.assertRaises(ValueError):module.verify(request,r,f)

    def test_requested_mode_is_enforced(self):
        for action in ['baseline','accessories']:
            request={'request_id':'fixture','action':action};r,f=synthetic(request)
            with self.subTest(action=action),self.assertRaises(ValueError):module.verify(request,r,f)
        request={'request_id':'fixture','action':'skin'};r,f=synthetic(request);module.verify(request,r,f)

    def test_authentic_empty_runtime_baseline_and_skin_verify(self):
        for action in ['baseline', 'skin']:
            for full in [None, {'accessories': None}]:
                for compact in [None, {'accessories': None}]:
                    request={'request_id':'fixture','action':action};r,f=synthetic(request)
                    r['desired']=r['applied']=action
                    for appearance in [r['appearance'],f['appearance']]:appearance['state']='plain' if action=='baseline' else 'skin'
                    r['appearance']['accessory_runtime']=copy.deepcopy(compact)
                    f['appearance']['accessory_runtime']=copy.deepcopy(full)
                    with self.subTest(action=action,full=full,compact=compact):module.verify(request,r,f)

    def test_nonempty_missing_or_false_runtime_verify_rejects(self):
        malformed=[False,{},[],{'accessories':[]},{'accessories':None,'generation':2},{'accessories':None,'identity':{}},{'accessories':[{'name':'hair'}]}]
        for action in ['baseline','skin']:
            request={'request_id':'fixture','action':action};report,frame=synthetic(request)
            report['desired']=report['applied']=action
            for appearance in [report['appearance'],frame['appearance']]:appearance['state']='plain' if action=='baseline' else 'skin'
            for target in ['report','frame']:
                for value in malformed:
                    r,f=copy.deepcopy(report),copy.deepcopy(frame)
                    (r if target=='report' else f)['appearance']['accessory_runtime']=value
                    with self.subTest(action=action,target=target,value=value),self.assertRaises(ValueError):module.verify(request,r,f)
                r,f=copy.deepcopy(report),copy.deepcopy(frame)
                (r if target=='report' else f)['appearance'].pop('accessory_runtime')
                with self.subTest(action=action,target=target,missing=True),self.assertRaises(ValueError):module.verify(request,r,f)

    def test_protected_inputs_never_overwritten_or_create_output(self):
        for protected_name in ['manifest','binary']:
            for channel_name in ['command_file','report_file','frame_file','out']:
                with self.subTest(input=protected_name,channel=channel_name),tempfile.TemporaryDirectory(dir=HERE,prefix='fixture-') as directory:
                    base=Path(directory);inputs={name:base/(name+'.raw') for name in ['command','report','frame','protected']}
                    for name,path in inputs.items():path.write_bytes(('KEEP-'+name).encode())
                    args=argparse.Namespace(command_file=str(inputs['command']),report_file=str(inputs['report']),frame_file=str(inputs['frame']),out=str(base/'new-output'),request_json=json.dumps({'request_id':'fixture','action':'report'}),manifest=None,case=None,timeout=.1,binary=None,binary_sha256=None)
                    setattr(args,protected_name,str(inputs['protected']));setattr(args,channel_name,str(inputs['protected']))
                    with self.assertRaises(ValueError):module.collect(args)
                    self.assertFalse((base/'new-output').exists())
                    for name,path in inputs.items():self.assertEqual(path.read_bytes(),('KEEP-'+name).encode())

    def pipeline(self, directory, request, report, frame, timeout=0.3):
        base = Path(directory)
        command, report_path, frame_path = [base/name for name in ['command.json','report.json','frame.json']]
        command.write_bytes(b'{"request_id":"old","action":"report"}')
        report_path.write_bytes(module.encode({'phase':'pending'}));frame_path.write_bytes(module.encode({}))
        def respond():
            deadline=time.monotonic()+1
            while time.monotonic()<deadline:
                try: current=command.read_bytes()
                except FileNotFoundError:return
                if current!=b'{"request_id":"old","action":"report"}':
                    report_path.write_bytes(module.encode(report));frame_path.write_bytes(module.encode(frame));return
                time.sleep(.001)
        thread=threading.Thread(target=respond,daemon=True);thread.start()
        return argparse.Namespace(command_file=str(command),report_file=str(report_path),frame_file=str(frame_path),out=str(base/'output'),
                                  request_json=json.dumps(request),manifest=None,case=None,timeout=timeout,binary=None,binary_sha256=None)

    def test_positive_artificial_pipeline_preserves_raw_bytes(self):
        request = {'request_id':'fixture','action':'report'};r,f=synthetic(request)
        with tempfile.TemporaryDirectory(dir=HERE,prefix='fixture-') as directory:
            args=self.pipeline(directory,request,r,f)
            result=module.collect(args)
            self.assertEqual(result['status'],'captured')
            output=Path(args.out)
            self.assertEqual((output/'report.raw').read_bytes(),Path(args.report_file).read_bytes())
            self.assertEqual((output/'frame.raw').read_bytes(),Path(args.frame_file).read_bytes())
            self.assertTrue((output/'original-command.raw').exists())
            with self.assertRaises(ValueError):module.collect(args)

    def test_old_id_times_out_and_error_stops(self):
        request={'request_id':'fixture','action':'report'}
        for error in [False,True]:
            r,f=synthetic({'request_id':'automatic-rebind','action':'report'})
            if error:r={'phase':'error','error':'fixture failure'}
            with tempfile.TemporaryDirectory(dir=HERE,prefix='fixture-') as directory:
                args=self.pipeline(directory,request,r,f,timeout=0.1)
                with self.assertRaises(RuntimeError if error else TimeoutError):module.collect(args)
                receipt=module.parse((Path(args.out)/'receipt.json').read_bytes())
                self.assertEqual(receipt['status'],'failed')
                self.assertFalse((Path(args.out)/'envelope.json').exists())

    def recovery_fixture(self,directory,request,next_report,next_frame,delay=0.08,timeout=0.4):
        base=Path(directory);command,report_path,frame_path=[base/name for name in ['command.json','report.json','frame.json']]
        old_command=b'{"request_id":"old","action":"report"}'
        old_error=module.encode({'phase':'error','error':'old invalid UTF8 command'})
        command.write_bytes(old_command);report_path.write_bytes(old_error);frame_path.write_bytes(b'{}')
        def respond():
            deadline=time.monotonic()+1
            while time.monotonic()<deadline:
                try:current=command.read_bytes()
                except FileNotFoundError:return
                if current!=old_command:
                    time.sleep(delay)
                    if next_report is not None:
                        try:report_path.write_bytes(module.encode(next_report));frame_path.write_bytes(module.encode(next_frame))
                        except FileNotFoundError:pass
                    return
                time.sleep(.001)
        if next_report is not None:threading.Thread(target=respond,daemon=True).start()
        args=argparse.Namespace(command_file=str(command),report_file=str(report_path),frame_file=str(frame_path),out=str(base/'output'),request_json=json.dumps(request),manifest=None,case=None,timeout=timeout,binary=None,binary_sha256=None)
        return args,old_error

    def test_pre_send_error_then_delayed_matching_capture_recovers(self):
        request={'request_id':'recovery','action':'report'};report,frame=synthetic(request)
        with tempfile.TemporaryDirectory(dir=HERE,prefix='fixture-') as directory:
            args,old_error=self.recovery_fixture(directory,request,report,frame)
            result=module.collect(args)
            self.assertEqual(result['status'],'captured')
            self.assertEqual(result['pre_send_report_sha256'],module.digest(old_error))
            self.assertEqual((Path(args.out)/'original-report.raw').read_bytes(),old_error)
            self.assertEqual((Path(args.out)/'report.raw').read_bytes(),module.encode(report))
            self.assertTrue(any((Path(args.out)/row['file']).read_bytes()==old_error for row in result['observations']))

    def test_changed_error_after_pre_send_error_stops(self):
        request={'request_id':'recovery','action':'report'}
        with tempfile.TemporaryDirectory(dir=HERE,prefix='fixture-') as directory:
            args,old_error=self.recovery_fixture(directory,request,{'phase':'error','error':'new failure without request ID'}, {})
            with self.assertRaises(RuntimeError):module.collect(args)
            receipt=module.parse((Path(args.out)/'receipt.json').read_bytes())
            self.assertEqual(receipt['status'],'failed')
            self.assertIn('new failure',receipt['error'])
            self.assertFalse((Path(args.out)/'envelope.json').exists())

    def test_unchanged_pre_send_error_times_out_with_raw_evidence(self):
        request={'request_id':'recovery','action':'report'}
        with tempfile.TemporaryDirectory(dir=HERE,prefix='fixture-') as directory:
            args,old_error=self.recovery_fixture(directory,request,None,None,timeout=.12)
            started=time.monotonic()
            with self.assertRaises(TimeoutError):module.collect(args)
            self.assertLess(time.monotonic()-started,.5)
            receipt=module.parse((Path(args.out)/'receipt.json').read_bytes())
            self.assertEqual(receipt['status'],'failed')
            self.assertEqual(receipt['pre_send_report_sha256'],module.digest(old_error))
            self.assertEqual((Path(args.out)/'original-report.raw').read_bytes(),old_error)
            self.assertFalse((Path(args.out)/'envelope.json').exists())

    def test_prior_report_same_id_is_not_adopted(self):
        request={'request_id':'fixture','action':'report'};r,f=synthetic(request)
        with tempfile.TemporaryDirectory(dir=HERE,prefix='fixture-') as directory:
            args=self.pipeline(directory,request,r,f)
            Path(args.report_file).write_bytes(module.encode(r))
            before=Path(args.command_file).read_bytes()
            with self.assertRaises(ValueError):module.collect(args)
            self.assertEqual(Path(args.command_file).read_bytes(),before)

    def test_existing_request_id_refused(self):
        request={'request_id':'old','action':'report'};r,f=synthetic(request)
        with tempfile.TemporaryDirectory(dir=HERE,prefix='fixture-') as directory:
            args=self.pipeline(directory,request,r,f)
            before=Path(args.command_file).read_bytes()
            with self.assertRaises(ValueError):module.collect(args)
            self.assertEqual(Path(args.command_file).read_bytes(),before)
            self.assertTrue((Path(args.out)/'original-command.raw').exists())


if __name__=='__main__':unittest.main()
