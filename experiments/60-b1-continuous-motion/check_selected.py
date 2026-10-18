#!/usr/bin/env python3
"""Check14 actual Studio readbacks per platform; parity never fills a missing platform."""
import argparse
import hashlib
import json
from pathlib import Path
from checker import Checker,CLIPS,sha,require

def main():
 p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--web',type=Path,required=True);p.add_argument('--asset-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--skip-surfaces',action='store_true');args=p.parse_args();args.out.mkdir(parents=True,exist_ok=False)
 expected={(0.,0.,c,float(t)) for c in CLIPS for t in [0,1,2,3,4]}|{(float(torso),0.,c,2.) for torso in [-1,1] for c in CLIPS};platforms={};allresults={};failures=[]
 for platform,folder in [('native',args.native),('web',args.web)]:
  checker=Checker(args.asset_root,surfaces=not args.skip_surfaces);records={};results=[]
  for file in sorted(folder.glob('*.json')):
   record=json.loads(file.read_text())
   if not isinstance(record,dict):continue
   if record.get('kind')!='studio' or record.get('request',{}).get('action')!='sample':continue
   r=record['request'];key=(float(r['torso_length']),float(r['jaw_drop']),r['clip_id'],float(r['seconds']))
   if key not in expected:continue
   if key in records:raise ValueError(f'duplicate exact selected snapshot {platform} {key}')
   records[key]=(file,record)
  for key,(file,record) in sorted(records.items()):
   record['deep']=True
   try:
    result,_=checker.check(record);result['file_sha256']=hashlib.sha256(file.read_bytes()).hexdigest();results.append(result)
   except (ValueError,KeyError,TypeError,IndexError,ZeroDivisionError) as error:failures.append({'platform':platform,'key':key,'file':str(file),'error':str(error)})
  platforms[platform]={'expected':14,'observed':len(records),'missing':sorted(expected-set(records)),'technical_passing':len(results),'live_visual_observation':'NOT-RUN by this numerical checker; attach root GUI evidence separately'};allresults[platform]=records
  with (args.out/(platform+'-metrics.jsonl')).open('x') as f:
   for result in results:f.write(json.dumps(result,separators=(',',':'),allow_nan=False)+'\n')
 parity=[]
 for key in sorted(set(allresults['native'])&set(allresults['web'])):
  _,a=allresults['native'][key];_,b=allresults['web'][key];a=a['snapshot'];b=b['snapshot'];maximum={'position':0.,'matrix':0.,'normal':0.,'tangent':0.}
  try:
   require(a['parameters']==b['parameters'] and a['sample']['clip_id']==b['sample']['clip_id'] and abs(a['sample']['source_seconds']-b['sample']['source_seconds'])<1e-6,'state mismatch')
   def compare(x,y,bucket):
    require(isinstance(x,list) and isinstance(y,list) and len(x)==len(y) and bool(x),'parity array coverage')
    for i,j in zip(x,y):
     if isinstance(i,list):compare(i,j,bucket)
     else:maximum[bucket]=max(maximum[bucket],abs(i-j))
   for left,right in zip(a['bones'],b['bones']):
    require(left['name']==right['name'] and left['parent']==right['parent'],'bone parity order')
    for field in ['rest','posed','inverse_bind','canonical_rest','canonical_posed','frame_gauge']:compare(left[field],right[field],'matrix')
   for left,right in zip(a['parts'],b['parts']):
    require(left['name']==right['name'] and left['source_ids']==right['source_ids'] and left['indices']==right['indices'],'part/source/index parity')
    for field,bucket in [('positions','position'),('rest_positions','position'),('normals','normal'),('tangents','tangent'),('display_transform','matrix')]:compare(left[field],right[field],bucket)
   require(maximum['position']<=1e-5 and maximum['matrix']<=1e-4 and maximum['normal']<=1e-4 and maximum['tangent']<=1e-4,'native/Web numeric parity')
   parity.append({'key':key,'maximum_component':maximum,'passed':True})
  except (ValueError,KeyError,TypeError,IndexError) as error:failures.append({'parity_key':key,'error':str(error)})
 summary={'passed':not failures and all(v['observed']==14 and v['technical_passing']==14 for v in platforms.values()) and len(parity)==14,'platforms':platforms,'parity':parity,'failures':failures,'cloth_quality':'HOLD','gpu_vertex_readback':False,'source_mutation_red':'NOT-RUN by this checker'}
 (args.out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n');print(json.dumps(summary,allow_nan=False));return 0 if summary['passed'] else 3
if __name__=='__main__':raise SystemExit(main())
