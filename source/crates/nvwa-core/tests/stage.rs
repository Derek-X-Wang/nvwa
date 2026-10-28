use nvwa_core::{CharacterProfile, Command, CommandEnvelope, Editor, SceneDocument, StageSettings};
use serde_json::json;
fn document() -> SceneDocument {
    SceneDocument::from_profile(
        CharacterProfile::from_json(include_str!("../../../assets/character.profile.json"))
            .unwrap(),
    )
    .unwrap()
}
fn envelope(stage: StageSettings) -> CommandEnvelope {
    CommandEnvelope {
        command_id: "stage".into(),
        expected_revision: 0,
        command: Command::SetStage { stage },
    }
}
#[test]
fn exact_legacy_upgrade_and_required_strict_current_stage() {
    let original = document();
    let mut legacy = serde_json::to_value(&original).unwrap();
    legacy["profile"].as_object_mut().unwrap().remove("backend");
    legacy["character"]
        .as_object_mut()
        .unwrap()
        .remove("diagnostic_pose");
    legacy["character"]
        .as_object_mut()
        .unwrap()
        .remove("appearance");
    legacy["schema_version"] = json!(1);
    legacy["revision"] = json!(37);
    legacy.as_object_mut().unwrap().remove("stage");
    let upgraded = SceneDocument::from_json(&legacy.to_string()).unwrap();
    assert_eq!(upgraded.schema_version, nvwa_core::SCHEMA_VERSION);
    assert_eq!(upgraded.revision, 37);
    assert_eq!(upgraded.stage, StageSettings::white_studio());
    assert_eq!(upgraded.character, original.character);
    assert_eq!(upgraded.timeline, original.timeline);
    assert_eq!(
        SceneDocument::from_json(&upgraded.to_json().unwrap()).unwrap(),
        upgraded
    );
    legacy["stage"] = json!(null);
    assert_eq!(
        SceneDocument::from_json(&legacy.to_string())
            .unwrap_err()
            .code,
        "invalid_json"
    );
    legacy.as_object_mut().unwrap().remove("stage");
    legacy["schema_version"] = json!(2);
    assert_eq!(
        SceneDocument::from_json(&legacy.to_string())
            .unwrap_err()
            .code,
        "invalid_json"
    );
    let mut current = serde_json::to_value(&original).unwrap();
    current["stage"]["camera"]["surprise"] = json!(true);
    assert_eq!(
        SceneDocument::from_json(&current.to_string())
            .unwrap_err()
            .code,
        "invalid_json"
    );
    let duplicate = original.to_json().unwrap().replacen(
        "\"quality\": \"balanced\"",
        "\"quality\": \"balanced\", \"quality\": \"high\"",
        1,
    );
    assert_eq!(
        SceneDocument::from_json(&duplicate).unwrap_err().code,
        "invalid_json"
    );
}
#[test]
fn stage_transactions_retry_undo_redo_and_failed_edits_are_atomic() {
    let initial = document();
    let mut editor = Editor::new(initial.clone()).unwrap();
    let stage = StageSettings::black_space();
    let request = envelope(stage.clone());
    let preview = editor.preview(&request.command).unwrap();
    assert_eq!(preview.stage, stage);
    assert_eq!(editor.document(), &initial);
    assert_eq!(editor.retention_stats().undo_snapshots, 0);
    assert_eq!(editor.apply(request.clone()).unwrap().revision, 1);
    assert!(editor.apply(request.clone()).unwrap().duplicate);
    let retained = editor.retention_stats();
    let committed = editor.document().clone();
    let mut invalid = stage.clone();
    invalid.camera.distance = f32::NAN;
    assert_eq!(
        editor
            .apply(CommandEnvelope {
                command_id: "bad".into(),
                expected_revision: 1,
                command: Command::SetStage { stage: invalid }
            })
            .unwrap_err()
            .code,
        "nonfinite_value"
    );
    assert_eq!(editor.document(), &committed);
    assert_eq!(editor.retention_stats(), retained);
    let mut conflict = request.clone();
    conflict.command = Command::SetStage {
        stage: StageSettings::default(),
    };
    assert_eq!(
        editor.apply(conflict).unwrap_err().code,
        "command_id_conflict"
    );
    for (i, command) in [Command::Undo, Command::Redo].into_iter().enumerate() {
        editor
            .apply(CommandEnvelope {
                command_id: format!("history-{i}"),
                expected_revision: (i + 1) as u64,
                command,
            })
            .unwrap();
        assert_eq!(
            editor.document().stage,
            if i == 0 {
                initial.stage.clone()
            } else {
                stage.clone()
            }
        );
        assert_eq!(editor.document().character, initial.character);
        assert_eq!(editor.document().timeline, initial.timeline);
    }
    assert_eq!(editor.document().revision, 3);
}
#[test]
fn every_stage_numeric_family_is_finite_and_bounded() {
    let mut cases = Vec::new();
    macro_rules! bad {
        ($field:ident.$inner:ident, $value:expr) => {{
            let mut s = StageSettings::default();
            s.$field.$inner = $value;
            cases.push(s);
        }};
    }
    bad!(key_light.illuminance_lux, -1.0);
    bad!(fill_light.illuminance_lux, 100001.0);
    bad!(key_light.azimuth_degrees, f32::INFINITY);
    bad!(fill_light.elevation_degrees, 0.0);
    bad!(ambient.brightness, 2001.0);
    bad!(camera.azimuth_degrees, 181.0);
    bad!(camera.elevation_degrees, -21.0);
    bad!(camera.distance, 0.349);
    bad!(camera.target_height, 4.001);
    bad!(camera.fov_degrees, 76.0);
    for mut stage in [StageSettings::default(), StageSettings::black_space()] {
        stage.background_color_srgb[0] = f32::NAN;
        cases.push(stage);
    }
    let mut stage = StageSettings::default();
    stage.key_light.color_srgb[2] = 1.1;
    cases.push(stage);
    let mut stage = StageSettings::default();
    stage.fill_light.color_srgb[1] = -0.1;
    cases.push(stage);
    let mut stage = StageSettings::default();
    stage.ambient.color_srgb[0] = f32::NEG_INFINITY;
    cases.push(stage);
    let mut stage = StageSettings::default();
    stage.floor.color_srgb[2] = -0.01;
    cases.push(stage);
    for stage in cases {
        assert!(stage.validate().is_err());
        assert!(envelope(stage).to_json().is_err());
    }
    for stage in [StageSettings::default(), StageSettings::black_space()] {
        stage.validate().unwrap();
    }
}

#[test]
fn direct_serde_trait_preserves_duplicate_field_rejection() {
    let json = document().to_json().unwrap();
    for (needle, replacement) in [
        ("\"revision\": 0", "\"revision\": 0, \"revision\": 1"),
        (
            "\"quality\": \"balanced\"",
            "\"quality\": \"balanced\", \"quality\": \"high\"",
        ),
        ("\"distance\": 3.8", "\"distance\": 3.8, \"distance\": 4.0"),
    ] {
        assert!(json.contains(needle));
        let duplicate = json.replacen(needle, replacement, 1);
        assert!(
            serde_json::from_str::<SceneDocument>(&duplicate).is_err(),
            "direct decoder accepted {needle}"
        );
    }
}
