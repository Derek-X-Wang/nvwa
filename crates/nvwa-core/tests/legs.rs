use nvwa_core::*;
use std::collections::BTreeMap;

const LEG_KEYS: [&str; 4] = [
    "thigh_length",
    "lower_leg_length",
    "thigh_girth",
    "calf_girth",
];

#[test]
fn leg_profile_is_explicit_versioned_static_and_old_works_remain_unchanged() {
    let old = CharacterProfile::b1_character_waist();
    let profile = CharacterProfile::b1_character_legs();
    assert_eq!(profile.parameters[..old.parameters.len()], old.parameters);
    assert_eq!(profile.backend.b1_asset_version(), Some(B1AssetVersion::V6));
    assert!(!profile.backend.supports_timeline());
    assert!(profile.clips.is_empty());
    assert_eq!(B1AppearanceSet::for_base(B1AssetVersion::V6), None);
    assert_eq!(profile.parameters.len(), 15);
    for (index, key) in LEG_KEYS.iter().enumerate() {
        let spec = &profile.parameters[11 + index];
        assert_eq!(
            (&*spec.id, spec.min, spec.max, spec.default),
            (*key, -1.0, 1.0, 0.0)
        );
    }
    let old_doc = SceneDocument::from_profile(old).unwrap();
    assert_eq!(
        SceneDocument::from_json(&old_doc.to_json().unwrap()).unwrap(),
        old_doc
    );
    let mut forged_old = serde_json::to_value(&old_doc).unwrap();
    forged_old["character"]["parameters"]["thigh_length"] = 0.0.into();
    assert!(SceneDocument::from_json(&forged_old.to_string()).is_err());
    let previous =
        B1AssetManifest::from_bytes_for(B1AssetVersion::V5, B1AssetVersion::V5.manifest_bytes())
            .unwrap();
    let next =
        B1AssetManifest::from_bytes_for(B1AssetVersion::V6, B1AssetVersion::V6.manifest_bytes())
            .unwrap();
    assert_eq!(next.files.len(), 39);
    for file in previous.files {
        assert!(
            next.files.contains(&file),
            "old payload changed: {}",
            file.path
        );
    }
    let doc = SceneDocument::from_profile(profile).unwrap();
    assert_eq!(
        SceneDocument::from_json(&doc.to_json().unwrap()).unwrap(),
        doc
    );
    for schema in [6, 7, 9] {
        let mut forged = serde_json::to_value(&doc).unwrap();
        forged["profile"]["backend"]["schema_version"] = schema.into();
        assert!(SceneDocument::from_json(&forged.to_string()).is_err());
    }
}

#[test]
fn all_leg_axes_round_trip_and_reject_out_of_range_atomically() {
    let doc = SceneDocument::from_profile(CharacterProfile::b1_character_legs()).unwrap();
    let mut editor = Editor::new(doc.clone()).unwrap();
    for (key, value) in LEG_KEYS.iter().zip([-1.0, -0.5, 0.5, 1.0]) {
        let revision = editor.document().revision;
        editor
            .apply(CommandEnvelope {
                command_id: format!("set-{key}"),
                expected_revision: revision,
                command: Command::SetParameters {
                    character_id: doc.character.id.clone(),
                    values: BTreeMap::from([(key.to_string(), value)]),
                },
            })
            .unwrap();
        assert_eq!(editor.document().character.parameters[*key], value);
        assert_eq!(
            SceneDocument::from_json(&editor.document().to_json().unwrap()).unwrap(),
            *editor.document()
        );
    }
    for key in LEG_KEYS {
        for value in [-1.01, 1.01, f32::NAN, f32::INFINITY] {
            let before = editor.document().clone();
            let history = editor.retention_stats();
            assert!(
                editor
                    .apply(CommandEnvelope {
                        command_id: format!("bad-{key}-{value}"),
                        expected_revision: before.revision,
                        command: Command::SetParameters {
                            character_id: doc.character.id.clone(),
                            values: BTreeMap::from([
                                (key.into(), value),
                                ("hip_width".into(), 0.8)
                            ])
                        },
                    })
                    .is_err()
            );
            assert_eq!(*editor.document(), before);
            assert_eq!(editor.retention_stats(), history);
        }
    }
}
