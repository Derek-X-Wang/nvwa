use nvwa_core::{B1_RUN_CLIP_ID, CharacterProfile, SceneDocument};
use serde_json::{Value, json};
use std::{path::Path, process::Command};
fn cli(args: &[&Path]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_nvwa-cli"))
        .args(args)
        .output()
        .unwrap()
}
fn success(args: &[&Path]) -> Value {
    let out = cli(args);
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    serde_json::from_slice(&out.stdout).unwrap()
}
#[test]
fn running_creation_discovery_finite_edit_history_and_saved_exchange() {
    let dir = std::env::temp_dir().join(format!(
        "nvwa-running-cli-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    std::fs::create_dir(&dir).unwrap();
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../assets");
    let initial = dir.join("initial.json");
    let request = dir.join("request.json");
    let edited = dir.join("edited.json");
    let saved = dir.join("saved.json");
    success(&["new-character-running".as_ref(), &root, &initial]);
    let d = SceneDocument::from_json(&std::fs::read_to_string(&initial).unwrap()).unwrap();
    assert_eq!(d.profile, CharacterProfile::b1_running());
    assert!(!d.timeline[0].looping);
    assert_eq!(d.timeline[0].clip_id, B1_RUN_CLIP_ID);
    let caps = success(&["describe-capabilities".as_ref(), &initial]);
    assert_eq!(
        caps["cli_contract"]["authored_motion"]["travel"]["source_forward_metres"],
        2
    );
    let batch = json!([
        {"command_id":"arrange","expected_revision":0,"command":{"type":"set_timeline","clips":[{"id":"run","clip_id":B1_RUN_CLIP_ID,"start_seconds":0,"duration_seconds":4,"speed":1,"looping":false},{"id":"arrival","clip_id":"b1_arm_rehearsal_v1","start_seconds":5,"duration_seconds":4,"speed":1,"looping":false}]}},
        {"command_id":"undo","expected_revision":1,"command":{"type":"undo"}},
        {"command_id":"redo","expected_revision":2,"command":{"type":"redo"}}
    ]);
    std::fs::write(&request, serde_json::to_vec(&batch).unwrap()).unwrap();
    success(&["apply".as_ref(), &initial, &request, &edited]);
    success(&["validate".as_ref(), &edited, &root]);
    success(&["save".as_ref(), &edited, &saved]);
    assert_eq!(
        std::fs::read(&edited).unwrap(),
        std::fs::read(&saved).unwrap()
    );
    let saved_doc = SceneDocument::from_json(&std::fs::read_to_string(&saved).unwrap()).unwrap();
    assert_eq!(
        nvwa_core::running::resolve(&saved_doc, 5.0)
            .unwrap()
            .actor_offset_metres,
        [0.0, 0.0, 2.0]
    );
    let bad = json!({"command_id":"bad","expected_revision":0,"command":{"type":"set_timeline","clips":[{"id":"run","clip_id":B1_RUN_CLIP_ID,"start_seconds":0,"duration_seconds":4,"speed":1,"looping":true}]}});
    std::fs::write(&request, serde_json::to_vec(&bad).unwrap()).unwrap();
    let before = std::fs::read(&edited).unwrap();
    let out = cli(&["apply".as_ref(), &initial, &request, &edited]);
    assert!(!out.status.success());
    assert_eq!(std::fs::read(&edited).unwrap(), before);
    std::fs::remove_dir_all(dir).unwrap();
}
