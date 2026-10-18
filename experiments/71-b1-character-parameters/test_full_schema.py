"""One full-shape synthetic transport fixture; never runtime/fit/quality proof."""
import copy,hashlib,json,unittest,struct
from oracle import Oracle,CAGE
from prepare_works import EXP
from verify import validate
from hash_encoding import mesh_array_sha256
I=[1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.]

class FullSchema(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.oracle=Oracle();cls.plan=json.loads((EXP/'works/plan.json').read_text())['plan'][0];cls.case=json.loads((EXP/'inputs/cases.json').read_text())['held_cases'][0];cls.work=json.loads(cls.plan['requests'][0]['work_json'])
    def envelope(self):
        work=self.work;text=json.dumps(work);selection=work['character']['appearance'];parts=[];observed=[];accessories=[]
        rest=[[struct.unpack('!f',struct.pack('!f',x))[0] for x in p] for p in self.oracle.expected(work['character']['parameters'])];ids=list(range(CAGE))+list(range(22077-CAGE))
        skin=None
        for role in ('body','garment','eyes','hair'):
            n,ic=(22077,68676) if role=='body' else ((1986,10308) if role=='garment' else (3,3))
            positions=[rest[i] for i in ids] if role=='body' else [[0.,0.,0.]]*n;normals=[[0.,1.,0.]]*n;triangles=[0,1,2]*(ic//3);tangents=[[1.,0.,0.,1.]]*n
            image={'image_handle':'image-'+role,'width':1,'height':1,'format':'Rgba8UnormSrgb','decoded_rgba_sha256':'rgba-'+role,'decoded_bytes':4}
            fields={'base_color':'WHITE','roughness':0.7,'metallic':0.,'alpha_mode':'Mask(0.5)','cull_mode':'Some(Back)','double_sided':False}
            source={**fields,'name':role,'entity':role,'mesh_handle':'mesh-'+role,'material_handle':'mat-'+role,'texture':{k:v for k,v in image.items() if k!='decoded_bytes'},'render_vertices':n,'display_transform':I.copy(),**{k:k+'-'+role for k in ('positions_sha256','normals_sha256','uv_sha256','indices_sha256')}}
            hashes={key:mesh_array_sha256(array,integer=key=='indices_sha256') for key,array in [('positions_sha256',positions),('normals_sha256',normals),('uv_sha256',[[0.,0.]]*n if role!='garment' else []),('indices_sha256',triangles)]}
            source.update(hashes)
            observed.append({'role':role,'entity':role,'mesh_handle':'mesh-'+role,'material_handle':'mat-'+role,'positions':positions,'normals':normals,'tangents':tangents,'uv_0':[[0.,0.]]*n if role!='garment' else None,'indices':triangles,'display_transform':I.copy(),'material':{**fields,'unlit':False,'image':image},**{k:source[k] for k in ('positions_sha256','normals_sha256','uv_sha256','indices_sha256')}})
            if role in ('body','garment'):parts.append({'name':role,'display_entity':role,'mesh_handle':'mesh-'+role,'positions':positions,'normals':normals,'tangents':tangents,'rest_positions':positions,'rest_normals':normals,'source_ids':ids if role=='body' else list(range(n)),'indices':triangles,'display_transform':I.copy(),'model_to_world':I.copy(),'full_joint_influences':[[[0,1.]]]*n})
            elif role in ('eyes','hair'):accessories.append(source)
            if role=='body':skin=source
        sample={'clip_id':self.case['clip_id'],'position_seconds':0,'source_seconds':0,'playing':False,'timeline_id':'acceptance-held','completed':False,'serial':17}
        base={'backend':work['profile']['backend'],'asset_id':work['profile']['backend']['asset_id'],'profile_id':work['profile']['id'],'parameters':work['character']['parameters'],'generation':1,'revision':work['revision'],'character_entity':'character-entity','sample':sample,'parts':parts,'bones':[{'name':str(i),'skin':I.copy()} for i in range(53)]}
        appearance={'serial':sample['serial'],'base_asset_id':base['asset_id'],'generation':1,'revision':work['revision'],'ready':True,'error':None,'requested':selection,'applied':selection,'character_entity':'character-entity','body_vertices':22077,'body_positions_sha256':observed[0]['positions_sha256'],'body_entity':'body','body_mesh':'mesh-body','body_material':'mat-body','skin':skin,'accessories':accessories}
        camera={'active':True,'global_transform':I.copy(),'viewport':[1280,720],'projection':'synthetic-projection','sub_camera_view':'None'}
        identity={'generation':1,'revision':work['revision'],'body_entity':'body','clip_id':sample['clip_id'],'timeline_id':sample['timeline_id'],'completed':False,'playing':False,'seconds':0,'runtime_ready':True,'appearance_ready':True,'camera':camera,**{k:None for k in ('preview_sha256','pending_open_sha256','open_error','runtime_error','runtime_appearance_error','appearance_error','stage_error','playback_error','seek_request')}}
        digest=hashlib.sha256(text.encode()).hexdigest();identity['work_sha256']=digest;skin['uv_sha256']=observed[0]['uv_sha256'];frame={'endpoint':'native','request_id':'fixture','work_json':text,'work_sha256':digest,'identity':identity,'full_base':base,'appearance':appearance,'observed':observed,'camera':camera}
        report={'endpoint':'native','request_id':'fixture','phase':'ready','acknowledged':True,'request_succeeded':True,'current':True,'captured_identity':identity,'work_json':text,'work_sha256':digest,'appearance':appearance,'base_summary':{k:base[k] for k in ('backend','asset_id','profile_id','generation','revision','parameters','sample')}}
        report.update({'evidence_kind':'held-stable-two-frames','stable_observations':2});frame.update({'evidence_kind':'held-stable-two-frames','stable_observations':2})
        return {'case_id':self.case['id'],'report':report,'frame':frame}
    def test_complete_synthetic_schema_reaches_independent_oracles(self):
        result=validate(self.envelope(),self.case,self.plan,self.oracle,self.work['character']['parameters']);self.assertEqual(result['evidence']['raw_rest_cage']['source_vertices'],CAGE);self.assertEqual(result['evidence']['body']['vertices'],22077)
    def test_accessory_array_mutations_rejected_even_when_claimed_hashes_still_agree(self):
        for change,role,key,replacement in (
            ('eye_position','eyes','positions',[999.,888.,777.]),
            ('hair_normal','hair','normals',[0.,0.,0.]),
            ('eye_uv','eyes','uv_0',[999.,888.]),
            ('eye_indices','eyes','indices',[2,1,0]),
        ):
            value=self.envelope();actual=next(p for p in value['frame']['observed'] if p['role']==role)
            if key=='indices':actual[key]=replacement
            else:actual[key][0]=replacement
            # Report and frame share the original producer labels: equality alone is insufficient.
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,'exported array/observed/production hash'):
                validate(value,self.case,self.plan,self.oracle,self.work['character']['parameters'])
    def test_conflicting_but_correlated_identity_and_sample_bindings_reject(self):
        for change in ('work_sha256','body_entity','clip_id','timeline_id','completed','serial','character_entity','base_asset_id','summary_asset_id'):
            value=self.envelope();frame=value['frame']
            if change in ('work_sha256','body_entity','clip_id','timeline_id'):
                frame['identity'][change]='conflicting-'+change
                value['report']['captured_identity']=copy.deepcopy(frame['identity'])
            elif change=='completed':
                frame['identity'][change]=True
                value['report']['captured_identity']=copy.deepcopy(frame['identity'])
            elif change=='serial':frame['appearance']['serial']+=1
            elif change=='character_entity':frame['appearance'][change]='wrong-character'
            elif change=='base_asset_id':frame['appearance'][change]='wrong-base'
            else:value['report']['base_summary']['asset_id']='wrong-base'
            self.assertEqual(value['report']['captured_identity'],frame['identity'])
            self.assertEqual(value['report']['appearance'],frame['appearance'])
            with self.subTest(change=change),self.assertRaises(ValueError):
                validate(value,self.case,self.plan,self.oracle,self.work['character']['parameters'])
    def test_actual_source_rest_bone_and_image_negative_controls_reject(self):
        for change in ('rest','bone','image','binding','truncated','live','unstable'):
            value=self.envelope();frame=value['frame']
            if change=='rest':
                frame['full_base']['parts'][0]['rest_positions'][0]=[v+2e-6 for v in frame['full_base']['parts'][0]['rest_positions'][0]]
            elif change=='bone':frame['full_base']['bones'][0]['skin'][12]+=2e-6
            elif change=='image':frame['observed'][2]['material']['image']['decoded_rgba_sha256']='wrong'
            elif change=='binding':frame['observed'][2]['mesh_handle']='wrong'
            elif change=='truncated':frame['full_base']['parts'][1]['full_joint_influences']=[]
            elif change=='live':value['report']['evidence_kind']=frame['evidence_kind']='live-transient'
            else:value['report']['stable_observations']=frame['stable_observations']=1
            with self.subTest(change=change),self.assertRaises(ValueError):validate(value,self.case,self.plan,self.oracle,self.work['character']['parameters'])

if __name__=='__main__':unittest.main()
