#!/usr/bin/env python3
"""Explicit current19 native cohort. Historical authentication stays in experiment84.

Structural controls do not constitute captured geometry or quality acceptance.
"""
import gzip
import hashlib
import json
import math
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
KIND = 'current19-native-production-v1'
PREFIX = 'B1_85_REPLAY '
ARM = 'b1_arm_rehearsal_v1'
KNEE = 'b1_knee_flex_v1'
ANCHOR = 'fresh-default-arm2'
WORK_PATH = 'experiments/79-shoulder-pose-corrective/works/shoulder-rear-baseline-arms.nvwa.json'
V1_ASSET_PATH = 'characters/mpfb-b1-v1/manifest.json'
V1_ASSET_SHA = 'abcdbc26e03431c740c5fce98de22902089f985823a3c655db2416d042d62b18'
PARAMETERS_V2 = ('chin_width', 'head_width', 'hip_width', 'jaw_drop', 'mouth_width',
                 'neck_width', 'nose_width', 'torso_length')
RECIPES = tuple((t,c,k) for t in (-1,0,1) for c in (ARM,KNEE)
                for k in ((0,8,16,24,32) if c == ARM else (16,)))


def need(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def safe_path(root, name):
    need(isinstance(name,str), 'path must be string')
    relative=Path(name)
    need(name==relative.as_posix() and relative.parts and not relative.is_absolute() and
         '..' not in relative.parts, 'unsafe relative path')
    path=root/relative
    need(path.resolve().is_relative_to(root.resolve()), 'escaped source path')
    return path


def pairs(items):
    result = {}
    for key,value in items:
        need(key not in result, 'duplicate JSON key: '+key)
        result[key] = value
    return result


def strict_load(raw):
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: need(False, 'nonfinite JSON'))


def finite(value):
    return type(value) in (int,float) and math.isfinite(value)


def identity(value,label):
    need(type(value) is str and bool(value.strip()),'invalid publication identity: '+label)


def case_name(key):
    t,c,k = key
    return f't{t:+g}__{c}__k{k:02}.json.gz'


CASES = tuple(case_name(key) for key in RECIPES)+(ANCHOR,)


def expected(case):
    need(case in CASES, 'unrequested case')
    if case == ANCHOR:
        return {'parameters':dict.fromkeys(PARAMETERS_V2,0), 'clip_id':ARM,
                'seconds':2, 'k':16, 'timeline_id':'hairline-arms',
                'profile_id':'nvwa-mpfb-b1-motion-v2', 'backend':{
                    'type':'b1_cpu','schema_version':3,
                    'asset_id':'mpfb-hm08-game-engine-female-sportsuit01-v2'}}
    t,c,k = RECIPES[CASES.index(case)]
    return {'parameters':{'torso_length':t,'jaw_drop':0}, 'clip_id':c,
            'seconds':k/8, 'k':k, 'timeline_id':'probe-entry',
            'profile_id':'nvwa-mpfb-b1-motion-v1', 'backend':{
                'type':'b1_cpu','schema_version':2,
                'asset_id':'mpfb-hm08-game-engine-female-sportsuit01-v1'}}


def finite_tree(value):
    if isinstance(value,dict):
        for item in value.values(): finite_tree(item)
    elif isinstance(value,list):
        for item in value: finite_tree(item)
    elif isinstance(value,float):
        need(math.isfinite(value), 'nonfinite numeric value')


def validate_record(record, run_id):
    need(isinstance(record,dict) and record.get('run_id') == run_id, 'mixed run identity')
    need(record.get('kind') == 'sample', 'unexpected record kind')
    case = record['case']; recipe = expected(case)
    need(record['request'] == recipe, 'mislabeled request')
    # Equality alone permits bool/int aliasing. Reject bool numeric recipes explicitly.
    need(all(finite(v) for v in record['request']['parameters'].values()) and
         finite(record['request']['seconds']) and type(record['request']['k']) is int,
         'malformed numeric recipe')
    snapshot,work = record['snapshot'],record['work']
    need(isinstance(snapshot,dict) and isinstance(work,dict), 'snapshot/Work missing')
    finite_tree(record)
    need(type(snapshot['schema_version']) is int and snapshot['schema_version']==1 and
         snapshot['mode']=='motion', 'wrong snapshot schema/mode')
    need(snapshot['diagnostic_pose']=='neutral'==work['character']['diagnostic_pose'],
         'wrong actual diagnostic pose')
    identity(snapshot['character_entity'],'character_entity')
    need(snapshot['profile_id']==recipe['profile_id'] and snapshot['backend']==recipe['backend'] and
         snapshot['asset_id']==recipe['backend']['asset_id'], 'wrong profile/backend/asset')
    need(snapshot['parameters']==recipe['parameters'] and
         all(finite(v) for v in snapshot['parameters'].values()), 'wrong actual parameters')
    sample = snapshot['sample']
    need(sample['clip_id']==recipe['clip_id'] and sample['timeline_id']==recipe['timeline_id'] and
         sample['playing'] is False and type(sample['completed']) is bool, 'wrong sample identity')
    need(type(sample['serial']) is int and sample['serial']>=0, 'invalid sample serial')
    for key in ('position_seconds','source_seconds'):
        need(finite(sample[key]) and abs(sample[key]-recipe['seconds'])<=1e-6,
             'requested actual time mismatch: '+key)
    need(type(snapshot['generation']) is int and snapshot['generation']>0 and
         type(snapshot['revision']) is int and snapshot['revision']>=0,
         'invalid production generation/revision')
    need(work['profile']['id']==snapshot['profile_id'] and
         work['profile']['backend']==snapshot['backend'] and
         work['character']['profile_id']==snapshot['profile_id'] and
         work['character']['parameters']==snapshot['parameters'] and
         work['revision']==snapshot['revision'], 'actual Work/snapshot differs')
    need(type(work['revision']) is int and
         all(finite(v) for v in work['character']['parameters'].values()),
         'actual Work numeric schema differs')
    need(work['timeline']==[{'id':recipe['timeline_id'],'clip_id':recipe['clip_id'],
                           'start_seconds':0,'duration_seconds':4,'speed':1,'looping':False}],
         'actual Work timeline differs')
    entry=work['timeline'][0]
    need(all(finite(entry[key]) for key in ('start_seconds','duration_seconds','speed')) and
         entry['looping'] is False, 'actual Work timeline numeric schema differs')
    if case == ANCHOR:
        # Preserve the actual committed original Work identity, including stage/appearance.
        original = strict_load((ROOT/WORK_PATH).read_bytes())
        need({k:v for k,v in work.items() if k!='revision'} ==
             {k:v for k,v in original.items() if k!='revision'},
             'fresh v2 Work differs from original recipe')
    else:
        need(work['profile']['asset_path']==V1_ASSET_PATH and
             work['profile']['asset_sha256']==V1_ASSET_SHA,
             'actual legacy Work asset path/hash differs')
    bones,parts = snapshot['bones'],snapshot['parts']
    need(isinstance(bones,list) and len(bones)==53 and
         len({b['name'] for b in bones})==53, 'full53 bone coverage differs')
    need(isinstance(parts,list) and len(parts)==2 and
         {p['name'] for p in parts}=={'body','garment'}, 'body/garment coverage differs')
    for bone in bones:
        identity(bone['name'],'bone/name')
        need(bone['parent'] is None or type(bone['parent']) is str,'invalid source bone parent')
        for field in ('rest','posed','inverse_bind','skin','canonical_rest','canonical_posed',
                      'frame_gauge','local_rest','local_posed'):
            matrix=bone[field]
            need(type(matrix) is list and len(matrix)==16 and all(finite(v) for v in matrix),
                 'invalid finite bone matrix: '+bone['name']+'/'+field)
    for part in parts:
        identity(part['display_entity'],part['name']+'/display_entity')
        identity(part['mesh_handle'],part['name']+'/mesh_handle')
    need(len({p['display_entity'] for p in parts})==2 and
         snapshot['character_entity'] not in {p['display_entity'] for p in parts},
         'publication entities overlap')
    return case


def replay_stream(raw_records,run_id):
    """The exact shared capture/readback sample+completion admission seam."""
    seen=[];complete=False;max_legacy_generation=0
    for raw in raw_records:
        need(not complete, 'record after completion')
        record=strict_load(raw)
        need(isinstance(record,dict) and record.get('run_id')==run_id, 'mixed run identity')
        if record.get('kind')=='complete':
            need(type(record['samples']) is int and record['samples']==19 and
                 record['cases']==list(CASES), 'wrong completion coverage')
            complete=True
            continue
        case=validate_record(record,run_id)
        need(case not in seen, 'duplicate case')
        need(case==CASES[len(seen)], 'misordered case')
        if case==ANCHOR:
            need(record['snapshot']['generation']>max_legacy_generation,
                 'v2 Work did not create separate generation')
        else:max_legacy_generation=max(max_legacy_generation,record['snapshot']['generation'])
        seen.append(case)
        yield case,raw,record
    need(complete and tuple(seen)==CASES, 'missing case/completion')


def collect(lines, out, run_id, entries=None):
    """Retain complete structural19 first. Geometry runs only after producer EOF."""
    if entries is None:entries=[]
    (out/'raw').mkdir();(out/'keyframes').mkdir()
    def raw_records():
        index=0
        for line in lines:
            if not line.startswith(PREFIX):
                need(not line.startswith(('B1_60 ','B1_84_REPLAY ')), 'wrong producer prefix')
                continue
            raw=line[len(PREFIX):].encode('utf-8')
            (out/'raw'/f'{index:02d}.json').write_bytes(raw)
            index+=1
            yield raw
    for case,raw,record in replay_stream(raw_records(),run_id):
        compressed=gzip.compress(raw,mtime=0)
        filename=case if case.endswith('.json.gz') else case+'.json.gz'
        path=out/'keyframes'/filename
        path.write_bytes(compressed)
        entries.append({'case':case,'path':str(path.relative_to(out)),
                        'bytes':len(compressed),'sha256':digest(compressed),
                        'raw_bytes':len(raw),'raw_sha256':digest(raw)})
    return entries


def audit_geometry(records,validator,budget_seconds=900):
    """Aggregate every slot. Budget is cooperative before each case, not preemptive."""
    deadline=time.monotonic()+budget_seconds;results=[]
    for record in records:
        case=record['case']
        if time.monotonic()>=deadline:
            results.append({'case':case,'status':'NOT-RUN_BUDGET_EXHAUSTED'})
            continue
        try:
            checks=validator(record)
            results.append({'case':case,'status':'PASS','checks':checks})
        except (ValueError,KeyError,TypeError,OSError,IndexError,ArithmeticError) as error:
            results.append({'case':case,'status':'REJECT','failure':str(error)})
    need([r['case'] for r in results]==list(CASES),'geometry audit omitted/misordered slots')
    failures=[r for r in results if r['status']!='PASS']
    return {'schema_version':1,'status':'REJECT_CURRENT19_GEOMETRY' if failures else 'PASS_CURRENT19_GEOMETRY',
            'budget_seconds':budget_seconds,'results':results,'failures':failures,
            'candidate_read':False,'quality_acceptance':False}
