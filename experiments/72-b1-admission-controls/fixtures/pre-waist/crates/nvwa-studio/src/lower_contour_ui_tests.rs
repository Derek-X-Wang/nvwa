// Included in appearance_ui_tests; these exercise CPU UI and shared commands.
#[test]
fn explicit_lower_contour_creation_range_and_hairstyles_use_existing_history() {
    use nvwa_core::{B1AppearanceSet, CharacterAppearance, Command};
    for size in [egui::vec2(1280.0, 720.0), egui::vec2(1024.0, 768.0)] {
        let mut app = StudioHarness::new(size);
        let old = app.editor.document().unwrap().clone();
        for label in [
            "▾",
            "新建方正轮廓人物… / New character + lower-face squaring…",
        ] {
            let output = app.frame(vec![]);
            let rect = text_rect(&output, label);
            assert!(egui::Rect::from_min_size(egui::Pos2::ZERO, size).contains_rect(rect));
            output.drop_without_applying_deltas();
            app.click(rect.center());
        }
        assert_eq!(app.editor.document(), Some(&old));
        let pending = app.editor.pending_open.as_ref().unwrap().clone();
        assert_eq!(
            pending.profile,
            CharacterProfile::b1_character_lower_contour()
        );
        assert_eq!(pending.character.parameters["lower_face_squareness"], 0.0);
        assert!(pending.timeline[0].looping);
        assert_eq!(pending.timeline[0].duration_seconds, 4.0);
        assert_eq!(pending.character.appearance, CharacterAppearance::None);
        app.editor.replace(pending).unwrap(); // CPU harness has no asset/GPU sink.
        let before = app.editor.document().unwrap().clone();
        let spec = &before.profile.parameters[9];
        assert_eq!((spec.min, spec.max, spec.default), (0.0, 1.0, 0.0));
        let mut invalid = before.character.parameters.clone();
        invalid.insert("lower_face_squareness".into(), -0.1);
        assert!(app.editor.preview_parameters(invalid).is_err());
        assert_eq!(app.editor.document(), Some(&before));
        let mut values = before.character.parameters.clone();
        values.insert("lower_face_squareness".into(), 0.75);
        app.editor.preview_parameters(values.clone()).unwrap();
        assert_eq!(app.editor.document(), Some(&before));
        assert_eq!(
            app.editor.visible_document().unwrap().character.parameters,
            values
        );
        app.editor.commit_preview().unwrap();
        assert_eq!(
            app.editor.document().unwrap().character.parameters["lower_face_squareness"],
            0.75
        );
        app.editor.apply(Command::Undo).unwrap();
        assert_eq!(
            app.editor.document().unwrap().character.parameters["lower_face_squareness"],
            0.0
        );
        app.editor.apply(Command::Redo).unwrap();
        assert_eq!(
            app.editor.document().unwrap().character.parameters["lower_face_squareness"],
            0.75
        );
        // The shared controls remain reachable through ordinary scrolling.
        click_visible_appearance_control(&mut app, size, "下半脸轮廓方正度 / Lower-face squaring");
        click_visible_appearance_control(&mut app, size, "皮肤 / Skin");
        click_visible_appearance_control(&mut app, size, "头发 / Hair");
        for (label, expected) in [
            ("short01", B1AppearanceSet::V4Short01),
            ("short04", B1AppearanceSet::V4),
        ] {
            click_visible_appearance_control(&mut app, size, label);
            let doc = app.editor.document().unwrap();
            assert_eq!(doc.character.appearance.b1_set(), Some(expected));
            assert_eq!(
                doc.character.appearance.b1_flags(),
                Some((true, false, true))
            );
            assert_eq!(doc.character.parameters["lower_face_squareness"], 0.75);
            assert_eq!(
                SceneDocument::from_json(&doc.to_json().unwrap()).unwrap(),
                *doc
            );
        }
    }
}
