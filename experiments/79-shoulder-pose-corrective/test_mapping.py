#!/usr/bin/env python3
"""Controls of the actual mapper's source-mask/ray seams; no GPU acceptance."""
import unittest
import map_notch as m

class MappingControls(unittest.TestCase):
 def test_ray_controls(self):self.assertEqual(m.controls(),7)
 def test_source_quad_exact_fan(self):
  faces=[{'source_face0':131,'OBJ_line1':3931,'source_ids':[830,168,212,847]}]
  part={'source_ids':[830,168,212,847],'indices':[0,1,2,0,2,3]}
  bound,removed,tris=m.bind_source(part,faces)
  self.assertEqual([r['fan_triangle0'] for r in bound],[0,1]);self.assertEqual(removed,[])
  bad={**part,'indices':[0,1,2,0,3,2]}
  with self.assertRaises(ValueError):m.bind_source(bad,faces)
 def test_partial_delete_quad_stays_whole_and_fully_covered_quad_is_removed(self):
  faces=[{'source_face0':0,'source_ids':[0,1,2,3]},{'source_face0':1,'source_ids':[4,5,6,7]}]
  part={'source_ids':list(range(8)),'indices':[0,1,2,0,2,3]}
  bound,removed,tris=m.bind_source(part,faces,{0,1,4,5,6,7})
  self.assertEqual(removed,[1]);self.assertEqual(len(tris),2)
  with self.assertRaises(ValueError):m.bind_source(part,faces,{0,1,2,3,4,5,6,7})
 def test_helpers_are_never_displayed(self):
  faces=[{'source_face0':0,'source_ids':[0,1,2,3]},{'source_face0':1,'source_ids':[13380,13381,13382,13383]}]
  part={'source_ids':[0,1,2,3],'indices':[0,1,2,0,2,3]}
  self.assertEqual(m.bind_source(part,faces,set())[1],[1])
 def test_depth_and_double_sided(self):
  origin=[0,0,0];direction=[0,0,1]
  near=[[-1,-1,.9],[1,-1,.9],[0,1,.9]];far=[[-1,-1,1.],[1,-1,1.],[0,1,1.]]
  self.assertLess(m.intersect(origin,direction,near)['distance_m'],m.intersect(origin,direction,far)['distance_m'])
  self.assertIsNotNone(m.intersect(origin,direction,list(reversed(near))))
 def test_nonorthogonal_camera_inverse_not_transpose(self):
  c={'azimuth_degrees':180,'elevation_degrees':3,'distance':.95,'target_height':1.2807446,'fov_degrees':30}
  cam=m.camera(c);r,u,b,o=cam;r=[v*1.000003 for v in r];u=[v*.999997 for v in u]
  det=m.dot(r,m.cross(u,b));rows=[[x/det for x in v] for v in (m.cross(u,b),m.cross(b,r),m.cross(r,u))]
  actual=(r,u,b,o,rows);pixel=[340.5,196.5];direction=m.ray(pixel,actual,m.projection(c));p=[x+v*.98 for x,v in zip(o,direction)]
  for a,b in zip(m.project(p,actual,m.projection(c)),pixel):self.assertAlmostEqual(a,b,places=9)

if __name__=='__main__':unittest.main()
