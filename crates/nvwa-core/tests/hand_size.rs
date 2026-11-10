use nvwa_core::*;
use std::collections::BTreeMap;

#[test]
fn hand_size_profile_preserves_v9_and_rejects_forged_identity() {
    let old = CharacterProfile::b1_character_arm_proportions();
    let new = CharacterProfile::b1_character_hand_size();
    assert_eq!(new.parameters[..23], old.parameters);
    assert_eq!(new.backend.b1_asset_version(), Some(B1AssetVersion::V11));
    assert!(!new.backend.supports_timeline());
    assert!(new.clips.is_empty());
    assert_eq!(new.parameters.len(), 25);
    for (index, key) in ["left_hand_size", "right_hand_size"].iter().enumerate() {
        let p = &new.parameters[23 + index];
        assert_eq!(
            (&*p.id, p.morph_index, p.min, p.max, p.default),
            (*key, 23 + index, -1.0, 1.0, 0.0)
        );
    }
    let old_work = SceneDocument::from_profile(old).unwrap();
    assert_eq!(
        SceneDocument::from_json(&old_work.to_json().unwrap()).unwrap(),
        old_work
    );
    let old_assets =
        B1AssetManifest::from_bytes_for(B1AssetVersion::V9, B1AssetVersion::V9.manifest_bytes())
            .unwrap();
    let new_assets =
        B1AssetManifest::from_bytes_for(B1AssetVersion::V11, B1AssetVersion::V11.manifest_bytes())
            .unwrap();
    assert_eq!(new_assets.files.len(), 59);
    for file in old_assets.files {
        assert!(
            new_assets.files.contains(&file),
            "changed v9 file: {}",
            file.path
        );
    }
    let work = SceneDocument::from_profile(new).unwrap();
    assert_eq!(
        work.profile.asset_path,
        "characters/mpfb-b1-v11/manifest.json"
    );
    assert_eq!(
        SceneDocument::from_json(&work.to_json().unwrap()).unwrap(),
        work
    );
    let mut forged = serde_json::to_value(&work).unwrap();
    forged["profile"]["backend"]["schema_version"] = 11.into();
    assert!(SceneDocument::from_json(&forged.to_string()).is_err());
    forged["profile"]["backend"]["schema_version"] = 12.into();
    assert!(SceneDocument::from_json(&forged.to_string()).is_err());
    forged["profile"]["backend"]["schema_version"] = 13.into();
    forged["profile"]["backend"]["asset_id"] =
        "mpfb-hm08-game-engine-female-sportsuit01-v10".into();
    assert!(SceneDocument::from_json(&forged.to_string()).is_err());
}

#[test]
fn independent_hand_weights_are_bounded_and_atomic() {
    let doc = SceneDocument::from_profile(CharacterProfile::b1_character_hand_size()).unwrap();
    let mut editor = Editor::new(doc.clone()).unwrap();
    for (key, value) in [("left_hand_size", -1.0), ("right_hand_size", 1.0)] {
        editor
            .apply(CommandEnvelope {
                command_id: format!("set-{key}"),
                expected_revision: editor.document().revision,
                command: Command::SetParameters {
                    character_id: doc.character.id.clone(),
                    values: BTreeMap::from([(key.into(), value)]),
                },
            })
            .unwrap();
        assert_eq!(editor.document().character.parameters[key], value);
    }
    for value in [-1.01, 1.01, f32::NAN, f32::INFINITY] {
        let before = editor.document().clone();
        assert!(
            editor
                .apply(CommandEnvelope {
                    command_id: format!("bad-{value}"),
                    expected_revision: before.revision,
                    command: Command::SetParameters {
                        character_id: doc.character.id.clone(),
                        values: BTreeMap::from([
                            ("left_hand_size".into(), value),
                            ("hip_width".into(), 0.5)
                        ]),
                    },
                })
                .is_err()
        );
        assert_eq!(*editor.document(), before);
    }
}
