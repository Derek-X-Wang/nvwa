"""Three records only: unchanged source validator and unchanged cross-control body."""
import argparse,ast,copy,hashlib,json,sys
from pathlib import Path
from source_root import verify_validator_root,expected_id,require,OUT,VROOT
from server import contract_valid
from collect_transfer import verify_bytes,raw_object
BASELINE_SHA='d79f44812cd6b840bd8d4f15d71b9f4d886ccc05bce062ea5be5232916c6f4d2'
def unchanged_cross_controls(checker,envelopes):
 """Execute original check() group loop verbatim, without claiming its full matrix."""
 source=(Path(checker.__file__)).read_text();tree=ast.parse(source);check=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='check');start=next(i for i,n in enumerate(check.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='groups' for t in n.targets));body=copy.deepcopy(check.body[start:-1]);fn=ast.FunctionDef(name='original_cross_controls',args=ast.arguments(posonlyargs=[],args=[ast.arg(arg='records'),ast.arg(arg='keys')],kwonlyargs=[],kw_defaults=[],defaults=[]),body=body,decorator_list=[]);module=ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[]));ns=dict(checker.__dict__);exec(compile(module,str(checker.__file__)+'::unchanged-group-loop','exec'),ns);keys=[checker.control_key(e) for e in envelopes];require(len(set(keys))==len(keys),'cross-control inputs must be distinct');ns['original_cross_controls'](dict(zip(keys,envelopes)),keys)
def restoration(a,b):
 """Only request correlation and observed stable-update count may differ."""
 aa=copy.deepcopy(a);bb=copy.deepcopy(b)
 for e in (aa,bb):
  del e['report']['request_id'];del e['frame']['request_id'];del e['frame']['stable_updates']
 require(aa==bb,'A restoration/baseline typed content differs outside request_id/stable_updates')
def historical_semantics(e):
 """Declared source projection across page lifetimes; not runtime identity equality."""
 f=copy.deepcopy(e['frame']);base=f['full_base'];base.pop('character_entity');base.pop('generation');base['sample'].pop('serial')
 for part in base['parts']:
  part.pop('display_entity');part.pop('mesh_handle')
 buffers=f['buffers']
 for b in buffers:
  for field in ['entity','material_handle','mesh_handle']:b.pop(field)
  if b['bound_image'] is not None:b['bound_image'].pop('handle')
 candidate=f['candidate']
 for field in ['entity','mesh_handle','material_handle','image_handle','generation','pre_visibility_publication','original_standard_material_debug']:candidate.pop(field)
 candidate['sample'].pop('serial')
 camera=f['camera'];camera.pop('entity')
 diagnostic=f['diagnostic']
 for target in diagnostic['targets']:
  for field in ['entity','material_handle','mesh_handle']:target.pop(field)
  for name in ['production_material','render_material']:
   material=target[name];material.pop('full_standard_material_debug');material['has_base_color_texture']=material.pop('base_color_texture') is not None
 return {'work':json.loads(e['report']['work_json']),'endpoint':f['endpoint'],'fixed_case':f['fixed_case'],'work_sha256':f['work_sha256'],'full_base':base,'buffers':buffers,'candidate':candidate,'camera':camera,'diagnostic':diagnostic,'environment':f['identity']['environment']}
def historical_baseline(original,current):require(historical_semantics(original)==historical_semantics(current),'historical A semantic/source projection differs')
def validate(contract,directory,baseline):
 c=contract_valid(contract);verify_validator_root(VROOT,OUT/'VALIDATOR-ROOT.json');sys.path.insert(0,str(VROOT/'experiments/78-hairline-local-quality'));import check_captures
 from source_binding import strict_json
 rows=[];envelopes=[]
 for s in c['stages']:
  expected_id(s['request_id']);p=directory/s['label'];raw=(p/'capture.json').read_bytes();m=json.loads((p/'manifest.json').read_text());verify_bytes(m,raw,expected_request_id=s['request_id']);e=strict_json(raw.decode());require(e['frame']['candidate']['variant']==s['typed_variant'],'contract variant mismatch');key,error=check_captures.validate(e);require(key==('web','default-arms',0,s['typed_variant'],'Combined','Textured'),'fixed control mismatch');envelopes.append(e);rows.append({'label':s['label'],'request_id':s['request_id'],'sha256':hashlib.sha256(raw).hexdigest(),'key':key,'replay_errors':error})
 # Receipts qualify an interval, never an image by themselves.
 for stage in c['stages']:
  p=directory/stage['label'];m=json.loads((p/'manifest.json').read_text());receipt=json.loads((p/'currentness.json').read_text());window=json.loads((p/'window-close.json').read_text());require(receipt['run_id']==c['run_id'] and receipt['request_id']==stage['request_id'] and receipt['manifest']==m,'currentness receipt identity')
  fences=receipt['fences'];required={'after-prepare','after-exactText','pre-manifest-upload','post-manifest-response','pre-raw-upload','post-raw-response'};require(required.issubset({f['name'] for f in fences}),'six currentness fences absent')
  for f in fences+[window['close']]:require(f['ready'] is True and f['token']==m['token'] and f['exact_report_before_after'] is True and f['exact_frame_before_after'] is True,'currentness receipt fence invalid')
  require(window['request_id']==stage['request_id'] and window['token']==m['token'] and window['open']['request_id']==stage['request_id'] and window['open']['token']==m['token'] and window['open']['name']=='SCREENSHOT-WINDOW-OPEN' and window['close']['name']=='screenshot-close','window identity invalid');require(0<=window['close']['ms']-window['open']['ms']<=90000,'window exceeds bound')
 events=[json.loads(p.read_text()) for p in sorted((directory/'events').glob('*.json'))]
 for stage in c['stages']:
  for name in ['currentness-post-currentness-response','currentness-post-window-close-response','SCREENSHOT-WINDOW-CLOSED']:require(any(e.get('name')==name and e.get('request_id')==stage['request_id'] for e in events),'post-response event absent '+stage['label']+' '+name)
 require(any(e.get('name')=='DONE' and e.get('no_further_commands') is True for e in events) and not any(e.get('name')=='FAILED' for e in events),'successful finite chain absent')
 unchanged_cross_controls(check_captures,envelopes[:2]);unchanged_cross_controls(check_captures,envelopes[1:]);restoration(envelopes[0],envelopes[2]);raw=baseline.read_bytes();require(hashlib.sha256(raw).hexdigest()==BASELINE_SHA,'independently pinned prior actual A baseline differs');original=strict_json(raw.decode());check_captures.validate(original);historical_baseline(original,envelopes[0])
 return {'version':1,'records':rows,'unchanged_single_source_cpu':'PASS','unchanged_cross_controls':'PASS','A1_A2_restoration':'PASS','prior_actual_A_semantic_baseline':'PASS','excluded_metadata':['report.request_id','frame.request_id','frame.stable_updates'],'scope':'bounded source/CPU A/B/A only; full cohort and GPU pixels NOT-SCORED; screenshot interval must be qualified separately; quality HOLD'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--contract',type=Path,required=True);p.add_argument('--records',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 try:result=validate(json.loads(a.contract.read_text()),a.records,a.baseline)
 except Exception as e:result={'result':'FAIL','error':str(e),'scope':'no quality admission'};code=1
 else:code=0
 with a.out.open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result,indent=2));return code
if __name__=='__main__':raise SystemExit(main())
