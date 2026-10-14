#!/usr/bin/env python3
"""Read-only Cargo/cache audit. Writes only the explicitly supplied experiment output."""
import argparse, hashlib, json, re, shutil, subprocess
from pathlib import Path
from notice_types import classify_document, select_documents, CLASSIFICATION_VERSION

TARGETS = {'native': 'aarch64-apple-darwin', 'web': 'wasm32-unknown-unknown'}
EXPECTED = {'Cargo.lock': '457f603a78c6822b6dec754978c425ed6b61d4ed3acd0b856e606e180f5c4e73',
 'dist/Nvwa.app/Contents/MacOS/Nvwa': '72d3df8cfdeea062282c8731b0a95cb971f90976fe881772f3e3c24afe76973a',
 'dist/web/nvwa_studio_bg.wasm': 'd890dfee73e9eeeee6ce3d82f255c79979e8c8b6bed90243c6101f8e1c1763a8'}
TOKENS = {'MIT','Apache-2.0','OFL-1.1','Ubuntu-font-1.0','Unicode-3.0','0BSD','BSD-2-Clause','BSD-3-Clause','CC0-1.0','MIT-0','Zlib','ISC','Unlicense','GPL-2.0-only','LLVM-exception','AND','OR','WITH'}

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,data): path.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
def package_key(p): return p['name']+'@'+p['version']
def parse_tree(text):
    result={}
    for line in text.splitlines():
        if not line.strip():continue
        line=line.removesuffix(' (*)')
        m=re.match(r'^([^ ]+) v([^ |]+)([^|]*)\|(.*)$',line)
        if not m: raise ValueError('unrecognized cargo-tree row: '+line)
        key=m[1]+'@'+m[2]; result.setdefault(key,set()).update(x for x in m[4].split(',') if x and x!=' (*)')
    return {k:sorted(v) for k,v in sorted(result.items())}
def expression_status(value):
    if value is None:return 'UNKNOWN'
    # Preserve historical Cargo slash syntax exactly; do not silently select OR branches.
    tokens=re.findall(r'[A-Za-z0-9.+-]+',value)
    if not tokens or set(tokens)-TOKENS or re.sub(r'[A-Za-z0-9.+-]+|[()/\s]','',value):raise ValueError('unknown license expression: '+value)
    parts=re.findall(r'[A-Za-z0-9.+-]+|[()/]',value);position=0
    def primary():
        nonlocal position
        if position>=len(parts):raise ValueError('malformed license expression: '+value)
        token=parts[position];position+=1
        if token=='(':
            expression()
            if position>=len(parts) or parts[position]!=')':raise ValueError('malformed license expression: '+value)
            position+=1
        elif token not in TOKENS-{'AND','OR','WITH','LLVM-exception'}:raise ValueError('malformed license expression: '+value)
        if position<len(parts) and parts[position]=='WITH':
            position+=1
            if position>=len(parts) or parts[position]!='LLVM-exception':raise ValueError('malformed license expression: '+value)
            position+=1
    def expression():
        nonlocal position
        primary()
        while position<len(parts) and parts[position] in {'AND','OR','/'}:
            position+=1;primary()
    expression()
    if position!=len(parts):raise ValueError('malformed license expression: '+value)
    return 'legacy-slash-needs-review' if '/' in value else 'declared-expression-not-legally-adjudicated'
def text_files(root):
    return sorted(p for p in root.rglob('*') if p.is_file() and not any(x in {'.git','target'} for x in p.relative_to(root).parts) and (re.match(r'^(license|licence|copying|copyright|notice|authors|attribution)([._-]|$)',p.name,re.I) or 'license' in p.name.lower()))
def collect(root,output,scratch,supplements_path=None,prepare_unreviewed=False):
    output.mkdir(parents=True,exist_ok=False); (output/'texts').mkdir(); (output/'inputs').mkdir(); scratch.mkdir(parents=True,exist_ok=True)
    files={}; pkgs={}; targets={}; raw={}
    supplements=json.loads(supplements_path.read_text()) if supplements_path else []
    def copy(source,destination,provenance):
        path=output/destination;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,path)
        entry={'path':destination,'sha256':digest(path),'bytes':path.stat().st_size,'source':provenance};files[destination]=entry;return destination
    for label,triple in TARGETS.items():
        commands=[['cargo','metadata','--locked','--offline','--format-version','1','--filter-platform',triple],['cargo','tree','--locked','--offline','-p','nvwa-studio','--target',triple,'--edges','normal,build','--prefix','none','--format','{p}|{f}'],['cargo','tree','--locked','--offline','-p','nvwa-studio','--target',triple,'--edges','normal,no-proc-macro','--prefix','none','--format','{p}|{f}']]
        results=[subprocess.run(cmd,cwd=root,check=True,capture_output=True).stdout for cmd in commands]
        for name,data in zip(['metadata.json','tree.txt','runtime-tree.txt'],results):
            (scratch/(label+'-'+name)).write_bytes(data)
            if name!='metadata.json':copy(scratch/(label+'-'+name),'inputs/'+label+'-'+name,{'kind':'selected-target-cargo-tree','argv':commands[1 if name=='tree.txt' else 2]})
        metadata=json.loads(results[0]); raw[label]=metadata; trees=[parse_tree(x.decode()) for x in results[1:]]
        lookup={package_key(p):p for p in metadata['packages']}
        targets[triple]={'label':label,'root':'nvwa-studio@0.1.0','commands':commands,'resolver_workspace_packages':len(lookup),'normal_build_packages':sorted(trees[0]),'normal_without_proc_macro_packages':sorted(trees[1]),'features_by_package':trees[0],'scope':'selected target normal+build resolver input superset; no exact linked-membership claim'}
        for key in trees[0]:
            p=lookup[key]
            if key in pkgs:
                if pkgs[key]['license_expression']!=p['license']:raise ValueError('license differs across targets')
                continue
            srcroot=Path(p['manifest_path']).parent;licensefiles=text_files(srcroot)
            if p['name']=='craft-ui':licensefiles=text_files(srcroot.parent.parent)
            if p['name']=='epaint_default_fonts':licensefiles=sorted(set(licensefiles)|{srcroot/'fonts'/n for n in ['Hack-Regular.txt','OFL.txt','UFL.txt','emoji-icon-font-mit-license.txt']})
            origin={'source':p['source'],'manifest_path':str(srcroot/'Cargo.toml'),'manifest_sha256':digest(srcroot/'Cargo.toml')}
            vcs=srcroot/'.cargo_vcs_info.json'
            if vcs.is_file():origin['cargo_vcs_info']=json.loads(vcs.read_text())
            manifest=copy(srcroot/'Cargo.toml','inputs/manifests/'+key+'/Cargo.toml',origin)
            copied=[];notice_documents={}
            included_documents,excluded_documents=select_documents(licensefiles)
            licensefiles=[f for f,r in included_documents]
            base=srcroot.parent.parent if p['name']=='craft-ui' else srcroot
            for f,classification in included_documents:
                dest=copy(f,'texts/packages/'+key+'/'+str(f.relative_to(base)),{'kind':'exact-local-pinned-source','package':key,'relative_path':str(f.relative_to(base)),**origin});copied.append(dest);notice_documents[dest]=classification
            excluded_records=[{'relative_path':str(f.relative_to(base)),'source_path':str(f),'classification':r,'origin':origin} for f,r in excluded_documents]
            license_candidates=[path for path in copied if notice_documents[path]['full_license_text_candidate']];supplement_receipts=[]
            package_repo=(p['repository'] or '').split('/tree/')[0]
            package_commit=origin.get('cargo_vcs_info',{}).get('git',{}).get('sha1')
            for extra in supplements:
                if extra['repository']!=package_repo or extra['commit']!=package_commit:continue
                source=Path(extra['file'])
                if digest(source)!=extra['sha256']:raise ValueError('supplement hash mismatch')
                if extra['kind']=='pinned-public-primary-exact-bytes' and extra['url']!='https://raw.githubusercontent.com/'+package_repo.removeprefix('https://github.com/')+'/'+package_commit+'/'+extra['path']:raise ValueError('unpinned supplement URL')
                dest=copy(source,'texts/packages/'+key+'/upstream-root/'+extra['path'],extra);copied.append(dest);supplement_receipts.append(extra)
                notice_documents[dest]=classify_document(source,source.read_bytes())
                if notice_documents[dest]['full_license_text_candidate']:license_candidates.append(dest)
            copyrights=[]
            for f in licensefiles:
                for line in f.read_text(errors='replace').splitlines():
                    if re.search(r'copyright|©',line,re.I):copyrights.append({'source':str(f.relative_to(base)),'line':line})
            for extra in supplement_receipts:
                for line in Path(extra['file']).read_text(errors='replace').splitlines():
                    if re.search(r'copyright|©',line,re.I):copyrights.append({'source':'upstream-root/'+extra['path'],'line':line})
            pkgs[key]={'name':p['name'],'version':p['version'],'package_id':p['id'],'license_expression':p['license'],'expression_status':expression_status(p['license']),'license_file_metadata':p['license_file'],'authors':p['authors'],'repository':p['repository'],'source':p['source'],'manifest':manifest,'origin':origin,'notice_files':copied,'notice_documents':notice_documents,'excluded_source_documents':excluded_records,'license_text_candidate_files':license_candidates,'supplement_receipts':supplement_receipts,'copyright_lines_in_collected_texts':copyrights,'text_coverage':'candidate-texts-found-needs-applicability-review' if license_candidates else 'notice-only-license-text-MISSING' if copied else 'MISSING'}
    native_build_argv=['cargo','tree','--locked','--offline','-p','nvwa-studio','-p','nvwa-cli','--target',TARGETS['native'],'--edges','normal,build','--prefix','none','--format','{p}|{f}']
    native_actual_tree=subprocess.run(native_build_argv,cwd=root,check=True,capture_output=True).stdout
    (scratch/'native-production-command-tree.txt').write_bytes(native_actual_tree)
    copy(scratch/'native-production-command-tree.txt','inputs/native-production-command-tree.txt',{'kind':'retained-build-command-root-feature-comparison','argv':native_build_argv})
    actual_features=parse_tree(native_actual_tree.decode())
    selected_features=targets[TARGETS['native']]['features_by_package']
    differences=[k for k in selected_features if actual_features.get(k)!=selected_features[k]]
    if differences:raise ValueError('native production command feature cohort differs: '+str(differences))
    targets[TARGETS['native']]['production_command_feature_comparison']={'roots':['nvwa-studio@0.1.0','nvwa-cli@0.1.0'],'selected_studio_feature_differences':differences,'extra_build_root_packages':sorted(set(actual_features)-set(selected_features))}
    identity={}
    for name,expected in EXPECTED.items():
        got=digest(root/name)
        if got!=expected:raise ValueError('frozen cohort hash mismatch '+name)
        identity[name]={'sha256':got,'bytes':(root/name).stat().st_size}
    identity['dist/web/nvwa_studio.js']={'sha256':digest(root/'dist/web/nvwa_studio.js'),'bytes':(root/'dist/web/nvwa_studio.js').stat().st_size}
    snapshot=json.loads((root/'.work/m11-final/build-inputs-after-lint-fix.json').read_text()); comparisons=[]
    for name,record in snapshot.items():
        if name.startswith(('crates/','assets/','web/','scripts/','examples/','licenses/')) or name in {'Cargo.toml','Cargo.lock','rust-toolchain.toml'}:
            comparisons.append({'path':name,'retained_sha256':record['sha256'],'current_sha256':digest(root/name),'equal':record['sha256']==digest(root/name)})
    if any(not x['equal'] for x in comparisons):raise ValueError('production source cohort changed')
    asset_specs=[('original-fixture','CC0-1.0',['assets/fixtures/LICENSE.txt','assets/fixtures/provenance-manifest.json'],['assets/fixtures/nvwa-humanoid.glb']),('nvwa-sans-derivative','OFL-1.1',['assets/fonts/OFL.txt','assets/fonts/NOTICE.md','assets/fonts/PROVENANCE.json'],['assets/fonts/NvwaSansSC-Regular.ttf']),('craft-ui-existing-packaged-notice','MIT',['licenses/craft-ui/LICENSE-MIT.txt'],[])]
    assets=[]
    for name,license_expr,notices,binaries in asset_specs:
        assets.append({'id':name,'license_expression':license_expr,'notice_files':[copy(root/f,'texts/assets/'+f,{'kind':'repository-original-bytes','path':f}) for f in notices],'asset_hashes':{f:digest(root/f) for f in binaries}})
    fontroot=Path(next(p['manifest_path'] for p in raw['native']['packages'] if p['name']=='epaint_default_fonts')).parent
    font_notices={'Hack-Regular.ttf':['Hack-Regular.txt'],'NotoEmoji-Regular.ttf':['OFL.txt'],'Ubuntu-Light.ttf':['UFL.txt'],'emoji-icon-font.ttf':['emoji-icon-font-mit-license.txt']}
    fonts=[{'name':n,'sha256':digest(fontroot/'fonts'/n),'bytes':(fontroot/'fonts'/n).stat().st_size,'source':'epaint_default_fonts@0.36.2/fonts/'+n,'notice_files':['texts/packages/epaint_default_fonts@0.36.2/fonts/'+s for s in ns],'coverage':'include_bytes declared by pinned source; final linker retention not independently established'} for n,ns in font_notices.items()]
    copy(fontroot/'src/lib.rs','inputs/epaint-default-fonts-lib.rs',{'kind':'pinned-subasset-embedding-source'})
    copy(root/'Cargo.lock','inputs/Cargo.lock',{'kind':'frozen-lockfile'})
    for f in ['scripts/build-web.sh','scripts/package-native.py','.work/m11-final/artifact-identities.json','.work/m11-final/build-inputs-after-lint-fix.json','.work/m11-final/native-release/result.json','.work/m11-final/web-release/result.json']:
        copy(root/f,'inputs/'+f.replace('.work/m11-final/','retained-build/'),{'kind':'retained-production-evidence','path':f})
    save(output/'inputs/package-metadata.json',{k:{'package_id':v['package_id'],'license_expression':v['license_expression'],'authors':v['authors'],'notice_files':v['notice_files'],'license_text_candidate_files':v['license_text_candidate_files'],'notice_documents':v['notice_documents'],'excluded_source_documents':v['excluded_source_documents']} for k,v in pkgs.items()})
    files['inputs/package-metadata.json']={'path':'inputs/package-metadata.json','sha256':digest(output/'inputs/package-metadata.json'),'bytes':(output/'inputs/package-metadata.json').stat().st_size,'source':{'kind':'target-filtered-cargo-metadata-extracted-no-license-normalization'}}
    gaps=[{'kind':'missing-license-text','package':k} for k,v in sorted(pkgs.items()) if not v['license_text_candidate_files']]
    gaps += [{'kind':'first-party-owner-license-decision','package':k} for k,v in sorted(pkgs.items()) if v['license_expression'] is None]
    gaps += [{'kind':'legacy-license-expression','package':k,'expression':v['license_expression']} for k,v in sorted(pkgs.items()) if v['expression_status'].startswith('legacy')]
    if not pkgs['epaint_default_fonts@0.36.2']['supplement_receipts']:gaps += [{'kind':'missing-Rust-code-license-text','package':'epaint_default_fonts@0.36.2','detail':'Local crate has font subasset notices, but no shared egui MIT/Apache code license files.'}]
    if supplements_path:
        copy(supplements_path,'inputs/supplements.json',{'kind':'exact-source-receipts'})
        if (supplements_path.parent/'requests.json').is_file():copy(supplements_path.parent/'requests.json','inputs/primary-requests.json',{'kind':'bounded-public-retrieval-success-and-failure-log'})
    gaps += [{'kind':'objc2-pinned-root-notice-SDK-provenance-implications-unresolved'}] if any(x['coverage']=='notice-only' for x in supplements) else []
    gaps += [{'kind':x} for x in ['applicable-text-and-copyright-header-review-incomplete','rust-stdlib-compiler-builtins-not-in-cargo-metadata','native-system-frameworks-and-dynamic-link-inventory-not-audited','wasm-bindgen-generated-javascript-runtime-license-not-separately-audited','CC0-repository-statement-is-not-full-legal-instrument','no-model-weights-or-vam-imports-source-scope-only','signing-notarization-clean-machine-public-distribution-NOT-RUN']]
    audit={k:{'notice_documents':v['notice_documents'],'excluded_source_documents':v['excluded_source_documents'],'full_text_candidate_files':v['license_text_candidate_files'],'text_coverage':v['text_coverage']} for k,v in pkgs.items()}
    save(output/'inputs/document-audit.json',audit)
    files['inputs/document-audit.json']={'path':'inputs/document-audit.json','sha256':digest(output/'inputs/document-audit.json'),'bytes':(output/'inputs/document-audit.json').stat().st_size,'source':{'kind':'production-called-content-classification','version':CLASSIFICATION_VERSION,'legal_approval':'NOT-RUN'}}
    manifest={'schema':1,'audit_revision':3,'document_classification_version':CLASSIFICATION_VERSION,'review_status':'PENDING independent Astra R2 for corrected capture','cohort_commit':'7851c2e74f757f93774f2d5fa05151562c393012','issue':'https://github.com/Derek-X-Wang/nvwa/issues/10','identity':identity,'source_comparisons':comparisons,'targets':targets,'packages':pkgs,'assets':assets,'embedded_default_font_candidates':fonts,'files':files,'gaps':gaps,'redistribution_completeness':'BLOCKED','legal_approval':'NOT-RUN','root_first_party_license':'UNKNOWN; no root LICENSE; no license selected or assigned','models':'Separate optional model research licenses remain experiments/05-ai-motion; no weights/runtime bundled; no VaM assets imported'}
    from cohort import frozen
    if any(p.is_file() for p in root.iterdir() if p.name.upper().startswith(('LICENSE','COPYING'))):raise ValueError('root first-party license no longer UNKNOWN; explicit new owner audit required')
    if not prepare_unreviewed and manifest!=frozen():raise ValueError('capture differs from independent frozen production cohort; explicit new audit required')
    save(output/'manifest.json',manifest)
    print(json.dumps({'output':str(output),'manifest_sha256':digest(output/'manifest.json'),'packages':len(pkgs),'files':len(files),'gaps':len(gaps),'target_counts':{k:len(v['normal_build_packages']) for k,v in targets.items()}}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--scratch',type=Path,required=True);parser.add_argument('--supplements',type=Path);parser.add_argument('--prepare-unreviewed-cohort',action='store_true');a=parser.parse_args();collect(a.root.resolve(),a.output.resolve(),a.scratch.resolve(),a.supplements.resolve() if a.supplements else None,a.prepare_unreviewed_cohort)
