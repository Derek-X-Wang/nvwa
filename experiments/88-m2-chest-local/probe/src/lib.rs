//! Bounded diagnostic using the unmodified Studio production graph.
use bevy::{
    animation::graph::AnimationNodeType,
    app::AnimationSystems,
    gltf::{Gltf, GltfMesh, GltfNode, GltfSkin},
    mesh::skinning::{SkinnedMesh, SkinnedMeshInverseBindposes},
    prelude::*,
};
use nvwa_runtime::{EditorState, Playback, RuntimeStatus};
use serde_json::{Value, json};
use std::collections::{BTreeMap, BTreeSet};

const KEYS: [u32; 7] = [0, 15, 30, 45, 60, 75, 89];
const CLIP: &str = "genuine44_calibrated47";
const SCHEDULE: &str = "PostUpdate.after(AnimationSystems).after(TransformSystems::Propagate)";
#[derive(Resource, Default)]
struct Probe {
    frame: u64,
    key: usize,
    settled: u32,
    samples: Vec<Value>,
    done: bool,
    requested: bool,
    exit_after: Option<f64>,
    failed: bool,
}

pub fn run() -> AppExit {
    let mut app = nvwa_studio::build_app();
    app.init_resource::<Probe>()
        .add_systems(Startup, identify_window)
        .insert_resource(bevy::winit::WinitSettings::continuous())
        .add_systems(
            PostUpdate,
            request_seek.before(nvwa_runtime::RuntimeSystems::Transport),
        )
        .add_systems(
            PostUpdate,
            capture
                .after(AnimationSystems)
                .after(bevy::transform::TransformSystems::Propagate),
        );
    app.run()
}
fn identify_window(mut windows: Query<&mut Window>) {
    for mut window in &mut windows {
        window.title = "Nvwa · Frozen upper-arm A/B probe".into();
    }
}

#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen(start)]
pub fn start() {
    let _ = run();
}

fn key_time(index: usize) -> f32 {
    (KEYS[index] as f64 / 30.0) as f32
}
fn request_seek(
    mut probe: ResMut<Probe>,
    status: Res<RuntimeStatus>,
    mut playback: ResMut<Playback>,
) {
    if probe.done || !status.ready || probe.key >= KEYS.len() {
        return;
    }
    probe.requested = true;
    playback.playing = false;
    playback.seek_request = Some(key_time(probe.key));
}
fn capture(world: &mut World) {
    if world.resource::<Probe>().done {
        #[cfg(not(target_arch = "wasm32"))]
        if world
            .resource::<Probe>()
            .exit_after
            .is_some_and(|deadline| world.resource::<Time<Real>>().elapsed_secs_f64() >= deadline)
        {
            let exit = if world.resource::<Probe>().failed {
                AppExit::error()
            } else {
                AppExit::Success
            };
            world.write_message(exit);
        }
        return;
    }
    world.resource_mut::<Probe>().frame += 1;
    let status = world.resource::<RuntimeStatus>();
    if let Some(error) = &status.error {
        finish(world, Some(format!("runtime: {error}")));
        return;
    }
    if world.resource::<Time<Real>>().elapsed_secs_f64() > 60.0 {
        finish(world, Some("60 second readiness/capture timeout".into()));
        return;
    }
    if !status.ready || !world.resource::<Probe>().requested {
        return;
    }
    match sample(world) {
        Err(error) => finish(world, Some(error)),
        Ok(value) => {
            let mut probe = world.resource_mut::<Probe>();
            probe.settled += 1;
            if probe.settled >= 2 {
                probe.samples.push(value);
                probe.key += 1;
                probe.settled = 0;
                probe.requested = false;
                if probe.key == KEYS.len() {
                    finish(world, None);
                }
            }
        }
    }
}
fn require(ok: bool, message: &str) -> Result<(), String> {
    if ok { Ok(()) } else { Err(message.into()) }
}
fn id(entity: Entity) -> String {
    format!("{entity:?}")
}
fn sample(world: &mut World) -> Result<Value, String> {
    let probe = world.resource::<Probe>();
    let (key, frame, settled) = (probe.key, probe.frame, probe.settled + 1);
    let requested = key_time(key);
    let doc = world
        .resource::<EditorState>()
        .document()
        .ok_or("missing Work")?;
    require(
        matches!(
            doc.profile.id.as_str(),
            "nvwa-experiment48-genuine44-calibrated47" | "nvwa-experiment50-upper-arm-neutral-ab"
                | "nvwa-experiment88-chest-local"
        ),
        "wrong Work/profile",
    )?;
    let work = serde_json::to_value(doc).map_err(|e| e.to_string())?;
    let profile_clips = doc.profile.clips.clone();
    let playback = world.resource::<Playback>();
    require(playback.error.is_none(), "playback error")?;
    require(
        playback.clip_id == CLIP
            && playback.position_seconds.to_bits() == requested.to_bits()
            && !playback.playing
            && playback.seek_request.is_none(),
        "actual playback clip/time/pause mismatch",
    )?;
    let playback_json = json!({"clip_id":playback.clip_id,"position_seconds":playback.position_seconds,
        "position_bits":playback.position_seconds.to_bits(),"playing":playback.playing,
        "active_timeline_id":playback.active_timeline_id,"seek_pending":playback.seek_request.is_some(),"error":playback.error});
    // Resolve the actual loaded GLTF and its scene host, never infer from a graph index.
    let gltfs = world.resource::<Assets<Gltf>>();
    let loaded: Vec<_> = gltfs.iter().collect();
    require(loaded.len() == 1, "missing/ambiguous loaded Gltf")?;
    let gltf = loaded[0].1;
    let scenes: Vec<_> = gltf.scenes.iter().map(|h| h.id()).collect();
    let animation_ids: Vec<_> = gltf.animations.iter().map(|h| h.id()).collect();
    let node_handles = gltf.nodes.clone();
    let mesh_handles = gltf.meshes.clone();
    let skin_handles = gltf.skins.clone();
    let roots: Vec<_> = world
        .query::<(Entity, &WorldAssetRoot)>()
        .iter(world)
        .filter(|(_, r)| scenes.contains(&r.0.id()))
        .map(|(e, _)| e)
        .collect();
    require(
        roots.len() == 1,
        "missing/ambiguous CharacterRoot scene host",
    )?;
    let root = roots[0];
    let mut members = BTreeSet::new();
    let mut todo = vec![root];
    while let Some(entity) = todo.pop() {
        require(members.insert(entity), "cycle/duplicate entity hierarchy")?;
        if let Some(children) = world.get::<Children>(entity) {
            todo.extend(children.iter());
        }
    }
    let node_assets = world.resource::<Assets<GltfNode>>();
    let mut names = BTreeMap::new();
    for handle in &node_handles {
        let node = node_assets.get(handle).ok_or("missing GltfNode asset")?;
        require(
            names.insert(node.name.clone(), node.index).is_none(),
            "ambiguous GLTF node name",
        )?;
    }
    let mut seen = BTreeSet::new();
    let mut nodes = Vec::new();
    for entity in &members {
        let transform = world
            .get::<Transform>(*entity)
            .ok_or("missing local Transform")?;
        let global = world
            .get::<GlobalTransform>(*entity)
            .ok_or("missing GlobalTransform")?
            .to_matrix();
        require(
            transform.translation.is_finite()
                && transform.rotation.is_finite()
                && transform.scale.is_finite()
                && global.is_finite(),
            "nonfinite transform",
        )?;
        let name = world.get::<Name>(*entity).map(|n| n.as_str());
        let node_index = name.and_then(|n| names.get(n)).copied();
        if let Some(index) = node_index {
            require(seen.insert(index), "duplicate runtime GLTF node")?;
        }
        let parent = world.get::<ChildOf>(*entity).map(|p| p.parent());
        require(
            *entity == root || parent.is_some_and(|p| members.contains(&p)),
            "missing GLTF ancestor",
        )?;
        nodes.push(json!({"entity":id(*entity),"parent":parent.map(id),"name":name,"gltf_node_index":node_index,
            "translation":transform.translation.to_array(),"rotation":transform.rotation.to_array(),
            "scale":transform.scale.to_array(),"global":global.to_cols_array()}));
    }
    require(
        seen.len() == node_handles.len(),
        "missing runtime GLTF node",
    )?;
    let mut players = Vec::new();
    for entity in &members {
        let Some(player) = world.get::<AnimationPlayer>(*entity) else {
            continue;
        };
        let handle = world
            .get::<AnimationGraphHandle>(*entity)
            .ok_or("missing player graph handle")?;
        let graph = world
            .resource::<Assets<AnimationGraph>>()
            .get(&handle.0)
            .ok_or("missing graph asset")?;
        let mut animations = Vec::new();
        for (index, active) in player.playing_animations() {
            let node = graph.get(*index).ok_or("missing actual graph node")?;
            let AnimationNodeType::Clip(clip) = &node.node_type else {
                return Err("actual active node is not clip".into());
            };
            let gltf_index = animation_ids
                .iter()
                .position(|i| *i == clip.id())
                .ok_or("active clip outside current GLTF")?;
            let spec = profile_clips
                .iter()
                .find(|s| s.animation_index == gltf_index)
                .ok_or("active clip outside profile")?;
            require(
                spec.id == CLIP
                    && gltf_index == 3
                    && active.seek_time().to_bits() == requested.to_bits()
                    && active.is_paused()
                    && active.weight() == 1.0,
                "actual active clip/time/weight/pause mismatch",
            )?;
            animations.push(json!({"node_index":index.index(),"clip_asset":format!("{:?}",clip.id()),
                "gltf_animation_index":gltf_index,"clip_name":spec.id,"seek_time":active.seek_time(),
                "seek_time_bits":active.seek_time().to_bits(),"paused":active.is_paused(),"weight":active.weight()}));
        }
        require(
            animations.len() == 1,
            "expected exactly one actual animation per player",
        )?;
        players.push(json!({"entity":id(*entity),"graph_asset":format!("{:?}",handle.0.id()),"animations":animations}));
    }
    require(!players.is_empty(), "missing actual animation player")?;
    let mut skins = Vec::new();
    for entity in &members {
        let Some(skin) = world.get::<SkinnedMesh>(*entity) else {
            continue;
        };
        let mesh = world
            .get::<Mesh3d>(*entity)
            .ok_or("skinned entity missing mesh")?;
        let mesh_assets = world.resource::<Assets<GltfMesh>>();
        let mut mesh_matches = Vec::new();
        for handle in &mesh_handles {
            let source = mesh_assets.get(handle).ok_or("missing GltfMesh asset")?;
            for primitive in &source.primitives {
                if primitive.mesh.id() == mesh.0.id() {
                    mesh_matches.push((source.index, primitive.index));
                }
            }
        }
        require(
            mesh_matches.len() == 1,
            "missing/ambiguous primitive binding",
        )?;
        let skin_assets = world.resource::<Assets<GltfSkin>>();
        let mut skin_matches = Vec::new();
        for handle in &skin_handles {
            let source = skin_assets.get(handle).ok_or("missing GltfSkin asset")?;
            if source.inverse_bind_matrices.id() == skin.inverse_bindposes.id() {
                skin_matches.push(source.index);
            }
        }
        require(
            skin_matches.len() == 1,
            "missing/ambiguous actual skin binding",
        )?;
        let inverse = world
            .resource::<Assets<SkinnedMeshInverseBindposes>>()
            .get(&skin.inverse_bindposes)
            .ok_or("missing inverse bind asset")?;
        require(
            !skin.joints.is_empty()
                && skin.joints.len() == inverse.len()
                && skin.joints.iter().all(|j| members.contains(j))
                && inverse.iter().all(|m| m.is_finite()),
            "invalid actual skin joints/inverse binds",
        )?;
        skins.push(json!({"entity":id(*entity),"mesh_asset":format!("{:?}",mesh.0.id()),
            "gltf_mesh_index":mesh_matches[0].0,"gltf_primitive_index":mesh_matches[0].1,
            "gltf_skin_index":skin_matches[0],"inverse_bind_asset":format!("{:?}",skin.inverse_bindposes.id()),
            "inverse_bind_matrices":inverse.iter().map(|m|m.to_cols_array()).collect::<Vec<_>>(),
            "joints":skin.joints.iter().copied().map(id).collect::<Vec<_>>()}));
    }
    require(!skins.is_empty(), "missing actual skinned mesh")?;
    Ok(
        json!({"source_key_index":KEYS[key],"requested_clip":CLIP,"requested_time":requested,
        "requested_time_bits":requested.to_bits(),"frame":frame,"settled_frames":settled,
        "work":work,"playback":playback_json,"players":players,"character_root":id(root),"nodes":nodes,"skins":skins}),
    )
}
fn finish(world: &mut World, error: Option<String>) {
    let now = world.resource::<Time<Real>>().elapsed_secs_f64();
    let mut probe = world.resource_mut::<Probe>();
    probe.done = true;
    probe.failed = error.is_some();
    probe.exit_after = Some(now + 10.0);
    let result = json!({"schema_version":1,"platform":if cfg!(target_arch="wasm32"){"web"}else{"native"},
        "schedule":SCHEDULE,"status":if error.is_none(){"complete"}else{"failed"},"error":error,"samples":probe.samples});
    let count = probe.samples.len();
    let raw = serde_json::to_string_pretty(&result).expect("finite validated JSON");
    for mut window in world.query::<&mut Window>().iter_mut(world) {
        window.title = format!(
            "Nvwa · Frozen upper-arm A/B probe · {} · {count}/7 · last key {}",
            result["status"],
            result["samples"]
                .as_array()
                .and_then(|s| s.last())
                .map(|s| s["source_key_index"].to_string())
                .unwrap_or_else(|| "none".into())
        );
    }
    #[cfg(not(target_arch = "wasm32"))]
    {
        let output = std::env::var("NVWA_POSE_OUTPUT").unwrap_or_else(|_| "raw-native.json".into());
        std::fs::write(&output, raw).expect("write raw capture");
        println!(
            "NVWA_POSE_RESULT status={} samples={} output={output}",
            result["status"], count
        );
    }
    #[cfg(target_arch = "wasm32")]
    {
        let document = web_sys::window()
            .and_then(|w| w.document())
            .expect("browser document");
        let element = document.create_element("pre").expect("result element");
        element.set_id("nvwa-pose-result");
        element.set_text_content(Some(&raw));
        document
            .body()
            .expect("body")
            .append_child(&element)
            .expect("publish raw capture");
        web_sys::console::log_1(&wasm_bindgen::JsValue::from_str(
            "NVWA_POSE_RESULT ready in #nvwa-pose-result",
        ));
    }
}
