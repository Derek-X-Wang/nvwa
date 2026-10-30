//! Private adapter for pinned tabs and split controls. Layout belongs to the app
//! session; this module never receives a Work or a command handler.
use bevy_egui::egui;
use craft_ui::{
    layout::{ResizeHandle, ResizeHandleStyle, SplitAxis},
    tabs::Tab,
};

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(super) enum InspectorTab {
    #[default]
    Shape,
    Profile,
}

#[derive(Clone, Debug, PartialEq)]
pub(super) struct EditorLayout {
    pub tab: InspectorTab,
    pub locked: bool,
    // Preferred session height survives temporary viewport clamping.
    height: f32,
    drag_origin: Option<f32>,
    cancelled_drag: bool,
}
impl Default for EditorLayout {
    fn default() -> Self {
        Self {
            tab: default(),
            locked: false,
            height: 210.0,
            drag_origin: None,
            cancelled_drag: false,
        }
    }
}
fn default<T: Default>() -> T {
    T::default()
}
impl EditorLayout {
    fn reset(&mut self) {
        self.tab = InspectorTab::Shape;
        self.height = 210.0;
        self.drag_origin = None;
        self.cancelled_drag = true;
    }
    fn cancel(&mut self) {
        if let Some(height) = self.drag_origin.take() {
            self.height = height;
        }
        self.cancelled_drag = true;
    }
    fn set_locked(&mut self, locked: bool) {
        if locked {
            self.cancel();
        }
        self.locked = locked;
    }
    fn resize(&mut self, delta: f32, viewport_height: f32) {
        if !self.locked && !self.cancelled_drag && delta.is_finite() && delta != 0.0 {
            self.height = (self.height - delta).clamp(160.0, Self::maximum(viewport_height));
        }
    }
    fn maximum(viewport_height: f32) -> f32 {
        (viewport_height * 0.55).max(160.0)
    }
    pub fn height_for(&self, viewport_height: f32) -> f32 {
        self.height.clamp(160.0, Self::maximum(viewport_height))
    }
    pub fn draw_controls(&mut self, ui: &mut egui::Ui) {
        ui.horizontal(|ui| {
            let mut locked = self.locked;
            if ui.checkbox(&mut locked, "Lock timeline height").changed() {
                self.set_locked(locked);
            }
            if ui.button("Reset layout").clicked() {
                self.reset();
            }
        });
    }
    pub fn draw_tabs(&mut self, ui: &mut egui::Ui) {
        ui.horizontal(|ui| {
            for (tab, label) in [
                (InspectorTab::Shape, "Shape"),
                (InspectorTab::Profile, "Profile"),
            ] {
                let (rect, _) =
                    ui.allocate_exact_size(egui::vec2(100.0, 26.0), egui::Sense::hover());
                let selected = self.tab == tab;
                let response = Tab::new(ui.id().with(label), label, selected).show_at(
                    ui,
                    rect,
                    |ui, response| {
                        let visuals = if selected {
                            &ui.visuals().widgets.active
                        } else {
                            ui.style().interact(response)
                        };
                        ui.painter().rect_filled(rect, 3.0, visuals.bg_fill);
                        ui.painter().text(
                            rect.center(),
                            egui::Align2::CENTER_CENTER,
                            label,
                            egui::FontId::proportional(14.0),
                            visuals.fg_stroke.color,
                        );
                    },
                );
                if response.clicked() {
                    self.tab = tab;
                }
            }
        });
        ui.separator();
    }
    pub fn draw_resize(&mut self, ui: &mut egui::Ui, viewport_height: f32) {
        let (rect, _) =
            ui.allocate_exact_size(egui::vec2(ui.available_width(), 8.0), egui::Sense::hover());
        ui.painter().line_segment(
            [rect.left_center(), rect.right_center()],
            ui.visuals().widgets.inactive.bg_stroke,
        );
        let response = ui
            .add_enabled_ui(!self.locked, |ui| {
                ResizeHandle::new(
                    ui.id().with("timeline_split"),
                    SplitAxis::Vertical,
                    rect,
                    "Timeline height",
                    ResizeHandleStyle {
                        hovered: ui.visuals().selection.bg_fill,
                        dragged: ui.visuals().selection.bg_fill,
                        focused: ui.visuals().selection.stroke.color,
                    },
                )
                .hit_margin(0.0)
                .show(ui)
            })
            .inner;
        if response.response.drag_started() {
            self.drag_origin = Some(self.height);
            self.cancelled_drag = false;
        }
        if ui.input(|input| input.key_pressed(egui::Key::Escape)) && self.drag_origin.is_some() {
            self.cancel();
        } else if !response.response.dragged() && !response.response.is_pointer_button_down_on() {
            self.cancelled_drag = false;
        }
        self.resize(response.delta, viewport_height);
        if response.response.drag_stopped() {
            self.drag_origin = None;
        }
    }
}

#[cfg(test)]
#[path = "editor_layout_paint_tests.rs"]
mod paint_tests;

#[cfg(test)]
mod tests {
    use super::*;
    use nvwa_core::{Command, SceneDocument};
    use nvwa_runtime::EditorState;

    fn root_ui(ctx: &egui::Context, screen: egui::Rect) -> egui::Ui {
        egui::Ui::new(
            ctx.clone(),
            "layout_tests".into(),
            egui::UiBuilder::new()
                .layer_id(egui::LayerId::background())
                .max_rect(screen),
        )
    }
    fn editor_with_both_history_directions() -> EditorState {
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
        let id = editor.document().unwrap().character.id.clone();
        editor
            .apply(Command::SetParameters {
                character_id: id,
                values,
            })
            .unwrap();
        editor
            .apply(Command::SetTimeline {
                clips: crate::nine_second_sequence(),
            })
            .unwrap();
        editor.apply(Command::Undo).unwrap();
        editor
    }

    pub(super) struct StudioHarness {
        pub(super) ctx: egui::Context,
        size: egui::Vec2,
        pub(super) editor: EditorState,
        pub(super) time: Option<f64>,
        state: crate::StudioUi,
        playback: crate::Playback,
        io: crate::PlatformIo,
        guard: crate::UiInputGuard,
    }
    impl StudioHarness {
        pub(super) fn new(size: egui::Vec2) -> Self {
            Self {
                ctx: default(),
                size,
                editor: editor_with_both_history_directions(),
                time: None,
                state: default(),
                playback: crate::Playback {
                    clip_id: "idle".into(),
                    ..default()
                },
                io: default(),
                guard: default(),
            }
        }
        pub(super) fn frame(&mut self, events: Vec<egui::Event>) -> egui::FullOutput {
            self.ctx.run_ui(
                egui::RawInput {
                    screen_rect: Some(egui::Rect::from_min_size(egui::Pos2::ZERO, self.size)),
                    events,
                    time: self.time,
                    ..default()
                },
                |ui| {
                    crate::draw_editor_ui(
                        ui.ctx(),
                        &crate::RuntimeStatus {
                            ready: true,
                            ..default()
                        },
                        &default(),
                        crate::EditorUiSession {
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
        pub(super) fn click(&mut self, position: egui::Pos2) {
            self.frame(vec![
                egui::Event::PointerMoved(position),
                pointer(position, true),
            ])
            .drop_without_applying_deltas();
            self.frame(vec![pointer(position, false)])
                .drop_without_applying_deltas();
        }
        fn focus_by_tab(&mut self, position: egui::Pos2) {
            for _ in 0..32 {
                self.frame(vec![
                    egui::Event::Key {
                        key: egui::Key::Tab,
                        physical_key: None,
                        pressed: false,
                        repeat: false,
                        modifiers: default(),
                    },
                    key(egui::Key::Tab),
                ])
                .drop_without_applying_deltas();
                if self
                    .ctx
                    .memory(|memory| memory.focused())
                    .and_then(|id| self.ctx.read_response(id))
                    .is_some_and(|response| response.rect.contains(position))
                {
                    return;
                }
            }
            panic!("actual control was not reached by keyboard focus traversal: {position:?}");
        }
    }
    pub(super) fn pointer(pos: egui::Pos2, pressed: bool) -> egui::Event {
        egui::Event::PointerButton {
            pos,
            button: egui::PointerButton::Primary,
            pressed,
            modifiers: default(),
        }
    }
    fn key(key: egui::Key) -> egui::Event {
        egui::Event::Key {
            key,
            physical_key: None,
            pressed: true,
            repeat: false,
            modifiers: default(),
        }
    }
    fn document_shortcut(shift: bool) -> Vec<egui::Event> {
        let modifiers = egui::Modifiers {
            command: true,
            mac_cmd: true,
            shift,
            ..default()
        };
        vec![
            // Key-event modifiers do not set InputState.modifiers in egui 0.36.
            egui::Event::ModifiersChanged(modifiers),
            egui::Event::Key {
                key: egui::Key::Z,
                physical_key: None,
                pressed: false,
                repeat: false,
                modifiers,
            },
            egui::Event::Key {
                key: egui::Key::Z,
                physical_key: None,
                pressed: true,
                repeat: false,
                modifiers,
            },
        ]
    }
    fn label_rect(output: &egui::FullOutput, label: &str) -> egui::Rect {
        fn find(shape: &egui::Shape, label: &str) -> Option<egui::Rect> {
            match shape {
                egui::Shape::Text(text) if text.galley.job.text == label => {
                    Some(text.galley.rect.translate(text.pos.to_vec2()))
                }
                egui::Shape::Vec(shapes) => shapes.iter().find_map(|shape| find(shape, label)),
                _ => None,
            }
        }
        output
            .shapes
            .iter()
            .find_map(|shape| find(&shape.shape, label))
            .unwrap_or_else(|| panic!("actual control label missing: {label}"))
    }

    #[test]
    fn actual_shape_drag_is_one_command_and_undo_redo_restore_complete_work() {
        for size in [egui::vec2(1280.0, 720.0), egui::vec2(1024.0, 768.0)] {
            let mut app = StudioHarness::new(size);
            app.frame(vec![]).drop_without_applying_deltas();
            let output = app.frame(vec![]);
            let jaw = label_rect(&output, "jaw width");
            let before = app.editor.document().unwrap().clone();
            // The actual slider precedes its label within the 280-point inspector.
            let origin = egui::pos2(size.x - 260.0, jaw.center().y);
            app.frame(vec![
                egui::Event::PointerMoved(origin),
                pointer(origin, true),
            ])
            .drop_without_applying_deltas();
            for x in [size.x - 230.0, size.x - 205.0, size.x - 190.0] {
                app.frame(vec![egui::Event::PointerMoved(egui::pos2(x, origin.y))])
                    .drop_without_applying_deltas();
                assert!(app.guard.pointer);
                assert!(
                    app.editor.preview.is_some(),
                    "real slider must preview at {size:?}"
                );
                assert_eq!(app.editor.document().unwrap(), &before);
            }
            let destination = egui::pos2(size.x - 190.0, origin.y);
            app.frame(vec![pointer(destination, false)])
                .drop_without_applying_deltas();
            assert!(app.editor.preview.is_none());
            let edited = app.editor.document().unwrap().clone();
            assert_eq!(edited.revision, before.revision + 1);
            assert_ne!(
                edited.character.parameters["jaw_width"],
                before.character.parameters["jaw_width"]
            );
            let mut expected = before.clone();
            expected.character.parameters = edited.character.parameters.clone();
            expected.revision = edited.revision;
            assert_eq!(edited, expected);
            app.editor.apply(Command::Undo).unwrap();
            let mut restored = before.clone();
            restored.revision = edited.revision + 1;
            assert_eq!(app.editor.document().unwrap(), &restored);
            app.editor.apply(Command::Redo).unwrap();
            expected.revision += 2;
            assert_eq!(app.editor.document().unwrap(), &expected);
            assert_eq!(app.state.file_path, "scene.nvwa.json");
        }
    }

    #[test]
    fn actual_studio_layout_controls_preserve_work_history_and_guard_focused_space() {
        for size in [egui::vec2(1280.0, 720.0), egui::vec2(1024.0, 768.0)] {
            let mut app = StudioHarness::new(size);
            app.frame(vec![]).drop_without_applying_deltas();
            let output = app.frame(vec![]);
            let before_work = app.editor.document().unwrap().to_json().unwrap();
            let before_history = format!("{:?}", app.editor.editor.as_ref().unwrap());
            app.click(label_rect(&output, "Profile").center());
            assert_eq!(app.state.layout.tab, InspectorTab::Profile);
            // Mouse clicks select tabs without taking keyboard focus. Reach the
            // actual tab through normal keyboard traversal before sending Space.
            let output = app.frame(vec![]);
            app.focus_by_tab(label_rect(&output, "Profile").center());
            for shift in [false, true] {
                app.frame(document_shortcut(shift))
                    .drop_without_applying_deltas();
                assert!(app.guard.keyboard);
                // A focused tab leaves Z unconsumed. This proves the production
                // shortcut condition is armed and the keyboard guard blocks it.
                assert!(
                    app.ctx
                        .input(|input| input.modifiers.command && input.key_pressed(egui::Key::Z))
                );
            }
            assert_eq!(
                app.editor.document().unwrap().to_json().unwrap(),
                before_work
            );
            assert_eq!(
                format!("{:?}", app.editor.editor.as_ref().unwrap()),
                before_history
            );
            app.frame(vec![key(egui::Key::Space)])
                .drop_without_applying_deltas();
            assert!(app.guard.keyboard);
            assert!(!app.playback.playing);
            app.frame(vec![egui::Event::ModifiersChanged(default())])
                .drop_without_applying_deltas();
            let output = app.frame(vec![]);
            app.click(label_rect(&output, "Lock timeline height").center());
            assert!(app.state.layout.locked);
            let output = app.frame(vec![]);
            app.click(label_rect(&output, "Reset layout").center());
            assert_eq!(app.state.layout.tab, InspectorTab::Shape);
            assert_eq!(app.state.layout.height, 210.0);
            assert_eq!(
                app.editor.document().unwrap().to_json().unwrap(),
                before_work
            );
            assert_eq!(
                format!("{:?}", app.editor.editor.as_ref().unwrap()),
                before_history
            );
            app.editor.apply(Command::Redo).unwrap();
            assert_eq!(app.editor.document().unwrap().timeline.len(), 3);
            app.editor.apply(Command::Undo).unwrap();
            assert_eq!(
                app.editor.document().unwrap().character.parameters["jaw_width"],
                0.4
            );
        }
    }

    #[test]
    fn actual_work_path_focus_blocks_space_and_document_shortcuts() {
        for size in [egui::vec2(1280.0, 720.0), egui::vec2(1024.0, 768.0)] {
            let mut app = StudioHarness::new(size);
            app.frame(vec![]).drop_without_applying_deltas();
            // Positive control: the same real shortcut input reaches the Work
            // command path while no widget has keyboard focus.
            app.click(egui::pos2(size.x / 2.0, 200.0));
            let original = app.editor.document().unwrap().clone();
            app.frame(document_shortcut(false))
                .drop_without_applying_deltas();
            assert!(!app.guard.keyboard);
            assert!(
                app.ctx
                    .input(|input| input.modifiers.command && input.key_pressed(egui::Key::Z))
            );
            assert_eq!(
                app.editor.document().unwrap().revision,
                original.revision + 1
            );
            assert_eq!(
                app.editor.document().unwrap().character.parameters["jaw_width"],
                0.0
            );
            app.frame(document_shortcut(true))
                .drop_without_applying_deltas();
            assert!(!app.guard.keyboard);
            assert!(
                app.ctx
                    .input(|input| input.modifiers.command && input.key_pressed(egui::Key::Z))
            );
            let mut restored = original;
            restored.revision += 2;
            assert_eq!(app.editor.document().unwrap(), &restored);
            app.frame(vec![egui::Event::ModifiersChanged(default())])
                .drop_without_applying_deltas();
            let output = app.frame(vec![]);
            let before_work = app.editor.document().unwrap().to_json().unwrap();
            let before_history = format!("{:?}", app.editor.editor.as_ref().unwrap());
            // Focus the production Work-path TextEdit through real pointer input.
            app.click(label_rect(&output, "scene.nvwa.json").center());
            assert!(app.guard.pointer);
            app.frame(vec![key(egui::Key::Space)])
                .drop_without_applying_deltas();
            assert!(app.guard.keyboard);
            assert!(!app.playback.playing);
            for shift in [false, true] {
                app.frame(document_shortcut(shift))
                    .drop_without_applying_deltas();
                assert!(app.guard.keyboard);
                assert!(app.ctx.input(|input| input.modifiers.command));
            }
            assert_eq!(
                app.editor.document().unwrap().to_json().unwrap(),
                before_work
            );
            assert_eq!(
                format!("{:?}", app.editor.editor.as_ref().unwrap()),
                before_history
            );
            assert_eq!(app.state.file_path, "scene.nvwa.json");
        }
    }

    #[test]
    fn discarded_editor_pass_does_not_install_layout_or_apply_commands() {
        // Exercise both a layout intent and an actual Work command intent.
        for label in ["Profile", "Reset shape"] {
            let mut app = StudioHarness::new(egui::vec2(1280.0, 720.0));
            app.frame(vec![]).drop_without_applying_deltas();
            let output = app.frame(vec![]);
            let position = label_rect(&output, label).center();
            app.frame(vec![
                egui::Event::PointerMoved(position),
                pointer(position, true),
            ])
            .drop_without_applying_deltas();
            let before = app.state.layout.clone();
            let history = format!("{:?}", app.editor.editor.as_ref().unwrap());
            app.ctx.begin_pass(egui::RawInput {
                screen_rect: Some(egui::Rect::from_min_size(egui::Pos2::ZERO, app.size)),
                events: vec![pointer(position, false)],
                ..default()
            });
            app.ctx
                .request_discard("exercise production final-pass guard");
            assert!(app.ctx.will_discard());
            crate::draw_editor_ui(
                &app.ctx,
                &crate::RuntimeStatus {
                    ready: true,
                    ..default()
                },
                &default(),
                crate::EditorUiSession {
                    editor: &mut app.editor,
                    playback: &mut app.playback,
                    state: &mut app.state,
                    io: &mut app.io,
                    guard: &mut app.guard,
                },
            )
            .unwrap();
            assert_eq!(app.state.layout, before);
            assert_eq!(
                format!("{:?}", app.editor.editor.as_ref().unwrap()),
                history
            );
            app.ctx.end_pass().drop_without_applying_deltas();
        }
    }
    #[test]
    fn layout_reset_cancel_lock_and_tabs_preserve_full_work_and_history() {
        let mut editor = editor_with_both_history_directions();
        let before_work = editor.document().unwrap().to_json().unwrap();
        // Debug includes every retained document, retry envelope/result and byte budget.
        let before_session = format!("{:?}", editor.editor.as_ref().unwrap());
        let mut layout = EditorLayout::default();
        layout.drag_origin = Some(layout.height);
        layout.resize(-80.0, 720.0);
        assert_eq!(layout.height, 290.0);
        layout.cancel();
        assert_eq!(layout.height, 210.0);
        layout.cancelled_drag = false;
        layout.resize(-40.0, 720.0);
        layout.set_locked(true);
        layout.resize(-80.0, 720.0);
        assert_eq!(layout.height, 250.0);
        layout.tab = InspectorTab::Profile;
        layout.reset();
        assert_eq!(layout.tab, InspectorTab::Shape);
        assert_eq!(layout.height, 210.0);
        assert_eq!(editor.document().unwrap().to_json().unwrap(), before_work);
        assert_eq!(
            format!("{:?}", editor.editor.as_ref().unwrap()),
            before_session
        );
        // Ensure both retained directions still operate after layout changes.
        editor.apply(Command::Redo).unwrap();
        assert_eq!(editor.document().unwrap().timeline.len(), 3);
        editor.apply(Command::Undo).unwrap();
        assert_eq!(
            editor.document().unwrap().character.parameters["jaw_width"],
            0.4
        );
    }
    #[test]
    fn reset_during_drag_prevents_subsequent_delta_and_small_window_recovers() {
        let mut layout = EditorLayout {
            drag_origin: Some(210.0),
            ..default()
        };
        layout.resize(-100.0, 768.0);
        layout.reset();
        layout.resize(-100.0, 768.0);
        assert_eq!(layout.height, 210.0);
        layout.cancelled_drag = false;
        layout.resize(f32::NAN, 720.0);
        assert_eq!(layout.height, 210.0);
        layout.resize(-1000.0, 768.0);
        assert_eq!(layout.height_for(300.0), 165.0);
        assert!((layout.height_for(768.0) - 422.4).abs() < 0.001);
    }
    #[test]
    fn real_studio_keeps_scene_and_panel_guards_and_full_work() {
        for size in [egui::vec2(1280.0, 720.0), egui::vec2(1024.0, 768.0)] {
            let ctx = egui::Context::default();
            let mut editor = editor_with_both_history_directions();
            let before = format!("{:?}", editor.editor.as_ref().unwrap());
            let mut state = crate::StudioUi::default();
            let mut playback = crate::Playback {
                clip_id: "idle".into(),
                ..default()
            };
            let status = crate::RuntimeStatus {
                ready: true,
                ..default()
            };
            let mut io = crate::PlatformIo::default();
            let mut guard = crate::UiInputGuard::default();
            let screen = egui::Rect::from_min_size(egui::Pos2::ZERO, size);
            for (position, owned) in [
                (egui::pos2(size.x / 2.0, 200.0), false),
                (egui::pos2(size.x - 100.0, 150.0), true),
                (egui::pos2(size.x / 2.0, size.y - 70.0), true),
            ] {
                // Warm panel geometry, then exercise its current-frame pointer seam.
                for _ in 0..2 {
                    ctx.begin_pass(egui::RawInput {
                        screen_rect: Some(screen),
                        events: vec![egui::Event::PointerMoved(position)],
                        ..default()
                    });
                    crate::draw_editor_ui(
                        &ctx,
                        &status,
                        &default(),
                        crate::EditorUiSession {
                            editor: &mut editor,
                            playback: &mut playback,
                            state: &mut state,
                            io: &mut io,
                            guard: &mut guard,
                        },
                    )
                    .unwrap();
                    assert_eq!(guard.pointer, owned, "size={size:?}, pointer={position:?}");
                    ctx.end_pass().drop_without_applying_deltas();
                }
            }
            assert_eq!(format!("{:?}", editor.editor.as_ref().unwrap()), before);
            ctx.begin_pass(egui::RawInput {
                screen_rect: Some(screen),
                events: vec![egui::Event::Key {
                    key: egui::Key::Space,
                    physical_key: None,
                    pressed: true,
                    repeat: false,
                    modifiers: default(),
                }],
                ..default()
            });
            crate::draw_editor_ui(
                &ctx,
                &status,
                &default(),
                crate::EditorUiSession {
                    editor: &mut editor,
                    playback: &mut playback,
                    state: &mut state,
                    io: &mut io,
                    guard: &mut guard,
                },
            )
            .unwrap();
            assert!(!guard.keyboard);
            assert!(playback.playing);
            assert_eq!(format!("{:?}", editor.editor.as_ref().unwrap()), before);
            ctx.end_pass().drop_without_applying_deltas();
        }
    }
    #[test]
    fn actual_resize_idle_window_shrink_preserves_preferred_height() {
        let ctx = egui::Context::default();
        let mut layout = EditorLayout::default();
        layout.resize(-1000.0, 768.0);
        let preferred = layout.height;
        for height in [768.0, 720.0, 300.0, 768.0] {
            let screen = egui::Rect::from_min_size(egui::Pos2::ZERO, egui::vec2(1024.0, height));
            ctx.begin_pass(egui::RawInput {
                screen_rect: Some(screen),
                ..default()
            });
            egui::CentralPanel::default().show(&mut root_ui(&ctx, screen), |ui| {
                layout.draw_resize(ui, height);
            });
            ctx.end_pass().drop_without_applying_deltas();
            assert_eq!(
                layout.height, preferred,
                "idle window height {height} lost preferred layout"
            );
        }
        assert_eq!(layout.height_for(768.0), preferred);
    }
    #[test]
    fn actual_resize_escape_cancels_and_focus_guards_keyboard() {
        let ctx = egui::Context::default();
        let mut layout = EditorLayout::default();
        let screen = egui::Rect::from_min_size(egui::Pos2::ZERO, egui::vec2(800.0, 600.0));
        let pointer = |position, pressed| egui::Event::PointerButton {
            pos: position,
            button: egui::PointerButton::Primary,
            pressed,
            modifiers: default(),
        };
        let origin = egui::pos2(200.0, 12.0);
        for events in [
            vec![],
            vec![egui::Event::PointerMoved(origin), pointer(origin, true)],
            vec![egui::Event::PointerMoved(egui::pos2(200.0, 32.0))],
        ] {
            ctx.begin_pass(egui::RawInput {
                screen_rect: Some(screen),
                events,
                ..default()
            });
            egui::CentralPanel::default().show(&mut root_ui(&ctx, screen), |ui| {
                layout.draw_resize(ui, 600.0);
            });
            ctx.end_pass().drop_without_applying_deltas();
        }
        assert!(layout.drag_origin.is_some());
        assert!(layout.height < 210.0);
        assert!(ctx.egui_wants_keyboard_input());
        ctx.begin_pass(egui::RawInput {
            screen_rect: Some(screen),
            events: vec![egui::Event::Key {
                key: egui::Key::Escape,
                physical_key: None,
                pressed: true,
                repeat: false,
                modifiers: default(),
            }],
            ..default()
        });
        egui::CentralPanel::default().show(&mut root_ui(&ctx, screen), |ui| {
            layout.draw_resize(ui, 600.0);
        });
        assert_eq!(layout.height, 210.0);
        assert!(layout.cancelled_drag);
        assert!(!ctx.egui_wants_keyboard_input());
        ctx.end_pass().drop_without_applying_deltas();
    }
    #[test]
    fn actual_tabs_are_pointer_owned_and_keyboard_focus_guards_space() {
        for size in [egui::vec2(1280.0, 720.0), egui::vec2(1024.0, 768.0)] {
            let ctx = egui::Context::default();
            let mut layout = EditorLayout::default();
            let screen = egui::Rect::from_min_size(egui::Pos2::ZERO, size);
            let mut profile_center = egui::Pos2::ZERO;
            // Real craft Tab draw and click through egui; no direct state assignment.
            for events in [
                vec![],
                vec![
                    egui::Event::PointerMoved(egui::pos2(168.0, 21.0)),
                    egui::Event::PointerButton {
                        pos: egui::pos2(168.0, 21.0),
                        button: egui::PointerButton::Primary,
                        pressed: true,
                        modifiers: default(),
                    },
                ],
                vec![egui::Event::PointerButton {
                    pos: egui::pos2(168.0, 21.0),
                    button: egui::PointerButton::Primary,
                    pressed: false,
                    modifiers: default(),
                }],
            ] {
                ctx.begin_pass(egui::RawInput {
                    screen_rect: Some(screen),
                    events,
                    ..default()
                });
                egui::CentralPanel::default().show(&mut root_ui(&ctx, screen), |ui| {
                    layout.draw_tabs(ui);
                    profile_center = ui.min_rect().center();
                });
                ctx.end_pass().drop_without_applying_deltas();
            }
            assert_eq!(
                layout.tab,
                InspectorTab::Profile,
                "actual tab click at {size:?}, panel {profile_center:?}"
            );
            ctx.begin_pass(egui::RawInput {
                screen_rect: Some(screen),
                ..default()
            });
            egui::CentralPanel::default().show(&mut root_ui(&ctx, screen), |ui| {
                let mut work_path = "scene.nvwa.json".to_owned();
                let response = ui.add(egui::TextEdit::singleline(&mut work_path));
                response.request_focus();
            });
            assert!(ctx.egui_wants_keyboard_input());
            ctx.end_pass().drop_without_applying_deltas();
        }
    }
}

#[cfg(test)]
#[path = "appearance_ui_tests.rs"]
mod appearance_tests;

#[cfg(test)]
#[path = "b1_rehearsal_ui_tests.rs"]
mod rehearsal_tests;
