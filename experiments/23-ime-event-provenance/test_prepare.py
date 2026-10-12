"""Expected-red package identity controls; never edit product inputs."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
spec=importlib.util.spec_from_file_location('prepare',Path(__file__).with_name('prepare.py'))
prepare=importlib.util.module_from_spec(spec);spec.loader.exec_module(prepare)

class Tests(unittest.TestCase):
    def test_refuses_changed_runtime_members(self):
        private=prepare.ROOT/'.work/bounded-scale-ime/issue32'
        for changed in ('index.html','nvwa_studio.js','nvwa_studio_bg.wasm'):
            with tempfile.TemporaryDirectory(dir=private) as temporary:
                base=Path(temporary);bundle=base/'input';bundle.mkdir();out=base/'output'
                for name in ('index.html','nvwa_studio.js','nvwa_studio_bg.wasm'):
                    if name==changed:(bundle/name).write_bytes(b'expected-red-mutated-package')
                    else:(bundle/name).symlink_to(prepare.ROOT/'dist/web'/name)
                with self.assertRaisesRegex(ValueError,'differs from frozen accepted bytes: '+changed):prepare.prepare(bundle,out)
                self.assertFalse(out.exists())
    def test_refuses_overwrite(self):
        with tempfile.TemporaryDirectory(dir=prepare.ROOT/'.work/bounded-scale-ime/issue32') as temporary:
            out=Path(temporary);(out/'preserve').write_text('owned-control')
            with self.assertRaisesRegex(ValueError,'refusing to replace prior evidence'):prepare.prepare(prepare.ROOT/'dist/web',out)
            self.assertEqual((out/'preserve').read_text(),'owned-control')
    def test_refuses_out_of_scope(self):
        with self.assertRaisesRegex(ValueError,'output must stay inside'):prepare.prepare(prepare.ROOT/'dist/web',prepare.ROOT/'dist/forbidden')

if __name__=='__main__':unittest.main()
