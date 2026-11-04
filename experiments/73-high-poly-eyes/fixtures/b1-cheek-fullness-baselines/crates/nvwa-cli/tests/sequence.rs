use nvwa_core::SceneDocument;
use std::{path::PathBuf, process::Command as Process};

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

fn output_dir(name: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!("nvwa-cli-{}-{name}", std::process::id()));
    std::fs::create_dir_all(&dir).expect("create test-owned directory");
    dir
}

#[test]
fn cli_applies_and_round_trips_the_m1_sequence() {
    let root = root();
    let examples = root.join("examples");
    let expected = SceneDocument::from_json(
        &std::fs::read_to_string(examples.join("m1-sequence.nvwa.json"))
            .expect("M1 sequence fixture"),
    )
    .expect("valid M1 sequence");
    let dir = output_dir("sequence");
    let applied = dir.join("applied.nvwa.json");
    let saved = dir.join("saved.nvwa.json");

    let output = Process::new(env!("CARGO_BIN_EXE_nvwa-cli"))
        .arg("apply")
        .arg(examples.join("default.nvwa.json"))
        .arg(examples.join("m1-commands.json"))
        .arg(&applied)
        .output()
        .expect("run actual CLI apply");
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let applied_document =
        SceneDocument::from_json(&std::fs::read_to_string(&applied).expect("applied document"))
            .expect("valid applied document");
    assert_eq!(applied_document, expected);

    let validation = Process::new(env!("CARGO_BIN_EXE_nvwa-cli"))
        .arg("validate")
        .arg(&applied)
        .arg(root.join("assets"))
        .output()
        .expect("validate against repository assets");
    assert!(
        validation.status.success(),
        "{}",
        String::from_utf8_lossy(&validation.stderr)
    );

    let save = Process::new(env!("CARGO_BIN_EXE_nvwa-cli"))
        .arg("save")
        .arg(&applied)
        .arg(&saved)
        .output()
        .expect("run actual CLI save");
    assert!(
        save.status.success(),
        "{}",
        String::from_utf8_lossy(&save.stderr)
    );
    let reloaded =
        SceneDocument::from_json(&std::fs::read_to_string(&saved).expect("saved document"))
            .expect("reload saved document");
    assert_eq!(reloaded.character, expected.character);
    assert_eq!(reloaded.timeline, expected.timeline);
    assert_eq!(reloaded.revision, expected.revision);
    assert_eq!(reloaded, expected);
}

#[test]
fn failed_cli_batch_preserves_input_and_existing_work() {
    let examples = root().join("examples");
    let dir = output_dir("failed-sequence");
    let input = dir.join("input.nvwa.json");
    let commands = dir.join("commands.json");
    let saved = dir.join("existing-work.nvwa.json");
    std::fs::copy(examples.join("default.nvwa.json"), &input).expect("copy input work");
    std::fs::copy(examples.join("m1-sequence.nvwa.json"), &saved).expect("copy existing work");
    let input_before = std::fs::read(&input).expect("input bytes");
    let saved_before = std::fs::read(&saved).expect("existing work bytes");
    std::fs::write(
        &commands,
        r#"[
          {"command_id":"valid-first","expected_revision":0,"command":{"type":"set_parameters","character_id":"character-1","values":{"smile":0.5}}},
          {"command_id":"invalid-second","expected_revision":1,"command":{"type":"set_parameters","character_id":"character-1","values":{"smile":99.0}}}
        ]"#,
    )
    .expect("write failing batch");

    let output = Process::new(env!("CARGO_BIN_EXE_nvwa-cli"))
        .arg("apply")
        .arg(&input)
        .arg(&commands)
        .arg(&saved)
        .output()
        .expect("run actual CLI apply");
    assert!(!output.status.success());
    assert_eq!(std::fs::read(&input).expect("input bytes"), input_before);
    assert_eq!(
        std::fs::read(&saved).expect("existing work bytes"),
        saved_before
    );
    let error: serde_json::Value =
        serde_json::from_slice(&output.stderr).expect("structured CLI error");
    assert_eq!(error["code"], "out_of_range");
}
