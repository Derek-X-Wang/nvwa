#!/usr/bin/env python3
"""Cached/offline one-job build. Compilation is separate from execution and comparison."""
import argparse,hashlib,json,os,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def main():
 p=argparse.ArgumentParser();p.add_argument('--receipt',type=Path,required=True);a=p.parse_args();assert not a.receipt.exists()
 command=['cargo','build','--offline','--locked','--jobs','1','--manifest-path',str(ROOT/'adapter/Cargo.toml')];env=os.environ.copy();env.update(CARGO_NET_OFFLINE='true',CARGO_TARGET_DIR=str(ROOT/'target'));start=time.monotonic();log=a.receipt.with_suffix('.log');assert not log.exists()
 with log.open('x') as stream:r=subprocess.run(command,env=env,stdout=stream,stderr=subprocess.STDOUT)
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();result={'command':command,'exit_code':r.returncode,'duration_seconds':time.monotonic()-start,'manifest_sha256':sha(ROOT/'adapter/Cargo.toml'),'lock_sha256':sha(ROOT/'adapter/Cargo.lock'),'log_sha256':sha(log),'runtime_executed':False,'gpu_executed':False}
 if r.returncode==0:result['binary_sha256']=sha(ROOT/'target/debug/b1-pose-adapter')
 a.receipt.write_text(json.dumps(result,indent=2)+'\n');return r.returncode
if __name__=='__main__':raise SystemExit(main())
