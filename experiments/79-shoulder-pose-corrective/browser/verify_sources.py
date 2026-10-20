"""Offline correlation verifier for three original b1_79 source proofs. No GPU claim."""
from pathlib import Path
from decimal import Decimal
import argparse,hashlib,json,math,re
from collect_transfer import verify_bytes,raw_object
MODES=('combined','source_body','source_garment');DIAG=('Combined','SourceBody','SourceGarment');SOURCE=('baseline','SourceBody','SourceGarment')
QUADS={'body':(7941,[8319,8318,8309,8310]),'garment':(131,[830,168,212,847])}
COMMON={'mode','target_active','publication_key_sha256','actual_render_publication','pre_visibility_publication_matches','pre_visibility_witness','Last_independent_witness','scope_publication'}
BASE={'target_authored','geometry','scope'}
COLOR={'role','source_face0','source_quad_ids','source_render_triangles0','display_entity','original_mesh','ordered_triangle_positions_preserved','all_attributes_duplicated_by_existing_Bevy_API','only_selected_fan_vertex_colors_changed','material_handle','material_visibility_culling_and_depth_unchanged','scope'}
def need(ok,message):
 if not ok:raise ValueError(message)
def equal(a,b):
 if isinstance(a,bool) or isinstance(b,bool):return type(a) is type(b) and a==b
 if isinstance(a,dict) or isinstance(b,dict):return isinstance(a,dict) and isinstance(b,dict) and set(a)==set(b) and all(equal(a[k],b[k]) for k in a)
 if isinstance(a,list) or isinstance(b,list):return isinstance(a,list) and isinstance(b,list) and len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
 return a==b
def same(a,b,message):need(equal(a,b),message)
def sha(value):need(isinstance(value,str) and re.fullmatch(r'[0-9a-f]{64}',value) is not None,'invalid SHA256');return value
def integer(value,label):need(type(value) is int and value>=0,label+' must be nonnegative integer');return value
def required(obj,keys,label):need(isinstance(obj,dict) and set(keys).issubset(obj),label+' missing required fields')
def aabb(value):
 required(value,('center','half_extents'),'AABB')
 for key in ['center','half_extents']:
  rows=value[key];need(isinstance(rows,list) and len(rows)==3,'AABB shape')
  for x in rows:need(not isinstance(x,bool) and isinstance(x,(int,float,Decimal)) and math.isfinite(x) and (key!='half_extents' or x>=0),'AABB nonfinite/negative')
def publication_parts(actual,frame,mode):
 required(actual,('parts','camera','work_sha256','generation','mode','target_sha256'),'actual publication');need(set(actual)=={'parts','camera','work_sha256','generation','mode','target_sha256'},'unknown publication field')
 same(actual['camera'],frame['camera'],'actual publication camera differs');same(actual['work_sha256'],frame['work_sha256'],'actual publication Work differs');same(actual['generation'],frame['full_base']['generation'],'actual publication generation differs');need(actual['mode']==SOURCE[MODES.index(mode)] and actual['target_sha256'] is None,'actual publication mode/target differs')
 refs=frame['full_base']['parts'];need(isinstance(refs,list) and len(refs)==2,'two production reference parts required');refs={p['name']:p for p in refs};need(set(refs)=={'body','garment'},'production role set differs');parts=actual['parts'];need(isinstance(parts,list) and len(parts)==2,'two actual published parts required');parts={p['role']:p for p in parts};need(set(parts)==set(refs),'actual published role set differs')
 for role,p in parts.items():
  ref=refs[role];required(p,('entity','production_mesh_handle','actual_render_mesh_handle','buffers','actual_aabb','computed_mesh_aabb','changed_mesh_exact_bounds','inherited_production_no_frustum_culling','visibility','material_handle','material_debug_sha256','display_transform'),'published part');same(p['entity'],ref['display_entity'],'publication entity differs');same(p['production_mesh_handle'],ref['mesh_handle'],'production mesh binding differs');same(p['display_transform'],ref['display_transform'],'publication placement differs');need(type(p['inherited_production_no_frustum_culling']) is bool,'culling policy absent');sha(p['material_debug_sha256']);need(isinstance(p['material_handle'],str) and p['material_handle'] and isinstance(p['visibility'],str),'material/visibility absent');aabb(p['computed_mesh_aabb'])
  for field in ['material_handle','material_debug_sha256','visibility','inherited_production_no_frustum_culling']:
   if field in ref:same(p[field],ref[field],'full production reference '+field+' differs')
  need(isinstance(p['actual_render_mesh_handle'],str) and p['actual_render_mesh_handle'] and isinstance(p['production_mesh_handle'],str) and p['production_mesh_handle'],'mesh handles absent')
  changed=(mode=='source_'+role)
  if changed:need(p['actual_render_mesh_handle']!=p['production_mesh_handle'] and p['changed_mesh_exact_bounds'] is True,'changed mesh/bounds flag false');aabb(p['actual_aabb']);same(p['actual_aabb'],p['computed_mesh_aabb'],'changed AABB differs from computed mesh bounds')
  else:need(p['actual_render_mesh_handle']==p['production_mesh_handle'] and p['changed_mesh_exact_bounds'] is None,'unchanged mesh/bounds association differs')
  b=p['buffers'];required(b,('positions_sha256_le_f32','normals_sha256_le_f32','vertex_colors_sha256_le_f32','indices_sha256','vertex_count','index_count','complete_rendered_attributes','attribute_presence','raw_byte_endianness','index_format','primitive_topology'),'actual rendered buffers')
  for k in ['positions_sha256_le_f32','normals_sha256_le_f32','indices_sha256']:sha(b[k])
  if b['vertex_colors_sha256_le_f32'] is not None:sha(b['vertex_colors_sha256_le_f32'])
  vertices=integer(b['vertex_count'],'vertex count');need(vertices>0 and b['primitive_topology']=='TriangleList','vertex count/topology differs')
  if changed:
   need(b['index_count'] is None and b['index_format'] is None,'selected source mesh must be nonindexed');need(vertices==len(ref['indices']) and vertices%3==0,'selected source vertex expansion differs from production indices');need(b['indices_sha256']==hashlib.sha256(b'null').hexdigest(),'nonindexed mesh indices hash differs')
  else:
   need(integer(b['index_count'],'index count')==len(ref['indices']) and b['index_count']>0 and b['index_count']%3==0 and b['index_format'] in ['U16','U32'],'production mesh must retain indexed triangle layout');need(vertices==len(ref['positions']),'production vertex count differs')
  need(b['raw_byte_endianness']=='native target, little-endian on this Mac and Wasm' and isinstance(b['attribute_presence'],str),'attribute/endian metadata absent');attrs=b['complete_rendered_attributes'];need(isinstance(attrs,list) and attrs,'complete rendered attributes absent');ids=[]
  for attr in attrs:
   required(attr,('id','name','format','values','raw_bytes_sha256'),'render attribute');need(isinstance(attr['id'],str) and isinstance(attr['name'],str) and isinstance(attr['format'],str) and attr['values']==b['vertex_count'],'attribute identity/count differs');sha(attr['raw_bytes_sha256']);ids.append(attr['id'])
  need(len(set(ids))==len(ids),'duplicate rendered attribute')
 return parts,refs
def verify_one(raw,manifest,currentness,contract,expected_id,mode):
 verify_bytes(manifest,raw,expected_request_id=expected_id);envelope=raw_object(raw,'record');r,f=envelope['report'],envelope['frame'];need(r['endpoint']==f['endpoint']=='web','Web endpoint required');required(r,('capture_update_epoch','stable_updates','camera','base','source_diagnostic','work_json'),'report');required(f,('capture_update_epoch','stable_updates','camera','base','source_diagnostic','full_base','buffers'),'frame')
 for field in ['capture_update_epoch','stable_updates','camera','base','diagnostic','source_diagnostic']:same(r[field],f[field],'report/frame '+field+' mismatch')
 epoch=integer(f['capture_update_epoch'],'capture epoch');need(integer(f['stable_updates'],'stable updates')>=2,'stable updates below2');need(f['diagnostic']['mode']==DIAG[MODES.index(mode)] and f['diagnostic']['palette']=='Textured','diagnostic mode/palette differs');need(isinstance(r['work_json'],str) and hashlib.sha256(r['work_json'].encode()).hexdigest()==r['work_sha256'],'original Work string hash differs')
 base=f['full_base'];required(base,('generation','sample','bones','parts','parameters'),'full base');integer(base['generation'],'base generation');need(isinstance(base['bones'],list) and base['bones'],'bones absent');need(base['sample']['source_seconds']==2 and base['sample']['playing'] is False and base['sample']['clip_id']=='b1_arm_rehearsal_v1','held arm2 absent')
 for key in ['generation','sample','parameters']:same(f['base'][key],base[key],'compact/full base '+key+' mismatch')
 if 'camera' in f['identity']:same(f['identity']['camera'],f['camera'],'captured identity camera differs')
 s=f['source_diagnostic'];need(set(s)==COMMON|(BASE if mode=='combined' else COLOR),'unknown/missing source schema');need(s['mode']==SOURCE[MODES.index(mode)] and s['target_active'] is False and s['pre_visibility_publication_matches'] is True,'source mode/publication/target flag false');rule=contract['stage_rules'][mode]
 for key,value in rule['source_equals'].items():need(key in s and equal(s[key],value),'root-fixed source field mismatch '+key)
 for key in rule['required_source_keys']:need(key in s and s[key] is not None,'unknown root-required source field '+key)
 key=sha(s['publication_key_sha256']);actual=s['actual_render_publication']
 for name in ['pre_visibility_witness','Last_independent_witness']:
  w=s[name];same(integer(w['update_epoch'],'witness epoch'),epoch,'witness epoch differs');need(sha(w['publication']['key_sha256'])==key,'witness publication key differs');same(w['publication']['actual'],actual,'independent actual publication differs')
 need(s['Last_independent_witness']['pre_visibility_publication_matches'] is True,'Last publication match false');parts,refs=publication_parts(actual,f,mode)
 if mode=='combined':need(s['target_authored'] is None and s['geometry']=='unchanged production mesh/materials','baseline geometry/target differs')
 else:
  role=mode.removeprefix('source_');face,quad=QUADS[role];need(s['role']==role and s['source_face0']==face and equal(s['source_quad_ids'],quad),'fixed source quad differs')
  for flag in ['ordered_triangle_positions_preserved','all_attributes_duplicated_by_existing_Bevy_API','only_selected_fan_vertex_colors_changed','material_visibility_culling_and_depth_unchanged']:need(s[flag] is True,'source preservation flag false '+flag)
  same(s['display_entity'],refs[role]['display_entity'],'source display entity differs');same(s['original_mesh'],refs[role]['mesh_handle'],'source original mesh differs');same(s['material_handle'],parts[role]['material_handle'],'source material differs');tris=s['source_render_triangles0'];need(isinstance(tris,list) and len(tris)==2 and all(type(t) is int and t>=0 for t in tris) and len(set(tris))==2,'two source triangles required');indices=refs[role]['indices'];ids=refs[role]['source_ids'];union=set()
  for t in tris:
   need(3*t+3<=len(indices),'source triangle out of range');corners=[ids[i] for i in indices[3*t:3*t+3]];need(set(corners).issubset(quad) and len(set(corners))==3,'source triangle maps outside fixed quad');union.update(corners)
  need(union==set(quad),'source fan does not cover fixed quad')
 need(currentness['request_id']==expected_id and currentness['mode']==mode,'currentness request/mode differs');same(currentness['manifest'],manifest,'currentness manifest differs');fences=currentness['fences'];need(isinstance(fences,list) and fences,'currentness fences absent');required_names={'after-prepare','after-exactText','pre-manifest-upload','post-manifest-response','pre-raw-upload','post-raw-response'};need(required_names.issubset({x['name'] for x in fences}),'currentness fence missing')
 for fence in fences:need(fence.get('ready') is True and fence.get('token')==manifest['token'] and fence.get('exact_report_before_after') is True and fence.get('exact_frame_before_after') is True,'currentness fence false')
 return {'report':r,'frame':f,'parts':parts,'sha256':hashlib.sha256(raw).hexdigest(),'publication_key':key}
def verify_records(records,contract,expected_ids):
 need(isinstance(contract,dict) and contract.get('root_frozen') is True,'root contract not frozen');need(set(contract['stage_rules'])==set(MODES),'root stage schema differs');need(set(records)==set(expected_ids)==set(MODES),'exact three records/independent IDs required');need(len(set(expected_ids.values()))==3 and all(isinstance(v,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,64}',v) for v in expected_ids.values()),'independent IDs invalid/duplicate');verified={}
 for mode in MODES:
  item=records[mode];verified[mode]=verify_one(item['raw'],item['manifest'],item['currentness'],contract,expected_ids[mode],mode)
 first=verified['combined'];r0,f0=first['report'],first['frame']
 for mode in MODES[1:]:
  item=verified[mode];r,f=item['report'],item['frame']
  for a,b,label in [(r['work_json'],r0['work_json'],'Work string'),(r['captured_identity'],r0['captured_identity'],'identity'),(f['full_base'],f0['full_base'],'full production base'),(f['buffers'],f0['buffers'],'production buffers'),(f['camera'],f0['camera'],'camera')]:same(a,b,'three-proof '+label+' changed')
  for role,p in item['parts'].items():
   original=first['parts'][role]
   for k in ['entity','production_mesh_handle','inherited_production_no_frustum_culling','visibility','material_handle','material_debug_sha256','display_transform']:same(p[k],original[k],'production publication '+k+' changed')
   if mode!='source_'+role:same(p,original,'nonselected actual publication changed')
 return {'status':'PASS','records':{mode:{'request_id':expected_ids[mode],'original_record_sha256':verified[mode]['sha256'],'publication_key_sha256':verified[mode]['publication_key']} for mode in MODES},'publication_key_recomputed':False,'scope':'exact original bytes plus source/publication correlation; no numerical reserialization hash, independent geometry oracle, GPU pixel ownership, screenshot or quality admission'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--input-root',type=Path,required=True);p.add_argument('--contract',type=Path,required=True);p.add_argument('--expected-ids',required=True,help='root-independent JSON object mapping three mode names to IDs');a=p.parse_args();contract_raw=a.contract.read_bytes();contract=raw_object(contract_raw,'root contract');ids=raw_object(a.expected_ids.encode(),'independent IDs');records={}
 for mode in MODES:
  folder=a.input_root/mode;records[mode]={'raw':(folder/'capture.json').read_bytes(),'manifest':raw_object((folder/'manifest.json').read_bytes(),'manifest'),'currentness':raw_object((folder/'currentness.json').read_bytes(),'currentness')}
 result=verify_records(records,contract,ids);result['root_contract_original_sha256']=hashlib.sha256(contract_raw).hexdigest();print(json.dumps(result,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
