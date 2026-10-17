use super::*;

fn apply(editor: &mut Editor, command: Command) {
    editor
        .apply(CommandEnvelope {
            command_id: format!("motion-{}", editor.document().revision),
            expected_revision: editor.document().revision,
            command,
        })
        .unwrap();
}
#[test]
fn versioned_motion_is_same_asset_and_static_identity_is_immutable() {
    let static_profile = CharacterProfile::b1();
    let motion = CharacterProfile::b1_motion();
    assert_ne!(motion.id, static_profile.id);
    assert_eq!(motion.asset_path, static_profile.asset_path);
    assert_eq!(motion.asset_sha256, static_profile.asset_sha256);
    assert!(static_profile.clips.is_empty());
    assert_eq!(motion.clips.len(), 2);
    let document = SceneDocument::from_profile(motion.clone()).unwrap();
    assert_eq!(document.timeline.len(), 1);
    assert_eq!(
        SceneDocument::from_json(&document.to_json().unwrap()).unwrap(),
        document
    );
    let mut bad = motion.clone();
    bad.clips[0].duration_seconds = 3.0;
    assert!(bad.validate().is_err());
    let mut bad = motion.clone();
    bad.clips.pop();
    assert!(bad.validate().is_err());
    let mut bad = motion.clone();
    bad.clips[0].id = "unknown".into();
    assert!(bad.validate().is_err());
    let mut bad = motion.clone();
    bad.id = B1_PROFILE_ID.into();
    assert_eq!(
        bad.validate().unwrap_err().code,
        "unsupported_character_version"
    );
    let mut bad = static_profile;
    bad.clips = motion.clips.clone();
    assert!(bad.validate().is_err());
    let mut bad = motion;
    bad.backend = CharacterBackend::B1Cpu {
        schema_version: 3,
        asset_id: B1_ASSET_ID.into(),
    };
    assert_eq!(
        bad.validate().unwrap_err().code,
        "unsupported_character_version"
    );
}
#[test]
fn diagnostic_switch_is_one_atomic_edit_and_undo_restores_dormant_pose_and_timeline() {
    let original = SceneDocument::from_profile(CharacterProfile::b1_motion()).unwrap();
    let mut editor = Editor::new(original.clone()).unwrap();
    apply(
        &mut editor,
        Command::SetDiagnosticPose {
            character_id: original.character.id.clone(),
            pose_id: "knee".into(),
        },
    );
    assert!(editor.document().timeline.is_empty());
    assert_eq!(
        editor.document().character.diagnostic_pose.as_deref(),
        Some("knee")
    );
    apply(&mut editor, Command::Undo);
    assert_eq!(editor.document().timeline, original.timeline);
    assert_eq!(
        editor.document().character.diagnostic_pose,
        original.character.diagnostic_pose
    );
    apply(&mut editor, Command::Redo);
    assert!(editor.document().timeline.is_empty());
    let before = editor.document().clone();
    let result = editor.apply(CommandEnvelope {
        command_id: "bad".into(),
        expected_revision: before.revision,
        command: Command::SetDiagnosticPose {
            character_id: before.character.id.clone(),
            pose_id: "bad".into(),
        },
    });
    assert!(result.is_err());
    assert_eq!(editor.document(), &before);
}
#[test]
fn shape_edits_preserve_motion_and_static_work_still_rejects_timeline() {
    let original = SceneDocument::from_profile(CharacterProfile::b1_motion()).unwrap();
    let mut editor = Editor::new(original.clone()).unwrap();
    apply(
        &mut editor,
        Command::SetParameters {
            character_id: original.character.id.clone(),
            values: [("torso_length".into(), 0.5)].into_iter().collect(),
        },
    );
    assert_eq!(editor.document().timeline, original.timeline);
    assert_eq!(
        editor.document().character.diagnostic_pose,
        original.character.diagnostic_pose
    );
    let mut old = SceneDocument::from_profile(CharacterProfile::b1()).unwrap();
    old.timeline = original.timeline;
    assert_eq!(
        old.validate().unwrap_err().code,
        "unsupported_character_operation"
    );
}
