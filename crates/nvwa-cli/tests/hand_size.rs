use nvwa_core::*;
use serde_json::{Value, json};
use std::{
    path::{Path, PathBuf},
    process::Command,
};

fn assets() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../assets")
}
fn temp() -> PathBuf {
    static SEQ: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    let p = std::env::temp_dir().join(format!(
        "nvwa-hand-size-{}-{}",
        std::process::id(),
        SEQ.fetch_add(1, std::sync::atomic::Ordering::Relaxed)
    ));
    std::fs::create_dir(&p).unwrap();
    p
}
fn run(args: &[&Path]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_nvwa-cli"))
        .args(args)
        .output()
        .unwrap()
}
fn success(args: &[&Path]) -> Value {
    let out = run(args);
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    serde_json::from_slice(&out.stdout).unwrap()
}

#[test]
fn create_discover_edit_validate_and_preserve_v9() {
    let dir = temp();
    let initial = dir.join("initial.json");
    success(&["new-character-hand-size".as_ref(), &assets(), &initial]);
    let doc = SceneDocument::from_json(&std::fs::read_to_string(&initial).unwrap()).unwrap();
    assert_eq!(doc.profile, CharacterProfile::b1_character_hand_size());
    success(&["validate".as_ref(), &initial, &assets()]);
    let caps = success(&["describe-capabilities".as_ref(), &initial]);
    assert_eq!(caps["parameters"].as_array().unwrap().len(), 25);
    assert_eq!(caps["cli_contract"]["hand_size_shape"]["supported"], true);
    assert_eq!(
        caps["cli_contract"]["arm_proportions_shape"]["supported"],
        true
    );
    #[cfg(feature = "cpu-render")]
    assert!(
        caps["cpu_render"]["profiles"]
            .as_array()
            .unwrap()
            .iter()
            .any(|x| x == "nvwa-mpfb-b1-hand-size-v1")
    );
    let request = dir.join("request.json");
    std::fs::write(
        &request,
        json!({"command_id":"set-hands","expected_revision":doc.revision,
        "command":{"type":"set_parameters","character_id":doc.character.id,
        "values":{"left_hand_size":-0.75,"right_hand_size":0.5}}})
        .to_string(),
    )
    .unwrap();
    let changed = dir.join("changed.json");
    success(&["apply".as_ref(), &initial, &request, &changed]);
    let saved = SceneDocument::from_json(&std::fs::read_to_string(&changed).unwrap()).unwrap();
    assert_eq!(saved.character.parameters["left_hand_size"], -0.75);
    assert_eq!(saved.character.parameters["right_hand_size"], 0.5);
    success(&["validate".as_ref(), &changed, &assets()]);
    let old = dir.join("old.json");
    success(&["new-character-arm-proportions".as_ref(), &assets(), &old]);
    success(&["validate".as_ref(), &old, &assets()]);
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn missing_new_hand_target_rejects_without_affecting_v9() {
    let dir = temp();
    let root = dir.join("assets");
    for version in [B1AssetVersion::V9, B1AssetVersion::V11] {
        let manifest = B1AssetManifest::from_bytes_for(version, version.manifest_bytes()).unwrap();
        let parent = Path::new(version.manifest_path()).parent().unwrap();
        for path in
            std::iter::once("manifest.json").chain(manifest.files.iter().map(|f| f.path.as_str()))
        {
            let dest = root.join(parent).join(path);
            std::fs::create_dir_all(dest.parent().unwrap()).unwrap();
            std::fs::copy(assets().join(parent).join(path), dest).unwrap();
        }
    }
    std::fs::remove_file(root.join("characters/mpfb-b1-v11/targets/l-hand-scale-incr.target"))
        .unwrap();
    let rejected = dir.join("rejected.json");
    let out = run(&["new-character-hand-size".as_ref(), &root, &rejected]);
    assert_eq!(out.status.code(), Some(1));
    assert_eq!(
        serde_json::from_slice::<Value>(&out.stderr).unwrap()["code"],
        "asset_missing"
    );
    assert!(!rejected.exists());
    success(&[
        "new-character-arm-proportions".as_ref(),
        &root,
        &dir.join("v9.json"),
    ]);
    std::fs::remove_dir_all(dir).unwrap();
}
