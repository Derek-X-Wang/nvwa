#!/usr/bin/env python3
"""Read actual GLB accessors, topology, skin weights, morphs and motion.

No Blender or third-party package needed. --publish writes the exact M0 profile
and source/hash manifest after structural validation succeeds.
"""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / 'assets/fixtures/nvwa-humanoid.glb'
MORPHS = ['jaw_width', 'nose_width', 'smile', 'shoulder_width']
# These are the authored first-to-last spans, not the runtime duration from
# time zero. Blender's frame-1 offset can make the last input time larger.
NOMINAL_AUTHORED_SPANS = {'idle': 3.0, 'wave': 3.0, 'turn': 4.0}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read_glb(path):
    raw = path.read_bytes()
    magic, version, length = struct.unpack_from('<4sII', raw)
    assert magic == b'glTF' and version == 2 and length == len(raw)
    offset, doc, binary = 12, None, None
    while offset < len(raw):
        size, kind = struct.unpack_from('<II', raw, offset)
        chunk = raw[offset + 8:offset + 8 + size]
        if kind == 0x4E4F534A:
            doc = json.loads(chunk)
        elif kind == 0x004E4942:
            binary = chunk
        offset += 8 + size
    assert doc is not None and binary is not None
    return doc, binary

def accessor(doc, binary, index):
    acc = doc['accessors'][index]
    assert 'sparse' not in acc, 'Sparse accessor unsupported in this fixture validator'
    view = doc['bufferViews'][acc['bufferView']]
    kinds = {5120: 'b', 5121: 'B', 5122: 'h', 5123: 'H', 5125: 'I', 5126: 'f'}
    counts = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}
    kind, count = kinds[acc['componentType']], counts[acc['type']]
    fmt = '<' + kind * count
    size = struct.calcsize(fmt)
    stride = view.get('byteStride', size)
    offset = view.get('byteOffset', 0) + acc.get('byteOffset', 0)
    rows = [struct.unpack_from(fmt, binary, offset + n * stride) for n in range(acc['count'])]
    if acc.get('normalized') and acc['componentType'] != 5126:
        maximum = {5121: 255, 5123: 65535, 5120: 127, 5122: 32767}[acc['componentType']]
        rows = [tuple(max(-1, val / maximum) for val in row) for row in rows]
    assert all(math.isfinite(val) for row in rows for val in row)
    return rows

def validate(path):
    doc, binary = read_glb(path)
    assert len(doc['skins']) == 1
    skin = doc['skins'][0]
    joint_count = len(skin['joints'])
    assert joint_count >= 16
    binds = accessor(doc, binary, skin['inverseBindMatrices'])
    assert len(binds) == joint_count
    bone_names = [doc['nodes'][idx]['name'] for idx in skin['joints']]
    assert all(name in bone_names for name in ['head', 'pelvis', 'upper_arm.R', 'forearm.R', 'hand.R', 'thigh.L', 'shin.L'])
    body = next(mesh for mesh in doc['meshes'] if mesh.get('extras', {}).get('targetNames') == MORPHS)
    mesh_index = doc['meshes'].index(body)
    body_nodes = [n for n in doc['nodes'] if n.get('mesh') == mesh_index]
    assert len(body_nodes) == 1 and body_nodes[0].get('skin') == 0
    delta_counts = [0] * len(MORPHS)
    delta_max = [0.0] * len(MORPHS)
    vertex_count = weighted = blended = 0
    welded = {}
    adjacency = collections.defaultdict(set)
    for primitive in body['primitives']:
        assert primitive.get('mode', 4) == 4
        assert len(primitive['targets']) == len(MORPHS)
        pos = accessor(doc, binary, primitive['attributes']['POSITION'])
        weights = accessor(doc, binary, primitive['attributes']['WEIGHTS_0'])
        joints = accessor(doc, binary, primitive['attributes']['JOINTS_0'])
        assert len(pos) == len(weights) == len(joints)
        vertex_count += len(pos)
        for row, jrow in zip(weights, joints):
            assert min(row) >= 0 and abs(sum(row) - 1) < 1e-4
            assert all(0 <= idx < joint_count for idx in jrow)
            weighted += int(sum(row) > .99)
            blended += int(sum(value > .01 for value in row) > 1)
        local_welded = []
        for point in pos:
            # glTF duplicates material/normal seams; weld exact source positions.
            local_welded.append(welded.setdefault(point, len(welded)))
        indices = [row[0] for row in accessor(doc, binary, primitive['indices'])]
        assert len(indices) % 3 == 0
        for a, b, c in zip(indices[::3], indices[1::3], indices[2::3]):
            a, b, c = (local_welded[n] for n in (a, b, c))
            adjacency[a].update((b, c)); adjacency[b].update((a, c)); adjacency[c].update((a, b))
        for idx, target in enumerate(primitive['targets']):
            deltas = accessor(doc, binary, target['POSITION'])
            assert len(deltas) == len(pos)
            magnitudes = [math.sqrt(sum(v*v for v in row)) for row in deltas]
            delta_counts[idx] += sum(v > 1e-7 for v in magnitudes)
            delta_max[idx] = max(delta_max[idx], max(magnitudes))
        material = doc['materials'][primitive['material']]
        assert material.get('alphaMode', 'OPAQUE') == 'OPAQUE'
        assert material.get('pbrMetallicRoughness', {}).get('baseColorFactor', [1,1,1,1])[3] == 1
    unseen = set(range(len(welded)))
    components = []
    while unseen:
        pending = [unseen.pop()]; size = 0
        while pending:
            node = pending.pop(); size += 1
            for other in adjacency[node]:
                if other in unseen:
                    unseen.remove(other); pending.append(other)
        components.append(size)
    assert components == [len(welded)], components
    assert weighted == vertex_count and blended > vertex_count * .20
    assert all(count > 100 for count in delta_counts)
    assert all(size > .015 for size in delta_max)
    # Distinct displacement vectors, beyond merely four differently named keys.
    signatures = []
    for idx in range(len(MORPHS)):
        packed = b''.join(struct.pack('<3f', *row) for primitive in body['primitives'] for row in accessor(doc, binary, primitive['targets'][idx]['POSITION']))
        signatures.append(hashlib.sha256(packed).hexdigest())
    assert len(set(signatures)) == len(MORPHS)
    animations = []
    for index, animation in enumerate(doc['animations']):
        name = animation['name']
        assert name in NOMINAL_AUTHORED_SPANS
        all_times = []
        changed_bones = set()
        for channel in animation['channels']:
            sampler = animation['samplers'][channel['sampler']]
            times = accessor(doc, binary, sampler['input'])
            values = accessor(doc, binary, sampler['output'])
            all_times.extend(row[0] for row in times)
            assert len(times) == len(values)
            assert all(a[0] <= b[0] for a,b in zip(times,times[1:]))
            if any(max(abs(a-b) for a,b in zip(values[0],row)) > 1e-4 for row in values[1:]):
                node = channel['target'].get('node')
                assert node in skin['joints'], 'Animation change must target a skeleton joint'
                changed_bones.add(doc['nodes'][node]['name'])
        first_time, duration = min(all_times), max(all_times)
        authored_span = duration - first_time
        assert first_time >= 0
        assert abs(authored_span - NOMINAL_AUTHORED_SPANS[name]) < .002, (name, authored_span)
        assert changed_bones
        if name == 'wave':
            assert {'upper_arm.R', 'forearm.R', 'hand.R'}.issubset(changed_bones)
        animations.append({'id': name, 'animation_index': index, 'duration_seconds': duration,
                           'first_keyframe_seconds': first_time, 'authored_span_seconds': authored_span,
                           'changed_bones': sorted(changed_bones)})
    assert {a['id'] for a in animations} == set(NOMINAL_AUTHORED_SPANS)
    return {'status': 'PASS', 'glb_sha256': digest(path), 'glb_bytes': path.stat().st_size,
            'joint_count': joint_count, 'joint_names': bone_names, 'primary_mesh': body_nodes[0]['name'],
            'material_split_vertex_count': vertex_count, 'welded_vertex_count': len(welded),
            'continuous_surface_components': components, 'weighted_vertices': weighted,
            'vertices_with_multiple_influences': blended, 'opaque_materials': True,
            'morphs': [{'id': name, 'morph_index': i, 'nonzero_vertices_with_seams': delta_counts[i], 'maximum_displacement_metres': delta_max[i], 'delta_sha256': signatures[i]} for i, name in enumerate(MORPHS)],
            'clips': animations, 'validation_scope': 'GLB binary structure and numeric deformation data; no native or Web runtime claim'}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    result = validate(FIXTURE)
    print(json.dumps(result, indent=2))
    if args.publish:
        profile = {'id': 'nvwa-original-humanoid-v1', 'asset_path': 'fixtures/nvwa-humanoid.glb',
                   'asset_sha256': result['glb_sha256'], 'license': 'CC0-1.0 (original Nvwa test fixture only)',
                   'parameters': [{'id': name, 'morph_index': i, 'min': 0.0, 'max': 1.0, 'default': 0.0} for i, name in enumerate(MORPHS)],
                   'clips': [{key: clip[key] for key in ('id', 'animation_index', 'duration_seconds')} for clip in result['clips']]}
        profile_path = ROOT / 'assets/character.profile.json'
        profile_text = json.dumps(profile, indent=2) + '\n'
        # Preserve the published profile (including mtime) when unchanged;
        # consumers may be compiling it into their runtime at the same time.
        if not profile_path.exists() or profile_path.read_text() != profile_text:
            profile_path.write_text(profile_text)
        (ROOT / 'experiments/01-character/structural-validation.json').write_text(json.dumps(result, indent=2) + '\n')
        paths = ['assets/fixtures/nvwa-humanoid.glb', 'assets/fixtures/nvwa-humanoid.blend',
                 'assets/fixtures/source-structure.json', 'assets/character.profile.json',
                 'tools/blender/generate_fixture.py', 'tools/blender/validate_fixture.py',
                 'tools/blender/check_reproducibility.py', 'assets/fixtures/LICENSE.txt',
                 'experiments/01-character/structural-validation.json']
        paths += [str(path.relative_to(ROOT)) for path in sorted((ROOT/'assets/fixtures').glob('preview-*.png'))]
        if (ROOT/'experiments/01-character/reproducibility.json').exists():
            paths.append('experiments/01-character/reproducibility.json')
        manifest = {'fixture_id': profile['id'], 'license': 'CC0-1.0',
                    'scope': 'Original fixture, generation/validation sources, previews, and their metadata only; no license assigned to the repository.',
                    'provenance': 'Original agent-authored geometry coordinates, voxel-union topology, numeric morph displacement functions, smooth skin weights, opaque material colors, and manually authored skeletal presets. User authorized original distributable M0 test fixture. No third-party character, texture, mocap, AI motion, or purchased asset.',
                    'generation_command': '/opt/homebrew/bin/blender -b -t 2 --python tools/blender/generate_fixture.py',
                    'validation_command': 'python3 tools/blender/validate_fixture.py --publish',
                    'generator_version': 'Blender 3.3.1 arm64; exporter bundled with Blender',
                    'files': [{'path': name, 'sha256': digest(ROOT/name), 'bytes': (ROOT/name).stat().st_size} for name in paths]}
        (ROOT / 'assets/fixtures/provenance-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')

if __name__ == '__main__':
    main()
