#!/usr/bin/env python3
"""Fail-closed rest-asset evaluator. Candidate scoring needs the root freeze receipt.

Historical source authentication is separate from current runtime authentication.
No pose activation, sample/time gating, or candidate-dependent threshold exists here.
"""
import argparse
import copy
import gzip
import hashlib
import importlib
import json
import math
import re
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
OLD = ROOT / 'experiments/81-shoulder-patch-corrective'
sys.path.insert(0, str(OLD))
import evaluate_patch as kernels
from derive_target import InvalidEvidence, need, digest, raw_f32_hash
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'replay'))
import collect as corpus

INPUTS_SHA = 'fdd3918b7124397862adb33d4170eaf8f7b0e2c687687a4866c763e62ae4cda0'
SOURCE_MHCLO_SHA = '700e8cb224a2c27a30220efa2ed7077e6a6901f5fcd74a1ee610f3e0370776e7'
THRESHOLDS = {'proper_crossing_epsilon': 1e-9, 'degenerate_double_area_m2': 1e-12,
              'ray_tie_m': 1e-5, 'default_roi': [330,185,350,205],
              'body_source_faces0': [7941,7983]}


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def fsum(values):
    result = 0.
    for x in values:
        result = f32(result + x)
    return result


def parse_mapping(data):
    """Read actual garment mapping semantics; keep original text for byte guards."""
    lines = data.decode('utf-8').splitlines(keepends=True)
    rows, scales, section = [], {}, False
    for i, line in enumerate(lines):
        fields = line.split()
        if not fields or fields[0].startswith('#'):
            continue
        if fields[0] in ('x_scale','y_scale','z_scale'):
            need(len(fields)==4 and fields[0][0] not in scales, 'scale declaration malformed')
            reference = f32(float(fields[3]))
            need(math.isfinite(reference) and reference != 0, 'scale reference invalid')
            scales[fields[0][0]] = (int(fields[1]),int(fields[2]),reference)
        if fields == ['verts','0']:
            need(not section and not rows, 'duplicate mapping section')
            section = True
            continue
        if fields[0] == 'delete_verts':
            section = False
        if section:
            need(len(fields) in (1,9), 'mapping row malformed')
            if len(fields)==1:
                helpers, weights, offset = [int(fields[0])], [1.], [0.]*3
            else:
                helpers = list(map(int, fields[:3]))
                weights = [f32(float(x)) for x in fields[3:6]]
                total = fsum(weights)
                if abs(total)>2**-23:
                    weights = [f32(x/total) for x in weights]
                offset = [f32(float(x)) for x in fields[6:9]]
            need(all(math.isfinite(x) for x in weights+offset), 'nonfinite mapping row')
            rows.append({'line0':i, 'fields':fields, 'helpers':helpers,
                         'weights':weights, 'offset':offset})
    need(len(scales)==3 and rows, 'mapping scales/rows incomplete')
    return {'lines':lines, 'rows':rows, 'scales':scales}


def validate_source_change(original, candidate, position_support):
    """Only offset tokens of declared rows may change; every other byte is fixed."""
    need(hashlib.sha256(original).hexdigest()==SOURCE_MHCLO_SHA, 'original garment source hash differs')
    a,b = parse_mapping(original),parse_mapping(candidate)
    need(len(a['lines'])==len(b['lines']) and len(a['rows'])==len(b['rows']), 'source row count differs')
    support = set(position_support)
    need(len(support)==len(position_support) and support, 'position support duplicate/empty')
    need(all(type(i) is int and 0<=i<len(a['rows']) for i in support), 'position support outside source')
    allowed_lines = {a['rows'][i]['line0'] for i in support}
    for i,(old,new) in enumerate(zip(a['lines'],b['lines'])):
        if i not in allowed_lines:
            need(old==new, 'source bytes outside declared offset rows changed')
    changed=[]
    for sid,(old,new) in enumerate(zip(a['rows'],b['rows'])):
        need(old['line0']==new['line0'], 'source mapping line identity differs')
        if sid in support:
            need(len(old['fields'])==len(new['fields'])==9 and old['fields'][:6]==new['fields'][:6],
                 'source helpers or signed coefficients changed')
            def mask_offsets(line):
                matches=list(re.finditer(rb'\S+',line))
                need(len(matches)==9,'source offset token spans malformed')
                for match in reversed(matches[6:9]):
                    line=line[:match.start()]+b'<offset>'+line[match.end():]
                return line
            old_line=a['lines'][old['line0']].encode('utf-8')
            new_line=b['lines'][new['line0']].encode('utf-8')
            need(mask_offsets(old_line)==mask_offsets(new_line),'source bytes outside exact offset token spans changed')
        if old['offset']!=new['offset']:
            need(sid in support, 'source offset outside support changed')
            changed.append(sid)
    need(changed, 'candidate has no actual source offset change')
    need(a['scales']==b['scales'], 'source scale policy changed')
    return a,b,changed


def source_rows(part, key):
    need(len(part['source_ids'])==len(part[key]), 'source row coverage mismatch')
    result={}
    for sid,row in zip(part['source_ids'],part[key]):
        need(sid not in result or result[sid]==row, 'duplicate source rows disagree')
        result[sid]=row
    return result


def fit_rows(mapping, cage):
    """Actual garment f32 signed mapping, raw source refs/offsets (no extra ×0.1)."""
    scales=[]
    for axis,key in enumerate('xyz'):
        lo,hi,reference=mapping['scales'][key]
        need(lo in cage and hi in cage, 'actual scale cage reference absent')
        scales.append(f32(f32(cage[hi][axis]-cage[lo][axis])/reference))
    result=[]
    for row in mapping['rows']:
        need(all(i in cage for i in row['helpers']), 'actual signed mapping helper absent')
        result.append([f32(fsum(f32(cage[h][axis]*w) for h,w in zip(row['helpers'],row['weights']))
                           + f32(scales[axis]*row['offset'][axis])) for axis in range(3)])
    return result,scales


def full_positive_skin(rest, influences, bones):
    """Full original positive aggregates, normalized once; column-major actual skin."""
    need(len(rest)==len(influences), 'skin row coverage mismatch')
    result=[]
    for p,row in zip(rest,influences):
        need(row and len({j for j,w in row})==len(row), 'empty/duplicate joint row')
        need(all(type(j) is int and 0<=j<len(bones) and math.isfinite(w) and w>0 for j,w in row),
             'invalid full positive joint row')
        total=fsum(w for j,w in row)
        weights=[(j,f32(w/total)) for j,w in row]
        matrix=[fsum(f32(bones[j]['skin'][i]*w) for j,w in weights) for i in range(16)]
        need(all(math.isfinite(x) for x in matrix), 'nonfinite actual skin matrix')
        # Scalar f32 analytical reconstruction; actual SIMD order may differ slightly.
        result.append([f32(fsum(f32(matrix[4*k+axis]*p[k]) for k in range(3))+matrix[12+axis])
                       for axis in range(3)])
    return result


COHORT_KIND = 'current18-plus-original-anchor-v1'
WASM_COHORT_KIND = 'current18-wasm-plus-original-anchor-v1'
COHORT_MANIFEST_TYPES = {COHORT_KIND:'hybrid-current18-original-anchor',
                         WASM_COHORT_KIND:'hybrid-current18-wasm-original-anchor'}
REST_BOUND = 1e-7
POSED_BOUND = 1e-5
SOURCE = ROOT/'assets/characters/mpfb-b1-v1'


EXECUTION_DIRECTORIES = ('60-b1-continuous-motion','70-b1-garment-defect',
                         '79-shoulder-pose-corrective','81-shoulder-patch-corrective',
                         '84-shoulder-rest-refit')


def required_execution_paths():
    return sorted(str(path.relative_to(ROOT)) for name in EXECUTION_DIRECTORIES
                  for path in (ROOT/'experiments'/name).rglob('*.py'))


def verify_execution(freeze):
    """Pin every imported experiment implementation before any input admission."""
    rows=freeze['execution_files']
    need(isinstance(rows,list) and rows,'execution source closure absent')
    canonical=json.dumps(rows,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    need(hashlib.sha256(canonical).hexdigest()==freeze['execution_files_sha256'],
         'execution source closure digest differs')
    names=[]
    for row in rows:
        need(isinstance(row,dict) and set(row)=={'path','bytes','sha256'},'execution source row schema differs')
        name=row['path'];relative=Path(name)
        need(isinstance(name,str) and name==relative.as_posix() and not relative.is_absolute()
             and '..' not in relative.parts and relative.parts,'unsafe execution source path')
        path=ROOT/relative
        need(path.resolve().is_relative_to(ROOT.resolve()) and path.is_file(),'execution source absent/escaped')
        need(type(row['bytes']) is int and row['bytes']>=0 and path.stat().st_size==row['bytes']
             and re.fullmatch('[0-9a-f]{64}',row['sha256']) and digest(path)==row['sha256'],
             'execution source bytes differ: '+name)
        names.append(name)
    need(names==sorted(set(names)),'execution source closure unsorted/duplicate')
    need(set(required_execution_paths())<=set(names),'execution imported source closure incomplete')
    return freeze['execution_files_sha256']


def validate_freeze(freeze_path, policy_path, candidate_path=None, preflight=False):
    need(freeze_path is not None and freeze_path.is_file(), 'scoring disabled: root candidate freeze receipt required')
    freeze=corpus.strict_load(freeze_path.read_bytes())
    verify_execution(freeze)
    statuses=('FROZEN_BASELINE_PREFLIGHT','FROZEN_FOR_SCORING') if preflight else ('FROZEN_FOR_SCORING',)
    need(freeze.get('status') in statuses and type(freeze.get('candidate_count')) is int and freeze.get('candidate_count')==1,
         'scoring disabled: root candidate freeze invalid')
    need(freeze['policy_sha256']==digest(policy_path), 'frozen authoring policy hash differs')
    policy=corpus.strict_load(policy_path.read_bytes())
    need(policy['thresholds']==THRESHOLDS, 'unchanged evaluation thresholds differ')
    need(policy['input_hashes_sha256']==INPUTS_SHA, 'fixed19 historical input ledger differs')
    need(policy['cohort_kind']==freeze['cohort_kind'] and freeze['cohort_kind'] in COHORT_MANIFEST_TYPES,
         'explicit new hybrid cohort kind required')
    for key in ('cohort_manifest_sha256','source_inventory_sha256'):
        need(policy[key]==freeze[key] and re.fullmatch('[0-9a-f]{64}',freeze[key]), 'frozen new cohort hash differs: '+key)
    need(policy['baseline_rest_bound_m']==REST_BOUND and policy['baseline_posed_bound_m']==POSED_BOUND,
         'frozen baseline reconstruction bounds differ')
    return freeze,policy


def authenticate_inputs(history, fresh):
    ledger_path=OLD/'input-hashes.json'
    need(digest(ledger_path)==INPUTS_SHA, 'fixed19 ledger changed')
    rows=json.loads(ledger_path.read_text())['cases']
    need(len(rows)==19 and len({r['case'] for r in rows})==19, 'exact19 unique inputs required')
    fixture_path=ROOT/'experiments/79-shoulder-pose-corrective/fixtures/historical-actual-activation.json'
    need(digest(fixture_path)==kernels.ACTIVATION_FIXTURE_SHA, 'historical actual case fixture changed')
    cases={c['input_name']:c for c in json.loads(fixture_path.read_text())['cases']}
    loaded=[]
    for row in rows:
        path=fresh if row['case']=='fresh-default-arm2' else history/row['case']
        need(path.is_file() and path.stat().st_size==row['bytes'] and digest(path)==row['sha256'],
             'missing/mixed/tampered actual input: '+row['case'])
        envelope=json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes())
        snapshot=envelope['frame']['full_base'] if row['case']=='fresh-default-arm2' else envelope['snapshot']
        if row['case']!='fresh-default-arm2':
            case=cases[row['case']]
            need(snapshot['sample']['clip_id']==case['clip'] and snapshot['sample']['source_seconds']==
                 snapshot['sample']['position_seconds']==case['seconds'] and
                 snapshot['parameters']['torso_length']==case['torso'] and snapshot['parameters']['jaw_drop']==0,
                 'actual case identity differs')
            need(all(all(next(b for b in snapshot['bones'] if b['name']==fb['name'])[k]==v
                         for k,v in fb.items()) for fb in case['bones']), 'actual case bone identity differs')
        need(len(snapshot['parts'])==2 and {p['name'] for p in snapshot['parts']}=={'body','garment'},
             'actual case part identity differs')
        loaded.append((row['case'],snapshot,path))
    return loaded


def authenticate_hybrid(directory,fresh,freeze):
    """NEW cohort seam; never substitutes new hashes into historical authentication."""
    kind=freeze['cohort_kind']
    need(kind in COHORT_MANIFEST_TYPES,'wrong new cohort kind')
    manifest=corpus.strict_load((directory/'manifest.json').read_bytes())
    need(manifest['cohort_type']==COHORT_MANIFEST_TYPES[kind],'frozen cohort kind/manifest target differs')
    # Separate authenticators retain their own immutable target/build/source receipts.
    collector=corpus
    if kind==WASM_COHORT_KIND:
        try:
            collector=importlib.import_module('collect_wasm')
        except ModuleNotFoundError as error:
            if error.name!='collect_wasm':raise
            raise InvalidEvidence('Wasm cohort authenticator unavailable; no native fallback') from error
    records=collector.authenticate_corpus(directory,freeze['cohort_manifest_sha256'],
                                          freeze['source_inventory_sha256'],fresh)
    inventory=corpus.strict_load((directory/'source-before.json').read_bytes())
    for row in inventory['files']:
        relative=Path(row['path'])
        need(not relative.is_absolute() and '..' not in relative.parts,'unsafe source inventory path')
        path=ROOT/relative
        need(path.is_file() and path.stat().st_size==row['bytes'] and digest(path)==row['sha256'],
             'current evaluation source differs from captured closure: '+row['path'])
    validator=corpus.geometry_validator(ROOT/'assets',fresh)
    loaded=[]
    for record in records:
        key=corpus.validate_record(record,record['run_id'])
        validator(record,key)  # Recheck source/FK/all weights, not stored manifest checks.
        loaded.append((corpus.case_name(key),record['snapshot']))
    # Existing immutable original source/capture authentication remains strict.
    import author_patch
    author_patch.authenticate(fresh.parents[2])
    loaded.append(('original-fresh-default-anchor',corpus.strict_load(fresh.read_bytes())['frame']['full_base']))
    need(len(loaded)==19 and len({name for name,_ in loaded})==19,'exact hybrid19 required')
    return loaded


def component_error(a,b):
    need(len(a)==len(b) and all(len(x)==len(y)==3 for x,y in zip(a,b)), 'position dimensions differ')
    return max((abs(x-y) for aa,bb in zip(a,b) for x,y in zip(aa,bb)),default=0.)


def raw_cage(parameters):
    rows=[list(map(lambda x:f32(float(x)),line.split()[1:4]))
          for line in (SOURCE/'base.obj').read_text().splitlines() if line.startswith('v ')]
    need(len(rows)==19158,'raw complete body cage absent')
    t=parameters['torso_length']
    need(t in (-1,0,1) and parameters['jaw_drop']==0 and
         all(v==0 for k,v in parameters.items() if k not in ('torso_length','jaw_drop')),
         'unsupported baseline recipe')
    if t:
        name='torso-scale-vert-'+('incr' if t>0 else 'decr')+'.target'
        for line in (SOURCE/'targets'/name).read_text().splitlines():
            fields=line.split()
            if not fields or fields[0].startswith('#'):continue
            sid=int(fields[0]);offset=[f32(f32(float(x))*f32(.1)) for x in fields[1:4]]
            if fsum(f32(x*x) for x in offset)>0:
                rows[sid]=[f32(a+f32(b*abs(t))) for a,b in zip(rows[sid],offset)]
    return dict(enumerate(rows))


def morph_roundtrip(base,shape):
    """Stored MorphAttributes delta, followed by the adapter's base+delta read."""
    need(len(base)==len(shape),'base/shape morph coverage differs')
    return [[f32(a+f32(b-a)) for a,b in zip(old,new)] for old,new in zip(base,shape)]


def reconstruct_source(mapping,parameters):
    """Shared original/candidate path: raw helpers -> base/shape -> f32 morph."""
    neutral=raw_cage({'torso_length':0,'jaw_drop':0})
    shape=raw_cage(parameters)
    base_fit,_=fit_rows(mapping,neutral)
    shape_fit,scales=fit_rows(mapping,shape)
    body=morph_roundtrip([neutral[i] for i in range(19158)],[shape[i] for i in range(19158)])
    garment=morph_roundtrip(base_fit,shape_fit)
    return {'body':body,'garment':garment},scales


def independent_source_rows(part,source_checker,bone_order):
    """Original source weights in binary64; independent of captured aggregates."""
    rows=[]
    for sid,actual in zip(part['source_ids'],part['full_joint_influences']):
        aggregate={}
        mapping=[(sid,1.)] if part['name']=='body' else source_checker.garment_map[sid]
        for helper,coefficient in mapping:
            for bone,weight in source_checker.source_weights.get(helper,{}).items():
                if weight>0:aggregate[bone]=aggregate.get(bone,0.)+coefficient*weight
        positive={bone:weight for bone,weight in aggregate.items() if weight>0}
        total=sum(positive.values());need(math.isfinite(total) and total>0,'source positive row absent')
        expected=[(i,positive[name]/total) for i,name in enumerate(bone_order) if name in positive]
        need(actual and len({j for j,w in actual})==len(actual) and
             all(type(j) is int and 0<=j<len(bone_order) and math.isfinite(w) and w>0 for j,w in actual),
             'original full positive row invalid')
        captured_total=sum(w for j,w in actual);captured={j:w/captured_total for j,w in actual}
        need(set(captured)=={j for j,w in expected},'independent original source influence support differs')
        need(max(abs(captured[j]-w) for j,w in expected)<=1e-6,
             'existing source influence arithmetic bound exceeded')
        rows.append(expected)
    need(len(rows)==len(part['source_ids'])==len(part['full_joint_influences']),'independent source row coverage differs')
    return rows


def comparison_metrics(expected,actual):
    maximum=component_error(expected,actual)
    return {'max_component_error_m':maximum,
            'component_count':3*len(expected),
            'exact_component_count':sum(x==y for a,b in zip(expected,actual) for x,y in zip(a,b)),
            'nonexact_component_count':sum(x!=y for a,b in zip(expected,actual) for x,y in zip(a,b))}


def check_baseline_part(part,expected,bones,source_checker,bone_order,skins,label):
    """Both posed methods must directly pass for each role, including old anchor."""
    rest=comparison_metrics(expected,part['rest_positions'])
    need(rest['max_component_error_m']<=REST_BOUND,
         'all-row original source rest reconstruction exceeds frozen1e-7: '+label)
    posed=full_positive_skin(expected,part['full_joint_influences'],bones)
    scalar=comparison_metrics(posed,part['positions'])
    need(scalar['max_component_error_m']<=POSED_BOUND,
         'all-row scalar-f32 PreparedSkin exceeds frozen1e-5: '+label)
    source_rows64=independent_source_rows(part,source_checker,bone_order)
    posed64=corpus.independent_lbs(expected,source_rows64,skins)
    independent=comparison_metrics(posed64,part['positions'])
    need(independent['max_component_error_m']<=POSED_BOUND,
         'all-row source/FK/binary64 LBS exceeds frozen1e-5: '+label)
    return {'render_rows':len(expected),'full_positive_rows':len(part['full_joint_influences']),
            'ordered_source_fit_f32_morph_roundtrip':rest,
            'scalar_f32_PreparedSkin_matrix_blend':scalar,
            'independent_source_weights_FK_binary64_LBS':independent}


def baseline_preflight(loaded):
    """Finish both independent posed checks on ALL19 before candidate construction."""
    need(len(loaded)==19 and len({name for name,_ in loaded})==19,'all19 baseline slots incomplete')
    need(digest(SOURCE/'garment/female_sportsuit01.mhclo')==SOURCE_MHCLO_SHA,'baseline MHCLO differs')
    need(digest(SOURCE/'garment/female_sportsuit01.obj')=='f9f91788c1dd2918fceedd4dd4ada520f56fb8dfd68cbbeb9a4f6bfbd8e101a9',
         'baseline OBJ differs')
    mapping=parse_mapping((SOURCE/'garment/female_sportsuit01.mhclo').read_bytes())
    body_faces=kernels.read_obj(SOURCE/'base.obj')
    cloth_faces=kernels.read_obj(SOURCE/'garment/female_sportsuit01.obj')
    deleted=kernels.deleted_ids(SOURCE/'garment/female_sportsuit01.mhclo')
    source_checker=corpus.Checker(ROOT/'assets',surfaces=False)
    anchors=[s for name,s in loaded if name=='original-fresh-default-anchor']
    need(len(anchors)==1,'original anchor baseline slot missing')
    bone_order=[b['name'] for b in anchors[0]['bones']]
    need(len(bone_order)==53 and set(bone_order)==set(source_checker.rig),'original anchor/source bone coverage differs')
    reports=[]
    for name,snapshot in loaded:
        parts={p['name']:p for p in snapshot['parts']}
        need(len(parts)==len(snapshot['parts'])==2 and set(parts)=={'body','garment'},'baseline role coverage differs')
        body,cloth=parts['body'],parts['garment']
        kernels.bind_source(body,body_faces,deleted);kernels.bind_source(cloth,cloth_faces)
        need(set(source_rows(body,'rest_positions'))==set(range(19158)),'complete original body cage coverage differs')
        need([b['name'] for b in snapshot['bones']]==bone_order,'all19 original full bone order differs')
        need({b['name']:b['parent'] for b in snapshot['bones']}==
             {n:r['parent'] or None for n,r in source_checker.rig.items()},'all19 source bone hierarchy differs')
        # No recapture request/profile is invented for the old anchor; use its actual sample.
        sample=snapshot['sample']
        skins,fk,heads,bind=corpus.check_bones(snapshot['bones'],sample['clip_id'],sample['source_seconds'])
        reconstructed,scales=reconstruct_source(mapping,snapshot['parameters'])
        errors={}
        for part in (body,cloth):
            expected=[reconstructed[part['name']][sid] for sid in part['source_ids']]
            errors[part['name']]=check_baseline_part(part,expected,snapshot['bones'],source_checker,
                                                    bone_order,skins,name+'/'+part['name'])
        reports.append({'case':name,'parameters':snapshot['parameters'],'sample':sample,
                        'scale_f32':scales,'parts':errors,
                        'independent_FK':{'max_matrix_error':fk,'max_head_error_m':heads,'max_bind_error':bind}})
    return mapping,reports


def support_closure(cloth,policy):
    ids=cloth['source_ids'];tris=[cloth['indices'][i:i+3] for i in range(0,len(cloth['indices']),3)]
    support=set(policy['position_source_ids'])
    need(len(support)==len(policy['position_source_ids']) and support,'duplicate/empty frozen position support')
    affected=[i for i,t in enumerate(tris) if support.intersection(ids[j] for j in t)]
    normal=sorted({ids[j] for i in affected for j in tris[i]})
    accumulation=[i for i,t in enumerate(tris) if set(normal).intersection(ids[j] for j in t)]
    need(affected==policy['incident_triangles0'] and normal==policy['normal_source_ids'] and
         accumulation==policy['normal_accumulation_triangles0'],'frozen support closure differs')
    adjacency={sid:set() for sid in support}
    for t in tris:
        sources={ids[j] for j in t}&support
        for sid in sources:adjacency[sid].update(sources-{sid})
    seen=set();pending=[min(support)]
    while pending:
        sid=pending.pop()
        if sid not in seen:seen.add(sid);pending.extend(adjacency[sid]-seen)
    need(seen==support,'frozen positional support disconnected')
    return support,affected


def candidate_part(snapshot,old_mapping,new_mapping,policy):
    """Refit actual new source row, then actual full-positive LBS; no activation delta."""
    parts={p['name']:p for p in snapshot['parts']};cloth=parts['garment']
    support,affected=support_closure(cloth,policy)
    original_source,scales=reconstruct_source(old_mapping,snapshot['parameters'])
    new_source,_=reconstruct_source(new_mapping,snapshot['parameters'])
    original,new=original_source['garment'],new_source['garment']
    maximum=max(kernels.length(kernels.sub(b,a)) for a,b in zip(original,new))
    need(maximum<=policy['max_displacement_m']==.020,'case source refit exceeds frozen20mm')
    need(all(a==b for sid,(a,b) in enumerate(zip(original,new)) if sid not in support),
         'candidate rest changed outside support')
    neutral=raw_cage({'torso_length':0,'jaw_drop':0})
    reference,_=fit_rows(old_mapping,neutral)
    need(all(kernels.length(kernels.sub(reference[sid],reference[847]))<=policy['support_radius_m']==.070
             for sid in support),'frozen neutral70mm support radius exceeded')
    candidate=copy.deepcopy(cloth)
    allrest=[new[sid] for sid in cloth['source_ids']]
    allposed=full_positive_skin(allrest,cloth['full_joint_influences'],snapshot['bones'])
    # Baseline reconstruction was already checked on every duplicate before copy.
    for i,sid in enumerate(cloth['source_ids']):
        if sid in support:
            candidate['rest_positions'][i]=allrest[i]
            candidate['positions'][i]=allposed[i]
    need(all(raw_f32_hash([a])==raw_f32_hash([b]) for sid,a,b in
             zip(cloth['source_ids'],cloth['positions'],candidate['positions']) if sid not in support),
         'candidate posed positions outside support changed')
    posed_max=max(kernels.length(kernels.sub(a,b)) for a,b in zip(cloth['positions'],candidate['positions']))
    need(posed_max<=.020,'case posed displacement exceeds frozen20mm')
    need(all(cloth[k]==candidate[k] for k in cloth if k not in ('positions','rest_positions')),
         'candidate unchanged attribute differs')
    return candidate,affected,maximum,scales


def camera_for(fresh):
    actual=corpus.strict_load(fresh.read_bytes())['frame']['camera'];m=actual['global_transform']
    cols=([m[0],m[1],m[2]],[m[4],m[5],m[6]],[m[8],m[9],m[10]])
    det=kernels.dot(cols[0],kernels.cross(cols[1],cols[2]))
    inverse=[[x/det for x in row] for row in (kernels.cross(cols[1],cols[2]),kernels.cross(cols[2],cols[0]),kernels.cross(cols[0],cols[1]))]
    cam=(*cols,m[12:15],inverse)
    fov=float(re.search(r'fov: ([0-9.e-]+)',actual['projection'])[1]);top=.05*math.tan(fov/2)
    right=top*1280/610;bp=-top+2*top*(610-720)/610
    return cam,(.05/right,2*.05/(top-bp),0.,(top+bp)/(top-bp))


def score_case(name,snapshot,candidate,affected,maximum,scales,cam,fr):
    parts={p['name']:p for p in snapshot['parts']};cloth,body=parts['garment'],parts['body']
    failures=[];faces=[]
    for ti in affected:
        indices=cloth['indices'][3*ti:3*ti+3]
        a=[cloth['positions'][i] for i in indices];b=[candidate['positions'][i] for i in indices]
        na=kernels.cross(kernels.sub(a[1],a[0]),kernels.sub(a[2],a[0]))
        nb=kernels.cross(kernels.sub(b[1],b[0]),kernels.sub(b[2],b[0]))
        if kernels.length(na)>1e-12 and kernels.length(nb)<=1e-12:failures.append('new_degenerate:'+str(ti))
        if kernels.length(na)*kernels.length(nb)>1e-30 and kernels.dot(na,nb)<=0:failures.append('winding_inversion:'+str(ti))
        faces.append({'render_triangle0':ti,'baseline_double_area_m2':kernels.length(na),'candidate_double_area_m2':kernels.length(nb)})
    before=kernels.crossing_pairs(cloth,body,affected,cloth['source_ids'])
    after=kernels.crossing_pairs(candidate,body,affected,cloth['source_ids'])
    for key in ('body_pairs','nonadjacent_cloth_pairs'):
        new=sorted(set(map(tuple,after[key]))-set(map(tuple,before[key])))
        if new:failures.append('new_proper_crossing:'+key+':'+str(new))
    pixels=[];selected=[]
    for k in range(0,len(body['indices']),3):
        tri=body['indices'][k:k+3]
        if set(body['source_ids'][i] for i in tri) in ({8319,8318,8309},{8319,8309,8310},{8102,8319,8310},{8102,8310,8128}):selected.append(tri)
    need(len(selected)==4,'fixed original7941/7983 body source fans absent')
    for tri in selected:
        world=[kernels.point(body['display_transform'],body['positions'][i]) for i in tri]
        for bary in kernels.BARY_SAMPLES:
            pixels.append(kernels.project([sum(w*p[j] for w,p in zip(bary,world)) for j in range(3)],cam,fr))
    before_probe=kernels.ray_probes(body,cloth,cam,fr,pixels)
    after_probe=kernels.ray_probes(body,candidate,cam,fr,pixels)
    if after_probe['body_first']>before_probe['body_first']:failures.append('new_body_surface_probe_exposure')
    roi=[[x+.5,y+.5] for y in range(185,205) for x in range(330,350)]
    before_roi=kernels.ray_probes(body,cloth,cam,fr,roi);after_roi=kernels.ray_probes(body,candidate,cam,fr,roi)
    if name=='original-fresh-default-anchor' and after_roi['body_first']>=before_roi['body_first']:
        failures.append('no_measurable_default_ROI_benefit')
    return {'case':name,'parameters':snapshot['parameters'],'sample':snapshot['sample'],
            'max_rest_displacement_m':maximum,'scale_f32':scales,'faces':faces,
            'proper_crossings':{'baseline':before,'candidate':after},
            'fixed_body_surface_probes':{'baseline':before_probe,'candidate':after_probe},
            'fixed_default_ROI':{'baseline':before_roi,'candidate':after_roi},'failures':failures,
            'normals_tangents':'NOT-RUN source-fitter generated normals/tangents; position-only scoring; copied fields are not claimed candidate runtime output'}


def old_rejection_control(fresh,retained):
    """Actual old rejected target through SAME candidate scorer crossing-pair seam."""
    import evaluate_target as old
    from derive_target import quaternion,rotate
    need(digest(fresh)==old.FRESH_SHA,'old control actual anchor differs')
    path=retained/'retained-shoulder-source80/one-target-v1/target.json'
    need(digest(path)==old.TARGET_SHA,'old rejected target differs')
    snapshot=corpus.strict_load(fresh.read_bytes())['frame']['full_base']
    witness_path=retained/'retained-shoulder-source80/one-target-evaluation-v1/fresh-new-pair-witness.json'
    witness=corpus.strict_load(witness_path.read_bytes())
    need(witness['garment_render_triangle0']==240 and witness['body_render_triangle0']==13661,'old rejected witness pair identity differs')
    parts={p['name']:p for p in snapshot['parts']};cloth,body=parts['garment'],parts['body']
    target=corpus.strict_load(path.read_bytes());weight,_=old.activation(snapshot['bones'])
    q=quaternion(next(b for b in snapshot['bones'] if b['name']=='clavicle_l')['canonical_posed'])
    delta=[f32(x*weight) for x in rotate(q,target['delta_clavicle_m'])]
    candidate=copy.deepcopy(cloth)
    candidate['positions']=[[f32(x+d) for x,d in zip(p,delta)] if sid==847 else p[:]
                            for sid,p in zip(cloth['source_ids'],cloth['positions'])]
    before=kernels.crossing_pairs(cloth,body,[240],cloth['source_ids'])
    after=kernels.crossing_pairs(candidate,body,[240],cloth['source_ids'])
    need((240,13661) not in before['body_pairs'] and (240,13661) in after['body_pairs'],
         'known rejected new pair escaped scoring crossing seam')
    return {'pair':[240,13661],'status':'PASS_RED_CAPABLE_OLD_REJECTION','fresh_sha256':digest(fresh),'target_sha256':digest(path)}


def run(args):
    freeze,policy=validate_freeze(args.freeze,args.policy,preflight=getattr(args,'preflight_only',False))
    loaded=authenticate_hybrid(args.corpus,args.fresh,freeze)
    mapping,baseline=baseline_preflight(loaded)
    base_report={'cohort_kind':freeze['cohort_kind'],'historical18':'MISSING / NOT-RUN exact historical raw replay',
                 'cohort_manifest_sha256':freeze['cohort_manifest_sha256'],
                 'source_inventory_sha256':freeze['source_inventory_sha256'],
                 'execution_files_sha256':freeze['execution_files_sha256'],
                 'policy_sha256':freeze['policy_sha256'],'baseline_reconstruction':baseline}
    if args.preflight_only:
        report={**base_report,'status':'PASS_BASELINE_PREFLIGHT_ONLY','candidate_read':False}
    else:
        # All19 baseline checks completed before candidate byte authentication/construction.
        need(digest(args.candidate)==freeze['candidate_sha256'],'frozen candidate source hash differs')
        _,new_mapping,changed=validate_source_change((SOURCE/'garment/female_sportsuit01.mhclo').read_bytes(),
                                                    args.candidate.read_bytes(),policy['position_source_ids'])
        cam,fr=camera_for(args.fresh);results=[]
        control=old_rejection_control(args.fresh,args.retained)
        for name,snapshot in loaded:
            candidate,affected,maximum,scales=candidate_part(snapshot,mapping,new_mapping,policy)
            results.append(score_case(name,snapshot,candidate,affected,maximum,scales,cam,fr))
        failures=[{'case':r['case'],'failures':r['failures']} for r in results if r['failures']]
        report={**base_report,'status':'REJECT' if failures else 'POSITION_ONLY_OFFLINE_PASS_RUNTIME_PARITY_NOT_RUN',
                'candidate_sha256':freeze['candidate_sha256'],'changed_source_offsets':changed,
                'old_rejection_control':control,'results':results,'failures':failures,
                'scope':'Hybrid actual baseline + analytical source-refit/full-positive LBS positions. Normal/tangent runtime parity, actual candidate upload, full collision, GPU, visual adoption NOT-RUN.'}
    need(not args.out.exists(),'unique output already exists')
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return 3 if report.get('failures') else 0


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--freeze',type=Path)
    parser.add_argument('--policy',type=Path,required=True)
    parser.add_argument('--candidate',type=Path)
    parser.add_argument('--corpus',type=Path,required=True)
    parser.add_argument('--fresh',type=Path,required=True)
    parser.add_argument('--retained',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--preflight-only',action='store_true')
    try:
        sys.exit(run(parser.parse_args()))
    except (InvalidEvidence,KeyError,TypeError,ValueError,OSError,IndexError) as exc:
        print('NOT-RUN:',exc,file=sys.stderr)
        sys.exit(2)
