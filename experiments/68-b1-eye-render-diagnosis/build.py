#!/usr/bin/env python3
"""Root-scheduled, offline exports only. Does not launch an app, browser or server."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
ROOT = Path(__file__).resolve().parents[2]
EXP = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def closure():
    files = [ROOT/name for name in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']]
    for directory in [ROOT/'crates', ROOT/'vendor', ROOT/'assets', EXP]:
        files += [p for p in directory.rglob('*') if p.is_file() and not set(p.relative_to(ROOT).parts)&{'target','__pycache__','.git'}]
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(files)}

def main():
    if sys.version_info < (3,11):raise SystemExit("Existing Python3.11+ required (tomllib); select that interpreter, no installation/download is performed")
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--target-dir',type=Path,required=True)
    parser.add_argument('--bindgen',type=Path,required=True)
    args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    target=args.target_dir.resolve()
    env=dict(os.environ,CARGO_TARGET_DIR=str(target),CARGO_BUILD_JOBS='1',CARGO_NET_OFFLINE='true')
    before=closure();(out/'source-closure.json').write_text(json.dumps(before,indent=2)+'\n')
    checks=[]
    def run(label,command):
        start=time.monotonic();print('START '+label,flush=True)
        with (out/(label+'.log')).open('w') as log:
            process=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        checks.append({'label':label,'exit_code':process.returncode,'seconds':round(time.monotonic()-start,3)})
        (out/'checks.json').write_text(json.dumps(checks,indent=2)+'\n')
        print(('PASS ' if not process.returncode else 'FAIL ')+label,flush=True)
        if process.returncode:raise SystemExit(f'{label} failed; retained log, no successful export receipt')
    manifest=str(EXP/'Cargo.toml')
    run('source-tests',[sys.executable,'-B','-m','unittest','discover','-s',str(EXP),'-p','test_*.py'])
    run('format',['rustfmt','--edition','2024','--check',*[str(p) for p in sorted((EXP/'src').rglob('*.rs'))]])
    run('native-tests',['cargo','test','--manifest-path',manifest,'--lib','--locked','--offline'])
    run('native-build',['cargo','build','--manifest-path',manifest,'--bin','studio68','--locked','--offline'])
    native=out/'native';native.mkdir();shutil.copy2(target/'debug/studio68',native/'studio68')
    run('web-build',['cargo','build','--manifest-path',manifest,'--lib','--target','wasm32-unknown-unknown','--locked','--offline'])
    site=out/'web';(site/'pkg').mkdir(parents=True)
    run('web-bindgen',[str(args.bindgen),'--target','web','--out-dir',str(site/'pkg'),str(target/'wasm32-unknown-unknown/debug/b1_eye_render_diagnosis.wasm')])
    shutil.copy2(EXP/'index.html',site/'index.html');shutil.copytree(ROOT/'assets',site/'assets');shutil.copytree(EXP/'works',site/'works')
    if closure()!=before:raise SystemExit('source closure changed during build; no successful export receipt')
    (out/'export-receipt.json').write_text(json.dumps({'scope':'native tests and native/Wasm compilation/export only; actual launch, screenshot, GPU observation, performance and cause remain NOT-RUN','checks':checks,'sources':before,'artifacts':{str(p.relative_to(out)):sha(p) for directory in [native,site] for p in sorted(directory.rglob('*')) if p.is_file()}},indent=2)+'\n')
    print('EXPORTS_READY '+str(out),flush=True)
if __name__=='__main__':main()
