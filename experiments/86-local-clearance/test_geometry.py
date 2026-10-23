"""Analytical failure controls for independent diagnostics; no quality claim."""
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import audit
import geometry as g


TRI = [[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]]


class BoundedGeometry(unittest.TestCase):
    def test_interior_analytic(self):
        hit = g.face_query([.25, .25, .003], TRI)
        self.assertEqual(hit['point'], [.25, .25, 0.])
        self.assertEqual(hit['barycentric'], [.5, .25, .25])
        self.assertAlmostEqual(hit['bounded_distance_m'], .003)

    def test_distant_plane_is_not_penetration(self):
        hit = g.face_query([.5, -73., -.008], TRI)
        self.assertAlmostEqual(hit['supporting_plane_projection_m'], -.008)
        self.assertGreater(hit['bounded_distance_m'], 73.)
        self.assertEqual(hit['point'], [.5, 0., 0.])

    def test_edge_analytic(self):
        q, bary, d2 = g.closest([.5, -.3, .4], TRI)
        self.assertEqual(q, [.5, 0., 0.])
        self.assertEqual(bary, [.5, .5, 0.])
        self.assertAlmostEqual(d2, .25)

    def test_vertex_analytic(self):
        q, bary, d2 = g.closest([-1., -2., -2.], TRI)
        self.assertEqual(q, [0., 0., 0.])
        self.assertEqual(bary, [1., 0., 0.])
        self.assertEqual(d2, 9.)

    def test_opposite_edge_analytic(self):
        q, bary, d2 = g.closest([1., 1., 0.], TRI)
        self.assertEqual(q, [.5, .5, 0.])
        self.assertEqual(bary, [0., .5, .5])
        self.assertEqual(d2, .5)

    def test_winding_changes_projection_not_distance(self):
        a = g.face_query([.25, .25, -.002], TRI)
        b = g.face_query([.25, .25, -.002], list(reversed(TRI)))
        self.assertEqual(a['bounded_distance_m'], b['bounded_distance_m'])
        self.assertAlmostEqual(a['supporting_plane_projection_m'], -b['supporting_plane_projection_m'])

    def test_rigid_translation(self):
        point = [.25, .25, .003]
        shift = [5., -8., 3.]
        translated = [[x+y for x, y in zip(v, shift)] for v in TRI]
        moved = [x+y for x, y in zip(point, shift)]
        self.assertAlmostEqual(g.face_query(point, TRI)['bounded_distance_m'],
                               g.face_query(moved, translated)['bounded_distance_m'])

    def test_refuse_degenerate_not_silent_skip(self):
        with self.assertRaisesRegex(ValueError, 'degenerate'):
            g.closest([0., 0., 1.], [[0., 0., 0.]]*3)

    def test_refuse_nonfinite(self):
        for value in (math.inf, -math.inf, math.nan, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                g.closest([value, 0., 0.], TRI)

    def test_all_equal_nearest_faces_retained(self):
        vertices = TRI+[[0., 0., 2.], [1., 0., 2.], [0., 1., 2.]]
        triangles = [{'sources': [0, 1, 2]}, {'sources': [3, 4, 5]}]
        hits = g.nearest([.25, .25, 1.], vertices, triangles)
        self.assertEqual([hit['triangle0'] for hit in hits], [0, 1])

    def test_later_closer_face_drops_old_nontie(self):
        vertices = TRI+[[0., 0., 2.], [1., 0., 2.], [0., 1., 2.]]
        hits = g.nearest([.25, .25, 1.5], vertices,
                         [{'sources': [0, 1, 2]}, {'sources': [3, 4, 5]}])
        self.assertEqual([hit['triangle0'] for hit in hits], [1])

    def test_edge_and_vertex_identity(self):
        self.assertEqual(g.feature({'sources': [8, 4, 3], 'barycentric': [0., .2, .8]}),
                         {'kind': 'edge', 'sources': [3, 4]})
        self.assertEqual(g.feature({'sources': [8, 4, 3], 'barycentric': [0., 0., 1.]})['kind'], 'vertex')

    def test_real_segment_crossing_despite_clear_endpoints(self):
        p, q = [.25, .25, .01], [.25, .25, -.01]
        self.assertGreater(g.face_query(p, TRI)['bounded_distance_m'], .001)
        self.assertGreater(g.face_query(q, TRI)['bounded_distance_m'], .001)
        self.assertTrue(g.proper_segment_crossing(p, q, TRI))

    def test_distant_plane_crossing_is_not_triangle_crossing(self):
        self.assertFalse(g.proper_segment_crossing([3., 3., .01], [3., 3., -.01], TRI))

    def test_tangent_and_edge_touch_not_proper_crossing(self):
        self.assertFalse(g.proper_segment_crossing([.25, .25, 0.], [.25, .25, 1.], TRI))
        self.assertFalse(g.proper_segment_crossing([.5, 0., 1.], [.5, 0., -1.], TRI))

    def test_bounded_distance_control_detects_unbounded_plane_mutant(self):
        # Call the production-called diagnostic seam with a deliberately wrong
        # closest-point implementation. The analytical bounded-distance control
        # must go red; no test catches its own raised exception as success.
        with patch.object(g, 'closest', return_value=([.5, -73., 0.], [.5, .5, 0.], .008**2)):
            with self.assertRaises(AssertionError):
                self.test_distant_plane_is_not_penetration()

    def test_crossing_control_detects_disabled_predicate(self):
        with patch.object(g, 'proper_segment_crossing', return_value=False):
            with self.assertRaises(AssertionError):
                self.test_real_segment_crossing_despite_clear_endpoints()


class SourceAndTopology(unittest.TestCase):
    def test_signed_transfer_filters_after_aggregate(self):
        row = {'helpers': [0, 1, 2], 'weights': [-1., 1., 1.]}
        weights = {'positive': {0: .5, 1: .25, 2: .5}, 'nonpositive': {0: 1., 1: .1}}
        self.assertEqual(audit.positive_aggregates(row, ['positive', 'nonpositive'], weights), [[0, .25]])

    def test_complete_weight_rows_do_not_truncate_or_normalize(self):
        row = {'helpers': [0], 'weights': [1.]}
        names = ['a', 'b', 'c', 'd', 'e']
        weights = {name: {0: .25} for name in names}
        self.assertEqual(audit.positive_aggregates(row, names, weights), [[i, .25] for i in range(5)])

    def test_mapping_keeps_signed_coefficients_and_f32_order(self):
        text = 'x_scale 0 1 1\ny_scale 0 1 1\nz_scale 0 1 1\nverts 0\n0 1 2 -1 1 1 0 0 0\ndelete_verts\n0 - 1 4\n'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'map.mhclo'
            path.write_text(text)
            axes, rows, deleted = audit.read_mapping(path)
        self.assertEqual(rows[0]['weights'], [-1., 1., 1.])
        fitted, scales = audit.fit([[1., 1., 1.], [2., 2., 2.], [4., 4., 4.]], axes, rows)
        self.assertEqual(fitted, [[5., 5., 5.]])
        self.assertEqual(scales, [1., 1., 1.])
        self.assertEqual(deleted, {0, 1, 4})

    def test_only_all_deleted_polygon_is_removed(self):
        faces = [[0, 1, 2, 3], [2, 3, 4, 5], [0, 1, 13380, 13381]]
        full, shown, ownership = audit.surfaces(faces, {0, 1, 2, 3}, ['body', 'body', 'helper'])
        self.assertEqual(len(full), 4)
        self.assertEqual(len(shown), 2)
        self.assertEqual([(r['obj_face0'], r['fan_triangle0']) for r in shown], [(1, 0), (1, 1)])
        self.assertTrue(ownership[2]['helper_excluded'])

    def test_mask_boundary_ownership_is_local(self):
        faces = [[0, 1, 2], [1, 0, 3]]
        full, shown, ownership = audit.surfaces(faces, {0, 1, 3})
        edges, vertices, info = audit.topology(shown)
        hit = {'triangle0': 0, 'sources': [0, 1, 2], 'barycentric': [.5, .5, 0.]}
        classified = audit.classify(hit, edges, vertices, ownership)
        self.assertTrue(classified['is_mask_boundary_feature'])
        hit['barycentric'] = [0., .5, .5]
        self.assertFalse(audit.classify(hit, edges, vertices, ownership)['is_mask_boundary_feature'])

    def test_open_surface_cannot_claim_closed(self):
        _, _, info = audit.topology([{'sources': [0, 1, 2]}])
        self.assertFalse(info['closed_two_manifold_edge_test'])
        self.assertEqual(info['edges_by_incidence'], {1: 3})

    def test_opposite_winding_closed_tetrahedron(self):
        tris = [{'sources': sources} for sources in ([0, 2, 1], [0, 1, 3], [1, 2, 3], [2, 0, 3])]
        self.assertTrue(audit.topology(tris)[2]['closed_two_manifold_edge_test'])
        tris[0]['sources'] = list(reversed(tris[0]['sources']))
        self.assertFalse(audit.topology(tris)[2]['closed_two_manifold_edge_test'])

    def test_input_mutation_refuses(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'input.json'
            path.write_text('original')
            expected = audit.identity(path)
            path.write_text('modified')
            with self.assertRaisesRegex(ValueError, 'identity differs'):
                audit.pinned(path, expected)


if __name__ == '__main__':
    unittest.main()
