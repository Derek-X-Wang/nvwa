#!/usr/bin/env python3
"""Compare actual Rust output to root's independent MPFB reference, never fit output."""
import argparse,hashlib,json,math,pathlib,subprocess,time
HERE=pathlib.Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def max_error(a,b):
 assert len(a)==len(b) and a,'different/empty topology'
 assert all(len(p)==len(q)==3 and all(math.isfinite(v) for v in p+q) for p,q in zip(a,b)),'invalid/non-finite comparison coordinate'
 return max(abs(x-y) for p,q in zip(a,b) for x,y in zip(p,q))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--compiled',type=pathlib.Path,required=True);ap.add_argument('--out',type=pathlib.Path,required=True);ap.add_argument('--tolerance',type=float,required=True);a=ap.parse_args();assert math.isfinite(a.tolerance) and a.tolerance>0
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);compiled=a.compiled.resolve();receipt=json.loads((compiled/'compile-receipt.json').read_text());pp=compiled/'compiled-package.json';assert sha(pp)==receipt['package_sha256'];rows=[];start=time.monotonic()
 for case in receipt['cases']:
  rp=pathlib.Path(case['recipe']);reference_path=pathlib.Path(case['reference']);assert sha(reference_path)==case['reference_sha256'],'reference changed since compilation';reference=json.loads(reference_path.read_text());op=out/(case['case_id']+'.result.json');command=[str(HERE/'target/debug/compiled-numeric-probe'),str(pp),str(rp),str(op)];r=subprocess.run(command,capture_output=True,text=True);assert r.returncode==0,(case['case_id'],r.stderr)
  actual=json.loads(op.read_text());body=actual['bodies'][0];pos_error=max_error(body['positions'],reference['positions']);refbones={b['name']:b for b in reference['bones']};assert set(refbones)=={b['id'] for b in body['bones']}
  bone_error=0.
  for bone in body['bones']:
   expected=refbones[bone['id']];assert bone['parent']==expected['parent'];bone_error=max(bone_error,max_error([bone['head'],bone['tail']],[expected['head'],expected['tail']]))
  garment_error=None;garment_ref=reference.get('garment_positions')
  if body['garments'] and garment_ref is not None:
   if isinstance(garment_ref,dict):
    assert set(body['garments'])==set(garment_ref);garment_error=max(max_error(body['garments'][key],garment_ref[key]) for key in garment_ref)
   else:assert len(body['garments'])==1;garment_error=max_error(next(iter(body['garments'].values())),garment_ref)
  if receipt['sample_class']=='makehuman-approved-sample':assert body['garments'] and garment_error is not None,'full sample garment channel missing'
  passed=pos_error<=a.tolerance and bone_error<=a.tolerance and (garment_error is None or garment_error<=a.tolerance)
  rows.append({'case_id':case['case_id'],'status':'passed' if passed else 'failed','recipe':actual['recipe'],'vertices':len(body['positions']),'bones':len(body['bones']),'body_max_abs_error':pos_error,'bone_endpoint_max_abs_error':bone_error,'garment_max_abs_error':garment_error,'reference_sha256':sha(reference_path),'result_sha256':sha(op),'command':command,'exit_code':r.returncode})
 summary={'schema_version':2,'sample_class':receipt['sample_class'],'route_id':'compiled-package','status':'passed' if all(r['status']=='passed' for r in rows) else 'failed','scope':'source-compiled body positions and GameEngine helper-derived joint endpoints; garment only if both candidate+reference present','source_input_manifest_sha256':receipt['source_manifest_sha256'],'package_sha256':receipt['package_sha256'],'package_bytes':receipt['package_bytes'],'coordinate_convention':'root measured Blender mesh-local; raw OBJ conversion .1x,-.1z,.1y','tolerance_max_abs':a.tolerance,'tolerance_defined_before_evaluation':True,'cases':rows,'max_body_abs_error':max(r['body_max_abs_error'] for r in rows),'max_joint_endpoint_abs_error':max(r['bone_endpoint_max_abs_error'] for r in rows),'garment_comparison_executed':all(r['garment_max_abs_error'] is not None for r in rows),'rest_matrix_inverse_bind_comparison_executed':False,'reference_pipeline_executed_by_root':True,'native_graphical_execution_run':False,'web_graphical_execution_run':False,'private_evidence_path':str(out),'duration_seconds':time.monotonic()-start}
 (out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n');print(json.dumps({k:summary[k] for k in ['sample_class','status','max_body_abs_error','max_joint_endpoint_abs_error','garment_comparison_executed','duration_seconds']}));assert summary['status']=='passed'
if __name__=='__main__':main()
