"""Fail-closed adapter for probe/SCHEMA.md v1. Never writes to raw captures."""
import argparse
import json
import math
from pathlib import Path
import struct

from evaluator import (Asset, CLIP, KEYS, WORK_PATH, WORK_SHA, Rejected, column_major,
                       digest, finite_vector, from_column_major, identity,
                       max_error, multiply, quaternion_error, require, strict_loads, transform, trs)

SCHEDULE = 'PostUpdate.after(AnimationSystems).after(TransformSystems::Propagate)'
# Frozen ahead of runtime exposure. Local thresholds cover several binary32
# operation ulps; global threshold covers accumulated <=18-joint propagation.
# No fitted alignment, unit conversion, quaternion normalization or root removal.
TOL = {'local_translation_m': 2e-6, 'local_rotation_component': 2e-6,
       'local_scale': 2e-6, 'global_matrix_component': 2e-5,
       'inverse_bind_component': 2e-6, 'skinned_vertex_m': 3e-5}


def bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def same_work(actual, expected, path=()):
    """Typed exact comparison except declared nvwa-core f32 schema leaves.

    Source: crates/nvwa-core/src/lib.rs SceneDocument structs, not observed
    output. Only f32 decimal spellings can round to the same binary32 value.
    Unknown/missing keys still fail; integers, booleans and strings stay typed.
    """
    f32_field = (
        len(path) == 4 and path[:2] == ('profile', 'parameters') and path[-1] in ('min', 'max', 'default') or
        len(path) == 4 and path[:2] == ('profile', 'clips') and path[-1] == 'duration_seconds' or
        path == ('character', 'scale') or
        len(path) == 3 and path[:2] == ('character', 'parameters') or
        len(path) == 3 and path[0] == 'timeline' and path[-1] in ('start_seconds', 'duration_seconds', 'speed'))
    if f32_field:
        require(type(actual) is float and type(expected) is float and math.isfinite(actual) and math.isfinite(expected), 'complete Work finite f32 field '+str(path))
        require(bits(actual) == bits(expected), 'complete Work binary32 field '+str(path))
    else:
        require(type(actual) is type(expected), 'complete Work typed field '+str(path))
        if type(expected) is dict:
            require(actual.keys() == expected.keys(), 'complete Work unknown/missing fields '+str(path))
            for key in expected:
                same_work(actual[key], expected[key], path+(key,))
        elif type(expected) is list:
            require(len(actual) == len(expected), 'complete Work list length '+str(path))
            for index, (a, e) in enumerate(zip(actual, expected)):
                same_work(a, e, path+(index,))
        else:
            require(actual == expected, 'complete Work identity/revision/content '+str(path))


def compare(raw, asset=None, skin_vertices=True):
    asset = asset or Asset()
    require(type(raw.get('schema_version')) is int and raw['schema_version'] == 1, 'capture schema version')
    require(raw.get('platform') in ('native', 'web'), 'native/Web platform')
    require(raw.get('schedule') == SCHEDULE, 'post-animation post-propagation schedule')
    require(raw.get('status') == 'complete' and raw.get('error') is None, 'capture completed without error')
    samples = raw.get('samples')
    require(isinstance(samples, list) and all(type(s.get('source_key_index')) is int for s in samples) and [s.get('source_key_index') for s in samples] == KEYS, 'exact seven keys in order')
    require(digest(WORK_PATH) == WORK_SHA, 'pinned experiment48 Work bytes')
    work = strict_loads(WORK_PATH.read_text())
    require(work['profile']['asset_sha256'] == digest(asset.path), 'expected Work asset identity')
    require(work['character']['scale'] == 1 and all(v == 0 for v in work['character']['parameters'].values()), 'expected zero morphs, unit root')
    maxima = {key: 0. for key in TOL}
    frames = []
    points_compared = 0
    sample_reports = []
    def check(kind, got, expected, label, quaternion=False):
        err = quaternion_error(got, expected) if quaternion else max_error(got, expected)
        maxima[kind] = max(maxima[kind], err)
        require(err <= TOL[kind], '%s: %s error %.12g > %.12g' % (label, kind, err, TOL[kind]))
    expected_bindings = {(owner, primitive) for owner, n in enumerate(asset.nodes) if 'skin' in n
                         for primitive in range(len(asset.doc['meshes'][n['mesh']]['primitives']))}
    expected_skin_count = len(expected_bindings)
    for sample in samples:
        key = sample['source_key_index']
        label = 'key %d' % key
        time = asset.times[key]
        require(sample.get('requested_clip') == CLIP, label+' requested clip')
        require(type(sample.get('requested_time')) is float and sample['requested_time'] == time and type(sample.get('requested_time_bits')) is int and sample['requested_time_bits'] == bits(time), label+' exact requested time')
        same_work(sample.get('work'), work)
        frame = sample.get('frame')
        require(type(frame) is int and frame > 0 and (not frames or frame > frames[-1]), label+' increasing frame')
        frames.append(frame)
        require(type(sample.get('settled_frames')) is int and sample['settled_frames'] >= 2, label+' settled propagation passes')
        playback = sample.get('playback', {})
        require(playback.get('clip_id') == CLIP and type(playback.get('position_seconds')) is float and playback['position_seconds'] == time and type(playback.get('position_bits')) is int and playback['position_bits'] == bits(time), label+' actual playback clip/time')
        require(playback.get('playing') is False and playback.get('seek_pending') is False and playback.get('error') is None, label+' paused applied seek')
        require(playback.get('active_timeline_id') == work['timeline'][0]['id'], label+' active timeline')
        players = sample.get('players')
        require(isinstance(players, list) and len(players) == 1 and players[0].get('graph_asset') is not None, label+' one bound animation player')
        animations = players[0].get('animations')
        require(isinstance(animations, list) and len(animations) == 1, label+' one active animation')
        animation = animations[0]
        require(animation.get('clip_name') == CLIP and type(animation.get('gltf_animation_index')) is int and animation['gltf_animation_index'] == asset.clip_index and animation.get('clip_asset') is not None, label+' actual loaded clip identity')
        require(type(animation.get('seek_time')) is float and animation['seek_time'] == time and type(animation.get('seek_time_bits')) is int and animation['seek_time_bits'] == bits(time) and animation.get('paused') is True and type(animation.get('weight')) is float and animation['weight'] == 1., label+' player exact paused time/weight')
        nodes = sample.get('nodes')
        require(isinstance(nodes, list), label+' node records')
        entities = {}
        mapped = {}
        for node in nodes:
            entity = node.get('entity')
            require(entity is not None and entity not in entities, label+' unique entity')
            entities[entity] = node
            for field, width in [('translation', 3), ('rotation', 4), ('scale', 3), ('global', 16)]:
                finite_vector(node.get(field), width, label+' '+field)
            index = node.get('gltf_node_index')
            if index is not None:
                require(type(index) is int and index in asset.active and index not in mapped, label+' unique valid GLB node')
                require(node.get('name') == asset.nodes[index].get('name'), label+' exact GLB node name')
                mapped[index] = node
        require(set(mapped) == asset.active, label+' all GLB nodes including bones/meshes/ancestors')
        host_id = sample.get('character_root')
        require(host_id in entities, label+' CharacterRoot present')
        host = entities[host_id]
        require(host.get('gltf_node_index') is None and host.get('parent') is None, label+' CharacterRoot ancestry')
        # Work scale 1 + production root Transform::default gives identity.
        # Expected does NOT adopt the observed host transform; root bugs fail.
        for node in nodes:
            if node.get('gltf_node_index') is None:
                check('local_translation_m', node['translation'], [0., 0., 0.], label+' helper/root translation')
                check('local_rotation_component', node['rotation'], [0., 0., 0., 1.], label+' helper/root rotation', True)
                check('local_scale', node['scale'], [1., 1., 1.], label+' helper/root scale')
        check('global_matrix_component', host['global'], column_major(identity()), label+' CharacterRoot global')
        for node in nodes:
            if node['entity'] != host_id:
                require(node.get('parent') in entities, label+' every actual parent transform present')
                parent = entities[node['parent']]
                propagated = multiply(from_column_major(parent['global']), trs(node['translation'], node['rotation'], node['scale']))
                check('global_matrix_component', node['global'], column_major(propagated), label+' actual parent propagation consistency')
        expected_local, expected_global = asset.pose(key)
        actual_global = {}
        def glb_parent(node):
            parent = node.get('parent')
            seen = {node['entity']}
            while parent != host_id:
                require(parent in entities and parent not in seen, label+' complete acyclic ancestry to CharacterRoot')
                seen.add(parent)
                ancestor = entities[parent]
                if ancestor.get('gltf_node_index') is not None:
                    return ancestor['gltf_node_index']
                parent = ancestor.get('parent')
            return None
        for index, node in mapped.items():
            require(glb_parent(node) == asset.parents[index], label+' exact serialized parent node %d' % index)
            for field, kind in [('translation', 'local_translation_m'), ('rotation', 'local_rotation_component'), ('scale', 'local_scale')]:
                check(kind, node[field], expected_local[index][field], label+' node %d' % index, field == 'rotation')
            check('global_matrix_component', node['global'], column_major(expected_global[index]), label+' node %d full matrix' % index)
            actual_global[index] = from_column_major(node['global'])
        skins = sample.get('skins')
        require(isinstance(skins, list) and len(skins) == expected_skin_count, label+' all mesh primitive skins')
        seen_bindings = set()
        seen_skin_entities = set()
        mesh_assets = {}
        inverse_bind_assets = {}
        for skin in skins:
            entity = skin.get('entity')
            require(type(entity) is str and entity in entities, label+' skin entity transform')
            require(entity not in seen_skin_entities, label+' unique actual skin component entity')
            seen_skin_entities.add(entity)
            mesh = skin.get('gltf_mesh_index')
            primitive = skin.get('gltf_primitive_index')
            skin_index = skin.get('gltf_skin_index')
            require(all(type(v) is int for v in (mesh, primitive, skin_index)), label+' resolved mesh/primitive/skin')
            owners = [i for i, n in enumerate(asset.nodes) if n.get('mesh') == mesh and n.get('skin') == skin_index]
            require(len(owners) == 1, label+' unique serialized mesh owner')
            owner = owners[0]
            require(0 <= primitive < len(asset.doc['meshes'][mesh]['primitives']), label+' valid primitive')
            binding = (owner, primitive)
            require(binding not in seen_bindings, label+' unique primitive binding')
            seen_bindings.add(binding)
            require(glb_parent(entities[entity]) == owner or entities[entity].get('gltf_node_index') == owner, label+' primitive mesh ancestry')
            mesh_asset = skin.get('mesh_asset')
            inverse_bind_asset = skin.get('inverse_bind_asset')
            require(type(mesh_asset) is str and bool(mesh_asset) and type(inverse_bind_asset) is str and bool(inverse_bind_asset), label+' mesh/inverse-bind asset identities')
            primitive_identity = (mesh, primitive)
            require(mesh_asset not in mesh_assets or mesh_assets[mesh_asset] == primitive_identity, label+' mesh handle resolves to one actual GLB primitive')
            require(primitive_identity not in mesh_assets.values(), label+' one actual mesh handle per GLB primitive')
            mesh_assets[mesh_asset] = primitive_identity
            require(inverse_bind_asset not in inverse_bind_assets or inverse_bind_assets[inverse_bind_asset] == skin_index, label+' inverse-bind handle resolves to one actual GLB skin')
            require(not inverse_bind_assets or inverse_bind_assets.get(inverse_bind_asset) == skin_index, label+' one actual inverse-bind handle for fixture skin')
            inverse_bind_assets[inverse_bind_asset] = skin_index
            serialized = asset.doc['skins'][skin_index]
            joint_nodes = serialized['joints']
            require(skin.get('joints') == [mapped[i]['entity'] for i in joint_nodes], label+' actual ordered joint bindings')
            expected_ibm = asset.accessor(serialized['inverseBindMatrices'])
            actual_ibm = skin.get('inverse_bind_matrices')
            require(isinstance(actual_ibm, list) and len(actual_ibm) == len(expected_ibm), label+' all inverse binds')
            for i, matrix in enumerate(actual_ibm):
                check('inverse_bind_component', matrix, expected_ibm[i], label+' inverse bind %d' % i)
            check('global_matrix_component', entities[entity]['global'], column_major(expected_global[owner]), label+' actual mesh primitive global')
            if skin_vertices:
                prim = asset.doc['meshes'][mesh]['primitives'][primitive]
                attrs = prim['attributes']
                positions = asset.accessor(attrs['POSITION'])
                slots = asset.accessor(attrs['JOINTS_0'])
                weights = asset.accessor(attrs['WEIGHTS_0'])
                expected_points = asset.skin_vertices(key, owner, primitive)
                # Source GLB vertex inputs + ACTUAL captured joints/inverse binds.
                # This is CPU reconstruction, not GPU vertex-output readback.
                actual_matrices = [multiply(from_column_major(entities[j]['global']), from_column_major(m)) for j, m in zip(skin['joints'], actual_ibm)]
                for p, js, ws, expected in zip(positions, slots, weights, expected_points):
                    actual = [0., 0., 0.]
                    for slot, weight in zip(js, ws):
                        if weight:
                            moved = transform(actual_matrices[slot], p)
                            for axis in range(3):
                                actual[axis] += weight*moved[axis]
                    check('skinned_vertex_m', actual, expected, label+' CPU skin reconstruction')
                points_compared += len(positions)
        require(seen_bindings == expected_bindings and len(seen_skin_entities) == expected_skin_count, label+' all nine actual skin component instances and primitive bindings represented')
        sample_reports.append({'key_index': key, 'time_seconds': time, 'frame': frame, 'glb_nodes': len(mapped), 'primitive_skins': len(skins)})
    return {'status': 'PASS', 'platform': raw['platform'], 'glb_sha256': digest(asset.path),
            'work_sha256': digest(WORK_PATH), 'thresholds': TOL, 'max_errors': maxima,
            'samples': sample_reports, 'cpu_reconstructed_vertices_compared': points_compared,
            'expectation_space': 'serialized scene under independently expected identity CharacterRoot; no observed-root fitting',
            'not_run': ['GPU deformed vertex readback', 'anatomical/semantic quality', 'official decoder parity']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('capture', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = compare(strict_loads(args.capture.read_text()))
    except (Rejected, KeyError, TypeError, IndexError, ValueError) as error:
        result = {'status': 'FAIL', 'reason': str(error)}
    result['capture_sha256'] = digest(args.capture)
    data = json.dumps(result, indent=2, allow_nan=False)+'\n'
    if args.output:
        args.output.write_text(data)
    else:
        print(data, end='')
    raise SystemExit(0 if result['status'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
