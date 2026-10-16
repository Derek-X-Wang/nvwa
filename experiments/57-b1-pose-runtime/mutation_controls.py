#!/usr/bin/env python3
"""Fault injection on captured actual output through the unmodified comparator.
No claim that a separately compiled mutant or GPU kernel executed.
"""
import copy,json
from pathlib import Path
from compare import compare,sha
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent.parent

def main():
 candidate_path=ROOT/'results/padding-fixed1/neutral/combined.json';reference_path=REPO/'.work/b1-pose-reference/run1/neutral__combined.json'
 freeze=json.loads((ROOT.parent/'56-b1-pose-reference/reference/frozen/manifest.json').read_text());ref=next(c for c in freeze['cases'] if c['case_id']=='neutral__combined');assert sha(reference_path)==ref['sha256']
 candidate=json.loads(candidate_path.read_text());reference=json.loads(reference_path.read_text());baseline=compare(candidate,reference);assert all(m['candidate_weight_oracle']['passed'] for m in baseline.values())
 rows=[]
 for fault in ('wrong-bone-order','omitted-deformation'):
  mutant=copy.deepcopy(candidate)
  for part in ('body','garment'):
   frame=mutant['parts'][part]['frame']
   if fault=='wrong-bone-order':frame['bones']=frame['bones'][1:]+frame['bones'][:1]
   else:frame['positions']=frame['rest_positions']
  measured=compare(mutant,reference);assert all(not m['candidate_weight_oracle']['passed'] for m in measured.values())
  rows.append({'fault':fault,'mutant_oracle':{part:m['candidate_weight_oracle'] for part,m in measured.items()},'baseline_oracle_passed':True,'mutant_detected':True})
 restored=compare(candidate,reference);assert all(m['candidate_weight_oracle']['passed'] for m in restored.values())
 result={'schema_version':1,'status':'captured_output_mutations_detected_restored_green','scope':'actual captured frame fault injection; unchanged real comparator; no compiled runtime mutant claim','candidate_sha256':sha(candidate_path),'reference_sha256':sha(reference_path),'comparator_sha256':sha(ROOT/'compare.py'),'baseline_oracle':{part:m['candidate_weight_oracle'] for part,m in baseline.items()},'mutations':rows,'restored_oracle_passed':True,'full_mpfb_quality':'HOLD unchanged, never used as mutation witness'}
 (ROOT/'evidence/mutation-controls.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return 0
if __name__=='__main__':raise SystemExit(main())
