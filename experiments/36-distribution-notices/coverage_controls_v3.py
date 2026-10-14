#!/usr/bin/env python3
"""Self-consistent metadata mutations must fail against original document bytes."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('pack',type=Path);p.add_argument('--scratch',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();a.scratch.mkdir(parents=True,exist_ok=False);a.evidence.mkdir(parents=True,exist_ok=False);root=Path(__file__).resolve().parent;rows=[]

def run(name,pack,red,message=None):
 argv=[sys.executable,'-B',str(root/'check.py'),str(pack)];r=subprocess.run(argv,capture_output=True);(a.evidence/(name+'.stdout.json')).write_bytes(r.stdout);(a.evidence/(name+'.stderr.log')).write_bytes(r.stderr);ok=r.returncode==(1 if red else 0) and (message is None or message in r.stdout.decode());rows.append({'name':name,'argv':argv,'exit_code':r.returncode,'expected':'red' if red else 'green','expected_message':message,'passed':ok,'stdout_sha256':hashlib.sha256(r.stdout).hexdigest()});assert ok,(name,r.stdout,r.stderr)

def synchronize(pack,m):
 # Reconcile all mutable mirrors and hashes deliberately; the real bytes and
 # independently recomputed content roles must still reject the false claim.
 meta=json.loads((pack/'inputs/package-metadata.json').read_text());audit=json.loads((pack/'inputs/document-audit.json').read_text())
 for key,p in m['packages'].items():
  for field in ['notice_files','license_text_candidate_files','notice_documents','excluded_source_documents']:meta[key][field]=p[field]
  audit[key]={'notice_documents':p['notice_documents'],'excluded_source_documents':p['excluded_source_documents'],'full_text_candidate_files':p['license_text_candidate_files'],'text_coverage':p['text_coverage']}
 for path,obj in [('inputs/package-metadata.json',meta),('inputs/document-audit.json',audit)]:
  f=pack/path;f.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n');m['files'][path].update(sha256=hashlib.sha256(f.read_bytes()).hexdigest(),bytes=f.stat().st_size)
 (pack/'manifest.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')

cases=[('promote-AUTHORS','linebender_resource_handle@0.1.1','AUTHORS',True),('promote-declaration-LICENSE','typenum@1.20.1','LICENSE',True),('promote-short-Apache-notice','guillotiere@0.7.0','LICENSE-APACHE',True),('promote-craft-NOTICE','craft-ui@0.1.0','NOTICE',True),('promote-ATTRIBUTION','craft-ui@0.1.0','ATTRIBUTION.md',True),('promote-COPYRIGHT','tiff@0.11.3','tests/COPYRIGHT',True),('promote-COPYING-choice','byteorder@1.5.0','COPYING',True),('promote-framework-provenance','objc2-foundation@0.3.2','upstream-root/LICENSE.md',True),('demote-short-0BSD','adler2@2.0.1','LICENSE-0BSD',False),('demote-mixed-license','atomic-waker@1.1.2','LICENSE-THIRD-PARTY',False),('demote-substantive-ATTRIBUTION','glam@0.32.1','ATTRIBUTION.md',False)]
run('baseline-green',a.pack,False)
for name,key,relative,promote in cases:
 copy=a.scratch/name;shutil.copytree(a.pack,copy);m=json.loads((copy/'manifest.json').read_text());p=m['packages'][key];path='texts/packages/'+key+'/'+relative;p['notice_documents'][path]['full_license_text_candidate']=promote;p['notice_documents'][path]['kind']='full-license-text-candidate' if promote else 'license-reference-or-provenance-notice'
 p['license_text_candidate_files']=[f for f in p['notice_files'] if p['notice_documents'][f]['full_license_text_candidate']];p['text_coverage']='candidate-texts-found-needs-applicability-review' if p['license_text_candidate_files'] else 'notice-only-license-text-MISSING' if p['notice_files'] else 'MISSING'
 m['gaps']=[g for g in m['gaps'] if not(g['kind']=='missing-license-text' and g['package']==key)]
 if not p['license_text_candidate_files']:m['gaps'].insert(0,{'kind':'missing-license-text','package':key})
 synchronize(copy,m);run(name+'-self-consistent-red',copy,True,'content-derived document roles differ');shutil.rmtree(copy);run(name+'-restored-green',a.pack,False)
# Restore historical source-code promotion and old missing count consistently.
name='restore-source-code-and-old-missing-count';copy=a.scratch/name;shutil.copytree(a.pack,copy);m=json.loads((copy/'manifest.json').read_text());old=root/'baseline-v2/sample-production-pack';oldm=json.loads((old/'manifest.json').read_text())
for key in ['objc2-foundation@0.2.2','objc2-foundation@0.3.2']:
 p=m['packages'][key]
 for exclusion in p['excluded_source_documents']:
  path='texts/packages/'+key+'/'+exclusion['relative_path'];destination=copy/path;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/path,destination);m['files'][path]=oldm['files'][path];p['notice_files'].append(path);p['notice_documents'][path]={**exclusion['classification'],'kind':'full-license-text-candidate','full_license_text_candidate':True};p['license_text_candidate_files'].append(path)
 p['excluded_source_documents']=[];p['text_coverage']='candidate-texts-found-needs-applicability-review';m['gaps']=[g for g in m['gaps'] if not(g['kind']=='missing-license-text' and g['package']==key)]
synchronize(copy,m);run(name+'-self-consistent-red',copy,True,'content-derived full-text candidate coverage differs');shutil.rmtree(copy);run(name+'-restored-green',a.pack,False)
report={'status':'VERIFIED','runs':len(rows),'mutations':len(cases)+1,'all_passed':all(x['passed'] for x in rows),'controls':rows,'temporary_mutation_copies_removed':True};(a.evidence/'controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='controls'}))
