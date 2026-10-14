#!/usr/bin/env python3
"""Trust-anchor, unindexed-file and live-source absence controls on real candidate."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('pack',type=Path);p.add_argument('--scratch',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True);a=p.parse_args();a.scratch.mkdir(parents=True,exist_ok=False);a.evidence.mkdir(parents=True,exist_ok=False)
tools=Path(__file__).resolve().parent;original=hashlib.sha256((a.pack/'manifest.json').read_bytes()).hexdigest();rows=[]

def run(name,checker,pack,red,flags=(),message=None):
    argv=[sys.executable,'-B',str(checker),str(pack),*flags];r=subprocess.run(argv,capture_output=True);(a.evidence/(name+'.stdout.json')).write_bytes(r.stdout);(a.evidence/(name+'.stderr.log')).write_bytes(r.stderr);d=json.loads(r.stdout);ok=r.returncode==(1 if red else 0) and (message is None or message in r.stdout.decode());rows.append({'name':name,'argv':argv,'exit_code':r.returncode,'expected':'red' if red else 'green','expected_message':message,'passed':ok,'stdout_sha256':hashlib.sha256(r.stdout).hexdigest()});assert ok,(name,d)

copy=a.scratch/'extra-file';shutil.copytree(a.pack,copy);(copy/'UNINDEXED-LICENSE.txt').write_text('CONTROL unindexed text\n');run('unindexed-file-red',tools/'check.py',copy,True,message='independent indexed file inventory differs');(copy/'UNINDEXED-LICENSE.txt').unlink();run('unindexed-file-restored-green',tools/'check.py',copy,False);shutil.rmtree(copy)
bundle=a.scratch/'checker-bundle';bundle.mkdir();(bundle/'anchors').mkdir()
for f in ['collect.py','check.py','cohort.py']:shutil.copyfile(tools/f,bundle/f)
anchor=(tools/'anchors/cohort-v1-manifest.json').read_bytes();(bundle/'anchors/cohort-v1-manifest.json').write_bytes(anchor+b'\n');run('tampered-independent-anchor-red',bundle/'check.py',a.pack,True,message='independent cohort anchor hash mismatch');(bundle/'anchors/cohort-v1-manifest.json').write_bytes(anchor);run('tampered-independent-anchor-restored-green',bundle/'check.py',a.pack,False);shutil.rmtree(bundle)
empty=a.scratch/'empty-source-root';empty.mkdir();run('missing-live-sources-red',tools/'check.py',a.pack,True,['--source-root',str(empty.resolve())],message='live source path/hash differs');run('actual-live-sources-restored-green',tools/'check.py',a.pack,False,['--source-root',str(a.source_root.resolve())]);empty.rmdir()
assert hashlib.sha256((a.pack/'manifest.json').read_bytes()).hexdigest()==original
report={'status':'VERIFIED','controls':rows,'runs':len(rows),'all_passed':all(x['passed'] for x in rows),'candidate_manifest_sha256':original,'temporary_copy_and_checker_bundle_removed':True};(a.evidence/'controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='controls'}))
