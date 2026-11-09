use serde_json::{Value, json};
use std::{fs, path::Path, process::Command};

fn cli(args: &[&str]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_nvwa-cli"))
        .args(args)
        .output()
        .unwrap()
}

fn ok(args: &[&str]) -> Value {
    let output = cli(args);
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    serde_json::from_slice(&output.stdout).unwrap()
}

#[test]
fn a_saved_reference_edit_changes_one_key_and_only_adjacent_intervals() {
    let directory = std::env::temp_dir().join(format!(
        "nvwa-reference-{}-{:?}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    fs::create_dir(&directory).unwrap();
    let paths = [
        "start.json",
        "motion.json",
        "edit.json",
        "resaved.json",
        "command.json",
    ]
    .map(|name| directory.join(name));
    let [start, original, edited, resaved, command] =
        paths.each_ref().map(|path| path.to_str().unwrap());
    let assets = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../assets");
    ok(&["new-character", assets.to_str().unwrap(), start]);
    let reference = json!({
        "command_id": "reference",
        "expected_revision": 0,
        "command": {
            "type": "set_reference_motion",
            "motion": {
                "duration_seconds": 4,
                "pelvis_offsets": [{"seconds": 0, "offset_metres": [0, 0, 0]},
                                   {"seconds": 4, "offset_metres": [0.04, 0, 0]}],
                "rotations": {
                    "calf_l": {"axis": [1, 0, 0], "keys": [
                        {"seconds": 0, "degrees": 0}, {"seconds": 0.5, "degrees": 6},
                        {"seconds": 1, "degrees": 36}, {"seconds": 2, "degrees": 6},
                        {"seconds": 4, "degrees": 0}]},
                    "pelvis": {"axis": [0, 0, 1], "keys": [
                        {"seconds": 0, "degrees": 170}, {"seconds": 4, "degrees": -170}]}
                }
            }
        }
    });
    fs::write(command, reference.to_string()).unwrap();
    ok(&["apply", start, command, original]);
    let original_bytes = fs::read(original).unwrap();
    let capabilities = ok(&["describe-capabilities", original]);
    let contract = &capabilities["cli_contract"];
    assert_eq!(contract["reference_motion"]["present"], true);
    assert!(
        contract["command_examples"]
            .as_array()
            .unwrap()
            .iter()
            .all(|example| example["command"]["type"] != "set_timeline")
    );
    let pose = |work, time| ok(&["reference-pose", work, time])["pose"].clone();
    assert_eq!(pose(original, "0.75")["rotations"][0]["degrees"], 21.0);
    assert_eq!(pose(original, "2")["rotations"][1]["degrees"], 180.0);
    assert!(!cli(&["reference-pose", original, "NaN"]).status.success());
    assert!(!cli(&["reference-pose", original, "4.001"]).status.success());

    let mut edit = json!({"command_id": "reduce-bend", "expected_revision": 1, "command": {
        "type": "set_reference_rotation_key", "bone": "calf_l", "seconds": 1, "degrees": 18
    }});
    let mut invalid = reference.clone();
    invalid["command"]["motion"]["rotations"]["unknown"] =
        invalid["command"]["motion"]["rotations"]["calf_l"].clone();
    fs::write(command, invalid.to_string()).unwrap();
    assert!(!cli(&["apply", start, command, edited]).status.success());
    assert!(!Path::new(edited).exists());
    fs::write(command, edit.to_string()).unwrap();
    ok(&["apply", original, command, edited]);
    let edited_bytes = fs::read(edited).unwrap();
    assert_eq!(pose(edited, "1")["rotations"][0]["degrees"], 18.0);
    assert_eq!(pose(edited, "0.75")["rotations"][0]["degrees"], 12.0);
    for time in ["0", "0.5", "2", "3", "4"] {
        assert_eq!(pose(original, time), pose(edited, time), "{time}");
    }
    assert_eq!(
        pose(original, "1")["pelvis_offset_metres"],
        pose(edited, "1")["pelvis_offset_metres"]
    );
    assert_eq!(
        pose(original, "1")["rotations"][1],
        pose(edited, "1")["rotations"][1]
    );
    let mut before = ok(&["inspect", original]);
    before["revision"] = 2.into();
    before["reference_motion"]["rotations"]["calf_l"]["keys"][2]["degrees"] = 18.0.into();
    assert_eq!(before, ok(&["inspect", edited]));
    edit["expected_revision"] = 2.into();
    edit["command"]["seconds"] = 1.1.into();
    fs::write(command, edit.to_string()).unwrap();
    assert!(!cli(&["apply", edited, command, edited]).status.success());
    assert_eq!(fs::read(edited).unwrap(), edited_bytes);
    ok(&["validate", edited, assets.to_str().unwrap()]);
    ok(&["save", edited, resaved]);
    assert_eq!(fs::read(resaved).unwrap(), edited_bytes);
    assert_eq!(fs::read(original).unwrap(), original_bytes);
    fs::remove_dir_all(directory).unwrap();
}
