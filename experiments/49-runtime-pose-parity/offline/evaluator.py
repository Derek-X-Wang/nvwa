"""Independent glTF 2 evaluator. Python standard library only; no Bevy imports.

Matrices are row-major internally and explicitly column-major in exported JSON.
This oracle predicts playback of serialized bytes, not correctness of retargeting.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct


CLIP = 'genuine44_calibrated47'
KEYS = [0, 15, 30, 45, 60, 75, 89]
ROOT = Path(__file__).resolve().parents[3]
GLB_PATH = ROOT / 'experiments/48-genuine-fixture-work/artifacts/assets/generated/genuine44-calibrated47.glb'
WORK_PATH = ROOT / 'experiments/48-genuine-fixture-work/artifacts/genuine44-calibrated47.nvwa.json'
GLB_SHA = 'c343f6cf47dc0a7c0b09f13ad7d21cf2706a08fb1cfdaca233f14edab02e44fc'
WORK_SHA = '7668eb7a2a2f87070500cbf49fa27d6794aa1fb83f5392b75a0ff51667cde779'


class Rejected(ValueError):
    pass


def require(value, message):
    if not value:
        raise Rejected(message)


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def strict_loads(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key '+key)
            result[key] = value
        return result
    def bad(value):
        raise Rejected('nonfinite JSON '+value)
    return json.loads(data, object_pairs_hook=pairs, parse_constant=bad)


def finite_vector(value, size, label):
    require(isinstance(value, list) and len(value) == size and
            all(type(v) in (int, float) and math.isfinite(v) for v in value), label)
    return value


def identity():
    return [[float(r == c) for c in range(4)] for r in range(4)]


def multiply(a, b):
    return [[sum(a[r][k] * b[k][c] for k in range(4)) for c in range(4)] for r in range(4)]


def column_major(matrix):
    return [matrix[r][c] for c in range(4) for r in range(4)]


def from_column_major(values):
    finite_vector(values, 16, 'finite column-major matrix')
    return [[values[c * 4 + r] for c in range(4)] for r in range(4)]


def transform(matrix, point):
    p = list(point) + [1.0]
    return [sum(matrix[r][c] * p[c] for c in range(4)) for r in range(3)]


def trs(translation, rotation, scale):
    # glTF's stored quaternion is unit-length. Do not renormalize it here:
    # doing so could hide malformed bytes or a runtime scale/axis error.
    x, y, z, w = finite_vector(rotation, 4, 'quaternion')
    finite_vector(translation, 3, 'translation')
    finite_vector(scale, 3, 'scale')
    require(abs(sum(v*v for v in rotation)-1) < 2e-6, 'unit glTF quaternion')
    m = [[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w), translation[0]],
         [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w), translation[1]],
         [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y), translation[2]],
         [0., 0., 0., 1.]]
    for row in range(3):
        for col in range(3):
            m[row][col] *= scale[col]
    return m


def quaternion_error(a, b):
    finite_vector(a, 4, 'actual quaternion')
    finite_vector(b, 4, 'expected quaternion')
    return min(max(abs(x-y) for x, y in zip(a, b)), max(abs(x+y) for x, y in zip(a, b)))


def max_error(a, b):
    require(len(a) == len(b), 'comparison dimensions')
    require(all(type(v) in (int, float) and math.isfinite(v) for v in a+b), 'finite comparison')
    return max(abs(x-y) for x, y in zip(a, b))


class Asset:
    def __init__(self, path=GLB_PATH):
        self.path = Path(path)
        require(digest(self.path) == GLB_SHA, 'pinned experiment48 GLB bytes')
        raw = self.path.read_bytes()
        require(struct.unpack_from('<III', raw) == (0x46546C67, 2, len(raw)), 'GLB header')
        chunks = []
        offset = 12
        while offset < len(raw):
            length, kind = struct.unpack_from('<II', raw, offset)
            offset += 8
            require(length % 4 == 0 and offset+length <= len(raw), 'GLB chunk bounds')
            chunks.append((kind, raw[offset:offset+length]))
            offset += length
        require([kind for kind, _ in chunks] == [0x4E4F534A, 0x004E4942], 'JSON/BIN chunks')
        self.doc = strict_loads(chunks[0][1])
        self.binary = chunks[1][1]
        require(len(self.doc['buffers']) == 1 and 'uri' not in self.doc['buffers'][0], 'embedded buffer')
        self.nodes = self.doc['nodes']
        self.parents = [None] * len(self.nodes)
        for parent, node in enumerate(self.nodes):
            for child in node.get('children', []):
                require(type(child) is int and 0 <= child < len(self.nodes), 'child index')
                require(self.parents[child] is None, 'multiple node parents')
                self.parents[child] = parent
        self.roots = self.doc['scenes'][self.doc.get('scene', 0)]['nodes']
        self.active = set()
        def walk(i, ancestors):
            require(i not in ancestors, 'node cycle')
            self.active.add(i)
            for child in self.nodes[i].get('children', []):
                walk(child, ancestors | {i})
        for node in self.roots:
            require(self.parents[node] is None, 'scene root has parent')
            walk(node, set())
        self.clip_index = next(i for i, a in enumerate(self.doc['animations']) if a.get('name') == CLIP)
        self.clip = self.doc['animations'][self.clip_index]
        self.channels = {}
        self.times = None
        for channel in self.clip['channels']:
            target = channel['target']
            sampler = self.clip['samplers'][channel['sampler']]
            require(sampler.get('interpolation', 'LINEAR') == 'LINEAR', 'fixture LINEAR channel')
            times = [row[0] for row in self.accessor(sampler['input'])]
            require(times == [f32(i/30) for i in range(90)], 'exact 90 binary32 times')
            require(self.times is None or times == self.times, 'same channel timeline')
            self.times = times
            key = (target['node'], target['path'])
            require(key not in self.channels and target['path'] in ('rotation', 'translation', 'scale'), 'unique TRS channel')
            values = self.accessor(sampler['output'])
            require(len(values) == len(times), 'channel key counts')
            self.channels[key] = values

    def accessor(self, index):
        accessor = self.doc['accessors'][index]
        require('sparse' not in accessor, 'sparse unsupported, fail closed')
        view = self.doc['bufferViews'][accessor['bufferView']]
        require(view.get('buffer', 0) == 0, 'accessor buffer')
        formats = {5120: ('b', 1), 5121: ('B', 1), 5122: ('h', 2), 5123: ('H', 2), 5125: ('I', 4), 5126: ('f', 4)}
        fmt, size = formats[accessor['componentType']]
        width = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[accessor['type']]
        stride = view.get('byteStride', width*size)
        start = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
        end = start + (accessor['count']-1)*stride + width*size
        require(stride >= width*size and end <= view.get('byteOffset', 0)+view['byteLength'] and end <= self.doc['buffers'][0]['byteLength'], 'accessor bounds')
        rows = [list(struct.unpack_from('<'+fmt*width, self.binary, start+i*stride)) for i in range(accessor['count'])]
        if accessor.get('normalized', False):
            require(accessor['componentType'] != 5126, 'normalized float')
            denom = {5120: 127, 5121: 255, 5122: 32767, 5123: 65535, 5125: 4294967295}[accessor['componentType']]
            rows = [[max(-1, v/denom) for v in row] for row in rows]
        require(all(math.isfinite(v) for row in rows for v in row), 'finite accessor')
        return rows

    def pose(self, key, character_root=None):
        require(type(key) is int and 0 <= key < 90, 'source key')
        base = character_root if character_root is not None else identity()
        locals_ = {}
        globals_ = {}
        for index in sorted(self.active):
            node = self.nodes[index]
            require('matrix' not in node, 'fixture uses TRS nodes')
            values = {path: list(self.channels[index, path][key] if (index, path) in self.channels else node.get(path, default))
                      for path, default in [('translation', [0., 0., 0.]), ('rotation', [0., 0., 0., 1.]), ('scale', [1., 1., 1.])]}
            locals_[index] = values
        def global_for(index):
            if index not in globals_:
                parent = self.parents[index]
                before = base if parent is None else global_for(parent)
                globals_[index] = multiply(before, trs(**locals_[index]))
            return globals_[index]
        for index in locals_:
            global_for(index)
        return locals_, globals_

    def skin_vertices(self, key, mesh_node, primitive, character_root=None, globals_override=None):
        node = self.nodes[mesh_node]
        skin = self.doc['skins'][node['skin']]
        mesh = self.doc['meshes'][node['mesh']]['primitives'][primitive]
        attrs = mesh['attributes']
        points = self.accessor(attrs['POSITION'])
        joints = self.accessor(attrs['JOINTS_0'])
        weights = self.accessor(attrs['WEIGHTS_0'])
        require(len(points) == len(joints) == len(weights), 'skin vertex dimensions')
        # Work has all morph parameters zero. Nonzero morphs require an explicit
        # separate evaluator; do not silently compare a morphed capture here.
        inverse = [from_column_major(v) for v in self.accessor(skin['inverseBindMatrices'])]
        globals_ = globals_override if globals_override is not None else self.pose(key, character_root)[1]
        matrices = [multiply(globals_[joint], inverse[i]) for i, joint in enumerate(skin['joints'])]
        result = []
        for point, js, ws in zip(points, joints, weights):
            require(abs(sum(ws)-1) <= 2e-6, 'weights sum')
            out = [0., 0., 0.]
            for joint, weight in zip(js, ws):
                require(type(joint) is int and 0 <= joint < len(matrices), 'skin joint slot')
                if weight:
                    moved = transform(matrices[joint], point)
                    for axis in range(3):
                        out[axis] += weight*moved[axis]
            result.append(out)
        return result

    def expectation(self, keys=KEYS):
        require(digest(WORK_PATH) == WORK_SHA, 'pinned experiment48 Work bytes')
        work = strict_loads(WORK_PATH.read_text())
        require(work['character']['scale'] == 1 and all(v == 0 for v in work['character']['parameters'].values()), 'fixture Work scale and zero morphs')
        samples = []
        for key in keys:
            locals_, globals_ = self.pose(key)
            samples.append({'key_index': key, 'time_seconds': self.times[key], 'nodes': [
                {'node_index': i, 'name': self.nodes[i].get('name'), 'parent_node_index': self.parents[i],
                 **locals_[i], 'global_matrix_columns': column_major(globals_[i])} for i in sorted(self.active)]})
        return {'schema': 'nvwa.experiment49.serialized-expectation.v1',
                'source': 'independent glTF channels + static TRS + full hierarchy; serialized scene space',
                'glb_sha256': digest(self.path), 'work_sha256': digest(WORK_PATH),
                'clip_id': CLIP, 'animation_index': self.clip_index,
                'skin_bindings': [{'mesh_node_index': i, 'mesh_index': n['mesh'], 'skin_index': n['skin'],
                                   'joint_node_indices': self.doc['skins'][n['skin']]['joints']}
                                  for i, n in enumerate(self.nodes) if 'skin' in n],
                'samples': samples}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--all-keys', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = Asset().expectation(range(90) if args.all_keys else KEYS)
    data = json.dumps(result, indent=2, allow_nan=False)+'\n'
    if args.output:
        args.output.write_text(data)
    else:
        print(data, end='')


if __name__ == '__main__':
    main()
