"""Current Work/body/source/publication verifier; original independent71/60 math."""
import hashlib,importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);out=importlib.util.module_from_spec(spec);spec.loader.exec_module(out);return out
oracle71=module('eye73_oracle71',ROOT/'experiments/71-b1-character-parameters/oracle.py')
hash71=module('eye73_hash71',ROOT/'experiments/71-b1-character-parameters/hash_encoding.py')
sys.path.insert(0,str(ROOT/'experiments/60-b1-continuous-motion'))
from checker import check_bones
def serde_value_sha256(value):
 def token(v):
  if v is None:return 'null'
  if v is True:return 'true'
  if v is False:return 'false'
  if type(v) is int:return str(v)
  if type(v) is float:return hash71.promoted_f32_token(v)
  if isinstance(v,str):return json.dumps(v,ensure_ascii=False,separators=(',',':'))
  if isinstance(v,list):return '['+','.join(token(x) for x in v)+']'
  require(isinstance(v,dict),'JSON object/array primitive required')
  return '{'+','.join(token(k)+':'+token(v[k]) for k in sorted(v))+'}'
 return hashlib.sha256(token(value).encode()).hexdigest()
ORACLE=None
require=oracle71.require
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def strict_json(text):
 def pairs(items):
  out={}
  for key,value in items:require(key not in out,'duplicate JSON key '+key);out[key]=value
  return out
 return json.loads(text,object_pairs_hook=pairs,parse_constant=lambda _:require(False,'nonfinite JSON'))
def frame_binding(e,topology):
 global ORACLE
 if ORACLE is None:ORACLE=oracle71.Oracle()
 r,f=e['report'],e['frame'];b=f['full_base'];i=f['identity'];a=f['appearance'];c=f['candidate'];sample=b['sample'];raw=r['work_json'];w=strict_json(raw)
 require(all(oracle71.finite(v) for v in b['parameters'].values()),'nonfinite/non-numeric actual parameters')
 for k in ['generation','revision']:require(type(b[k]) is int and b[k]>=0,'actual integer '+k+' required')
 for k in ['source_seconds','position_seconds']:require(oracle71.finite(sample[k]),'finite numeric actual '+k+' required')
 oracle71.vector(f['camera']['global_transform'],16,'actual camera')
 require(sha(raw.encode())==r['work_sha256']==f['work_sha256']==i['work_sha256'],'serialized Work hash mismatch')
 require(f['base']['bone_count']==len(b['bones'])==53 and serde_value_sha256(b['bones'])==f['base']['bones_sha256'],'compact/full53bone digest differs; preserve raw Rust JSON including negative zero')
 require(r['captured_identity']==i and r['base']==f['base'] and r['appearance']==a and r['camera']==f['camera']==i['camera'],'report/frame current records differ')
 require(i['runtime_ready'] is True and i['appearance_ready'] is True,'runtime/current appearance not ready')
 for k in ['preview_sha256','pending_open_sha256','open_error','runtime_error','runtime_appearance_error','appearance_error','stage_error','seek_request']:require(k in i and i[k] is None,'unverified current identity '+k)
 for key in ['generation','revision','character_entity','backend','parameters','sample']:require(f['base'][key]==b[key],'compact/full base mismatch '+key)
 require(b['parameters']==w['character']['parameters'] and b['backend']==w['profile']['backend'] and b['profile_id']==w['profile']['id'] and b['asset_id']==w['profile']['backend']['asset_id'],'typed Work/current base recipe or backend mismatch')
 require(b['diagnostic_pose']==w['character']['diagnostic_pose'] and b['mode']=='motion','typed diagnostic pose/motion mismatch')
 require(b['revision']==w['revision']==a['revision']==i['revision'] and b['generation']==a['generation']==i['generation']==c['generation'],'current generation/revision mismatch')
 require(a['requested']==w['character']['appearance']==a['applied'] and a['ready'] is True and a['error'] is None and a['base_asset_id']==b['asset_id'],'current applied selection differs')
 require(a['serial']==sample['serial'] and type(sample['serial']) is int and sample['serial']>0,'actual appearance/base sample serial mismatch')
 require(len(w['timeline'])>0,'saved timeline missing');entries=[t for t in w['timeline'] if t['id']==sample['timeline_id']];require(len(entries)==1,'actual timeline entry absent/ambiguous')
 entry=entries[0];require(entry['clip_id']==sample['clip_id']=='b1_arm_rehearsal_v1','held clip differs from saved timeline')
 require(sample['source_seconds'] in [0,2] and sample['position_seconds']==sample['source_seconds'] and sample['playing'] is False and sample['completed'] is False,'held source/cursor time mismatch')
 for left,right in [('clip_id','clip_id'),('timeline_id','timeline_id'),('seconds','position_seconds'),('playing','playing'),('completed','completed')]:require(i[left]==sample[right],'identity/sample mismatch '+left)
 parts={p['name']:p for p in b['parts']};require(len(parts)==len(b['parts']) and set(parts)=={'body','garment'},'body/garment part set differs')
 buffers={p['role']:p for p in f['buffers']};require(set(buffers)=={'body','garment','eyes','hair'} and len(buffers)==len(f['buffers']),'actual role set differs')
 require(i['body_entity']==a['body_entity']==parts['body']['display_entity']==buffers['body']['entity'],'actual body entity mismatch')
 require(a['character_entity']==b['character_entity'] and a['body_mesh']==parts['body']['mesh_handle'] and a['body_vertices']==len(parts['body']['positions']),'actual body source binding mismatch')
 proof={}
 for name,p in parts.items():
  actual=buffers[name];require(actual['entity']==p['display_entity'] and actual['mesh_handle']==p['mesh_handle'],'part actual Mesh3d binding mismatch')
  for field in ['positions','normals','indices','display_transform']:require(actual[field]==p[field],'full/base actual buffer differs '+name+' '+field)
  oracle71.vector(p['display_transform'],16,'actual part placement');oracle71.vector(p['model_to_world'],16,'recorded model frame')
  rows=len(p['source_ids']);require(rows==topology[name]['render_vertices'] and len(p['indices'])==topology[name]['indices'],'actual body/garment count differs')
  require(hash71.mesh_array_sha256(p['source_ids'],integer=True)==topology[name]['source_ids_sha256'] and hash71.mesh_array_sha256(p['indices'],integer=True)==topology[name]['indices_sha256'],'source ID/index correspondence differs '+name)
  for key in ['positions','normals','rest_positions','rest_normals']:oracle71.rows(p[key],3,rows,name+' '+key)
  oracle71.rows(p['tangents'],4,rows,name+' tangents')
  compact=[x for x in f['base']['parts'] if x['name']==name];require(len(compact)==1,'compact part missing/duplicate');compact=compact[0]
  for key in ['display_entity','mesh_handle','source_ids','display_transform']:require(compact[key]==p[key],'compact/full part source binding differs '+key)
  require(compact['vertices']==rows and compact['indices']==len(p['indices']),'compact part counts differ')
  for field,key in [('positions','positions_sha256'),('normals','normals_sha256'),('rest_positions','rest_positions_sha256'),('indices','indices_sha256')]:require(hash71.mesh_array_sha256(p[field],integer=field=='indices')==compact[key],'compact part array hash differs '+field)
  proof[name]=oracle71.full_positive_lbs(p,b['bones'])
  require(hash71.mesh_array_sha256(actual['positions'])==actual['positions_sha256'],'actual POSITION digest mismatch '+name)
 parameters={name:0 for name in ORACLE.targets};parameters.update(w['character']['parameters']);proof['raw_rest_cage']=ORACLE.rest_error(parts['body'],parameters)
 proof['authored_FK']=check_bones(b['bones'],sample['clip_id'],sample['source_seconds'])[1:]
 require(hash71.mesh_array_sha256(buffers['body']['positions'])==a['body_positions_sha256'],'current appearance/body array digest mismatch')
 source_map=json.loads((ROOT/'experiments/73-high-poly-eyes/works'/('eye-source-map.json' if c['variant']=='AOriginal' else 'high-source-map.json')).read_text())
 require(hash71.mesh_array_sha256(buffers['eyes']['uv_0'])==hash71.mesh_array_sha256(source_map['uv_0']),'actual eye UV source identity differs')
 for key in ['positions','normals']:
  digest=hash71.mesh_array_sha256(buffers['eyes'][key]);require(digest==c['published_'+key+'_sha256'],'actual eye publication digest mismatch '+key)
 expected={'variant':c['variant'],'positions_sha256':c['published_positions_sha256'],'normals_sha256':c['published_normals_sha256'],'placement':c['display_transform'],'camera':f['camera'],'work_sha256':f['work_sha256'],'generation':b['generation']}
 require(c.get('pre_visibility_publication')==expected,'previsibility publication witness differs/missing')
 return proof
