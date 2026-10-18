"""Tool regressions only; no runtime or quality claim from synthetic frames."""
import copy,hashlib,json,tempfile,shutil,unittest
from pathlib import Path
from oracle import Oracle,CAGE,TOLERANCE_M,full_positive_lbs
from prepare_works import EXP,ROOT,CASES_SHA,prepare
from verify import complete_case_ids,strict_json

class RawOracle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.oracle=Oracle();cls.cases=json.loads((EXP/'inputs/cases.json').read_text());cls.zero=cls.cases['recipes'][0]['parameters']
    def body(self,parameters):return {'source_ids':list(range(CAGE)),'rest_positions':self.oracle.expected(parameters)}
    def test_all21_raw_recipes_have_full19158_cage_and_signed_effects(self):
        baseline=self.oracle.expected(self.zero)
        for recipe in self.cases['recipes']:
            actual=self.body(recipe['parameters']);result=self.oracle.rest_error(actual,recipe['parameters']);self.assertEqual(result['source_vertices'],CAGE)
            if recipe['id']!='zero':self.assertNotEqual(actual['rest_positions'],baseline)
    def test_wrong_sign_double_scale_source_id_permutation_and_duplicate_disagreement_reject(self):
        plus=self.zero.copy();plus['head_width']=1;minus=self.zero.copy();minus['head_width']=-1
        bad=self.body(minus)
        with self.assertRaisesRegex(ValueError,'rest cage'):self.oracle.rest_error(bad,plus)
        bad=self.body(plus);bad['rest_positions']=[[x*10 for x in p] for p in bad['rest_positions']]
        with self.assertRaises(ValueError):self.oracle.rest_error(bad,plus)
        bad=self.body(plus);bad['source_ids'][0],bad['source_ids'][1]=bad['source_ids'][1],bad['source_ids'][0]
        with self.assertRaises(ValueError):self.oracle.rest_error(bad,plus)
        bad=self.body(plus);bad['source_ids'].append(0);bad['rest_positions'].append([v+TOLERANCE_M*2 for v in bad['rest_positions'][0]])
        with self.assertRaisesRegex(ValueError,'duplicate'):self.oracle.rest_error(bad,plus)
    def test_missing_helper_or_changed_raw_source_identity_rejects(self):
        bad=self.body(self.zero);bad['source_ids'].pop();bad['rest_positions'].pop()
        with self.assertRaisesRegex(ValueError,'coverage'):self.oracle.rest_error(bad,self.zero)
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);shutil.copytree(EXP/'inputs',root/'inputs');target=next((root/'inputs/raw').glob('*.target'));target.write_bytes(target.read_bytes()+b'\n#changed')
            with self.assertRaisesRegex(ValueError,'source identity'):Oracle(root/'inputs')
    def test_independent_allpositive_lbs_uses_every_influence_and_normalizes_full_sum(self):
        bones=[]
        for i in range(53):
            matrix=[1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.,float(i),0.,0.,1.];bones.append({'name':str(i),'skin':matrix})
        part={'rest_positions':[[1.,2.,3.]],'positions':[[1.+40./15.,2.,3.]],'full_joint_influences':[[[i,float(i+1)] for i in range(5)]]}
        proof=full_positive_lbs(part,bones);self.assertEqual(proof['max_positive_influences'],5)
        truncated=copy.deepcopy(part);truncated['full_joint_influences'][0].pop()
        with self.assertRaisesRegex(ValueError,'LBS/upload'):full_positive_lbs(truncated,bones)
        moved=copy.deepcopy(bones);moved[4]['skin'][12]+=1
        with self.assertRaises(ValueError):full_positive_lbs(part,moved)
        for key in ('empty','nonpositive','duplicate','missingbone'):
            bad=copy.deepcopy(part);test_bones=copy.deepcopy(bones)
            if key=='empty':bad['full_joint_influences'][0]=[]
            elif key=='nonpositive':bad['full_joint_influences'][0][0][1]=0
            elif key=='duplicate':bad['full_joint_influences'][0][1][0]=0
            else:test_bones.pop()
            with self.subTest(key=key),self.assertRaises(ValueError):full_positive_lbs(bad,test_bones)

class CohortAndLinkedInputs(unittest.TestCase):
    def test_frozen69_exact_unique_ids_and_negative_missing_duplicate_unknown(self):
        data=(EXP/'inputs/cases.json').read_bytes();self.assertEqual(hashlib.sha256(data).hexdigest(),CASES_SHA);cases=json.loads(data);ids=[c['id'] for c in cases['held_cases']];complete_case_ids(ids,cases)
        for bad in [ids[:-1],ids+[ids[0]],ids[:-1]+[ids[0]],ids[:-1]+['unknown-case']]:
            with self.assertRaises(ValueError):complete_case_ids(bad,cases)
    def test_duplicate_and_nonfinite_json_are_not_accepted(self):
        for raw in ['{"current":true,"current":false}','{"v":NaN}','{"v":Infinity}']:
            with self.assertRaises(ValueError):strict_json(raw)
    def test_linked_canonical_work_plan_and_exact_source4_nonloop_cases(self):
        with tempfile.TemporaryDirectory() as temporary:
            receipt=prepare(ROOT,Path(temporary));self.assertEqual(receipt['case_count'],69)
            self.assertEqual(receipt['profile']['backend']['schema_version'],3)
            self.assertEqual(receipt['appearance']['asset_set_id'],'mpfb-b1-cc0-appearance-v2')
            final=[]
            for item in receipt['plan']:
                path=Path(temporary)/item['work_file'];self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),item['work_file_sha256'])
                work=json.loads(path.read_text());self.assertEqual(len(work['timeline']),1);self.assertFalse(work['timeline'][0]['looping']);self.assertEqual(work['timeline'][0]['duration_seconds'],4.)
                self.assertEqual(set(work['character']['parameters']),set(receipt['profile']['parameters'][i]['id'] for i in range(8)))
                for request in item['requests']:self.assertLessEqual(len(request['request_id']),64)
                if item['requests'][1]['seek_seconds']==4:final.append(item['case_id'])
            self.assertEqual(len(final),6)
    def test_missing85_integration_is_explicitly_not_linked(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError,'NOT-LINKED'):prepare(Path(temporary),Path(temporary)/'out')
    def test_raw16_targets_and_base_agree_with_linked_approved_payloads(self):
        manifest=json.loads((EXP/'inputs/oracle-sources.json').read_text());runtime=ROOT/'assets/characters/mpfb-b1-v2'
        for pair in manifest['parameters'].values():
            for item in pair.values():self.assertEqual(hashlib.sha256((runtime/'targets'/item['file']).read_bytes()).hexdigest(),item['sha256'])
        raw=Oracle().base;converted=[]
        for line in (runtime/'base.obj').read_text().splitlines():
            f=line.split()
            if f and f[0]=='v':converted.append([float(x) for x in f[1:]])
        self.assertEqual(len(raw),len(converted));self.assertLessEqual(max(abs(a-b) for p,q in zip(raw,converted) for a,b in zip(p,q)),1e-12)


class Correlation(unittest.TestCase):
    def pair(self):
        work='{}';identity={'runtime_ready':True,'appearance_ready':True,**{k:None for k in ('preview_sha256','pending_open_sha256','open_error','runtime_error','runtime_appearance_error','appearance_error','stage_error','playback_error','seek_request')}}
        identity['work_sha256']=hashlib.sha256(work.encode()).hexdigest()
        frame={'endpoint':'native','request_id':'one','identity':identity,'work_json':work,'work_sha256':hashlib.sha256(work.encode()).hexdigest(),'appearance':{'bound':True}}
        report={'endpoint':'native','request_id':'one','phase':'ready','acknowledged':True,'request_succeeded':True,'current':True,'captured_identity':identity,'work_json':work,'work_sha256':frame['work_sha256'],'appearance':frame['appearance']}
        report.update({'evidence_kind':'held-stable-two-frames','stable_observations':2});frame.update({'evidence_kind':'held-stable-two-frames','stable_observations':2})
        return {'report':report,'frame':frame}
    def test_actual_pair_guard_accepts_only_correlated_current_acknowledgement(self):
        from verify import current_pair
        current_pair(self.pair())
        for change in ('stale','unacknowledged','failed','request','endpoint','hash','preview','pending','open_error','runtime_error','playback_error'):
            value=self.pair()
            if change=='stale':value['report']['current']=False
            elif change=='unacknowledged':value['report']['acknowledged']=False
            elif change=='failed':value['report']['request_succeeded']=False
            elif change=='request':value['frame']['request_id']='wrong'
            elif change=='endpoint':value['frame']['endpoint']='web'
            elif change=='hash':value['frame']['work_sha256']=value['report']['work_sha256']='wrong'
            else:value['frame']['identity'][{'preview':'preview_sha256','pending':'pending_open_sha256'}.get(change,change)]='bad'
            with self.subTest(change=change),self.assertRaises(ValueError):current_pair(value)

    def test_frozen_recipe_and_source4_mislabels_fail_before_array_oracle(self):
        from verify import validate
        cases=json.loads((EXP/'inputs/cases.json').read_text());recipes={r['id']:r['parameters'] for r in cases['recipes']}
        value=self.pair();work={'revision':1,'profile':{'backend':{'type':'b1_cpu','schema_version':3,'asset_id':'mpfb-hm08-game-engine-female-sportsuit01-v2'},'id':'nvwa-mpfb-b1-motion-v2'},'character':{'parameters':recipes['zero'],'appearance':{'asset_set_id':'mpfb-b1-cc0-appearance-v2','skin':True,'eyes':True,'hair':True}}}
        text=json.dumps(work);value['report']['work_json']=value['frame']['work_json']=text;value['report']['work_sha256']=value['frame']['work_sha256']=hashlib.sha256(text.encode()).hexdigest();value['frame']['identity']['work_sha256']=value['frame']['work_sha256']
        planned={'requests':[{'work_json':text}]};case=next(c for c in cases['held_cases'] if c['recipe_id']=='head_width-plus')
        with self.assertRaisesRegex(ValueError,'recipe/case'):validate(value,case,planned,None,recipes['head_width-plus'])
        case=next(c for c in cases['held_cases'] if c['recipe_id']=='zero' and c['source_seconds']==4 and c['clip_id']=='b1_arm_rehearsal_v1')
        sample={'clip_id':case['clip_id'],'source_seconds':0,'position_seconds':0,'playing':False,'timeline_id':'acceptance-held','completed':False,'serial':17}
        base={'backend':work['profile']['backend'],'asset_id':work['profile']['backend']['asset_id'],'profile_id':work['profile']['id'],'parameters':recipes['zero'],'generation':1,'revision':1,'sample':sample}
        value['frame']['full_base']=base;value['report']['base_summary']=base.copy();value['frame']['identity'].update({'generation':1,'revision':1,'playing':False,'seconds':0,'clip_id':case['clip_id'],'timeline_id':'acceptance-held','completed':False,'serial':17})
        appearance={'serial':sample['serial'],'base_asset_id':base['asset_id'],'generation':1,'revision':1,'ready':True,'requested':work['character']['appearance'],'applied':work['character']['appearance'],'error':None}
        value['frame']['appearance']=value['report']['appearance']=appearance
        with self.assertRaisesRegex(ValueError,'held actual'):validate(value,case,planned,None,recipes['zero'])

if __name__=='__main__':unittest.main()
