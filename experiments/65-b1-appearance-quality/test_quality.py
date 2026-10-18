"""Cheap mathematical controls; no Cargo, renderer, network or new assets."""
import copy
import math
import unittest
import analyze

class NormalControls(unittest.TestCase):
    def test_planar_quad_has_exact_outward_normal_at_every_corner(self):
        rest = [[0,0,0], [2,0,0], [2,1,0], [0,1,0]]
        self.assertEqual(analyze.normals(rest, [[0,1,2,3]], True), [[0,0,1]]*4)

    def test_reversed_winding_reverses_normals(self):
        rest = [[0,0,0], [2,0,0], [2,1,0], [0,1,0]]
        self.assertEqual(analyze.normals(rest, [[3,2,1,0]], True), [[0,0,-1]]*4)

    def test_pinned_polygon_cycle_invariance_and_fan_mutation_sensitivity(self):
        for stem in ['eyes/low-poly/low-poly', 'hair/short04/short04']:
            rest, faces = analyze.polygons(analyze.ASSETS/(stem+'.obj'))
            baseline = analyze.normals(rest, faces, True)
            for shift in [1,2,3]:
                shifted = [f[shift:]+f[:shift] for f in faces]
                candidate = analyze.normals(rest, shifted, True)
                self.assertLess(max(abs(x-y) for a,b in zip(baseline,candidate) for x,y in zip(a,b)), 1e-12)
            shifted = [f[1:]+f[:1] for f in faces]
            old = analyze.normals(rest, faces)
            mutated = analyze.normals(rest, shifted)
            self.assertGreater(max(analyze.degrees(a,b) for a,b in zip(old,mutated)), 15)

    def test_source_inputs_are_unchanged_and_all_outputs_unit(self):
        for stem in ['eyes/low-poly/low-poly', 'hair/short04/short04']:
            rest, faces = analyze.polygons(analyze.ASSETS/(stem+'.obj'))
            before = copy.deepcopy((rest,faces))
            normals = analyze.normals(rest, faces, True)
            self.assertEqual((rest,faces), before)
            self.assertTrue(all(abs(analyze.dot(n,n)-1) < 1e-12 for n in normals))

    def test_rigid_translation_does_not_change_normals(self):
        rest, faces = analyze.polygons(analyze.ASSETS/'eyes/low-poly/low-poly.obj')
        shifted = [[x+1,y-2,z+3] for x,y,z in rest]
        a,b = analyze.normals(rest,faces,True), analyze.normals(shifted,faces,True)
        self.assertLess(max(abs(x-y) for p,q in zip(a,b) for x,y in zip(p,q)),1e-11)

    def test_degenerate_polygon_fails_closed(self):
        with self.assertRaisesRegex(ValueError,'degenerate'):
            analyze.normals([[0,0,0],[1,0,0],[2,0,0]], [[0,1,2]], True)

if __name__ == '__main__': unittest.main()
