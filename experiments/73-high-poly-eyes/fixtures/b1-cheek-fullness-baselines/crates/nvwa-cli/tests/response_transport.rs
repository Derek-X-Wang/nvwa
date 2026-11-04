//! Production response transport is separate from committing an output work.
use nvwa_core::SceneDocument;
use serde_json::Value;
use std::{path::PathBuf, process::Command};

#[test]
fn closed_stdout_reports_transport_error_after_save_without_panicking() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let dir = std::env::temp_dir().join(format!("nvwa-transport-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let input = dir.join("input.json");
    std::fs::copy(root.join("examples/default.nvwa.json"), &input).unwrap();
    let original = std::fs::read(&input).unwrap();
    let requests = dir.join("commands.json");
    std::fs::write(&requests, r#"{"command_id":"transport-edit","expected_revision":0,"command":{"type":"set_parameters","character_id":"character-1","values":{"jaw_width":0.42}}}"#).unwrap();
    for verb in [
        "new",
        "apply",
        "save",
        "inspect",
        "describe-capabilities",
        "validate",
        "help",
    ] {
        let output_path = dir.join(format!("{verb}-output.json"));
        let mut command = Command::new(env!("CARGO_BIN_EXE_nvwa-cli"));
        command.arg(verb);
        match verb {
            "new" => {
                command
                    .arg(root.join("assets/character.profile.json"))
                    .arg(&output_path);
            }
            "apply" => {
                command.arg(&input).arg(&requests).arg(&output_path);
            }
            "save" => {
                command.arg(&input).arg(&output_path);
            }
            "help" => {}
            _ => {
                command.arg(&input);
            }
        }
        let (reader, writer) = std::io::pipe().expect("actual OS stdout pipe");
        drop(reader); // No consumer exists before the child can produce a response.
        let output = command.stdout(writer).output().expect("run actual CLI");
        assert_eq!(
            output.status.code(),
            Some(1),
            "{verb}: {}",
            String::from_utf8_lossy(&output.stderr)
        );
        let error: Value =
            serde_json::from_slice(&output.stderr).expect("structured transport error");
        assert_eq!(error["code"], "stdout_write", "{verb}");
        assert!(error["message"].as_str().unwrap().contains("inspect"));
        assert!(!String::from_utf8_lossy(&output.stderr).contains("panicked"));
        assert_eq!(
            std::fs::read(&input).unwrap(),
            original,
            "{verb}: input preserved"
        );
        if ["new", "apply", "save"].contains(&verb) {
            let saved =
                SceneDocument::from_json(&std::fs::read_to_string(&output_path).unwrap()).unwrap();
            assert_eq!(saved.revision, if verb == "apply" { 1 } else { 0 });
            if verb == "apply" {
                assert_eq!(saved.character.parameters["jaw_width"], 0.42);
            }
        } else {
            assert!(!output_path.exists());
        }
    }
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn closed_stderr_does_not_turn_a_domain_failure_into_a_panic() {
    let (reader, writer) = std::io::pipe().unwrap();
    drop(reader);
    let output = Command::new(env!("CARGO_BIN_EXE_nvwa-cli"))
        .arg("unknown-command")
        .stderr(writer)
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(1));
    assert!(output.stdout.is_empty());
}
