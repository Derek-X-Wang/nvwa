#!/usr/bin/env python3
"""One fixed original-fixture arm-side chest mix; no fitting or pruning."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import signal
import struct
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONTROL = ROOT/'experiments/50-upper-arm-neutral-ab/artifacts/assets/generated/genuine44-upper-arm-neutral50.glb'
WORK = ROOT/'experiments/50-upper-arm-neutral-ab/artifacts/genuine44-upper-arm-neutral50.nvwa.json'
REGION = ROOT/'experiments/87-m2-shoulder-routing/region.json'
ASSET = HERE/'artifacts/assets/generated/genuine44-chest-local88.glb'
OUT_WORK = HERE/'artifacts/genuine44-chest-local88.nvwa.json'
PROPOSAL_SHA = '26a88b0a04fdf7248612a592def42b63086192d59a3504de872a187742894aeb'
PINS_SHA = '02dc61cc3ea3c9ced7fc917f6f6d0c3bbe151e71372c76e0a3855c2752b602db'
TOL, DISCARD_LIMIT, MAX_MIX = 2e-6, .01, .5
ARM = frozenset(('upper_arm.R', 'forearm.R'))
TORSO = frozenset(('pelvis', 'spine', 'chest', 'neck'))
REAL_CONSTRUCTOR_CALLS = 0


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def verify_inputs():
    require(sha((HERE/'PROPOSAL.md').read_bytes()) == PROPOSAL_SHA, 'frozen proposal')
    raw = (HERE/'input-pins.json').read_bytes()
    require(sha(raw) == PINS_SHA, 'frozen input manifest')
    pins = json.loads(raw)['repository_inputs']
    for name, expected in pins.items():
        require(sha((ROOT/name).read_bytes()) == expected, 'pinned input '+name)
    return pins


def smooth(t):
    t = max(0., min(1., t))
    return t*t*(3-2*t)


def field(point):
    require(len(point) == 3 and all(math.isfinite(v) for v in point), 'finite rest point')
    x, y, _ = point
    if not (.285 <= x < .305 and 1.28 < y < 1.40):
        return 0.
    return MAX_MIX*(1-smooth((x-.285)/.020))*smooth((y-1.28)/.020)*smooth((1.40-y)/.020)


def positive_support(joints, weights, slot_names):
    require(len(joints) == len(weights) == 4, 'original four slots')
    require(all(type(s) is int and 0 <= s < len(slot_names) for s in joints), 'valid serialized joint slot')
    require(all(math.isfinite(w) and w >= 0 for w in weights), 'finite nonnegative weights')
    require(abs(sum(weights)-1) <= TOL, 'unchanged2e-6 normalization')
    names = [slot_names[s] for s, w in zip(joints, weights) if w > 0]
    require(len(names) == len(set(names)), 'distinct old positive bones')
    return frozenset(names)


def mix_record(point, joints, weights, slot_names):
    require(positive_support(joints, weights, slot_names) == ARM, 'exact original arm support')
    require(slot_names.count('chest') == 1, 'unique existing chest joint')
    zeros = [i for i, w in enumerate(weights) if w == 0]
    require(len(zeros) == 2, 'two original zero slots')
    mix = field(point)
    require(math.isfinite(mix) and 0 <= mix <= MAX_MIX, 'fixed finite mix bound')
    if mix == 0:
        return list(joints), list(weights), mix
    result_j, result_w = list(joints), list(weights)
    for i, w in enumerate(weights):
        if w > 0:
            result_w[i] = struct.unpack('<f', struct.pack('<f', (1-mix)*w))[0]
            require(result_w[i] > 0, 'float32 old positive retention')
    first = zeros[0]
    result_j[first] = slot_names.index('chest')
    result_w[first] = struct.unpack('<f', struct.pack('<f', mix))[0]
    require(result_w[first] > 0, 'float32 positive chest')
    positive_support(result_j, result_w, slot_names)
    return result_j, result_w, mix


def layout(doc, accessor_index, vertex):
    a = doc['accessors'][accessor_index]
    v = doc['bufferViews'][a['bufferView']]
    require(a['type'] == 'VEC4' and not a.get('normalized', False) and 'sparse' not in a, 'plain VEC4 record')
    require(type(vertex) is int and 0 <= vertex < a['count'], 'record vertex bounds')
    require(v.get('buffer', 0) == 0, 'embedded record buffer')
    require(a['componentType'] in (5121, 5123, 5126), 'supported original record format')
    fmt, size = {5121: ('B', 1), 5123: ('H', 2), 5126: ('f', 4)}[a['componentType']]
    stride = v.get('byteStride', 4*size)
    offset = v.get('byteOffset', 0)+a.get('byteOffset', 0)+vertex*stride
    require(stride >= 4*size and offset+4*size <= v.get('byteOffset', 0)+v['byteLength']
            and offset+4*size <= doc['buffers'][0]['byteLength'], 'record byte bounds')
    return offset, '<4'+fmt, 4*size


def read_record(doc, binary, accessor, vertex):
    offset, fmt, size = layout(doc, accessor, vertex)
    require(offset+size <= len(binary), 'binary record bounds')
    return list(struct.unpack_from(fmt, binary, offset))


def write_record(doc, binary, accessor, vertex, values):
    offset, fmt, size = layout(doc, accessor, vertex)
    require(offset+size <= len(binary), 'binary record bounds')
    struct.pack_into(fmt, binary, offset, *values)
    return set(range(offset, offset+size))


def validate_binary(doc, before, after_doc, after, attrs, eligible, positions, slot_names):
    """Constructor-called readback gate, also used independently after generation."""
    require(doc == after_doc, 'whole GLB JSON exact')
    require(len(before) == len(after), 'binary length exact')
    allowed, rows = set(), []
    require(doc['accessors'][attrs['WEIGHTS_0']]['componentType'] == 5126, 'original float32 weights')
    require(doc['accessors'][attrs['JOINTS_0']]['componentType'] in (5121, 5123), 'original integer joints')
    for vertex in eligible:
        old_j = read_record(doc, before, attrs['JOINTS_0'], vertex)
        old_w = read_record(doc, before, attrs['WEIGHTS_0'], vertex)
        new_j = read_record(doc, after, attrs['JOINTS_0'], vertex)
        new_w = read_record(doc, after, attrs['WEIGHTS_0'], vertex)
        # Explicit rejection precedes exact-operation identity, so loss/nonfinite
        # controls exercise the actual serialized-retention seam.
        positive_support(new_j, new_w, slot_names)
        for i, old_weight in enumerate(old_w):
            if old_weight > 0:
                require(new_j[i] == old_j[i] and new_w[i] > 0, 'serialized old positive loss')
        expected_j, expected_w, mix = mix_record(positions[vertex], old_j, old_w, slot_names)
        for accessor, expected in ((attrs['JOINTS_0'], expected_j), (attrs['WEIGHTS_0'], expected_w)):
            offset, fmt, size = layout(doc, accessor, vertex)
            require(after[offset:offset+size] == struct.pack(fmt, *expected), 'exact fixed mix / in-place zero-slot bytes')
            if mix > 0:
                allowed.update(range(offset, offset+size))
        discarded_mass = 0.  # No removal operation exists in this construction.
        require(discarded_mass <= DISCARD_LIMIT, 'unchanged1% discard cap')
        rows.append({'vertex': vertex, 'lambda': mix, 'old_joints': old_j, 'old_weights': old_w,
                     'new_joints': new_j, 'new_weights': new_w, 'old_positive_retained': True,
                     'discarded_mass': 0., 'pruned': False, 'serialized_sum': sum(new_w)})
    changed = {i for i, (x, y) in enumerate(zip(before, after)) if x != y}
    require(changed <= allowed, 'forbidden binary byte changed')
    return {'all_other_binary_bytes_exact': True, 'whole_glb_json_exact': True,
            'changed_binary_bytes': len(changed), 'allowed_record_bytes': len(allowed),
            'original_positive_retention': True, 'normalization_tolerance': TOL,
            'discard_limit': DISCARD_LIMIT, 'maximum_discarded_mass': 0.,
            'sum_discarded_mass': 0., 'pruned_vertices': 0, 'records': rows}


def load_control():
    pins = verify_inputs()
    c = module('candidate50_for88', 'experiments/50-upper-arm-neutral-ab/candidate.py')
    a = c.candidate_asset(CONTROL)
    region = json.loads(REGION.read_text())
    work = json.loads(WORK.read_text())
    require(work['character']['scale'] == 1 and all(v == 0 for v in work['character']['parameters'].values()), 'Work scale1 zero morphs')
    primitive = a.doc['meshes'][a.nodes[22]['mesh']]['primitives'][1]
    attrs = primitive['attributes']
    positions = a.accessor(attrs['POSITION'])
    skin = a.doc['skins'][a.nodes[22]['skin']]
    slot_names = [a.nodes[node]['name'] for node in skin['joints']]
    ids = region['vertex_indices']
    require(ids == [v for v, p in enumerate(positions) if .265 < p[0] < .305 and 1.28 < p[1] < 1.40] and len(ids) == 96, 'exact frozen96 vertices')
    require(len(region['boundary_edge_indices']) == 39 and len(region['incident_face_indices']) == 259, 'frozen39 edges259 faces')
    joints, weights = a.accessor(attrs['JOINTS_0']), a.accessor(attrs['WEIGHTS_0'])
    eligible, torso = [], []
    for v in ids:
        support = positive_support(joints[v], weights[v], slot_names)
        require(support in (ARM, TORSO), 'original saved support patterns')
        (eligible if support == ARM else torso).append(v)
    require(len(eligible) == 42 and len(torso) == 54, '42 arm54 torso capacity')
    require(all(positions[v][0] > .285 for v in eligible), 'saved arm-side rest positions')
    return c, a, region, attrs, positions, slot_names, eligible, pins


def patch_binary(doc, before, attrs, eligible, positions, slot_names):
    """Small-input testable core. Real construction has a separate one-shot entry."""
    binary = bytearray(before)
    for vertex in eligible:
        joints = read_record(doc, before, attrs['JOINTS_0'], vertex)
        weights = read_record(doc, before, attrs['WEIGHTS_0'], vertex)
        js, ws, mix = mix_record(positions[vertex], joints, weights, slot_names)
        if mix > 0:
            write_record(doc, binary, attrs['JOINTS_0'], vertex, js)
            write_record(doc, binary, attrs['WEIGHTS_0'], vertex, ws)
    evidence = validate_binary(doc, before, doc, binary, attrs, eligible, positions, slot_names)
    return bytes(binary), evidence


def construct_once():
    global REAL_CONSTRUCTOR_CALLS
    require(REAL_CONSTRUCTOR_CALLS == 0, 'one real constructor call only')
    REAL_CONSTRUCTOR_CALLS += 1
    require(not ASSET.exists() and not OUT_WORK.exists(), 'fresh candidate outputs only')
    c, a, region, attrs, positions, names, eligible, pins = load_control()
    binary, evidence = patch_binary(a.doc, a.binary, attrs, eligible, positions, names)
    require(evidence['changed_binary_bytes'] > 0, 'nonempty local change')
    # Patch only the original BIN payload; preserve header, JSON bytes and pads.
    original = CONTROL.read_bytes()
    json_length = struct.unpack_from('<I', original, 12)[0]
    start = 12+8+json_length+8
    require(original[start:] == a.binary, 'original BIN framing')
    raw = original[:start]+binary
    doc, reloaded = c.export48.decode_glb(raw)
    validate_binary(a.doc, a.binary, doc, reloaded, attrs, eligible, positions, names)
    require(raw[:start] == original[:start] and len(raw) == len(original), 'original GLB framing exact')
    work = json.loads(WORK.read_text())
    work['profile']['id'] = 'nvwa-experiment88-chest-local'
    work['character']['profile_id'] = work['profile']['id']
    work['profile']['asset_path'] = 'generated/genuine44-chest-local88.glb'
    work['profile']['asset_sha256'] = sha(raw)
    ASSET.parent.mkdir(parents=True, exist_ok=True)
    ASSET.write_bytes(raw)
    OUT_WORK.write_text(json.dumps(work, indent=2, allow_nan=False)+'\n')
    return {'status': 'CONSTRUCTED_PENDING_OFFLINE', 'quality': 'HOLD',
            'glb_sha256': sha(raw), 'work_sha256': sha(OUT_WORK.read_bytes()),
            'real_constructor_calls': REAL_CONSTRUCTOR_CALLS, 'input_sha256': pins,
            'eligible_vertices': eligible, 'source_scope': {'vertices': 96, 'edges': 39, 'incident_faces': 259},
            'preservation': evidence}


def hard_stop(seconds):
    def expired(*_):
        raise TimeoutError(str(seconds)+'-second hard stop')
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(seconds)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'fresh construction receipt only')
    started = time.monotonic()
    hard_stop(30)
    try:
        result = construct_once()
        code = 0
    except Exception as error:
        result = {'status': 'STOP', 'quality': 'HOLD', 'error': str(error),
                  'real_constructor_calls': REAL_CONSTRUCTOR_CALLS, 'retry_authorized': False}
        code = 1
    signal.alarm(0)
    result['elapsed_seconds'] = time.monotonic()-started
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('preservation', 'input_sha256', 'eligible_vertices')}))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
