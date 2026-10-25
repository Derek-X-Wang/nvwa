"""Exact-copy controls for the retained numerical and controller implementation."""
from pathlib import Path
import unittest
EXP=Path(__file__).resolve().parent
OLD=EXP.parent/'86-hairline-geometry'
RETAINED=Path('/Users/derekxwang/.codex/work-products/nvwa/2026-10-19-source-export-followup/retained-hairline-export79/validator-root/experiments/78-hairline-local-quality')

class Isolation(unittest.TestCase):
    def test_numeric_controller_locks_and_fixture_bytes(self):
        self.assertEqual((EXP/'src/geometry.rs').read_bytes(),(OLD/'src/geometry.rs').read_bytes())
        self.assertEqual((EXP/'cpu_replay.py').read_bytes(),(RETAINED/'cpu_replay.py').read_bytes())
        for name in ['lib.rs','protocol_tests.rs']:
            expected=(OLD/'src'/name).read_text().replace('BFrontArch','BShort03').replace('b_front_arch','b_short03').replace('mod deform;\n','')
            self.assertEqual((EXP/'src'/name).read_text(),expected)
        for name in ['Cargo.toml','Cargo.lock']:
            self.assertEqual((EXP/name).read_bytes(),(OLD/name).read_bytes())
        for p in (OLD/'works').iterdir():self.assertEqual((EXP/'works'/p.name).read_bytes(),p.read_bytes(),p.name)
    def test_restore_and_apply_mechanisms_are_exact(self):
        actual=(EXP/'src/candidate.rs').read_text()
        original=(OLD/'src/candidate.rs').read_text().replace('BFrontArch','BShort03')
        for start,end in [('    pub fn restore(', '    pub fn clear('),('    fn apply(', '\n#[cfg(test)]')]:
            self.assertEqual(actual[actual.index(start):actual.index(end,actual.index(start))],original[original.index(start):original.index(end,original.index(start))])
        self.assertNotIn('front_arch',actual);self.assertNotIn('mod deform;', (EXP/'src/lib.rs').read_text())
        self.assertIn('let b = short03_fitted(&cage, &weights)?;',actual)
        self.assertIn('let (b_image, b_image_pixels) = short03_image()?;',actual)
        self.assertIn('image_policy(pixels) != image_policy(&b_image)',actual)
    def test_only_b_diagnostic_source_map_changes(self):
        actual=(EXP/'src/diagnostic.rs').read_text()
        expected=(OLD/'src/diagnostic.rs').read_text().replace('BFrontArch','BShort03').replace('b_front_arch','b_short03')
        expected=expected.replace('''                    } else {
                        include_str!("../works/a-short04-source-map.json")''','''                    } else {
                        include_str!("../works/b-short03-source-map.json")''')
        self.assertEqual(actual,expected)

if __name__=='__main__':unittest.main()
