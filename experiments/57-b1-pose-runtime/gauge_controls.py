#!/usr/bin/env python3
"""Wrong source-frame gauge must fail the unchanged canonical matrix gate."""
import copy,json
from pathlib import Path
from compare import compare,sha
from validation import require
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent.parent

def main():
 cp=ROOT/'results/full-weight-probe/body-positive/combined.json';rp=REPO/'.work/b1-pose-reference/run1/body-positive__combined.json';manifest=json.loads((ROOT.parent/'56-b1-pose-reference/reference/frozen/manifest.json').read_text());entry=next(c for c in manifest['cases'] if c['case_id']=='body-positive__combined');assert sha(rp)==entry['sha256']
 c=json.loads(cp.read_text());r=json.loads(rp.read_text());baseline=compare(c,r);assert all(m['rest_matrix']['passed'] and m['posed_matrix']['passed'] for m in baseline.values())
 mutant=copy.deepcopy(c);identity=[1.,0,0,0,0,1.,0,0,0,0,1.,0,0,0,0,1.]
 for part in ('body','garment'):
  for b in mutant['parts'][part]['frame']['bones']:
   b['frame_gauge']=identity;b['canonical_rest']=b['rest'];b['canonical_posed']=b['posed']
 try:
  measured=compare(mutant,r);require(all(not m['rest_matrix']['passed'] and not m['posed_matrix']['passed'] for m in measured.values()),'wrong gauge escaped matrix gate');wrong_gauge={'rejected':True,'measures':measured}
 except ValueError as error:wrong_gauge={'rejected':True,'error':str(error)}
 restored=compare(c,r);assert all(m['rest_matrix']['passed'] and m['posed_matrix']['passed'] for m in restored.values())
 result={'status':'wrong_gauge_detected_restored_green','scope':'actual captured frame fault injection; no separately compiled mutant claim','candidate_sha256':sha(cp),'reference_sha256':sha(rp),'comparator_sha256':sha(ROOT/'compare.py'),'baseline':{p:{k:m[k] for k in ('rest_matrix','posed_matrix','frame_gauge_identities')} for p,m in baseline.items()},'wrong_gauge':wrong_gauge,'restored_passed':True}
 (ROOT/'evidence/gauge-controls.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
