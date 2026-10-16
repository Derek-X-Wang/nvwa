"""Measure retained-sample reproduction differences; never judge acceptance."""
import argparse
import json
import math
from pathlib import Path
import platform
import struct

import directions


def float_bits(value):
    return struct.unpack('>Q', struct.pack('>d', value))[0]


def ordered_float_bits(value):
    bits = float_bits(value)
    return (~bits & ((1 << 64)-1)) if bits >> 63 else bits | (1 << 63)


def measure(expected, actual):
    floats, structures = [], []
    float_leaves = 0

    def visit(left, right, path):
        nonlocal float_leaves
        if type(left) is not type(right):
            structures.append({'path': path, 'kind': 'type', 'expected_type': type(left).__name__, 'actual_type': type(right).__name__})
        elif type(left) is dict:
            if left.keys() != right.keys():
                structures.append({'path': path, 'kind': 'object_keys', 'missing': sorted(left.keys()-right.keys()), 'extra': sorted(right.keys()-left.keys())})
            for key in left.keys() & right.keys():
                visit(left[key], right[key], path+'/'+str(key).replace('~', '~0').replace('/', '~1'))
        elif type(left) is list:
            if len(left) != len(right):
                structures.append({'path': path, 'kind': 'list_length', 'expected': len(left), 'actual': len(right)})
            for i, (a, b) in enumerate(zip(left, right)):
                visit(a, b, path+'/'+str(i))
        elif type(left) is float:
            float_leaves += 1
            if float_bits(left) != float_bits(right):
                finite = math.isfinite(left) and math.isfinite(right)
                floats.append({'path': path, 'expected': left if math.isfinite(left) else repr(left),
                               'actual': right if math.isfinite(right) else repr(right),
                               'absolute_error': abs(left-right) if finite else None,
                               'binary64_ulp_distance': abs(ordered_float_bits(left)-ordered_float_bits(right)) if finite else None,
                               'expected_binary64_hex': '%016x' % float_bits(left),
                               'actual_binary64_hex': '%016x' % float_bits(right)})
        elif left != right:
            structures.append({'path': path, 'kind': 'discrete_value', 'expected': left, 'actual': right})

    visit(expected, actual, '')
    floats.sort(key=lambda item: item['path'])
    structures.sort(key=lambda item: (item['path'], item['kind']))
    return {'typed_sample_equality': not floats and not structures,
            'float_leaves_compared': float_leaves, 'float_difference_count': len(floats),
            'structural_or_discrete_difference_count': len(structures),
            'max_absolute_float_error': max((v['absolute_error'] for v in floats if v['absolute_error'] is not None), default=0.),
            'max_binary64_ulp_distance': max((v['binary64_ulp_distance'] for v in floats if v['binary64_ulp_distance'] is not None), default=0),
            'float_differences': floats, 'structural_or_discrete_differences': structures}


def core_controls():
    one = measure({'x': 1.}, {'x': math.nextafter(1., math.inf)})
    if one['float_difference_count'] != 1 or one['max_binary64_ulp_distance'] != 1 or one['max_absolute_float_error'] != 2**-52:
        raise ValueError('one-ULP diagnostic control failed')
    typed = measure([1, True], [True, 1])
    if typed['structural_or_discrete_difference_count'] != 2:
        raise ValueError('typed discrete diagnostic control failed')
    shape = measure({'x': [1, 2], 'missing': None}, {'x': [2], 'extra': None})
    if shape['structural_or_discrete_difference_count'] != 3:
        raise ValueError('schema/list/discrete diagnostic control failed')
    return {'status': 'MEASUREMENTS', 'scope': 'diagnostic implementation controls only; no reproduction acceptance decision',
            'one_ulp': one, 'typed_discrete': typed, 'schema_list_discrete': shape}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        result = core_controls()
    else:
        golden = json.loads((Path(__file__).with_name('retained-native-directions.json')).read_text())['samples']
        native = directions.evaluate('native')['samples']
        web = directions.evaluate('web')['samples']
        result = {'status': 'MEASUREMENTS', 'python': platform.python_version(), 'platform': platform.platform(),
                  'scope': 'All float64 leaf differences measured without thresholds or acceptance waiver; types, object keys, list positions and discrete values checked exactly',
                  'ulp_definition': 'Distance in ordered IEEE754 binary64 bit encodings; -0 and +0 are distinct adjacent encodings',
                  'native_vs_retained': measure(golden, native), 'web_vs_retained': measure(golden, web),
                  'native_vs_web': measure(native, web)}
    print(json.dumps(result, separators=(',', ':'), allow_nan=False))


if __name__ == '__main__':
    main()
