use nvwa_core::*;
use std::{collections::BTreeMap, path::Path};

#[test]
fn lower_contour_is_explicit_one_sided_and_preserves_all_old_specs() {
    let old = CharacterProfile::b1_character_contour();
    let new = CharacterProfile::b1_character_lower_contour();
    assert_eq!(SCHEMA_VERSION, 4);
    assert_eq!(new.backend.b1_asset_version(), Some(B1AssetVersion::V4));
    assert!(new.backend.is_b1_motion());
    assert_eq!(new.parameters.len(), 10);
    assert_eq!(new.parameters[..9], old.parameters);
    assert_eq!(new.clips, old.clips);
    assert_eq!(
        B1AssetVersion::V4.parameters()[..9],
        B1_CONTOUR_PARAMETER_TARGETS
    );
    let spec = &new.parameters[9];
    assert_eq!(
        (&*spec.id, spec.min, spec.max, spec.default),
        ("lower_face_squareness", 0.0, 1.0, 0.0)
    );
    let pair = B1AssetVersion::V4.parameters()[9];
    assert_eq!(
        (pair.decrease, pair.increase),
        ("chin-bones-decr", "chin-bones-incr")
    );
    for (field, value) in [("min", -1.0), ("max", 2.0), ("default", 0.5)] {
        let mut tampered = serde_json::to_value(&new).unwrap();
        tampered["parameters"][9][field] = value.into();
        assert!(
            CharacterProfile::from_json(&tampered.to_string()).is_err(),
            "{field}"
        );
    }
    for profile in [
        CharacterProfile::b1(),
        CharacterProfile::b1_motion(),
        CharacterProfile::b1_character(),
        old,
        new.clone(),
    ] {
        let document = SceneDocument::from_profile(profile.clone()).unwrap();
        assert_eq!(
            SceneDocument::from_json(&document.to_json().unwrap()).unwrap(),
            document
        );
        for set in [
            B1AppearanceSet::V1,
            B1AppearanceSet::V2,
            B1AppearanceSet::V2Short01,
            B1AppearanceSet::V3,
            B1AppearanceSet::V3Short01,
            B1AppearanceSet::V4,
            B1AppearanceSet::V4Short01,
        ] {
            assert_eq!(
                CharacterAppearance::b1_cc0_for_set(&profile.backend, set, true, true, true)
                    .is_ok(),
                profile.backend.b1_asset_version() == Some(set.base())
            );
        }
        if profile != new {
            let mut value = serde_json::to_value(&document).unwrap();
            value["character"]["parameters"]["lower_face_squareness"] = 0.5.into();
            assert!(SceneDocument::from_json(&value.to_string()).is_err());
            for field in ["backend", "id", "asset_path", "asset_sha256", "parameters"] {
                let mut value = serde_json::to_value(&new).unwrap();
                value[field] = serde_json::to_value(&profile).unwrap()[field].clone();
                assert!(
                    CharacterProfile::from_json(&value.to_string()).is_err(),
                    "{} {field}",
                    profile.id
                );
            }
        }
    }
}

#[test]
fn lower_contour_values_history_reload_and_negative_edits_are_transactional() {
    let doc = SceneDocument::from_profile(CharacterProfile::b1_character_lower_contour()).unwrap();
    let mut editor = Editor::new(doc.clone()).unwrap();
    let apply = |editor: &mut Editor, command| {
        editor
            .apply(CommandEnvelope {
                command_id: format!("lower-{}", editor.document().revision),
                expected_revision: editor.document().revision,
                command,
            })
            .unwrap()
    };
    for value in [0.25, 0.5, 0.75, 1.0, 0.0] {
        apply(
            &mut editor,
            Command::SetParameters {
                character_id: doc.character.id.clone(),
                values: BTreeMap::from([("lower_face_squareness".into(), value)]),
            },
        );
        assert_eq!(
            editor.document().character.parameters["lower_face_squareness"],
            value
        );
        assert_eq!(
            SceneDocument::from_json(&editor.document().to_json().unwrap()).unwrap(),
            *editor.document()
        );
    }
    apply(&mut editor, Command::Undo);
    assert_eq!(
        editor.document().character.parameters["lower_face_squareness"],
        1.0
    );
    apply(&mut editor, Command::Redo);
    assert_eq!(
        editor.document().character.parameters["lower_face_squareness"],
        0.0
    );
    for value in [
        -1.0,
        -f32::EPSILON,
        1.01,
        f32::NAN,
        f32::INFINITY,
        f32::NEG_INFINITY,
    ] {
        let before = editor.document().clone();
        let history = editor.retention_stats();
        assert!(
            editor
                .apply(CommandEnvelope {
                    command_id: format!("invalid-{value}"),
                    expected_revision: before.revision,
                    command: Command::SetParameters {
                        character_id: doc.character.id.clone(),
                        values: BTreeMap::from([
                            ("head_width".into(), 0.4),
                            ("lower_face_squareness".into(), value)
                        ])
                    }
                })
                .is_err()
        );
        assert_eq!(*editor.document(), before);
        assert_eq!(editor.retention_stats(), history);
    }
    let mut missing = serde_json::to_value(&doc).unwrap();
    missing["character"]["parameters"]
        .as_object_mut()
        .unwrap()
        .remove("lower_face_squareness");
    assert!(SceneDocument::from_json(&missing.to_string()).is_err());
}

#[test]
fn lower_contour_descriptors_preserve_all_previous_payload_bytes() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../assets");
    let old =
        B1AssetManifest::from_bytes_for(B1AssetVersion::V3, B1AssetVersion::V3.manifest_bytes())
            .unwrap();
    let new =
        B1AssetManifest::from_bytes_for(B1AssetVersion::V4, B1AssetVersion::V4.manifest_bytes())
            .unwrap();
    assert_eq!(new.files.len(), 29);
    for file in old.files {
        assert!(new.files.contains(&file));
        assert_eq!(
            std::fs::read(root.join("characters/mpfb-b1-v3").join(&file.path)).unwrap(),
            std::fs::read(root.join("characters/mpfb-b1-v4").join(&file.path)).unwrap()
        );
    }
    for version in [B1AssetVersion::V1, B1AssetVersion::V2, B1AssetVersion::V3] {
        assert!(
            B1AssetManifest::from_bytes_for(version, B1AssetVersion::V4.manifest_bytes()).is_err()
        );
        assert!(
            B1AssetManifest::from_bytes_for(B1AssetVersion::V4, version.manifest_bytes()).is_err()
        );
    }
    for (new, old) in [
        (B1AppearanceSet::V4, B1AppearanceSet::V3),
        (B1AppearanceSet::V4Short01, B1AppearanceSet::V3Short01),
    ] {
        let next = B1AppearanceManifest::from_bytes_for(new, new.manifest_bytes()).unwrap();
        let prior = B1AppearanceManifest::from_bytes_for(old, old.manifest_bytes()).unwrap();
        assert_eq!(next.files, prior.files);
        assert_eq!(next.base_asset_id, B1_V4_ASSET_ID);
        assert_eq!(next.base_manifest_sha256, B1_V4_ASSET_MANIFEST_SHA256);
        assert!(B1AppearanceManifest::from_bytes_for(new, old.manifest_bytes()).is_err());
        assert!(B1AppearanceManifest::from_bytes_for(old, new.manifest_bytes()).is_err());
        for (path, file) in &next.files {
            let bytes = std::fs::read(
                root.join(Path::new(new.manifest_path()).parent().unwrap())
                    .join(path),
            )
            .unwrap();
            assert_eq!(bytes.len(), file.bytes);
            next.validate_file_bytes(path, &bytes).unwrap();
        }
    }
}
