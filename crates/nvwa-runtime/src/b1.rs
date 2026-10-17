//! Production bridge for the admitted, bounded B1 CPU character.
//! Raw bytes are authenticated once per explicit Open and typed loaders consume
//! an immutable in-memory copy, never a second read of the original source.
use super::{CharacterAsset, EditorState, Playback, RuntimeStatus};
use bevy::{
    asset::{
        RenderAssetUsages,
        io::{
            AssetReaderError, AssetSourceBuilder, AssetSourceId, Reader,
            memory::{Dir, MemoryAssetReader},
        },
    },
    ecs::intern::Internable,
    mesh::{Indices, skinning::SkinnedMesh},
    prelude::*,
    tasks::{
        IoTaskPool, Task,
        futures_lite::{AsyncReadExt, future},
    },
};
use humentity::prelude::*;
use nvwa_b1_adapter::{
    BoneFrame, DiagnosticPose, PreparedRig, PreparedSkin, apply_pose_canonical, motion,
    poses::diagnostic_pose, skin_mesh_frame_full_weights,
};
use nvwa_core::{
    B1_ASSET_PATH, B1_MAX_ASSET_BYTES, B1_MAX_MANIFEST_BYTES, B1AssetManifest, SceneDocument,
    TimelineClip,
};
use std::{
    collections::{BTreeMap, BTreeSet},
    path::Path,
};

const SOURCE: &str = "nvwa-b1-verified";
const TARGETS: [&str; 4] = [
    "torso-scale-vert-decr",
    "torso-scale-vert-incr",
    "chin-jaw-drop-decr",
    "chin-jaw-drop-incr",
];
type VerifiedBytes = BTreeMap<String, Vec<u8>>;

#[derive(Resource, Clone)]
struct VerifiedSource(Dir);

/// Install before AssetPlugin. The source contains only fully authenticated
/// immutable bytes; ordinary GLB assets keep using the existing default source.
pub fn register_b1_asset_source(app: &mut App) {
    let dir = Dir::default();
    let reader = MemoryAssetReader { root: dir.clone() };
    app.register_asset_source(
        SOURCE,
        AssetSourceBuilder::new(move || Box::new(reader.clone())),
    )
    .insert_resource(VerifiedSource(dir));
}

pub(super) fn install(app: &mut App) {
    app.add_plugins(HumentityPlugin)
        .insert_resource(SkeletonLodConfig::new(&[BoneMergeConfig::full()]))
        .init_resource::<B1Runtime>()
        .add_systems(
            PostUpdate,
            drive
                .in_set(super::RuntimeSystems::Mirror)
                .after(bevy::app::AnimationSystems)
                .before(bevy::transform::TransformSystems::Propagate),
        )
        .add_systems(
            PostUpdate,
            publish.after(bevy::transform::TransformSystems::Propagate),
        );
}

#[derive(Clone, PartialEq)]
struct Selection {
    parameters: BTreeMap<String, f32>,
    pose: String,
}
impl Selection {
    fn from_doc(doc: &SceneDocument) -> Self {
        Self {
            parameters: doc.character.parameters.clone(),
            pose: if doc.profile.backend.is_b1_motion() {
                String::new()
            } else {
                doc.character.diagnostic_pose.clone().unwrap_or_default()
            },
        }
    }
}
struct Part {
    name: &'static str,
    child: Entity,
    mapping: Handle<MhcloAsset>,
    mesh: Handle<Mesh>,
    source_vertices: Handle<ObjVertsAsset>,
    source_mesh: Handle<Mesh>,
}
struct Session {
    character: Entity,
    template: Handle<CharacterTemplate>,
    parts: Vec<Part>,
    displays: Vec<Entity>,
    display_meshes: Vec<Handle<Mesh>>,
    display_transforms: Vec<Transform>,
    materials: Vec<Handle<StandardMaterial>>,
    selection: Selection,
    generation: u64,
    // 0: fit, 1: pose ready for propagation, 2: uploaded.
    phase: u8,
    joint_count: usize,
    rig: Option<PreparedRig>,
    skins: Vec<PreparedSkin>,
    source_ids: Vec<Vec<u16>>,
    last_sample: Option<FrameSample>,
    pending_sample: Option<FrameSample>,
    last_bones: Vec<BoneFrame>,
    serial: u64,
    frame_error: Option<String>,
    published_binding: Option<PublishedBinding>,
    skeleton_binding: Option<Entity>,
    bone_bindings: Vec<(String, Entity)>,
    hierarchy_bindings: Vec<(Entity, Entity)>,
    display_indices: Vec<Vec<usize>>,
    display_vertex_counts: Vec<usize>,
}
struct Candidate {
    document: SceneDocument,
    request: u64,
    is_open: bool,
    task: Option<Task<Result<VerifiedBytes, String>>>,
    session: Option<Session>,
    elapsed: f32,
}
#[derive(Resource, Default)]
struct B1Runtime {
    candidate: Option<Candidate>,
    active: Option<Session>,
    initialized: bool,
    last_failed: Option<(u64, Selection)>,
    timeline: Vec<TimelineClip>,
    transport_generation: u64,
}

async fn bounded_read(reader: &mut dyn Reader, max: usize) -> Result<Vec<u8>, String> {
    let mut bytes = Vec::new();
    reader
        .take(max as u64 + 1)
        .read_to_end(&mut bytes)
        .await
        .map_err(|e| e.to_string())?;
    if bytes.len() > max {
        return Err("invalid_asset: B1 asset exceeds byte limit".into());
    }
    Ok(bytes)
}
fn read_failure(path: &str, error: AssetReaderError) -> String {
    let code = if matches!(error, AssetReaderError::NotFound(_)) {
        "asset_missing"
    } else {
        "invalid_asset"
    };
    format!("{code}: {path}: {error}")
}
#[cfg(target_arch = "wasm32")]
#[path = "b1_web.rs"]
mod web;

async fn read_raw(server: &AssetServer, path: &str, max: usize) -> Result<Vec<u8>, String> {
    #[cfg(target_arch = "wasm32")]
    {
        let _ = server;
        web::read(path, max).await
    }
    #[cfg(not(target_arch = "wasm32"))]
    {
        let source = server
            .get_source(AssetSourceId::Default)
            .map_err(|e| e.to_string())?;
        let mut reader = source
            .reader()
            .read(Path::new(path))
            .await
            .map_err(|e| read_failure(path, e))?;
        bounded_read(&mut *reader, max).await
    }
}
async fn verify_source(server: AssetServer) -> Result<VerifiedBytes, String> {
    let bytes = read_raw(&server, B1_ASSET_PATH, B1_MAX_MANIFEST_BYTES).await?;
    let manifest = B1AssetManifest::from_bytes(&bytes).map_err(|e| e.to_string())?;
    let mut result = BTreeMap::new();
    for file in &manifest.files {
        let path = format!("characters/mpfb-b1-v1/{}", file.path);
        let bytes = read_raw(&server, &path, file.bytes.min(B1_MAX_ASSET_BYTES)).await?;
        manifest
            .validate_file_bytes(&file.path, &bytes)
            .map_err(|e| e.to_string())?;
        result.insert(file.path.clone(), bytes);
    }
    Ok(result)
}
fn asset(path: &str) -> String {
    format!("{SOURCE}://{path}")
}

fn initialize(world: &mut World, bytes: VerifiedBytes) -> Result<(), String> {
    let source = world
        .get_resource::<VerifiedSource>()
        .ok_or("invalid_asset: B1 verified asset source was not installed before AssetPlugin")?
        .clone();
    for (path, bytes) in bytes {
        source.0.insert_asset(Path::new(&path), bytes);
    }
    let server = world.resource::<AssetServer>().clone();
    let mut commands = world.commands();
    humentity::load_and_insert_humentity_assets_explicit(
        &mut commands,
        &server,
        asset("base.obj"),
        asset("vertex_groups.json"),
        asset("composite.json"),
        asset("empty.macro"),
        TARGETS
            .iter()
            .map(|name| asset(&format!("targets/{name}.target")))
            .collect(),
        asset("rig.game_engine.json"),
        asset("weights.game_engine.json"),
    );
    world.flush();
    Ok(())
}
fn selection_current(world: &World, c: &Candidate) -> bool {
    let editor = world.resource::<EditorState>();
    if c.is_open {
        editor.open_request_sequence == c.request
            && editor.pending_open.as_ref() == Some(&c.document)
    } else {
        editor.pending_open.is_none()
            && editor.document_generation == c.request
            && editor.visible_document().is_some_and(|d| {
                d.profile.backend.is_b1()
                    && Selection::from_doc(d) == Selection::from_doc(&c.document)
            })
    }
}
fn cleanup(world: &mut World, session: Session) {
    for entity in session.displays {
        let _ = world.despawn(entity);
    }
    world.trigger(TeardownCharacter(session.character));
    world.flush();
    let _ = world.despawn(session.character);
    world
        .resource_mut::<CachedMhcloMeshHandles>()
        .retain(|(_, template, _), _| *template != session.template);
    for handle in session.display_meshes {
        world.resource_mut::<Assets<Mesh>>().remove(handle.id());
    }
    for handle in session.materials {
        world
            .resource_mut::<Assets<StandardMaterial>>()
            .remove(handle.id());
    }
}
fn discard(world: &mut World, candidate: Candidate) {
    // Dropping Task cancels it; verification has no shared writes.
    if let Some(session) = candidate.session {
        cleanup(world, session);
    }
}
fn fail(world: &mut World, runtime: &mut B1Runtime, error: String) {
    if let Some(candidate) = runtime.candidate.take() {
        runtime.last_failed = Some((candidate.request, Selection::from_doc(&candidate.document)));
        if candidate.is_open {
            let mut editor = world.resource_mut::<EditorState>();
            if editor.open_request_sequence == candidate.request {
                editor.pending_open = None;
                editor.open_error = Some(format!(
                    "B1 candidate rejected · current Work preserved: {error}"
                ));
                editor.message = "B1 candidate rejected · current Work preserved".into();
            }
        } else {
            let mut status = world.resource_mut::<RuntimeStatus>();
            status.error = Some(error);
            status.ready = false;
            status.phase = "B1 update failed · last frame preserved".into();
        }
        discard(world, candidate);
    }
}
fn drive(world: &mut World) {
    let mut runtime = world.remove_resource::<B1Runtime>().unwrap();
    if runtime
        .candidate
        .as_ref()
        .is_some_and(|c| !selection_current(world, c))
    {
        discard(world, runtime.candidate.take().unwrap());
    }
    let (doc, request, is_open) = {
        let editor = world.resource::<EditorState>();
        if let Some(doc) = editor.pending_open.as_ref() {
            (Some(doc.clone()), editor.open_request_sequence, true)
        } else {
            (
                editor.visible_document().cloned(),
                editor.document_generation,
                false,
            )
        }
    };
    let mut retained = BTreeSet::new();
    if let Some(active) = &runtime.active {
        retained.insert(active.template.id());
    }
    if let Some(session) = runtime.candidate.as_ref().and_then(|c| c.session.as_ref()) {
        retained.insert(session.template.id());
    }
    world
        .resource_mut::<CachedMhcloMeshHandles>()
        .retain(|(_, template, _), _| retained.contains(&template.id()));
    let Some(doc) = doc.filter(|d| d.profile.backend.is_b1()) else {
        if let Some(active) = runtime.active.take() {
            cleanup(world, active);
        }
        world.insert_resource(runtime);
        return;
    };
    let selected = Selection::from_doc(&doc);
    if runtime.candidate.is_none()
        && (is_open
            || runtime
                .active
                .as_ref()
                .is_none_or(|s| s.selection != selected || s.generation != request))
        && runtime.last_failed.as_ref() != Some(&(request, selected.clone()))
    {
        let task = (is_open || !runtime.initialized).then(|| {
            let server = world.resource::<AssetServer>().clone();
            IoTaskPool::get().spawn(verify_source(server))
        });
        if !is_open {
            world.resource_mut::<RuntimeStatus>().ready = false;
        }
        runtime.candidate = Some(Candidate {
            document: doc,
            request,
            is_open,
            task,
            session: None,
            elapsed: 0.0,
        });
    }
    if let Some(active) = runtime.active.as_mut() {
        if let Err(error) = validate_structure(world, active) {
            frame_failure(world, active, error);
        } else if active.rig.is_none() && active.frame_error.take().is_some() {
            world.resource_mut::<RuntimeStatus>().error = None;
            world.resource_mut::<Playback>().error = None;
        }
    }
    update_motion_transport(world, &mut runtime);
    if let Some(mut c) = runtime.candidate.take() {
        c.elapsed += world.resource::<Time<Real>>().delta_secs();
        let mut error = None;
        if c.elapsed > 30.0 {
            error = Some("invalid_asset: B1 verification/build exceeded 30 seconds".into());
        }
        if let Some(task) = c.task.as_mut() {
            if let Some(result) = future::block_on(future::poll_once(task)) {
                c.task = None;
                match result {
                    Ok(bytes) => {
                        if !runtime.initialized {
                            match initialize(world, bytes) {
                                Ok(()) => runtime.initialized = true,
                                Err(e) => error = Some(e),
                            }
                        }
                    }
                    Err(e) => error = Some(e),
                }
            }
        }
        if error.is_none()
            && c.task.is_none()
            && runtime.initialized
            && world.contains_resource::<humentity::HumentityAssetsReady>()
        {
            let result = advance(world, &mut c);
            if let Err(e) = result {
                error = Some(e);
            }
        }
        runtime.candidate = Some(c);
        if let Some(error) = error {
            fail(world, &mut runtime, error);
        }
    }
    // Scale and stage are presentation only; changing them never reruns fitting/LBS.
    if let Some(active) = &runtime.active {
        let scale = world
            .resource::<EditorState>()
            .visible_document()
            .map_or(1.0, |d| d.character.scale);
        for (entity, base) in active.displays.iter().zip(&active.display_transforms) {
            if let Some(mut transform) = world.get_mut::<Transform>(*entity) {
                *transform = *base;
                transform.translation *= scale;
                transform.scale *= scale;
            }
        }
    }
    animate_active(world, &mut runtime);
    refresh_active_status(world, &runtime);
    world.insert_resource(runtime);
}
fn refresh_active_status(world: &mut World, runtime: &B1Runtime) {
    let Some(active) = &runtime.active else {
        return;
    };
    let editor = world.resource::<EditorState>();
    let current = editor.visible_document().is_some_and(|doc| {
        doc.profile.backend.is_b1()
            && Selection::from_doc(doc) == active.selection
            && editor.document_generation == active.generation
    });
    if !current {
        return;
    }
    let meshes = active
        .displays
        .iter()
        .filter(|entity| {
            world
                .get::<Mesh3d>(**entity)
                .is_some_and(|handle| world.resource::<Assets<Mesh>>().get(&handle.0).is_some())
        })
        .count();
    let joints = world
        .get::<CharacterSkeleton>(active.character)
        .map_or(0, |s| s.bone_map.len());
    let ready = active.frame_error.is_none()
        && active.phase == 2
        && meshes == 2
        && joints == active.joint_count
        && joints == 53
        && validate_structure(world, active).is_ok();
    let mut status = world.resource_mut::<RuntimeStatus>();
    status.ready = ready;
    status.meshes = meshes;
    status.joints = joints;
    if ready {
        // Undo/Escape can return to the already uploaded selection while a newer
        // fit is still pending. That retained frame is current again immediately.
        status.error = None;
        status.phase = if active.rig.is_some() {
            "Ready · B1 authored rehearsal · full-positive CPU"
        } else {
            "Ready · B1 positive aggregate CPU · static diagnostic pose"
        }
        .into();
    }
}
fn advance(world: &mut World, c: &mut Candidate) -> Result<(), String> {
    if c.session.is_none() {
        // At most one source fit is outstanding. A superseded candidate may
        // already have submitted CPU work, which must settle before another
        // fit starts; the latest requested selection stays queued above.
        if !world.resource::<MhcloMeshBuilder>().is_empty() {
            return Ok(());
        }
        let morphs = world.resource::<MakeHumanMorphs>();
        for target in TARGETS {
            if !morphs
                .targets
                .read()
                .map_err(|_| "morph target lock poisoned")?
                .contains_key(target)
            {
                return Err(format!("invalid_asset: Explicit target missing: {target}"));
            }
        }
        let values = &c.document.character.parameters;
        let body = values["torso_length"];
        let jaw = values["jaw_drop"];
        let mut requested = MorphTargets::default();
        for (name, value) in TARGETS.into_iter().zip([
            (-body).max(0.0),
            body.max(0.0),
            (-jaw).max(0.0),
            jaw.max(0.0),
        ]) {
            requested.insert(humentity::NAME_INTERNER.intern(name).leak(), value);
        }
        let resolved = morphs
            .compute_target_weights(&requested)
            .map_err(|e| e.to_string())?;
        let template =
            world
                .resource_mut::<Assets<CharacterTemplate>>()
                .add(CharacterTemplate::new([CharacterMorphShape::new(
                    "selected", resolved,
                )]));
        let mut weights = MorphTargets::default();
        weights.insert("selected", 1.0);
        let shape = world
            .resource_mut::<Assets<CharacterShapeAsset>>()
            .add(CharacterShapeAsset::new(template.clone(), weights));
        let character = world
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
        let mut session = Session {
            character,
            template: template.clone(),
            parts: Vec::new(),
            displays: Vec::new(),
            display_meshes: Vec::new(),
            display_transforms: Vec::new(),
            materials: Vec::new(),
            selection: Selection::from_doc(&c.document),
            generation: c.request,
            phase: 0,
            joint_count: 0,
            rig: None,
            skins: Vec::new(),
            source_ids: Vec::new(),
            last_sample: None,
            pending_sample: None,
            last_bones: Vec::new(),
            serial: 0,
            frame_error: None,
            published_binding: None,
            skeleton_binding: None,
            bone_bindings: Vec::new(),
            hierarchy_bindings: Vec::new(),
            display_indices: Vec::new(),
            display_vertex_counts: Vec::new(),
        };
        for (name, path, obj) in [
            ("body", "body.mhclo", "base.obj"),
            (
                "garment",
                "garment/female_sportsuit01.mhclo",
                "garment/female_sportsuit01.obj",
            ),
        ] {
            let server = world.resource::<AssetServer>();
            let mapping = server.load::<MhcloAsset>(asset(path));
            let source_vertices = server.load::<ObjVertsAsset>(asset(obj));
            let source_mesh = server.load::<Mesh>(asset(obj));
            world
                .resource_mut::<MhcloMeshBuilder>()
                .trigger(LoadAssetMeshJob::Single {
                    part: mapping.clone(),
                    template_handle: template.clone(),
                    skeleton_lod: MeshBuildLod::Cpu(0),
                });
            let child = world
                .spawn((
                    humentity::prelude::CharacterPart {
                        mesh: mapping.clone(),
                        skeleton_lod: 0,
                    },
                    Transform::default(),
                    GlobalTransform::default(),
                ))
                .id();
            world.entity_mut(character).add_child(child);
            session.parts.push(Part {
                name,
                child,
                mapping,
                mesh: Handle::default(),
                source_vertices,
                source_mesh,
            });
        }
        c.session = Some(session);
    }
    let session = c.session.as_mut().unwrap();
    if session.phase == 0 {
        if world.get::<SkeletonReady>(session.character).is_none() {
            return Ok(());
        }
        for part in &mut session.parts {
            if world.get::<SkinnedMesh>(part.child).is_none() {
                return Ok(());
            }
            let key = (
                part.mapping.clone(),
                session.template.clone(),
                MeshBuildLod::Cpu(0),
            );
            let Some(mesh) = world
                .resource::<CachedMhcloMeshHandles>()
                .get(&key)
                .cloned()
            else {
                return Ok(());
            };
            part.mesh = mesh;
        }
        if c.document.profile.backend.is_b1_motion() {
            let doc = if !c.is_open {
                world
                    .resource::<EditorState>()
                    .visible_document()
                    .cloned()
                    .unwrap_or_else(|| c.document.clone())
            } else {
                c.document.clone()
            };
            let position = if c.is_open {
                0.0
            } else {
                requested_position(&doc, world.resource::<Playback>())
            };
            let sample = frame_sample(&doc, position);
            let rig = PreparedRig::new(world, session.character)?;
            rig.apply(world, &sample_pose(&sample)?)?;
            session.rig = Some(rig);
            session.pending_sample = Some(sample);
        } else {
            let pose = diagnostic_pose(&session.selection.pose)?;
            apply_pose_canonical(world, session.character, &pose)?;
        }
        session.phase = 1;
    }
    Ok(())
}
fn source_ids(world: &World, part: &Part) -> Result<Vec<u16>, String> {
    let vertices = world
        .resource::<Assets<ObjVertsAsset>>()
        .get(&part.source_vertices)
        .ok_or("source vertices absent")?;
    let mesh = world
        .resource::<Assets<Mesh>>()
        .get(&part.source_mesh)
        .ok_or("source mesh absent")?;
    Ok(generate_mhid_lookup(&generate_vertex_map(
        &vertices.vertices,
        &get_vertex_positions(mesh),
    )))
}
fn visible_body_indices(indices: &Indices, ids: &[u16], delete: &[u16]) -> Result<Indices, String> {
    let values: Vec<_> = indices.iter().collect();
    if values.len() % 6 != 0 {
        return Err("approved body quad fan missing".into());
    }
    let covered: BTreeSet<_> = delete.iter().copied().collect();
    let mut result = Vec::new();
    for quad in values.chunks_exact(6) {
        if quad[0] != quad[3] || quad[2] != quad[4] {
            return Err("approved body quad ordering changed".into());
        }
        let mut source = [0; 4];
        for (slot, index) in [quad[0], quad[1], quad[2], quad[5]].into_iter().enumerate() {
            source[slot] = *ids.get(index).ok_or("body source ID absent")?;
        }
        if source.iter().any(|id| *id >= 13380) || source.iter().all(|id| covered.contains(id)) {
            continue;
        }
        result.extend(quad.iter().map(|index| *index as u32));
    }
    Ok(Indices::U32(result))
}
fn upload(world: &mut World, c: &mut Candidate) -> Result<(), String> {
    let s = c.session.as_mut().ok_or("B1 fit absent")?;
    let garment = world
        .resource::<Assets<MhcloAsset>>()
        .get(&s.parts[1].mapping)
        .ok_or("garment mapping absent")?;
    let delete = garment.delete_verts.clone();
    // Evaluate and validate BOTH parts before publishing either display mesh.
    let mut frames = Vec::new();
    for part in &s.parts {
        let mesh = world
            .resource::<Assets<Mesh>>()
            .get(&part.mesh)
            .ok_or("built mesh absent")?;
        let mapping = world
            .resource::<Assets<MhcloAsset>>()
            .get(&part.mapping)
            .ok_or("proxy mapping absent")?;
        let ids = source_ids(world, part)?;
        let frame = if let Some(rig) = &s.rig {
            let skin = PreparedSkin::new(world, s.character, mesh, mapping, &ids)?;
            let frame = skin.evaluate(&rig.frames(world, s.character)?)?;
            s.skins.push(skin);
            s.source_ids.push(ids.clone());
            frame
        } else {
            skin_mesh_frame_full_weights(world, s.character, mesh, mapping, &ids)?
        };
        if frame.bones.len() != 53 {
            return Err("B1 full reference rig must have 53 bones".into());
        }
        let indices = mesh.indices().ok_or("built indices absent")?;
        let indices = if part.name == "body" {
            visible_body_indices(indices, &ids, &delete)?
        } else {
            indices.clone()
        };
        frames.push((frame, indices));
    }
    // Source display roots face -Z; the existing rehearsal stage views +Z.
    // This backend-only placement keeps source geometry and bone frames intact.
    let facing = Mat4::from_quat(Quat::from_xyzw(0.0, 1.0, 0.0, 0.0));
    let (body, body_indices) = frames.first().ok_or("B1 body frame absent")?;
    let body_to_stage = facing * Mat4::from_cols_array(&body.model_to_world);
    let mut rest_min_y = f32::INFINITY;
    for index in body_indices.iter() {
        let rest = body
            .rest_positions
            .get(index)
            .ok_or("B1 visible body rest vertex absent")?;
        let p = body_to_stage.transform_point3(Vec3::from_array(*rest));
        if !p.is_finite() {
            return Err("B1 visible body rest bounds are nonfinite".into());
        }
        rest_min_y = rest_min_y.min(p.y);
    }
    if !rest_min_y.is_finite() {
        return Err("B1 visible body rest bounds are empty".into());
    }
    // Ground the fitted rest shape, never the posed minimum: knee/combined
    // diagnostics must not move the stage anchor. Both parts share this offset.
    let placement = Mat4::from_translation(Vec3::Y * -rest_min_y) * facing;
    s.joint_count = frames.first().map_or(0, |(frame, _)| frame.bones.len());
    if let Some(rig) = &s.rig {
        s.last_bones = rig.frames(world, s.character)?;
    }
    s.last_sample = s.pending_sample.take();
    s.serial = 1;
    for (part, (frame, indices)) in s.parts.iter().zip(frames) {
        let mut mesh = Mesh::new(
            bevy::mesh::PrimitiveTopology::TriangleList,
            RenderAssetUsages::default(),
        );
        mesh.insert_attribute(Mesh::ATTRIBUTE_POSITION, frame.positions);
        mesh.insert_attribute(Mesh::ATTRIBUTE_NORMAL, frame.normals);
        mesh.insert_attribute(Mesh::ATTRIBUTE_TANGENT, frame.tangents);
        mesh.insert_indices(indices);
        s.display_vertex_counts
            .push(match mesh.attribute(Mesh::ATTRIBUTE_POSITION) {
                Some(bevy::mesh::VertexAttributeValues::Float32x3(v)) => v.len(),
                _ => return Err("display positions absent".into()),
            });
        let cached_indices: Vec<_> = mesh
            .indices()
            .ok_or("display indices absent")?
            .iter()
            .collect();
        if cached_indices
            .iter()
            .any(|i| *i >= s.display_vertex_counts[s.display_vertex_counts.len() - 1])
        {
            return Err("display index outside fitted vertex coverage".into());
        }
        s.display_indices.push(cached_indices);
        let handle = world.resource_mut::<Assets<Mesh>>().add(mesh);
        let material = world
            .resource_mut::<Assets<StandardMaterial>>()
            .add(StandardMaterial {
                base_color: if part.name == "body" {
                    Color::srgb(0.63, 0.39, 0.28)
                } else {
                    Color::srgb(0.12, 0.35, 0.61)
                },
                perceptual_roughness: 0.72,
                cull_mode: None,
                ..default()
            });
        let mut transform =
            Transform::from_matrix(placement * Mat4::from_cols_array(&frame.model_to_world));
        s.display_transforms.push(transform);
        transform.translation *= c.document.character.scale;
        transform.scale *= c.document.character.scale;
        let display = world
            .spawn((
                Mesh3d(handle.clone()),
                MeshMaterial3d(material.clone()),
                bevy::camera::visibility::NoFrustumCulling,
                transform,
                GlobalTransform::from(transform),
            ))
            .id();
        s.displays.push(display);
        s.display_meshes.push(handle);
        s.materials.push(material);
    }
    capture_structure(world, s)?;
    s.phase = 2;
    validate_structure(world, s)?;
    Ok(())
}
fn publish(world: &mut World) {
    let mut runtime = world.remove_resource::<B1Runtime>().unwrap();
    if runtime
        .candidate
        .as_ref()
        .is_some_and(|c| c.session.as_ref().is_some_and(|s| s.phase == 1))
    {
        let mut c = runtime.candidate.take().unwrap();
        if !selection_current(world, &c) {
            discard(world, c);
        } else {
            if !c.is_open {
                if let Some(doc) = world.resource::<EditorState>().visible_document() {
                    c.document = doc.clone();
                }
            }
            match upload(world, &mut c) {
                Err(error) => {
                    runtime.candidate = Some(c);
                    fail(world, &mut runtime, error);
                }
                Ok(()) => {
                    let mut session = c.session.take().unwrap();
                    if c.is_open {
                        // The committed editor and its history change only after both uploads.
                        let result = world.resource_mut::<EditorState>().replace(c.document);
                        if let Err(error) = result {
                            cleanup(world, session);
                            world.resource_mut::<EditorState>().open_error = Some(error);
                            world.insert_resource(runtime);
                            return;
                        }
                        session.generation = world.resource::<EditorState>().document_generation;
                    }
                    let uploaded_meshes = session.displays.len();
                    let joint_count = session.joint_count;
                    if let Some(old) = runtime.active.replace(session) {
                        cleanup(world, old);
                    }
                    let root = world.resource_mut::<CharacterAsset>().root.take();
                    if let Some(root) = root {
                        let _ = world.despawn(root);
                    }
                    if c.is_open || !session_is_motion(world, &runtime) {
                        *world.resource_mut::<Playback>() = Playback::default();
                        if session_is_motion(world, &runtime) {
                            if let (Some(doc), Some(sample)) = (
                                world.resource::<EditorState>().document().cloned(),
                                runtime.active.as_ref().and_then(|s| s.last_sample.as_ref()),
                            ) {
                                adopt_published_transport(
                                    &doc,
                                    &mut world.resource_mut::<Playback>(),
                                    sample,
                                );
                            }
                        }
                    }
                    if c.is_open {
                        runtime.transport_generation = 0;
                    } else if let Some(sample) =
                        runtime.active.as_ref().and_then(|s| s.last_sample.as_ref())
                    {
                        if let Some(doc) =
                            world.resource::<EditorState>().visible_document().cloned()
                        {
                            adopt_published_transport(
                                &doc,
                                &mut world.resource_mut::<Playback>(),
                                sample,
                            );
                        }
                    }
                    let now = world.resource::<Time<Real>>().elapsed_secs_f64();
                    let session_is_motion_label = session_is_motion(world, &runtime);
                    let mut status = world.resource_mut::<RuntimeStatus>();
                    status.ready = uploaded_meshes == 2 && joint_count == 53;
                    status.error = None;
                    status.meshes = uploaded_meshes;
                    status.skins = 0;
                    status.joints = joint_count;
                    status.morph_nodes = 0;
                    status.morph_weights = 0;
                    status.players = 0;
                    status.active_animations = 0;
                    status.paused_animations = 0;
                    status.phase = if session_is_motion_label {
                        "Ready · B1 authored rehearsal · full-positive CPU"
                    } else {
                        "Ready · B1 positive aggregate CPU · static diagnostic pose"
                    }
                    .into();
                    if c.is_open {
                        status.first_ready_seconds = Some(now);
                        status.ready_frames = 0;
                        status.warmed_frame_times_ms.clear();
                    }
                    runtime.last_failed = None;
                }
            }
        }
    }
    publish_active(world, &mut runtime);
    bind_published_frame(world, &mut runtime);
    if world
        .resource::<EditorState>()
        .document()
        .is_some_and(|d| d.profile.backend.is_b1())
    {
        let now = world.resource::<Time<Real>>().elapsed_secs_f64();
        let delta = world.resource::<Time<Real>>().delta_secs() * 1000.0;
        let mut status = world.resource_mut::<RuntimeStatus>();
        status.frames += 1;
        if status.frame_times_ms.len() >= 600 {
            status.frame_times_ms.remove(0);
        }
        status.frame_times_ms.push(delta);
        if status.ready {
            status.ready_frames += 1;
            if status
                .first_ready_seconds
                .is_some_and(|start| now - start >= 1.0)
            {
                if status.warmed_frame_times_ms.len() >= 600 {
                    status.warmed_frame_times_ms.remove(0);
                }
                status.warmed_frame_times_ms.push(delta);
            }
        }
    }
    world.insert_resource(runtime);
}

#[cfg(test)]
mod tests {
    use super::*;
    use bevy::asset::{
        AssetMetaCheck,
        io::{AssetReader, PathStream},
    };
    use std::sync::{
        Arc,
        atomic::{AtomicUsize, Ordering},
    };

    #[derive(Clone)]
    struct ChangingReader {
        inner: MemoryAssetReader,
        reads: Arc<AtomicUsize>,
        mutate: bool,
    }
    impl AssetReader for ChangingReader {
        async fn read<'a>(&'a self, path: &'a Path) -> Result<impl Reader + 'a, AssetReaderError> {
            self.reads.fetch_add(1, Ordering::SeqCst);
            let reader = self.inner.read(path).await?;
            // MemoryAssetReader returned a snapshot; overwrite its source before
            // the verifier reads. Any later typed reopen would now parse rubbish.
            if self.mutate {
                self.inner
                    .root
                    .insert_asset(path, b"mutated after read".to_vec());
            }
            Ok(reader)
        }
        async fn read_meta<'a>(
            &'a self,
            path: &'a Path,
        ) -> Result<impl Reader + 'a, AssetReaderError> {
            self.inner.read_meta(path).await
        }
        async fn read_directory<'a>(
            &'a self,
            path: &'a Path,
        ) -> Result<Box<PathStream>, AssetReaderError> {
            self.inner.read_directory(path).await
        }
        async fn is_directory<'a>(&'a self, path: &'a Path) -> Result<bool, AssetReaderError> {
            self.inner.is_directory(path).await
        }
    }
    fn original() -> SceneDocument {
        SceneDocument::from_profile(
            nvwa_core::CharacterProfile::from_json(include_str!(
                "../../../assets/character.profile.json"
            ))
            .unwrap(),
        )
        .unwrap()
    }
    fn b1() -> SceneDocument {
        SceneDocument::from_profile(nvwa_core::CharacterProfile::b1()).unwrap()
    }
    fn fill(dir: &Dir) {
        let root = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../assets");
        dir.insert_asset(
            Path::new(B1_ASSET_PATH),
            nvwa_core::B1_ASSET_MANIFEST_BYTES.to_vec(),
        );
        let manifest = B1AssetManifest::from_bytes(nvwa_core::B1_ASSET_MANIFEST_BYTES).unwrap();
        for file in manifest.files {
            let path = format!("characters/mpfb-b1-v1/{}", file.path);
            dir.insert_asset(Path::new(&path), std::fs::read(root.join(&path)).unwrap());
        }
    }
    fn harness(mutate: bool) -> (App, Dir, Arc<AtomicUsize>) {
        let dir = Dir::default();
        fill(&dir);
        let reads = Arc::new(AtomicUsize::new(0));
        let reader = ChangingReader {
            inner: MemoryAssetReader { root: dir.clone() },
            reads: reads.clone(),
            mutate,
        };
        let mut app = App::new();
        register_b1_asset_source(&mut app);
        app.register_asset_source(
            AssetSourceId::Default,
            AssetSourceBuilder::new(move || Box::new(reader.clone())),
        )
        .add_plugins((
            MinimalPlugins,
            AssetPlugin {
                meta_check: AssetMetaCheck::Never,
                ..default()
            },
            bevy::transform::TransformPlugin,
            bevy::world_serialization::WorldSerializationPlugin,
            bevy::scene::ScenePlugin,
            bevy::mesh::MeshPlugin,
            bevy::image::ImagePlugin::default(),
            AnimationPlugin,
        ))
        .init_asset::<StandardMaterial>()
        .init_resource::<EditorState>()
        .init_resource::<CharacterAsset>()
        .init_resource::<RuntimeStatus>()
        .init_resource::<Playback>();
        install(&mut app);
        app.finish();
        app.cleanup();
        app.world_mut()
            .resource_mut::<EditorState>()
            .replace(original())
            .unwrap();
        (app, dir, reads)
    }
    fn until(app: &mut App, predicate: impl Fn(&World) -> bool) {
        let deadline = std::time::Instant::now() + std::time::Duration::from_secs(20);
        while !predicate(app.world()) && std::time::Instant::now() < deadline {
            app.update();
            std::thread::sleep(std::time::Duration::from_millis(2));
        }
        assert!(
            predicate(app.world()),
            "B1 runtime did not reach requested state: {:?}; open error {:?}",
            app.world().resource::<RuntimeStatus>(),
            app.world().resource::<EditorState>().open_error
        );
    }
    fn uploaded_positions(app: &App) -> Vec<Vec<[f32; 3]>> {
        let active = app.world().resource::<B1Runtime>().active.as_ref().unwrap();
        active
            .displays
            .iter()
            .map(|entity| {
                let handle = &app.world().get::<Mesh3d>(*entity).unwrap().0;
                match app
                    .world()
                    .resource::<Assets<Mesh>>()
                    .get(handle)
                    .unwrap()
                    .attribute(Mesh::ATTRIBUTE_POSITION)
                    .unwrap()
                {
                    bevy::mesh::VertexAttributeValues::Float32x3(positions) => {
                        assert!(
                            positions
                                .iter()
                                .flatten()
                                .all(|coordinate| coordinate.is_finite()),
                            "every actual uploaded POSITION coordinate must be finite"
                        );
                        positions.clone()
                    }
                    _ => panic!("CPU display POSITION must be Float32x3"),
                }
            })
            .collect()
    }
    fn part_position_deltas(a: &[Vec<[f32; 3]>], b: &[Vec<[f32; 3]>]) -> Vec<f32> {
        assert_eq!(a.len(), b.len());
        a.iter()
            .zip(b)
            .map(|(part_a, part_b)| {
                assert_eq!(part_a.len(), part_b.len());
                assert!(
                    part_a
                        .iter()
                        .chain(part_b)
                        .flatten()
                        .all(|coordinate| coordinate.is_finite()),
                    "position comparisons reject nonfinite coordinates before reduction"
                );
                let delta = part_a
                    .iter()
                    .zip(part_b)
                    .flat_map(|(p, q)| (0..3).map(move |axis| (p[axis] - q[axis]).abs()))
                    .fold(0.0_f32, f32::max);
                assert!(delta.is_finite(), "POSITION differences must be finite");
                delta
            })
            .collect()
    }
    fn position_delta(a: &[Vec<[f32; 3]>], b: &[Vec<[f32; 3]>]) -> f32 {
        part_position_deltas(a, b)
            .into_iter()
            .fold(0.0_f32, f32::max)
    }
    fn uploaded_visible_world_bounds(app: &App) -> Vec<(Vec3, Vec3)> {
        let active = app.world().resource::<B1Runtime>().active.as_ref().unwrap();
        active
            .displays
            .iter()
            .map(|entity| {
                let transform = app.world().get::<GlobalTransform>(*entity).unwrap();
                let handle = &app.world().get::<Mesh3d>(*entity).unwrap().0;
                let mesh = app.world().resource::<Assets<Mesh>>().get(handle).unwrap();
                let positions = get_vertex_positions(mesh);
                // Only uploaded triangles render: helper vertices and body faces
                // deleted beneath the garment must not define the stage bounds.
                let mut min = Vec3::splat(f32::INFINITY);
                let mut max = Vec3::splat(f32::NEG_INFINITY);
                let mut count = 0;
                for index in mesh.indices().unwrap().iter() {
                    let p = transform.transform_point(positions[index]);
                    assert!(
                        p.is_finite(),
                        "actual indexed world positions must be finite"
                    );
                    min = min.min(p);
                    max = max.max(p);
                    count += 1;
                }
                assert!(count > 0);
                (min, max)
            })
            .collect()
    }
    #[test]
    fn production_b1_neutral_visible_body_stands_on_stage_floor() {
        let (mut app, _, _) = harness(false);
        app.world_mut()
            .resource_mut::<EditorState>()
            .request_open(b1())
            .unwrap();
        until(&mut app, |w| {
            w.resource::<EditorState>()
                .document()
                .is_some_and(|d| d.profile.backend.is_b1())
                && w.resource::<RuntimeStatus>().ready
        });
        let bounds = uploaded_visible_world_bounds(&app);
        assert_eq!(bounds.len(), 2);
        let (body_min, body_max) = bounds[0];
        let body_height = body_max.y - body_min.y;
        assert!(
            (1.3..2.2).contains(&body_height),
            "default visible body must have a plausible full height in metres: {bounds:?}"
        );
        assert!(
            body_min.y.abs() < 1e-4,
            "neutral body feet must meet the persisted stage floor at y=0; bounds={bounds:?}"
        );
        assert!(
            bounds[1].0.y >= -1e-4 && bounds[1].1.y <= body_max.y + 1e-4,
            "actual indexed garment must remain above the floor and within body height: {bounds:?}"
        );
        let active = app.world().resource::<B1Runtime>().active.as_ref().unwrap();
        let placement = active.display_transforms.clone();
        assert_eq!(active.joint_count, 53);
        for transform in &placement {
            assert!(
                (transform.rotation * Vec3::Z).abs_diff_eq(Vec3::Z, 1e-6),
                "admitted model front +Z must face the existing stage camera's +Z side"
            );
        }
        let document = app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .clone();
        let character_id = document.character.id.clone();
        for pose in ["shoulder", "elbow", "knee", "combined", "neutral"] {
            app.world_mut()
                .resource_mut::<EditorState>()
                .apply(nvwa_core::Command::SetDiagnosticPose {
                    character_id: character_id.clone(),
                    pose_id: pose.into(),
                })
                .unwrap();
            until(&mut app, |w| {
                w.resource::<B1Runtime>()
                    .active
                    .as_ref()
                    .is_some_and(|s| s.selection.pose == pose)
                    && w.resource::<RuntimeStatus>().ready
            });
            let active = app.world().resource::<B1Runtime>().active.as_ref().unwrap();
            for (actual, expected) in active.display_transforms.iter().zip(&placement) {
                assert!(
                    actual.translation.abs_diff_eq(expected.translation, 1e-6),
                    "{pose} must retain the fitted rest anchor, not ground its posed minimum"
                );
                assert!(actual.scale.abs_diff_eq(expected.scale, 1e-6));
                assert!(actual.rotation.abs_diff_eq(expected.rotation, 1e-6));
            }
            // Every diagnostic still uploads finite indexed geometry for both parts.
            assert_eq!(uploaded_visible_world_bounds(&app).len(), 2);
        }
        for torso in [-1.0, 1.0] {
            let mut parameters = document.character.parameters.clone();
            parameters.insert("torso_length".into(), torso);
            app.world_mut()
                .resource_mut::<EditorState>()
                .apply(nvwa_core::Command::SetParameters {
                    character_id: character_id.clone(),
                    values: parameters.clone(),
                })
                .unwrap();
            until(&mut app, |w| {
                w.resource::<B1Runtime>()
                    .active
                    .as_ref()
                    .is_some_and(|s| s.selection.parameters == parameters)
                    && w.resource::<RuntimeStatus>().ready
            });
            let bounds = uploaded_visible_world_bounds(&app);
            assert!(
                bounds[0].0.y.abs() < 1e-4,
                "signed torso={torso} neutral rest feet must meet floor: {bounds:?}"
            );
            assert!(bounds[1].0.y >= -1e-4);
        }
        let before_scale = uploaded_visible_world_bounds(&app);
        let local_positions = uploaded_positions(&app);
        let mesh_handles = app
            .world()
            .resource::<B1Runtime>()
            .active
            .as_ref()
            .unwrap()
            .display_meshes
            .clone();
        app.world_mut()
            .resource_mut::<EditorState>()
            .apply(nvwa_core::Command::SetScale {
                character_id,
                scale: 1.2,
            })
            .unwrap();
        app.update();
        for ((before_min, before_max), (after_min, after_max)) in
            before_scale.iter().zip(uploaded_visible_world_bounds(&app))
        {
            assert!(after_min.abs_diff_eq(*before_min * 1.2, 1e-5));
            assert!(after_max.abs_diff_eq(*before_max * 1.2, 1e-5));
        }
        assert_eq!(
            position_delta(&local_positions, &uploaded_positions(&app)),
            0.0
        );
        assert_eq!(
            app.world()
                .resource::<B1Runtime>()
                .active
                .as_ref()
                .unwrap()
                .display_meshes,
            mesh_handles,
            "scaling presentation must reuse uploaded CPU meshes"
        );
        assert_eq!(
            app.world()
                .resource::<EditorState>()
                .document()
                .unwrap()
                .stage,
            document.stage,
            "backend placement must preserve the Work's floor and camera settings"
        );
    }
    #[test]
    fn production_plugin_keeps_original_glb_ready_without_fetching_b1_assets() {
        let dir = Dir::default();
        let profile = original().profile;
        dir.insert_asset(
            Path::new(&profile.asset_path),
            include_bytes!("../../../assets/fixtures/nvwa-humanoid.glb").to_vec(),
        );
        let reads = Arc::new(AtomicUsize::new(0));
        let reader = ChangingReader {
            inner: MemoryAssetReader { root: dir.clone() },
            reads: reads.clone(),
            mutate: false,
        };
        let mut app = App::new();
        register_b1_asset_source(&mut app);
        app.register_asset_source(
            AssetSourceId::Default,
            AssetSourceBuilder::new(move || Box::new(reader.clone())),
        )
        .add_plugins((
            MinimalPlugins,
            AssetPlugin {
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
        .add_plugins(super::super::NvwaRuntimePlugin);
        app.finish();
        app.cleanup();
        until(&mut app, |world| world.resource::<RuntimeStatus>().ready);
        assert!(
            app.world()
                .resource::<EditorState>()
                .document()
                .unwrap()
                .profile
                .backend
                .is_glb()
        );
        assert_eq!(
            reads.load(Ordering::SeqCst),
            1,
            "default GLB must not request any B1 input"
        );
        assert!(!app.world().contains_resource::<MakeHumanMorphs>());
        assert!(app.world().resource::<B1Runtime>().candidate.is_none());
        assert!(app.world().resource::<B1Runtime>().active.is_none());
        fill(&dir);
        app.world_mut().resource_mut::<Playback>().playing = true;
        motion_tick(&mut app, 0.25);
        assert!(
            app.world().resource::<RuntimeStatus>().players > 0,
            "transition starts from the actual GLB player"
        );
        assert!(!app.world().resource::<Playback>().clip_id.is_empty());
        // Only the playback observation above advances simulated time. Async
        // I/O/fitting waits retain the real 20s harness deadline, but must not
        // spend another 250ms of the production 30s budget on every poll.
        app.insert_resource(bevy::time::TimeUpdateStrategy::ManualDuration(
            std::time::Duration::ZERO,
        ));
        app.world_mut()
            .resource_mut::<EditorState>()
            .request_open(b1())
            .unwrap();
        until(&mut app, |w| {
            w.resource::<EditorState>().pending_open.is_none()
                && w.resource::<B1Runtime>().active.is_some()
                && w.resource::<RuntimeStatus>().ready
        });
        assert_static_transport(&app);
        assert_eq!(app.world().resource::<Time<Real>>().delta_secs(), 0.0);
    }
    #[test]
    fn production_candidate_timeout_still_rejects_elapsed_clock_over_30_seconds() {
        let (mut app, _, _) = harness(false);
        motion_tick(&mut app, 0.0);
        let committed = app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .clone();
        app.world_mut()
            .resource_mut::<EditorState>()
            .request_open(b1())
            .unwrap();
        motion_tick(&mut app, 31.0);
        assert_eq!(app.world().resource::<Time<Real>>().delta_secs(), 31.0);
        assert!(
            app.world()
                .resource::<EditorState>()
                .open_error
                .as_deref()
                .unwrap()
                .contains("exceeded 30 seconds")
        );
        assert_eq!(
            app.world().resource::<EditorState>().document(),
            Some(&committed)
        );
        assert!(app.world().resource::<B1Runtime>().candidate.is_none());
        assert!(app.world().resource::<B1Runtime>().active.is_none());
    }
    #[test]
    fn pending_open_keeps_committed_history_and_edit_cancels_it() {
        let mut editor = EditorState::default();
        editor.replace(original()).unwrap();
        let id = editor.document().unwrap().character.id.clone();
        editor
            .apply(nvwa_core::Command::SetScale {
                character_id: id,
                scale: 1.4,
            })
            .unwrap();
        let before = editor.document().unwrap().clone();
        let history = editor.editor.as_ref().unwrap().retention_stats();
        editor.request_open(b1()).unwrap();
        assert_eq!(editor.document(), Some(&before));
        assert_eq!(editor.editor.as_ref().unwrap().retention_stats(), history);
        assert!(editor.pending_open.is_some());
        editor.apply(nvwa_core::Command::Undo).unwrap();
        assert!(editor.pending_open.is_none());
        assert_eq!(editor.document().unwrap().character.scale, 1.0);
    }
    #[test]
    fn missing_asset_rejects_candidate_and_preserves_document_history_and_render() {
        let (mut app, dir, _) = harness(false);
        dir.remove_asset(Path::new("characters/mpfb-b1-v1/weights.game_engine.json"));
        let sentinel = app.world_mut().spawn_empty().id();
        app.world_mut().resource_mut::<CharacterAsset>().root = Some(sentinel);
        app.world_mut().resource_mut::<RuntimeStatus>().ready = true;
        let before = app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .clone();
        let history = app
            .world()
            .resource::<EditorState>()
            .editor
            .as_ref()
            .unwrap()
            .retention_stats();
        app.world_mut()
            .resource_mut::<EditorState>()
            .request_open(b1())
            .unwrap();
        until(&mut app, |w| {
            w.resource::<EditorState>().open_error.is_some()
        });
        let editor = app.world().resource::<EditorState>();
        assert_eq!(editor.document(), Some(&before));
        assert_eq!(editor.editor.as_ref().unwrap().retention_stats(), history);
        assert!(
            editor
                .open_error
                .as_ref()
                .unwrap()
                .contains("asset_missing")
        );
        assert!(app.world().get_entity(sentinel).is_ok());
        assert!(app.world().resource::<RuntimeStatus>().ready);
        assert!(app.world().resource::<B1Runtime>().candidate.is_none());
    }
    #[test]
    fn exact_snapshot_builds_both_cpu_parts_then_commits_and_reopen_failure_preserves_them() {
        let (mut app, dir, reads) = harness(true);
        let sentinel = app.world_mut().spawn_empty().id();
        app.world_mut().resource_mut::<CharacterAsset>().root = Some(sentinel);
        let before = app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .clone();
        app.world_mut()
            .resource_mut::<EditorState>()
            .request_open(b1())
            .unwrap();
        app.update();
        assert_eq!(
            app.world().resource::<EditorState>().document(),
            Some(&before)
        );
        assert!(app.world().get_entity(sentinel).is_ok());
        until(&mut app, |w| {
            w.resource::<EditorState>()
                .document()
                .is_some_and(|d| d.profile.backend.is_b1())
        });
        assert!(app.world().get_entity(sentinel).is_err());
        assert_eq!(
            reads.load(Ordering::SeqCst),
            14,
            "typed loaders must never reopen original input"
        );
        let status = app.world().resource::<RuntimeStatus>();
        assert!(status.ready);
        assert_eq!(
            (status.meshes, status.joints, status.skins, status.players),
            (2, 53, 0, 0)
        );
        let active = app.world().resource::<B1Runtime>().active.as_ref().unwrap();
        let displays = active.displays.clone();
        assert_eq!(displays.len(), 2);
        for display in &displays {
            assert!(app.world().get::<SkinnedMesh>(*display).is_none());
            assert!(
                app.world()
                    .get::<bevy::mesh::morph::MorphWeights>(*display)
                    .is_none()
            );
            let handle = &app.world().get::<Mesh3d>(*display).unwrap().0;
            let mesh = app.world().resource::<Assets<Mesh>>().get(handle).unwrap();
            assert!(mesh.attribute(Mesh::ATTRIBUTE_JOINT_WEIGHT).is_none());
            assert!(mesh.morph_targets().is_none());
            assert!(mesh.count_vertices() > 1000);
        }
        let character_id = app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .character
            .id
            .clone();
        // A changed selection invalidates readiness before the replacement fit
        // publishes. Undo must make the retained uploaded selection ready again.
        app.world_mut()
            .resource_mut::<EditorState>()
            .apply(nvwa_core::Command::SetDiagnosticPose {
                character_id: character_id.clone(),
                pose_id: "shoulder".into(),
            })
            .unwrap();
        app.update();
        assert!(!app.world().resource::<RuntimeStatus>().ready);
        app.world_mut()
            .resource_mut::<EditorState>()
            .apply(nvwa_core::Command::Undo)
            .unwrap();
        app.update();
        assert!(app.world().resource::<RuntimeStatus>().ready);
        assert_eq!(
            app.world()
                .resource::<B1Runtime>()
                .active
                .as_ref()
                .unwrap()
                .displays,
            displays
        );
        assert_eq!(
            app.world()
                .resource::<B1Runtime>()
                .active
                .as_ref()
                .unwrap()
                .selection
                .pose,
            "neutral"
        );
        let mut preview = app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .character
            .parameters
            .clone();
        preview.insert("torso_length".into(), 0.5);
        app.world_mut()
            .resource_mut::<EditorState>()
            .preview_parameters(preview)
            .unwrap();
        app.update();
        assert!(!app.world().resource::<RuntimeStatus>().ready);
        app.world_mut()
            .resource_mut::<EditorState>()
            .cancel_preview();
        app.update();
        assert!(app.world().resource::<RuntimeStatus>().ready);
        assert_eq!(
            app.world()
                .resource::<B1Runtime>()
                .active
                .as_ref()
                .unwrap()
                .displays,
            displays
        );
        let neutral_positions = uploaded_positions(&app);
        // Now let a shared pose command finish, then undo it through the same
        // production fitter and CPU upload path.
        app.world_mut()
            .resource_mut::<EditorState>()
            .apply(nvwa_core::Command::SetDiagnosticPose {
                character_id,
                pose_id: "elbow".into(),
            })
            .unwrap();
        until(&mut app, |w| {
            w.resource::<B1Runtime>()
                .active
                .as_ref()
                .is_some_and(|s| s.selection.pose == "elbow")
                && w.resource::<RuntimeStatus>().ready
        });
        let pose_deltas = part_position_deltas(&neutral_positions, &uploaded_positions(&app));
        assert_eq!(pose_deltas.len(), 2);
        for (part, delta) in ["body", "garment"].into_iter().zip(pose_deltas) {
            assert!(
                delta > 1e-4,
                "the actual uploaded {part} POSITION arrays must change for canonical elbow pose; delta={delta}"
            );
        }
        app.world_mut()
            .resource_mut::<EditorState>()
            .apply(nvwa_core::Command::Undo)
            .unwrap();
        until(&mut app, |w| {
            w.resource::<B1Runtime>()
                .active
                .as_ref()
                .is_some_and(|s| s.selection.pose == "neutral")
                && w.resource::<RuntimeStatus>().ready
        });
        for (part, delta) in ["body", "garment"].into_iter().zip(part_position_deltas(
            &neutral_positions,
            &uploaded_positions(&app),
        )) {
            assert!(
                delta < 1e-5,
                "pose Undo must restore uploaded {part} within 10 micrometres; delta={delta}"
            );
        }
        let prior_parameters = app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .character
            .parameters
            .clone();
        // Exercise the bindings independently: a working jaw must not hide a
        // missing torso binding, or vice versa. Chin edits need not move clothes.
        for (parameter, value, changed_parts) in [("torso_length", 0.5, 2), ("jaw_drop", -0.5, 1)] {
            let prior_positions = uploaded_positions(&app);
            let mut changed_parameters = prior_parameters.clone();
            changed_parameters.insert(parameter.into(), value);
            let id = app
                .world()
                .resource::<EditorState>()
                .document()
                .unwrap()
                .character
                .id
                .clone();
            app.world_mut()
                .resource_mut::<EditorState>()
                .apply(nvwa_core::Command::SetParameters {
                    character_id: id,
                    values: changed_parameters.clone(),
                })
                .unwrap();
            until(&mut app, |w| {
                w.resource::<B1Runtime>()
                    .active
                    .as_ref()
                    .is_some_and(|session| session.selection.parameters == changed_parameters)
                    && w.resource::<RuntimeStatus>().ready
            });
            let deltas = part_position_deltas(&prior_positions, &uploaded_positions(&app));
            assert_eq!(deltas.len(), 2);
            for (part, delta) in ["body", "garment"]
                .into_iter()
                .zip(deltas)
                .take(changed_parts)
            {
                assert!(
                    delta > 1e-4,
                    "independent {parameter}={value} must change uploaded {part}; delta={delta}"
                );
            }
            app.world_mut()
                .resource_mut::<EditorState>()
                .apply(nvwa_core::Command::Undo)
                .unwrap();
            until(&mut app, |w| {
                w.resource::<B1Runtime>()
                    .active
                    .as_ref()
                    .is_some_and(|session| session.selection.parameters == prior_parameters)
                    && w.resource::<RuntimeStatus>().ready
            });
            for (part, delta) in ["body", "garment"].into_iter().zip(part_position_deltas(
                &prior_positions,
                &uploaded_positions(&app),
            )) {
                assert!(
                    delta < 1e-5,
                    "{parameter} Undo must restore uploaded {part} within 10 micrometres; delta={delta}"
                );
            }
        }
        let prior_mesh_handles = app
            .world()
            .resource::<B1Runtime>()
            .active
            .as_ref()
            .unwrap()
            .display_meshes
            .clone();
        let active_character = app
            .world()
            .resource::<B1Runtime>()
            .active
            .as_ref()
            .unwrap()
            .character;
        let mut stage = app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .stage
            .clone();
        stage.camera.azimuth_degrees += 15.0;
        app.world_mut()
            .resource_mut::<EditorState>()
            .apply(nvwa_core::Command::SetStage { stage })
            .unwrap();
        app.update();
        assert_eq!(
            app.world()
                .resource::<B1Runtime>()
                .active
                .as_ref()
                .unwrap()
                .character,
            active_character,
            "camera-only Work edit must not refit or skin"
        );
        assert_eq!(
            app.world()
                .resource::<B1Runtime>()
                .active
                .as_ref()
                .unwrap()
                .display_meshes,
            prior_mesh_handles
        );
        let id = app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .character
            .id
            .clone();
        app.world_mut()
            .resource_mut::<EditorState>()
            .apply(nvwa_core::Command::SetScale {
                character_id: id,
                scale: 1.2,
            })
            .unwrap();
        app.update();
        let active = app.world().resource::<B1Runtime>().active.as_ref().unwrap();
        assert_eq!(
            active.display_meshes, prior_mesh_handles,
            "scale must keep the same CPU meshes"
        );
        assert_eq!(active.character, active_character);
        for (entity, base) in active.displays.iter().zip(&active.display_transforms) {
            let actual = app.world().get::<Transform>(*entity).unwrap();
            assert!(actual.translation.abs_diff_eq(base.translation * 1.2, 1e-6));
            assert!(actual.scale.abs_diff_eq(base.scale * 1.2, 1e-6));
            assert_eq!(actual.rotation, base.rotation);
        }
        assert_eq!(
            position_delta(&neutral_positions, &uploaded_positions(&app)),
            0.0,
            "stage and scale are presentation transforms; local POSITION arrays stay unchanged"
        );
        assert_eq!(reads.load(Ordering::SeqCst), 14);
        let displays = app
            .world()
            .resource::<B1Runtime>()
            .active
            .as_ref()
            .unwrap()
            .displays
            .clone();
        let committed = app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .clone();
        // Original source is now corrupt. Explicit reopening must verify it again,
        // reject it, and retain the successfully committed Work and display pair.
        app.world_mut()
            .resource_mut::<EditorState>()
            .request_open(b1())
            .unwrap();
        until(&mut app, |w| {
            w.resource::<EditorState>().open_error.is_some()
        });
        assert_eq!(
            app.world().resource::<EditorState>().document(),
            Some(&committed)
        );
        for display in displays {
            assert!(app.world().get_entity(display).is_ok());
        }
        assert!(app.world().resource::<RuntimeStatus>().ready);
        // A fresh explicit request can recover; no fatal application latch.
        fill(&dir);
        app.world_mut()
            .resource_mut::<EditorState>()
            .request_open(b1())
            .unwrap();
        until(&mut app, |w| {
            w.resource::<EditorState>().pending_open.is_none()
                && w.resource::<EditorState>().open_error.is_none()
        });
        assert!(app.world().resource::<B1Runtime>().candidate.is_none());
    }
    #[test]
    fn superseding_pending_open_rejects_late_completion_without_replacing_work() {
        let (mut app, _, _) = harness(false);
        app.world_mut()
            .resource_mut::<EditorState>()
            .request_open(b1())
            .unwrap();
        app.update();
        let replacement = original();
        app.world_mut()
            .resource_mut::<EditorState>()
            .request_open(replacement.clone())
            .unwrap();
        for _ in 0..20 {
            app.update();
        }
        assert_eq!(
            app.world().resource::<EditorState>().document(),
            Some(&replacement)
        );
        assert!(app.world().resource::<B1Runtime>().candidate.is_none());
        assert!(app.world().resource::<B1Runtime>().active.is_none());
    }
    fn motion_app() -> (App, Dir, Arc<AtomicUsize>) {
        let (mut app, dir, reads) = harness(false);
        super::super::add_playback_systems(&mut app);
        app.insert_resource(bevy::time::TimeUpdateStrategy::ManualDuration(
            std::time::Duration::ZERO,
        ));
        app.world_mut()
            .resource_mut::<Time<Virtual>>()
            .set_max_delta(std::time::Duration::from_secs(20));
        app.world_mut()
            .resource_mut::<EditorState>()
            .request_open(
                SceneDocument::from_profile(nvwa_core::CharacterProfile::b1_motion()).unwrap(),
            )
            .unwrap();
        until(&mut app, |w| {
            w.resource::<EditorState>().pending_open.is_none()
                && w.resource::<B1Runtime>()
                    .active
                    .as_ref()
                    .is_some_and(|s| s.rig.is_some())
                && w.resource::<RuntimeStatus>().ready
        });
        app.update();
        (app, dir, reads)
    }
    fn motion_tick(app: &mut App, seconds: f32) {
        app.insert_resource(bevy::time::TimeUpdateStrategy::ManualDuration(
            std::time::Duration::from_secs_f32(seconds),
        ));
        app.update();
    }
    fn motion_seek(app: &mut App, seconds: f32) {
        app.world_mut().resource_mut::<Playback>().seek_request = Some(seconds);
        motion_tick(app, 0.0);
    }
    #[test]
    fn actual_motion_clock_changes_bones_and_both_uploaded_meshes_without_refit() {
        assert_eq!(motion::CLIP_IDS, nvwa_core::B1_MOTION_CLIPS);
        assert_eq!(
            motion::DURATION_SECONDS,
            nvwa_core::B1_MOTION_DURATION_SECONDS
        );
        let (mut app, _, reads) = motion_app();
        let initial = b1_frame_snapshot(app.world()).unwrap();
        let handles = app
            .world()
            .resource::<B1Runtime>()
            .active
            .as_ref()
            .unwrap()
            .display_meshes
            .clone();
        let character = app
            .world()
            .resource::<B1Runtime>()
            .active
            .as_ref()
            .unwrap()
            .character;
        for id in motion::CLIP_IDS {
            let mut timeline = app
                .world()
                .resource::<EditorState>()
                .document()
                .unwrap()
                .timeline
                .clone();
            timeline[0].clip_id = id.into();
            app.world_mut()
                .resource_mut::<EditorState>()
                .apply(nvwa_core::Command::SetTimeline { clips: timeline })
                .unwrap();
            motion_tick(&mut app, 0.0);
            motion_seek(&mut app, 0.0);
            let rest = uploaded_positions(&app);
            let rest_bones = b1_frame_snapshot(app.world()).unwrap()["bones"].clone();
            app.world_mut().resource_mut::<Playback>().playing = true;
            motion_tick(&mut app, 1.0);
            assert_eq!(app.world().resource::<Playback>().position_seconds, 1.0);
            let middle = uploaded_positions(&app);
            assert!(
                part_position_deltas(&rest, &middle)
                    .iter()
                    .all(|delta| *delta > 1e-4)
            );
            let snap = b1_frame_snapshot(app.world()).unwrap();
            assert_ne!(snap["bones"], rest_bones);
            assert_eq!(snap["sample"]["source_seconds"], 1.0);
            app.world_mut().resource_mut::<Playback>().playing = false;
            motion_tick(&mut app, 0.5);
            assert_eq!(uploaded_positions(&app), middle);
            assert_eq!(app.world().resource::<Playback>().position_seconds, 1.0);
            motion_seek(&mut app, 4.0);
            assert!(position_delta(&rest, &uploaded_positions(&app)) < 1e-6);
            assert_eq!(
                b1_frame_snapshot(app.world()).unwrap()["sample"]["source_seconds"],
                0.0
            );
            let active = app.world().resource::<B1Runtime>().active.as_ref().unwrap();
            assert_eq!(active.display_meshes, handles);
            assert_eq!(active.character, character);
            assert_eq!(reads.load(Ordering::SeqCst), 14);
        }
        assert_eq!(initial["parts"].as_array().unwrap().len(), 2);
        assert_eq!(initial["bones"].as_array().unwrap().len(), 53);
    }
    #[test]
    fn finite_motion_replay_speed_gaps_and_backward_seek_use_production_transport() {
        let (mut app, _, _) = motion_app();
        let mut entry = app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .timeline[0]
            .clone();
        entry.looping = false;
        entry.speed = 2.0;
        entry.duration_seconds = 2.0;
        let mut later = entry.clone();
        later.id = "again".into();
        later.start_seconds = 3.0;
        later.speed = 0.5;
        later.duration_seconds = 4.0;
        app.world_mut()
            .resource_mut::<EditorState>()
            .apply(nvwa_core::Command::SetTimeline {
                clips: vec![later, entry],
            })
            .unwrap();
        motion_tick(&mut app, 0.0);
        motion_seek(&mut app, 1.0);
        assert_eq!(
            b1_frame_snapshot(app.world()).unwrap()["sample"]["source_seconds"],
            2.0
        );
        motion_seek(&mut app, 2.5);
        assert_eq!(
            b1_frame_snapshot(app.world()).unwrap()["sample"]["source_seconds"],
            4.0
        );
        motion_seek(&mut app, 3.0);
        assert_eq!(
            b1_frame_snapshot(app.world()).unwrap()["sample"]["source_seconds"],
            0.0
        );
        motion_seek(&mut app, 7.0);
        assert!(app.world().resource::<Playback>().completed);
        assert!(!app.world().resource::<Playback>().playing);
        app.world_mut().resource_mut::<Playback>().playing = true;
        motion_tick(&mut app, 0.5);
        assert_eq!(app.world().resource::<Playback>().position_seconds, 0.0);
        motion_tick(&mut app, 0.5);
        assert_eq!(
            b1_frame_snapshot(app.world()).unwrap()["sample"]["source_seconds"],
            1.0
        );
        motion_seek(&mut app, 0.25);
        assert_eq!(
            b1_frame_snapshot(app.world()).unwrap()["sample"]["source_seconds"],
            0.5
        );
    }
    #[test]
    fn delayed_and_superseded_fit_retains_latest_seek_restart_and_live_pause_intent() {
        let (mut app, _, reads) = motion_app();
        motion_seek(&mut app, 1.25);
        let character_id = app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .character
            .id
            .clone();
        let set_shape = |app: &mut App, value| {
            app.world_mut()
                .resource_mut::<EditorState>()
                .apply(nvwa_core::Command::SetParameters {
                    character_id: character_id.clone(),
                    values: [("torso_length".into(), value)].into_iter().collect(),
                })
                .unwrap()
        };
        set_shape(&mut app, 0.25);
        {
            let mut playback = app.world_mut().resource_mut::<Playback>();
            playback.playing = true;
            playback.seek_request = Some(2.5);
        }
        motion_tick(&mut app, 0.25);
        assert_eq!(app.world().resource::<Playback>().seek_request, Some(2.5));
        assert_eq!(app.world().resource::<Playback>().position_seconds, 1.25);
        assert!(app.world().resource::<B1Runtime>().candidate.is_some());
        set_shape(&mut app, 0.5);
        app.world_mut().resource_mut::<Playback>().seek_request = Some(3.0);
        motion_tick(&mut app, 0.0);
        assert_eq!(app.world().resource::<Playback>().seek_request, Some(3.0));
        // Restart is an explicit seek0 + play; a subsequent Pause wins while fitting.
        {
            let mut playback = app.world_mut().resource_mut::<Playback>();
            playback.seek_request = Some(0.0);
            playback.playing = true;
        }
        app.world_mut().resource_mut::<Playback>().playing = false;
        until(&mut app, |w| {
            w.resource::<RuntimeStatus>().ready
                && w.resource::<B1Runtime>()
                    .active
                    .as_ref()
                    .is_some_and(|s| s.selection.parameters["torso_length"] == 0.5)
        });
        assert_eq!(app.world().resource::<Playback>().seek_request, None);
        assert_eq!(app.world().resource::<Playback>().position_seconds, 0.0);
        assert!(!app.world().resource::<Playback>().playing);
        assert_eq!(
            b1_frame_snapshot(app.world()).unwrap()["sample"]["source_seconds"],
            0.0
        );
        set_shape(&mut app, 0.75);
        app.world_mut().resource_mut::<Playback>().seek_request = Some(1.75);
        until(&mut app, |w| {
            w.resource::<RuntimeStatus>().ready
                && w.resource::<B1Runtime>()
                    .active
                    .as_ref()
                    .is_some_and(|s| s.selection.parameters["torso_length"] == 0.75)
        });
        assert_eq!(
            b1_frame_snapshot(app.world()).unwrap()["sample"]["source_seconds"],
            1.75
        );
        motion_tick(&mut app, 0.5);
        assert_eq!(app.world().resource::<Playback>().position_seconds, 1.75);
        assert_eq!(reads.load(Ordering::SeqCst), 14);
    }
    fn assert_static_transport(app: &App) {
        let playback = app.world().resource::<Playback>();
        assert!(!playback.playing);
        assert!(playback.clip_id.is_empty());
        assert!(playback.active_timeline_id.is_empty());
        assert_eq!(playback.position_seconds, 0.0);
        assert_eq!(playback.seek_request, None);
        assert!(!playback.completed);
        assert!(playback.error.is_none());
        assert_eq!(
            app.world()
                .resource::<EditorState>()
                .document()
                .unwrap()
                .profile,
            nvwa_core::CharacterProfile::b1()
        );
    }
    #[test]
    fn successful_static_open_clears_all_prior_motion_transport_identity() {
        let (mut app, _, _) = motion_app();
        motion_seek(&mut app, 1.5);
        {
            let mut playback = app.world_mut().resource_mut::<Playback>();
            playback.playing = true;
            playback.error = Some("prior error".into());
        }
        app.world_mut()
            .resource_mut::<EditorState>()
            .request_open(b1())
            .unwrap();
        until(&mut app, |w| {
            w.resource::<EditorState>().pending_open.is_none()
                && w.resource::<B1Runtime>()
                    .active
                    .as_ref()
                    .is_some_and(|s| s.rig.is_none())
                && w.resource::<RuntimeStatus>().ready
        });
        assert_static_transport(&app);
        motion_tick(&mut app, 0.5);
        assert_static_transport(&app);
    }
    fn cached_positions(app: &App) -> Vec<Vec<[f32; 3]>> {
        app.world()
            .resource::<B1Runtime>()
            .active
            .as_ref()
            .unwrap()
            .display_meshes
            .iter()
            .map(|handle| {
                match app
                    .world()
                    .resource::<Assets<Mesh>>()
                    .get(handle)
                    .unwrap()
                    .attribute(Mesh::ATTRIBUTE_POSITION)
                    .unwrap()
                {
                    bevy::mesh::VertexAttributeValues::Float32x3(v) => v.clone(),
                    _ => panic!("cached CPU positions absent"),
                }
            })
            .collect()
    }
    #[test]
    fn actual_display_and_bone_bindings_guard_clock_publication_status_and_readback() {
        let (mut app, _, _) = motion_app();
        motion_seek(&mut app, 1.0);
        let (display, correct, wrong, bone, parent) = {
            let active = app.world().resource::<B1Runtime>().active.as_ref().unwrap();
            let bone = active
                .bone_bindings
                .iter()
                .find(|(name, _)| name == "calf_l")
                .unwrap()
                .1;
            (
                active.displays[0],
                active.display_meshes[0].clone(),
                active.display_meshes[1].clone(),
                bone,
                app.world().get::<ChildOf>(bone).unwrap().parent(),
            )
        };
        for fault in [
            "wrong_mesh",
            "missing_mesh",
            "missing_bone_transform",
            "wrong_bone_parent",
        ] {
            let before = cached_positions(&app);
            let transform = *app.world().get::<Transform>(bone).unwrap();
            match fault {
                "wrong_mesh" => {
                    app.world_mut()
                        .entity_mut(display)
                        .insert(Mesh3d(wrong.clone()));
                }
                "missing_mesh" => {
                    app.world_mut().entity_mut(display).remove::<Mesh3d>();
                }
                "missing_bone_transform" => {
                    app.world_mut().entity_mut(bone).remove::<Transform>();
                }
                _ => {
                    let character = app
                        .world()
                        .resource::<B1Runtime>()
                        .active
                        .as_ref()
                        .unwrap()
                        .character;
                    app.world_mut().entity_mut(character).add_child(bone);
                }
            }
            assert!(
                b1_frame_snapshot(app.world()).is_err(),
                "actual binding mutation must reject direct readback: {fault}"
            );
            app.world_mut().resource_mut::<Playback>().playing = true;
            motion_tick(&mut app, 0.25);
            assert_eq!(
                app.world().resource::<Playback>().position_seconds,
                1.0,
                "clock must hold invalid binding: {fault}"
            );
            assert!(
                !app.world().resource::<RuntimeStatus>().ready,
                "invalid binding cannot remain Ready: {fault}"
            );
            assert!(app.world().resource::<RuntimeStatus>().error.is_some());
            assert_eq!(
                cached_positions(&app),
                before,
                "invalid binding must not update detached cached meshes: {fault}"
            );
            assert!(b1_frame_snapshot(app.world()).is_err());
            app.world_mut()
                .entity_mut(display)
                .insert(Mesh3d(correct.clone()));
            app.world_mut().entity_mut(bone).insert(transform);
            app.world_mut().entity_mut(parent).add_child(bone);
            motion_tick(&mut app, 0.0);
            assert!(
                app.world().resource::<RuntimeStatus>().ready,
                "restored binding recovers: {fault}"
            );
            assert!(b1_frame_snapshot(app.world()).is_ok());
        }
    }

    #[test]
    fn snapshot_rejects_commands_and_queued_seek_before_publication_then_accepts_real_frame() {
        let (mut app, _, _) = motion_app();
        motion_seek(&mut app, 1.0);
        let before = b1_frame_snapshot(app.world()).unwrap();
        let mut timeline = app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .timeline
            .clone();
        timeline[0].clip_id = motion::CLIP_IDS[1].into();
        app.world_mut()
            .resource_mut::<EditorState>()
            .apply(nvwa_core::Command::SetTimeline { clips: timeline })
            .unwrap();
        assert!(
            b1_frame_snapshot(app.world()).is_err(),
            "new timeline cannot label old arm buffers"
        );
        motion_tick(&mut app, 0.0);
        let changed = b1_frame_snapshot(app.world()).unwrap();
        assert_eq!(changed["sample"]["clip_id"], motion::CLIP_IDS[1]);
        assert_ne!(changed["revision"], before["revision"]);
        let id = app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .character
            .id
            .clone();
        app.world_mut()
            .resource_mut::<EditorState>()
            .apply(nvwa_core::Command::SetDiagnosticPose {
                character_id: id.clone(),
                pose_id: "elbow".into(),
            })
            .unwrap();
        assert!(
            b1_frame_snapshot(app.world()).is_err(),
            "new diagnostic cannot label old motion buffers"
        );
        motion_tick(&mut app, 0.0);
        let diagnostic = b1_frame_snapshot(app.world()).unwrap();
        assert_eq!(diagnostic["mode"], "diagnostic");
        assert_eq!(diagnostic["diagnostic_pose"], "elbow");
        app.world_mut()
            .resource_mut::<EditorState>()
            .apply(nvwa_core::Command::Undo)
            .unwrap();
        motion_tick(&mut app, 0.0);
        app.world_mut().resource_mut::<Playback>().seek_request = Some(2.0);
        assert!(
            b1_frame_snapshot(app.world()).is_err(),
            "queued seek is not a published frame"
        );
        motion_tick(&mut app, 0.0);
        let sought = b1_frame_snapshot(app.world()).unwrap();
        assert_eq!(sought["sample"]["source_seconds"], 2.0);
        let handles = app
            .world()
            .resource::<B1Runtime>()
            .active
            .as_ref()
            .unwrap()
            .display_meshes
            .clone();
        let positions = uploaded_positions(&app);
        app.world_mut()
            .resource_mut::<EditorState>()
            .apply(nvwa_core::Command::SetScale {
                character_id: id,
                scale: 1.2,
            })
            .unwrap();
        assert!(
            b1_frame_snapshot(app.world()).is_err(),
            "scale command awaits actual propagated display transform"
        );
        motion_tick(&mut app, 0.0);
        assert!(b1_frame_snapshot(app.world()).is_ok());
        assert_eq!(uploaded_positions(&app), positions);
        assert_eq!(
            app.world()
                .resource::<B1Runtime>()
                .active
                .as_ref()
                .unwrap()
                .display_meshes,
            handles
        );
        let mut stage = app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .stage
            .clone();
        stage.camera.azimuth_degrees += 20.0;
        app.world_mut()
            .resource_mut::<EditorState>()
            .apply(nvwa_core::Command::SetStage { stage })
            .unwrap();
        assert!(
            b1_frame_snapshot(app.world()).is_err(),
            "stage revision awaits normal frame publication"
        );
        motion_tick(&mut app, 0.0);
        assert!(b1_frame_snapshot(app.world()).is_ok());
        assert_eq!(uploaded_positions(&app), positions);
    }

    #[test]
    fn rejected_motion_open_preserves_committed_history_and_continuing_playback() {
        let (mut app, dir, _) = motion_app();
        let id = app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .character
            .id
            .clone();
        app.world_mut()
            .resource_mut::<EditorState>()
            .apply(nvwa_core::Command::SetScale {
                character_id: id,
                scale: 1.1,
            })
            .unwrap();
        motion_seek(&mut app, 1.0);
        app.world_mut().resource_mut::<Playback>().playing = true;
        let committed = app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .clone();
        let handles = app
            .world()
            .resource::<B1Runtime>()
            .active
            .as_ref()
            .unwrap()
            .display_meshes
            .clone();
        dir.remove_asset(Path::new("characters/mpfb-b1-v1/weights.game_engine.json"));
        app.world_mut()
            .resource_mut::<EditorState>()
            .request_open(
                SceneDocument::from_profile(nvwa_core::CharacterProfile::b1_motion()).unwrap(),
            )
            .unwrap();
        // The committed renderer advances despite a different pending candidate.
        motion_tick(&mut app, 0.25);
        assert_eq!(app.world().resource::<Playback>().position_seconds, 1.25);
        motion_tick(&mut app, 0.0);
        until(&mut app, |w| {
            w.resource::<EditorState>().open_error.is_some()
        });
        assert_eq!(
            app.world().resource::<EditorState>().document(),
            Some(&committed)
        );
        assert!(app.world().resource::<Playback>().playing);
        assert_eq!(app.world().resource::<Playback>().position_seconds, 1.25);
        assert_eq!(
            app.world()
                .resource::<B1Runtime>()
                .active
                .as_ref()
                .unwrap()
                .display_meshes,
            handles
        );
        assert!(b1_frame_snapshot(app.world()).is_ok());
        app.world_mut()
            .resource_mut::<EditorState>()
            .apply(nvwa_core::Command::Undo)
            .unwrap();
        assert_eq!(
            app.world()
                .resource::<EditorState>()
                .document()
                .unwrap()
                .character
                .scale,
            1.0
        );
    }

    #[test]
    fn rejected_frame_keeps_both_uploaded_buffers_and_never_returns_inconsistent_snapshot() {
        let (mut app, _, _) = motion_app();
        motion_seek(&mut app, 1.0);
        let before = uploaded_positions(&app);
        let skin = app
            .world_mut()
            .resource_mut::<B1Runtime>()
            .active
            .as_mut()
            .unwrap()
            .skins
            .pop()
            .unwrap();
        motion_seek(&mut app, 2.0);
        assert_eq!(uploaded_positions(&app), before);
        assert!(b1_frame_snapshot(app.world()).is_err());
        assert!(!app.world().resource::<RuntimeStatus>().ready);
        assert!(!app.world().resource::<Playback>().playing);
        app.world_mut()
            .resource_mut::<B1Runtime>()
            .active
            .as_mut()
            .unwrap()
            .skins
            .push(skin);
        motion_tick(&mut app, 0.0);
        assert!(b1_frame_snapshot(app.world()).is_ok());
        assert!(app.world().resource::<RuntimeStatus>().ready);
        assert!(position_delta(&before, &uploaded_positions(&app)) > 1e-4);
    }

    #[test]
    fn bounded_reader_stops_at_one_over_limit() {
        let mut reader = bevy::asset::io::VecReader::new(vec![0; 1025]);
        let error = future::block_on(bounded_read(&mut reader, 1024)).unwrap_err();
        assert!(error.contains("byte limit"));
    }
}

#[derive(Clone, Debug, PartialEq)]
struct FrameSample {
    clip_id: String,
    timeline_id: String,
    position: f32,
    source: f32,
    diagnostic: String,
}
fn frame_sample(doc: &SceneDocument, position: f32) -> FrameSample {
    if doc.timeline.is_empty() {
        FrameSample {
            clip_id: String::new(),
            timeline_id: String::new(),
            position: 0.0,
            source: 0.0,
            diagnostic: doc.character.diagnostic_pose.clone().unwrap_or_default(),
        }
    } else if doc.is_single_loop() {
        FrameSample {
            clip_id: doc.timeline[0].clip_id.clone(),
            timeline_id: doc.timeline[0].id.clone(),
            position,
            source: position.rem_euclid(motion::DURATION_SECONDS),
            diagnostic: String::new(),
        }
    } else {
        let (entry, source) = super::sequence_sample(doc, position);
        FrameSample {
            clip_id: entry.clip_id.clone(),
            timeline_id: entry.id.clone(),
            position,
            source,
            diagnostic: String::new(),
        }
    }
}
fn sample_pose(sample: &FrameSample) -> Result<DiagnosticPose, String> {
    if sample.clip_id.is_empty() {
        diagnostic_pose(&sample.diagnostic)
    } else {
        motion::sample(&sample.clip_id, sample.source)
    }
}
fn session_is_motion(_world: &World, runtime: &B1Runtime) -> bool {
    runtime.active.as_ref().is_some_and(|s| s.rig.is_some())
}

fn requested_position(doc: &SceneDocument, playback: &Playback) -> f32 {
    let duration = if doc.is_single_loop() {
        motion::DURATION_SECONDS
    } else {
        doc.timeline_duration_seconds()
    };
    playback
        .seek_request
        .filter(|t| t.is_finite())
        .map(|t| t.clamp(0.0, duration))
        .unwrap_or(playback.position_seconds)
}
fn adopt_published_transport(doc: &SceneDocument, playback: &mut Playback, sample: &FrameSample) {
    if playback
        .seek_request
        .is_some_and(|t| t.is_finite() && requested_position(doc, playback) == sample.position)
    {
        playback.seek_request = None;
    }
    playback.position_seconds = sample.position;
    playback.clip_id = sample.clip_id.clone();
    playback.active_timeline_id = sample.timeline_id.clone();
    playback.completed = !doc.timeline.is_empty()
        && !doc.is_single_loop()
        && sample.position >= doc.timeline_duration_seconds();
    if playback.completed {
        playback.playing = false;
    }
}

/// The real B1 transport. Tests drive the same Time resource and seek intents.
fn advance_motion_transport(
    doc: &SceneDocument,
    playback: &mut Playback,
    delta: f32,
    changed: bool,
    ready: bool,
) {
    if changed {
        playback.position_seconds = 0.0;
        playback.completed = false;
    }
    if doc.timeline.is_empty() {
        playback.position_seconds = 0.0;
        playback.playing = false;
        playback.completed = false;
        playback.seek_request = None;
        playback.clip_id.clear();
        playback.active_timeline_id.clear();
        return;
    }
    let duration = if doc.is_single_loop() {
        motion::DURATION_SECONDS
    } else {
        doc.timeline_duration_seconds()
    };
    if !ready {
        if playback.seek_request.is_some_and(|t| !t.is_finite()) {
            playback.error = Some("Seek time must be finite".into());
            playback.seek_request = None;
        }
        let sample = frame_sample(doc, playback.position_seconds);
        playback.clip_id = sample.clip_id;
        playback.active_timeline_id = sample.timeline_id;
        return;
    }
    let seek = playback.seek_request.take();
    if let Some(position) = seek {
        if !position.is_finite() {
            playback.error = Some("Seek time must be finite".into());
            return;
        }
        playback.position_seconds = position.clamp(0.0, duration);
        playback.error = None;
    } else if playback.completed && playback.playing {
        playback.position_seconds = 0.0;
    } else if playback.playing && !changed && ready {
        let step = delta
            * if doc.is_single_loop() {
                doc.timeline[0].speed
            } else {
                1.0
            };
        playback.position_seconds = if doc.is_single_loop() {
            (playback.position_seconds + step).rem_euclid(duration)
        } else {
            (playback.position_seconds + step).min(duration)
        };
    }
    playback.completed = !doc.is_single_loop() && playback.position_seconds >= duration;
    if playback.completed {
        playback.playing = false;
    }
    let sample = frame_sample(doc, playback.position_seconds);
    playback.clip_id = sample.clip_id;
    playback.active_timeline_id = sample.timeline_id;
}

fn update_motion_transport(world: &mut World, runtime: &mut B1Runtime) {
    let editor = world.resource::<EditorState>();
    let Some(doc) = editor
        .visible_document()
        .filter(|d| d.profile.backend.is_b1_motion())
        .cloned()
    else {
        return;
    };
    let generation = editor.document_generation;
    let changed = runtime.transport_generation != generation || runtime.timeline != doc.timeline;
    runtime.timeline = doc.timeline.clone();
    runtime.transport_generation = generation;
    let ready = runtime.active.as_ref().is_some_and(|s| {
        s.rig.is_some()
            && s.generation == generation
            && s.selection == Selection::from_doc(&doc)
            && s.frame_error.is_none()
            && validate_structure(world, s).is_ok()
    });
    let delta = world.resource::<Time>().delta_secs();
    advance_motion_transport(
        &doc,
        &mut world.resource_mut::<Playback>(),
        delta,
        changed,
        ready,
    );
}
fn animate_active(world: &mut World, runtime: &mut B1Runtime) {
    let editor = world.resource::<EditorState>();
    let Some(doc) = editor
        .visible_document()
        .filter(|d| d.profile.backend.is_b1_motion())
        .cloned()
    else {
        return;
    };
    let generation = editor.document_generation;
    let Some(active) = runtime.active.as_mut().filter(|s| {
        s.rig.is_some() && s.generation == generation && s.selection == Selection::from_doc(&doc)
    }) else {
        return;
    };
    let sample = frame_sample(&doc, requested_position(&doc, world.resource::<Playback>()));
    if active.last_sample.as_ref() == Some(&sample) && active.frame_error.is_none() {
        return;
    }
    let result =
        sample_pose(&sample).and_then(|pose| active.rig.as_ref().unwrap().apply(world, &pose));
    match result {
        Ok(()) => {
            active.pending_sample = Some(sample);
        }
        Err(error) => frame_failure(world, active, error),
    }
}
fn frame_failure(world: &mut World, session: &mut Session, error: String) {
    session.frame_error = Some(error.clone());
    session.pending_sample = None;
    let mut playback = world.resource_mut::<Playback>();
    playback.playing = false;
    playback.error = Some(error.clone());
    let mut status = world.resource_mut::<RuntimeStatus>();
    status.ready = false;
    status.error = Some(error);
    status.phase = "B1 frame failed · last displayed frame preserved".into();
}
fn publish_active(world: &mut World, runtime: &mut B1Runtime) {
    let Some(active) = runtime
        .active
        .as_mut()
        .filter(|s| s.pending_sample.is_some())
    else {
        return;
    };
    let result = (|| {
        validate_structure(world, active)?;
        let bones = active
            .rig
            .as_ref()
            .ok_or("prepared rig absent")?
            .frames(world, active.character)?;
        if bones.len() != 53 {
            return Err("B1 motion requires all53 bones".to_string());
        }
        let frames = active
            .skins
            .iter()
            .map(|skin| skin.evaluate(&bones))
            .collect::<Result<Vec<_>, _>>()?;
        if frames.len() != 2 || active.display_meshes.len() != 2 {
            return Err("B1 motion requires both display parts".into());
        }
        // Validate every destination before mutating either one.
        for handle in &active.display_meshes {
            if world.resource::<Assets<Mesh>>().get(handle).is_none() {
                return Err("B1 display mesh absent".into());
            }
        }
        let mut meshes = world.resource_mut::<Assets<Mesh>>();
        for (handle, frame) in active.display_meshes.iter().zip(frames) {
            let mut mesh = meshes.get_mut(handle).unwrap();
            mesh.insert_attribute(Mesh::ATTRIBUTE_POSITION, frame.positions);
            mesh.insert_attribute(Mesh::ATTRIBUTE_NORMAL, frame.normals);
            mesh.insert_attribute(Mesh::ATTRIBUTE_TANGENT, frame.tangents);
        }
        active.last_bones = bones;
        Ok(())
    })();
    match result {
        Ok(()) => {
            active.last_sample = active.pending_sample.take();
            active.serial = active.serial.saturating_add(1);
            active.frame_error = None;
            if let Some(doc) = world.resource::<EditorState>().visible_document().cloned() {
                adopt_published_transport(
                    &doc,
                    &mut world.resource_mut::<Playback>(),
                    active.last_sample.as_ref().unwrap(),
                );
            }
            world.resource_mut::<Playback>().error = None;
            refresh_active_status(world, runtime);
        }
        Err(error) => frame_failure(world, active, error),
    }
}

/// Pin the actual fitted ECS hierarchy once; roots may include source scene
/// nodes, so retain those exact edges rather than inventing a direct-parent rig.
fn capture_structure(world: &World, session: &mut Session) -> Result<(), String> {
    let skeleton = world
        .get::<CharacterSkeleton>(session.character)
        .ok_or("B1 skeleton absent")?;
    let rig = world
        .resource::<RigData>()
        .0
        .as_ref()
        .ok_or("B1 rig absent")?;
    let reference = rig.reference_rig();
    session.skeleton_binding = Some(skeleton.skeleton_entity);
    let mut edges = BTreeMap::new();
    for &name in &reference.bone_names {
        let entity = *skeleton
            .bone_map
            .get(name)
            .ok_or("B1 required bone absent")?;
        session.bone_bindings.push((name.into(), entity));
        if let Some(expected_parent) = skeleton.bone_map.get(reference.bone_parents[name].as_str())
        {
            if world.get::<ChildOf>(entity).map(ChildOf::parent) != Some(*expected_parent) {
                return Err("B1 fitted bone parent differs from source rig".into());
            }
        }
        let mut current = entity;
        let mut seen = BTreeSet::new();
        while current != session.character {
            if !seen.insert(current) {
                return Err("B1 hierarchy cycle".into());
            }
            let parent = world
                .get::<ChildOf>(current)
                .ok_or("B1 hierarchy parent absent")?
                .parent();
            edges.insert(current, parent);
            current = parent;
        }
    }
    session.hierarchy_bindings = edges.into_iter().collect();
    Ok(())
}

/// Cheap structural guard shared by clock, pose/publication, readiness and QA.
/// It checks bindings/counts only; full mesh arrays stay opt-in in readback.
fn validate_structure(world: &World, session: &Session) -> Result<(), String> {
    use bevy::mesh::VertexAttributeValues;
    if session.parts.len() != 2
        || session.displays.len() != 2
        || session.display_meshes.len() != 2
        || session.display_transforms.len() != 2
        || session.display_indices.len() != 2
        || session.display_vertex_counts.len() != 2
        || session.bone_bindings.len() != 53
        || session.joint_count != 53
    {
        return Err("B1 fitted part/bone coverage changed".into());
    }
    let skeleton = world
        .get::<CharacterSkeleton>(session.character)
        .ok_or("B1 actual skeleton absent")?;
    if session.skeleton_binding != Some(skeleton.skeleton_entity)
        || skeleton.bone_map.len() != 53
        || skeleton.model_space_inv_bindposes.len() != 53
        || world.get::<Transform>(skeleton.skeleton_entity).is_none()
        || world
            .get::<GlobalTransform>(skeleton.skeleton_entity)
            .is_none()
    {
        return Err("B1 actual skeleton root or bone coverage absent".into());
    }
    for (name, entity) in &session.bone_bindings {
        if skeleton.bone_map.get(name.as_str()) != Some(entity)
            || world
                .get::<Transform>(*entity)
                .is_none_or(|t| !t.to_matrix().is_finite())
            || world
                .get::<GlobalTransform>(*entity)
                .is_none_or(|t| !t.to_matrix().is_finite())
        {
            return Err(format!("B1 actual bone binding absent or changed: {name}"));
        }
    }
    for (entity, parent) in &session.hierarchy_bindings {
        if world.get::<ChildOf>(*entity).map(ChildOf::parent) != Some(*parent)
            || world.get::<Transform>(*entity).is_none()
            || world.get::<GlobalTransform>(*entity).is_none()
        {
            return Err("B1 actual bone hierarchy binding changed".into());
        }
    }
    if session.rig.is_some()
        && (session.skins.len() != 2
            || session.source_ids.len() != 2
            || session.last_bones.len() != 53
            || session
                .last_sample
                .as_ref()
                .is_none_or(|sample| !sample.position.is_finite() || !sample.source.is_finite())
            || session
                .source_ids
                .iter()
                .zip(&session.display_vertex_counts)
                .any(|(ids, count)| ids.len() != *count))
    {
        return Err("B1 published sample/fitted cache coverage changed".into());
    }
    let meshes = world.resource::<Assets<Mesh>>();
    for i in 0..2 {
        let actual = world
            .get::<Mesh3d>(session.displays[i])
            .ok_or("B1 actual display binding absent")?;
        if actual.0 != session.display_meshes[i]
            || world.get::<Transform>(session.displays[i]).is_none()
            || world.get::<GlobalTransform>(session.displays[i]).is_none()
        {
            return Err("B1 actual display points at a different mesh or lacks transform".into());
        }
        let mesh = meshes
            .get(&actual.0)
            .ok_or("B1 actual display mesh absent")?;
        let count = session.display_vertex_counts[i];
        if !matches!(mesh.attribute(Mesh::ATTRIBUTE_POSITION), Some(VertexAttributeValues::Float32x3(v)) if v.len() == count)
            || !matches!(mesh.attribute(Mesh::ATTRIBUTE_NORMAL), Some(VertexAttributeValues::Float32x3(v)) if v.len() == count)
            || !matches!(mesh.attribute(Mesh::ATTRIBUTE_TANGENT), Some(VertexAttributeValues::Float32x4(v)) if v.len() == count)
            || mesh.indices().map(Indices::len) != Some(session.display_indices[i].len())
        {
            return Err("B1 actual part vertex/index coverage changed".into());
        }
    }
    Ok(())
}

struct PublishedBinding {
    document: SceneDocument,
    transport: Playback,
    display_transforms: Vec<[f32; 16]>,
}

/// A paused sample need not be skinned again for presentation-only changes, but
/// its new document/transport identity is admitted only after this normal frame.
fn bind_published_frame(world: &World, runtime: &mut B1Runtime) {
    let Some(active) = runtime.active.as_mut().filter(|s| s.rig.is_some()) else {
        return;
    };
    active.published_binding = None;
    if validate_structure(world, active).is_err() {
        return;
    }
    let editor = world.resource::<EditorState>();
    let Some(doc) = editor.visible_document() else {
        return;
    };
    let playback = world.resource::<Playback>();
    if active.frame_error.is_some()
        || active.pending_sample.is_some()
        || active.phase != 2
        || active.generation != editor.document_generation
        || active.selection != Selection::from_doc(doc)
        || !doc.profile.backend.is_b1_motion()
        || playback.seek_request.is_some()
        || active.last_sample.as_ref() != Some(&frame_sample(doc, playback.position_seconds))
    {
        return;
    }
    let mut transforms = Vec::new();
    for (entity, base) in active.displays.iter().zip(&active.display_transforms) {
        let Some(global) = world.get::<GlobalTransform>(*entity) else {
            return;
        };
        let mut expected = *base;
        expected.translation *= doc.character.scale;
        expected.scale *= doc.character.scale;
        if !global.to_matrix().abs_diff_eq(expected.to_matrix(), 1e-6) {
            return;
        }
        transforms.push(global.to_matrix().to_cols_array());
    }
    if transforms.len() != 2 {
        return;
    }
    active.published_binding = Some(PublishedBinding {
        document: doc.clone(),
        transport: playback.clone(),
        display_transforms: transforms,
    });
}

/// Read successful production bones and actual uploaded mesh buffers. Explicit QA only.
/// Matrices are column-major; fitted/model arrays use metres, transforms map to stage/world.
pub fn b1_frame_snapshot(world: &World) -> Result<serde_json::Value, String> {
    use bevy::mesh::VertexAttributeValues;
    let runtime = world
        .get_resource::<B1Runtime>()
        .ok_or("B1 runtime absent")?;
    let active = runtime.active.as_ref().ok_or("B1 active session absent")?;
    if active.frame_error.is_some() || active.phase != 2 || active.pending_sample.is_some() {
        return Err("B1 frame not successfully published".into());
    }
    validate_structure(world, active)?;
    let editor = world.resource::<EditorState>();
    let doc = editor.visible_document().ok_or("Work absent")?;
    if !doc.profile.backend.is_b1_motion()
        || active.generation != editor.document_generation
        || active.selection != Selection::from_doc(doc)
    {
        return Err("B1 displayed shape does not match visible Work".into());
    }
    let binding = active
        .published_binding
        .as_ref()
        .ok_or("B1 frame has no published document/transport binding")?;
    let playback = world.resource::<Playback>();
    if &binding.document != doc
        || playback.seek_request.is_some()
        || !super::same_transport(playback, &binding.transport)
    {
        return Err("B1 document or transport changed since frame publication".into());
    }
    let sample = active
        .last_sample
        .as_ref()
        .ok_or("published motion sample absent")?;
    let bones = active
        .rig
        .as_ref()
        .ok_or("prepared rig absent")?
        .frames(world, active.character)?;
    if serde_json::to_value(&bones).map_err(|e| e.to_string())?
        != serde_json::to_value(&active.last_bones).map_err(|e| e.to_string())?
    {
        return Err("B1 bones differ from published mesh frame".into());
    }
    let mut parts = Vec::new();
    for (i, part) in active.parts.iter().enumerate() {
        let entity = active.displays[i];
        let handle = &world.get::<Mesh3d>(entity).ok_or("display absent")?.0;
        let mesh = world
            .resource::<Assets<Mesh>>()
            .get(handle)
            .ok_or("display mesh absent")?;
        let positions = match mesh.attribute(Mesh::ATTRIBUTE_POSITION) {
            Some(VertexAttributeValues::Float32x3(v)) => v,
            _ => return Err("uploaded positions absent".into()),
        };
        let normals = match mesh.attribute(Mesh::ATTRIBUTE_NORMAL) {
            Some(VertexAttributeValues::Float32x3(v)) => v,
            _ => return Err("uploaded normals absent".into()),
        };
        let tangents = match mesh.attribute(Mesh::ATTRIBUTE_TANGENT) {
            Some(VertexAttributeValues::Float32x4(v)) => v,
            _ => return Err("uploaded tangents absent".into()),
        };
        let frame = active.skins[i].evaluate(&bones)?;
        if positions != &frame.positions || normals != &frame.normals || tangents != &frame.tangents
        {
            return Err("uploaded buffers differ from sampled full-positive frame".into());
        }
        let indices: Vec<_> = mesh
            .indices()
            .ok_or("display indices absent")?
            .iter()
            .collect();
        if indices != active.display_indices[i] {
            return Err("B1 uploaded triangle binding changed".into());
        }
        let transform = world
            .get::<GlobalTransform>(entity)
            .ok_or("display transform absent")?
            .to_matrix()
            .to_cols_array();
        if binding.display_transforms.get(i) != Some(&transform) {
            return Err("B1 presentation changed since frame publication".into());
        }
        parts.push(serde_json::json!({"name":part.name,"display_entity":format!("{entity:?}"),"mesh_handle":format!("{:?}",handle.id()),"source_ids":active.source_ids[i],"indices":indices,"positions":positions,"normals":normals,"tangents":tangents,"rest_positions":frame.rest_positions,"rest_normals":frame.rest_normals,"full_joint_influences":frame.full_joint_influences,"model_to_world":frame.model_to_world,"display_transform":transform}));
    }
    let (left, right) = if sample.clip_id.is_empty() {
        ("diagnostic", "diagnostic")
    } else {
        motion::contacts(&sample.clip_id, sample.source)?
    };
    Ok(
        serde_json::json!({"schema_version":1,"backend":doc.profile.backend,"profile_id":doc.profile.id,"asset_id":nvwa_core::B1_ASSET_ID,"generation":active.generation,"revision":doc.revision,"parameters":doc.character.parameters,"diagnostic_pose":doc.character.diagnostic_pose,"mode":if sample.clip_id.is_empty(){"diagnostic"}else{"motion"},"sample":{"serial":active.serial,"clip_id":sample.clip_id,"timeline_id":sample.timeline_id,"position_seconds":sample.position,"source_seconds":sample.source,"playing":playback.playing,"completed":playback.completed},"character_entity":format!("{:?}",active.character),"bones":bones,"parts":parts,"contacts":{"left":left,"right":right}}),
    )
}
