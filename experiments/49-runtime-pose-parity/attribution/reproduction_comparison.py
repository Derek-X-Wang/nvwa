"""Typed retained-sample comparison with the measured angle-only ULP bound."""
import math
import struct


TARGETS = frozenset(('root', 'pelvis', 'spine', 'chest', 'neck', 'head',
                     'upper_arm.L', 'forearm.L', 'hand.L', 'upper_arm.R',
                     'forearm.R', 'hand.R', 'thigh.L', 'shin.L', 'foot.L',
                     'thigh.R', 'shin.R', 'foot.R'))
ARMS = frozenset(('upper_arm.L', 'forearm.L', 'upper_arm.R', 'forearm.R'))
UPPER_ARMS = frozenset(('upper_arm.L', 'upper_arm.R'))
BASE_ANGLES = frozenset(('raw_world_angle_deg', 'neutral_world_angle_deg',
                        'neutral_gauge_direction_error_deg',
                        'source_excursion_from_declared_neutral_deg',
                        'target_excursion_from_declared_neutral_deg'))
UPPER_ANGLES = frozenset(('body_relative_world_angle_deg',
                         'actual_vs_existing_policy_prediction_angle_deg'))
ELBOW_ANGLES = frozenset(('source_elbow_deflection_deg', 'target_elbow_deflection_deg'))
EXACT_ELBOW_ANGLES = frozenset(('source_neutral_elbow_deflection_deg',
                              'target_neutral_elbow_deflection_deg'))


class ReproductionMismatch(AssertionError):
    pass


def bits(value):
    return struct.unpack('>Q', struct.pack('>d', value))[0]


def ordered_bits(value):
    value = bits(value)
    return (~value & ((1 << 64)-1)) if value >> 63 else value | (1 << 63)


def angle_kind(path):
    """Explicit existing scalar locations; a suffix never grants tolerance."""
    if len(path) != 4 or type(path[0]) is not int or not 0 <= path[0] < 7:
        return None
    _, branch, joint, field = path
    if branch == 'directions' and joint in TARGETS:
        if (field in BASE_ANGLES or
                joint in ARMS and field == 'marker_vs_actual_child_angle_deg' or
                joint in UPPER_ARMS and field in UPPER_ANGLES):
            return 'portable'
    if branch == 'elbow_and_reach' and joint in ('Left', 'Right'):
        if field in ELBOW_ANGLES:
            return 'portable'
        if field in EXACT_ELBOW_ANGLES:
            return 'exact'
    return None


def _compare(expected, actual, allow_retained_angles, path=()):
    def fail(reason):
        raise ReproductionMismatch('/'+'/'.join(map(str, path))+': '+reason)
    if type(expected) is not type(actual):
        fail('exact type differs: %s vs %s' % (type(expected).__name__, type(actual).__name__))
    if type(expected) is dict:
        if list(expected) != list(actual):
            fail('object keys/order differ')
        for key in expected:
            _compare(expected[key], actual[key], allow_retained_angles, path+(key,))
    elif type(expected) is list:
        if len(expected) != len(actual):
            fail('list length differs')
        for i, (left, right) in enumerate(zip(expected, actual)):
            _compare(left, right, allow_retained_angles, path+(i,))
    elif type(expected) is float:
        if not math.isfinite(expected) or not math.isfinite(actual):
            fail('nonfinite float')
        kind = angle_kind(path)
        if path and isinstance(path[-1], str) and path[-1].endswith('_deg') and kind is None:
            fail('unrecognized angle scalar path')
        if kind is not None and (not 0. <= expected <= 180. or not 0. <= actual <= 180.):
            fail('angle outside [0,180] degrees')
        if bits(expected) == bits(actual):
            return
        if expected == actual == 0.:
            fail('signed zero differs')
        if bits(expected) >> 63 != bits(actual) >> 63:
            fail('float sign differs')
        distance = abs(ordered_bits(expected)-ordered_bits(actual))
        if allow_retained_angles and kind == 'portable' and distance <= 2:
            return
        fail('binary64 value differs: expected %r actual %r distance %d ULP' % (expected, actual, distance))
    elif expected != actual:
        fail('discrete value differs: expected %r actual %r' % (expected, actual))


def assert_retained_samples(expected, actual):
    """Allow at most two binary64 ULP at the ten enumerated angle-field groups."""
    _compare(expected, actual, True)


def assert_exact_samples(expected, actual):
    """Native/Web agreement: exact types, structure, ordering and float bits."""
    _compare(expected, actual, False)
