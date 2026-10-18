"""Actual parser/store controls with synthetic envelopes; no HTTP server or runtime."""
import copy
import json
from pathlib import Path
import types
import tempfile
import hashlib
import unittest

module = types.ModuleType('appearance65_serve')
exec(compile(Path(__file__).with_name('serve.py').read_text(), 'serve.py', 'exec'), module.__dict__)


def envelope(mode):
    request = {'request_id': 'case', 'action': 'report'}
    snapshot = {'schema_version': 1, 'profile_id': 'nvwa-mpfb-b1-motion-v1',
                'generation': 7, 'revision': 2, 'sample': {'serial': 4},
                'parameters': {'torso_length': 0, 'jaw_drop': 0},
                'bones': [{} for _ in range(53)], 'parts': [{'name': 'body'}, {'name': 'garment'}]}
    runtime = None
    if mode == 'skin+eyes+hair':
        runtime = {'generation': 7, 'revision': 2, 'sample': {'serial': 4},
                   'identity': {'generation': 7, 'revision': 2},
                   'accessories': [{'name': name, 'not_saved': True} for name in ['eyes', 'hair']]}
    appearance = {'state': 'plain' if mode == 'baseline' else 'skin', 'accessory_runtime': runtime}
    report = {'phase': 'captured', 'request': request, 'desired': mode, 'applied': mode,
              'geometry_before_sha256': 'a' * 64, 'geometry_after_sha256': 'a' * 64,
              'applied_generation': 7, 'sample': snapshot['sample'], 'parameters': snapshot['parameters'],
              'appearance': copy.deepcopy(appearance)}
    if mode != 'skin+eyes+hair':
        # Actual runtime full-null / compact-null-sentinel representation.
        report['appearance']['accessory_runtime'] = {'accessories': None}
    frame = {'request': request, 'geometry_equal': True, 'geometry_before_sha256': 'a' * 64,
             'geometry_after_sha256': 'a' * 64, 'snapshot': snapshot, 'appearance': appearance}
    quality = {'selected':'frozen64','scene_camera':{'msaa_samples':4,'active':True},
               'work_appearance':{'type':'none'},'production_appearance_controller_disabled':True,
               'base_binding_identity':{'runtime_ready':True,'runtime_error':None,'revision':2}}
    report['quality']=copy.deepcopy(quality);frame['quality']=copy.deepcopy(quality)
    if mode == 'skin+eyes+hair':
        for target in [report,frame]:
            proof=target['appearance']['accessory_runtime']
            proof['quality']='frozen64';proof['actual_msaa_samples']=4
            for row in proof['accessories']:
                row['material']={'quality':'frozen64','actual_msaa_samples':4,'alpha':'Mask(0.5)','unlit':False}
    return {'request': request, 'report': report, 'frame': frame}


class ParserControls(unittest.TestCase):
    def parse(self, value):
        return module.parse_record(json.dumps(value).encode(), 'case')

    def test_three_actual_producer_modes(self):
        for mode in ['baseline', 'skin', 'skin+eyes+hair']:
            with self.subTest(mode=mode):
                value = envelope(mode)
                self.assertEqual(self.parse(value), value)

    def test_mode_mismatch_rejects(self):
        value = envelope('skin+eyes+hair'); value['report']['applied'] = 'skin'
        with self.assertRaises(module.CaptureError): self.parse(value)

    def test_stale_or_missing_accessory_identity_rejects(self):
        for key in ['generation', 'revision', 'sample']:
            value = envelope('skin+eyes+hair'); value['frame']['appearance']['accessory_runtime'][key] = -1
            with self.assertRaises(module.CaptureError): self.parse(value)
        value = envelope('skin+eyes+hair'); value['frame']['appearance']['accessory_runtime']['accessories'].pop()
        with self.assertRaises(module.CaptureError): self.parse(value)

    def test_accessories_outside_mode_reject(self):
        value = envelope('skin'); value['frame']['appearance']['accessory_runtime'] = {}
        with self.assertRaises(module.CaptureError): self.parse(value)

    def test_exact_authentic_empty_representations_are_consistently_empty(self):
        for mode in ['baseline', 'skin']:
            for full in [None, {'accessories': None}]:
                for compact in [None, {'accessories': None}]:
                    value = envelope(mode)
                    value['frame']['appearance']['accessory_runtime'] = copy.deepcopy(full)
                    value['report']['appearance']['accessory_runtime'] = copy.deepcopy(compact)
                    with self.subTest(mode=mode,full=full,compact=compact):
                        self.assertEqual(self.parse(value), value)

    def test_residual_nonempty_malformed_or_missing_empty_runtime_rejects(self):
        bad = [{}, [], False, 'null', {'accessories': []}, {'accessories': {}},
               {'accessories': [{'name': 'hair'}]}, {'accessories': None, 'generation': 7},
               {'accessories': None, 'identity': {}}, {'generation': 7}]
        for mode in ['baseline', 'skin']:
            for target in ['report', 'frame']:
                for runtime in bad:
                    value = envelope(mode);value[target]['appearance']['accessory_runtime'] = runtime
                    with self.subTest(mode=mode,target=target,runtime=runtime),self.assertRaises(module.CaptureError):
                        self.parse(value)
                value = envelope(mode);value[target]['appearance'].pop('accessory_runtime')
                with self.subTest(mode=mode,target=target,missing=True),self.assertRaises(module.CaptureError):
                    self.parse(value)

    def test_capture_store_accepts_real_payload_shape_and_preserves_exact_bytes(self):
        for mode in ['baseline', 'skin']:
            value = envelope(mode)
            raw = (json.dumps(value,indent=1) + '\n').encode()
            with tempfile.TemporaryDirectory(prefix='nvwa64-store-fixture-') as directory:
                store = module.CaptureStore(directory)
                receipt = store.save('case',raw)
                self.assertTrue(receipt['stored'])
                self.assertEqual((Path(directory)/'case.json').read_bytes(),raw)
                self.assertEqual(receipt['sha256'],hashlib.sha256(raw).hexdigest())
                with self.assertRaises(module.CaptureError):store.save('case',raw)

    def test_capture_store_rejects_full_compact_mismatch_without_writing(self):
        for target in ['report', 'frame']:
            for runtime in [{'accessories': []}, {'accessories': None, 'generation': 7}]:
                value = envelope('baseline');value[target]['appearance']['accessory_runtime'] = runtime
                with tempfile.TemporaryDirectory(prefix='nvwa64-store-fixture-') as directory:
                    store = module.CaptureStore(directory)
                    with self.assertRaises(module.CaptureError):store.save('case',json.dumps(value).encode())
                    self.assertEqual(list(Path(directory).iterdir()),[])

    def test_limit_is_unchanged(self): self.assertEqual(module.MAX_CAPTURES, 32)

    def test_missing_mismatched_quality_and_non_none_production_reject(self):
        for target in ['report','frame']:
            for field,bad in [('selected','invented'),('work_appearance',{'type':'b1_cc0'}),
                              ('production_appearance_controller_disabled',False),('base_binding_identity',{})]:
                value=envelope('skin+eyes+hair');value[target]['quality'][field]=bad
                with self.subTest(target=target,field=field),self.assertRaises(module.CaptureError):self.parse(value)
        value=envelope('skin');value['frame'].pop('quality')
        with self.assertRaises(module.CaptureError):self.parse(value)

    def test_material_policy_and_msaa_are_observed_not_assumed(self):
        value=envelope('skin+eyes+hair')
        for target in ['report','frame']:
            proof=value[target]['appearance']['accessory_runtime']
            value[target]['quality']['selected']='hair_coverage';proof['quality']='hair_coverage'
            for row in proof['accessories']:
                row['material']['quality']='hair_coverage'
                if row['name']=='hair':row['material']['alpha']='AlphaToCoverage'
        self.assertEqual(self.parse(value),value)
        value['frame']['appearance']['accessory_runtime']['accessories'][1]['material']['alpha']='Mask(0.5)'
        with self.assertRaises(module.CaptureError):self.parse(value)

        for target in ['report','frame']:
            value[target]['quality']['scene_camera']['msaa_samples']=1
        with self.assertRaises(module.CaptureError):self.parse(value)

    def test_disabled_controller_must_not_claim_production_ready_or_applied(self):
        for field,value in [('production_ready',True),('production_applied',{'type':'none'}),
                            ('production_requested',{'type':'none'}),('production_generation',7)]:
            capture=envelope('skin+eyes+hair')
            for target in ['report','frame']:capture[target]['quality'][field]=value
            with self.subTest(field=field),self.assertRaises(module.CaptureError):self.parse(capture)
        for field,value in [('runtime_ready',False),('runtime_error','failed'),('revision',3)]:
            capture=envelope('skin+eyes+hair')
            for target in ['report','frame']:capture[target]['quality']['base_binding_identity'][field]=value
            with self.subTest(field=field),self.assertRaises(module.CaptureError):self.parse(capture)


if __name__ == '__main__': unittest.main()
