//! Actual production runtime plugin, no window/renderer/GPU. JSONL streams to the checker.
use bevy::{asset::AssetMetaCheck, prelude::*};
use nvwa_core::{CharacterProfile, Command, SceneDocument, TimelineClip};
use nvwa_runtime::{
    EditorState, NvwaRuntimePlugin, Playback, StartupDocumentPolicy, b1_frame_snapshot,
    register_b1_asset_source,
};
use serde_json::{Value, json};
use std::time::{Duration, Instant};

fn tick(app: &mut App, delta: f32) {
    app.insert_resource(bevy::time::TimeUpdateStrategy::ManualDuration(
        Duration::from_secs_f32(delta),
    ));
    app.update();
}
fn wait(
    app: &mut App,
    parameters: &Value,
    clip: &str,
    seconds: f32,
    expected_entry: Option<&str>,
) -> Result<Value, String> {
    let deadline = Instant::now() + Duration::from_secs(45);
    loop {
        tick(app, 0.0);
        if let Ok(frame) = b1_frame_snapshot(app.world()) {
            let sample = &frame["sample"];
            if frame["parameters"] == *parameters
                && sample["clip_id"] == clip
                && expected_entry.is_none_or(|entry| sample["timeline_id"] == entry)
                && sample["source_seconds"]
                    .as_f64()
                    .is_some_and(|t| (t - seconds as f64).abs() < 1e-6)
            {
                return Ok(frame);
            }
        }
        if let Some(error) = &app.world().resource::<EditorState>().open_error {
            return Err(error.clone());
        }
        if Instant::now() >= deadline {
            return Err(format!(
                "production snapshot timeout: recipe={parameters}, clip={clip}, seconds={seconds}"
            ));
        }
        std::thread::sleep(Duration::from_millis(1));
    }
}
fn timeline(clip: &str, looping: bool, speed: f32) -> Command {
    Command::SetTimeline {
        clips: vec![TimelineClip {
            id: "probe-entry".into(),
            clip_id: clip.into(),
            start_seconds: 0.0,
            duration_seconds: 4.0,
            speed,
            looping,
        }],
    }
}
fn emit(kind: &str, request: Value, snapshot: Value) {
    println!(
        "B1_60 {}",
        json!({"kind":kind,"request":request,"snapshot":snapshot})
    );
}
fn run() -> Result<(), String> {
    let assets = std::env::var("B1_60_ASSET_ROOT")
        .map_err(|_| "B1_60_ASSET_ROOT must be the actual absolute asset root")?;
    if !std::path::Path::new(&assets).is_absolute() {
        return Err("asset root must be absolute".into());
    }
    let mut app = App::new();
    register_b1_asset_source(&mut app);
    app.add_plugins((
        MinimalPlugins,
        AssetPlugin {
            file_path: assets,
            meta_check: AssetMetaCheck::Never,
            ..default()
        },
        bevy::transform::TransformPlugin,
        bevy::world_serialization::WorldSerializationPlugin,
        bevy::scene::ScenePlugin,
        bevy::mesh::MeshPlugin,
        bevy::image::ImagePlugin::default(),
        AnimationPlugin,
        bevy::gltf::GltfPlugin::default(),
    ))
    .init_asset::<StandardMaterial>()
    .insert_resource(StartupDocumentPolicy::WaitForOpen)
    .add_plugins(NvwaRuntimePlugin);
    app.finish();
    app.cleanup();
    tick(&mut app, 0.0);
    let document =
        SceneDocument::from_profile(CharacterProfile::b1_motion()).map_err(|e| e.to_string())?;
    app.world_mut()
        .resource_mut::<EditorState>()
        .request_open(document)?;
    let clips = ["b1_arm_rehearsal_v1", "b1_knee_flex_v1"];
    wait(
        &mut app,
        &json!({"torso_length":0.0,"jaw_drop":0.0}),
        clips[0],
        0.0,
        None,
    )?;
    for torso in [-1.0_f32, 0.0, 1.0] {
        for jaw in [-1.0_f32, 0.0, 1.0] {
            let parameters = json!({"torso_length":torso,"jaw_drop":jaw});
            let character_id = app
                .world()
                .resource::<EditorState>()
                .document()
                .unwrap()
                .character
                .id
                .clone();
            app.world_mut()
                .resource_mut::<EditorState>()
                .apply(Command::SetParameters {
                    character_id,
                    values: [("torso_length".into(), torso), ("jaw_drop".into(), jaw)]
                        .into_iter()
                        .collect(),
                })?;
            for clip in clips {
                app.world_mut()
                    .resource_mut::<EditorState>()
                    .apply(timeline(clip, false, 1.0))?;
                app.world_mut().resource_mut::<Playback>().playing = false;
                for k in 0..=32 {
                    let seconds = k as f32 / 8.0;
                    app.world_mut().resource_mut::<Playback>().seek_request = Some(seconds);
                    let frame = wait(&mut app, &parameters, clip, seconds, Some("probe-entry"))?;
                    emit(
                        "matrix",
                        json!({"torso_length":torso,"jaw_drop":jaw,"clip_id":clip,"seconds":seconds,"k":k}),
                        frame,
                    );
                }
                if torso == 0.0 && jaw == 0.0 {
                    for seconds in [2.0_f32, 0.37, 4.0, 0.0, 1.13, 2.0, 2.71, 3.89] {
                        app.world_mut().resource_mut::<Playback>().seek_request = Some(seconds);
                        let frame =
                            wait(&mut app, &parameters, clip, seconds, Some("probe-entry"))?;
                        emit(
                            "seek",
                            json!({"torso_length":torso,"jaw_drop":jaw,"clip_id":clip,"seconds":seconds}),
                            frame,
                        );
                    }
                    let held = b1_frame_snapshot(app.world())?;
                    for _ in 0..3 {
                        tick(&mut app, 0.125);
                    }
                    emit(
                        "pause",
                        json!({"torso_length":torso,"jaw_drop":jaw,"clip_id":clip,"seconds":3.89,"prior_sample":held["sample"],"prior_parts":held["parts"].as_array().unwrap().iter().map(|p| json!({"name":p["name"],"positions":p["positions"]})).collect::<Vec<_>>()}),
                        b1_frame_snapshot(app.world())?,
                    );
                }
            }
        }
    }
    println!(
        "B1_60 {}",
        json!({"kind":"complete","matrix_samples":594,"evidence":"production-plugin CPU; no graphics"})
    );
    Ok(())
}
fn main() {
    if let Err(error) = run() {
        eprintln!("B1_60_ERROR {error}");
        std::process::exit(2);
    }
}
