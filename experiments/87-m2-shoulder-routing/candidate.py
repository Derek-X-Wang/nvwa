#!/usr/bin/env python3
"""One original-four-slot-fixture routing feather; no motion fitting."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONTROL = ROOT / 'experiments/50-upper-arm-neutral-ab/artifacts/assets/generated/genuine44-upper-arm-neutral50.glb'
WORK = ROOT / 'experiments/50-upper-arm-neutral-ab/artifacts/genuine44-upper-arm-neutral50.nvwa.json'
CONTROL_SHA = '2779b012405a915cbc84b38dc18e5eb7a91215661b54ac0c7753ecebb49feae7'
WORK_SHA = '033344a831e3a8c6a9bb2fd1e03ce84c78662e568572c528302b86bfaab50fcf'
REGION_SHA = '3f1b28f7d75717b961f388479b15e93dbabac973da1acdfbbc7ca202a5729092'
AUTHOR_SHA = 'bc54eec314ccba2ca2a77499b03d96b1ec9afb8c38cfbb9ac9e1fb04f5736f0e'
TOL = 2e-6
DISCARD_LIMIT = .01


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


C = module('candidate50', 'experiments/50-upper-arm-neutral-ab/candidate.py')

# Exact original author segments, converted (x,y,z)->(x,z,-y) to glTF axes.
SEGMENTS = {
    'pelvis': ((0, .83, 0), (0, 1., 0)),
    'spine': ((0, 1., 0), (0, 1.19, 0)),
    'chest': ((0, 1.19, 0), (0, 1.38, 0)),
    'neck': ((0, 1.38, 0), (0, 1.48, 0)),
    'upper_arm.R': ((.235, 1.33, 0), (.43, 1.13, 0)),
    'forearm.R': ((.43, 1.13, 0), (.57, .94, .01)),
    'hand.R': ((.57, .94, .01), (.615, .85, .015)),
}
TORSO = ('pelvis', 'spine', 'chest', 'neck')
ARM = ('upper_arm.R', 'forearm.R', 'hand.R', 'chest')


def distance(point, segment):
    a, b = segment
    delta = [y-x for x, y in zip(a, b)]
    t = max(0., min(1., sum((p-x)*d for p, x, d in zip(point, a, delta))/sum(d*d for d in delta)))
    return math.sqrt(sum((p-(x+t*d))**2 for p, x, d in zip(point, a, delta)))


def route(point, names):
    nearest = sorted(((name, distance(point, SEGMENTS[name])) for name in names), key=lambda row: row[1])[:4]
    weights = {name: math.exp(-((d-nearest[0][1])/.070)**2) for name, d in nearest}
    total = sum(weights.values())
    weights = {name: w/total for name, w in weights.items() if w/total > .0001}
    total = sum(weights.values())
    return {name: w/total for name, w in weights.items()}


def load():
    for path, digest in [(CONTROL, CONTROL_SHA), (WORK, WORK_SHA), (HERE/'region.json', REGION_SHA),
                         (ROOT/'tools/blender/generate_fixture.py', AUTHOR_SHA)]:
        require(sha(path.read_bytes()) == digest, 'pinned input '+str(path))
    a = C.candidate_asset(CONTROL)
    region = json.loads((HERE/'region.json').read_text())
    primitive = a.doc['meshes'][a.nodes[22]['mesh']]['primitives'][1]
    attrs = primitive['attributes']
    pos = a.accessor(attrs['POSITION'])
    js, ws = a.accessor(attrs['JOINTS_0']), a.accessor(attrs['WEIGHTS_0'])
    skin = a.doc['skins'][a.nodes[22]['skin']]
    names = {a.nodes[node]['name']: node for node in skin['joints']}
    node_to_slot = {node: slot for slot, node in enumerate(skin['joints'])}
    selected = [i for i, p in enumerate(pos) if .265 < p[0] < .305 and 1.28 < p[1] < 1.40]
    require(selected == region['vertex_indices'] and len(selected) == 96, 'exact frozen96 region')
    require(all(len(j) == len(w) == 4 for j, w in zip(js, ws)), 'original four-slot fixture only')
    return a, region, attrs, pos, js, ws, skin, names, node_to_slot


def source_preflight(data):
    a, region, attrs, pos, js, ws, skin, names, node_to_slot = data
    maximum = 0.
    rows = []
    for v in region['vertex_indices']:
        # Convert serialized slots through skin.joints before resolving names.
        actual = {a.nodes[skin['joints'][slot]]['name']: w for slot, w in zip(js[v], ws[v]) if w}
        expected = route(pos[v], ARM if pos[v][0] > .285 else TORSO)
        residual = max(abs(actual.get(n, 0.)-expected.get(n, 0.)) for n in set(actual)|set(expected))
        maximum = max(maximum, residual)
        rows.append({'vertex': v, 'maximum_weight_error': residual})
    require(maximum <= TOL, 'source-route reconstruction exceeds unchanged2e-6: '+str(maximum))
    return {'status': 'SOURCE_RULE_PASS', 'vertices': 96, 'maximum_weight_error': maximum,
            'tolerance': TOL, 'skin_joints_slot_to_node': skin['joints'], 'samples': rows,
            'new_weights_constructed': False}


def smooth(t):
    t = max(0., min(1., t))
    return t*t*(3-2*t)


def four_slots(weights, names, node_to_slot):
    require(all(math.isfinite(w) and w >= 0 for w in weights.values()), 'finite positive union weights')
    ordered = sorted(((names[name], w) for name, w in weights.items() if w > 0), key=lambda row: (-row[1], row[0]))
    discarded = ordered[4:]
    mass = sum(w for node, w in discarded)
    require(mass <= DISCARD_LIMIT, 'original-fixture union discarded mass exceeds1%: '+str(mass))
    kept = ordered[:4]
    total = sum(w for node, w in kept)
    require(total > 0, 'positive retained weight')
    joints = [node_to_slot[node] for node, w in kept]
    stored = [struct.unpack('<f', struct.pack('<f', w/total))[0] for node, w in kept]
    joints += [0]*(4-len(joints))
    stored += [0.]*(4-len(stored))
    require(abs(sum(stored)-1.) <= TOL, 'serialized normalized weights')
    return joints, stored, {'discarded_mass': mass, 'discarded': [{'node': node, 'weight': w} for node, w in discarded]}


def write_record(a, binary, accessor_index, vertex, values):
    accessor = a.doc['accessors'][accessor_index]
    view = a.doc['bufferViews'][accessor['bufferView']]
    fmt, size = {5121: ('B', 1), 5123: ('H', 2), 5126: ('f', 4)}[accessor['componentType']]
    require(accessor['type'] == 'VEC4' and not accessor.get('normalized', False), 'original VEC4 record')
    stride = view.get('byteStride', 4*size)
    offset = view.get('byteOffset', 0)+accessor.get('byteOffset', 0)+vertex*stride
    struct.pack_into('<4'+fmt, binary, offset, *values)
    return set(range(offset, offset+4*size))


def construct(data):
    preflight = source_preflight(data)  # Mandatory actual-called seam before any new weights.
    a, region, attrs, pos, js, ws, skin, names, node_to_slot = data
    binary = bytearray(a.binary)
    rows, allowed = [], set()
    for v in region['vertex_indices']:
        point = pos[v]
        arm_mix = smooth((point[0]-.265)/.040)
        mix = smooth((point[1]-1.28)/.020)*smooth((1.40-point[1])/.020)
        torso, arm = route(point, TORSO), route(point, ARM)
        saved = {a.nodes[skin['joints'][slot]]['name']: w for slot, w in zip(js[v], ws[v]) if w}
        union = {n: (1-mix)*saved.get(n, 0.)+mix*((1-arm_mix)*torso.get(n, 0.)+arm_mix*arm.get(n, 0.))
                 for n in set(saved)|set(torso)|set(arm)}
        new_joints, new_weights, reduction = four_slots(union, names, node_to_slot)
        allowed |= write_record(a, binary, attrs['JOINTS_0'], v, new_joints)
        allowed |= write_record(a, binary, attrs['WEIGHTS_0'], v, new_weights)
        rows.append({'vertex': v, 'arm_mix': arm_mix, 'mix': mix, **reduction})
    changed = {i for i, (before, after) in enumerate(zip(a.binary, binary)) if before != after}
    require(changed and changed <= allowed, 'only96 allowed joint/weight records changed')
    out = C.export48.pack_glb(a.doc, bytes(binary))
    doc, packed = C.export48.decode_glb(out)
    require(doc == a.doc and packed == bytes(binary), 'complete GLB JSON and BIN reload')
    return out, {'status': 'CONSTRUCTED', 'source_preflight': preflight, 'vertices': rows,
                 'maximum_discarded_mass': max(row['discarded_mass'] for row in rows),
                 'sum_discarded_mass': sum(row['discarded_mass'] for row in rows),
                 'pruned_vertices': sum(bool(row['discarded']) for row in rows),
                 'changed_binary_bytes': len(changed), 'allowed_record_bytes': len(allowed),
                 'all_other_binary_bytes_exact': True, 'whole_glb_json_exact': True,
                 'glb_sha256': sha(out)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        data = load()
        if args.preflight:
            result = source_preflight(data)
        else:
            raw, result = construct(data)
            asset_path = HERE/'artifacts/assets/generated/genuine44-shoulder-routing87.glb'
            asset_path.parent.mkdir(parents=True, exist_ok=True)
            require(not asset_path.exists(), 'new candidate output only')
            asset_path.write_bytes(raw)
            work = json.loads(WORK.read_text())
            work['profile']['id'] = 'nvwa-experiment87-shoulder-routing'
            work['character']['profile_id'] = work['profile']['id']
            work['profile']['asset_path'] = 'generated/genuine44-shoulder-routing87.glb'
            work['profile']['asset_sha256'] = sha(raw)
            (HERE/'artifacts/genuine44-shoulder-routing87.nvwa.json').write_text(json.dumps(work, indent=2)+'\n')
    except ValueError as error:
        result = {'status': 'STOP', 'error': str(error), 'candidate_retry_authorized': False}
        args.output.write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result))
        return 1
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('vertices', 'samples', 'source_preflight')}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
