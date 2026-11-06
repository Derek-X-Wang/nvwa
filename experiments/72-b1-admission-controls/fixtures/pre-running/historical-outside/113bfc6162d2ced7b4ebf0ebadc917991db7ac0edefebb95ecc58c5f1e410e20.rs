//! Rust Studio: egui and the renderer share one Bevy event loop on both targets.
mod appearance_ui;
mod editor_layout;
mod first_save;
mod fonts;
pub mod platform;
mod scene_view;
mod stage_ui;
#[cfg(any(target_arch = "wasm32", test))]
mod web_input;

use bevy::{
    ecs::system::SystemParam,
    prelude::*,
    render::view::screenshot::{Screenshot, ScreenshotCaptured, save_to_disk},
};
use bevy_egui::{EguiContexts, EguiPlugin, EguiPrimaryContextPass, egui};
use nvwa_core::{Command, SceneDocument, TimelineClip};
use nvwa_runtime::{
    CharacterInteraction, CharacterInteractionInput, EditorState, NvwaRuntimePlugin, Playback,
    RuntimeStatus, SceneCamera, StageViewOverride, StartupDocumentPolicy, register_b1_asset_source,
};
use platform::{FileCompletion, PlatformIo};
use std::collections::BTreeMap;

#[derive(Resource)]
struct StudioUi {
    selected: bool,
    layout: editor_layout::EditorLayout,
    file_path: String,
    error: Option<String>,
    save_notice: Option<SaveNotice>,
    first_save: first_save::FirstSave,
    stage: stage_ui::StageUi,
}
impl Default for StudioUi {
    fn default() -> Self {
        Self {
            selected: true,
            layout: default(),
            file_path: "scene.nvwa.json".into(),
            error: None,
            save_notice: None,
            first_save: default(),
            stage: default(),
        }
    }
}

/// Session-only feedback. The dwell starts when the completion is first drawn.
#[derive(Clone)]
struct SaveNotice {
    title: &'static str,
    destination: String,
    work_path: String,
    shown_at: Option<f64>,
}
impl SaveNotice {
    fn new(title: &'static str, destination: String, work_path: String) -> Self {
        Self {
            title,
            destination,
            work_path,
            shown_at: None,
        }
    }

    fn draw(&mut self, ctx: &egui::Context) -> bool {
        const DWELL_SECONDS: f64 = 8.0;
        let now = ctx.input(|input| input.time);
        let shown_at = *self.shown_at.get_or_insert(now);
        let remaining = DWELL_SECONDS - (now - shown_at);
        if remaining <= 0.0 {
            return false;
        }
        ctx.request_repaint_after(std::time::Duration::from_secs_f64(remaining));
        let width = 360.0_f32.min((ctx.viewport_rect().width() - 48.0).max(0.0));
        // Different contents get a fresh sizing pass, so a longer destination
        // cannot reuse a shorter notice's height at the bottom anchor.
        egui::Area::new(egui::Id::new((
            "save_notice",
            self.title,
            &self.destination,
        )))
        .order(egui::Order::Foreground)
        .anchor(egui::Align2::RIGHT_BOTTOM, egui::vec2(-16.0, -16.0))
        .fade_in(false)
        .show(ctx, |ui| {
            // Area's first pass measures its size invisibly. Resolve that
            // pass now so the completion frame already paints the notice.
            if ui.is_sizing_pass() {
                ctx.request_discard("measure save notice before first paint");
            }
            egui::Frame::popup(ui.style()).show(ui, |ui| {
                ui.set_width(width);
                ui.colored_label(egui::Color32::LIGHT_GREEN, self.title);
                egui::ScrollArea::vertical()
                    .max_height(120.0)
                    .show(ui, |ui| {
                        ui.add(egui::Label::new(&self.destination).selectable(true).wrap());
                    });
            });
        });
        true
    }
}

/// This is set by egui, before any viewport keyboard/mouse handler.
/// Stage gestures and picking reject editor-owned input.
#[derive(Resource, Default)]
pub struct UiInputGuard {
    pub pointer: bool,
    pub keyboard: bool,
    scene_view: Option<scene_view::SceneViewport>,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
enum AppMode {
    #[default]
    Studio,
    Player,
}
impl AppMode {
    #[cfg(any(target_arch = "wasm32", test))]
    fn browser_title(self) -> &'static str {
        match self {
            Self::Studio => "Nvwa · Character Studio",
            Self::Player => "Nvwa · Player",
        }
    }

    fn label(self) -> &'static str {
        match self {
            Self::Studio => "studio",
            Self::Player => "player",
        }
    }
}

#[derive(Resource, Clone, Default, Debug)]
struct LaunchConfig {
    mode: AppMode,
    benchmark: bool,
    work: Option<String>,
    error: Option<String>,
}
impl LaunchConfig {
    fn startup_policy(&self) -> StartupDocumentPolicy {
        if self.mode == AppMode::Player || self.work.is_some() || self.error.is_some() {
            StartupDocumentPolicy::WaitForOpen
        } else {
            StartupDocumentPolicy::DefaultFixture
        }
    }
}

pub fn build_app() -> App {
    let (config, smoke) = launch_options();
    build_app_for_mode(config, smoke)
}

fn build_app_for_mode(config: LaunchConfig, smoke: SmokeRun) -> App {
    #[cfg(target_arch = "wasm32")]
    if let Some(document) = web_sys::window().and_then(|window| window.document()) {
        // Use the final Rust launch mode, including the existing error-recovery
        // mode. The HTML bootstrap cannot validate a launch query itself.
        document.set_title(config.mode.browser_title());
    }
    let benchmark = config.benchmark;
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
        title: if config.mode == AppMode::Player {
            "Nvwa · Player"
        } else {
            "Nvwa · Character Studio"
        }
        .into(),
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
    register_b1_asset_source(&mut app);
    app.add_plugins(DefaultPlugins.set(asset_plugin).set(WindowPlugin {
        primary_window: Some(window),
        ..default()
    }))
    .add_plugins((NvwaRuntimePlugin, EguiPlugin::default()))
    .init_resource::<PlatformIo>()
    .insert_resource(StudioUi {
        file_path: config
            .work
            .clone()
            .unwrap_or_else(|| "scene.nvwa.json".into()),
        error: config.error.clone(),
        ..default()
    })
    .insert_resource(config.startup_policy())
    .insert_resource(config)
    .init_resource::<UiInputGuard>()
    .configure_sets(
        PostUpdate,
        (
            nvwa_runtime::RuntimeSystems::Transport.after(bevy_egui::EguiPostUpdateSet::EndPass),
            nvwa_runtime::RuntimeSystems::Mirror.after(bevy_egui::EguiPostUpdateSet::EndPass),
        ),
    )
    .insert_resource(smoke)
    .add_systems(Startup, request_initial_work)
    .add_systems(
        PreUpdate,
        fonts::install_fonts
            .after(bevy_egui::EguiPreUpdateSet::InitContexts)
            .before(bevy_egui::EguiPreUpdateSet::BeginPass),
    )
    .add_systems(EguiPrimaryContextPass, draw_studio)
    .add_systems(Update, poll_files)
    .add_systems(
        PostUpdate,
        scene_view::fit_scene_camera
            .after(bevy_egui::EguiPostUpdateSet::EndPass)
            .after(nvwa_runtime::RuntimeSystems::Mirror)
            .before(bevy::camera::CameraUpdateSystems),
    )
    .add_systems(
        PostUpdate,
        scene_click
            .after(bevy::camera::CameraUpdateSystems)
            .after(bevy_egui::EguiPostUpdateSet::EndPass)
            .after(bevy::transform::TransformSystems::Propagate),
    )
    .add_systems(
        PostUpdate,
        smoke_and_capture.after(nvwa_runtime::RuntimeSystems::Mirror),
    );
    if benchmark {
        // Default Bevy settings are reactive when unfocused. Benchmark cadence
        // must not include that focus-dependent event-loop throttle.
        app.insert_resource(bevy::winit::WinitSettings::continuous());
    }
    #[cfg(target_arch = "wasm32")]
    app.add_plugins(web_input::DesktopWebInputPlugin);
    app
}

#[derive(SystemParam)]
struct ScenePointerInput<'w, 's> {
    buttons: Res<'w, ButtonInput<MouseButton>>,
    guard: Res<'w, UiInputGuard>,
    windows: Query<'w, 's, (Entity, &'static Window), With<bevy::window::PrimaryWindow>>,
    focus: MessageReader<'w, 's, bevy::window::WindowFocused>,
}
impl ScenePointerInput<'_, '_> {
    fn press_cursor(&mut self) -> Option<Vec2> {
        let (entity, window) = self.windows.single().ok()?;
        // Drain every event, including later events in the same frame. The
        // final focused flag alone cannot distinguish a refocus click.
        let mut restored = false;
        for event in self.focus.read() {
            restored |= event.window == entity && event.focused;
        }
        if restored
            || !scene_pointer_allowed(
                self.buttons.just_pressed(MouseButton::Left),
                window.focused,
                self.guard.pointer,
            )
        {
            return None;
        }
        window.cursor_position()
    }
}

fn scene_click(
    mut pointer: ScenePointerInput,
    cameras: Query<(&Camera, &GlobalTransform), With<SceneCamera>>,
    mut interaction: CharacterInteractionInput,
) {
    let Some(cursor) = pointer.press_cursor() else {
        return;
    };
    let Ok((camera, transform)) = cameras.single() else {
        return;
    };
    if !camera.is_active {
        return;
    }
    if camera
        .logical_viewport_rect()
        .is_some_and(|viewport| viewport.contains(cursor))
        && let Ok(ray) = camera.viewport_to_world(transform, cursor)
    {
        interaction.click(ray);
    }
}

fn scene_pointer_allowed(pressed: bool, focused: bool, editor_pointer: bool) -> bool {
    pressed && focused && !editor_pointer
}

fn editor_owns_pointer(ctx: &egui::Context, scene_rect: egui::Rect) -> bool {
    if ctx.egui_is_using_pointer() {
        return true;
    }
    let Some(position) = ctx.input(|input| input.pointer.interact_pos()) else {
        return false;
    };
    // A manually constructed root Ui does not populate egui's run_ui-only
    // root_ui_available_rect. Its generic Background test would consume the
    // entire scene. Use the actual unoccupied rect and retain popup capture.
    !scene_rect.contains(position)
        || ctx
            .layer_id_at(position)
            .is_some_and(|layer| layer.order != egui::Order::Background)
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
    build_app().run()
}

#[cfg(not(target_arch = "wasm32"))]
fn launch_options() -> (LaunchConfig, SmokeRun) {
    let arguments: Vec<_> = std::env::args_os().skip(1).collect();
    match parse_native_args(arguments.clone()) {
        Ok(options) => options,
        Err(error) => (
            LaunchConfig {
                mode: if arguments.iter().any(|argument| argument == "--player") {
                    AppMode::Player
                } else {
                    AppMode::Studio
                },
                error: Some(error),
                ..default()
            },
            SmokeRun::default(),
        ),
    }
}

#[cfg(not(target_arch = "wasm32"))]
fn parse_native_args(
    arguments: impl IntoIterator<Item = std::ffi::OsString>,
) -> std::result::Result<(LaunchConfig, SmokeRun), String> {
    let mut config = LaunchConfig::default();
    let mut smoke = SmokeRun::default();
    let mut seen = std::collections::BTreeSet::new();
    let mut arguments = arguments.into_iter();
    while let Some(argument) = arguments.next() {
        let argument = argument
            .into_string()
            .map_err(|_| "Launch arguments must be UTF-8")?;
        if !seen.insert(argument.clone()) {
            return Err(format!("Duplicate launch argument: {argument}"));
        }
        match argument.as_str() {
            "--player" => config.mode = AppMode::Player,
            "--benchmark" => config.benchmark = true,
            "--smoke" => smoke.enabled = true,
            "--work" | "--capture" | "--smoke-seconds" | "--timeout" => {
                let value = arguments
                    .next()
                    .ok_or_else(|| format!("Missing value for {argument}"))?
                    .into_string()
                    .map_err(|_| format!("{argument} must be UTF-8"))?;
                if value.starts_with("--") || value.is_empty() {
                    return Err(format!("Missing value for {argument}"));
                }
                match argument.as_str() {
                    "--work" => {
                        if !std::path::Path::new(&value).is_absolute() {
                            return Err("--work must be an absolute path".into());
                        }
                        config.work = Some(value);
                    }
                    "--capture" => smoke.capture = Some(value),
                    flag => {
                        let seconds = value
                            .parse::<f64>()
                            .ok()
                            .filter(|value| value.is_finite())
                            .ok_or_else(|| format!("{flag} requires finite seconds"))?;
                        if flag == "--timeout" {
                            smoke.timeout = seconds.clamp(5.0, 120.0);
                        } else {
                            smoke.smoke_seconds = seconds.clamp(1.0, 60.0);
                            smoke.enabled = true;
                        }
                    }
                }
            }
            _ => return Err(format!("Unknown launch argument: {argument}")),
        }
    }
    Ok((config, smoke))
}

#[cfg(any(target_arch = "wasm32", test))]
fn parse_web_pairs(
    pairs: impl IntoIterator<Item = (String, String)>,
) -> std::result::Result<LaunchConfig, String> {
    let mut config = LaunchConfig::default();
    let mut seen = std::collections::BTreeSet::new();
    for (key, value) in pairs {
        if !matches!(key.as_str(), "player" | "work" | "benchmark") {
            continue;
        }
        if !seen.insert(key.clone()) {
            return Err(format!("Duplicate launch query: {key}"));
        }
        match key.as_str() {
            "work" => {
                platform::validate_static_work_path(&value)?;
                config.work = Some(value);
            }
            flag => {
                if value != "0" && value != "1" {
                    return Err(format!("{flag} query must be 0 or 1"));
                }
                if flag == "player" {
                    config.mode = if value == "1" {
                        AppMode::Player
                    } else {
                        AppMode::Studio
                    };
                } else {
                    config.benchmark = value == "1";
                }
            }
        }
    }
    Ok(config)
}

#[cfg(any(target_arch = "wasm32", test))]
fn web_launch_or_recovery(
    parsed: std::result::Result<LaunchConfig, String>,
    requested_mode: AppMode,
) -> LaunchConfig {
    parsed.unwrap_or_else(|error| LaunchConfig {
        mode: requested_mode,
        error: Some(error),
        ..default()
    })
}

#[cfg(target_arch = "wasm32")]
fn launch_options() -> (LaunchConfig, SmokeRun) {
    let mut requested_mode = AppMode::Studio;
    let parsed = web_sys::window()
        .ok_or("Browser window unavailable".into())
        .and_then(|window| {
            window
                .location()
                .search()
                .map_err(|error| format!("Launch query: {error:?}"))
        })
        .and_then(|query| {
            web_sys::UrlSearchParams::new_with_str(&query)
                .map_err(|error| format!("Launch query: {error:?}"))
        })
        .and_then(|params| {
            if params
                .get_all("player")
                .iter()
                .any(|value| value.as_string().as_deref() == Some("1"))
            {
                requested_mode = AppMode::Player;
            }
            let mut pairs = Vec::new();
            for key in ["player", "work", "benchmark"] {
                for value in params.get_all(key).iter() {
                    pairs.push((
                        key.into(),
                        value.as_string().ok_or("Invalid launch query value")?,
                    ));
                }
            }
            parse_web_pairs(pairs)
        });
    let config = web_launch_or_recovery(parsed, requested_mode);
    let smoke = if config.benchmark {
        SmokeRun {
            capture: Some("nvwa-web-benchmark.png".into()),
            smoke_seconds: 15.0,
            timeout: 60.0,
            ..default()
        }
    } else {
        SmokeRun::default()
    };
    (config, smoke)
}

fn request_initial_work(
    config: Res<LaunchConfig>,
    mut io: ResMut<PlatformIo>,
    mut ui: ResMut<StudioUi>,
) {
    let Some(path) = config.work.as_deref() else {
        return;
    };
    #[cfg(not(target_arch = "wasm32"))]
    let result = io.request_open(path);
    #[cfg(target_arch = "wasm32")]
    let result = io.request_open_static(path);
    if let Err(error) = result {
        ui.error = Some(error);
    }
}

#[cfg(all(target_arch = "wasm32", not(feature = "manual-start")))]
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
    ui.first_save.sync(editor, &ui.file_path);
    match result {
        Ok(FileCompletion::Saved(destination)) => {
            if !ui.first_save.saved(editor, &ui.file_path, &destination) {
                ui.save_notice = None;
                return;
            }
            ui.error = None;
            ui.save_notice = Some(SaveNotice::new(
                "已保存 / Saved",
                destination,
                ui.file_path.clone(),
            ));
        }
        #[cfg(any(target_arch = "wasm32", test))]
        Ok(FileCompletion::DownloadStarted(file_name)) => {
            ui.first_save.finish_other_io();
            ui.error = None;
            ui.save_notice = Some(SaveNotice::new(
                "下载已开始 / Download started",
                format!("{file_name} · Check your browser downloads."),
                ui.file_path.clone(),
            ));
        }
        Ok(FileCompletion::Opened(json)) => {
            ui.first_save.finish_other_io();
            ui.first_save.dismiss();
            ui.save_notice = None;
            match SceneDocument::from_json(&json)
                .map_err(|e| e.to_string())
                .and_then(|d| editor.request_open(d))
            {
                Ok(()) => ui.error = None,
                Err(error) => ui.error = Some(error),
            }
        }
        Err(error) => {
            ui.first_save.finish_other_io();
            ui.first_save.dismiss();
            ui.save_notice = None;
            ui.error = Some(error);
        }
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
    interaction: Res<CharacterInteraction>,
    config: Res<LaunchConfig>,
    mut view: ResMut<StageViewOverride>,
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
    if config.mode == AppMode::Player {
        draw_player(
            ctx,
            &status,
            &interaction,
            PlayerSession {
                editor: &editor,
                playback: &mut playback,
                state: &mut state,
                io: &mut io,
                guard: &mut guard,
                view: &mut view,
            },
        );
        return Ok(());
    }
    draw_editor_ui(
        ctx,
        &status,
        &interaction,
        EditorUiSession {
            editor: &mut editor,
            playback: &mut playback,
            state: &mut state,
            io: &mut io,
            guard: &mut guard,
        },
    )
}

/// Borrowed editor session shared by Bevy and real-control headless tests.
struct EditorUiSession<'a> {
    editor: &'a mut EditorState,
    playback: &'a mut Playback,
    state: &'a mut StudioUi,
    io: &'a mut PlatformIo,
    guard: &'a mut UiInputGuard,
}

/// Shared editor draw path, exercised with real controls in headless tests.
fn draw_editor_ui(
    ctx: &egui::Context,
    status: &RuntimeStatus,
    interaction: &CharacterInteraction,
    session: EditorUiSession<'_>,
) -> Result {
    let EditorUiSession {
        editor,
        playback,
        state,
        io,
        guard,
    } = session;
    state.first_save.sync(editor, &state.file_path);
    let mut viewport_ui = egui::Ui::new(
        ctx.clone(),
        "nvwa_viewport".into(),
        egui::UiBuilder::new()
            .layer_id(egui::LayerId::background())
            .max_rect(ctx.viewport_rect()),
    );
    let mut layout = state.layout.clone();
    let mut stage_ui = state.stage.clone();
    let mut save_notice = if io.busy() {
        None
    } else {
        state
            .save_notice
            .clone()
            .filter(|notice| notice.work_path == state.file_path)
    };
    let document = editor.visible_document().cloned();
    let mut next_playback = playback.clone();
    let mut file_action = None;
    let mut new_b1 = false;
    let mut command = None;
    let mut preview: Option<BTreeMap<String, f32>> = None;
    let mut commit_drag = false;
    egui::Panel::top("document_toolbar").show(&mut viewport_ui, |ui| {
        ui.horizontal_wrapped(|ui| {
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
            ui.toggle_value(&mut stage_ui.open, "舞台 / Stage");
            if ui
                .add_enabled(!io.busy(), egui::Button::new("新建人物… / New character…"))
                .clicked()
            {
                new_b1 = true;
            }
            ui.label("作品 / Work");
            let previous_path = state.file_path.clone();
            draw_work_path(ui, &mut state.file_path, 220.0);
            if previous_path != state.file_path {
                state.first_save.dismiss();
                save_notice = None;
            }
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
            if editor.pending_open.is_some() {
                ui.label(
                    "B1 candidate pending · Save keeps current Work · editing cancels candidate",
                );
            }
            if let Some(doc) = editor.document() {
                ui.label(format!("Revision {}", doc.revision));
            }
        });
        if file_action.is_some() {
            save_notice = None;
        }
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
                ui.small(if doc.profile.backend.is_b1_motion() {
                    "B1 positive aggregate CPU · authored rehearsal"
                } else if doc.profile.backend.is_b1() {
                    "B1 positive aggregate CPU · static diagnostics"
                } else {
                    "Skinned humanoid"
                });
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
            layout.draw_tabs(ui);
            if layout.tab == editor_layout::InspectorTab::Shape {
                egui::ScrollArea::vertical()
                    .id_salt("shape_controls")
                    .show(ui, |ui| {
                        ui.label("Shape parameters");
                        ui.small("Drag to preview. Release to make one edit.");
                        let mut values = doc.character.parameters.clone();
                        for parameter in &doc.profile.parameters {
                            let value = values
                                .entry(parameter.id.clone())
                                .or_insert(parameter.default);
                            let response = if doc.profile.backend.is_b1() {
                                let label = ui.label(shape_parameter_label(&parameter.id));
                                ui.add(egui::Slider::new(value, parameter.min..=parameter.max)).labelled_by(label.id)
                            } else {
                                ui.add(egui::Slider::new(value, parameter.min..=parameter.max).text(parameter.id.replace('_', " ")))
                            };
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
                        if let Some(appearance) = appearance_ui::draw(ui, doc) {
                            command = Some(appearance);
                        }
                        if doc.profile.backend.is_b1() {
                            ui.separator();
                            ui.label("Static diagnostic poses");
                            for pose in nvwa_core::B1_DIAGNOSTIC_POSES.iter() {
                                if ui
                                    .selectable_label(
                                        doc.character.diagnostic_pose.as_deref() == Some(*pose),
                                        *pose,
                                    )
                                    .clicked()
                                {
                                    command = Some(Command::SetDiagnosticPose {
                                        character_id: doc.character.id.clone(),
                                        pose_id: (*pose).into(),
                                    });
                                }
                            }
                            ui.small("Selecting a diagnostic stops the timeline. Cloth and full visual quality remain unaccepted.");
                        }
                        ui.separator();
                    });
            }
            if layout.tab == editor_layout::InspectorTab::Profile {
                ui.small(format!("Profile: {}", doc.profile.id));
                ui.small(format!("Asset: {}", doc.profile.asset_path));
                ui.small(format!("License: {}", doc.profile.license));
            }
        });
    let timeline_height = layout.height_for(ctx.viewport_rect().height());
    let state_error = state.error.clone();
    let mut timeline_body = |ui: &mut egui::Ui| {
        if interaction.busy() {
            ui.disable();
        }
        ui.horizontal(|ui| {
            ui.heading(
                if document
                    .as_ref()
                    .is_some_and(|doc| doc.profile.backend.is_b1_motion())
                {
                    "B1 authored rehearsal"
                } else if document
                    .as_ref()
                    .is_some_and(|doc| doc.profile.backend.is_b1())
                {
                    "B1 static diagnostic pose"
                } else {
                    "Animation"
                },
            );
            ui.add_enabled_ui(
                transport_enabled(
                    document.as_ref(),
                    status,
                    &next_playback,
                    interaction.busy(),
                ),
                |ui| {
                    draw_transport_buttons(ui, &mut next_playback);
                },
            );
            if let Some(doc) = document
                .as_ref()
                .filter(|doc| doc.profile.backend.supports_timeline())
            {
                let has_sequence_actions = ["idle", "wave", "turn"]
                    .iter()
                    .all(|id| doc.profile.clips.iter().any(|clip| clip.id == *id));
                if doc.profile.backend.is_glb()
                    && ui
                        .add_enabled(
                            has_sequence_actions,
                            egui::Button::new("Create 9s sequence"),
                        )
                        .clicked()
                {
                    command = Some(Command::SetTimeline {
                        clips: nine_second_sequence(),
                    });
                }
                if doc.profile.backend.is_b1_motion() && ui.button("Create 8s rehearsal").clicked()
                {
                    let clips = b1_eight_second_rehearsal();
                    if doc.timeline != clips {
                        command = Some(Command::SetTimeline { clips });
                    }
                }
                egui::ComboBox::from_id_salt("single_clip")
                    .selected_text("Single action…")
                    .show_ui(ui, |ui| {
                        for clip in &doc.profile.clips {
                            if ui
                                .selectable_label(
                                    doc.is_single_loop() && doc.timeline[0].clip_id == clip.id,
                                    if clip.id == "b1_arm_rehearsal_v1" {
                                        "Arm rehearsal · authored"
                                    } else if clip.id == "b1_knee_flex_v1" {
                                        "Knee flex · authored"
                                    } else {
                                        &clip.id
                                    },
                                )
                                .clicked()
                            {
                                command = Some(Command::SetTimeline {
                                    clips: vec![TimelineClip {
                                        id: "timeline-1".into(),
                                        clip_id: clip.id.clone(),
                                        start_seconds: 0.0,
                                        duration_seconds: clip.duration_seconds,
                                        speed: 1.0,
                                        looping: true,
                                    }],
                                });
                            }
                        }
                    });
                draw_transport_seek(ui, doc, &mut next_playback);
                ui.label(format!(
                    "Active: {} · {}{}",
                    next_playback.active_timeline_id,
                    next_playback.clip_id,
                    if next_playback.completed {
                        " · complete"
                    } else {
                        ""
                    }
                ));
            }
        });
        if let Some(doc) = document
            .as_ref()
            .filter(|doc| doc.profile.backend.supports_timeline())
        {
            let mut ordered = doc.timeline.clone();
            ordered.sort_by(|a, b| a.start_seconds.total_cmp(&b.start_seconds));
            if !doc.is_single_loop() {
                for (index, entry) in ordered.iter().enumerate() {
                    ui.horizontal(|ui| {
                        ui.label(format!(
                            "{} · {:.1}–{:.1}s",
                            index + 1,
                            entry.start_seconds,
                            entry.start_seconds + entry.duration_seconds
                        ));
                        egui::ComboBox::from_id_salt(("sequence_action", &entry.id))
                            .selected_text(&entry.clip_id)
                            .show_ui(ui, |ui| {
                                for clip in &doc.profile.clips {
                                    if ui
                                        .selectable_label(entry.clip_id == clip.id, &clip.id)
                                        .clicked()
                                    {
                                        let mut clips = ordered.clone();
                                        clips[index].clip_id = clip.id.clone();
                                        command = Some(Command::SetTimeline { clips });
                                    }
                                }
                            });
                        ui.label(format!("{:.1}s", entry.duration_seconds));
                        for (label, delta) in [("−0.5s", -0.5), ("+0.5s", 0.5)] {
                            if ui.button(label).clicked() {
                                let mut clips = ordered.clone();
                                clips[index].duration_seconds =
                                    (entry.duration_seconds + delta).clamp(0.5, 10.0);
                                command = Some(Command::SetTimeline {
                                    clips: compact_sequence(clips),
                                });
                            }
                        }
                        if ui.add_enabled(index > 0, egui::Button::new("↑")).clicked() {
                            let mut clips = ordered.clone();
                            clips.swap(index, index - 1);
                            command = Some(Command::SetTimeline {
                                clips: compact_sequence(clips),
                            });
                        }
                        if ui
                            .add_enabled(index + 1 < ordered.len(), egui::Button::new("↓"))
                            .clicked()
                        {
                            let mut clips = ordered.clone();
                            clips.swap(index, index + 1);
                            command = Some(Command::SetTimeline {
                                clips: compact_sequence(clips),
                            });
                        }
                        if ui.button("Remove").clicked() {
                            let mut clips = ordered.clone();
                            clips.remove(index);
                            command = Some(Command::SetTimeline {
                                clips: compact_sequence(clips),
                            });
                        }
                    });
                }
                ui.small("Durations are wall time. Duration, order and removal edits join the rows without gaps.");
            }
        }
        ui.small("Right-drag orbits · wheel zooms · Space plays/pauses without keyboard focus.");
        ui.small(if interaction.busy() {
            "Wave interaction · sequence cursor held"
        } else if document
            .as_ref()
            .is_some_and(|doc| doc.profile.backend.is_b1_motion())
        {
            "B1 authored rehearsal/diagnostic · not AI-generated · shape edits preserve phase"
        } else if document
            .as_ref()
            .is_some_and(|doc| doc.profile.backend.is_b1())
        {
            "B1 static diagnostic pose · shape and pose edits use shared Work commands"
        } else {
            "Original fixture: Click chest/head to wave"
        });
        if let Some(error) = &status.stage_error {
            ui.colored_label(egui::Color32::LIGHT_RED, error);
        }
        if let Some(error) = &status.appearance_error {
            ui.colored_label(egui::Color32::LIGHT_RED, error);
        }
        if let Some(error) = &status.error {
            ui.colored_label(egui::Color32::LIGHT_RED, error);
        }
        if let Some(error) = &next_playback.error {
            ui.colored_label(egui::Color32::LIGHT_RED, error);
        }
        if let Some(error) = &state_error {
            ui.colored_label(egui::Color32::LIGHT_RED, error);
        }
        if let Some(error) = &editor.open_error {
            ui.colored_label(egui::Color32::LIGHT_RED, error);
        }
        ui.label(&editor.message);
    };
    egui::Panel::bottom("timeline")
        .resizable(false)
        .exact_size(timeline_height)
        .show(&mut viewport_ui, |ui| {
            layout.draw_resize(ui, ctx.viewport_rect().height());
            layout.draw_controls(ui);
            egui::ScrollArea::both()
                .id_salt("timeline_scroll")
                .show(ui, &mut timeline_body);
        });
    if let Some(notice) = &mut save_notice
        && !notice.draw(ctx)
    {
        save_notice = None;
    }
    let mut stage_intent = if let Some(document) = &document {
        stage_ui::draw(ctx, &mut stage_ui, &document.stage)
    } else {
        default()
    };
    if let Some(document) = &document {
        stage_ui::orbit(
            ctx,
            viewport_ui.available_rect_before_wrap(),
            &mut stage_ui,
            &document.stage,
            &mut stage_intent,
        );
    }
    let confirmation_intent = state.first_save.draw(ctx);
    let first_save_modal = !matches!(confirmation_intent, first_save::ConfirmationIntent::None)
        || state.first_save.confirmation_open();
    // Do not paint a central egui panel: the scene remains visible through it.
    guard.pointer =
        first_save_modal || editor_owns_pointer(ctx, viewport_ui.available_rect_before_wrap());
    guard.keyboard = first_save_modal || ctx.egui_wants_keyboard_input();
    if !guard.keyboard
        && transport_enabled(
            document.as_ref(),
            status,
            &next_playback,
            interaction.busy(),
        )
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
    guard.scene_view = Some(scene_view::SceneViewport {
        canvas: ctx.viewport_rect(),
        scene: viewport_ui.available_rect_before_wrap(),
    });
    state.layout = layout;
    state.stage = stage_ui;
    state.save_notice = save_notice;
    *playback = next_playback;
    if new_b1 {
        let result = SceneDocument::from_profile(nvwa_core::CharacterProfile::b1_character())
            .map_err(|e| e.to_string())
            .and_then(|doc| state.first_save.request_new(editor, &state.file_path, doc));
        if let Err(error) = result {
            state.error = Some(error);
        }
    }
    if stage_intent.cancel {
        preview = None;
        commit_drag = false;
    }
    if let Err(error) = stage_ui::apply(editor, stage_intent) {
        state.error = Some(error);
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
    if let Some(save) = file_action {
        let result = if save {
            state.first_save.request_save(editor, &state.file_path, io)
        } else {
            state.first_save.dismiss();
            io.request_open(&state.file_path)
        };
        if let Err(error) = result {
            state.error = Some(error);
        }
    }
    match confirmation_intent {
        first_save::ConfirmationIntent::Cancel => state.first_save.dismiss(),
        first_save::ConfirmationIntent::Save => {
            if let Err(error) = state.first_save.confirm(editor, &state.file_path, io) {
                state.error = Some(error);
            }
        }
        first_save::ConfirmationIntent::None => {}
    }
    state.first_save.sync(editor, &state.file_path);
    Ok(())
}

/// Player has immutable access to the editor: transport cannot apply edits.
struct PlayerSession<'a> {
    editor: &'a EditorState,
    playback: &'a mut Playback,
    state: &'a mut StudioUi,
    io: &'a mut PlatformIo,
    guard: &'a mut UiInputGuard,
    view: &'a mut StageViewOverride,
}

fn draw_player(
    ctx: &egui::Context,
    status: &RuntimeStatus,
    interaction: &CharacterInteraction,
    session: PlayerSession<'_>,
) {
    let PlayerSession {
        editor,
        playback,
        state,
        io,
        guard,
        view,
    } = session;
    let mut viewport = egui::Ui::new(
        ctx.clone(),
        "nvwa_player".into(),
        egui::UiBuilder::new()
            .layer_id(egui::LayerId::background())
            .max_rect(ctx.viewport_rect()),
    );
    let mut next = playback.clone();
    let mut open = false;
    egui::Panel::bottom("player_transport")
        .min_size(110.0)
        .show(&mut viewport, |ui| {
            ui.horizontal(|ui| {
                ui.heading("Nvwa Player");
                #[cfg(not(target_arch = "wasm32"))]
                draw_work_path(ui, &mut state.file_path, 240.0);
                open = ui
                    .add_enabled(!io.busy(), egui::Button::new("Open…"))
                    .clicked();
                if io.busy() {
                    ui.label("Opening work…");
                }
                if editor.pending_open.is_some() {
                    ui.label("Verifying B1 candidate · current Work remains active");
                }
                ui.add_enabled_ui(
                    transport_enabled(editor.document(), status, &next, interaction.busy()),
                    |ui| {
                        draw_transport_buttons(ui, &mut next);
                        if let Some(doc) = editor.document() {
                            draw_transport_seek(ui, doc, &mut next);
                        }
                    },
                );
            });
            ui.label(format!(
                "{} · Active: {}{}",
                status.phase,
                next.clip_id,
                if next.completed { " · complete" } else { "" }
            ));
            ui.small(
                if editor
                    .document()
                    .is_some_and(|doc| doc.profile.backend.is_b1_motion())
                {
                    "B1 authored rehearsal/diagnostic · not AI-generated"
                } else if editor
                    .document()
                    .is_some_and(|doc| doc.profile.backend.is_b1())
                {
                    "B1 static diagnostic pose · no continuous motion"
                } else if interaction.busy() {
                    "Wave interaction · sequence cursor held"
                } else {
                    "Original fixture: Click chest/head to wave"
                },
            );
            for error in [
                status.stage_error.as_ref(),
                status.appearance_error.as_ref(),
                status.error.as_ref(),
                next.error.as_ref(),
                state.error.as_ref(),
                editor.open_error.as_ref(),
            ]
            .into_iter()
            .flatten()
            {
                ui.colored_label(egui::Color32::LIGHT_RED, error);
            }
        });
    let mut stage_ui = state.stage.clone();
    let prior_camera = view.camera(editor).cloned();
    let mut orbit_intent = stage_ui::Intent::default();
    if let (Some(document), Some(camera)) = (editor.visible_document(), prior_camera.as_ref()) {
        let mut stage = document.stage.clone();
        stage.camera = camera.clone();
        stage_ui::orbit(
            ctx,
            viewport.available_rect_before_wrap(),
            &mut stage_ui,
            &stage,
            &mut orbit_intent,
        );
    }
    guard.pointer = editor_owns_pointer(ctx, viewport.available_rect_before_wrap());
    guard.keyboard = ctx.egui_wants_keyboard_input();
    if !guard.keyboard
        && transport_enabled(editor.document(), status, &next, interaction.busy())
        && ctx.input(|input| input.key_pressed(egui::Key::Space))
    {
        next.playing = !next.playing;
    }
    if ctx.will_discard() {
        return;
    }
    guard.scene_view = Some(scene_view::SceneViewport {
        canvas: ctx.viewport_rect(),
        scene: viewport.available_rect_before_wrap(),
    });
    *playback = next;
    state.stage = stage_ui;
    if orbit_intent.cancel {
        view.reset();
    } else if let Some(stage) = orbit_intent.preview
        && let Err(error) = view.set(editor, stage.camera)
    {
        state.error = Some(error);
    }
    if open {
        match io.request_open(&state.file_path) {
            Ok(()) => state.error = None,
            Err(error) => state.error = Some(error),
        }
    }
}

fn shape_parameter_label(id: &str) -> String {
    match id {
        "torso_length" => "躯干长度 / Torso length".into(),
        "jaw_drop" => "下颌开合 / Jaw opening".into(),
        "head_width" => "头部宽度 / Head width".into(),
        "nose_width" => "鼻部宽度 / Nose width".into(),
        "mouth_width" => "嘴部宽度 / Mouth width".into(),
        "chin_width" => "下巴宽度 / Chin width".into(),
        "neck_width" => "颈部宽度 / Neck width".into(),
        "hip_width" => "髋部宽度 / Hip width".into(),
        _ => id.replace('_', " "),
    }
}

fn draw_work_path(ui: &mut egui::Ui, path: &mut String, width: f32) {
    #[cfg(target_arch = "wasm32")]
    web_input::work_text_edit(ui, path, width);
    #[cfg(not(target_arch = "wasm32"))]
    ui.add(
        egui::TextEdit::singleline(path)
            .id(egui::Id::new("work_path"))
            .desired_width(width),
    );
}

/// Shared Studio/Player capability gate; old static Works never expose Play,
/// even if a stale transport intent exists before the next runtime update.
fn transport_enabled(
    doc: Option<&SceneDocument>,
    status: &RuntimeStatus,
    playback: &Playback,
    busy: bool,
) -> bool {
    !busy
        && !playback.clip_id.is_empty()
        && doc.is_some_and(|doc| {
            doc.profile.backend.supports_timeline()
                && !doc.timeline.is_empty()
                && (status.ready || doc.profile.backend.is_b1_motion())
        })
}

fn draw_transport_buttons(ui: &mut egui::Ui, playback: &mut Playback) {
    if ui
        .button(if playback.playing {
            "Pause"
        } else if playback.completed {
            "Replay"
        } else {
            "Play"
        })
        .clicked()
    {
        playback.playing = !playback.playing;
    }
    if ui.button("Restart").clicked() {
        playback.seek_request = Some(0.0);
        playback.playing = true;
    }
}

fn draw_transport_seek(ui: &mut egui::Ui, doc: &SceneDocument, playback: &mut Playback) {
    let duration = if doc.is_single_loop() {
        doc.profile
            .clips
            .iter()
            .find(|clip| clip.id == doc.timeline[0].clip_id)
            .map(|clip| clip.duration_seconds)
            .unwrap_or(0.0)
    } else {
        doc.timeline_duration_seconds()
    };
    if duration > 0.0 {
        let mut position = if doc.is_single_loop() {
            playback.position_seconds.rem_euclid(duration)
        } else {
            playback.position_seconds
        };
        if ui
            .add(egui::Slider::new(&mut position, 0.0..=duration).text("seconds"))
            .changed()
        {
            playback.seek_request = Some(position);
        }
    }
}

fn nine_second_sequence() -> Vec<TimelineClip> {
    ["idle", "wave", "turn"]
        .iter()
        .enumerate()
        .map(|(index, clip_id)| TimelineClip {
            id: format!("sequence-{}", index + 1),
            clip_id: (*clip_id).into(),
            start_seconds: index as f32 * 3.0,
            duration_seconds: 3.0,
            speed: 1.0,
            looping: false,
        })
        .collect()
}

fn b1_eight_second_rehearsal() -> Vec<TimelineClip> {
    nvwa_core::B1_MOTION_CLIPS
        .iter()
        .enumerate()
        .map(|(index, clip_id)| TimelineClip {
            id: format!("sequence-{}", index + 1),
            clip_id: (*clip_id).into(),
            start_seconds: index as f32 * nvwa_core::B1_MOTION_DURATION_SECONDS,
            duration_seconds: nvwa_core::B1_MOTION_DURATION_SECONDS,
            speed: 1.0,
            looping: false,
        })
        .collect()
}

fn compact_sequence(mut clips: Vec<TimelineClip>) -> Vec<TimelineClip> {
    let mut start = 0.0;
    for entry in &mut clips {
        entry.start_seconds = start;
        start += entry.duration_seconds;
    }
    clips
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

#[derive(SystemParam)]
struct WorkEvidence<'w> {
    config: Res<'w, LaunchConfig>,
    editor: Res<'w, EditorState>,
    interaction: Res<'w, CharacterInteraction>,
    ui: Res<'w, StudioUi>,
    time: Res<'w, Time<Real>>,
}

fn smoke_and_capture(
    mut commands: Commands,
    mut smoke: ResMut<SmokeRun>,
    status: Res<RuntimeStatus>,
    appearance: Res<nvwa_runtime::AppearanceStatus>,
    playback: Res<Playback>,
    mut exit: MessageWriter<AppExit>,
    surface: RenderSurfaceEvidence,
    work: WorkEvidence,
) {
    let RenderSurfaceEvidence { windows, adapter } = surface;
    if (!smoke.enabled && smoke.capture.is_none()) || smoke.reported {
        return;
    }
    let now = work.time.elapsed_secs_f64();
    if status.ready && smoke.ready_at.is_none() {
        smoke.ready_at = Some(now);
    }
    let warmed = smoke
        .ready_at
        .is_some_and(|start| now - start > smoke.smoke_seconds)
        && appearance.ready
        && !appearance.pending;
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
    let failed = status.error.is_some()
        || status.stage_error.is_some()
        || status.appearance_error.is_some()
        || work.ui.error.is_some()
        || work.editor.open_error.is_some()
        || now > smoke.timeout;
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
        let mut evidence = serde_json::json!({
            "ready": status.ready, "error": status.error.as_ref().or(work.ui.error.as_ref()).or(work.editor.open_error.as_ref()), "elapsed_seconds": now,
            "mode": work.config.mode.label(),
            "stage": work.editor.visible_document().map(|doc| &doc.stage),
            "stage_error": status.stage_error,
            "appearance_error": status.appearance_error,
            "appearance": {
                "requested": appearance.requested,
                "applied": appearance.applied,
                "generation": appearance.generation,
                "revision": appearance.revision,
                "ready": appearance.ready,
                "pending": appearance.pending,
                "retained": appearance.retained,
                "error": appearance.error,
            },
            "document_revision": work.editor.document().map(|doc| doc.revision),
            "timeline_count": work.editor.document().map(|doc| doc.timeline.len()),
            "playing": playback.playing, "completed": playback.completed,
            "interaction_busy": work.interaction.busy(),
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
        let backend_evidence = serde_json::json!({
            "character_backend": work.editor.document().map(|doc| &doc.profile.backend),
            "diagnostic_pose": work.editor.document().and_then(|doc| doc.character.diagnostic_pose.as_ref()),
            "pending_open": work.editor.pending_open.is_some(),
        });
        evidence
            .as_object_mut()
            .expect("evidence is an object")
            .extend(
                backend_evidence
                    .as_object()
                    .expect("backend evidence is an object")
                    .clone(),
            );
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

    #[cfg(not(target_arch = "wasm32"))]
    #[test]
    fn native_launch_work_is_shared_by_studio_player_and_smoke_options() {
        let parse = |args: &[&str]| {
            parse_native_args(args.iter().map(|arg| std::ffi::OsString::from(*arg)))
        };
        let (studio, smoke) = parse(&[
            "--work",
            "/tmp/work.nvwa.json",
            "--benchmark",
            "--smoke",
            "--smoke-seconds",
            "15",
            "--capture",
            "capture.png",
            "--timeout",
            "60",
        ])
        .unwrap();
        assert_eq!(studio.mode, AppMode::Studio);
        assert_eq!(studio.work.as_deref(), Some("/tmp/work.nvwa.json"));
        assert!(matches!(
            studio.startup_policy(),
            StartupDocumentPolicy::WaitForOpen
        ));
        assert!(studio.benchmark && smoke.enabled);
        assert_eq!(smoke.smoke_seconds, 15.0);
        assert_eq!(smoke.timeout, 60.0);
        assert_eq!(smoke.capture.as_deref(), Some("capture.png"));
        let (player, _) = parse(&["--player"]).unwrap();
        assert_eq!(player.mode, AppMode::Player);
        assert!(player.work.is_none());
        assert!(matches!(
            player.startup_policy(),
            StartupDocumentPolicy::WaitForOpen
        ));
        let (default, _) = parse(&[]).unwrap();
        assert!(matches!(
            default.startup_policy(),
            StartupDocumentPolicy::DefaultFixture
        ));
        for args in [
            vec!["--work"],
            vec!["--work", "relative.json"],
            vec!["--player", "--player"],
            vec!["--work", "/a", "--work", "/b"],
            vec!["--smoke-seconds", "NaN"],
            vec!["--timeout", "--player"],
            vec!["--unknown"],
        ] {
            assert!(parse(&args).is_err(), "accepted {args:?}");
        }
        #[cfg(unix)]
        {
            use std::os::unix::ffi::OsStringExt;
            assert!(
                parse_native_args([
                    std::ffi::OsString::from("--work"),
                    std::ffi::OsString::from_vec(vec![b'/', 0xff])
                ])
                .is_err()
            );
        }
    }

    #[test]
    fn web_launch_validation_keeps_mode_separate_from_work_and_rejects_duplicates() {
        let parse = |pairs: &[(&str, &str)]| {
            parse_web_pairs(
                pairs
                    .iter()
                    .map(|(key, value)| ((*key).into(), (*value).into())),
            )
        };
        let studio = parse(&[("work", "works/m1-sequence.nvwa.json")]).unwrap();
        assert_eq!(studio.mode, AppMode::Studio);
        assert!(matches!(
            studio.startup_policy(),
            StartupDocumentPolicy::WaitForOpen
        ));
        let player = parse(&[
            ("player", "1"),
            ("work", "works/m1-sequence.nvwa.json"),
            ("benchmark", "1"),
        ])
        .unwrap();
        assert_eq!(player.mode, AppMode::Player);
        assert!(player.benchmark);
        for pairs in [
            vec![("work", "../work.json")],
            vec![("work", "https://host/work.json")],
            vec![("work", "%2e%2e/work.json")],
            vec![("work", "")],
            vec![("player", "true")],
            vec![("player", "1"), ("player", "0")],
            vec![("work", "works/a.json"), ("work", "works/b.json")],
        ] {
            assert!(parse(&pairs).is_err(), "accepted {pairs:?}");
        }
    }

    #[test]
    fn web_title_follows_validated_launch_and_preserves_error_recovery_mode() {
        let launch = |pairs: &[(&str, &str)], requested_mode| {
            web_launch_or_recovery(
                parse_web_pairs(
                    pairs
                        .iter()
                        .map(|(key, value)| ((*key).into(), (*value).into())),
                ),
                requested_mode,
            )
        };
        for pairs in [vec![], vec![("player", "0")]] {
            // A successful parse owns the mode, regardless of a fallback hint.
            let config = launch(&pairs, AppMode::Player);
            assert_eq!(config.mode.browser_title(), "Nvwa · Character Studio");
            assert!(config.error.is_none());
        }
        let player = launch(
            &[("player", "1"), ("work", "works/alpha.json")],
            AppMode::Studio,
        );
        assert_eq!(player.mode.browser_title(), "Nvwa · Player");
        assert!(player.error.is_none());
        assert_eq!(player.work.as_deref(), Some("works/alpha.json"));

        for (pairs, requested_mode, expected_title) in [
            (
                vec![("player", "true")],
                AppMode::Studio,
                "Nvwa · Character Studio",
            ),
            (
                vec![("player", "1"), ("player", "0")],
                AppMode::Player,
                "Nvwa · Player",
            ),
            (
                vec![("player", "1"), ("work", "../alpha.json")],
                AppMode::Player,
                "Nvwa · Player",
            ),
        ] {
            let rejected = parse_web_pairs(
                pairs
                    .iter()
                    .map(|(key, value)| ((*key).into(), (*value).into())),
            )
            .unwrap_err();
            let config = launch(&pairs, requested_mode);
            assert_eq!(config.mode.browser_title(), expected_title);
            assert_eq!(config.error.as_deref(), Some(rejected.as_str()));
            assert!(config.work.is_none());
            assert!(matches!(
                config.startup_policy(),
                StartupDocumentPolicy::WaitForOpen
            ));
        }
    }

    #[cfg(not(target_arch = "wasm32"))]
    #[test]
    fn failed_initial_work_has_visible_error_and_manual_completion_can_recover() {
        let path = std::env::temp_dir().join(format!(
            "nvwa-missing-launch-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        let mut app = App::new();
        app.insert_resource(LaunchConfig {
            mode: AppMode::Player,
            work: Some(path.to_str().unwrap().into()),
            ..default()
        })
        .init_resource::<PlatformIo>()
        .init_resource::<StudioUi>()
        .init_resource::<EditorState>()
        .add_systems(Startup, request_initial_work)
        .add_systems(Update, poll_files);
        app.update();
        assert!(app.world().resource::<EditorState>().document().is_none());
        assert!(app.world().resource::<StudioUi>().error.is_some());
        assert!(!app.world().resource::<PlatformIo>().busy());
        let document = editor().document().unwrap().clone();
        let mut recovered = EditorState::default();
        let mut ui = app.world_mut().resource_mut::<StudioUi>();
        accept_file_completion(
            Ok(FileCompletion::Opened(document.to_json().unwrap())),
            &mut recovered,
            &mut ui,
        );
        assert!(ui.error.is_none());
        assert_eq!(recovered.document(), Some(&document));
    }

    #[test]
    fn player_ui_transport_is_read_only_and_retains_panel_input_guards() {
        let ctx = egui::Context::default();
        let mut editor = editor();
        editor
            .apply(Command::SetTimeline {
                clips: nine_second_sequence(),
            })
            .unwrap();
        let original = editor.document().unwrap().clone();
        let mut playback = Playback {
            clip_id: "wave".into(),
            playing: true,
            position_seconds: 4.0,
            ..default()
        };
        let mut state = StudioUi::default();
        let mut io = PlatformIo::default();
        let mut guard = UiInputGuard::default();
        let status = RuntimeStatus {
            ready: true,
            ..default()
        };
        let interaction = CharacterInteraction::default();
        for (position, expected_guard) in [
            (egui::pos2(700.0, 250.0), false),
            (egui::pos2(700.0, 710.0), true),
        ] {
            let prior_playing = playback.playing;
            ctx.begin_pass(egui::RawInput {
                screen_rect: Some(egui::Rect::from_min_size(
                    egui::Pos2::ZERO,
                    egui::vec2(1280.0, 720.0),
                )),
                events: vec![
                    egui::Event::PointerMoved(position),
                    egui::Event::Key {
                        key: egui::Key::Space,
                        physical_key: None,
                        pressed: false,
                        repeat: false,
                        modifiers: egui::Modifiers::NONE,
                    },
                    egui::Event::Key {
                        key: egui::Key::Space,
                        physical_key: None,
                        pressed: true,
                        repeat: false,
                        modifiers: egui::Modifiers::NONE,
                    },
                ],
                ..default()
            });
            draw_player(
                &ctx,
                &status,
                &interaction,
                PlayerSession {
                    view: &mut StageViewOverride::default(),
                    editor: &editor,
                    playback: &mut playback,
                    state: &mut state,
                    io: &mut io,
                    guard: &mut guard,
                },
            );
            ctx.end_pass().drop_without_applying_deltas();
            assert_eq!(guard.pointer, expected_guard);
            assert_ne!(playback.playing, prior_playing);
            assert_eq!(editor.document().unwrap(), &original);
        }
        // Player did not add an undo transaction; the preceding authored edit
        // remains the next undo, with one monotonic revision increment.
        editor.apply(Command::Undo).unwrap();
        assert!(editor.document().unwrap().is_single_loop());
        assert_eq!(editor.document().unwrap().revision, original.revision + 1);
    }
    #[test]
    fn refocus_press_is_rejected_but_next_focused_press_reaches_scene_input() {
        use bevy::input::{ButtonState, InputPlugin, mouse::MouseButtonInput};
        use bevy::window::{PrimaryWindow, WindowFocused};
        #[derive(Resource, Default)]
        struct AcceptedCursor(Option<Vec2>);
        fn capture(mut pointer: ScenePointerInput, mut result: ResMut<AcceptedCursor>) {
            result.0 = pointer.press_cursor();
        }
        let mut app = App::new();
        app.add_plugins(InputPlugin)
            .add_message::<WindowFocused>()
            .init_resource::<UiInputGuard>()
            .init_resource::<AcceptedCursor>()
            .add_systems(PostUpdate, capture);
        let mut window = Window {
            focused: true,
            ..default()
        };
        let cursor = Vec2::new(300.0, 200.0);
        window.set_cursor_position(Some(cursor));
        let primary = app.world_mut().spawn((PrimaryWindow, window)).id();
        let other = app.world_mut().spawn(Window::default()).id();
        let button = |state| MouseButtonInput {
            button: MouseButton::Left,
            state,
            window: primary,
        };
        // Winit has applied the final focused=true flag, and a press arrives
        // together with the real focus-restoration message in this frame.
        app.world_mut().write_message(WindowFocused {
            window: primary,
            focused: true,
        });
        app.world_mut().write_message(button(ButtonState::Pressed));
        app.update();
        assert!(
            app.world()
                .resource::<ButtonInput<MouseButton>>()
                .just_pressed(MouseButton::Left)
        );
        assert!(app.world().resource::<AcceptedCursor>().0.is_none());
        app.world_mut().write_message(button(ButtonState::Released));
        app.update();
        app.world_mut().write_message(button(ButtonState::Pressed));
        app.update();
        assert_eq!(app.world().resource::<AcceptedCursor>().0, Some(cursor));
        app.world_mut().write_message(button(ButtonState::Released));
        app.update();
        // A secondary window's focus event must not suppress the primary's
        // ordinary click, and an earlier consumed event must not leak forward.
        app.world_mut().write_message(WindowFocused {
            window: other,
            focused: true,
        });
        app.world_mut().write_message(button(ButtonState::Pressed));
        app.update();
        assert_eq!(app.world().resource::<AcceptedCursor>().0, Some(cursor));
    }

    #[test]
    fn current_egui_frame_guards_panels_and_overlays_but_leaves_scene_clickable() {
        let ctx = egui::Context::default();
        let input = |position| egui::RawInput {
            screen_rect: Some(egui::Rect::from_min_size(
                egui::Pos2::ZERO,
                egui::vec2(1280.0, 720.0),
            )),
            events: vec![egui::Event::PointerMoved(position)],
            ..default()
        };
        let mut guarded = false;
        for (position, expected) in [
            (egui::pos2(700.0, 250.0), false),
            (egui::pos2(20.0, 250.0), true),
            (egui::pos2(700.0, 710.0), true),
            (egui::pos2(700.0, 250.0), false),
        ] {
            ctx.begin_pass(input(position));
            {
                let mut root = egui::Ui::new(
                    ctx.clone(),
                    "viewport-test".into(),
                    egui::UiBuilder::new()
                        .layer_id(egui::LayerId::background())
                        .max_rect(ctx.viewport_rect()),
                );
                egui::Panel::left("test-side")
                    .exact_size(200.0)
                    .show(&mut root, |ui| {
                        ui.label("Editor");
                    });
                egui::Panel::bottom("test-transport")
                    .exact_size(100.0)
                    .show(&mut root, |ui| {
                        ui.label("Transport");
                    });
                guarded = editor_owns_pointer(&ctx, root.available_rect_before_wrap());
            }
            ctx.end_pass().drop_without_applying_deltas();
            assert_eq!(guarded, expected, "pointer {position:?}");
            assert_eq!(scene_pointer_allowed(true, true, guarded), !expected);
        }
        // Real foreground egui area in the otherwise empty viewport.
        for _ in 0..2 {
            ctx.begin_pass(input(egui::pos2(710.0, 260.0)));
            {
                egui::Area::new("popup-test".into())
                    .fixed_pos(egui::pos2(700.0, 250.0))
                    .order(egui::Order::Foreground)
                    .show(&ctx, |ui| {
                        ui.allocate_space(egui::vec2(100.0, 100.0));
                    });
                guarded = editor_owns_pointer(&ctx, ctx.viewport_rect());
            }
            ctx.end_pass().drop_without_applying_deltas();
        }
        assert!(guarded);
        assert!(!scene_pointer_allowed(true, false, false));
        assert!(!scene_pointer_allowed(false, true, false));
    }
    fn editor() -> EditorState {
        let profile = nvwa_core::CharacterProfile::from_json(include_str!(
            "../../../assets/character.profile.json"
        ))
        .unwrap();
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
        accept_file_completion(
            Ok(FileCompletion::Saved("/tmp/scene.json".into())),
            &mut editor,
            &mut ui,
        );
        assert!(ui.save_notice.is_some());
        assert!(ui.error.is_none());
        assert_eq!(editor.document().unwrap(), &original);
    }

    #[test]
    fn sequence_creation_and_reorder_are_atomic_portable_edits() {
        let mut editor = editor();
        let original = editor.document().unwrap().clone();
        editor
            .apply(Command::SetTimeline {
                clips: nine_second_sequence(),
            })
            .unwrap();
        assert_eq!(editor.document().unwrap().revision, original.revision + 1);
        assert_eq!(editor.document().unwrap().timeline_duration_seconds(), 9.0);
        let saved = editor.document().unwrap().to_json().unwrap();
        let reopened = SceneDocument::from_json(&saved).unwrap();
        assert_eq!(&reopened, editor.document().unwrap());
        let mut reordered = reopened.timeline.clone();
        reordered.swap(0, 2);
        editor
            .apply(Command::SetTimeline {
                clips: compact_sequence(reordered),
            })
            .unwrap();
        assert_eq!(editor.document().unwrap().timeline[0].clip_id, "turn");
        editor.apply(Command::Undo).unwrap();
        assert_eq!(editor.document().unwrap().timeline, reopened.timeline);
        editor.apply(Command::Undo).unwrap();
        assert_eq!(editor.document().unwrap().timeline, original.timeline);
        editor.apply(Command::Redo).unwrap();
        assert_eq!(editor.document().unwrap().timeline, reopened.timeline);
    }
}

#[cfg(all(test, not(target_arch = "wasm32")))]
mod save_feedback_tests;

#[cfg(test)]
mod b1_player_transport_tests {
    use super::*;
    #[test]
    fn studio_and_player_gate_static_work_even_with_stale_transport_identity() {
        let status = RuntimeStatus {
            ready: true,
            ..default()
        };
        let stale = Playback {
            clip_id: "idle".into(),
            playing: true,
            active_timeline_id: "timeline-1".into(),
            ..default()
        };
        let static_work = SceneDocument::from_profile(nvwa_core::CharacterProfile::b1()).unwrap();
        assert!(!transport_enabled(
            Some(&static_work),
            &status,
            &stale,
            false
        ));
        let motion = SceneDocument::from_profile(nvwa_core::CharacterProfile::b1_motion()).unwrap();
        let playback = Playback {
            clip_id: nvwa_core::B1_MOTION_CLIPS[0].into(),
            ..default()
        };
        assert!(transport_enabled(Some(&motion), &status, &playback, false));
        assert!(
            transport_enabled(Some(&motion), &RuntimeStatus::default(), &playback, false),
            "Pause remains available while a motion shape fit is pending"
        );
        assert!(!transport_enabled(Some(&motion), &status, &playback, true));
    }
}
