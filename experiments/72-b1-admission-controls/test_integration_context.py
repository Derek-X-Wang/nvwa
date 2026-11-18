"""Candidate exactness/negative controls; no historical numerical acceptance claim."""
from pathlib import Path
import importlib.util,json,tempfile,shutil,unittest,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
API=load('integration_test72_run',HERE/'run.py');I=load('integration_test72_gate',HERE/'integration_context.py')
class IntegrationCandidate(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.pins=json.loads((HERE/'pins.json').read_bytes());cls.main,cls.chest=I.predecessors72(API,cls.pins);cls.expected=I.expected(cls.main,cls.chest,'72')[1]
 def test_exact_root_and_historical_rejection(self):
  self.assertEqual(API.check_inputs(ROOT)['checked_input_context']['id'],I.ID)
  self.assertEqual(len(self.expected),1264)
  with self.assertRaisesRegex(ValueError,'not historical'):API.check_source_context(ROOT,self.pins,historical_only=True)
 def test_source_asset_and_inventory_mutations(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   for name in self.expected:
    dst=root/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dst)
   self.assertEqual(I.verify(root,self.main,self.chest,'72')[0],I.ID)
   for version in [10,14]:
    directory=root/f'assets/characters/mpfb-b1-v{version}';held=root/f'held-{version}';directory.rename(held)
    try:
     with self.subTest(missing_lineage=version),self.assertRaisesRegex(ValueError,'missing'):
      API.check_source_context(root,self.pins)
    finally:held.rename(directory)
   for name in ['crates/nvwa-core/src/b1.rs','assets/characters/mpfb-b1-v10/targets/breast-trans-up.target','assets/characters/mpfb-b1-v14/manifest.json']:
    p=root/name;b=p.read_bytes();p.write_bytes(bytes([b[0]^1])+b[1:])
    with self.subTest(path=name),self.assertRaisesRegex(ValueError,'source bytes mismatch'):I.verify(root,self.main,self.chest,'72')
    p.write_bytes(b)
   for version in range(9,15):
    extra=root/f'assets/characters/mpfb-b1-v{version}/unreviewed.target';extra.write_bytes(b'x')
    with self.subTest(extra_version=version),self.assertRaisesRegex(ValueError,'inventory mismatch'):I.verify(root,self.main,self.chest,'72')
    extra.unlink()
   p=root/'crates/nvwa-core/src/b1.rs';b=p.read_bytes();p.unlink();p.symlink_to(ROOT/'crates/nvwa-core/src/b1.rs')
   with self.assertRaisesRegex(ValueError,'symlink'):I.verify(root,self.main,self.chest,'72')
 def test_predecessor_bytes_and_manifest_mutation(self):
  original=I.EXP
  with tempfile.TemporaryDirectory() as tmp:
   exp=Path(tmp);shutil.copytree(HERE/'fixtures/pre-chest-v14-integration',exp/'fixtures/pre-chest-v14-integration');shutil.copyfile(HERE/I.NAME,exp/I.NAME)
   try:
    I.EXP=exp;I.expected(self.main,self.chest,'72')
    p=exp/'fixtures/pre-chest-v14-integration/pr/crates/nvwa-core/src/b1.rs';b=p.read_bytes();p.write_bytes(b+b' ')
    with self.assertRaisesRegex(ValueError,'fixture bytes mismatch'):I.expected(self.main,self.chest,'72')
    p.write_bytes(b);p=exp/I.NAME;p.write_bytes(p.read_bytes()+b' ')
    with self.assertRaisesRegex(ValueError,'manifest identity mismatch'):I.expected(self.main,self.chest,'72')
   finally:I.EXP=original
 def test_same_count_sibling_swap_rejects(self):
  wrong=(self.main[0],dict(self.main[1]));wrong[1]['crates/nvwa-core/src/b1.rs']=self.chest[1]['crates/nvwa-core/src/b1.rs']
  with self.assertRaises(ValueError):I.expected(wrong,self.chest,'72')

class RetainedHistoricalTests(unittest.TestCase):
 def test_original_test_bytes_are_pinned(self):
  tree=HERE/'fixtures/integration-historical-tests';raw=(tree/'manifest.json').read_bytes()
  self.assertEqual(hashlib.sha256(raw).hexdigest(),'5f2610963cbb1aa2e7a8c7c2cb04feee1a40893cd085fb2a4a7b3fa104b9e899')
  items=json.loads(raw)
  self.assertEqual({p.relative_to(tree).as_posix() for p in tree.rglob('*') if p.is_file()},set(items)|{'manifest.json'})
  for name,item in items.items():self.assertEqual(I.pin(I.file(tree,name).read_bytes()),{k:item[k] for k in ['bytes','sha256']})

if __name__=='__main__':unittest.main()
