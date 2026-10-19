"""Synthetic checker controls from authenticated historical source cages. No render proof."""
import copy,hashlib,importlib.util,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];EXP=Path(__file__).resolve().parent;sys.path.insert(0,str(EXP));import cpu_probe as cpu
spec=importlib.util.spec_from_file_location('h71',ROOT/'experiments/71-b1-character-parameters/hash_encoding.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
def serde_bytes(v):
 def token(v):
  if v is None:return 'null'
  if v is True:return 'true'
  if v is False:return 'false'
  if type(v) is int:return str(v)
  if type(v) is float:return h.promoted_f32_token(v)
  if isinstance(v,str):return json.dumps(v,ensure_ascii=False,separators=(',',':'))
  if isinstance(v,list):return '['+','.join(token(x) for x in v)+']'
  return '{'+','.join(token(k)+':'+token(v[k]) for k in sorted(v))+'}'
 return token(v).encode()
sha=lambda v:hashlib.sha256(serde_bytes(v)).hexdigest()
def summary(base):
 return {k:copy.deepcopy(base[k]) for k in ['generation','revision','character_entity','backend','parameters','sample']}|{'bone_count':len(base['bones']),'bones_sha256':sha(base['bones']),'parts':[{k:copy.deepcopy(p[k]) for k in ['name','display_entity','mesh_handle','source_ids','display_transform']}|{'vertices':len(p['positions']),'indices':len(p['indices']),**{target:sha(p[key]) for target,key in [('positions_sha256','positions'),('normals_sha256','normals'),('rest_positions_sha256','rest_positions'),('indices_sha256','indices')]}} for p in base['parts']],'scope':'synthetic compact fixture for checker only'}
def base_part(p):
 return {'role':p['name'],'entity':p['display_entity'],'mesh_handle':p['mesh_handle'],'source_map':None,'positions':p['positions'],'normals':p['normals'],'uv_0':None,'indices':p['indices'],'display_transform':p['display_transform'],'positions_sha256':sha(p['positions']),'scope':'synthetic checker fixture'}
def aabb(p):
 lo=[min(v[a] for v in p) for a in range(3)];hi=[max(v[a] for v in p) for a in range(3)]
 return {'center':[cpu.f32(cpu.f32(x+y)*.5) for x,y in zip(lo,hi)],'half_extents':[cpu.f32(cpu.f32(y-x)*.5) for x,y in zip(lo,hi)]}
def fixtures(legacy_root,actual68,force_short_cage=False,force_peak_at_zero=False):
 template=json.loads(actual68.read_bytes());out=[]
 for ordinal,case in enumerate(['short-front','long-front','short-quarter','long-quarter']):
  suffix={'short-front':'sf','long-front':'lf','short-quarter':'sq','long-quarter':'lq'}[case]
  legacy=json.loads((legacy_root/f"quality-native/captures/n65-{'sf' if force_short_cage else suffix}-reference-envelope.json").read_bytes())['frame']['snapshot'];raw=(EXP/f'works/{case}.nvwa.json').read_text();work=json.loads(raw);digest=hashlib.sha256(raw.encode()).hexdigest()
  for seconds in [0,2]:
   base=copy.deepcopy(legacy);base.update({'generation':100+ordinal,'revision':work['revision'],'parameters':work['character']['parameters'],'backend':work['profile']['backend'],'asset_id':work['profile']['backend']['asset_id'],'profile_id':work['profile']['id'],'diagnostic_pose':work['character']['diagnostic_pose']});base['sample'].update({'source_seconds':seconds,'position_seconds':seconds,'playing':False,'completed':False,'timeline_id':'arms','serial':2+seconds})
   if seconds==0 and not force_peak_at_zero:
    for b in base['bones']:
     b['posed']=b['rest'];b['canonical_posed']=b['canonical_rest'];b['local_posed']=b['local_rest'];b['skin']=[float(i%5==0) for i in range(16)]
    for p in base['parts']:p['positions']=p['rest_positions'];p['normals']=p['rest_normals']
   parts={p['name']:p for p in base['parts']};buffers=[base_part(p) for p in base['parts']];camera=copy.deepcopy(template['frame']['camera']);pin=json.loads((EXP/f'works/reference-{case}.json').read_text())['camera'];camera.update({'global_transform':pin['global_transform'],'projection':pin['projection'],'viewport':pin['viewport_size_pixels'],'msaa':pin['msaa']})
   appearance=copy.deepcopy(template['frame']['appearance']);appearance.update({'generation':base['generation'],'revision':base['revision'],'serial':base['sample']['serial'],'base_asset_id':base['asset_id'],'character_entity':base['character_entity'],'body_entity':parts['body']['display_entity'],'body_mesh':parts['body']['mesh_handle'],'body_vertices':len(parts['body']['positions']),'body_positions_sha256':sha(parts['body']['positions'])})
   a=cpu.replay(base,'a');low=next(x for x in template['frame']['appearance']['accessories'] if x['name']=='eyes');eye_header=copy.deepcopy(next(x for x in template['frame']['buffers'] if x['role']=='eyes'))
   for accessory in appearance['accessories']:
    accessory['display_transform']=parts['body']['display_transform']
    if accessory['name']=='eyes':
     accessory.update({'positions_sha256':sha(a['positions']),'normals_sha256':sha(a['normals']),'uv_sha256':sha(a['uv_0']),'indices_sha256':sha(a['indices'])})
   hair=copy.deepcopy(next(x for x in template['frame']['buffers'] if x['role']=='hair'));hair['display_transform']=parts['body']['display_transform']
   identity=copy.deepcopy(template['frame']['identity']);identity.update({'work_sha256':digest,'generation':base['generation'],'revision':base['revision'],'body_entity':parts['body']['display_entity'],'seconds':seconds,'playing':False,'completed':False,'seek_request':None,'camera':camera,'clip_id':'b1_arm_rehearsal_v1','timeline_id':'arms'})
   for variant,code in [('AOriginal','a'),('BHigh','b')]:
    replay=a if code=='a' else cpu.replay(base,code);eye=eye_header.copy();eye.update({k:replay[k] for k in ['positions','normals','uv_0','indices']});eye.update({'display_transform':parts['body']['display_transform'],'positions_sha256':sha(replay['positions'])});bound=buffers+[eye,hair]
    diagnostic=copy.deepcopy(template['frame']['diagnostic']);diagnostic['mode']='Combined';diagnostic['palette']='Textured';diagnostic['visibility_prepared_before_postupdate']=True
    for t in diagnostic['targets']:
     b=next(x for x in bound if x['role']==t['role']);t['entity']=b['entity'];t['mesh_handle']=b['mesh_handle']
    target=next(x for x in diagnostic['targets'] if x['role']=='eyes');image=low['texture']
    c={'variant':variant,'A_replay_exact':True,'pre_visibility_publication_matches':True,'entity':eye['entity'],'mesh_handle':eye['mesh_handle'],'material_handle':target['material_handle'],'image_handle':image['image_handle'],'decoded_rgba_sha256':image['decoded_rgba_sha256'],'original_standard_material_debug':target['production_material']['full_standard_material_debug'],'display_transform':eye['display_transform'],'generation':base['generation'],'sample':base['sample'],'source_vertices':replay['source_count'],'render_vertices':len(replay['positions']),'triangles':len(replay['indices'])//3,'rest_source_positions':replay['rest'],'full_positive_source_weights':replay['weights'],'bones':base['bones'],'actual_aabb':aabb(replay['positions']),'published_positions_sha256':sha(replay['positions']),'published_normals_sha256':sha(replay['normals'])}
    c['pre_visibility_publication']={'variant':variant,'positions_sha256':c['published_positions_sha256'],'normals_sha256':c['published_normals_sha256'],'placement':c['display_transform'],'camera':camera,'work_sha256':digest,'generation':base['generation']}
    request=f'synthetic-{case}-{seconds}-{variant}';f={'endpoint':'web','request_id':request,'work_sha256':digest,'full_base':base,'base':summary(base),'appearance':appearance,'buffers':bound,'candidate':c,'stable_updates':2,'camera':camera,'identity':identity,'diagnostic':diagnostic};r={'endpoint':'web','request_id':request,'work_sha256':digest,'work_json':raw,'phase':'ready','acknowledged':True,'request_succeeded':True,'current':True,'captured_identity':identity,'appearance':appearance,'base':f['base'],'camera':camera};out.append({'report':r,'frame':f})
 return out
