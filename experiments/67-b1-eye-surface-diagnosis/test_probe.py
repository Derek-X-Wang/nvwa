"""Analytic controls and adverse inputs; tests also execute under python -O."""
import copy
import math
import unittest
from unittest.mock import patch

import probe


class GeometryControls(unittest.TestCase):
    def triangle(self, z=2, reverse=False):
        vertices = [[-1, -1, z], [0, 1, z], [1, -1, z]]
        return probe.indexed_mesh(vertices, [0, 2, 1] if reverse else [0, 1, 2], [{}])[0]

    def test_hand_calculated_interior(self):
        # At z=2, (0,0) = .25*(-1,-1)+.5*(0,1)+.25*(1,-1).
        h = probe.intersect((0, 0, 0), (0, 0, 1), self.triangle())
        self.assertEqual(h["ray_distance_m"], 2)
        self.assertEqual(h["barycentric"], [.25, .5, .25])
        self.assertEqual(h["world_point_m"], [0, 0, 2])
        self.assertFalse(h["boundary"])
        self.assertTrue(h["winding_normal_toward_camera"])

    def test_winding_changes_only_front_subset(self):
        a = probe.intersect((0, 0, 0), (0, 0, 1), self.triangle())
        b = probe.intersect((0, 0, 0), (0, 0, 1), self.triangle(reverse=True))
        self.assertEqual(a["ray_distance_m"], b["ray_distance_m"])
        self.assertFalse(b["winding_normal_toward_camera"])
        self.assertIsNotNone(probe.nearest([b]))
        self.assertIsNone(probe.nearest([b], front_only=True))

    def test_hand_calculated_boundary(self):
        h = probe.intersect((0, -1, 0), (0, 0, 1), self.triangle())
        self.assertEqual(h["barycentric"], [.5, 0, .5])
        self.assertTrue(h["boundary"])

    def test_outside_parallel_coplanar_and_behind(self):
        t = self.triangle()
        self.assertIsNone(probe.intersect((2, 0, 0), (0, 0, 1), t))
        self.assertIsNone(probe.intersect((0, 0, 0), (1, 0, 0), t))
        self.assertIsNone(probe.intersect((0, 0, 2), (1, 0, 0), t))
        self.assertIsNone(probe.intersect((0, 0, 3), (0, 0, 1), t))

    def test_degenerate_and_tiny_triangles_rejected(self):
        for points in ([[0, 0, 0], [1, 0, 0], [2, 0, 0]],
                       [[0, 0, 0], [1e-8, 0, 0], [0, 1e-8, 0]]):
            with self.assertRaisesRegex(ValueError, "degenerate"):
                probe.indexed_mesh(points, [0, 1, 2], [{}])

    def test_invalid_vectors_indices_and_label_coverage(self):
        for points, indices, labels in (([[math.nan, 0, 0]], [], []),
            ([[0, 0, 0]], [0, 0, 4], [{}]), ([[0, 0, 0]], [0], []),
            ([[0, 0, 0]], [0, 0, 0], [])):
            with self.assertRaises(ValueError):
                probe.indexed_mesh(points, indices, labels)
        with self.assertRaises(ValueError):
            probe.unit((0, 0, 0))
        with self.assertRaises(ValueError):
            probe.vec((True, 0, 0))

    def test_column_major_affine_hand_calculation(self):
        # Scale (2,3,4), rotate +90 degrees about Z, translate (5,6,7).
        m = probe.matrix([0, 2, 0, 0, -3, 0, 0, 0, 0, 0, 4, 0, 5, 6, 7, 1])
        self.assertEqual(probe.point(m, (1, 2, 3)), (-1, 8, 19))
        self.assertEqual(probe.inverse_point(m, (-1, 8, 19)), (1, 2, 3))
        # A second application is explicitly a different point: catches a
        # model-to-world/display-transform duplication in this control.
        self.assertNotEqual(probe.point(m, probe.point(m, (1, 2, 3))), (-1, 8, 19))

    def test_bad_matrix_and_camera_axis_control(self):
        identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
        for bad in ([0]*16, identity[:15], [math.inf]+identity[1:],
                    identity[:3]+[.2]+identity[4:]):
            with self.assertRaises(ValueError):
                probe.matrix(bad)
        camera = identity[:12]+[0, 0, 3, 1]
        self.assertEqual(probe.inverse_point(camera, (0, 0, 1)), (0, 0, -2))
        self.assertEqual(probe.unit(probe.sub((0, 0, 1), camera[12:15])), (0, 0, -1))

    def test_ordering_and_contact_band_controls(self):
        eye = {"ray_distance_m": 2}
        for distance, expected in ((1, "body_first"), (3, "eye_first"),
                                   (2, "within_contact_band"),
                                   (2+probe.CONTACT_M/2, "within_contact_band")):
            result = probe.ordering({"ray_distance_m": distance}, eye)
            self.assertEqual(result["classification"], expected)
            self.assertEqual(result["body_minus_eye_m"], distance-2)
        self.assertEqual(probe.ordering(None, eye)["classification"], "missing_intersection")

    def test_nearest_is_sorted_distance_not_triangle_or_target_order(self):
        hits = probe.intersections((0, 0, 0), (0, 0, 1), [self.triangle(3), self.triangle(1)])
        self.assertEqual([h["ray_distance_m"] for h in hits], [1, 3])
        self.assertEqual(probe.nearest(hits)["ray_distance_m"], 1)
        self.assertEqual(len(probe.nearest(hits)["ties"]), 1)

    def test_equal_depth_boundary_ties_preserved(self):
        triangles = probe.indexed_mesh([[-1, -1, 2], [1, -1, 2], [1, 1, 2], [-1, 1, 2]],
                                      [0, 1, 2, 0, 2, 3], [{}, {}])
        hits = probe.intersections((0, 0, 0), (0, 0, 1), triangles)
        self.assertEqual(len(probe.nearest(hits)["ties"]), 2)
        self.assertTrue(all(h["boundary"] for h in hits))


class ProvenanceControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = probe.load_sources(probe.REPO)

    def test_original_pinned_asset_hashes(self):
        self.assertEqual(probe.sha((probe.REPO/probe.BASE).read_bytes()),
                         "ee8a4b4061eb481551a8e69ae5b8a088e13e746fb3b272f6d27fa97cd99164d2")
        self.assertEqual(probe.sha((probe.REPO/probe.MAP).read_bytes()),
                         "68582e28e9176cba7cfcf35208f671b6201b8d1bc95c32decff61a3160ec34d8")
        self.assertEqual(probe.sha((probe.REPO/probe.EYE).read_bytes()),
                         "783fe1e6331162c876520b4c2bed7a8ca06354ca15497e8ebd68bb1b59f4d3de")

    def test_fixed_selection_and_side_membership(self):
        selection = probe.selection(self.sources["eye_triangles"], self.sources["mapping"])
        self.assertEqual(len(selection), 12)
        self.assertEqual([p["probe_id"] for p in selection], [f"{side}/{suffix}"
            for side in ("source_left", "source_right")
            for suffix in ("triangle-0", "triangle-28", "triangle-56", "triangle-85", "helper-min", "helper-max")])
        for p in selection:
            lo, hi = probe.SIDE_RANGES[p["side"]]
            self.assertTrue(all(lo <= i <= hi for i in p["helper_ids"]))
        # Counterexample: a different triangle choice produces different
        # provenance; it cannot silently reuse the fixed selection identity.
        with patch.object(probe, "TRIANGLE_ORDINALS", (1, 28, 56, 85)):
            changed = probe.selection(self.sources["eye_triangles"], self.sources["mapping"])
        self.assertNotEqual(probe.semantic_sha(selection), probe.semantic_sha(changed))

    def test_missing_mixed_or_reordered_source_selection_counterexamples(self):
        triangles = self.sources["eye_triangles"]
        mapping = self.sources["mapping"]
        with self.assertRaises(ValueError):
            probe.selection(triangles[:-1], mapping)
        changed = copy.deepcopy(triangles)
        left_id = next(i for i, helper in enumerate(mapping) if helper < 14670)
        right_id = next(i for i, helper in enumerate(mapping) if helper >= 14670)
        first = changed[0]["source_vertex_ids"]
        first[0], first[1] = left_id, right_id
        with self.assertRaises(ValueError):
            probe.selection(changed, mapping)
        original = probe.selection(triangles, mapping)
        reversed_selection = probe.selection(list(reversed(triangles)), mapping)
        self.assertNotEqual(probe.semantic_sha(original), probe.semantic_sha(reversed_selection))

    def test_bad_obj_and_mapping_fail_explicitly(self):
        for text in ("", "v 0 0 0\nf 1 2 3 4", "v 0 0 0\nf 1 1 1"):
            with self.assertRaises(ValueError):
                probe.obj(text)
        text = (probe.REPO/probe.MAP).read_text()
        with self.assertRaisesRegex(ValueError, "deletion"):
            probe.eye_mapping(text+"\ndelete_verts\n")
        with self.assertRaises(ValueError):
            probe.eye_mapping(text.replace("14666\n", "0\n", 1))

    def test_bad_raw_identity_stops_before_json_or_geometry(self):
        with self.assertRaisesRegex(ValueError, "exact raw envelope hash mismatch"):
            probe.capture_record(b"{}", "native", "sf", {}, [])
        self.assertEqual(len(probe.EXPECTED), 8)
        self.assertTrue(all(len(h) == 64 for h in probe.EXPECTED.values()))


if __name__ == "__main__":
    unittest.main()
