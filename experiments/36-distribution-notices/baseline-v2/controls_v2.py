#!/usr/bin/env python3
"""Actual-copy controls for accepted R2 findings and broader invariant families."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('pack',type=Path);p.add_argument('--scratch',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);a=p.parse_args()
a.scratch.mkdir(parents=True,exist_ok=False);a.evidence.mkdir(parents=True,exist_ok=False)
check=Path(__file__).with_name('check.py').resolve();original=(a.pack/'manifest.json').read_bytes();results=[]

def run(name,pack,red=False,flags=()):
    c=[sys.executable,'-B',str(check),str(pack),*flags];r=subprocess.run(c,capture_output=True)
    (a.evidence/(name+'.stdout.json')).write_bytes(r.stdout);(a.evidence/(name+'.stderr.log')).write_bytes(r.stderr)
    data=json.loads(r.stdout);ok=r.returncode==(1 if red else 0) and data['status']==('FAIL' if red else 'VERIFIED-INTEGRITY/PARTIAL-COVERAGE') and (bool(data.get('errors')) if red else not data['errors'])
    results.append({'name':name,'argv':c,'exit_code':r.returncode,'expected':'red' if red else 'green','passed':ok,'stdout_sha256':hashlib.sha256(r.stdout).hexdigest()})
    if not ok:raise SystemExit('unexpected control result '+name)

def transform(name,m):
    if name=='empty-source-comparisons':m['source_comparisons']=[]
    elif name=='false-source-hashes':m['source_comparisons'][0].update(current_sha256='0'*64,retained_sha256='0'*64)
    elif name=='false-notice-source-path':m['files']['texts/packages/craft-ui@0.1.0/NOTICE']['source']['relative_path']='WRONG-NOTICE'
    elif name=='drop-font-inventory':m['embedded_default_font_candidates']=[]
    elif name=='drop-distinct-asset-inventory':m['assets']=[]
    elif name=='drop-sdk-signing-system-gaps':m['gaps']=[g for g in m['gaps'] if g['kind'] in {'missing-license-text','first-party-owner-license-decision'}]
    elif name=='claim-first-party-license-chosen':m['root_first_party_license']='MIT; owner approved'
    elif name=='changed-required-source-path':m['source_comparisons'][0]['path']='crates/WRONG.rs'
    elif name=='duplicate-source-comparison':m['source_comparisons'][0]=m['source_comparisons'][1]
    elif name=='changed-observed-source-hash':m['source_comparisons'][0]['current_sha256']='0'*64
    elif name=='changed-notice-origin-manifest-hash':m['files']['texts/packages/craft-ui@0.1.0/NOTICE']['source']['manifest_sha256']='0'*64
    elif name=='changed-package-origin':m['packages']['craft-ui@0.1.0']['origin']['source']='registry+WRONG'
    elif name=='changed-package-repository':m['packages']['craft-ui@0.1.0']['repository']='https://github.com/WRONG/WRONG'
    elif name=='changed-package-authors':m['packages']['craft-ui@0.1.0']['authors']=['OWNER APPROVED']
    elif name=='erased-copyright-lines':m['packages']['craft-ui@0.1.0']['copyright_lines_in_collected_texts']=[]
    elif name=='changed-supplement-url':m['packages']['egui@0.36.2']['supplement_receipts'][0]['url']='https://raw.githubusercontent.com/emilk/egui/main/LICENSE-MIT'
    elif name=='dropped-supplement-record':m['packages']['egui@0.36.2']['supplement_receipts']=[]
    elif name=='promoted-notice-only-text':
        q=m['packages']['objc2-app-kit@0.3.2'];q['license_text_candidate_files']=list(q['notice_files']);q['text_coverage']='candidate-texts-found-needs-applicability-review'
    elif name=='changed-asset-payload-hash':m['assets'][0]['asset_hashes']['assets/fixtures/nvwa-humanoid.glb']='0'*64
    elif name=='changed-asset-license':m['assets'][0]['license_expression']='MIT'
    elif name=='changed-asset-notice-reference':m['assets'][0]['notice_files'][0]='texts/assets/assets/fonts/OFL.txt'
    elif name=='changed-default-font-payload-hash':m['embedded_default_font_candidates'][0]['sha256']='0'*64
    elif name=='changed-default-font-notice-reference':m['embedded_default_font_candidates'][0]['notice_files']=[]
    elif name=='dropped-legacy-gap':m['gaps']=[g for g in m['gaps'] if g['kind']!='legacy-license-expression']
    elif name=='changed-required-gap-record':next(g for g in m['gaps'] if g['kind']=='missing-license-text')['package']='WRONG@0.0'
    elif name=='changed-target-resolver-count':m['targets']['aarch64-apple-darwin']['resolver_workspace_packages']=0
    elif name=='changed-target-command':m['targets']['aarch64-apple-darwin']['commands'][0].append('--all-features')
    elif name=='changed-inventory-byte-count':m['files']['inputs/epaint-default-fonts-lib.rs']['bytes']=0
    elif name=='dropped-unreferenced-indexed-input':m['files'].pop('inputs/scripts/package-native.py')
    elif name=='added-unknown-schema-field':m['release_approved']=True
    elif name not in {'self-consistent-altered-retained-input','self-consistent-altered-package-anchor'}:raise ValueError(name)

names=['empty-source-comparisons','false-source-hashes','false-notice-source-path','drop-font-inventory','drop-distinct-asset-inventory','drop-sdk-signing-system-gaps','claim-first-party-license-chosen','changed-required-source-path','duplicate-source-comparison','changed-observed-source-hash','changed-notice-origin-manifest-hash','changed-package-origin','changed-package-repository','changed-package-authors','erased-copyright-lines','changed-supplement-url','dropped-supplement-record','promoted-notice-only-text','changed-asset-payload-hash','changed-asset-license','changed-asset-notice-reference','changed-default-font-payload-hash','changed-default-font-notice-reference','dropped-legacy-gap','changed-required-gap-record','changed-target-resolver-count','changed-target-command','changed-inventory-byte-count','dropped-unreferenced-indexed-input','added-unknown-schema-field','self-consistent-altered-retained-input','self-consistent-altered-package-anchor']
run('baseline-green',a.pack)
for name in names:
    copy=a.scratch/name;shutil.copytree(a.pack,copy);m=json.loads((copy/'manifest.json').read_text());transform(name,m)
    if name.startswith('self-consistent-altered-'):
        f='inputs/retained-build/build-inputs-after-lint-fix.json' if name.endswith('retained-input') else 'inputs/package-metadata.json';path=copy/f;d=json.loads(path.read_text())
        if name.endswith('retained-input'):
            key=m['source_comparisons'][0]['path'];d[key]['sha256']='0'*64;m['source_comparisons'][0].update(current_sha256='0'*64,retained_sha256='0'*64)
        else:
            d['nvwa-core@0.1.0']['license_expression']='MIT';m['packages']['nvwa-core@0.1.0']['license_expression']='MIT';m['packages']['nvwa-core@0.1.0']['expression_status']='declared-expression-not-legally-adjudicated';m['gaps']=[g for g in m['gaps'] if not (g['kind']=='first-party-owner-license-decision' and g['package']=='nvwa-core@0.1.0')]
        path.write_text(json.dumps(d,indent=2)+'\n');m['files'][f].update(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)
    (copy/'manifest.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n');run(name+'-red',copy,True)
    shutil.rmtree(copy);run(name+'-restored-green',a.pack)
run('completeness-blocked-red',a.pack,True,['--require-complete'])
assert (a.pack/'manifest.json').read_bytes()==original
summary={'status':'VERIFIED','mutations':len(names),'runs':len(results),'all_passed':all(x['passed'] for x in results),'original_candidate_sha256':hashlib.sha256(original).hexdigest(),'candidate_bytes_unchanged':True,'temporary_mutation_copies_removed':True,'controls':results}
(a.evidence/'controls.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='controls'}))
