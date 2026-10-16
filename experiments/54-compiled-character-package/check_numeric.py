#!/usr/bin/env python3
"""Handwritten numeric controls only. Never a MakeHuman reference or sample."""
import argparse,copy,hashlib,json,pathlib,subprocess
HERE=pathlib.Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def write(p,j):p.write_text(json.dumps(j,indent=2,allow_nan=False)+'\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=pathlib.Path,required=True);a=ap.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 manifest=out/'control-manifest.json';write(manifest,{'sample_class':'handwritten-numeric-control','source':'three handwritten vertices; no third-party asset'})
 p={'schema_version':2,'sample_class':'handwritten-numeric-control','source_manifest_path':str(manifest),'source_manifest_sha256':sha(manifest.read_bytes()),'source_package_revision':'handwritten-control-v1','compiler_provenance':{'status':'handwritten-control-only'},'coordinate_convention':'handwritten-coordinate-space','transform_identity':{'matrix':'identity'},'bodies':[{'topology_id':'tiny-control','node':'control-node','mesh':'control-mesh','primitive':'control-primitive','positions':[[0,0,0],[2,0,0],[0,2,2]],'signed_pairs':[{'parameter_id':'control','negative':[{'vertex':1,'delta':[-1,0,0]}],'positive':[{'vertex':1,'delta':[2,0,0]}]}],'helper_rules':[{'id':'head','vertices':[0]},{'id':'tail','vertices':[1,2]}],'bone_rules':[{'id':'bone','parent':None,'head':'head','tail':'tail','roll':0}],'garment_rules':[{'id':'control-garment','scales':[{'vertices':[0,1],'axis':0,'denominator':2},{'vertices':[0,2],'axis':1,'denominator':2},{'vertices':[0,2],'axis':2,'denominator':2}],'vertices':[{'vertices':[0,1,2],'weights':[.25,.5,.25],'offset':[1,2,3]}]}]}]}
 pp=out/'package.json';write(pp,p);binary=HERE/'target/debug/compiled-numeric-probe';cases=[]
 def recipe(v,package=pp):return {'schema_version':2,'case_id':f'handwritten-{v}','package_sha256':sha(package.read_bytes()),'source_manifest_sha256':p['source_manifest_sha256'],'values':{'control':v}}
 def run(package,rp,op):return subprocess.run([str(binary),str(package),str(rp),str(op)],capture_output=True,text=True)
 for v in [-1,-.5,-.25,0,.25,.5,1]:
  rp=out/f'{v}.recipe.json';op=out/f'{v}.result.json';write(rp,recipe(v));r=run(pp,rp,op);assert r.returncode==0,r.stderr
  got=json.loads(op.read_text())['bodies'][0];x=2+(2*v if v>=0 else v)
  assert got['positions']==[[0,0,0],[x,0,0],[0,2,2]]
  assert got['helper_points']['tail']==[x/2,1,1]
  assert got['bones'][0]['tail']==[x/2,1,1]
  assert got['garments']['control-garment']==[[x,2.5,3.5]]
  cases.append({'case_id':f'handwritten-{v}','status':'passed','result_sha256':sha(op.read_bytes())})
 failures=[]
 for name,mutate in [
  ('unselected-branch-invalid-index',lambda p:p['bodies'][0]['signed_pairs'][0]['negative'][0].update(vertex=3)),
  ('invalid-helper-index',lambda p:p['bodies'][0]['helper_rules'][0].update(vertices=[3])),
  ('zero-garment-denominator',lambda p:p['bodies'][0]['garment_rules'][0]['scales'][0].update(denominator=0)),
  ('unknown-bone-parent',lambda p:p['bodies'][0]['bone_rules'][0].update(parent='absent')),
  ('duplicate-node-primitive',lambda p:p['bodies'].append(copy.deepcopy(p['bodies'][0]))),
 ]:
  bad=copy.deepcopy(p);mutate(bad);bp=out/'invalid.package.json';write(bp,bad);rp=out/'invalid.recipe.json';write(rp,recipe(.5,bp));op=out/'failure.json';r=run(bp,rp,op);assert r.returncode==2 and not op.exists(),(name,r.stdout,r.stderr)
  op.write_bytes(b'PRESERVE\n');r=run(bp,rp,op);assert r.returncode==2 and op.read_bytes()==b'PRESERVE\n';op.unlink();failures.append({'case_id':name,'status':'passed-rejection-control','diagnostic':json.loads(r.stderr)})
 rp=out/'0.recipe.json';existing=out/'existing-output.json';existing.write_bytes(b'KEEP\n');r=run(pp,rp,existing);assert r.returncode==2 and existing.read_bytes()==b'KEEP\n';failures.append({'case_id':'valid-existing-output','status':'passed-rejection-control'})
 summary={'sample_class':'handwritten-numeric-control','status':'passed','cases':cases,'failure_controls':failures,'actual_makehuman_data_run':False,'reference_pipeline_run':False,'private_evidence_path':str(out)};write(out/'summary.json',summary)
 print(json.dumps({'sample_class':'handwritten-numeric-control','cases':len(cases),'failure_controls':len(failures),'summary':str(out/'summary.json')}))
if __name__=='__main__':main()
