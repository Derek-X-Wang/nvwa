"""93 controls; transformed metadata is synthetic, never new capture evidence."""
import copy
import hashlib
import inspect
import json
import unittest
from pathlib import Path
import supplement_validate as checker
from supplement_contract import EXP, work, camera, check_context
from supplement_cohort import check_matrix, admit_request_ids
from test_isolation import Isolation

ROOT=EXP.parents[1]
RAW=Path('/Users/derekxwang/.codex/work-products/nvwa/2026-10-25-hair79-short01-cohort92/web')
# Exact actual92plus-arms/source0 bytes are controls only; new framing is synthetic.
PINS={'h92-051-plus-arms-s0-A1':'b78eeae15876a3f31585201e5255ca5febbb3b32081a629cc159e889a0a194d9',
      'h92-052-plus-arms-s0-B':'6a54c27b780f2314165cc0d0602cca39b7b6c32eee0d71ab08d24ad6c355b54c',
      'h92-053-plus-arms-s0-A2':'86c012ed6106b08312bfbe6dce84e907bcc60c33321f2c72e246bb8120e743a9'}
_CACHE=None

def original():
    global _CACHE
    if _CACHE is None:
        records=[]
        for stem,pin in PINS.items():
            raw=(RAW/(stem+'.json')).read_bytes()
            manifest=json.loads((RAW/(stem+'-manifest.json')).read_text());transfer=manifest['transfer'];transfer=json.loads(transfer) if isinstance(transfer,str) else transfer
            checker.require(hashlib.sha256(raw).hexdigest()==(pin or transfer['sha256']),'actual92control raw authentication failed')
            records.append(checker.load_capture(RAW/(stem+'.json'),RAW/(stem+'-manifest.json')))
        _CACHE=records
    return _CACHE

def synthetic():
    records=copy.deepcopy(original());selected=work('plus-arms',0);text=json.dumps(selected,separators=(',',':'));digest=hashlib.sha256(text.encode()).hexdigest();view=camera()
    for record in records:
        r,f=record['report'],record['frame'];r['work_json']=text;r['work_sha256']=f['work_sha256']=digest
        f['identity']['work_sha256']=r['captured_identity']['work_sha256']=digest
        r['camera']=copy.deepcopy(view);f['camera']=copy.deepcopy(view);f['identity']['camera']=copy.deepcopy(view);r['captured_identity']['camera']=copy.deepcopy(view)
        f['candidate']['pre_visibility_publication']['camera']=copy.deepcopy(view);f['candidate']['pre_visibility_publication']['work_sha256']=digest
    return records

class Framing(unittest.TestCase):
    def test_only_two_work_field_diffs_and_production_derived_camera_pin(self):
        for case in ['plus-arms','plus-knee']:
            current=work(case,0);self.assertEqual(current['stage']['camera']['target_height'],1.6)
            current['stage']['camera']['target_height']=1.5
            self.assertEqual(current,json.loads((ROOT/'experiments/91-hair-short01-ab/works'/(case+'.nvwa.json')).read_text()))
        reference=json.loads((EXP/'works/reference-plus-framing160.json').read_text())['camera']
        self.assertEqual(camera()['global_transform'],reference['global_transform'])
        old=json.loads((ROOT/'experiments/92-hair-short01-cohort/reference-camera.json').read_text());expected=copy.deepcopy(old);expected['global_transform']=reference['global_transform'];self.assertEqual(camera(),expected)
        for case,seconds in [('default-arms',0),('plus-arms',1)]:
            with self.assertRaises(ValueError):work(case,seconds)
        copied=(EXP/'supplement_validate.py').read_text();expected=(ROOT/'experiments/92-hair-short01-cohort/validate.py').read_text().replace('from contract import LEGACY, check_context, load_capture','from supplement_contract import LEGACY, check_context, load_capture')
        prefix=copied[:copied.index('def capture_request_ids(')]
        suffix=copied[copied.index('def validate(records,case,seconds):'):].replace('    capture_request_ids(records)\n','',1)
        self.assertEqual(prefix+suffix,expected)

    def test_synthetic_new_framing_positive_and_old_framing_reject(self):
        self.assertEqual(checker.validate(synthetic(),'plus-arms',0)['result'],'PASS')
        with self.assertRaisesRegex(ValueError,'selected Work'):checker.validate(original(),'plus-arms',0)
        r=synthetic();old=json.loads((ROOT/'experiments/92-hair-short01-cohort/reference-camera.json').read_text())
        for record in r:
            record['frame']['camera']=copy.deepcopy(old);record['report']['camera']=copy.deepcopy(old);record['frame']['identity']['camera']=copy.deepcopy(old);record['report']['captured_identity']['camera']=copy.deepcopy(old);record['frame']['candidate']['pre_visibility_publication']['camera']=copy.deepcopy(old)
        with self.assertRaisesRegex(ValueError,'front camera'):checker.validate(r,'plus-arms',0)

    def test_wrong_work_sample_clip_current_camera_reject_at_context(self):
        for case,seconds in [('plus-knee',0),('plus-arms',2)]:
            with self.assertRaises(ValueError):check_context(synthetic()[0],case,seconds)
        r=synthetic()[0]
        for sample in [r['frame']['candidate']['sample'],r['frame']['full_base']['sample'],r['frame']['base']['sample'],r['report']['base']['sample']]:sample['clip_id']='wrong-clip'
        r['frame']['identity']['clip_id']=r['report']['captured_identity']['clip_id']='wrong-clip'
        with self.assertRaisesRegex(ValueError,'clip/timeline'):check_context(r,'plus-arms',0)
        r=synthetic()[0];r['frame']['identity']['appearance_pending']=r['report']['captured_identity']['appearance_pending']=True
        with self.assertRaisesRegex(ValueError,'readiness'):check_context(r,'plus-arms',0)
        r=synthetic()[0];changed=camera();changed['global_transform'][13]+=.01
        r['frame']['camera']=r['report']['camera']=r['frame']['identity']['camera']=r['report']['captured_identity']['camera']=changed
        with self.assertRaisesRegex(ValueError,'front camera'):check_context(r,'plus-arms',0)

    def test_nonhair_forged_hair_and_restoration_reject(self):
        r=synthetic();next(b for b in r[1]['frame']['buffers'] if b['role']=='body')['positions'][0][0]+=.001
        with self.assertRaisesRegex(ValueError,'unexpected state change'):checker.validate(r,'plus-arms',0)
        r=synthetic();c=r[1]['frame']['candidate'];hair=next(b for b in r[1]['frame']['buffers'] if b['role']=='hair');hair['positions'][0][0]=checker.numeric.f32(hair['positions'][0][0]+.001)
        digest=checker.hashes.mesh_array_sha256(hair['positions']);hair['positions_sha256']=c['published_positions_sha256']=c['pre_visibility_publication']['positions_sha256']=digest
        with self.assertRaisesRegex(ValueError,'actual positions differs from authenticated source replay'):checker.validate(r,'plus-arms',0)
        r=synthetic();r[2]['frame']['candidate']['decoded_rgba_sha256']='broken'
        with self.assertRaisesRegex(ValueError,'A restoration differs'):checker.validate(r,'plus-arms',0)

    def test_reused_a1_and_nonempty_string_request_ids_reject_at_new_guard(self):
        baseline=synthetic()
        self.assertEqual(len(set(checker.capture_request_ids(baseline))),3)
        reused=list(baseline);reused[2]=reused[0]
        with self.assertRaisesRegex(ValueError,'three distinct authenticated nonempty request IDs required'):
            checker.validate(reused,'plus-arms',0)
        for invalid in ['',7]:
            records=copy.deepcopy(baseline)
            records[2]['report']['request_id']=records[2]['frame']['request_id']=invalid
            with self.assertRaisesRegex(ValueError,'three distinct authenticated nonempty request IDs required'):
                checker.validate(records,'plus-arms',0)
        seen=set();admit_request_ids(seen,baseline)
        with self.assertRaisesRegex(ValueError,'twelve distinct authenticated capture request IDs required'):
            admit_request_ids(seen,baseline)

    def test_four_key_observed_consistency_controls(self):
        observed={(case,t):{'body_rest':'plus','body_source_ids':'ids','body_pose':'pose'+str(t),'bone_skin':'bones'+str(t),'bone_names':['b'+str(i) for i in range(53)]} for case in ['plus-arms','plus-knee'] for t in [0,2]}
        self.assertEqual(check_matrix(observed)['result'],'PASS');observed['plus-knee',2]['body_pose']='pose0'
        with self.assertRaisesRegex(ValueError,'pose movement'):check_matrix(observed)

if __name__=='__main__':unittest.main()
