#!/usr/bin/env python3
"""Small controls for the research recipe and boundary comparator, not product proof."""
import unittest,sys
sys.dont_write_bytecode=True
from run import smooth,boundary_control,normalize
class Controls(unittest.TestCase):
 def test_noop_has_no_overrides(self):
  rows={0:{'a':1.},1:{'a':.2,'b':.8},2:{'b':1.}};adj={0:{1},1:{0,2},2:{1}};out,ring=smooth(rows,adj,core={0},core_strength=0,ring_strength=0);self.assertEqual(out,{});self.assertEqual(ring,{1})
 def test_one_simultaneous_pass_exact_constants(self):
  rows={0:{'a':1.},1:{'b':1.},2:{'c':1.}};adj={0:{1},1:{0,2},2:{1}};out,_=smooth(rows,adj,core={0});self.assertEqual(out[0],{'a':.5,'b':.5});self.assertEqual(out[1],{'a':.125,'b':.75,'c':.125});self.assertNotIn(2,out)
 def test_more_than_four_influences_retained(self):
  rows={0:{'a':1.},1:{str(i):1/6 for i in range(6)}};out,_=smooth(rows,{0:{1},1:{0}},core={0});self.assertEqual(len(out[0]),7);self.assertIn('a',out[0]);self.assertAlmostEqual(sum(out[0].values()),1)
 def test_boundary_negative_control(self):
  original={0:[0,0,0],1:[1,0,0]};boundary_control(original,{0:[0,1,0],1:[1,0,0]},{0})
  with self.assertRaisesRegex(ValueError,'outside region changed'):boundary_control(original,{0:[0,1,0],1:[1,0,.01]},{0})
 def test_nonfinite_negative_control(self):
  with self.assertRaises(ValueError):normalize({'a':float('nan')})
if __name__=='__main__':unittest.main()
