#!/usr/bin/env python3
"""Controlled coordinate-basis retargeting experiment on the real Nvwa GLB.

No external target asset, AI generation, IK, or general retargeting framework.
Uses numpy already available in the local Python environment.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import struct

import numpy as np


class InputError(ValueError):
    pass


def quaternion(q):
    q = np.asarray(q, dtype=float)
    if q.shape != (4,) or not np.isfinite(q).all() or np.linalg.norm(q) < 1e-12:
        raise InputError("invalid/degenerate quaternion")
    return q / np.linalg.norm(q)


def multiply(a, b):
    a, b = quaternion(a), quaternion(b)
    av, aw, bv, bw = a[:3], a[3], b[:3], b[3]
    return quaternion(np.r_[aw * bv + bw * av + np.cross(av, bv), aw * bw - av @ bv])


def inverse(q):
    q = quaternion(q)
    return np.r_[-q[:3], q[3]]


def rotation(q):
    x, y, z, w = quaternion(q)
    return np.array([
        [1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
        [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
        [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)],
    ])


def quarter(axis):
    q = np.zeros(4)
    q[axis] = np.sqrt(0.5)
    q[3] = np.sqrt(0.5)
    return q


def trs(t, q, s):
    t, s = np.asarray(t), np.asarray(s)
    if t.shape != (3,) or s.shape != (3,) or not np.isfinite(t).all() or not np.isfinite(s).all() or np.any(np.abs(s) < 1e-12):
        raise InputError("invalid/degenerate transform")
    m = np.eye(4)
    m[:3, :3] = rotation(q) @ np.diag(s)
    m[:3, 3] = t
    return m


def slerp(a, b, amount):
    a, b = quaternion(a), quaternion(b)
    dot = float(a @ b)
    if dot < 0:
        b, dot = -b, -dot
    dot = min(1.0, max(-1.0, dot))
    if dot > 0.9995:
        return quaternion(a + amount * (b-a))
    angle = np.arccos(dot)
    return quaternion((np.sin((1-amount)*angle)*a + np.sin(amount*angle)*b) / np.sin(angle))


DTYPES = {5120: '<i1', 5121: '<u1', 5122: '<i2', 5123: '<u2', 5125: '<u4', 5126: '<f4'}
SIZES = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


class Glb:
    def __init__(self, path):
        self.path = Path(path)
        self.source_bytes = self.path.read_bytes()
        b = self.source_bytes
        if len(b) < 12 or b[:4] != b'glTF' or struct.unpack_from('<II', b, 4) != (2, len(b)):
            raise InputError('invalid GLB header')
        chunks, offset = {}, 12
        while offset < len(b):
            if offset + 8 > len(b):
                raise InputError('truncated GLB chunk')
            length, kind = struct.unpack_from('<II', b, offset)
            offset += 8
            if length % 4 or offset + length > len(b) or kind in chunks:
                raise InputError('invalid GLB chunk')
            chunks[kind] = b[offset:offset+length]
            offset += length
        if 0x4E4F534A not in chunks or 0x004E4942 not in chunks:
            raise InputError('GLB requires JSON and binary chunks')
        self.json = json.loads(chunks[0x4E4F534A])
        self.binary = bytearray(chunks[0x004E4942])
        self.parents = {}
        for parent, node in enumerate(self.json['nodes']):
            for child in node.get('children', []):
                if child in self.parents:
                    raise InputError('node has multiple parents')
                self.parents[child] = parent

    def accessor(self, index):
        a = self.json['accessors'][index]
        if 'sparse' in a or 'bufferView' not in a:
            raise InputError('sparse/missing accessor unsupported by bounded spike')
        view = self.json['bufferViews'][a['bufferView']]
        if view.get('buffer', 0) != 0:
            raise InputError('external buffer unsupported')
        dtype = np.dtype(DTYPES[a['componentType']])
        width = SIZES[a['type']]
        start = view.get('byteOffset', 0) + a.get('byteOffset', 0)
        stride = view.get('byteStride', width*dtype.itemsize)
        end = start + (a['count']-1)*stride + width*dtype.itemsize
        if a['count'] < 1 or end > len(self.binary):
            raise InputError('out-of-bounds accessor')
        values = np.ndarray((a['count'], width), dtype=dtype, buffer=self.binary,
                            offset=start, strides=(stride, dtype.itemsize)).copy()
        if a.get('normalized'):
            if dtype.kind != 'u':
                raise InputError('signed normalized accessor unsupported')
            values = values.astype(float) / np.iinfo(dtype).max
        if not np.isfinite(values).all():
            raise InputError('nonfinite accessor')
        if a['type'] == 'MAT4':
            return values.reshape(-1, 4, 4).transpose(0, 2, 1)
        return values

    def add_accessor(self, values, kind):
        values = np.asarray(values, dtype='<f4')
        if kind == 'MAT4':
            values = values.transpose(0, 2, 1).reshape(-1, 16)
        while len(self.binary) % 4:
            self.binary.append(0)
        start, raw = len(self.binary), values.tobytes()
        self.binary.extend(raw)
        view_index = len(self.json['bufferViews'])
        self.json['bufferViews'].append({'buffer': 0, 'byteOffset': start, 'byteLength': len(raw)})
        index = len(self.json['accessors'])
        self.json['accessors'].append({'bufferView': view_index, 'componentType': 5126,
                                      'count': len(values), 'type': kind})
        return index

    def write(self, path):
        self.json['buffers'][0]['byteLength'] = len(self.binary)
        j = json.dumps(self.json, separators=(',', ':')).encode()
        j += b' ' * (-len(j) % 4)
        binary = bytes(self.binary) + b'\0' * (-len(self.binary) % 4)
        length = 12 + 8 + len(j) + 8 + len(binary)
        data = b'glTF' + struct.pack('<II', 2, length)
        data += struct.pack('<II', len(j), 0x4E4F534A) + j
        data += struct.pack('<II', len(binary), 0x004E4942) + binary
        Path(path).write_bytes(data)

    def locals(self, animation=None, time=0):
        nodes = self.json['nodes']
        parts = [{
            'translation': np.array(n.get('translation', [0, 0, 0]), dtype=float),
            'rotation': np.array(n.get('rotation', [0, 0, 0, 1]), dtype=float),
            'scale': np.array(n.get('scale', [1, 1, 1]), dtype=float),
        } for n in nodes]
        if animation is not None:
            for channel in animation['channels']:
                sampler = animation['samplers'][channel['sampler']]
                if sampler.get('interpolation', 'LINEAR') != 'LINEAR':
                    raise InputError('non-LINEAR animation unsupported')
                target, path = channel['target']['node'], channel['target']['path']
                if path not in parts[target]:
                    raise InputError('non-TRS animation unsupported')
                times = self.accessor(sampler['input'])[:, 0]
                values = self.accessor(sampler['output'])
                if len(times) != len(values) or np.any(np.diff(times) <= 0):
                    raise InputError('degenerate/non-increasing animation times')
                hi = min(len(times)-1, max(1, int(np.searchsorted(times, time, side='right'))))
                lo = hi-1
                amount = float(np.clip((time-times[lo])/(times[hi]-times[lo]), 0, 1))
                value = slerp(values[lo], values[hi], amount) if path == 'rotation' else values[lo]*(1-amount)+values[hi]*amount
                parts[target][path] = value
        result = []
        for node, part in zip(nodes, parts):
            if 'matrix' in node:
                raise InputError('matrix node unsupported in this TRS spike')
            result.append(trs(part['translation'], part['rotation'], part['scale']))
        return result

    def globals(self, locals_):
        result, active = {}, set()
        def visit(i):
            if i in active:
                raise InputError('cyclic skeleton')
            if i in result:
                return result[i]
            active.add(i)
            result[i] = visit(self.parents[i]) @ locals_[i] if i in self.parents else locals_[i]
            active.remove(i)
            return result[i]
        return [visit(i) for i in range(len(locals_))]

    def animation(self, name):
        matches = [a for a in self.json['animations'] if a.get('name') == name]
        if len(matches) != 1:
            raise InputError(f'expected exactly one animation named {name}')
        return matches[0]

    def vertices(self, globals_):
        result = []
        for i, node in enumerate(self.json['nodes']):
            if 'mesh' not in node or 'skin' not in node:
                continue
            skin = self.json['skins'][node['skin']]
            ibm = self.accessor(skin['inverseBindMatrices'])
            matrices = np.array([globals_[joint] @ ibm[k] for k, joint in enumerate(skin['joints'])])
            for primitive in self.json['meshes'][node['mesh']]['primitives']:
                attrs = primitive['attributes']
                positions = self.accessor(attrs['POSITION'])
                joints = self.accessor(attrs['JOINTS_0']).astype(int)
                weights = self.accessor(attrs['WEIGHTS_0']).astype(float)
                if np.any(joints < 0) or np.any(joints >= len(matrices)):
                    raise InputError('invalid skin joint reference')
                p4 = np.c_[positions, np.ones(len(positions))]
                transformed = np.einsum('nkij,nj->nki', matrices[joints], p4)
                result.append(np.sum(transformed * weights[:, :, None], axis=1)[:, :3])
        if not result:
            raise InputError('missing skinned geometry')
        return np.concatenate(result)


def make_target(source, bases, corrected):
    target = copy.deepcopy(source)
    ident = np.array([0., 0., 0., 1.])
    basis = lambda i: bases.get(i, ident)
    def converted(i, path, values):
        parent = basis(source.parents.get(i, -1))
        own = basis(i)
        values = np.asarray(values)
        if path == 'translation':
            return values @ rotation(parent)
        if path == 'scale':
            return values @ np.abs(rotation(own))
        if path == 'rotation':
            return np.array([multiply(multiply(inverse(parent), q), own) for q in values])
        raise InputError('unsupported animation channel')
    for i, node in enumerate(target.json['nodes']):
        for path, default in [('translation', [0,0,0]), ('rotation', [0,0,0,1]), ('scale', [1,1,1])]:
            node[path] = converted(i, path, [node.get(path, default)])[0].tolist()
    for skin in target.json['skins']:
        ibm = source.accessor(skin['inverseBindMatrices'])
        for k, joint in enumerate(skin['joints']):
            c = np.eye(4)
            c[:3, :3] = rotation(basis(joint))
            ibm[k] = np.linalg.inv(c) @ ibm[k]
        skin['inverseBindMatrices'] = target.add_accessor(ibm, 'MAT4')
    for animation in target.json['animations']:
        animation['extras'] = {'experiment': 'controlled basis derivative', 'rotation_mapping': 'corrected' if corrected else 'naive copy'}
        for channel in animation['channels']:
            path, i = channel['target']['path'], channel['target']['node']
            sampler = animation['samplers'][channel['sampler']]
            if path == 'rotation' and not corrected:
                continue
            values = source.accessor(sampler['output'])
            values = converted(i, path, values)
            sampler['output'] = target.add_accessor(values, 'VEC4' if path == 'rotation' else 'VEC3')
    target.json['asset']['extras'] = {'source_sha256': hashlib.sha256(source.source_bytes).hexdigest(),
                                      'derivative': 'controlled target rig, equivalent geometry, changed joint coordinate bases',
                                      'ai_generated': False}
    return target


def max_distance(a, b):
    return float(np.linalg.norm(np.asarray(a)-np.asarray(b), axis=-1).max())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='assets/fixtures/nvwa-humanoid.glb')
    parser.add_argument('--out', default='experiments/04-retarget-basis')
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    source = Glb(args.source)
    names = {node['name']: i for i, node in enumerate(source.json['nodes']) if 'name' in node}
    required = ['chest', 'upper_arm.R', 'forearm.R', 'hand.R']
    if any(name not in names for name in required):
        raise InputError('required humanoid joints missing')
    basis_by_name = {'chest': quarter(1), 'upper_arm.R': quarter(2), 'forearm.R': quarter(0), 'hand.R': quarter(1)}
    bases = {names[name]: q for name, q in basis_by_name.items()}
    source.animation('wave')
    corrected, naive = make_target(source, bases, True), make_target(source, bases, False)
    identity = make_target(source, {}, True)
    corrected.write(out/'target-corrected.glb')
    naive.write(out/'target-naive.glb')
    # Measure the serialized float32 outputs, not only pre-export math.
    corrected, naive = Glb(out/'target-corrected.glb'), Glb(out/'target-naive.glb')
    source_rest = source.globals(source.locals())
    target_rest = corrected.globals(corrected.locals())
    rest_error = max_distance(source.vertices(source_rest), corrected.vertices(target_rest))
    joints = source.json['skins'][0]['joints']
    times = np.sort(np.r_[np.linspace(0, 3, 13), [0.123, 0.567, 1.111, 1.789, 2.345, 2.987]])
    rows, identity_error = [], 0.
    for time in times:
        sg = source.globals(source.locals(source.animation('wave'), float(time)))
        cg = corrected.globals(corrected.locals(corrected.animation('wave'), float(time)))
        ng = naive.globals(naive.locals(naive.animation('wave'), float(time)))
        ig = identity.globals(identity.locals(identity.animation('wave'), float(time)))
        positions = lambda globals_: np.array([globals_[i][:3,3] for i in joints])
        identity_error = max(identity_error, max_distance(source.vertices(sg), identity.vertices(ig)))
        rows.append({
            'time_seconds': float(time),
            'naive_hand_error_m': float(np.linalg.norm(sg[names['hand.R']][:3,3]-ng[names['hand.R']][:3,3])),
            'corrected_hand_error_m': float(np.linalg.norm(sg[names['hand.R']][:3,3]-cg[names['hand.R']][:3,3])),
            'naive_max_joint_error_m': max_distance(positions(sg), positions(ng)),
            'corrected_max_joint_error_m': max_distance(positions(sg), positions(cg)),
            'naive_max_vertex_error_m': max_distance(source.vertices(sg), naive.vertices(ng)),
            'corrected_max_vertex_error_m': max_distance(source.vertices(sg), corrected.vertices(cg)),
        })
    degenerate_checks = {}
    for label, function in [('zero_quaternion', lambda: quaternion([0,0,0,0])),
                            ('nonfinite_quaternion', lambda: quaternion([0,np.nan,0,1])),
                            ('singular_scale', lambda: trs([0,0,0],[0,0,0,1],[1,0,1]))]:
        try:
            function()
        except InputError as error:
            degenerate_checks[label] = str(error)
        else:
            raise AssertionError(f'degenerate check accepted: {label}')
    broken = copy.deepcopy(source)
    broken.json['nodes'][names['upper_arm.R']]['rotation'] = [0, 0, 0, 0]
    try:
        broken.locals()
    except InputError as error:
        degenerate_checks['actual_rig_zero_joint_quaternion'] = str(error)
    else:
        raise AssertionError('actual-rig degenerate quaternion accepted')
    assert Path(args.source).read_bytes() == source.source_bytes, 'source asset changed'
    metrics = {
        'source': str(Path(args.source)), 'source_sha256': hashlib.sha256(source.source_bytes).hexdigest(),
        'numpy_version': np.__version__, 'vertex_count': len(source.vertices(source_rest)), 'joint_count': len(joints),
        'basis_changes': {name: q.tolist() for name, q in basis_by_name.items()},
        'rest_max_vertex_error_m': rest_error, 'identity_max_vertex_error_m': identity_error,
        'degenerate_input_errors': degenerate_checks, 'samples': rows,
        'max_naive_hand_error_m': max(r['naive_hand_error_m'] for r in rows),
        'max_corrected_hand_error_m': max(r['corrected_hand_error_m'] for r in rows),
        'max_naive_joint_error_m': max(r['naive_max_joint_error_m'] for r in rows),
        'max_corrected_joint_error_m': max(r['corrected_max_joint_error_m'] for r in rows),
        'max_naive_vertex_error_m': max(r['naive_max_vertex_error_m'] for r in rows),
        'max_corrected_vertex_error_m': max(r['corrected_max_vertex_error_m'] for r in rows),
        'output_sha256': {name: hashlib.sha256((out/name).read_bytes()).hexdigest() for name in ['target-naive.glb','target-corrected.glb']},
    }
    assert rest_error < 1e-5, f'rest geometry changed: {rest_error}'
    assert identity_error < 1e-5, f'identity regression: {identity_error}'
    assert metrics['max_corrected_hand_error_m'] < 1e-5
    assert metrics['max_corrected_joint_error_m'] < 1e-5
    assert metrics['max_corrected_vertex_error_m'] < 1e-5
    assert metrics['max_naive_hand_error_m'] > .05, 'control failed to expose naive basis mismatch'
    metrics['decision'] = 'adopt rest-basis correction for this controlled equal-topology case; reject naive local rotation copy'
    (out/'metrics.json').write_text(json.dumps(metrics, indent=2)+'\n')
    print(json.dumps(metrics, indent=2))


if __name__ == '__main__':
    main()
