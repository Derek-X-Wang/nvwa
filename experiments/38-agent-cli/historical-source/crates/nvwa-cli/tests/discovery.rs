//! Synthetic real-binary contract checks, separate from the adaptive agent run.
use nvwa_core::{CharacterProfile, SceneDocument};
use serde_json::{Value, json};
use std::{path::PathBuf, process::Command};

fn cli(args: &[&std::path::Path]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_nvwa-cli"))
        .args(args)
        .output()
        .expect("run production CLI binary")
}

fn setup(name: &str) -> (PathBuf, PathBuf) {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let dir = std::env::temp_dir().join(format!("nvwa-discovery-{}-{name}", std::process::id()));
    std::fs::create_dir_all(&dir).expect("test directory");
    let mut document = SceneDocument::from_profile(
        CharacterProfile::from_json(
            &std::fs::read_to_string(root.join("assets/character.profile.json")).expect("profile"),
        )
        .expect("valid profile"),
    )
    .expect("new work");
    // Discovery must reflect the supplied work rather than the repository fixture.
    document.character.id = "custom-character".into();
    document.revision = 23;
    let input = dir.join("input.json");
    std::fs::write(&input, document.to_json().expect("document JSON")).expect("input");
    (dir, input)
}

#[test]
fn discovered_examples_execute_and_keep_existing_profile_contract() {
    let (dir, input) = setup("examples");
    let output = cli(&["describe-capabilities".as_ref(), &input]);
    assert!(output.status.success());
    assert!(output.stderr.is_empty());
    let caps: Value = serde_json::from_slice(&output.stdout).expect("capabilities JSON");
    let input_json: Value = serde_json::from_slice(&std::fs::read(&input).unwrap()).unwrap();
    for (key, expected) in input_json["profile"].as_object().unwrap() {
        assert_eq!(&caps[key], expected, "existing profile key {key}");
    }
    assert_eq!(caps["document_revision"], 23);
    assert_eq!(caps["character_id"], "custom-character");
    assert_eq!(caps["editor_retention"]["session_local"], true);
    assert_eq!(caps["cli_contract"]["schema_version"], 1);
    assert_eq!(
        caps["cli_contract"]["input"]["max_json_bytes"],
        nvwa_core::MAX_JSON_BYTES
    );
    let mut examples = caps["cli_contract"]["command_examples"]
        .as_array()
        .expect("command examples")
        .clone();
    let kinds: Vec<_> = examples
        .iter()
        .map(|e| e["command"]["type"].as_str().unwrap())
        .collect();
    assert_eq!(
        kinds,
        [
            "set_parameters",
            "set_scale",
            "set_timeline",
            "undo",
            "redo"
        ]
    );
    for (index, envelope) in examples.iter_mut().enumerate() {
        assert_eq!(envelope["expected_revision"], 23);
        envelope["expected_revision"] = json!(23 + index);
    }
    let requests = dir.join("discovered-commands.json");
    let saved = dir.join("saved.json");
    std::fs::write(&requests, serde_json::to_vec(&examples).unwrap()).unwrap();
    let applied = cli(&["apply".as_ref(), &input, &requests, &saved]);
    assert!(
        applied.status.success(),
        "{}",
        String::from_utf8_lossy(&applied.stderr)
    );
    assert!(applied.stderr.is_empty());
    let results: Value = serde_json::from_slice(&applied.stdout).unwrap();
    assert_eq!(results.as_array().unwrap().len(), 5);
    let loaded: Value = serde_json::from_slice(&std::fs::read(&saved).unwrap()).unwrap();
    assert_eq!(loaded["revision"], 28);
    assert_eq!(loaded["character"], input_json["character"]);
    assert_eq!(loaded["timeline"], input_json["timeline"]);
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn stale_second_envelope_is_atomic_and_correctable_after_inspection() {
    let (dir, input) = setup("recovery");
    let before = std::fs::read(&input).unwrap();
    let requests = dir.join("commands.json");
    let saved = dir.join("output.json");
    let mut batch = json!([
        {"command_id":"first","expected_revision":23,"command":{"type":"set_parameters","character_id":"custom-character","values":{"jaw_width":0.42}}},
        {"command_id":"stale","expected_revision":23,"command":{"type":"set_parameters","character_id":"custom-character","values":{"smile":0.2}}}
    ]);
    std::fs::write(&requests, serde_json::to_vec(&batch).unwrap()).unwrap();
    for existing_output in [false, true] {
        if existing_output {
            std::fs::write(&saved, &before).unwrap();
        }
        let failed = cli(&["apply".as_ref(), &input, &requests, &saved]);
        assert_eq!(failed.status.code(), Some(1));
        assert!(failed.stdout.is_empty());
        let error: Value = serde_json::from_slice(&failed.stderr).unwrap();
        assert_eq!(error["code"], "revision_conflict");
        assert!(
            error["message"]
                .as_str()
                .unwrap()
                .contains("current revision is 24")
        );
        assert_eq!(std::fs::read(&input).unwrap(), before);
        if existing_output {
            assert_eq!(std::fs::read(&saved).unwrap(), before);
        } else {
            assert!(!saved.exists());
        }
    }
    let inspected = cli(&["inspect".as_ref(), &input]);
    assert!(inspected.status.success());
    let actual: Value = serde_json::from_slice(&inspected.stdout).unwrap();
    assert_eq!(
        actual["revision"], 23,
        "failed batch did not persist its first command"
    );
    batch[0]["expected_revision"] = actual["revision"].clone();
    batch[1]["expected_revision"] = json!(actual["revision"].as_u64().unwrap() + 1);
    std::fs::write(&requests, serde_json::to_vec(&batch).unwrap()).unwrap();
    let corrected = cli(&["apply".as_ref(), &input, &requests, &saved]);
    assert!(
        corrected.status.success(),
        "{}",
        String::from_utf8_lossy(&corrected.stderr)
    );
    let loaded: Value = serde_json::from_slice(&std::fs::read(&saved).unwrap()).unwrap();
    assert_eq!(loaded["revision"], 25);
    assert_eq!(loaded["character"]["parameters"]["jaw_width"], json!(0.42));
    assert_eq!(loaded["character"]["parameters"]["smile"], json!(0.2));
    assert_eq!(std::fs::read(&input).unwrap(), before);
    // A new apply opens a fresh session: previous undo history is unavailable.
    std::fs::write(
        &requests,
        r#"{"command_id":"undo-later","expected_revision":25,"command":{"type":"undo"}}"#,
    )
    .unwrap();
    let undone = dir.join("undone.json");
    let undo = cli(&["apply".as_ref(), &saved, &requests, &undone]);
    assert_eq!(undo.status.code(), Some(1));
    assert!(undo.stdout.is_empty());
    let error: Value = serde_json::from_slice(&undo.stderr).unwrap();
    assert_eq!(error["code"], "nothing_to_undo");
    assert!(!undone.exists());
    std::fs::remove_dir_all(dir).unwrap();
}
