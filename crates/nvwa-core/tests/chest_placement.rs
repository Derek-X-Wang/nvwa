use nvwa_core::*;
use std::collections::BTreeMap;

const KEYS: [&str; 2] = ["breast_spacing", "breast_vertical_position"];

#[test]
fn chest_profile_is_versioned_and_preserves_v9_assets_and_work() {
    let previous = CharacterProfile::b1_character_arm_proportions();
    let next = CharacterProfile::b1_character_chest_placement();
    assert_eq!(next.parameters[..23], previous.parameters);
    assert_eq!(next.backend.b1_asset_version(), Some(B1AssetVersion::V10));
    assert!(!next.backend.supports_timeline());
    assert!(next.clips.is_empty());
    assert_eq!(next.parameters.len(), 25);
    for (index, key) in KEYS.iter().enumerate() {
        let p = &next.parameters[23 + index];
        assert_eq!(
            (&*p.id, p.morph_index, p.min, p.max, p.default),
            (*key, 23 + index, -1.0, 1.0, 0.0)
        );
    }
    let old_work = SceneDocument::from_profile(previous).unwrap();
    assert_eq!(
        SceneDocument::from_json(&old_work.to_json().unwrap()).unwrap(),
        old_work
    );
    let old_assets =
        B1AssetManifest::from_bytes_for(B1AssetVersion::V9, B1AssetVersion::V9.manifest_bytes())
            .unwrap();
    let new_assets =
        B1AssetManifest::from_bytes_for(B1AssetVersion::V10, B1AssetVersion::V10.manifest_bytes())
            .unwrap();
    assert_eq!(new_assets.files.len(), 59);
    for file in old_assets.files {
        assert!(
            new_assets.files.contains(&file),
            "changed v9 file: {}",
            file.path
        );
    }
    let work = SceneDocument::from_profile(next).unwrap();
    assert_eq!(
        SceneDocument::from_json(&work.to_json().unwrap()).unwrap(),
        work
    );
    for schema in [9, 10, 11] {
        let mut forged = serde_json::to_value(&work).unwrap();
        forged["profile"]["backend"]["schema_version"] = schema.into();
        assert!(SceneDocument::from_json(&forged.to_string()).is_err());
    }
}

#[test]
fn chest_axes_round_trip_and_reject_invalid_edits_atomically() {
    let doc =
        SceneDocument::from_profile(CharacterProfile::b1_character_chest_placement()).unwrap();
    let mut editor = Editor::new(doc.clone()).unwrap();
    for (key, value) in KEYS.iter().zip([-1.0, 1.0]) {
        editor
            .apply(CommandEnvelope {
                command_id: format!("set-{key}"),
                expected_revision: editor.document().revision,
                command: Command::SetParameters {
                    character_id: doc.character.id.clone(),
                    values: BTreeMap::from([(key.to_string(), value)]),
                },
            })
            .unwrap();
        assert_eq!(editor.document().character.parameters[*key], value);
    }
    for key in KEYS {
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
                        }
                    })
                    .is_err()
            );
            assert_eq!(*editor.document(), before);
            assert_eq!(editor.retention_stats(), history);
        }
    }
}
