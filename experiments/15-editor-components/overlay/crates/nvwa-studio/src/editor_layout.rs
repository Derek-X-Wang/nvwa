//! Throwaway M1.1 layout experiment; never receives a Work or command handler.
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
    pub component: bool,
    pub tab: InspectorTab,
    pub locked: bool,
    height: f32,
    drag_origin: Option<f32>,
    cancelled_drag: bool,
}
impl Default for EditorLayout {
    fn default() -> Self {
        Self {
            component: false,
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
        ui.horizontal_wrapped(|ui| {
            ui.label("M1.1 prototype");
            if ui
                .selectable_label(!self.component, "A · Existing")
                .clicked()
            {
                self.cancel();
                self.component = false;
            }
            if ui
                .selectable_label(self.component, "B · Components")
                .clicked()
            {
                self.cancel();
                self.component = true;
            }
            ui.add_enabled_ui(self.component, |ui| {
                let mut locked = self.locked;
                if ui.checkbox(&mut locked, "Lock split").changed() {
                    self.set_locked(locked);
                }
                if ui.button("Reset layout").clicked() {
                    self.reset();
                }
            });
            ui.small(format!(
                "Session only · {:?} · {:.0}px · {}",
                self.tab,
                self.height,
                if self.locked {
                    "locked"
                } else {
                    "resize / Escape cancels"
                }
            ));
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
                    "Timeline split",
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
        let profile =
            serde_json::from_str(include_str!("../../../assets/character.profile.json")).unwrap();
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
    #[test]
    fn layout_reset_cancel_lock_tabs_and_switch_preserve_full_work_and_history() {
        let mut editor = editor_with_both_history_directions();
        let before_work = editor.document().unwrap().to_json().unwrap();
        // Debug includes every retained document, retry envelope/result and byte budget.
        let before_session = format!("{:?}", editor.editor.as_ref().unwrap());
        let mut layout = EditorLayout {
            component: true,
            ..default()
        };
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
        layout.component = false;
        assert!(!layout.component);
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
            component: true,
            ..default()
        };
        layout.drag_origin = Some(210.0);
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
    fn real_studio_variants_keep_scene_and_panel_guards_and_full_work() {
        for component in [false, true] {
            for size in [egui::vec2(1280.0, 720.0), egui::vec2(1024.0, 768.0)] {
                let ctx = egui::Context::default();
                let mut editor = editor_with_both_history_directions();
                let before = format!("{:?}", editor.editor.as_ref().unwrap());
                let mut state = crate::StudioUi::default();
                state.layout.component = component;
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
                            &mut editor,
                            &mut playback,
                            &mut state,
                            &mut io,
                            &mut guard,
                        )
                        .unwrap();
                        assert_eq!(
                            guard.pointer, owned,
                            "component={component}, size={size:?}, pointer={position:?}"
                        );
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
                    &mut editor,
                    &mut playback,
                    &mut state,
                    &mut io,
                    &mut guard,
                )
                .unwrap();
                assert!(!guard.keyboard);
                assert!(playback.playing);
                assert_eq!(format!("{:?}", editor.editor.as_ref().unwrap()), before);
                ctx.end_pass().drop_without_applying_deltas();
            }
        }
    }
    #[test]
    fn actual_resize_idle_window_shrink_preserves_preferred_height() {
        let ctx = egui::Context::default();
        let mut layout = EditorLayout {
            component: true,
            ..default()
        };
        layout.resize(-1000.0, 768.0);
        let preferred = layout.height;
        for height in [768.0, 720.0, 768.0] {
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
        let mut layout = EditorLayout {
            component: true,
            ..default()
        };
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
            let mut layout = EditorLayout {
                component: true,
                ..default()
            };
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
                let mut work_path = "component-work.nvwa.json".to_owned();
                let response = ui.add(egui::TextEdit::singleline(&mut work_path));
                response.request_focus();
            });
            assert!(ctx.egui_wants_keyboard_input());
            ctx.end_pass().drop_without_applying_deltas();
        }
    }
}
