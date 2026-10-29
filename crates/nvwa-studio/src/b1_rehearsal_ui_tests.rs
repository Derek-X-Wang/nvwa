//! Production egui commands and CPU paint; Web/GPU acceptance is separate.
use super::tests::StudioHarness;
use bevy_egui::egui;
use nvwa_core::{B1AppearanceSet, CharacterAppearance, CharacterProfile, SceneDocument};

fn text_rects(output: &egui::FullOutput, label: &str) -> Vec<egui::Rect> {
    fn find(shape: &egui::Shape, clip: egui::Rect, label: &str, out: &mut Vec<egui::Rect>) {
        match shape {
            egui::Shape::Text(text) if text.galley.job.text == label => {
                let rect = egui::Rect::from_min_size(text.pos, text.galley.size());
                if clip.contains_rect(rect) {
                    out.push(rect);
                }
            }
            egui::Shape::Vec(shapes) => {
                for shape in shapes {
                    find(shape, clip, label, out);
                }
            }
            _ => {}
        }
    }
    let mut out = Vec::new();
    for shape in &output.shapes {
        find(&shape.shape, shape.clip_rect, label, &mut out);
    }
    out
}

fn click(app: &mut StudioHarness, label: &str, index: usize) {
    let output = app.frame(vec![]);
    let rects = text_rects(&output, label);
    assert!(
        rects.len() > index,
        "missing visible control {label}[{index}]"
    );
    let position = rects[index].center();
    output.drop_without_applying_deltas();
    app.click(position);
}

fn assert_preserved(app: &StudioHarness, original: &SceneDocument) {
    let current = app.editor.document().unwrap();
    let mut expected = original.clone();
    expected.revision = current.revision;
    expected.timeline = current.timeline.clone();
    assert_eq!(
        current, &expected,
        "timeline edits changed other Work content"
    );
    let saved = current.to_json().unwrap();
    assert_eq!(&SceneDocument::from_json(&saved).unwrap(), current);
}

fn assert_rehearsal(app: &StudioHarness) {
    let doc = app.editor.document().unwrap();
    assert!(!doc.is_single_loop());
    assert_eq!(doc.timeline_duration_seconds(), 8.0);
    assert_eq!(doc.timeline.len(), 2);
    for (i, id) in ["b1_arm_rehearsal_v1", "b1_knee_flex_v1"]
        .iter()
        .enumerate()
    {
        let entry = &doc.timeline[i];
        assert_eq!(entry.clip_id, *id);
        assert_eq!(entry.start_seconds, i as f32 * 4.0);
        assert_eq!(entry.duration_seconds, 4.0);
        assert_eq!(entry.speed, 1.0);
        assert!(!entry.looping);
    }
    assert_ne!(doc.timeline[0].id, doc.timeline[1].id);
}

#[test]
fn actual_b1_rehearsal_create_restore_rows_and_history_preserve_edited_work() {
    for size in [egui::vec2(1280.0, 720.0), egui::vec2(1024.0, 768.0)] {
        for set in [B1AppearanceSet::V2Short01, B1AppearanceSet::V2] {
            let mut app = StudioHarness::new(size);
            let mut original =
                SceneDocument::from_profile(CharacterProfile::b1_character()).unwrap();
            original.character.id = "edited-current-work".into();
            assert_eq!(original.character.parameters.len(), 8);
            for (i, value) in original.character.parameters.values_mut().enumerate() {
                *value = if i % 2 == 0 { 0.65 } else { -0.45 };
            }
            original.character.scale = 1.2;
            original.character.appearance = CharacterAppearance::b1_cc0_for_set(
                &original.profile.backend,
                set,
                true,
                false,
                true,
            )
            .unwrap();
            original.stage.camera.azimuth_degrees = -23.0;
            original.stage.background_color_srgb = [0.1, 0.2, 0.3];
            app.editor.replace(original.clone()).unwrap();
            app.editor
                .apply(nvwa_core::Command::SetScale {
                    character_id: original.character.id.clone(),
                    scale: 1.3,
                })
                .unwrap();
            let original = app.editor.document().unwrap().clone();
            app.frame(vec![]).drop_without_applying_deltas();
            let before = app.editor.document().unwrap().revision;
            click(&mut app, "Create 8s rehearsal", 0);
            assert_eq!(app.editor.document().unwrap().revision, before + 1);
            assert_rehearsal(&app);
            assert_preserved(&app, &original);
            let rehearsal = app.editor.document().unwrap().timeline.clone();
            let unchanged = app.editor.document().unwrap().clone();
            click(&mut app, "Create 8s rehearsal", 0);
            assert_eq!(app.editor.document(), Some(&unchanged));
            click(&mut app, "Undo", 0);
            assert_eq!(app.editor.document().unwrap().timeline, original.timeline);
            click(&mut app, "Undo", 0);
            assert_eq!(app.editor.document().unwrap().character.scale, 1.2);
            click(&mut app, "Redo", 0);
            assert_eq!(app.editor.document().unwrap().character.scale, 1.3);
            click(&mut app, "Redo", 0);
            assert_rehearsal(&app);

            // Exercise existing row commands through their actual controls.
            click(&mut app, "+0.5s", 0);
            assert_eq!(
                app.editor.document().unwrap().timeline[0].duration_seconds,
                4.5
            );
            assert_eq!(
                app.editor.document().unwrap().timeline[1].start_seconds,
                4.5
            );
            click(&mut app, "↓", 0);
            assert_eq!(
                app.editor.document().unwrap().timeline[0].clip_id,
                "b1_knee_flex_v1"
            );
            assert_eq!(
                app.editor.document().unwrap().timeline[1].start_seconds,
                4.0
            );
            click(&mut app, "b1_arm_rehearsal_v1", 0);
            // The first knee label is the other row; the last is the popup choice.
            let output = app.frame(vec![]);
            let choices = text_rects(&output, "b1_knee_flex_v1");
            assert_eq!(choices.len(), 2);
            let choice = choices.last().unwrap().center();
            output.drop_without_applying_deltas();
            app.click(choice);
            assert_eq!(
                app.editor.document().unwrap().timeline[1].clip_id,
                "b1_knee_flex_v1"
            );
            click(&mut app, "Undo", 0);
            assert_eq!(
                app.editor.document().unwrap().timeline[1].clip_id,
                "b1_arm_rehearsal_v1"
            );
            click(&mut app, "Redo", 0);
            assert_eq!(
                app.editor.document().unwrap().timeline[1].clip_id,
                "b1_knee_flex_v1"
            );
            assert_preserved(&app, &original);
            click(&mut app, "Remove", 0);
            click(&mut app, "Remove", 0);
            assert!(app.editor.document().unwrap().timeline.is_empty());
            click(&mut app, "Create 8s rehearsal", 0);
            assert_rehearsal(&app);
            assert_eq!(app.editor.document().unwrap().timeline, rehearsal);
            click(&mut app, "Undo", 0);
            assert!(app.editor.document().unwrap().timeline.is_empty());
            click(&mut app, "Redo", 0);
            assert_rehearsal(&app);
            assert_preserved(&app, &original);
        }
    }
}

#[test]
fn actual_rehearsal_button_keeps_glb_and_static_b1_capability_boundaries() {
    let glb = CharacterProfile::from_json(include_str!("../../../assets/character.profile.json"))
        .unwrap();
    for profile in [glb, CharacterProfile::b1(), CharacterProfile::b1_motion()] {
        let mut app = StudioHarness::new(egui::vec2(1280.0, 720.0));
        let original = SceneDocument::from_profile(profile).unwrap();
        app.editor.replace(original.clone()).unwrap();
        app.frame(vec![]).drop_without_applying_deltas();
        let output = app.frame(vec![]);
        assert_eq!(
            text_rects(&output, "Create 8s rehearsal").len(),
            usize::from(original.profile.backend.is_b1_motion())
        );
        assert_eq!(
            text_rects(&output, "Create 9s sequence").len(),
            usize::from(original.profile.backend.is_glb())
        );
        output.drop_without_applying_deltas();
        if original.profile.backend.is_glb() {
            click(&mut app, "Create 9s sequence", 0);
            assert_eq!(
                app.editor.document().unwrap().timeline_duration_seconds(),
                9.0
            );
            assert_eq!(
                app.editor
                    .document()
                    .unwrap()
                    .timeline
                    .iter()
                    .map(|e| e.clip_id.as_str())
                    .collect::<Vec<_>>(),
                ["idle", "wave", "turn"]
            );
        } else if original.profile.backend.is_b1_motion() {
            click(&mut app, "Create 8s rehearsal", 0);
            assert_rehearsal(&app);
        } else {
            assert_eq!(app.editor.document(), Some(&original));
        }
        assert_preserved(&app, &original);
    }
}

#[test]
fn actual_b1_rehearsal_restores_from_motion_profile_diagnostic_mode() {
    let mut app = StudioHarness::new(egui::vec2(1024.0, 768.0));
    let mut original = SceneDocument::from_profile(CharacterProfile::b1_character()).unwrap();
    original.character.diagnostic_pose = Some("elbow".into());
    original.timeline.clear();
    app.editor.replace(original.clone()).unwrap();
    app.frame(vec![]).drop_without_applying_deltas();
    click(&mut app, "Create 8s rehearsal", 0);
    assert_rehearsal(&app);
    assert_preserved(&app, &original);
    click(&mut app, "Undo", 0);
    let mut restored = original.clone();
    restored.revision = app.editor.document().unwrap().revision;
    assert_eq!(app.editor.document(), Some(&restored));
    click(&mut app, "Redo", 0);
    assert_rehearsal(&app);
    assert_preserved(&app, &original);
}
