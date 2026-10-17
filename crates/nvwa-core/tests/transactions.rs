use nvwa_core::*;
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;

fn profile() -> CharacterProfile {
    CharacterProfile {
        backend: CharacterBackend::Glb { schema_version: 1 },
        id: "humanoid-v1".into(),
        asset_path: "fixtures/humanoid.glb".into(),
        asset_sha256: "0".repeat(64),
        license: "CC0-1.0".into(),
        parameters: vec![
            ParameterSpec {
                id: "jaw_width".into(),
                morph_index: 0,
                min: 0.0,
                max: 1.0,
                default: 0.0,
            },
            ParameterSpec {
                id: "smile".into(),
                morph_index: 1,
                min: 0.0,
                max: 1.0,
                default: 0.0,
            },
        ],
        clips: vec![ClipSpec {
            id: "idle".into(),
            animation_index: 0,
            duration_seconds: 3.0,
        }],
    }
}

fn document() -> SceneDocument {
    SceneDocument::from_profile(profile()).unwrap()
}
fn envelope(id: &str, revision: u64, command: Command) -> CommandEnvelope {
    CommandEnvelope {
        command_id: id.into(),
        expected_revision: revision,
        command,
    }
}
fn parameters(values: &[(&str, f32)]) -> Command {
    Command::SetParameters {
        character_id: "character-1".into(),
        values: values
            .iter()
            .map(|(key, value)| (key.to_string(), *value))
            .collect(),
    }
}
fn scale(value: f32) -> Command {
    Command::SetScale {
        character_id: "character-1".into(),
        scale: value,
    }
}
fn code<T: std::fmt::Debug>(result: Result<T, CoreError>) -> String {
    result.unwrap_err().code
}

#[test]
fn defaults_and_json_roundtrip_preserve_document() {
    let original = document();
    assert_eq!(original.character.id, "character-1");
    assert_eq!(original.character.scale, 1.0);
    assert_eq!(original.timeline.len(), 1);
    assert_eq!(
        SceneDocument::from_json(&original.to_json().unwrap()).unwrap(),
        original
    );
    assert_eq!(
        CharacterProfile::from_json(&original.profile.to_json().unwrap()).unwrap(),
        original.profile
    );
    let mut no_idle = profile();
    no_idle.clips.clear();
    assert!(
        SceneDocument::from_profile(no_idle)
            .unwrap()
            .timeline
            .is_empty()
    );
}

#[test]
fn failed_multi_parameter_command_has_no_partial_mutation_or_history() {
    let mut editor = Editor::new(document()).unwrap();
    let before = editor.document().clone();
    assert_eq!(
        code(editor.apply(envelope(
            "bad",
            0,
            parameters(&[("jaw_width", 0.7), ("smile", 1.1)])
        ))),
        "out_of_range"
    );
    assert_eq!(editor.document(), &before);
    assert_eq!(
        code(editor.apply(envelope("undo", 0, Command::Undo))),
        "nothing_to_undo"
    );
    // Failed IDs are not journaled; a corrected submission can use the same ID.
    editor
        .apply(envelope(
            "bad",
            0,
            parameters(&[("jaw_width", 0.7), ("smile", 0.2)]),
        ))
        .unwrap();
    assert_eq!(editor.document().character.parameters["jaw_width"], 0.7);
    assert_eq!(editor.document().revision, 1);
}

#[test]
fn typed_and_serialized_commands_produce_identical_results() {
    let command = envelope(
        "typed",
        0,
        parameters(&[("jaw_width", 0.75), ("smile", 0.3)]),
    );
    let parsed = CommandEnvelope::from_json(&command.to_json().unwrap()).unwrap();
    assert_eq!(command, parsed);
    let mut typed = Editor::new(document()).unwrap();
    let mut json = Editor::new(document()).unwrap();
    assert_eq!(typed.apply(command).unwrap(), json.apply(parsed).unwrap());
    assert_eq!(typed.document(), json.document());
}

#[test]
fn retry_is_idempotent_even_after_later_commits_and_id_reuse_conflicts() {
    let mut editor = Editor::new(document()).unwrap();
    let first = envelope("first", 0, scale(1.5));
    let result = editor.apply(first.clone()).unwrap();
    editor.apply(envelope("second", 1, scale(2.0))).unwrap();
    let duplicate = editor.apply(first).unwrap();
    assert!(duplicate.duplicate);
    assert_eq!(duplicate.revision, result.revision);
    assert_eq!(editor.document().revision, 2);
    assert_eq!(editor.document().character.scale, 2.0);
    assert_eq!(
        code(editor.apply(envelope("first", 2, scale(1.5)))),
        "command_id_conflict"
    );
    assert_eq!(
        code(editor.apply(envelope("first", 0, scale(1.6)))),
        "command_id_conflict"
    );
    assert_eq!(
        code(editor.apply(envelope("stale", 0, scale(1.5)))),
        "revision_conflict"
    );
    assert_eq!(editor.document().revision, 2);
}

#[test]
fn undo_redo_restore_content_and_monotonically_advance_revision() {
    let mut editor = Editor::new(document()).unwrap();
    editor.apply(envelope("a", 0, scale(2.0))).unwrap();
    editor
        .apply(envelope("b", 1, parameters(&[("smile", 0.8)])))
        .unwrap();
    editor.apply(envelope("undo-b", 2, Command::Undo)).unwrap();
    assert_eq!(editor.document().revision, 3);
    assert_eq!(editor.document().character.parameters["smile"], 0.0);
    assert_eq!(editor.document().character.scale, 2.0);
    editor.apply(envelope("undo-a", 3, Command::Undo)).unwrap();
    assert_eq!(editor.document().revision, 4);
    assert_eq!(editor.document().character.scale, 1.0);
    editor.apply(envelope("redo-a", 4, Command::Redo)).unwrap();
    editor.apply(envelope("redo-b", 5, Command::Redo)).unwrap();
    assert_eq!(editor.document().revision, 6);
    assert_eq!(editor.document().character.parameters["smile"], 0.8);
    assert_eq!(editor.document().character.scale, 2.0);
    assert_eq!(
        code(editor.apply(envelope("empty-redo", 6, Command::Redo))),
        "nothing_to_redo"
    );
    editor
        .apply(envelope("undo-again", 6, Command::Undo))
        .unwrap();
    editor.apply(envelope("branch", 7, scale(3.0))).unwrap();
    assert_eq!(
        code(editor.apply(envelope("discarded-redo", 8, Command::Redo))),
        "nothing_to_redo"
    );
}

#[test]
fn slider_previews_are_one_committed_transaction() {
    let mut editor = Editor::new(document()).unwrap();
    for step in 0..=20 {
        let preview = editor
            .preview(&parameters(&[("smile", step as f32 / 20.0)]))
            .unwrap();
        assert_eq!(preview.revision, 0);
        assert_eq!(editor.document().character.parameters["smile"], 0.0);
        assert_eq!(editor.document().revision, 0);
    }
    assert_eq!(
        code(editor.preview(&parameters(&[("smile", 2.0)]))),
        "out_of_range"
    );
    editor
        .apply(envelope("drag-release", 0, parameters(&[("smile", 1.0)])))
        .unwrap();
    assert_eq!(editor.document().revision, 1);
    editor
        .apply(envelope("undo-drag", 1, Command::Undo))
        .unwrap();
    assert_eq!(editor.document().character.parameters["smile"], 0.0);
    assert_eq!(
        code(editor.apply(envelope("second-undo", 2, Command::Undo))),
        "nothing_to_undo"
    );
}

#[test]
fn unknown_fields_duplicate_keys_oversized_json_and_schema_are_rejected() {
    let original = document().to_json().unwrap();
    let mut value: serde_json::Value = serde_json::from_str(&original).unwrap();
    value["schema_version"] = 99.into();
    assert_eq!(
        code(SceneDocument::from_json(&value.to_string())),
        "unsupported_schema_version"
    );
    value["schema_version"] = nvwa_core::SCHEMA_VERSION.into();
    value["character"]["surprise"] = true.into();
    assert_eq!(
        code(SceneDocument::from_json(&value.to_string())),
        "invalid_json"
    );
    assert_eq!(
        code(CommandEnvelope::from_json(
            r#"{"command_id":"a","expected_revision":0,"command":{"type":"undo","extra":true}}"#
        )),
        "invalid_json"
    );
    let duplicate = original.replacen("\"revision\": 0", "\"revision\": 0, \"revision\": 1", 1);
    assert_eq!(code(SceneDocument::from_json(&duplicate)), "invalid_json");
    let duplicated_parameter =
        original.replacen("\"smile\": 0.0", "\"smile\": 0.0, \"smile\": 0.5", 1);
    assert_eq!(
        code(SceneDocument::from_json(&duplicated_parameter)),
        "invalid_json"
    );
    assert_eq!(
        code(SceneDocument::from_json(&" ".repeat(MAX_JSON_BYTES + 1))),
        "input_too_large"
    );
}

#[test]
fn profile_ids_paths_hashes_defaults_and_references_are_strict() {
    for path in [
        "",
        "/asset.glb",
        "../asset.glb",
        "x/../asset.glb",
        "./asset.glb",
        "x//asset.glb",
        "C:/asset.glb",
        "x\\asset.glb",
        "https://x/a.glb",
        "x/%2e%2e/a.glb",
    ] {
        let mut p = profile();
        p.asset_path = path.into();
        assert_eq!(code(p.validate()), "unsafe_asset_path", "{path}");
    }
    let mut p = profile();
    p.id = " ".into();
    assert_eq!(code(p.validate()), "invalid_id");
    let mut p = profile();
    p.asset_sha256 = "g".repeat(64);
    assert_eq!(code(p.validate()), "invalid_asset_hash");
    let mut p = profile();
    p.parameters.push(p.parameters[0].clone());
    assert_eq!(code(p.validate()), "duplicate_id");
    let mut p = profile();
    p.parameters[1].morph_index = 0;
    assert_eq!(code(p.validate()), "duplicate_morph_index");
    let mut p = profile();
    p.parameters[0].default = 1.1;
    assert_eq!(code(p.validate()), "out_of_range");
    let mut d = document();
    d.character.profile_id = "missing".into();
    assert_eq!(code(d.validate()), "invalid_reference");
    let mut d = document();
    d.character.parameters.remove("smile");
    assert_eq!(code(d.validate()), "missing_parameter");
    let mut d = document();
    d.character.parameters.insert("missing".into(), 0.2);
    assert_eq!(code(d.validate()), "invalid_reference");
}

#[test]
fn nonfinite_ranges_invalid_timeline_and_overflow_never_mutate() {
    let mut editor = Editor::new(document()).unwrap();
    for value in [f32::NAN, f32::INFINITY, f32::NEG_INFINITY] {
        assert_eq!(
            code(editor.apply(envelope("bad", 0, scale(value)))),
            "nonfinite_value"
        );
        assert_eq!(
            code(envelope("bad", 0, parameters(&[("smile", value)])).to_json()),
            "nonfinite_value"
        );
    }
    for value in [0.0, -1.0] {
        assert_eq!(
            code(editor.apply(envelope("bad", 0, scale(value)))),
            "out_of_range"
        );
    }
    let mut clips = document().timeline;
    clips[0].clip_id = "unknown".into();
    assert_eq!(
        code(editor.apply(envelope("bad", 0, Command::SetTimeline { clips }))),
        "invalid_reference"
    );
    let mut clips = document().timeline;
    clips[0].duration_seconds = -1.0;
    assert_eq!(
        code(editor.apply(envelope("bad", 0, Command::SetTimeline { clips }))),
        "out_of_range"
    );
    let mut clips = document().timeline;
    clips.push(clips[0].clone());
    assert_eq!(
        code(editor.apply(envelope("bad", 0, Command::SetTimeline { clips }))),
        "duplicate_id"
    );
    let mut clips = document().timeline;
    clips[0].start_seconds = f32::MAX;
    clips[0].duration_seconds = f32::MAX;
    assert_eq!(
        code(editor.apply(envelope("bad", 0, Command::SetTimeline { clips }))),
        "nonfinite_value"
    );
    assert_eq!(editor.document(), &document());
    let mut d = document();
    d.revision = u64::MAX;
    let mut full = Editor::new(d.clone()).unwrap();
    assert_eq!(
        code(full.apply(envelope("overflow", u64::MAX, scale(2.0)))),
        "revision_overflow"
    );
    assert_eq!(full.document(), &d);
}

fn glb(json: serde_json::Value) -> Vec<u8> {
    let mut json = serde_json::to_vec(&json).unwrap();
    while !json.len().is_multiple_of(4) {
        json.push(b' ');
    }
    let mut bytes = b"glTF".to_vec();
    bytes.extend(2u32.to_le_bytes());
    bytes.extend(((20 + json.len()) as u32).to_le_bytes());
    bytes.extend((json.len() as u32).to_le_bytes());
    bytes.extend(0x4e4f534au32.to_le_bytes());
    bytes.extend(json);
    bytes
}
fn asset_json() -> serde_json::Value {
    serde_json::json!({"asset":{"version":"2.0"}, "meshes":[{"primitives":[{"targets":[{},{}]}]}], "animations":[{"channels":[{}]}]})
}
fn hashed_profile(bytes: &[u8]) -> CharacterProfile {
    let mut profile = profile();
    profile.asset_sha256 = format!("{:x}", Sha256::digest(bytes));
    profile
}

#[test]
fn missing_corrupt_and_mismatched_assets_are_rejected() {
    assert_eq!(code(profile().validate_asset_bytes(&[])), "missing_asset");
    let bytes = glb(asset_json());
    let p = hashed_profile(&bytes);
    p.validate_asset_bytes(&bytes).unwrap();
    let mut corrupted = bytes.clone();
    *corrupted.last_mut().unwrap() ^= 1;
    assert_eq!(
        code(p.validate_asset_bytes(&corrupted)),
        "asset_hash_mismatch"
    );
    let mut malformed = bytes.clone();
    malformed[8..12].copy_from_slice(&1u32.to_le_bytes());
    assert_eq!(
        code(hashed_profile(&malformed).validate_asset_bytes(&malformed)),
        "invalid_asset"
    );
    assert_eq!(
        code(hashed_profile(b"garbage").validate_asset_bytes(b"garbage")),
        "invalid_asset"
    );
    let mut p = p.clone();
    p.parameters[1].morph_index = 2;
    assert_eq!(code(p.validate_asset_bytes(&bytes)), "invalid_morph_index");
    let mut p = hashed_profile(&bytes);
    p.clips[0].animation_index = 1;
    assert_eq!(
        code(p.validate_asset_bytes(&bytes)),
        "invalid_animation_index"
    );
    let mut json = asset_json();
    json["buffers"] = serde_json::json!([{"uri":"../private.bin"}]);
    let external = glb(json);
    assert_eq!(
        code(hashed_profile(&external).validate_asset_bytes(&external)),
        "external_asset_reference"
    );
}

#[test]
fn valid_timeline_command_is_undoable_and_invalid_character_is_rejected() {
    let mut editor = Editor::new(document()).unwrap();
    let before = editor.document().timeline.clone();
    editor
        .apply(envelope("clear", 0, Command::SetTimeline { clips: vec![] }))
        .unwrap();
    assert!(editor.document().timeline.is_empty());
    editor.apply(envelope("restore", 1, Command::Undo)).unwrap();
    assert_eq!(editor.document().timeline, before);
    assert_eq!(
        code(editor.apply(envelope(
            "bad-character",
            2,
            Command::SetParameters {
                character_id: "missing".into(),
                values: BTreeMap::new()
            }
        ))),
        "invalid_reference"
    );
    assert_eq!(
        code(editor.apply(envelope("", 2, scale(1.0)))),
        "invalid_id"
    );
}

#[test]
fn single_and_batch_command_parsers_reject_duplicate_parameter_keys() {
    // A plain Serde map would silently replace 99 with 0.5 and accept this edit.
    let ambiguous = r#"{"command_id":"ambiguous","expected_revision":0,"command":{"type":"set_parameters","character_id":"character-1","values":{"smile":99,"smile":0.5}}}"#;
    let single_error = CommandEnvelope::from_json(ambiguous).unwrap_err();
    assert_eq!(single_error.code, "invalid_json");
    assert!(single_error.message.contains("duplicate object key: smile"));
    let batch_error = CommandEnvelope::batch_from_json(&format!("[{ambiguous}]")).unwrap_err();
    assert_eq!(batch_error.code, "invalid_json");
    assert!(batch_error.message.contains("duplicate object key: smile"));
    let valid = envelope("valid", 0, scale(1.5)).to_json().unwrap();
    // Strictness applies throughout the entire array, including a later command.
    let batch_error =
        CommandEnvelope::batch_from_json(&format!("[{valid},{ambiguous}]")).unwrap_err();
    assert_eq!(batch_error.code, "invalid_json");
    assert!(batch_error.message.contains("duplicate object key: smile"));
}

#[test]
fn batch_parser_matches_single_envelopes_and_bounds_whole_input() {
    let first = envelope("first", 0, parameters(&[("smile", 0.5)]));
    let second = envelope("second", 1, scale(1.5));
    let batch = format!(
        "[{},{}]",
        first.to_json().unwrap(),
        second.to_json().unwrap()
    );
    assert_eq!(
        CommandEnvelope::batch_from_json(&batch).unwrap(),
        vec![first, second]
    );
    assert!(CommandEnvelope::batch_from_json("[]").unwrap().is_empty());
    let invalid_id = r#"[{"command_id":" ","expected_revision":0,"command":{"type":"undo"}}]"#;
    assert_eq!(
        code(CommandEnvelope::batch_from_json(invalid_id)),
        "invalid_id"
    );
    assert_eq!(
        code(CommandEnvelope::batch_from_json(
            &" ".repeat(MAX_JSON_BYTES + 1)
        )),
        "input_too_large"
    );
    assert_eq!(
        code(CommandEnvelope::batch_from_json(
            r#"[{"command_id":"a","expected_revision":0,"command":{"type":"redo","unknown":true}}]"#
        )),
        "invalid_json"
    );
}
