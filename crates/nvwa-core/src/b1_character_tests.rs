use super::*;

#[test]
fn eight_parameter_identity_does_not_widen_legacy_profiles_or_appearance() {
    let legacy = CharacterProfile::b1_motion();
    let current = CharacterProfile::b1_character();
    assert_eq!(legacy.parameters.len(), 2);
    assert_eq!(legacy.backend.b1_asset_version(), Some(B1AssetVersion::V1));
    assert_eq!(current.backend.b1_asset_version(), Some(B1AssetVersion::V2));
    assert_eq!(current.parameters.len(), 8);
    assert_eq!(current.clips, legacy.clips);
    current.validate().unwrap();
    for (i, (spec, targets)) in current
        .parameters
        .iter()
        .zip(B1_PARAMETER_TARGETS)
        .enumerate()
    {
        assert_eq!(spec.id, targets.id);
        assert_eq!(
            (spec.morph_index, spec.min, spec.max, spec.default),
            (i, -1.0, 1.0, 0.0)
        );
    }
    for profile in [CharacterProfile::b1(), legacy, current] {
        let doc = SceneDocument::from_profile(profile.clone()).unwrap();
        assert_eq!(
            SceneDocument::from_json(&doc.to_json().unwrap()).unwrap(),
            doc
        );
        for other in [
            CharacterProfile::b1(),
            CharacterProfile::b1_motion(),
            CharacterProfile::b1_character(),
        ] {
            let mut mixed = profile.clone();
            mixed.backend = other.backend.clone();
            assert_eq!(mixed.validate().is_ok(), profile.backend == other.backend);
        }
        for mask in 0..8 {
            let flags = (mask & 1 != 0, mask & 2 != 0, mask & 4 != 0);
            let selection =
                CharacterAppearance::b1_cc0_for(&profile.backend, flags.0, flags.1, flags.2)
                    .unwrap();
            selection.validate_for(&profile.backend).unwrap();
            assert_eq!(selection.b1_flags(), (mask != 0).then_some(flags));
            if mask != 0 {
                let opposite = if profile.backend.b1_asset_version() == Some(B1AssetVersion::V1) {
                    CharacterProfile::b1_character()
                } else {
                    CharacterProfile::b1_motion()
                };
                assert!(selection.validate_for(&opposite.backend).is_err());
            }
        }
    }
    assert_eq!(
        CharacterAppearance::b1_cc0(true, false, false).b1_set(),
        Some(B1AppearanceSet::V1)
    );
}

#[test]
fn exact_new_descriptors_preserve_all_legacy_payloads_and_reject_mutations() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../../assets");
    let old = B1AssetManifest::from_bytes(B1_ASSET_MANIFEST_BYTES).unwrap();
    let new =
        B1AssetManifest::from_bytes_for(B1AssetVersion::V2, B1_V2_ASSET_MANIFEST_BYTES).unwrap();
    assert!(B1AssetManifest::from_bytes(B1_V2_ASSET_MANIFEST_BYTES).is_err());
    assert!(B1AssetManifest::from_bytes_for(B1AssetVersion::V2, B1_ASSET_MANIFEST_BYTES).is_err());
    assert_eq!(new.files.len(), 25);
    assert_eq!(new.files.iter().map(|f| f.bytes).sum::<usize>(), 6_016_330);
    for f in &old.files {
        assert!(new.files.contains(f));
        assert_eq!(
            std::fs::read(root.join("characters/mpfb-b1-v1").join(&f.path)).unwrap(),
            std::fs::read(root.join("characters/mpfb-b1-v2").join(&f.path)).unwrap()
        );
    }
    for f in &new.files {
        let bytes = std::fs::read(root.join("characters/mpfb-b1-v2").join(&f.path)).unwrap();
        new.validate_file_bytes(&f.path, &bytes).unwrap();
        let mut bad = bytes.clone();
        bad[0] ^= 1;
        assert!(new.validate_file_bytes(&f.path, &bad).is_err());
        assert!(
            new.validate_file_bytes(&f.path, &bytes[..bytes.len() - 1])
                .is_err()
        );
    }
    for set in [B1AppearanceSet::V1, B1AppearanceSet::V2] {
        let m = B1AppearanceManifest::from_bytes_for(set, set.manifest_bytes()).unwrap();
        for (path, f) in &m.files {
            let old = std::fs::read(root.join("appearances/mpfb-b1-cc0-v1").join(path)).unwrap();
            let new = std::fs::read(root.join("appearances/mpfb-b1-cc0-v2").join(path)).unwrap();
            assert_eq!(old, new);
            assert_eq!(new.len(), f.bytes);
            m.validate_file_bytes(path, &new).unwrap();
        }
        let mut bad = m;
        bad.base_asset_id.push('x');
        assert!(bad.validate().is_err());
    }
    assert!(B1AppearanceManifest::from_bytes(B1_V2_APPEARANCE_MANIFEST_BYTES).is_err());
    let mut bad = new;
    bad.files[0].sha256 = "0".repeat(64);
    assert!(bad.validate().is_err());
}

#[test]
fn all_eight_parameters_share_atomic_history_and_legacy_work_is_not_upgraded() {
    let initial = SceneDocument::from_profile(CharacterProfile::b1_character()).unwrap();
    let mut editor = Editor::new(initial.clone()).unwrap();
    let selected: std::collections::BTreeMap<_, _> = initial
        .profile
        .parameters
        .iter()
        .enumerate()
        .map(|(i, p)| (p.id.clone(), if i % 2 == 0 { -1.0 } else { 1.0 }))
        .collect();
    let apply = |editor: &mut Editor, command: Command| {
        editor
            .apply(CommandEnvelope {
                command_id: format!("eight-{}", editor.document().revision),
                expected_revision: editor.document().revision,
                command,
            })
            .unwrap();
    };
    apply(
        &mut editor,
        Command::SetParameters {
            character_id: initial.character.id.clone(),
            values: selected.clone(),
        },
    );
    assert_eq!(editor.document().character.parameters, selected);
    apply(
        &mut editor,
        Command::SetParameters {
            character_id: initial.character.id.clone(),
            values: initial.character.parameters.clone(),
        },
    );
    assert_eq!(
        editor.document().character.parameters,
        initial.character.parameters
    );
    apply(&mut editor, Command::Undo);
    assert_eq!(editor.document().character.parameters, selected);
    apply(&mut editor, Command::Redo);
    assert_eq!(
        editor.document().character.parameters,
        initial.character.parameters
    );
    for bad in [f32::NAN, f32::INFINITY, -1.01, 1.01] {
        let before = editor.document().clone();
        assert!(
            editor
                .apply(CommandEnvelope {
                    command_id: format!("bad-{bad}"),
                    expected_revision: before.revision,
                    command: Command::SetParameters {
                        character_id: before.character.id.clone(),
                        values: std::collections::BTreeMap::from([("hip_width".into(), bad)])
                    }
                })
                .is_err()
        );
        assert_eq!(editor.document(), &before);
    }
    let legacy = SceneDocument::from_profile(CharacterProfile::b1_motion()).unwrap();
    let reread = SceneDocument::from_json(&legacy.to_json().unwrap()).unwrap();
    assert_eq!(reread, legacy);
    assert_eq!(reread.character.parameters.len(), 2);
    let mut missing = serde_json::to_value(&initial).unwrap();
    missing["character"]["parameters"]
        .as_object_mut()
        .unwrap()
        .remove("hip_width");
    assert!(SceneDocument::from_json(&missing.to_string()).is_err());
}
