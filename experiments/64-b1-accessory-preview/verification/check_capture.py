#!/usr/bin/env python3
"""Frozen r4 Rust / r5 Python sink adapter. Protocol binding only; no independent world/GPU oracle."""
import argparse, collections, copy, hashlib, json, math, re
from pathlib import Path
import source_reference as ref
HERE=Path(__file__).resolve().parent
R4_CANONICAL='549ba3161723a92db3065fa79edd2d869dc06ea4c809558a8a2c6ef1f71303d4'
REFERENCE_SHA='46d0e909b8f08822941e24e20d7fffdd47105b7ef86e0046da9f2a4fe225c572'
FREEZE=HERE/'source-freeze-r5.json'
need=ref.need
RUNTIME_FIELDS=frozenset(('identity','generation','revision','sample','bone_names','actual_skin_matrices','accessories','material_conversion'))
COMPACT_RUNTIME_FIELDS=RUNTIME_FIELDS-{'actual_skin_matrices'}
ACCESSORY_FIELDS=frozenset(('name','entity','mesh_handle','source_vertices','source_uv_pairs','rest_model_m','rest_normals','full_normalized_positive_influences','axis_scales','positions','normals','uv_0','indices','display_transform','model_to_world_record_only','material','tangents','posed_model_bounds_m','posed_stage_bounds_m','actual_cpu_upload_sha256','observation','not_saved'))
BULK_FIELDS=frozenset(('rest_model_m','rest_normals','full_normalized_positive_influences','positions','normals','uv_0','indices','source_uv_pairs'))
COMPACT_ACCESSORY_FIELDS=ACCESSORY_FIELDS-BULK_FIELDS
MATERIAL_FIELDS=frozenset(('handle','base_color','roughness','metallic','alpha','double_sided','cull_mode','texture','image_handle','image_width','image_height','format','decoded_rgba_sha256','observation'))
def require_fields(value,expected,label):
 need(type(value) is dict,label+' object required')
 need(set(value)==expected,label+' frozen field set differs: missing='+','.join(sorted(expected-set(value)))+' extra='+','.join(sorted(set(value)-expected)))
def require_observations(value,compact,label):
 require_fields(value,COMPACT_ACCESSORY_FIELDS if compact else ACCESSORY_FIELDS,label)
 require_fields(value['material'],MATERIAL_FIELDS,label+' material')
 for field in ('entity','mesh_handle'):
  need(type(value[field]) is str and bool(value[field].strip()),label+' missing/invalid '+field)
 for field in ('handle','image_handle'):
  need(type(value['material'][field]) is str and bool(value['material'][field].strip()),label+' missing/invalid material '+field)
 digest=value['actual_cpu_upload_sha256']
 need(type(digest) is str and re.fullmatch('[0-9a-f]{64}',digest) is not None,label+' malformed actual CPU upload sha256')
 need(type(value['axis_scales']) is list and len(value['axis_scales'])==3 and ref.finite(value['axis_scales']),label+' invalid axis_scales observation')
 need(type(value['model_to_world_record_only']) is list and len(value['model_to_world_record_only'])==16 and ref.finite(value['model_to_world_record_only']),label+' invalid record-only model_to_world observation')

def load(path):
 def pairs(items):
  out={}
  for k,v in items:need(k not in out,'duplicate JSON key '+k);out[k]=v
  return out
 def constant(v):raise ValueError('nonfinite JSON '+v)
 v=json.loads(path.read_bytes(),object_pairs_hook=pairs,parse_constant=constant)
 def walk(x):
  if isinstance(x,dict):
   for v in x.values():walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
  elif type(x) is float:need(math.isfinite(x),'nonfinite JSON number')
 walk(v);return v

def verify_freeze():
 need(ref.sha(HERE/'source_reference.py')==REFERENCE_SHA,'frozen source_reference.py changed')
 frozen=load(FREEZE);need(hashlib.sha256(json.dumps(frozen,sort_keys=True).encode()).hexdigest()==R4_CANONICAL,'r4 freeze identity')
 for p,h in frozen.items():need(ref.sha(ref.REPO/p)==h,'r4 source changed '+p)
 manifest_path=ref.ASSETS/'asset-manifest.json';need(ref.sha(manifest_path)=='620099486462ed31f5ca0a7e06b351d8fb8a6a59120f85b604d5ea94c3808a59','pinned source manifest identity')
 manifest=load(manifest_path)
 for path,identity in manifest['outputs'].items():
  original=ref.ASSETS/path;need(ref.sha(original)==identity['sha256'] and original.stat().st_size==identity['size'],'pinned source bytes '+path)
 need(ref.sha(ref.REPO/'assets/characters/mpfb-b1-v1/weights.game_engine.json')=='9f4a773e74ce5ba08415b4f30070338e9f75bae5971b5075b10cd6b9caa58473','pinned stable53 source weights')
 return {'authenticated_source_payloads':len(manifest['outputs']),'source_weights_sha256':'9f4a773e74ce5ba08415b4f30070338e9f75bae5971b5075b10cd6b9caa58473','canonical_sha256':R4_CANONICAL,'file_sha256':ref.sha(FREEZE),'files':len(frozen),'reference_sha256':REFERENCE_SHA}

def array(value,count,width,label):
 need(type(value) is list and len(value)==count,label+' length')
 need(all(type(p) is list and len(p)==width and ref.finite(p) for p in value),label+' dimensions/nonfinite')

def same_weights(actual,expected,label):
 need(len(actual)==len(expected),label+' source weight coverage')
 maximum=0.
 for a,e in zip(actual,expected):
  need(type(a) is list and all(type(v) is list and len(v)==2 and type(v[0]) is int and 0<=v[0]<53 and type(v[1]) in (float,int) and math.isfinite(v[1]) and v[1]>0 for v in a),label+' invalid influences')
  da=dict(a);de=dict(e);need(len(da)==len(a) and set(da)==set(de),label+' missing/duplicate/extra positive final joints')
  need(abs(math.fsum(da.values())-1)<1e-6,label+' weights not normalized')
  delta=math.fsum(abs(da[j]-de[j]) for j in de);maximum=max(maximum,delta);need(delta<=ref.TOL,label+' normalized influence error')
 return maximum

def protocol(record,command,receipt):
 need(type(record) is dict and set(record)=={'request','report','frame'},'exact capture envelope required')
 frame=record['frame'];report=record['report'];snapshot=frame['snapshot'];runtime=frame['appearance']['accessory_runtime']
 require_fields(runtime,RUNTIME_FIELDS,'full accessory runtime')
 need(record['request']==frame['request']==report['request']==receipt['request']==command,'sent command/report/frame/receipt mismatch')
 need(report==receipt,'separately observed compact report differs; stale/error/pending receipt')
 need(report['phase']=='captured' and report['desired']==report['applied']=='skin+eyes+hair','current accessories mode not captured')
 need(frame['appearance']['state']==report['appearance']['state']=='skin','body appearance state disagrees with mode')
 need(snapshot['schema_version']==1 and snapshot['asset_id']=='mpfb-hm08-game-engine-female-sportsuit01-v1' and snapshot['profile_id']=='nvwa-mpfb-b1-motion-v1','B1 snapshot identity')
 need(report['geometry_equal'] is True and frame['geometry_equal'] is True,'geometry invariant failed')
 hashes=[report[k] for k in ('geometry_before_sha256','geometry_after_sha256')]+[frame[k] for k in ('geometry_before_sha256','geometry_after_sha256')]
 need(len(set(hashes))==1 and re.fullmatch('[0-9a-f]{64}',hashes[0]) is not None,'geometry hash protocol mismatch')
 need(type(snapshot['sample']['serial']) is int and snapshot['sample']['serial']>=0,'published snapshot serial missing/null')
 need('stream_frame' not in snapshot['sample'],'live sample cannot be published snapshot')
 for key in ('generation','revision','sample'):need(runtime[key]==snapshot[key],'stale accessory '+key)
 need(report['sample']==snapshot['sample'] and report['parameters']==snapshot['parameters'],'report snapshot sample/shape differs')
 need(report['requested_published_generation']==report['applied_generation']==snapshot['generation'],'report generation mismatch')
 identity=runtime['identity'];body=next(p for p in snapshot['parts'] if p['name']=='body')
 need(identity=={'generation':snapshot['generation'],'revision':snapshot['revision'],'character':snapshot['character_entity'],'body':body['mesh_handle'],'parameters':snapshot['parameters']},'stale accessory entity/mesh/cache identity')
 need(report['identity']['revision']==snapshot['revision'] and report['identity']['parameters']==snapshot['parameters'],'current report marker mismatch')
 need(report['identity']['runtime_ready'] is True and report['identity']['runtime_error'] is None,'current report runtime unavailable')
 need([body['display_entity'],body['mesh_handle'],True] in report['identity']['display_mesh_bindings'],'body entity/mesh absent from current report marker')
 bones=snapshot['bones'];need(len(bones)==53 and len(set(b['name'] for b in bones))==53,'stable53 bones')
 # Frozen r4 actual_skin_matrices contains full BoneFrame objects, exactly as source exports.
 need(runtime['actual_skin_matrices']==bones,'runtime actual_skin_matrices differs from same capture bone frames')
 need(runtime['bone_names']==[b['name'] for b in bones],'bone order mismatch')
 for b in bones:need(len(b['skin'])==16 and ref.finite(b['skin']),'nonfinite actual skin matrix')
 if command['action']=='sample':
  need(snapshot['parameters']=={k:command[k] for k in ('torso_length','jaw_drop')},'requested shape not captured')
  sample=snapshot['sample'];need(sample['clip_id']==command['clip_id'] and sample['timeline_id']=='probe-entry' and abs(sample['source_seconds']-command['seconds'])<=1e-6,'requested source sample not captured')
 compact=report['appearance']['accessory_runtime']
 require_fields(compact,COMPACT_RUNTIME_FIELDS,'compact accessory runtime')
 for key in ('identity','generation','revision','sample','bone_names','material_conversion'):need(compact[key]==runtime[key],'compact accessory '+key+' mismatch')
 return frame,snapshot,runtime,compact

def point_bounds(points):
 return {'min':[min(p[a] for p in points) for a in range(3)],'max':[max(p[a] for p in points) for a in range(3)]}

def check_record(record,command,receipt):
 frame,snapshot,runtime,compact=protocol(record,command,receipt)
 need([p['name'] for p in snapshot['parts']]==['body','garment'],'unexpected body/garment snapshot parts')
 need(len(runtime['accessories'])==2 and {a['name'] for a in runtime['accessories']}==set(ref.STEMS),'missing/duplicate accessory')
 need(len(compact['accessories'])==2 and {a['name'] for a in compact['accessories']}==set(ref.STEMS),'compact accessory coverage')
 manifest=load(ref.ASSETS/'asset-manifest.json');need(ref.sha(ref.ASSETS/'asset-manifest.json')=='620099486462ed31f5ca0a7e06b351d8fb8a6a59120f85b604d5ea94c3808a59','source manifest changed')
 results={}
 for actual in runtime['accessories']:
  require_observations(actual,False,'full accessory')
  name=actual['name'];e=ref.compute(snapshot,name);obj=e['obj'];count=obj['source_count'];pairs=actual['source_uv_pairs'];n=len(pairs)
  need(all(type(c) is list and len(c)==2 and all(type(i) is int for i in c) for c in pairs),name+' source/UV pair types')
  need(actual['source_vertices']==count and pairs==[list(c) for c in obj['corners']],name+' exact OBJ source/UV-index corner identity mismatch')
  array(actual['rest_model_m'],count,3,name+' rest');array(actual['rest_normals'],count,3,name+' source rest normals')
  array(actual['positions'],n,3,name+' actual upload');array(actual['normals'],n,3,name+' actual normals');array(actual['uv_0'],n,2,name+' actual UV')
  for uv,(_,t) in zip(actual['uv_0'],pairs):need(max(abs(uv[a]-obj['uvs'][t][a]) for a in range(2))<=1e-6,name+' actual UV values differ from source once-V-flip')
  index={tuple(c):i for i,c in enumerate(obj['corners'])};expected_indices=[index[c] for triangle in obj['triangles'] for c in triangle]
  need(all(type(i) is int for i in actual['indices']),name+' index types')
  need(actual['indices']==expected_indices,name+' actual triangle fan/winding/corner indices differ')
  rest_error=ref.err(actual['rest_model_m'],e['rest_positions']);posed_error=ref.err(actual['positions'],[e['positions'][i] for i,t in pairs]);need(max(rest_error,posed_error)<=ref.TOL,name+' actual rest/LBS exceeds existing arithmetic guard')
  weight_error=same_weights(actual['full_normalized_positive_influences'],e['full_joint_influences'],name)
  need(actual['display_transform']==e['display_transform'],name+' actual display transform differs from body')
  need(all(abs(math.sqrt(math.fsum(x*x for x in v))-1)<1e-3 for v in actual['normals']),name+' actual normals zero/nonunit')
  c=next(p for p in compact['accessories'] if p['name']==name)
  require_observations(c,True,name+' compact accessory')
  for k in sorted(COMPACT_ACCESSORY_FIELDS):need(actual[k]==c[k],name+' compact actual field mismatch '+k)
  material=actual['material'];texture={'eyes':'eyes/materials/brown_eye.png','hair':'hair/short04/short04_diffuse.png'}[name];source=manifest['png'][texture]
  need(material['texture']==texture and material['image_width']==source['width'] and material['image_height']==source['height'] and material['format']=='Rgba8UnormSrgb',name+' texture identity/dimensions/format')
  need(material['decoded_rgba_sha256']==source['decoded_sha256'],name+' actual bound image RGBA sha differs from pinned source')
  need(material['base_color']=='LinearRgba(LinearRgba { red: 1.0, green: 1.0, blue: 1.0, alpha: 1.0 })' and material['alpha']=='Mask(0.5)' and material['metallic']==0 and abs(material['roughness']-.7)<1e-6,name+' exported simple material mismatch')
  need(material['double_sided'] is (name=='hair'),name+' actual bound double-sided policy mismatch')
  need(material['cull_mode']==('None' if name=='hair' else 'Some(Back)'),name+' actual bound cull policy mismatch')
  need(material['observation']=='current entity MeshMaterial3d -> Assets<StandardMaterial> -> actual base_color_texture -> Assets<Image> CPU bytes',name+' actual material/image observation route missing')
  need(actual['tangents']=='NOT-EXPORTED; no normal map in simple material',name+' tangent observation scope changed')
  model_bounds=point_bounds(actual['positions']);stage_bounds=point_bounds([ref.point(actual['display_transform'],p) for p in actual['positions']])
  for field,expected in [('posed_model_bounds_m',model_bounds),('posed_stage_bounds_m',stage_bounds)]:
   bounds=actual[field];array([bounds['min'],bounds['max']],2,3,name+' '+field);need(ref.err([bounds['min'],bounds['max']],[expected['min'],expected['max']])<=ref.TOL,name+' '+field+' disagrees with actual arrays/placement')
  need(actual['observation']=='CPU Assets<Mesh> through actual entity handles; NOT GPU readback' and actual['not_saved'] is True,name+' observation scope mismatch')
  results[name]={'source_vertices':count,'render_corners':n,'rest_error_m':rest_error,'actual_upload_LBS_error_m':posed_error,'normalized_positive_weight_L1_max':weight_error,'source_UV_index_identity':'exact source_uv_pairs+actual uv values+actual ordered indices','normal_check':'finite/unit only','tangents':'NOT-EXPORTED','material_observation':'current entity-bound material/cull/double_sided/current-image CPU digest exported and source-checked; not GPU readback','bounds_observation':'actual uploaded model and once-placed stage bounds cross-checked'}
 return {'result':'PASS_WITH_LIMITS','input_provenance':'Caller-supplied capture/command/receipt; collector provenance must be verified externally','binding_scope':'sent command + separately read compact report + frame protocol consistency; same capture producer, NOT independent world freshness oracle','sample_scope':'published full snapshot; live serial=null/stream_frame is rejected','geometry_hash_limit':'equality of producer hashes; no cross-language JSON hash recomputation claimed','accessories':results,'not_run':['GPU readback','independent current-world producer','tangent parity','visual quality']}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--capture',type=Path,required=True);p.add_argument('--command',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 ref.configure(a.repo);freeze=verify_freeze();out=check_record(load(a.capture),load(a.command),load(a.receipt));out['freeze']=freeze;out['inputs']={str(f):ref.sha(f) for f in (a.capture,a.command,a.receipt)};ref.dump(a.output,out);print(json.dumps(out,indent=2))
