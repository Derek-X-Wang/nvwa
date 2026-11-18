use nvwa_core::*;
use serde_json::{Value, json};
use std::{
    path::{Path, PathBuf},
    process::Command,
};

fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../assets")
}
fn run(args: &[&Path]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_nvwa-cli"))
        .args(args)
        .output()
        .unwrap()
}
fn success(args: &[&Path]) -> Value {
    let output = run(args);
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    serde_json::from_slice(&output.stdout).unwrap()
}
fn temp() -> PathBuf {
    static SEQ: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    let path = std::env::temp_dir().join(format!(
        "nvwa-chest-placement-{}-{}",
        std::process::id(),
        SEQ.fetch_add(1, std::sync::atomic::Ordering::Relaxed)
    ));
    std::fs::create_dir(&path).unwrap();
    path
}

#[test]
fn create_validate_discover_edit_and_save_chest_profile() {
    let dir = temp();
    let initial = dir.join("initial.json");
    success(&["new-character-chest-placement".as_ref(), &root(), &initial]);
    let doc = SceneDocument::from_json(&std::fs::read_to_string(&initial).unwrap()).unwrap();
    assert_eq!(
        doc.profile,
        CharacterProfile::b1_character_chest_placement()
    );
    success(&["validate".as_ref(), &initial, &root()]);
    let caps = success(&["describe-capabilities".as_ref(), &initial]);
    assert_eq!(caps["parameters"].as_array().unwrap().len(), 25);
    for area in [
        "leg_shape",
        "upper_body_shape",
        "hip_contour_shape",
        "arm_proportions_shape",
        "chest_placement_shape",
    ] {
        assert_eq!(caps["cli_contract"][area]["supported"], true);
    }
    assert_eq!(
        caps["cli_contract"]["set_appearance"]["b1_cc0_supported"],
        false
    );
    let request = dir.join("request.json");
    std::fs::write(&request, json!({"command_id":"set-chest","expected_revision":doc.revision,"command":{"type":"set_parameters","character_id":doc.character.id,"values":{"breast_spacing":0.5,"breast_vertical_position":-0.5}}}).to_string()).unwrap();
    let changed = dir.join("changed.json");
    success(&["apply".as_ref(), &initial, &request, &changed]);
    let saved = SceneDocument::from_json(&std::fs::read_to_string(&changed).unwrap()).unwrap();
    assert_eq!(saved.character.parameters["breast_spacing"], 0.5);
    assert_eq!(saved.character.parameters["breast_vertical_position"], -0.5);
    success(&["validate".as_ref(), &changed, &root()]);
    #[cfg(feature = "cpu-render")]
    {
        let export = caps["cpu_render"].clone();
        assert_eq!(export["current_work_supported"], true);
        assert!(
            export["profiles"]
                .as_array()
                .unwrap()
                .iter()
                .any(|v| v == "nvwa-mpfb-b1-chest-placement-v1")
        );
    }
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn missing_new_target_rejects_without_harming_v9() {
    let dir = temp();
    let assets = dir.join("assets");
    for version in [B1AssetVersion::V9, B1AssetVersion::V10] {
        let manifest = B1AssetManifest::from_bytes_for(version, version.manifest_bytes()).unwrap();
        let parent = Path::new(version.manifest_path()).parent().unwrap();
        for path in
            std::iter::once("manifest.json").chain(manifest.files.iter().map(|f| f.path.as_str()))
        {
            let dest = assets.join(parent).join(path);
            std::fs::create_dir_all(dest.parent().unwrap()).unwrap();
            std::fs::copy(root().join(parent).join(path), dest).unwrap();
        }
    }
    std::fs::remove_file(assets.join("characters/mpfb-b1-v10/targets/breast-trans-up.target"))
        .unwrap();
    let rejected = dir.join("rejected.json");
    let output = run(&["new-character-chest-placement".as_ref(), &assets, &rejected]);
    assert_eq!(output.status.code(), Some(1));
    assert_eq!(
        serde_json::from_slice::<Value>(&output.stderr).unwrap()["code"],
        "asset_missing"
    );
    assert!(!rejected.exists());
    success(&[
        "new-character-arm-proportions".as_ref(),
        &assets,
        &dir.join("previous.json"),
    ]);
    std::fs::remove_dir_all(dir).unwrap();
}
