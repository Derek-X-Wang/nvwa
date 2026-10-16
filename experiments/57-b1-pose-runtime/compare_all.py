#!/usr/bin/env python3
import argparse,json
from pathlib import Path
from compare import compare,sha,COMMON,POSES
from validation import require
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent.parent
MANIFEST_SHA='98ffb4b7947101bdd2107055beed866d7f040b33f699fb859c090c4c03242636'
def main():
 p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 manifest=ROOT.parent/'56-b1-pose-reference/reference/frozen/manifest.json';require(sha(manifest)==MANIFEST_SHA,'reference manifest mismatch')
 frozen=json.loads(manifest.read_text());execution=json.loads((a.results/'summary.json').read_text());require(execution['status']=='actual_candidate_executed' and execution['common_sha256']==COMMON and execution['poses_sha256']==POSES,'execution identity mismatch')
 runs={c['recipe_id']:c for c in execution['cases']};cases=[]
 for entry in frozen['cases']:
  ref=REPO/entry['path'];require(sha(ref)==entry['sha256'],'reference case mismatch');candidate=a.results/entry['recipe_id']/(entry['pose_id']+'.json');require(sha(candidate)==runs[entry['recipe_id']]['outputs'][candidate.name],'candidate case mismatch')
  c=json.loads(candidate.read_text());r=json.loads(ref.read_text());measures=compare(c,r)
  case={'case_id':entry['case_id'],'candidate_sha256':sha(candidate),'reference_sha256':sha(ref),'measures':measures};cases.append(case)
  print(entry['case_id'],{name:round(m['full_mpfb_geometry']['max_component'],8) for name,m in measures.items()},flush=True)
 keys=('candidate_weight_oracle','rest_matrix','posed_matrix','joint_heads','full_mpfb_geometry','normals_tangents')
 gates={part:{key:{'passed_cases':sum(c['measures'][part][key]['passed'] for c in cases),'total_cases':len(cases),'max_component':max(c['measures'][part][key].get('max_component',c['measures'][part][key].get('max_frame_identity_error',0.)) for c in cases)} for key in keys} for part in ('body','garment')}
 result={'schema_version':1,'status':'PASS' if all(v['passed_cases']==40 for g in gates.values() for v in g.values()) else 'HOLD','reference_manifest_sha256':sha(manifest),'execution_summary_sha256':sha(a.results/'summary.json'),'comparator_sha256':sha(ROOT/'compare.py'),'aggregate_sha256':sha(Path(__file__)),'validator_sha256':sha(ROOT/'validation.py'),'gates':gates,'cases':cases,'appearance_acceptance':'NOT-RUN','product_admission':False}
 a.out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(gates));return 0 if result['status']=='PASS' else 3
if __name__=='__main__':raise SystemExit(main())
