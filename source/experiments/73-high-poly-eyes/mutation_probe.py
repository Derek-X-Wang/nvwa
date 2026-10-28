"""Bounded negative controls against an existing production68 CPU capture."""
import argparse,copy,json
from pathlib import Path
import cpu_probe as p

def run(path):
 e=json.loads(path.read_bytes());base=e['frame']['full_base'];good=p.replay(base,'b');bad=p.replay(base,'b',clamp_signed=True)
 delta=max(abs(x-y) for a,b in zip(good['positions'],bad['positions']) for x,y in zip(a,b));p.require(delta>p.LIMIT,'signed-clamp control did not change retained fit')
 rejected=[]
 for name,actual in [('clamped_signed',bad),('second_unit_conversion',{**good,'positions':[[x*.1 for x in v] for v in good['positions']]})]:
  try:p.compare(good,actual)
  except ValueError:rejected.append(name)
 p.require(len(rejected)==2,'mutation escaped declared1e-6 limit')
 missing=copy.deepcopy(base);body=next(x for x in missing['parts'] if x['name']=='body');target=body['source_ids'][0];keep=[i for i,x in enumerate(body['source_ids']) if x!=target];body['source_ids']=[body['source_ids'][i] for i in keep];body['rest_positions']=[body['rest_positions'][i] for i in keep]
 try:p.replay(missing,'b')
 except ValueError as error:
  p.require('complete19158' in str(error),'wrong rejection reason');rejected.append('missing_cage_vertex')
 p.require(len(rejected)==3,'incomplete helper cage escaped')
 return {'capture_basename':path.name,'capture_sha256':p.sha(path.read_bytes()),'rejected':rejected,'signed_clamp_max_component_change_m':delta,'original_limit_m':p.LIMIT,'scope':'independent CPU arithmetic/rejection controls only; Rust live publication tests separate'}
def main():
 a=argparse.ArgumentParser();a.add_argument('capture',type=Path);a.add_argument('--out',type=Path,required=True);r=a.parse_args();r.out.write_text(json.dumps(run(r.capture),indent=2)+'\n')
if __name__=='__main__':main()
