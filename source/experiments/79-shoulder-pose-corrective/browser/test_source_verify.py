"""Portable synthetic correlation controls; no real assets or GPU evidence."""
import copy,hashlib,json,unittest
from verify_sources import verify_records,MODES,SOURCE,DIAG,QUADS

H='a'*64

def encoded(value):return json.dumps(value,separators=(',',':')).encode()
def pack(r,f,mode):
 rb,fb=encoded(r),encoded(f);raw=b'{"report":'+rb+b',"frame":'+fb+b'}';digest=hashlib.sha256(raw).hexdigest()
 m={'request_id':r['request_id'],'format':'nvwa76-raw-transfer-v1','encoding':'utf-8','bytes':len(raw),'chars':len(raw.decode().encode('utf-16-le'))//2,'sha256':digest,'token':'transfer-1-'+digest,'report_bytes':len(rb),'frame_bytes':len(fb),'report_sha256':hashlib.sha256(rb).hexdigest(),'frame_sha256':hashlib.sha256(fb).hexdigest()}
 c={'request_id':r['request_id'],'mode':mode,'manifest':copy.deepcopy(m),'fences':[{'name':n,'ready':True,'token':m['token'],'exact_report_before_after':True,'exact_frame_before_after':True} for n in ['after-prepare','after-exactText','pre-manifest-upload','post-manifest-response','pre-raw-upload','post-raw-response']]}
 return {'raw':raw,'manifest':m,'currentness':c}

def fixture():
 work='{"fixture":"rear"}';wh=hashlib.sha256(work.encode()).hexdigest();camera={'position':[0,1,-1],'projection':[1,0,1]};transform=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]
 refs=[{'name':role,'display_entity':role+'entity','mesh_handle':role+'mesh','display_transform':transform,'source_ids':QUADS[role][1],'indices':[0,1,2,0,2,3],'positions':[[0,0,0],[1,0,0],[1,1,0],[0,1,0]]} for role in ['body','garment']]
 base={'generation':1,'sample':{'source_seconds':2,'playing':False,'clip_id':'b1_arm_rehearsal_v1'},'parameters':{'torso':0},'bones':[{'matrix':transform}],'parts':refs};compact={k:base[k] for k in ['generation','sample','parameters']};identity={'generation':1,'camera':camera};records={};objects={};ids={m:'fixture-'+m for m in MODES};contract={'root_frozen':True,'stage_rules':{}}
 for index,mode in enumerate(MODES):
  parts=[]
  for ref in refs:
   role=ref['name'];changed=mode=='source_'+role
   buffers={'positions_sha256_le_f32':H,'normals_sha256_le_f32':H,'vertex_colors_sha256_le_f32':H if changed else None,'indices_sha256':H,'vertex_count':4,'index_count':6,'complete_rendered_attributes':[{'id':'0','name':'Position','format':'Float32x3','values':4,'raw_bytes_sha256':H}],'attribute_presence':'complete','raw_byte_endianness':'native target, little-endian on this Mac and Wasm','index_format':'U32','primitive_topology':'TriangleList'}
   if changed:
    buffers.update(vertex_count=6,index_count=None,index_format=None,indices_sha256=hashlib.sha256(b'null').hexdigest());buffers['complete_rendered_attributes'][0]['values']=6
   bounds={'center':[0,0,0],'half_extents':[1,1,1]}
   parts.append({'role':role,'entity':ref['display_entity'],'production_mesh_handle':ref['mesh_handle'],'actual_render_mesh_handle':role+'highlight' if changed else ref['mesh_handle'],'buffers':buffers,'actual_aabb':bounds if changed else None,'computed_mesh_aabb':bounds,'changed_mesh_exact_bounds':True if changed else None,'inherited_production_no_frustum_culling':False,'visibility':'Inherited','material_handle':role+'material','material_debug_sha256':H,'display_transform':transform})
  actual={'parts':parts,'camera':camera,'work_sha256':wh,'generation':1,'mode':SOURCE[index],'target_sha256':None};key=str(index+1)*64;w={'update_epoch':20+index,'publication':{'key_sha256':key,'actual':actual}}
  source={'mode':SOURCE[index],'target_active':False,'publication_key_sha256':key,'actual_render_publication':actual,'pre_visibility_publication_matches':True,'pre_visibility_witness':copy.deepcopy(w),'Last_independent_witness':dict(copy.deepcopy(w),pre_visibility_publication_matches=True),'scope_publication':'fixture','scope':'fixture'}
  if mode=='combined':source.update(target_authored=None,geometry='unchanged production mesh/materials')
  else:
   role=mode.removeprefix('source_');source.update(role=role,source_face0=QUADS[role][0],source_quad_ids=QUADS[role][1],source_render_triangles0=[0,1],display_entity=role+'entity',original_mesh=role+'mesh',ordered_triangle_positions_preserved=True,all_attributes_duplicated_by_existing_Bevy_API=True,only_selected_fan_vertex_colors_changed=True,material_handle=role+'material',material_visibility_culling_and_depth_unchanged=True)
  diag={'mode':DIAG[index],'palette':'Textured'}
  f={'endpoint':'web','request_id':ids[mode],'capture_update_epoch':20+index,'stable_updates':2,'camera':camera,'base':compact,'diagnostic':diag,'source_diagnostic':source,'full_base':base,'buffers':{'production':'unchanged'},'identity':identity,'work_sha256':wh}
  r={k:copy.deepcopy(f[k]) for k in ['endpoint','request_id','capture_update_epoch','stable_updates','camera','base','diagnostic','source_diagnostic','work_sha256']};r.update(phase='ready',current=True,acknowledged=True,request_succeeded=True,captured_identity=identity,work_json=work)
  objects[mode]=copy.deepcopy((r,f));records[mode]=pack(r,f,mode);contract['stage_rules'][mode]={'source_equals':{'mode':SOURCE[index],'target_active':False},'required_source_keys':['publication_key_sha256','actual_render_publication','pre_visibility_witness','Last_independent_witness']}
 return records,contract,ids,objects

class SourceVerifyTests(unittest.TestCase):
 def test_valid_three_synthetic_records(self):
  records,c,ids,_=fixture();out=verify_records(records,c,ids);self.assertEqual(out['status'],'PASS');self.assertIs(out['publication_key_recomputed'],False)
 def reject(self,mode,change):
  records,c,ids,objects=fixture();r,f=objects[mode];change(r,f);records[mode]=pack(r,f,mode)
  with self.assertRaises((ValueError,KeyError,TypeError,IndexError)):verify_records(records,c,ids)
 def mutate_source(self,change):
  def edit(r,f):
   change(f['source_diagnostic']);r['source_diagnostic']=copy.deepcopy(f['source_diagnostic'])
  return edit
 def test_witness_epoch_and_key_red(self):
  for witness in ['pre_visibility_witness','Last_independent_witness']:
   with self.subTest(witness=witness,field='epoch'):self.reject('source_body',self.mutate_source(lambda s:s[witness].update(update_epoch=999)))
   with self.subTest(witness=witness,field='key'):self.reject('source_body',self.mutate_source(lambda s:s[witness]['publication'].update(key_sha256='b'*64)))
 def test_publication_outer_binding_red(self):
  for field,value in [('camera',{'wrong':True}),('work_sha256','b'*64),('generation',999),('parts',[]),('target_sha256',H),('mode','Unknown')]:
   def change(s):
    s['actual_render_publication'][field]=value
    for w in ['pre_visibility_witness','Last_independent_witness']:s[w]['publication']['actual']=copy.deepcopy(s['actual_render_publication'])
   with self.subTest(field=field):self.reject('source_body',self.mutate_source(change))
 def test_base_camera_epoch_stable_and_anchors_red(self):
  for field,value in [('stable_updates',1),('capture_update_epoch',999),('camera',{'wrong':True}),('base',{'wrong':True})]:
   def change(r,f):r[field]=value;f[field]=value
   with self.subTest(field=field):self.reject('source_body',change)
  for field in ['full_base','buffers']:
   def change(r,f):f[field]['unexpected']='changed'
   with self.subTest(anchor=field):self.reject('source_body',change)
 def test_source_flags_unknown_quad_red(self):
  for field,value in [('mode','Unknown'),('unknown_field',True),('target_active',True),('pre_visibility_publication_matches',False),('only_selected_fan_vertex_colors_changed',False),('source_quad_ids',[1,2,3,4]),('source_face0',1),('source_render_triangles0',[0,0])]:
   with self.subTest(field=field):self.reject('source_body',self.mutate_source(lambda s:s.update({field:value})))
  self.reject('source_body',self.mutate_source(lambda s:s['Last_independent_witness'].update(pre_visibility_publication_matches=False)))
 def test_actual_mesh_bounds_and_policy_red(self):
  for field,value in [('changed_mesh_exact_bounds',False),('actual_aabb',{'center':[9,0,0],'half_extents':[1,1,1]}),('entity','wrong'),('production_mesh_handle','wrong'),('display_transform',[]),('material_handle','wrong'),('inherited_production_no_frustum_culling',True)]:
   def change(s):
    s['actual_render_publication']['parts'][0][field]=value
    for w in ['pre_visibility_witness','Last_independent_witness']:s[w]['publication']['actual']=copy.deepcopy(s['actual_render_publication'])
   with self.subTest(field=field):self.reject('source_body',self.mutate_source(change))
  def other(s):
   s['actual_render_publication']['parts'][1]['actual_render_mesh_handle']='unexpected'
   for w in ['pre_visibility_witness','Last_independent_witness']:s[w]['publication']['actual']=copy.deepcopy(s['actual_render_publication'])
  self.reject('source_body',self.mutate_source(other))
  def material_ref(r,f):f['full_base']['parts'][0]['material_handle']='wrong'
  self.reject('source_body',material_ref)
 def test_strict_selected_nonindexed_layout_red(self):
  for mode,role_index in [('combined',0),('source_body',1),('source_garment',0)]:
   def change(s):
    p=s['actual_render_publication']['parts'][role_index];p['buffers'].update(index_count=None,index_format=None)
    for w in ['pre_visibility_witness','Last_independent_witness']:s[w]['publication']['actual']=copy.deepcopy(s['actual_render_publication'])
   with self.subTest(mode=mode):self.reject(mode,self.mutate_source(change))
  for field,value in [('index_count',6),('index_format','U32'),('vertex_count',5),('indices_sha256',H)]:
   def change(s):
    s['actual_render_publication']['parts'][0]['buffers'][field]=value
    for w in ['pre_visibility_witness','Last_independent_witness']:s[w]['publication']['actual']=copy.deepcopy(s['actual_render_publication'])
   with self.subTest(field=field):self.reject('source_body',self.mutate_source(change))
 def test_exact_bytes_independent_id_and_fences_red(self):
  records,c,ids,_=fixture();ids['combined']='wrong'
  with self.assertRaises(ValueError):verify_records(records,c,ids)
  records,c,ids,_=fixture();records['combined']['raw']+=b' '
  with self.assertRaises(ValueError):verify_records(records,c,ids)
  records,c,ids,_=fixture();records['combined']['currentness']['fences'][0]['ready']=False
  with self.assertRaises(ValueError):verify_records(records,c,ids)
if __name__=='__main__':unittest.main()
