//! Shared native/Web renderer. The editor document is the source of truth.
use std::collections::{BTreeMap, BTreeSet};

use bevy::{
    app::AnimationSystems,
    asset::{
        AssetLoadFailedEvent, AssetLoader, LoadContext, LoadState, RecursiveDependencyLoadState,
        io::Reader,
    },
    ecs::system::SystemParam,
    math::bounding::{BoundingSphere, RayCast3d},
    mesh::{morph::MorphWeights, skinning::SkinnedMesh},
    prelude::*,
    world_serialization::WorldInstanceReady,
};
use nvwa_core::{CharacterProfile, Command, CommandEnvelope, Editor, SceneDocument, TimelineClip};

/// Launch-only policy; a requested work must never silently show the fixture.
#[derive(Resource, Default, Clone, Copy)]
pub enum StartupDocumentPolicy {
    #[default]
    DefaultFixture,
    WaitForOpen,
}

#[derive(Resource, Default)]
pub struct EditorState {
    pub editor: Option<Editor>,
    /// A validated clone used during a drag. Never mutates editor history.
    pub preview: Option<SceneDocument>,
    pub message: String,
    command_sequence: u64,
    document_generation: u64,
}
impl EditorState {
    pub fn document(&self) -> Option<&SceneDocument> {
        self.editor.as_ref().map(Editor::document)
    }
    pub fn visible_document(&self) -> Option<&SceneDocument> {
        self.preview.as_ref().or_else(|| self.document())
    }
    pub fn replace(&mut self, document: SceneDocument) -> Result<(), String> {
        self.editor = Some(Editor::new(document).map_err(|e| e.to_string())?);
        self.preview = None;
        self.document_generation = self.document_generation.saturating_add(1);
        self.message = "Document opened".into();
        Ok(())
    }
    pub fn apply(&mut self, command: Command) -> Result<(), String> {
        self.preview = None;
        let editor = self.editor.as_mut().ok_or("No document is open")?;
        self.command_sequence += 1;
        let result = editor
            .apply(CommandEnvelope {
                command_id: format!("studio-{}", self.command_sequence),
                expected_revision: editor.document().revision,
                command,
            })
            .map_err(|e| e.to_string())?;
        self.message = result.summary;
        Ok(())
    }
    pub fn preview_parameters(&mut self, values: BTreeMap<String, f32>) -> Result<(), String> {
        let mut preview = self.document().ok_or("No document is open")?.clone();
        preview.character.parameters = values;
        preview.validate().map_err(|e| e.to_string())?;
        self.preview = Some(preview);
        Ok(())
    }
    pub fn commit_preview(&mut self) -> Result<(), String> {
        if let Some(preview) = self.preview.take() {
            self.apply(Command::SetParameters {
                character_id: preview.character.id,
                values: preview.character.parameters,
            })?;
        }
        Ok(())
    }
}

#[derive(Resource, Default, Debug)]
pub struct RuntimeStatus {
    pub phase: String,
    pub error: Option<String>,
    pub ready: bool,
    pub meshes: usize,
    pub skins: usize,
    pub joints: usize,
    pub morph_nodes: usize,
    pub morph_weights: usize,
    pub players: usize,
    pub active_animations: usize,
    pub paused_animations: usize,
    pub frames: u64,
    pub frame_times_ms: Vec<f32>,
    pub first_ready_seconds: Option<f64>,
    pub ready_frames: u64,
    pub warmed_frame_times_ms: Vec<f32>,
}
#[derive(Resource, Default, Clone)]
pub struct Playback {
    /// Actual sampled authored action, including a held action in a gap.
    pub clip_id: String,
    pub playing: bool,
    pub position_seconds: f32,
    pub seek_request: Option<f32>,
    pub active_timeline_id: String,
    pub completed: bool,
    pub error: Option<String>,
}
/// The one scene camera, shared by Studio and the editor-free Player.
#[derive(Component)]
pub struct SceneCamera;

#[derive(Clone, Copy, PartialEq, Eq)]
struct InteractionScope {
    generation: u64,
    revision: u64,
}
struct ActiveInteraction {
    scope: InteractionScope,
    prior: Playback,
    node: AnimationNodeIndex,
    players: Vec<Entity>,
}
/// Temporary authored interaction. Never serialized or applied as an edit.
#[derive(Resource, Default)]
pub struct CharacterInteraction {
    requested: Option<InteractionScope>,
    active: Option<ActiveInteraction>,
}
impl CharacterInteraction {
    /// Includes a click awaiting the next animation-control pass.
    pub fn busy(&self) -> bool {
        self.requested.is_some() || self.active.is_some()
    }
}

/// Real ray input for the original fixture's conservative chest/head hotspots.
/// It intentionally does not claim full deformed-mesh silhouette picking.
#[derive(SystemParam)]
pub struct CharacterInteractionInput<'w, 's> {
    editor: Res<'w, EditorState>,
    asset: Res<'w, CharacterAsset>,
    status: Res<'w, RuntimeStatus>,
    joints: Query<'w, 's, (&'static Name, &'static GlobalTransform), With<CharacterPart>>,
    interaction: ResMut<'w, CharacterInteraction>,
}
impl CharacterInteractionInput<'_, '_> {
    /// A caller must first reject editor-owned input and unfocused windows.
    /// Repeated hits while pending/active are ignored, never queued.
    pub fn click(&mut self, ray: Ray3d) -> bool {
        let Some(document) = self.editor.document() else {
            return false;
        };
        if self.interaction.busy()
            || !self.status.ready
            || !self.asset.verified
            || !self.asset.scene_ready
            || self.asset.document_generation != self.editor.document_generation
            || document.timeline.is_empty()
            || document.profile.id != "nvwa-original-humanoid-v1"
            || document.profile.asset_sha256
                != "f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6"
            || !self.asset.nodes.contains_key("wave")
        {
            return false;
        }
        let hit = self.joints.iter().any(|(name, transform)| {
            let (center, radii) = match name.as_str() {
                "chest" => (Vec3::new(0.0, 0.03, 0.0), Vec3::new(0.17, 0.18, 0.10)),
                "head" => (Vec3::new(0.0, 0.17, 0.015), Vec3::new(0.11, 0.15, 0.09)),
                _ => return false,
            };
            hotspot_hit(ray, transform, center, radii)
        });
        if hit {
            self.interaction.requested = Some(InteractionScope {
                generation: self.editor.document_generation,
                revision: document.revision,
            });
        }
        hit
    }
}

fn hotspot_hit(ray: Ray3d, joint: &GlobalTransform, center: Vec3, radii: Vec3) -> bool {
    if !ray.origin.is_finite() || !radii.is_finite() || radii.min_element() <= 0.0 {
        return false;
    }
    let world_from_sphere = joint.affine()
        * bevy::math::Affine3A::from_scale_rotation_translation(radii, Quat::IDENTITY, center);
    let determinant = world_from_sphere.matrix3.determinant();
    if !determinant.is_finite() || determinant == 0.0 {
        return false;
    }
    let sphere_from_world = world_from_sphere.inverse();
    if !sphere_from_world.is_finite() {
        return false;
    }
    let origin = sphere_from_world.transform_point3(ray.origin);
    let direction = sphere_from_world.transform_vector3(*ray.direction);
    let length = direction.length();
    let Ok(direction) = Dir3::new(direction) else {
        return false;
    };
    let max_distance = 100.0 * length;
    if !origin.is_finite() || !max_distance.is_finite() {
        return false;
    }
    RayCast3d::from_ray(Ray3d::new(origin, direction), max_distance)
        .sphere_intersection_at(&BoundingSphere::new(Vec3::ZERO, 1.0))
        .is_some()
}
#[derive(Component)]
struct CharacterRoot;
#[derive(Component)]
struct CharacterPart;
#[derive(Resource, Default)]
struct CharacterAsset {
    path: String,
    profile_key: String,
    document_generation: u64,
    bytes: Option<Handle<GlbBytes>>,
    verified: bool,
    fresh_bytes: bool,
    fresh_gltf: bool,
    gltf_failure: Option<String>,
    handle: Option<Handle<Gltf>>,
    root: Option<Entity>,
    graph: Option<Handle<AnimationGraph>>,
    nodes: BTreeMap<String, AnimationNodeIndex>,
    spawned: bool,
    scene_ready: bool,
    elapsed: f32,
    applied_clip: String,
    applied_playing: bool,
    applied_timeline: Vec<TimelineClip>,
    playback_generation: u64,
}

#[derive(Asset, TypePath)]
struct GlbBytes(Vec<u8>);
#[derive(Default, TypePath)]
struct GlbBytesLoader;
impl AssetLoader for GlbBytesLoader {
    type Asset = GlbBytes;
    type Settings = ();
    type Error = std::io::Error;
    async fn load(
        &self,
        reader: &mut dyn Reader,
        _: &(),
        _: &mut LoadContext<'_>,
    ) -> Result<GlbBytes, Self::Error> {
        let mut bytes = Vec::new();
        reader.read_to_end(&mut bytes).await?;
        Ok(GlbBytes(bytes))
    }
}

#[derive(SystemSet, Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum RuntimeSystems {
    Transport,
    Mirror,
}

pub struct NvwaRuntimePlugin;
impl Plugin for NvwaRuntimePlugin {
    fn build(&self, app: &mut App) {
        app.init_asset::<GlbBytes>()
            .init_asset_loader::<GlbBytesLoader>()
            .init_resource::<EditorState>()
            .init_resource::<StartupDocumentPolicy>()
            .init_resource::<RuntimeStatus>()
            .init_resource::<Playback>()
            .init_resource::<CharacterAsset>()
            .add_systems(Startup, (open_default_document, setup_environment))
            .add_systems(Update, load_character)
            // Override user morph channels after skeletal animation evaluation.
            // The joints and recipe morphs therefore remain active together.
            .add_systems(
                PostUpdate,
                (apply_recipe, collect_evidence)
                    .chain()
                    .after(AnimationSystems)
                    .in_set(RuntimeSystems::Mirror)
                    .before(bevy::transform::TransformSystems::Propagate),
            );
        add_playback_systems(app);
    }
}

/// Keep production and real-graph CPU regression tests on the same ordering.
fn add_playback_systems(app: &mut App) {
    app.init_resource::<CharacterInteraction>()
        .add_systems(
            PostUpdate,
            (
                begin_character_interaction,
                control_single_loop_before_advance,
            )
                .chain()
                .in_set(RuntimeSystems::Transport)
                .before(bevy::animation::advance_animations),
        )
        .add_systems(
            PostUpdate,
            control_playback
                .after(bevy::animation::advance_animations)
                .before(bevy::animation::animate_targets),
        );
}

fn open_default_document(
    mut editor: ResMut<EditorState>,
    mut status: ResMut<RuntimeStatus>,
    policy: Res<StartupDocumentPolicy>,
) {
    if matches!(*policy, StartupDocumentPolicy::WaitForOpen) {
        status.phase = "Open a work to play".into();
        return;
    }
    let result = serde_json::from_str::<CharacterProfile>(include_str!(
        "../../../assets/character.profile.json"
    ))
    .map_err(|e| e.to_string())
    .and_then(|profile| SceneDocument::from_profile(profile).map_err(|e| e.to_string()))
    .and_then(|document| editor.replace(document));
    if let Err(error) = result {
        status.error = Some(error);
        status.phase = "Profile error".into();
    }
}
fn setup_environment(
    mut commands: Commands,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
) {
    commands.insert_resource(ClearColor(Color::srgb(0.055, 0.07, 0.095)));
    commands.insert_resource(GlobalAmbientLight {
        brightness: 450.0,
        ..default()
    });
    commands.spawn((
        SceneCamera,
        Camera3d::default(),
        bevy::core_pipeline::tonemapping::Tonemapping::Reinhard,
        Transform::from_xyz(3.1, 2.0, 4.8).looking_at(Vec3::new(0.0, 0.95, 0.0), Vec3::Y),
    ));
    commands.spawn((
        DirectionalLight {
            illuminance: 8000.0,
            ..default()
        },
        Transform::from_rotation(Quat::from_euler(EulerRot::XYZ, -0.65, -0.5, 0.0)),
    ));
    commands.spawn((
        Mesh3d(meshes.add(Plane3d::default().mesh().size(200.0, 200.0))),
        MeshMaterial3d(materials.add(Color::srgb(0.1, 0.13, 0.17))),
    ));
}

#[derive(SystemParam)]
struct CharacterLoadAssets<'w, 's> {
    server: Res<'w, AssetServer>,
    gltfs: Res<'w, Assets<Gltf>>,
    raw_assets: Res<'w, Assets<GlbBytes>>,
    clips: Res<'w, Assets<AnimationClip>>,
    graphs: ResMut<'w, Assets<AnimationGraph>>,
    byte_events: MessageReader<'w, 's, AssetEvent<GlbBytes>>,
    byte_failures: MessageReader<'w, 's, AssetLoadFailedEvent<GlbBytes>>,
    gltf_events: MessageReader<'w, 's, AssetEvent<Gltf>>,
    gltf_failures: MessageReader<'w, 's, AssetLoadFailedEvent<Gltf>>,
}

fn load_character(
    mut commands: Commands,
    editor: Res<EditorState>,
    loading: CharacterLoadAssets,
    mut asset: ResMut<CharacterAsset>,
    mut status: ResMut<RuntimeStatus>,
    mut playback: ResMut<Playback>,
    time: Res<Time<Real>>,
) {
    let CharacterLoadAssets {
        server,
        gltfs,
        raw_assets,
        clips,
        mut graphs,
        mut byte_events,
        mut byte_failures,
        mut gltf_events,
        mut gltf_failures,
    } = loading;
    // Drain before issuing a new generation request. Earlier completion events
    // cannot authorize validation of this generation's cached bytes.
    let completed_bytes: Vec<_> = byte_events
        .read()
        .filter_map(|event| match event {
            AssetEvent::Added { id }
            | AssetEvent::Modified { id }
            | AssetEvent::LoadedWithDependencies { id } => Some(*id),
            _ => None,
        })
        .collect();
    let failed_bytes: Vec<_> = byte_failures
        .read()
        .map(|event| (event.id, event.error.to_string()))
        .collect();
    let completed_gltf: Vec<_> = gltf_events
        .read()
        .filter_map(|event| match event {
            AssetEvent::Added { id }
            | AssetEvent::Modified { id }
            | AssetEvent::LoadedWithDependencies { id } => Some(*id),
            _ => None,
        })
        .collect();
    let failed_gltf: Vec<_> = gltf_failures
        .read()
        .map(|event| (event.id, event.error.to_string()))
        .collect();
    let Some(document) = editor.document() else {
        return;
    };
    let path = &document.profile.asset_path;
    let profile_key = serde_json::to_string(&document.profile).unwrap_or_default();
    if asset.path != *path
        || asset.profile_key != profile_key
        || asset.document_generation != editor.document_generation
    {
        if let Some(root) = asset.root {
            commands.entity(root).despawn();
        }
        let reload = asset.handle.is_some();
        *asset = CharacterAsset {
            path: path.clone(),
            profile_key,
            document_generation: editor.document_generation,
            bytes: Some(server.load(path.clone())),
            handle: Some(server.load(path.clone())),
            ..default()
        };
        // `load` can return a cached failed handle. Explicit open must also
        // request a real retry after the user restores the missing file.
        if reload {
            server.reload(path.clone());
        }
        status.ready = false;
        status.first_ready_seconds = None;
        status.ready_frames = 0;
        status.warmed_frame_times_ms.clear();
        status.error = None;
        status.phase = "Loading character…".into();
        playback.clip_id = document
            .timeline
            .first()
            .map(|c| c.clip_id.clone())
            .or_else(|| document.profile.clips.first().map(|c| c.id.clone()))
            .unwrap_or_default();
        playback.playing = true;
        playback.position_seconds = 0.0;
        playback.seek_request = None;
        playback.completed = false;
        playback.active_timeline_id.clear();
        playback.error = None;
        return;
    }
    asset.elapsed += time.delta_secs();
    if let Some(id) = asset.bytes.as_ref().map(Handle::id) {
        if completed_bytes.contains(&id) {
            asset.fresh_bytes = true;
            asset.verified = false;
        }
        if let Some((_, error)) = failed_bytes.iter().find(|(failed_id, _)| *failed_id == id) {
            status.error = Some(format!("Asset byte load failed: {error}"));
            status.ready = false;
            status.phase = "Load error".into();
        }
    }
    if let Some(id) = asset.handle.as_ref().map(Handle::id) {
        if completed_gltf.contains(&id) {
            asset.fresh_gltf = true;
        }
        if let Some((_, error)) = failed_gltf.iter().find(|(failed_id, _)| *failed_id == id) {
            asset.gltf_failure = Some(format!("Character load failed: {error}"));
        }
    }
    if !verify_byte_generation(
        &document.profile,
        &server,
        &raw_assets,
        &mut asset,
        &mut status,
    ) {
        return;
    }
    let Some(handle) = asset.handle.clone() else {
        return;
    };
    // Cached load/dependency failures can belong to the previous request.
    // Only a failure event or a freshly parsed root can authorize this error.
    let loaded = asset.fresh_gltf && server.is_loaded_with_dependencies(handle.id());
    let fresh_dependency_failure = if asset.fresh_gltf {
        match server.get_recursive_dependency_load_state(handle.id()) {
            Some(RecursiveDependencyLoadState::Failed(error)) => {
                Some(format!("Character dependency failed: {error}"))
            }
            _ => None,
        }
    } else {
        None
    };
    let had_gltf_failure = asset.gltf_failure.is_some();
    if loaded {
        asset.gltf_failure = None;
    } else if let Some(error) = fresh_dependency_failure {
        asset.gltf_failure = Some(error);
    }
    if asset.spawned && loaded && !had_gltf_failure {
        return;
    }
    if !accept_gltf_completion(
        asset.fresh_gltf,
        loaded,
        asset.gltf_failure.as_deref(),
        &mut status,
    ) {
        if asset.elapsed > 30.0 && asset.gltf_failure.is_none() {
            status.error = Some("Character loading exceeded 30 seconds".into());
            status.ready = false;
        }
        return;
    }
    if asset.spawned {
        return;
    }
    status.error = None;
    let Some(gltf) = gltfs.get(&handle) else {
        return;
    };
    let Some(scene) = gltf
        .default_scene
        .clone()
        .or_else(|| gltf.scenes.first().cloned())
    else {
        status.error = Some("The GLB has no scene".into());
        return;
    };
    let mut animation_handles = Vec::new();
    for spec in &document.profile.clips {
        let Some(handle) = gltf.animations.get(spec.animation_index) else {
            status.error = Some(format!(
                "Missing animation {} at index {}",
                spec.id, spec.animation_index
            ));
            return;
        };
        if let Some(clip) = clips.get(handle)
            && (clip.duration() - spec.duration_seconds).abs() > 0.15
        {
            status.error = Some(format!(
                "Animation {} duration differs from profile",
                spec.id
            ));
            return;
        }
        animation_handles.push(handle.clone());
    }
    let (graph, nodes) = AnimationGraph::from_clips(animation_handles);
    asset.nodes = document
        .profile
        .clips
        .iter()
        .zip(nodes)
        .map(|(spec, node)| (spec.id.clone(), node))
        .collect();
    asset.graph = Some(graphs.add(graph));
    asset.root = Some(
        commands
            .spawn((CharacterRoot, WorldAssetRoot(scene), Transform::default()))
            .observe(scene_loaded)
            .id(),
    );
    asset.spawned = true;
    status.phase = "Preparing skin and animation…".into();
}

fn accept_gltf_completion(
    fresh: bool,
    loaded_with_dependencies: bool,
    current_failure: Option<&str>,
    status: &mut RuntimeStatus,
) -> bool {
    if fresh && loaded_with_dependencies {
        status.error = None;
        status.phase = "Preparing skin and animation…".into();
        true
    } else {
        if let Some(error) = current_failure {
            status.error = Some(error.to_owned());
            status.phase = "Load error".into();
            status.ready = false;
        }
        false
    }
}

/// Verify only a completion received after this document generation requested
/// bytes. Asset storage deliberately retains old bytes while a reload runs.
fn verify_byte_generation(
    profile: &CharacterProfile,
    server: &AssetServer,
    raw_assets: &Assets<GlbBytes>,
    asset: &mut CharacterAsset,
    status: &mut RuntimeStatus,
) -> bool {
    if asset.verified {
        return true;
    }
    let Some(handle) = &asset.bytes else {
        return false;
    };
    if !asset.fresh_bytes || !matches!(server.get_load_state(handle.id()), Some(LoadState::Loaded))
    {
        if asset.elapsed > 30.0 {
            status.error = Some("Asset verification exceeded 30 seconds".into());
            status.ready = false;
        }
        return false;
    }
    let Some(bytes) = raw_assets.get(handle) else {
        return false;
    };
    asset.fresh_bytes = false;
    match profile.validate_asset_bytes(&bytes.0) {
        Ok(()) => {
            asset.verified = true;
            status.error = None;
            status.phase = "Preparing skin and animation…".into();
            true
        }
        Err(error) => {
            status.error = Some(error.to_string());
            status.ready = false;
            false
        }
    }
}

fn scene_loaded(
    ready: On<WorldInstanceReady>,
    mut commands: Commands,
    roots: Query<(), With<CharacterRoot>>,
    children: Query<&Children>,
    mut asset: ResMut<CharacterAsset>,
    mut players: Query<&mut AnimationPlayer>,
) {
    if !roots.contains(ready.entity) {
        return;
    }
    for entity in children.iter_descendants(ready.entity) {
        commands.entity(entity).insert(CharacterPart);
        if players.get_mut(entity).is_ok()
            && let Some(graph) = &asset.graph
        {
            commands
                .entity(entity)
                .insert(AnimationGraphHandle(graph.clone()));
        }
    }
    asset.scene_ready = true;
}

fn prepare_timeline(
    asset: &mut CharacterAsset,
    playback: &mut Playback,
    document: &SceneDocument,
    generation: u64,
) -> bool {
    let changed =
        asset.applied_timeline != document.timeline || asset.playback_generation != generation;
    if changed {
        // A timeline transaction or explicit open discards the old cursor. A
        // concurrent explicit seek still wins. Appearance edits keep the cursor.
        playback.position_seconds = 0.0;
        playback.completed = false;
        asset.applied_clip.clear();
        asset.applied_timeline = document.timeline.clone();
        asset.playback_generation = generation;
    }
    changed
}

fn interaction_scope(editor: &EditorState) -> Option<InteractionScope> {
    editor.document().map(|document| InteractionScope {
        generation: editor.document_generation,
        revision: document.revision,
    })
}

fn same_transport(a: &Playback, b: &Playback) -> bool {
    a.clip_id == b.clip_id
        && a.playing == b.playing
        && a.position_seconds == b.position_seconds
        && a.seek_request == b.seek_request
        && a.active_timeline_id == b.active_timeline_id
        && a.completed == b.completed
}

fn begin_character_interaction(
    mut players: Query<(Entity, &mut AnimationPlayer), With<CharacterPart>>,
    mut asset: ResMut<CharacterAsset>,
    playback: Res<Playback>,
    editor: Res<EditorState>,
    status: Option<Res<RuntimeStatus>>,
    mut interaction: ResMut<CharacterInteraction>,
) {
    let scope = interaction_scope(&editor);
    let ready = status.as_ref().is_some_and(|status| status.ready)
        && asset.verified
        && asset.scene_ready
        && asset.document_generation == editor.document_generation;
    if let Some(active) = &interaction.active {
        let unchanged_players = players.iter().count() == active.players.len()
            && active.players.iter().all(|entity| {
                players
                    .get(*entity)
                    .is_ok_and(|(_, player)| player.animation(active.node).is_some())
            });
        if scope != Some(active.scope)
            || !ready
            || !unchanged_players
            || !same_transport(&playback, &active.prior)
        {
            // Playback was never overwritten by the wave. Discard the old
            // snapshot; current document/transport intents remain authoritative.
            interaction.active = None;
            asset.applied_clip.clear();
        }
    }
    let Some(requested) = interaction.requested.take() else {
        return;
    };
    if interaction.active.is_some()
        || scope != Some(requested)
        || !ready
        || players.is_empty()
        || editor.document().is_none_or(|doc| doc.timeline.is_empty())
    {
        return;
    }
    let Some(&node) = asset.nodes.get("wave") else {
        return;
    };
    let mut entities = Vec::new();
    for (entity, mut player) in &mut players {
        player.stop_all();
        player.play(node).replay();
        if let Some(active) = player.animation_mut(node) {
            active.set_speed(1.0);
            active.set_repeat(bevy::animation::RepeatAnimation::Never);
            active.resume();
        }
        entities.push(entity);
    }
    interaction.active = Some(ActiveInteraction {
        scope: requested,
        prior: (*playback).clone(),
        node,
        players: entities,
    });
}

/// Apply M0 transport intents before Bevy advances its natural looping clock.
/// Pause therefore holds the last rendered pose, and resume advances this frame.
fn control_single_loop_before_advance(
    mut players: Query<&mut AnimationPlayer, With<CharacterPart>>,
    mut asset: ResMut<CharacterAsset>,
    mut playback: ResMut<Playback>,
    editor: Res<EditorState>,
    interaction: Option<Res<CharacterInteraction>>,
) {
    if interaction.is_some_and(|interaction| interaction.active.is_some()) {
        return;
    }
    let Some(document) = editor
        .document()
        .filter(|document| document.is_single_loop())
    else {
        return;
    };
    prepare_timeline(
        &mut asset,
        &mut playback,
        document,
        editor.document_generation,
    );
    playback.error = None;
    playback.active_timeline_id = document.timeline[0].id.clone();
    playback.completed = false;
    control_single_loop(&mut players, &mut asset, &mut playback, document);
}

fn control_playback(
    mut players: Query<&mut AnimationPlayer, With<CharacterPart>>,
    mut asset: ResMut<CharacterAsset>,
    mut playback: ResMut<Playback>,
    editor: Res<EditorState>,
    time: Option<Res<Time>>,
    interaction: Option<ResMut<CharacterInteraction>>,
) {
    let mut restored = false;
    if let Some(mut interaction) = interaction
        && let Some(active) = &interaction.active
    {
        if !players.iter().all(|player| {
            player
                .animation(active.node)
                .is_some_and(|animation| animation.is_finished())
        }) {
            return;
        }
        // Completion is observed after Bevy's actual wave clock advances.
        // Reconstruct the prior sample in this frame, with no cursor advance.
        *playback = active.prior.clone();
        interaction.active = None;
        asset.applied_clip.clear();
        restored = true;
    }
    let Some(document) = editor.document() else {
        return;
    };
    let changed = prepare_timeline(
        &mut asset,
        &mut playback,
        document,
        editor.document_generation,
    );
    playback.error = None;
    if document.timeline.is_empty() {
        for mut player in &mut players {
            player.stop_all();
        }
        playback.clip_id.clear();
        playback.active_timeline_id.clear();
        playback.playing = false;
        playback.position_seconds = 0.0;
        playback.seek_request = None;
        playback.completed = false;
        asset.applied_clip.clear();
        asset.applied_playing = false;
        return;
    }
    if document.is_single_loop() {
        if restored {
            playback.seek_request = Some(playback.position_seconds);
            control_single_loop(&mut players, &mut asset, &mut playback, document);
        }
        // Loop controls ran before advancement. Mirror the pose Bevy will now
        // evaluate without applying pause/seek/switch intents a second time.
        if let Some(&node) = asset.nodes.get(&playback.clip_id) {
            for player in &mut players {
                if let Some(active) = player.animation(node) {
                    playback.position_seconds = active.seek_time();
                }
            }
        }
        return;
    }
    let duration = document.timeline_duration_seconds();
    let seek = playback.seek_request.take();
    let restarting = playback.completed && playback.playing && seek.is_none();
    if let Some(position) = seek {
        if position.is_finite() {
            playback.position_seconds = position.clamp(0.0, duration);
        } else {
            playback.error = Some("Seek time must be finite".into());
        }
    } else if restarting {
        playback.position_seconds = 0.0;
    } else if playback.playing && !changed && !restored && !players.is_empty() {
        playback.position_seconds = (playback.position_seconds
            + time.as_ref().map(|time| time.delta_secs()).unwrap_or(0.0))
        .min(duration);
    }
    playback.completed = playback.position_seconds >= duration;
    if playback.completed {
        playback.playing = false;
    }
    let (entry, local_seconds) = sequence_sample(document, playback.position_seconds);
    playback.clip_id = entry.clip_id.clone();
    playback.active_timeline_id = entry.id.clone();
    let Some(&node) = asset.nodes.get(&entry.clip_id) else {
        playback.error = Some(format!("Animation {} is not ready", entry.clip_id));
        for mut player in &mut players {
            player.stop_all();
        }
        return;
    };
    for mut player in &mut players {
        // The entry ID, not the source ID, distinguishes repeated actions.
        // Sampling absolute local time also removes completion-counter history
        // from backward seeks and reopens. Bevy evaluates the real graph next.
        if asset.applied_clip != entry.id || player.animation(node).is_none() {
            player.stop_all();
            player.play(node);
        }
        if let Some(active) = player.animation_mut(node) {
            active.replay();
            active.set_repeat(bevy::animation::RepeatAnimation::Never);
            active.set_speed(entry.speed);
            active.set_seek_time(local_seconds);
            if playback.playing {
                active.resume();
            } else {
                active.pause();
            }
        }
    }
    asset.applied_clip = entry.id.clone();
    asset.applied_playing = playback.playing;
}

/// Half-open spans select the next action at an exact boundary. Gaps hold the
/// preceding endpoint; before the first entry hold its initial pose.
fn sequence_sample(document: &SceneDocument, position: f32) -> (&TimelineClip, f32) {
    let first = document
        .timeline
        .iter()
        .min_by(|a, b| a.start_seconds.total_cmp(&b.start_seconds))
        .expect("nonempty timeline");
    let entry = document
        .timeline
        .iter()
        .filter(|entry| entry.start_seconds <= position)
        .max_by(|a, b| a.start_seconds.total_cmp(&b.start_seconds))
        .unwrap_or(first);
    let wall_time = (position - entry.start_seconds).clamp(0.0, entry.duration_seconds);
    let source_duration = document
        .profile
        .clips
        .iter()
        .find(|clip| clip.id == entry.clip_id)
        .expect("validated clip reference")
        .duration_seconds;
    let local_time = wall_time * entry.speed;
    (
        entry,
        if entry.looping {
            local_time.rem_euclid(source_duration)
        } else {
            local_time.min(source_duration)
        },
    )
}

fn control_single_loop(
    players: &mut Query<&mut AnimationPlayer, With<CharacterPart>>,
    asset: &mut CharacterAsset,
    playback: &mut Playback,
    document: &SceneDocument,
) {
    // An empty authoritative timeline also applies to a newly opened document
    // with the same profile. Stop the existing player rather than retaining it.
    let Some(first) = document.timeline.first() else {
        for mut player in players.iter_mut() {
            player.stop_all();
        }
        playback.clip_id.clear();
        playback.playing = false;
        playback.position_seconds = 0.0;
        playback.seek_request = None;
        asset.applied_clip.clear();
        asset.applied_playing = false;
        return;
    };
    if playback.clip_id != first.clip_id {
        playback.clip_id = first.clip_id.clone();
        playback.seek_request = Some(0.0);
    }
    let Some(&node) = asset.nodes.get(&playback.clip_id) else {
        return;
    };
    let switching = asset.applied_clip != playback.clip_id;
    let seek = playback.seek_request.take();
    let play_requested = playback.playing && !asset.applied_playing;
    let timeline = document
        .timeline
        .iter()
        .find(|c| c.clip_id == playback.clip_id);
    let speed = timeline.map(|c| c.speed).unwrap_or(1.0);
    let looping = timeline.map(|c| c.looping).unwrap_or(true);
    let mut found = false;
    for mut player in players.iter_mut() {
        // Shared playback state can already be applied to an earlier scene's
        // player while its replacement arrives with no active animation.
        let initializing = switching || player.animation(node).is_none();
        if initializing {
            player.stop_all();
            player.play(node);
        }
        if let Some(active) = player.animation_mut(node) {
            found = true;
            // `seek_to` leaves Bevy's completion counter intact. Reset it only
            // on a user seek/play request, not on natural nonloop completion.
            if active.is_finished() && (seek.is_some() || play_requested) {
                active.replay();
            }
            active.set_speed(speed);
            active.set_repeat(if looping {
                bevy::animation::RepeatAnimation::Forever
            } else {
                bevy::animation::RepeatAnimation::Never
            });
            if playback.playing {
                active.resume();
            } else {
                active.pause();
            }
            if let Some(position) =
                seek.or_else(|| initializing.then_some(playback.position_seconds))
            {
                active.seek_to(position);
            }
            playback.position_seconds = active.seek_time();
        }
    }
    if found {
        asset.applied_clip = playback.clip_id.clone();
        asset.applied_playing = playback.playing;
    }
}
fn apply_recipe(
    editor: Res<EditorState>,
    mut roots: Query<&mut Transform, With<CharacterRoot>>,
    mut morphs: Query<&mut MorphWeights, With<CharacterPart>>,
) {
    let Some(document) = editor.visible_document() else {
        return;
    };
    for mut transform in &mut roots {
        transform.scale = Vec3::splat(document.character.scale);
    }
    for mut weights in &mut morphs {
        for spec in &document.profile.parameters {
            if let Some(weight) = weights.weights_mut().get_mut(spec.morph_index) {
                *weight = *document
                    .character
                    .parameters
                    .get(&spec.id)
                    .unwrap_or(&spec.default);
            }
        }
    }
}
#[derive(SystemParam)]
struct CharacterEvidenceQueries<'w, 's> {
    meshes: Query<'w, 's, &'static Mesh3d, With<CharacterPart>>,
    skins: Query<'w, 's, &'static SkinnedMesh, With<CharacterPart>>,
    morphs: Query<'w, 's, &'static MorphWeights, With<CharacterPart>>,
    players: Query<'w, 's, &'static AnimationPlayer, With<CharacterPart>>,
}

fn collect_evidence(
    mut status: ResMut<RuntimeStatus>,
    asset: Res<CharacterAsset>,
    editor: Res<EditorState>,
    scene: CharacterEvidenceQueries,
    time: Res<Time<Real>>,
) {
    let CharacterEvidenceQueries {
        meshes,
        skins,
        morphs,
        players,
    } = scene;
    status.frames += 1;
    if status.frame_times_ms.len() >= 600 {
        status.frame_times_ms.remove(0);
    }
    status.frame_times_ms.push(time.delta_secs() * 1000.0);
    status.meshes = meshes.iter().count();
    status.skins = skins.iter().count();
    status.joints = skins
        .iter()
        .flat_map(|skin| skin.joints.iter().copied())
        .collect::<BTreeSet<_>>()
        .len();
    status.morph_nodes = morphs.iter().count();
    status.morph_weights = morphs.iter().map(|m| m.weights().len()).max().unwrap_or(0);
    status.players = players.iter().count();
    status.active_animations = players.iter().map(|p| p.playing_animations().count()).sum();
    status.paused_animations = players
        .iter()
        .flat_map(|p| p.playing_animations())
        .filter(|(_, a)| a.is_paused())
        .count();
    if !asset.scene_ready || status.error.is_some() {
        return;
    }
    let required_weights = editor
        .document()
        .map(|d| {
            d.profile
                .parameters
                .iter()
                .map(|p| p.morph_index + 1)
                .max()
                .unwrap_or(0)
        })
        .unwrap_or(0);
    status.ready = status.meshes > 0
        && status.skins > 0
        && status.joints > 0
        && status.morph_weights >= required_weights
        && status.players > 0;
    if status.ready {
        let now = time.elapsed_secs_f64();
        let first = *status.first_ready_seconds.get_or_insert(now);
        status.ready_frames += 1;
        if now - first >= 1.0 {
            if status.warmed_frame_times_ms.len() >= 600 {
                status.warmed_frame_times_ms.remove(0);
            }
            status
                .warmed_frame_times_ms
                .push(time.delta_secs() * 1000.0);
        }
        status.phase = if status.active_animations > 0 {
            "Ready · skin + morph + animation"
        } else {
            "Ready · no animation selected"
        }
        .into();
    } else if asset.elapsed > 30.0 {
        status.error = Some(format!(
            "Scene readiness failed: meshes={} skins={} joints={} morph_weights={} players={} active={}",
            status.meshes,
            status.skins,
            status.joints,
            status.morph_weights,
            status.players,
            status.active_animations
        ));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn startup_waits_for_explicit_work_without_falling_back_to_fixture() {
        let mut app = App::new();
        app.init_resource::<EditorState>()
            .init_resource::<RuntimeStatus>()
            .insert_resource(StartupDocumentPolicy::WaitForOpen)
            .add_systems(Startup, open_default_document);
        app.update();
        assert!(app.world().resource::<EditorState>().document().is_none());
        assert!(!app.world().resource::<RuntimeStatus>().ready);
        assert_eq!(
            app.world().resource::<RuntimeStatus>().phase,
            "Open a work to play"
        );
        let mut default_app = App::new();
        default_app
            .init_resource::<EditorState>()
            .init_resource::<RuntimeStatus>()
            .init_resource::<StartupDocumentPolicy>()
            .add_systems(Startup, open_default_document);
        default_app.update();
        assert!(
            default_app
                .world()
                .resource::<EditorState>()
                .document()
                .is_some()
        );
    }
    fn state() -> EditorState {
        let profile: CharacterProfile =
            serde_json::from_str(include_str!("../../../assets/character.profile.json")).unwrap();
        let mut state = EditorState::default();
        state
            .replace(SceneDocument::from_profile(profile).unwrap())
            .unwrap();
        state
    }
    #[test]
    fn repeated_preview_is_one_undoable_transaction() {
        let mut state = state();
        let initial = state.document().unwrap().clone();
        for value in [0.15, 0.35, 0.8] {
            let mut values = initial.character.parameters.clone();
            values.insert("smile".into(), value);
            state.preview_parameters(values).unwrap();
            assert_eq!(state.document().unwrap(), &initial);
        }
        assert_eq!(
            state.visible_document().unwrap().character.parameters["smile"],
            0.8
        );
        state.commit_preview().unwrap();
        assert_eq!(state.document().unwrap().revision, initial.revision + 1);
        assert!(state.preview.is_none());
        state.apply(Command::Undo).unwrap();
        assert_eq!(state.document().unwrap().character, initial.character);
        state.apply(Command::Redo).unwrap();
        assert_eq!(state.document().unwrap().character.parameters["smile"], 0.8);
        assert_eq!(state.document().unwrap().revision, initial.revision + 3);
    }
    #[test]
    fn invalid_preview_preserves_document_and_previous_valid_preview() {
        let mut state = state();
        let initial = state.document().unwrap().clone();
        let mut values = initial.character.parameters.clone();
        values.insert("smile".into(), 0.5);
        state.preview_parameters(values.clone()).unwrap();
        values.insert("smile".into(), 2.0);
        assert!(state.preview_parameters(values).is_err());
        assert_eq!(state.document().unwrap(), &initial);
        assert_eq!(
            state.visible_document().unwrap().character.parameters["smile"],
            0.5
        );
    }
    #[test]
    fn replacing_document_discards_transient_preview() {
        let mut state = state();
        let document = state.document().unwrap().clone();
        let mut values = document.character.parameters.clone();
        values.insert("smile".into(), 0.5);
        state.preview_parameters(values).unwrap();
        state.replace(document.clone()).unwrap();
        assert!(state.preview.is_none());
        assert_eq!(state.document().unwrap(), &document);
    }

    #[test]
    fn opening_same_profile_with_empty_timeline_stops_existing_animation() {
        let editor = state();
        let (graph, node) = AnimationGraph::from_clip(Handle::<AnimationClip>::default());
        let _ = graph;
        let mut asset = CharacterAsset::default();
        asset.nodes.insert("idle".into(), node);
        let mut player = AnimationPlayer::default();
        player.play(node).repeat();
        let mut app = App::new();
        app.insert_resource(editor)
            .insert_resource(asset)
            .insert_resource(Playback {
                clip_id: "idle".into(),
                playing: true,
                position_seconds: 1.0,
                seek_request: Some(1.0),
                ..default()
            })
            .add_systems(
                PostUpdate,
                (control_single_loop_before_advance, control_playback).chain(),
            );
        let entity = app.world_mut().spawn((CharacterPart, player)).id();
        app.update();
        assert_eq!(
            app.world()
                .get::<AnimationPlayer>(entity)
                .unwrap()
                .playing_animations()
                .count(),
            1
        );
        let mut document = app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .clone();
        document.timeline.clear();
        app.world_mut()
            .resource_mut::<EditorState>()
            .replace(document)
            .unwrap();
        app.update();
        assert_eq!(
            app.world()
                .get::<AnimationPlayer>(entity)
                .unwrap()
                .playing_animations()
                .count(),
            0
        );
        let playback = app.world().resource::<Playback>();
        assert!(playback.clip_id.is_empty());
        assert!(!playback.playing);
        assert_eq!(playback.position_seconds, 0.0);
        assert!(playback.seek_request.is_none());
        assert!(
            app.world()
                .resource::<CharacterAsset>()
                .applied_clip
                .is_empty()
        );
    }

    #[test]
    fn explicit_same_profile_open_changes_load_generation_but_edits_do_not() {
        let mut editor = state();
        let generation = editor.document_generation;
        let mut values = editor.document().unwrap().character.parameters.clone();
        values.insert("smile".into(), 0.6);
        editor
            .apply(Command::SetParameters {
                character_id: "character-1".into(),
                values,
            })
            .unwrap();
        assert_eq!(editor.document_generation, generation);
        let same_profile = editor.document().unwrap().clone();
        editor.replace(same_profile).unwrap();
        assert_eq!(editor.document_generation, generation + 1);
    }
    fn sequence() -> Vec<TimelineClip> {
        ["idle", "wave", "turn"]
            .iter()
            .enumerate()
            .map(|(index, id)| TimelineClip {
                id: format!("part-{}", index + 1),
                clip_id: (*id).into(),
                start_seconds: index as f32 * 3.0,
                duration_seconds: 3.0,
                speed: 1.0,
                looping: false,
            })
            .collect()
    }

    struct SequenceHarness {
        app: App,
        player: Entity,
        joint: Entity,
        graph: Handle<AnimationGraph>,
    }
    impl SequenceHarness {
        fn new(timeline: Vec<TimelineClip>) -> Self {
            use bevy::animation::{AnimatedBy, AnimationTargetId, animated_field};
            let mut editor = state();
            editor
                .apply(Command::SetTimeline { clips: timeline })
                .unwrap();
            let target = AnimationTargetId::from_name(&Name::new("test-joint"));
            let mut app = App::new();
            app.add_plugins((
                MinimalPlugins,
                AssetPlugin::default(),
                AnimationPlugin,
                TransformPlugin,
            ))
            .insert_resource(editor)
            .insert_resource(RuntimeStatus {
                ready: true,
                ..default()
            })
            .insert_resource(Playback {
                playing: true,
                ..default()
            })
            .insert_resource(bevy::time::TimeUpdateStrategy::ManualDuration(
                std::time::Duration::ZERO,
            ));
            add_playback_systems(&mut app);
            app.world_mut()
                .resource_mut::<Time<Virtual>>()
                .set_max_delta(std::time::Duration::from_secs(20));
            let profile = app
                .world()
                .resource::<EditorState>()
                .document()
                .unwrap()
                .profile
                .clone();
            let handles: Vec<_> = profile
                .clips
                .iter()
                .map(|spec| {
                    let base = match spec.id.as_str() {
                        "idle" => 0.0,
                        "wave" => 10.0,
                        "turn" => 20.0,
                        _ => panic!("fixture action"),
                    };
                    let mut clip = AnimationClip::default();
                    clip.add_curve_to_target(
                        target,
                        AnimatableCurve::new(
                            animated_field!(Transform::translation),
                            AnimatableKeyframeCurve::new([
                                (0.0, Vec3::new(base, 0.0, 0.0)),
                                (
                                    spec.duration_seconds,
                                    Vec3::new(base + spec.duration_seconds, 0.0, 0.0),
                                ),
                            ])
                            .unwrap(),
                        ),
                    );
                    app.world_mut()
                        .resource_mut::<Assets<AnimationClip>>()
                        .add(clip)
                })
                .collect();
            let (graph, nodes) = AnimationGraph::from_clips(handles);
            let graph = app
                .world_mut()
                .resource_mut::<Assets<AnimationGraph>>()
                .add(graph);
            let asset = CharacterAsset {
                verified: true,
                scene_ready: true,
                document_generation: app.world().resource::<EditorState>().document_generation,
                nodes: profile
                    .clips
                    .iter()
                    .zip(nodes)
                    .map(|(spec, node)| (spec.id.clone(), node))
                    .collect(),
                ..default()
            };
            app.insert_resource(asset);
            let player = app
                .world_mut()
                .spawn((
                    CharacterPart,
                    AnimationPlayer::default(),
                    AnimationGraphHandle(graph.clone()),
                ))
                .id();
            let joint = app
                .world_mut()
                .spawn((
                    CharacterPart,
                    Name::new("chest"),
                    Transform::default(),
                    target,
                    AnimatedBy(player),
                ))
                .id();
            let mut harness = Self {
                app,
                player,
                joint,
                graph,
            };
            // Deliver graph asset events and prepare the actual evaluator.
            harness.tick(0.0);
            harness.tick(0.0);
            harness
        }
        fn tick(&mut self, seconds: f32) {
            self.app
                .insert_resource(bevy::time::TimeUpdateStrategy::ManualDuration(
                    std::time::Duration::from_secs_f32(seconds),
                ));
            self.app.update();
        }
        fn seek(&mut self, seconds: f32) {
            self.app.world_mut().resource_mut::<Playback>().seek_request = Some(seconds);
            self.tick(0.0);
        }
        fn assert_pose(&self, x: f32) {
            let actual = self
                .app
                .world()
                .get::<Transform>(self.joint)
                .unwrap()
                .translation
                .x;
            assert!((actual - x).abs() < 0.001, "joint pose {actual} != {x}");
            assert_eq!(
                self.app
                    .world()
                    .get::<AnimationPlayer>(self.player)
                    .unwrap()
                    .playing_animations()
                    .count(),
                1
            );
        }
        fn playback(&self) -> &Playback {
            self.app.world().resource::<Playback>()
        }
        fn click(&mut self) -> bool {
            let position = self
                .app
                .world()
                .get::<GlobalTransform>(self.joint)
                .unwrap()
                .translation();
            self.click_ray(Ray3d::new(
                position + Vec3::new(0.0, 0.03, 5.0),
                Dir3::NEG_Z,
            ))
        }
        fn click_ray(&mut self, ray: Ray3d) -> bool {
            use bevy::ecs::system::RunSystemOnce;
            self.app
                .world_mut()
                .run_system_once(move |mut input: CharacterInteractionInput| input.click(ray))
                .unwrap()
        }
        fn busy(&self) -> bool {
            self.app.world().resource::<CharacterInteraction>().busy()
        }
    }

    #[test]
    fn character_click_wave_restores_running_sequence_cursor_and_history() {
        let mut test = SequenceHarness::new(sequence());
        test.seek(4.25);
        let before = test
            .app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .clone();
        assert!(test.click());
        assert!(!test.click());
        test.tick(0.0);
        test.assert_pose(10.0);
        test.tick(1.0);
        test.assert_pose(11.0);
        assert_eq!(test.playback().position_seconds, 4.25);
        assert!(test.playback().playing);
        assert!(!test.click());
        test.tick(2.0);
        test.assert_pose(13.0);
        assert!(test.busy());
        test.tick(0.05);
        test.assert_pose(11.25);
        assert!(!test.busy());
        assert_eq!(test.playback().position_seconds, 4.25);
        assert_eq!(test.playback().active_timeline_id, "part-2");
        assert_eq!(
            test.app
                .world()
                .resource::<EditorState>()
                .document()
                .unwrap(),
            &before
        );
        test.tick(0.25);
        test.assert_pose(11.5);
        test.app
            .world_mut()
            .resource_mut::<EditorState>()
            .apply(Command::Undo)
            .unwrap();
        // The next undo is still the preceding SetTimeline transaction.
        assert!(
            test.app
                .world()
                .resource::<EditorState>()
                .document()
                .unwrap()
                .is_single_loop()
        );
    }

    #[test]
    fn character_wave_restores_paused_completed_and_m0_loop_samples() {
        for (timeline, cursor, expected_pose, completed) in [
            (sequence(), 7.0, 21.0, false),
            (sequence(), 9.0, 23.0, true),
            (
                state().document().unwrap().timeline.clone(),
                1.75,
                1.75,
                false,
            ),
        ] {
            let mut test = SequenceHarness::new(timeline);
            test.app.world_mut().resource_mut::<Playback>().playing = false;
            test.seek(cursor);
            test.assert_pose(expected_pose);
            assert!(test.click());
            test.tick(0.0);
            test.tick(1.0);
            test.assert_pose(11.0);
            assert_eq!(test.playback().position_seconds, cursor);
            test.tick(2.05);
            test.assert_pose(expected_pose);
            assert!(!test.busy());
            assert!(!test.playback().playing);
            assert_eq!(test.playback().position_seconds, cursor);
            assert_eq!(test.playback().completed, completed);
            test.tick(0.5);
            test.assert_pose(expected_pose);
        }
        // Running M0 also restores source time without advancing on completion.
        let mut test = SequenceHarness::new(state().document().unwrap().timeline.clone());
        test.seek(1.25);
        assert!(test.click());
        test.tick(0.0);
        test.tick(3.05);
        test.assert_pose(1.25);
        assert_eq!(test.playback().position_seconds, 1.25);
        test.tick(0.25);
        test.assert_pose(1.5);
    }

    #[test]
    fn character_interaction_cancels_on_open_edit_undo_and_player_loss() {
        let mut test = SequenceHarness::new(sequence());
        test.seek(7.0);
        assert!(test.click());
        test.tick(0.0);
        let document = test
            .app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .clone();
        test.app
            .world_mut()
            .resource_mut::<EditorState>()
            .replace(document)
            .unwrap();
        test.tick(0.0);
        assert!(!test.busy());
        test.assert_pose(0.0);
        // Simulate the loader's newly verified generation after replacement.
        let generation = test
            .app
            .world()
            .resource::<EditorState>()
            .document_generation;
        test.app
            .world_mut()
            .resource_mut::<CharacterAsset>()
            .document_generation = generation;
        test.seek(4.5);
        assert!(test.click());
        test.tick(0.0);
        let mut values = test
            .app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .character
            .parameters
            .clone();
        values.insert("smile".into(), 0.6);
        test.app
            .world_mut()
            .resource_mut::<EditorState>()
            .apply(Command::SetParameters {
                character_id: "character-1".into(),
                values,
            })
            .unwrap();
        test.tick(0.0);
        assert!(!test.busy());
        test.assert_pose(11.5);
        assert!(test.click());
        test.tick(0.0);
        test.app
            .world_mut()
            .resource_mut::<EditorState>()
            .apply(Command::Undo)
            .unwrap();
        test.tick(0.0);
        assert!(!test.busy());
        test.assert_pose(11.5);
        assert!(test.click());
        test.tick(0.0);
        test.app.world_mut().despawn(test.player);
        test.tick(0.5);
        assert!(!test.busy());
        assert_eq!(test.playback().position_seconds, 4.5);
    }

    #[test]
    fn character_hotspot_rejects_background_stale_clicks_and_tracks_animated_joint() {
        let mut test = SequenceHarness::new(sequence());
        test.seek(7.0);
        assert!(!test.click_ray(Ray3d::new(Vec3::new(0.0, 0.03, 5.0), Dir3::NEG_Z)));
        assert!(!test.click_ray(Ray3d::new(Vec3::new(22.0, 0.03, 5.0), Dir3::NEG_Z)));
        assert!(test.click());
        let document = test
            .app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .clone();
        test.app
            .world_mut()
            .resource_mut::<EditorState>()
            .replace(document)
            .unwrap();
        test.tick(0.0);
        assert!(!test.busy());
        test.assert_pose(0.0);
        assert!(!test.click()); // loader has not verified this generation
        assert!(!hotspot_hit(
            Ray3d::new(Vec3::new(0.0, 0.03, 5.0), Dir3::NEG_Z),
            &GlobalTransform::from(Transform::from_scale(Vec3::ZERO)),
            Vec3::ZERO,
            Vec3::ONE,
        ));
    }

    #[test]
    fn chest_and_head_hotspots_accept_small_scale_centers_without_accepting_outside() {
        for scale in [0.01, 0.03, 0.1, 1.0] {
            let joint = GlobalTransform::from(Transform::from_scale(Vec3::splat(scale)));
            for (center, radii) in [
                (Vec3::new(0.0, 0.03, 0.0), Vec3::new(0.17, 0.18, 0.10)),
                (Vec3::new(0.0, 0.17, 0.015), Vec3::new(0.11, 0.15, 0.09)),
            ] {
                let center_world = joint.affine().transform_point3(center);
                assert!(
                    hotspot_hit(
                        Ray3d::new(center_world + Vec3::Z, Dir3::NEG_Z),
                        &joint,
                        center,
                        radii,
                    ),
                    "center must hit at scale {scale}"
                );
                assert!(
                    !hotspot_hit(
                        Ray3d::new(
                            center_world + Vec3::new(radii.x * scale * 1.1, 0.0, 1.0),
                            Dir3::NEG_Z
                        ),
                        &joint,
                        center,
                        radii,
                    ),
                    "outside must miss at scale {scale}"
                );
            }
        }
    }

    #[test]
    fn m0_loop_pause_holds_rendered_joint_and_resume_advances_in_production_order() {
        let timeline = state().document().unwrap().timeline.clone();
        let duration = timeline[0].duration_seconds;
        let mut test = SequenceHarness::new(timeline);
        test.tick(1.0);
        test.assert_pose(1.0);
        assert_eq!(test.playback().position_seconds, 1.0);
        test.app.world_mut().resource_mut::<Playback>().playing = false;
        test.tick(0.25);
        test.assert_pose(1.0);
        assert_eq!(test.playback().position_seconds, 1.0);
        for _ in 0..3 {
            test.tick(0.5);
            test.assert_pose(1.0);
        }
        // A paused seek is exact even on a frame with nonzero time delta.
        test.app.world_mut().resource_mut::<Playback>().seek_request = Some(1.75);
        test.tick(0.25);
        test.assert_pose(1.75);
        test.tick(0.5);
        test.assert_pose(1.75);
        test.app.world_mut().resource_mut::<Playback>().playing = true;
        test.tick(0.25);
        test.assert_pose(2.0);
        test.tick(0.25);
        test.assert_pose(2.25);
        test.tick(1.0);
        test.assert_pose(3.25 % duration);
        // A paused action switch initializes its real source pose before advance.
        test.app.world_mut().resource_mut::<Playback>().playing = false;
        let mut clips = test
            .app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .timeline
            .clone();
        clips[0].clip_id = "wave".into();
        test.app
            .world_mut()
            .resource_mut::<EditorState>()
            .apply(Command::SetTimeline { clips })
            .unwrap();
        test.tick(0.25);
        test.assert_pose(10.0);
        test.tick(0.25);
        test.assert_pose(10.0);
        test.app.world_mut().resource_mut::<Playback>().playing = true;
        test.tick(0.25);
        test.assert_pose(10.25);
    }

    #[test]
    fn sequence_advances_real_joint_across_boundaries_and_pause_seek_holds() {
        let mut test = SequenceHarness::new(sequence());
        test.assert_pose(0.0);
        test.tick(2.5);
        test.assert_pose(2.5);
        test.tick(0.5);
        test.assert_pose(10.0);
        assert_eq!(test.playback().active_timeline_id, "part-2");
        test.tick(0.25);
        test.assert_pose(10.25);
        test.app.world_mut().resource_mut::<Playback>().playing = false;
        test.tick(1.0);
        test.assert_pose(10.25);
        assert_eq!(test.playback().position_seconds, 3.25);
        test.seek(6.5);
        test.assert_pose(20.5);
        test.tick(1.0);
        test.assert_pose(20.5);
        test.seek(1.0);
        test.assert_pose(1.0);
        test.seek(3.0);
        test.assert_pose(10.0);
        test.app.world_mut().resource_mut::<Playback>().playing = true;
        test.tick(0.5);
        test.assert_pose(10.5);
    }

    #[test]
    fn repeated_source_entries_backward_seeks_completion_and_restart_are_deterministic() {
        let mut clips = sequence();
        clips[0].clip_id = "wave".into();
        let mut test = SequenceHarness::new(clips);
        test.seek(2.75);
        test.assert_pose(12.75);
        test.seek(3.0);
        test.assert_pose(10.0);
        test.seek(4.5);
        test.assert_pose(11.5);
        test.seek(0.5);
        test.assert_pose(10.5);
        test.seek(8.5);
        test.tick(1.0);
        test.assert_pose(23.0);
        assert!(test.playback().completed);
        assert!(!test.playback().playing);
        assert_eq!(test.playback().position_seconds, 9.0);
        test.tick(1.0);
        test.assert_pose(23.0);
        test.app.world_mut().resource_mut::<Playback>().playing = true;
        test.tick(0.25);
        test.assert_pose(10.0);
        assert!(!test.playback().completed);
        test.tick(0.5);
        test.assert_pose(10.5);
        // A seek after completion can resume without stale Bevy completion state.
        test.seek(9.0);
        test.seek(7.0);
        test.assert_pose(21.0);
        test.app.world_mut().resource_mut::<Playback>().playing = true;
        test.tick(0.25);
        test.assert_pose(21.25);
    }

    #[test]
    fn gap_holds_source_endpoint_and_nonunit_speed_maps_wall_time() {
        let mut clips = sequence();
        clips.truncate(2);
        clips[0].start_seconds = 1.0;
        clips[0].duration_seconds = 1.0;
        clips[0].speed = 2.0;
        clips[1].start_seconds = 3.0;
        clips[1].duration_seconds = 2.0;
        clips[1].speed = 0.5;
        // Playback is independent of storage ordering.
        clips.reverse();
        let mut test = SequenceHarness::new(clips);
        test.assert_pose(0.0);
        test.seek(1.5);
        test.assert_pose(1.0);
        test.seek(2.5);
        test.assert_pose(2.0);
        test.seek(3.0);
        test.assert_pose(10.0);
        test.seek(4.0);
        test.assert_pose(10.5);
        test.seek(5.0);
        test.assert_pose(11.0);
        assert!(test.playback().completed);
        let mut clips = sequence();
        clips[0].speed = 2.0;
        test.app
            .world_mut()
            .resource_mut::<EditorState>()
            .apply(Command::SetTimeline {
                clips: clips.clone(),
            })
            .unwrap();
        test.seek(2.5);
        let source_end = test
            .app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .profile
            .clips
            .iter()
            .find(|clip| clip.id == "idle")
            .unwrap()
            .duration_seconds;
        test.assert_pose(source_end);
        // Looping repeats only the source pose inside its finite sequence span.
        clips[0].looping = true;
        test.app
            .world_mut()
            .resource_mut::<EditorState>()
            .apply(Command::SetTimeline { clips })
            .unwrap();
        test.seek(2.5);
        test.assert_pose(5.0 % source_end);
    }

    #[test]
    fn sequence_reopen_undo_and_replacement_player_reset_and_sample_real_pose() {
        use bevy::animation::AnimatedBy;
        let mut test = SequenceHarness::new(sequence());
        test.app.world_mut().resource_mut::<Playback>().playing = false;
        test.seek(4.25);
        test.assert_pose(11.25);
        let saved = test
            .app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .to_json()
            .unwrap();
        test.app
            .world_mut()
            .resource_mut::<EditorState>()
            .apply(Command::Undo)
            .unwrap();
        test.tick(0.0);
        test.assert_pose(0.0);
        test.app
            .world_mut()
            .resource_mut::<EditorState>()
            .apply(Command::Redo)
            .unwrap();
        test.tick(0.0);
        test.assert_pose(0.0);
        test.seek(7.0);
        test.assert_pose(21.0);
        test.app
            .world_mut()
            .resource_mut::<EditorState>()
            .replace(SceneDocument::from_json(&saved).unwrap())
            .unwrap();
        test.tick(0.0);
        test.assert_pose(0.0);
        test.seek(4.25);
        test.assert_pose(11.25);
        test.app.world_mut().despawn(test.player);
        test.player = test
            .app
            .world_mut()
            .spawn((
                CharacterPart,
                AnimationPlayer::default(),
                AnimationGraphHandle(test.graph.clone()),
            ))
            .id();
        test.app
            .world_mut()
            .entity_mut(test.joint)
            .insert(AnimatedBy(test.player));
        test.tick(0.5);
        test.assert_pose(11.25);
        test.app.world_mut().resource_mut::<Playback>().playing = true;
        test.tick(0.25);
        test.assert_pose(11.5);
    }

    #[test]
    fn overlap_transaction_is_rejected_without_changing_cursor_or_joint() {
        let mut test = SequenceHarness::new(sequence());
        test.seek(4.0);
        let before = test
            .app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .clone();
        let mut clips = sequence();
        clips[1].start_seconds = 2.0;
        let error = test
            .app
            .world_mut()
            .resource_mut::<EditorState>()
            .apply(Command::SetTimeline { clips })
            .unwrap_err();
        assert!(error.contains("overlapping_timeline"));
        assert_eq!(
            test.app
                .world()
                .resource::<EditorState>()
                .document()
                .unwrap(),
            &before
        );
        test.tick(0.0);
        test.assert_pose(11.0);
        assert_eq!(test.playback().position_seconds, 4.0);
    }

    #[test]
    fn replacement_player_initializes_already_applied_clip_and_advances() {
        let editor = state();
        let mut clips = Assets::<AnimationClip>::default();
        let mut clip = AnimationClip::default();
        clip.set_duration(3.0);
        let (graph, node) = AnimationGraph::from_clip(clips.add(clip));
        let mut graphs = Assets::<AnimationGraph>::default();
        let graph_handle = graphs.add(graph);
        let mut asset = CharacterAsset::default();
        asset.nodes.insert("idle".into(), node);
        let mut time = Time::<()>::default();
        time.advance_by(std::time::Duration::from_secs_f32(0.1));
        let mut app = App::new();
        app.add_plugins(TaskPoolPlugin::default())
            .insert_resource(editor)
            .insert_resource(asset)
            .insert_resource(Playback {
                clip_id: "idle".into(),
                playing: true,
                position_seconds: 0.0,
                seek_request: None,
                ..default()
            })
            .insert_resource(clips)
            .insert_resource(graphs)
            .insert_resource(time)
            .add_systems(
                PostUpdate,
                (
                    control_single_loop_before_advance,
                    bevy::animation::advance_animations,
                    control_playback,
                )
                    .chain(),
            );
        let original = app
            .world_mut()
            .spawn((
                CharacterPart,
                AnimationPlayer::default(),
                AnimationGraphHandle(graph_handle.clone()),
            ))
            .id();
        app.update();
        assert_eq!(
            app.world().resource::<CharacterAsset>().applied_clip,
            "idle"
        );
        assert!(app.world().resource::<CharacterAsset>().applied_playing);
        assert!(
            app.world()
                .get::<AnimationPlayer>(original)
                .unwrap()
                .animation(node)
                .unwrap()
                .seek_time()
                > 0.0
        );
        app.world_mut().despawn(original);
        let replacement = app
            .world_mut()
            .spawn((
                CharacterPart,
                AnimationPlayer::default(),
                AnimationGraphHandle(graph_handle),
            ))
            .id();
        app.update();
        let active = app
            .world()
            .get::<AnimationPlayer>(replacement)
            .unwrap()
            .animation(node)
            .unwrap();
        assert!(!active.is_paused());
        assert!(active.seek_time() > 0.0);
        let position = active.seek_time();
        app.update();
        assert!(
            app.world()
                .get::<AnimationPlayer>(replacement)
                .unwrap()
                .animation(node)
                .unwrap()
                .seek_time()
                > position
        );
        // A replacement also inherits the authoritative paused state.
        app.world_mut().resource_mut::<Playback>().playing = false;
        app.update();
        app.world_mut()
            .entity_mut(replacement)
            .insert(AnimationPlayer::default());
        app.update();
        assert!(
            app.world()
                .get::<AnimationPlayer>(replacement)
                .unwrap()
                .animation(node)
                .unwrap()
                .is_paused()
        );
    }

    #[derive(Resource)]
    struct TestProfile(CharacterProfile);
    fn verify_test_bytes(
        profile: Res<TestProfile>,
        server: Res<AssetServer>,
        bytes: Res<Assets<GlbBytes>>,
        mut asset: ResMut<CharacterAsset>,
        mut status: ResMut<RuntimeStatus>,
        mut events: MessageReader<AssetEvent<GlbBytes>>,
    ) {
        let id = asset.bytes.as_ref().unwrap().id();
        if events.read().fold(false, |seen, event| {
            seen || event.is_added(id)
                || event.is_modified(id)
                || event.is_loaded_with_dependencies(id)
        }) {
            asset.fresh_bytes = true;
            asset.verified = false;
        }
        verify_byte_generation(&profile.0, &server, &bytes, &mut asset, &mut status);
    }
    #[test]
    fn actual_async_reload_waits_for_fresh_bytes_and_recovers_hash_error() {
        let profile: CharacterProfile =
            serde_json::from_str(include_str!("../../../assets/character.profile.json")).unwrap();
        let correct = include_bytes!("../../../assets/fixtures/nvwa-humanoid.glb");
        let mut stale = correct.to_vec();
        *stale.last_mut().unwrap() ^= 1;
        let directory = std::env::temp_dir().join(format!(
            "nvwa-raw-recovery-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(directory.join("fixtures")).unwrap();
        let path = directory.join(&profile.asset_path);
        std::fs::write(&path, &stale).unwrap();
        let mut app = App::new();
        app.add_plugins(MinimalPlugins)
            .add_plugins(AssetPlugin {
                file_path: directory.to_string_lossy().into_owned(),
                ..default()
            })
            .init_asset::<GlbBytes>()
            .init_asset_loader::<GlbBytesLoader>()
            .insert_resource(TestProfile(profile.clone()))
            .init_resource::<RuntimeStatus>()
            .add_systems(Update, verify_test_bytes);
        let handle: Handle<GlbBytes> = app
            .world()
            .resource::<AssetServer>()
            .load(profile.asset_path.clone());
        app.insert_resource(CharacterAsset {
            bytes: Some(handle.clone()),
            ..default()
        });
        let deadline = std::time::Instant::now() + std::time::Duration::from_secs(10);
        while app.world().resource::<RuntimeStatus>().error.is_none()
            && std::time::Instant::now() < deadline
        {
            app.update();
            std::thread::sleep(std::time::Duration::from_millis(2));
        }
        assert!(
            app.world()
                .resource::<RuntimeStatus>()
                .error
                .as_ref()
                .is_some_and(|error| error.contains("asset_hash_mismatch"))
        );
        // Drain the previous generation's final events before issuing its retry.
        app.update();
        app.world_mut().resource_mut::<CharacterAsset>().fresh_bytes = false;
        // Keep the previous hash error: successful fresh verification must clear it.
        std::fs::write(&path, correct).unwrap();
        let server = app.world().resource::<AssetServer>().clone();
        server.reload(profile.asset_path.clone());
        // A reload is asynchronous; cached bad bytes must not be validated now.
        let mut asset = CharacterAsset {
            bytes: Some(handle.clone()),
            ..default()
        };
        let mut status = RuntimeStatus::default();
        assert!(!verify_byte_generation(
            &profile,
            &server,
            app.world().resource::<Assets<GlbBytes>>(),
            &mut asset,
            &mut status
        ));
        assert!(status.error.is_none());
        let deadline = std::time::Instant::now() + std::time::Duration::from_secs(10);
        while !app.world().resource::<CharacterAsset>().verified
            && std::time::Instant::now() < deadline
        {
            app.update();
            std::thread::sleep(std::time::Duration::from_millis(2));
        }
        assert!(app.world().resource::<CharacterAsset>().verified);
        assert!(app.world().resource::<RuntimeStatus>().error.is_none());
        assert_eq!(
            app.world()
                .resource::<Assets<GlbBytes>>()
                .get(&handle)
                .unwrap()
                .0
                .as_slice(),
            correct.as_slice()
        );
        std::fs::remove_dir_all(directory).unwrap();
    }

    #[test]
    fn fresh_successful_gltf_completion_clears_superseded_parse_error() {
        let mut status = RuntimeStatus {
            error: Some("old parse error".into()),
            ..default()
        };
        assert!(accept_gltf_completion(true, true, None, &mut status));
        assert!(status.error.is_none());
        let mut pending = RuntimeStatus::default();
        assert!(!accept_gltf_completion(false, true, None, &mut pending));
        assert!(pending.error.is_none());
    }
    #[test]
    fn current_gltf_failure_is_visible_until_a_fresh_success() {
        let mut status = RuntimeStatus {
            ready: true,
            ..default()
        };
        let failure = "Character load failed: current parse error";
        assert!(!accept_gltf_completion(
            false,
            false,
            Some(failure),
            &mut status
        ));
        assert_eq!(status.error.as_deref(), Some(failure));
        assert!(!status.ready);
        // A fresh root whose dependencies are still pending cannot clear it.
        assert!(!accept_gltf_completion(
            true,
            false,
            Some(failure),
            &mut status
        ));
        assert_eq!(status.error.as_deref(), Some(failure));
        assert!(accept_gltf_completion(true, true, None, &mut status));
        assert!(status.error.is_none());
    }
}
