//! Sparse experiment markers. No event here means physically displayed pixels.
use bevy::{
    diagnostic::DiagnosticsStore,
    prelude::*,
    render::{
        Render, RenderApp, RenderSystems,
        diagnostic::RenderDiagnosticsPlugin,
        render_resource::PipelineCache,
        renderer::{RenderAdapterInfo, RenderDevice, RenderQueue},
        view::screenshot::ScreenshotCaptured,
    },
};
use nvwa_runtime::{Playback, RuntimeStatus};
use std::time::Instant;

#[derive(Resource, Clone)]
struct Clock(Instant);
impl Clock {
    fn record(&self, boundary: &str, fields: serde_json::Value) {
        eprintln!("NVWA_STARTUP_PROBE {}", serde_json::json!({
            "boundary": boundary,
            "clock": "process_Instant_since_before_build_app",
            "elapsed_seconds": self.0.elapsed().as_secs_f64(),
            "pid": std::process::id(),
            "fields": fields,
        }));
    }
}

fn main() -> AppExit {
    let clock = Clock(Instant::now());
    clock.record("before_build_app", serde_json::json!({"physical_presentation": "NOT-RUN"}));
    // Production reads the original process arguments; no alternate startup builder.
    let mut app = nvwa_studio::build_app();
    clock.record("after_build_app", serde_json::json!({}));
    app.insert_resource(clock.clone())
        .add_plugins(RenderDiagnosticsPlugin)
        .add_systems(Startup, startup)
        .add_systems(PostUpdate, readiness)
        .add_observer(captured);
    let render_app = app.get_sub_app_mut(RenderApp).expect("production RenderApp required");
    render_app.insert_resource(clock.clone()).add_systems(
        Render,
        after_render_system.after(RenderSystems::Render).before(RenderSystems::Cleanup),
    );
    let result = app.run();
    clock.record("app_run_returned", serde_json::json!({"exit": format!("{result:?}")}));
    result
}

fn startup(clock: Res<Clock>) {
    clock.record("startup_system", serde_json::json!({}));
}

fn readiness(
    clock: Res<Clock>,
    status: Res<RuntimeStatus>,
    playback: Res<Playback>,
    diagnostics: Res<DiagnosticsStore>,
    mut ready: Local<Option<f64>>,
    mut reported: Local<bool>,
    mut completed: Local<bool>,
) {
    if status.ready && ready.is_none() {
        *ready = Some(clock.0.elapsed().as_secs_f64());
        clock.record("first_runtime_ready_observation", serde_json::json!({
            "bevy_asset_ready_seconds": status.first_ready_seconds,
            "bevy_clock": "bevy_TimeReal_since_first_update",
            "meshes": status.meshes, "skins": status.skins, "joints": status.joints,
        }));
    }
    if playback.completed && !*completed {
        clock.record("first_playback_completed_observation", serde_json::json!({
            "playing": playback.playing, "animation_seconds": playback.position_seconds,
            "ready_observed_at_process_seconds": *ready,
            "phase_after_this_boundary": "completed_hold_not_sustained_animation",
        }));
        *completed = true;
    }
    if !*reported && ready.is_some_and(|at| clock.0.elapsed().as_secs_f64() - at >= 2.0) {
        let entries: Vec<_> = diagnostics.iter().map(|entry| serde_json::json!({
            "path": entry.path().as_str(), "latest_value": entry.value(),
            "unit": entry.suffix,
        })).collect();
        clock.record("diagnostics_observation_after_ready_plus_2s", serde_json::json!({"entries": entries}));
        *reported = true;
    }
}

fn captured(event: On<ScreenshotCaptured>, clock: Res<Clock>) {
    clock.record("screenshot_gpu_readback_callback", serde_json::json!({
        "image_width": event.image.width(), "image_height": event.image.height(),
        "physical_presentation": "NOT-RUN",
    }));
}

fn after_render_system(
    clock: Res<Clock>,
    queue: Res<RenderQueue>,
    device: Res<RenderDevice>,
    adapter: Res<RenderAdapterInfo>,
    pipelines: Res<PipelineCache>,
    mut frames: Local<u64>,
) {
    *frames += 1;
    if *frames == 1 {
        clock.record("first_render_system_returned", serde_json::json!({
            "adapter": adapter.name, "backend": format!("{:?}", adapter.backend),
            "enabled_device_features": format!("{:?}", device.features()),
            "timestamp_period_ns": queue.get_timestamp_period(),
            "waiting_pipeline_count": pipelines.waiting_pipelines().count(),
            "physical_presentation": "NOT-RUN",
        }));
        let callback_clock = clock.clone();
        clock.record("first_gpu_completion_callback_registered", serde_json::json!({}));
        queue.on_submitted_work_done(move || {
            callback_clock.record("previous_submissions_gpu_complete_callback", serde_json::json!({
                "delivery_includes_poll_delay": true, "physical_presentation": "NOT-RUN",
            }));
        });
    } else if *frames <= 300 && *frames % 60 == 0 {
        clock.record("render_system_returned_sparse", serde_json::json!({
            "render_frame_count": *frames,
            "waiting_pipeline_count": pipelines.waiting_pipelines().count(),
        }));
    }
}
