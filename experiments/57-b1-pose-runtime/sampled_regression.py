#!/usr/bin/env python3
"""Real full-weight source execution against the pinned public CI sample (stdlib only).
This sampled gate does not replace the separately measured full40 local gate.
"""
import argparse,hashlib,json,math,os,subprocess,time,copy
from pathlib import Path
from validation import validate_frame
ROOT=Path(__file__).resolve().parent
COMMON='2e8566a4f12de710ead88f6aa2d71fc44e0680761a4f2fdc48a844b6f3534ab7'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,message):
 if not ok:raise ValueError(message)
def finite(rows):return all(math.isfinite(x) for row in rows for x in row)
def mat(v):return [[v[4*j+i] for j in range(4)] for i in range(4)]
def mul(a,b):return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
def converted(m):return [m[0],[-x for x in m[2]],m[1],m[3]]
def error(a,b):return max(abs(x-y) for ra,rb in zip(a,b) for x,y in zip(ra,rb))
def inspect_frame(candidate,reference):
 require(candidate['route_id']=='b1-full-weight-cpu' and candidate['frame_gauge_enabled'] and candidate['actual_candidate_code_executed'] is True and candidate['actual_candidate_skeleton_propagated'] is True,'wrong candidate route/execution')
 require(candidate['common_manifest_sha256']==COMMON and candidate['case_id']==reference['recipe_id'] and candidate['pose_id']==reference['pose_id'],'case identity mismatch')
 refs={b['name']:b for b in reference['bones']};result={}
 for part,tol,count in [('body',1e-3,19158),('garment',3e-3,1797)]:
  entry=candidate['parts'][part];frame=entry['frame'];ids=entry['source_vertex_ids'];vector_validation=validate_frame(frame,len(ids),canonical=True);lookup={sid:i for i,sid in enumerate(ids)}
  require(set(lookup)==set(range(count)),'full candidate source ID coverage mismatch')
  require(all(len(frame[key])==len(ids) and finite(frame[key]) for key in ('positions','rest_positions','normals','tangents')) and len(frame['full_joint_influences'])==len(ids),'invalid frame vectors')
  require(len(frame['bones'])==len(refs)==53 and {b['name'] for b in frame['bones']}==set(refs),'bone coverage mismatch')
  require(all(all(math.isfinite(x) for key in ('rest','posed','inverse_bind','canonical_rest','canonical_posed','frame_gauge') for x in b[key]) for b in frame['bones']),'nonfinite matrix')
  expected=reference[part];maximum=0.;oracle_max=0.
  kernels=[mul(mat(b['posed']),mat(b['inverse_bind'])) for b in frame['bones']]
  for sid,position in zip(expected['source_ids'],expected['positions']):
   i=lookup[sid];p=frame['positions'][i];actual=[p[0],-p[2],p[1]];maximum=max(maximum,max(abs(a-b) for a,b in zip(actual,position)))
   row=frame['full_joint_influences'][i];total=sum(w for _,w in row);require(total>0 and all(0<=j<53 and math.isfinite(w) and w>0 for j,w in row),'invalid full influences');h=frame['rest_positions'][i]+[1.]
   oracle=[sum(w/total*sum(kernels[j][r][k]*h[k] for k in range(4)) for j,w in row) for r in range(3)]
   oracle_max=max(oracle_max,max(abs(a-b) for a,b in zip(p,oracle)))
  rest_error=posed_error=head_error=0.
  require(len(frame['bones'])==len(refs)==53,'bone coverage mismatch')
  for b in frame['bones']:
   ref=refs[b['name']];require(b['parent']==ref['parent'],'bone parent mismatch');rest=converted(mat(b['canonical_rest']));posed=converted(mat(b['canonical_posed']));rest_error=max(rest_error,error(rest,ref['matrix_local']));posed_error=max(posed_error,error(posed,ref['matrix_pose']));head_error=max(head_error,max(abs(posed[i][3]-ref['matrix_pose'][i][3]) for i in range(3)))
  require(maximum<=tol and oracle_max<=1e-5 and rest_error<=1e-4 and posed_error<=1e-4 and head_error<=1e-5,'sampled geometry/matrix/oracle gate failed: '+part)
  result[part]={'sampled_source_ids':len(expected['source_ids']),'full_candidate_source_ids':count,'max_component':maximum,'oracle_max_component':oracle_max,'rest_matrix_max':rest_error,'posed_matrix_max':posed_error,'joint_head_max':head_error,'normals_tangents':vector_validation}
 return result

def negative_controls(candidate,reference):
 inspect_frame(candidate,reference);rows=[]
 for fault in ('tampered-expectation','wrong-bone-order','omitted-deformation','wrong-gauge','missing-bone','nonfinite-matrix','zero-normals','empty-normals','zero-tangents','empty-tangents','zero-gauge','zero-raw-rest','wrong-rest','wrong-inverse-bind','invalid-tangent-handedness'):
  mutated=copy.deepcopy(candidate);expected=copy.deepcopy(reference)
  if fault=='tampered-expectation':expected['body']['positions'][0][0]+=0.01
  for part in ('body','garment'):
   f=mutated['parts'][part]['frame']
   if fault=='wrong-bone-order':f['bones']=f['bones'][1:]+f['bones'][:1]
   elif fault=='omitted-deformation':f['positions']=f['rest_positions']
   elif fault=='wrong-gauge':
    for b in f['bones']:b['canonical_rest']=b['rest'];b['canonical_posed']=b['posed']
   elif fault=='missing-bone':f['bones']=f['bones'][:-1]
   elif fault=='nonfinite-matrix':f['bones'][0]['canonical_rest'][0]=float('nan')
   elif fault=='zero-normals':f['normals'][0]=[0.,0.,0.]
   elif fault=='empty-normals':f['normals']=[]
   elif fault=='zero-tangents':f['tangents'][0]=[0.,0.,0.,1.]
   elif fault=='empty-tangents':f['tangents']=[]
   elif fault=='zero-gauge':f['bones'][0]['frame_gauge']=[0.]*16
   elif fault=='zero-raw-rest':f['bones'][0]['rest']=[0.]*16
   elif fault=='wrong-rest':f['bones'][0]['rest'][12]+=0.01
   elif fault=='wrong-inverse-bind':f['bones'][0]['inverse_bind'][12]+=0.01
   elif fault=='invalid-tangent-handedness':f['tangents'][0][3]=0.
  try:inspect_frame(mutated,expected)
  except (ValueError,KeyError,IndexError,TypeError) as error:rows.append({'fault':fault,'rejected':True,'error':str(error)})
  else:raise AssertionError('sampled comparator missed '+fault)
 inspect_frame(candidate,reference);return {'scope':'captured actual executable output and tampered expectation through exact CI comparator; no compiled mutant claim','mutations':rows,'restored_passed':True}

def main():
 p=argparse.ArgumentParser();p.add_argument('--ci-inputs',type=Path,required=True);p.add_argument('--binary',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();require(not a.out.exists(),'output already exists')
 manifest_path=ROOT.parent/'59-b1-ci-inputs/manifest.json';require(sha(manifest_path)=='925688915e0ff918ba9c373c3aba39a5dbc1d4b93cabb65a3b51398fdfab3bcb','CI manifest mismatch');manifest=json.loads(manifest_path.read_text())
 for entry in manifest['files']:
  path=a.ci_inputs/entry['path'];require(path.is_file() and not path.is_symlink() and sha(path)==entry['sha256'],'CI seed identity mismatch: '+entry['path'])
 reference_path=a.ci_inputs/'regression/reference.json';reference=json.loads(reference_path.read_text());a.out.mkdir(parents=True);byrecipe={c['recipe_id']:c for c in reference['cases']};binary=a.binary.resolve();poses=ROOT.parent/'56-b1-pose-reference/poses.json';results=[];commands=[];control_pair=None;start=time.monotonic();env=os.environ.copy();env['B1_FULL_WEIGHTS']='1'
 for recipe_id,case in sorted(byrecipe.items()):
  recipe=case['recipe'];weights={}
  for param,stem in [('torso_length','torso-scale-vert'),('jaw_drop','chin-jaw-drop')]:
   for sign in ('decr','incr'):weights[stem+'-'+sign]=max(0.,-recipe[param] if sign=='decr' else recipe[param])
  config={'case_id':recipe_id,'asset_root':str((a.ci_inputs/'sample').resolve()),'base':'base.obj','vertex_groups':'vertex_groups.json','composite':'composite.json','macros':'empty.macro','targets':'targets','rig':'rig.game_engine.json','weights':'weights.game_engine.json','body':'body.mhclo','garment':'garment/female_sportsuit01.mhclo','target_weights':weights,'common_manifest_sha256':COMMON,'candidate_to_raw_scale':10.}
  config_path=a.out/(recipe_id+'-config.json');config_path.write_text(json.dumps(config));output=a.out/recipe_id;command=[str(binary),str(config_path),str(poses),str(output)];log=a.out/(recipe_id+'.log')
  with log.open('x') as stream:r=subprocess.run(command,env=env,stdout=stream,stderr=subprocess.STDOUT)
  commands.append({'command':command,'exit_code':r.returncode,'B1_FULL_WEIGHTS':'1','config_sha256':sha(config_path),'log_sha256':sha(log)});require(r.returncode==0,'actual candidate execution failed')
  for expected in [c for c in reference['cases'] if c['recipe_id']==recipe_id]:
   candidate_path=output/(expected['pose_id']+'.json');candidate=json.loads(candidate_path.read_text());results.append({'case_id':expected['case_id'],'output_sha256':sha(candidate_path),'measures':inspect_frame(candidate,expected)})
   if expected['case_id']=='body-positive__combined':control_pair=(candidate,expected)
 require(len(results)==40 and control_pair is not None,'incomplete sampled regression');controls=negative_controls(*control_pair);result={'status':'sampled_regression_pass','full40_acceptance_replacement':False,'cases':results,'commands':commands,'mutation_controls':controls,'script_sha256':sha(Path(__file__)),'validator_sha256':sha(ROOT/'validation.py'),'binary_sha256':sha(binary),'reference_sha256':sha(reference_path),'duration_seconds':time.monotonic()-start};(a.out/'sampled-regression.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'cases':len(results),'duration_seconds':result['duration_seconds']}))
if __name__=='__main__':main()
