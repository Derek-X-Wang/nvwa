use nvwa_core::*;
use std::collections::BTreeMap;

#[test]
fn upper_arm_muscle_extends_v13_without_changing_older_works() {
    let old = CharacterProfile::b1_character_forearm_form();
    let new = CharacterProfile::b1_character_upper_arm_muscle();
    assert_eq!(new.parameters[..27], old.parameters);
    assert_eq!(new.backend.b1_asset_version(), Some(B1AssetVersion::V14));
    assert!(!new.backend.supports_timeline());
    assert!(new.clips.is_empty());
    assert_eq!(new.parameters.len(), 28);
    let p = &new.parameters[27];
    assert_eq!(
        (&*p.id, p.morph_index, p.min, p.max, p.default),
        ("upper_arm_muscle_fullness", 27, -1.0, 1.0, 0.0)
    );
    let old_work = SceneDocument::from_profile(old).unwrap();
    assert_eq!(
        SceneDocument::from_json(&old_work.to_json().unwrap()).unwrap(),
        old_work
    );
    let old_assets =
        B1AssetManifest::from_bytes_for(B1AssetVersion::V13, B1AssetVersion::V13.manifest_bytes())
            .unwrap();
    let new_assets =
        B1AssetManifest::from_bytes_for(B1AssetVersion::V14, B1AssetVersion::V14.manifest_bytes())
            .unwrap();
    assert_eq!(new_assets.files.len(), 65);
    for file in old_assets.files {
        assert!(
            new_assets.files.contains(&file),
            "changed v13 file: {}",
            file.path
        );
    }
    let work = SceneDocument::from_profile(new).unwrap();
    assert_eq!(
        work.profile.asset_path,
        "characters/mpfb-b1-v14/manifest.json"
    );
    assert_eq!(
        SceneDocument::from_json(&work.to_json().unwrap()).unwrap(),
        work
    );
    let mut forged = serde_json::to_value(&work).unwrap();
    forged["profile"]["backend"]["schema_version"] = 15.into();
    assert!(SceneDocument::from_json(&forged.to_string()).is_err());
    forged["profile"]["backend"]["schema_version"] = 16.into();
    forged["profile"]["backend"]["asset_id"] =
        "mpfb-hm08-game-engine-female-sportsuit01-v13".into();
    assert!(SceneDocument::from_json(&forged.to_string()).is_err());
}

#[test]
fn upper_arm_muscle_weight_is_bounded_and_bad_edit_is_atomic() {
    let doc =
        SceneDocument::from_profile(CharacterProfile::b1_character_upper_arm_muscle()).unwrap();
    let mut editor = Editor::new(doc.clone()).unwrap();
    for value in [-1.0, 1.0] {
        editor
            .apply(CommandEnvelope {
                command_id: format!("set-{value}"),
                expected_revision: editor.document().revision,
                command: Command::SetParameters {
                    character_id: doc.character.id.clone(),
                    values: BTreeMap::from([("upper_arm_muscle_fullness".into(), value)]),
                },
            })
            .unwrap();
        assert_eq!(
            editor.document().character.parameters["upper_arm_muscle_fullness"],
            value
        );
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
                            ("upper_arm_muscle_fullness".into(), value),
                            ("hip_width".into(), 0.5),
                        ]),
                    },
                })
                .is_err()
        );
        assert_eq!(*editor.document(), before);
    }
}
