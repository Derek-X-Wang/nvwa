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
    let dir = std::env::temp_dir().join(format!(
        "nvwa-contour-{}-{}",
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
fn explicit_contour_cli_creation_discovery_history_appearance_and_exchange() {
    let dir = dir();
    let initial = dir.join("initial.json");
    let request = dir.join("request.json");
    let edited = dir.join("edited.json");
    let saved = dir.join("saved.json");
    let help = cli(&["help".as_ref()]);
    assert!(
        String::from_utf8(help.stdout)
            .unwrap()
            .contains("new-character-contour")
    );
    success(&["new-character-contour".as_ref(), &root(), &initial]);
    let doc = SceneDocument::from_json(&std::fs::read_to_string(&initial).unwrap()).unwrap();
    assert_eq!(doc.profile, CharacterProfile::b1_character_contour());
    assert_eq!(doc.character.parameters["cheek_fullness"], 0.0);
    assert!(matches!(
        doc.character.appearance,
        CharacterAppearance::None
    ));
    assert_eq!(doc.timeline.len(), 1);
    assert!(doc.timeline[0].looping);
    assert_eq!(doc.timeline[0].duration_seconds, 4.0);
    let caps = success(&["describe-capabilities".as_ref(), &initial]);
    assert_eq!(caps["parameters"].as_array().unwrap().len(), 9);
    assert_eq!(caps["cli_contract"]["cheek_fullness"]["supported"], true);
    assert_eq!(caps["cli_contract"]["set_appearance"]["schema_version"], 3);
    assert_eq!(
        caps["cli_contract"]["set_appearance"]["compatible_sets"]
            .as_array()
            .unwrap()
            .len(),
        2
    );
    let appearance = CharacterAppearance::b1_cc0_for_set(
        &doc.profile.backend,
        B1AppearanceSet::V3Short01,
        true,
        true,
        true,
    )
    .unwrap();
    let batch = json!([
        {"command_id":"shape","expected_revision":0,"command":{"type":"set_parameters","character_id":doc.character.id,"values":{"cheek_fullness":-0.35,"head_width":0.2}}},
        {"command_id":"look","expected_revision":1,"command":{"type":"set_appearance","character_id":doc.character.id,"appearance":appearance}},
        {"command_id":"undo","expected_revision":2,"command":{"type":"undo"}},
        {"command_id":"redo","expected_revision":3,"command":{"type":"redo"}}
    ]);
    std::fs::write(&request, serde_json::to_vec(&batch).unwrap()).unwrap();
    success(&["apply".as_ref(), &initial, &request, &edited]);
    success(&["validate".as_ref(), &edited, &root()]);
    success(&["save".as_ref(), &edited, &saved]);
    assert_eq!(
        std::fs::read(&edited).unwrap(),
        std::fs::read(&saved).unwrap()
    );
    let actual = SceneDocument::from_json(&std::fs::read_to_string(&saved).unwrap()).unwrap();
    assert_eq!(actual.character.parameters["cheek_fullness"], -0.35);
    assert_eq!(actual.character.appearance, appearance);
    success(&["new-character".as_ref(), &root(), &initial]);
    let old = SceneDocument::from_json(&std::fs::read_to_string(&initial).unwrap()).unwrap();
    assert_eq!(old.profile, CharacterProfile::b1_character());
    assert!(!old.character.parameters.contains_key("cheek_fullness"));
    std::fs::remove_dir_all(dir).unwrap();
}
#[test]
fn contour_creation_rejects_each_missing_or_corrupt_cheek_target_and_leaves_old_constructor_usable()
{
    let dir = dir();
    let assets = dir.join("assets");
    let output = dir.join("output.json");
    for version in [B1AssetVersion::V2, B1AssetVersion::V3] {
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
    for name in ["cheek-volume-bilateral-decr", "cheek-volume-bilateral-incr"] {
        let path = assets.join(format!("characters/mpfb-b1-v3/targets/{name}.target"));
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
            let result = cli(&["new-character-contour".as_ref(), &assets, &output]);
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
    std::fs::remove_dir_all(assets.join("characters/mpfb-b1-v3")).unwrap();
    success(&["new-character".as_ref(), &assets, &output]);
    std::fs::remove_dir_all(dir).unwrap();
}
