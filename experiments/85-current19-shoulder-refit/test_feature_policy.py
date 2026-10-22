"""Small v4 controls plus only the retained real source213 witness."""
import copy
import json
import math
from pathlib import Path
import unittest
from unittest.mock import patch
import feature_policy as f
from geometry_checks import source_triangles,e


def bent():
    body=[[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,-1.,1.]]
    triangles=[[0,1,2],[1,0,3]]
    return body,triangles,f.source_normals(body,triangles)


def controls():
    body,triangles,smooth=bent();samples=[];planes=[]
    f.append_constraints(samples,planes,10,0,(1.,0.,0.),[0,1,2],[.5,0.,0.],
                         [0.,1.,1.],body,triangles,smooth)
    return samples,planes


class PolicyControls(unittest.TestCase):
    def test_frozen_json_semantics_and_all_mutations_refuse(self):
        policy=json.loads(f.POLICY_PATH.read_text());self.assertEqual(f.validate_policy(policy),f.POLICY)
        for key,value in [('authoring_policy_version',3),('candidate_count',True),('extra',1)]:
            changed=copy.deepcopy(policy);changed[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):f.validate_policy(changed)
        changed=copy.deepcopy(policy);changed['constraints']['saved_text_residual_floor_m']=.0009
        with self.assertRaises(ValueError):f.validate_policy(changed)

    def test_face_edge_vertex_declared_field_and_continuity(self):
        body,triangles,smooth=bent()
        for point,feature in [([.25,.25,0.],[0,1,2]),([.5,0.,0.],[0,1]),([0.,0.,0.],[0])]:
            result=f.feature_direction(point,body,triangles,smooth)
            self.assertEqual(result['source_feature'],feature)
            weights=result['source_weights']
            expected=f.normalized([sum(smooth[i][k]*w for i,w in weights) for k in range(3)],'expected')
            self.assertLess(f.norm(f.sub(result['normal'],expected)),1e-15)
        edge=f.feature_direction([.5,0.,0.],body,triangles,smooth)['normal']
        close=f.feature_direction([.5,1e-5,0.],body,triangles,smooth)['normal']
        self.assertLess(f.norm(f.sub(close,edge)),1e-5)
        vertex=f.feature_direction([0.,0.,0.],body,triangles,smooth)['normal']
        close=f.feature_direction([1e-5,1e-5,0.],body,triangles,smooth)['normal']
        self.assertLess(f.norm(f.sub(close,vertex)),1e-5)

    def test_triangle_order_and_cyclic_render_representations_preserve_direction(self):
        body,triangles,smooth=bent();expected=f.feature_direction([.5,0.,0.],body,triangles,smooth)
        for changed in [triangles[::-1],[[1,2,0],[0,3,1]]]:
            field=f.source_normals(body,changed)
            actual=f.feature_direction([.5,0.,0.],body,changed,field)
            self.assertEqual(actual['source_weights'],expected['source_weights'])
            self.assertLess(f.norm(f.sub(actual['normal'],expected['normal'])),f.NORMAL_AGREEMENT)
        # Coincident position with distinct source identity is a separate feature.
        duplicate=body+[list(v) for v in body]
        changed=triangles+[[i+4 for i in tri] for tri in triangles]
        field=f.source_normals(duplicate,changed)
        with self.assertRaisesRegex(ValueError,'distinct nearest'):
            f.feature_direction([.5,0.,0.],duplicate,changed,field)

    def test_translation_and_rotation_transform_direction(self):
        body,triangles,smooth=bent();point=[.25,.25,0.]
        original=f.feature_direction(point,body,triangles,smooth)['normal']
        def transform(v):return [-v[1]+2,v[0]+4,v[2]-3]
        moved=[transform(v) for v in body];field=f.source_normals(moved,triangles)
        actual=f.feature_direction(transform(point),moved,triangles,field)['normal']
        self.assertLess(f.norm(f.sub(actual,[-original[1],original[0],original[2]])),1e-14)

    def test_distinct_nearest_surfaces_refuse_direction_but_keep_all_face_constraints(self):
        body=[[0.,0.,-1.],[1.,0.,-1.],[0.,1.,-1.],[0.,0.,1.],[1.,0.,1.],[0.,1.,1.]]
        triangles=[[0,1,2],[3,4,5]];smooth=f.source_normals(body,triangles)
        self.assertEqual(len(f.nearest_faces([.25,.25,0.],body,triangles,smooth)),2)
        with self.assertRaisesRegex(ValueError,'distinct nearest'):
            f.feature_direction([.25,.25,0.],body,triangles,smooth)

    def test_exact_point_and_weight_equivalence_refuse_without_epsilon(self):
        body,triangles,smooth=bent();faces=f.nearest_faces([.5,0.,0.],body,triangles,smooth)
        for key in ('point','source_weights'):
            changed=copy.deepcopy(faces)
            if key=='point':changed[1][key][0]+=1e-15
            else:changed[1][key][0][1]+=1e-15
            with self.subTest(key=key),patch.object(f,'nearest_faces',return_value=changed):
                with self.assertRaisesRegex(ValueError,'distinct nearest'):
                    f.feature_direction([.5,0.,0.],body,triangles,smooth)

    def test_nonfinite_invalid_repeated_topology_refuses(self):
        for body,triangles in [([[0,0,math.nan],[1,0,0],[0,1,0]],[[0,1,2]]),
            ([[0,0,0],[1,0,0],[0,1,0]],[[0,1,4]]),
            ([[0,0,0],[1,0,0],[0,1,0]],[[0,1,1]]),
            ([[0,0,0],[1,0,0],[0,1,0]],[[False,1,2]])]:
            with self.subTest(triangles=triangles),self.assertRaises(ValueError):f.source_normals(body,triangles)
        body,triangles,smooth=bent()
        with self.assertRaises(ValueError):f.feature_direction([math.inf,0,0],body,triangles,smooth)
        with self.assertRaises(ValueError):f.nearest_faces([0,0,0],body,triangles,dict(smooth))

    def test_relevant_degenerate_zero_reversed_disconnected_nonmanifold_refuse(self):
        fixtures=[
            ([[0,0,0],[1,0,0],[2,0,0]],[[0,1,2]],'degenerate'),
            ([[0,0,0],[1,0,0],[0,1,0]],[[0,1,2],[0,2,1]],'zero'),
            ([[0,0,0],[1,0,0],[0,1,0],[0,-1,1]],[[0,1,2],[0,1,3]],'winding'),
            ([[0,0,0],[1,0,0],[0,1,0],[-1,0,0],[0,-1,0]],[[0,1,2],[0,3,4]],'fan'),
            ([[0,0,0],[1,0,0],[0,1,0],[0,-1,1],[0,-1,2]],[[0,1,2],[1,0,3],[1,0,4]],'nonmanifold')]
        for body,triangles,message in fixtures:
            with self.subTest(message=message):
                smooth=f.source_normals(body,triangles)
                with self.assertRaisesRegex(ValueError,message):f.feature_direction(body[0],body,triangles,smooth)

    def test_unrelated_bad_fan_does_not_require_whole_body_manifold(self):
        body,triangles,_=bent()
        body=body+[[10.,10.,10.],[11.,10.,10.],[10.,11.,10.],[9.,10.,10.],[10.,9.,10.]]
        triangles=triangles+[[4,5,6],[4,7,8]]
        smooth=f.source_normals(body,triangles)
        self.assertEqual(f.feature_direction([0.,0.,0.],body,triangles,smooth)['source_feature'],[0])

    def test_nonpositive_source_orientation_refuses(self):
        body,triangles,smooth=bent();smooth[0]=[0.,0.,-1.]
        with self.assertRaisesRegex(ValueError,'nonpositive'):
            f.feature_direction(body[0],body,triangles,smooth)


class ConstraintControls(unittest.TestCase):
    def test_all_faces_stable_identity_and_omission_rejects_production_seam(self):
        samples,planes=controls();self.assertEqual(samples[0]['nearest_face_ids'],[0,1])
        self.assertEqual([(r['logical_sample0'],r['body_triangle0']) for r in planes],[(0,0),(0,1)])
        self.assertEqual(f.validate_constraint_coverage(samples,planes,expected_count=1),2)
        with self.assertRaisesRegex(ValueError,'omitted'):
            f.amplitude_interval(samples,planes[:1],{0:[0,1,1]},expected_count=1)
        # Even a self-consistent omitted list is rejected against independent expected coverage.
        omitted=copy.deepcopy(samples);omitted[0]['nearest_face_ids']=[0]
        with self.assertRaisesRegex(ValueError,'independent'):
            f.amplitude_interval(omitted,planes[:1],{0:[0,1,1]},expected_count=1,expected_samples=samples)

    def test_signed_interval_and_caps_are_original_rules(self):
        samples,planes=controls()
        planes[0].update(d_m=0.,slope=1.)
        planes[1].update(d_m=.003,slope=-1.)
        self.assertEqual(f.amplitude_interval(samples,planes,{0:[0,0,1]},expected_count=1),(.001,.002))
        planes[1].update(d_m=.001,slope=1e-12)
        self.assertEqual(f.amplitude_interval(samples,planes,{0:[0,0,1]},expected_count=1),(.001,.02))
        planes[1].update(d_m=.0009,slope=-1e-12)
        with self.assertRaisesRegex(ValueError,'zero-slope'):
            f.amplitude_interval(samples,planes,{0:[0,0,1]},expected_count=1)

    def test_contradictory_and_nonpositive_interval_refuse(self):
        samples,planes=controls();planes[0].update(d_m=0.,slope=1.)
        planes[1].update(d_m=.0015,slope=-1.)
        with self.assertRaisesRegex(ValueError,'empty/nonpositive'):
            f.amplitude_interval(samples,planes,{0:[0,0,1]},expected_count=1)
        for row in planes:row.update(d_m=.002,slope=1.)
        with self.assertRaisesRegex(ValueError,'empty/nonpositive'):
            f.amplitude_interval(samples,planes,{0:[0,0,1]},expected_count=1)

    def test_ideal_pass_and_single_realized_face_fail_rejects(self):
        samples,planes=controls()
        lower,_=f.amplitude_interval(samples,planes,{0:[0,1,1]},expected_count=1)
        self.assertTrue(all(r['d_m']+lower*r['slope']>=f.MARGIN for r in planes))
        realized=[[.5,.001,.001],[0,0,0],[0,0,0]]
        self.assertEqual(f.validate_realized_constraints(samples,planes,realized,expected_count=1),2)
        # f32 values are the serialized/parsed values; only the second retained face fails.
        realized[0]=[.5,e.f32(-.0005),e.f32(.0011)]
        self.assertGreater(f.dot(realized[0],planes[0]['plane']['normal']),f.RESIDUAL_FLOOR)
        with self.assertRaisesRegex(ValueError,'realized face'):
            f.validate_realized_constraints(samples,planes,realized,expected_count=1)
        self.assertGreaterEqual(planes[0]['realized_side_m'],f.RESIDUAL_FLOOR)
        self.assertLess(planes[1]['realized_side_m'],f.RESIDUAL_FLOOR)

    def test_duplicate_logical_points_remain_separate(self):
        samples,planes=controls();second=copy.deepcopy(samples[0]);second['logical_sample0']=1
        rows=copy.deepcopy(planes)
        for row in rows:row['logical_sample0']=1
        self.assertEqual(f.validate_constraint_coverage(samples+[second],planes+rows,expected_count=2),4)

    def test_invalid_count_identity_duplicate_metadata_and_nonfinite_refuse(self):
        samples,planes=controls()
        with self.assertRaisesRegex(ValueError,'coverage'):f.validate_constraint_coverage(samples,planes)
        for key,value in [('logical_sample0',True),('body_triangle0',3),('triangle0',11),('slope',math.nan)]:
            changed=copy.deepcopy(planes);changed[0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                f.validate_constraint_coverage(samples,changed,expected_count=1)
        with self.assertRaisesRegex(ValueError,'duplicate'):
            f.validate_constraint_coverage(samples,planes+[planes[0]],expected_count=1)
        with self.assertRaises(ValueError):
            f.validate_realized_constraints(samples,planes,[[math.nan,0,0]]*3,expected_count=1)


class RetainedSource213Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.body=e.raw_cage({'torso_length':0,'jaw_drop':0})
        cls.mapping=e.parse_mapping((e.SOURCE/'garment/female_sportsuit01.mhclo').read_bytes())
        cls.triangles=source_triangles(e.kernels.read_obj(e.SOURCE/'base.obj'),
                                     e.kernels.deleted_ids(e.SOURCE/'garment/female_sportsuit01.mhclo'))
        cls.smooth=f.source_normals(cls.body,cls.triangles)
        cls.point=[.23986494541168213,.5030818581581116,.037759795784950256]

    def test_real213_v3_rejects_and_v4_yields_canonical_three_face_direction(self):
        with self.assertRaisesRegex(ValueError,'ambiguous nearest normal tie'):
            f.old.nearest_plane(self.point,self.body,self.triangles,self.smooth)
        result=f.feature_direction(self.point,self.body,self.triangles,self.smooth)
        self.assertEqual(result['nearest_face_ids'],[13494,13495,13524])
        self.assertEqual(result['source_feature'],[8147])
        self.assertEqual(result['normal'],[.648487329830408,.48106648987859674,.5899484853487749])
        self.assertTrue(all(f.dot(result['normal'],face['normal'])>0 for face in result['nearest_faces']))

    def test_eight_real213_memberships_and_all24_constraints_preserved(self):
        cloth=source_triangles(e.kernels.read_obj(e.SOURCE/'garment/female_sportsuit01.obj'))
        support=json.loads((f.HERE.parent/'84-shoulder-rest-refit/authoring/support-proposal.json').read_text())
        memberships=[]
        for ordinal,ti in enumerate(support['incident_triangles0']):
            for sample0,bary in enumerate(f.old.SAMPLES):
                if any(sid==213 and w==1 for sid,w in zip(cloth[ti],bary)):
                    memberships.append((ordinal*7+sample0,ti,sample0))
        self.assertEqual(memberships,[(2,164,2),(8,165,1),(30,198,2),(36,199,1),
                                     (100,224,2),(106,225,1),(128,242,2),(134,243,1)])
        # Each real witness membership gets all three same retained nearest faces.
        faces=f.nearest_faces(self.point,self.body,self.triangles,self.smooth)
        samples=[];planes=[]
        with patch.object(f,'nearest_faces',return_value=faces):
            for _,ti,bi in memberships:
                f.append_constraints(samples,planes,ti,bi,f.old.SAMPLES[bi],cloth[ti],self.point,
                                     [0,0,0],self.body,self.triangles,self.smooth)
        self.assertEqual(f.validate_constraint_coverage(samples,planes,expected_count=8),24)
        self.assertTrue(all(sample['nearest_face_ids']==[13494,13495,13524] for sample in samples))

    def test_real213_triangle_order_direction_with_full_frozen_source_normals(self):
        # Only the one retained query is revisited; no other source directions/samples run.
        reverse=list(reversed(self.triangles));smooth=f.source_normals(self.body,reverse)
        result=f.feature_direction(self.point,self.body,reverse,smooth)
        self.assertLess(f.norm(f.sub(result['normal'],self.smooth[8147])),f.NORMAL_AGREEMENT)
        self.assertEqual(result['source_feature'],[8147])


if __name__=='__main__':unittest.main()
