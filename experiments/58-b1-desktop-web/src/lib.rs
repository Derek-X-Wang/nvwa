//! Isolated same-code native/Web source-runtime diagnostic viewer. No production Work format.
use b1_pose_adapter::{
    DiagnosticPose, apply_pose_canonical, skin_mesh_frame_canonical, skin_mesh_frame_full_weights,
};
use bevy::ecs::intern::Internable;
use bevy::{
    asset::{AssetMetaCheck, AssetPlugin, RenderAssetUsages},
    mesh::{Indices, VertexAttributeValues, skinning::SkinnedMesh},
    prelude::*,
};
use bevy_egui::{EguiContexts, EguiPlugin, EguiPrimaryContextPass, egui};
use humentity::prelude::*;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::collections::{BTreeMap, BTreeSet};

const BUILD_IDENTITY: &str = include_str!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../.work/b1-pose-viewer/site/assets/build-identity.json"
));
const COMMON: &str = "2e8566a4f12de710ead88f6aa2d71fc44e0680761a4f2fdc48a844b6f3534ab7";
const RECIPES: [&str; 8] = [
    "neutral",
    "body-negative",
    "body-half",
    "body-positive",
    "face-negative",
    "face-half",
    "face-positive",
    "combined",
];
const POSES: [&str; 5] = ["neutral", "shoulder", "elbow", "knee", "combined"];
const TARGETS: [&str; 4] = [
    "torso-scale-vert-decr",
    "torso-scale-vert-incr",
    "chin-jaw-drop-decr",
    "chin-jaw-drop-incr",
];
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PrototypeState {
    pub format: String,
    pub schema_version: u32,
    pub recipe: String,
    pub pose: String,
    pub camera_yaw: f32,
    #[serde(default = "default_backend")]
    pub backend: String,
}
fn default_backend() -> String {
    "gpu4".into()
}
impl Default for PrototypeState {
    fn default() -> Self {
        Self {
            format: "nvwa-b1-pose-prototype".into(),
            schema_version: 1,
            recipe: "neutral".into(),
            pose: "neutral".into(),
            camera_yaw: 0.0,
            backend: default_backend(),
        }
    }
}
impl PrototypeState {
    pub fn parse(text: &str) -> Result<Self, String> {
        let s: Self = serde_json::from_str(text).map_err(|e| e.to_string())?;
        s.validate()?;
        Ok(s)
    }
    fn validate(&self) -> Result<(), String> {
        if self.format != "nvwa-b1-pose-prototype"
            || self.schema_version != 1
            || !RECIPES.contains(&self.recipe.as_str())
            || !POSES.contains(&self.pose.as_str())
            || !["gpu4", "full-weight-cpu"].contains(&self.backend.as_str())
            || !self.camera_yaw.is_finite()
            || self.camera_yaw.abs() > 180.0
        {
            return Err("Invalid prototype state: format/version/recipe/pose/camera".into());
        }
        Ok(())
    }
}
#[derive(Resource)]
struct Viewer {
    state: PrototypeState,
    built_recipe: String,
    posed: String,
    character: Option<Entity>,
    parts: Vec<(String, Entity, Handle<MhcloAsset>, Handle<Mesh>)>,
    template: Option<Handle<CharacterTemplate>>,
    status: String,
    error: String,
    exchange: String,
    frame: Value,
    phase: u8,
    wait_frames: u64,
    source_handles: Vec<(Handle<ObjVertsAsset>, Handle<Mesh>)>,
    rendered: bool,
    display_entities: Vec<Entity>,
    built_backend: String,
    visibility_mask: Value,
    camera_target: Vec3,
    camera_distance: f32,
    omit_target: bool,
    headless: bool,
    command_file: Option<String>,
    frame_file: Option<String>,
    output_sequence: u64,
    last_report: String,
    last_command: String,
    rejected_commands: u64,
    inspect: bool,
    inspect_part: String,
    inspect_bone: usize,
    inspect_vertex: usize,
}
impl Viewer {
    fn fail(&mut self, error: String) {
        if self.phase != 255 {
            self.error = error;
            self.status = "FAILED — reload required; state and frame frozen".into();
            self.phase = 255;
        }
    }
    fn recoverable_error(&mut self, error: String) {
        if self.phase != 255 {
            self.error = error;
        }
    }
    fn new() -> Self {
        Self {
            state: default(),
            built_recipe: String::new(),
            posed: String::new(),
            character: None,
            parts: vec![],
            template: None,
            status: "Loading original source assets with explicit target paths".into(),
            error: String::new(),
            exchange: String::new(),
            frame: Value::Null,
            phase: 0,
            wait_frames: 0,
            source_handles: vec![],
            rendered: false,
            display_entities: vec![],
            built_backend: String::new(),
            visibility_mask: Value::Null,
            camera_target: Vec3::ZERO,
            camera_distance: 3.7,
            omit_target: false,
            headless: false,
            command_file: None,
            frame_file: None,
            output_sequence: 0,
            last_report: String::new(),
            last_command: String::new(),
            rejected_commands: 0,
            inspect: false,
            inspect_part: "body".into(),
            inspect_bone: 0,
            inspect_vertex: 0,
        }
    }
}
#[derive(Component)]
struct LabCamera;

#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen(start)]
pub fn web_start() {
    run();
}

pub fn run() -> AppExit {
    let mut viewer = Viewer::new();
    #[cfg(not(target_arch = "wasm32"))]
    {
        viewer.headless = std::env::var_os("B1_HEADLESS").is_some();
        viewer.omit_target = std::env::var_os("B1_OMIT_TARGET").is_some();
        viewer.command_file = std::env::var("B1_COMMAND_FILE").ok();
        viewer.frame_file = std::env::var("B1_FRAME_FILE").ok();
        if let Ok(state) = std::env::var("B1_INITIAL_STATE") {
            match PrototypeState::parse(&state) {
                Ok(s) => viewer.state = s,
                Err(e) => viewer.error = e,
            }
        }
    }
    #[cfg(target_arch = "wasm32")]
    {
        viewer.omit_target = web_sys::window()
            .and_then(|w| w.location().search().ok())
            .unwrap_or_default()
            .contains("omit_target=1");
    }
    let headless = viewer.headless;
    let mut app = App::new();
    if headless {
        app.add_plugins(MinimalPlugins)
            .add_plugins(AssetPlugin {
                file_path: asset_root(),
                meta_check: AssetMetaCheck::Never,
                ..default()
            })
            .add_plugins((
                bevy::transform::TransformPlugin,
                bevy::world_serialization::WorldSerializationPlugin,
                bevy::scene::ScenePlugin,
                bevy::mesh::MeshPlugin,
                bevy::image::ImagePlugin::default(),
                AnimationPlugin,
            ));
    } else {
        app.add_plugins(
            DefaultPlugins
                .set(AssetPlugin {
                    file_path: asset_root(),
                    meta_check: AssetMetaCheck::Never,
                    ..default()
                })
                .set(WindowPlugin {
                    primary_window: Some(Window {
                        title: "Nvwa B1 Pose Lab".into(),
                        resolution: bevy::window::WindowResolution::new(1440, 900),
                        canvas: Some("#b1-canvas".into()),
                        fit_canvas_to_parent: true,
                        ..default()
                    }),
                    ..default()
                }),
        )
        .add_plugins(EguiPlugin::default())
        .add_systems(Startup, scene)
        .add_systems(EguiPrimaryContextPass, ui);
    }
    app.add_plugins(HumentityPlugin)
        .insert_resource(SkeletonLodConfig::new(&[BoneMergeConfig::full()]))
        .insert_resource(viewer)
        .add_systems(Startup, load)
        .add_systems(
            Update,
            (
                asset_errors::<TargetAsset>,
                asset_errors::<MhcloAsset>,
                asset_errors::<ObjVertsAsset>,
                drive,
            )
                .chain(),
        )
        .add_systems(
            PostUpdate,
            publish.after(bevy::transform::TransformSystems::Propagate),
        );
    if headless {
        app.finish();
        app.cleanup();
        #[cfg(not(target_arch = "wasm32"))]
        let stop_file = std::env::var_os("B1_HEADLESS_STOP_FILE").map(std::path::PathBuf::from);
        #[cfg(target_arch = "wasm32")]
        let stop_file: Option<std::path::PathBuf> = None;
        for _ in 0..60000 {
            app.update();
            let v = app.world().resource::<Viewer>();
            if (v.phase == 255 || !v.error.is_empty()) && stop_file.is_none() {
                eprintln!("B1_FAILED {}", v.error);
                return AppExit::error();
            }
            if (v.phase == 4 || v.phase == 255)
                && (stop_file.is_none() || stop_file.as_ref().is_some_and(|p| p.is_file()))
            {
                return if v.phase == 4 && v.error.is_empty() {
                    AppExit::Success
                } else {
                    AppExit::error()
                };
            }
            std::thread::sleep(std::time::Duration::from_millis(2));
        }
        eprintln!("B1_FAILED timeout");
        AppExit::error()
    } else {
        app.run()
    }
}
fn asset_root() -> String {
    #[cfg(target_arch = "wasm32")]
    {
        "assets".into()
    }
    #[cfg(not(target_arch = "wasm32"))]
    {
        std::env::var("B1_ASSET_ROOT").unwrap_or_else(|_| {
            concat!(
                env!("CARGO_MANIFEST_DIR"),
                "/../../.work/b1-pose-viewer/site/assets"
            )
            .into()
        })
    }
}
fn load(mut commands: Commands, server: Res<AssetServer>, viewer: Res<Viewer>) {
    let targets = TARGETS
        .iter()
        .enumerate()
        .filter(|(i, _)| !viewer.omit_target || *i != 3)
        .map(|(_, s)| format!("targets/{s}.target"))
        .collect();
    humentity::load_and_insert_humentity_assets_explicit(
        &mut commands,
        &server,
        "base.obj",
        "vertex_groups.json",
        "composite.json",
        "empty.macro",
        targets,
        "rig.game_engine.json",
        "weights.game_engine.json",
    );
}
fn asset_errors<A: bevy::asset::Asset>(
    mut errors: MessageReader<bevy::asset::AssetLoadFailedEvent<A>>,
    mut v: ResMut<Viewer>,
) {
    for error in errors.read() {
        v.fail(format!("Asset failed: {}: {}", error.path, error.error));
    }
}
fn scene(mut commands: Commands) {
    commands.spawn((
        Camera3d::default(),
        bevy::core_pipeline::tonemapping::Tonemapping::Reinhard,
        Transform::from_xyz(0.0, 0.1, -3.7).looking_at(Vec3::ZERO, Vec3::Y),
        LabCamera,
    ));
    commands.insert_resource(ClearColor(Color::srgb(0.055, 0.075, 0.105)));
    commands.insert_resource(GlobalAmbientLight {
        color: Color::WHITE,
        brightness: 160.0,
        ..default()
    });
    commands.spawn((
        DirectionalLight {
            illuminance: 11000.0,
            shadow_maps_enabled: false,
            ..default()
        },
        Transform::from_xyz(3.0, 6.0, 4.0).looking_at(Vec3::new(0.0, 1.0, 0.0), Vec3::Y),
    ));
    commands.spawn((
        DirectionalLight {
            illuminance: 5500.0,
            ..default()
        },
        Transform::from_xyz(-4.0, 2.0, -3.0).looking_at(Vec3::new(0.0, 0.8, 0.0), Vec3::Y),
    ));
}
fn weights(recipe: &str) -> BTreeMap<String, f32> {
    let (body, face) = match recipe {
        "body-negative" => (-1.0f32, 0.0f32),
        "body-half" => (0.5, 0.0),
        "body-positive" => (1.0, 0.0),
        "face-negative" => (0.0, -1.0),
        "face-half" => (0.0, 0.5),
        "face-positive" => (0.0, 1.0),
        "combined" => (0.5, 0.5),
        _ => (0.0, 0.0),
    };
    TARGETS
        .into_iter()
        .zip([
            (-body).max(0.0),
            body.max(0.0),
            (-face).max(0.0),
            face.max(0.0),
        ])
        .map(|(k, v)| (k.into(), v))
        .collect()
}
fn pose(id: &str) -> DiagnosticPose {
    #[derive(Deserialize)]
    struct Set {
        poses: Vec<DiagnosticPose>,
    }
    serde_json::from_str::<Set>(include_str!("../../56-b1-pose-reference/poses.json"))
        .unwrap()
        .poses
        .into_iter()
        .find(|p| p.pose_id == id)
        .unwrap()
}
fn import_state(v: &mut Viewer, text: &str) {
    if v.phase == 255 {
        return;
    }
    match PrototypeState::parse(text) {
        Ok(state) => {
            v.state = state;
            v.error.clear();
        }
        Err(error) => v.recoverable_error(error),
    }
}
fn command(v: &mut Viewer, text: &str) {
    if v.phase == 255 {
        v.rejected_commands += 1;
        return;
    }
    let parsed = serde_json::from_str::<Value>(text);
    let result = (|| {
        let x = parsed.map_err(|e| e.to_string())?;
        match x.get("action").and_then(Value::as_str) {
            Some("select") => {
                let mut next = v.state.clone();
                if let Some(s) = x.get("recipe").and_then(Value::as_str) {
                    next.recipe = s.into()
                }
                if let Some(s) = x.get("pose").and_then(Value::as_str) {
                    next.pose = s.into()
                }
                if let Some(s) = x.get("backend").and_then(Value::as_str) {
                    next.backend = s.into();
                }
                if let Some(y) = x.get("camera_yaw").and_then(Value::as_f64) {
                    next.camera_yaw = y as f32
                }
                next.validate()?;
                v.state = next;
            }
            Some("import") => {
                let text = x.get("state").ok_or("state missing")?.to_string();
                import_state(v, &text);
                if !v.error.is_empty() {
                    return Err(v.error.clone());
                }
            }
            Some("export") => {}
            _ => return Err("Unknown command".into()),
        }
        Ok::<(), String>(())
    })();
    match result {
        Ok(()) => v.error.clear(),
        Err(e) => v.recoverable_error(e),
    }
}
fn drive(world: &mut World) {
    let mut v = world.remove_resource::<Viewer>().unwrap();
    #[cfg(target_arch = "wasm32")]
    {
        if let Some(w) = web_sys::window() {
            let key = wasm_bindgen::JsValue::from_str("__b1command");
            if let Ok(x) = js_sys::Reflect::get(&w, &key) {
                if let Some(text) = x.as_string() {
                    let _ = js_sys::Reflect::delete_property(&w, &key);
                    command(&mut v, &text);
                }
            }
        }
    }
    #[cfg(not(target_arch = "wasm32"))]
    {
        if let Some(path) = v.command_file.clone() {
            match std::fs::read_to_string(path) {
                Ok(s) => {
                    if s != v.last_command {
                        command(&mut v, &s);
                        v.last_command = s;
                    }
                }
                Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
                Err(e) => v.recoverable_error(e.to_string()),
            }
        }
    }
    v.wait_frames += 1;
    let result = advance(world, &mut v);
    if let Err(e) = result {
        v.fail(e);
    }
    if v.wait_frames > 12000 && v.phase < 3 {
        v.fail("Loader/build timeout — no selected frame ready".into());
    }
    world.insert_resource(v);
}
fn advance(world: &mut World, v: &mut Viewer) -> Result<(), String> {
    if v.phase == 255 {
        return Ok(());
    }
    if v.phase == 0 {
        if !world.contains_resource::<humentity::HumentityAssetsReady>() {
            return Ok(());
        }
        let morphs = world.resource::<MakeHumanMorphs>();
        for target in TARGETS {
            if !morphs.targets.read().unwrap().contains_key(target) {
                return Err(format!("Explicit target missing: {target}"));
            }
        }
        v.phase = 1;
    }
    if v.built_recipe != v.state.recipe {
        for entity in v.display_entities.drain(..) {
            world.entity_mut(entity).despawn();
        }
        if let Some(entity) = v.character.take() {
            world.entity_mut(entity).despawn();
        }
        v.parts.clear();
        v.source_handles.clear();
        v.posed.clear();
        v.rendered = false;
        v.display_entities.clear();
        v.built_backend.clear();
        v.frame = Value::Null;
        let mut requested = MorphTargets::default();
        for (name, value) in weights(&v.state.recipe) {
            requested.insert(humentity::NAME_INTERNER.intern(&name).leak(), value);
        }
        let resolved = world
            .resource::<MakeHumanMorphs>()
            .compute_target_weights(&requested)
            .map_err(|e| e.to_string())?;
        let template =
            world
                .resource_mut::<Assets<CharacterTemplate>>()
                .add(CharacterTemplate::new([CharacterMorphShape::new(
                    "selected", resolved,
                )]));
        let mut w = MorphTargets::default();
        w.insert("selected", 1.0);
        let shape = world
            .resource_mut::<Assets<CharacterShapeAsset>>()
            .add(CharacterShapeAsset::new(template.clone(), w));
        let entity = world
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
        for (name, path) in [
            ("body", "body.mhclo"),
            ("garment", "garment/female_sportsuit01.mhclo"),
        ] {
            let part: Handle<MhcloAsset> = world.resource::<AssetServer>().load(path);
            world
                .resource_mut::<MhcloMeshBuilder>()
                .trigger(LoadAssetMeshJob::Single {
                    part: part.clone(),
                    template_handle: template.clone(),
                    skeleton_lod: MeshBuildLod::Cpu(0),
                });
            let child = world
                .spawn((
                    CharacterPart {
                        mesh: part.clone(),
                        skeleton_lod: 0,
                    },
                    Transform::default(),
                    GlobalTransform::default(),
                ))
                .id();
            world.entity_mut(entity).add_child(child);
            v.parts.push((name.into(), child, part, Handle::default()));
            let path = if name == "body" {
                "base.obj"
            } else {
                "garment/female_sportsuit01.obj"
            };
            v.source_handles.push((
                world.resource::<AssetServer>().load(path),
                world.resource::<AssetServer>().load(path),
            ));
        }
        v.template = Some(template);
        v.character = Some(entity);
        v.built_recipe = v.state.recipe.clone();
        v.phase = 2;
        v.status = "Actual B1 fitting body, garment and skeleton".into();
        v.wait_frames = 0;
    }
    let Some(character) = v.character else {
        return Ok(());
    };
    if v.phase == 2 {
        if world.get::<SkeletonReady>(character).is_none() {
            return Ok(());
        }
        for (_, child, part, mesh) in &mut v.parts {
            if world.get::<SkinnedMesh>(*child).is_none() {
                return Ok(());
            }
            let key = (
                part.clone(),
                v.template.clone().unwrap(),
                MeshBuildLod::Cpu(0),
            );
            let Some(handle) = world
                .resource::<CachedMhcloMeshHandles>()
                .get(&key)
                .cloned()
            else {
                return Ok(());
            };
            *mesh = handle;
        }
        if !v.headless {
            attach_render_meshes(world, v)?;
        }
        v.phase = 3;
    }
    if v.built_backend != v.state.backend && !v.headless && v.phase >= 3 {
        for entity in v.display_entities.drain(..) {
            world.entity_mut(entity).despawn();
        }
        attach_render_meshes(world, v)?;
        v.frame = Value::Null;
        v.phase = 3;
    }
    if v.posed != v.state.pose {
        apply_pose_canonical(world, character, &pose(&v.state.pose))?;
        v.posed = v.state.pose.clone();
        v.phase = 3;
        v.frame = Value::Null;
    }
    if !v.headless {
        let yaw = v.state.camera_yaw.to_radians();
        let mut q = world.query_filtered::<&mut Transform, With<LabCamera>>();
        for mut t in q.iter_mut(world) {
            *t = Transform::from_translation(
                v.camera_target
                    + Vec3::new(
                        yaw.sin() * v.camera_distance,
                        0.1,
                        -yaw.cos() * v.camera_distance,
                    ),
            )
            .looking_at(v.camera_target, Vec3::Y);
        }
    }
    Ok(())
}
fn source_ids(world: &World, v: &Viewer, index: usize) -> Result<Vec<u16>, String> {
    let (verts, mesh) = &v.source_handles[index];
    let verts = world
        .resource::<Assets<ObjVertsAsset>>()
        .get(verts)
        .ok_or("source verts absent")?;
    let mesh = world
        .resource::<Assets<Mesh>>()
        .get(mesh)
        .ok_or("source mesh absent")?;
    Ok(generate_mhid_lookup(&generate_vertex_map(
        &verts.vertices,
        &get_vertex_positions(mesh),
    )))
}
fn configure_skin_attributes(mesh: &mut Mesh, gpu_four: bool) {
    if !gpu_four {
        mesh.remove_attribute(Mesh::ATTRIBUTE_JOINT_INDEX);
        mesh.remove_attribute(Mesh::ATTRIBUTE_JOINT_WEIGHT);
    }
}
fn body_visible_indices(
    indices: &Indices,
    source_ids: &[u16],
    raw_delete: &[u16],
) -> Result<(Indices, Value), String> {
    let values: Vec<usize> = indices.iter().collect();
    if values.len() % 6 != 0 {
        return Err("approved body must retain original quad fan indices".into());
    }
    let covered: BTreeSet<u16> = raw_delete.iter().copied().collect();
    let mut displayed = Vec::new();
    let mut helper_quads = 0;
    let mut covered_quads = 0;
    for q in values.chunks_exact(6) {
        if q[0] != q[3] || q[2] != q[4] {
            return Err("approved body quad fan ordering changed".into());
        }
        let mut ids = [0u16; 4];
        for (slot, index) in [q[0], q[1], q[2], q[5]].into_iter().enumerate() {
            ids[slot] = *source_ids.get(index).ok_or("body source ID absent")?;
        }
        if ids.iter().any(|id| *id >= 13380) {
            helper_quads += 1;
            continue;
        }
        // Bounded asset-data visibility: retain every mixed boundary quad.
        if ids.iter().all(|id| covered.contains(id)) {
            covered_quads += 1;
            continue;
        }
        displayed.extend(q.iter().map(|index| *index as u32));
    }
    let metadata = json!({"rule":"actual garment MhcloAsset.delete_verts; omit original quad only when all four source IDs are covered; mixed boundary quads retained","raw_delete_source_ids":covered.len(),"source_quads":values.len()/6,"helper_quads_omitted":helper_quads,"covered_body_quads_omitted":covered_quads,"displayed_indices":displayed.len(),"full_numerical_cage_preserved":true});
    Ok((Indices::U32(displayed), metadata))
}
fn attach_render_meshes(world: &mut World, v: &mut Viewer) -> Result<(), String> {
    // Keep full candidate geometry for frame inspection. Display omits MakeHuman's
    // helper/joint faces by source ID; positions/weights of visible cage are unchanged.
    for (index, (name, child, part, mesh)) in v.parts.iter().enumerate() {
        let built = world
            .resource::<Assets<Mesh>>()
            .get(mesh)
            .ok_or("built mesh absent")?;
        let morph = built.morph_targets().ok_or("morph absent")?;
        let p = get_vertex_positions(built);
        let n: Vec<Vec3> = match built.attribute(Mesh::ATTRIBUTE_NORMAL) {
            Some(VertexAttributeValues::Float32x3(values)) => {
                values.iter().map(|n| Vec3::from_array(*n)).collect()
            }
            _ => return Err("normals absent".into()),
        };
        let mut display = Mesh::new(
            bevy::mesh::PrimitiveTopology::TriangleList,
            RenderAssetUsages::default(),
        );
        for (attr, values) in built.attributes() {
            display.insert_attribute(attr.clone(), values.clone());
        }
        display.insert_attribute(
            Mesh::ATTRIBUTE_POSITION,
            p.iter()
                .zip(morph)
                .map(|(p, m)| (*p + m.position).to_array())
                .collect::<Vec<_>>(),
        );
        display.insert_attribute(
            Mesh::ATTRIBUTE_NORMAL,
            n.iter()
                .zip(morph)
                .map(|(n, m)| (*n + m.normal).normalize_or_zero().to_array())
                .collect::<Vec<_>>(),
        );
        if let Some(VertexAttributeValues::Float32x4(t)) = built.attribute(Mesh::ATTRIBUTE_TANGENT)
        {
            display.insert_attribute(
                Mesh::ATTRIBUTE_TANGENT,
                t.iter()
                    .zip(morph)
                    .map(|(t, m)| {
                        let x = (Vec3::new(t[0], t[1], t[2]) + m.tangent).normalize_or_zero();
                        [x.x, x.y, x.z, t[3]]
                    })
                    .collect::<Vec<_>>(),
            );
        }
        let indices = built.indices().ok_or("indices absent")?;
        if name == "body" {
            let ids = source_ids(world, v, index)?;
            let garment = world
                .resource::<Assets<MhcloAsset>>()
                .get(&v.parts[1].2)
                .ok_or("approved garment mapping absent")?;
            let (visible, mut metadata) =
                body_visible_indices(indices, &ids, &garment.delete_verts)?;
            metadata["garment_source_path"] = json!("garment/female_sportsuit01.mhclo");
            metadata["garment_source_sha256"] = serde_json::from_str::<Value>(BUILD_IDENTITY)
                .unwrap()["input_identity"]["asset_files"]["garment/female_sportsuit01.mhclo"]
                .clone();
            v.visibility_mask = metadata;
            display.insert_indices(visible);
        } else {
            display.insert_indices(indices.clone());
        }
        configure_skin_attributes(&mut display, v.state.backend == "gpu4");
        let _ = part;
        let display_handle = world.resource_mut::<Assets<Mesh>>().add(display);
        let material = world
            .resource_mut::<Assets<StandardMaterial>>()
            .add(StandardMaterial {
                base_color: if name == "body" {
                    Color::srgb(0.63, 0.39, 0.28)
                } else {
                    Color::srgb(0.12, 0.35, 0.61)
                },
                perceptual_roughness: 0.72,
                cull_mode: None,
                ..default()
            });
        let skin = world
            .get::<SkinnedMesh>(*child)
            .ok_or("actual part skin absent")?
            .clone();
        let display_entity = world
            .spawn((
                Mesh3d(display_handle),
                MeshMaterial3d(material),
                bevy::camera::visibility::NoFrustumCulling,
                Transform::default(),
                GlobalTransform::default(),
            ))
            .id();
        if v.state.backend == "gpu4" {
            world.entity_mut(display_entity).insert(skin);
            world
                .entity_mut(v.character.unwrap())
                .add_child(display_entity);
        } else {
            let skeleton = world
                .get::<CharacterSkeleton>(v.character.unwrap())
                .ok_or("skeleton absent")?;
            let root = world
                .get::<GlobalTransform>(skeleton.skeleton_entity)
                .ok_or("display root absent")?
                .to_matrix();
            // CPU display is a world root: apply the actual skeleton's global
            // display matrix exactly once. No skin component or morph stream.
            world
                .entity_mut(display_entity)
                .insert(Transform::from_matrix(root));
        }
        v.display_entities.push(display_entity);
    }
    v.built_backend = v.state.backend.clone();
    v.rendered = true;
    Ok(())
}
#[cfg(not(target_arch = "wasm32"))]
fn write_report(path: &str, text: &str) -> std::io::Result<()> {
    let temporary = format!("{path}.tmp");
    std::fs::write(&temporary, text)?;
    std::fs::rename(temporary, path)
}
fn refresh_frame_metadata(v: &mut Viewer) {
    if v.phase != 4 || v.frame.is_null() {
        return;
    }
    let current = serde_json::to_value(&v.state).unwrap();
    if v.frame["state"] == current {
        return;
    }
    if ["recipe", "pose", "backend"]
        .iter()
        .all(|key| v.frame["state"][*key] == current[*key])
    {
        // Camera-only changes preserve the actual skin result and sequence.
        // Both outer state and embedded frame state publish in one report.
        v.frame["state"] = current;
    } else {
        v.frame = Value::Null;
        v.phase = 3;
        v.status = "Selected change pending actual B1 update".into();
    }
}
fn publish(world: &mut World) {
    let mut v = world.remove_resource::<Viewer>().unwrap();
    if v.phase == 3 {
        let result = (|| {
            let mut parts = BTreeMap::new();
            for (index, (name, _, _, handle)) in v.parts.iter().enumerate() {
                let mesh = world
                    .resource::<Assets<Mesh>>()
                    .get(handle)
                    .ok_or("selected mesh absent")?;
                let ids = source_ids(world, &v, index)?;
                let selected = if v.state.backend == "full-weight-cpu" {
                    let mhclo = world
                        .resource::<Assets<MhcloAsset>>()
                        .get(&v.parts[index].2)
                        .ok_or("actual proxy mapping absent")?;
                    skin_mesh_frame_full_weights(world, v.character.unwrap(), mesh, mhclo, &ids)?
                } else {
                    skin_mesh_frame_canonical(world, v.character.unwrap(), mesh)?
                };
                let mut frame = serde_json::to_value(selected).map_err(|e| e.to_string())?;
                frame["source_vertex_ids"] = json!(ids);
                parts.insert(name.clone(), frame);
            }
            Ok::<_, String>(parts)
        })();
        match result {
            Ok(parts) => {
                let skeleton = world
                    .get::<CharacterSkeleton>(v.character.unwrap())
                    .unwrap();
                let display_root = world
                    .get::<GlobalTransform>(skeleton.skeleton_entity)
                    .unwrap()
                    .to_matrix();
                if !v.headless && v.state.backend == "full-weight-cpu" {
                    for (index, (name, _, _, _)) in v.parts.iter().enumerate() {
                        let part = &parts[name];
                        let positions: Vec<[f32; 3]> =
                            serde_json::from_value(part["positions"].clone()).unwrap();
                        let normals: Vec<[f32; 3]> =
                            serde_json::from_value(part["normals"].clone()).unwrap();
                        let tangents: Vec<[f32; 4]> =
                            serde_json::from_value(part["tangents"].clone()).unwrap();
                        world
                            .entity_mut(v.display_entities[index])
                            .insert(Transform::from_matrix(display_root));
                        let display_handle = world
                            .get::<Mesh3d>(v.display_entities[index])
                            .unwrap()
                            .0
                            .clone();
                        let mut meshes = world.resource_mut::<Assets<Mesh>>();
                        let mut mesh = meshes.get_mut(&display_handle).unwrap();
                        mesh.insert_attribute(Mesh::ATTRIBUTE_POSITION, positions);
                        mesh.insert_attribute(Mesh::ATTRIBUTE_NORMAL, normals);
                        mesh.insert_attribute(Mesh::ATTRIBUTE_TANGENT, tangents);
                        drop(mesh);
                        drop(meshes);
                        assert!(
                            world
                                .get::<SkinnedMesh>(v.display_entities[index])
                                .is_none(),
                            "CPU display must not skin twice"
                        );
                    }
                }
                let mut low = Vec3::splat(f32::INFINITY);
                let mut high = Vec3::splat(f32::NEG_INFINITY);
                for (name, part) in &parts {
                    let ids = part["source_vertex_ids"].as_array().unwrap();
                    for (i, p) in part["positions"].as_array().unwrap().iter().enumerate() {
                        if name == "body" && ids[i].as_u64().unwrap() >= 13380 {
                            continue;
                        }
                        let p = display_root.transform_point3(Vec3::new(
                            p[0].as_f64().unwrap() as f32,
                            p[1].as_f64().unwrap() as f32,
                            p[2].as_f64().unwrap() as f32,
                        ));
                        low = low.min(p);
                        high = high.max(p);
                    }
                }
                v.camera_target = (low + high) * 0.5;
                v.camera_distance = ((high - low).length() * 1.6).max(3.0);
                let bounds = json!({"world_min":low.to_array(),"world_max":high.to_array(),"orbit_target":v.camera_target.to_array(),"orbit_distance":v.camera_distance});
                let bindings:Vec<Value>=v.display_entities.iter().map(|entity|{
                    let handle=&world.get::<Mesh3d>(*entity).unwrap().0;
                    let mesh=world.resource::<Assets<Mesh>>().get(handle).unwrap();
                    json!({"skinned_mesh_component":world.get::<SkinnedMesh>(*entity).is_some(),"morph_stream_present":mesh.morph_targets().is_some(),"joint_index_attribute":mesh.attribute(Mesh::ATTRIBUTE_JOINT_INDEX).is_some(),"joint_weight_attribute":mesh.attribute(Mesh::ATTRIBUTE_JOINT_WEIGHT).is_some(),"vertices":mesh.count_vertices(),"indices":mesh.indices().map(|i|i.len()),"display_transform":world.get::<Transform>(*entity).unwrap().to_matrix().to_cols_array()})
                }).collect();
                v.output_sequence += 1;
                v.frame = json!({"schema_version":1,"build_identity":serde_json::from_str::<Value>(BUILD_IDENTITY).unwrap(),"common_manifest_sha256":COMMON,"source":"57-b1-pose-runtime/derived","actual_candidate_code_executed":true,"actual_explicit_loader":true,"renderer_backend":v.state.backend,"actual_display_bindings":bindings,"display_visibility_mask":v.visibility_mask,"actual_character_bounds":bounds,"actual_skeleton_display_root":display_root.to_cols_array(),"quality_status":if v.state.backend=="gpu4"{"HOLD: four-influence quality gate fails"}else{"source-derived positive-influence CPU; no four-cap; product admission undecided"},"readback_kind":"original CPU LBS adapter over actual candidate ECS and mesh; canonical frame gauge is source-derived; not GPU vertex readback","gpu_vertex_readback":false,"state":v.state,"sequence":v.output_sequence,"space":"MakeHuman Y-up metres, column-major matrices; display root transform cancelled","parts":parts});
                v.status = if v.state.backend == "gpu4" {
                    "READY · GPU4 frame; quality HOLD".into()
                } else {
                    "READY · positive-influence CPU; no four-cap".into()
                };
                v.phase = 4;
            }
            Err(e) => {
                v.fail(e);
            }
        }
    }
    refresh_frame_metadata(&mut v);
    #[cfg(not(target_arch = "wasm32"))]
    {
        let key = format!(
            "{:?}|{}|{}|{}|{}|{}",
            v.state, v.status, v.error, v.phase, v.output_sequence, v.rejected_commands
        );
        if key != v.last_report {
            if let Some(path) = &v.frame_file {
                let report = json!({"state":v.state,"status":v.status,"error":v.error,"phase":v.phase,"frame":v.frame,"graphical_path_attached":v.rendered,"fatal_reload_required":v.phase==255,"rejected_commands":v.rejected_commands});
                if let Err(e) = write_report(path, &report.to_string()) {
                    v.recoverable_error(e.to_string());
                }
            }
            v.last_report = key;
        }
    }
    #[cfg(target_arch = "wasm32")]
    if let Some(w) = web_sys::window() {
        let key = format!(
            "{:?}|{}|{}|{}|{}|{}|{}",
            v.state, v.status, v.error, v.phase, v.output_sequence, v.rendered, v.rejected_commands
        );
        if key != v.last_report {
            let report = json!({"state":v.state,"status":v.status,"error":v.error,"phase":v.phase,"frame":v.frame,"graphical_path_attached":v.rendered,"fatal_reload_required":v.phase==255,"rejected_commands":v.rejected_commands});
            let _ = js_sys::Reflect::set(&w, &"__b1report".into(), &report.to_string().into());
            v.last_report = key;
        }
    }
    world.insert_resource(v);
}
fn ui(mut contexts: EguiContexts, mut v: ResMut<Viewer>) -> Result {
    let ctx = contexts.ctx_mut()?;
    let mut root_ui = egui::Ui::new(
        ctx.clone(),
        "b1-viewport".into(),
        egui::UiBuilder::new()
            .layer_id(egui::LayerId::background())
            .max_rect(ctx.viewport_rect()),
    );
    egui::Panel::left("b1-controls")
        .default_size(340.0)
        .show(&mut root_ui, |ui| {
            ui.heading("B1 Pose Lab");
            ui.label("Isolated source runtime · native + Web");
            if v.phase == 255 {
                ui.colored_label(egui::Color32::LIGHT_RED, &v.error);
                ui.label("Reload required. State and frame are frozen.");
                ui.disable();
            }
            ui.separator();
            let mut next = v.state.clone();
            egui::ComboBox::from_label("Body recipe")
                .selected_text(&next.recipe)
                .show_ui(ui, |ui| {
                    for s in RECIPES {
                        ui.selectable_value(&mut next.recipe, s.into(), s);
                    }
                });
            egui::ComboBox::from_label("Renderer")
                .selected_text(&next.backend)
                .show_ui(ui, |ui| {
                    ui.selectable_value(&mut next.backend, "gpu4".into(), "GPU4 · quality HOLD");
                    ui.selectable_value(
                        &mut next.backend,
                        "full-weight-cpu".into(),
                        "Positive CPU · no four-cap",
                    );
                });
            egui::ComboBox::from_label("Diagnostic pose")
                .selected_text(&next.pose)
                .show_ui(ui, |ui| {
                    for s in POSES {
                        ui.selectable_value(&mut next.pose, s.into(), s);
                    }
                });
            ui.add(egui::Slider::new(&mut next.camera_yaw, -180.0..=180.0).text("Camera yaw"));
            if v.phase != 255 {
                v.state = next;
            }
            ui.separator();
            ui.label(&v.status);
            if !v.error.is_empty() {
                ui.colored_label(egui::Color32::LIGHT_RED, &v.error);
            }
            ui.separator();
            ui.label("Prototype state JSON — distinct from production Work");
            ui.horizontal(|ui| {
                if ui.button("Export state").clicked() {
                    v.exchange = serde_json::to_string_pretty(&v.state).unwrap();
                }
                if ui.button("Import state").clicked() {
                    let text = v.exchange.clone();
                    import_state(&mut v, &text);
                }
            });
            ui.add(
                egui::TextEdit::multiline(&mut v.exchange)
                    .desired_rows(9)
                    .desired_width(f32::INFINITY),
            );
            if ui.button("Inspect selected frame").clicked() {
                v.inspect = !v.inspect;
            }
            if v.inspect && !v.frame.is_null() {
                egui::ComboBox::from_label("Inspect part")
                    .selected_text(&v.inspect_part)
                    .show_ui(ui, |ui| {
                        for part in ["body", "garment"] {
                            ui.selectable_value(&mut v.inspect_part, part.into(), part);
                        }
                    });
                let count = v.frame["parts"][&v.inspect_part]["positions"]
                    .as_array()
                    .map_or(1, Vec::len);
                ui.horizontal(|ui| {
                    ui.label("Vertex");
                    ui.add(egui::DragValue::new(&mut v.inspect_vertex).range(0..=count - 1));
                    ui.label("Bone");
                    ui.add(egui::DragValue::new(&mut v.inspect_bone).range(0..=52));
                });
                let part = &v.frame["parts"][&v.inspect_part];
                let bone = &part["bones"][v.inspect_bone];
                ui.label(format!(
                    "Source vertex {}",
                    part["source_vertex_ids"][v.inspect_vertex]
                ));
                ui.monospace(format!("Skinned {}", part["positions"][v.inspect_vertex]));
                ui.label(format!("Bone {}", bone["name"]));
                for key in ["rest", "posed"] {
                    ui.label(key);
                    if let Some(matrix) = bone[key].as_array() {
                        for row in 0..4 {
                            ui.monospace(
                                (0..4)
                                    .map(|col| {
                                        format!(
                                            "{:.5}",
                                            matrix[col * 4 + row].as_f64().unwrap_or(0.0)
                                        )
                                    })
                                    .collect::<Vec<_>>()
                                    .join(" "),
                            );
                        }
                    }
                }
            }
            #[cfg(not(target_arch = "wasm32"))]
            if ui.button("Write selected-frame.json").clicked() {
                let result = std::fs::write(
                    concat!(
                        env!("CARGO_MANIFEST_DIR"),
                        "/../../.work/b1-pose-viewer/selected-frame.json"
                    ),
                    serde_json::to_vec_pretty(&v.frame).unwrap(),
                );
                if let Err(e) = result {
                    v.recoverable_error(e.to_string());
                }
            }
            #[cfg(target_arch = "wasm32")]
            ui.label("Browser: b1.download('frame') or b1.download('state')");
            if let Some(parts) = v.frame.get("parts").and_then(Value::as_object) {
                for (name, p) in parts {
                    ui.label(format!(
                        "{name}: {} vertices, {} bones",
                        p["positions"].as_array().map_or(0, Vec::len),
                        p["bones"].as_array().map_or(0, Vec::len)
                    ));
                }
            }
        });
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn state_round_trip_and_invalid_import_preserves_active_selection() {
        let mut v = Viewer::new();
        command(
            &mut v,
            r#"{"action":"select","recipe":"body-half","pose":"combined"}"#,
        );
        assert!(v.error.is_empty());
        let accepted = v.state.clone();
        let text = serde_json::to_string(&accepted).unwrap();
        assert_eq!(PrototypeState::parse(&text).unwrap(), accepted);
        command(
            &mut v,
            r#"{"action":"import","state":{"format":"nvwa-b1-pose-prototype","schema_version":1,"recipe":"INVALID","pose":"neutral","camera_yaw":0}}"#,
        );
        assert!(!v.error.is_empty());
        assert_eq!(v.state, accepted);
        command(&mut v, r#"{"action":"select","pose":"INVALID"}"#);
        assert_eq!(v.state, accepted);
        assert!(PrototypeState::parse(r#"{"format":"nvwa-work","schema_version":1,"recipe":"neutral","pose":"neutral","camera_yaw":0}"#).is_err());
    }
    #[test]
    fn production_import_rejects_invalid_fields_without_losing_frame_or_state() {
        let mut viewer = Viewer::new();
        command(
            &mut viewer,
            r#"{"action":"select","recipe":"combined","pose":"knee","backend":"full-weight-cpu","camera_yaw":25}"#,
        );
        let accepted = viewer.state.clone();
        viewer.frame = json!({"actual_selected_frame":"retained"});
        let frame = viewer.frame.clone();
        for (key, bad) in [
            ("recipe", json!("INVALID")),
            ("pose", json!("INVALID")),
            ("backend", json!("INVALID")),
            ("format", json!("nvwa-work")),
            ("schema_version", json!(2)),
            ("camera_yaw", json!(181.0)),
            ("camera_yaw", json!(-181.0)),
            ("camera_yaw", json!("NaN")),
            ("unknown_field", json!(true)),
        ] {
            let mut state = serde_json::to_value(&accepted).unwrap();
            state[key] = bad;
            command(
                &mut viewer,
                &json!({"action":"import","state":state}).to_string(),
            );
            assert!(!viewer.error.is_empty(), "accepted invalid {key}");
            assert_eq!(viewer.state, accepted, "changed state on invalid {key}");
            assert_eq!(viewer.frame, frame, "lost active frame on invalid {key}");
        }
        for raw in ["NaN", "Infinity", "1e999"] {
            let text = format!(
                r#"{{"action":"import","state":{{"format":"nvwa-b1-pose-prototype","schema_version":1,"recipe":"neutral","pose":"neutral","camera_yaw":{raw}}}}}"#
            );
            command(&mut viewer, &text);
            assert!(!viewer.error.is_empty());
            assert_eq!(viewer.state, accepted);
            assert_eq!(viewer.frame, frame);
        }
    }
    #[test]
    fn production_import_defaults_earlier_backend_and_restores_explicit_backend() {
        let mut viewer = Viewer::new();
        let mut state = serde_json::to_value(PrototypeState {
            backend: "full-weight-cpu".into(),
            recipe: "body-positive".into(),
            pose: "elbow".into(),
            ..default()
        })
        .unwrap();
        command(
            &mut viewer,
            &json!({"action":"import","state":state}).to_string(),
        );
        assert!(viewer.error.is_empty());
        assert_eq!(viewer.state.backend, "full-weight-cpu");
        state.as_object_mut().unwrap().remove("backend");
        command(
            &mut viewer,
            &json!({"action":"import","state":state}).to_string(),
        );
        assert!(viewer.error.is_empty());
        assert_eq!(viewer.state.backend, "gpu4");
        assert_eq!(viewer.state.recipe, "body-positive");
        assert_eq!(viewer.state.pose, "elbow");
    }
    #[test]
    fn fatal_failure_freezes_first_error_state_and_frame_across_all_import_routes() {
        for retained_frame in [Value::Null, json!({"actual_selected_frame":"retained"})] {
            for first_error in [
                "Explicit target missing: chin-jaw-drop-incr",
                "Asset failed: target: Failed to fetch",
            ] {
                let mut viewer = Viewer::new();
                command(
                    &mut viewer,
                    r#"{"action":"select","recipe":"combined","pose":"elbow","backend":"full-weight-cpu","camera_yaw":25}"#,
                );
                let state = viewer.state.clone();
                viewer.frame = retained_frame.clone();
                viewer.fail(first_error.into());
                let status = viewer.status.clone();
                for input in [
                    json!({"action":"import","state":PrototypeState::default()}).to_string(),
                    r#"{"action":"select","camera_yaw":-40}"#.into(),
                    r#"{"action":"select","recipe":"neutral","pose":"knee","backend":"gpu4"}"#
                        .into(),
                    r#"{"action":"export"}"#.into(),
                    "not JSON".into(),
                ] {
                    command(&mut viewer, &input);
                    refresh_frame_metadata(&mut viewer);
                    assert_eq!(viewer.state, state);
                    assert_eq!(viewer.frame, retained_frame);
                    assert_eq!(viewer.error, first_error);
                    assert_eq!(viewer.status, status);
                    assert_eq!(viewer.phase, 255);
                }
                assert_eq!(viewer.rejected_commands, 5);
                // Native Import state calls this same production seam.
                import_state(
                    &mut viewer,
                    &serde_json::to_string(&PrototypeState::default()).unwrap(),
                );
                viewer.recoverable_error("later command-file/write error".into());
                viewer.fail("later asset failure".into());
                assert_eq!(viewer.state, state);
                assert_eq!(viewer.frame, retained_frame);
                assert_eq!(viewer.error, first_error);
            }
        }
    }
    #[test]
    fn native_import_seam_recovers_nonfatal_error_without_losing_character() {
        let mut viewer = Viewer::new();
        viewer.phase = 4;
        viewer.frame = json!({"actual_selected_frame":"retained"});
        let frame = viewer.frame.clone();
        import_state(&mut viewer, "invalid JSON");
        assert!(!viewer.error.is_empty());
        assert_eq!(viewer.frame, frame);
        let next = PrototypeState {
            camera_yaw: 25.,
            ..default()
        };
        import_state(&mut viewer, &serde_json::to_string(&next).unwrap());
        assert!(viewer.error.is_empty());
        assert_eq!(viewer.state, next);
        assert_eq!(viewer.frame, frame);
        assert_eq!(viewer.phase, 4);
    }
    #[test]
    fn actual_display_configuration_removes_cpu_skin_shader_attributes() {
        let mut mesh = Mesh::new(
            bevy::mesh::PrimitiveTopology::TriangleList,
            RenderAssetUsages::default(),
        );
        mesh.insert_attribute(
            Mesh::ATTRIBUTE_JOINT_INDEX,
            VertexAttributeValues::Uint16x4(vec![[0, 1, 2, 3]]),
        );
        mesh.insert_attribute(Mesh::ATTRIBUTE_JOINT_WEIGHT, vec![[0.25f32; 4]]);
        configure_skin_attributes(&mut mesh, true);
        assert!(mesh.attribute(Mesh::ATTRIBUTE_JOINT_INDEX).is_some());
        assert!(mesh.attribute(Mesh::ATTRIBUTE_JOINT_WEIGHT).is_some());
        configure_skin_attributes(&mut mesh, false);
        assert!(mesh.attribute(Mesh::ATTRIBUTE_JOINT_INDEX).is_none());
        assert!(mesh.attribute(Mesh::ATTRIBUTE_JOINT_WEIGHT).is_none());
        assert!(mesh.morph_targets().is_none());
    }
    #[test]
    fn actual_garment_mask_retains_mixed_quad_boundary_and_numeric_source() {
        let indices = Indices::U32(vec![
            0, 1, 2, 0, 2, 3, 4, 5, 6, 4, 6, 7, 8, 9, 10, 8, 10, 11,
        ]);
        let ids = vec![0, 1, 2, 3, 4, 5, 6, 7, 13380, 13381, 13382, 13383];
        let original = ids.clone();
        let (filtered, metadata) =
            body_visible_indices(&indices, &ids, &[0, 1, 2, 3, 4, 5]).unwrap();
        assert_eq!(filtered.iter().collect::<Vec<_>>(), vec![4, 5, 6, 4, 6, 7]);
        assert_eq!(ids, original);
        assert_eq!(metadata["raw_delete_source_ids"], 6);
        assert_eq!(metadata["covered_body_quads_omitted"], 1);
        assert_eq!(metadata["helper_quads_omitted"], 1);
    }
    #[test]
    fn actual_report_camera_metadata_changes_without_skin_rerun() {
        let mut viewer = Viewer::new();
        viewer.phase = 4;
        let original_state = serde_json::to_value(&viewer.state).unwrap();
        viewer.frame =
            json!({"state":original_state,"sequence":7,"parts":{"actual_skin":"preserved"}});
        viewer.output_sequence = 7;
        command(&mut viewer, r#"{"action":"select","camera_yaw":25}"#);
        refresh_frame_metadata(&mut viewer);
        assert_eq!(
            viewer.frame["state"],
            serde_json::to_value(&viewer.state).unwrap()
        );
        assert_eq!(viewer.frame["state"]["camera_yaw"], 25.0);
        assert_eq!(viewer.frame["sequence"], 7);
        assert_eq!(viewer.output_sequence, 7);
        assert_eq!(viewer.frame["parts"], json!({"actual_skin":"preserved"}));
        command(&mut viewer, r#"{"action":"select","pose":"elbow"}"#);
        refresh_frame_metadata(&mut viewer);
        assert!(viewer.frame.is_null());
        assert_ne!(viewer.phase, 4);
    }
}
