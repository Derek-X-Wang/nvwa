//! Actual Humentity loader/morph/mesh/rig adapter. No graphics/window plugin.
use b1_pose_adapter::{
    DiagnosticPose, apply_pose, apply_pose_canonical, skin_mesh_frame, skin_mesh_frame_canonical,
    skin_mesh_frame_full_weights,
};
use bevy::asset::{AssetMetaCheck, AssetPlugin};
use bevy::image::ImagePlugin;
use bevy::mesh::MeshPlugin;
use bevy::prelude::*;
use bevy::scene::ScenePlugin;
use bevy::transform::TransformPlugin;
use bevy::world_serialization::WorldSerializationPlugin;
use humentity::prelude::*;
use serde::Deserialize;
use serde_json::json;
use std::{
    collections::BTreeMap,
    fs,
    path::PathBuf,
    time::{Duration, Instant},
};

#[derive(Deserialize)]
struct Config {
    case_id: String,
    asset_root: String,
    base: String,
    vertex_groups: String,
    composite: String,
    macros: String,
    targets: String,
    rig: String,
    weights: String,
    body: String,
    garment: String,
    target_weights: BTreeMap<String, f32>,
    common_manifest_sha256: String,
    candidate_to_raw_scale: f32,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().collect();
    if args.len() != 4 {
        return Err("usage: b1-pose-adapter CONFIG_JSON POSES_JSON NEW_OUTPUT_DIR".into());
    }
    let config: Config = serde_json::from_slice(&fs::read(&args[1])?)?;
    let output = PathBuf::from(&args[3]);
    let pose_input: serde_json::Value = serde_json::from_slice(&fs::read(&args[2])?)?;
    let poses: Vec<DiagnosticPose> = serde_json::from_value(pose_input["poses"].clone())?;
    if output.exists() {
        return Err("output already exists".into());
    }
    if config.common_manifest_sha256.len() != 64
        || !config.candidate_to_raw_scale.is_finite()
        || config.candidate_to_raw_scale <= 0.0
        || config.target_weights.values().any(|v| !v.is_finite())
    {
        return Err("invalid identity, scale or recipe".into());
    }
    let started = Instant::now();
    let mut app = App::new();
    app.add_plugins(MinimalPlugins)
        .add_plugins(AssetPlugin {
            file_path: config.asset_root.clone(),
            meta_check: AssetMetaCheck::Never,
            ..default()
        })
        .add_plugins((
            TransformPlugin,
            WorldSerializationPlugin,
            ScenePlugin,
            MeshPlugin,
            ImagePlugin::default(),
            AnimationPlugin,
            HumentityPlugin,
        ))
        .insert_resource(SkeletonLodConfig::new(&[BoneMergeConfig::full()]));
    app.finish();
    app.cleanup();
    let server = app.world().resource::<AssetServer>().clone();
    let mut commands = app.world_mut().commands();
    humentity::load_and_insert_humentity_assets_explicit(
        &mut commands,
        &server,
        config.base.clone(),
        config.vertex_groups.clone(),
        config.composite.clone(),
        config.macros.clone(),
        config
            .target_weights
            .keys()
            .map(|name| format!("{}/{}.target", config.targets, name))
            .filter(|path| std::env::var("B1_OMIT_TARGET").ok().as_ref() != Some(path))
            .collect(),
        config.rig.clone(),
        config.weights.clone(),
    );
    app.world_mut().flush();
    while !app
        .world()
        .contains_resource::<humentity::HumentityAssetsReady>()
    {
        app.update();
        if started.elapsed() > Duration::from_secs(60) {
            return Err("core loader timeout; no result emitted".into());
        }
        std::thread::sleep(Duration::from_millis(2));
    }
    let mut requested = MorphTargets::default();
    for (name, value) in &config.target_weights {
        use bevy::ecs::intern::Internable;
        requested.insert(humentity::NAME_INTERNER.intern(name).leak(), *value);
    }
    let morphs = app.world().resource::<MakeHumanMorphs>();
    if morphs.targets.read().unwrap().is_empty() {
        return Err("no actual source targets loaded".into());
    }
    let resolved = morphs.compute_target_weights(&requested)?;
    if resolved
        .keys()
        .any(|key| !morphs.targets.read().unwrap().contains_key(key))
    {
        return Err("requested target absent".into());
    }
    let loaded_targets: BTreeMap<_, _> = morphs
        .targets
        .read()
        .unwrap()
        .iter()
        .map(|(k, v)| (k.to_string(), v.deltas.len()))
        .collect();
    let _helpers = adjust_helpers_to_morphs(
        &resolved,
        &morphs.targets,
        &app.world().resource::<BaseMesh>().vertices,
    )?;
    let template = app
        .world_mut()
        .resource_mut::<Assets<CharacterTemplate>>()
        .add(CharacterTemplate::new([CharacterMorphShape::new(
            "case",
            resolved.clone(),
        )]));
    let mut shape_weights = MorphTargets::default();
    shape_weights.insert("case", 1.0);
    let shape = app
        .world_mut()
        .resource_mut::<Assets<CharacterShapeAsset>>()
        .add(CharacterShapeAsset::new(template.clone(), shape_weights));
    let body: Handle<MhcloAsset> = server.load(config.body.clone());
    let garment: Handle<MhcloAsset> = server.load(config.garment.clone());
    while app
        .world()
        .resource::<Assets<MhcloAsset>>()
        .get(&body)
        .is_none()
        || app
            .world()
            .resource::<Assets<MhcloAsset>>()
            .get(&garment)
            .is_none()
    {
        app.update();
        if started.elapsed() > Duration::from_secs(60) {
            return Err("part loader timeout".into());
        }
        std::thread::sleep(Duration::from_millis(2));
    }
    // Retain original typed sources through readback. Candidate jobs otherwise
    // release their transient input handles once the final mesh is cached.
    let source_handles: Vec<(Handle<ObjVertsAsset>, Handle<Mesh>)> = [&body, &garment]
        .iter()
        .map(|part| {
            let path = app
                .world()
                .resource::<Assets<MhcloAsset>>()
                .get(*part)
                .unwrap()
                .obj_file
                .clone();
            (server.load(path.clone()), server.load(path))
        })
        .collect();
    for part in [&body, &garment] {
        app.world_mut()
            .resource_mut::<MhcloMeshBuilder>()
            .trigger(LoadAssetMeshJob::Single {
                part: part.clone(),
                template_handle: template.clone(),
                skeleton_lod: MeshBuildLod::Cpu(0),
            });
    }
    let character = app
        .world_mut()
        .spawn((
            CharacterShape(shape),
            BuildCpuSkeleton,
            Transform::default(),
            GlobalTransform::default(),
            SkeletonLodState {
                active: [true, false, false, false],
            },
        ))
        .id();
    for part in [&body, &garment] {
        let child = app
            .world_mut()
            .spawn((
                CharacterPart {
                    mesh: part.clone(),
                    skeleton_lod: 0,
                },
                Transform::default(),
                GlobalTransform::default(),
            ))
            .id();
        app.world_mut().entity_mut(character).add_child(child);
    }
    loop {
        app.update();
        let cache = app.world().resource::<CachedMhcloMeshHandles>();
        if app.world().get::<SkeletonReady>(character).is_some()
            && cache.contains_key(&(body.clone(), template.clone(), MeshBuildLod::Cpu(0)))
            && cache.contains_key(&(garment.clone(), template.clone(), MeshBuildLod::Cpu(0)))
        {
            break;
        }
        if started.elapsed() > Duration::from_secs(90) {
            return Err("mesh/rig timeout; no result emitted".into());
        }
        std::thread::sleep(Duration::from_millis(2));
    }
    let mut built_parts = Vec::new();
    for (index, (name, part)) in [("body", body), ("garment", garment)]
        .into_iter()
        .enumerate()
    {
        let meshes = app.world().resource::<Assets<Mesh>>();
        let cache = app.world().resource::<CachedMhcloMeshHandles>();
        let handle = cache
            .get(&(part.clone(), template.clone(), MeshBuildLod::Cpu(0)))
            .ok_or("built mesh missing")?;
        let mesh = meshes.get(handle).ok_or("mesh missing")?.clone();
        let (source_verts_handle, source_mesh_handle) = &source_handles[index];
        let source_verts = app
            .world()
            .resource::<Assets<ObjVertsAsset>>()
            .get(source_verts_handle)
            .ok_or("source verts missing")?;
        let source_mesh = meshes
            .get(source_mesh_handle)
            .ok_or("source mesh missing")?;
        let mapping =
            generate_vertex_map(&source_verts.vertices, &get_vertex_positions(source_mesh));
        let ids = generate_mhid_lookup(&mapping);
        let mhclo = app
            .world()
            .resource::<Assets<MhcloAsset>>()
            .get(&part)
            .ok_or("Mhclo absent")?
            .clone();
        built_parts.push((name, mesh, ids, mhclo));
    }
    fs::create_dir(&output)?;
    for pose in &poses {
        let full_weights = std::env::var("B1_FULL_WEIGHTS").as_deref() == Ok("1");
        let canonical = full_weights || std::env::var("B1_FRAME_GAUGE").as_deref() == Ok("1");
        if canonical {
            apply_pose_canonical(app.world_mut(), character, pose)?;
        } else {
            apply_pose(app.world_mut(), character, pose)?;
        }
        app.update(); // actual Bevy transform propagation, after diagnostic local edits.
        let mut parts = BTreeMap::new();
        for (name, mesh, ids, mhclo) in &built_parts {
            let frame = if full_weights {
                skin_mesh_frame_full_weights(app.world(), character, mesh, mhclo, ids)?
            } else if canonical {
                skin_mesh_frame_canonical(app.world(), character, mesh)?
            } else {
                skin_mesh_frame(app.world(), character, mesh)?
            };
            parts.insert(*name, json!({"source_vertex_ids":ids,"frame":frame}));
        }
        let result = json!({"schema_version":1,"case_id":config.case_id,"pose_id":pose.pose_id,
            "common_manifest_sha256":config.common_manifest_sha256,"space":"MakeHuman Y-up model metres; column-major matrices",
            "actual_candidate_code_executed":true,"actual_candidate_skeleton_propagated":true,
            "source_skinning_kernel":"WGSL; CPU adapter readback follows source formula, no GPU execution claimed",
            "target_weights":config.target_weights,"resolved_targets":resolved,"loaded_target_delta_counts":loaded_targets,
            "route_id":if full_weights {"b1-full-weight-cpu"} else {"b1-four-slot"},"frame_gauge_enabled":canonical,"parts":parts,"elapsed_seconds":started.elapsed().as_secs_f64()});
        let path = output.join(format!("{}.json", pose.pose_id));
        let mut stream = fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(path)?;
        use std::io::Write;
        stream.write_all(serde_json::to_string(&result)?.as_bytes())?;
        println!(
            "actual source ECS + adapter CPU skin readback: {} / {}",
            config.case_id, pose.pose_id
        );
    }
    Ok(())
}
