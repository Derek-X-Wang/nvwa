use nvwa_core::*;
use serde_json::{Value, json};
use std::{
    path::{Path, PathBuf},
    process::Command,
};
fn cli(args: &[&Path]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_nvwa-cli"))
        .args(args)
        .output()
        .unwrap()
}
fn success(args: &[&Path]) -> Value {
    let output = cli(args);
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    serde_json::from_slice(&output.stdout).unwrap()
}
fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../assets")
}
fn dir() -> PathBuf {
    static NEXT_DIR: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    let sequence = NEXT_DIR.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
    let dir = std::env::temp_dir().join(format!(
        "nvwa-waist-{}-{}-{sequence}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    std::fs::create_dir(&dir).unwrap();
    dir
}
#[test]
fn static_waist_cli_creates_validates_and_describes_finite_scope() {
    let dir = dir();
    let initial = dir.join("initial.json");
    success(&["new-character-waist".as_ref(), &root(), &initial]);
    let doc = SceneDocument::from_json(&std::fs::read_to_string(&initial).unwrap()).unwrap();
    assert_eq!(doc.profile, CharacterProfile::b1_character_waist());
    assert_eq!(doc.character.parameters["waist_circumference"], 0.0);
    assert!(doc.timeline.is_empty());
    success(&["validate".as_ref(), &initial, &root()]);
    let caps = success(&["describe-capabilities".as_ref(), &initial]);
    assert_eq!(caps["parameters"].as_array().unwrap().len(), 11);
    assert_eq!(
        caps["cli_contract"]["waist_circumference"]["supported"],
        true
    );
    assert_eq!(
        caps["cli_contract"]["set_appearance"]["b1_cc0_supported"],
        false
    );
    assert_eq!(
        caps["cli_contract"]["diagnostic_poses"]["timeline_supported"],
        false
    );
    let request = dir.join("request.json");
    std::fs::write(&request, json!({"command_id":"set-waist","expected_revision":doc.revision,"command":{"type":"set_parameters","character_id":doc.character.id,"values":{"waist_circumference":1.0}}}).to_string()).unwrap();
    let edited = dir.join("edited.json");
    success(&["apply".as_ref(), &initial, &request, &edited]);
    let changed = SceneDocument::from_json(&std::fs::read_to_string(&edited).unwrap()).unwrap();
    assert_eq!(changed.character.parameters["waist_circumference"], 1.0);
    std::fs::remove_dir_all(dir).unwrap();
}
#[test]
fn waist_missing_or_corrupt_pair_rejects_without_requiring_new_files_on_old_work() {
    let dir = dir();
    let assets = dir.join("assets");
    let output = dir.join("output.json");
    for version in [B1AssetVersion::V2, B1AssetVersion::V5] {
        let manifest = B1AssetManifest::from_bytes_for(version, version.manifest_bytes()).unwrap();
        let parent = Path::new(version.manifest_path()).parent().unwrap();
        for path in
            std::iter::once("manifest.json").chain(manifest.files.iter().map(|f| f.path.as_str()))
        {
            let dst = assets.join(parent).join(path);
            std::fs::create_dir_all(dst.parent().unwrap()).unwrap();
            std::fs::copy(root().join(parent).join(path), dst).unwrap();
        }
    }
    for name in ["measure-waist-circ-decr", "measure-waist-circ-incr"] {
        let path = assets.join(format!("characters/mpfb-b1-v5/targets/{name}.target"));
        let bytes = std::fs::read(&path).unwrap();
        std::fs::remove_file(&path).unwrap();
        for (expected, replacement) in [
            ("asset_missing", None),
            (
                "asset_hash_mismatch",
                Some({
                    let mut bad = bytes.clone();
                    bad[0] ^= 1;
                    bad
                }),
            ),
        ] {
            if let Some(bytes) = replacement {
                std::fs::write(&path, bytes).unwrap();
            }
            let result = cli(&["new-character-waist".as_ref(), &assets, &output]);
            assert_eq!(result.status.code(), Some(1));
            assert!(result.stdout.is_empty());
            assert_eq!(
                serde_json::from_slice::<Value>(&result.stderr).unwrap()["code"],
                expected
            );
            assert!(!output.exists());
        }
        std::fs::write(path, bytes).unwrap();
    }
    std::fs::remove_dir_all(assets.join("characters/mpfb-b1-v5")).unwrap();
    success(&["new-character".as_ref(), &assets, &output]);
    std::fs::remove_dir_all(dir).unwrap();
}
