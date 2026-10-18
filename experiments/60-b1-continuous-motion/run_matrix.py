#!/usr/bin/env python3
"""Stream actual probe records; retain every failure and only30 full compressed frames."""
import argparse
import gzip
import hashlib
import json
import subprocess
from pathlib import Path
from checker import Checker,sha

ROOT=Path(__file__).resolve().parent

def write_json(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--binary',type=Path,required=True);p.add_argument('--asset-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--skip-surfaces',action='store_true');args=p.parse_args()
 require_new=args.out.resolve();require_new.mkdir(parents=True,exist_ok=False);(args.out/'keyframes').mkdir()
 checker=Checker(args.asset_root,surfaces=not args.skip_surfaces);failures=[];count=0;complete=False;records=0
 import os
 env=os.environ.copy();env['B1_60_ASSET_ROOT']=str(args.asset_root.resolve())
 identity={'evidence':'actual production NvwaRuntimePlugin CPU; graphics NOT-RUN','binary_sha256':hashlib.sha256(args.binary.read_bytes()).hexdigest(),'binary':str(args.binary.resolve()),'asset_root':str(args.asset_root.resolve()),'checker_sources':{str(q.relative_to(ROOT)):hashlib.sha256(q.read_bytes()).hexdigest() for q in sorted(ROOT.glob('*.py'))},'surfaces_requested':not args.skip_surfaces,'source_mutation_evidence':'NOT-RUN; scheduled separately by root','appearance':'HOLD; existing sportsuit findings retained'}
 write_json(args.out/'identity.json',identity)
 with (args.out/'metrics.jsonl').open('x') as metrics,(args.out/'probe-stderr.log').open('x') as stderr:
  child=subprocess.Popen([str(args.binary.resolve())],stdout=subprocess.PIPE,stderr=stderr,text=True,env=env)
  try:
   for line in child.stdout:
    if not line.startswith('B1_60 '):continue
    record=json.loads(line[6:]);records+=1
    if record['kind']=='complete':complete=True;continue
    request=record['request'];deep=record['kind']=='matrix' and request['jaw_drop']==0 and request['k']%8==0
    if deep:
     name=f"t{request['torso_length']:+g}__{request['clip_id']}__k{request['k']:02}.json.gz"
     with gzip.open(args.out/'keyframes'/name,'wt') as f:json.dump(record,f,separators=(',',':'),allow_nan=False)
    try:
     result,_=checker.check(record);count+=1
    except (ValueError,KeyError,TypeError,IndexError,ZeroDivisionError) as error:
     result={'kind':record['kind'],'request':{k:v for k,v in request.items() if k not in ('prior_parts',)},'technical_pass':False,'error':str(error),'actual_record_sha256':sha(record)};failures.append(result)
     # Preserve the first failure in full even outside the keyframe cohort.
     if len(failures)<=3:
      with gzip.open(args.out/f'failure-{len(failures)}.json.gz','wt') as f:json.dump(record,f,separators=(',',':'),allow_nan=False)
    metrics.write(json.dumps(result,separators=(',',':'),allow_nan=False)+'\n');metrics.flush()
   code=child.wait()
  except BaseException:
   child.terminate();child.wait();raise
 summary={'passed':code==0 and complete and not failures and checker.coverage()['complete'],'probe_exit':code,'probe_complete_marker':complete,'records':records,'passing_records':count,'failures':failures,'coverage':checker.coverage(),'desktop_live':'NOT-RUN','web_live':'NOT-RUN','gpu_vertex_readback':False,'garment_quality':'HOLD; nearest-triangle/strain descriptors do not constitute cloth acceptance','source_mutation_red':'NOT-RUN; separate root evidence required'}
 write_json(args.out/'summary.json',summary)
 hashes={str(q.relative_to(args.out)):hashlib.sha256(q.read_bytes()).hexdigest() for q in args.out.rglob('*') if q.is_file()};write_json(args.out/'SHA256SUMS.json',hashes)
 print(json.dumps(summary,allow_nan=False));return 0 if summary['passed'] else 3
if __name__=='__main__':raise SystemExit(main())
