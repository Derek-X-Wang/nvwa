"""Portable attribution diagnostic. No mapper/evaluator implementation imports."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import tempfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def read(relative):
    return json.loads((ROOT/relative).read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_inputs():
    for relative, expected in json.loads((HERE/'input-pins.json').read_text()).items():
        path = ROOT/relative
        if not path.is_file() or path.is_symlink() or sha(path) != expected:
            raise ValueError('repository input pin mismatch '+relative)


def validate_capture(value, platform):
    if (type(value.get('schema_version')) is not int or value['schema_version'] != 1 or
            value.get('platform') != platform or value.get('status') != 'complete' or value.get('error') is not None):
        raise ValueError('complete fixed-seven '+platform+' capture required')
    samples = value.get('samples')
    if (type(samples) is not list or not all(type(s.get('source_key_index')) is int for s in samples) or
            [s['source_key_index'] for s in samples] != [0,15,30,45,60,75,89]):
        raise ValueError('complete fixed-seven '+platform+' capture required')


def output_target(path):
    path = path.resolve()
    if path.is_relative_to(HERE) or path.exists():
        raise ValueError('output must be fresh and outside retained attribution directory')
    return path


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def norm(v):
    length = math.sqrt(dot(v, v))
    if length <= 1e-12:
        raise ValueError('singular vector')
    return [x/length for x in v]


def sub(a, b):
    return [x-y for x, y in zip(a, b)]


def mv(a, v):
    return [dot(row, v) for row in a]


def mm(a, b):
    return [[dot(row, col) for col in zip(*b)] for row in a]


def tr(a):
    return [list(row) for row in zip(*a)]


def inverse(a):
    def cross(x, y):
        return [x[1]*y[2]-x[2]*y[1], x[2]*y[0]-x[0]*y[2], x[0]*y[1]-x[1]*y[0]]
    cofactors = [cross(a[1], a[2]), cross(a[2], a[0]), cross(a[0], a[1])]
    determinant = dot(a[0], cofactors[0])
    if abs(determinant) <= 1e-12:
        raise ValueError('singular actual body affine')
    return [[v/determinant for v in row] for row in tr(cofactors)]


def qr(q):
    x, y, z, w = norm(q)
    return [[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
            [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
            [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]]


def angle(a, b):
    return math.degrees(math.acos(max(-1., min(1., dot(norm(a), norm(b))))))


def fk(meta, rotations, root):
    matrices, positions = [], []
    for i, parent in enumerate(meta['parents']):
        local = qr(rotations[i])
        offset = meta['rest_local_translations'][i]
        if parent == -1:
            matrices.append(local)
            positions.append(list(root))
        else:
            matrices.append(mm(matrices[parent], local))
            moved = mv(matrices[parent], offset)
            positions.append([x+y for x, y in zip(positions[parent], moved)])
    return matrices, positions


def evaluate(capture='native', source_cache=None):
    if capture not in ('native', 'web'):
        raise ValueError('capture must be native or web')
    verify_inputs()
    source = read('experiments/41-real-short-motion/source-skeleton.json')
    cal = read('experiments/47-fixture-rig-calibration/calibration.json')
    capture_relative = 'experiments/49-runtime-pose-parity/probe/results/'+capture+'.json'
    native = read(capture_relative)
    validate_capture(native, capture)
    pins = read('experiments/47-fixture-rig-calibration/reference/input-hashes.json')
    claims = read('experiments/47-fixture-rig-calibration/reference/authority-claims.json')
    receipt_path = ROOT/'experiments/41-real-short-motion/evidence/source-receipts.json'
    if sha(receipt_path) != pins['experiments/41-real-short-motion/evidence/source-receipts.json']['sha256']:
        raise ValueError('archived source receipt pin mismatch')
    receipts = {entry['file']: entry for entry in json.loads(receipt_path.read_text())}
    checked = {}
    receipt_bindings = {}
    for name in ['cpp-src__motion_decode.cpp', 'cpp-src__motion_rep.cpp', 'cpp-src__skeleton.hpp',
                 'cpp-scripts__export_glb.py', 'official-output-formats.md', 'official-skeleton.md']:
        alias = 'cached-original-source/'+name
        actual = pins[alias]['sha256']
        byte_count = pins[alias]['bytes']
        if source_cache is not None:
            p = source_cache/name
            if not p.is_file() or p.is_symlink() or sha(p) != actual or p.stat().st_size != byte_count:
                raise ValueError('cache pin mismatch '+name)
        checked[alias] = actual
        receipt = receipts[name]
        if receipt['sha256'] != actual or receipt['bytes'] != byte_count or receipt['url'] != claims['original_sources'][name]['url']:
            raise ValueError('archived URL/bytes receipt mismatch '+name)
        receipt_bindings[name] = {'url': receipt['url'], 'bytes': receipt['bytes'], 'sha256': actual}
    for relative, expected in cal['input_sha256'].items():
        if sha(ROOT/relative) != expected:
            raise ValueError('calibration input pin mismatch '+relative)
    rawpath = ROOT/'experiments/44-approved-cpu-motion-trial/evidence/run/raw'
    q = struct.unpack('<10800f', (rawpath/'local_rotations_xyzw.f32').read_bytes())
    roots = struct.unpack('<270f', (rawpath/'root_positions.f32').read_bytes())
    names = source['joint_names']
    si = {name: i for i, name in enumerate(names)}
    rest_matrix, rest_positions = fk(source, source['rest_local_rotations_xyzw'], [0., 0., 0.])
    # Four independent numerical convention controls, none call mapper code.
    numerical_controls = {}
    unit_z90 = qr([0., 0., math.sqrt(.5), math.sqrt(.5)])
    numerical_controls['known_positive_z90_maps_x_to_y'] = max(abs(x-y) for x,y in zip(mv(unit_z90,[1.,0.,0.]), [0.,1.,0.])) < 1e-14
    tiny = {'parents':[-1,0], 'rest_local_translations':[[0.,0.,0.],[1.,0.,0.]]}
    _, tiny_points = fk(tiny, [[0.,0.,math.sqrt(.5),math.sqrt(.5)],[0.,0.,0.,1.]], [2.,3.,4.])
    numerical_controls['known_parent_rotation_transports_child_offset'] = max(abs(x-y) for x,y in zip(tiny_points[1],[2.,4.,4.])) < 1e-14
    numerical_controls['quaternion_sign_equivalent'] = qr(q[:4]) == qr([-x for x in q[:4]])
    numerical_controls['identity_source_rest_offsets_add'] = all(angle(mv(rest_matrix[i],[1.,0.,0.]),[1.,0.,0.]) < 1e-12 for i in range(30))
    if not all(numerical_controls.values()):
        raise ValueError('numerical convention control failed')
    rows = []
    for sample in native['samples']:
        key = sample['source_key_index']
        local = [q[(key*30+i)*4:(key*30+i+1)*4] for i in range(30)]
        global_s, points_s = fk(source, local, roots[key*3:key*3+3])
        nodes = {n['name']: n for n in sample['nodes'] if n['gltf_node_index'] is not None}
        chest_t = [[nodes['chest']['global'][c*4+r] for c in range(3)] for r in range(3)]
        inverse_chest_t = inverse(chest_t)
        directions = {}
        for row in cal['rows']:
            target = row['target']
            n = nodes[target]
            global_t = [[n['global'][c*4+r] for c in range(3)] for r in range(3)]
            # Source FK longitudinal direction from declared primary pair;
            # target actual signed affine marker was declared by experiment47.
            src = norm(sub(points_s[si[row['source_distal']]], points_s[si[row['source_primary_start']]]))
            dst = norm(mv(global_t, row['orientation_markers_local_m']['primary']))
            src0 = norm(row['source_primary_m'])
            dst0 = norm(row['target_primary_m'])
            # A diagnostic invariant, NOT a replacement mapping: compare each
            # bone in its own already-declared STATIC geometric neutral gauge.
            # Both neutral longitudinal directions become +X exactly. No
            # runtime angle is fitted and no dynamic frame is reconstructed.
            src_gauge = mv(tr(row['source_frame']), src)
            dst_gauge = mv(tr(row['target_frame']), dst)
            directions[target] = {'source_joint': row['source'], 'source_world': src, 'target_actual_world': dst,
                                  'neutral_source_world': src0, 'neutral_target_world': dst0,
                                  'raw_world_angle_deg': angle(src, dst), 'neutral_world_angle_deg': angle(src0, dst0),
                                  'neutral_gauge_direction_error_deg': angle(src_gauge, dst_gauge),
                                  'source_excursion_from_declared_neutral_deg': angle(src0, src),
                                  'target_excursion_from_declared_neutral_deg': angle(dst0, dst),
                                  'source_neutral_gauge_direction': src_gauge, 'target_neutral_gauge_direction': dst_gauge}
            if target.startswith(('upper_arm.', 'forearm.')):
                child = target.replace('upper_arm.', 'forearm.') if target.startswith('upper_arm.') else target.replace('forearm.', 'hand.')
                direct = norm(sub([nodes[child]['global'][i] for i in (12,13,14)], [n['global'][i] for i in (12,13,14)]))
                directions[target]['actual_child_segment_world'] = direct
                directions[target]['marker_vs_actual_child_angle_deg'] = angle(direct, dst)
            if target.startswith('upper_arm.'):
                source_body = norm(mv(tr(global_s[si['Chest']]), src))
                target_body = norm(mv(inverse_chest_t, direct))
                # Static declared frames remove the T/A-neutral difference.
                # EXISTING_POLICY_PREDICTION uses only existing rest geometry.
                # It predicts the current mapping, with no runtime intervention.
                neutral_only = norm(mv(row['target_frame'], mv(tr(row['source_frame']), source_body)))
                directions[target]['source_body_relative'] = source_body
                directions[target]['target_actual_body_relative'] = target_body
                directions[target]['body_relative_world_angle_deg'] = angle(source_body, target_body)
                directions[target]['existing_policy_prediction'] = neutral_only
                directions[target]['actual_vs_existing_policy_prediction_angle_deg'] = angle(neutral_only, target_body)
        bends = {}
        for side, target in [('Left', 'R'), ('Right', 'L')]:
            upper_s = sub(points_s[si[side+'ForeArm']], points_s[si[side+'Arm']])
            lower_s = sub(points_s[si[side+'Hand']], points_s[si[side+'ForeArm']])
            upper_t = directions['upper_arm.'+target]['target_actual_world']
            lower_t = directions['forearm.'+target]['target_actual_world']
            upper0_s = sub(rest_positions[si[side+'ForeArm']], rest_positions[si[side+'Arm']])
            lower0_s = sub(rest_positions[si[side+'Hand']], rest_positions[si[side+'ForeArm']])
            upper0_t = directions['upper_arm.'+target]['neutral_target_world']
            lower0_t = directions['forearm.'+target]['neutral_target_world']
            bends[side] = {'source_elbow_deflection_deg': angle(upper_s, lower_s),
                           'target_elbow_deflection_deg': angle(upper_t, lower_t),
                           'source_neutral_elbow_deflection_deg': angle(upper0_s, lower0_s),
                           'target_neutral_elbow_deflection_deg': angle(upper0_t, lower0_t),
                           'source_hand_minus_shoulder_m': sub(points_s[si[side+'Hand']], points_s[si[side+'Arm']]),
                           'target_hand_minus_shoulder_m': sub([nodes['hand.'+target]['global'][i] for i in (12,13,14)],
                                                               [nodes['upper_arm.'+target]['global'][i] for i in (12,13,14)])}
        rows.append({'key_index': key, 'time_seconds': sample['requested_time'], 'directions': directions, 'elbow_and_reach': bends})
    result = {'status': 'MEASURED_NOT_ADMITTED', 'method': 'Independent source parent-local quaternion FK against captured actual '+capture+' signed affine primary directions, expressed in declared static source/target geometric neutral frames; elbow deflection additionally uses actual directed segments',
              'limits': ['static gauge direction equality is a diagnostic invariant, not an admitted retarget policy', 'EXISTING_POLICY_PREDICTION uses existing static calibration without fitted angles; no runtime intervention or fix', 'forearm global gauge errors are descriptive only: local hierarchy transfer does not promise global neutral-gauge equality', 'does not identify anatomical twist or weights as cause', 'source convention claims retained from pinned earlier static inspection; current source-text audit is reported separately; no official decoder/runtime parity'],
              'recorded_source_hashes': checked, 'capture_platform': capture, 'capture_sha256': sha(ROOT/capture_relative),
              'source_text_audit': {'status': 'PASS' if source_cache is not None else 'NOT-RUN',
                                    'scope': 'Existing six cached source files match pinned hashes/bytes and archived URL receipts; no fetch' if source_cache is not None else 'No --source-cache supplied; archived hashes/URL receipts checked, original source text not freshly read'},
              'source_receipt_sha256': sha(receipt_path), 'verified_url_byte_receipts': receipt_bindings,
              'numerical_controls': numerical_controls,
              'counts': {'archived_source_receipt_matches': len(checked), 'raw_frames_retained': 90, 'sampled_keys': len(rows),
                         'signed_primary_directions': len(rows)*len(cal['rows']), 'actual_arm_child_segment_checks':len(rows)*4, 'elbow_comparisons':len(rows)*2},
              'calibration_sha256': sha(ROOT/'experiments/47-fixture-rig-calibration/calibration.json'), 'samples': rows}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', choices=('native', 'web'), default='native')
    parser.add_argument('--source-cache', type=Path, help='Optional existing six-file cache; never downloads')
    parser.add_argument('--output', type=Path, help='Fresh output file outside retained attribution directory')
    args = parser.parse_args()
    result = evaluate(args.capture, args.source_cache)
    if args.output is None:
        parent = ROOT/'.work/runtime-pose-attribution-check'
        parent.mkdir(parents=True, exist_ok=True)
        output = Path(tempfile.mkdtemp(prefix=args.capture+'-', dir=parent))/'directions.json'
    else:
        output = args.output
    output = output_target(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'status': result['status'], 'capture': args.capture,
                      'source_text_audit': result['source_text_audit']['status'],
                      'numeric_controls': result['numerical_controls'], 'output': str(output)}))


if __name__ == '__main__':
    main()
