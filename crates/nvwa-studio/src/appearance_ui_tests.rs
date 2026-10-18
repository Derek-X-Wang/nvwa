//! Actual production editor controls and transactions; CPU paint, not GPU proof.
use super::tests::StudioHarness;
use bevy_egui::egui;
use nvwa_core::{CharacterProfile, SceneDocument};

fn text_rect(output: &egui::FullOutput, label: &str) -> egui::Rect {
    fn find(shape: &egui::Shape, label: &str, result: &mut Vec<egui::Rect>) {
        match shape {
            egui::Shape::Text(text) if text.galley.job.text == label => {
                result.push(egui::Rect::from_min_size(text.pos, text.galley.size()));
            }
            egui::Shape::Vec(shapes) => {
                for shape in shapes {
                    find(shape, label, result);
                }
            }
            _ => {}
        }
    }
    let mut found = Vec::new();
    for shape in &output.shapes {
        find(&shape.shape, label, &mut found);
    }
    assert_eq!(found.len(), 1, "expected one actual control label: {label}");
    found[0]
}

#[test]
fn actual_b1_checkboxes_preserve_other_roles_and_use_shared_undo_redo() {
    for size in [egui::vec2(1280.0, 720.0), egui::vec2(1024.0, 768.0)] {
        let mut app = StudioHarness::new(size);
        app.editor
            .replace(SceneDocument::from_profile(CharacterProfile::b1_motion()).unwrap())
            .unwrap();
        let viewport = egui::Rect::from_min_size(egui::Pos2::ZERO, size);
        for (label, flags) in [
            ("皮肤 / Skin", (true, false, false)),
            ("眼睛 / Eyes", (true, true, false)),
            ("头发 / Hair", (true, true, true)),
            ("Undo", (true, true, false)),
            ("Redo", (true, true, true)),
        ] {
            let output = app.frame(vec![]);
            let rect = text_rect(&output, label);
            assert!(
                viewport.contains_rect(rect),
                "control clipped at {size:?}: {label}"
            );
            let before = app.editor.document().unwrap().revision;
            app.click(rect.center());
            assert_eq!(
                app.editor
                    .document()
                    .unwrap()
                    .character
                    .appearance
                    .b1_flags(),
                Some(flags),
                "actual click failed: {label}"
            );
            assert_eq!(app.editor.document().unwrap().revision, before + 1);
            app.frame(vec![]).drop_without_applying_deltas();
        }
        let saved = app.editor.document().unwrap().to_json().unwrap();
        assert_eq!(
            SceneDocument::from_json(&saved)
                .unwrap()
                .character
                .appearance
                .b1_flags(),
            Some((true, true, true))
        );
    }
}
