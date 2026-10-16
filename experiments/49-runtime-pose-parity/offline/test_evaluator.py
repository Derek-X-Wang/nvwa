"""Executable controls; synthetic captures test the comparator, not Bevy."""
import copy
import json
import math
from pathlib import Path
import unittest

from evaluator import (Asset, CLIP, KEYS, WORK_PATH, Rejected, column_major,
                       f32, identity, max_error, multiply, trs)
from compare import SCHEDULE, bits, compare
from surface import crossing, segment_triangle


def synthetic_capture(asset):
    work = json.loads(WORK_PATH.read_text())
    result = {'schema_version': 1, 'platform': 'native', 'schedule': SCHEDULE,
              'status': 'complete', 'error': None, 'samples': []}
    for sample_index, key in enumerate(KEYS):
        local, glob = asset.pose(key)
        nodes = [{'entity': 'host', 'parent': None, 'name': None, 'gltf_node_index': None,
                  'translation': [0., 0., 0.], 'rotation': [0., 0., 0., 1.], 'scale': [1., 1., 1.], 'global': column_major(identity())}]
        for i in sorted(asset.active):
            nodes.append({'entity': 'node%d' % i,
                          'parent': 'host' if asset.parents[i] is None else 'node%d' % asset.parents[i],
                          'name': asset.nodes[i]['name'], 'gltf_node_index': i,
                          **local[i], 'global': column_major(glob[i])})
        skins = []
        for owner, node in enumerate(asset.nodes):
            if 'skin' not in node:
                continue
            skin = asset.doc['skins'][node['skin']]
            for primitive in range(len(asset.doc['meshes'][node['mesh']]['primitives'])):
                entity = 'primitive%d_%d' % (owner, primitive)
                nodes.append({'entity': entity, 'parent': 'node%d' % owner, 'name': None, 'gltf_node_index': None,
                              'translation': [0., 0., 0.], 'rotation': [0., 0., 0., 1.], 'scale': [1., 1., 1.], 'global': column_major(glob[owner])})
                skins.append({'entity': entity, 'mesh_asset': 'synthetic_mesh%d_%d' % (node['mesh'], primitive), 'gltf_mesh_index': node['mesh'],
                              'gltf_primitive_index': primitive, 'gltf_skin_index': node['skin'],
                              'inverse_bind_asset': 'synthetic_inverse_bind',
                              'inverse_bind_matrices': asset.accessor(skin['inverseBindMatrices']),
                              'joints': ['node%d' % i for i in skin['joints']]})
        time = asset.times[key]
        result['samples'].append({'source_key_index': key, 'requested_clip': CLIP,
                                  'requested_time': time, 'requested_time_bits': bits(time),
                                  'frame': sample_index*4+4, 'settled_frames': 2, 'work': copy.deepcopy(work),
                                  'playback': {'clip_id': CLIP, 'position_seconds': time, 'position_bits': bits(time),
                                               'playing': False, 'active_timeline_id': work['timeline'][0]['id'], 'seek_pending': False, 'error': None},
                                  'players': [{'entity': 'player', 'graph_asset': 'synthetic_graph', 'animations': [
                                      {'node_index': 0, 'clip_asset': 'synthetic_clip', 'gltf_animation_index': asset.clip_index,
                                       'clip_name': CLIP, 'seek_time': time, 'seek_time_bits': bits(time), 'paused': True, 'weight': 1.}]}],
                                  'character_root': 'host', 'nodes': nodes, 'skins': skins})
    return result


class EvaluatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.asset = Asset()
        cls.baseline = synthetic_capture(cls.asset)

    def altered(self):
        return copy.deepcopy(self.baseline)

    def reject(self, raw, message):
        with self.assertRaisesRegex(Rejected, message):
            compare(raw, self.asset, skin_vertices=False)

    def test_serialized_expected_90_keys(self):
        self.assertEqual(self.asset.clip_index, 3)
        self.assertEqual(len(self.asset.channels), 19)
        for key in range(90):
            local, glob = self.asset.pose(key)
            self.assertEqual(len(local), 24)
            for index in local:
                parent = self.asset.parents[index]
                expected = multiply(identity() if parent is None else glob[parent], trs(**local[index]))
                self.assertEqual(expected, glob[index])
            self.assertEqual(self.asset.times[key], f32(key/30))
        self.assertEqual(self.asset.times[89], 2.9666666984558105)

    def test_matrix_convention_nonidentity_ancestor(self):
        root = trs([1., 2., 3.], [0., 0., math.sqrt(.5), math.sqrt(.5)], [2., 3., 4.])
        _, base = self.asset.pose(30)
        _, moved = self.asset.pose(30, root)
        for i in base:
            self.assertLess(max_error(column_major(moved[i]), column_major(multiply(root, base[i]))), 2e-14)

    def test_synthetic_baseline_cpu_skin_reconstruction(self):
        report = compare(self.baseline, self.asset)
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(report['cpu_reconstructed_vertices_compared'], 173152)
        self.assertEqual(max(report['max_errors'].values()), 0.)

    def test_quaternion_sign_equivalence(self):
        raw = self.altered()
        for sample in raw['samples']:
            for node in sample['nodes']:
                node['rotation'] = [-x for x in node['rotation']]
        self.assertEqual(compare(raw, self.asset, skin_vertices=False)['status'], 'PASS')

    def test_wrong_time(self):
        raw = self.altered()
        raw['samples'][1]['players'][0]['animations'][0]['seek_time'] = self.asset.times[16]
        self.reject(raw, 'player exact paused time')

    def test_nominal_three_seconds_is_wrong(self):
        raw = self.altered()
        raw['samples'][-1]['requested_time'] = 3.
        self.reject(raw, 'exact requested time')

    def test_wrong_clip(self):
        raw = self.altered()
        raw['samples'][1]['players'][0]['animations'][0]['clip_name'] = 'idle'
        self.reject(raw, 'actual loaded clip identity')

    def test_missing_bone(self):
        raw = self.altered()
        raw['samples'][0]['nodes'] = [n for n in raw['samples'][0]['nodes'] if n['gltf_node_index'] != 4]
        self.reject(raw, 'all GLB nodes')

    def test_wrong_pose_with_correct_time_metadata(self):
        raw = self.altered()
        first = {n['gltf_node_index']: n for n in raw['samples'][0]['nodes'] if n['gltf_node_index'] is not None}
        for node in raw['samples'][1]['nodes']:
            if node['gltf_node_index'] is not None:
                other = first[node['gltf_node_index']]
                for field in ('rotation', 'translation', 'scale', 'global'):
                    node[field] = list(other[field])
        self.reject(raw, 'local_rotation_component|local_translation_m|global_matrix_component')

    def test_root_double_application(self):
        raw = self.altered()
        sample = raw['samples'][1]
        _, glob = self.asset.pose(KEYS[1])
        root = glob[17]
        for node in sample['nodes']:
            if node['gltf_node_index'] is not None:
                i = node['gltf_node_index']
                node['global'] = column_major(multiply(root, glob[i]))
        self.reject(raw, 'global_matrix_component')

    def test_root_scale_not_fitted(self):
        raw = self.altered()
        raw['samples'][0]['nodes'][0]['scale'] = [2., 2., 2.]
        self.reject(raw, 'helper/root scale')

    def test_perturbed_bone(self):
        raw = self.altered()
        next(n for n in raw['samples'][0]['nodes'] if n['gltf_node_index'] == 3)['rotation'][0] += .01
        self.reject(raw, 'local_rotation_component|unit glTF quaternion')

    def test_perturbed_global_only(self):
        raw = self.altered()
        next(n for n in raw['samples'][0]['nodes'] if n['gltf_node_index'] == 3)['global'][12] += .01
        self.reject(raw, 'global_matrix_component')

    def test_nonfinite_rejected(self):
        raw = self.altered()
        raw['samples'][0]['nodes'][0]['global'][0] = float('nan')
        self.reject(raw, 'global')

    def test_wrong_work_revision(self):
        raw = self.altered()
        raw['samples'][0]['work']['revision'] = 1
        self.reject(raw, 'complete Work')

    def test_work_f32_serde_decimal_spelling(self):
        raw = self.altered()
        for sample in raw['samples']:
            sample['work']['timeline'][0]['duration_seconds'] = 2.9666667
            sample['work']['profile']['clips'][3]['duration_seconds'] = 2.9666667
        self.assertEqual(compare(raw, self.asset, skin_vertices=False)['status'], 'PASS')

    def test_work_f32_different_value_rejected(self):
        raw = self.altered()
        raw['samples'][0]['work']['character']['scale'] = 1.000001
        self.reject(raw, 'Work binary32 field')

    def test_work_boolean_integer_coercion_rejected(self):
        for path in ('schema_version', 'revision'):
            raw = self.altered()
            raw['samples'][0]['work'][path] = bool(raw['samples'][0]['work'][path])
            self.reject(raw, 'Work typed field')

    def test_work_float_integer_coercion_rejected(self):
        raw = self.altered()
        raw['samples'][0]['work']['character']['scale'] = 1
        self.reject(raw, 'Work finite f32 field')

    def test_work_unknown_field_rejected(self):
        raw = self.altered()
        raw['samples'][0]['work']['timeline'][0]['unknown'] = None
        self.reject(raw, 'Work unknown/missing fields')

    def test_capture_boolean_integer_coercion_rejected(self):
        raw = self.altered()
        raw['schema_version'] = True
        self.reject(raw, 'capture schema version')
        raw = self.altered()
        raw['samples'][0]['source_key_index'] = False
        self.reject(raw, 'exact seven keys')

    def test_wrong_skin_joint_order(self):
        raw = self.altered()
        joints = raw['samples'][0]['skins'][0]['joints']
        joints[0], joints[1] = joints[1], joints[0]
        self.reject(raw, 'ordered joint bindings')

    def test_perturbed_inverse_bind(self):
        raw = self.altered()
        raw['samples'][0]['skins'][0]['inverse_bind_matrices'][0][12] += .01
        self.reject(raw, 'inverse_bind_component')

    def test_wrong_ancestor(self):
        raw = self.altered()
        next(n for n in raw['samples'][0]['nodes'] if n['gltf_node_index'] == 3)['parent'] = 'node8'
        self.reject(raw, 'exact serialized parent|actual parent propagation consistency')

    def test_missing_skin(self):
        raw = self.altered()
        raw['samples'][0]['skins'].pop()
        self.reject(raw, 'all mesh primitive skins')

    def test_missing_primitive_instances_aliased_skin_records(self):
        raw = self.altered()
        missing = {'primitive22_1', 'primitive22_2', 'primitive22_3', 'primitive22_4'}
        for sample in raw['samples']:
            sample['nodes'] = [node for node in sample['nodes'] if node['entity'] not in missing]
            for skin in sample['skins']:
                if skin['gltf_mesh_index'] == 4:
                    skin['entity'] = 'primitive22_0'
        self.reject(raw, 'unique actual skin component entity')

    def test_duplicate_skin_entity_without_missing_transform(self):
        raw = self.altered()
        skins = raw['samples'][0]['skins']
        skins[-1]['entity'] = skins[-2]['entity']
        self.reject(raw, 'unique actual skin component entity')

    def test_mesh_handle_cannot_relabel_different_primitives(self):
        raw = self.altered()
        skins = raw['samples'][0]['skins']
        skins[-1]['mesh_asset'] = skins[-2]['mesh_asset']
        self.reject(raw, 'mesh handle resolves to one actual GLB primitive')

    def test_fixture_inverse_bind_asset_identity_consistency(self):
        raw = self.altered()
        raw['samples'][0]['skins'][-1]['inverse_bind_asset'] = 'synthetic_second_inverse_bind'
        self.reject(raw, 'one actual inverse-bind handle for fixture skin')

    def test_skin_inverse_bind_rest_reconstruction(self):
        static = {}
        def world(i):
            if i not in static:
                n = self.asset.nodes[i]
                parent = self.asset.parents[i]
                local = trs(n.get('translation', [0., 0., 0.]), n.get('rotation', [0., 0., 0., 1.]), n.get('scale', [1., 1., 1.]))
                static[i] = multiply(identity() if parent is None else world(parent), local)
            return static[i]
        for i in self.asset.active:
            world(i)
        error = 0.
        for owner, node in enumerate(self.asset.nodes):
            if 'skin' not in node:
                continue
            for primitive, mesh in enumerate(self.asset.doc['meshes'][node['mesh']]['primitives']):
                original = self.asset.accessor(mesh['attributes']['POSITION'])
                reconstructed = self.asset.skin_vertices(0, owner, primitive, globals_override=static)
                for actual, expected in zip(reconstructed, original):
                    error = max(error, max_error(actual, expected))
        self.assertLess(error, 1e-6)

    def test_surface_strict_crossing_known_geometry(self):
        flat = [[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]]
        through = [[.2, .2, -1.], [.2, .2, 1.], [.7, .2, 1.]]
        point = crossing(flat, through)
        self.assertIsNotNone(point)
        self.assertAlmostEqual(point[2], 0.)
        self.assertIsNotNone(crossing(list(reversed(through)), flat))
        self.assertIsNone(crossing(flat, [[2., 2., -1.], [2., 2., 1.], [3., 2., 1.]]))
        self.assertIsNone(crossing(flat, [[.1, .1, 0.], [.2, .1, 0.], [.1, .2, 0.]]))
        # Contact at endpoint or triangle boundary is deliberately excluded.
        self.assertIsNone(segment_triangle([.2, .2, 0.], [.2, .2, 1.], flat))
        self.assertIsNone(segment_triangle([0., 0., -1.], [0., 0., 1.], flat))


if __name__ == '__main__':
    unittest.main(verbosity=2)
