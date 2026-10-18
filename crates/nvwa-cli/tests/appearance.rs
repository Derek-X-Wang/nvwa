//! Actual production CLI processes: portable file edits, strict recovery and assets.
use nvwa_core::*;
use serde_json::{Value, json};
use std::{
    path::{Path, PathBuf},
    process::{Command, Output},
};

fn directory(name: &str) -> PathBuf {
    let stamp = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let path = std::env::temp_dir().join(format!(
        "nvwa-appearance-cli-{}-{name}-{stamp}",
        std::process::id()
    ));
    std::fs::create_dir(&path).unwrap();
    path
}
fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../assets")
}
fn cli(args: &[&Path]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_nvwa-cli"))
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
    let error: Value = serde_json::from_slice(&output.stderr).unwrap();
    assert_eq!(error["code"], code, "{error}");
}
fn envelope(id: &str, revision: u64, appearance: CharacterAppearance) -> Value {
    serde_json::to_value(CommandEnvelope {
        command_id: id.into(),
        expected_revision: revision,
        command: nvwa_core::Command::SetAppearance {
            character_id: "character-1".into(),
            appearance,
        },
    })
    .unwrap()
}
fn write(path: &Path, value: &Value) {
    std::fs::write(path, serde_json::to_vec(value).unwrap()).unwrap();
}

#[test]
fn real_cli_discovers_applies_all_independent_roles_undo_redo_retry_saves_and_reopens() {
    let dir = directory("roundtrip");
    let input = dir.join("input.json");
    let output = dir.join("output.json");
    let saved = dir.join("saved.json");
    let requests = dir.join("requests.json");
    success(cli(&["new-b1-motion".as_ref(), &root(), &input]));
    let initial = success(cli(&["inspect".as_ref(), &input]));
    assert_eq!(initial["schema_version"], 4);
    assert_eq!(initial["character"]["appearance"], json!({"type":"none"}));
    let caps = success(cli(&["describe-capabilities".as_ref(), &input]));
    assert_eq!(
        caps["cli_contract"]["work_schema"]["reads"],
        json!([1, 2, 3, 4])
    );
    assert_eq!(
        caps["cli_contract"]["set_appearance"]["b1_cc0_supported"],
        true
    );
    assert!(
        caps["cli_contract"]["command_examples"]
            .as_array()
            .unwrap()
            .iter()
            .any(|e| e["command"]["type"] == "set_appearance")
    );
    for bits in 0..8 {
        let appearance = CharacterAppearance::b1_cc0(bits & 1 != 0, bits & 2 != 0, bits & 4 != 0);
        let first = envelope("selected", 0, appearance.clone());
        let batch = json!([first.clone(),first,{"command_id":"undo","expected_revision":1,"command":{"type":"undo"}},{"command_id":"redo","expected_revision":2,"command":{"type":"redo"}}]);
        write(&requests, &batch);
        let applied = success(cli(&["apply".as_ref(), &input, &requests, &output]));
        assert_eq!(applied[1]["duplicate"], true);
        assert_eq!(applied[1]["revision"], 1);
        success(cli(&["save".as_ref(), &output, &saved]));
        assert_eq!(
            std::fs::read(&output).unwrap(),
            std::fs::read(&saved).unwrap()
        );
        let reopened = success(cli(&["inspect".as_ref(), &saved]));
        assert_eq!(reopened["revision"], 3);
        assert_eq!(
            reopened["character"]["appearance"],
            serde_json::to_value(&appearance).unwrap()
        );
        assert_eq!(reopened["timeline"], initial["timeline"]);
        assert_eq!(
            reopened["character"]["parameters"],
            initial["character"]["parameters"]
        );
        assert_eq!(
            reopened["character"]["diagnostic_pose"],
            initial["character"]["diagnostic_pose"]
        );
        assert_eq!(reopened["stage"], initial["stage"]);
        assert_eq!(
            success(cli(&["validate".as_ref(), &saved, &root()]))["asset_checked"],
            true
        );
    }
    assert_eq!(success(cli(&["inspect".as_ref(), &input])), initial);
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn rejected_commands_and_malformed_legacy_inputs_preserve_input_and_any_output() {
    let dir = directory("atomic");
    let input = dir.join("input.json");
    let bad = dir.join("bad.json");
    let output = dir.join("output.json");
    let requests = dir.join("requests.json");
    let document = SceneDocument::from_profile(
        CharacterProfile::from_json(include_str!("../../../assets/character.profile.json"))
            .unwrap(),
    )
    .unwrap();
    std::fs::write(&input, document.to_json().unwrap()).unwrap();
    let before = std::fs::read(&input).unwrap();
    let selected = envelope(
        "appearance",
        1,
        CharacterAppearance::b1_cc0(true, false, false),
    );
    write(
        &requests,
        &json!([{"command_id":"good","expected_revision":0,"command":{"type":"set_scale","character_id":"character-1","scale":1.5}},selected]),
    );
    for existing in [false, true] {
        if existing {
            std::fs::write(&output, b"preserved output").unwrap();
        }
        rejected(
            cli(&["apply".as_ref(), &input, &requests, &output]),
            "unsupported_character_operation",
        );
        assert_eq!(std::fs::read(&input).unwrap(), before);
        if existing {
            assert_eq!(std::fs::read(&output).unwrap(), b"preserved output");
        } else {
            assert!(!output.exists());
        }
    }
    let mut forged = envelope("forged", 0, CharacterAppearance::b1_cc0(true, false, false));
    forged["command"]["appearance"]["asset_set_id"] = json!("untrusted");
    write(&requests, &forged);
    rejected(
        cli(&["apply".as_ref(), &input, &requests, &output]),
        "unsupported_appearance_asset",
    );
    assert_eq!(std::fs::read(&output).unwrap(), b"preserved output");
    for version in [1, 2, 3] {
        let mut legacy: Value = serde_json::from_slice(&before).unwrap();
        legacy["schema_version"] = json!(version);
        legacy["character"]
            .as_object_mut()
            .unwrap()
            .remove("appearance");
        if version < 3 {
            legacy["profile"].as_object_mut().unwrap().remove("backend");
            legacy["character"]
                .as_object_mut()
                .unwrap()
                .remove("diagnostic_pose");
        }
        if version == 1 {
            legacy.as_object_mut().unwrap().remove("stage");
        }
        write(&bad, &legacy);
        success(cli(&["save".as_ref(), &bad, &output]));
        let upgraded = success(cli(&["inspect".as_ref(), &output]));
        assert_eq!(upgraded["schema_version"], 4);
        assert_eq!(upgraded["character"]["appearance"], json!({"type":"none"}));
        let valid = std::fs::read(&output).unwrap();
        for appearance in [Value::Null, json!({"type":"none"})] {
            legacy["character"]["appearance"] = appearance;
            write(&bad, &legacy);
            rejected(cli(&["save".as_ref(), &bad, &output]), "invalid_json");
            assert_eq!(std::fs::read(&output).unwrap(), valid);
        }
    }
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn real_validation_rejects_missing_unselected_role_corrupt_manifest_and_payload() {
    let dir = directory("assets");
    let assets = dir.join("assets");
    let base = assets.join("characters/mpfb-b1-v1");
    std::fs::create_dir_all(&base).unwrap();
    std::fs::write(base.join("manifest.json"), B1_ASSET_MANIFEST_BYTES).unwrap();
    for file in B1AssetManifest::from_bytes(B1_ASSET_MANIFEST_BYTES)
        .unwrap()
        .files
    {
        let target = base.join(&file.path);
        std::fs::create_dir_all(target.parent().unwrap()).unwrap();
        std::fs::copy(root().join("characters/mpfb-b1-v1").join(file.path), target).unwrap();
    }
    let appearance = assets.join("appearances/mpfb-b1-cc0-v1");
    std::fs::create_dir_all(&appearance).unwrap();
    let descriptor = appearance.join("manifest.json");
    std::fs::write(&descriptor, B1_APPEARANCE_MANIFEST_BYTES).unwrap();
    for path in B1AppearanceManifest::from_bytes(B1_APPEARANCE_MANIFEST_BYTES)
        .unwrap()
        .files
        .keys()
    {
        let target = appearance.join(path);
        std::fs::create_dir_all(target.parent().unwrap()).unwrap();
        std::fs::copy(root().join("appearances/mpfb-b1-cc0-v1").join(path), target).unwrap();
    }
    let mut work = SceneDocument::from_profile(CharacterProfile::b1()).unwrap();
    work.character.appearance = CharacterAppearance::b1_cc0(false, true, false);
    let input = dir.join("work.json");
    std::fs::write(&input, work.to_json().unwrap()).unwrap();
    success(cli(&["validate".as_ref(), &input, &assets]));
    let payload = appearance.join("hair/short04/short04.obj");
    let original = std::fs::read(&payload).unwrap();
    std::fs::remove_file(&payload).unwrap();
    rejected(
        cli(&["validate".as_ref(), &input, &assets]),
        "asset_missing",
    );
    let mut corrupt = original.clone();
    corrupt[0] ^= 1;
    std::fs::write(&payload, corrupt).unwrap();
    rejected(
        cli(&["validate".as_ref(), &input, &assets]),
        "asset_hash_mismatch",
    );
    std::fs::write(&payload, original).unwrap();
    let mut corrupt = B1_APPEARANCE_MANIFEST_BYTES.to_vec();
    corrupt[0] ^= 1;
    std::fs::write(&descriptor, corrupt).unwrap();
    rejected(
        cli(&["validate".as_ref(), &input, &assets]),
        "asset_hash_mismatch",
    );
    std::fs::write(&descriptor, B1_APPEARANCE_MANIFEST_BYTES).unwrap();
    success(cli(&["validate".as_ref(), &input, &assets]));
    std::fs::remove_dir_all(dir).unwrap();
}
