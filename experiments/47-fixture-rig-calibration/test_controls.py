#!/usr/bin/env python3
"""Independent signed-vector/affine expectations against actual candidate path.

Authored poses below are diagnostics. They never replace the genuine sample.
The independent oracle does not use candidate frame construction, matrix math,
quaternion conversion, FK, or direction calculation to compute expectations.
"""
import copy
import json
import math
from pathlib import Path

import calibrate as c

HERE = Path(__file__).resolve().parent


def check(ok, message):
    if not ok:
        raise ValueError(message)


def near(a, b, tol=1e-10):
    check(len(a) == len(b) and all(type(x) in (int, float) and math.isfinite(x) for x in a+b), 'finite comparison')
    check(max(abs(x-y) for x, y in zip(a, b)) < tol, 'independent signed direction/position mismatch')


def compare(a, b):
    check(type(a) is type(b), 'strict result type')
    if isinstance(a, dict):
        check(a.keys() == b.keys(), 'strict result keys')
        for k in a:
            compare(a[k], b[k])
    elif isinstance(a, list):
        check(len(a) == len(b), 'strict result list length')
        for x, y in zip(a, b):
            compare(x, y)
    elif type(a) is float:
        check(math.isfinite(a) and math.isfinite(b) and abs(a-b) <= 1e-13+1e-13*max(abs(a), abs(b)), 'strict finite result float')
    else:
        check(a == b, 'strict discrete result identity')


def normalized(v):
    n = math.sqrt(sum(x*x for x in v))
    check(n > 0, 'nonzero expected direction')
    return [x/n for x in v]


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def projected(axis, guide):
    # Independent Gram-Schmidt expression; no candidate cross-cross construction.
    dot = sum(x*y for x, y in zip(axis, guide))
    return normalized([g-dot*x for x, g in zip(axis, guide)])


def turn(v, axis, angle):
    # Closed-form Rodrigues vector formula, independent of candidate matrices.
    co, si = math.cos(angle), math.sin(angle)
    cr = cross(axis, v)
    d = sum(x*y for x, y in zip(axis, v))
    return [x*co+y*si+a*d*(1-co) for x, y, a in zip(v, cr, axis)]


def quaternion(axis, angle):
    return [x*math.sin(angle/2) for x in normalized(axis)]+[math.cos(angle/2)]


def qmul(a, b):
    x, y, z, w = a
    i, j, k, r = b
    return [w*i+x*r+y*k-z*j, w*j-x*k+y*r+z*i,
            w*k+x*j-y*i+z*r, w*r-x*i-y*j-z*k]


def independent_fk(target, local, root):
    # Recursive point transport. This does not use candidate affine FK or its
    # accumulated matrix multiplication. Every local scale/rotation applies once.
    def transport(j, point):
        point = [point[k]*target['scales'][j][k] for k in range(3)]
        point = [sum(local[j][r][k]*point[k] for k in range(3)) for r in range(3)]
        t = root if target['parents'][j] is None else target['translations'][j]
        point = [point[k]+t[k] for k in range(3)]
        p = target['parents'][j]
        return point if p is None else transport(p, point)
    return [transport(j, [0., 0., 0.]) for j in range(18)]


def rotate_quaternion(q, v):
    q = normalized(q)
    axis, w = q[:3], q[3]
    a = cross(axis, v)
    b = cross(axis, a)
    return [v[k]+2*w*a[k]+2*b[k] for k in range(3)]


def independent_marker_local(target, j, direction):
    chain = []
    while j is not None:
        chain.append(j)
        j = target['parents'][j]
    v = [x*.1 for x in direction]
    for k in reversed(chain):
        q = target['rotations'][k]
        v = rotate_quaternion([-x for x in q[:3]]+[q[3]], v)
        v = [x/s for x, s in zip(v, target['scales'][k])]
    return v


def independent_marker_direction(target, local, j, direction):
    v = independent_marker_local(target, j, direction)
    while j is not None:
        v = [x*s for x, s in zip(v, target['scales'][j])]
        v = [sum(local[j][r][k]*v[k] for k in range(3)) for r in range(3)]
        j = target['parents'][j]
    return normalized(v)


# Independently transcribed generator head->tail expectations. Blender Y is
# negative front; glTF maps (x,y,z)->(x,z,-y). No calibration rows are used.
TARGET_SEGMENTS = {
    'root': ([0., .08, 0.], [0., .28, 0.]),
    'pelvis': ([0., .83, 0.], [0., 1., 0.]),
    'spine': ([0., 1., 0.], [0., 1.19, 0.]),
    'chest': ([0., 1.19, 0.], [0., 1.38, 0.]),
    'neck': ([0., 1.38, 0.], [0., 1.48, 0.]),
    'head': ([0., 1.48, 0.], [0., 1.83, 0.]),
    'upper_arm.L': ([-.235, 1.33, 0.], [-.43, 1.13, 0.]),
    'forearm.L': ([-.43, 1.13, 0.], [-.57, .94, .01]),
    'hand.L': ([-.57, .94, .01], [-.615, .85, .015]),
    'upper_arm.R': ([.235, 1.33, 0.], [.43, 1.13, 0.]),
    'forearm.R': ([.43, 1.13, 0.], [.57, .94, .01]),
    'hand.R': ([.57, .94, .01], [.615, .85, .015]),
    'thigh.L': ([-.125, .86, 0.], [-.145, .50, 0.]),
    'shin.L': ([-.145, .50, 0.], [-.155, .14, 0.]),
    'foot.L': ([-.155, .14, 0.], [-.155, .075, .15]),
    'thigh.R': ([.125, .86, 0.], [.145, .50, 0.]),
    'shin.R': ([.145, .50, 0.], [.155, .14, 0.]),
    'foot.R': ([.155, .14, 0.], [.155, .075, .15]),
}


def expectations(calibration):
    # These observations are separate from the mapping equation. Physical +X
    # follows source LeftEye/LeftLeg; target names .L lie on -X. Whether to adopt
    # physical identity or named reflection remains a root review decision.
    b = calibration['basis']
    up = [sum(b[r][k]*[0, 1, 0][k] for k in range(3)) for r in range(3)]
    front = [sum(b[r][k]*[0, 0, 1][k] for k in range(3)) for r in range(3)]
    near(up, [0., 1., 0.]); near(front, [0., 0., 1.])
    for row in calibration['rows']:
        h, t = TARGET_SEGMENTS[row['target']]
        near(row['target_head_m'], h); near(row['target_tail_m'], t)
        primary = normalized([t[i]-h[i] for i in range(3)])
        guide = [0., 1., 0.] if row['target'].startswith('foot.') else [0., 0., 1.]
        secondary = projected(primary, guide)
        # Signed columns, not an orthogonality-only acceptance.
        near([r[0] for r in row['target_frame']], primary)
        near([r[1] for r in row['target_frame']], secondary)


def side_correspondence(source, calibration):
    # Source pelvis limbs and hand distal offsets encode the observed signs.
    # Require lateral source landmarks to land on the independently transcribed
    # target side after the candidate basis. No endpoint-fit score is involved.
    def rest_x(j):
        out = 0.
        while j is not None:
            out += source['translations'][j][0]
            j = source['parents'][j]
        return out
    for row in calibration['rows']:
        if not row['target'].endswith(('.L', '.R')):
            continue
        x = rest_x(source['names'].index(row['source']))
        expected = TARGET_SEGMENTS[row['target']][0][0]
        actual = calibration['basis'][0][0]*x
        check(actual*expected > 0., 'independent signed side landmark mismatch')


def pose_oracle(source, target, calibration, joint, axis_kind):
    """One authored rotation: independent signed expected primary/secondary."""
    row = next(r for r in calibration['rows'] if r['target'] == joint)
    k = source['names'].index(row['source'])
    distal = source['names'].index(row['source_distal'])
    # All pinned source static rest rotations are identity. Distal is a direct
    # child for every mapped source segment. Verify that independent prerequisite.
    start = source['names'].index(row['source_primary_start'])
    check(source['parents'][distal] == start, 'direct source landmark')
    check(all(q == [0, 0, 0, 1] for q in source['rotations']), 'source identity static rest')
    primary_s = normalized(source['translations'][distal])
    guide = [0., 1., 0.] if joint.startswith('foot.') else [0., 0., 1.]
    secondary_s = projected(primary_s, guide)
    axis_s = primary_s if axis_kind == 'longitudinal' else secondary_s
    angle = math.pi/3
    qs = copy.deepcopy(source['rotations'])
    qs[k] = quaternion(axis_s, angle)
    local, root = c.map_frame(source, target, calibration, qs, [0., 1., 0.])
    directions = c.candidate_directions(target, local, calibration)
    observed = next(d for d in directions if d['joint'] == joint)
    head, tail = TARGET_SEGMENTS[joint]
    primary_t = normalized([tail[i]-head[i] for i in range(3)])
    secondary_t = projected(primary_t, guide)
    axis_t = primary_t if axis_kind == 'longitudinal' else secondary_t
    # Reflection reverses axial-vector sign, including the handed twist sign.
    sign = -1 if calibration['candidate'] == 'named_labels_reflected' else 1
    expected_primary = turn(primary_t, axis_t, sign*angle)
    expected_secondary = turn(secondary_t, axis_t, sign*angle)
    near(observed['primary'], expected_primary, 2e-6)
    near(observed['secondary'], expected_secondary, 2e-6)
    j = c.TARGET.index(joint)
    near(observed['primary'], independent_marker_direction(target, local, j, primary_t))
    near(observed['secondary'], independent_marker_direction(target, local, j, secondary_t))
    affine_residual = max(abs(x-y) for actual, expected in ((observed['primary'], expected_primary),
                (observed['secondary'], expected_secondary)) for x, y in zip(actual, expected))
    # Observe a real child joint position, separately from the frame/marker
    # functions. Exact export scales remain in recursive FK. The 2e-6 metre
    # tolerance covers the pinned float export versus authored decimal heads;
    # it is not a motion-quality tolerance.
    child = {'upper_arm.L': 'forearm.L', 'forearm.L': 'hand.L',
             'upper_arm.R': 'forearm.R', 'forearm.R': 'hand.R',
             'thigh.L': 'shin.L', 'shin.L': 'foot.L',
             'thigh.R': 'shin.R', 'shin.R': 'foot.R'}.get(joint)
    landmark_error = None
    if child is not None:
        child_head = TARGET_SEGMENTS[child][0]
        rotated = turn([child_head[i]-head[i] for i in range(3)], axis_t, sign*angle)
        # Authored hips [0,1,0] replaces target pelvis [.0,.83,.0] once.
        expected = [head[i]+rotated[i]+[0., .17, 0.][i] for i in range(3)]
        actual = independent_fk(target, local, root)[c.TARGET.index(child)]
        near(actual, expected, 2e-6)
        landmark_error = math.sqrt(sum((x-y)**2 for x, y in zip(actual, expected)))
    return {'closed_form_vs_exact_affine_direction_residual': affine_residual,
            'authored_head_vs_exact_affine_child_residual_m': landmark_error}


def run():
    checks = []

    def positive(name, fn):
        detail = fn()
        checks.append({'name': name, 'expected': 'PASS', 'observed': 'PASS', 'detail': detail})

    def rejects(name, fn, message):
        try:
            fn()
        except ValueError as error:
            check(message in str(error), 'unexpected rejection: '+name+': '+str(error))
            checks.append({'name': name, 'expected': 'REJECT', 'observed': 'REJECT', 'reason': str(error)})
        else:
            raise ValueError('negative survived: '+name)

    source, target, roots, frames, blobs = c.load_inputs()
    for name in c.PINS:
        bad = dict(blobs)
        bad[name] = b'corrupted'+bad[name]
        rejects('input-pin '+name, lambda b=bad: c.load_inputs(b), 'SHA256 mismatch')
    missing = dict(blobs); missing.pop(next(iter(missing)))
    rejects('missing input identity', lambda: c.load_inputs(missing), 'exact input identities')
    rejects('parallel-front gauge singularity has no fallback', lambda: c.geometric_frame([0., 0., 1.], [0., 0., 1.]), 'nonzero direction')
    rejects('boolean quaternion is not numeric rotation', lambda: c.rotation([False, 0., 0., 1.]), 'finite vector')
    rejects('nonfinite quaternion', lambda: c.rotation([float('inf'), 0., 0., 1.]), 'finite vector')

    bundles = {}
    for label in ('named_labels_reflected', 'physical_sides_identity'):
        cal, result = c.analyze(label)
        bundles[label] = {'calibration': cal, 'results': result}
        positive(label+' independent generator segment and signed roll references', lambda: expectations(cal))
        positive(label+' independent signed source/target lateral landmarks', lambda: side_correspondence(source, cal))
        if label == 'physical_sides_identity':
            positive('independently anchored physical policy', lambda: c.check_physical_policy(cal))
        else:
            rejects('named reflection fails independently anchored physical policy', lambda: c.check_physical_policy(cal), 'independent physical')
        for joint in c.TARGET:
            if joint == 'pelvis':  # deliberately duplicate Hips has no own motion
                continue
            for axis in ('longitudinal', 'secondary'):
                positive(label+' authored '+joint+' '+axis, lambda j=joint, a=axis: pose_oracle(source, target, cal, j, a))
        for omitted, descendant in (('Spine2', 'Chest'), ('Neck2', 'Head'), ('LeftShoulder', 'LeftArm'), ('RightShoulder', 'RightArm')):
            first, second = copy.deepcopy(source['rotations']), copy.deepcopy(source['rotations'])
            first[source['names'].index(omitted)] = quaternion([.3, .4, .5], .6)
            second[source['names'].index(descendant)] = quaternion([.3, .4, .5], .6)
            a, ar = c.map_frame(source, target, cal, first, [0., 1., 0.])
            b, br = c.map_frame(source, target, cal, second, [0., 1., 0.])
            positive(label+' collapsed omitted '+omitted+' into '+descendant,
                     lambda x=a, y=b: near([v for m in x for r in m for v in r], [v for m in y for r in m for v in r]))
        max_root = 0.
        baseline_points = []
        for h, qs in zip(roots, frames):
            local, root = c.map_frame(source, target, cal, qs, h)
            points = independent_fk(target, local, root)
            desired = [sum(cal['basis'][r][k]*h[k] for k in range(3)) for r in range(3)]
            near(points[1], desired, 1e-12)
            max_root = max(max_root, math.sqrt(sum((x-y)**2 for x, y in zip(points[1], desired))))
            baseline_points.append(points)
            # All 18 actual affine signed markers, every frame, using a separate
            # inverse quaternion/scale transport oracle and static authored axes.
            directions = c.candidate_directions(target, local, cal)
            for j, d in enumerate(directions):
                head, tail = TARGET_SEGMENTS[d['joint']]
                primary = normalized([tail[k]-head[k] for k in range(3)])
                secondary = projected(primary, [0., 1., 0.] if d['joint'].startswith('foot.') else [0., 0., 1.])
                near(d['primary'], independent_marker_direction(target, local, j, primary))
                near(d['secondary'], independent_marker_direction(target, local, j, secondary))
        checks.append({'name': label+' independent all90 recursive pelvis world oracle', 'expected': 'PASS', 'observed': 'PASS', 'maximum_m': max_root})
        checks.append({'name': label+' independent all90 x18 exact affine signed markers', 'expected': 'PASS', 'observed': 'PASS', 'marker_count': 3240})
        neutral, neutral_root = c.map_frame(source, target, cal, source['rotations'], [0., 0., 0.])
        wrong, _ = c.map_frame(source, target, cal, source['rotations'], [0., 0., 0.], neutral=frames[0])
        rejects(label+' first animated frame is wrong neutral', lambda: near([x for r in wrong for row in r for x in row],
                [x for r in neutral for row in r for x in row]), 'independent signed')
        # A target frame half-twist about longitudinal leaves primary unchanged.
        # The secondary-axis authored control must reject the altered production basis.
        twisted = copy.deepcopy(cal)
        row = next(r for r in twisted['rows'] if r['target'] == 'hand.L')
        frame = row['target_rest_gauge']
        half = [[1., 0., 0.], [0., -1., 0.], [0., 0., -1.]]
        row['delta_basis'] = c.mm(c.mm(frame, half), c.tr(row['source_rest_gauge']))
        rejects(label+' hand180 twist actual candidate path', lambda: pose_oracle(source, target, twisted, 'hand.L', 'secondary'), 'independent signed')
        for mutation in ('parent_localized_twice', 'conjugated_xyz', 'wrong_xywz', 'q_negated'):
            maximum = 0.
            for i, (h, qs) in enumerate(zip(roots, frames)):
                if mutation == 'parent_localized_twice':
                    changed = [q if p is None else qmul([-x for x in qs[p][:3]]+[qs[p][3]], q)
                               for p, q in zip(source['parents'], qs)]
                elif mutation == 'conjugated_xyz':
                    changed = [[-q[0], -q[1], -q[2], q[3]] for q in qs]
                elif mutation == 'wrong_xywz':
                    changed = [[q[0], q[1], q[3], q[2]] for q in qs]
                else:
                    changed = [[-x for x in q] for q in qs]
                local, root = c.map_frame(source, target, cal, changed, h)
                altered = independent_fk(target, local, root)
                maximum = max(maximum, max(math.sqrt(sum((x-y)**2 for x, y in zip(a, b))) for a, b in zip(altered, baseline_points[i])))
            if mutation == 'q_negated':
                check(maximum == 0., 'q sign invariance')
            else:
                rejects(label+' '+mutation+' actual90 path', lambda m=maximum: check(m < 1e-10, 'changed candidate trajectory'), 'changed candidate')
            checks.append({'name': label+' '+mutation+' trajectory difference', 'expected': 'MEASURE', 'observed': maximum})
        local, root = c.map_frame(source, target, cal, frames[47], roots[47])
        for mutation, offset in (('double_target_root_offset', target['translations'][0]), ('double_source_trajectory', roots[47]), ('exporter_height', [0., .988, 0.])):
            wrong_root = [x+y for x, y in zip(root, offset)]
            expected = [sum(cal['basis'][r][k]*roots[47][k] for k in range(3)) for r in range(3)]
            rejects(label+' '+mutation+' independent FK', lambda t=wrong_root: near(independent_fk(target, local, t)[1], expected, 1e-12), 'independent signed')
        desired = [sum(cal['basis'][r][k]*roots[47][k] for k in range(3)) for r in range(3)]
        unrotated = [x-y for x, y in zip(desired, target['translations'][1])]
        old43 = [x+y for x, y in zip(desired, target['translations'][0])]
        for mutation, wrong_root in (('unrotated_pelvis_subtraction', unrotated), ('unchanged43_root_addition', old43)):
            rejects(label+' '+mutation+' actual candidate rotations', lambda t=wrong_root: near(independent_fk(target, local, t)[1], desired, 1e-12), 'independent signed')
        # The output remains explicitly proposed even after numeric positives.
        positive(label+' status cannot promote from numeric closure', lambda: check(cal['status'] == result['status'] == 'PROPOSED_NOT_ADMITTED' and cal['anatomical_twist_recovered'] is False, 'candidate authority limit'))

    physical = bundles['physical_sides_identity']['calibration']
    for name, basis in (('mirror', c.BASIS), ('front180 reversal', [[-1., 0., 0.], [0., 1., 0.], [0., 0., -1.]])):
        altered = c.build_calibration(source, target, blobs['tools/blender/generate_fixture.py'], basis,
                    [r['source'] for r in physical['rows']], 'physical_sides_identity')
        if name == 'mirror':
            # A fixed asymmetric authored source trajectory is an independent
            # signed reference; the actual map must put +X displacement on +X.
            local, root = c.map_frame(source, target, altered, source['rotations'], [.25, 1., .1])
            rejects(name+' physical signed trajectory', lambda: near(independent_fk(target, local, root)[1], [.25, 1., .1]), 'independent signed')
        else:
            rejects(name+' independent front reference', lambda: expectations(altered), 'independent signed')
            local, root = c.map_frame(source, target, altered, source['rotations'], [.25, 1., .1])
            rejects(name+' actual signed trajectory', lambda: near(independent_fk(target, local, root)[1], [.25, 1., .1]), 'independent signed')
    swapped = copy.deepcopy(physical)
    left = c.TARGET.index('upper_arm.L'); right = c.TARGET.index('upper_arm.R')
    swapped['rows'][left]['source'], swapped['rows'][right]['source'] = swapped['rows'][right]['source'], swapped['rows'][left]['source']
    rejects('side swap independent signed rest landmarks', lambda: side_correspondence(source, swapped), 'independent signed side')
    # Pose is authored on source physical +X LeftArm; only target +X .R moves.
    qs = copy.deepcopy(source['rotations'])
    qs[source['names'].index('LeftArm')] = quaternion([0., 0., 1.], .7)
    ref, _ = c.map_frame(source, target, physical, qs, [0., 1., 0.])
    wrong, _ = c.map_frame(source, target, swapped, qs, [0., 1., 0.])
    rejects('side swap asymmetric actual candidate path', lambda: near([x for a in wrong for row in a for x in row],
            [x for a in ref for row in a for x in row]), 'independent signed')

    retained = HERE/'candidates.json'
    positive('retained candidates reproduce with strict typed finite comparator', lambda: compare(bundles, json.loads(retained.read_bytes())))
    positive('selected calibration reproduces exactly with strict typed finite comparator',
             lambda: compare(bundles['physical_sides_identity']['calibration'], json.loads((HERE/'calibration.json').read_bytes())))
    rejects('comparator bool vs integer', lambda: compare(True, 1), 'strict result type')
    rejects('comparator nonfinite', lambda: compare(float('nan'), float('nan')), 'strict finite')
    rejects('comparator discrete mutation', lambda: compare('PROPOSED_NOT_ADMITTED', 'ADMITTED'), 'strict discrete')
    return {'schema': 'nvwa.fixture-calibration-controls.v1', 'status': 'PASS',
            'positive_count': sum(r['expected'] == 'PASS' for r in checks),
            'rejection_count': sum(r['expected'] == 'REJECT' for r in checks),
            'measured_count': sum(r['expected'] == 'MEASURE' for r in checks),
            'diagnostic_provenance': 'hand-authored closed-form controls only; no generated claim', 'checks': checks}


if __name__ == '__main__':
    print(c.encode(run()).decode(), end='')
