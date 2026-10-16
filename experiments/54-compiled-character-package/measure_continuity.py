#!/usr/bin/env python3
"""Measure actual retained Rust receipts. This does not generate a reference."""
import argparse,hashlib,json,math,pathlib
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--comparison',type=pathlib.Path,required=True);ap.add_argument('--out',type=pathlib.Path,required=True);a=ap.parse_args();root=a.comparison.resolve();summary=json.loads((root/'summary.json').read_text());cases={}
 for row in summary['cases']:
  p=root/(row['case_id']+'.result.json');assert sha(p)==row['result_sha256'];cases[row['case_id']]=json.loads(p.read_text())['bodies'][0]
 def points(case,channel):
  b=cases[case]
  if channel=='body':return b['positions']
  if channel=='joint_endpoints':return [p for bone in b['bones'] for p in [bone['head'],bone['tail']]]
  assert len(b['garments'])==1;return next(iter(b['garments'].values()))
 rows=[]
 for case in cases:
  if case=='neutral':continue
  record={'case_id':case}
  for channel in ['body','joint_endpoints','garment']:
   distances=[math.dist(p,q) for p,q in zip(points('neutral',channel),points(case,channel))]
   record[channel]={'changed_entries_above_1e-12_metres':sum(d>1e-12 for d in distances),'max_displacement_metres':max(distances)}
  assert record['body']['changed_entries_above_1e-12_metres']>0
  rows.append(record)
 half_errors={}
 for prefix in ['body','face']:
  channels=['body','joint_endpoints','garment'] if prefix=='body' else ['body']
  for channel in channels:
   error=max(abs(h[i]-(n[i]+.5*(e[i]-n[i]))) for n,h,e in zip(points('neutral',channel),points(prefix+'-half',channel),points(prefix+'-positive',channel)) for i in range(3));assert error<1e-12
   half_errors[prefix+':'+channel]=error
 result={'schema_version':1,'sample_class':summary['sample_class'],'source_input_manifest_sha256':summary['source_input_manifest_sha256'],'status':'passed','basis':'same root-frozen reference-local metres','comparison_summary_sha256':sha(root/'summary.json'),'cases':rows,'positive_half_linearity_max_component_error':half_errors,'interpretation':'body changes relocate helper-derived joint endpoints and refit actual proxy garment; local jaw changes need not move this rig/garment; these are numeric observations only'}
 with a.out.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
 print(json.dumps({'status':'passed','cases_with_actual_body_changes':len(rows),'half_linearity_max_component_error':max(half_errors.values()),'out':str(a.out)}))
if __name__=='__main__':main()
