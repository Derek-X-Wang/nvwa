#!/usr/bin/env python3
"""Reject tampered copies of real B1 outputs through the actual comparator CLI."""
import copy,json,shutil,subprocess,sys,tempfile
from pathlib import Path
import run
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent.parent
STORE=REPO/'.work/character-approved-20261016';COMMON=STORE/'common-sample.json'
SHA='2e8566a4f12de710ead88f6aa2d71fc44e0680761a4f2fdc48a844b6f3534ab7'
def main():
    source=ROOT/'results/B1-run1'
    originals={p.name:run.digest(p) for p in source.iterdir() if p.is_file()}
    manifest_sha=run.digest(COMMON);records=[]
    with tempfile.TemporaryDirectory(prefix='.control-comparison-',dir=ROOT) as folder:
        temp=Path(folder);clone=temp/'copied-results';shutil.copytree(source,clone)
        summary_path=clone/'summary.json';baseline=json.loads(summary_path.read_text())
        neutral=clone/'neutral.json';neutral_bytes=neutral.read_bytes()
        controls=[('changed-output',None,'execution output SHA256 mismatch'),
                  ('summary-failed-status',lambda j:j.update(status='failed'),'summary status'),
                  ('changed-output-hash',lambda j:j['cases'][0].update(output_sha256='0'*64),'output SHA256 mismatch'),
                  ('missing-case',lambda j:j['cases'].pop(),'incomplete or duplicate cases'),
                  ('nonzero-exit',lambda j:j['cases'][0].update(exit_code=1),'case failed or did not execute'),
                  ('false-execution-flag',lambda j:j['cases'][0].update(actual_candidate_code_executed=False),'case failed or did not execute'),
                  ('wrong-common-manifest',lambda j:j.update(common_manifest_sha256='0'*64),'common manifest mismatch'),
                  ('wrong-variant',lambda j:j.update(variant='B0'),'run variant mismatch'),
                  ('wrong-binary',lambda j:j.update(binary_sha256='0'*64),'binary identity mismatch'),
                  ('wrong-adapter',lambda j:j.update(adapter_source_sha256='0'*64),'adapter identity mismatch')]
        for name,mutate,expected in controls:
            data=copy.deepcopy(baseline)
            if mutate:mutate(data)
            summary_path.write_text(json.dumps(data))
            neutral.write_bytes(neutral_bytes+b' ' if name=='changed-output' else neutral_bytes)
            snapshot={p.name:run.digest(p) for p in clone.iterdir() if p.is_file()}
            output=temp/(name+'.json')
            command=[sys.executable,str(ROOT/'compare.py'),'--variant','B1','--common-manifest',str(COMMON),
                     '--common-manifest-sha256',SHA,'--results',str(clone),'--out',str(output)]
            result=subprocess.run(command,cwd=REPO,capture_output=True,text=True,timeout=20)
            text=result.stdout+result.stderr
            assert result.returncode==2 and expected in text,(name,result.returncode,text)
            assert not output.exists(),name+' emitted a comparison receipt'
            assert snapshot=={p.name:run.digest(p) for p in clone.iterdir() if p.is_file()},name+' altered copied inputs'
            records.append({'name':name,'exit_code':result.returncode,'expected_reason':expected,'output':text,
                            'no_comparison_receipt_created':True,'copied_inputs_preserved':True})
    assert originals=={p.name:run.digest(p) for p in source.iterdir() if p.is_file()}
    assert run.digest(COMMON)==manifest_sha
    receipt={'schema_version':1,'all_passed':True,'controls':len(records),'scope':'Actual CLI comparator on tampered copies of retained real B1 results; original outputs/common manifest unchanged',
             'original_results_preserved':True,'common_manifest_preserved':True,'comparator_sha256':run.digest(ROOT/'compare.py'),'records':records}
    with (ROOT/'evidence/comparison-controls.json').open('x') as stream:json.dump(receipt,stream,indent=2)
    print(str(len(records))+' comparator tamper controls PASS; no rejected receipt created; inputs preserved')
if __name__=='__main__':main()
