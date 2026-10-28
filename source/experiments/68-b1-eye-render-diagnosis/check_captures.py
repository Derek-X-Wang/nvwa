#!/usr/bin/env python3
"""Accept complete per-endpoint diagnostic sets; no GPU/pixel/quality claims."""
import argparse
import math
import json
from pathlib import Path
import re

MODES = ('Combined', 'BodyOnly', 'EyeOnly')
PALETTES = ('Textured', 'UnlitTextured', 'RoleTint')
ROLES = {'body', 'garment', 'eyes', 'hair'}
# Existing frozen65 B1 reference record counts; shape/motion do not change topology.
PART_COUNTS = {'body': (22077, 68676), 'garment': (1986, 10308)}

def require(condition, message):
    if not condition:
        raise ValueError(message)

def number(value):
    return type(value) in (int, float) and math.isfinite(value)

def vector(value, size, label):
    require(isinstance(value, list) and len(value) == size and all(number(v) for v in value), label + ' malformed/nonfinite')

def vectors(value, size, count, label):
    require(isinstance(value, list) and len(value) == count and count > 0, label + ' missing/count mismatch')
    for row in value:
        vector(row, size, label)

def indexed(items, key, expected, label):
    require(isinstance(items, list), label + ' list missing')
    names = [item.get(key) for item in items]
    require(len(names) == len(set(names)) and set(names) == set(expected), label + ' missing/duplicate/unexpected identities')
    return dict(zip(names, items))

def indices(value, count, label):
    require(isinstance(value, list) and value and len(value) % 3 == 0, label + ' empty/incomplete triangle indices')
    require(all(type(i) is int and 0 <= i < count for i in value), label + ' out-of-range indices')

def color(text):
    match = re.fullmatch(r'(Srgba|LinearRgba)\((Srgba|LinearRgba) \{ red: ([^,]+), green: ([^,]+), blue: ([^,]+), alpha: ([^ }]+) \}\)', text)
    require(match is not None and match[1] == match[2], 'unrecognized actual color record')
    values = tuple(float(match[i]) for i in range(3, 7))
    require(all(math.isfinite(v) for v in values), 'nonfinite color')
    return values

def material(target, palette):
    before, after = target['production_material'], target['render_material']
    for key in ('base_color', 'unlit', 'base_color_texture', 'alpha_mode', 'cull_mode', 'double_sided', 'roughness', 'metallic', 'full_standard_material_debug'):
        require(key in before and key in after, 'incomplete actual material ' + key)
    require(type(before['unlit']) is bool and type(after['unlit']) is bool, 'invalid unlit state')
    changed = palette != 'Textured' and target['role'] in ('body', 'eyes')
    expected = dict(before)
    if changed:
        expected['unlit'] = True
        if palette == 'RoleTint':
            tint = (0., 1., 1., 1.) if target['role'] == 'body' else (1., 0., 1., 1.)
            require(color(after['base_color']) == tint, 'wrong actual role tint')
            expected['base_color'] = after['base_color']
        old_debug = before['full_standard_material_debug']
        require(('base_color: ' + before['base_color']) in old_debug and ('unlit: ' + str(before['unlit']).lower()) in old_debug, 'material Debug missing controlled fields')
        expected['full_standard_material_debug'] = old_debug.replace('base_color: ' + before['base_color'], 'base_color: ' + expected['base_color'], 1).replace('unlit: ' + str(before['unlit']).lower(), 'unlit: true', 1)
    require(after == expected, 'actual palette has missing or undeclared material changes')
    require(target['coverage_culling_policy_preserved'] is True, 'coverage policy changed')

def buffers(frame, targets):
    actual = indexed(frame['buffers'], 'role', ROLES, 'actual mesh buffers')
    for role, record in actual.items():
        target = targets[role]
        require(record['entity'] == target['entity'] and record['mesh_handle'] == target['mesh_handle'], 'target/buffer binding mismatch')
        count = len(record['positions'])
        vectors(record['positions'], 3, count, role + ' positions')
        vectors(record['normals'], 3, count, role + ' normals')
        if record['uv_0'] is not None:
            vectors(record['uv_0'], 2, count, role + ' UVs')
        else:
            require(role == 'garment', 'selected textured role has missing UV')
        indices(record['indices'], count, role)
        vector(record['display_transform'], 16, role + ' global')
    return actual

def validate(envelope):
    r, f = envelope['report'], envelope['frame']
    require(r['phase'] == 'ready' and r['acknowledged'] is True and r['current'] is True and r['request_succeeded'] is True, 'not acknowledged/current ready evidence')
    require(isinstance(r['request_id'], str) and re.fullmatch('[A-Za-z0-9_-]{1,64}', r['request_id']) is not None, 'invalid request identity')
    require(r['request_id'] == f['request_id'], 'request mismatch')
    require(r['endpoint'] == f['endpoint'] and f['endpoint'] in ('native', 'web'), 'missing/invalid endpoint')
    require(r['captured_identity'] == f['identity'], 'identity mismatch')
    require(r['work_sha256'] == f['work_sha256'] and bool(f['work_sha256']), 'Work mismatch')
    require(r['diagnostic'] == f['diagnostic'], 'diagnostic record mismatch')
    d = f['diagnostic']
    require(d['mode'] in MODES and d['palette'] in PALETTES, 'unknown control')
    require(d['production_appearance_controller_enabled'] is True, 'production controller disabled')
    require(d['visibility_prepared_before_postupdate'] is True, 'visibility not prepared')
    targets = indexed(d['targets'], 'role', ROLES, 'actual role targets')
    require(len({t['entity'] for t in targets.values()}) == len(ROLES), 'duplicate role entity')
    for role, target in targets.items():
        for key in ('entity', 'mesh_handle', 'material_handle'):
            require(isinstance(target[key], str) and bool(target[key]), 'missing actual binding ' + key)
        hidden = (d['mode'] == 'BodyOnly' and role != 'body') or (d['mode'] == 'EyeOnly' and role != 'eyes')
        require(target['isolation_hidden'] is hidden, 'actual mode/role isolation mismatch')
        expected_visibility = 'Some(Hidden)' if hidden else target['visibility_original']
        require(target['visibility_actual'] == expected_visibility, 'actual visibility differs from required role isolation')
        require(type(target['inherited_visibility']) is bool and type(target['view_visibility']) is bool, 'missing propagated/camera visibility')
        if hidden:
            require(target['inherited_visibility'] is False and target['view_visibility'] is False, 'hidden role still inherited/camera visible')
        material(target, d['palette'])
    camera = f['camera']
    require(camera['active'] is True, 'inactive scene camera')
    vector(camera['global_transform'], 16, 'camera global')
    for key in ('projection', 'sub_camera_view'):
        require(isinstance(camera[key], str) and bool(camera[key]), 'actual camera field absent ' + key)
    require(camera['viewport'] == [1280, 720] and camera['msaa'] == 'Sample4', 'wrong pinned viewport/MSAA')
    buffers(f, targets)
    return f

def frame_set(envelopes, count):
    require(len(envelopes) == count, 'incomplete/extra capture set')
    frames = [validate(e) for e in envelopes]
    require(len({f['request_id'] for f in frames}) == count, 'duplicate request IDs')
    require(len({f['endpoint'] for f in frames}) == 1, 'mixed endpoint capture set')
    return frames

def semantic(frame):
    # Handle labels remain in raw inputs; compare their buffers, production materials and state.
    return {'work_sha256': frame['work_sha256'], 'camera': frame['camera'], 'environment': frame['identity']['environment'], 'sample': frame['base']['sample'], 'bones_sha256': frame['base']['bones_sha256'], 'buffers': sorted([{k: v for k, v in b.items() if k not in ('entity', 'mesh_handle')} for b in frame['buffers']], key=lambda b: b['role']), 'production_materials': {t['role']: t['production_material'] for t in frame['diagnostic']['targets']}}

def compare(envelopes):
    frames = frame_set(envelopes, 9)
    controls = [(f['diagnostic']['mode'], f['diagnostic']['palette']) for f in frames]
    require(len(set(controls)) == 9 and set(controls) == {(m, p) for m in MODES for p in PALETTES}, 'missing/duplicate eye controls')
    baseline = semantic(frames[0])
    for f in frames:
        require(f['fixed_case'] == 'short_front', 'wrong eye case')
        sample = f['base']['sample']
        require(sample['source_seconds'] == 2 and sample['position_seconds'] == 2 and sample['playing'] is False and sample['clip_id'] == 'b1_arm_rehearsal_v1', 'wrong held eye sample')
        require(f['base']['parameters'] == {'torso_length': -1., 'jaw_drop': 0.}, 'wrong eye shape')
        require(semantic(f) == baseline, 'geometry/camera/Work/sample/environment/production-material delta')
    return {'scope': 'complete per-endpoint3x3 held actual CPU/control acceptance; no GPU/pixel/quality/cause claim', 'endpoint': frames[0]['endpoint'], 'requests': [f['request_id'] for f in frames], 'controls': [{'mode': m, 'palette': p} for m, p in controls], 'equal': True, 'complete_matrix': True}

def full_base(frame):
    base = frame['full_base']
    parts = indexed(base['parts'], 'name', PART_COUNTS, 'full body/garment parts')
    require(base['sample'] == frame['base']['sample'] and base['parameters'] == frame['base']['parameters'], 'full/compact sample or shape mismatch')
    bones = base['bones']
    require(isinstance(bones, list) and len(bones) == 53, 'incomplete actual bones')
    require(len({b['name'] for b in bones}) == 53, 'duplicate bone identity')
    for bone in bones:
        vector(bone['skin'], 16, 'bone skin')
    actual = {b['role']: b for b in frame['buffers']}
    summary = indexed(frame['base']['parts'], 'name', PART_COUNTS, 'compact body/garment parts')
    for role, part in parts.items():
        count, index_count = PART_COUNTS[role]
        require(summary[role]['vertices'] == count and summary[role]['indices'] == index_count, 'wrong admitted topology counts')
        for key, size in (('positions', 3), ('normals', 3), ('tangents', 4), ('rest_positions', 3), ('rest_normals', 3)):
            vectors(part[key], size, count, role + ' full ' + key)
        require(len(part['indices']) == index_count, 'truncated full triangle index array')
        indices(part['indices'], count, role)
        require(isinstance(part['source_ids'], list) and len(part['source_ids']) == count and all(type(i) is int and i >= 0 for i in part['source_ids']), 'truncated/malformed source IDs')
        influences = part['full_joint_influences']
        require(isinstance(influences, list) and len(influences) == count, 'truncated full influences')
        for row in influences:
            require(isinstance(row, list) and bool(row), 'empty full influence row')
            require(all(isinstance(pair, list) and len(pair) == 2 and type(pair[0]) is int and 0 <= pair[0] < 53 and number(pair[1]) and pair[1] > 0 for pair in row), 'malformed full influences')
            require(len({p[0] for p in row}) == len(row), 'duplicate full influence bone')
            # The frame retains raw positive aggregates. Production LBS divides
            # each weight by the finite positive row sum in a separate cache;
            # raw exported rows are not required to sum to one. Never edit them.
            total = sum(p[1] for p in row)
            require(number(total) and total > 0., 'invalid full influence sum')
        for key in ('display_transform', 'model_to_world'):
            vector(part[key], 16, role + ' ' + key)
        buffer = actual[role]
        require(part['display_entity'] == buffer['entity'] and part['mesh_handle'] == buffer['mesh_handle'], 'full/actual part binding mismatch')
        for key in ('positions', 'normals', 'indices', 'display_transform'):
            require(part[key] == buffer[key], 'full/actual part buffer mismatch ' + key)
    return base

def witness(envelopes):
    frames = frame_set(envelopes, 2)
    times, baseline = [], None
    for f in frames:
        require(f['fixed_case'] == 'long_front_shoulder', 'wrong witness case')
        require(f['diagnostic']['mode'] == 'Combined' and f['diagnostic']['palette'] == 'Textured', 'witness must retain formal production rendering')
        base = full_base(f)
        sample, seconds = base['sample'], base['sample']['source_seconds']
        require(type(seconds) in (int, float) and seconds in (0, 2) and sample['position_seconds'] == seconds and sample['playing'] is False and sample['clip_id'] == 'b1_arm_rehearsal_v1', 'wrong witness sample')
        require(base['parameters'] == {'torso_length': 1., 'jaw_drop': 0.}, 'wrong witness shape')
        fixed = {'work_sha256': f['work_sha256'], 'camera': f['camera'], 'environment': f['identity']['environment'], 'production_materials': semantic(f)['production_materials'], 'topology': sorted([{'name': p['name'], 'indices': p['indices'], 'source_ids': p['source_ids'], 'rest_positions': p['rest_positions'], 'rest_normals': p['rest_normals'], 'full_joint_influences': p['full_joint_influences']} for p in base['parts']], key=lambda p: p['name'])}
        if baseline is None:
            baseline = fixed
        else:
            require(fixed == baseline, 'witness fixed Work/camera/environment/rest/topology/material differs')
        times.append(seconds)
    require(set(times) == {0, 2}, 'missing/duplicate source0/source2 witness pair')
    return {'scope': 'complete per-endpoint paused source0/source2 body/garment witness arrays; posed buffers may differ; no penetration/quality/GPU claim', 'endpoint': frames[0]['endpoint'], 'requests': [f['request_id'] for f in frames], 'source_seconds': times, 'full_arrays_retained': True, 'complete_pair': True}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--witness', action='store_true')
    parser.add_argument('envelopes', type=Path, nargs='+')
    args = parser.parse_args()
    inputs = [json.loads(f.read_text()) for f in args.envelopes]
    print(json.dumps(witness(inputs) if args.witness else compare(inputs), indent=2))

if __name__ == '__main__':
    main()
