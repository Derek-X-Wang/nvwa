//! Rust Studio: egui and the renderer share one Bevy event loop on both targets.
pub mod platform;

use bevy::{
    ecs::system::SystemParam,
    prelude::*,
    render::view::screenshot::{Screenshot, ScreenshotCaptured, save_to_disk},
};
use bevy_egui::{EguiContexts, EguiPlugin, EguiPrimaryContextPass, egui};
use nvwa_core::{Command, SceneDocument, TimelineClip};
use nvwa_runtime::{EditorState, NvwaRuntimePlugin, Playback, RuntimeStatus};
use platform::{FileCompletion, PlatformIo};
use std::collections::BTreeMap;

#[derive(Resource)]
struct StudioUi {
    selected: bool,
    file_path: String,
    error: Option<String>,
}
impl Default for StudioUi {
    fn default() -> Self {
        Self {
            selected: true,
            file_path: "scene.nvwa.json".into(),
            error: None,
        }
    }
}
/// This is set by egui, before any viewport keyboard/mouse handler.
/// The initial Studio camera is fixed; UI drags cannot rotate it.
#[derive(Resource, Default)]
pub struct UiInputGuard {
    pub pointer: bool,
    pub keyboard: bool,
}

pub fn build_app() -> App {
    build_app_for_mode(benchmark_mode())
}

fn build_app_for_mode(benchmark: bool) -> App {
    let mut app = App::new();
    #[cfg(not(target_arch = "wasm32"))]
    let asset_plugin = AssetPlugin {
        file_path: native_asset_root(),
        ..default()
    };
    #[cfg(target_arch = "wasm32")]
    let asset_plugin = AssetPlugin {
        file_path: "assets".into(),
        ..default()
    };
    let window = Window {
        title: "Nvwa · Character Studio".into(),
        resolution: (1280, 720).into(),
        #[cfg(target_arch = "wasm32")]
        canvas: Some("#nvwa".into()),
        #[cfg(target_arch = "wasm32")]
        fit_canvas_to_parent: true,
        ..default()
    };
    let window = if benchmark {
        Window {
            resolution: bevy::window::WindowResolution::new(1280, 720)
                .with_scale_factor_override(1.0),
            // Winit sizes this canvas from the requested physical dimensions.
            // Fitting its CSS size to the parent would restore device-pixel scaling.
            #[cfg(target_arch = "wasm32")]
            fit_canvas_to_parent: false,
            ..window
        }
    } else {
        window
    };
    app.add_plugins(DefaultPlugins.set(asset_plugin).set(WindowPlugin {
        primary_window: Some(window),
        ..default()
    }))
    .add_plugins((NvwaRuntimePlugin, EguiPlugin::default()))
    .init_resource::<PlatformIo>()
    .init_resource::<StudioUi>()
    .init_resource::<UiInputGuard>()
    .configure_sets(
        PostUpdate,
        nvwa_runtime::RuntimeSystems::Mirror.after(bevy_egui::EguiPostUpdateSet::EndPass),
    )
    .insert_resource(SmokeRun::default())
    .add_systems(EguiPrimaryContextPass, draw_studio)
    .add_systems(Update, poll_files)
    .add_systems(
        PostUpdate,
        smoke_and_capture.after(nvwa_runtime::RuntimeSystems::Mirror),
    );
    if benchmark {
        // Default Bevy settings are reactive when unfocused. Benchmark cadence
        // must not include that focus-dependent event-loop throttle.
        app.insert_resource(bevy::winit::WinitSettings::continuous());
    }
    app
}

#[cfg(not(target_arch = "wasm32"))]
fn native_asset_root() -> String {
    if let Ok(path) = std::env::var("NVWA_ASSET_ROOT") {
        return path;
    }
    if let Ok(executable) = std::env::current_exe()
        && let Some(parent) = executable.parent()
    {
        let bundle_assets = parent.join("../Resources/assets");
        if bundle_assets.is_dir() {
            return bundle_assets.to_string_lossy().into_owned();
        }
    }
    format!("{}/../../assets", env!("CARGO_MANIFEST_DIR"))
}

pub fn run() -> AppExit {
    let benchmark = benchmark_mode();
    let mut app = build_app_for_mode(benchmark);
    #[cfg(not(target_arch = "wasm32"))]
    app.insert_resource(SmokeRun::from_args());
    #[cfg(target_arch = "wasm32")]
    if benchmark {
        app.insert_resource(SmokeRun {
            capture: Some("nvwa-web-benchmark.png".into()),
            smoke_seconds: 15.0,
            timeout: 60.0,
            ..default()
        });
    }
    app.run()
}

fn benchmark_mode() -> bool {
    #[cfg(not(target_arch = "wasm32"))]
    {
        std::env::args().any(|argument| argument == "--benchmark")
    }
    #[cfg(target_arch = "wasm32")]
    {
        web_sys::window()
            .and_then(|window| window.location().search().ok())
            .is_some_and(|query| {
                query
                    .trim_start_matches('?')
                    .split('&')
                    .any(|part| part == "benchmark=1")
            })
    }
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen(start)]
pub fn wasm_start() {
    let _ = run();
}

fn poll_files(
    mut io: ResMut<PlatformIo>,
    mut editor: ResMut<EditorState>,
    mut ui: ResMut<StudioUi>,
) {
    let Some(result) = io.poll() else { return };
    accept_file_completion(result, &mut editor, &mut ui);
}

fn accept_file_completion(
    result: std::result::Result<FileCompletion, String>,
    editor: &mut EditorState,
    ui: &mut StudioUi,
) {
    match result {
        Ok(FileCompletion::Saved) => {
            editor.message = "Document saved".into();
            ui.error = None;
        }
        Ok(FileCompletion::Opened(json)) => {
            match SceneDocument::from_json(&json)
                .map_err(|e| e.to_string())
                .and_then(|d| editor.replace(d))
            {
                Ok(()) => ui.error = None,
                Err(error) => ui.error = Some(error),
            }
        }
        Err(error) => ui.error = Some(error),
    }
}

#[derive(SystemParam)]
struct StudioSession<'w> {
    editor: ResMut<'w, EditorState>,
    playback: ResMut<'w, Playback>,
    state: ResMut<'w, StudioUi>,
    io: ResMut<'w, PlatformIo>,
    guard: ResMut<'w, UiInputGuard>,
}

fn draw_studio(
    mut contexts: EguiContexts,
    status: Res<RuntimeStatus>,
    session: StudioSession,
) -> Result {
    let StudioSession {
        mut editor,
        mut playback,
        mut state,
        mut io,
        mut guard,
    } = session;
    let ctx = contexts.ctx_mut()?;
    let mut viewport_ui = egui::Ui::new(
        ctx.clone(),
        "nvwa_viewport".into(),
        egui::UiBuilder::new()
            .layer_id(egui::LayerId::background())
            .max_rect(ctx.viewport_rect()),
    );
    let document = editor.visible_document().cloned();
    let mut next_playback = (*playback).clone();
    let mut file_action = None;
    let mut command = None;
    let mut preview: Option<BTreeMap<String, f32>> = None;
    let mut commit_drag = false;
    egui::Panel::top("document_toolbar").show(&mut viewport_ui, |ui| {
        ui.horizontal(|ui| {
            ui.heading("Nvwa");
            ui.separator();
            if ui
                .add_enabled(document.is_some(), egui::Button::new("Undo"))
                .clicked()
            {
                command = Some(Command::Undo);
            }
            if ui
                .add_enabled(document.is_some(), egui::Button::new("Redo"))
                .clicked()
            {
                command = Some(Command::Redo);
            }
            ui.separator();
            ui.label("File");
            ui.add(egui::TextEdit::singleline(&mut state.file_path).desired_width(220.0));
            if ui
                .add_enabled(!io.busy(), egui::Button::new("Open…"))
                .clicked()
            {
                file_action = Some(false);
            }
            if ui
                .add_enabled(document.is_some() && !io.busy(), egui::Button::new("Save"))
                .clicked()
            {
                file_action = Some(true);
            }
            if io.busy() {
                ui.label("File operation pending…");
            }
            if let Some(doc) = editor.document() {
                ui.label(format!("Revision {}", doc.revision));
            }
        });
    });
    egui::Panel::left("scene_objects")
        .exact_size(180.0)
        .show(&mut viewport_ui, |ui| {
            ui.heading("Scene");
            ui.separator();
            if let Some(doc) = &document {
                if ui
                    .selectable_label(state.selected, format!("◉ {}", doc.character.id))
                    .clicked()
                {
                    state.selected = true;
                }
                ui.small(&doc.profile.id);
                ui.small("Skinned humanoid");
                if ui.button("Clear selection").clicked() {
                    state.selected = false;
                }
            }
            ui.separator();
            ui.label(&status.phase);
            ui.small(format!("Meshes {} · skins {}", status.meshes, status.skins));
            ui.small(format!(
                "Joints {} · morphs {}",
                status.joints, status.morph_weights
            ));
            ui.small(format!(
                "Players {} · active {}",
                status.players, status.active_animations
            ));
        });
    egui::Panel::right("character_inspector")
        .exact_size(280.0)
        .show(&mut viewport_ui, |ui| {
            ui.heading("Character");
            ui.separator();
            if !state.selected {
                ui.label("Select the character to edit it.");
                return;
            }
            let Some(doc) = &document else {
                ui.label("Waiting for a valid profile.");
                return;
            };
            ui.label("Shape parameters");
            ui.small("Drag to preview. Release to make one edit.");
            let mut values = doc.character.parameters.clone();
            for parameter in doc.profile.parameters.iter().take(4) {
                let value = values
                    .entry(parameter.id.clone())
                    .or_insert(parameter.default);
                let response = ui.add(
                    egui::Slider::new(value, parameter.min..=parameter.max)
                        .text(parameter.id.replace('_', " ")),
                );
                if response.changed() {
                    preview = Some(values.clone());
                }
                if response.drag_stopped()
                    || (response.changed()
                        && !response.is_pointer_button_down_on()
                        && !response.dragged())
                {
                    commit_drag = true;
                }
            }
            if editor.preview.is_some() {
                ui.label("Preview · document unchanged");
            }
            if ui.button("Reset shape").clicked() {
                command = Some(Command::SetParameters {
                    character_id: doc.character.id.clone(),
                    values: doc
                        .profile
                        .parameters
                        .iter()
                        .map(|p| (p.id.clone(), p.default))
                        .collect(),
                });
            }
            ui.separator();
            ui.label(format!("Scale {:.2}", doc.character.scale));
            ui.separator();
            ui.small(format!("Profile: {}", doc.profile.id));
            ui.small(format!("Asset: {}", doc.profile.asset_path));
            ui.small(format!("License: {}", doc.profile.license));
        });
    egui::Panel::bottom("timeline").min_size(140.0).show(&mut viewport_ui, |ui| {
        ui.horizontal(|ui| {
            ui.heading("Animation");
            ui.add_enabled_ui(status.ready && !next_playback.clip_id.is_empty(), |ui| {
                if ui.button(if next_playback.playing { "Pause" } else { "Play" }).clicked() { next_playback.playing = !next_playback.playing; }
            });
            if let Some(doc) = &document {
                egui::ComboBox::from_id_salt("clip").selected_text(if next_playback.clip_id.is_empty() { "No animation" } else { &next_playback.clip_id }).show_ui(ui, |ui| {
                    for clip in &doc.profile.clips {
                        if ui.selectable_label(next_playback.clip_id == clip.id, &clip.id).clicked() {
                            command = Some(Command::SetTimeline { clips: vec![TimelineClip { id: "timeline-1".into(), clip_id: clip.id.clone(), start_seconds: 0.0, duration_seconds: clip.duration_seconds, speed: 1.0, looping: true }] });
                            next_playback.clip_id = clip.id.clone();
                            next_playback.seek_request = Some(0.0);
                        }
                    }
                });
                let duration = doc.profile.clips.iter().find(|c| c.id == next_playback.clip_id).map(|c| c.duration_seconds).unwrap_or(1.0);
                let mut position = next_playback.position_seconds.rem_euclid(duration.max(0.01));
                if ui.add(egui::Slider::new(&mut position, 0.0..=duration).text("seconds")).changed() {
                    next_playback.seek_request = Some(position);
                }
            }
        });
        ui.small("Viewport camera is fixed. Space plays or pauses when the editor has no keyboard focus.");
        if let Some(error) = &status.error { ui.colored_label(egui::Color32::LIGHT_RED, error); }
        if let Some(error) = &state.error { ui.colored_label(egui::Color32::LIGHT_RED, error); }
        ui.label(&editor.message);
    });
    // Do not paint a central egui panel: the scene remains visible through it.
    guard.pointer = ctx.egui_wants_pointer_input() || ctx.is_pointer_over_egui();
    guard.keyboard = ctx.egui_wants_keyboard_input();
    if !guard.keyboard
        && !next_playback.clip_id.is_empty()
        && ctx.input(|i| i.key_pressed(egui::Key::Space))
    {
        next_playback.playing = !next_playback.playing;
    }
    if !guard.keyboard && ctx.input(|i| i.modifiers.command && i.key_pressed(egui::Key::Z)) {
        command = Some(if ctx.input(|i| i.modifiers.shift) {
            Command::Redo
        } else {
            Command::Undo
        });
    }
    // egui can repeat a discarded layout pass. Apply side effects only once,
    // after the final pass has produced its input intents.
    if ctx.will_discard() {
        return Ok(());
    }
    *playback = next_playback;
    if let Some(save) = file_action {
        let result = if save {
            editor
                .document()
                .ok_or("No document is open".to_owned())
                .and_then(|d| d.to_json().map_err(|e| e.to_string()))
                .and_then(|json| io.request_save(json, &state.file_path))
        } else {
            io.request_open(&state.file_path)
        };
        if let Err(error) = result {
            state.error = Some(error);
        }
    }
    if let Some(values) = preview
        && let Err(error) = editor.preview_parameters(values)
    {
        state.error = Some(error);
    }
    if commit_drag && let Err(error) = editor.commit_preview() {
        state.error = Some(error);
    }
    if let Some(command) = command {
        match editor.apply(command) {
            Ok(()) => state.error = None,
            Err(error) => state.error = Some(error),
        }
    }
    Ok(())
}

#[derive(Resource)]
struct SmokeRun {
    enabled: bool,
    capture: Option<String>,
    timeout: f64,
    smoke_seconds: f64,
    ready_at: Option<f64>,
    requested_capture: bool,
    #[cfg(not(target_arch = "wasm32"))]
    capture_started: Option<std::time::SystemTime>,
    captured: bool,
    capture_callback_seconds: Option<f64>,
    reported: bool,
}
impl Default for SmokeRun {
    fn default() -> Self {
        Self {
            enabled: false,
            capture: None,
            timeout: 45.0,
            smoke_seconds: 3.0,
            ready_at: None,
            requested_capture: false,
            #[cfg(not(target_arch = "wasm32"))]
            capture_started: None,
            captured: false,
            capture_callback_seconds: None,
            reported: false,
        }
    }
}
impl SmokeRun {
    #[cfg(not(target_arch = "wasm32"))]
    fn from_args() -> Self {
        let mut options = Self::default();
        let mut args = std::env::args().skip(1);
        while let Some(argument) = args.next() {
            match argument.as_str() {
                "--smoke" => options.enabled = true,
                "--smoke-seconds" => {
                    if let Some(value) = args
                        .next()
                        .and_then(|s| s.parse::<f64>().ok())
                        .filter(|value| value.is_finite())
                    {
                        options.enabled = true;
                        options.smoke_seconds = value.clamp(1.0, 60.0);
                    }
                }
                "--capture" => options.capture = args.next(),
                "--timeout" => {
                    if let Some(value) = args
                        .next()
                        .and_then(|s| s.parse::<f64>().ok())
                        .filter(|value| value.is_finite())
                    {
                        options.timeout = value.clamp(5.0, 120.0);
                    }
                }
                _ => {}
            }
        }
        options
    }
}
fn capture_completed(
    _capture: On<ScreenshotCaptured>,
    mut smoke: ResMut<SmokeRun>,
    time: Res<Time<Real>>,
) {
    smoke.captured = true;
    smoke.capture_callback_seconds = Some(time.elapsed_secs_f64());
}
#[derive(SystemParam)]
struct RenderSurfaceEvidence<'w, 's> {
    windows: Query<'w, 's, &'static Window, With<bevy::window::PrimaryWindow>>,
    adapter: Option<Res<'w, bevy::render::renderer::RenderAdapterInfo>>,
}

fn smoke_and_capture(
    mut commands: Commands,
    mut smoke: ResMut<SmokeRun>,
    status: Res<RuntimeStatus>,
    playback: Res<Playback>,
    time: Res<Time<Real>>,
    mut exit: MessageWriter<AppExit>,
    surface: RenderSurfaceEvidence,
) {
    let RenderSurfaceEvidence { windows, adapter } = surface;
    if (!smoke.enabled && smoke.capture.is_none()) || smoke.reported {
        return;
    }
    let now = time.elapsed_secs_f64();
    if status.ready && smoke.ready_at.is_none() {
        smoke.ready_at = Some(now);
    }
    let warmed = smoke
        .ready_at
        .is_some_and(|start| now - start > smoke.smoke_seconds);
    if warmed
        && !smoke.requested_capture
        && let Some(path) = smoke.capture.clone()
    {
        commands
            .spawn(Screenshot::primary_window())
            .observe(save_to_disk(path))
            .observe(capture_completed);
        smoke.requested_capture = true;
        #[cfg(not(target_arch = "wasm32"))]
        {
            smoke.capture_started = Some(std::time::SystemTime::now());
        }
    }
    #[cfg(not(target_arch = "wasm32"))]
    let capture_file_bytes = smoke
        .capture
        .as_ref()
        .and_then(|path| std::fs::metadata(path).ok())
        .map(|meta| meta.len())
        .unwrap_or(0);
    #[cfg(target_arch = "wasm32")]
    let capture_file_bytes = 0_u64;
    #[cfg(not(target_arch = "wasm32"))]
    let capture_fresh = smoke
        .capture
        .as_ref()
        .and_then(|path| std::fs::metadata(path).ok())
        .and_then(|meta| meta.modified().ok())
        .zip(smoke.capture_started)
        .is_some_and(|(modified, started)| modified >= started);
    #[cfg(not(target_arch = "wasm32"))]
    let capture_complete = smoke.captured && capture_file_bytes > 0 && capture_fresh;
    #[cfg(target_arch = "wasm32")]
    let capture_complete = smoke.captured;
    let complete = warmed && (smoke.capture.is_none() || capture_complete);
    let failed = status.error.is_some() || now > smoke.timeout;
    if complete || failed {
        let mut times = status.warmed_frame_times_ms.clone();
        times.sort_by(f32::total_cmp);
        let percentile = |fraction: f32| {
            times
                .get(((times.len().saturating_sub(1)) as f32 * fraction) as usize)
                .copied()
        };
        let dimensions = windows.iter().next().map(|window| serde_json::json!({ "width": window.physical_width(), "height": window.physical_height(), "scale_factor": window.scale_factor() }));
        let gpu = adapter.as_ref().map(|adapter| serde_json::json!({ "name": adapter.name, "backend": format!("{:?}", adapter.backend) }));
        let evidence = serde_json::json!({
            "ready": status.ready, "error": status.error, "elapsed_seconds": now,
            "build_profile": if cfg!(debug_assertions) { "dev" } else { "release" },
            "physical_window": dimensions, "gpu": gpu, "first_asset_ready_seconds": status.first_ready_seconds,
            "capture_callback_seconds": smoke.capture_callback_seconds, "ready_frames": status.ready_frames,
            "first_visible_upper_bound_seconds": smoke.capture_callback_seconds,
            "first_visible_kind": "screenshot_callback_after_requested_warmup",
            "frame_timing_kind": "main_loop_cadence_not_gpu_timestamp", "frame_sample_count": times.len(),
            "clock": "bevy_TimeReal_since_first_update",
            "frames": status.frames, "frame_ms_p50": percentile(0.5), "frame_ms_p95": percentile(0.95),
            "meshes": status.meshes, "skins": status.skins, "joints": status.joints,
            "morph_nodes": status.morph_nodes, "morph_weights": status.morph_weights,
            "players": status.players, "active_animations": status.active_animations,
            "paused_animations": status.paused_animations, "clip": playback.clip_id,
            "animation_seconds": playback.position_seconds, "capture_callback": smoke.captured,
            "capture_file_bytes": capture_file_bytes, "frame_sample": "recent_up_to_600_frames_after_readiness_plus_1s_warmup",
            "timeout": now > smoke.timeout,
        });
        info!("NVWA_EVIDENCE {evidence}");
        smoke.reported = true;
        if smoke.enabled {
            exit.write(if complete && !failed {
                AppExit::Success
            } else {
                AppExit::error()
            });
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn editor() -> EditorState {
        let profile =
            serde_json::from_str(include_str!("../../../assets/character.profile.json")).unwrap();
        let mut editor = EditorState::default();
        editor
            .replace(SceneDocument::from_profile(profile).unwrap())
            .unwrap();
        editor
    }
    #[test]
    fn opening_empty_payload_is_an_error_and_preserves_document() {
        let mut editor = editor();
        let original = editor.document().unwrap().clone();
        let mut ui = StudioUi::default();
        accept_file_completion(
            Ok(FileCompletion::Opened(String::new())),
            &mut editor,
            &mut ui,
        );
        assert!(ui.error.is_some());
        assert_eq!(editor.document().unwrap(), &original);
        assert_ne!(editor.message, "Document saved");
    }
    #[test]
    fn saved_completion_does_not_replace_document() {
        let mut editor = editor();
        let original = editor.document().unwrap().clone();
        let mut ui = StudioUi {
            error: Some("old error".into()),
            ..default()
        };
        accept_file_completion(Ok(FileCompletion::Saved), &mut editor, &mut ui);
        assert_eq!(editor.message, "Document saved");
        assert!(ui.error.is_none());
        assert_eq!(editor.document().unwrap(), &original);
    }
}
