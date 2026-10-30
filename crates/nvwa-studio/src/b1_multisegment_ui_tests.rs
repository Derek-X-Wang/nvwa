//! Real egui input against the production editor; no renderer or desktop claim.
use super::*;

struct Harness {
    ctx: egui::Context,
    size: egui::Vec2,
    editor: EditorState,
    state: StudioUi,
    playback: Playback,
    io: PlatformIo,
    guard: UiInputGuard,
}
impl Harness {
    fn new(size: egui::Vec2, doc: SceneDocument) -> Self {
        let mut editor = EditorState::default();
        editor.replace(doc).unwrap();
        Self {
            ctx: default(),
            size,
            editor,
            state: default(),
            playback: default(),
            io: default(),
            guard: default(),
        }
    }
    fn frame(&mut self, events: Vec<egui::Event>) -> egui::FullOutput {
        self.ctx.run_ui(
            egui::RawInput {
                screen_rect: Some(egui::Rect::from_min_size(egui::Pos2::ZERO, self.size)),
                events,
                ..default()
            },
            |ui| {
                draw_editor_ui(
                    ui.ctx(),
                    &RuntimeStatus {
                        ready: true,
                        ..default()
                    },
                    &default(),
                    EditorUiSession {
                        editor: &mut self.editor,
                        playback: &mut self.playback,
                        state: &mut self.state,
                        io: &mut self.io,
                        guard: &mut self.guard,
                    },
                )
                .unwrap();
            },
        )
    }
    fn click_at(&mut self, pos: egui::Pos2) {
        for pressed in [true, false] {
            self.frame(vec![
                egui::Event::PointerMoved(pos),
                egui::Event::PointerButton {
                    pos,
                    button: egui::PointerButton::Primary,
                    pressed,
                    modifiers: default(),
                },
            ])
            .drop_without_applying_deltas();
        }
    }
    fn click(&mut self, label: &str, index: usize) {
        let output = self.frame(vec![]);
        let rects = visible_text(&output, label);
        assert!(rects.len() > index, "missing visible {label}[{index}]");
        let pos = rects[index].center();
        output.drop_without_applying_deltas();
        self.click_at(pos);
    }
    fn append(&mut self, clip: &str) {
        self.click("Append action…", 0);
        let output = self.frame(vec![]);
        let rects = visible_text(&output, clip);
        let pos = rects.last().expect("append choice").center();
        output.drop_without_applying_deltas();
        self.click_at(pos);
    }
    fn doc(&self) -> &SceneDocument {
        self.editor.document().unwrap()
    }
}
fn visible_text(output: &egui::FullOutput, label: &str) -> Vec<egui::Rect> {
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
    let mut out = vec![];
    for shape in &output.shapes {
        find(&shape.shape, shape.clip_rect, label, &mut out);
    }
    out
}
fn edited_work() -> SceneDocument {
    let mut doc = SceneDocument::from_profile(nvwa_core::CharacterProfile::b1_character()).unwrap();
    doc.character.id = "edited-current-work".into();
    assert_eq!(doc.character.parameters.len(), 8);
    for (i, value) in doc.character.parameters.values_mut().enumerate() {
        *value = if i % 2 == 0 { 0.6 } else { -0.4 };
    }
    doc.character.scale = 1.25;
    doc.character.appearance = nvwa_core::CharacterAppearance::b1_cc0_for_set(
        &doc.profile.backend,
        nvwa_core::B1AppearanceSet::V2Short01,
        true,
        false,
        true,
    )
    .unwrap();
    doc.character.diagnostic_pose = Some("elbow".into());
    doc.stage.camera.azimuth_degrees = -21.0;
    doc.stage.background_color_srgb = [0.2, 0.1, 0.3];
    doc
}
fn assert_preserved(app: &Harness, original: &SceneDocument) {
    let mut expected = original.clone();
    expected.revision = app.doc().revision;
    expected.timeline = app.doc().timeline.clone();
    assert_eq!(app.doc(), &expected);
    assert_eq!(
        SceneDocument::from_json(&app.doc().to_json().unwrap()).unwrap(),
        *app.doc()
    );
}
fn assert_finite_contiguous(doc: &SceneDocument) {
    let mut start = 0.0;
    let mut ids = std::collections::BTreeSet::new();
    for entry in &doc.timeline {
        assert!(!entry.looping);
        assert_eq!(entry.start_seconds, start);
        assert!(!entry.id.trim().is_empty());
        assert!(ids.insert(&entry.id), "duplicate timeline ID");
        start += entry.duration_seconds;
    }
}
#[test]
fn actual_multisegment_append_empty_and_single_loop_preserves_work_and_history() {
    for size in [egui::vec2(1280.0, 720.0), egui::vec2(1024.0, 768.0)] {
        for empty in [true, false] {
            let mut original = edited_work();
            if empty {
                original.timeline.clear();
            } else {
                assert!(original.is_single_loop());
                original.timeline[0].duration_seconds = 5.5;
                original.timeline[0].speed = 0.75;
                original.timeline[0].id = "sequence-1".into();
            }
            let mut app = Harness::new(size, original.clone());
            app.frame(vec![]).drop_without_applying_deltas();
            app.append("b1_knee_flex_v1");
            assert_eq!(app.doc().revision, original.revision + 1);
            assert_eq!(app.doc().timeline.len(), if empty { 1 } else { 2 });
            let tail = app.doc().timeline.last().unwrap();
            assert_eq!(tail.clip_id, "b1_knee_flex_v1");
            assert_eq!(tail.duration_seconds, 4.0);
            assert_eq!(tail.speed, 1.0);
            if !empty {
                assert_eq!(app.doc().timeline[0].duration_seconds, 5.5);
                assert_eq!(app.doc().timeline[0].speed, 0.75);
                assert_eq!(app.doc().timeline[0].clip_id, original.timeline[0].clip_id);
            }
            assert_finite_contiguous(app.doc());
            assert_preserved(&app, &original);
            let appended = app.doc().timeline.clone();
            app.click("Undo", 0);
            assert_eq!(app.doc().timeline, original.timeline);
            app.click("Redo", 0);
            assert_eq!(app.doc().timeline, appended);
            assert_preserved(&app, &original);
        }
    }
}
#[test]
fn actual_multisegment_duplicate_single_loop_and_middle_row_uses_fresh_ids_and_one_undo() {
    for single in [true, false] {
        let mut original = edited_work();
        if !single {
            original.timeline = b1_eight_second_rehearsal();
        }
        original.timeline[0].duration_seconds = 5.5;
        original.timeline[0].speed = 0.75;
        // Occupy candidate IDs out of visual order, including the final candidate.
        original.timeline[0].id = "sequence-2".into();
        if !single {
            original.timeline[1].id = "sequence-1".into();
            original.timeline[1].start_seconds = 5.5;
        }
        let mut app = Harness::new(egui::vec2(1280.0, 720.0), original.clone());
        app.frame(vec![]).drop_without_applying_deltas();
        app.click("Duplicate", 0);
        assert_eq!(app.doc().revision, original.revision + 1);
        assert_eq!(app.doc().timeline.len(), original.timeline.len() + 1);
        let mut expected = original.timeline[0].clone();
        expected.looping = false;
        assert_eq!(app.doc().timeline[0], expected);
        expected.id = app.doc().timeline[1].id.clone();
        expected.start_seconds = 5.5;
        assert_eq!(app.doc().timeline[1], expected);
        if !single {
            assert_eq!(app.doc().timeline[2].clip_id, original.timeline[1].clip_id);
        }
        assert_finite_contiguous(app.doc());
        assert_preserved(&app, &original);
        let duplicated = app.doc().timeline.clone();
        app.click("Undo", 0);
        assert_eq!(app.doc().timeline, original.timeline);
        app.click("Redo", 0);
        assert_eq!(app.doc().timeline, duplicated);
        if !single {
            // Duplicate the middle of three rows, keeping the former tail last.
            app.click("Duplicate", 1);
            assert_eq!(app.doc().timeline.len(), 4);
            let mut expected = duplicated[1].clone();
            expected.id = app.doc().timeline[2].id.clone();
            expected.start_seconds = 11.0;
            assert_eq!(app.doc().timeline[2], expected);
            assert_eq!(app.doc().timeline[3].clip_id, duplicated[2].clip_id);
            assert_finite_contiguous(app.doc());
            app.click("Undo", 0);
            assert_eq!(app.doc().timeline, duplicated);
        }
    }
}
#[test]
fn actual_multisegment_five_rows_twenty_seconds_and_scroll_reach_last_controls() {
    for size in [egui::vec2(1280.0, 720.0), egui::vec2(1024.0, 768.0)] {
        let mut original = edited_work();
        original.timeline.clear();
        let mut app = Harness::new(size, original.clone());
        app.frame(vec![]).drop_without_applying_deltas();
        for clip in [
            "b1_knee_flex_v1",
            "b1_arm_rehearsal_v1",
            "b1_knee_flex_v1",
            "b1_arm_rehearsal_v1",
            "b1_knee_flex_v1",
        ] {
            app.append(clip);
        }
        assert_eq!(app.doc().timeline.len(), 5);
        assert_eq!(app.doc().timeline_duration_seconds(), 20.0);
        assert_eq!(app.doc().timeline[0].clip_id, "b1_knee_flex_v1");
        assert_eq!(app.doc().timeline[3].clip_id, "b1_arm_rehearsal_v1");
        assert_finite_contiguous(app.doc());
        // Actual wheel input must bring the tail row and its controls into view.
        for _ in 0..8 {
            app.frame(vec![
                egui::Event::PointerMoved(egui::pos2(size.x * 0.6, size.y - 55.0)),
                egui::Event::MouseWheel {
                    unit: egui::MouseWheelUnit::Point,
                    delta: egui::vec2(0.0, -80.0),
                    phase: egui::TouchPhase::Move,
                    modifiers: default(),
                },
            ])
            .drop_without_applying_deltas();
        }
        let output = app.frame(vec![]);
        assert_eq!(visible_text(&output, "5 · 16.0–20.0s").len(), 1);
        let removes = visible_text(&output, "Remove");
        let pos = removes.last().expect("last row remove reachable").center();
        output.drop_without_applying_deltas();
        let last_id = app.doc().timeline[4].id.clone();
        app.click_at(pos);
        assert_eq!(app.doc().timeline.len(), 4);
        assert!(app.doc().timeline.iter().all(|entry| entry.id != last_id));
        app.click("Undo", 0);
        assert_eq!(app.doc().timeline.len(), 5);
        assert_preserved(&app, &original);
    }
}
#[test]
fn actual_multisegment_controls_only_exist_for_b1_motion_and_glb_stays_nine_seconds() {
    let glb = nvwa_core::CharacterProfile::from_json(include_str!(
        "../../../assets/character.profile.json"
    ))
    .unwrap();
    for profile in [
        glb,
        nvwa_core::CharacterProfile::b1(),
        nvwa_core::CharacterProfile::b1_motion(),
    ] {
        let original = SceneDocument::from_profile(profile).unwrap();
        let motion = original.profile.backend.is_b1_motion();
        let mut app = Harness::new(egui::vec2(1280.0, 720.0), original.clone());
        app.frame(vec![]).drop_without_applying_deltas();
        let output = app.frame(vec![]);
        assert_eq!(
            visible_text(&output, "Append action…").len(),
            usize::from(motion)
        );
        assert_eq!(
            visible_text(&output, "Duplicate").len(),
            usize::from(motion)
        );
        output.drop_without_applying_deltas();
        if original.profile.backend.is_glb() {
            app.click("Create 9s sequence", 0);
            assert_eq!(app.doc().timeline_duration_seconds(), 9.0);
            let output = app.frame(vec![]);
            assert!(visible_text(&output, "Duplicate").is_empty());
            assert!(visible_text(&output, "Append action…").is_empty());
            output.drop_without_applying_deltas();
        }
        assert_preserved(&app, &original);
    }
}
