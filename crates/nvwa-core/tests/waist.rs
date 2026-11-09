use nvwa_core::*;
use std::collections::BTreeMap;
#[test]
fn waist_profile_is_static_explicit_and_legacy_is_unchanged() {
    let old = CharacterProfile::b1_character_lower_contour();
    let p = CharacterProfile::b1_character_waist();
    assert_eq!(p.parameters[..10], old.parameters);
    assert_eq!(p.parameters.len(), 11);
    assert_eq!(p.backend.b1_asset_version(), Some(B1AssetVersion::V5));
    assert!(!p.backend.supports_timeline());
    assert!(p.clips.is_empty());
    assert_eq!(B1AppearanceSet::for_base(B1AssetVersion::V5), None);
    assert!(CharacterAppearance::b1_cc0_for(&p.backend, true, false, false).is_err());
    let spec = &p.parameters[10];
    assert_eq!(
        (&*spec.id, spec.min, spec.max, spec.default),
        ("waist_circumference", -1.0, 1.0, 0.0)
    );
    for legacy in [
        CharacterProfile::b1(),
        CharacterProfile::b1_motion(),
        CharacterProfile::b1_character(),
        CharacterProfile::b1_character_contour(),
        old,
        CharacterProfile::b1_running(),
    ] {
        let d = SceneDocument::from_profile(legacy).unwrap();
        assert_eq!(SceneDocument::from_json(&d.to_json().unwrap()).unwrap(), d);
        let mut invalid = serde_json::to_value(&d).unwrap();
        invalid["character"]["parameters"]["waist_circumference"] = 0.0.into();
        assert!(SceneDocument::from_json(&invalid.to_string()).is_err());
    }
    let previous =
        B1AssetManifest::from_bytes_for(B1AssetVersion::V4, B1AssetVersion::V4.manifest_bytes())
            .unwrap();
    let next =
        B1AssetManifest::from_bytes_for(B1AssetVersion::V5, B1AssetVersion::V5.manifest_bytes())
            .unwrap();
    for file in previous.files {
        assert!(next.files.contains(&file));
    }
    assert_eq!(next.files.len(), 31);
    let d = SceneDocument::from_profile(p).unwrap();
    let mut bad = serde_json::to_value(&d).unwrap();
    bad["profile"]["backend"]["schema_version"] = 6.into();
    assert!(SceneDocument::from_json(&bad.to_string()).is_err());
}
#[test]
fn waist_values_history_and_failed_mixed_edits_are_transactional() {
    let d = SceneDocument::from_profile(CharacterProfile::b1_character_waist()).unwrap();
    let mut editor = Editor::new(d.clone()).unwrap();
    for value in [-1.0, -0.5, 0.0, 0.5, 1.0] {
        let revision = editor.document().revision;
        editor
            .apply(CommandEnvelope {
                command_id: format!("waist-{revision}"),
                expected_revision: revision,
                command: Command::SetParameters {
                    character_id: d.character.id.clone(),
                    values: BTreeMap::from([("waist_circumference".into(), value)]),
                },
            })
            .unwrap();
        assert_eq!(
            editor.document().character.parameters["waist_circumference"],
            value
        );
        assert_eq!(
            SceneDocument::from_json(&editor.document().to_json().unwrap()).unwrap(),
            *editor.document()
        );
    }
    for (command, expected) in [(Command::Undo, 0.5), (Command::Redo, 1.0)] {
        let revision = editor.document().revision;
        editor
            .apply(CommandEnvelope {
                command_id: format!("history-{revision}"),
                expected_revision: revision,
                command,
            })
            .unwrap();
        assert_eq!(
            editor.document().character.parameters["waist_circumference"],
            expected
        );
    }
    for value in [-1.01, 1.01, f32::NAN, f32::INFINITY, f32::NEG_INFINITY] {
        let before = editor.document().clone();
        let history = editor.retention_stats();
        assert!(
            editor
                .apply(CommandEnvelope {
                    command_id: format!("bad-{value}"),
                    expected_revision: before.revision,
                    command: Command::SetParameters {
                        character_id: d.character.id.clone(),
                        values: BTreeMap::from([
                            ("waist_circumference".into(), value),
                            ("hip_width".into(), 0.8)
                        ])
                    }
                })
                .is_err()
        );
        assert_eq!(*editor.document(), before);
        assert_eq!(editor.retention_stats(), history);
    }
}

#[test]
fn static_waist_rejects_motion_and_foreign_appearance() {
    let d = SceneDocument::from_profile(CharacterProfile::b1_character_waist()).unwrap();
    let old = SceneDocument::from_profile(CharacterProfile::b1_character_lower_contour()).unwrap();
    let mut forged = serde_json::to_value(&d).unwrap();
    forged["timeline"] = serde_json::to_value(&old.timeline).unwrap();
    assert!(SceneDocument::from_json(&forged.to_string()).is_err());
    let appearance =
        CharacterAppearance::b1_cc0_for(&old.profile.backend, true, true, true).unwrap();
    let mut forged = serde_json::to_value(&d).unwrap();
    forged["character"]["appearance"] = serde_json::to_value(appearance).unwrap();
    assert!(SceneDocument::from_json(&forged.to_string()).is_err());
    for field in [
        "backend",
        "id",
        "asset_path",
        "asset_sha256",
        "parameters",
        "clips",
    ] {
        let mut forged = serde_json::to_value(&d.profile).unwrap();
        forged[field] = serde_json::to_value(&old.profile).unwrap()[field].clone();
        assert!(
            CharacterProfile::from_json(&forged.to_string()).is_err(),
            "{field}"
        );
    }
}
