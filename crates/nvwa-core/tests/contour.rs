use nvwa_core::*;
use std::{collections::BTreeMap, path::Path};

#[test]
fn contour_is_explicit_canonical_and_cannot_cross_old_profiles_or_appearance() {
    let profiles = [
        CharacterProfile::b1(),
        CharacterProfile::b1_motion(),
        CharacterProfile::b1_character(),
        CharacterProfile::b1_character_contour(),
    ];
    let contour = &profiles[3];
    assert_eq!(contour.backend.b1_asset_version(), Some(B1AssetVersion::V3));
    assert!(contour.backend.is_b1_motion());
    assert_eq!(contour.parameters.len(), 9);
    assert_eq!(contour.parameters[..8], profiles[2].parameters);
    assert_eq!(contour.clips, profiles[2].clips);
    assert_eq!(B1AssetVersion::V3.parameters()[..8], B1_PARAMETER_TARGETS);
    let cheek = &contour.parameters[8];
    assert_eq!(
        (&*cheek.id, cheek.min, cheek.max, cheek.default),
        ("cheek_fullness", -1.0, 1.0, 0.0)
    );
    for profile in &profiles {
        let doc = SceneDocument::from_profile(profile.clone()).unwrap();
        assert_eq!(
            SceneDocument::from_json(&doc.to_json().unwrap()).unwrap(),
            doc
        );
        for other in &profiles {
            for field in ["backend", "id", "asset_path", "asset_sha256", "parameters"] {
                let mut value = serde_json::to_value(profile).unwrap();
                value[field] = serde_json::to_value(other).unwrap()[field].clone();
                let same = serde_json::to_value(profile).unwrap()[field] == value[field];
                assert_eq!(
                    CharacterProfile::from_json(&value.to_string()).is_ok(),
                    same,
                    "{} {} {field}",
                    profile.id,
                    other.id
                );
            }
        }
        for set in [
            B1AppearanceSet::V1,
            B1AppearanceSet::V2,
            B1AppearanceSet::V2Short01,
            B1AppearanceSet::V3,
            B1AppearanceSet::V3Short01,
        ] {
            let selection =
                CharacterAppearance::b1_cc0_for_set(&profile.backend, set, true, true, true);
            assert_eq!(
                selection.is_ok(),
                profile.backend.b1_asset_version() == Some(set.base())
            );
        }
    }
    for field in ["id", "min", "max", "default", "morph_index"] {
        let mut value = serde_json::to_value(contour).unwrap();
        value["parameters"][8][field] = if field == "id" {
            "jaw_width".into()
        } else {
            2.into()
        };
        assert!(
            CharacterProfile::from_json(&value.to_string()).is_err(),
            "{field}"
        );
    }
}

#[test]
fn contour_exact_descriptors_preserve_old_payloads_and_reject_crossovers() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../assets");
    for version in [B1AssetVersion::V1, B1AssetVersion::V2, B1AssetVersion::V3] {
        let manifest = B1AssetManifest::from_bytes_for(version, version.manifest_bytes()).unwrap();
        for selected in [B1AssetVersion::V1, B1AssetVersion::V2, B1AssetVersion::V3] {
            assert_eq!(
                B1AssetManifest::from_bytes_for(selected, version.manifest_bytes()).is_ok(),
                selected == version
            );
        }
        if version == B1AssetVersion::V3 {
            assert_eq!(manifest.files.len(), 27);
            let old =
                B1AssetManifest::from_bytes_for(B1AssetVersion::V2, B1_V2_ASSET_MANIFEST_BYTES)
                    .unwrap();
            for file in old.files {
                assert!(manifest.files.contains(&file));
                assert_eq!(
                    std::fs::read(root.join("characters/mpfb-b1-v2").join(&file.path)).unwrap(),
                    std::fs::read(root.join("characters/mpfb-b1-v3").join(&file.path)).unwrap()
                );
            }
            for file in &manifest.files {
                let bytes =
                    std::fs::read(root.join("characters/mpfb-b1-v3").join(&file.path)).unwrap();
                manifest.validate_file_bytes(&file.path, &bytes).unwrap();
                let mut bad = bytes;
                bad[0] ^= 1;
                assert!(manifest.validate_file_bytes(&file.path, &bad).is_err());
            }
        }
    }
    for (set, old) in [
        (B1AppearanceSet::V3, B1AppearanceSet::V2),
        (B1AppearanceSet::V3Short01, B1AppearanceSet::V2Short01),
    ] {
        let manifest = B1AppearanceManifest::from_bytes_for(set, set.manifest_bytes()).unwrap();
        assert_eq!(set.schema_version(), 3);
        assert!(B1AppearanceManifest::from_bytes_for(old, set.manifest_bytes()).is_err());
        assert!(B1AppearanceManifest::from_bytes_for(set, old.manifest_bytes()).is_err());
        for path in manifest.files.keys() {
            let bytes = std::fs::read(
                root.join(Path::new(set.manifest_path()).parent().unwrap())
                    .join(path),
            )
            .unwrap();
            assert_eq!(
                bytes,
                std::fs::read(
                    root.join(Path::new(old.manifest_path()).parent().unwrap())
                        .join(path)
                )
                .unwrap()
            );
            manifest.validate_file_bytes(path, &bytes).unwrap();
        }
    }
}

#[test]
fn contour_uses_atomic_commands_history_save_open_and_rejects_old_work_edits() {
    let doc = SceneDocument::from_profile(CharacterProfile::b1_character_contour()).unwrap();
    let mut editor = Editor::new(doc.clone()).unwrap();
    let apply = |editor: &mut Editor, command| {
        editor
            .apply(CommandEnvelope {
                command_id: format!("contour-{}", editor.document().revision),
                expected_revision: editor.document().revision,
                command,
            })
            .unwrap()
    };
    for value in [-1.0, -0.35, 0.0, 0.65, 1.0] {
        apply(
            &mut editor,
            Command::SetParameters {
                character_id: doc.character.id.clone(),
                values: BTreeMap::from([("cheek_fullness".into(), value)]),
            },
        );
        assert_eq!(
            editor.document().character.parameters["cheek_fullness"],
            value
        );
        let json = editor.document().to_json().unwrap();
        assert_eq!(SceneDocument::from_json(&json).unwrap(), *editor.document());
    }
    apply(&mut editor, Command::Undo);
    assert_eq!(
        editor.document().character.parameters["cheek_fullness"],
        0.65
    );
    apply(&mut editor, Command::Redo);
    assert_eq!(
        editor.document().character.parameters["cheek_fullness"],
        1.0
    );
    for value in [f32::NAN, f32::INFINITY, -1.01, 1.01] {
        let before = editor.document().clone();
        assert!(
            editor
                .apply(CommandEnvelope {
                    command_id: format!("bad-{value}"),
                    expected_revision: before.revision,
                    command: Command::SetParameters {
                        character_id: doc.character.id.clone(),
                        values: BTreeMap::from([("cheek_fullness".into(), value)])
                    }
                })
                .is_err()
        );
        assert_eq!(*editor.document(), before);
    }
    let old = SceneDocument::from_profile(CharacterProfile::b1_character()).unwrap();
    let mut old_editor = Editor::new(old.clone()).unwrap();
    assert!(
        old_editor
            .apply(CommandEnvelope {
                command_id: "no-upgrade".into(),
                expected_revision: 0,
                command: Command::SetParameters {
                    character_id: old.character.id.clone(),
                    values: BTreeMap::from([("cheek_fullness".into(), 0.5)])
                }
            })
            .is_err()
    );
    assert_eq!(*old_editor.document(), old);
}
