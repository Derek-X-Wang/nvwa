//! Shared native/Web renderer. The editor document is the source of truth.
use std::collections::{BTreeMap, BTreeSet};

use bevy::{
    app::AnimationSystems,
    asset::{
        AssetLoadFailedEvent, AssetLoader, LoadContext, LoadState, RecursiveDependencyLoadState,
        io::Reader,
    },
    ecs::system::SystemParam,
    mesh::{morph::MorphWeights, skinning::SkinnedMesh},
    prelude::*,
    world_serialization::WorldInstanceReady,
};
use nvwa_core::{CharacterProfile, Command, CommandEnvelope, Editor, SceneDocument};

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
    pub clip_id: String,
    pub playing: bool,
    pub position_seconds: f32,
    pub seek_request: Option<f32>,
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
    Mirror,
}

pub struct NvwaRuntimePlugin;
impl Plugin for NvwaRuntimePlugin {
    fn build(&self, app: &mut App) {
        app.init_asset::<GlbBytes>()
            .init_asset_loader::<GlbBytesLoader>()
            .init_resource::<EditorState>()
            .init_resource::<RuntimeStatus>()
            .init_resource::<Playback>()
            .init_resource::<CharacterAsset>()
            .add_systems(Startup, (open_default_document, setup_environment))
            .add_systems(Update, (load_character, control_playback).chain())
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
    }
}

fn open_default_document(mut editor: ResMut<EditorState>, mut status: ResMut<RuntimeStatus>) {
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

fn control_playback(
    mut players: Query<&mut AnimationPlayer, With<CharacterPart>>,
    mut asset: ResMut<CharacterAsset>,
    mut playback: ResMut<Playback>,
    editor: Res<EditorState>,
) {
    let Some(document) = editor.document() else {
        return;
    };
    // An empty authoritative timeline also applies to a newly opened document
    // with the same profile. Stop the existing player rather than retaining it.
    let Some(first) = document.timeline.first() else {
        for mut player in &mut players {
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
    for mut player in &mut players {
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
            })
            .add_systems(Update, control_playback);
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
    #[test]
    fn seeking_completed_nonloop_animation_resets_completion_and_advances() {
        let mut editor = state();
        let mut document = editor.document().unwrap().clone();
        document.timeline[0].looping = false;
        editor.replace(document).unwrap();
        let mut clips = Assets::<AnimationClip>::default();
        let mut clip = AnimationClip::default();
        clip.set_duration(3.0);
        let handle = clips.add(clip);
        let (graph, node) = AnimationGraph::from_clip(handle);
        let mut graphs = Assets::<AnimationGraph>::default();
        let graph_handle = graphs.add(graph);
        let mut asset = CharacterAsset {
            applied_clip: "idle".into(),
            applied_playing: true,
            ..default()
        };
        asset.nodes.insert("idle".into(), node);
        let mut player = AnimationPlayer::default();
        player.play(node);
        let mut time = Time::<()>::default();
        time.advance_by(std::time::Duration::from_secs_f32(4.0));
        let mut app = App::new();
        app.add_plugins(TaskPoolPlugin::default())
            .insert_resource(editor)
            .insert_resource(asset)
            .insert_resource(Playback {
                clip_id: "idle".into(),
                playing: true,
                position_seconds: 0.0,
                seek_request: None,
            })
            .insert_resource(clips)
            .insert_resource(graphs)
            .insert_resource(time)
            .add_systems(Update, bevy::animation::advance_animations);
        let entity = app
            .world_mut()
            .spawn((CharacterPart, player, AnimationGraphHandle(graph_handle)))
            .id();
        app.update();
        assert!(
            app.world()
                .get::<AnimationPlayer>(entity)
                .unwrap()
                .animation(node)
                .unwrap()
                .is_finished()
        );
        app.world_mut().resource_mut::<Playback>().seek_request = Some(1.0);
        app.world_mut()
            .resource_mut::<Time>()
            .advance_by(std::time::Duration::from_secs_f32(0.1));
        app.add_systems(
            Update,
            control_playback.before(bevy::animation::advance_animations),
        );
        app.update();
        let active = app
            .world()
            .get::<AnimationPlayer>(entity)
            .unwrap()
            .animation(node)
            .unwrap();
        assert!(!active.is_finished());
        assert!((active.seek_time() - 1.1).abs() < 0.001);
        // Without a new user request, reaching the end stays stopped.
        app.world_mut()
            .resource_mut::<Time>()
            .advance_by(std::time::Duration::from_secs_f32(4.0));
        app.update();
        app.world_mut()
            .resource_mut::<Time>()
            .advance_by(std::time::Duration::from_secs_f32(0.1));
        app.update();
        assert!(
            app.world()
                .get::<AnimationPlayer>(entity)
                .unwrap()
                .animation(node)
                .unwrap()
                .is_finished()
        );
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
            })
            .insert_resource(clips)
            .insert_resource(graphs)
            .insert_resource(time)
            .add_systems(
                Update,
                (control_playback, bevy::animation::advance_animations).chain(),
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
