"""Exact-copy controls for the retained numerical and controller implementation."""
from pathlib import Path
import unittest
EXP=Path(__file__).resolve().parent
OLD=EXP.parent/'89-hair-short03-ab'

class Isolation(unittest.TestCase):
    def test_numeric_controller_locks_and_fixture_bytes(self):
        self.assertEqual((EXP/'src/geometry.rs').read_bytes(),(OLD/'src/geometry.rs').read_bytes())
        self.assertEqual((EXP/'cpu_replay.py').read_bytes(),(OLD/'cpu_replay.py').read_bytes())
        for name in ['lib.rs','protocol_tests.rs']:
            expected=(OLD/'src'/name).read_text().replace('BShort03','BShort01').replace('b_short03','b_short01')
            self.assertEqual((EXP/'src'/name).read_text(),expected)
        for name in ['Cargo.toml','Cargo.lock']:
            self.assertEqual((EXP/name).read_bytes(),(OLD/name).read_bytes())
        for p in (OLD/'works').iterdir():
            if p.name!='b-short03-source-map.json':self.assertEqual((EXP/'works'/p.name).read_bytes(),p.read_bytes(),p.name)
    def test_restore_and_apply_mechanisms_are_exact(self):
        actual=(EXP/'src/candidate.rs').read_text()
        original=(OLD/'src/candidate.rs').read_text().replace('BShort03','BShort01')
        for start,end in [('    pub fn restore(', '    pub fn clear('),('    fn apply(', '\n#[cfg(test)]')]:
            self.assertEqual(actual[actual.index(start):actual.index(end,actual.index(start))],original[original.index(start):original.index(end,original.index(start))])
        self.assertNotIn('front_arch',actual);self.assertNotIn('mod deform;', (EXP/'src/lib.rs').read_text())
        self.assertIn('let b = short01_fitted(&cage, &weights)?;',actual)
        self.assertIn('let (b_image, b_image_pixels) = short01_image()?;',actual)
        self.assertIn('image_policy(pixels) != image_policy(&b_image)',actual)
    def test_only_b_diagnostic_source_map_changes(self):
        actual=(EXP/'src/diagnostic.rs').read_text()
        expected=(OLD/'src/diagnostic.rs').read_text().replace('BShort03','BShort01').replace('b_short03','b_short01')
        expected=expected.replace('b-short03-source-map.json','b-short01-source-map.json')
        self.assertEqual(actual,expected)

if __name__=='__main__':unittest.main()
