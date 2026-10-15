#!/usr/bin/env python3
"""Bounded authored SOMA-layout -> frozen Nvwa18 rotation experiment. Stdlib only.

No inference, GLB exporter, IK, or production retargeter. See REPORT.md.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FIXTURE_HASH = "f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6"
CONTRACT_HASH = "74bb268930428195242a99cffe6fd3307338be2dbd435583212607185a6bb257"
I = [0.0, 0.0, 0.0, 1.0]
MAP = dict(zip(
    ['root', 'pelvis', 'spine', 'chest', 'neck', 'head', 'upper_arm.L', 'forearm.L',
     'hand.L', 'upper_arm.R', 'forearm.R', 'hand.R', 'thigh.L', 'shin.L', 'foot.L',
     'thigh.R', 'shin.R', 'foot.R'],
    ['Hips', 'Hips', 'Spine1', 'Chest', 'Neck1', 'Head', 'LeftArm', 'LeftForeArm',
     'LeftHand', 'RightArm', 'RightForeArm', 'RightHand', 'LeftLeg', 'LeftShin',
     'LeftFoot', 'RightLeg', 'RightShin', 'RightFoot']))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def add(a, b):
    return [x + y for x, y in zip(a, b)]


def sub(a, b):
    return [x - y for x, y in zip(a, b)]


def length(v):
    return math.sqrt(sum(x*x for x in v))


def unit(q):
    n = length(q)
    if not math.isfinite(n) or n < 1e-12:
        raise ValueError('invalid quaternion')
    return [x / n for x in q]


def mul(a, b):
    x, y, z, w = a
    X, Y, Z, W = b
    return [w*X+x*W+y*Z-z*Y, w*Y-x*Z+y*W+z*X,
            w*Z+x*Y-y*X+z*W, w*W-x*X-y*Y-z*Z]


def inv(q):
    q = unit(q)
    return [-q[0], -q[1], -q[2], q[3]]


def axis(axis_index, angle):
    q = [0., 0., 0., math.cos(angle/2)]
    q[axis_index] = math.sin(angle/2)
    return q


def rotation(q):
    x, y, z, w = unit(q)
    return [[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
            [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
            [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]]


def mm(a, b):
    return [[sum(x*y for x, y in zip(row, col)) for col in zip(*b)] for row in a]


def mv(a, b):
    return [sum(x*y for x, y in zip(row, b)) for row in a]


def transpose(a):
    return [list(x) for x in zip(*a)]


def globals_q(s, qs):
    out = []
    for p, q in zip(s['parent_indices'], qs):
        out.append(unit(q if p is None else mul(out[p], q)))
    return out


def fk(s, qs, root, scales=True):
    """Independent 4x4 affine FK: scales participate before parent composition."""
    out = []
    for j, p in enumerate(s['parent_indices']):
        r = rotation(qs[j])
        scale = s['rest_local_scales_xyz'][j] if scales else [1, 1, 1]
        t = root if p is None else s['rest_local_translations_m'][j]
        m = [[r[a][b]*scale[b] for b in range(3)] + [t[a]] for a in range(3)]
        m.append([0., 0., 0., 1.])
        out.append(m if p is None else mm(out[p], m))
    return [[m[a][3] for a in range(3)] for m in out]


def matrix_globals(s, qs):
    """Oracle uses matrix products rather than quaternion chain multiplication."""
    out = []
    for p, q in zip(s['parent_indices'], qs):
        r = rotation(q)
        out.append(r if p is None else mm(out[p], r))
    return out


def oracle_positions(target, desired, root):
    """Target FK from independent desired global matrices and exact local scales."""
    affine = []
    for j, p in enumerate(target['parent_indices']):
        local = desired[j] if p is None else mm(transpose(desired[p]), desired[j])
        t = root if p is None else target['rest_local_translations_m'][j]
        scale = target['rest_local_scales_xyz'][j]
        m = [[local[a][b]*scale[b] for b in range(3)] + [t[a]] for a in range(3)]
        m.append([0., 0., 0., 1.])
        affine.append(m if p is None else mm(affine[p], m))
    return [[m[a][3] for a in range(3)] for m in affine]


def fixture():
    b = (ROOT / 'assets/fixtures/nvwa-humanoid.glb').read_bytes()
    assert sha(b) == FIXTURE_HASH
    size, kind = struct.unpack_from('<II', b, 12)
    assert kind == 0x4e4f534a
    g = json.loads(b[20:20+size])
    joints = g['skins'][0]['joints']
    parents = {c: p for p, n in enumerate(g['nodes']) for c in n.get('children', [])}
    # A nonjoint parent must be identity for these joint-local FK calculations.
    outside = g['nodes'][parents[joints[0]]]
    assert outside.get('translation', [0, 0, 0]) == [0, 0, 0]
    assert outside.get('rotation', I) == I and outside.get('scale', [1, 1, 1]) == [1, 1, 1]
    assert 'matrix' not in outside
    nodes = [g['nodes'][i] for i in joints]
    s = {'identity': 'nvwa18', 'joint_names': [n['name'] for n in nodes],
         'parent_indices': [joints.index(parents[i]) if parents[i] in joints else None for i in joints],
         'rest_local_translations_m': [n.get('translation', [0., 0., 0.]) for n in nodes],
         'rest_local_rotations_xyzw': [n.get('rotation', I) for n in nodes],
         'rest_local_scales_xyz': [n.get('scale', [1., 1., 1.]) for n in nodes]}
    assert s['joint_names'] == list(MAP)
    assert all(p is None or p < j for j, p in enumerate(s['parent_indices']))
    return s


def authored_source(target, rows, identity):
    """Official hierarchy; deliberately authored rest positions and nonidentity bases.

    Shared 30/77 joints have identical rest global transforms. Extra 77 end joints
    use arbitrary small positive offsets; these are controls, never SOMA rest assets.
    """
    names = [n for n, _ in rows]
    ps = [None if p is None else names.index(p) for _, p in rows]
    tq = target['rest_local_rotations_xyzw']
    tp = fk(target, tq, target['rest_local_translations_m'][0])
    known = {MAP[n]: p for n, p in zip(target['joint_names'], tp) if n != 'root'}
    def between(a, b, ratio):
        return [x+(y-x)*ratio for x, y in zip(known[a], known[b])]
    known['Spine2'] = between('Spine1', 'Chest', .43)
    known['Neck2'] = between('Neck1', 'Head', .41)
    known['LeftShoulder'] = between('Chest', 'LeftArm', .38)
    known['RightShoulder'] = between('Chest', 'RightArm', .61)
    pos, bases, translations, locals_ = [], [], [], []
    for j, (n, _) in enumerate(rows):
        p = ps[j]
        # Name-derived angles keep common 30/77 bases equal without any random seed.
        h = sum((i+1)*ord(c) for i, c in enumerate(n))
        basis = unit(mul(axis(1, .15+(h % 13)*.043), axis(0, -.18+(h % 11)*.037)))
        position = known[n] if n in known else add(pos[p], [.007, .011, .019])
        local = basis if p is None else unit(mul(inv(bases[p]), basis))
        translation = position if p is None else mv(transpose(rotation(bases[p])), sub(position, pos[p]))
        pos.append(position); bases.append(basis); translations.append(translation); locals_.append(local)
    return {'identity': identity, 'joint_names': names, 'parent_indices': ps,
            'rest_local_translations_m': translations, 'rest_local_rotations_xyzw': locals_,
            'rest_local_scales_xyz': [[1., 1., 1.] for _ in names]}


def map_pose(source, target, qs, root, naive=False, swap=False, reverse=False):
    sq = globals_q(source, qs)
    sr = globals_q(source, source['rest_local_rotations_xyzw'])
    tr = globals_q(target, target['rest_local_rotations_xyzw'])
    desired, result = [], []
    for j, n in enumerate(target['joint_names']):
        name = MAP[n]
        if swap:
            name = name.replace('Left', 'TEMP').replace('Right', 'Left').replace('TEMP', 'Right')
        k = source['joint_names'].index(name)
        d = mul(mul(sq[k], inv(sr[k])), tr[j])
        if reverse:
            d = mul(mul(inv(sr[k]), sq[k]), tr[j])
        desired.append(unit(d))
        p = target['parent_indices'][j]
        result.append(unit(qs[k] if naive and n != 'pelvis' else
                           target['rest_local_rotations_xyzw'][j] if naive else
                           d if p is None else mul(inv(desired[p]), d)))
    # Each envelope stores absolute local rotations, with root translation replaced once.
    mapped_root = add(target['rest_local_translations_m'][0],
                      sub(root, source['rest_local_translations_m'][0]))
    return result, mapped_root


def desired_matrices(source, target, qs):
    a = matrix_globals(source, qs)
    rest = matrix_globals(source, source['rest_local_rotations_xyzw'])
    tr = matrix_globals(target, target['rest_local_rotations_xyzw'])
    return [mm(mm(a[source['joint_names'].index(MAP[n])],
                     transpose(rest[source['joint_names'].index(MAP[n])])), tr[j])
            for j, n in enumerate(target['joint_names'])]


def authored_frames(s, case):
    frames, roots = [], []
    times = [i/10 for i in range(11)]
    amplitudes = {'Hips': (.24, -.31), 'Spine1': (-.17, .19), 'Spine2': (.53, -.23),
                  'Chest': (-.21, .13), 'Neck2': (.37, -.18),
                  'LeftShoulder': (.59, -.27), 'RightShoulder': (-.16, .39),
                  'LeftArm': (.81, .24), 'RightArm': (-.28, -.43),
                  'LeftForeArm': (.41, -.19), 'RightForeArm': (-.63, .11),
                  'LeftLeg': (.27, .14), 'RightLeg': (-.12, -.23)}
    for t in times:
        q = copy.deepcopy(s['rest_local_rotations_xyzw'])
        if case == 'asymmetric':
            for name, (x, z) in amplitudes.items():
                j = s['joint_names'].index(name)
                # Noncommuting rotations applied in each authored local coordinate basis.
                q[j] = unit(mul(q[j], mul(axis(0, x*math.sin(t*2.1)), axis(2, z*t))))
        delta = [0, 0, 0] if case == 'rest' else [.37*t, .06*math.sin(t*2), -.19*t*t]
        frames.append(q)
        roots.append(add(s['rest_local_translations_m'][0], delta))
    return times, frames, roots


CONVENTION = {'units': 'meters', 'handedness': 'right', 'up_axis': 'Y',
              'rotation_order': 'xyzw', 'transform_space': 'local',
              'root_motion_mode': 'absolute_translation'}


def portable(s, times, qs, roots):
    return {'schema_version': 1, 'provenance_kind': 'authored_control', 'skeleton': s,
            'convention': CONVENTION, 'sample_times_seconds': times,
            'local_rotations_xyzw': qs, 'root_translations_m': roots}


def write_portable(out, stem, raw, files):
    raw_bytes = encode(raw)
    normalized = copy.deepcopy(raw)
    normalized['provenance'] = {'source_id': stem, 'raw_format': 'nvwa.motion.portable.v1',
                                'raw_sha256': sha(raw_bytes), 'run_receipt_sha256': None,
                                'provider': None, 'code_revision': None, 'model_sha256': None}
    for suffix, data in [('raw', raw_bytes), ('normalized', encode(normalized))]:
        name = stem + '.' + suffix + '.json'
        (out / name).write_bytes(data)
        files[name] = {'sha256': sha(data), 'bytes': len(data)}


def max_error(a, b):
    return max(length(sub(x, y)) for x, y in zip(a, b))


def orientation_error_deg(actual, desired):
    # Frobenius distance avoids acos precision loss near zero.
    d = max(math.sqrt(sum((a-b)**2 for ar, br in zip(x, y) for a, b in zip(ar, br)))
            for x, y in zip(actual, desired))
    return math.degrees(2*math.asin(min(1., d/(2*math.sqrt(2)))))


def run(out):
    contract = ROOT / '.work/m2-mapping-inputs/CONTRACT.md'
    assert sha(contract.read_bytes()) == CONTRACT_HASH
    if out.exists():
        raise ValueError('output must be a new directory')
    target = fixture()
    layouts = json.loads((HERE / 'source-layouts.json').read_bytes())
    sources = {str(n): authored_source(target, layouts['SOMASkeleton'+str(n)], 'soma'+str(n)) for n in (30, 77)}
    out.mkdir(parents=True)
    files, metrics, target_results = {}, {}, {}
    for count, s in sources.items():
        for case in ('rest', 'trajectory', 'asymmetric'):
            times, frames, roots = authored_frames(s, case)
            write_portable(out, 'source'+count+'-'+case, portable(s, times, frames, roots), files)
            all_positions = {}
            for method in ('naive', 'calibrated', 'swap_lr', 'reverse_product', 'drop_collapsed_links'):
                poses, mapped_roots, positions = [], [], []
                max_pos = max_rot = root_error = scale_error = source_endpoint_error = 0.
                for qs, root in zip(frames, roots):
                    input_qs = copy.deepcopy(qs)
                    if method == 'drop_collapsed_links':
                        for name in ('Spine2', 'Neck2', 'LeftShoulder', 'RightShoulder'):
                            j = s['joint_names'].index(name)
                            input_qs[j] = s['rest_local_rotations_xyzw'][j]
                    mapped, mapped_root = map_pose(s, target, input_qs, root, method == 'naive',
                                                    method == 'swap_lr', method == 'reverse_product')
                    desired = desired_matrices(s, target, qs)
                    p = fk(target, mapped, mapped_root)
                    expected = oracle_positions(target, desired, mapped_root)
                    max_pos = max(max_pos, max_error(p, expected))
                    max_rot = max(max_rot, orientation_error_deg(matrix_globals(target, mapped), desired))
                    root_error = max(root_error, length(sub(p[0], mapped_root)))
                    scale_error = max(scale_error, max_error(p, fk(target, mapped, mapped_root, scales=False)))
                    source_positions = fk(s, qs, root)
                    source_endpoint_error = max(source_endpoint_error, max(length(sub(p[target['joint_names'].index(tn)],
                        source_positions[s['joint_names'].index(MAP[tn])])) for tn in ('hand.L', 'hand.R', 'foot.L', 'foot.R')))
                    poses.append(mapped); mapped_roots.append(mapped_root); positions.append(p)
                key = count+'-'+case+'-'+method
                all_positions[method] = positions
                horizontal_travel = {}
                for name in ('foot.L', 'foot.R'):
                    j = target['joint_names'].index(name)
                    horizontal_travel[name] = sum(math.hypot(b[j][0]-a[j][0], b[j][2]-a[j][2])
                                                  for a, b in zip(positions, positions[1:]))
                metrics[key] = {'max_target_oracle_joint_error_m': max_pos,
                                'max_target_global_orientation_error_deg': max_rot,
                                'max_root_replace_once_error_m': root_error,
                                'max_scale_drop_position_error_m': scale_error,
                                'max_source_hand_foot_position_difference_m': source_endpoint_error,
                                'horizontal_foot_joint_travel_m_no_contact_labels': horizontal_travel}
                if method in ('naive', 'calibrated'):
                    raw = portable(target, times, poses, mapped_roots)
                    write_portable(out, key, raw, files)
                    target_results[key] = raw
                if method == 'calibrated':
                    assert max_pos < 1e-12 and max_rot < 1e-9 and root_error < 1e-15
                    if case == 'rest':
                        rest_positions = fk(target, target['rest_local_rotations_xyzw'], target['rest_local_translations_m'][0])
                        assert max_error(positions[0], rest_positions) < 1e-12
                if case == 'asymmetric' and method in ('naive', 'swap_lr', 'reverse_product', 'drop_collapsed_links'):
                    assert max_pos > .01 and max_rot > 1.
            if case == 'trajectory':
                expected_travel = sum(math.hypot(b[0]-a[0], b[2]-a[2]) for a, b in zip(roots, roots[1:]))
                for travel in metrics[count+'-'+case+'-calibrated']['horizontal_foot_joint_travel_m_no_contact_labels'].values():
                    assert abs(travel-expected_travel) < 1e-12
    # Sign-equivalence is a positive invariant. Conjugating only XYZ is a wrong
    # physical angle-sign control, unlike negating all four quaternion components.
    s = sources['30']; _, frames, roots = authored_frames(s, 'asymmetric')
    sign_error = wrong_sign_error = 0.
    for frame, root in zip(frames, roots):
        good, r = map_pose(s, target, frame, root)
        equiv, _ = map_pose(s, target, [[-v for v in q] for q in frame], root)
        bad, _ = map_pose(s, target, [inv(q) for q in frame], root)
        sign_error = max(sign_error, max_error(fk(target, good, r), fk(target, equiv, r)))
        wrong_sign_error = max(wrong_sign_error, max_error(fk(target, good, r), fk(target, bad, r)))
    assert sign_error < 1e-12 and wrong_sign_error > .01
    # Both layouts share body ancestry, so the same body input must map identically.
    shared_layout_error = max(max_error(fk(target, a, ra), fk(target, b, rb))
        for case in ('rest', 'trajectory', 'asymmetric')
        for a, b, ra, rb in zip(target_results['30-'+case+'-calibrated']['local_rotations_xyzw'],
                                target_results['77-'+case+'-calibrated']['local_rotations_xyzw'],
                                target_results['30-'+case+'-calibrated']['root_translations_m'],
                                target_results['77-'+case+'-calibrated']['root_translations_m']))
    assert shared_layout_error < 1e-12
    # Absolute roots must not acquire the target rest root translation a second time.
    raw = target_results['30-trajectory-calibrated']
    double_root_error = max(max_error(fk(target, qs, root),
        fk(target, qs, add(root, target['rest_local_translations_m'][0])))
        for qs, root in zip(raw['local_rotations_xyzw'], raw['root_translations_m']))
    assert double_root_error > .07
    # Exercise the float32 boundary numerically without claiming importer execution.
    float32_error = 0.
    for key, raw in target_results.items():
        reloaded = json.loads((out / (key+'.normalized.json')).read_bytes())
        assert reloaded['skeleton'] == target
        for qs, root in zip(reloaded['local_rotations_xyzw'], reloaded['root_translations_m']):
            f32 = lambda x: struct.unpack('<f', struct.pack('<f', x))[0]
            rounded_qs = [[f32(x) for x in q] for q in qs]
            rounded_root = [f32(x) for x in root]
            assert all(abs(length(q)-1) < 1e-4 for q in rounded_qs)
            float32_error = max(float32_error, max_error(fk(target, qs, root), fk(target, rounded_qs, rounded_root)))
    assert float32_error < 1e-6
    report = {'evidence_kind': 'authored_control; CPU math only', 'frames_per_case': 11,
              'cases': metrics, 'q_and_negative_q_position_error_m': sign_error,
              'wrong_xyz_sign_position_error_m': wrong_sign_error,
              'shared30_77_target_pose_error_m': shared_layout_error,
              'double_root_translation_negative_control_error_m': double_root_error,
              'json_reload_float32_rounding_max_joint_error_m': float32_error,
              'max_target_rest_scale_deviation_from_one': max(abs(v-1) for row in target['rest_local_scales_xyz'] for v in row),
              'genuine_generation': 'NOT-RUN', 'renderer_playback': 'NOT-RUN'}
    (out / 'metrics.json').write_bytes(encode(report))
    manifest = {'fixture_sha256': FIXTURE_HASH, 'contract_sha256': CONTRACT_HASH,
                'script_sha256': sha(Path(__file__).read_bytes()),
                'source_layout_sha256': sha((HERE / 'source-layouts.json').read_bytes()),
                'source_definitions_url': layouts['source_url'],
                'source_definitions_sha256': layouts['source_sha256'],
                'source_rest_kind': 'authored_control; NOT official SOMA calibration',
                'mapping_target_to_source': MAP, 'target_exact_rest_skeleton': target,
                'source_authored_rest_skeletons': sources,
                'root_policy': 'target rest root + (source absolute root - source authored rest root); replace target root once',
                'scale_policy': 'preserve every target rest local scale exactly; source scales unit authored controls only',
                'files': files}
    (out / 'mapping-manifest.json').write_bytes(encode(manifest))
    print(json.dumps({'output': str(out.relative_to(ROOT) if out.is_relative_to(ROOT) else out),
                      'normalized_target_count': len(target_results), 'portable_file_count': len(files),
                      'metrics_sha256': sha(encode(report)), 'manifest_sha256': sha(encode(manifest)),
                      'result': 'PASS authored controls only'}, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / '.work/m2-mapping/output')
    run(parser.parse_args().out.resolve())
