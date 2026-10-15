#!/usr/bin/env python3
"""Offline signed-reference diagnostics on the fixed public sample; JSON stdout.

No mapping/export is admitted. Candidate root policies and geometric frames are
conditional calculations, independent of anatomical and playable admission.
"""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
RAW = 'experiments/44-approved-cpu-motion-trial/evidence/run/raw/'
PINS = {
    'experiments/41-real-short-motion/source-skeleton.json': 'd137f3ea5522deeb70257d2fd5522ca6d5436c0145ea001a1e8b4fc646cddd9a',
    'experiments/43-rig-mapping/spike.py': '063aefdd56d988256154b291b7f783d874f513b714303c546a36d8bf695bfe93',
    'assets/fixtures/nvwa-humanoid.glb': 'f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6',
    'experiments/44-approved-cpu-motion-trial/evidence/run/generation-receipt.json': '554fd2e64e316d218fd699bbbe8d3e45351a7b3a3e08ef077cdc2c6cfaaa52c9',
    'experiments/44-approved-cpu-motion-trial/evidence/run/process/receipt.json': 'f67726f84982d6e5bd7c22e944131a7991016508e541d88972da6e20abc6410b',
    'experiments/44-approved-cpu-motion-trial/evidence/run/process/stdout.txt': 'd8cafdcca9f05b92f112232345c7435335858a1f019cabc2067d30ba4e71d5d1',
    RAW+'root_positions.f32': 'dcc221d506999a803b1d0fddef87abc0131b1e8f4e64187bc57fde3a63c204af',
    RAW+'local_rotations_xyzw.f32': '67914c5d72c54429bf8a70d3f9ef43157fb5181fa36ab2c5f8ce7f9dc69d3a55',
    'tools/blender/generate_fixture.py': 'bc54eec314ccba2ca2a77499b03d96b1ec9afb8c38cfbb9ac9e1fb04f5736f0e',
    'assets/fixtures/provenance-manifest.json': '8d9d507238470d22460b979c49659b5f3794551e006a4481420695905414f37f',
}
TARGET_NAMES = ['root', 'pelvis', 'spine', 'chest', 'neck', 'head',
                'upper_arm.L', 'forearm.L', 'hand.L', 'upper_arm.R',
                'forearm.R', 'hand.R', 'thigh.L', 'shin.L', 'foot.L',
                'thigh.R', 'shin.R', 'foot.R']
# Frozen 43 correspondence, used only for historical direction/endpoint controls.
MAP = dict(zip(TARGET_NAMES, ['Hips', 'Hips', 'Spine1', 'Chest', 'Neck1',
    'Head', 'LeftArm', 'LeftForeArm', 'LeftHand', 'RightArm', 'RightForeArm',
    'RightHand', 'LeftLeg', 'LeftShin', 'LeftFoot', 'RightLeg', 'RightShin', 'RightFoot']))
I = [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]]
ROOT_TOL = 1e-12
FRAME_TOL = 1e-10
ZERO_TOL = 1e-12  # Numerical rank only, never a trusted anatomical threshold.


def require(ok, message):
    if not ok:
        raise ValueError(message)


def finite_number(x):
    return type(x) in (int, float) and math.isfinite(x)


def vector(v, size, label):
    require(type(v) is list and len(v) == size and all(finite_number(x) for x in v),
            'invalid finite vector: '+label)
    return v


def encode(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n').encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def mm(a, b):
    return [[sum(x*y for x, y in zip(row, col)) for col in zip(*b)] for row in a]


def tr(a):
    return [list(c) for c in zip(*a)]


def mv(a, b):
    return [sum(x*y for x, y in zip(row, b)) for row in a]


def sub(a, b):
    return [x-y for x, y in zip(a, b)]


def add(a, b):
    return [x+y for x, y in zip(a, b)]


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def norm(v):
    return math.sqrt(dot(v, v))


def unit(v):
    n = norm(v)
    require(math.isfinite(n) and n > ZERO_TOL, 'zero/nonfinite direction')
    return [x/n for x in v]


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def angle(a, b):
    a, b = unit(a), unit(b)
    return math.atan2(norm(cross(a, b)), dot(a, b))


def det(a):
    return dot(a[0], cross(a[1], a[2]))


def rotation(q):
    vector(q, 4, 'XYZW quaternion')
    x, y, z, w = unit(q)
    return [[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
            [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
            [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]]


def globals_(s, local):
    out = []
    for p, r in zip(s['parents'], local):
        out.append(r if p is None else mm(out[p], r))
    return out


def affine_fk(s, local, root):
    """4x4 TRS composition, independent of candidate root subtraction arithmetic."""
    out = []
    for j, p in enumerate(s['parents']):
        t = root if p is None else s['translations'][j]
        a = [[local[j][r][c]*s['scales'][j][c] for c in range(3)]+[t[r]] for r in range(3)]
        a.append([0., 0., 0., 1.])
        out.append(a if p is None else mm(out[p], a))
    return [[a[r][3] for r in range(3)] for a in out]


def validate_skeleton(s):
    n = len(s['names'])
    require(n > 0 and len(set(s['names'])) == n and all(type(x) is str for x in s['names']), 'joint names')
    for key in ('parents', 'translations', 'rotations', 'scales'):
        require(type(s[key]) is list and len(s[key]) == n, 'skeleton shape: '+key)
    for j, p in enumerate(s['parents']):
        require((j == 0 and p is None) or (type(p) is int and 0 <= p < j), 'parent order')
        vector(s['translations'][j], 3, 'rest translation')
        vector(s['scales'][j], 3, 'rest scale')
        require(all(x > 0 for x in s['scales'][j]), 'positive scales required')
        rotation(s['rotations'][j])


def parse_target(data):
    require(data[:4] == b'glTF' and struct.unpack_from('<I', data, 4)[0] == 2, 'GLB header')
    require(struct.unpack_from('<I', data, 8)[0] == len(data), 'GLB byte length')
    n, kind = struct.unpack_from('<II', data, 12)
    require(kind == 0x4e4f534a, 'GLB JSON chunk')
    g = json.loads(data[20:20+n])
    joints = g['skins'][0]['joints']
    parents = {c: p for p, node in enumerate(g['nodes']) for c in node.get('children', [])}
    outside = g['nodes'][parents[joints[0]]]
    require(outside.get('translation', [0, 0, 0]) == [0, 0, 0] and
            outside.get('rotation', [0, 0, 0, 1]) == [0, 0, 0, 1] and
            outside.get('scale', [1, 1, 1]) == [1, 1, 1] and 'matrix' not in outside,
            'unsupported nonidentity target ancestor')
    require(parents[joints[0]] in g['scenes'][g.get('scene', 0)]['nodes'], 'unsupported ancestor hierarchy')
    nodes = [g['nodes'][j] for j in joints]
    require(all('matrix' not in node for node in nodes), 'matrix joint unsupported')
    s = {'names': [node['name'] for node in nodes],
         'parents': [joints.index(parents[j]) if parents[j] in joints else None for j in joints],
         'translations': [node.get('translation', [0., 0., 0.]) for node in nodes],
         'rotations': [node.get('rotation', [0., 0., 0., 1.]) for node in nodes],
         'scales': [node.get('scale', [1., 1., 1.]) for node in nodes]}
    validate_skeleton(s)
    require(s['names'] == TARGET_NAMES and s['parents'][:2] == [None, 0], 'exact target hierarchy')
    # Read base POSITION samples from the actual eyeball/pupil meshes. These are
    # geometric corroboration, not a replacement anatomical or trained-data label.
    bin_n, bin_kind = struct.unpack_from('<II', data, 20+n)
    require(bin_kind == 0x004e4942, 'GLB BIN chunk')
    binary = data[28+n:28+n+bin_n]
    eyes = {}
    for node in g['nodes']:
        name = node.get('name', '')
        if not name.startswith(('Eye white ', 'Eye pupil ')):
            continue
        require('matrix' not in node and node.get('translation', [0, 0, 0]) == [0, 0, 0] and
                node.get('rotation', [0, 0, 0, 1]) == [0, 0, 0, 1] and
                node.get('scale', [1, 1, 1]) == [1, 1, 1], 'eye node transform')
        require(parents.get(g['nodes'].index(node)) == parents[joints[0]], 'eye ancestor')
        points = []
        for primitive in g['meshes'][node['mesh']]['primitives']:
            a = g['accessors'][primitive['attributes']['POSITION']]
            require(a['componentType'] == 5126 and a['type'] == 'VEC3' and 'sparse' not in a, 'eye accessor')
            view = g['bufferViews'][a['bufferView']]
            start = view.get('byteOffset', 0)+a.get('byteOffset', 0)
            stride = view.get('byteStride', 12)
            points.extend(struct.unpack_from('<3f', binary, start+i*stride) for i in range(a['count']))
        require(len(points) > 0 and all(finite_number(x) for p in points for x in p), 'eye positions')
        eyes[name] = [sum(p[d] for p in points)/len(points) for d in range(3)]
    require(len(eyes) == 4, 'four eye geometry landmarks required')
    return s, eyes


def load_inputs(input_bytes=None):
    inputs = {} if input_bytes is None else dict(input_bytes)
    require(input_bytes is None or set(inputs) == set(PINS), 'exact input identities required')
    for name, pin in PINS.items():
        data = (ROOT/name).read_bytes() if input_bytes is None else inputs[name]
        require(sha(data) == pin, 'SHA256 mismatch: '+name)
        inputs[name] = data
    meta = json.loads(inputs['experiments/41-real-short-motion/source-skeleton.json'])
    require(meta['units'] == 'meters' and meta['up_axis'] == '+Y' and meta['forward_axis'] == '+Z', 'source declared anchors')
    source = {'names': meta['joint_names'], 'parents': [None if p == -1 else p for p in meta['parents']],
              'translations': meta['rest_local_translations'], 'rotations': meta['rest_local_rotations_xyzw'],
              'scales': meta['rest_local_scales']}
    validate_skeleton(source)
    require(len(source['names']) == 30 and source['names'][0] == 'Hips', 'SOMA30 identity')
    target, eyes = parse_target(inputs['assets/fixtures/nvwa-humanoid.glb'])
    manifest = json.loads(inputs['assets/fixtures/provenance-manifest.json'])
    published = {r['path']: r['sha256'] for r in manifest['files']}
    for name in ('assets/fixtures/nvwa-humanoid.glb', 'tools/blender/generate_fixture.py'):
        require(published[name] == PINS[name], 'target generator/fixture provenance binding')
    receipt = json.loads(inputs['experiments/44-approved-cpu-motion-trial/evidence/run/generation-receipt.json'])
    require(type(receipt['returncode']) is int and receipt['returncode'] == 0 and receipt['reason'] == 'exited' and
            receipt['raw_complete'] is True, 'successful genuine receipt')
    require(type(receipt['request']['frames']) is int and receipt['request']['frames'] == 90 and
            type(receipt['request']['fps']) is int and receipt['request']['fps'] == 30, 'exact frame/fps identity')
    require(len(receipt['raw_provenance']) == 2, 'raw provenance count')
    bound = {RAW+Path(r['path']).name: r['sha256'] for r in receipt['raw_provenance']}
    require(bound == {RAW+k: PINS[RAW+k] for k in ('root_positions.f32', 'local_rotations_xyzw.f32')}, 'raw provenance binding')
    rb, qb = inputs[RAW+'root_positions.f32'], inputs[RAW+'local_rotations_xyzw.f32']
    require(len(rb) == 1080 and len(qb) == 43200, 'raw byte shape')
    rr, qq = struct.unpack('<270f', rb), struct.unpack('<10800f', qb)
    require(all(math.isfinite(x) for x in rr+qq), 'nonfinite raw input')
    roots = [list(rr[i:i+3]) for i in range(0, 270, 3)]
    frames = [[list(qq[(t*30+j)*4:(t*30+j+1)*4]) for j in range(30)] for t in range(90)]
    return source, target, roots, frames, eyes


def signed_policies(anchors=None):
    # Each signed axis is declared independently. Never derive named side from
    # cross(up, front), nor transform both sides by the policy under test.
    anchors = anchors or {'up': ([0, 1, 0], [0, 1, 0]),
                          'front': ([0, 0, 1], [0, 0, 1]),
                          'named_left': ([1, 0, 0], [-1, 0, 0])}
    rows = []
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((-1, 1), repeat=3):
            b = [[signs[i] if j == perm[i] else 0 for j in range(3)] for i in range(3)]
            residuals = {key: angle(mv(b, a), z) for key, (a, z) in anchors.items()}
            rows.append({'basis': b, 'determinant': int(det(b)), 'residual_rad': residuals,
                         'agrees': {k: x <= FRAME_TOL for k, x in residuals.items()}})
    return {'candidates': rows, 'counts': {'all': len(rows),
        'up': sum(r['agrees']['up'] for r in rows),
        'up_front': sum(r['agrees']['up'] and r['agrees']['front'] for r in rows),
        'up_front_named_left': sum(all(r['agrees'].values()) for r in rows)},
        'policy_selected': None, 'semantic_status': 'HOLD',
        'reason': 'Identity preserves common up/front; X reflection also preserves those axes and matches current named-side signs. Anatomical label/parity authority is unresolved.'}


def frame_from_directions(primary, secondary):
    x = unit(primary)
    # Cross-cross projection avoids subtracting nearly equal longitudinal
    # components at the almost straight source elbows. It cannot cure their
    # physical conditioning; that is still reported as inverse sine, with HOLD.
    y = unit(cross(cross(x, unit(secondary)), x))
    z = unit(cross(x, y))
    f = tr([x, y, z])  # primary X, projected secondary Y, right cross product Z
    require(max(abs(v-I[i][j]) for i, row in enumerate(mm(tr(f), f)) for j, v in enumerate(row)) < FRAME_TOL,
            'frame orthogonality')
    require(abs(det(f)-1) < FRAME_TOL, 'proper geometric frame')
    return f


def check_geometric_frame(frame, primary, secondary):
    """Observe primary direction AND signed secondary; a half twist fails."""
    x = unit(primary)
    y = unit(cross(cross(x, unit(secondary)), x))
    require(angle(mv(frame, [1., 0., 0.]), x) < FRAME_TOL, 'primary segment direction mismatch')
    require(angle(mv(frame, [0., 1., 0.]), y) < FRAME_TOL, 'signed secondary/twist mismatch')


def frame_observability(s):
    rest = affine_fk(s, [rotation(q) for q in s['rotations']], s['translations'][0])
    rows = []
    for j, name in enumerate(s['names']):
        children = [k for k, p in enumerate(s['parents']) if p == j]
        # Name the intended primary before choosing secondary geometry.
        preferred = {'Hips': 'Spine1', 'Chest': 'Neck1', 'Head': 'Jaw',
                     'LeftHand': 'LeftHandMiddleEnd', 'RightHand': 'RightHandMiddleEnd',
                     'pelvis': 'spine', 'chest': 'neck'}
        c = s['names'].index(preferred[name]) if name in preferred else (children[0] if children else None)
        primary = sub(rest[c], rest[j]) if c is not None else (sub(rest[j], rest[s['parents'][j]]) if s['parents'][j] is not None else None)
        secondary, label = None, None
        if c is not None:
            other = [k for k in children if k != c]
            grandchildren = [k for k, p in enumerate(s['parents']) if p == c]
            # Elbow/knee bend references must use the proximal limb segment.
            # A hand thumb grandchild would instead observe wrist geometry and
            # hide the almost straight source elbow's poor conditioning.
            proximal_limb = name in ('LeftForeArm', 'RightForeArm', 'LeftShin', 'RightShin',
                                    'forearm.L', 'forearm.R', 'shin.L', 'shin.R')
            if proximal_limb and s['parents'][j] is not None:
                k = s['parents'][j]
                secondary, label = sub(rest[k], rest[j]), name+' -> '+s['names'][k]+' (proximal bend plane)'
            elif other:
                k = other[0]
                secondary, label = sub(rest[k], rest[j]), name+' -> '+s['names'][k]
            elif grandchildren:
                k = grandchildren[0]
                secondary, label = sub(rest[k], rest[c]), s['names'][c]+' -> '+s['names'][k]
            elif s['parents'][j] is not None:
                k = s['parents'][j]
                secondary, label = sub(rest[k], rest[j]), name+' -> '+s['names'][k]+' (proximal)'
        row = {'joint': name, 'primary': None if primary is None else {'vector_m': primary,
                   'landmark': name+' -> '+s['names'][c] if c is not None else 'incoming only; distal direction absent'},
               'secondary': None if secondary is None else {'vector_m': secondary, 'landmark': label},
               'terminal': c is None, 'sign_authority': 'pinned joint names and geometric order only; anatomical sign unverified',
               'anatomical_twist_status': 'HOLD', 'trusted_anatomical_frame': False}
        if primary is None or norm(primary) <= ZERO_TOL:
            row.update({'geometric_rank': 0, 'conditioning': 'UNOBSERVABLE', 'frame': None,
                        'projected_secondary_m': None, 'normalized_projection_sine': None,
                        'inverse_sine_sensitivity': None})
        elif secondary is None or norm(secondary) <= ZERO_TOL:
            row.update({'geometric_rank': 1, 'conditioning': 'SECONDARY_ABSENT', 'frame': None,
                        'projected_secondary_m': None, 'normalized_projection_sine': None,
                        'inverse_sine_sensitivity': None})
        else:
            x = unit(primary)
            projection = norm(cross(cross(x, secondary), x))
            sine = projection/norm(secondary)
            rank = 2 if sine > ZERO_TOL else 1
            # A number alone cannot certify anatomical twist. Report sensitivity
            # continuously; even the nearly straight elbows retain HOLD.
            row.update({'geometric_rank': rank, 'conditioning': 'GEOMETRY_ONLY' if rank == 2 else 'COLLINEAR',
                        'frame': frame_from_directions(primary, secondary) if rank == 2 else None,
                        'projected_secondary_m': projection, 'normalized_projection_sine': sine,
                        'inverse_sine_sensitivity': 1/sine if rank == 2 else None})
            if rank == 2:
                check_geometric_frame(row['frame'], primary, secondary)
        rows.append(row)
    return rows


def root_candidate(h, r, scale, pelvis, policy, rest):
    offset = mv(r, [x*y for x, y in zip(scale, pelvis)])
    exact = sub(h, offset)
    if policy == 'affine':
        return exact
    if policy == 'old43':
        return add(rest, h)
    if policy == 'unrotated_offset':
        return sub(h, [x*y for x, y in zip(scale, pelvis)])
    if policy == 'double_target_rest':
        return add(exact, rest)
    if policy == 'double_source_trajectory':
        return add(exact, h)
    if policy == 'exporter_height':
        return add(exact, [0., .988, 0.])
    if policy == 'transpose_rotation':
        return sub(h, mv(tr(r), [x*y for x, y in zip(scale, pelvis)]))
    raise ValueError('unknown root policy')


def root_oracle(s, roots, frames, basis, policy='affine', inconsistent_translation=False):
    require(s['parents'][:2] == [None, 0] and s['names'][:2] == ['root', 'pelvis'], 'unsupported pelvis hierarchy')
    points, scene, errors = [], [], []
    rest = [rotation(q) for q in s['rotations']]
    for h, qs in zip(roots, frames):
        desired = mv(basis, h)
        r = mm(mm(mm(basis, rotation(qs[0])), tr(basis)), rest[0])
        candidate_h = h if inconsistent_translation else desired
        t = root_candidate(candidate_h, r, s['scales'][0], s['translations'][1], policy, s['translations'][0])
        local = [r]+rest[1:]
        actual = affine_fk(s, local, t)[1]
        points.append(actual); scene.append(t); errors.append(norm(sub(actual, desired)))
    require(len(errors) == 90, 'all 90 frames required')
    return {'frames': len(errors), 'max_pelvis_world_error_m': max(errors),
            'per_frame_error_m': errors, 'numeric_status': 'PASS' if max(errors) <= ROOT_TOL else 'FAIL',
            'max_scene_root_vs_hips_difference_m': max(norm(sub(t, mv(basis, h))) for t, h in zip(scene, roots)),
            'scene_root_xz_path_m': sum(math.hypot(b[0]-a[0], b[2]-a[2]) for a, b in zip(scene, scene[1:])),
            'hips_xz_path_m': sum(math.hypot(b[0]-a[0], b[2]-a[2]) for a, b in zip(points, points[1:]))}


def check_root(result):
    require(type(result['frames']) is int and result['frames'] == 90, 'root frame count')
    e = result['max_pelvis_world_error_m']
    require(type(e) is float and math.isfinite(e) and e <= ROOT_TOL, 'pelvis-world oracle failed')


def admit_semantics(evidence):
    # This executable admission boundary explicitly requires independent authority.
    # A boolean claim, a numeric pass, or a proper geometric frame is insufficient.
    require(type(evidence) is dict and evidence.get('independent_signed_reference') is not None,
            'HOLD: independent signed anatomical reference missing')
    raise ValueError('HOLD: no independent signed reference is admitted by this experiment')


def representation_diagnostics(source, roots, frames):
    base = [affine_fk(source, [rotation(q) for q in qs], h) for h, qs in zip(roots, frames)]
    out = {}
    for name, transform in [('q_negated', lambda q: [-x for x in q]),
                            ('xyz_conjugated', lambda q: [-q[0], -q[1], -q[2], q[3]]),
                            ('XYWZ_misread', lambda q: [q[0], q[1], q[3], q[2]])]:
        altered = [affine_fk(source, [rotation(transform(q)) for q in qs], h) for h, qs in zip(roots, frames)]
        out[name] = max(norm(sub(x, y)) for a, b in zip(base, altered) for x, y in zip(a, b))
    twice = []
    for h, qs in zip(roots, frames):
        r = [rotation(q) for q in qs]
        wrong = [r[j] if p is None else mm(tr(r[p]), r[j]) for j, p in enumerate(source['parents'])]
        twice.append(affine_fk(source, wrong, h))
    out['parent_localized_twice'] = max(norm(sub(x, y)) for a, b in zip(base, twice) for x, y in zip(a, b))
    return out


def algebraic_basis_diagnostic(source, roots, frames, candidates):
    """One actual frame, all48 policies: algebra cannot identify a signed anchor."""
    local = [rotation(q) for q in frames[47]]
    original = affine_fk(source, local, roots[47])
    maximum = 0.
    for row in candidates:
        b = row['basis']
        s = dict(source, translations=[mv(b, t) for t in source['translations']])
        # Source scales are exactly unit; the target is not used in this invariant.
        require(all(v == [1, 1, 1] for v in source['scales']), 'unit source scale invariant scope')
        actual = affine_fk(s, [mm(mm(b, r), tr(b)) for r in local], mv(b, roots[47]))
        maximum = max(maximum, max(norm(sub(x, mv(b, y))) for x, y in zip(actual, original)))
    require(maximum < ROOT_TOL, 'coordinate equivariance')
    return {'frame_index': 47, 'proper': sum(r['determinant'] == 1 for r in candidates),
            'improper': sum(r['determinant'] == -1 for r in candidates),
            'max_fk_equivariance_error_m': maximum, 'meaning': 'numerical consistency only; not signed-reference evidence'}


def historical_endpoint_limits(source, target, roots, frames, basis):
    """43 rest-delta orientation, conditional root fix; no new mapper adoption."""
    sr = globals_(source, [rotation(q) for q in source['rotations']])
    tg = globals_(target, [rotation(q) for q in target['rotations']])
    out = {name: 0. for name in ('hand.L', 'hand.R', 'foot.L', 'foot.R')}
    for h, qs in zip(roots, frames):
        source_positions = affine_fk(source, [rotation(q) for q in qs], h)
        sg = globals_(source, [rotation(q) for q in qs])
        desired = []
        for j, name in enumerate(target['names']):
            k = source['names'].index(MAP[name])
            delta = mm(sg[k], tr(sr[k]))
            desired.append(mm(mm(mm(basis, delta), tr(basis)), tg[j]))
        local = [r if p is None else mm(tr(desired[p]), r) for p, r in zip(target['parents'], desired)]
        t = root_candidate(mv(basis, h), desired[0], target['scales'][0], target['translations'][1], 'affine', target['translations'][0])
        target_positions = affine_fk(target, local, t)
        for name in out:
            a = target_positions[target['names'].index(name)]
            b = mv(basis, source_positions[source['names'].index(MAP[name])])
            out[name] = max(out[name], norm(sub(a, b)))
    return {'max_named_endpoint_difference_m': out,
            'meaning': 'historical43 orientation rule after conditional root fix; differences mix rest directions, lengths and removed offsets; not a quality bound'}


def rest_diagnostics(source, target):
    sr = affine_fk(source, [rotation(q) for q in source['rotations']], source['translations'][0])
    tl = [rotation(q) for q in target['rotations']]
    tp = affine_fk(target, tl, target['translations'][0])
    rows = []
    for a, b in [('upper_arm.L', 'forearm.L'), ('forearm.L', 'hand.L'),
                 ('upper_arm.R', 'forearm.R'), ('forearm.R', 'hand.R'),
                 ('thigh.L', 'shin.L'), ('shin.L', 'foot.L'),
                 ('thigh.R', 'shin.R'), ('shin.R', 'foot.R')]:
        sv = sub(sr[source['names'].index(MAP[b])], sr[source['names'].index(MAP[a])])
        tv = sub(tp[target['names'].index(b)], tp[target['names'].index(a)])
        rows.append({'segment': a+' -> '+b, 'source_direction': unit(sv), 'target_direction': unit(tv),
                     'source_length_m': norm(sv), 'target_length_m': norm(tv),
                     'identity_direction_error_rad': angle(sv, tv),
                     'x_reflection_direction_error_rad': angle([-sv[0], sv[1], sv[2]], tv)})
    return {'segments': rows, 'source_neutral': 'pinned static rest; frame zero is animated and is not a neutral reference',
            'target_neutral': 'pinned authored bind pose',
            'transfer_mode_selected': None, 'neutral_relative_anatomical_reference': None,
            'twist_rule': 'HOLD without signed secondary reference. Bind rotations/global forward may define an explicitly adopted gauge only; none is adopted here.',
            'collapsed_chain_twist': 'No twist distribution chosen. Historical43 multiplies removed-link rotations and omits their moving translations.',
            'endpoint_limit': 'Lengths, removed positional links and T-like versus A-like rest geometry prevent interpreting endpoint fit as semantic acceptance.'}


def analyze():
    source, target, roots, frames, eyes = load_inputs()
    qerr = max(abs(norm(q)-1) for qs in frames for q in qs)
    require(qerr < 1e-7, 'raw quaternion norm')
    policies = signed_policies()
    equivariance = algebraic_basis_diagnostic(source, roots, frames, policies['candidates'])
    root_results = {}
    reflection = [[-1, 0, 0], [0, 1, 0], [0, 0, 1]]
    for label, basis in [('identity_conditional', I), ('x_reflection_conditional', reflection)]:
        root_results[label] = root_oracle(target, roots, frames, basis)
        check_root(root_results[label])
    root_negatives = {p: root_oracle(target, roots, frames, I, p) for p in (
        'old43', 'unrotated_offset', 'double_target_rest', 'double_source_trajectory', 'exporter_height', 'transpose_rotation')}
    root_negatives['basis_rotations_without_translation'] = root_oracle(target, roots, frames, reflection, inconsistent_translation=True)
    require(all(r['numeric_status'] == 'FAIL' for r in root_negatives.values()), 'root negatives must fail actual oracle')
    representation = representation_diagnostics(source, roots, frames)
    require(representation['q_negated'] == 0. and all(v > .7 for k, v in representation.items() if k != 'q_negated'), 'representation controls')
    source_rest = affine_fk(source, [rotation(q) for q in source['rotations']], source['translations'][0])
    target_rest = affine_fk(target, [rotation(q) for q in target['rotations']], target['translations'][0])
    left = lambda s, p, a, b: sub(p[s['names'].index(a)], p[s['names'].index(b)])
    return {'schema_version': 1, 'issue': 59, 'kind': 'offline fixed-sample reference diagnostics',
        'input_sha256': PINS, 'script_sha256': sha(Path(__file__).read_bytes()),
        'provenance_kind': 'generated', 'frames': 90, 'source_joints': 30, 'target_joints': 18, 'fps': 30,
        'provenance_scope': 'Original public44 sample only. All transformed quantities are diagnostic controls; no generated product artifact is admitted.',
        'max_raw_quaternion_norm_error': qerr, 'raw_floats_finite': True,
        'tolerances': {'root_world_m': ROOT_TOL, 'frame_algebra': FRAME_TOL, 'numerical_rank_sine': ZERO_TOL,
                       'anatomical_conditioning_threshold': None},
        'reference_anchors': {
            'source_up': {'signed_axis': '+Y', 'authority': 'pinned41 metadata declaration; trained-data parity unverified'},
            'source_front': {'signed_axis': '+Z',
                'left_toe_minus_foot_m': left(source, source_rest, 'LeftToeBase', 'LeftFoot'),
                'left_eye_minus_head_m': left(source, source_rest, 'LeftEye', 'Head'),
                'authority': 'pinned41 metadata declaration and toe/eye offsets; trained-data parity unverified'},
            'source_named_left': {'signed_axis': '+X', 'geometry_left_minus_right_m': left(source, source_rest, 'LeftLeg', 'RightLeg'), 'authority': 'pinned41 names/offsets; anatomical label unverified'},
            'target_up': {'signed_axis': '+Y', 'authority': 'pinned generator export and actual bind geometry'},
            'target_front': {'signed_axis': '+Z', 'eye_centroids_m': eyes, 'authority': 'pinned generator eye/front placement corroborated by actual GLB POSITION vertices'},
            'target_named_left': {'signed_axis': '-X', 'geometry_left_minus_right_m': left(target, target_rest, 'thigh.L', 'thigh.R'), 'authority': 'pinned generator side=-1 for L and actual bind geometry; anatomical label unverified'}},
        'signed_policies': policies,
        'all48_algebraic_invariance': equivariance,
        'observability': {'source': frame_observability(source), 'target': frame_observability(target)},
        'neutral_geometry': rest_diagnostics(source, target), 'root_candidates': root_results,
        'historical43_endpoint_limits': {label: historical_endpoint_limits(source, target, roots, frames, b)
            for label, b in [('identity_conditional', I), ('x_reflection_conditional', reflection)]},
        'root_negative_controls': root_negatives, 'representation_max_fk_position_change_m': representation,
        'root_scope': {'scale': target['scales'][0], 'units_policy': '1 metre/metre; no height fit',
                       'hierarchy': 'identity nonjoint scene ancestor; pelvis directly under joint root',
                       'equation': 'absolute scene translation = B*h - R*S*pelvis_local_rest',
                       'rotation_assumption': 'R = (B*R_source_Hips(t)*B^-1)*R_target_root_bind. This is a declared conditional convention, not an independently identified target orientation.',
                       'oracle': 'generic 4x4 affine pelvis WORLD position for all90; scene-root path equality is not required',
                       'nonunit_root_scale_support': 'NOT-RUN on this fixed unit-scale fixture'},
        'numerical_calibration': 'PASS conditional root arithmetic only',
        'anatomical_semantic_admission': 'HOLD', 'target_playable_admission': 'HOLD',
        'missing_references': ['independent signed anatomical up/front/left and parity authority',
                               'signed palm/sole or explicitly reviewed authored twist gauge for target leaf joints',
                               'trusted neutral/twist reference; near-collinear elbows do not provide stable anatomical roll'],
        'not_run': ['pose transfer adoption', 'normalized motion', 'export', 'generated Work', 'native/Web playback',
                    'contact/quality/scale-fitting admission', 'new inference', 'trained-data semantic parity']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()  # Deliberately stdout-only: no overwrite or symlink surface.
    try:
        sys.stdout.write(encode(analyze()).decode())
    except (ValueError, OSError, KeyError, TypeError, struct.error) as error:
        sys.stderr.write(json.dumps({'code': 'calibration_rejected', 'message': str(error)})+'\n')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
