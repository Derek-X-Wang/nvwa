from pathlib import Path
import unittest,json,hashlib,tempfile
import frozen_context as F
EXP=Path(__file__).resolve().parent;ROOT=EXP.parents[1]
class Integration73(unittest.TestCase):
 def test_exact_cohort_and_old_test_bytes(self):
  raw=(EXP/'FROZEN-INPUTS.json').read_bytes();old=json.loads(raw)
  contexts=F.current_source_contexts(EXP,raw,old)
  cpu=F._cpu_context(EXP,F._motion_query_source_context(EXP,F._running_source_context(EXP,old,contexts))[1])
  name,expected=F.integration_source_context(EXP,cpu,ROOT)
  self.assertEqual(name,F.INTEGRATION_CONTEXT_ID);self.assertEqual(len(expected),1552)
  # Presence, not completeness, routes a nonhistorical sibling to strict union validation.
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);assets=root/'assets/characters';assets.mkdir(parents=True)
   (assets/'mpfb-b1-v10').mkdir()
   self.assertFalse(F.has_chest_sibling_inputs(root))
   for version in (11,12,13):
    sibling=assets/f'mpfb-b1-v{version}';sibling.mkdir()
    with self.subTest(sibling=version):self.assertTrue(F.has_chest_sibling_inputs(root))
    sibling.rmdir()
  tree=EXP/'fixtures/integration-historical-test-prepare';raw=(tree/'manifest.json').read_bytes()
  self.assertEqual(hashlib.sha256(raw).hexdigest(),'33d52a24b909473c7db7469d80956c9193638c4f1238d31854d666881a1a2025')
  items=json.loads(raw)
  self.assertEqual({p.name for p in tree.iterdir()},set(items)|{'manifest.json'})
  for name,item in items.items():
   b=(tree/name).read_bytes();self.assertEqual(len(b),item['bytes']);self.assertEqual(hashlib.sha256(b).hexdigest(),item['sha256'])
if __name__=='__main__':unittest.main()
