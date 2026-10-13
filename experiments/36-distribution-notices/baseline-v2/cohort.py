"""Version-2 audit invariants for the independently reviewed, frozen v1 cohort.

The trust root is this checker code and the external SHA-pinned original record,
not any path/hash supplied by the candidate manifest. This is not a signature.
"""
import hashlib, json, re, tomllib
from pathlib import Path

COHORT_SHA256 = 'ab92b4816b18191e0d24d063e43a9e183cd3204114a4321da5d478455a403bf2'
TOOLING_VERSION = 2


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def frozen():
    path=Path(__file__).with_name('anchors')/'cohort-v1-manifest.json'
    if sha(path)!=COHORT_SHA256:raise ValueError('independent cohort anchor hash mismatch')
    return json.loads(path.read_text())
def production_source(name):
    return name.startswith(('crates/','assets/','web/','scripts/','examples/','licenses/')) or name in {'Cargo.toml','Cargo.lock','rust-toolchain.toml'}


def semantic_errors(pack,m,source_root=None):
    anchor=frozen();errors=[]
    def need(ok,message):
        if not ok:errors.append(message)
    need(set(m)==set(anchor),'frozen schema fields missing or unexpected')
    for field,expected in anchor.items():
        need(m.get(field)==expected,'independent frozen cohort field differs: '+field)
    # Reject changed record schema before following any untrusted source paths.
    # Further joins operate only after all captured facts match the independent
    # anchor; actual copied bytes are still checked independently below.
    if errors:return errors
    # Hash and inventory trust comes from the external anchor, not m['files'].
    expected_files=anchor['files']
    actual_paths={str(p.relative_to(pack)) for p in pack.rglob('*') if p.is_file()}
    need(actual_paths==set(expected_files)|{'manifest.json'},'independent indexed file inventory differs')
    for name,entry in expected_files.items():
        path=pack/name
        need(path.is_file() and not path.is_symlink(),'missing independent indexed file: '+name)
        if path.is_file():
            need(sha(path)==entry['sha256'],'independent indexed hash mismatch: '+name)
            need(path.stat().st_size==entry['bytes'],'independent indexed byte count mismatch: '+name)
    # Required path set and hashes are derived from the retained build record.
    retained=json.loads((pack/'inputs/retained-build/build-inputs-after-lint-fix.json').read_text())
    required={name:record['sha256'] for name,record in retained.items() if production_source(name)}
    observed=m['source_comparisons']
    need(len(observed)==len(required) and len({x['path'] for x in observed})==len(required),'required source comparisons absent or duplicated')
    need({x['path'] for x in observed}==set(required),'required source path set differs from retained build inputs')
    for x in observed:
        expected=required.get(x['path'])
        need(expected is not None and x=={'path':x['path'],'retained_sha256':expected,'current_sha256':expected,'equal':True},'source path/hash comparison differs from retained input: '+x['path'])
    if source_root is not None:
        for name,expected in required.items():
            path=source_root/name
            need(path.is_file() and sha(path)==expected,'live source path/hash differs: '+name)
        need(not any(p.is_file() for p in source_root.iterdir() if p.name.upper().startswith(('LICENSE','COPYING'))),'root first-party license no longer UNKNOWN: explicit owner review required')
    supplements=json.loads((pack/'inputs/supplements.json').read_text())
    requests=json.loads((pack/'inputs/primary-requests.json').read_text())
    by_url={x['url']:x for x in requests}
    for key,p in m['packages'].items():
        manifest_path=pack/p['manifest'];origin=p['origin']
        need(p['manifest']=='inputs/manifests/'+key+'/Cargo.toml','package manifest path join differs: '+key)
        need(sha(manifest_path)==origin['manifest_sha256'],'package origin manifest hash differs: '+key)
        need(origin['source']==p['source'],'package origin source differs: '+key)
        need(m['files'][p['manifest']]['source']==origin,'indexed manifest provenance differs: '+key)
        parsed=tomllib.loads(manifest_path.read_text())['package']
        need(parsed['name']==p['name'],'package manifest name differs: '+key)
        if isinstance(parsed.get('version'),str):need(parsed['version']==p['version'],'package manifest version differs: '+key)
        if isinstance(parsed.get('license'),str):need(parsed['license']==p['license_expression'],'package manifest expression differs: '+key)
        if p['license_expression'] is None:need('license' not in parsed,'first-party manifest unknown was erased: '+key)
        repo=(p['repository'] or '').split('/tree/')[0]
        commit=origin.get('cargo_vcs_info',{}).get('git',{}).get('sha1')
        expected_supplements=[x for x in supplements if x['repository']==repo and x['commit']==commit]
        need(p['supplement_receipts']==expected_supplements,'package supplement join differs: '+key)
        copyright_lines=[];local=[];supplement_files=[];license_candidates=[]
        for path in p['notice_files']:
            entry=m['files'][path];source=entry['source'];prefix='texts/packages/'+key+'/'
            need(path.startswith(prefix),'notice package path differs: '+key)
            relative=path.removeprefix(prefix)
            if relative.startswith('upstream-root/'):
                receipt=next((x for x in expected_supplements if x['path']==relative.removeprefix('upstream-root/')),None)
                need(receipt is not None and source==receipt,'notice supplement source path/hash join differs: '+path)
                if receipt is None:continue
                need(entry['sha256']==receipt['sha256'],'notice supplemental hash differs: '+path)
                supplement_files.append(path)
                if receipt['coverage']=='license-text-candidate':license_candidates.append(path)
                if receipt['kind']=='pinned-public-primary-exact-bytes':
                    url='https://raw.githubusercontent.com/'+repo.removeprefix('https://github.com/')+'/'+commit+'/'+receipt['path']
                    record=by_url.get(url,{})
                    need(receipt['url']==url and record.get('http_status')==200 and record.get('sha256')==entry['sha256'] and record.get('bytes')==entry['bytes'],'pinned public request receipt join differs: '+path)
                else:
                    donors=[v for v in m['packages'].values() if (v['repository'] or '').split('/tree/')[0]==repo and v['origin'].get('cargo_vcs_info',{}).get('git',{}).get('sha1')==commit and v['origin']['manifest_path']==str(Path(receipt['file']).parent/'Cargo.toml')]
                    need(bool(donors),'local sibling source manifest/commit join absent: '+path)
                    need(any(m['files'][f]['sha256']==entry['sha256'] for d in donors for f in d['notice_files'] if not '/upstream-root/' in f and f.endswith('/'+receipt['path'])),'local sibling original notice hash join differs: '+path)
            else:
                expected_source={'kind':'exact-local-pinned-source','package':key,'relative_path':relative,**origin}
                need(source==expected_source,'notice source path/hash join differs: '+path)
                local.append(path);license_candidates.append(path)
            for line in (pack/path).read_text(errors='replace').splitlines():
                if re.search(r'copyright|©',line,re.I):copyright_lines.append({'source':relative,'line':line})
        need(supplement_files==[prefix+'upstream-root/'+r['path'] for r in expected_supplements],'required supplemental notice inventory differs: '+key)
        need(p['license_text_candidate_files']==license_candidates,'notice-only/full-text candidate distinction differs: '+key)
        need(p['copyright_lines_in_collected_texts']==copyright_lines,'collected copyright lines differ: '+key)
        coverage='candidate-texts-found-needs-applicability-review' if license_candidates else 'notice-only-license-text-MISSING' if p['notice_files'] else 'MISSING'
        need(p['text_coverage']==coverage,'unknown text coverage changed: '+key)
    # Fixed distinct assets and font payload records are indexed by the external
    # reviewed anchor; provenance files independently join their declared hashes.
    need(m['assets']==anchor['assets'],'required distinct asset inventory differs')
    need(m['embedded_default_font_candidates']==anchor['embedded_default_font_candidates'],'required default-font payload/notice inventory differs')
    for asset in m['assets']:
        for name in asset['notice_files']:
            src=name.removeprefix('texts/assets/')
            need(m['files'][name]['source']=={'kind':'repository-original-bytes','path':src},'asset notice source path differs: '+name)
        for src,value in asset['asset_hashes'].items():need(required.get(src)==value,'asset payload hash differs from retained build input: '+src)
    font_provenance=json.loads((pack/'texts/assets/assets/fonts/PROVENANCE.json').read_text())
    font_asset=next(x for x in m['assets'] if x['id']=='nvwa-sans-derivative')
    need(font_provenance['sha256']==font_asset['asset_hashes']['assets/fonts/NvwaSansSC-Regular.ttf'],'derivative font payload/provenance join differs')
    need(font_provenance['license_sha256']==m['files']['texts/assets/assets/fonts/OFL.txt']['sha256'],'derivative font OFL provenance hash differs')
    fixture=json.loads((pack/'texts/assets/assets/fixtures/provenance-manifest.json').read_text())
    fixture_hashes={x['path']:x['sha256'] for x in fixture['files']}
    fixture_asset=next(x for x in m['assets'] if x['id']=='original-fixture')
    need(fixture_hashes['assets/fixtures/nvwa-humanoid.glb']==fixture_asset['asset_hashes']['assets/fixtures/nvwa-humanoid.glb'],'original fixture payload/provenance join differs')
    embedding=(pack/'inputs/epaint-default-fonts-lib.rs').read_text()
    for f in m['embedded_default_font_candidates']:
        need('include_bytes!("../fonts/'+f['name']+'")' in embedding,'font payload absent from pinned embedding declaration: '+f['name'])
        need(f['source']=='epaint_default_fonts@0.36.2/fonts/'+f['name'],'font payload source join differs: '+f['name'])
    need(m['gaps']==anchor['gaps'],'required gap records/families differ')
    need(m['root_first_party_license']==anchor['root_first_party_license'],'root first-party owner UNKNOWN not preserved')
    return errors
