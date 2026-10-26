"""Actual pilot controls plus synthetic contract-only metadata; no cohort evidence."""
import copy
import hashlib
import inspect
import json
import unittest
from pathlib import Path
import validate as checker
from contract import EXP, LEGACY, cases, work, check_context, parse_capture
from cohort import check_matrix, witness

INFO=json.loads((EXP/'SOURCE-REUSE.json').read_text())
PILOT=Path(INFO['pilot_path'])
_CACHE=None

def pilot():
    global _CACHE
    if _CACHE is None:
        result=[]
        for name in ['A1','B','A2']:
            raw=(PILOT/(name+'.json')).read_bytes()
            checker.require(hashlib.sha256(raw).hexdigest()==INFO['pilot_raw_sha256'][name],'actual pilot authentication failed')
            result.append(parse_capture(raw,json.loads((PILOT/(name+'-manifest.json')).read_text())))
        _CACHE=result
    return _CACHE

def context_only(case,seconds):
    """Shallow-share untouched actual arrays; change metadata only for guard tests.
    This is never passed off as fitted nondefault or source2 cohort evidence.
    """
    actual=pilot()[0];r={'report':dict(actual['report']),'frame':dict(actual['frame'])};f=r['frame'];report=r['report']
    f['candidate']=dict(f['candidate']);f['full_base']=dict(f['full_base']);f['base']=dict(f['base'])
    f['identity']=copy.deepcopy(f['identity']);report['captured_identity']=f['identity'];report['base']=f['base']
    selected=work(case,seconds);report['work_json']=json.dumps(selected,separators=(',',':'))
    digest=hashlib.sha256(report['work_json'].encode()).hexdigest()
    report['work_sha256']=f['work_sha256']=f['identity']['work_sha256']=digest
    f['base']['parameters']=f['full_base']['parameters']=selected['character']['parameters']
    timeline=selected['timeline'][0];sample=dict(f['candidate']['sample'])
    sample.update(source_seconds=seconds,position_seconds=seconds,clip_id=timeline['clip_id'],timeline_id=timeline['id'])
    f['candidate']['sample']=f['full_base']['sample']=f['base']['sample']=sample
    f['identity'].update(seconds=seconds,clip_id=timeline['clip_id'],timeline_id=timeline['id'])
    return r

class Controls(unittest.TestCase):
    def test_actual_pilot_passes_adapter_and_original_strict91(self):
        self.assertEqual(checker.validate(pilot(),'default-arms',0)['result'],'PASS')
        self.assertEqual(checker.old.validate(pilot())['result'],'PASS')
        self.assertEqual(len(witness(pilot()[0])['bone_names']),53)

    def test_exact91_source_proof_and_nine_controls_remain_available(self):
        for name,digest in INFO['experiment91_files'].items():
            self.assertEqual(hashlib.sha256((LEGACY/name).read_bytes()).hexdigest(),digest,name)
        old=inspect.getsource(checker.old.check_record).rstrip()
        expected=old.replace('def check_record(record,which):','def check_record(record,which,case,seconds):').replace("    require(c['sample']['source_seconds']==0 and c['sample']['playing'] is False,'held source0 required')","    check_context(record,case,seconds)").replace("    require(json.loads(r['work_json'])==json.loads((EXP/'works/default.nvwa.json').read_text()),'exact default Work required')","    # The explicit case/sample contract above replaces only91's default guard.")
        self.assertEqual(inspect.getsource(checker.check_record).rstrip(),expected)
        self.assertEqual(sum((LEGACY/name).read_text().count('    def test_') for name in ['test_source.py','test_isolation.py']),9)

    def test_all_fourteen_metadata_contracts_and_unknown_case_sample_rejection(self):
        for case,spec in cases().items():
            for seconds in spec['samples_seconds']:check_context(context_only(case,seconds),case,seconds)
        for case,seconds in [('unknown',0),('default-arms',1),('default-arms',True)]:
            with self.assertRaises(ValueError):work(case,seconds)

    def test_self_consistent_wrong_work_sample_clip_camera_and_identity_reject(self):
        with self.assertRaisesRegex(ValueError,'selected Work'):check_context(context_only('minus-arms',0),'default-arms',0)
        with self.assertRaisesRegex(ValueError,'held source/position'):check_context(context_only('default-arms',2),'default-arms',0)
        r=context_only('default-arms',0)
        for sample in [r['frame']['candidate']['sample'],r['frame']['full_base']['sample'],r['frame']['base']['sample']]:sample['clip_id']='wrong-clip'
        r['frame']['identity']['clip_id']='wrong-clip'
        with self.assertRaisesRegex(ValueError,'clip/timeline'):check_context(r,'default-arms',0)
        r=context_only('default-arms',0);changed=copy.deepcopy(r['frame']['camera']);changed['viewport']=[640,360]
        r['frame']['camera']=r['report']['camera']=r['frame']['identity']['camera']=changed
        with self.assertRaisesRegex(ValueError,'pilot front camera'):check_context(r,'default-arms',0)
        r=context_only('default-arms',0);r['frame']['identity']['appearance_pending']=True
        with self.assertRaisesRegex(ValueError,'readiness'):check_context(r,'default-arms',0)

    def test_wrong_nonhair_and_self_consistent_forged_hair_reject(self):
        r=copy.deepcopy(pilot());next(b for b in r[1]['frame']['buffers'] if b['role']=='body')['positions'][0][0]+=.001
        with self.assertRaisesRegex(ValueError,'unexpected state change'):checker.validate(r,'default-arms',0)
        r=copy.deepcopy(pilot())
        for record in r:next(b for b in record['frame']['buffers'] if b['role']=='body')['positions'][0][0]+=.001
        with self.assertRaisesRegex(ValueError,'non-hair upload'):checker.validate(r,'default-arms',0)
        r=copy.deepcopy(pilot());c=r[1]['frame']['candidate'];hair=next(b for b in r[1]['frame']['buffers'] if b['role']=='hair')
        hair['positions'][0][0]=checker.numeric.f32(hair['positions'][0][0]+.001)
        digest=checker.hashes.mesh_array_sha256(hair['positions'])
        hair['positions_sha256']=c['published_positions_sha256']=c['pre_visibility_publication']['positions_sha256']=digest
        with self.assertRaisesRegex(ValueError,'actual positions differs from authenticated source replay'):checker.validate(r,'default-arms',0)

    def test_raw_transfer_tamper_and_rehashed_outer_envelope_reject(self):
        raw=(PILOT/'A1.json').read_bytes();manifest=json.loads((PILOT/'A1-manifest.json').read_text())
        with self.assertRaisesRegex(ValueError,'raw transfer size/hash'):parse_capture(raw+b' ',manifest)
        bad=raw.replace(b'"web76-2"',b'"web76-X"',1);forged=copy.deepcopy(manifest);transfer=json.loads(forged['transfer']);transfer['sha256']=hashlib.sha256(bad).hexdigest();forged['transfer']=transfer
        with self.assertRaisesRegex(ValueError,'raw report size/hash'):parse_capture(bad,forged)

    def test_synthetic_compact_matrix_controls_reject_reused_rest_or_missing_pose(self):
        def observed():
            return {(case,t):{'body_rest':case.rsplit('-',1)[0] if case!='head-width-plus' else case,'body_source_ids':'ids','body_pose':'pose'+str(t),'bone_skin':'bones'+str(t),'bone_names':['bone'+str(i) for i in range(53)]} for case,spec in cases().items() for t in spec['samples_seconds']}
        self.assertEqual(check_matrix(observed())['result'],'PASS')
        r=observed()
        for item in r.values():item['body_rest']='substituted-default-cage'
        with self.assertRaisesRegex(ValueError,'reused a rest cage'):check_matrix(r)
        r=observed();r['default-knee',2]['body_pose']=r['default-knee',0]['body_pose']
        with self.assertRaisesRegex(ValueError,'pose movement missing'):check_matrix(r)
        r=observed();r.pop(('head-width-plus',2))
        with self.assertRaisesRegex(ValueError,'seven cases by two'):check_matrix(r)

if __name__=='__main__':unittest.main()
