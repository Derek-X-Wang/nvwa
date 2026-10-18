"""Standalone artificial envelope pipeline controls. NEVER runtime acceptance."""
import argparse, copy, json
from pathlib import Path
import check_capture as a
import source_reference as r
parser=argparse.ArgumentParser();parser.add_argument('--repo',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True);args=parser.parse_args()
work=args.output_dir.resolve();r.need(not work.exists(),'test output directory must be new');work.mkdir(parents=True);r.configure(args.repo)
# Fully artificial core snapshot. No retained raw captures, Blender or runtime needed.
identity=[1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.]
display=identity.copy();display[12:15]=[.25,1.5,-.5]
weights=json.loads((r.REPO/'assets/characters/mpfb-b1-v1/weights.game_engine.json').read_bytes())['weights']
command={'request_id':'ARTIFICIAL-pipeline-only','action':'sample','clip_id':'b1_arm_rehearsal_v1','seconds':2.,'torso_length':0.,'jaw_drop':0.}
body={'name':'body','source_ids':list(range(19158)),'rest_positions':[[i%137*.0001,(i//137)%137*.0001,i*.00001] for i in range(19158)],'display_entity':'ARTIFICIAL-body','mesh_handle':'ARTIFICIAL-body-mesh','display_transform':display,'model_to_world':identity}
s={'schema_version':1,'asset_id':'mpfb-hm08-game-engine-female-sportsuit01-v1','profile_id':'nvwa-mpfb-b1-motion-v1','generation':1,'revision':1,'character_entity':'ARTIFICIAL-character','parameters':{'torso_length':0.,'jaw_drop':0.},'sample':{'serial':1,'clip_id':'b1_arm_rehearsal_v1','timeline_id':'probe-entry','position_seconds':2.,'source_seconds':2.,'playing':False,'completed':False},'parts':[body,{'name':'garment'}],'bones':[{'name':name,'skin':identity.copy()} for name in weights]}
raw={'request':command,'snapshot':s};manifest=json.loads((r.ASSETS/'asset-manifest.json').read_bytes())
runtime={'identity':{'generation':s['generation'],'revision':s['revision'],'character':s['character_entity'],'body':body['mesh_handle'],'parameters':s['parameters']},'generation':s['generation'],'revision':s['revision'],'sample':s['sample'],'bone_names':[b['name'] for b in s['bones']],'actual_skin_matrices':s['bones'],'accessories':[],'material_conversion':'simple diffuse sRGB ×white; cutout Mask(0.5); no legacyshader parity'}
for name in r.STEMS:
 e=r.compute(s,name);obj=e['obj'];pairs=[list(c) for c in obj['corners']];index={tuple(c):i for i,c in enumerate(obj['corners'])};texture={'eyes':'eyes/materials/brown_eye.png','hair':'hair/short04/short04_diffuse.png'}[name];image=manifest['png'][texture]
 runtime['accessories'].append({'name':name,'entity':'fixture-'+name,'mesh_handle':'fixture-mesh-'+name,'source_vertices':obj['source_count'],'source_uv_pairs':pairs,'rest_model_m':e['rest_positions'],'rest_normals':[[0.,1.,0.] for _ in e['rest_positions']],'full_normalized_positive_influences':e['full_joint_influences'],'axis_scales':e['scales'],'positions':[e['positions'][v] for v,t in pairs],'normals':[[0.,1.,0.] for v,t in pairs],'uv_0':[obj['uvs'][t] for v,t in pairs],'indices':[index[c] for tri in obj['triangles'] for c in tri],'display_transform':e['display_transform'],'model_to_world_record_only':body['model_to_world'],'material':{'handle':'fixture-material-'+name,'base_color':'LinearRgba(LinearRgba { red: 1.0, green: 1.0, blue: 1.0, alpha: 1.0 })','roughness':.7,'metallic':0.,'alpha':'Mask(0.5)','double_sided':name=='hair','cull_mode':'None' if name=='hair' else 'Some(Back)','observation':'current entity MeshMaterial3d -> Assets<StandardMaterial> -> actual base_color_texture -> Assets<Image> CPU bytes','texture':texture,'image_handle':'fixture-image-'+name,'image_width':image['width'],'image_height':image['height'],'format':'Rgba8UnormSrgb','decoded_rgba_sha256':image['decoded_sha256']},'actual_cpu_upload_sha256':'f'*64,'observation':'CPU Assets<Mesh> through actual entity handles; NOT GPU readback','not_saved':True})
for item in runtime['accessories']:
 item['tangents']='NOT-EXPORTED; no normal map in simple material'
 item['posed_model_bounds_m']=a.point_bounds(item['positions'])
 item['posed_stage_bounds_m']=a.point_bounds([r.point(item['display_transform'],p) for p in item['positions']])
compact=copy.deepcopy(runtime)
compact.pop('actual_skin_matrices')
for item in compact['accessories']:
 for key in ('rest_model_m','rest_normals','full_normalized_positive_influences','positions','normals','uv_0','indices','source_uv_pairs'):item.pop(key)
report={'phase':'captured','request':command,'desired':'skin+eyes+hair','applied':'skin+eyes+hair','identity':{'revision':s['revision'],'parameters':s['parameters'],'runtime_ready':True,'runtime_error':None,'display_mesh_bindings':[[body['display_entity'],body['mesh_handle'],True]]},'requested_published_generation':s['generation'],'applied_generation':s['generation'],'sample':s['sample'],'parameters':s['parameters'],'geometry_before_sha256':'f'*64,'geometry_after_sha256':'f'*64,'geometry_equal':True,'appearance':{'state':'skin','accessory_runtime':compact}}
frame={'request':command,'snapshot':s,'geometry_before_sha256':'f'*64,'geometry_after_sha256':'f'*64,'geometry_equal':True,'appearance':{'state':'skin','accessory_runtime':runtime}}
record={'request':command,'report':report,'frame':frame};receipt=copy.deepcopy(report)
freeze=a.verify_freeze();valid=a.check_record(record,command,receipt);observations=[]
def rejects(label,mutate):
 trial=json.loads(json.dumps(record));ack=json.loads(json.dumps(receipt));mutate(trial,ack)
 try:a.check_record(trial,command,ack)
 except (ValueError,KeyError,TypeError,IndexError) as e:observations.append({'mutation':label,'rejected':str(e)});return
 raise RuntimeError('mutation passed '+label)
def rt(d):return d['frame']['appearance']['accessory_runtime']
def hair(d):return next(p for p in rt(d)['accessories'] if p['name']=='hair')
rejects('wrong separately read request receipt',lambda d,ack:ack['request'].__setitem__('request_id','wrong-receipt'))
rejects('stale/null published sample serial',lambda d,ack:d['frame']['snapshot']['sample'].__setitem__('serial',None))
rejects('live stream sample masquerades as published snapshot',lambda d,ack:d['frame']['snapshot']['sample'].__setitem__('stream_frame',9))
rejects('old accessory generation',lambda d,ack:rt(d).__setitem__('generation',-1))
rejects('old accessory revision',lambda d,ack:rt(d).__setitem__('revision',-1))
rejects('old accessory character entity',lambda d,ack:rt(d)['identity'].__setitem__('character','old entity'))
rejects('old body mesh handle',lambda d,ack:rt(d)['identity'].__setitem__('body','old mesh'))
rejects('different accessory bone frame',lambda d,ack:rt(d).__setitem__('actual_skin_matrices',[]))
rejects('absent actual upload positions (no offline substitution)',lambda d,ack:hair(d).pop('positions'))
rejects('actual upload position corrupted',lambda d,ack:hair(d)['positions'][0].__setitem__(0,99))
rejects('source UV-index identity forged',lambda d,ack:hair(d)['source_uv_pairs'][0].__setitem__(1,999))
rejects('actual UV double V-flip',lambda d,ack:hair(d).__setitem__('uv_0',[[u,1-v] for u,v in hair(d)['uv_0']]))
rejects('actual triangle winding changed',lambda d,ack:hair(d)['indices'].__setitem__(slice(0,3),list(reversed(hair(d)['indices'][:3]))))
rejects('actual five-influence source82 truncated',lambda d,ack:hair(d)['full_normalized_positive_influences'].__setitem__(82,sorted(hair(d)['full_normalized_positive_influences'][82],key=lambda x:-x[1])[:4]))
rejects('actual normals zero',lambda d,ack:hair(d)['normals'].__setitem__(0,[0.,0.,0.]))
rejects('wrong cached declared decoded texture SHA',lambda d,ack:hair(d)['material'].__setitem__('decoded_rgba_sha256','0'*64))
def change_material_everywhere(d,ack,key,value):
 for container in (rt(d),d['report']['appearance']['accessory_runtime'],ack['appearance']['accessory_runtime']):
  next(x for x in container['accessories'] if x['name']=='hair')['material'][key]=value
rejects('current hair material cull Back (all protocol copies agree)',lambda d,ack:change_material_everywhere(d,ack,'cull_mode','Some(Back)'))
rejects('current hair material double_sided false (all protocol copies agree)',lambda d,ack:change_material_everywhere(d,ack,'double_sided',False))
rejects('current bound image changed SHA (all protocol copies agree)',lambda d,ack:change_material_everywhere(d,ack,'decoded_rgba_sha256','0'*64))
rejects('cached r2 white literal replacing actual Debug field',lambda d,ack:change_material_everywhere(d,ack,'base_color','white'))
rejects('current material observer route absent',lambda d,ack:change_material_everywhere(d,ack,'observation','intended policy only'))
def mode_mismatch(d,ack):
 d['report']['desired']='skin';ack['desired']='skin'
rejects('mode desired/applied mismatch (both reports agree)',mode_mismatch)
def change_accessory_everywhere(d,ack,key,value):
 for container in (rt(d),d['report']['appearance']['accessory_runtime'],ack['appearance']['accessory_runtime']):
  next(x for x in container['accessories'] if x['name']=='hair')[key]=copy.deepcopy(value)
rejects('actual source model bounds corrupted',lambda d,ack:change_accessory_everywhere(d,ack,'posed_model_bounds_m',{'min':[0.,0.,0.],'max':[99.,99.,99.]}))
rejects('actual placed stage bounds corrupted',lambda d,ack:change_accessory_everywhere(d,ack,'posed_stage_bounds_m',{'min':[-99.,-99.,-99.],'max':[0.,0.,0.]}))
rejects('tangents invented as observed',lambda d,ack:change_accessory_everywhere(d,ack,'tangents',[]))
# Coherent missing/malformed observations reach the actual parser with independently
# serialized JSON copies, not shared-object aliases or mismatched receipts.
def all_hair_copies(d,ack):
 return [next(row for row in container['accessories'] if row['name']=='hair') for container in (rt(d),d['report']['appearance']['accessory_runtime'],ack['appearance']['accessory_runtime'])]
def drop_observation(d,ack,key,nested=False):
 for row in all_hair_copies(d,ack):
  (row['material'] if nested else row).pop(key)
def replace_observation(d,ack,key,value,nested=False):
 for row in all_hair_copies(d,ack):
  (row['material'] if nested else row)[key]=copy.deepcopy(value)
def only_names(d,ack):
 for report in (d['report'],ack):report['appearance']['accessory_runtime']['accessories']=[{'name':'eyes'},{'name':'hair'}]
rejects('name-only compact records in both reports',only_names)
for key in ('actual_cpu_upload_sha256','entity','mesh_handle','axis_scales','model_to_world_record_only'):
 rejects('coherent missing full/compact '+key,lambda d,ack,k=key:drop_observation(d,ack,k))
for key in ('handle','image_handle'):
 rejects('coherent missing nested material '+key,lambda d,ack,k=key:drop_observation(d,ack,k,True))
for value in ('not-a-sha','A'*64,'f'*63,None,123):
 rejects('coherent malformed upload hash '+repr(value),lambda d,ack,v=value:replace_observation(d,ack,'actual_cpu_upload_sha256',v))
for key in ('entity','mesh_handle'):
 rejects('coherent empty identity '+key,lambda d,ack,k=key:replace_observation(d,ack,k,' '))
for key in ('handle','image_handle'):
 rejects('coherent empty material identity '+key,lambda d,ack,k=key:replace_observation(d,ack,k,'',True))
def mismatch_hash(d,ack):
 for report in (d['report'],ack):next(row for row in report['appearance']['accessory_runtime']['accessories'] if row['name']=='hair')['actual_cpu_upload_sha256']='a'*64
rejects('valid lowerhex compact hash differs from full',mismatch_hash)
def extra_compact_field(d,ack):
 for report in (d['report'],ack):next(row for row in report['appearance']['accessory_runtime']['accessories'] if row['name']=='hair')['unexpected_observer']=True
rejects('unknown compact r4 field in both reports',extra_compact_field)
# Coherently stale whole bundle passes protocol checks: this is the explicit non-oracle limit.
coherent=copy.deepcopy(record);ack=copy.deepcopy(receipt);coherent['frame']['snapshot']['generation']+=100;newgen=coherent['frame']['snapshot']['generation'];rt(coherent)['generation']=newgen;rt(coherent)['identity']['generation']=newgen
for report_like in (coherent['report'],ack):
 report_like['requested_published_generation']=newgen;report_like['applied_generation']=newgen;report_like['appearance']['accessory_runtime']['generation']=newgen;report_like['appearance']['accessory_runtime']['identity']['generation']=newgen
coherent_pass=a.check_record(coherent,command,ack)['result']
output={'scope':'ARTIFICIAL standalone synthetic cage/frame; source-grounded fake attachments only; actual runtime NOT-RUN','source_freeze':freeze,'valid_fixture':valid,'negative_controls':observations,'coherent_bundle_limitation':{'whole_bundle_generation_changed_and_protocol_still_passes':coherent_pass,'meaning':'same-producer consistent bundle cannot establish independently current world freshness; no independent binding fabricated'}}
import ast,hashlib,shutil,subprocess,sys
here=Path(__file__).resolve().parent;proof=json.loads((here/'equivalence.json').read_bytes())
def function_hashes(path):
 return {n.name:hashlib.sha256(ast.dump(n,include_attributes=False).encode()).hexdigest() for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef)}
for filename,key in [('source_reference.py','reference_function_AST_sha256'),('check_capture.py','checker_function_AST_sha256')]:
 actual=function_hashes(here/filename)
 for name,expected in proof[key].items():r.need(actual[name]==expected,'AST baseline differs '+filename+' '+name)
for filename in ('source_reference.py','check_capture.py','test_candidate.py'):
 text=(here/filename).read_text();r.need(('/'+'Users'+'/') not in text,'private root embedded '+filename)
# Independent relocated source fixture: ONLY public pinned files/assets/weights, no captures.
original_repo=r.REPO;relocated=work/'relocated repo';relocated.mkdir()
files=set(a.load(a.FREEZE))|{'experiments/62-b1-appearance-preview/assets/asset-manifest.json','assets/characters/mpfb-b1-v1/weights.game_engine.json'}
files|={'experiments/62-b1-appearance-preview/assets/'+name for name in manifest['outputs']}
for relative in files:
 destination=relocated/relative;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(original_repo/relative,destination)
r.configure(relocated);relocation=a.verify_freeze();r.need(a.check_record(record,command,receipt)==valid,'relocated projection differs')
relative='experiments/64-b1-accessory-preview/src/bin/studio.rs';target=relocated/relative;backup=target.read_bytes();target.rename(target.with_suffix('.missing'))
try:
 try:a.verify_freeze();raise RuntimeError('missing source accepted')
 except FileNotFoundError:missing_rejected=True
finally:target.with_suffix('.missing').rename(target)
target.write_bytes(backup+b'\n')
try:
 try:a.verify_freeze();raise RuntimeError('source byte drift accepted')
 except ValueError as ex:drift_rejected=str(ex)
finally:target.write_bytes(backup)
# Run the real CLI on explicitly ARTIFICIAL files. Result is pipeline proof only.
for name,value in [('ARTIFICIAL-capture.json',record),('ARTIFICIAL-command.json',command),('ARTIFICIAL-report.json',receipt)]:r.dump(work/name,value)
cli_result=work/'ARTIFICIAL-cli-result.json'
proc=subprocess.run([sys.executable,'-S',str(here/'check_capture.py'),'--repo',str(relocated),'--capture',str(work/'ARTIFICIAL-capture.json'),'--command',str(work/'ARTIFICIAL-command.json'),'--receipt',str(work/'ARTIFICIAL-report.json'),'--output',str(cli_result)],capture_output=True,text=True)
r.need(proc.returncode==0,'artificial CLI failed '+proc.stderr[-1000:]);r.need(a.load(cli_result)['result']=='PASS_WITH_LIMITS','unexpected artificial CLI result')
cli_rejections=[]
for label,mutator,expected_error in [('name-only',only_names,'frozen field set differs'),('bad-upload-hash',lambda d,ack:replace_observation(d,ack,'actual_cpu_upload_sha256','not-a-sha'),'malformed actual CPU upload sha256')]:
 malformed=json.loads(json.dumps(record));current=json.loads(json.dumps(receipt));mutator(malformed,current)
 bad_capture=work/('ARTIFICIAL-'+label+'-capture.json');bad_receipt=work/('ARTIFICIAL-'+label+'-report.json');bad_output=work/('ARTIFICIAL-'+label+'-result.json')
 r.dump(bad_capture,malformed);r.dump(bad_receipt,current)
 bad=subprocess.run([sys.executable,'-S',str(here/'check_capture.py'),'--repo',str(relocated),'--capture',str(bad_capture),'--command',str(work/'ARTIFICIAL-command.json'),'--receipt',str(bad_receipt),'--output',str(bad_output)],capture_output=True,text=True)
 r.need(bad.returncode!=0 and not bad_output.exists() and expected_error in bad.stderr,'malformed public CLI did not reject at intended parser boundary '+label)
 cli_rejections.append({'case':label,'nonzero_exit':True,'success_output_absent':True,'expected_error':expected_error})
output['public_CLI_coherent_rejections']=cli_rejections
output.update({'AST_equivalence':'10 numerical helpers unchanged; initial strict6 unchanged at extraction, then protocol/check_record intentionally hardened plus2field validators; current parser baselines recorded','relocated_repo_gate':'PASS; only frozen public files/assets/weights, no retained captures','missing_frozen_file_rejected':missing_rejected,'source_hash_drift_rejected':drift_rejected,'artificial_full_CLI':'PASS_WITH_LIMITS; pipeline only','runtime':'NOT-RUN'})
r.dump(work/'test-results.json',output);print(json.dumps(output,indent=2))
