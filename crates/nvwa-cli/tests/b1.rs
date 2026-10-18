//! Actual offline production CLI; no Studio, window, source library or GPU.
use nvwa_core::{B1_ASSET_MANIFEST_BYTES, B1AssetManifest, CharacterProfile, SceneDocument};
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
    let path =
        std::env::temp_dir().join(format!("nvwa-b1-cli-{}-{name}-{stamp}", std::process::id()));
    std::fs::create_dir(&path).unwrap();
    path
}
fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../assets")
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
    let value: Value = serde_json::from_slice(&output.stderr).unwrap();
    assert_eq!(value["code"], code, "{}", value["message"]);
}
fn copy_assets(dir: &Path) -> PathBuf {
    let destination = dir.join("assets");
    let package = destination.join("characters/mpfb-b1-v1");
    std::fs::create_dir_all(&package).unwrap();
    std::fs::write(package.join("manifest.json"), B1_ASSET_MANIFEST_BYTES).unwrap();
    for file in B1AssetManifest::from_bytes(B1_ASSET_MANIFEST_BYTES)
        .unwrap()
        .files
    {
        let target = package.join(&file.path);
        std::fs::create_dir_all(target.parent().unwrap()).unwrap();
        std::fs::copy(
            root().join("characters/mpfb-b1-v1").join(&file.path),
            target,
        )
        .unwrap();
    }
    destination
}

#[test]
fn no_window_new_discover_apply_validate_save_and_inspect_share_full_work() {
    let dir = directory("roundtrip");
    let input = dir.join("input.json");
    let output = dir.join("edited.json");
    let saved = dir.join("saved.json");
    let request = dir.join("request.json");
    let created = success(cli(&["new-b1".as_ref(), &root(), &input]));
    assert_eq!(created["asset_checked"], true);
    let inspected = success(cli(&["inspect".as_ref(), &input]));
    assert_eq!(inspected["schema_version"], 4);
    assert_eq!(inspected["character"]["diagnostic_pose"], "neutral");
    assert_eq!(inspected["timeline"], json!([]));
    let caps = success(cli(&["describe-capabilities".as_ref(), &input]));
    assert_eq!(caps["backend"]["type"], "b1_cpu");
    assert_eq!(
        caps["cli_contract"]["entrypoints"]["new-b1"],
        json!(["asset_root", "output.json"])
    );
    assert_eq!(
        caps["cli_contract"]["diagnostic_poses"]["ids"],
        json!(["neutral", "shoulder", "elbow", "knee", "combined"])
    );
    assert_eq!(
        caps["cli_contract"]["diagnostic_poses"]["morph_index"],
        "inert_legacy_metadata_unused_on_b1"
    );
    assert_eq!(
        caps["cli_contract"]["diagnostic_poses"]["timeline_supported"],
        false
    );
    assert_eq!(caps["editor_retention"]["session_local"], true);
    let mut examples = caps["cli_contract"]["command_examples"]
        .as_array()
        .unwrap()
        .clone();
    assert!(
        !examples
            .iter()
            .any(|example| example["command"]["type"] == "set_timeline")
    );
    for (index, example) in examples.iter_mut().enumerate() {
        example["expected_revision"] = json!(index);
        match example["command"]["type"].as_str().unwrap() {
            "set_parameters" => {
                example["command"]["values"] = json!({"torso_length":0.375,"jaw_drop":-0.25})
            }
            "set_diagnostic_pose" => example["command"]["pose_id"] = json!("knee"),
            "set_stage" => example["command"]["stage"]["camera"]["azimuth_degrees"] = json!(27),
            _ => {}
        }
    }
    std::fs::write(&request, serde_json::to_vec(&examples).unwrap()).unwrap();
    let results = success(cli(&["apply".as_ref(), &input, &request, &output]));
    assert_eq!(results.as_array().unwrap().len(), 7);
    let work = success(cli(&["inspect".as_ref(), &output]));
    assert_eq!(work["revision"], 7);
    assert_eq!(work["character"]["parameters"]["torso_length"], 0.375);
    assert_eq!(work["character"]["parameters"]["jaw_drop"], -0.25);
    assert_eq!(work["character"]["diagnostic_pose"], "knee");
    assert_eq!(work["stage"]["camera"]["azimuth_degrees"], 27.0);
    assert_eq!(
        success(cli(&["validate".as_ref(), &output, &root()]))["asset_checked"],
        true
    );
    rejected(cli(&["validate".as_ref(), &output]), "asset_root_required");
    success(cli(&["save".as_ref(), &output, &saved]));
    assert_eq!(
        std::fs::read(&output).unwrap(),
        std::fs::read(&saved).unwrap()
    );
    assert_eq!(success(cli(&["inspect".as_ref(), &input])), inspected);
    // A profile-only new command must not bypass B1's explicit asset admission.
    let profile = dir.join("b1-profile.json");
    std::fs::write(&profile, CharacterProfile::b1().to_json().unwrap()).unwrap();
    rejected(
        cli(&["new".as_ref(), &profile, &saved]),
        "unsupported_character_operation",
    );
    assert_eq!(success(cli(&["inspect".as_ref(), &saved])), work);
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn failed_pose_batch_and_invalid_import_preserve_input_and_existing_or_absent_output() {
    let dir = directory("atomic");
    let input = dir.join("input.json");
    success(cli(&["new-b1".as_ref(), &root(), &input]));
    let before = std::fs::read(&input).unwrap();
    let request = dir.join("requests.json");
    std::fs::write(&request, r#"[{"command_id":"good","expected_revision":0,"command":{"type":"set_parameters","character_id":"character-1","values":{"torso_length":0.5}}},{"command_id":"bad","expected_revision":1,"command":{"type":"set_diagnostic_pose","character_id":"character-1","pose_id":"wave"}}]"#).unwrap();
    for existing in [false, true] {
        let output = dir.join(if existing {
            "existing.json"
        } else {
            "absent.json"
        });
        if existing {
            std::fs::write(&output, b"preserved output").unwrap();
        }
        rejected(
            cli(&["apply".as_ref(), &input, &request, &output]),
            "unsupported_pose",
        );
        assert_eq!(std::fs::read(&input).unwrap(), before);
        if existing {
            assert_eq!(std::fs::read(&output).unwrap(), b"preserved output");
        } else {
            assert!(!output.exists());
        }
    }
    let bad = dir.join("invalid.json");
    let output = dir.join("existing.json");
    let mut invalid: Value = serde_json::from_slice(&before).unwrap();
    for (pointer, value, code) in [
        (
            "/profile/backend/type",
            json!("gpu4"),
            "unsupported_character_backend",
        ),
        (
            "/profile/backend/schema_version",
            json!(2),
            "unsupported_character_version",
        ),
        (
            "/profile/backend/asset_id",
            json!("unknown"),
            "unsupported_character_asset",
        ),
        (
            "/character/diagnostic_pose",
            json!("wave"),
            "unsupported_pose",
        ),
    ] {
        let old = invalid.pointer(pointer).unwrap().clone();
        *invalid.pointer_mut(pointer).unwrap() = value;
        std::fs::write(&bad, serde_json::to_vec(&invalid).unwrap()).unwrap();
        rejected(cli(&["save".as_ref(), &bad, &output]), code);
        assert_eq!(std::fs::read(&output).unwrap(), b"preserved output");
        *invalid.pointer_mut(pointer).unwrap() = old;
    }
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn real_asset_missing_corrupt_and_oversized_data_fail_validation_and_creation_without_output() {
    let dir = directory("assets");
    let assets = copy_assets(&dir);
    let work = dir.join("valid.json");
    success(cli(&["new-b1".as_ref(), &assets, &work]));
    let output = dir.join("created.json");
    let target = assets.join("characters/mpfb-b1-v1/targets/chin-jaw-drop-incr.target");
    let original = std::fs::read(&target).unwrap();
    std::fs::remove_file(&target).unwrap();
    for existing in [false, true] {
        if existing {
            std::fs::write(&output, b"preserved output").unwrap();
        }
        rejected(cli(&["new-b1".as_ref(), &assets, &output]), "asset_missing");
        if existing {
            assert_eq!(std::fs::read(&output).unwrap(), b"preserved output");
        } else {
            assert!(!output.exists());
        }
    }
    rejected(cli(&["validate".as_ref(), &work, &assets]), "asset_missing");
    let mut corrupt = original.clone();
    corrupt[0] ^= 1;
    std::fs::write(&target, corrupt).unwrap();
    rejected(
        cli(&["validate".as_ref(), &work, &assets]),
        "asset_hash_mismatch",
    );
    rejected(
        cli(&["new-b1".as_ref(), &assets, &output]),
        "asset_hash_mismatch",
    );
    assert_eq!(std::fs::read(&output).unwrap(), b"preserved output");
    let file = std::fs::OpenOptions::new()
        .write(true)
        .open(&target)
        .unwrap();
    file.set_len(nvwa_core::B1_MAX_ASSET_BYTES as u64 + 1)
        .unwrap();
    drop(file);
    rejected(cli(&["validate".as_ref(), &work, &assets]), "invalid_asset");
    std::fs::write(&target, original).unwrap();
    let manifest = assets.join("characters/mpfb-b1-v1/manifest.json");
    std::fs::write(&manifest, b"changed").unwrap();
    rejected(
        cli(&["validate".as_ref(), &work, &assets]),
        "asset_hash_mismatch",
    );
    std::fs::write(manifest, B1_ASSET_MANIFEST_BYTES).unwrap();
    assert_eq!(
        success(cli(&["validate".as_ref(), &work, &assets]))["asset_checked"],
        true
    );
    assert_eq!(std::fs::read(output).unwrap(), b"preserved output");
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn glb_asset_validation_caps_regular_file_bytes_before_hashing() {
    let dir = directory("glb-limit");
    let input = dir.join("input.json");
    let document = SceneDocument::from_profile(
        CharacterProfile::from_json(include_str!("../../../assets/character.profile.json"))
            .unwrap(),
    )
    .unwrap();
    std::fs::write(&input, document.to_json().unwrap()).unwrap();
    let asset = dir.join(&document.profile.asset_path);
    std::fs::create_dir_all(asset.parent().unwrap()).unwrap();
    let file = std::fs::File::create(&asset).unwrap();
    file.set_len(64 * 1024 * 1024 + 1).unwrap();
    drop(file);
    rejected(cli(&["validate".as_ref(), &input, &dir]), "invalid_asset");
    std::fs::remove_file(&asset).unwrap();
    std::fs::create_dir(&asset).unwrap();
    rejected(
        cli(&["validate".as_ref(), &input, &dir]),
        "unsupported_file",
    );
    std::fs::remove_dir_all(dir).unwrap();
}

#[cfg(unix)]
#[test]
fn outside_asset_symlink_and_fifo_fail_actual_rooted_validator_without_blocking() {
    use std::os::unix::fs::symlink;
    let dir = directory("containment");
    let assets = copy_assets(&dir);
    let work = dir.join("work.json");
    std::fs::write(
        &work,
        SceneDocument::from_profile(CharacterProfile::b1())
            .unwrap()
            .to_json()
            .unwrap(),
    )
    .unwrap();
    let target = assets.join("characters/mpfb-b1-v1/targets");
    let outside = dir.join("outside-targets");
    std::fs::rename(&target, &outside).unwrap();
    symlink(&outside, &target).unwrap();
    rejected(
        cli(&["validate".as_ref(), &work, &assets]),
        "unsafe_asset_path",
    );
    std::fs::remove_file(&target).unwrap();
    std::fs::rename(&outside, &target).unwrap();
    let fifo = target.join("chin-jaw-drop-incr.target");
    std::fs::remove_file(&fifo).unwrap();
    assert!(
        Command::new("mkfifo")
            .arg(&fifo)
            .status()
            .unwrap()
            .success()
    );
    // O_NONBLOCK rejects a real FIFO with no writer; command is bounded by
    // the test harness's child polling timeout rather than a blocking wait.
    let mut child = Command::new(env!("CARGO_BIN_EXE_nvwa-cli"))
        .arg("validate")
        .arg(&work)
        .arg(&assets)
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn()
        .unwrap();
    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(5);
    while child.try_wait().unwrap().is_none() {
        if std::time::Instant::now() >= deadline {
            child.kill().unwrap();
            let _ = child.wait();
            panic!("asset FIFO blocked validator");
        }
        std::thread::sleep(std::time::Duration::from_millis(10));
    }
    rejected(child.wait_with_output().unwrap(), "unsupported_file");
    std::fs::remove_dir_all(dir).unwrap();
}

#[cfg(unix)]
#[test]
fn b1_saved_output_survives_response_transport_failure_for_each_mutating_verb() {
    let dir = directory("transport");
    let input = dir.join("input.json");
    std::fs::write(
        &input,
        SceneDocument::from_profile(CharacterProfile::b1())
            .unwrap()
            .to_json()
            .unwrap(),
    )
    .unwrap();
    let request = dir.join("request.json");
    std::fs::write(&request, r#"{"command_id":"pose","expected_revision":0,"command":{"type":"set_diagnostic_pose","character_id":"character-1","pose_id":"combined"}}"#).unwrap();
    for verb in ["new-b1", "apply", "save"] {
        let output = dir.join(format!("{verb}.json"));
        let mut command = Command::new(env!("CARGO_BIN_EXE_nvwa-cli"));
        command.arg(verb);
        match verb {
            "new-b1" => {
                command.arg(root()).arg(&output);
            }
            "apply" => {
                command.arg(&input).arg(&request).arg(&output);
            }
            _ => {
                command.arg(&input).arg(&output);
            }
        }
        let (reader, writer) = std::io::pipe().unwrap();
        drop(reader);
        let result = command.stdout(writer).output().unwrap();
        assert_eq!(result.status.code(), Some(1));
        assert_eq!(
            serde_json::from_slice::<Value>(&result.stderr).unwrap()["code"],
            "stdout_write"
        );
        let saved = SceneDocument::from_json(&std::fs::read_to_string(output).unwrap()).unwrap();
        assert_eq!(saved.revision, if verb == "apply" { 1 } else { 0 });
        assert_eq!(
            saved.character.diagnostic_pose.as_deref(),
            Some(if verb == "apply" {
                "combined"
            } else {
                "neutral"
            })
        );
    }
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn explicit_motion_creation_authenticates_same_asset_and_roundtrips_timeline() {
    let dir = directory("motion");
    let input = dir.join("motion.json");
    let output = dir.join("saved.json");
    success(cli(&["new-b1-motion".as_ref(), &root(), &input]));
    let work = success(cli(&["inspect".as_ref(), &input]));
    assert_eq!(work["profile"]["id"], "nvwa-mpfb-b1-motion-v1");
    assert_eq!(work["profile"]["backend"]["schema_version"], 2);
    assert_eq!(work["timeline"][0]["clip_id"], "b1_arm_rehearsal_v1");
    let caps = success(cli(&["describe-capabilities".as_ref(), &input]));
    assert_eq!(
        caps["cli_contract"]["diagnostic_poses"]["timeline_supported"],
        true
    );
    assert!(
        caps["cli_contract"]["command_examples"]
            .as_array()
            .unwrap()
            .iter()
            .any(|v| v["command"]["type"] == "set_timeline")
    );
    success(cli(&["save".as_ref(), &input, &output]));
    assert_eq!(
        std::fs::read(&input).unwrap(),
        std::fs::read(&output).unwrap()
    );
    let assets = copy_assets(&dir);
    std::fs::remove_file(assets.join("characters/mpfb-b1-v1/base.obj")).unwrap();
    rejected(
        cli(&["new-b1-motion".as_ref(), &assets, &output]),
        "asset_missing",
    );
    assert_eq!(success(cli(&["inspect".as_ref(), &output])), work);
    std::fs::remove_dir_all(dir).unwrap();
}
