use nvwa_core::*;
use serde_json::{Value, json};
use std::path::Path;

fn b1() -> SceneDocument {
    SceneDocument::from_profile(CharacterProfile::b1_motion()).unwrap()
}
fn glb() -> SceneDocument {
    SceneDocument::from_profile(
        CharacterProfile::from_json(include_str!("../../../assets/character.profile.json"))
            .unwrap(),
    )
    .unwrap()
}
fn envelope(id: &str, revision: u64, appearance: CharacterAppearance) -> CommandEnvelope {
    CommandEnvelope {
        command_id: id.into(),
        expected_revision: revision,
        command: Command::SetAppearance {
            character_id: "character-1".into(),
            appearance,
        },
    }
}
fn apply(editor: &mut Editor, id: &str, command: Command) {
    editor
        .apply(CommandEnvelope {
            command_id: id.into(),
            expected_revision: editor.document().revision,
            command,
        })
        .unwrap();
}

#[test]
fn every_independent_selection_roundtrips_with_exact_identity_on_both_b1_backends() {
    for profile in [CharacterProfile::b1(), CharacterProfile::b1_motion()] {
        for bits in 0..8 {
            let flags = (bits & 1 != 0, bits & 2 != 0, bits & 4 != 0);
            let appearance = CharacterAppearance::b1_cc0(flags.0, flags.1, flags.2);
            assert_eq!(appearance.b1_flags(), (bits != 0).then_some(flags));
            let mut document = SceneDocument::from_profile(profile.clone()).unwrap();
            document.character.appearance = appearance.clone();
            assert_eq!(
                SceneDocument::from_json(&document.to_json().unwrap()).unwrap(),
                document
            );
            let raw = serde_json::to_string(&appearance).unwrap();
            assert_eq!(
                serde_json::from_str::<CharacterAppearance>(&raw).unwrap(),
                appearance
            );
            let value: Value = serde_json::from_str(&raw).unwrap();
            if bits == 0 {
                assert_eq!(value, json!({"type":"none"}));
            } else {
                assert_eq!(value.as_object().unwrap().len(), 7);
                assert_eq!(value["schema_version"], 1);
                assert_eq!(value["asset_set_id"], "mpfb-b1-cc0-appearance-v1");
                assert_eq!(
                    value["asset_set_sha256"],
                    "c3cf2b1040eed083fb1a328f0494b0c978cec42c71f3b7c826e14992f97cef04"
                );
            }
        }
    }
    assert!(
        CharacterAppearance::None
            .validate_for(&glb().profile.backend)
            .is_ok()
    );
}

#[test]
fn appearance_decode_rejects_unknown_duplicate_missing_null_and_forged_values() {
    let canonical = serde_json::to_value(CharacterAppearance::b1_cc0(true, true, true)).unwrap();
    for key in [
        "type",
        "schema_version",
        "asset_set_id",
        "asset_set_sha256",
        "skin",
        "eyes",
        "hair",
    ] {
        let mut missing = canonical.clone();
        missing.as_object_mut().unwrap().remove(key);
        assert!(
            serde_json::from_str::<CharacterAppearance>(&missing.to_string()).is_err(),
            "missing {key}"
        );
        let mut null = canonical.clone();
        null[key] = Value::Null;
        assert!(
            serde_json::from_str::<CharacterAppearance>(&null.to_string()).is_err(),
            "null {key}"
        );
        let duplicate = format!(
            "{{\"{key}\":{},{}",
            canonical[key],
            &canonical.to_string()[1..]
        );
        assert!(
            serde_json::from_str::<CharacterAppearance>(&duplicate).is_err(),
            "duplicate {key}"
        );
    }
    for invalid in [
        json!({"type":"none","skin":false}),
        json!({"type":"none","extra":null}),
        json!({"type":"other"}),
        Value::Null,
    ] {
        assert!(serde_json::from_str::<CharacterAppearance>(&invalid.to_string()).is_err());
    }
    for (key, value) in [
        ("schema_version", json!(2)),
        ("asset_set_id", json!("other")),
        ("asset_set_sha256", json!("0".repeat(64))),
        ("skin", json!(1)),
        ("eyes", json!("true")),
        ("extra", json!(null)),
    ] {
        let mut invalid = canonical.clone();
        invalid[key] = value;
        assert!(
            serde_json::from_str::<CharacterAppearance>(&invalid.to_string()).is_err(),
            "forged {key}"
        );
    }
    let all_false = canonical.to_string().replace("true", "false");
    assert!(serde_json::from_str::<CharacterAppearance>(&all_false).is_err());
    let mut current = serde_json::to_value(b1()).unwrap();
    for appearance in [Value::Null, json!({"type":"none","extra":false})] {
        current["character"]["appearance"] = appearance;
        assert!(SceneDocument::from_json(&current.to_string()).is_err());
    }
    current["character"]
        .as_object_mut()
        .unwrap()
        .remove("appearance");
    assert!(SceneDocument::from_json(&current.to_string()).is_err());
}

#[test]
fn exact_legacy_shapes_migrate_to_none_and_never_accept_an_injected_appearance() {
    for version in [1, 2, 3] {
        let mut expected = glb();
        expected.revision = 29;
        expected.character.parameters.insert("smile".into(), 0.375);
        expected.stage = StageSettings::black_space();
        let mut legacy = serde_json::to_value(&expected).unwrap();
        legacy["schema_version"] = json!(version);
        legacy["character"]
            .as_object_mut()
            .unwrap()
            .remove("appearance");
        if version < 3 {
            legacy["profile"].as_object_mut().unwrap().remove("backend");
            legacy["character"]
                .as_object_mut()
                .unwrap()
                .remove("diagnostic_pose");
        }
        if version == 1 {
            legacy.as_object_mut().unwrap().remove("stage");
            expected.stage = StageSettings::white_studio();
        }
        assert_eq!(
            SceneDocument::from_json(&legacy.to_string()).unwrap(),
            expected
        );
        for appearance in [
            Value::Null,
            json!({"type":"none"}),
            serde_json::to_value(CharacterAppearance::b1_cc0(true, false, false)).unwrap(),
        ] {
            let mut injected = legacy.clone();
            injected["character"]["appearance"] = appearance;
            assert!(
                SceneDocument::from_json(&injected.to_string()).is_err(),
                "schema{version}"
            );
            assert!(serde_json::from_str::<SceneDocument>(&injected.to_string()).is_err());
        }
        if version == 3 {
            for key in ["backend", "diagnostic_pose"] {
                let mut missing = legacy.clone();
                missing[if key == "backend" {
                    "profile"
                } else {
                    "character"
                }]
                .as_object_mut()
                .unwrap()
                .remove(key);
                assert!(SceneDocument::from_json(&missing.to_string()).is_err());
            }
        }
    }
    // Schema3 B1 retains its backend, pose, authored timeline and stage.
    let mut expected = b1();
    expected.revision = 77;
    expected.stage = StageSettings::black_space();
    let mut legacy = serde_json::to_value(&expected).unwrap();
    legacy["schema_version"] = json!(3);
    legacy["character"]
        .as_object_mut()
        .unwrap()
        .remove("appearance");
    assert_eq!(
        SceneDocument::from_json(&legacy.to_string()).unwrap(),
        expected
    );
}

#[test]
fn appearance_transactions_preserve_other_content_and_keep_failure_history_and_retries_atomic() {
    let original = b1();
    let mut editor = Editor::new(original.clone()).unwrap();
    let selected = CharacterAppearance::b1_cc0(true, false, true);
    let request = envelope("selected", 0, selected.clone());
    let preview = editor.preview(&request.command).unwrap();
    assert_eq!(preview.character.appearance, selected);
    assert_eq!(editor.document(), &original);
    editor.apply(request.clone()).unwrap();
    let retained = editor.retention_stats();
    assert!(editor.apply(request.clone()).unwrap().duplicate);
    assert_eq!(editor.retention_stats(), retained);
    assert_eq!(editor.document().timeline, original.timeline);
    assert_eq!(
        editor.document().character.parameters,
        original.character.parameters
    );
    apply(&mut editor, "undo", Command::Undo);
    assert_eq!(
        editor.document().character.appearance,
        CharacterAppearance::None
    );
    let before = editor.document().clone();
    let retained = editor.retention_stats();
    let mut forged = selected.clone();
    if let CharacterAppearance::B1Cc0 {
        asset_set_sha256, ..
    } = &mut forged
    {
        *asset_set_sha256 = "0".repeat(64);
    }
    let failed = envelope("recoverable", before.revision, forged);
    assert_eq!(
        editor.apply(failed.clone()).unwrap_err().code,
        "unsupported_appearance_asset"
    );
    assert!(editor.preview(&failed.command).is_err());
    assert_eq!(editor.document(), &before);
    assert_eq!(editor.retention_stats(), retained);
    apply(&mut editor, "redo", Command::Redo);
    assert_eq!(editor.document().character.appearance, selected);
    // A failed ID is not reserved; a corrected payload can use it.
    editor
        .apply(envelope(
            "recoverable",
            editor.document().revision,
            CharacterAppearance::None,
        ))
        .unwrap();
    assert_eq!(
        editor.document().character.appearance,
        CharacterAppearance::None
    );
    assert_eq!(editor.apply(request.clone()).unwrap().revision, 1);
    assert_eq!(
        editor.document().character.appearance,
        CharacterAppearance::None
    );
    let mut conflict = request;
    if let Command::SetAppearance { appearance, .. } = &mut conflict.command {
        *appearance = CharacterAppearance::None;
    }
    assert_eq!(
        editor.apply(conflict).unwrap_err().code,
        "command_id_conflict"
    );
}

#[test]
fn unsupported_backend_base_identity_and_malformed_commands_fail_without_mutation() {
    let selected = CharacterAppearance::b1_cc0(false, true, false);
    let mut editor = Editor::new(glb()).unwrap();
    let before = editor.document().clone();
    let retained = editor.retention_stats();
    assert_eq!(
        editor
            .apply(envelope("unsupported", 0, selected.clone()))
            .unwrap_err()
            .code,
        "unsupported_character_operation"
    );
    assert_eq!(editor.document(), &before);
    assert_eq!(editor.retention_stats(), retained);
    assert!(
        selected
            .validate_for(&CharacterBackend::B1Cpu {
                schema_version: 1,
                asset_id: "other".into()
            })
            .is_err()
    );
    assert!(
        selected
            .validate_for(&CharacterBackend::B1Cpu {
                schema_version: 3,
                asset_id: B1_ASSET_ID.into()
            })
            .is_err()
    );
    let raw = envelope("command", 0, selected).to_json().unwrap();
    for (needle, replacement) in [
        ("\"eyes\": true", "\"eyes\": true, \"eyes\": false"),
        ("\"appearance\":", "\"extra\": null, \"appearance\":"),
        (
            "\"type\": \"set_appearance\"",
            "\"type\": \"set_appearance\", \"type\": \"undo\"",
        ),
    ] {
        assert!(raw.contains(needle));
        assert!(CommandEnvelope::from_json(&raw.replacen(needle, replacement, 1)).is_err());
    }
    let mut work = glb();
    work.character.appearance = CharacterAppearance::b1_cc0(true, false, false);
    assert_eq!(
        work.validate().unwrap_err().code,
        "unsupported_character_operation"
    );
    assert!(SceneDocument::from_json(&serde_json::to_string(&work).unwrap()).is_err());
}

#[test]
fn descriptor_and_all_payloads_are_authenticated_before_use_and_public_fields_cannot_forge_them() {
    assert_eq!(
        appearance_sha256(b"abc"),
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    );
    assert_eq!(
        appearance_sha256(B1_APPEARANCE_MANIFEST_BYTES),
        B1_APPEARANCE_MANIFEST_SHA256
    );
    let manifest = B1AppearanceManifest::from_bytes(B1_APPEARANCE_MANIFEST_BYTES).unwrap();
    assert_eq!(manifest.files.len(), 13);
    let root =
        Path::new(env!("CARGO_MANIFEST_DIR")).join("../../assets/appearances/mpfb-b1-cc0-v1");
    for path in manifest.files.keys() {
        let bytes = std::fs::read(root.join(path)).unwrap();
        manifest.validate_file_bytes(path, &bytes).unwrap();
        let mut corrupt = bytes.clone();
        corrupt[0] ^= 1;
        assert_eq!(
            manifest
                .validate_file_bytes(path, &corrupt)
                .unwrap_err()
                .code,
            "asset_hash_mismatch"
        );
        assert_eq!(
            manifest
                .validate_file_bytes(path, &bytes[..bytes.len() - 1])
                .unwrap_err()
                .code,
            "invalid_asset"
        );
        assert_eq!(
            manifest.validate_file_bytes(path, &[]).unwrap_err().code,
            "asset_missing"
        );
        let mut forged = manifest.clone();
        forged.files.get_mut(path).unwrap().sha256 = appearance_sha256(&corrupt);
        assert_eq!(
            forged.validate_file_bytes(path, &corrupt).unwrap_err().code,
            "invalid_asset"
        );
    }
    assert!(manifest.validate_file_bytes("../outside", b"x").is_err());
    assert_eq!(
        B1AppearanceManifest::from_bytes(&[]).unwrap_err().code,
        "asset_missing"
    );
    assert_eq!(
        B1AppearanceManifest::from_bytes(&vec![0; B1_APPEARANCE_MAX_MANIFEST_BYTES + 1])
            .unwrap_err()
            .code,
        "invalid_asset"
    );
    let descriptor: Value = serde_json::from_slice(B1_APPEARANCE_MANIFEST_BYTES).unwrap();
    for (key, value) in [
        ("asset_set_id", json!("other")),
        ("schema_version", json!(2)),
        ("base_asset_id", json!("other")),
        ("base_manifest_sha256", json!("0".repeat(64))),
        ("material_policy", json!("unreviewed")),
        ("extra", Value::Null),
    ] {
        let mut changed = descriptor.clone();
        changed[key] = value;
        assert_eq!(
            B1AppearanceManifest::from_bytes(changed.to_string().as_bytes())
                .unwrap_err()
                .code,
            "asset_hash_mismatch"
        );
    }
    let mut forged = manifest;
    let file = forged.files.remove("SOURCE.json").unwrap();
    forged.files.insert("../outside".into(), file);
    assert!(forged.validate_file_bytes("../outside", b"x").is_err());
}

#[test]
fn short01_all_roles_keep_exact_wire_shape_and_legacy_defaults() {
    let backend = CharacterProfile::b1_character().backend;
    assert_eq!(
        B1AppearanceSet::for_base(B1AssetVersion::V2),
        B1AppearanceSet::V2
    );
    assert_eq!(
        B1AppearanceSet::for_base(B1AssetVersion::V1),
        B1AppearanceSet::V1
    );
    for bits in 0..8 {
        let flags = (bits & 1 != 0, bits & 2 != 0, bits & 4 != 0);
        let selected = CharacterAppearance::b1_cc0_for_set(
            &backend,
            B1AppearanceSet::V2Short01,
            flags.0,
            flags.1,
            flags.2,
        )
        .unwrap();
        assert_eq!(selected.b1_flags(), (bits != 0).then_some(flags));
        assert_eq!(
            selected.b1_set(),
            (bits != 0).then_some(B1AppearanceSet::V2Short01)
        );
        let mut document = SceneDocument::from_profile(CharacterProfile::b1_character()).unwrap();
        document.character.appearance = selected.clone();
        assert_eq!(
            SceneDocument::from_json(&document.to_json().unwrap()).unwrap(),
            document
        );
        let wire = serde_json::to_value(&selected).unwrap();
        assert_eq!(
            wire.as_object().unwrap().len(),
            if bits == 0 { 1 } else { 7 }
        );
        if bits != 0 {
            assert_eq!(wire["schema_version"], 2);
            assert_eq!(wire["asset_set_id"], B1_V2_SHORT01_APPEARANCE_ID);
            assert_eq!(
                wire["asset_set_sha256"],
                B1_V2_SHORT01_APPEARANCE_MANIFEST_SHA256
            );
            assert_eq!(
                CharacterAppearance::b1_cc0_for(&backend, flags.0, flags.1, flags.2)
                    .unwrap()
                    .b1_set(),
                Some(B1AppearanceSet::V2)
            );
        }
        for incompatible in [
            CharacterProfile::b1().backend,
            CharacterProfile::b1_motion().backend,
            glb().profile.backend,
        ] {
            assert_eq!(
                CharacterAppearance::b1_cc0_for_set(
                    &incompatible,
                    B1AppearanceSet::V2Short01,
                    flags.0,
                    flags.1,
                    flags.2
                )
                .unwrap_err()
                .code,
                "unsupported_character_operation"
            );
        }
    }
}

#[test]
fn short01_strict_production_decoders_reject_forged_shapes_and_cross_base_work() {
    let mut document = SceneDocument::from_profile(CharacterProfile::b1_character()).unwrap();
    document.character.appearance = CharacterAppearance::b1_cc0_for_set(
        &document.profile.backend,
        B1AppearanceSet::V2Short01,
        true,
        true,
        true,
    )
    .unwrap();
    let canonical = serde_json::to_value(&document.character.appearance).unwrap();
    let mut invalid = Vec::new();
    for key in [
        "type",
        "schema_version",
        "asset_set_id",
        "asset_set_sha256",
        "skin",
        "eyes",
        "hair",
    ] {
        let mut missing = canonical.clone();
        missing.as_object_mut().unwrap().remove(key);
        invalid.push(missing.to_string());
        let mut null = canonical.clone();
        null[key] = Value::Null;
        invalid.push(null.to_string());
        invalid.push(format!(
            "{{\"{key}\":{},{}",
            canonical[key],
            &canonical.to_string()[1..]
        ));
    }
    for (key, value) in [
        ("schema_version", json!(1)),
        ("asset_set_id", json!(B1_V2_APPEARANCE_ID)),
        ("asset_set_sha256", json!(B1_V2_APPEARANCE_MANIFEST_SHA256)),
        ("skin", json!(1)),
        ("eyes", json!("true")),
        ("extra", Value::Null),
    ] {
        let mut forged = canonical.clone();
        forged[key] = value;
        invalid.push(forged.to_string());
    }
    invalid.push(canonical.to_string().replace("true", "false"));
    let work = document.to_json().unwrap();
    let command = envelope("strict", 0, document.character.appearance.clone())
        .to_json()
        .unwrap();
    // Inject raw JSON, preserving duplicate keys all the way into the production decoders.
    let work_value: Value = serde_json::from_str(&work).unwrap();
    let command_value: Value = serde_json::from_str(&command).unwrap();
    let compact = canonical.to_string();
    assert!(work_value.to_string().contains(&compact));
    assert!(command_value.to_string().contains(&compact));
    for raw in invalid {
        assert!(
            serde_json::from_str::<CharacterAppearance>(&raw).is_err(),
            "{raw}"
        );
        assert!(
            SceneDocument::from_json(&work_value.to_string().replacen(&compact, &raw, 1)).is_err(),
            "{raw}"
        );
        assert!(
            CommandEnvelope::from_json(&command_value.to_string().replacen(&compact, &raw, 1))
                .is_err(),
            "{raw}"
        );
    }
    for profile in [
        CharacterProfile::b1(),
        CharacterProfile::b1_motion(),
        glb().profile,
    ] {
        let mut cross = SceneDocument::from_profile(profile).unwrap();
        cross.character.appearance = document.character.appearance.clone();
        assert_eq!(
            cross.validate().unwrap_err().code,
            "unsupported_character_operation"
        );
        assert!(SceneDocument::from_json(&serde_json::to_string(&cross).unwrap()).is_err());
    }
}

#[test]
fn short01_descriptor_and_every_payload_are_pinned_and_source_bytes_preserved() {
    let set = B1AppearanceSet::V2Short01;
    assert_eq!(
        appearance_sha256(set.manifest_bytes()),
        set.manifest_sha256()
    );
    let manifest = B1AppearanceManifest::from_bytes_for(set, set.manifest_bytes()).unwrap();
    assert_eq!(manifest.files.len(), 14);
    assert_eq!(manifest.schema_version, 2);
    assert_eq!(manifest.material_policy, "simple-srgb-mask-v1");
    assert!(set.manifest_bytes().len() <= B1_APPEARANCE_MAX_MANIFEST_BYTES);
    assert!(
        manifest.files.values().map(|f| f.bytes).sum::<usize>()
            <= B1_APPEARANCE_MAX_TOTAL_ASSET_BYTES
    );
    let assets = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../assets");
    let root = assets.join(Path::new(set.manifest_path()).parent().unwrap());
    for (path, file) in &manifest.files {
        let bytes = std::fs::read(root.join(path)).unwrap();
        assert_eq!(bytes.len(), file.bytes);
        manifest.validate_file_bytes(path, &bytes).unwrap();
        let mut corrupt = bytes.clone();
        corrupt[0] ^= 1;
        assert_eq!(
            manifest
                .validate_file_bytes(path, &corrupt)
                .unwrap_err()
                .code,
            "asset_hash_mismatch"
        );
        assert_eq!(
            manifest
                .validate_file_bytes(path, &bytes[..bytes.len() - 1])
                .unwrap_err()
                .code,
            "invalid_asset"
        );
        assert_eq!(
            manifest.validate_file_bytes(path, &[]).unwrap_err().code,
            "asset_missing"
        );
        let mut forged = manifest.clone();
        forged.files.get_mut(path).unwrap().sha256 = appearance_sha256(&corrupt);
        assert_eq!(
            forged.validate_file_bytes(path, &corrupt).unwrap_err().code,
            "invalid_asset"
        );
        if path.starts_with("skins/") || path.starts_with("eyes/") || path.starts_with("licenses/")
        {
            assert_eq!(
                bytes,
                std::fs::read(assets.join("appearances/mpfb-b1-cc0-v2").join(path)).unwrap()
            );
        }
    }
    let metadata = std::fs::read(root.join("provenance/makehuman_system_assets.json")).unwrap();
    assert_eq!(metadata.len(), 39220);
    assert_eq!(
        appearance_sha256(&metadata),
        "e86f1572432cfd062f372adddba4eb7c2e2e31280e96c29291a970320e0a5df0"
    );
    assert!(
        std::fs::read(root.join("hair/short01/short01.mhclo"))
            .unwrap()
            .ends_with(b"\n\n")
    );
    let mut corrupt = set.manifest_bytes().to_vec();
    corrupt[0] ^= 1;
    assert_eq!(
        B1AppearanceManifest::from_bytes_for(set, &corrupt)
            .unwrap_err()
            .code,
        "asset_hash_mismatch"
    );
    for other in [B1AppearanceSet::V1, B1AppearanceSet::V2] {
        assert_eq!(
            B1AppearanceManifest::from_bytes_for(other, set.manifest_bytes())
                .unwrap_err()
                .code,
            "asset_hash_mismatch"
        );
        assert_eq!(
            B1AppearanceManifest::from_bytes_for(set, other.manifest_bytes())
                .unwrap_err()
                .code,
            "asset_hash_mismatch"
        );
    }
    let mut forged = manifest;
    let file = forged.files.remove("SOURCE.json").unwrap();
    forged.files.insert("../outside".into(), file);
    assert_eq!(forged.validate().unwrap_err().code, "invalid_asset");
}

#[test]
fn short01_switch_undo_redo_failed_command_and_retry_preserve_full_work() {
    let mut original =
        SceneDocument::from_json(include_str!("../../../examples/b1-character.nvwa.json")).unwrap();
    original.stage = StageSettings::black_space();
    original.revision = 17;
    let mut editor = Editor::new(original.clone()).unwrap();
    let selection = CharacterAppearance::b1_cc0_for_set(
        &original.profile.backend,
        B1AppearanceSet::V2Short01,
        true,
        false,
        true,
    )
    .unwrap();
    let request = envelope("short01", 17, selection.clone());
    let mut expected = original.clone();
    expected.character.appearance = selection.clone();
    expected.revision = 18;
    editor.apply(request.clone()).unwrap();
    assert_eq!(editor.document(), &expected);
    let stats = editor.retention_stats();
    assert!(editor.apply(request).unwrap().duplicate);
    assert_eq!(editor.retention_stats(), stats);
    apply(&mut editor, "undo-short01", Command::Undo);
    let mut undone = original.clone();
    undone.revision = 19;
    assert_eq!(editor.document(), &undone);
    let stats = editor.retention_stats();
    assert_eq!(
        editor
            .apply(envelope(
                "recoverable-short01",
                19,
                CharacterAppearance::b1_cc0(true, true, true)
            ))
            .unwrap_err()
            .code,
        "unsupported_character_operation"
    );
    assert_eq!(editor.document(), &undone);
    assert_eq!(editor.retention_stats(), stats);
    apply(&mut editor, "redo-short01", Command::Redo);
    expected.revision = 20;
    assert_eq!(editor.document(), &expected);
    editor
        .apply(envelope(
            "recoverable-short01",
            20,
            CharacterAppearance::None,
        ))
        .unwrap();
    expected.revision = 21;
    expected.character.appearance = CharacterAppearance::None;
    assert_eq!(editor.document(), &expected);
}
