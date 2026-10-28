use nvwa_core::{CharacterProfile, Command, CommandEnvelope, Editor, SceneDocument, TimelineClip};
use std::{collections::BTreeMap, path::PathBuf, process::Command as Process};

fn output_dir(name: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!("nvwa-cli-{}-{name}", std::process::id()));
    std::fs::create_dir_all(&dir).expect("create test-owned directory");
    dir
}

#[test]
fn typed_ui_and_offline_cli_produce_equivalent_documents() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let profile = CharacterProfile::from_json(
        &std::fs::read_to_string(root.join("assets/character.profile.json")).expect("real profile"),
    )
    .expect("valid profile");
    let initial = SceneDocument::from_profile(profile).expect("default scene");
    let commands = vec![
        CommandEnvelope {
            command_id: "morph-edit".into(),
            expected_revision: 0,
            command: Command::SetParameters {
                character_id: "character-1".into(),
                values: BTreeMap::from([("smile".into(), 0.7), ("jaw_width".into(), 0.4)]),
            },
        },
        CommandEnvelope {
            command_id: "wave-edit".into(),
            expected_revision: 1,
            command: Command::SetTimeline {
                clips: vec![TimelineClip {
                    id: "wave-1".into(),
                    clip_id: "wave".into(),
                    start_seconds: 0.0,
                    duration_seconds: 3.0,
                    speed: 1.0,
                    looping: true,
                }],
            },
        },
        CommandEnvelope {
            command_id: "undo".into(),
            expected_revision: 2,
            command: Command::Undo,
        },
        CommandEnvelope {
            command_id: "redo".into(),
            expected_revision: 3,
            command: Command::Redo,
        },
    ];
    let mut typed = Editor::new(initial.clone()).expect("editor");
    for envelope in commands.iter().cloned() {
        typed.apply(envelope).expect("typed edit");
    }
    let dir = output_dir("equivalence");
    let scene = dir.join("native-saved.json");
    let command_file = dir.join("commands.json");
    let saved = dir.join("web-compatible.json");
    std::fs::write(&scene, initial.to_json().expect("serialize scene")).expect("scene fixture");
    std::fs::write(
        &command_file,
        serde_json::to_string(&commands).expect("serialize commands"),
    )
    .expect("command fixture");
    let output = Process::new(env!("CARGO_BIN_EXE_nvwa-cli"))
        .args(["apply"])
        .arg(&scene)
        .arg(&command_file)
        .arg(&saved)
        .output()
        .expect("run actual CLI");
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let loaded = SceneDocument::from_json(&std::fs::read_to_string(&saved).expect("saved JSON"))
        .expect("reloaded scene");
    assert_eq!(loaded, typed.document().clone());
    let validate = Process::new(env!("CARGO_BIN_EXE_nvwa-cli"))
        .arg("validate")
        .arg(&saved)
        .arg(root.join("assets"))
        .output()
        .expect("validate real asset");
    assert!(
        validate.status.success(),
        "{}",
        String::from_utf8_lossy(&validate.stderr)
    );
}

#[test]
fn failed_batch_does_not_overwrite_existing_output() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let profile = CharacterProfile::from_json(
        &std::fs::read_to_string(root.join("assets/character.profile.json")).expect("profile"),
    )
    .expect("profile parse");
    let dir = output_dir("atomic-output");
    let scene = dir.join("scene.json");
    let commands = dir.join("commands.json");
    let saved = dir.join("existing.json");
    std::fs::write(
        &scene,
        SceneDocument::from_profile(profile)
            .expect("scene")
            .to_json()
            .expect("json"),
    )
    .expect("fixture");
    std::fs::write(&commands,r#"[{"command_id":"ok","expected_revision":0,"command":{"type":"set_scale","character_id":"character-1","scale":1.1}},{"command_id":"bad","expected_revision":1,"command":{"type":"set_parameters","character_id":"character-1","values":{"smile":99}}}]"#).expect("commands");
    std::fs::write(&saved, "preserve existing output").expect("existing output");
    let output = Process::new(env!("CARGO_BIN_EXE_nvwa-cli"))
        .arg("apply")
        .arg(&scene)
        .arg(&commands)
        .arg(&saved)
        .output()
        .expect("CLI");
    assert!(!output.status.success());
    assert_eq!(
        std::fs::read_to_string(&saved).expect("output"),
        "preserve existing output"
    );
    let error: serde_json::Value =
        serde_json::from_slice(&output.stderr).expect("structured error");
    assert_eq!(error["code"], "out_of_range");
}

#[test]
fn cli_rejects_duplicate_map_keys_and_preserves_unrelated_save_sibling() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let profile = root.join("assets/character.profile.json");
    let dir = output_dir("strict-json");
    let scene = dir.join("scene.json");
    let sibling = dir.join("scene.nvwa.json.tmp");
    std::fs::write(&sibling, "unrelated sibling").expect("sibling fixture");
    let created = Process::new(env!("CARGO_BIN_EXE_nvwa-cli"))
        .arg("new")
        .arg(profile)
        .arg(&scene)
        .output()
        .expect("new scene");
    assert!(created.status.success());
    assert_eq!(
        std::fs::read_to_string(&sibling).expect("sibling"),
        "unrelated sibling"
    );
    let duplicate = r#"{"command_id":"duplicate","expected_revision":0,"command":{"type":"set_parameters","character_id":"character-1","values":{"smile":99,"smile":0.5}}}"#;
    for (index, contents) in [duplicate.to_string(), format!("[{duplicate}]")]
        .into_iter()
        .enumerate()
    {
        let commands = dir.join(format!("commands-{index}.json"));
        let saved = dir.join(format!("output-{index}.json"));
        std::fs::write(&commands, contents).expect("duplicate fixture");
        let output = Process::new(env!("CARGO_BIN_EXE_nvwa-cli"))
            .arg("apply")
            .arg(&scene)
            .arg(&commands)
            .arg(&saved)
            .output()
            .expect("CLI apply");
        assert!(!output.status.success());
        assert!(!saved.exists());
        let error: serde_json::Value =
            serde_json::from_slice(&output.stderr).expect("structured error");
        assert_eq!(error["code"], "invalid_json");
    }
}

#[cfg(unix)]
#[test]
fn fifo_without_writer_is_rejected_within_timeout() {
    let path = output_dir("fifo-open").join("pipe.json");
    assert!(
        Process::new("mkfifo")
            .arg(&path)
            .status()
            .expect("FIFO")
            .success()
    );
    let mut child = Process::new(env!("CARGO_BIN_EXE_nvwa-cli"))
        .arg("inspect")
        .arg(path)
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::piped())
        .spawn()
        .expect("CLI FIFO input");
    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(2);
    loop {
        if let Some(status) = child.try_wait().expect("poll child") {
            assert!(!status.success());
            let output = child.wait_with_output().expect("output");
            let error: serde_json::Value =
                serde_json::from_slice(&output.stderr).expect("structured error");
            assert_eq!(error["code"], "unsupported_file");
            break;
        }
        if std::time::Instant::now() >= deadline {
            child.kill().expect("stop blocked child");
            child.wait().expect("reap child");
            panic!("FIFO import blocked without a writer");
        }
        std::thread::sleep(std::time::Duration::from_millis(10));
    }
}
