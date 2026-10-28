"""Finite job-log transport of original raw streams and identity; no source dump."""
import json
import os
from pathlib import Path
import signal
import sys
import time
from codec import encode
HERE=Path(__file__).resolve().parent

def stop(signum,frame): raise TimeoutError('bounded export expired')
signal.signal(signal.SIGALRM,stop)
setup=json.loads((HERE/'SETUP.json').read_text())
remaining=min(60,setup['job_start_monotonic']+900-time.monotonic())
if remaining<=0: raise RuntimeError('total900 exhausted before export')
signal.setitimer(signal.ITIMER_REAL,remaining)
allowed=['SETUP.json','ACQUISITION-RAW.json']
allowed += ['attempt/input-hashes.json','attempt/final-input-hashes.json','attempt/status.json']
allowed += [f'attempt/{i:02d}.{stream}.log' for i in range(1,22) for stream in ('stdout','stderr')]
files={}
for name in allowed:
    path=HERE/name
    if path.exists():
        if path.is_symlink() or not path.is_file():raise RuntimeError('invalid evidence file')
        raw=path.read_bytes()
        if b'/Users/' in raw or b'/opt/homebrew/' in raw:raise RuntimeError('private host path in public evidence')
        files[name]=raw
identity={k:os.environ[k] for k in ('GITHUB_REPOSITORY','GITHUB_SHA','GITHUB_REF','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT')}
if identity!=setup['identity']:raise RuntimeError('export identity mismatch')
wire=encode(files,identity)
sys.stdout.buffer.write(wire);sys.stdout.buffer.flush()
if time.monotonic()>=setup['job_start_monotonic']+900:raise RuntimeError('total900 reached during export')
signal.setitimer(signal.ITIMER_REAL,0)
