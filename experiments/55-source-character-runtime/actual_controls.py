#!/usr/bin/env python3
"""Real prepare_data/run_cases rejection controls using copied, approved bytes."""
import hashlib,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent.parent;STORE=REPO/'.work/character-approved-20261016'
MANIFEST=STORE/'common-sample.json';SHA='2e8566a4f12de710ead88f6aa2d71fc44e0680761a4f2fdc48a844b6f3534ab7'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    binary_sha=digest(ROOT/'target/debug/humentity-probe')
    prepare=[sys.executable,str(ROOT/'prepare_data.py'),'--common-manifest',str(MANIFEST),'--common-manifest-sha256',SHA]
    execute=[sys.executable,str(ROOT/'run_cases.py'),'--common-manifest',str(MANIFEST),'--common-manifest-sha256',SHA,'--binary-sha256',binary_sha,'--case','neutral']
    immutable=[MANIFEST]+[STORE/e['path'] for e in json.loads(MANIFEST.read_text())['files']]
    immutable += [STORE/'upstream/Humentity'/e['path'] for e in json.loads((ROOT/'upstream-inventory.json').read_text())['files']]
    before={str(p):digest(p) for p in immutable};records=[]
    def check(name,command,reason):
        result=subprocess.run(command,cwd=REPO,capture_output=True,text=True,timeout=20)
        output=result.stdout+result.stderr
        assert result.returncode!=0 and reason in output,(name,result.returncode,output)
        assert all(digest(Path(p))==sha for p,sha in before.items()),name+' mutated approved input'
        records.append(dict(name=name,exit_code=result.returncode,expected_reason=reason,output=output,
                            input_hashes_preserved=True,candidate_execution_attempted=False))
    with tempfile.TemporaryDirectory(prefix='.control-',dir=ROOT) as folder:
        temp=Path(folder)
        fake_manifest=temp/'changed-manifest.json';fake_manifest.write_bytes(MANIFEST.read_bytes()+b' ')
        check('manifest-tamper-real-prepare',[sys.executable,str(ROOT/'prepare_data.py'),'--common-manifest',str(fake_manifest),'--common-manifest-sha256',SHA],'SHA-256 mismatch')
        clone=temp/'source';shutil.copytree(STORE/'upstream/Humentity',clone)
        p=clone/'src/morphs.rs';data=p.read_bytes();p.write_bytes(b'x'+data[1:])
        check('upstream-source-tamper-real-run',execute+['--candidate',str(clone),'--out',str(temp/'not-created-source')],'upstream Git blob mismatch')
        staging=temp/'staging';source=json.loads(MANIFEST.read_text())['files'][0];p=staging/source['path'];p.parent.mkdir(parents=True);shutil.copyfile(STORE/source['path'],p);data=p.read_bytes();p.write_bytes(b'x'+data[1:])
        check('raw-common-source-tamper-real-prepare',prepare+['--staging',str(staging)],'common frozen file mismatch')
        check('existing-data-preserved-real-prepare',prepare,'derived data already exists')
        check('receipt-is-common-manifest-real-run',execute+['--out',str(MANIFEST)],'result directory already exists')
        target=STORE/'mpfb-addon/data/3dobjs/base.obj'
        check('receipt-is-raw-source-real-run',execute+['--out',str(target)],'result directory already exists')
        for kind in ['symlink','hardlink']:
            p=temp/(kind+'-alias')
            if kind=='symlink':p.symlink_to(MANIFEST)
            else:os.link(MANIFEST,p)
            check(kind+'-input-alias-real-run',execute+['--out',str(p)],'result directory already exists')
        existing=temp/'old-result';existing.mkdir();sentinel=existing/'sentinel';sentinel.write_bytes(b'OLD RESULT')
        check('existing-result-preserved-real-run',execute+['--out',str(existing)],'result directory already exists')
        assert sentinel.read_bytes()==b'OLD RESULT'
        # Configs are task-owned derived files, never the shared raw inputs.
        cfg=ROOT/'configs/neutral.json';original=cfg.read_bytes()
        try:
            changed=json.loads(original);changed['target_weights']['torso-scale-vert-incr']=.25;cfg.write_text(json.dumps(changed))
            check('config-recipe-tamper-real-run',execute+['--out',str(temp/'not-created-config')],'config recipe/scale tamper')
        finally:cfg.write_bytes(original)
        assert not (temp/'not-created-source').exists() and not (temp/'not-created-config').exists()
    result=dict(schema_version=1,controls=len(records),all_passed=True,
                scope='Actual new prepare_data.py/run_cases.py subprocess paths; approved-byte copies for source tamper; no candidate execution',
                inputs_checked=len(before),records=records)
    with (ROOT/'evidence/actual-controls.json').open('x') as stream:json.dump(result,stream,indent=2)
    print(str(len(records))+' real-path controls PASS; '+str(len(before))+' approved input hashes preserved')
if __name__=='__main__':main()
