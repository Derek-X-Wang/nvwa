#!/usr/bin/env python3
"""Stage existing artifacts only. Does not compile, download or launch."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shlex
import shutil
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import candidate as c


def prepare(variant,stage,binary=None,wasm=None,bindgen=None):
    source=c.ROOT/'experiments/48-genuine-fixture-work/artifacts' if variant=='baseline' else c.HERE/'artifacts'
    name='genuine44-calibrated47' if variant=='baseline' else 'genuine44-upper-arm-neutral50'
    stage=stage.resolve()
    c.need(stage.is_relative_to(c.ROOT/'.work/m2-neutral-ab'),'owned private staging directory')
    c.need(not stage.exists(),'fresh staging directory required')
    if binary is not None:
        c.need(binary.is_file() and os.access(binary,os.X_OK),'existing native binary required')
    else:
        c.need(wasm is not None and wasm.is_file(),'existing Wasm required')
        c.need(bindgen is not None and bindgen.is_file() and os.access(bindgen,os.X_OK),'existing pinned bindgen required')
        v=subprocess.run([str(bindgen),'--version'],capture_output=True,text=True,check=True)
        c.need(v.stdout.strip()=='wasm-bindgen 0.2.129','exact wasm-bindgen 0.2.129')
    stage.mkdir(parents=True)
    paths=[(source/(name+'.nvwa.json'),'works/'+name+'.nvwa.json'),(source/'assets/generated'/(name+'.glb'),'assets/generated/'+name+'.glb')]
    for src,rel in paths:
        dst=stage/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
        c.need(c.sha(src.read_bytes())==c.sha(dst.read_bytes()),'staged bytes exact')
    receipt={'variant':variant,'inputs':{str(src.relative_to(c.ROOT)):c.sha(src.read_bytes()) for src,_ in paths},'work_query':'?work=works/'+name+'.nvwa.json'}
    if binary is not None:
        app=stage/'NvwaNeutralAB.app';mac=app/'Contents/MacOS';mac.mkdir(parents=True)
        shutil.copy2(binary,mac/'probe-bin')
        q=lambda p:shlex.quote(str(p))
        launcher=mac/'NvwaNeutralAB'
        output=stage/'native.json';log=stage/'native.log';exitcode=stage/'exit-code.txt'
        launcher.write_text('#!/bin/sh\nexport NVWA_ASSET_ROOT='+q(stage/'assets')+'\nexport NVWA_POSE_OUTPUT='+q(output)+'\n'+q(mac/'probe-bin')+' --work '+q(stage/'works'/(name+'.nvwa.json'))+' > '+q(log)+' 2>&1\nprobe_exit=$?\nprintf \'%s\\n\' "$probe_exit" > '+q(exitcode)+'\nexit "$probe_exit"\n')
        launcher.chmod(0o755)
        with (app/'Contents/Info.plist').open('wb') as f:plistlib.dump({'CFBundleIdentifier':'dev.nvwa.neutral-ab-'+variant,'CFBundleName':'Nvwa Upper Arm A/B '+variant,'CFBundleExecutable':'NvwaNeutralAB','CFBundlePackageType':'APPL','CFBundleVersion':'1'},f)
        receipt.update(native_binary_sha256=c.sha(binary.read_bytes()),launch=str(app),output=str(output))
    else:
        subprocess.run([str(bindgen),'--target','web','--out-dir',str(stage),str(wasm)],check=True)
        shutil.copy2(Path(__file__).resolve().parent/'index.html',stage/'index.html')
        receipt.update(wasm_sha256=c.sha(wasm.read_bytes()),bindgen_sha256=c.sha(bindgen.read_bytes()),bindgen_version='0.2.129')
    (stage/'staging.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt

def main():
    p=argparse.ArgumentParser();p.add_argument('--variant',choices=['baseline','candidate'],required=True);p.add_argument('--stage',type=Path,required=True)
    group=p.add_mutually_exclusive_group(required=True);group.add_argument('--binary',type=Path);group.add_argument('--wasm',type=Path)
    p.add_argument('--wasm-bindgen',type=Path);a=p.parse_args()
    print(json.dumps(prepare(a.variant,a.stage,a.binary,a.wasm,a.wasm_bindgen),indent=2))
if __name__=='__main__':main()
