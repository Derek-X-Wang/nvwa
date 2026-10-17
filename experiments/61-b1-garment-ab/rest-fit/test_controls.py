"""Cheap controls for the experimental delta path; no private capture imports."""
import unittest
import compare


class DeltaControls(unittest.TestCase):
    def setUp(self):
        self.rest = {0: (1., 2., 3.), 1: (7., 8., 9.)}
        self.posed = {0: (4., 5., 6.), 1: (10., 11., 12.)}
        # Opposite x/y bases and arbitrary translations: delta ignores translation.
        self.skins = [((1., 0., 0., 99.), (0., 1., 0., 98.), (0., 0., 1., 97.), (0., 0., 0., 1.)),
                      ((-1., 0., 0., -99.), (0., -1., 0., -98.), (0., 0., 1., -97.), (0., 0., 0., 1.))]
        self.weights = {0: ((0, .25), (1, .75))}

    def test_same_path_zero_delta_exact(self):
        rest, posed = compare.apply_offsets(self.rest, self.posed, {0: (0., 0., 0.)}, {0: -2., 1: 3., 2: .5}, self.weights, self.skins)
        self.assertEqual(rest, self.rest)
        self.assertEqual(posed, self.posed)

    def test_signed_scale_all_influences_and_fixed_exterior(self):
        rest, posed = compare.apply_offsets(self.rest, self.posed, {0: (1., 2., 4.)}, {0: -2., 1: 3., 2: .5}, self.weights, self.skins)
        self.assertEqual(rest[0], (-1., 8., 5.))
        self.assertEqual(posed[0], (5., 2., 8.))
        self.assertEqual(rest[1], self.rest[1])
        self.assertEqual(posed[1], self.posed[1])
        self.assertEqual(self.rest[0], (1., 2., 3.))

    def test_incident_set_includes_transition_exterior_faces(self):
        tri = [(182, 244, 246), (246, 22, 29), (22, 900, 901), (902, 903, 904)]
        groups = compare.groups(tri, (182, 244, 246, 22, 29))
        self.assertEqual(groups['all_affected_incident'], [0, 1, 2])
        self.assertEqual(groups['ring_incident'], [2])
        self.assertEqual(set(groups['all_affected_incident']), set(groups['core_incident']) | set(groups['ring_incident']))


if __name__ == '__main__':
    unittest.main()
