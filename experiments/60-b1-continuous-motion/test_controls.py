#!/usr/bin/env python3
"""Comparator-only known-geometry and tampered-record controls. No Rust mutation claim."""
import copy
import math
import unittest
from checker import Checker,check_time_binding,check_region_floor,I,CLIPS,check_bones,expected_fk,flatten,independent_lbs,inv,mul,rotation
from geometry import BVH,closest_triangle,strain,surface_queries

class Controls(unittest.TestCase):
 def time_record(self,k=0,seconds=0.):
  return {'kind':'matrix','request':{'k':k,'seconds':seconds},'snapshot':{'sample':{'timeline_id':'probe-entry','position_seconds':seconds,'source_seconds':seconds}}}
 def test_exact_matrix_time_binding_accepts_complete_grid(self):
  for k in range(33):self.assertEqual(check_time_binding(self.time_record(k,k/8)),k/8)
 def test_relabelled_neutral_k_cannot_earn_coverage(self):
  # Exercise the actual Checker.check entry point before it accesses rig/assets.
  checker=Checker.__new__(Checker);checker.seen=set();checker.keyframes=0
  for k in range(1,33):
   with self.assertRaisesRegex(ValueError,'seconds must equal k/8'):checker.check(self.time_record(k,0.))
  self.assertEqual(checker.seen,set());self.assertEqual(checker.keyframes,0)
 def test_matrix_k_rejects_bool_noninteger_and_out_of_range(self):
  for k in [True,False,0.,'0',-1,33]:
   with self.assertRaisesRegex(ValueError,'matrix k must'):check_time_binding(self.time_record(k,0.))
 def test_finite_timeline_cursor_and_source_mapping_are_both_checked(self):
  for field in ['position_seconds','source_seconds']:
   for value in [float('nan'),float('inf'),True,-.1,4.1,0.]:
    record=self.time_record(8,1.);record['snapshot']['sample'][field]=value
    with self.assertRaisesRegex(ValueError,'timeline cursor/source'):check_time_binding(record)
  record=self.time_record(8,1.);record['snapshot']['sample']['timeline_id']='other-entry'
  with self.assertRaisesRegex(ValueError,'timeline entry'):check_time_binding(record)
 def test_nearest_triangle_interior_is_not_nearest_vertex(self):
  q,bary=closest_triangle((.25,.25,1.),(0.,0.,0.),(1.,0.,0.),(0.,1.,0.))
  self.assertEqual(q,(.25,.25,0.));self.assertEqual(bary,(.5,.25,.25))
  hit=BVH([(0.,0.,0.),(1.,0.,0.),(0.,1.,0.)],[(0,1,2)]).nearest((.25,.25,1.))
  self.assertEqual(hit['distance'],1.);self.assertEqual(hit['local_signed_projection'],1.)
 def test_local_side_reverses_with_winding(self):
  points=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.)];p=(.25,.25,-.005)
  a=BVH(points,[(0,1,2)]).nearest(p);b=BVH(points,[(0,2,1)]).nearest(p)
  self.assertEqual(a['distance'],b['distance']);self.assertEqual(a['local_signed_projection'],-b['local_signed_projection']);self.assertLess(a['local_signed_projection'],0)
 def test_coincident_and_open_boundary_are_descriptors(self):
  points=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.)]
  hit=BVH(points,[(0,1,2)]).nearest((.25,.25,0.));self.assertEqual(hit['distance'],0.)
  self.assertEqual(strain(points,points,[(0,1,2)])['boundary_edges'],3)
 def test_degenerate_triangle_is_finite(self):
  q,b=closest_triangle((.5,1.,0.),(0.,0.,0.),(1.,0.,0.),(2.,0.,0.));self.assertEqual(q,(.5,0.,0.));self.assertIsNone(b)
 def test_authored_fold_and_rigid_rotation_control(self):
  rest=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.),(0.,-1.,0.)];tris=[(0,1,2),(1,0,3)];fold=copy.deepcopy(rest);fold[3]=(0.,1.,.001)
  green=strain(rest,rest,tris);red=strain(fold,rest,tris)
  self.assertEqual(green['fold_candidates_over_150_degrees'],0);self.assertEqual(red['fold_candidates_over_150_degrees'],1)
  rotated=[(p[0],-p[1],-p[2]) for p in rest];self.assertEqual(strain(rotated,rest,tris)['fold_candidates_over_150_degrees'],0)
 def test_descriptor_bands_are_not_quality_approval(self):
  p=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.)];result=surface_queries(p,[(0,1,2)],[(.2,.2,-.006)],[42]);self.assertEqual(result['negative_over_2mm'],1);self.assertEqual(result['negative_over_5mm'],1);self.assertIn('NOT-RUN',result['claim'])
 def bones(self,t):
  rest=[r[:] for r in I];rest[1][3]=.5
  bones=[{'name':'Root','parent':None,'canonical_rest':flatten(I),'frame_gauge':flatten(I),'rest':flatten(I),'inverse_bind':flatten(I)},
    {'name':'calf_l','parent':'Root','canonical_rest':flatten(rest),'frame_gauge':flatten(I),'rest':flatten(rest),'inverse_bind':flatten(inv(rest))},
    {'name':'foot_l','parent':'calf_l','canonical_rest':flatten(I),'frame_gauge':flatten(I),'rest':flatten(I),'inverse_bind':flatten(I)}]
  canonical,raw=expected_fk(bones,CLIPS[1],t)
  for b in bones:b.update(posed=flatten(raw[b['name']]),canonical_posed=flatten(canonical[b['name']]),skin=flatten(mul(raw[b['name']],inv(__import__('checker').mat(b['rest'])))))
  return bones
 def test_posed_skin_is_nonidentity_at_peak_and_valid(self):
  bones=self.bones(2.);skins,*_=check_bones(bones,CLIPS[1],2.);self.assertGreater(abs(skins[1][1][2]),.8)
 def test_frozen_identity_skin_at_peak_is_rejected(self):
  bones=self.bones(2.);bones[1]['skin']=flatten(I)
  with self.assertRaisesRegex(ValueError,'posed\\*IBM|FK'):check_bones(bones,CLIPS[1],2.)
 def test_frozen_rest_pose_at_peak_is_rejected(self):
  bones=self.bones(0.)
  with self.assertRaisesRegex(ValueError,'FK'):check_bones(bones,CLIPS[1],2.)
 def test_independent_lbs_normalizes_all_positive_aggregates(self):
  transform=[r[:] for r in I];transform[0][3]=1.
  result=independent_lbs([[0.,0.,0.]],[[[0,.1],[1,.2],[2,.3],[3,.4],[4,.5]]],[I,I,I,I,transform])
  self.assertAlmostEqual(result[0][0],1/3)
  with self.assertRaisesRegex(ValueError,'positive'):independent_lbs([[0.,0.,0.]],[[[0,-1.]]],[I])
 def test_original_calf_only_sweep_fails_unchanged_floor_gate_counterrotation_passes(self):
  # Authored geometry fixture: knee1m above floor, ankle at0, forward patch point20cm.
  # This is comparator-only; the actual r2 measured failure remains separate evidence.
  knee=[r[:] for r in I];knee[1][3]=1.
  bones=[{'name':'Root','parent':None,'canonical_rest':flatten(I),'frame_gauge':flatten(I),'rest':flatten(I),'inverse_bind':flatten(I)},
   {'name':'calf_l','parent':'Root','canonical_rest':flatten(knee),'frame_gauge':flatten(I),'rest':flatten(knee),'inverse_bind':flatten(inv(knee))},
   {'name':'foot_l','parent':'calf_l','canonical_rest':flatten(I),'frame_gauge':flatten(I),'rest':flatten(I),'inverse_bind':flatten(I)}]
  t=.4;angle=65*(1-math.cos(math.pi*t/2))/2
  corrected,raw=expected_fk(bones,CLIPS[1],t)
  local_ankle=inv(knee);original_foot=mul(mul(knee,rotation('x',angle)),local_ankle)
  original_point=independent_lbs([[0.,0.,.2]],[[[0,1.]]],[original_foot])[0]
  with self.assertRaisesRegex(ValueError,'foot region below floor'):check_region_floor(original_point[1],'left')
  corrected_point=independent_lbs([[0.,0.,.2]],[[[0,1.]]],[raw['foot_l']])[0]
  check_region_floor(corrected_point[1],'left')
  self.assertGreater(corrected_point[1],0.)
  for i in range(3):
   for j in range(3):self.assertAlmostEqual(raw['foot_l'][i][j],I[i][j],places=12)
 def test_wrong_gauge_is_not_identity_shortcut(self):
  bones=self.bones(2.);bones[1]['frame_gauge']=flatten(rotation('z',30))
  with self.assertRaisesRegex(ValueError,'FK'):check_bones(bones,CLIPS[1],2.)

if __name__=='__main__':unittest.main()
