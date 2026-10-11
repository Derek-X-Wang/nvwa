#!/usr/bin/env python3
"""Verify public raw evidence and publication hashes; no renderer/server/measurement."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
PUBLIC = EXPERIMENT/'evidence/public'
spec = importlib.util.spec_from_file_location('followup',HERE/'followup.py')
f = importlib.util.module_from_spec(spec); spec.loader.exec_module(f)

def load(path): return json.loads(path.read_text())
def digest(path):
    data=path.read_bytes();return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def require(condition,message):
    if not condition: raise AssertionError(message)
def jpeg_dimensions(data):
    require(data[:2]==b'\xff\xd8','JPEG signature')
    offset=2
    while offset+4<=len(data):
        require(data[offset]==255,'JPEG segment')
        marker=data[offset+1];offset+=2
        length=int.from_bytes(data[offset:offset+2],'big')
        if marker in {0xc0,0xc1,0xc2,0xc3,0xc5,0xc6,0xc7,0xc9,0xca,0xcb,0xcd,0xce,0xcf}:
            return int.from_bytes(data[offset+5:offset+7],'big'),int.from_bytes(data[offset+3:offset+5],'big')
        require(length>=2,'JPEG length');offset+=length
    raise AssertionError('JPEG dimensions missing')

inventory=load(EXPERIMENT/'PUBLICATION_FILES.json')
private_prefix='/'+'Users'+'/'
for name,expected in inventory['files'].items():
    path=EXPERIMENT/name
    require(digest(path)==expected,'Publication hash:'+name)
    if path.suffix in {'.json','.md','.js','.py','.diff'}:
        require(private_prefix not in path.read_text(),'Private user path:'+name)
comparison=load(PUBLIC/'comparison.json')
require(comparison['verdict']=='DEFER','Strict verdict')
require(comparison['identity_unchanged'] and comparison['attempt_order_valid'] and comparison['protocol_script_identity_unchanged'],'Comparison identities/order')
require(len(comparison['runs'])==20 and len(comparison['pairs'])==10,'Run/pair bound')
require(f.ledger_checks(load(PUBLIC/'raw/attempt-ledger.json')),'Chronological exact20 ledger')
before,after=[load(PUBLIC/f'identity-{phase}.json') for phase in ('before','after')]
for key in ('bundles','static_equality','frozen_source'):
    require(before[key]==after[key],'Frozen identity:'+key)
require(not before['failures'] and not after['failures'],'Frozen identity failures')
measured_seals=[load(PUBLIC/f'seal-{phase}.json') for phase in ('before','after')]
require(measured_seals[0]==measured_seals[1],'Measured source seals')
copies=load(HERE/'source-manifest.json')['copies']
for name,row in copies.items():
    require(row['measured_original']==measured_seals[0][name],'Original source hash:'+name)
    require(row['published_copy']==digest(HERE/name),'Published reproduction hash:'+name)
collector=load(PUBLIC/'final-raw-audit-v2.json')['collector_source_hash']
require(digest(PUBLIC/'root-collector.js')==collector,'Separately recorded collector final hash')
require('root-collector.js' not in measured_seals[0],'No retroactive collector preseal')
mapping=load(PUBLIC/'screenshot-map.json')
require(len(mapping)==20,'Screenshot count')
for row in mapping:
    path=EXPERIMENT/row['candidate_path']
    require(digest(path)=={k:row[k] for k in ('bytes','sha256')},'Screenshot raw/copy hash')
    require(jpeg_dimensions(path.read_bytes())==(1280,720),'Screenshot dimensions')
ua=set();raw=PUBLIC/'raw'
for label in f.ORDER:
    requests=load(raw/f'{label}-requests.json')
    groups=[]
    for row in requests:
        if row['client_kind']!='browser-candidate':continue
        if row['path'] in ('/','/index.html'):groups.append([])
        require(bool(groups),'Resource before document');groups[-1].append(row)
    require(len(groups)==2,'Exact two navigations:'+label)
    require(load(raw/f'{label}-cleanup.json')['group_absent'],'Owned server cleanup:'+label)
    for workload,group in zip(('idle','finite'),groups):
        prefix=f'{label}-{workload}'
        logs=load(raw/f'{prefix}-console.json')
        selected=[r for r in logs if 'NVWA_EVIDENCE ' in r['message']]
        require(len(selected)==1 and len(logs)<1000,'Runtime report/capture count:'+prefix)
        runtime,_=json.JSONDecoder().raw_decode(selected[0]['message'].split('NVWA_EVIDENCE ',1)[1])
        require(not f.runtime_checks(runtime,workload),'Runtime invariants:'+prefix)
        require(not [r for r in logs if r['level']=='error'],'Console errors:'+prefix)
        collection=load(raw/f'{prefix}-collection.json')
        require(not collection['errors'] and collection['elapsed_ms']<=45000,'Collection bound/errors:'+prefix)
        product=f.PRODUCT+([f.WORK] if workload=='finite' else [])
        for name in product:
            observed=[r for r in group if ('/index.html' if r['path']=='/' else r['path'])==name]
            require(len(observed)==1,'Exactly-once resource:'+prefix+name)
            row=observed[0];bundle_name=name.removeprefix('/')+'.gz'
            require(row['status']==200 and not row['transfer_error'] and row['cache_control']=='no-store' and row['content_encoding']=='gzip','HTTP response:'+prefix+name)
            require(row['body_bytes_written']==int(row['content_length'])==before['bundles'][label[0]][bundle_name]['bytes'],'Manifest HTTP bytes:'+prefix+name)
        if workload=='idle':require(not any(r['path']==f.WORK for r in group),'Idle Work absent')
        target='/?benchmark=1'+('&player=1&work=works%2Fm1-sequence.nvwa.json' if workload=='finite' else '')
        require(group[0]['request_target']==target,'Fixed document target:'+prefix)
        ua.update(r['user_agent'] for r in group)
        for endpoint in ('before','after'):
            dom=load(raw/f'{prefix}-{endpoint}-dom.json')
            require(dom['visibility']=='visible' and dom['activeElementId']=='nvwa' and dom['canvas']=={'width':1280,'height':720},'Available DOM observation:'+prefix)
            require(dom['focus'] is None and dom['browser_visible'] is False and bool(f.endpoint_checks(dom)),'Unknown-focus/presentation strict DEFER:'+prefix)
require(len(ua)==1 and 'Chrome/155.0.0.0' in next(iter(ua)),'Single browser/version')
for pair in comparison['pairs']:
    calculated=f.pair_result(pair['A_p95_ms'],pair['B_p95_ms'],False)
    require(not pair['valid'] and not pair['passes'],'Invalid pairs cannot pass')
    require(abs(calculated['change_percent']-pair['change_percent'])<1e-10,'Pair arithmetic')
    require(pair['descriptive_cadence_within_10_percent']==calculated['descriptive_cadence_within_10_percent'],'Descriptive threshold')
require(load(raw/'root-port-cleanup.json')['listener_absent'],'Root port cleanup')
browser=load(raw/'root-browser-cleanup.json')
require(not browser['tabs'] and browser['viewport_reset'],'Root browser cleanup')
processes=load(PUBLIC/'process-summary.json')['snapshots']
require(len(processes)==40,'Available process snapshot count')
review=load(PUBLIC/'independent-review.json')
require(review['adoption'].startswith('DEFER'),'Independent review does not adopt')
print('PASS — publication hashes/privacy, 20 JPEG captures/runtime/HTTP inventories, 10 descriptive pairs, DEFER gate, seals/order and cleanup; no new measurements')
