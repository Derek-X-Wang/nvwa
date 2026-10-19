import importlib.util,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));import check_captures as check
class Checker(unittest.TestCase):
 def test_hash_codec_preserves_original_negative_zero(self):
  from source_binding import serde_value_sha256
  self.assertNotEqual(serde_value_sha256({'skin':[-0.0]}),serde_value_sha256({'skin':[0.0]}))
  self.assertEqual(serde_value_sha256({'b':1,'a':[1.0]}),serde_value_sha256({'a':[1.0],'b':1}))
 def test_nonfinite_and_duplicate_wire_json_rejects(self):
  from source_binding import strict_json
  for raw in ['{"x":NaN}','{"x":Infinity}','{"x":1,"x":2}']:
   with self.assertRaises(ValueError):strict_json(raw)

 def test_bounded_matrix_is_sixteen_combined_records_per_endpoint(self):
  keys=check.matrix_keys('native');self.assertEqual(len(keys),16);self.assertEqual({(k[4],k[5]) for k in keys},{('Combined','Textured')});self.assertEqual(len(check.matrix_keys('web','short-front',2)),12)
 def test_exact_bounds_reject_inflation_and_doubleplacement(self):
  p=[[-1.,-2.,-3.],[1.,2.,3.]];check.bounds(p,{'center':[0,0,0],'half_extents':[1,2,3]})
  for aabb in [{'center':[0,0,0],'half_extents':[1.001,2,3]},{'center':[0,1,0],'half_extents':[1,2,3]},None]:
   with self.assertRaises(ValueError):check.bounds(p,aabb)
 def test_unknown_or_edited_work_rejects(self):
  p=Path(__file__).resolve().parent/'works/short-front.nvwa.json';raw=p.read_text();self.assertEqual(check.classify_work(raw),'short-front');doc=json.loads(raw);doc['character']['parameters']['jaw_drop']=.1
  with self.assertRaises(ValueError):check.classify_work(json.dumps(doc))
 def test_empty_matrix_rejects(self):
  with self.assertRaises(ValueError):check.check([])
if __name__=='__main__':unittest.main()
