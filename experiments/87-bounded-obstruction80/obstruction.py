#!/usr/bin/env python3
"""Exact, rejection-only source-space certificate. No clearance/PASS API.

Actual physical admission deliberately remains unavailable: the saved packets do
not themselves establish the neutral feature -> posed visible defect/contact
intent link. Root can execute once to receive an honest refusal with a separately
labelled conditional arithmetic record. No boolean attestation promotes it.
"""
from dataclasses import dataclass
from fractions import Fraction as F
from pathlib import Path
import argparse
import hashlib
import json
import math
import time
import multiprocessing
import os
import uuid
import signal

KIND = 'nvwa87-obstruction80-freeze-v1'
FLOOR = F(9999, 10_000_000)
SUPPORT = [24,37,38,41,115,118,128,144,168,211,212,213,558,559,560,570,576,577,582,583,584,586,588,594,829,830,831,841,847,848]
PINS = {
    'ledger': 'b3fbfb6ebf715f14bf106dec777f4845ddcb8cfeb513c49c78f6e77f6aee0707',
    'audit': '50ccf0c75a6a762dae1b6642411edfdb7f10d70a2e5ba09c0000b936c0a2baff',
    'v4_receipt': 'e2950b175f7a84ae15062d5a29b68492cf2ee73a91eef95594bdc89438ee832d',
    'v4_freeze': '3f9a2a48390436f4955d65cef684e811ecfaeaab6dcdf755a0ac844a7cf53e48',
    'v3_receipt': '10c8394cdb980d347a3c8bfbf0c034b858efdbf6bd13ba7750b804192759fd99',
    'support': '66dd2cc157b92bf5651e3c1e88c33d3ce72e6f6ec9fed8694a27984970b05053',
    'base': 'ee8a4b4061eb481551a8e69ae5b8a088e13e746fb3b272f6d27fa97cd99164d2',
    'mhclo': '700e8cb224a2c27a30220efa2ed7077e6a6901f5fcd74a1ee610f3e0370776e7',
    'garment_obj': 'f9f91788c1dd2918fceedd4dd4ada520f56fb8dfd68cbbeb9a4f6bfbd8e101a9',
    'design': '81e182a653560db5bcbc6e451cb43ae4b8f40bdc67ec90e0091f69db55ddf8a0',
    'rereview': '4f9e114c8226bf1db85b1caa03a26bb04f83c1f3d9435ef481853e2e2e3c2e97',
}

class Refusal(ValueError):
    pass

def need(ok, message):
    if not ok:
        raise Refusal(message)

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def strict_load(raw):
    def pairs(items):
        out = {}
        for key, val in items:
            need(key not in out, 'duplicate JSON key')
            out[key] = val
        return out
    def bad_constant(value):
        raise Refusal('nonfinite JSON constant '+value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=bad_constant)

def read_pinned(row):
    path = Path(row['path'])
    need(path.is_absolute() and not path.is_symlink(), 'input must be absolute regular path')
    raw = path.read_bytes()
    need(len(raw) == row['bytes'] and digest(raw) == row['sha256'], 'stale input hash: '+str(path))
    return raw

def fraction(value):
    need(type(value) in (str, int, float, F), 'unsupported number')
    if type(value) is float:
        need(math.isfinite(value), 'nonfinite number')
    try:
        return F(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise Refusal('invalid rational') from exc

def power2(e):
    return F(2**e) if e >= 0 else F(1, 2**(-e))

def f32(value):
    """Exact IEEE binary32 nearest, ties-to-even; no host floating arithmetic."""
    value = fraction(value)
    if not value:
        return F(0)
    sign = -1 if value < 0 else 1
    value = abs(value)
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    if value < power2(exponent):
        exponent -= 1
    need(exponent <= 127, 'binary32 overflow')
    quantum = power2(max(exponent-23, -149))
    scaled = value / quantum
    whole, remainder = divmod(scaled.numerator, scaled.denominator)
    if 2*remainder > scaled.denominator or (2*remainder == scaled.denominator and whole % 2):
        whole += 1
    result = sign * whole * quantum
    need(abs(result) < power2(128), 'binary32 overflow')
    return result

def obj(raw):
    vertices, polygons, groups = [], [], []
    group = ''
    for line in raw.decode('utf-8').splitlines():
        words = line.split()
        if not words:
            continue
        if words[0] == 'g':
            group = ' '.join(words[1:])
        elif words[0] == 'v':
            need(len(words) == 4, 'unsupported OBJ vertex')
            vertices.append([f32(x) for x in words[1:]])
        elif words[0] == 'f':
            face = [int(x.split('/')[0])-1 for x in words[1:]]
            need(len(face) >= 3 and all(0 <= s < len(vertices) for s in face), 'invalid OBJ face')
            polygons.append(face)
            groups.append(group)
    return vertices, polygons, groups

def mapping(raw):
    axes, rows, section = {}, [], False
    for line in raw.decode('utf-8').splitlines():
        words = line.split()
        if not words or words[0].startswith('#'):
            continue
        if words[0] in ('x_scale','y_scale','z_scale'):
            need(len(words) == 4 and words[0][0] not in axes, 'invalid scale')
            axes[words[0][0]] = (int(words[1]), int(words[2]), f32(words[3]))
        if words == ['verts','0']:
            section = True
            continue
        if words[0] == 'delete_verts':
            break
        if section:
            need(len(words) in (1,9), 'invalid mapping row')
            if len(words) == 1:
                rows.append(([int(words[0])],[F(1)],[F(0)]*3))
            else:
                weights = [f32(w) for w in words[3:6]]
                total = F(0)
                for w in weights:
                    total = f32(total+w)
                if abs(total) > power2(-23):
                    weights = [f32(w/total) for w in weights]
                rows.append((list(map(int,words[:3])),weights,[f32(w) for w in words[6:9]]))
    need(set(axes) == set('xyz') and rows, 'missing scales/mapping')
    return axes, rows

def fit_one(cage, axes, rows, sid):
    helpers, weights, offsets = rows[sid]
    result = []
    for axis, key in enumerate('xyz'):
        lo, hi, denominator = axes[key]
        need(denominator != 0, 'zero scale denominator')
        scale = f32(f32(cage[hi][axis]-cage[lo][axis])/denominator)
        total = F(0)
        for helper, weight in zip(helpers,weights):
            total = f32(total+f32(cage[helper][axis]*weight))
        result.append(f32(total+f32(scale*offsets[axis])))
    return result

def sub(a,b):
    return [x-y for x,y in zip(a,b)]

def dot(a,b):
    return sum((x*y for x,y in zip(a,b)), F(0))

def rational_json(x):
    if isinstance(x,F):
        return str(x)
    if isinstance(x,dict):
        return {k:rational_json(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):
        return [rational_json(v) for v in x]
    return x

@dataclass(frozen=True)
class BoundedInput:
    point: tuple
    triangle: tuple
    barycentric: tuple
    units: str
    frame: str
    body_frame: str
    domain: str
    error_m: F
    error_basis: str
    allowed_offsets: tuple
    active_sources: tuple
    body_fixed: bool

def edge_barycentric(point, triangle):
    """Construct q on this one preselected edge; never a nearest-surface query."""
    edge = sub(triangle[2],triangle[1])
    denominator = dot(edge,edge)
    need(denominator > 0, 'degenerate witness edge')
    t = dot(sub(point,triangle[1]),edge)/denominator
    t = max(F(0),min(F(1),t))
    return (F(0),1-t,t)

def certify(value):
    need(value.units == 'm', 'units not admitted')
    need(value.frame and value.frame == value.body_frame, 'relative frame mismatch')
    need(value.domain == 'contact-real-body-unmasked', 'wrong domain')
    need(value.error_basis == 'exact-serialized-binary32-source-space' and value.error_m == 0,
         'unproved input/reconstruction error bound')
    need(list(value.allowed_offsets) == SUPPORT, 'support changed')
    need(value.body_fixed and not set(value.active_sources).intersection(SUPPORT), 'fixed dependency failed')
    need(len(value.point)==3 and len(value.triangle)==3 and all(len(v)==3 for v in value.triangle), 'wrong dimensions')
    p = tuple(fraction(x) for x in value.point)
    tri = tuple(tuple(fraction(x) for x in v) for v in value.triangle)
    bary = tuple(fraction(x) for x in value.barycentric)
    need(len(bary)==3 and all(x>=0 for x in bary) and sum(bary)==1, 'invalid bounded membership')
    cross = (sub(tri[1],tri[0]),sub(tri[2],tri[0]))
    need(dot(cross[0],cross[0])*dot(cross[1],cross[1])-dot(cross[0],cross[1])**2 > 0,
         'degenerate triangle')
    q = tuple(sum((bary[i]*tri[i][k] for i in range(3)),F(0)) for k in range(3))
    squared = dot(sub(p,q),sub(p,q))
    # Ceil sqrt to a 1-picometre grid entirely with integer arithmetic.
    grid = 10**12
    scaled = squared*grid*grid
    top = math.isqrt(scaled.numerator//scaled.denominator)
    if F(top*top) < scaled:
        top += 1
    upper = F(top,grid)
    need(upper*upper >= squared, 'upper enclosure failed')
    return rational_json({'kind':'conditional-source-space-bounded-feature-v1',
        'status': 'CONDITIONAL_STRICT_OBSTRUCTION' if upper < FLOOR else 'UNKNOWN_BOUND_NOT_STRICT',
        'point':p,'q':q,'triangle':tri,'barycentric':bary,
        'distance_squared_m2':squared,'distance_upper_m':upper,'floor_m':FLOOR,
        'input_error_m':F(0),'error_basis':value.error_basis,
        'membership':'nonnegative-exact-barycentrics-sum-one',
        'physical_domain_admitted':False,'nearest_or_side_claim':False})

def validate_ledger(audit, ledger):
    samples = audit['logical_samples']
    rows = audit['rows']
    need(len(samples)==27 and len(rows)==30 and sum(len(s['unmasked_real_body']) for s in samples)==29,
         'omitted samples/rows/ties')
    need(len({s['logical_sample0'] for s in samples})==27, 'duplicate logical IDs')
    need(ledger['counts']['logical_points']==27 and ledger['counts']['original_inequalities']==30 and
         ledger['counts']['unmasked_ties']==29, 'ledger counts differ')
    points = ledger['points']
    need(len(points)==27 and {p['logical_sample0'] for p in points}=={s['logical_sample0'] for s in samples},
         'ledger logical IDs differ')
    for sample in samples:
        point = next(p for p in points if p['logical_sample0']==sample['logical_sample0'])
        expected = [r for r in rows if r['logical_sample0']==sample['logical_sample0']]
        need(point['garment_triangle0']==sample['garment_triangle0'] and point['garment_sources']==sample['garment_sources'] and
             point['barycentric']==sample['barycentric'], 'ledger sample identity differs')
        need(sorted(x['body_triangle0'] for x in point['original_inequalities'])==sorted(x['body_triangle0'] for x in expected),
             'omitted original row')
        need(sorted(x['body_triangle0'] for x in point['unmasked_ties'])==sorted(x['triangle0'] for x in sample['unmasked_real_body']),
             'omitted original tie')
        need(all(x['retained_slope']==0 for x in expected), 'fixed slope changed')
    return {'logical_points':27,'old_rows':30,'unmasked_ties':29,'ledger':ledger,'original_rows':rows,
            'logical_samples':samples}

def reconstruct(inputs):
    audit, old = strict_load(inputs['audit']), strict_load(inputs['v4_receipt'])
    support = strict_load(inputs['support'])
    ledger = validate_ledger(audit,strict_load(inputs['ledger']))
    need(old['status']=='REJECT_AUTHORING_SINGLE_ATTEMPT' and old['candidate_created'] is False, 'old v4 rejection changed')
    need(support['position_source_ids']==SUPPORT and len(old['logical_samples'])==581 and len(old['planes'])==623,
         'original support/coverage changed')
    need(len(support['incident_triangles0'])==83 and {1063,1600}.issubset(support['incident_triangles0']),
         'witness outside frozen83 audit domain')
    cage, body_faces, groups = obj(inputs['base'])
    _, garment_faces, _ = obj(inputs['garment_obj'])
    need(len(cage)==19158 and len(body_faces)==len(groups), 'source geometry count changed')
    need(all([fraction(x) for x in old['neutral_inputs']['raw_neutral_helper_cage'][str(i)]] == v for i,v in enumerate(cage)),
         'source/captured neutral binary32 differs')
    triangles = [(fi,fan-1,[face[0],face[fan],face[fan+1]])
                 for fi,face in enumerate(body_faces) if groups[fi]=='body'
                 for fan in range(1,len(face)-1)]
    need(len(triangles)==26756, 'body domain source set differs')
    fi, fan, sources = triangles[16002]
    need((fi,fan,sources)==(8001,0,[8373,8377,8330]), 'selected original body feature changed')
    cloth_triangles = [[f[0],f[i],f[i+1]] for f in garment_faces for i in range(1,len(f)-1)]
    for logical, triangle0 in ((386,1063),(568,1600)):
        sample = old['logical_samples'][logical]
        need(sample['logical_sample0']==logical and sample['triangle0']==triangle0 and
             sample['sources']==cloth_triangles[triangle0] and sample['barycentric']==[0,1,0] and
             sample['sources'][1]==566, 'witness duplicate/sample identity differs')
    axes, rows = mapping(inputs['mhclo'])
    need(len(rows)==1797, 'mapping count changed')
    p = fit_one(cage,axes,rows,566)
    saved = next(s for s in audit['logical_samples'] if s['logical_sample0']==386)
    need(p==[fraction(x) for x in saved['source_neutral_point']], 'exact source fit differs from saved point')
    tri = tuple(tuple(cage[i]) for i in sources)
    value = BoundedInput(tuple(p),tri,edge_barycentric(p,tri),'m','neutral-source','neutral-source',
                         'contact-real-body-unmasked',F(0),'exact-serialized-binary32-source-space',
                         tuple(SUPPORT),(566,),True)
    return value, ledger, {'logical_ids':[386,568], 'body_triangle0':16002,'obj_face0':fi,'fan_triangle0':fan,
                          'body_source_ids':sources,'garment_source_id':566,
                          'scope':'neutral source-space only; no posed or runtime parity claim',
                          'fixed_dependency_rule':'only offsets of frozen30 mapping rows may change; all cage, scales, other rows, topology fixed',
                          'witness_mapping_helpers':rows[566][0],
                          'normal_scope':'source566 is in normal accumulation support; positions alone are fixed; no visual-invariance claim'}

def inventory(root):
    return {str(p.relative_to(root)):digest(p.read_bytes()) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}

def stage_judgment(conditional, physical_correspondence):
    # Even a true distance bound cannot prove missing physical intent/cause.
    return {'status':'REFUSE_MISSING_PREREQUISITE',
            'physical_obstruction':False, 'physical_domain_admitted':False,
            'conditional_arithmetic':conditional,
            'physical_correspondence':physical_correspondence}

PREREQ_SHA = '7a77d4338960a946587ec3c50b68ee94d4f787d0777def7070dca1fe4c5bc8ec'
TECHNICAL = ('exact_historical_shoulder_raw','same_work_camera_epoch_bindings',
    'current19_exact_byte_provenance','common_source_euclidean_coordinates',
    'original_patch_fixed_dependencies','named_frozen_sample_domain')
CLAIM_STATES = {**{key:('VERIFIED','AVAILABLE') for key in TECHNICAL},
    'saved_44_ROI_visible_source_proof':('AVAILABLE','AVAILABLE'),
    'neutral_lead_to_visible_notch':('UNKNOWN','REFUSE'),
    'physical_intended_contact_domain':('UNKNOWN','REFUSE'),
    'hidden_overlap_intent':('UNKNOWN','REFUSE'),
    'historical18_arrays':('MISSING','REFUSE_IF_REQUESTED'),
    'rigorous_obstruction_certificate':('UNKNOWN','NOT-RUN')}

def identity_key(row):
    return (row['path'],row['bytes'],row['sha256'])

def validate_prerequisites(raw, supplemental, roles):
    need(digest(raw)==PREREQ_SHA, 'prerequisite report not independently reviewed exact bytes')
    report=strict_load(raw)
    need(report['kind']=='OBSTRUCTION80_PREREQUISITE_EVIDENCE_AUDIT_V1' and
         report['status']=='PARTIAL_PHYSICAL_ADMISSION_REFUSE' and
         report['source_base']=='f7fbc39604c8ce7f4dfbb55a1e6a3680d8645cf2', 'wrong prerequisite schema/base')
    claims=report['claims']
    need(len(claims)==len(CLAIM_STATES) and len({c['id'] for c in claims})==len(claims), 'missing/duplicate technical claim')
    need({c['id']:(c['status'],c['gate']) for c in claims}==CLAIM_STATES, 'false/unknown/contradictory prerequisite claim')
    required=report['files']
    need(len(required)==80 and len({r['path'] for r in required})==80, 'report evidence coverage differs')
    need(len({r['path'] for r in supplemental})==len(supplemental), 'duplicate supplemental identity')
    closure={identity_key(r) for r in supplemental}
    required_keys={identity_key(r) for r in required}
    need(required_keys.issubset(closure), 'omitted raw/source prerequisite closure binding')
    by_path={r['path']:identity_key(r) for r in required}
    def bound(row):
        need(identity_key(row) in required_keys, 'nested source identity omitted/contradictory')
    shoulder=report['shoulder_packets']
    need(len(shoulder)==5 and len({r['label'] for r in shoulder})==5, 'missing shoulder package')
    for packet in shoulder:
        bound(packet)
        need(packet['status']=='VERIFIED' and all(v is True for v in packet['checks'].values()), 'false shoulder binding')
    current=report['current19_authentication']
    need(current['raw_records']==20 and current['gzip_cases']==19 and current['all_exact'] is True,
         'current cohort provenance unavailable')
    need(len(current['records'])==39 and sum(r['pointer'].startswith('/cases/') for r in current['records'])==19, 'omitted current provenance record')
    need(current['manifest'] in by_path, 'current manifest not bound')
    for row in current['records']:
        bound(row['identity']);need(row['exact'] is True,'false current identity')
        if 'decompressed_exact' in row:need(row['decompressed_exact'] is True,'false raw/gzip binding')
    for asset in report['assets']:
        bound(asset['source']);bound(asset['capsule'])
        need(asset['exact_source_capture_capsule'] is True,'false capsule source binding')
    need({a['name'] for a in report['assets']}=={'base.obj','body.mhclo','garment/female_sportsuit01.obj',
         'garment/female_sportsuit01.mhclo','weights.game_engine.json','rig.game_engine.json'}, 'source asset omitted')
    for role in ('base','mhclo','garment_obj'):
        bound(roles[role])
    support=report['support']
    need(support['position_source_ids']==SUPPORT and support['counts']['position']==30 and
         support['counts']['position_incident_triangles']==83 and support['source566_position_member'] is False and
         support['source566_normal_member'] is True and support['parsed_affected_exact'] is True,
         'support dependency contradiction')
    need(support['path'] in by_path and by_path[support['path']][2]==roles['support']['sha256'],'support identity mismatch')
    need(report['body_domain']['unmasked_triangles']==26756 and report['body_domain']['displayed_triangles']==22892,
         'named body domain mismatch')
    need(report['ledger']=={'logical_points':27,'old_inequalities':30,'unmasked_ties':29,
                            'all_active_sources_outside_patch':True}, 'ledger evidence mismatch')
    need(report['v4_closure']['count']==309 and report['v4_closure']['all_exact'] is True,'old closure evidence missing')
    cross=report['cross_packet_correspondence']
    need(cross['same_parameters'] is True and cross['current_path'] in by_path,'source/frame correspondence missing')
    for part in cross['parts']:
        need(part['model_to_world_exact'] is True and part['display_transform_exact'] is True and
             part['displayed_triangle_source_order_exact'] is True and
             part['fields']['rest_positions']['mismatch_count']==0 and
             part['fields']['full_joint_influences']['mismatch_count']==0 and
             part['explicit_all_rest_posed_influence_values_exact'] is True,'source/frame identity contradiction')
    return report

class AttemptError(OSError):
    def __init__(self,message,consumed):
        super().__init__(message);self.consumed=consumed

def atomic_publish(path, value):
    path=Path(path)
    temporary=path.with_name(path.name+'.tmp-'+uuid.uuid4().hex)
    try:
        with temporary.open('x') as file:
            file.write(json.dumps(value,indent=2,sort_keys=True)+'\n')
            file.flush();os.fsync(file.fileno())
        os.replace(temporary,path)
        fd=os.open(path.parent,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
    finally:
        try:temporary.unlink(missing_ok=True)
        except OSError:pass

def calculation(policy, receipt):
    consumed_rows=[]
    try:
        roles=policy['inputs']
        need(set(roles)==set(PINS)|{'prerequisites'},'input closure roles differ')
        inputs={role:read_pinned(row) for role,row in roles.items()}
        consumed_rows.extend(roles.values())
        for role,sha in PINS.items():need(digest(inputs[role])==sha,'required original pin differs: '+role)
        # Complete evidence admission always precedes reconstruction/certification.
        report=validate_prerequisites(inputs['prerequisites'],policy['supplemental_inputs'],roles)
        for row in policy['supplemental_inputs']:
            read_pinned(row);consumed_rows.append(row)
        freeze=strict_load(inputs['v4_freeze'])
        need(len(freeze['execution_files'])==309,'old closure omitted')
        for row in freeze['execution_files']:
            resolved={**row,'path':str(Path(policy['old_v4_source_root'])/row['path'])}
            read_pinned(resolved);consumed_rows.append(resolved)
        value,ledger,source=reconstruct(inputs)
        receipt['retained_coverage']=ledger
        receipt.update(stage_judgment(certify(value),'UNKNOWN'))
        receipt['coverage']['arithmetic_witness_count']=1
        receipt['source_witness']=source
        receipt['prerequisites']=report
        receipt['verified_technical_prerequisites']=list(TECHNICAL)
        receipt['missing_prerequisites']=['neutral lead-to-visible-notch causal/visibility correspondence',
                                          'intended physical-contact clearance policy']
    except (Refusal,ValueError,KeyError,TypeError,OSError,IndexError,ZeroDivisionError) as exc:
        receipt.pop('conditional_arithmetic',None)
        receipt['status']='REFUSE_INVALID_OR_UNAVAILABLE_INPUT';receipt['error']=str(exc)
    finally:
        try:
            for row in consumed_rows:read_pinned(row)
            need(inventory(Path(__file__).parent)==policy['execution_files'],'execution closure changed during run')
        except (Refusal,OSError,KeyError,TypeError) as exc:
            receipt.pop('conditional_arithmetic',None)
            receipt['status']='REFUSE_CLOSURE_OR_BUDGET';receipt['error']=str(exc)
        receipt['authenticated_input_closure']=consumed_rows
    return receipt

def child_calculation(policy, receipt, destination):
    # Independent child wall timer also stops it if its supervisor disappears.
    signal.signal(signal.SIGALRM,signal.SIG_DFL)
    signal.setitimer(signal.ITIMER_REAL,policy['time_limit_seconds'])
    try:
        result=calculation(policy,receipt)
        atomic_publish(destination,result)
    except BaseException:
        # Parent retains STARTED and the durable consumed marker if interrupted.
        raise

def execute_bounded(policy,receipt,out):
    # Explicit fork is local POSIX only. It inherits no new machine/dependency.
    # Parent owns this child and terminates/kills it on timeout or interruption.
    context=multiprocessing.get_context('fork')
    target=Path(out)/'calculation-result.json'
    process=context.Process(target=child_calculation,args=(policy,receipt,target))
    process.start()
    old_term=signal.getsignal(signal.SIGTERM)
    def terminate_requested(signum,frame):
        raise KeyboardInterrupt('supervisor termination requested')
    signal.signal(signal.SIGTERM,terminate_requested)
    try:
        process.join(policy['time_limit_seconds'])
        if process.is_alive():
            process.kill();process.join(1)
            receipt['status']='REFUSE_HARD_TIMEOUT'
            receipt['error']='owned calculation killed at frozen deadline'
            receipt['calculation_exit_code']=process.exitcode
            return receipt
        if process.exitcode!=0 or not target.exists():
            receipt['status']='REFUSE_HARD_TIMEOUT' if process.exitcode==-signal.SIGALRM else 'REFUSE_INTERRUPTED_CALCULATION'
            receipt['calculation_exit_code']=process.exitcode
            return receipt
        return strict_load(target.read_bytes())
    finally:
        if process.is_alive():process.kill();process.join(1)
        signal.signal(signal.SIGTERM,old_term)

def run(freeze_path, freeze_sha, output):
    started=time.monotonic()
    raw=Path(freeze_path).read_bytes();need(digest(raw)==freeze_sha,'freeze hash mismatch')
    policy=strict_load(raw)
    need(policy['kind']==KIND and policy['attempt_limit']==1 and policy['mode']=='rejection-only','wrong typed policy')
    need(type(policy['time_limit_seconds']) is int and policy['time_limit_seconds'] in range(1,1201),'time bound invalid')
    need(policy['execution_files']==inventory(Path(__file__).parent),'execution closure mismatch')
    need(all(type(policy[k]) is str and len(policy[k])==64 and all(c in '0123456789abcdef' for c in policy[k])
             for k in ('review_sha256','authorization_sha256')),'missing review/authorization freeze')
    out=Path(output);need(out.is_absolute() and str(out)==policy['exclusive_output'],'exclusive output mismatch')
    out.mkdir(parents=False,exist_ok=False)
    receipt={'kind':'nvwa87-obstruction80-receipt-v1','status':'STARTED','attempt_consumed':True,
       'candidate_created':False,'physical_obstruction':False,'physical_domain_admitted':False,
       'freeze_sha256':freeze_sha,'execution_files_before':policy['execution_files'],
       'coverage':{'expected_preserved_logical':27,'expected_old_rows':30,'expected_ties':29,
                   'arithmetic_witness_count':0,'physical_admitted_count':0},
       'not_run':['nearest-search','side','global-embedding','all581','remaining18','newcandidate','refit'],
       'preserved':['#112 original FAIL','#3 blocked','#4 gaps','#79/M2 scope','v3/v4 REJECT']}
    persistence_errors=[]
    try:
        # Directory existence itself is the no-reuse guard. Marker is fsynced
        # before any calculation and never replaced by later receipt publication.
        atomic_publish(out/'CONSUMED.json',{'attempt_consumed':True,'freeze_sha256':freeze_sha,'status':'CONSUMED_INCOMPLETE'})
        try:atomic_publish(out/'receipt.json',receipt)
        except OSError as exc:
            persistence_errors.append('initial receipt: '+str(exc))
            receipt['status']='REFUSE_PERSISTENCE';receipt['error']=str(exc)
        if not persistence_errors:
            try:receipt=execute_bounded(policy,receipt,out)
            except (KeyboardInterrupt,SystemExit) as exc:
                receipt['status']='REFUSE_INTERRUPTED';receipt['error']=type(exc).__name__
        receipt['elapsed_seconds']=time.monotonic()-started
        receipt['completed']=True
        receipt['execution_files_after']=inventory(Path(__file__).parent)
        if receipt['execution_files_after']!=policy['execution_files']:
            receipt.pop('conditional_arithmetic',None);receipt['status']='REFUSE_CLOSURE_OR_BUDGET'
        if persistence_errors:receipt['persistence_errors']=persistence_errors
        try:atomic_publish(out/'receipt.json',receipt)
        except OSError as exc:
            persistence_errors.append('final receipt: '+str(exc))
            receipt.pop('conditional_arithmetic',None)
            receipt['status']='REFUSE_PERSISTENCE';receipt['persistence_errors']=persistence_errors
            # One-shot recoverable failure gets an explicit incomplete/refusal
            # receipt. Atomic replacement preserves the previous valid receipt.
            atomic_publish(out/'receipt.json',receipt)
        return receipt
    except BaseException as exc:
        receipt.pop('conditional_arithmetic',None)
        receipt['status']='REFUSE_INCOMPLETE_PERSISTENCE_OR_INTERRUPTION'
        receipt['error']=str(exc);receipt['completed']=False
        try:atomic_publish(out/'fallback-receipt.json',receipt)
        except BaseException:pass
        raise AttemptError(str(exc),True) from exc

def cli_summary_error(exc, output):
    consumed=getattr(exc,'consumed',False) or Path(output).exists()
    return {'status':'REFUSE_AFTER_CONSUMPTION' if consumed else 'REFUSE_BEFORE_ATTEMPT',
            'attempt_consumed':consumed,'error':str(exc)}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze',required=True);parser.add_argument('--freeze-sha256',required=True)
    parser.add_argument('--output',required=True);args=parser.parse_args()
    try:
        result=run(args.freeze,args.freeze_sha256,args.output)
        print(json.dumps({'status':result['status'],'attempt_consumed':True,
                          'persistence_errors':result.get('persistence_errors',[])}))
    except (Refusal,OSError,ValueError,KeyError,TypeError) as exc:
        print(json.dumps(cli_summary_error(exc,args.output)))
    raise SystemExit(2)
