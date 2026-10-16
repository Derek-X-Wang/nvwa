#!/usr/bin/env python3
"""Run the actual candidate locally, binding each frame to exact command/source/build."""
import argparse,hashlib,json,subprocess,time,os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'55-source-character-runtime'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tree(p):return hashlib.sha256(b''.join(x.relative_to(p).as_posix().encode()+b'\0'+sha(x).encode()+b'\n' for x in sorted(p.rglob('*')) if x.is_file() and not any(k in ('.git','target') for k in x.relative_to(p).parts))).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--recipes',nargs='*');a=p.parse_args();assert not a.out.exists();a.out.mkdir(parents=True)
 binary=ROOT/'target/debug/b1-pose-adapter';poses=ROOT.parent/'56-b1-pose-reference/poses.json';entries=[];start=time.monotonic()
 for config in sorted((OLD/'configs').glob('*.json')):
  if a.recipes and config.stem not in a.recipes:continue
  output=a.out/config.stem;cmd=[str(binary),str(config),str(poses),str(output)];log=a.out/(config.stem+'.log');t=time.monotonic()
  with log.open('x') as stream:r=subprocess.run(cmd,stdout=stream,stderr=subprocess.STDOUT)
  outputs={x.name:sha(x) for x in sorted(output.glob('*.json'))} if output.exists() else {}
  entry={'recipe_id':config.stem,'config_sha256':sha(config),'command':cmd,'exit_code':r.returncode,'duration_seconds':time.monotonic()-t,'log_sha256':sha(log),'outputs':outputs};entries.append(entry);print(config.stem,r.returncode,len(outputs),flush=True)
  if r.returncode:break
 result={'schema_version':1,'status':('actual_candidate_executed' if len(entries)==8 else 'actual_candidate_probe') if len(entries)==(len(a.recipes) if a.recipes else 8) and all(e['exit_code']==0 and len(e['outputs'])==5 for e in entries) else 'execution_failed','binary_sha256':sha(binary),'adapter_tree_sha256':tree(ROOT/'adapter'),'source_tree_sha256':tree(ROOT/'derived'),'poses_sha256':sha(poses),'common_sha256':sha(ROOT.parent.parent/'.work/character-approved-20261016/common-sample.json'),'route_environment':{k:os.environ.get(k) for k in ('B1_FRAME_GAUGE','B1_FULL_WEIGHTS')},'cases':entries,'duration_seconds':time.monotonic()-start}
 (a.out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');return 0 if result['status']!='execution_failed' else 2
if __name__=='__main__':raise SystemExit(main())
