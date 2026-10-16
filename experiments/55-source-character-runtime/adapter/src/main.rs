//! Actual Humentity loader/morph/mesh/rig adapter. No graphics/window plugin.
use bevy::prelude::*;
use bevy::asset::{AssetMetaCheck, AssetPlugin};
use bevy::mesh::MeshPlugin;
use bevy::image::ImagePlugin;
use bevy::scene::ScenePlugin;
use bevy::world_serialization::WorldSerializationPlugin;
use bevy::transform::TransformPlugin;
use humentity::prelude::*;
use serde::Deserialize;
use serde_json::json;
use std::{collections::BTreeMap, fs, path::PathBuf, time::{Duration, Instant}};

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
    if args.len() != 3 { return Err("usage: humentity-probe CONFIG_JSON NEW_OUTPUT_JSON".into()); }
    let config: Config = serde_json::from_slice(&fs::read(&args[1])?)?;
    let output = PathBuf::from(&args[2]);
    if output.exists() { return Err("output already exists".into()); }
    if config.common_manifest_sha256.len() != 64 || !config.candidate_to_raw_scale.is_finite()
        || config.candidate_to_raw_scale <= 0.0 || config.target_weights.values().any(|v| !v.is_finite()) {
        return Err("invalid identity, scale or recipe".into());
    }
    let started = Instant::now();
    let mut app = App::new();
    app.add_plugins(MinimalPlugins)
        .add_plugins(AssetPlugin { file_path: config.asset_root.clone(), meta_check: AssetMetaCheck::Never, ..default() })
        .add_plugins((TransformPlugin, WorldSerializationPlugin, ScenePlugin, MeshPlugin, ImagePlugin::default(), AnimationPlugin, HumentityPlugin))
        .insert_resource(SkeletonLodConfig::new(&[BoneMergeConfig::full()]));
    app.finish(); app.cleanup();
    let server = app.world().resource::<AssetServer>().clone();
    let mut commands = app.world_mut().commands();
    humentity::load_and_insert_humentity_assets(&mut commands, &server,
        config.base.clone(), config.vertex_groups.clone(), config.composite.clone(),
        config.macros.clone(), config.targets.clone(), config.rig.clone(), config.weights.clone());
    app.world_mut().flush();
    while !app.world().contains_resource::<humentity::HumentityAssetsReady>() {
        app.update();
        if started.elapsed() > Duration::from_secs(60) { return Err("core loader timeout; no result emitted".into()); }
        std::thread::sleep(Duration::from_millis(2));
    }
    let mut requested = MorphTargets::default();
    for (name, value) in &config.target_weights {
        use bevy::ecs::intern::Internable;
        requested.insert(humentity::NAME_INTERNER.intern(name).leak(), *value);
    }
    let morphs = app.world().resource::<MakeHumanMorphs>();
    if morphs.targets.read().unwrap().is_empty() { return Err("no actual source targets loaded".into()); }
    let resolved = morphs.compute_target_weights(&requested)?;
    if resolved.keys().any(|key| !morphs.targets.read().unwrap().contains_key(key)) {
        return Err("requested target absent".into());
    }
    let loaded_targets: BTreeMap<_,_> = morphs.targets.read().unwrap().iter()
        .map(|(k,v)| (k.to_string(), v.deltas.len())).collect();
    let helpers = adjust_helpers_to_morphs(&resolved, &morphs.targets,
        &app.world().resource::<BaseMesh>().vertices)?;
    let template = app.world_mut().resource_mut::<Assets<CharacterTemplate>>()
        .add(CharacterTemplate::new([CharacterMorphShape::new("case", resolved.clone())]));
    let mut shape_weights = MorphTargets::default(); shape_weights.insert("case", 1.0);
    let shape = app.world_mut().resource_mut::<Assets<CharacterShapeAsset>>()
        .add(CharacterShapeAsset::new(template.clone(), shape_weights));
    let body: Handle<MhcloAsset> = server.load(config.body.clone());
    let garment: Handle<MhcloAsset> = server.load(config.garment.clone());
    while app.world().resource::<Assets<MhcloAsset>>().get(&body).is_none()
        || app.world().resource::<Assets<MhcloAsset>>().get(&garment).is_none() {
        app.update();
        if started.elapsed() > Duration::from_secs(60) { return Err("part loader timeout".into()); }
        std::thread::sleep(Duration::from_millis(2));
    }
    // Retain original typed sources through readback. Candidate jobs otherwise
    // release their transient input handles once the final mesh is cached.
    let source_handles: Vec<(Handle<ObjVertsAsset>, Handle<Mesh>)> = [&body, &garment].iter().map(|part| {
        let path = app.world().resource::<Assets<MhcloAsset>>().get(*part).unwrap().obj_file.clone();
        (server.load(path.clone()), server.load(path))
    }).collect();
    for part in [&body, &garment] {
        app.world_mut().resource_mut::<MhcloMeshBuilder>().trigger(LoadAssetMeshJob::Single {
            part: part.clone(), template_handle: template.clone(), skeleton_lod: MeshBuildLod::Cpu(0),
        });
    }
    let character = app.world_mut().spawn((CharacterShape(shape), BuildCpuSkeleton,
        Transform::default(), GlobalTransform::default(), SkeletonLodState { active: [true,false,false,false] })).id();
    for part in [&body, &garment] {
        let child = app.world_mut().spawn((CharacterPart { mesh: part.clone(), skeleton_lod: 0 },
            Transform::default(), GlobalTransform::default())).id();
        app.world_mut().entity_mut(character).add_child(child);
    }
    loop {
        app.update();
        let cache = app.world().resource::<CachedMhcloMeshHandles>();
        if app.world().get::<SkeletonReady>(character).is_some()
            && cache.contains_key(&(body.clone(), template.clone(), MeshBuildLod::Cpu(0)))
            && cache.contains_key(&(garment.clone(), template.clone(), MeshBuildLod::Cpu(0))) { break; }
        if started.elapsed() > Duration::from_secs(90) { return Err("mesh/rig timeout; no result emitted".into()); }
        std::thread::sleep(Duration::from_millis(2));
    }
    let scale = config.candidate_to_raw_scale;
    let meshes = app.world().resource::<Assets<Mesh>>();
    let cache = app.world().resource::<CachedMhcloMeshHandles>();
    let mut parts = BTreeMap::new();
    for (index, (name, part)) in [("body", body), ("garment", garment)].into_iter().enumerate() {
        let handle = cache.get(&(part.clone(), template.clone(), MeshBuildLod::Cpu(0))).ok_or("missing built mesh")?;
        let mesh = meshes.get(handle).ok_or("built mesh asset absent")?;
        let (source_verts_handle, source_mesh_handle) = &source_handles[index];
        let source_verts = app.world().resource::<Assets<ObjVertsAsset>>().get(source_verts_handle).ok_or("part vertex source absent")?;
        let source_mesh = meshes.get(source_mesh_handle).ok_or("part mesh source absent")?;
        let mapping = generate_vertex_map(&source_verts.vertices, &get_vertex_positions(source_mesh));
        let source_vertex_ids = generate_mhid_lookup(&mapping);
        let base = get_vertex_positions(mesh);
        if source_vertex_ids.len() != base.len() { return Err("part vertex map mismatch".into()); }
        let morph = mesh.morph_targets().ok_or("actual mesh has no case morph data")?;
        if morph.len() != base.len() { return Err("expected one actual morph per mesh vertex".into()); }
        let positions: Vec<_> = base.iter().zip(morph).map(|(p,m)| ((*p + m.position) * scale).to_array()).collect();
        let joint_indices = match mesh.attribute(Mesh::ATTRIBUTE_JOINT_INDEX) {
            Some(bevy::mesh::VertexAttributeValues::Uint16x4(values)) => Some(values.clone()), _ => None,
        };
        let joint_weights = match mesh.attribute(Mesh::ATTRIBUTE_JOINT_WEIGHT) {
            Some(bevy::mesh::VertexAttributeValues::Float32x4(values)) => Some(values.clone()), _ => None,
        };
        parts.insert(name, json!({"positions_raw_basis": positions, "source_vertex_ids": source_vertex_ids, "vertex_count": base.len(),
            "joint_indices": joint_indices, "joint_weights": joint_weights,
            "joint_indices_present": mesh.attribute(Mesh::ATTRIBUTE_JOINT_INDEX).is_some(),
            "joint_weights_present": mesh.attribute(Mesh::ATTRIBUTE_JOINT_WEIGHT).is_some()}));
    }
    let skeleton = app.world().get::<CharacterSkeleton>(character).ok_or("actual skeleton absent")?;
    let rig = app.world().resource::<RigData>().0.as_ref().ok_or("actual rig absent")?;
    let names = &rig.reference_rig().bone_names;
    if names.len() != skeleton.model_space_inv_bindposes.len() { return Err("inverse bind count mismatch".into()); }
    let bones: BTreeMap<_,_> = names.iter().zip(&skeleton.model_space_inv_bindposes).map(|(name, inv)| {
        let rest = inv.inverse();
        let (_, rotation, translation) = rest.to_scale_rotation_translation();
        (name.to_string(), json!({"head_raw_basis": (translation * scale).to_array(),
            "candidate_rest_matrix": rest.to_cols_array(), "candidate_inverse_bind_matrix": inv.to_cols_array(),
            "candidate_rotation": rotation.to_array()}))
    }).collect();
    let result = json!({"schema_version":1,"route_id":"source-runtime","case_id":config.case_id,
        "sample_class":"makehuman-approved-sample","common_manifest_sha256":config.common_manifest_sha256,
        "candidate_commit":"286d33124648501535655a0de811cef55152b9fd",
        "actual_candidate_code_executed":true,"candidate_loader_executed":true,"candidate_morph_executed":true,
        "candidate_mesh_executed":true,"candidate_rig_executed":true,"native_graphical_executed":false,
        "web_graphical_executed":false,"reference_pipeline_executed":false,"comparison_status":"not_compared",
        "target_weights":config.target_weights,"resolved_targets":resolved,"loaded_target_delta_counts":loaded_targets,
        "candidate_to_raw_scale":scale,"helper_positions_raw_basis":helpers.iter().map(|p|(*p*scale).to_array()).collect::<Vec<_>>(),
        "parts":parts,"bones":bones,"elapsed_seconds":started.elapsed().as_secs_f64()});
    let mut stream = fs::OpenOptions::new().write(true).create_new(true).open(output)?;
    use std::io::Write; stream.write_all(serde_json::to_string(&result)?.as_bytes())?;
    println!("Executed actual Humentity loader/morph/mesh/rig for {}; comparison not yet run", config.case_id);
    Ok(())
}
