#!/usr/bin/env python3
"""Faults pass through the exact sampled CI comparator called by real regression."""
import copy,json
from pathlib import Path
from sampled_regression import inspect_frame,sha
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent.parent

def main():
 cp=ROOT/'results/full-weight-probe/body-positive/combined.json';rp=REPO/'.work/b1-pose-runtime/ci-inputs/regression/reference.json';reference=json.loads(rp.read_text());r=next(c for c in reference['cases'] if c['case_id']=='body-positive__combined');c=json.loads(cp.read_text());inspect_frame(c,r);results=[]
 for fault in ('wrong-bone-order','omitted-deformation','wrong-gauge','missing-bone','nonfinite-matrix'):
  m=copy.deepcopy(c)
  for part in ('body','garment'):
   f=m['parts'][part]['frame']
   if fault=='wrong-bone-order':f['bones']=f['bones'][1:]+f['bones'][:1]
   elif fault=='omitted-deformation':f['positions']=f['rest_positions']
   elif fault=='wrong-gauge':
    for b in f['bones']:b['canonical_rest']=b['rest'];b['canonical_posed']=b['posed']
   elif fault=='missing-bone':f['bones']=f['bones'][:-1]
   elif fault=='nonfinite-matrix':f['bones'][0]['canonical_rest'][0]=float('nan')
  try:inspect_frame(m,r)
  except (ValueError,KeyError,IndexError,TypeError) as error:results.append({'fault':fault,'rejected':True,'error':str(error)})
  else:raise AssertionError('sampled comparator missed '+fault)
 inspect_frame(c,r);receipt={'status':'sampled_comparator_mutations_detected_restored_green','scope':'fault injection on captured actual output; no separately compiled mutant claim','candidate_sha256':sha(cp),'reference_sha256':sha(rp),'sampled_comparator_sha256':sha(ROOT/'sampled_regression.py'),'mutations':results,'restored_passed':True};(ROOT/'evidence/sampled-controls.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
