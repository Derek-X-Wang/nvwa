#!/usr/bin/env python3
"""Fixture-only, explicitly authored calibration candidate. Standard library only.

This creates diagnostic quantities, never a normalized clip or playable Work.
No vendor/model source is imported or executed. Candidate policy is reviewable
in calibration.json; source and target input bytes remain immutable.
"""
import ast
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
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
TARGET = ['root', 'pelvis', 'spine', 'chest', 'neck', 'head',
          'upper_arm.L', 'forearm.L', 'hand.L', 'upper_arm.R', 'forearm.R', 'hand.R',
          'thigh.L', 'shin.L', 'foot.L', 'thigh.R', 'shin.R', 'foot.R']
SOURCE_MAP = ['Hips', 'Hips', 'Spine1', 'Chest', 'Neck1', 'Head', 'LeftArm',
              'LeftForeArm', 'LeftHand', 'RightArm', 'RightForeArm', 'RightHand',
              'LeftLeg', 'LeftShin', 'LeftFoot', 'RightLeg', 'RightShin', 'RightFoot']
DISTAL = dict(zip(SOURCE_MAP[2:], ['Spine2', 'Neck1', 'Neck2', 'Jaw',
              'LeftForeArm', 'LeftHand', 'LeftHandMiddleEnd', 'RightForeArm',
              'RightHand', 'RightHandMiddleEnd', 'LeftShin', 'LeftFoot',
              'LeftToeBase', 'RightShin', 'RightFoot', 'RightToeBase']))
DISTAL['Hips'] = 'Spine1'
DISTAL['Head'] = 'Head'  # incoming Neck2->Head, rather than face-forward Head->Jaw
I = [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]]
BASIS = [[-1., 0., 0.], [0., 1., 0.], [0., 0., 1.]]
TOL = 1e-10


def candidate_policy(label):
    require(label in ('named_labels_reflected', 'physical_sides_identity'), 'named candidate')
    if label == 'named_labels_reflected':
        return BASIS, list(SOURCE_MAP)
    swapped = [n.replace('Left', 'TEMP').replace('Right', 'Left').replace('TEMP', 'Right') for n in SOURCE_MAP]
    return I, swapped


def require(ok, message):
    if not ok:
        raise ValueError(message)


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def vector(x, n=3):
    require(type(x) is list and len(x) == n and
            all(type(v) in (float, int) and math.isfinite(v) for v in x), 'finite vector')
    return x


def mm(a, b):
    return [[sum(x*y for x, y in zip(row, col)) for col in zip(*b)] for row in a]


def tr(a):
    return [list(x) for x in zip(*a)]


def mv(a, v):
    return [sum(x*y for x, y in zip(row, v)) for row in a]


def sub(a, b):
    return [x-y for x, y in zip(a, b)]


def add(a, b):
    return [x+y for x, y in zip(a, b)]


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def norm(v):
    return math.sqrt(dot(v, v))


def unit(v):
    vector(v, len(v))
    n = norm(v)
    require(n > 1e-12, 'nonzero direction')
    return [x/n for x in v]


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def rotation(q):
    vector(q, 4)
    x, y, z, w = unit(q)
    return [[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
            [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
            [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]]


def validate_rotation(r):
    require(type(r) is list and len(r) == 3, 'rotation rows')
    for row in r:
        vector(row)
    require(max(abs(v-I[i][j]) for i, row in enumerate(mm(tr(r), r))
                for j, v in enumerate(row)) < TOL and
            abs(dot(r[0], cross(r[1], r[2]))-1) < TOL, 'proper orthonormal rotation')


def globals_(parents, local):
    out = []
    for p, r in zip(parents, local):
        out.append(r if p is None else mm(out[p], r))
    return out


def affine_transforms(s, local, root):
    """General affine composition: scales and parent transforms are composed once."""
    out = []
    for j, p in enumerate(s['parents']):
        t = root if p is None else s['translations'][j]
        a = [[local[j][r][c]*s['scales'][j][c] for c in range(3)]+[t[r]] for r in range(3)]
        a.append([0., 0., 0., 1.])
        out.append(a if p is None else mm(out[p], a))
    return out


def fk(s, local, root):
    return [[a[k][3] for k in range(3)] for a in affine_transforms(s, local, root)]


def inverse3(a):
    determinant = dot(a[0], cross(a[1], a[2]))
    require(abs(determinant) > 1e-12, 'invertible marker bind transform')
    cofactors = tr([cross(a[1], a[2]), cross(a[2], a[0]), cross(a[0], a[1])])
    return [[v/determinant for v in row] for row in cofactors]


def validate_skeleton(s):
    n = len(s['names'])
    require(n > 0 and len(set(s['names'])) == n, 'unique joint names')
    for k in ('parents', 'translations', 'rotations', 'scales'):
        require(type(s[k]) is list and len(s[k]) == n, 'skeleton shape')
    for j, p in enumerate(s['parents']):
        require((j == 0 and p is None) or (type(p) is int and 0 <= p < j), 'parent order')
        vector(s['translations'][j]); vector(s['scales'][j]); rotation(s['rotations'][j])
        require(all(v > 0 for v in s['scales'][j]), 'positive fixture scales')


def parse_target(data):
    require(data[:4] == b'glTF' and struct.unpack_from('<II', data, 4) == (2, len(data)), 'GLB header')
    length, kind = struct.unpack_from('<II', data, 12)
    require(kind == 0x4e4f534a, 'GLB JSON')
    g = json.loads(data[20:20+length])
    require(len(g['skins']) == 1, 'one fixture skin')
    joints = g['skins'][0]['joints']
    parents = {c: p for p, node in enumerate(g['nodes']) for c in node.get('children', [])}
    ancestor = parents[joints[0]]
    node = g['nodes'][ancestor]
    require(node.get('translation', [0, 0, 0]) == [0, 0, 0] and
            node.get('rotation', [0, 0, 0, 1]) == [0, 0, 0, 1] and
            node.get('scale', [1, 1, 1]) == [1, 1, 1] and 'matrix' not in node and
            ancestor in g['scenes'][g.get('scene', 0)]['nodes'], 'identity scene ancestor')
    nodes = [g['nodes'][j] for j in joints]
    require(all('matrix' not in x for x in nodes), 'joint TRS required')
    s = {'names': [x['name'] for x in nodes],
         'parents': [joints.index(parents[j]) if parents[j] in joints else None for j in joints],
         'translations': [x.get('translation', [0., 0., 0.]) for x in nodes],
         'rotations': [x.get('rotation', [0., 0., 0., 1.]) for x in nodes],
         'scales': [x.get('scale', [1., 1., 1.]) for x in nodes]}
    validate_skeleton(s)
    require(s['names'] == TARGET and s['parents'][:2] == [None, 0], 'exact Nvwa18 hierarchy')
    require(s['scales'][:2] == [[1, 1, 1], [1, 1, 1]], 'exact unit root/pelvis scale')
    return s


def load_inputs(blobs=None):
    blobs = {name: (ROOT/name).read_bytes() for name in PINS} if blobs is None else blobs
    require(type(blobs) is dict and blobs.keys() == PINS.keys(), 'exact input identities')
    for name, digest in PINS.items():
        require(type(blobs[name]) is bytes and sha(blobs[name]) == digest, 'SHA256 mismatch: '+name)
    meta = json.loads(blobs['experiments/41-real-short-motion/source-skeleton.json'])
    require(meta['units'] == 'meters' and meta['up_axis'] == '+Y' and meta['forward_axis'] == '+Z', 'source axis declarations')
    source = {'names': meta['joint_names'], 'parents': [None if p == -1 else p for p in meta['parents']],
              'translations': meta['rest_local_translations'], 'rotations': meta['rest_local_rotations_xyzw'],
              'scales': meta['rest_local_scales']}
    validate_skeleton(source)
    require(all(v == [1, 1, 1] for v in source['scales']), 'unit source scale')
    require(len(source['names']) == 30 and source['names'][0] == 'Hips', 'SOMA30 identity')
    target = parse_target(blobs['assets/fixtures/nvwa-humanoid.glb'])
    manifest = json.loads(blobs['assets/fixtures/provenance-manifest.json'])
    published = {r['path']: r['sha256'] for r in manifest['files']}
    require(all(published[n] == PINS[n] for n in ('assets/fixtures/nvwa-humanoid.glb',
            'tools/blender/generate_fixture.py')), 'fixture generator binding')
    receipt = json.loads(blobs['experiments/44-approved-cpu-motion-trial/evidence/run/generation-receipt.json'])
    require(type(receipt['returncode']) is int and receipt['returncode'] == 0 and
            receipt['reason'] == 'exited' and receipt['raw_complete'] is True, 'genuine generation receipt')
    require(type(receipt['request']['frames']) is int and receipt['request']['frames'] == 90 and
            type(receipt['request']['fps']) is int and receipt['request']['fps'] == 30, '90-frame 30fps identity')
    bound = {RAW+Path(x['path']).name: x['sha256'] for x in receipt['raw_provenance']}
    require(len(receipt['raw_provenance']) == 2 and bound == {RAW+x: PINS[RAW+x]
            for x in ('root_positions.f32', 'local_rotations_xyzw.f32')}, 'raw provenance binding')
    rb, qb = blobs[RAW+'root_positions.f32'], blobs[RAW+'local_rotations_xyzw.f32']
    require(len(rb) == 1080 and len(qb) == 43200, 'raw byte shape')
    rr, qq = struct.unpack('<270f', rb), struct.unpack('<10800f', qb)
    require(all(math.isfinite(v) for v in rr+qq), 'finite raw arrays')
    roots = [list(rr[i:i+3]) for i in range(0, 270, 3)]
    frames = [[list(qq[(t*30+j)*4:(t*30+j+1)*4]) for j in range(30)] for t in range(90)]
    require(max(abs(norm(q)-1) for qs in frames for q in qs) < 1e-7, 'near-unit raw quaternions')
    return source, target, roots, frames, blobs


def literal(node, env):
    """Tiny AST reader for coordinates only. Never eval/exec/import generator code."""
    if isinstance(node, ast.Constant) and type(node.value) in (str, int, float):
        return node.value
    if isinstance(node, (ast.Tuple, ast.List)):
        return [literal(x, env) for x in node.elts]
    if isinstance(node, ast.Name) and node.id in env:
        return env[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -literal(node.operand, env)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mult)):
        a, b = literal(node.left, env), literal(node.right, env)
        return a+b if isinstance(node.op, ast.Add) else a*b
    raise ValueError('unsupported coordinate AST')


def generator_bones(data):
    tree = ast.parse(data)
    bones = {}

    def take(statement, env):
        if (isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call) and
                isinstance(statement.value.func, ast.Name) and statement.value.func.id == 'bone'):
            args = [literal(x, env) for x in statement.value.args]
            bones[args[0]] = {'head': args[1], 'tail': args[2], 'parent': args[3] if len(args) == 4 else None}

    for statement in tree.body:
        take(statement, {})
        if isinstance(statement, ast.For) and isinstance(statement.target, ast.Tuple):
            if [x.id for x in statement.target.elts] == ['side', 'suffix']:
                for side, suffix in literal(statement.iter, {}):
                    for child in statement.body:
                        take(child, {'side': side, 'suffix': suffix})
    require(list(bones) == TARGET[:6]+TARGET[6:9]+TARGET[12:15]+TARGET[9:12]+TARGET[15:18], 'generator bone identity')
    # Exact pinned generator contains the explicit bone roll instruction.
    require(b'eb.align_roll(Vector((0,-1,0)))' in data, 'generator front roll reference')
    return bones


def blender_to_gltf(v):
    return [v[0], v[2], -v[1]]


def geometric_frame(primary, guide):
    x = unit(primary)
    y = unit(cross(cross(x, guide), x))
    frame = tr([x, y, unit(cross(x, y))])
    validate_rotation(frame)
    return frame


def build_calibration(source, target, generator, basis=None, source_map=None, label='named_labels_reflected'):
    """Construct the named, reversible candidate; no sample fitting occurs here."""
    b = BASIS if basis is None else basis
    require(type(b) is list and len(b) == 3, 'basis rows')
    for r in b:
        vector(r)
    require(max(abs(v-I[i][j]) for i, r in enumerate(mm(tr(b), b)) for j, v in enumerate(r)) < TOL,
            'orthogonal signed basis')
    source_map = SOURCE_MAP if source_map is None else source_map
    require(type(source_map) is list and len(source_map) == 18 and source_map[:2] == ['Hips', 'Hips'] and
            all(n in DISTAL for n in source_map), 'explicit source correspondence')
    sr = [rotation(q) for q in source['rotations']]
    tg = globals_(target['parents'], [rotation(q) for q in target['rotations']])
    sg = globals_(source['parents'], sr)
    sp = fk(source, sr, source['translations'][0])
    tp = fk(target, [rotation(q) for q in target['rotations']], target['translations'][0])
    bind_affine = affine_transforms(target, [rotation(q) for q in target['rotations']], target['translations'][0])
    bones = generator_bones(generator)
    rows = []
    for j, name in enumerate(TARGET):
        k = source['names'].index(source_map[j])
        distal = source['names'].index(DISTAL[source_map[j]])
        start_name = 'Neck2' if source_map[j] == 'Head' else source_map[j]
        start = source['names'].index(start_name)
        primary_s = mv(b, sub(sp[distal], sp[start]))
        bone = bones[name]
        head, tail = blender_to_gltf(bone['head']), blender_to_gltf(bone['tail'])
        require(norm(sub(head, tp[j])) < 2e-7, 'generator head vs actual bind: '+name)
        require(bone['parent'] == (None if target['parents'][j] is None else TARGET[target['parents'][j]]), 'generator hierarchy')
        primary_t = sub(tail, head)
        # The actual exported bind local +Y must follow the authored bone tail.
        require(norm(sub(mv(tg[j], [0., 1., 0.]), unit(primary_t))) < 2e-6, 'generator tail vs bind axis: '+name)
        guide = [0., 1., 0.] if name.startswith('foot.') else [0., 0., 1.]
        fs, ft = geometric_frame(primary_s, guide), geometric_frame(primary_t, guide)
        gs = mm(mm(b, sg[k]), tr(b))
        # A expresses geometric gauge axes in each joint's static rest coordinates.
        a_s, a_t = mm(tr(gs), fs), mm(tr(tg[j]), ft)
        bind_inverse = inverse3([r[:3] for r in bind_affine[j][:3]])
        markers = {axis: mv(bind_inverse, mv(ft, vector_)) for axis, vector_ in
                   [('primary', [.1, 0., 0.]), ('secondary', [0., .1, 0.])]}
        rows.append({'target': name, 'source': source_map[j], 'source_distal': DISTAL[source_map[j]],
                     'source_primary_start': start_name,
                     'target_parent': None if target['parents'][j] is None else TARGET[target['parents'][j]],
                     'source_primary_m': primary_s, 'target_primary_m': primary_t,
                     'target_head_m': head, 'target_tail_m': tail, 'guide': guide,
                     'source_frame': fs, 'target_frame': ft,
                     'source_rest_gauge': a_s, 'target_rest_gauge': a_t,
                     'orientation_markers_local_m': markers,
                     'marker_authority': 'AUTHORED_0.1_METRE_GAUGE_MARKERS_INVERTED_THROUGH_EXACT_AFFINE_BIND',
                     'foot_down_marker': 'negative secondary' if name.startswith('foot.') else None,
                     'generator_head_bind_residual_m': norm(sub(head, tp[j])),
                     'generator_tail_bind_rotation_axis_residual': norm(sub(mv(tg[j], [0., 1., 0.]), unit(primary_t))),
                     'delta_basis': mm(a_t, tr(a_s)),
                     'roll_authority': 'AUTHORED_ENGINEERING_GAUGE',
                     'primary_authority': 'PINNED_SOURCE_STATIC_DISTAL / PINNED_TARGET_GENERATOR_HEAD_TAIL',
                     'recovered_anatomical_twist': False,
                     'source_guide_projection_sine': norm(cross(unit(primary_s), guide)),
                     'target_guide_projection_sine': norm(cross(unit(primary_t), guide))})
    return {'schema': 'nvwa.fixture-calibration-candidate.v1', 'status': 'PROPOSED_NOT_ADMITTED',
            'scope': 'exact SOMA30 metadata / exact Nvwa18 fixture / existing 90 frames only',
            'candidate': label, 'basis': b,
            'implementation_selection': 'ROOT_SELECTED_PENDING_R2' if label == 'physical_sides_identity' else 'REJECTED_PHYSICAL_POLICY_COMPARATOR',
            'basis_authority': 'INDEPENDENT_DOCUMENTED_AXES_AND_FACE_UP_PHYSICAL_SIDE_REFERENCE',
            'independent_authority_first_report_sha256': '9ddd992efb4af47cd524ec55124a28889448208541f4a73ab08f7a74462a19d2',
            'root_policy_decision_sha256': 'c5c1b0ef3deac7410f0b6da1e05490d347fd0189219b7898a741ac6dcb0f8d67',
            'independent_static_physical_side_supported': True,
            'runtime_decoder_parity_verified': False, 'anatomical_twist_recovered': False,
            'authorities': {
                'up': 'source41 +Y declaration and source torso rest; fixture generator +Z Blender maps to +Y glTF',
                'front': 'source41 +Z declaration, source eye/jaw/toe geometry; fixture negative Blender Y nose/eyes maps to +Z glTF',
                'side': 'root selects physical identity and sourceLeft->target.R / sourceRight->target.L from independent original-source face/up audit; named reflection is rejected comparator',
                'neutral': 'pinned static source rest and exact target bind, independently distinct from animated frame zero',
                'twist': 'authored projected-front gauge (feet projected-up); no claim of recovered anatomical palm/sole normal',
                'chains': 'authored collapse of omitted rotations into next mapped descendant; omitted moving translations stay omitted'},
            'neutral': 'pinned static source rest and exact target bind; never frame zero',
            'delta_policy': 'collapsed-chain parent-local neutral-relative gauge conjugation',
            'root_policy': 'source Hips delta once on root; pelvis bind rotation; absolute Hips world position once',
            'translation_policy': 'target bind translations fixed; omitted moving source links not transferred',
            'scale_policy': 'exact fixture bind scales preserved / unit scene-root scale / 1 metre per metre; no endpoint fitting or contact guarantee',
            'singularity_rule': 'static-only gauge; secondary is +Z except feet +Y; reject projection sine <=1e-12; no fallback or per-frame frame reconstruction',
            'rows': rows, 'input_sha256': PINS}


def check_physical_policy(calibration):
    """Independent reference admission subcheck, never overall calibration admission."""
    b = calibration['basis']
    for axis in ([1., 0., 0.], [0., 1., 0.], [0., 0., 1.]):
        require(norm(sub(mv(b, axis), axis)) < TOL, 'independent physical side/up/front mismatch')
    expected = candidate_policy('physical_sides_identity')[1]
    require([r['source'] for r in calibration['rows']] == expected, 'independent physical source correspondence mismatch')
    return 'PASS'


def map_frame(source, target, calibration, qs, hips, neutral=None):
    """The candidate production path used by every positive and mutation control."""
    require(len(qs) == len(source['names']), 'source frame joint count')
    vector(hips)
    b = calibration['basis']
    local_s = [rotation(q) for q in qs]
    local_rest = [rotation(q) for q in (source['rotations'] if neutral is None else neutral)]
    gs = globals_(source['parents'], local_s)
    gr = globals_(source['parents'], local_rest)
    rest_t = [rotation(q) for q in target['rotations']]
    out = []
    for j, row in enumerate(calibration['rows']):
        k = source['names'].index(row['source'])
        p = target['parents'][j]
        if j == 1:  # Hips already rotates the scene root; do not apply it twice.
            out.append(rest_t[j])
            continue
        if p is None:
            animated, static = gs[k], gr[k]
        else:
            pk = source['names'].index(calibration['rows'][p]['source'])
            animated, static = mm(tr(gs[pk]), gs[k]), mm(tr(gr[pk]), gr[k])
        delta = mm(tr(static), animated)
        delta = mm(mm(b, delta), tr(b))
        c = row['delta_basis']
        out.append(mm(rest_t[j], mm(mm(c, delta), tr(c))))
    for r in out:
        validate_rotation(r)
    desired_hips = mv(b, hips)
    root = sub(desired_hips, mv(out[0], target['translations'][1]))
    return out, root


def candidate_directions(target, local, calibration):
    """Actual affine signed markers, with every exact nonunit descendant scale."""
    animated = affine_transforms(target, local, [0., 0., 0.])
    return [{'joint': row['target'], 'kind': 'authored_affine_orientation_markers',
             **{axis: unit(mv([r[:3] for r in animated[j][:3]], row['orientation_markers_local_m'][axis]))
                for axis in ('primary', 'secondary')}} for j, row in enumerate(calibration['rows'])]


def analyze(label='named_labels_reflected'):
    source, target, roots, frames, blobs = load_inputs()
    basis, source_map = candidate_policy(label)
    cal = build_calibration(source, target, blobs['tools/blender/generate_fixture.py'], basis, source_map, label)
    outputs, errors, motion = [], [], []
    for h, qs in zip(roots, frames):
        local, root = map_frame(source, target, cal, qs, h)
        points = fk(target, local, root)
        errors.append(norm(sub(points[1], mv(cal['basis'], h))))
        dirs = candidate_directions(target, local, cal)
        motion.append({'frame': len(motion), 'pelvis_world_error_m': errors[-1],
                       'root_translation_m': root,
                       'directions': [d for d in dirs if d['joint'] in ('hand.L', 'hand.R', 'foot.L', 'foot.R')]})
        outputs.append(points)
    require(len(errors) == 90 and max(errors) < 1e-12, 'all90 pelvis-world oracle')
    neutral, root = map_frame(source, target, cal, source['rotations'], [0., 0., 0.])
    rest = [rotation(q) for q in target['rotations']]
    neutral_error = max(abs(x-y) for a, b in zip(neutral, rest) for ar, br in zip(a, b) for x, y in zip(ar, br))
    require(neutral_error < TOL, 'static neutral maps to target bind')
    try:
        physical_status = check_physical_policy(cal)
    except ValueError:
        physical_status = 'REJECT'
    return cal, {'schema': 'nvwa.fixture-calibration-diagnostics.v1', 'status': 'PROPOSED_NOT_ADMITTED',
                 'candidate': label,
                 'independent_physical_reference_subcheck': physical_status,
                 'raw_provenance': 'generated; unchanged public44 input bytes',
                 'derived_values': 'fixture engineering calibration diagnostics only; not playable export',
                 'frames': 90, 'fps': 30, 'source_joints': 30, 'target_joints': 18,
                 'max_pelvis_world_error_m': max(errors), 'neutral_bind_matrix_error': neutral_error,
                 'minimum_gauge_projection_sine': min(min(r['source_guide_projection_sine'], r['target_guide_projection_sine']) for r in cal['rows']),
                 'max_generator_head_bind_residual_m': max(r['generator_head_bind_residual_m'] for r in cal['rows']),
                 'max_generator_tail_bind_rotation_axis_residual': max(r['generator_tail_bind_rotation_axis_residual'] for r in cal['rows']),
                 'max_target_endpoint_step_m': {n: max(norm(sub(outputs[i][TARGET.index(n)], outputs[i-1][TARGET.index(n)]))
                      for i in range(1, 90)) for n in ('hand.L', 'hand.R', 'foot.L', 'foot.R')},
                 'endpoint_step_meaning': 'observations only; no quality/contact or source-endpoint-fit acceptance threshold',
                 'per_frame': motion, 'input_sha256': PINS}


if __name__ == '__main__':
    bundle = {}
    for label in ('named_labels_reflected', 'physical_sides_identity'):
        calibration, result = analyze(label)
        bundle[label] = {'calibration': calibration, 'results': result}
    print(encode(bundle).decode(), end='')
