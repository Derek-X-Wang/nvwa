//! Diagnostic wrapper around the unchanged production builder and renderer.
use bevy::{
    prelude::*,
    render::{
        Render, RenderApp, RenderSystems,
        render_resource::PipelineCache,
        renderer::{RenderAdapter, RenderAdapterInfo, RenderDevice, RenderQueue},
        view::screenshot::{Screenshot, ScreenshotCaptured, save_to_disk},
        view::window::ExtractedWindows,
    },
};
use nvwa_runtime::{Playback, RuntimeStatus};
use std::{path::PathBuf, time::Instant};

fn monotonic_ns() -> u64 {
    let mut ts = libc::timespec { tv_sec: 0, tv_nsec: 0 };
    if unsafe { libc::clock_gettime(libc::CLOCK_MONOTONIC, &mut ts) } != 0 { return 0; }
    ts.tv_sec as u64 * 1_000_000_000 + ts.tv_nsec as u64
}
#[derive(Resource, Clone)]
struct Clock { zero: Instant, captures: PathBuf }
impl Clock {
    fn record(&self, event: &str, fields: serde_json::Value) {
        let before = monotonic_ns();
        let elapsed = self.zero.elapsed().as_secs_f64();
        let after = monotonic_ns();
        eprintln!("NVWA_NATIVE_PROBE {}", serde_json::json!({
            "event":event,"pid":std::process::id(),"monotonic_before_ns":before,
            "process_Instant_elapsed_seconds":elapsed,"monotonic_after_ns":after,"fields":fields,
        }));
    }
}
fn main() -> AppExit {
    let captures = PathBuf::from(std::env::var_os("NVWA_PROBE_CAPTURE_DIR").expect("absolute capture directory required"));
    assert!(captures.is_absolute() && captures.is_dir(), "capture directory must already exist");
    let clock = Clock { zero: Instant::now(), captures };
    clock.record("before_build_app", serde_json::json!({"variant":"diagnostic_wgpu_hal_patch","metal_probe_enabled":std::env::var("NVWA_METAL_PROBE").as_deref()==Ok("1")}));
    let mut app = nvwa_studio::build_app();
    clock.record("after_build_app", serde_json::json!({}));
    app.insert_resource(clock.clone()).add_systems(PostUpdate, observe_main);
    app.get_sub_app_mut(RenderApp).expect("production RenderApp")
        .insert_resource(clock.clone())
        .add_systems(Render, observe_render.after(RenderSystems::Render).before(RenderSystems::Cleanup));
    let exit = app.run();
    clock.record("app_run_returned", serde_json::json!({"exit":format!("{exit:?}")}));
    exit
}
fn request_capture(commands: &mut Commands, clock: &Clock, tag: &'static str) {
    let path = clock.captures.join(format!("{tag}.png"));
    clock.record("screenshot_requested", serde_json::json!({"tag":tag,"path":path}));
    let callback_clock = clock.clone();
    commands.spawn(Screenshot::primary_window())
        .observe(save_to_disk(path))
        .observe(move |event: On<ScreenshotCaptured>| {
            callback_clock.record("screenshot_gpu_readback_callback", serde_json::json!({
                "tag":tag,"width":event.image.width(),"height":event.image.height(),
                "scope":"GPU readback observation; requires pixel inspection; not compositor display time",
            }));
        });
}
fn observe_main(
    mut commands: Commands,
    clock: Res<Clock>, status: Res<RuntimeStatus>, playback: Res<Playback>,
    mut first_update: Local<bool>, mut ready_at: Local<Option<f64>>, mut later: Local<bool>,
) {
    if !*first_update {
        clock.record("first_main_post_update", serde_json::json!({}));
        request_capture(&mut commands, &clock, "first-main-update");
        *first_update = true;
    }
    if status.ready && ready_at.is_none() {
        *ready_at = Some(clock.zero.elapsed().as_secs_f64());
        clock.record("first_runtime_ready_observation", serde_json::json!({
            "bevy_TimeReal_first_ready_seconds":status.first_ready_seconds,"meshes":status.meshes,
            "joints":status.joints,"morph_nodes":status.morph_nodes,"morph_weights":status.morph_weights,
            "playing":playback.playing,"animation_position_seconds":playback.position_seconds,
            "scope":"runtime readiness only; no character-pixel claim",
        }));
        request_capture(&mut commands, &clock, "first-runtime-ready");
    }
    if !*later && ready_at.is_some_and(|at| clock.zero.elapsed().as_secs_f64() - at >= 2.0) {
        request_capture(&mut commands, &clock, "ready-plus-2s");
        clock.record("animation_observation_after_ready_plus_2s", serde_json::json!({
            "playing":playback.playing,"completed":playback.completed,"animation_position_seconds":playback.position_seconds,
        }));
        *later = true;
    }
}
fn observe_render(
    clock: Res<Clock>, windows: Res<ExtractedWindows>, device: Res<RenderDevice>,
    adapter: Res<RenderAdapter>, info: Res<RenderAdapterInfo>, queue: Res<RenderQueue>,
    pipelines: Res<PipelineCache>, mut count: Local<u64>,
) {
    *count += 1;
    if *count == 1 {
        clock.record("first_render_system_returned", serde_json::json!({
            "adapter":info.name,"backend":format!("{:?}",info.backend),
            "adapter_supported_features":format!("{:?}",adapter.features()),
            "device_enabled_features":format!("{:?}",device.features()),
            "timestamp_period_ns":queue.get_timestamp_period(),
            "primary_window":windows.primary.map(|id|format!("{id:?}")),
            "window_dimensions":windows.values().map(|w|serde_json::json!([w.physical_width,w.physical_height])).collect::<Vec<_>>(),
            "waiting_pipelines":pipelines.waiting_pipelines().count(),
            "scope":"CPU return; exact actual display supplied separately by Metal callback",
        }));
    } else if *count <= 1200 && *count % 120 == 0 {
        clock.record("render_sparse", serde_json::json!({"render_count":*count,"waiting_pipelines":pipelines.waiting_pipelines().count()}));
    }
}
