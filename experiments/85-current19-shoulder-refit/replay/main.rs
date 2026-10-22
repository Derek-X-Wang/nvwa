//! One actual production app, eighteen legacy samples and a separately opened v2 Work.
//! No window, renderer, GPU, snapshot rewriting, or historical-fixture substitution.
use bevy::{asset::AssetMetaCheck, prelude::*};
use nvwa_core::{CharacterProfile, Command, SceneDocument, TimelineClip};
use nvwa_runtime::{
    EditorState, NvwaRuntimePlugin, Playback, StartupDocumentPolicy, b1_frame_snapshot,
    register_b1_asset_source,
};
use serde_json::{Value, json};
use std::time::{Duration, Instant};

const ARM: &str = "b1_arm_rehearsal_v1";
const KNEE: &str = "b1_knee_flex_v1";

fn tick(app: &mut App) {
    app.insert_resource(bevy::time::TimeUpdateStrategy::ManualDuration(
        Duration::ZERO,
    ));
    app.update();
}

fn wait(app: &mut App, request: &Value, min_generation: u64) -> Result<Value, String> {
    let deadline = Instant::now() + Duration::from_secs(45);
    loop {
        tick(app);
        if let Ok(frame) = b1_frame_snapshot(app.world()) {
            let sample = &frame["sample"];
            if frame["profile_id"] == request["profile_id"]
                && frame["backend"] == request["backend"]
                && frame["parameters"] == request["parameters"]
                && frame["generation"]
                    .as_u64()
                    .is_some_and(|g| g >= min_generation)
                && sample["clip_id"] == request["clip_id"]
                && sample["timeline_id"] == request["timeline_id"]
                && sample["playing"] == false
                && sample["source_seconds"]
                    .as_f64()
                    .is_some_and(|t| (t - request["seconds"].as_f64().unwrap()).abs() < 1e-6)
                && sample["position_seconds"] == sample["source_seconds"]
            {
                return Ok(frame);
            }
        }
        if let Some(error) = &app.world().resource::<EditorState>().open_error {
            return Err(error.clone());
        }
        if Instant::now() >= deadline {
            return Err(format!("production snapshot timeout: request={request}"));
        }
        std::thread::sleep(Duration::from_millis(1));
    }
}

fn request(
    profile: &CharacterProfile,
    parameters: Value,
    clip: &str,
    k: u32,
    entry: &str,
) -> Value {
    json!({"profile_id":profile.id,"backend":profile.backend,"parameters":parameters,
           "clip_id":clip,"seconds":k as f32/8.0,"k":k,"timeline_id":entry})
}

fn emit(
    app: &App,
    run_id: &str,
    case: &str,
    request: Value,
    snapshot: Value,
) -> Result<(), String> {
    let work = app
        .world()
        .resource::<EditorState>()
        .document()
        .ok_or("Work absent")?;
    let work: Value = serde_json::from_str(&work.to_json().map_err(|e| e.to_string())?)
        .map_err(|e| e.to_string())?;
    println!(
        "B1_85_REPLAY {}",
        json!({"kind":"sample","run_id":run_id,
        "case":case,"request":request,"snapshot":snapshot,"work":work})
    );
    Ok(())
}

fn run() -> Result<(), String> {
    let assets = std::env::var("B1_85_ASSET_ROOT").map_err(|_| "B1_85_ASSET_ROOT required")?;
    let run_id = std::env::var("B1_85_RUN_ID").map_err(|_| "B1_85_RUN_ID required")?;
    if !std::path::Path::new(&assets).is_absolute() || run_id.is_empty() {
        return Err("absolute asset root and nonempty new run identity required".into());
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
    tick(&mut app);
    let profile = CharacterProfile::b1_motion();
    let doc = SceneDocument::from_profile(profile.clone()).map_err(|e| e.to_string())?;
    app.world_mut()
        .resource_mut::<EditorState>()
        .request_open(doc)?;
    // Startup's canonical entry differs from the explicit per-case timeline below.
    // Wait for the actual legacy document to become available before commands.
    let deadline = Instant::now() + Duration::from_secs(45);
    loop {
        tick(&mut app);
        if b1_frame_snapshot(app.world()).is_ok() {
            break;
        }
        if let Some(error) = &app.world().resource::<EditorState>().open_error {
            return Err(error.clone());
        }
        if Instant::now() >= deadline {
            return Err("initial production Work timeout".into());
        }
        std::thread::sleep(Duration::from_millis(1));
    }
    let mut cases = Vec::new();
    let mut last_generation = 0;
    for torso in [-1.0_f32, 0.0, 1.0] {
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
                values: [("torso_length".into(), torso), ("jaw_drop".into(), 0.0)]
                    .into_iter()
                    .collect(),
            })?;
        for clip in [ARM, KNEE] {
            app.world_mut()
                .resource_mut::<EditorState>()
                .apply(Command::SetTimeline {
                    clips: vec![TimelineClip {
                        id: "probe-entry".into(),
                        clip_id: clip.into(),
                        start_seconds: 0.0,
                        duration_seconds: 4.0,
                        speed: 1.0,
                        looping: false,
                    }],
                })?;
            app.world_mut().resource_mut::<Playback>().playing = false;
            let keys: &[u32] = if clip == ARM {
                &[0, 8, 16, 24, 32]
            } else {
                &[16]
            };
            for &k in keys {
                app.world_mut().resource_mut::<Playback>().seek_request = Some(k as f32 / 8.0);
                let req = request(
                    &profile,
                    json!({"torso_length":torso,"jaw_drop":0.0}),
                    clip,
                    k,
                    "probe-entry",
                );
                let frame = wait(&mut app, &req, 1)?;
                last_generation = frame["generation"].as_u64().ok_or("generation missing")?;
                let case = format!("t{torso:+}__{clip}__k{k:02}.json.gz");
                emit(&app, &run_id, &case, req, frame)?;
                cases.push(case);
            }
        }
    }
    let anchor = SceneDocument::from_json(include_str!(
        "../../79-shoulder-pose-corrective/works/shoulder-rear-baseline-arms.nvwa.json"
    ))
    .map_err(|e| e.to_string())?;
    let parameters =
        serde_json::to_value(&anchor.character.parameters).map_err(|e| e.to_string())?;
    let req = request(&anchor.profile, parameters, ARM, 16, "hairline-arms");
    app.world_mut()
        .resource_mut::<EditorState>()
        .request_open(anchor)?;
    // Transactional open completes asynchronously and resets playback at commit.
    // Authenticate the new profile/generation at its actual initial sample first.
    let mut opened = req.clone();
    opened["seconds"] = json!(0.0);
    opened["k"] = json!(0);
    wait(&mut app, &opened, last_generation + 1)?;
    app.world_mut().resource_mut::<Playback>().playing = false;
    app.world_mut().resource_mut::<Playback>().seek_request = Some(2.0);
    let frame = wait(&mut app, &req, last_generation + 1)?;
    emit(&app, &run_id, "fresh-default-arm2", req, frame)?;
    cases.push("fresh-default-arm2".into());
    println!(
        "B1_85_REPLAY {}",
        json!({"kind":"complete","run_id":run_id,"samples":cases.len(),"cases":cases})
    );
    Ok(())
}

fn main() {
    if let Err(error) = run() {
        eprintln!("B1_85_REPLAY_ERROR {error}");
        std::process::exit(2);
    }
}
