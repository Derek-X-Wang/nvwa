//! Isolated production CPU snapshots in browser Wasm. No runner/window/renderer/GPU.
use bevy::{asset::AssetMetaCheck, prelude::*};
use nvwa_core::{CharacterProfile, Command, SceneDocument, TimelineClip};
use nvwa_runtime::{
    EditorState, NvwaRuntimePlugin, Playback, RuntimeStatus, StartupDocumentPolicy,
    b1_frame_snapshot, register_b1_asset_source,
};
use serde_json::json;
use std::{cell::RefCell, collections::BTreeSet, time::Duration};
#[cfg(target_arch = "wasm32")]
use wasm_bindgen::prelude::*;

const ARM: &str = "b1_arm_rehearsal_v1";
const KNEE: &str = "b1_knee_flex_v1";

struct Case {
    torso: i32,
    clip: String,
    k: u32,
    applied: bool,
}
struct Host {
    app: App,
    run_id: String,
    pending: Option<Case>,
    seen: BTreeSet<(i32, String, u32)>,
    stopped: bool,
    completed: bool,
    last_torso: Option<i32>,
    last_clip: Option<String>,
}
thread_local! {
    static HOST: RefCell<Option<Host>> = const { RefCell::new(None) };
}

fn tick(app: &mut App) {
    app.insert_resource(bevy::time::TimeUpdateStrategy::ManualDuration(
        Duration::ZERO,
    ));
    app.update();
}
fn build(asset_root: String, run_id: String) -> Result<Host, String> {
    // Production b1_web resolves assets/{path} against the page, independently
    // of AssetPlugin.file_path. Admit exactly that common same-origin root.
    if asset_root != "assets" {
        return Err("asset_root must be assets for the unchanged production Web reader".into());
    }
    if run_id.is_empty()
        || run_id.len() > 128
        || !run_id
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'_')
    {
        return Err("run_id requires 1..128 ASCII letters/digits/underscore/hyphen".into());
    }
    let mut app = App::new();
    register_b1_asset_source(&mut app);
    app.add_plugins((
        MinimalPlugins,
        AssetPlugin {
            file_path: asset_root,
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
    let document =
        SceneDocument::from_profile(CharacterProfile::b1_motion()).map_err(|e| e.to_string())?;
    app.world_mut()
        .resource_mut::<EditorState>()
        .request_open(document)?;
    Ok(Host {
        app,
        run_id,
        pending: None,
        seen: BTreeSet::new(),
        stopped: false,
        completed: false,
        last_torso: None,
        last_clip: None,
    })
}
fn with_host<T>(operation: impl FnOnce(&mut Host) -> Result<T, String>) -> Result<T, String> {
    HOST.with(|slot| {
        let mut slot = slot.try_borrow_mut().map_err(|_| "reentrant replay call")?;
        let host = slot.as_mut().ok_or("replay not initialized")?;
        if host.stopped || host.completed {
            return Err("replay stopped or completed".into());
        }
        let result = operation(host);
        if result.is_err() {
            host.stopped = true;
        }
        result
    })
}
fn begin(host: &mut Host, torso: i32, clip: String, k: u32, run_id: String) -> Result<(), String> {
    if run_id != host.run_id {
        return Err("immutable run_id differs".into());
    }
    if host.pending.is_some() {
        return Err("previous case still pending".into());
    }
    let valid = (-1..=1).contains(&torso)
        && ((clip == ARM && [0, 8, 16, 24, 32].contains(&k)) || (clip == KNEE && k == 16));
    if !valid || host.seen.contains(&(torso, clip.clone(), k)) {
        return Err("unrequested or duplicate legacy18 case".into());
    }
    host.pending = Some(Case {
        torso,
        clip,
        k,
        applied: false,
    });
    Ok(())
}
fn poll_host(host: &mut Host) -> Result<Option<String>, String> {
    if host.pending.is_none() {
        return Ok(None);
    }
    tick(&mut host.app);
    if let Some(error) = host
        .app
        .world()
        .resource::<EditorState>()
        .open_error
        .as_ref()
    {
        return Err(error.clone());
    }
    if let Some(error) = host.app.world().resource::<RuntimeStatus>().error.as_ref() {
        return Err(error.clone());
    }
    let pending = host.pending.as_mut().ok_or("pending case vanished")?;
    if !pending.applied {
        // The initial transactional Open must publish before editing its Work.
        if b1_frame_snapshot(host.app.world()).is_err() {
            return Ok(None);
        }
        // Mirror native replay command ordering: one parameter command per
        // torso, one timeline command/pause per clip, and one seek per slot.
        if host.last_torso != Some(pending.torso) {
            let character_id = host
                .app
                .world()
                .resource::<EditorState>()
                .document()
                .ok_or("ready snapshot without committed Work")?
                .character
                .id
                .clone();
            host.app
                .world_mut()
                .resource_mut::<EditorState>()
                .apply(Command::SetParameters {
                    character_id,
                    values: [
                        ("torso_length".into(), pending.torso as f32),
                        ("jaw_drop".into(), 0.),
                    ]
                    .into_iter()
                    .collect(),
                })?;
            host.last_torso = Some(pending.torso);
            host.last_clip = None;
        }
        if host.last_clip.as_deref() != Some(pending.clip.as_str()) {
            host.app
                .world_mut()
                .resource_mut::<EditorState>()
                .apply(Command::SetTimeline {
                    clips: vec![TimelineClip {
                        id: "probe-entry".into(),
                        clip_id: pending.clip.clone(),
                        start_seconds: 0.,
                        duration_seconds: 4.,
                        speed: 1.,
                        looping: false,
                    }],
                })?;
            host.app.world_mut().resource_mut::<Playback>().playing = false;
            host.last_clip = Some(pending.clip.clone());
        }
        host.app.world_mut().resource_mut::<Playback>().seek_request = Some(pending.k as f32 / 8.);
        pending.applied = true;
        return Ok(None);
    }
    let snapshot = match b1_frame_snapshot(host.app.world()) {
        Ok(frame) => frame,
        Err(_) => return Ok(None),
    };
    let sample = &snapshot["sample"];
    let parameters = json!({"torso_length":pending.torso as f32,"jaw_drop":0.0});
    let seconds = pending.k as f32 / 8.;
    if snapshot["parameters"] != parameters
        || sample["clip_id"] != pending.clip
        || sample["timeline_id"] != "probe-entry"
        || sample["playing"] != false
        || !sample["source_seconds"]
            .as_f64()
            .is_some_and(|v| (v - seconds as f64).abs() < 1e-6)
    {
        return Ok(None);
    }
    let request = json!({"torso_length":pending.torso as f32,"jaw_drop":0.0,
        "clip_id":pending.clip,"seconds":seconds,"k":pending.k});
    let raw = json!({"kind":"matrix","run_id":host.run_id,"request":request,"snapshot":snapshot})
        .to_string();
    host.seen
        .insert((pending.torso, pending.clip.clone(), pending.k));
    host.pending = None;
    Ok(Some(raw))
}

#[cfg(target_arch = "wasm32")]
#[wasm_bindgen]
pub fn init(asset_root: String, run_id: String) -> Result<(), JsValue> {
    HOST.with(|slot| {
        let mut slot = slot
            .try_borrow_mut()
            .map_err(|_| JsValue::from_str("reentrant init"))?;
        if slot.is_some() {
            return Err(JsValue::from_str("init may run only once"));
        }
        *slot = Some(build(asset_root, run_id).map_err(|e| JsValue::from_str(&e))?);
        Ok(())
    })
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen]
pub fn begin_case(torso: i32, clip: String, k: u32, run_id: String) -> Result<(), JsValue> {
    with_host(|host| begin(host, torso, clip, k, run_id)).map_err(|e| JsValue::from_str(&e))
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen]
pub fn poll() -> Result<Option<String>, JsValue> {
    with_host(poll_host).map_err(|e| JsValue::from_str(&e))
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen]
pub fn complete() -> Result<String, JsValue> {
    with_host(|host| {
        if host.pending.is_some() || host.seen.len()!=18 { return Err("exact18 cases not completed".into()); }
        host.completed=true;
        Ok(json!({"kind":"complete","run_id":host.run_id,"matrix_samples":18,
            "evidence":"NEW current production-plugin Wasm CPU replay; historical raw files remain missing; no graphics"}).to_string())
    }).map_err(|e| JsValue::from_str(&e))
}
