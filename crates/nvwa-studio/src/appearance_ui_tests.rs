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
            // This harness inspects CPU paint only and has no GPU texture sink.
            output.drop_without_applying_deltas();
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

#[test]
fn new_character_entry_stages_eight_parameters_and_all_bilingual_controls_are_reachable() {
    use std::collections::BTreeSet;
    for size in [egui::vec2(1280.0, 720.0), egui::vec2(1024.0, 768.0)] {
        let mut app = StudioHarness::new(size);
        let old = app.editor.document().unwrap().clone();
        let output = app.frame(vec![]);
        let creation = text_rect(&output, "新建人物… / New character…");
        assert!(egui::Rect::from_min_size(egui::Pos2::ZERO, size).contains_rect(creation));
        output.drop_without_applying_deltas();
        app.click(creation.center());
        assert_eq!(
            app.editor.document(),
            Some(&old),
            "normal creation must stage, never replace current Work before assets are ready"
        );
        let pending = app.editor.pending_open.as_ref().unwrap().clone();
        assert_eq!(pending.profile, CharacterProfile::b1_character());
        app.editor.replace(pending).unwrap(); // CPU UI harness has no asset/renderer sink.
        let labels: BTreeSet<_> = [
            "躯干长度 / Torso length",
            "下颌开合 / Jaw opening",
            "头部宽度 / Head width",
            "鼻部宽度 / Nose width",
            "嘴部宽度 / Mouth width",
            "下巴宽度 / Chin width",
            "颈部宽度 / Neck width",
            "髋部宽度 / Hip width",
            "皮肤 / Skin",
            "眼睛 / Eyes",
            "头发 / Hair",
        ]
        .into_iter()
        .collect();
        let mut seen = BTreeSet::new();
        fn record(
            shape: &egui::Shape,
            clip: egui::Rect,
            wanted: &BTreeSet<&str>,
            seen: &mut BTreeSet<String>,
        ) {
            match shape {
                egui::Shape::Text(t) if wanted.contains(t.galley.job.text.as_str()) => {
                    let rect = egui::Rect::from_min_size(t.pos, t.galley.size());
                    if clip.contains_rect(rect) {
                        seen.insert(t.galley.job.text.clone());
                    }
                }
                egui::Shape::Vec(shapes) => {
                    for shape in shapes {
                        record(shape, clip, wanted, seen);
                    }
                }
                _ => {}
            }
        }
        for step in 0..12 {
            app.time = Some(1.0 + f64::from(step) * 0.2);
            let output = app.frame(if step == 0 {
                vec![]
            } else {
                vec![
                    egui::Event::PointerMoved(egui::pos2(size.x - 120.0, 240.0)),
                    egui::Event::MouseWheel {
                        unit: egui::MouseWheelUnit::Point,
                        delta: egui::vec2(0.0, -100.0),
                        modifiers: egui::Modifiers::default(),
                    },
                ]
            });
            for clipped in &output.shapes {
                record(
                    &clipped.shape,
                    clipped
                        .clip_rect
                        .intersect(egui::Rect::from_min_size(egui::Pos2::ZERO, size)),
                    &labels,
                    &mut seen,
                );
            }
            output.drop_without_applying_deltas();
        }
        assert_eq!(
            seen,
            labels.into_iter().map(str::to_owned).collect(),
            "every actual bilingual control must become fully visible through normal scrolling at {size:?}"
        );
    }
}

#[test]
fn eight_parameter_preview_commit_reset_undo_and_appearance_use_same_work_contract() {
    let mut app = StudioHarness::new(egui::vec2(1280.0, 720.0));
    app.editor
        .replace(SceneDocument::from_profile(CharacterProfile::b1_character()).unwrap())
        .unwrap();
    let before = app.editor.document().unwrap().clone();
    let mut values = before.character.parameters.clone();
    for (i, value) in values.values_mut().enumerate() {
        *value = if i % 2 == 0 { 0.7 } else { -0.6 };
    }
    app.editor.preview_parameters(values.clone()).unwrap();
    assert_eq!(app.editor.document(), Some(&before));
    assert_eq!(
        app.editor.visible_document().unwrap().character.parameters,
        values
    );
    app.editor.commit_preview().unwrap();
    assert_eq!(app.editor.document().unwrap().revision, before.revision + 1);
    app.editor
        .apply(nvwa_core::Command::SetParameters {
            character_id: before.character.id.clone(),
            values: before.character.parameters.clone(),
        })
        .unwrap();
    app.editor.apply(nvwa_core::Command::Undo).unwrap();
    assert_eq!(app.editor.document().unwrap().character.parameters, values);
    app.editor.apply(nvwa_core::Command::Redo).unwrap();
    assert_eq!(
        app.editor.document().unwrap().character.parameters,
        before.character.parameters
    );
    // The actual checkbox seam uses the v2 base identity (all controls are above the initial fold except later poses).
    app.frame(vec![]).drop_without_applying_deltas();
    let output = app.frame(vec![]);
    if let Some(rect) = output.shapes.iter().find_map(|s| match &s.shape {
        egui::Shape::Text(t) if t.galley.job.text == "皮肤 / Skin" => {
            Some(egui::Rect::from_min_size(t.pos, t.galley.size()))
        }
        _ => None,
    }) {
        output.drop_without_applying_deltas();
        app.click(rect.center());
        assert_eq!(
            app.editor.document().unwrap().character.appearance.b1_set(),
            Some(nvwa_core::B1AppearanceSet::V2)
        );
    } else {
        output.drop_without_applying_deltas();
        panic!("skin checkbox must be visible at the wide initial inspector size");
    }
}
