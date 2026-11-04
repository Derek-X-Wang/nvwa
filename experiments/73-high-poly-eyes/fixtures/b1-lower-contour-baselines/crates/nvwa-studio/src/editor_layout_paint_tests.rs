//! CPU paint assertions for the production-called editor UI.
//! These observe egui shapes, not raster pixels or GPU/browser presentation.
use super::{
    egui,
    tests::{StudioHarness, pointer},
};
#[test]
fn actual_selected_tab_paint_matches_literal_click_sequence() {
    // Literal test inputs and expected outcomes are independent of layout.tab.
    let active = egui::Color32::from_rgb(17, 61, 113);
    let inactive = egui::Color32::from_rgb(149, 37, 71);
    let hovered = egui::Color32::from_rgb(31, 173, 89);
    let panel = egui::Color32::from_rgb(227, 211, 163);
    let steps = [
        (
            "initial-shape",
            None,
            [active, inactive],
            "Shape parameters",
            "Profile: nvwa-original-humanoid-v1",
        ),
        (
            "clicked-profile",
            Some("Profile"),
            [inactive, active],
            "Profile: nvwa-original-humanoid-v1",
            "Shape parameters",
        ),
        (
            "clicked-shape",
            Some("Shape"),
            [active, inactive],
            "Shape parameters",
            "Profile: nvwa-original-humanoid-v1",
        ),
    ];
    for size in [egui::vec2(1280.0, 720.0), egui::vec2(1024.0, 768.0)] {
        let mut app = StudioHarness::new(size);
        app.time = Some(1.0);
        app.ctx.set_pixels_per_point(1.0);
        app.ctx.set_theme(egui::Theme::Dark);
        app.ctx.style_mut_of(egui::Theme::Dark, |style| {
            style.animation_time = 0.0;
            style.visuals.widgets.active.bg_fill = active;
            style.visuals.widgets.inactive.bg_fill = inactive;
            style.visuals.widgets.hovered.bg_fill = hovered;
            style.visuals.panel_fill = panel;
            style.visuals.text_cursor.blink = false;
        });
        let before_work = app.editor.document().unwrap().to_json().unwrap();
        let before_history = format!("{:?}", app.editor.editor.as_ref().unwrap());
        assert!(
            app.editor
                .editor
                .as_ref()
                .unwrap()
                .retention_stats()
                .undo_snapshots
                > 0
        );
        assert!(
            app.editor
                .editor
                .as_ref()
                .unwrap()
                .retention_stats()
                .redo_snapshots
                > 0
        );
        let mut frames = 1;
        let mut output = app.frame(vec![]);
        output.textures_delta.clear();
        for (stage, click, expected, inspector, absent_inspector) in steps {
            if let Some(label) = click {
                app.click(paint_oracle_tab(&output, label).0.center());
                frames += 2;
                assert_eq!(
                    app.editor.document().unwrap().to_json().unwrap(),
                    before_work
                );
                assert_eq!(
                    format!("{:?}", app.editor.editor.as_ref().unwrap()),
                    before_history
                );
            }
            // Release and remove the pointer before observing selected paint.
            output = app.frame(vec![
                pointer(egui::pos2(1.0, 200.0), false),
                egui::Event::PointerMoved(egui::pos2(1.0, 200.0)),
                egui::Event::PointerGone,
            ]);
            output.textures_delta.clear();
            frames += 1;
            assert!(frames <= 12, "paint-oracle frame bound exceeded");
            assert_eq!(app.ctx.pixels_per_point(), 1.0);
            assert_eq!(app.ctx.input(|input| input.time), 1.0);
            assert!(!app.ctx.input(|input| input.pointer.any_down()));
            assert!(app.ctx.input(|input| input.pointer.hover_pos()).is_none());
            let shape = paint_oracle_tab(&output, "Shape");
            let profile = paint_oracle_tab(&output, "Profile");
            assert!(
                !shape.0.intersects(profile.0),
                "paint-oracle tab backgrounds overlap"
            );
            for (label, observed, wanted) in [
                ("Shape", shape, expected[0]),
                ("Profile", profile, expected[1]),
            ] {
                assert_eq!(
                    observed.1, wanted,
                    "paint-oracle fill mismatch viewport={size:?} stage={stage} tab={label}"
                );
                println!(
                    "PAINT viewport={size:?} stage={stage} tab={label} fill={:?} bounds={:?} nearby_rects={} inspector={inspector}",
                    observed.1, observed.0, observed.2
                );
            }
            assert_eq!(
                paint_oracle_text_count(&output, inspector),
                1,
                "paint-oracle inspector text missing/ambiguous: {inspector}"
            );
            assert_eq!(
                paint_oracle_text_count(&output, absent_inspector),
                0,
                "paint-oracle inactive inspector unexpectedly painted: {absent_inspector}"
            );
            assert_eq!(
                app.editor.document().unwrap().to_json().unwrap(),
                before_work
            );
            assert_eq!(
                format!("{:?}", app.editor.editor.as_ref().unwrap()),
                before_history
            );
        }
        println!(
            "INVARIANCE viewport={size:?} frames={frames} full_work=true full_history=true undo=true redo=true"
        );
    }
}

fn paint_oracle_visit(shape: &egui::Shape, visit: &mut impl FnMut(&egui::Shape)) {
    if let egui::Shape::Vec(shapes) = shape {
        for child in shapes {
            paint_oracle_visit(child, visit);
        }
    } else {
        visit(shape);
    }
}
fn paint_oracle_text_count(output: &egui::FullOutput, label: &str) -> usize {
    let mut count = 0;
    for shape in &output.shapes {
        paint_oracle_visit(&shape.shape, &mut |shape| {
            if matches!(shape, egui::Shape::Text(text) if text.galley.job.text == label) {
                count += 1;
            }
        });
    }
    count
}
fn paint_oracle_tab(output: &egui::FullOutput, label: &str) -> (egui::Rect, egui::Color32, usize) {
    let mut labels = Vec::new();
    for clipped in &output.shapes {
        paint_oracle_visit(&clipped.shape, &mut |shape| {
            if let egui::Shape::Text(text) = shape
                && text.galley.job.text == label
            {
                labels.push(text.galley.rect.translate(text.pos.to_vec2()));
            }
        });
    }
    assert_eq!(
        labels.len(),
        1,
        "paint-oracle label missing/ambiguous: {label}"
    );
    let text_rect = labels[0];
    let mut index = 0;
    let mut text_index = None;
    let mut nearby = Vec::new();
    for clipped in &output.shapes {
        paint_oracle_visit(&clipped.shape, &mut |shape| {
            if let egui::Shape::Text(text) = shape
                && text.galley.job.text == label
            {
                text_index = Some(index);
            }
            if let egui::Shape::Rect(rect) = shape
                && rect.rect.intersects(text_rect)
                && clipped.clip_rect.contains_rect(text_rect)
            {
                assert!(
                    nearby.len() < 64,
                    "paint-oracle observation exceeded 64 shapes: {label}"
                );
                nearby.push((index, rect.rect, rect.fill));
            }
            index += 1;
        });
    }
    let backgrounds: Vec<_> = nearby
        .iter()
        .filter(|(index, rect, _)| {
            *index < text_index.unwrap()
                && rect.contains_rect(text_rect)
                && rect.size() == egui::vec2(100.0, 26.0)
        })
        .collect();
    assert_eq!(
        backgrounds.len(),
        1,
        "paint-oracle background missing/ambiguous: {label}; candidates={backgrounds:?}"
    );
    (backgrounds[0].1, backgrounds[0].2, nearby.len())
}

#[test]
#[should_panic(expected = "paint-oracle label missing/ambiguous: Shape")]
fn empty_paint_output_is_rejected() {
    paint_oracle_tab(&egui::FullOutput::default(), "Shape");
}

// Rejection controls use real production output and delete/duplicate observations.
// The observer must fail loudly instead of accepting an empty or ambiguous match.
fn production_output() -> egui::FullOutput {
    let mut app = StudioHarness::new(egui::vec2(1280.0, 720.0));
    app.frame(vec![]).drop_without_applying_deltas();
    let mut output = app.frame(vec![]);
    output.textures_delta.clear();
    output
}

fn retain_leaves(shape: &mut egui::Shape, keep: &impl Fn(&egui::Shape) -> bool) {
    if let egui::Shape::Vec(children) = shape {
        for child in children.iter_mut() {
            retain_leaves(child, keep);
        }
        children.retain(keep);
    }
}

fn remove_observations(output: &mut egui::FullOutput, keep: impl Fn(&egui::Shape) -> bool) {
    for clipped in &mut output.shapes {
        retain_leaves(&mut clipped.shape, &keep);
    }
    output.shapes.retain(|clipped| keep(&clipped.shape));
}

#[test]
#[should_panic(expected = "paint-oracle label missing/ambiguous: Shape")]
fn missing_tab_label_is_rejected() {
    let mut output = production_output();
    // First prove the unmodified output has a complete observation.
    paint_oracle_tab(&output, "Shape");
    remove_observations(
        &mut output,
        |shape| !matches!(shape, egui::Shape::Text(text) if text.galley.job.text == "Shape"),
    );
    paint_oracle_tab(&output, "Shape");
}

#[test]
#[should_panic(expected = "paint-oracle background missing/ambiguous: Shape")]
fn missing_tab_background_is_rejected() {
    let mut output = production_output();
    let bounds = paint_oracle_tab(&output, "Shape").0;
    remove_observations(
        &mut output,
        |shape| !matches!(shape, egui::Shape::Rect(rect) if rect.rect == bounds),
    );
    paint_oracle_tab(&output, "Shape");
}

#[test]
#[should_panic(expected = "paint-oracle label missing/ambiguous: Shape")]
fn duplicate_tab_label_is_rejected() {
    let mut output = production_output();
    paint_oracle_tab(&output, "Shape");
    let mut duplicate = None;
    for clipped in &output.shapes {
        paint_oracle_visit(&clipped.shape, &mut |shape| {
            if matches!(shape, egui::Shape::Text(text) if text.galley.job.text == "Shape") {
                let mut copy = clipped.clone();
                copy.shape = shape.clone();
                duplicate = Some(copy);
            }
        });
    }
    output
        .shapes
        .push(duplicate.expect("production Shape text"));
    paint_oracle_tab(&output, "Shape");
}

#[test]
#[should_panic(expected = "paint-oracle background missing/ambiguous: Shape")]
fn duplicate_tab_background_is_rejected() {
    let mut output = production_output();
    let bounds = paint_oracle_tab(&output, "Shape").0;
    let mut duplicate = None;
    for clipped in &output.shapes {
        paint_oracle_visit(&clipped.shape, &mut |shape| {
            if matches!(shape, egui::Shape::Rect(rect) if rect.rect == bounds) {
                let mut copy = clipped.clone();
                copy.shape = shape.clone();
                duplicate = Some(copy);
            }
        });
    }
    // Put the duplicate before the label, where it is a second valid candidate.
    output
        .shapes
        .insert(0, duplicate.expect("production Shape background"));
    paint_oracle_tab(&output, "Shape");
}
