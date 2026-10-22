"""Immutable capture provenance, separate from any future author/scoring freeze."""
from pathlib import Path
import re
import current19 as c

BUILD_KIND='nvwa85-completed-native-build-v1'
RECEIPTS={'identity':'identity.json','build':'build-receipt.json',
          'source_before':'source-before.json','source_at_run':'source-at-run.json',
          'source_after':'source-after.json','authorization':'capture-authorization.json',
          'geometry':'geometry-audit.json'}
CAPTURE_FILES=('current19.py','geometry_checks.py','provenance.py','capture.py')
EXPERIMENTS=('60-b1-continuous-motion','70-b1-garment-defect','79-shoulder-pose-corrective',
             '81-shoulder-patch-corrective','84-shoulder-rest-refit')


def inventory_digest(rows):
    import json
    return c.digest(json.dumps(rows,sort_keys=True,separators=(',',':'),allow_nan=False).encode())


def file_row(root,path):
    raw=path.read_bytes()
    return {'path':path.relative_to(root).as_posix(),'bytes':len(raw),'sha256':c.digest(raw)}


def rows_for(root,paths):
    rows=[]
    for name in sorted(set(paths)):
        path=c.safe_path(root,name)
        c.need(path.is_file(),'source closure file absent: '+name)
        rows.append(file_row(root,path))
    return rows


def compiled_paths(root=c.ROOT):
    paths={'Cargo.toml','Cargo.lock','rust-toolchain.toml',c.WORK_PATH}
    for name in ('crates','vendor/humentity','vendor/bevy_obj','vendor/wobj','assets','.cargo'):
        paths.update(path.relative_to(root).as_posix() for path in (root/name).rglob('*')
                     if path.is_file() and not set(path.relative_to(root).parts)&{'target','__pycache__','.git'})
    paths.update('experiments/85-current19-shoulder-refit/replay/'+name
                 for name in ('main.rs','Cargo.toml','Cargo.lock'))
    return sorted(paths)


def capture_paths(root=c.ROOT):
    paths=set(compiled_paths(root))
    # Explicit new85 list allows later author/evaluator files to have their OWN freeze.
    paths.update('experiments/85-current19-shoulder-refit/'+name for name in CAPTURE_FILES)
    paths.add('experiments/85-current19-shoulder-refit/topology-reference.json')
    for name in EXPERIMENTS:
        paths.update(path.relative_to(root).as_posix() for path in
                     (root/'experiments'/name).rglob('*.py'))
    return sorted(paths)


def source_inventory(binary,root=c.ROOT):
    rows=rows_for(root,capture_paths(root))
    raw=binary.read_bytes()
    return {'schema_version':1,'kind':'nvwa85-capture-source-v1','files':rows,
            'inventory_sha256':inventory_digest(rows),'binary':{'bytes':len(raw),'sha256':c.digest(raw)}}


def check_rows(rows,root=c.ROOT,verify_current=True):
    c.need(isinstance(rows,list) and rows,'source rows missing')
    names=[]
    for row in rows:
        c.need(isinstance(row,dict) and set(row)=={'path','bytes','sha256'},'source row schema differs')
        path=c.safe_path(root,row['path']);names.append(row['path'])
        c.need(type(row['bytes']) is int and row['bytes']>=0 and
               isinstance(row['sha256'],str) and re.fullmatch('[0-9a-f]{64}',row['sha256']),
               'source row hash/length malformed')
        if verify_current:
            c.need(path.is_file() and file_row(root,path)==row,'current source bytes differ: '+row['path'])
    c.need(names==sorted(set(names)),'source closure unsorted/duplicate')


def check_build(build,source,identity,root=c.ROOT,verify_current=True):
    c.need(build['schema_version']==1 and build['kind']==BUILD_KIND,'wrong completed build schema')
    c.need(build['status']=='PASS_COMPLETED_BUILD' and type(build['exit_code']) is int and
           build['exit_code']==0,'completed build is not success')
    c.need(isinstance(build['build_run_id'],str) and build['build_run_id'] and
           build['build_run_id']!=identity['run_id']==identity['capture_run_id'] and
           build['build_run_id']==identity['build_run_id'],'build/capture run identity differs')
    c.need(isinstance(build['command'],list) and build['command'] and
           all(isinstance(v,str) and v for v in build['command']) and
           build['command']==identity['build_command'],'actual build command differs')
    c.need(build['target']=='aarch64-apple-darwin'==identity['target'],'wrong native target')
    c.need(set(build['toolchain'])=={'rustc','cargo'} and
           all(isinstance(v,str) and v for v in build['toolchain'].values()) and
           build['toolchain']==identity['toolchain'],'toolchain differs')
    c.need(build['host']==identity['host'] and build['host']['system']=='Darwin' and
           build['host']['machine']=='arm64','build/capture host differs')
    c.need(build['build_config']==identity['build_config'] and
           build['build_config']['offline'] is True and build['build_config']['locked'] is True,
           'build/capture config differs')
    c.need(re.fullmatch('[0-9a-f]{40}',build['source_head']) and
           build['source_head']==identity['source_head'],'build/capture source HEAD differs')
    c.need(build['binary']['name']=='nvwa-current19-replay' and
           {key:build['binary'][key] for key in ('bytes','sha256')}==source['binary'] and
           source['binary']==identity['binary'],'completed build binary differs')
    check_rows(build['source_files'],root,verify_current)
    expected=[row for row in source['files'] if row['path'] in set(compiled_paths(root))]
    c.need(build['source_files']==expected and len(expected)==len(compiled_paths(root)),
           'exact compiled source closure differs')
    c.need(inventory_digest(expected)==build['source_files_sha256']==identity['compiled_source_sha256'],
           'compiled source closure digest differs')


def receipt_row(directory,name):
    raw=(directory/name).read_bytes()
    return {'path':name,'bytes':len(raw),'sha256':c.digest(raw)}


def _authenticate(directory,manifest_sha256,source_sha256,root):
    """Shared exact readback path; tests supply a synthetic temporary source root."""
    import gzip
    raw=(directory/'manifest.json').read_bytes()
    c.need(c.digest(raw)==manifest_sha256,'frozen current19 manifest differs')
    manifest=c.strict_load(raw)
    c.need(manifest['schema_version']==1 and manifest['cohort_kind']==c.KIND and
           manifest['status']=='PASS_CURRENT19_BASELINE' and manifest['source_unchanged'] is True,
           'current19 baseline not admitted')
    c.need(manifest['historical_raw_identity_reused'] is False and
           manifest['quality_acceptance'] is False,'misrepresented current/historical quality identity')
    c.need(set(manifest['receipts'])==set(RECEIPTS),'missing provenance receipts')
    for key,name in RECEIPTS.items():
        c.need(manifest['receipts'][key]==receipt_row(directory,name),'tampered receipt: '+key)
    source=c.strict_load((directory/'source-before.json').read_bytes())
    c.need(source==c.strict_load((directory/'source-at-run.json').read_bytes())==
           c.strict_load((directory/'source-after.json').read_bytes()),'source closure changed during capture')
    c.need(source['schema_version']==1 and source['kind']=='nvwa85-capture-source-v1',
           'wrong source receipt schema')
    c.need(source['inventory_sha256']==source_sha256==manifest['source_inventory_sha256']==
           inventory_digest(source['files']),'frozen capture source differs')
    check_rows(source['files'],root)
    c.need([row['path'] for row in source['files']]==capture_paths(root),'capture source closure incomplete')
    identity=c.strict_load((directory/'identity.json').read_bytes())
    c.need(identity['cohort_kind']==c.KIND and identity['run_id']==manifest['run_id'] and
           identity['source_inventory_sha256']==source_sha256 and
           identity['source_before_sha256']==manifest['receipts']['source_before']['sha256'] and
           identity['build_receipt_sha256']==manifest['receipts']['build']['sha256'],
           'capture identity crosslink differs')
    authorization=c.strict_load((directory/'capture-authorization.json').read_bytes())
    c.need(identity['capture_authorization_sha256']==manifest['receipts']['authorization']['sha256'] and
           authorization['status']=='FROZEN_FOR_CURRENT19_CAPTURE' and authorization['cohort_kind']==c.KIND and
           authorization['source_inventory_sha256']==source_sha256 and authorization['binary']==source['binary'] and
           authorization['build_receipt_sha256']==manifest['receipts']['build']['sha256'],
           'capture authorization crosslink differs')
    c.need(type(manifest['producer_exit_code']) is int and manifest['producer_exit_code']==0,
           'actual producer did not complete successfully')
    check_build(c.strict_load((directory/'build-receipt.json').read_bytes()),source,identity,root)
    audit=c.strict_load((directory/'geometry-audit.json').read_bytes())
    c.need(audit['status']=='PASS_CURRENT19_GEOMETRY' and audit['failures']==[] and
           audit['candidate_read'] is False and audit['quality_acceptance'] is False and
           [r['case'] for r in audit['results']]==list(c.CASES) and
           all(r['status']=='PASS' for r in audit['results']), 'all19 geometry audit not admitted')
    raw_rows=manifest['retained_raw_records']
    c.need(type(raw_rows) is list and len(raw_rows)==20,'all20 raw records including completion required')
    expected_raw=[f'raw/{i:02d}.json' for i in range(20)]
    c.need([row['path'] for row in raw_rows]==expected_raw,'wrong/reordered raw stream paths')
    c.need(sorted(str(path.relative_to(directory)) for path in (directory/'raw').iterdir())==expected_raw,
           'missing/extra raw stream files')
    for row in raw_rows:
        c.safe_path(directory,row['path'])
        c.need(row==receipt_row(directory,row['path']),'tampered retained raw stream record')
    entries=manifest['cases'];c.need(len(entries)==19,'missing/extra current19 cases')
    records=[]
    raw_records=((directory/name).read_bytes() for name in expected_raw)
    for index,(case,actual_raw,record) in enumerate(c.replay_stream(raw_records,manifest['run_id'])):
        entry=entries[index]
        filename=case if case.endswith('.json.gz') else case+'.json.gz'
        c.need(entry['case']==case and entry['path']=='keyframes/'+filename,'wrong/unsafe case path')
        compressed=c.safe_path(directory,entry['path']).read_bytes()
        c.need(len(compressed)==entry['bytes'] and c.digest(compressed)==entry['sha256'],'tampered gzip case')
        raw=gzip.decompress(compressed)
        c.need(len(raw)==entry['raw_bytes'] and c.digest(raw)==entry['raw_sha256'],'tampered raw case')
        c.need(raw==actual_raw,'gzip/raw producer bytes differ')
        records.append(record)
    c.need(len(records)==19,'raw replay omitted sample')
    return records


def authenticate(directory,manifest_sha256,source_sha256):
    """Production raw19/provenance admission. Caller reruns all geometry too."""
    return _authenticate(directory,manifest_sha256,source_sha256,c.ROOT)
