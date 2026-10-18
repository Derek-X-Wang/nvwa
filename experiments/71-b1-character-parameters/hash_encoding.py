"""Pinned serde_json1.0.152 Value hash encoding for actual f32 mesh arrays.

Production: json!(Vec<[f32;N]>) -> Number::Float(f32 as f64), then
serde_json::to_vec(Value) -> zmij1.0.23 compact f64 formatting. Indices remain
unsigned JSON integers. This is not Python json.dumps canonicalization.
"""
from decimal import Decimal
import hashlib
import math
import struct


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def promoted_f32_token(value):
    _require(type(value) in (int, float) and math.isfinite(value), 'mesh hash needs finite f32 value')
    value = float(value)
    try:
        rounded = struct.unpack('!f', struct.pack('!f', value))[0]
    except (OverflowError, struct.error) as error:
        raise ValueError('mesh value outside f32 domain') from error
    _require(rounded == value, 'mesh number is not exact f32 promoted to f64')
    if value == 0.:
        return '-0.0' if math.copysign(1., value) < 0. else '0.0'
    # Python repr supplies the shortest correctly rounded f64 decimal digits.
    # Retain those digits, but use the pinned zmij f64 notation range [-5,15],
    # mandatory .0 on fixed integral floats, and unpadded signed exponent.
    sign = '-' if value < 0 else ''
    parts = Decimal(repr(abs(value))).as_tuple()
    digits = ''.join(str(d) for d in parts.digits)
    exponent = parts.exponent
    while len(digits) > 1 and digits[-1] == '0':
        digits = digits[:-1]
        exponent += 1
    decimal_exponent = len(digits) + exponent - 1
    if -5 <= decimal_exponent <= 15:
        cut = len(digits) + exponent
        if cut <= 0:
            token = '0.' + '0' * (-cut) + digits
        elif cut >= len(digits):
            token = digits + '0' * (cut - len(digits)) + '.0'
        else:
            token = digits[:cut] + '.' + digits[cut:]
    else:
        token = digits[0] + ('.' + digits[1:] if len(digits) > 1 else '')
        token += 'e' + ('+' if decimal_exponent >= 0 else '-') + str(abs(decimal_exponent))
    return sign + token


def mesh_array_bytes(values, integer=False):
    """Compact array bytes at the same typed boundary as production hash(Value)."""
    _require(isinstance(values, list), 'mesh hash array required')
    def encode(value):
        if isinstance(value, list):
            return '[' + ','.join(encode(v) for v in value) + ']'
        if integer:
            _require(type(value) is int and 0 <= value <= 0xffffffff, 'mesh index hash needs u32 integer')
            return str(value)
        return promoted_f32_token(value)
    return encode(values).encode('ascii')


def mesh_array_sha256(values, integer=False):
    return hashlib.sha256(mesh_array_bytes(values, integer)).hexdigest()
