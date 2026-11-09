use nvwa_core::*;
use serde_json::{Value, json};
use std::{
    path::{Path, PathBuf},
    process::Command,
};

fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../assets")
}
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
fn dir() -> PathBuf {
    static SEQ: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    let path = std::env::temp_dir().join(format!(
        "nvwa-legs-{}-{}",
        std::process::id(),
        SEQ.fetch_add(1, std::sync::atomic::Ordering::Relaxed)
    ));
    std::fs::create_dir(&path).unwrap();
    path
}

#[test]
fn create_validate_describe_edit_and_save_leg_profile() {
    let temp = dir();
    let initial = temp.join("initial.json");
    success(&["new-character-legs".as_ref(), &root(), &initial]);
    let doc = SceneDocument::from_json(&std::fs::read_to_string(&initial).unwrap()).unwrap();
    assert_eq!(doc.profile, CharacterProfile::b1_character_legs());
    success(&["validate".as_ref(), &initial, &root()]);
    let caps = success(&["describe-capabilities".as_ref(), &initial]);
    assert_eq!(caps["parameters"].as_array().unwrap().len(), 15);
    assert_eq!(caps["cli_contract"]["leg_shape"]["supported"], true);
    assert_eq!(
        caps["cli_contract"]["diagnostic_poses"]["timeline_supported"],
        false
    );
    assert_eq!(
        caps["cli_contract"]["set_appearance"]["b1_cc0_supported"],
        false
    );
    let request = temp.join("request.json");
    std::fs::write(&request, json!({"command_id":"set-legs","expected_revision":doc.revision,"command":{"type":"set_parameters","character_id":doc.character.id,"values":{"thigh_length":0.5,"lower_leg_length":-0.5,"thigh_girth":1.0,"calf_girth":-1.0}}}).to_string()).unwrap();
    let edited = temp.join("edited.json");
    success(&["apply".as_ref(), &initial, &request, &edited]);
    let changed = SceneDocument::from_json(&std::fs::read_to_string(&edited).unwrap()).unwrap();
    assert_eq!(changed.character.parameters["thigh_length"], 0.5);
    assert_eq!(changed.character.parameters["lower_leg_length"], -0.5);
    assert_eq!(changed.character.parameters["thigh_girth"], 1.0);
    assert_eq!(changed.character.parameters["calf_girth"], -1.0);
    success(&["validate".as_ref(), &edited, &root()]);
    std::fs::remove_dir_all(temp).unwrap();
}

#[test]
fn missing_new_target_rejects_without_affecting_old_work() {
    let temp = dir();
    let assets = temp.join("assets");
    for version in [B1AssetVersion::V5, B1AssetVersion::V6] {
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
    let removed = assets.join("characters/mpfb-b1-v6/targets/measure-thigh-circ-incr.target");
    std::fs::remove_file(removed).unwrap();
    let rejected = temp.join("rejected.json");
    let output = cli(&["new-character-legs".as_ref(), &assets, &rejected]);
    assert_eq!(output.status.code(), Some(1));
    assert_eq!(
        serde_json::from_slice::<Value>(&output.stderr).unwrap()["code"],
        "asset_missing"
    );
    assert!(!rejected.exists());
    let previous = temp.join("previous.json");
    success(&["new-character-waist".as_ref(), &assets, &previous]);
    std::fs::remove_dir_all(temp).unwrap();
}
