use nvwa_core::*;
use serde_json::{Value, json};
use std::{collections::BTreeMap, path::Path};

fn document() -> SceneDocument {
    SceneDocument::from_profile(CharacterProfile::b1()).unwrap()
}
fn error<T: std::fmt::Debug>(result: Result<T, CoreError>) -> String {
    result.unwrap_err().code
}
fn request(id: &str, revision: u64, command: Command) -> CommandEnvelope {
    CommandEnvelope {
        command_id: id.into(),
        expected_revision: revision,
        command,
    }
}
fn pose(id: &str) -> Command {
    Command::SetDiagnosticPose {
        character_id: "character-1".into(),
        pose_id: id.into(),
    }
}

#[test]
fn canonical_b1_defaults_roundtrip_and_reject_modified_profile_identity_or_bindings() {
    let original = document();
    assert_eq!(original.schema_version, 3);
    assert_eq!(original.profile.id, B1_PROFILE_ID);
    assert_eq!(
        original.character.diagnostic_pose.as_deref(),
        Some("neutral")
    );
    assert_eq!(
        original.character.parameters,
        BTreeMap::from([("jaw_drop".into(), 0.0), ("torso_length".into(), 0.0)])
    );
    assert!(original.timeline.is_empty());
    assert!(original.profile.clips.is_empty());
    assert_eq!(
        SceneDocument::from_json(&original.to_json().unwrap()).unwrap(),
        original
    );
    assert_eq!(
        CharacterProfile::from_json(&original.profile.to_json().unwrap()).unwrap(),
        original.profile
    );
    let value = serde_json::to_value(&original.profile).unwrap();
    for (pointer, replacement) in [
        ("/id", json!("other")),
        ("/asset_path", json!("other/manifest.json")),
        ("/asset_sha256", json!("0".repeat(64))),
        ("/license", json!("other")),
        ("/parameters/0/id", json!("height")),
        ("/parameters/0/morph_index", json!(2)),
        ("/parameters/0/min", json!(0)),
        ("/parameters/0/max", json!(2)),
        ("/parameters/0/default", json!(0.5)),
        ("/parameters", json!([])),
        (
            "/clips",
            json!([{"id":"fake","animation_index":0,"duration_seconds":1}]),
        ),
    ] {
        let mut changed = value.clone();
        *changed.pointer_mut(pointer).unwrap() = replacement;
        assert_eq!(
            error(CharacterProfile::from_json(&changed.to_string())),
            "unsupported_character_asset",
            "{pointer}"
        );
    }
}

#[test]
fn legacy_schema1_and_schema2_upgrade_only_representation_with_strict_exact_shapes() {
    let glb = CharacterProfile::from_json(include_str!("../../../assets/character.profile.json"))
        .unwrap();
    assert!(glb.backend.is_glb());
    let mut original = SceneDocument::from_profile(glb).unwrap();
    original.revision = 37;
    original.character.parameters.insert("smile".into(), 0.37);
    original.stage = StageSettings::black_space();
    let current = serde_json::to_value(&original).unwrap();
    for version in [1, 2] {
        let mut legacy = current.clone();
        legacy["schema_version"] = json!(version);
        legacy["profile"].as_object_mut().unwrap().remove("backend");
        legacy["character"]
            .as_object_mut()
            .unwrap()
            .remove("diagnostic_pose");
        let mut expected = original.clone();
        if version == 1 {
            legacy.as_object_mut().unwrap().remove("stage");
            expected.stage = StageSettings::white_studio();
        }
        let upgraded = SceneDocument::from_json(&legacy.to_string()).unwrap();
        assert_eq!(upgraded, expected);
        assert_eq!(
            SceneDocument::from_json(&upgraded.to_json().unwrap()).unwrap(),
            expected
        );
        let mut injected = legacy.clone();
        injected["profile"]["backend"] = json!({"type":"glb","schema_version":1});
        assert_eq!(
            error(SceneDocument::from_json(&injected.to_string())),
            "invalid_json"
        );
        injected = legacy.clone();
        injected["character"]["diagnostic_pose"] = Value::Null;
        assert_eq!(
            error(SceneDocument::from_json(&injected.to_string())),
            "invalid_json"
        );
        injected = legacy;
        injected["profile"]["extra"] = json!(true);
        assert_eq!(
            error(SceneDocument::from_json(&injected.to_string())),
            "invalid_json"
        );
    }
}

#[test]
fn current_work_requires_backend_and_present_pose_with_stable_unknown_identity_errors() {
    let b1 = serde_json::to_value(document()).unwrap();
    let glb = serde_json::to_value(
        SceneDocument::from_profile(
            CharacterProfile::from_json(include_str!("../../../assets/character.profile.json"))
                .unwrap(),
        )
        .unwrap(),
    )
    .unwrap();
    for original in [b1.clone(), glb.clone()] {
        for key in ["backend", "diagnostic_pose"] {
            let mut missing = original.clone();
            missing[if key == "backend" {
                "profile"
            } else {
                "character"
            }]
            .as_object_mut()
            .unwrap()
            .remove(key);
            assert_eq!(
                error(SceneDocument::from_json(&missing.to_string())),
                "invalid_json",
                "{key}"
            );
            assert!(serde_json::from_str::<SceneDocument>(&missing.to_string()).is_err());
        }
        let mut null_backend = original;
        null_backend["profile"]["backend"] = Value::Null;
        assert_eq!(
            error(SceneDocument::from_json(&null_backend.to_string())),
            "invalid_json"
        );
    }
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
            json!("other"),
            "unsupported_character_asset",
        ),
    ] {
        let mut invalid = b1.clone();
        *invalid.pointer_mut(pointer).unwrap() = value;
        assert_eq!(error(SceneDocument::from_json(&invalid.to_string())), code);
        assert_eq!(
            error(CharacterProfile::from_json(&invalid["profile"].to_string())),
            code
        );
    }
    let mut invalid = b1.clone();
    invalid["character"]["diagnostic_pose"] = Value::Null;
    assert_eq!(
        error(SceneDocument::from_json(&invalid.to_string())),
        "unsupported_pose"
    );
    invalid["character"]["diagnostic_pose"] = json!("wave");
    assert_eq!(
        error(SceneDocument::from_json(&invalid.to_string())),
        "unsupported_pose"
    );
    let mut invalid = glb;
    invalid["character"]["diagnostic_pose"] = json!("neutral");
    assert_eq!(
        error(SceneDocument::from_json(&invalid.to_string())),
        "unsupported_character_operation"
    );
    let raw = document().to_json().unwrap();
    for (needle, replacement) in [
        (
            "\"diagnostic_pose\": \"neutral\"",
            "\"diagnostic_pose\": \"neutral\", \"diagnostic_pose\": \"knee\"",
        ),
        (
            "\"type\": \"b1_cpu\"",
            "\"type\": \"b1_cpu\", \"type\": \"glb\"",
        ),
        ("\"asset_id\":", "\"extra\": true, \"asset_id\":"),
    ] {
        assert!(raw.contains(needle));
        let invalid = raw.replacen(needle, replacement, 1);
        assert_eq!(error(SceneDocument::from_json(&invalid)), "invalid_json");
        assert!(serde_json::from_str::<SceneDocument>(&invalid).is_err());
    }
}

#[test]
fn pose_and_parameters_share_preview_atomic_history_retries_and_failed_redo_preservation() {
    let mut editor = Editor::new(document()).unwrap();
    let before = editor.document().clone();
    let parameters = Command::SetParameters {
        character_id: "character-1".into(),
        values: BTreeMap::from([("torso_length".into(), 0.375), ("jaw_drop".into(), -0.25)]),
    };
    let preview = editor.preview(&parameters).unwrap();
    assert_eq!(preview.character.parameters["torso_length"], 0.375);
    assert_eq!(editor.document(), &before);
    editor.apply(request("parameters", 0, parameters)).unwrap();
    let posed = request("pose", 1, pose("combined"));
    assert_eq!(
        CommandEnvelope::from_json(&posed.to_json().unwrap()).unwrap(),
        posed
    );
    editor.apply(posed.clone()).unwrap();
    editor.apply(request("undo", 2, Command::Undo)).unwrap();
    let saved = editor.document().clone();
    let history = editor.retention_stats();
    for (id, command, code) in [
        ("bad-pose", pose("wave"), "unsupported_pose"),
        (
            "bad-character",
            Command::SetDiagnosticPose {
                character_id: "wrong".into(),
                pose_id: "neutral".into(),
            },
            "invalid_reference",
        ),
        (
            "bad-range",
            Command::SetParameters {
                character_id: "character-1".into(),
                values: BTreeMap::from([("jaw_drop".into(), 2.0)]),
            },
            "out_of_range",
        ),
        (
            "bad-timeline",
            Command::SetTimeline {
                clips: vec![TimelineClip {
                    id: "fake".into(),
                    clip_id: "wave".into(),
                    start_seconds: 0.0,
                    duration_seconds: 1.0,
                    speed: 1.0,
                    looping: false,
                }],
            },
            "unsupported_character_operation",
        ),
    ] {
        assert_eq!(error(editor.apply(request(id, 3, command))), code);
        assert_eq!(editor.document(), &saved);
        assert_eq!(editor.retention_stats(), history);
    }
    editor.apply(request("redo", 3, Command::Redo)).unwrap();
    assert_eq!(
        editor.document().character.diagnostic_pose.as_deref(),
        Some("combined")
    );
    assert_eq!(editor.document().revision, 4);
    assert!(editor.apply(posed).unwrap().duplicate);
    assert_eq!(editor.document().revision, 4);
    assert_eq!(
        error(editor.apply(request("pose", 4, pose("knee")))),
        "command_id_conflict"
    );
    for (index, pose_id) in B1_DIAGNOSTIC_POSES.into_iter().enumerate() {
        editor
            .apply(request(
                &format!("supported-{pose_id}"),
                4 + index as u64,
                pose(pose_id),
            ))
            .unwrap();
    }
    let mut glb = Editor::new(
        SceneDocument::from_profile(
            CharacterProfile::from_json(include_str!("../../../assets/character.profile.json"))
                .unwrap(),
        )
        .unwrap(),
    )
    .unwrap();
    assert_eq!(
        error(glb.apply(request("unsupported", 0, pose("neutral")))),
        "unsupported_character_operation"
    );
    assert_eq!(glb.retention_stats().undo_snapshots, 0);
}

#[test]
fn pinned_manifest_and_all_real_asset_bytes_validate_and_tampering_is_rejected() {
    let manifest = B1AssetManifest::from_bytes(B1_ASSET_MANIFEST_BYTES).unwrap();
    assert_eq!(manifest.files.len(), 13);
    assert_eq!(error(B1AssetManifest::from_bytes(&[])), "asset_missing");
    let mut changed = B1_ASSET_MANIFEST_BYTES.to_vec();
    changed[0] ^= 1;
    assert_eq!(
        error(B1AssetManifest::from_bytes(&changed)),
        "asset_hash_mismatch"
    );
    assert_eq!(
        error(B1AssetManifest::from_bytes(&vec![
            b' ';
            B1_MAX_MANIFEST_BYTES + 1
        ])),
        "invalid_asset"
    );
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../assets/characters/mpfb-b1-v1");
    let mut total = 0;
    for file in &manifest.files {
        let bytes = std::fs::read(root.join(&file.path)).unwrap();
        total += bytes.len();
        manifest.validate_file_bytes(&file.path, &bytes).unwrap();
        let mut corrupted = bytes.clone();
        corrupted[0] ^= 1;
        assert_eq!(
            error(manifest.validate_file_bytes(&file.path, &corrupted)),
            "asset_hash_mismatch"
        );
        assert_eq!(
            error(manifest.validate_file_bytes(&file.path, &bytes[..bytes.len() - 1])),
            "invalid_asset"
        );
    }
    assert!(total <= B1_MAX_TOTAL_ASSET_BYTES);
    assert_eq!(
        error(manifest.validate_file_bytes("../base.obj", b"outside")),
        "invalid_asset"
    );
    let mut forged = manifest.clone();
    forged.files[0].path = "../outside".into();
    assert_eq!(
        error(forged.validate_file_bytes("../outside", b"outside")),
        "invalid_asset"
    );
    let mut forged = manifest.clone();
    forged.files.pop();
    assert_eq!(error(forged.validate()), "invalid_asset");
    let mut forged = manifest;
    forged.files[0].sha256 = "0".repeat(64);
    assert_eq!(error(forged.validate()), "invalid_asset");
    CharacterProfile::b1()
        .validate_asset_bytes(B1_ASSET_MANIFEST_BYTES)
        .unwrap();
}
