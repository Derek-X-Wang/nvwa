// Included in appearance_ui_tests; these exercise CPU UI and shared commands.
#[test]
fn explicit_contour_creation_and_both_hairstyles_use_existing_work_and_history() {
    use nvwa_core::{B1AppearanceSet, CharacterAppearance, Command};
    for size in [egui::vec2(1280.0, 720.0), egui::vec2(1024.0, 768.0)] {
        let mut app = StudioHarness::new(size);
        let old = app.editor.document().unwrap().clone();
        for label in ["▾", "新建脸颊人物… / New character + cheek fullness…"] {
            let output = app.frame(vec![]);
            let rect = text_rect(&output, label);
            assert!(egui::Rect::from_min_size(egui::Pos2::ZERO, size).contains_rect(rect));
            output.drop_without_applying_deltas();
            app.click(rect.center());
        }
        assert_eq!(app.editor.document(), Some(&old));
        let pending = app.editor.pending_open.as_ref().unwrap().clone();
        assert_eq!(pending.profile, CharacterProfile::b1_character_contour());
        assert_eq!(pending.character.parameters["cheek_fullness"], 0.0);
        assert!(pending.timeline[0].looping);
        assert_eq!(pending.timeline[0].duration_seconds, 4.0);
        assert_eq!(pending.character.appearance, CharacterAppearance::None);
        app.editor.replace(pending).unwrap(); // CPU harness has no asset/GPU sink.
        let before = app.editor.document().unwrap().clone();
        let mut values = before.character.parameters.clone();
        values.insert("cheek_fullness".into(), -0.35);
        app.editor.preview_parameters(values.clone()).unwrap();
        assert_eq!(app.editor.document(), Some(&before));
        assert_eq!(
            app.editor.visible_document().unwrap().character.parameters,
            values
        );
        app.editor.commit_preview().unwrap();
        assert_eq!(
            app.editor.document().unwrap().character.parameters["cheek_fullness"],
            -0.35
        );
        app.editor.apply(Command::Undo).unwrap();
        assert_eq!(
            app.editor.document().unwrap().character.parameters["cheek_fullness"],
            0.0
        );
        app.editor.apply(Command::Redo).unwrap();
        assert_eq!(
            app.editor.document().unwrap().character.parameters["cheek_fullness"],
            -0.35
        );
        // The shared controls remain reachable through ordinary scrolling.
        click_visible_appearance_control(&mut app, size, "脸颊饱满度 / Cheek fullness");
        click_visible_appearance_control(&mut app, size, "皮肤 / Skin");
        click_visible_appearance_control(&mut app, size, "头发 / Hair");
        for (label, expected) in [
            ("short01", B1AppearanceSet::V3Short01),
            ("short04", B1AppearanceSet::V3),
        ] {
            click_visible_appearance_control(&mut app, size, label);
            let doc = app.editor.document().unwrap();
            assert_eq!(doc.character.appearance.b1_set(), Some(expected));
            assert_eq!(
                doc.character.appearance.b1_flags(),
                Some((true, false, true))
            );
            assert_eq!(doc.character.parameters["cheek_fullness"], -0.35);
            assert_eq!(
                SceneDocument::from_json(&doc.to_json().unwrap()).unwrap(),
                *doc
            );
        }
    }
}
