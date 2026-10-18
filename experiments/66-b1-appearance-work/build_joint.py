from pathlib import Path
import argparse, hashlib, json, os, shutil, subprocess, time
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--bindgen',type=Path,required=True);a=p.parse_args()
r=Path.cwd();o=a.out.resolve();o.mkdir(parents=True,exist_ok=False)
target=r/'target'; env=dict(os.environ,CARGO_BUILD_JOBS='1',CARGO_TARGET_DIR=str(target),CARGO_NET_OFFLINE='true',CARGO_PROFILE_DEV_DEBUG='0',CARGO_PROFILE_TEST_DEBUG='0')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def closure():
    paths=[r/n for n in ['Cargo.toml','Cargo.lock','rust-toolchain.toml','docs/evidence/b1-motion/web-edited.nvwa.json']]
    for d in ['crates','vendor','assets','scripts','web','examples','experiments/62-b1-appearance-preview','experiments/64-b1-accessory-preview','experiments/65-b1-appearance-quality','experiments/66-b1-appearance-work']:
        paths.extend(p for p in (r/d).rglob('*') if p.is_file() and not set(p.parts)&{'target','__pycache__','.git'})
    return {str(p.relative_to(r)):sha(p) for p in sorted(set(paths))}
before=closure();(o/'source-closure.json').write_text(json.dumps(before,indent=2)+'\n')
failures=[]
checks=[]
def run(label,args):
    print('START '+label,flush=True);start=time.time()
    with (o/(label+'.log')).open('w') as f:
        c=subprocess.run(args,env=env,stdout=f,stderr=subprocess.STDOUT)
    checks.append({'label':label,'exit_code':c.returncode,'seconds':round(time.time()-start,2)})
    (o/'check-results.json').write_text(json.dumps(checks,indent=2)+'\n')
    if c.returncode:
        print((o/(label+'.log')).read_text()[-13000:],flush=True)
        failures.append(label)
        print('FAILED '+label+' '+str(c.returncode)+'; required gate remains failed',flush=True)
        if label.endswith('-tests') or label=='workspace-clippy':
            return False  # collect other evidence, never convert the failed gate to success
        raise SystemExit(label+' FAILED '+str(c.returncode))
    print('PASS '+label+' '+str(round(time.time()-start,2))+'s',flush=True)
    return True
def record(label,base):
    if closure()!=before:raise SystemExit('source changed during '+label)
    (o/(label+'-receipt.json')).write_text(json.dumps({'scope':'Compilation/export only; actual launch, rendered checks, function, CPU and performance evidence are separate','validation_failures_so_far':list(failures),'sources':before,'artifacts':{str(p.relative_to(base)):sha(p) for p in sorted(base.rglob('*')) if p.is_file()}},indent=2)+'\n')
run('workspace-format',['cargo','fmt','-p','nvwa-core','-p','nvwa-cli','-p','nvwa-runtime','-p','nvwa-studio','-p','nvwa-b1-adapter','--check'])
run('workspace-tests',['cargo','test','--workspace','--no-fail-fast','--locked','--offline'])
run('workspace-clippy',['cargo','clippy','--workspace','--all-targets','--locked','--offline','--','-D','warnings'])
run('product-web',['cargo','build','-p','nvwa-studio','--lib','--target','wasm32-unknown-unknown','--locked','--offline'])
site=o/'product-web';site.mkdir();run('product-bindgen',[str(a.bindgen),'--target','web','--out-dir',str(site),str(target/'wasm32-unknown-unknown/debug/nvwa_studio.wasm')]);shutil.copy2(r/'web/index.html',site/'index.html');shutil.copytree(r/'assets',site/'assets');(site/'works').mkdir();shutil.copy2(r/'examples/m1-sequence.nvwa.json',site/'works/m1-sequence.nvwa.json');shutil.copy2(r/'examples/b1-appearance.nvwa.json',site/'works/b1-appearance.nvwa.json');record('product-web',site)
run('product-native',['cargo','build','-p','nvwa-studio','--bins','--locked','--offline'])
native=o/'product-native';native.mkdir();shutil.copy2(target/'debug/nvwa-studio',native/'nvwa-studio');run('package-native',['python3','scripts/package-native.py','--profile','debug']);shutil.copytree(r/'dist/Nvwa.app',native/'Nvwa.app');record('product-native',native)
for exp in ['66-b1-appearance-work','65-b1-appearance-quality/preview']:
    manifest=r/'experiments'/exp/'Cargo.toml';info=subprocess.check_output(['cargo','metadata','--no-deps','--format-version','1','--manifest-path',str(manifest),'--locked','--offline'],env=env,text=True);pkgs=json.loads(info)['packages'];pkg=next(q for q in pkgs if Path(q['manifest_path'])==manifest);name=pkg['name'];lib=next(t['name'] for t in pkg['targets'] if 'cdylib' in t['kind']);bn=next(t['name'] for t in pkg['targets'] if 'bin' in t['kind']);folder=o/name
    run(name+'-tests',['cargo','test','--manifest-path',str(manifest),'--lib','--locked','--offline'])
    run(name+'-web',['cargo','build','--manifest-path',str(manifest),'--lib','--target','wasm32-unknown-unknown','--locked','--offline'])
    site=folder/'web';(site/'pkg').mkdir(parents=True);run(name+'-bindgen',[str(a.bindgen),'--target','web','--out-dir',str(site/'pkg'),str(target/'wasm32-unknown-unknown/debug'/(lib+'.wasm'))]);shutil.copy2(manifest.parent/'index.html',site/'index.html');shutil.copytree(r/'assets',site/'assets');(site/'works').mkdir();shutil.copy2(r/'docs/evidence/b1-motion/web-edited.nvwa.json',site/'works/b1-motion.nvwa.json');shutil.copytree(manifest.parent/'works',site/'works',dirs_exist_ok=True);record(name+'-web',site)
    run(name+'-native',['cargo','build','--manifest-path',str(manifest),'--bins','--locked','--offline'])
    native=folder/'native';native.mkdir();shutil.copy2(target/'debug'/bn,native/bn);shutil.copytree(r/'dist/Nvwa.app',native/'Nvwa.app');shutil.copy2(target/'debug'/bn,native/'Nvwa.app/Contents/MacOS/Nvwa');record(name+'-native',native)
if failures:
    print('EXPORTS_READY_WITH_FAILED_CHECKS '+json.dumps(failures),flush=True)
    raise SystemExit(1)
print('ALL_EXPORTS_READY',flush=True)
