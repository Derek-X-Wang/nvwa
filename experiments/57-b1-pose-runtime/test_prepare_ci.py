#!/usr/bin/env python3
"""Exercise real portable-source preparation and its authenticated seed boundary."""
import importlib.util,json,shutil,tempfile,unittest
from pathlib import Path
from prepare_ci import prepare_ci
from prepare import tree
ROOT=Path(__file__).resolve().parent
class PortablePreparation(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.base=Path(cls.temp.name).resolve();module_path=ROOT.parent/'59-b1-ci-inputs/prepare_ci_inputs.py';spec=importlib.util.spec_from_file_location('b1_ci_inputs',module_path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);cls.seed=cls.base/'seed';module.prepare(cls.seed)
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def new_seed(self,name):p=self.base/name;shutil.copytree(self.seed,p);return p
 def test_actual_preparation_code_bytes(self):
  out=self.base/'prepared';r=prepare_ci(self.seed,out);self.assertEqual(r['source_code_tree_sha256'],'1c75796828d3af9311ac9bf6f8e8777a77d66838e598544aff7377b908c8a6e8');self.assertTrue((out/'.deps/bevy_obj-0.19.0/src/lib.rs').is_file());self.assertIn('../.deps/',(out/'derived/Cargo.toml').read_text())
 def test_tampered_source_rejected_before_output(self):
  seed=self.new_seed('tampered');p=seed/'source/humentity/src/rigs.rs';p.write_bytes(p.read_bytes()+b'\n');out=self.base/'tamper-out'
  with self.assertRaisesRegex(ValueError,'hash mismatch'):prepare_ci(seed,out)
  self.assertFalse(out.exists())
 def test_missing_or_extra_file_rejected(self):
  seed=self.new_seed('missing');(seed/'source/humentity/LICENSE').unlink();out=self.base/'missing-out'
  with self.assertRaisesRegex(ValueError,'file set mismatch'):prepare_ci(seed,out)
  self.assertFalse(out.exists())
 def test_symlink_rejected(self):
  seed=self.new_seed('symlink');p=seed/'source/humentity/LICENSE';p.unlink();p.symlink_to(self.seed/'source/humentity/LICENSE');out=self.base/'symlink-out'
  with self.assertRaisesRegex(ValueError,'symlink'):prepare_ci(seed,out)
  self.assertFalse(out.exists())
if __name__=='__main__':unittest.main()
