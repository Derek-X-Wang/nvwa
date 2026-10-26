"""Exact91 copy guards; only two explicit admissions and test hook may differ."""
from pathlib import Path
import unittest
EXP=Path(__file__).resolve().parent
OLD=EXP.parent/'91-hair-short01-ab'
ALLOW='    include_str!("../works/plus-arms-framing160.nvwa.json"),\n    include_str!("../works/plus-knee-framing160.nvwa.json"),\n'
PAIRS='''        (
            include_str!("../works/plus-arms-framing160.nvwa.json"),
            include_str!("../works/reference-plus-framing160.json"),
        ),
        (
            include_str!("../works/plus-knee-framing160.nvwa.json"),
            include_str!("../works/reference-plus-framing160.json"),
        ),
'''
HOOK='\n#[cfg(test)]\n#[path = "framing_source_tests.rs"]\nmod framing_source_tests;\n'
OLD_STEADY='''    capture_variant(&mut app, "steady-b", "b_short01");
    for _ in 0..3 {
        app.update();
        assert!(ready(app.world(), "steady-b"));
    }
'''
NEW_STEADY='''    capture_variant(&mut app, "steady-b", "b_short01");
    let b_arrays = hair_arrays(app.world(), &mesh);
    for _ in 0..3 {
        app.update();
        assert!(ready(app.world(), "steady-b"));
        assert!(
            hair_arrays(app.world(), &mesh) == b_arrays,
            "held real short01 B upload must remain exact and stable"
        );
    }
'''
OLD_B_ASSERT='''    assert_eq!(
        hair_arrays(app.world(), &mesh),
        arrays,
        "alpha-only B must preserve exact A source geometry"
    );
'''
NEW_B_ASSERT='''    // Real short01 B has its own authenticated topology and UV mapping.
    let b_positions: Vec<[f32; 3]> =
        serde_json::from_value(b_arrays["positions"].clone()).unwrap();
    let b_normals: Vec<[f32; 3]> =
        serde_json::from_value(b_arrays["normals"].clone()).unwrap();
    assert_eq!(b_positions.len(), 3177);
    assert_eq!(b_normals.len(), 3177);
    assert!(b_positions.iter().chain(&b_normals).flatten().all(|x| x.is_finite()));
    assert!(b_arrays["positions"] != arrays["positions"], "real B positions must differ from A");
    assert!(b_arrays["normals"] != arrays["normals"], "real B normals must differ from A");
    let source_map = include_str!("../works/b-short01-source-map.json");
    assert_eq!(
        appearance_sha256(source_map.as_bytes()),
        "218b454cd9100c9dcbb725f1aba0bf1a21ad97817b3ef4eb453b2f291de1432c"
    );
    let pinned: Value = serde_json::from_str(source_map).unwrap();
    let actual_uv: Vec<[f32; 2]> = serde_json::from_value(b_arrays["uv"].clone()).unwrap();
    let expected_uv: Vec<[f32; 2]> = serde_json::from_value(pinned["uv_0"].clone()).unwrap();
    let actual_indices: Vec<u32> = serde_json::from_value(b_arrays["indices"].clone()).unwrap();
    let expected_indices: Vec<u32> = serde_json::from_value(pinned["indices"].clone()).unwrap();
    assert!(actual_uv == expected_uv, "B typed-f32 UVs must match authenticated short01 corners");
    assert!(actual_indices == expected_indices, "B corner indices must match authenticated short01");
    let source_pairs = app.world().resource::<Bridge>().frame.as_ref().unwrap()
        ["candidate"]["source_uv_pairs"].clone();
    assert!(source_pairs == pinned["source_uv_pairs"], "B source/UV corner pairs must match short01");
'''
class Isolation(unittest.TestCase):
    def test_numeric_controller_locks_and_fixture_bytes(self):
        for name in ['src/geometry.rs','cpu_replay.py','source_check.py','validate.py','src/source_tests.rs','Cargo.toml','Cargo.lock','index.html','src/bin/studio76.rs','SOURCE.json']:
            self.assertEqual((EXP/name).read_bytes(),(OLD/name).read_bytes(),name)
        protocol=(OLD/'src/protocol_tests.rs').read_text()
        self.assertEqual(protocol.count(OLD_STEADY),1)
        self.assertEqual(protocol.count(OLD_B_ASSERT),1)
        self.assertEqual((EXP/'src/protocol_tests.rs').read_text(),protocol.replace(OLD_STEADY,NEW_STEADY).replace(OLD_B_ASSERT,NEW_B_ASSERT))
        old=(OLD/'src/lib.rs').read_text();needle='''        (
            include_str!("../works/shoulder-rear-baseline-arms.nvwa.json"),
            include_str!("../works/reference-shoulder-rear-baseline-arms.json"),
        ),
'''
        self.assertEqual((EXP/'src/lib.rs').read_text(),old.replace(needle,needle+PAIRS))
        for p in (OLD/'works').iterdir():self.assertEqual((EXP/'works'/p.name).read_bytes(),p.read_bytes(),p.name)
        for p in (OLD/'candidate').rglob('*'):
            if p.is_file():self.assertEqual((EXP/p.relative_to(OLD)).read_bytes(),p.read_bytes(),str(p))
    def test_restore_and_apply_mechanisms_are_exact(self):
        old=(OLD/'src/candidate.rs').read_text();needle='    include_str!("../works/shoulder-rear-baseline-arms.nvwa.json"),\n'
        self.assertEqual((EXP/'src/candidate.rs').read_text(),old.replace(needle,needle+ALLOW)+HOOK)
    def test_only_b_diagnostic_source_map_changes(self):
        self.assertEqual((EXP/'src/diagnostic.rs').read_bytes(),(OLD/'src/diagnostic.rs').read_bytes())
if __name__=='__main__':unittest.main()
