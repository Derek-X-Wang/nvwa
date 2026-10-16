"""Exercise the actual portable staging CLI, including Python -O rejection."""
import importlib.util,json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
class PortablePreparation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        work=REPO/'.work/b1-pose-viewer';work.mkdir(parents=True,exist_ok=True)
        cls.temporary=tempfile.TemporaryDirectory(prefix='portable-tests-',dir=work)
        cls.root=Path(cls.temporary.name)
        path=REPO/'experiments/59-b1-ci-inputs/prepare_ci_inputs.py'
        spec=importlib.util.spec_from_file_location('approved_input_extractor',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        cls.seed=cls.root/'seed';module.prepare(cls.seed)
    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()
    def invoke(self,seed,out):
        return subprocess.run([sys.executable,'-O',str(ROOT/'prepare.py'),'--ci-inputs',str(seed),'--out',str(out)],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    def test_real_portable_sources_stage_and_identity_is_stable(self):
        out=self.root/'valid-site'
        first=self.invoke(self.seed,out);self.assertEqual(first.returncode,0,first.stderr)
        identity=(out/'assets/build-identity.json').read_bytes()
        again=self.invoke(self.seed,out);self.assertEqual(again.returncode,0,again.stderr)
        self.assertEqual(identity,(out/'assets/build-identity.json').read_bytes())
        self.assertEqual(len(json.loads((out/'assets/input-identity.json').read_text())['asset_files']),13)
    def reject_corruption(self,relative,label):
        seed=self.root/(label+'-seed');shutil.copytree(self.seed,seed)
        path=seed/relative;data=bytearray(path.read_bytes());data[len(data)//2]^=1;path.write_bytes(data)
        out=self.root/(label+'-site');result=self.invoke(seed,out)
        self.assertNotEqual(result.returncode,0);self.assertIn('InputError',result.stderr);self.assertFalse(out.exists(),'rejected bytes created staging output')
    def test_corrupt_copied_sample_is_rejected_with_optimization(self):self.reject_corruption('sample/base.obj','sample-corrupt')
    def test_corrupt_copied_original_source_is_rejected_with_optimization(self):self.reject_corruption('source/humentity/src/lib.rs','source-corrupt')
    def test_missing_derived_source_rejects_real_identity_seam(self):
        spec=importlib.util.spec_from_file_location('viewer_preparation',ROOT/'prepare.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        fake=self.root/'missing-runtime';(fake/'adapter/src').mkdir(parents=True);(fake/'adapter/src/lib.rs').write_text('pub fn valid(){}')
        with self.assertRaises(module.InputError):module.source_files(fake)
        (fake/'derived/src').mkdir(parents=True)
        with self.assertRaises(module.InputError):module.source_files(fake)
        (fake/'derived/src/lib.rs').write_text('')
        with self.assertRaises(module.InputError):module.source_files(fake)
    def test_output_symlinks_preserve_unrelated_files(self):
        victim=self.root/'victim';victim.mkdir();marker=victim/'user-file.txt';marker.write_text('preserve')
        out=self.root/'symlink-site';out.symlink_to(victim,target_is_directory=True)
        result=self.invoke(self.seed,out);self.assertNotEqual(result.returncode,0);self.assertIn('symlink',result.stderr)
        self.assertEqual(marker.read_text(),'preserve');self.assertEqual(list(victim.iterdir()),[marker])
        nested=self.root/'nested-site';nested.mkdir();(nested/'assets').symlink_to(victim,target_is_directory=True)
        result=self.invoke(self.seed,nested);self.assertNotEqual(result.returncode,0);self.assertIn('symlink',result.stderr)
        self.assertEqual(list(victim.iterdir()),[marker]);self.assertFalse((nested/'index.html').exists())
if __name__=='__main__':unittest.main()
