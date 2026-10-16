//! Bilingual stage controls and one-transaction presentation gestures.
use super::{EditorState, editor_owns_pointer, egui};
use nvwa_core::{Command, StageCamera, StageLight, StageQuality, StageSettings};

#[derive(Default, Clone)]
pub(super) struct StageUi {
    pub open: bool,
    orbit: bool,
    wheel_deadline: Option<f64>,
    cancelled_until_release: bool,
}
#[derive(Default)]
pub(super) struct Intent {
    pub preview: Option<StageSettings>,
    pub commit: bool,
    pub cancel: bool,
    pub command: Option<Command>,
}
fn slider(
    ui: &mut egui::Ui,
    value: &mut f32,
    range: std::ops::RangeInclusive<f32>,
    label: &str,
    intent: &mut Intent,
) {
    let response = ui.add(egui::Slider::new(value, range).text(label));
    if response.changed() {
        intent.commit |= !response.is_pointer_button_down_on() && !response.dragged();
    }
    intent.commit |= response.drag_stopped();
}
fn rgb(ui: &mut egui::Ui, color: &mut [f32; 3], intent: &mut Intent) {
    for (channel, label) in color.iter_mut().zip(["红 / R", "绿 / G", "蓝 / B"]) {
        slider(ui, channel, 0.0..=1.0, label, intent);
    }
}
fn light(ui: &mut egui::Ui, light: &mut StageLight, intent: &mut Intent) {
    slider(
        ui,
        &mut light.illuminance_lux,
        0.0..=100_000.0,
        "强度 / Lux",
        intent,
    );
    slider(
        ui,
        &mut light.azimuth_degrees,
        -180.0..=180.0,
        "方位 / Azimuth",
        intent,
    );
    slider(
        ui,
        &mut light.elevation_degrees,
        5.0..=89.0,
        "高度 / Elevation",
        intent,
    );
    ui.collapsing("灯色 / Light color", |ui| {
        rgb(ui, &mut light.color_srgb, intent)
    });
}

pub(super) fn draw(ctx: &egui::Context, state: &mut StageUi, stage: &StageSettings) -> Intent {
    let mut intent = Intent::default();
    let mut next = stage.clone();
    if state.open {
        egui::Window::new("试演舞台 / Rehearsal stage")
            .id(egui::Id::new("rehearsal_stage"))
            .open(&mut state.open)
            .default_pos(egui::pos2(195.0, 72.0))
            .default_width(320.0)
            .max_width(360.0)
            .max_height((ctx.viewport_rect().height() - 110.0).max(120.0))
            .vscroll(true)
            .show(ctx, |ui| {
                ui.small("随作品保存 / Saved with Work · Esc cancels preview");
                ui.horizontal_wrapped(|ui| {
                    if ui.button("白棚 / White").clicked() {
                        let mut preset = StageSettings::white_studio();
                        preset.camera = stage.camera.clone();
                        preset.quality = stage.quality;
                        intent.command = Some(Command::SetStage { stage: preset });
                    }
                    if ui.button("黑场 / Black").clicked() {
                        let mut preset = StageSettings::black_space();
                        preset.camera = stage.camera.clone();
                        preset.quality = stage.quality;
                        intent.command = Some(Command::SetStage { stage: preset });
                    }
                });
                ui.horizontal_wrapped(|ui| {
                    ui.label("画质 / Quality");
                    for (quality, label) in [
                        (StageQuality::Low, "低 / Low"),
                        (StageQuality::Balanced, "均衡 / Balanced"),
                        (StageQuality::High, "高 / High"),
                    ] {
                        if ui
                            .selectable_value(&mut next.quality, quality, label)
                            .changed()
                        {
                            intent.commit = true;
                        }
                    }
                });
                ui.small(match next.quality {
                    StageQuality::Low => "MSAA off · shadows off",
                    StageQuality::Balanced => "MSAA 4× · 2048 shadow map",
                    StageQuality::High => "MSAA 4× · 4096 + contact shadows",
                });
                ui.collapsing("背景与地面 / Background & floor", |ui| {
                    ui.label("背景 / Background");
                    rgb(ui, &mut next.background_color_srgb, &mut intent);
                    intent.commit |= ui
                        .checkbox(&mut next.floor.visible, "显示地面 / Show floor")
                        .changed();
                    intent.commit |= ui
                        .checkbox(&mut next.floor.shadows, "阴影 / Shadows")
                        .changed();
                    ui.small("地面高度 / Ground y = 0 · Low disables shadows");
                    ui.label("地面颜色 / Floor color");
                    rgb(ui, &mut next.floor.color_srgb, &mut intent);
                });
                egui::CollapsingHeader::new("主灯 / Key light")
                    .default_open(true)
                    .show(ui, |ui| light(ui, &mut next.key_light, &mut intent));
                ui.collapsing("补光 / Fill light", |ui| {
                    light(ui, &mut next.fill_light, &mut intent)
                });
                ui.collapsing("环境光 / Ambient", |ui| {
                    slider(
                        ui,
                        &mut next.ambient.brightness,
                        0.0..=2000.0,
                        "亮度 / Brightness",
                        &mut intent,
                    );
                    rgb(ui, &mut next.ambient.color_srgb, &mut intent);
                });
                egui::CollapsingHeader::new("相机 / Camera")
                    .default_open(true)
                    .show(ui, |ui| {
                        ui.horizontal_wrapped(|ui| {
                            if ui.button("全身 / Full body").clicked() {
                                next.camera = StageCamera::full_body();
                                intent.commit = true;
                            }
                            if ui.button("特写 / Detail").clicked() {
                                next.camera = StageCamera::detail();
                                intent.commit = true;
                            }
                        });
                        slider(
                            ui,
                            &mut next.camera.azimuth_degrees,
                            -180.0..=180.0,
                            "水平 / Orbit",
                            &mut intent,
                        );
                        slider(
                            ui,
                            &mut next.camera.elevation_degrees,
                            -20.0..=80.0,
                            "仰角 / Elevation",
                            &mut intent,
                        );
                        slider(
                            ui,
                            &mut next.camera.distance,
                            0.35..=20.0,
                            "距离 / Distance × scale",
                            &mut intent,
                        );
                        slider(
                            ui,
                            &mut next.camera.target_height,
                            0.0..=4.0,
                            "取景高度 / Height × scale",
                            &mut intent,
                        );
                        slider(
                            ui,
                            &mut next.camera.fov_degrees,
                            15.0..=75.0,
                            "视野 / FOV",
                            &mut intent,
                        );
                    });
                ui.small("右键拖动环绕，滚轮缩放 / Right-drag orbit, wheel zoom");
            });
    }
    if next != *stage {
        intent.preview = Some(next);
    }
    if ctx.input(|input| input.key_pressed(egui::Key::Escape)) {
        intent = Intent {
            cancel: true,
            ..Default::default()
        };
        state.cancelled_until_release = true;
    }
    if state.cancelled_until_release {
        intent.preview = None;
        intent.commit = false;
        intent.command = None;
        if !ctx.input(|input| input.pointer.any_down()) {
            state.cancelled_until_release = false;
        }
    }
    intent
}

/// Reads the same egui input and editor ownership test as production picking.
/// A drag commits on release; a wheel burst commits after 220 ms of inactivity.
pub(super) fn orbit(
    ctx: &egui::Context,
    scene: egui::Rect,
    state: &mut StageUi,
    stage: &StageSettings,
    intent: &mut Intent,
) {
    let (pressed, down, released, delta, scroll, now, escape, focused) = ctx.input(|input| {
        (
            input.pointer.button_pressed(egui::PointerButton::Secondary),
            input.pointer.button_down(egui::PointerButton::Secondary),
            input
                .pointer
                .button_released(egui::PointerButton::Secondary),
            input.pointer.delta(),
            input.smooth_scroll_delta.y,
            input.time,
            input.key_pressed(egui::Key::Escape),
            input.focused,
        )
    });
    let allowed = focused && !editor_owns_pointer(ctx, scene) && !ctx.egui_wants_keyboard_input();
    if escape || !focused {
        intent.cancel |= state.orbit || state.wheel_deadline.is_some();
        state.orbit = false;
        state.wheel_deadline = None;
        return;
    }
    if state.cancelled_until_release {
        return;
    }
    if pressed && allowed {
        state.orbit = true;
    }
    let mut next = stage.clone();
    if state.orbit && down && !pressed {
        next.camera.azimuth_degrees =
            ((next.camera.azimuth_degrees - delta.x * 0.3 + 180.0).rem_euclid(360.0)) - 180.0;
        next.camera.elevation_degrees =
            (next.camera.elevation_degrees + delta.y * 0.2).clamp(-20.0, 80.0);
    }
    if allowed && scroll.abs() > 0.0 && !state.orbit {
        next.camera.distance = (next.camera.distance * (-scroll * 0.002).exp()).clamp(0.35, 20.0);
        state.wheel_deadline = Some(now + 0.22);
    }
    if next != *stage {
        intent.preview = Some(next);
    }
    if state.orbit && (released || !down) {
        state.orbit = false;
        intent.commit = true;
    }
    if let Some(deadline) = state.wheel_deadline {
        if now >= deadline {
            state.wheel_deadline = None;
            intent.commit = true;
        } else {
            ctx.request_repaint_after(std::time::Duration::from_secs_f64(deadline - now));
        }
    }
}
pub(super) fn apply(editor: &mut EditorState, intent: Intent) -> Result<(), String> {
    if intent.cancel {
        editor.cancel_preview();
        return Ok(());
    }
    if let Some(stage) = intent.preview {
        editor.preview_stage(stage)?;
    }
    if intent.commit {
        editor.commit_preview()?;
    }
    if let Some(command) = intent.command {
        editor.apply(command)?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        CharacterInteraction, EditorUiSession, PlatformIo, Playback, RuntimeStatus, StudioUi,
        UiInputGuard, draw_editor_ui,
    };
    use nvwa_core::{CharacterProfile, SceneDocument};
    struct Harness {
        ctx: egui::Context,
        editor: EditorState,
        ui: StudioUi,
        guard: UiInputGuard,
        playback: Playback,
        io: PlatformIo,
        time: f64,
        size: egui::Vec2,
    }
    impl Harness {
        fn new(size: egui::Vec2) -> Self {
            let mut editor = EditorState::default();
            editor
                .replace(
                    SceneDocument::from_profile(
                        CharacterProfile::from_json(include_str!(
                            "../../../assets/character.profile.json"
                        ))
                        .unwrap(),
                    )
                    .unwrap(),
                )
                .unwrap();
            let mut ui = StudioUi::default();
            ui.stage.open = true;
            Self {
                ctx: egui::Context::default(),
                editor,
                ui,
                guard: Default::default(),
                playback: Playback {
                    clip_id: "idle".into(),
                    ..Default::default()
                },
                io: Default::default(),
                time: 1.0,
                size,
            }
        }
        fn frame(&mut self, events: Vec<egui::Event>) -> egui::FullOutput {
            self.time += 0.016;
            self.ctx.run_ui(
                egui::RawInput {
                    screen_rect: Some(egui::Rect::from_min_size(egui::Pos2::ZERO, self.size)),
                    time: Some(self.time),
                    events,
                    ..Default::default()
                },
                |ui| {
                    draw_editor_ui(
                        ui.ctx(),
                        &RuntimeStatus {
                            ready: true,
                            ..Default::default()
                        },
                        &CharacterInteraction::default(),
                        EditorUiSession {
                            editor: &mut self.editor,
                            playback: &mut self.playback,
                            state: &mut self.ui,
                            io: &mut self.io,
                            guard: &mut self.guard,
                        },
                    )
                    .unwrap()
                },
            )
        }
        fn click(&mut self, pos: egui::Pos2) {
            self.frame(vec![
                egui::Event::PointerMoved(pos),
                pointer(pos, true, egui::PointerButton::Primary),
            ])
            .drop_without_applying_deltas();
            self.frame(vec![pointer(pos, false, egui::PointerButton::Primary)])
                .drop_without_applying_deltas();
        }
    }
    fn pointer(pos: egui::Pos2, pressed: bool, button: egui::PointerButton) -> egui::Event {
        egui::Event::PointerButton {
            pos,
            button,
            pressed,
            modifiers: Default::default(),
        }
    }
    fn key(key: egui::Key) -> egui::Event {
        egui::Event::Key {
            key,
            physical_key: None,
            pressed: true,
            repeat: false,
            modifiers: Default::default(),
        }
    }
    fn label(output: &egui::FullOutput, wanted: &str) -> egui::Rect {
        fn find(shape: &egui::Shape, wanted: &str) -> Option<egui::Rect> {
            match shape {
                egui::Shape::Text(text) if text.galley.job.text == wanted => {
                    Some(text.galley.rect.translate(text.pos.to_vec2()))
                }
                egui::Shape::Vec(shapes) => shapes.iter().find_map(|s| find(s, wanted)),
                _ => None,
            }
        }
        output
            .shapes
            .iter()
            .find_map(|s| find(&s.shape, wanted))
            .unwrap_or_else(|| panic!("missing actual UI label {wanted}"))
    }
    #[test]
    fn real_stage_slider_release_is_one_undo_and_escape_reverts_without_history() {
        for size in [egui::vec2(1280.0, 720.0), egui::vec2(1024.0, 768.0)] {
            let mut h = Harness::new(size);
            h.frame(vec![]).drop_without_applying_deltas();
            let out = h.frame(vec![]);
            let lux = label(&out, "强度 / Lux");
            let before = h.editor.document().unwrap().clone();
            // Window starts at x195; the slider is the first 100pt in its body.
            let start = egui::pos2(220.0, lux.center().y);
            h.frame(vec![
                egui::Event::PointerMoved(start),
                pointer(start, true, egui::PointerButton::Primary),
            ])
            .drop_without_applying_deltas();
            for x in [245.0, 265.0, 285.0] {
                h.frame(vec![egui::Event::PointerMoved(egui::pos2(x, start.y))])
                    .drop_without_applying_deltas();
                assert!(h.guard.pointer);
                assert!(h.editor.preview.is_some());
                assert_eq!(h.editor.document(), Some(&before));
            }
            let end = egui::pos2(285.0, start.y);
            h.frame(vec![pointer(end, false, egui::PointerButton::Primary)])
                .drop_without_applying_deltas();
            let edited = h.editor.document().unwrap().clone();
            assert_eq!(edited.revision, before.revision + 1);
            assert_ne!(
                edited.stage.key_light.illuminance_lux,
                before.stage.key_light.illuminance_lux
            );
            assert_eq!(edited.character, before.character);
            assert_eq!(edited.timeline, before.timeline);
            assert_eq!(
                h.editor
                    .editor
                    .as_ref()
                    .unwrap()
                    .retention_stats()
                    .undo_snapshots,
                1
            );
            h.editor.apply(Command::Undo).unwrap();
            assert_eq!(h.editor.document().unwrap().stage, before.stage);
            h.editor.apply(Command::Redo).unwrap();
            assert_eq!(h.editor.document().unwrap().stage, edited.stage);
            let retained = h.editor.editor.as_ref().unwrap().retention_stats();
            let committed = h.editor.document().unwrap().clone();
            h.frame(vec![
                egui::Event::PointerMoved(start),
                pointer(start, true, egui::PointerButton::Primary),
            ])
            .drop_without_applying_deltas();
            h.frame(vec![egui::Event::PointerMoved(egui::pos2(250.0, start.y))])
                .drop_without_applying_deltas();
            assert!(h.editor.preview.is_some());
            h.frame(vec![key(egui::Key::Escape)])
                .drop_without_applying_deltas();
            h.frame(vec![pointer(start, false, egui::PointerButton::Primary)])
                .drop_without_applying_deltas();
            assert!(h.editor.preview.is_none());
            assert_eq!(h.editor.document(), Some(&committed));
            assert_eq!(
                h.editor.editor.as_ref().unwrap().retention_stats(),
                retained
            );
        }
    }
    #[test]
    fn real_stage_presets_hide_return_and_viewport_orbit_preserve_character_and_playback() {
        let mut h = Harness::new(egui::vec2(1280.0, 720.0));
        h.frame(vec![]).drop_without_applying_deltas();
        let out = h.frame(vec![]);
        let before = h.editor.document().unwrap().clone();
        h.click(label(&out, "黑场 / Black").center());
        assert_eq!(
            h.editor.document().unwrap().stage.background_color_srgb,
            StageSettings::black_space().background_color_srgb
        );
        assert_eq!(h.editor.document().unwrap().character, before.character);
        assert_eq!(h.editor.document().unwrap().timeline, before.timeline);
        let prior = h.editor.document().unwrap().clone();
        let clip = h.playback.clip_id.clone();
        h.ui.stage.open = false;
        h.frame(vec![]).drop_without_applying_deltas();
        h.ui.stage.open = true;
        h.frame(vec![]).drop_without_applying_deltas();
        assert_eq!(h.editor.document(), Some(&prior));
        assert_eq!(h.playback.clip_id, clip);
        // Right drag in the unoccupied scene, outside the floating Stage window.
        let origin = egui::pos2(760.0, 300.0);
        let end = egui::pos2(810.0, 330.0);
        h.frame(vec![
            egui::Event::PointerMoved(origin),
            pointer(origin, true, egui::PointerButton::Secondary),
        ])
        .drop_without_applying_deltas();
        h.frame(vec![egui::Event::PointerMoved(end)])
            .drop_without_applying_deltas();
        assert_eq!(h.editor.document(), Some(&prior));
        assert!(h.editor.preview.is_some());
        h.frame(vec![pointer(end, false, egui::PointerButton::Secondary)])
            .drop_without_applying_deltas();
        let edited = h.editor.document().unwrap();
        assert_eq!(edited.revision, prior.revision + 1);
        assert_ne!(edited.stage.camera, prior.stage.camera);
        assert_eq!(edited.character, prior.character);
        assert_eq!(edited.timeline, prior.timeline);
    }
    #[test]
    fn stage_orbit_rejects_slider_and_text_ime_owned_input() {
        let mut h = Harness::new(egui::vec2(1280.0, 720.0));
        h.frame(vec![]).drop_without_applying_deltas();
        let out = h.frame(vec![]);
        let lux = label(&out, "强度 / Lux");
        let start = egui::pos2(220.0, lux.center().y);
        let before = h.editor.document().unwrap().clone();
        h.frame(vec![
            egui::Event::PointerMoved(start),
            pointer(start, true, egui::PointerButton::Secondary),
        ])
        .drop_without_applying_deltas();
        h.frame(vec![egui::Event::PointerMoved(
            start + egui::vec2(50.0, 20.0),
        )])
        .drop_without_applying_deltas();
        h.frame(vec![pointer(start, false, egui::PointerButton::Secondary)])
            .drop_without_applying_deltas();
        assert!(h.editor.preview.is_none());
        let after_slider = h.editor.document().unwrap().clone();
        assert_eq!(after_slider.stage.camera, before.stage.camera);
        assert_eq!(after_slider.character, before.character);
        assert_eq!(after_slider.timeline, before.timeline);
        // The egui slider accepts secondary drags as value edits. Its light
        // edit is valid; it must never also become a viewport camera gesture.
        // Real Work text edit owns keyboard input, including IME preedit.
        h.click(egui::pos2(500.0, 15.0));
        h.frame(vec![egui::Event::Ime(egui::ImeEvent::Preedit {
            text: "测试".into(),
            active_range_chars: Some(0..2),
        })])
        .drop_without_applying_deltas();
        assert!(h.guard.keyboard);
        let origin = egui::pos2(760.0, 300.0);
        h.frame(vec![
            egui::Event::PointerMoved(origin),
            pointer(origin, true, egui::PointerButton::Secondary),
        ])
        .drop_without_applying_deltas();
        h.frame(vec![egui::Event::PointerMoved(
            origin + egui::vec2(40.0, 20.0),
        )])
        .drop_without_applying_deltas();
        assert!(h.editor.preview.is_none());
        assert_eq!(h.editor.document(), Some(&after_slider));
    }
    #[test]
    fn viewport_orbit_escape_and_wheel_burst_have_bounded_history() {
        let mut h = Harness::new(egui::vec2(1280.0, 720.0));
        h.ui.stage.open = false;
        h.frame(vec![]).drop_without_applying_deltas();
        let before = h.editor.document().unwrap().clone();
        let origin = egui::pos2(700.0, 300.0);
        let end = egui::pos2(750.0, 330.0);
        h.frame(vec![
            egui::Event::PointerMoved(origin),
            pointer(origin, true, egui::PointerButton::Secondary),
        ])
        .drop_without_applying_deltas();
        h.frame(vec![egui::Event::PointerMoved(end)])
            .drop_without_applying_deltas();
        assert!(h.editor.preview.is_some());
        h.frame(vec![key(egui::Key::Escape)])
            .drop_without_applying_deltas();
        h.frame(vec![pointer(end, false, egui::PointerButton::Secondary)])
            .drop_without_applying_deltas();
        assert_eq!(h.editor.document(), Some(&before));
        assert!(h.editor.preview.is_none());
        for _ in 0..3 {
            h.frame(vec![
                egui::Event::PointerMoved(origin),
                egui::Event::MouseWheel {
                    unit: egui::MouseWheelUnit::Point,
                    delta: egui::vec2(0.0, 25.0),
                    phase: egui::TouchPhase::Move,
                    modifiers: Default::default(),
                },
            ])
            .drop_without_applying_deltas();
            assert_eq!(h.editor.document(), Some(&before));
        }
        assert!(h.editor.preview.is_some());
        for _ in 0..48 {
            h.time += 0.05;
            h.frame(vec![]).drop_without_applying_deltas();
        }
        assert!(h.editor.preview.is_none());
        assert_eq!(h.editor.document().unwrap().revision, before.revision + 1);
        assert_ne!(
            h.editor.document().unwrap().stage.camera.distance,
            before.stage.camera.distance
        );
        assert_eq!(
            h.editor
                .editor
                .as_ref()
                .unwrap()
                .retention_stats()
                .undo_snapshots,
            1
        );
    }
    #[test]
    fn real_player_orbit_is_temporary_and_escape_resets_saved_view() {
        let mut h = Harness::new(egui::vec2(1280.0, 720.0));
        let original = h.editor.document().unwrap().clone();
        let retained = h.editor.editor.as_ref().unwrap().retention_stats();
        let mut view = crate::StageViewOverride::default();
        let frame =
            |events: Vec<egui::Event>, h: &mut Harness, view: &mut crate::StageViewOverride| {
                h.time += 0.016;
                h.ctx
                    .run_ui(
                        egui::RawInput {
                            screen_rect: Some(egui::Rect::from_min_size(egui::Pos2::ZERO, h.size)),
                            time: Some(h.time),
                            events,
                            ..Default::default()
                        },
                        |ui| {
                            crate::draw_player(
                                ui.ctx(),
                                &RuntimeStatus {
                                    ready: true,
                                    ..Default::default()
                                },
                                &CharacterInteraction::default(),
                                crate::PlayerSession {
                                    editor: &h.editor,
                                    playback: &mut h.playback,
                                    state: &mut h.ui,
                                    io: &mut h.io,
                                    guard: &mut h.guard,
                                    view,
                                },
                            )
                        },
                    )
                    .drop_without_applying_deltas();
            };
        frame(vec![], &mut h, &mut view);
        let origin = egui::pos2(700.0, 300.0);
        let end = egui::pos2(750.0, 330.0);
        frame(
            vec![
                egui::Event::PointerMoved(origin),
                pointer(origin, true, egui::PointerButton::Secondary),
            ],
            &mut h,
            &mut view,
        );
        frame(vec![egui::Event::PointerMoved(end)], &mut h, &mut view);
        frame(
            vec![pointer(end, false, egui::PointerButton::Secondary)],
            &mut h,
            &mut view,
        );
        assert_ne!(view.camera(&h.editor), Some(&original.stage.camera));
        assert_eq!(h.editor.document(), Some(&original));
        assert_eq!(
            h.editor.editor.as_ref().unwrap().retention_stats(),
            retained
        );
        // Escape during a subsequent gesture restores the saved Player view.
        frame(
            vec![pointer(end, true, egui::PointerButton::Secondary)],
            &mut h,
            &mut view,
        );
        frame(vec![key(egui::Key::Escape)], &mut h, &mut view);
        assert_eq!(view.camera(&h.editor), Some(&original.stage.camera));
        assert_eq!(h.editor.document(), Some(&original));
    }
}
