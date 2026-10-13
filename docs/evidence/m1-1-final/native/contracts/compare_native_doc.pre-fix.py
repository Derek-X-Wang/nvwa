#!/usr/bin/env python3
"""Private whole-Doc comparator. File comparison is not native GUI proof."""
from pathlib import Path
from decimal import Decimal
from fractions import Fraction
import argparse
import copy
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
MAX_BYTES = 2 * 1024 * 1024
MAX_DIFFERENCES = 64


class InvalidDocument(ValueError):
    pass


def reject_constant(value):
    raise InvalidDocument(f'Non-finite JSON constant: {value}')


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidDocument(f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def parse(data):
    if len(data) > MAX_BYTES:
        raise InvalidDocument('Document exceeds 2 MiB')
    try:
        return json.loads(data.decode('utf-8'), parse_float=Decimal,
                          parse_constant=reject_constant, object_pairs_hook=strict_object)
    except (UnicodeError, ValueError, RecursionError) as error:
        raise InvalidDocument(str(error)) from error


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pointer(path, key):
    return path + '/' + str(key).replace('~', '~0').replace('/', '~1')


def matches(path, patterns):
    parts = path.split('/')[1:]
    return any(len(parts) == len(pattern.split('/')[1:]) and
               all(a == b or b == '*' for a, b in zip(parts, pattern.split('/')[1:]))
               for pattern in patterns)


def nearest_even(numerator, denominator):
    value, remainder = divmod(numerator, denominator)
    return value + int(2 * remainder > denominator or
                       (2 * remainder == denominator and value % 2 == 1))


def scaled_round(value, power):
    numerator, denominator = value.numerator, value.denominator
    if power >= 0:
        numerator <<= power
    else:
        denominator <<= -power
    return nearest_even(numerator, denominator)


def binary32(value):
    """Exact decimal/integer to finite IEEE-754 binary32, round ties to even.

    Avoid a decimal -> binary64 -> binary32 intermediate and any epsilon.
    Preserve the sign of zero; reject values that round to infinity.
    """
    if type(value) not in (int, Decimal):
        raise InvalidDocument('Expected a finite JSON number, excluding bool')
    decimal = Decimal(value) if type(value) is int else value
    if not decimal.is_finite():
        raise InvalidDocument('Non-finite number')
    sign = int(decimal.is_signed()) << 31
    if decimal.is_zero():
        return sign
    # Decimal exponents outside these bounds cannot change the conclusion.
    if decimal.adjusted() > 39:
        raise InvalidDocument('Number overflows finite binary32')
    if decimal.adjusted() < -60:
        return sign
    value = abs(Fraction(decimal))
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    boundary = Fraction(1 << exponent, 1) if exponent >= 0 else Fraction(1, 1 << -exponent)
    if value < boundary:
        exponent -= 1
    if exponent < -126:
        return sign | scaled_round(value, 149)
    mantissa = scaled_round(value, 23 - exponent)
    if mantissa == (1 << 24):
        exponent += 1
        mantissa = 1 << 23
    if exponent > 127:
        raise InvalidDocument('Number overflows finite binary32')
    return sign | ((exponent + 127) << 23) | (mantissa - (1 << 23))


def describe(value):
    if type(value) is Decimal:
        return {'type': 'number', 'decimal': str(value)}
    if type(value) is dict:
        return {'type': 'object', 'keys': sorted(value)}
    if type(value) is list:
        return {'type': 'array', 'length': len(value)}
    return {'type': type(value).__name__, 'value': value}


def compare(expected, actual, contract):
    differences = []
    total = 0

    def add(path, reason, left=None, right=None):
        nonlocal total
        total += 1
        if len(differences) < MAX_DIFFERENCES:
            differences.append({'pointer': path or '/', 'reason': reason,
                                'expected': describe(left), 'actual': describe(right)})

    def walk(left, right, path):
        if matches(path, contract['f32_paths']):
            try:
                a, b = binary32(left), binary32(right)
            except InvalidDocument as error:
                add(path, str(error), left, right)
                return
            if a != b:
                add(path, f'binary32 differs: expected 0x{a:08x}, actual 0x{b:08x}', left, right)
            return
        if type(left) is not type(right):
            add(path, 'JSON type differs', left, right)
            return
        if type(left) is dict:
            for key in sorted(left.keys() - right.keys()):
                add(pointer(path, key), 'Missing field', left[key], None)
            for key in sorted(right.keys() - left.keys()):
                add(pointer(path, key), 'Extra field', None, right[key])
            for key in sorted(left.keys() & right.keys()):
                walk(left[key], right[key], pointer(path, key))
        elif type(left) is list:
            if len(left) != len(right):
                add(path, 'Array length differs', left, right)
            for index, (a, b) in enumerate(zip(left, right)):
                walk(a, b, pointer(path, index))
        elif type(left) is int:
            if left != right:
                add(path, 'Integer differs', left, right)
        elif type(left) in (str, bool):
            if left != right:
                add(path, 'Value differs', left, right)
        else:
            add(path, 'Unexpected schema value or unmapped numeric field', left, right)

    try:
        walk(expected, actual, '')
    except RecursionError as error:
        raise InvalidDocument('Document nesting exceeds comparator limit') from error
    return {'equal': total == 0, 'difference_count': total,
            'differences': differences, 'differences_truncated': total > MAX_DIFFERENCES}


def validate_expected(document, contract):
    objects = [(document, 'strict_top_level_keys'),
               (document['profile'], 'strict_profile_keys'),
               (document['character'], 'strict_character_keys')]
    objects += [(item, 'strict_parameter_spec_keys') for item in document['profile']['parameters']]
    objects += [(item, 'strict_clip_spec_keys') for item in document['profile']['clips']]
    objects += [(item, 'strict_timeline_clip_keys') for item in document['timeline']]
    for obj, key in objects:
        if type(obj) is not dict or set(obj) != set(contract[key]):
            raise InvalidDocument(f'Expected input violates manifest: {key}')
    result = compare(document, document, contract)
    if not result['equal']:
        raise InvalidDocument('Expected input has unsupported or non-finite fields')


def load_inputs(case):
    manifest_bytes = (HERE / 'expected-manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    record = manifest['inputs'][case]
    expected_path = Path(record['path'])
    if not expected_path.resolve().is_relative_to(HERE):
        raise InvalidDocument('Expected input lies outside contract directory')
    data = expected_path.read_bytes()
    if sha(data) != record['sha256']:
        raise InvalidDocument('Expected input hash differs from manifest')
    doc = parse(data)
    validate_expected(doc, manifest['comparison'])
    return manifest, doc, {'path': str(expected_path), 'sha256': sha(data), 'bytes': len(data)}, sha(manifest_bytes)


def self_test():
    manifest, expected, identity, manifest_hash = load_inputs('other')
    contract = manifest['comparison']
    records = []

    def control(name, mutate, should_equal, pointer_prefix=None):
        actual = copy.deepcopy(expected)
        mutate(actual)
        result = compare(expected, actual, contract)
        passed = result['equal'] is should_equal
        if not should_equal and pointer_prefix:
            passed &= any(d['pointer'].startswith(pointer_prefix) for d in result['differences'])
        records.append({'name': name, 'control_passed': passed, 'expected_equal': should_equal, **result})

    control('unchanged', lambda d: None, True)
    control('revision', lambda d: d.update(revision=2), False, '/revision')
    control('extra_field', lambda d: d['profile'].update(extra='forbidden'), False, '/profile/extra')
    control('missing_field', lambda d: d['profile'].pop('license'), False, '/profile/license')
    control('array_reorder', lambda d: d['timeline'].reverse(), False, '/timeline/')
    control('bool_number', lambda d: d['timeline'][0].update(looping=0), False, '/timeline/0/looping')
    control('bool_as_f32', lambda d: d['character'].update(scale=True), False, '/character/scale')
    control('bool_as_int', lambda d: d.update(revision=True), False, '/revision')
    control('float_as_int', lambda d: d.update(revision=Decimal('1.0')), False, '/revision')
    control('clip_change', lambda d: d['profile']['clips'][0].update(duration_seconds=Decimal('3.1')), False, '/profile/clips/0/duration_seconds')
    control('parameter_change', lambda d: d['character']['parameters'].update(jaw_width=Decimal('0.62')), False, '/character/parameters/jaw_width')
    control('tiny_change_no_epsilon', lambda d: d['character']['parameters'].update(jaw_width=Decimal('0.610001')), False, '/character/parameters/jaw_width')
    control('string_change', lambda d: d['character'].update(id='different-character'), False, '/character/id')
    control('same_binary32_decimal', lambda d: d['character']['parameters'].update(jaw_width=Decimal('0.61000001430511474609375')), True)
    control('zero_integer_at_f32', lambda d: d['character']['parameters'].update(smile=0), True)
    control('finite_binary32_overflow', lambda d: d['character'].update(scale=Decimal('1e39')), False, '/character/scale')
    for name, data in [('nan', b'{"x":NaN}'), ('duplicate_key', b'{"x":1,"x":1}'), ('invalid_utf8', b'\xff')]:
        try:
            parse(data)
            passed = False
        except InvalidDocument:
            passed = True
        records.append({'name': name, 'control_passed': passed, 'expected_parse_failure': True})
    # Exact conversion controls include ties and subnormal handling.
    for name, value, bits in [('one', '1', 0x3f800000),
                              ('halfway_even_down', '1.000000059604644775390625', 0x3f800000),
                              ('halfway_even_up', '1.000000178813934326171875', 0x3f800002),
                              ('underflow', '1e-100', 0),
                              ('negative_zero', '-0.0', 0x80000000)]:
        observed = binary32(Decimal(value))
        records.append({'name': 'conversion_' + name, 'control_passed': observed == bits,
                        'expected_bits': f'0x{bits:08x}', 'actual_bits': f'0x{observed:08x}'})
    return {'status': 'PASS' if all(r['control_passed'] for r in records) else 'FAIL',
            'scope': 'Comparator-only synthetic CPU controls; no product or GUI execution',
            'manifest_sha256': manifest_hash, 'expected': identity, 'controls': records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=['same', 'other'])
    parser.add_argument('--actual', type=Path)
    parser.add_argument('--receipt', type=Path)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if not args.self_test and (not args.case or not args.actual):
        parser.error('Use --case same|other --actual PATH, or --self-test')
    if args.self_test and (args.case or args.actual):
        parser.error('--self-test is separate from actual file comparison')
    if args.receipt:
        target = args.receipt.resolve()
        if not target.is_relative_to(HERE):
            parser.error('Receipt writes must stay within the private contracts directory')
        protected = {Path(__file__).resolve(), (HERE / 'expected-manifest.json').resolve(),
                     (HERE / 'native-recovery-same.nvwa.json').resolve(),
                     (HERE / 'native-recovery-other.nvwa.json').resolve(),
                     (HERE / 'native-recovery-contract.md').resolve()}
        if target in protected or (args.actual and target == args.actual.resolve()):
            parser.error('Receipt cannot overwrite helper, contract, inputs or actual file')
    try:
        if args.self_test:
            result = self_test()
        else:
            manifest, expected, identity, manifest_hash = load_inputs(args.case)
            result = {'status': 'FAIL', 'scope': 'Whole-Doc file comparison only; native GUI behavior not established',
                      'manifest_sha256': manifest_hash, 'expected': identity,
                      'actual': {'path': str(args.actual.resolve())}}
            if not args.actual.is_file():
                result.update(execution='NOT-RUN', reason='Actual output file is absent or not a regular file')
            else:
                with args.actual.open('rb') as stream:
                    data = stream.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES:
                    raise InvalidDocument('Actual output exceeds 2 MiB; full hash not computed')
                result['actual'].update(sha256=sha(data), bytes=len(data))
                try:
                    result.update(compare(expected, parse(data), manifest['comparison']))
                    result['status'] = 'PASS' if result['equal'] else 'FAIL'
                except InvalidDocument as error:
                    result.update(equal=False, reason=str(error))
    except (OSError, InvalidDocument, KeyError, TypeError) as error:
        result = {'status': 'FAIL', 'execution': 'NOT-RUN', 'reason': str(error),
                  'scope': 'Comparator input/setup failure; no native GUI claim'}
    result['comparator_sha256'] = sha(Path(__file__).read_bytes())
    output = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.receipt:
        args.receipt.write_text(output)
    sys.stdout.write(output)
    return 0 if result['status'] == 'PASS' else 2


if __name__ == '__main__':
    sys.exit(main())
