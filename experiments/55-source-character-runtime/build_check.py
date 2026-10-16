#!/usr/bin/env python3
"""Actual approved Humentity CPU library compile, one job, offline, local target."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
manifest=ROOT/'derived/Cargo.toml'
command=['cargo','check','--offline','--locked','--lib','--jobs','1','--manifest-path',str(manifest)]
env=os.environ.copy();env.update(CARGO_NET_OFFLINE='true',CARGO_TARGET_DIR=str(ROOT/'target'))
start=time.monotonic()
log=ROOT/'evidence/actual-native-check.log'
with log.open('x') as stream:
    result=subprocess.run(command,env=env,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
receipt=dict(command=command,exit_code=result.returncode,duration_seconds=time.monotonic()-start,
             candidate_library_compiled=result.returncode==0,candidate_runtime_executed=False,
             native_graphical_executed=False,web_graphical_executed=False,
             manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
             lock_sha256=hashlib.sha256((ROOT/'derived/Cargo.lock').read_bytes()).hexdigest(),
             log_sha256=hashlib.sha256(log.read_bytes()).hexdigest())
with (ROOT/'evidence/actual-native-check.json').open('x') as stream:json.dump(receipt,stream,indent=2)
print(json.dumps(receipt))
sys.exit(result.returncode)
