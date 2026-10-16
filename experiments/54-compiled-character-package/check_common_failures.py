#!/usr/bin/env python3
"""Exercise the actual compiled package CLI with corrupted copies of real inputs."""
import argparse,copy,hashlib,json,pathlib,subprocess,tempfile
HERE=pathlib.Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,j):p.write_text(json.dumps(j,separators=(',',':'),allow_nan=False)+'\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--compiled',type=pathlib.Path,required=True);ap.add_argument('--out',type=pathlib.Path,required=True);a=ap.parse_args();compiled=a.compiled.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 pp=compiled/'compiled-package.json';p=json.loads(pp.read_text());receipt=json.loads((compiled/'compile-receipt.json').read_text());rp=pathlib.Path(receipt['cases'][0]['recipe']);r=json.loads(rp.read_text());before={x:sha(x) for x in [pp,rp,pathlib.Path(p['source_manifest_path'])]};results=[]
 with tempfile.TemporaryDirectory(prefix='common-failure-',dir=out) as td:
  td=pathlib.Path(td)
  controls=[
   ('recipe-package-hash',None,lambda r:r.update(package_sha256='0'*64),'recipe package/manifest identity mismatch'),
   ('recipe-common-manifest-hash',None,lambda r:r.update(source_manifest_sha256='0'*64),'recipe package/manifest identity mismatch'),
   ('out-of-domain-real-parameter',None,lambda r:r['values'].update(torso_length=1.1),'out-of-domain'),
   ('unselected-negative-real-target-index',lambda p:p['bodies'][0]['signed_pairs'][0]['negative'][0].update(vertex=19158),None,'invalid/duplicate sparse'),
   ('real-joint-helper-index',lambda p:p['bodies'][0]['helper_rules'][0].update(vertices=[19158]),None,'helper vertex outside'),
   ('compiled-bone-unknown-parent',lambda p:p['bodies'][0]['bone_rules'][0].update(parent='unknown'),None,'invalid bone parent'),
  ]
  if p['bodies'][0]['garment_rules']:
   controls += [('real-garment-proxy-index',lambda p:p['bodies'][0]['garment_rules'][0]['vertices'][0].update(vertices=[19158,0,0]),None,'garment vertex outside'),('real-garment-zero-scale',lambda p:p['bodies'][0]['garment_rules'][0]['scales'][0].update(denominator=0),None,'invalid garment scale')]
  for name,change_p,change_r,expected in controls:
   package=copy.deepcopy(p);recipe=copy.deepcopy(r)
   if change_p:change_p(package)
   bp=td/'package.json';put(bp,package);recipe['package_sha256']=sha(bp)
   if change_r:change_r(recipe)
   br=td/'recipe.json';put(br,recipe);op=td/'result.json';command=[str(HERE/'target/debug/compiled-numeric-probe'),str(bp),str(br),str(op)]
   run=subprocess.run(command,capture_output=True,text=True);assert run.returncode==2 and not op.exists() and expected in run.stderr,(name,run.stderr)
   op.write_bytes(b'PRESERVE-REAL-PACKAGE-CONTROL\n');rerun=subprocess.run(command,capture_output=True,text=True);assert rerun.returncode==2 and op.read_bytes()==b'PRESERVE-REAL-PACKAGE-CONTROL\n';op.unlink()
   results.append({'case_id':name,'status':'passed-rejection-control','exit_code':2,'diagnostic':json.loads(run.stderr),'absent_output_preserved':True,'existing_output_preserved':True})
 assert all(sha(x)==h for x,h in before.items())
 summary={'sample_class':p['sample_class'],'source_input_manifest_sha256':p['source_manifest_sha256'],'package_sha256':sha(pp),'status':'passed','failure_controls':results,'original_inputs_preserved':True};put(out/'summary.json',summary);print(json.dumps({'status':'passed','failure_controls':len(results),'summary':str(out/'summary.json')}))
if __name__=='__main__':main()
