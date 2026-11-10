use nvwa_core::*;
use std::collections::BTreeMap;

const KEYS: [&str; 2] = ["hip_depth", "buttocks_volume"];

#[test]
fn hip_contour_profile_is_versioned_and_preserves_v7_files() {
    let old = CharacterProfile::b1_character_upper_body();
    let profile = CharacterProfile::b1_character_hip_contour();
    assert_eq!(profile.parameters[..18], old.parameters);
    assert_eq!(profile.backend.b1_asset_version(), Some(B1AssetVersion::V8));
    assert!(!profile.backend.supports_timeline());
    assert!(profile.clips.is_empty());
    assert_eq!(profile.parameters.len(), 20);
    for (index, key) in KEYS.iter().enumerate() {
        let spec = &profile.parameters[18 + index];
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
    let previous =
        B1AssetManifest::from_bytes_for(B1AssetVersion::V7, B1AssetVersion::V7.manifest_bytes())
            .unwrap();
    let next =
        B1AssetManifest::from_bytes_for(B1AssetVersion::V8, B1AssetVersion::V8.manifest_bytes())
            .unwrap();
    assert_eq!(next.files.len(), 49);
    for file in previous.files {
        assert!(next.files.contains(&file), "changed v7 file: {}", file.path);
    }
    let doc = SceneDocument::from_profile(profile).unwrap();
    assert_eq!(
        SceneDocument::from_json(&doc.to_json().unwrap()).unwrap(),
        doc
    );
    for schema in [8, 9, 11] {
        let mut forged = serde_json::to_value(&doc).unwrap();
        forged["profile"]["backend"]["schema_version"] = schema.into();
        assert!(SceneDocument::from_json(&forged.to_string()).is_err());
    }
}

#[test]
fn hip_contour_axes_round_trip_and_invalid_edits_are_atomic() {
    let doc = SceneDocument::from_profile(CharacterProfile::b1_character_hip_contour()).unwrap();
    let mut editor = Editor::new(doc.clone()).unwrap();
    for (key, value) in KEYS.iter().zip([-1.0, 1.0]) {
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
                            ]),
                        },
                    })
                    .is_err()
            );
            assert_eq!(*editor.document(), before);
            assert_eq!(editor.retention_stats(), history);
        }
    }
}
