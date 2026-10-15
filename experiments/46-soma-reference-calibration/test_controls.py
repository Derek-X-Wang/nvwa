#!/usr/bin/env python3
"""Actual analyzer/oracle controls; strict discrete identity, finite float tolerance."""
import copy
import json
import math
from pathlib import Path
import sys

import calibrate as c

HERE = Path(__file__).resolve().parent
FLOAT_ATOL = 1e-13
FLOAT_RTOL = 1e-13


def compare(actual, expected, path='$'):
    """Only finite float leaves receive tolerance; types and shape remain exact."""
    c.require(type(actual) is type(expected), 'type mismatch: '+path)
    if type(expected) is dict:
        c.require(actual.keys() == expected.keys(), 'keys mismatch: '+path)
        for k in expected:
            compare(actual[k], expected[k], path+'.'+k)
    elif type(expected) is list:
        c.require(len(actual) == len(expected), 'length mismatch: '+path)
        for i, (a, e) in enumerate(zip(actual, expected)):
            compare(a, e, path+'['+str(i)+']')
    elif type(expected) is float:
        c.require(math.isfinite(actual) and math.isfinite(expected), 'nonfinite comparison: '+path)
        c.require(abs(actual-expected) <= FLOAT_ATOL+FLOAT_RTOL*max(abs(actual), abs(expected)), 'float mismatch: '+path)
    else:
        c.require(actual == expected, 'identity mismatch: '+path)


def run():
    baseline = c.analyze()
    retained = json.loads((HERE/'results.json').read_bytes())
    compare(baseline, retained)
    checks = []

    def positive(name, ok, detail=None):
        c.require(ok, 'positive control failed: '+name)
        checks.append({'name': name, 'expectation': 'PASS', 'observed': 'PASS', 'detail': detail})

    def rejects(name, fn, message):
        try:
            fn()
        except ValueError as error:
            c.require(message in str(error), 'wrong rejection '+name+': '+str(error))
            checks.append({'name': name, 'expectation': 'REJECT', 'observed': 'REJECT', 'detail': str(error)})
        else:
            raise ValueError('negative survived: '+name)

    positive('retained results reproduce under typed finite float policy', True)
    inputs = {name: (c.ROOT/name).read_bytes() for name in c.PINS}
    source, target, roots, frames, _ = c.load_inputs(inputs)
    for name in c.PINS:
        corrupted = dict(inputs)
        data = corrupted[name]
        corrupted[name] = bytes([data[0] ^ 1])+data[1:]
        rejects('input pin '+name, lambda x=corrupted: c.load_inputs(x), 'SHA256 mismatch')
    omitted = dict(inputs)
    omitted.pop(next(iter(omitted)))
    rejects('missing input identity', lambda: c.load_inputs(omitted), 'exact input identities')

    for name, result in baseline['root_candidates'].items():
        c.check_root(result)
        positive('all90 pelvis world '+name, result['frames'] == 90, result['max_pelvis_world_error_m'])
        positive('scene-root equality is a false oracle '+name,
                 result['max_scene_root_vs_hips_difference_m'] > .74,
                 {'root_compensation_m': result['max_scene_root_vs_hips_difference_m'],
                  'scene_root_xz_path_m': result['scene_root_xz_path_m'], 'hips_xz_path_m': result['hips_xz_path_m']})
    for name, result in baseline['root_negative_controls'].items():
        rejects('actual root oracle '+name, lambda r=result: c.check_root(r), 'pelvis-world oracle failed')

    counts = baseline['signed_policies']['counts']
    positive('independent signed anchors narrow48 to8 to2 to1', counts == {'all': 48, 'up': 8, 'up_front': 2, 'up_front_named_left': 1})
    matching = [r for r in baseline['signed_policies']['candidates'] if all(r['agrees'].values())]
    positive('named-side parity is conditional improper reflection', len(matching) == 1 and matching[0]['determinant'] == -1)
    positive('identity survives common up/front', any(r['basis'] == c.I and r['agrees']['up'] and r['agrees']['front'] and not r['agrees']['named_left'] for r in baseline['signed_policies']['candidates']))
    # Flip only the independent target signed-side annotation. The decision must
    # change; FK equivariance remains exactly as uninformative as before.
    alt = c.signed_policies({'up': ([0, 1, 0], [0, 1, 0]), 'front': ([0, 0, 1], [0, 0, 1]),
                             'named_left': ([1, 0, 0], [1, 0, 0])})
    alt_matching = [r for r in alt['candidates'] if all(r['agrees'].values())]
    positive('independent changed side anchor changes matching policy', len(alt_matching) == 1 and alt_matching[0]['basis'] == c.I)
    front = c.signed_policies({'up': ([0, 1, 0], [0, 1, 0]), 'front': ([0, 0, 1], [0, 0, -1]),
                               'named_left': ([1, 0, 0], [-1, 0, 0])})
    front_matching = [r for r in front['candidates'] if all(r['agrees'].values())]
    positive('independent changed front anchor distinguishes180 Y', len(front_matching) == 1 and front_matching[0]['determinant'] == 1)
    invariance = baseline['all48_algebraic_invariance']
    positive('actual48 FK invariance is numerical consistency', invariance['proper'] == 24 and invariance['improper'] == 24 and invariance['max_fk_equivariance_error_m'] < c.ROOT_TOL)
    rejects('false semantic promotion from48 invariant', lambda: c.admit_semantics(invariance), 'independent signed anatomical reference missing')
    rejects('false semantic promotion from root pass', lambda: c.admit_semantics(baseline['root_candidates']), 'independent signed anatomical reference missing')
    rejects('unrecognized invented authority cannot admit', lambda: c.admit_semantics({'independent_signed_reference': 'invented'}), 'no independent signed reference is admitted')

    observed = {r['joint']: r for r in baseline['observability']['source']}
    for name in ('LeftArm', 'LeftForeArm', 'RightArm', 'RightForeArm'):
        row = observed[name]
        positive('near-collinear '+name+' remains anatomical HOLD', row['geometric_rank'] == 2 and
                 .0001 < row['normalized_projection_sine'] < .0003 and
                 row['inverse_sine_sensitivity'] > 3000 and row['anatomical_twist_status'] == 'HOLD' and
                 row['trusted_anatomical_frame'] is False,
                 {'sine': row['normalized_projection_sine'], 'inverse_sine': row['inverse_sine_sensitivity']})
    for row in baseline['observability']['target']:
        if row['joint'] in ('hand.L', 'hand.R', 'foot.L', 'foot.R'):
            positive('target leaf twist absent '+row['joint'], row['terminal'] is True and row['geometric_rank'] == 1 and
                     row['secondary'] is None and row['frame'] is None and row['anatomical_twist_status'] == 'HOLD')
    hand = observed['LeftHand']
    p, s = hand['primary']['vector_m'], hand['secondary']['vector_m']
    f = c.frame_from_directions(p, s)
    c.check_geometric_frame(f, p, s)
    positive('hand geometric frame observes both landmark directions', True)
    reversed_secondary = c.frame_from_directions(p, [-x for x in s])
    positive('180 twist preserves primary but reverses secondary', c.angle(c.mv(f, [1, 0, 0]), c.mv(reversed_secondary, [1, 0, 0])) < c.FRAME_TOL)
    rejects('sign-reversed secondary actual frame oracle', lambda: c.check_geometric_frame(reversed_secondary, p, s), 'signed secondary/twist mismatch')
    wrong_primary = c.frame_from_directions([-x for x in p], s)
    rejects('reversed primary actual frame oracle', lambda: c.check_geometric_frame(wrong_primary, p, s), 'primary segment direction mismatch')
    rejects('collinear frame cannot recover twist', lambda: c.frame_from_directions([1., 0., 0.], [2., 0., 0.]), 'zero/nonfinite direction')
    # Matrix validity alone also cannot establish neutral segment compatibility.
    positive('actual rest directions differ after reflection', all(r['x_reflection_direction_error_rad'] > .01 for r in baseline['neutral_geometry']['segments']))

    representation = baseline['representation_max_fk_position_change_m']
    positive('actual q versus minus q equivalence', representation['q_negated'] == 0.)
    for name in ('xyz_conjugated', 'XYWZ_misread', 'parent_localized_twice'):
        changed = representation[name]
        rejects('actual FK representation '+name,
                lambda x=changed: c.require(x < c.ROOT_TOL, 'FK representation mismatch'), 'FK representation mismatch')

    for label, q in [('NaN', [float('nan'), 0., 0., 1.]), ('infinity', [0., float('inf'), 0., 1.]),
                     ('bool', [False, 0., 0., 1.]), ('string', ['0', 0., 0., 1.])]:
        rejects('quaternion rejects '+label, lambda x=q: c.rotation(x), 'invalid finite vector')
    rejects('zero quaternion', lambda: c.rotation([0., 0., 0., 0.]), 'zero/nonfinite direction')
    unsupported = copy.deepcopy(target)
    unsupported['parents'][1] = None
    rejects('unsupported pelvis hierarchy', lambda: c.root_oracle(unsupported, roots, frames, c.I), 'unsupported pelvis hierarchy')

    # Exercise the actual retained-result comparator: floats only, never discrete
    # identities/counts/pins, receive numerical tolerance.
    for name, mutate in [
        ('material root metric', lambda r: r['root_candidates']['identity_conditional'].__setitem__('max_pelvis_world_error_m', .01)),
        ('changed hash', lambda r: r['input_sha256'].__setitem__(next(iter(c.PINS)), '0'*64)),
        ('integer value', lambda r: r.__setitem__('frames', 91)),
        ('integer to float', lambda r: r.__setitem__('frames', 90.)),
        ('integer to bool', lambda r: r.__setitem__('schema_version', True)),
        ('boolean to integer', lambda r: r.__setitem__('raw_floats_finite', 1)),
        ('null to string', lambda r: r['signed_policies'].__setitem__('policy_selected', 'identity')),
        ('admission promotion', lambda r: r.__setitem__('target_playable_admission', 'PASS')),
        ('missing key', lambda r: r.pop('issue')),
        ('extra key', lambda r: r.__setitem__('extra', None)),
        ('list shape', lambda r: r['not_run'].pop()),
        ('list type', lambda r: r.__setitem__('not_run', tuple(r['not_run']))),
        ('NaN float', lambda r: r.__setitem__('max_raw_quaternion_norm_error', float('nan'))),
        ('infinite float', lambda r: r.__setitem__('max_raw_quaternion_norm_error', float('inf'))),
    ]:
        changed = copy.deepcopy(baseline)
        mutate(changed)
        rejects('typed result '+name, lambda x=changed: compare(x, baseline), 'mismatch' if name not in ('NaN float', 'infinite float') else 'nonfinite')
    rejects('nonfinite expected comparator', lambda: compare(0., float('nan')), 'nonfinite')
    compare({'x': [1.+1e-15], 'n': 90, 'ok': True}, {'x': [1.], 'n': 90, 'ok': True})
    positive('last-bit finite float tolerance accepted', True)
    positive('all source and target anatomical twists remain HOLD',
             all(r['anatomical_twist_status'] == 'HOLD' and r['trusted_anatomical_frame'] is False
                 for rows in baseline['observability'].values() for r in rows))
    positive('no semantic or playable promotion', baseline['anatomical_semantic_admission'] == 'HOLD' and
             baseline['target_playable_admission'] == 'HOLD' and baseline['signed_policies']['policy_selected'] is None)
    positive('public inputs unchanged after controls', all(c.sha((c.ROOT/name).read_bytes()) == pin for name, pin in c.PINS.items()))
    return {'schema_version': 1, 'status': 'PASS', 'python_version': sys.version.split()[0],
            'optimization': sys.flags.optimize, 'results_sha256': c.sha((HERE/'results.json').read_bytes()),
            'test_script_sha256': c.sha(Path(__file__).read_bytes()),
            'comparison': {'finite_float_atol': FLOAT_ATOL, 'finite_float_rtol': FLOAT_RTOL,
                           'discrete_types_shapes_identities_and_pins': 'exact'},
            'checks': checks, 'positive_checks': sum(r['expectation'] == 'PASS' for r in checks),
            'rejection_checks': sum(r['expectation'] == 'REJECT' for r in checks),
            'owned_temporary_resources': 'none created; all mutations in memory',
            'development_repairs': [
                {'control': 'near-collinear LeftForeArm remains anatomical HOLD',
                 'initial_failure': 'generic secondary selected hand-thumb grandchild; observed sine 0.427781260092206',
                 'repair': 'explicit proximal elbow segment selected; current actual sine retained in checks'},
                {'control': 'Python3.9 retained-result comparison',
                 'initial_failure': 'float mismatch: $.observability.source[17].frame[0][1]',
                 'initial_absolute_difference': 2.19198805e-12,
                 'repair': 'cross-cross perpendicular projection avoids longitudinal subtraction cancellation; comparator tolerance unchanged'}],
            'anatomical_semantic_admission': 'HOLD', 'target_playable_admission': 'HOLD'}


if __name__ == '__main__':
    try:
        sys.stdout.write(c.encode(run()).decode())
    except (ValueError, OSError, KeyError, TypeError) as error:
        sys.stderr.write(json.dumps({'code': 'controls_failed', 'message': str(error)})+'\n')
        sys.exit(1)
