//! Real binary checks for the eight-parameter Work and exact immutable asset sets.
use nvwa_core::*;
use serde_json::{Value, json};
use std::{
    path::{Path, PathBuf},
    process::{Command as Process, Output},
};
fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../assets")
}
fn directory(name: &str) -> PathBuf {
    let nonce = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let dir = std::env::temp_dir().join(format!(
        "nvwa-character-{}-{nonce}-{name}",
        std::process::id()
    ));
    std::fs::create_dir(&dir).unwrap();
    dir
}
fn cli(args: &[&Path]) -> Output {
    Process::new(env!("CARGO_BIN_EXE_nvwa-cli"))
        .args(args)
        .output()
        .unwrap()
}
fn success(output: Output) -> Value {
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(output.stderr.is_empty());
    serde_json::from_slice(&output.stdout).unwrap()
}
fn rejected(output: Output, code: &str) {
    assert_eq!(output.status.code(), Some(1));
    assert!(output.stdout.is_empty());
    let value: Value = serde_json::from_slice(&output.stderr).unwrap();
    assert_eq!(value["code"], code, "{value}");
}
#[test]
fn real_cli_creates_discovers_edits_saves_and_validates_same_eight_parameter_work() {
    let help = cli(&["help".as_ref()]);
    assert!(help.status.success());
    assert!(
        String::from_utf8(help.stdout)
            .unwrap()
            .contains("new-character <asset-root> <scene.json> (eight shape parameters)")
    );
    let dir = directory("exchange");
    let initial = dir.join("initial.json");
    let edited = dir.join("edited.json");
    let saved = dir.join("saved.json");
    let request = dir.join("commands.json");
    success(cli(&["new-character".as_ref(), &root(), &initial]));
    let doc = SceneDocument::from_json(&std::fs::read_to_string(&initial).unwrap()).unwrap();
    assert_eq!(doc.profile, CharacterProfile::b1_character());
    assert_eq!(doc.character.parameters.len(), 8);
    assert_eq!(doc.schema_version, 4);
    let caps = success(cli(&["describe-capabilities".as_ref(), &initial]));
    assert_eq!(caps["parameters"].as_array().unwrap().len(), 8);
    assert_eq!(
        caps["cli_contract"]["diagnostic_poses"]["targets"]
            .as_object()
            .unwrap()
            .len(),
        8
    );
    assert_eq!(caps["cli_contract"]["set_appearance"]["schema_version"], 2);
    assert_eq!(
        caps["cli_contract"]["set_appearance"]["asset_set_id"],
        B1_V2_APPEARANCE_ID
    );
    assert_eq!(
        caps["cli_contract"]["set_appearance"]["asset_set_sha256"],
        B1_V2_APPEARANCE_MANIFEST_SHA256
    );
    let selection =
        CharacterAppearance::b1_cc0_for(&doc.profile.backend, true, true, true).unwrap();
    let values: std::collections::BTreeMap<_, _> = B1_PARAMETER_TARGETS
        .into_iter()
        .enumerate()
        .map(|(i, t)| (t.id, if i % 2 == 0 { -1.0 } else { 1.0 }))
        .collect();
    let batch = json!([
        {"command_id":"eight","expected_revision":0,"command":{"type":"set_parameters","character_id":doc.character.id,"values":values}},
        {"command_id":"appearance","expected_revision":1,"command":{"type":"set_appearance","character_id":doc.character.id,"appearance":selection}},
        {"command_id":"undo","expected_revision":2,"command":{"type":"undo"}},
        {"command_id":"redo","expected_revision":3,"command":{"type":"redo"}}
    ]);
    std::fs::write(&request, serde_json::to_vec(&batch).unwrap()).unwrap();
    success(cli(&["apply".as_ref(), &initial, &request, &edited]));
    success(cli(&["validate".as_ref(), &edited, &root()]));
    success(cli(&["save".as_ref(), &edited, &saved]));
    assert_eq!(
        std::fs::read(&edited).unwrap(),
        std::fs::read(&saved).unwrap()
    );
    let actual = SceneDocument::from_json(&std::fs::read_to_string(&saved).unwrap()).unwrap();
    assert_eq!(actual.revision, 4);
    assert_eq!(actual.character.appearance, selection);
    for (id, expected) in values {
        assert_eq!(actual.character.parameters[id], expected);
    }
    // Same commands preserve legacy constructors and their two-parameter catalogue.
    for (verb, expected) in [
        ("new-b1", CharacterProfile::b1()),
        ("new-b1-motion", CharacterProfile::b1_motion()),
    ] {
        let path = dir.join(format!("{verb}.json"));
        success(cli(&[verb.as_ref(), &root(), &path]));
        assert_eq!(
            SceneDocument::from_json(&std::fs::read_to_string(path).unwrap())
                .unwrap()
                .profile,
            expected
        );
    }
    std::fs::remove_dir_all(dir).unwrap();
}
#[test]
fn every_extension_target_is_authenticated_before_creation_and_legacy_needs_none() {
    let dir = directory("bad-assets");
    let assets = dir.join("assets");
    let output = dir.join("out.json");
    for version in [B1AssetVersion::V1, B1AssetVersion::V2] {
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
    for targets in &B1_PARAMETER_TARGETS[2..] {
        for name in [targets.decrease, targets.increase] {
            let path = assets.join(format!("characters/mpfb-b1-v2/targets/{name}.target"));
            let bytes = std::fs::read(&path).unwrap();
            std::fs::remove_file(&path).unwrap();
            rejected(
                cli(&["new-character".as_ref(), &assets, &output]),
                "asset_missing",
            );
            assert!(!output.exists());
            let mut bad = bytes.clone();
            bad[0] ^= 1;
            std::fs::write(&path, bad).unwrap();
            rejected(
                cli(&["new-character".as_ref(), &assets, &output]),
                "asset_hash_mismatch",
            );
            assert!(!output.exists());
            std::fs::write(&path, bytes).unwrap();
        }
    }
    std::fs::remove_dir_all(assets.join("characters/mpfb-b1-v2")).unwrap();
    success(cli(&["new-b1-motion".as_ref(), &assets, &output]));
    assert_eq!(
        SceneDocument::from_json(&std::fs::read_to_string(output).unwrap())
            .unwrap()
            .profile,
        CharacterProfile::b1_motion()
    );
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn validation_discovery_and_missing_root_wording_cover_both_selected_base_versions() {
    let dir = directory("validation-wording");
    let contract = "b1_validate_requires_explicit_asset_root_and_authenticates_exact_selected_base_and_appearance_manifests_and_all_their_bounded_payloads_glb_asset_root_optional";
    let message = "B1 validation requires validate <work.json> <asset-root> to authenticate all payloads of the selected base and appearance";
    for (verb, version, count) in [
        ("new-b1-motion", B1AssetVersion::V1, 13),
        ("new-character", B1AssetVersion::V2, 25),
    ] {
        let input = dir.join(format!("{verb}.json"));
        success(cli(&[verb.as_ref(), &root(), &input]));
        let caps = success(cli(&["describe-capabilities".as_ref(), &input]));
        assert_eq!(caps["cli_contract"]["asset_validation"], contract);
        assert_eq!(caps["backend"]["asset_id"], version.asset_id());
        let descriptor =
            B1AssetManifest::from_bytes_for(version, version.manifest_bytes()).unwrap();
        assert_eq!(descriptor.files.len(), count);
        let failed = cli(&["validate".as_ref(), &input]);
        assert_eq!(failed.status.code(), Some(1));
        assert!(failed.stdout.is_empty());
        let error: Value = serde_json::from_slice(&failed.stderr).unwrap();
        assert_eq!(error["code"], "asset_root_required");
        assert_eq!(error["message"], message);
        success(cli(&["validate".as_ref(), &input, &root()]));
    }
    std::fs::remove_dir_all(dir).unwrap();
}
