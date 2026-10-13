//! Actual Bevy raster captures of the unchanged current production tab painter.
use bevy::{
    prelude::*,
    render::{renderer::RenderAdapterInfo, view::screenshot::{Screenshot, ScreenshotCaptured, save_to_disk}},
};
use bevy_egui::{egui, EguiContexts, EguiInput, EguiPlugin, EguiPreUpdateSet, EguiPrimaryContextPass};
use std::{path::PathBuf, time::Instant};

#[allow(dead_code)]
#[path = "../../../crates/nvwa-studio/src/editor_layout.rs"]
mod editor_layout;
use editor_layout::{EditorLayout, InspectorTab};

const CASES: [&str; 3] = ["normal-shape", "normal-profile", "mutant-profile"];

#[derive(Resource)]
struct Experiment {
    output: PathBuf,
    started: Instant,
    case: usize,
    frames: u32,
    requested: bool,
    captured: bool,
    layout: EditorLayout,
}

fn main() -> AppExit {
    let output = PathBuf::from(std::env::var_os("NVWA_PIXEL_OUTPUT").expect("root-assigned NVWA_PIXEL_OUTPUT required"));
    assert!(output.is_absolute() && output.is_dir(), "root must create exact absolute output directory");
    for case in CASES {
        assert!(!output.join(format!("{case}.png")).exists(), "refuse stale or overwritten capture");
    }
    App::new()
        .add_plugins(DefaultPlugins.set(WindowPlugin {
            primary_window: Some(Window {
                title: "Nvwa · two-tab raster experiment".into(),
                resolution: bevy::window::WindowResolution::new(1280, 720).with_scale_factor_override(1.0),
                resizable: false,
                ..default()
            }),
            ..default()
        }))
        .add_plugins(EguiPlugin::default())
        .insert_resource(bevy::winit::WinitSettings::continuous())
        .insert_resource(Experiment { output, started: Instant::now(), case: 0, frames: 0, requested: false, captured: false, layout: EditorLayout::default() })
        .add_systems(Startup, |mut commands: Commands| { commands.spawn(Camera2d); })
        .add_systems(PreUpdate, fixed_input.after(EguiPreUpdateSet::ProcessInput).before(EguiPreUpdateSet::BeginPass))
        .add_systems(EguiPrimaryContextPass, draw)
        .add_systems(PostUpdate, capture.after(bevy_egui::EguiPostUpdateSet::EndPass))
        .run()
}

fn fixed_input(mut inputs: Query<&mut EguiInput>) {
    for mut input in &mut inputs {
        input.time = Some(1.0);
        input.events.clear();
        input.events.push(egui::Event::PointerGone);
        input.focused = false;
    }
}

fn draw(mut contexts: EguiContexts, mut experiment: ResMut<Experiment>) -> Result {
    let ctx = contexts.ctx_mut()?;
    ctx.set_theme(egui::Theme::Dark);
    ctx.set_pixels_per_point(1.0);
    ctx.style_mut_of(egui::Theme::Dark, |style| {
        style.animation_time = 0.0;
        style.spacing.item_spacing = egui::vec2(8.0, 8.0);
        // Inputs are fixed. The reference is separate literal data in verify_pixels.py.
        style.visuals.widgets.active.bg_fill = if experiment.case == 2 {
            egui::Color32::from_rgb(199, 13, 151)
        } else { egui::Color32::from_rgb(17, 61, 113) };
        style.visuals.widgets.inactive.bg_fill = egui::Color32::from_rgb(149, 37, 71);
        style.visuals.widgets.hovered.bg_fill = egui::Color32::from_rgb(31, 173, 89);
        style.visuals.panel_fill = egui::Color32::from_rgb(227, 211, 163);
        style.visuals.text_cursor.blink = false;
    });
    let mut viewport = egui::Ui::new(ctx.clone(), "pixel-reference-viewport".into(),
        egui::UiBuilder::new().layer_id(egui::LayerId::background()).max_rect(ctx.viewport_rect()));
    egui::CentralPanel::default().frame(egui::Frame::NONE
        .fill(egui::Color32::from_rgb(227, 211, 163))
        .inner_margin(40.0)).show(&mut viewport, |ui| {
        experiment.layout.draw_tabs(ui);
    });
    assert_eq!(ctx.input(|input| input.time), 1.0);
    assert!(ctx.input(|input| input.pointer.hover_pos()).is_none());
    assert!(!ctx.input(|input| input.pointer.any_down()));
    Ok(())
}

fn capture(
    mut commands: Commands,
    mut experiment: ResMut<Experiment>,
    adapter: Option<Res<RenderAdapterInfo>>,
    mut exit: MessageWriter<AppExit>,
) {
    if experiment.started.elapsed().as_secs() > 30 {
        eprintln!("PIXEL_EXPERIMENT_FAILED timeout_without_complete_renderer_captures");
        exit.write(AppExit::error());
        return;
    }
    if experiment.captured {
        let path = experiment.output.join(format!("{}.png", CASES[experiment.case]));
        if !std::fs::metadata(&path).is_ok_and(|meta| meta.len() > 0) { return; }
        println!("PIXEL_CASE {}", serde_json::json!({
            "case": CASES[experiment.case], "selected_tab": format!("{:?}", experiment.layout.tab),
            "png": path, "renderer": adapter.as_ref().map(|info| &info.name),
            "backend": adapter.as_ref().map(|info| format!("{:?}", info.backend)),
            "fixed_time": 1.0, "pixels_per_point": 1.0,
        }));
        if experiment.case == 2 {
            assert_eq!(experiment.layout.tab, InspectorTab::Profile);
            exit.write(AppExit::Success);
            return;
        }
        experiment.case += 1;
        experiment.layout.tab = InspectorTab::Profile;
        experiment.frames = 0;
        experiment.requested = false;
        experiment.captured = false;
    }
    experiment.frames += 1;
    if experiment.frames >= 30 && !experiment.requested {
        let path = experiment.output.join(format!("{}.png", CASES[experiment.case]));
        commands.spawn(Screenshot::primary_window())
            .observe(save_to_disk(path))
            .observe(|_event: On<ScreenshotCaptured>, mut experiment: ResMut<Experiment>| { experiment.captured = true; });
        experiment.requested = true;
    }
}
