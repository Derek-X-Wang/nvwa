//! CPU checks of real toolbar controls, file polling and clipped egui paint.
use super::*;

struct Harness {
    app: App,
    ctx: egui::Context,
    size: egui::Vec2,
    time: f64,
    directory: std::path::PathBuf,
}
impl Harness {
    fn new(size: egui::Vec2) -> Self {
        let directory = std::env::temp_dir().join(format!(
            "nvwa-save-feedback-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(&directory).unwrap();
        let profile = nvwa_core::CharacterProfile::from_json(include_str!(
            "../../../assets/character.profile.json"
        ))
        .unwrap();
        let mut editor = EditorState::default();
        editor
            .replace(SceneDocument::from_profile(profile).unwrap())
            .unwrap();
        let mut values = editor.document().unwrap().character.parameters.clone();
        values.insert("jaw_width".into(), 0.4);
        editor
            .apply(Command::SetParameters {
                character_id: editor.document().unwrap().character.id.clone(),
                values,
            })
            .unwrap();
        editor
            .apply(Command::SetTimeline {
                clips: nine_second_sequence(),
            })
            .unwrap();
        editor.apply(Command::Undo).unwrap();
        let mut app = App::new();
        app.insert_resource(editor)
            .insert_resource(StudioUi {
                file_path: directory.join("scene.nvwa.json").display().to_string(),
                ..default()
            })
            .init_resource::<PlatformIo>()
            .init_resource::<Playback>()
            .init_resource::<UiInputGuard>()
            .add_systems(Update, poll_files);
        Self {
            app,
            ctx: default(),
            size,
            time: 1.0,
            directory,
        }
    }
    fn frame(&mut self, events: Vec<egui::Event>) -> egui::FullOutput {
        self.app.update();
        self.draw(events)
    }
    fn draw(&mut self, events: Vec<egui::Event>) -> egui::FullOutput {
        let world = self.app.world_mut();
        let mut editor = world.remove_resource::<EditorState>().unwrap();
        let mut state = world.remove_resource::<StudioUi>().unwrap();
        let mut playback = world.remove_resource::<Playback>().unwrap();
        let mut io = world.remove_resource::<PlatformIo>().unwrap();
        let mut guard = world.remove_resource::<UiInputGuard>().unwrap();
        let mut output = self.ctx.run_ui(
            egui::RawInput {
                screen_rect: Some(egui::Rect::from_min_size(egui::Pos2::ZERO, self.size)),
                time: Some(self.time),
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
                        editor: &mut editor,
                        playback: &mut playback,
                        state: &mut state,
                        io: &mut io,
                        guard: &mut guard,
                    },
                )
                .unwrap();
            },
        );
        output.textures_delta.clear();
        world.insert_resource(editor);
        world.insert_resource(state);
        world.insert_resource(playback);
        world.insert_resource(io);
        world.insert_resource(guard);
        output
    }
    fn click(&mut self, output: &egui::FullOutput, label: &str) -> egui::FullOutput {
        let position = text(output, label).center();
        self.frame(vec![
            egui::Event::PointerMoved(position),
            pointer(position, true),
        ])
        .drop_without_applying_deltas();
        // Draw without polling after the release: observe the frame that requests I/O.
        self.draw(vec![pointer(position, false)])
    }
    fn ui(&self) -> &StudioUi {
        self.app.world().resource::<StudioUi>()
    }
}
fn pointer(pos: egui::Pos2, pressed: bool) -> egui::Event {
    egui::Event::PointerButton {
        pos,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: default(),
    }
}
fn painted_text(output: &egui::FullOutput) -> Vec<(String, egui::Rect)> {
    fn collect(shape: &egui::Shape, clip: egui::Rect, found: &mut Vec<(String, egui::Rect)>) {
        match shape {
            egui::Shape::Text(text) => {
                let rect = text.galley.rect.translate(text.pos.to_vec2());
                if clip.intersects(rect) {
                    found.push((text.galley.job.text.clone(), rect));
                }
            }
            egui::Shape::Vec(shapes) => {
                for shape in shapes {
                    collect(shape, clip, found);
                }
            }
            _ => {}
        }
    }
    let mut found = Vec::new();
    for shape in &output.shapes {
        collect(&shape.shape, shape.clip_rect, &mut found);
    }
    found
}
fn text(output: &egui::FullOutput, label: &str) -> egui::Rect {
    painted_text(output)
        .into_iter()
        .find(|(value, _)| value == label)
        .unwrap_or_else(|| {
            panic!(
                "Missing visible text: {label}; painted: {:?}",
                painted_text(output)
            )
        })
        .1
}
fn notice_bounds(output: &egui::FullOutput, title_position: egui::Pos2) -> egui::Rect {
    fn collect(shape: &egui::Shape, point: egui::Pos2, found: &mut Vec<egui::Rect>) {
        match shape {
            egui::Shape::Rect(rect)
                if rect.blur_width == 0.0
                    && rect.rect.contains(point)
                    && rect.rect.width() < 420.0 =>
            {
                found.push(rect.rect);
            }
            egui::Shape::Vec(shapes) => {
                for shape in shapes {
                    collect(shape, point, found);
                }
            }
            _ => {}
        }
    }
    let mut found = Vec::new();
    for shape in &output.shapes {
        collect(&shape.shape, title_position, &mut found);
    }
    assert_eq!(
        found.len(),
        1,
        "Notice must have one small painted background"
    );
    found[0]
}
fn assert_bottom_right(bounds: egui::Rect, size: egui::Vec2) {
    assert!(egui::Rect::from_min_size(egui::Pos2::ZERO, size).contains_rect(bounds));
    assert!(
        (size.x - bounds.right() - 16.0).abs() <= 1.0,
        "right margin: {bounds:?}"
    );
    assert!(
        (size.y - bounds.bottom() - 16.0).abs() <= 1.0,
        "bottom margin: {bounds:?}"
    );
    assert!(
        bounds.width() <= 400.0 && bounds.height() <= 180.0,
        "bounded notice: {bounds:?}"
    );
}
fn no_notice(output: &egui::FullOutput) {
    assert!(painted_text(output).iter().all(|(value, _)|
        value != "已保存 / Saved" && value != "下载已开始 / Download started"));
}

#[test]
fn save_feedback_actual_save_control_completion_repeat_dwell_and_fit() {
    for size in [egui::vec2(1280.0, 720.0), egui::vec2(1024.0, 768.0)] {
        let mut h = Harness::new(size);
        let before = h
            .app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .to_json()
            .unwrap();
        let history = format!("{:?}", h.app.world().resource::<EditorState>().editor);
        let initial = h.frame(vec![]);
        no_notice(&initial);
        let pending = h.click(&initial, "Save");
        assert!(h.app.world().resource::<PlatformIo>().busy());
        no_notice(&pending);
        let complete = h.frame(vec![]);
        let destination = h.ui().file_path.clone();
        assert_eq!(std::fs::read_to_string(&destination).unwrap(), before);
        let saved = text(&complete, "已保存 / Saved");
        // The Work input also paints this string. Require the independent
        // destination observation below the completion title, not the input.
        let destinations: Vec<_> = painted_text(&complete)
            .into_iter()
            .filter(|(value, rect)| value == &destination && rect.top() >= saved.bottom())
            .collect();
        assert_eq!(
            destinations.len(),
            1,
            "Notice must paint its destination below the title"
        );
        let path = destinations[0].1;
        let bounds = notice_bounds(&complete, saved.center());
        assert_bottom_right(bounds, size);
        assert!(bounds.contains_rect(saved));
        assert!(bounds.contains_rect(path));
        // Floating feedback must not move the toolbar or editing panels.
        for label in ["Save", "Scene", "Shape parameters", "Animation"] {
            assert_eq!(text(&complete, label), text(&initial, label));
        }
        for label in [
            "Save",
            "Open…",
            "Undo",
            "Redo",
            "Shape",
            "Profile",
            "Shape parameters",
        ] {
            let rect = text(&complete, label);
            assert!(egui::Rect::from_min_size(egui::Pos2::ZERO, size).contains_rect(rect));
        }
        // The overlay captures its own pointer, without covering the scene.
        h.frame(vec![egui::Event::PointerMoved(saved.center())])
            .drop_without_applying_deltas();
        assert!(h.app.world().resource::<UiInputGuard>().pointer);
        assert!(!scene_pointer_allowed(
            true,
            true,
            h.app.world().resource::<UiInputGuard>().pointer
        ));
        h.frame(vec![egui::Event::PointerMoved(egui::pos2(700.0, 250.0))])
            .drop_without_applying_deltas();
        assert!(!h.app.world().resource::<UiInputGuard>().pointer);
        assert!(scene_pointer_allowed(
            true,
            true,
            h.app.world().resource::<UiInputGuard>().pointer
        ));
        // A real inspector control remains editable with the overlay present.
        h.click(&complete, "Profile").drop_without_applying_deltas();
        let profile = h.frame(vec![]);
        text(&profile, "Profile: nvwa-original-humanoid-v1");
        text(&profile, "已保存 / Saved");
        h.click(&profile, "Shape").drop_without_applying_deltas();
        h.time = 7.0;
        let pending = h.click(&complete, "Save");
        no_notice(&pending);
        h.frame(vec![]).drop_without_applying_deltas();
        h.time = 14.0; // Seven seconds after repeat, beyond first notice's dwell.
        let repeated = h.frame(vec![]);
        text(&repeated, "已保存 / Saved");
        h.time = 16.0;
        no_notice(&h.frame(vec![]));
        assert_eq!(
            h.app
                .world()
                .resource::<EditorState>()
                .document()
                .unwrap()
                .to_json()
                .unwrap(),
            before
        );
        assert_eq!(
            format!("{:?}", h.app.world().resource::<EditorState>().editor),
            history
        );
    }
}

#[test]
fn save_feedback_actual_failed_save_open_and_destination_edit_clear_success() {
    let mut h = Harness::new(egui::vec2(1024.0, 768.0));
    let initial = h.frame(vec![]);
    h.click(&initial, "Save").drop_without_applying_deltas();
    let saved = h.frame(vec![]);
    text(&saved, "已保存 / Saved");
    // Use the real Work text input. Replacing the destination must clear the notice.
    let input_position = egui::pos2(
        text(&saved, "作品 / Work").right() + 40.0,
        text(&saved, "Save").center().y,
    );
    h.frame(vec![
        egui::Event::PointerMoved(input_position),
        pointer(input_position, true),
    ])
    .drop_without_applying_deltas();
    h.frame(vec![pointer(input_position, false)])
        .drop_without_applying_deltas();
    let mut modifiers = egui::Modifiers::COMMAND;
    modifiers.mac_cmd = true;
    let invalid = h.directory.display().to_string(); // Atomic rename onto a directory must fail.
    let edited = h.frame(vec![
        egui::Event::Key {
            key: egui::Key::A,
            physical_key: None,
            pressed: true,
            repeat: false,
            modifiers,
        },
        egui::Event::Text(invalid.clone()),
    ]);
    assert_eq!(h.ui().file_path, invalid);
    no_notice(&edited);
    h.click(&edited, "Save").drop_without_applying_deltas();
    let failed = h.frame(vec![]);
    no_notice(&failed);
    let error = h.ui().error.clone().unwrap();
    text(&failed, &error);
    assert!(!h.app.world().resource::<PlatformIo>().busy());
    // Recovery through real Save, then real Open clears success while pending.
    h.app.world_mut().resource_mut::<StudioUi>().file_path =
        h.directory.join("recovery.json").display().to_string();
    let ready = h.frame(vec![]);
    h.click(&ready, "Save").drop_without_applying_deltas();
    let recovered = h.frame(vec![]);
    text(&recovered, "已保存 / Saved");
    assert!(h.ui().error.is_none());
    no_notice(&h.click(&recovered, "Open…"));
    no_notice(&h.frame(vec![]));
    assert!(h.ui().save_notice.is_none());
}

#[test]
fn save_feedback_long_native_destination_stays_small_and_selectable() {
    for size in [egui::vec2(1280.0, 720.0), egui::vec2(1024.0, 768.0)] {
        let mut h = Harness::new(size);
        let initial = h.frame(vec![]);
        h.click(&initial, "Save").drop_without_applying_deltas();
        let short = h.frame(vec![]);
        text(&short, "已保存 / Saved");
        let mut directory = h.directory.clone();
        for index in 0..12 {
            directory = directory.join(format!("long-destination-segment-{index:02}"));
        }
        std::fs::create_dir_all(&directory).unwrap();
        let destination = directory
            .join("long-work-name.nvwa.json")
            .display()
            .to_string();
        h.app.world_mut().resource_mut::<StudioUi>().file_path = destination.clone();
        let initial = h.frame(vec![]);
        h.click(&initial, "Save").drop_without_applying_deltas();
        let complete = h.frame(vec![]);
        let title = text(&complete, "已保存 / Saved");
        let bounds = notice_bounds(&complete, title.center());
        assert_bottom_right(bounds, size);
        let paths: Vec<_> = painted_text(&complete)
            .into_iter()
            .filter(|(value, rect)| value == &destination && rect.top() >= title.bottom())
            .collect();
        assert_eq!(
            paths.len(),
            1,
            "Notice must paint the long destination below its title"
        );
        let path = paths[0].1;
        assert!(bounds.intersects(path) && path.left() >= bounds.left());
        assert!(path.width() <= bounds.width());
        assert!(
            path.height() > 120.0,
            "Long destination must use bounded scrolling"
        );
        // Drag in the actual destination label: selectable path input stays
        // owned by egui, including over the scene's mouse interaction path.
        let inside = egui::pos2(path.left() + 10.0, title.bottom() + 12.0);
        h.frame(vec![
            egui::Event::PointerMoved(inside),
            pointer(inside, true),
        ])
        .drop_without_applying_deltas();
        assert!(h.app.world().resource::<UiInputGuard>().pointer);
        h.frame(vec![egui::Event::PointerMoved(
            inside + egui::vec2(80.0, 0.0),
        )])
        .drop_without_applying_deltas();
        assert!(h.app.world().resource::<UiInputGuard>().pointer);
        h.frame(vec![pointer(inside + egui::vec2(80.0, 0.0), false)])
            .drop_without_applying_deltas();
        let copied = h.frame(vec![egui::Event::Copy]);
        assert!(copied.platform_output.commands.iter().any(|command| {
            matches!(command, egui::OutputCommand::CopyText(value) if !value.is_empty() && destination.contains(value))
        }), "Dragging the destination must allow copying selected path text");
    }
}

#[test]
fn save_feedback_browser_completion_is_download_only_and_errors_replace_it() {
    let mut h = Harness::new(egui::vec2(1024.0, 768.0));
    let mut editor = h.app.world_mut().remove_resource::<EditorState>().unwrap();
    accept_file_completion(
        Ok(FileCompletion::DownloadStarted("scene.json".into())),
        &mut editor,
        &mut h.app.world_mut().resource_mut::<StudioUi>(),
    );
    h.app.world_mut().insert_resource(editor);
    let output = h.frame(vec![]);
    text(&output, "下载已开始 / Download started");
    text(&output, "scene.json · Check your browser downloads.");
    assert!(
        painted_text(&output)
            .iter()
            .all(|(value, _)| !value.contains("Document saved") && value != "已保存 / Saved")
    );
    let mut editor = h.app.world_mut().remove_resource::<EditorState>().unwrap();
    accept_file_completion(
        Err("File selection cancelled".into()),
        &mut editor,
        &mut h.app.world_mut().resource_mut::<StudioUi>(),
    );
    h.app.world_mut().insert_resource(editor);
    let failed = h.frame(vec![]);
    no_notice(&failed);
    text(&failed, "File selection cancelled");
}
