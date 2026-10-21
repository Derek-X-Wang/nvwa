#!/usr/bin/env python3
"""Authenticate only original neutral fitted rest; never author or score a candidate."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'experiments/81-shoulder-patch-corrective'))
from author_patch import authenticate

BOUND_M = 1e-7  # Frozen before first original-anchor reconstruction, not candidate residual tuning.


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def add(a, b):
    return f32(a + b)


def raw(values):
    return b''.join(struct.pack('<f', x) for p in values for x in p)


def vertices(path):
    return [[f32(float(x)) for x in line.split()[1:4]]
            for line in path.read_text().splitlines() if line.startswith('v ')]


def neutral_fit(asset):
    helpers = vertices(asset / 'base.obj')
    scales = {}; rows = []; active = False
    for line in (asset / 'garment/female_sportsuit01.mhclo').read_text().splitlines():
        tokens = line.split()
        if not tokens:
            continue
        if tokens[0] in ('x_scale', 'y_scale', 'z_scale'):
            axis = {'x_scale': 0, 'y_scale': 1, 'z_scale': 2}[tokens[0]]
            denominator = f32(float(tokens[3]))
            span = add(helpers[int(tokens[2])][axis], -helpers[int(tokens[1])][axis])
            if not (denominator > 0 and span > 0):
                raise ValueError('nonpositive original scale reference')
            scales[axis] = f32(span / denominator)
        if tokens[0] == 'verts':
            active = True
            continue
        if tokens[0] == 'delete_verts':
            break
        if active:
            if len(tokens) != 9:
                raise ValueError('unexpected garment helper row')
            ids = list(map(int, tokens[:3]))
            weights = [f32(float(x)) for x in tokens[3:6]]
            total = add(add(weights[0], weights[1]), weights[2])
            if abs(total) > 2 ** -23:
                weights = [f32(w / total) for w in weights]
            offsets = [f32(float(x)) for x in tokens[6:9]]
            rows.append((ids, weights, offsets))
    fitted = []
    for ids, weights, offsets in rows:
        point = []
        for axis in range(3):
            acc = 0.0
            for source, weight in zip(ids, weights):
                acc = add(acc, f32(helpers[source][axis] * weight))
            point.append(add(acc, f32(scales[axis] * offsets[axis])))
        fitted.append(point)
    return helpers, fitted, [scales[i] for i in range(3)]


def preflight(retained):
    frame = authenticate(retained)
    helpers, fitted, scales = neutral_fit(ROOT / 'assets/characters/mpfb-b1-v2')
    result = {'status': 'PASS', 'candidate_created': False, 'bound_m_component_absolute_frozen_before_run': BOUND_M,
              'method': 'original signed ordered scalar f32 neutral fit; unchanged81 original capsule authentication',
              'scale_f32': scales, 'roles': {}, 'scope': 'Original pre-skin rest only; no planes/amplitude/candidate/scoring'}
    for part in frame['full_base']['parts']:
        if part['name'] not in ('body', 'garment'):
            continue
        lookup = helpers if part['name'] == 'body' else fitted
        calculated = [lookup[source] for source in part['source_ids']]
        observed = part['rest_positions']
        if len(calculated) != len(observed):
            raise ValueError('rest length mismatch')
        errors = [abs(a-b) for p, q in zip(calculated, observed) for a, b in zip(p, q)]
        cb, ob = raw(calculated), raw(observed)
        result['roles'][part['name']] = {'render_rows': len(observed), 'max_abs_component_error_m': max(errors),
            'nonexact_numeric_components': sum(e != 0 for e in errors), 'raw_f32_bit_exact': cb == ob,
            'calculated_sha256_le_f32': hashlib.sha256(cb).hexdigest(),
            'observed_sha256_le_f32': hashlib.sha256(ob).hexdigest()}
        if max(errors) > BOUND_M:
            result['status'] = 'FAIL'
    result['original_anchor_sha256'] = hashlib.sha256((retained / 'h80proof-v1/combined/capture.json').read_bytes()).hexdigest()
    result['preflight_source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--retained', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit('refuse to overwrite receipt')
    result = preflight(args.retained)
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['status'] == 'PASS' else 1)
