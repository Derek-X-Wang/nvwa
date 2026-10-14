#!/usr/bin/env python3
"""Finite mutations of copied real production candidate; preserve checker stdout/stderr."""
import argparse, hashlib, json, shutil, subprocess, sys
from pathlib import Path

parser=argparse.ArgumentParser();parser.add_argument('pack',type=Path);parser.add_argument('--scratch',type=Path,required=True);parser.add_argument('--evidence',type=Path,required=True);a=parser.parse_args()
a.scratch.mkdir(parents=True,exist_ok=False);a.evidence.mkdir(parents=True,exist_ok=True)
checker=Path(__file__).with_name('check.py').resolve(); results=[]

def run(name,pack,flags=(),expected=0,contains=None):
    command=[sys.executable,str(checker),str(pack),*flags];p=subprocess.run(command,capture_output=True)
    (a.evidence/(name+'.stdout.json')).write_bytes(p.stdout);(a.evidence/(name+'.stderr.log')).write_bytes(p.stderr)
    passed=p.returncode==expected and (contains is None or contains.encode() in p.stdout)
    results.append({'name':name,'argv':command,'actual_exit_code':p.returncode,'expected_exit_code':expected,'expected_error_contains':contains,'passed':passed,'stdout_sha256':hashlib.sha256(p.stdout).hexdigest()})
    if not passed:raise SystemExit('control failed: '+name)

def mutate_manifest(pack,fn):
    path=pack/'manifest.json';m=json.loads(path.read_text());fn(m);path.write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')

run('baseline-green',a.pack)
for name,error in [('missing-font-OFL','missing required file'),('altered-craft-notice','altered required file'),('unknown-expression','unknown license expression'),('malformed-expression','malformed license expression'),('omitted-required-reference','required package file omitted'),('unsupported-target','unsupported or missing target'),('changed-feature','target features changed'),('altered-identity','frozen production identity changed')]:
    pack=a.scratch/name;shutil.copytree(a.pack,pack)
    if name=='missing-font-OFL':(pack/'texts/packages/epaint_default_fonts@0.36.2/fonts/OFL.txt').unlink()
    if name=='altered-craft-notice':
        path=pack/'texts/packages/craft-ui@0.1.0/NOTICE';path.write_bytes(path.read_bytes()+b'\nCONTROL ALTERATION\n')
    if name=='unknown-expression':mutate_manifest(pack,lambda m:m['packages']['craft-ui@0.1.0'].__setitem__('license_expression','Unknown-999.0'))
    if name=='malformed-expression':mutate_manifest(pack,lambda m:m['packages']['craft-ui@0.1.0'].__setitem__('license_expression','MIT OR OR Apache-2.0'))
    if name=='omitted-required-reference':mutate_manifest(pack,lambda m:m['files'].pop('texts/packages/epaint_default_fonts@0.36.2/fonts/UFL.txt'))
    if name=='unsupported-target':mutate_manifest(pack,lambda m:m['targets'].__setitem__('x86_64-pc-windows-msvc',m['targets'].pop('aarch64-apple-darwin')))
    if name=='changed-feature':mutate_manifest(pack,lambda m:m['targets']['wasm32-unknown-unknown']['features_by_package']['bevy@0.19.1'].append('invented-feature'))
    if name=='altered-identity':mutate_manifest(pack,lambda m:m['identity']['Cargo.lock'].__setitem__('sha256','0'*64))
    run(name+'-red',pack,expected=1,contains=error)
    shutil.rmtree(pack)
    run(name+'-restored-green',a.pack)
run('completeness-blocked-red',a.pack,['--require-complete'],expected=1,contains='redistribution completeness BLOCKED')
(a.evidence/'controls.json').write_text(json.dumps({'status':'VERIFIED','controls':results,'retained_pack_sha256':hashlib.sha256((a.pack/'manifest.json').read_bytes()).hexdigest(),'temporary_pack_copies_removed':True},indent=2)+'\n')
print(json.dumps({'status':'VERIFIED','runs':len(results),'expected_rejections':9,'all_passed':all(r['passed'] for r in results)}))
