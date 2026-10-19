"""CLI controls: frozen tamper rejection plus re-frozen semantic mutations.

Mutated copies are synthetic controls, never reference evidence. No Blender runs.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--prepared',type=Path,required=True)
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--freeze',type=Path,required=True)
    p.add_argument('--scratch',type=Path,required=True)
    a=p.parse_args()
    a.scratch.mkdir(parents=True,exist_ok=False)
    baseline=json.loads((a.run/'reference/arm2.json').read_text())
    tests=[('actual-pass',None,None,False),
        ('frozen-position-tamper',lambda x:x['positions'][244].__setitem__(0,x['positions'][244][0]+.01),'original run frozen hash mismatch',False),
        ('prepared-tamper',None,'prepared input frozen hash mismatch',False),
        ('stale-capture-identity',lambda x:x.__setitem__('historical_input_sha256','0'*64),'case/capture identity mismatch',True),
        ('bone-name-identity',lambda x:x['bones'][0].__setitem__('name','synthetic_wrong_bone'),'reference53-bone identity mismatch',True),
        ('bone-rest-relation',lambda x:x['bones'][0]['matrix_local'][0].__setitem__(3,x['bones'][0]['matrix_local'][0][3]+.01),'reference canonical rest mismatch',True),
        ('bone-skin-relation',lambda x:x['bones'][0]['matrix'][0].__setitem__(3,x['bones'][0]['matrix'][0][3]+.01),'reference authored skin mismatch',True),
        ('mesh-source-coverage',lambda x:x['positions'].pop(),'reference source mesh coverage',True),
        ('mesh-source-order',lambda x:(x['positions'].reverse(),x['rest_positions'].reverse(),x['weights'].reverse()),'reference fitted rest/source ID mismatch',True),
        ('modifier-policy',lambda x:x['modifiers'][0].__setitem__('preserve_volume',True),'reference modifier policy mismatch',True),
        ('modifier-position-lbs',lambda x:x['positions'][244].__setitem__(0,x['positions'][244][0]+.01),'reference modifier/LBS reconstruction mismatch',True)]
    receipts=[]
    for name,mutate,expected,refreeze in tests:
        target=a.scratch/name;target.mkdir()
        run=target/'run';run.mkdir();(run/'reference').mkdir()
        freeze=json.loads(a.freeze.read_text())
        for rel in freeze['run_files']:
            shutil.copy2(a.run/rel,run/rel)
        prepared=target/'inputs.json';shutil.copy2(a.prepared,prepared)
        if name=='prepared-tamper':
            prepared.write_bytes(prepared.read_bytes()+b' ')
        if mutate:
            changed=copy.deepcopy(baseline);mutate(changed)
            (run/'reference/arm2.json').write_text(json.dumps(changed,allow_nan=False))
        if refreeze:
            freeze['run_files']['reference/arm2.json']=digest(run/'reference/arm2.json')
        frozen=target/'freeze.json';frozen.write_text(json.dumps(freeze))
        command=[sys.executable,'-B']+(['-O'] if sys.flags.optimize else [])+[str(Path(__file__).with_name('compare.py').resolve()),'--prepared',str(prepared.resolve()),'--run',str(run.resolve()),'--freeze',str(frozen.resolve()),'--out',str((target/'comparison.json').resolve())]
        r=subprocess.run(command,capture_output=True,timeout=15)
        (target/'stdout.log').write_bytes(r.stdout);(target/'stderr.log').write_bytes(r.stderr)
        passed=r.returncode==0 if expected is None else r.returncode!=0 and expected in r.stderr.decode()
        receipts.append(dict(name=name,command=command,exit_code=r.returncode,expected_error=expected,passed=passed,scope='Synthetic modified output with updated freeze' if refreeze else 'Frozen provenance or actual baseline'))
    result=dict(tests=len(receipts),passed=sum(r['passed'] for r in receipts),optimized=bool(sys.flags.optimize),receipts=receipts)
    (a.scratch/'controls.json').write_text(json.dumps(result,indent=2)+'\n')
    require(result['tests']==result['passed'],'control failure; see preserved receipts')
    print(json.dumps({k:result[k] for k in ('tests','passed','optimized')}))


if __name__=='__main__':
    main()
