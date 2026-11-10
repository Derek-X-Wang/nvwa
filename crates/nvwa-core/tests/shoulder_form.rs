use nvwa_core::*;
use std::collections::BTreeMap;

#[test]
fn shoulder_form_extends_v11_without_changing_older_works() {
    let old = CharacterProfile::b1_character_hand_size();
    let new = CharacterProfile::b1_character_shoulder_form();
    assert_eq!(new.parameters[..25], old.parameters);
    assert_eq!(new.backend.b1_asset_version(), Some(B1AssetVersion::V12));
    assert!(!new.backend.supports_timeline());
    assert!(new.clips.is_empty());
    assert_eq!(new.parameters.len(), 26);
    let p = &new.parameters[25];
    assert_eq!(
        (&*p.id, p.morph_index, p.min, p.max, p.default),
        ("shoulder_muscle_fullness", 25, -1.0, 1.0, 0.0)
    );
    let old_work = SceneDocument::from_profile(old).unwrap();
    assert_eq!(
        SceneDocument::from_json(&old_work.to_json().unwrap()).unwrap(),
        old_work
    );
    let old_assets =
        B1AssetManifest::from_bytes_for(B1AssetVersion::V11, B1AssetVersion::V11.manifest_bytes())
            .unwrap();
    let new_assets =
        B1AssetManifest::from_bytes_for(B1AssetVersion::V12, B1AssetVersion::V12.manifest_bytes())
            .unwrap();
    assert_eq!(new_assets.files.len(), 61);
    for file in old_assets.files {
        assert!(
            new_assets.files.contains(&file),
            "changed v11 file: {}",
            file.path
        );
    }
    let work = SceneDocument::from_profile(new).unwrap();
    assert_eq!(
        work.profile.asset_path,
        "characters/mpfb-b1-v12/manifest.json"
    );
    assert_eq!(
        SceneDocument::from_json(&work.to_json().unwrap()).unwrap(),
        work
    );
    let mut forged = serde_json::to_value(&work).unwrap();
    forged["profile"]["backend"]["schema_version"] = 13.into();
    assert!(SceneDocument::from_json(&forged.to_string()).is_err());
    forged["profile"]["backend"]["schema_version"] = 14.into();
    forged["profile"]["backend"]["asset_id"] =
        "mpfb-hm08-game-engine-female-sportsuit01-v11".into();
    assert!(SceneDocument::from_json(&forged.to_string()).is_err());
}

#[test]
fn shoulder_weight_is_bounded_and_bad_edit_is_atomic() {
    let doc = SceneDocument::from_profile(CharacterProfile::b1_character_shoulder_form()).unwrap();
    let mut editor = Editor::new(doc.clone()).unwrap();
    for value in [-1.0, 1.0] {
        editor
            .apply(CommandEnvelope {
                command_id: format!("set-{value}"),
                expected_revision: editor.document().revision,
                command: Command::SetParameters {
                    character_id: doc.character.id.clone(),
                    values: BTreeMap::from([("shoulder_muscle_fullness".into(), value)]),
                },
            })
            .unwrap();
        assert_eq!(
            editor.document().character.parameters["shoulder_muscle_fullness"],
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
                            ("shoulder_muscle_fullness".into(), value),
                            ("hip_width".into(), 0.5),
                        ]),
                    },
                })
                .is_err()
        );
        assert_eq!(*editor.document(), before);
    }
}
