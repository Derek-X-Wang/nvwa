//! Native CPU tests exercise the production loading system and pinned GLTF loader.
use super::*;
use bevy::asset::io::{
    AssetReader, AssetReaderError, AssetSourceBuilder, AssetSourceId, PathStream,
    memory::{Dir, MemoryAssetReader},
};
use std::{
    path::Path,
    sync::{
        Arc,
        atomic::{AtomicUsize, Ordering},
    },
};

const FIXTURE: &[u8] = include_bytes!("../../../assets/fixtures/nvwa-humanoid.glb");

#[derive(Clone)]
struct CountingReader {
    inner: MemoryAssetReader,
    reads: Arc<AtomicUsize>,
    // Mutate the source after retrieval to catch a second-source-read race.
    replace_after_read: bool,
    gates: Option<Arc<ReadGates>>,
}
impl AssetReader for CountingReader {
    async fn read<'a>(&'a self, path: &'a Path) -> Result<impl Reader + 'a, AssetReaderError> {
        self.reads.fetch_add(1, Ordering::SeqCst);
        let reader = self.inner.read(path).await?;
        if let Some(gates) = &self.gates {
            let gate = gates.enter();
            std::future::poll_fn(|cx| gate.poll(cx)).await;
            if gate.failed.load(Ordering::SeqCst) {
                return Err(AssetReaderError::NotFound(path.to_path_buf()));
            }
        }
        if self.replace_after_read {
            self.inner
                .root
                .insert_asset(path, b"source changed after retrieval".to_vec());
        }
        Ok(reader)
    }
    async fn read_meta<'a>(&'a self, path: &'a Path) -> Result<impl Reader + 'a, AssetReaderError> {
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

struct Harness {
    app: App,
    dir: Dir,
    reads: Arc<AtomicUsize>,
    profile: CharacterProfile,
}
impl Harness {
    fn new(bytes: Option<&[u8]>, replace_after_read: bool) -> Self {
        Self::with_gates(bytes, replace_after_read, None)
    }
    fn with_gates(
        bytes: Option<&[u8]>,
        replace_after_read: bool,
        gates: Option<Arc<ReadGates>>,
    ) -> Self {
        let profile =
            CharacterProfile::from_json(include_str!("../../../assets/character.profile.json"))
                .unwrap();
        let dir = Dir::default();
        if let Some(bytes) = bytes {
            dir.insert_asset(Path::new(&profile.asset_path), bytes.to_vec());
        }
        let reads = Arc::new(AtomicUsize::new(0));
        let reader = CountingReader {
            inner: MemoryAssetReader { root: dir.clone() },
            reads: reads.clone(),
            replace_after_read,
            gates,
        };
        let mut app = App::new();
        app.register_asset_source(
            AssetSourceId::Default,
            AssetSourceBuilder::new(move || Box::new(reader.clone())),
        )
        .add_plugins((
            MinimalPlugins,
            AssetPlugin::default(),
            bevy::transform::TransformPlugin,
            bevy::world_serialization::WorldSerializationPlugin,
            bevy::mesh::MeshPlugin,
            AnimationPlugin,
            bevy::gltf::GltfPlugin::default(),
        ))
        .init_asset::<Image>()
        .init_asset::<StandardMaterial>()
        .init_asset::<CharacterGlb>()
        .init_asset_loader::<CharacterGlbLoader>()
        .init_resource::<EditorState>()
        .init_resource::<CharacterAsset>()
        .init_resource::<RuntimeStatus>()
        .init_resource::<Playback>()
        .add_systems(Update, load_character)
        .add_systems(PostUpdate, collect_evidence);
        app.finish();
        app.cleanup();
        let mut harness = Self {
            app,
            dir,
            reads,
            profile,
        };
        harness.open(harness.profile.clone());
        harness
    }
    fn open(&mut self, profile: CharacterProfile) {
        self.app
            .world_mut()
            .resource_mut::<EditorState>()
            .replace(SceneDocument::from_profile(profile).unwrap())
            .unwrap();
        self.app.update();
        let status = self.app.world().resource::<RuntimeStatus>();
        assert!(!status.ready);
        assert!(
            status.error.is_none(),
            "New generation reused an earlier error"
        );
        assert!(!self.app.world().resource::<CharacterAsset>().verified);
    }
    fn until(&mut self, predicate: impl Fn(&World) -> bool) {
        let deadline = std::time::Instant::now() + std::time::Duration::from_secs(15);
        while !predicate(self.app.world()) && std::time::Instant::now() < deadline {
            self.app.update();
            std::thread::sleep(std::time::Duration::from_millis(2));
        }
        assert!(
            predicate(self.app.world()),
            "Timed out: {:?}",
            self.app.world().resource::<RuntimeStatus>()
        );
    }
    fn ready(&mut self) {
        self.until(|world| world.resource::<RuntimeStatus>().ready);
        let asset = self.app.world().resource::<CharacterAsset>();
        assert!(asset.verified && asset.scene_ready && asset.spawned);
        let raw = self
            .app
            .world()
            .resource::<Assets<CharacterGlb>>()
            .get(asset.bytes.as_ref().unwrap())
            .unwrap();
        assert_eq!(raw.bytes, FIXTURE);
        let gltf = self
            .app
            .world()
            .resource::<Assets<Gltf>>()
            .get(raw.gltf.as_ref().unwrap())
            .unwrap();
        assert_eq!(gltf.animations.len(), self.profile.clips.len());
        assert!(!gltf.scenes.is_empty() && !gltf.meshes.is_empty() && !gltf.skins.is_empty());
        let status = self.app.world().resource::<RuntimeStatus>();
        assert!(status.error.is_none());
        assert_eq!(status.morph_weights, self.profile.parameters.len());
    }
    fn error(&mut self, expected: &str) {
        self.until(|world| world.resource::<RuntimeStatus>().error.is_some());
        let status = self.app.world().resource::<RuntimeStatus>();
        assert!(
            status.error.as_ref().unwrap().contains(expected),
            "{status:?}"
        );
        assert!(!status.ready);
        assert!(!self.app.world().resource::<CharacterAsset>().spawned);
    }
    fn reads(&self) -> usize {
        self.reads.load(Ordering::SeqCst)
    }
}

#[test]
fn one_retrieval_supplies_hash_scene_skin_morphs_and_animations() {
    let mut test = Harness::new(Some(FIXTURE), true);
    test.ready();
    assert_eq!(test.reads(), 1, "Delegation retrieved the source again");
}

#[test]
fn wrong_profile_then_correct_profile_at_same_path_requires_fresh_retrieval() {
    let mut test = Harness::new(Some(FIXTURE), false);
    test.ready();
    let mut wrong = test.profile.clone();
    wrong.asset_sha256 = "0".repeat(64);
    test.open(wrong);
    test.error("asset_hash_mismatch");
    assert_eq!(test.reads(), 2);
    test.open(test.profile.clone());
    test.ready();
    assert_eq!(test.reads(), 3);
}

#[test]
fn corrupt_and_missing_sources_recover_on_same_path_work_open() {
    for initial in [Some(b"corrupt GLB".as_slice()), Some(b"".as_slice()), None] {
        let mut test = Harness::new(initial, false);
        test.error(match initial {
            Some(b"") => "missing_asset",
            Some(_) => "asset_hash_mismatch",
            None => "Asset byte load failed",
        });
        assert_eq!(test.reads(), 1);
        test.dir
            .insert_asset(Path::new(&test.profile.asset_path), FIXTURE.to_vec());
        test.open(test.profile.clone());
        test.ready();
        assert_eq!(test.reads(), 2);
    }
}

#[test]
fn ready_character_replaced_by_corrupt_bytes_is_not_exposed() {
    let mut test = Harness::new(Some(FIXTURE), false);
    test.ready();
    test.dir.insert_asset(
        Path::new(&test.profile.asset_path),
        b"replacement is corrupt".to_vec(),
    );
    test.open(test.profile.clone());
    test.error("asset_hash_mismatch");
    assert_eq!(test.reads(), 2);
    test.dir
        .insert_asset(Path::new(&test.profile.asset_path), FIXTURE.to_vec());
    test.open(test.profile.clone());
    test.ready();
    assert_eq!(test.reads(), 3);
}

#[test]
fn matching_hash_glb_with_gltf_parse_error_surfaces_and_recovers() {
    // Valid container/core profile, invalid glTF mesh reference. The hash is
    // SHA-256 of this exact deterministic test container, not of the fixture.
    let json =
        br#"{"asset":{"version":"2.0"},"nodes":[{"mesh":1}],"scenes":[{"nodes":[0]}],"scene":0} "#;
    assert_eq!(json.len(), 84);
    let mut bytes = b"glTF".to_vec();
    bytes.extend_from_slice(&2u32.to_le_bytes());
    bytes.extend_from_slice(&(20u32 + json.len() as u32).to_le_bytes());
    bytes.extend_from_slice(&(json.len() as u32).to_le_bytes());
    bytes.extend_from_slice(&0x4e4f534au32.to_le_bytes());
    bytes.extend_from_slice(json);
    let mut test = Harness::new(Some(&bytes), false);
    let mut profile = test.profile.clone();
    profile.parameters.clear();
    profile.clips.clear();
    profile.asset_sha256 =
        "238beedebd5d2607133f177fef8f10f5bf0900b2dc78c5e50f9fcd8876616eab".into();
    assert!(profile.validate_asset_bytes(&bytes).is_ok());
    test.open(profile);
    test.error("Character load failed");
    assert!(test.app.world().resource::<CharacterAsset>().verified);
    test.dir
        .insert_asset(Path::new(&test.profile.asset_path), FIXTURE.to_vec());
    test.open(test.profile.clone());
    test.ready();
}

#[test]
fn switching_to_a_new_asset_path_retrieves_it_once() {
    let mut test = Harness::new(Some(FIXTURE), false);
    test.ready();
    let mut other = test.profile.clone();
    other.asset_path = "fixtures/another-character.glb".into();
    test.dir
        .insert_asset(Path::new(&other.asset_path), FIXTURE.to_vec());
    test.open(other);
    test.ready();
    assert_eq!(test.reads(), 2);
}

#[test]
fn asynchronous_io_failure_cannot_reuse_verified_scene_and_recovers() {
    let mut test = Harness::new(Some(FIXTURE), false);
    test.ready();
    // Ensure the prior generation's final dependency event is drained first.
    test.app.update();
    test.dir.remove_asset(Path::new(&test.profile.asset_path));
    let server = test.app.world().resource::<AssetServer>().clone();
    server.reload(test.profile.asset_path.clone());
    test.until(|world| world.resource::<RuntimeStatus>().error.is_some());
    let status = test.app.world().resource::<RuntimeStatus>();
    assert!(
        status
            .error
            .as_ref()
            .unwrap()
            .contains("Asset byte load failed")
    );
    assert!(!status.ready);
    assert!(!test.app.world().resource::<CharacterAsset>().verified);
    // Cached scene/dependency success must not clear the fresh I/O failure.
    test.app.update();
    assert!(test.app.world().resource::<RuntimeStatus>().error.is_some());
    assert!(!test.app.world().resource::<RuntimeStatus>().ready);
    // Pinned Bevy's forced-reload fallback attempts an untyped read after the
    // typed read fails while labels live. Both attempts here return NotFound;
    // neither retrieves a GLB. Successful recovery must retrieve it once.
    assert_eq!(test.reads(), 3);
    let before_recovery = test.reads();
    test.dir
        .insert_asset(Path::new(&test.profile.asset_path), FIXTURE.to_vec());
    test.open(test.profile.clone());
    test.ready();
    assert_eq!(test.reads() - before_recovery, 1);
}

#[derive(Default)]
struct ReadGate {
    failed: std::sync::atomic::AtomicBool,
    released: std::sync::atomic::AtomicBool,
    waker: std::sync::Mutex<Option<std::task::Waker>>,
}
impl ReadGate {
    fn poll(&self, cx: &mut std::task::Context<'_>) -> std::task::Poll<()> {
        let mut waker = self.waker.lock().unwrap();
        if self.released.load(Ordering::SeqCst) {
            std::task::Poll::Ready(())
        } else {
            *waker = Some(cx.waker().clone());
            std::task::Poll::Pending
        }
    }
    fn release(&self) {
        self.released.store(true, Ordering::SeqCst);
        if let Some(waker) = self.waker.lock().unwrap().take() {
            waker.wake();
        }
    }
}
#[derive(Default)]
struct ReadGates(std::sync::Mutex<Vec<Arc<ReadGate>>>);
impl ReadGates {
    fn enter(&self) -> Arc<ReadGate> {
        let gate = Arc::new(ReadGate::default());
        self.0.lock().unwrap().push(gate.clone());
        gate
    }
    fn entered(&self) -> usize {
        self.0.lock().unwrap().len()
    }
    fn release(&self, index: usize) {
        self.0.lock().unwrap()[index].release();
    }
    fn fail(&self, index: usize) {
        self.0.lock().unwrap()[index]
            .failed
            .store(true, Ordering::SeqCst);
        self.release(index);
    }
}
struct ReleaseReadGates(Arc<ReadGates>);
impl Drop for ReleaseReadGates {
    fn drop(&mut self) {
        for gate in self.0.0.lock().unwrap().iter() {
            gate.release();
        }
    }
}

/// Parseable A differs in actual scene translation, mesh position and animation
/// duration. B is the published fixture; B's profile rejects A's exact bytes.
fn stale_snapshot() -> Vec<u8> {
    let mut bytes = FIXTURE.to_vec();
    let json_len = u32::from_le_bytes(bytes[12..16].try_into().unwrap()) as usize;
    let json: serde_json::Value = serde_json::from_slice(&bytes[20..20 + json_len]).unwrap();
    let needle = b"0.10000002384185791";
    let offset = bytes[20..20 + json_len]
        .windows(needle.len())
        .position(|s| s == needle)
        .unwrap()
        + 20;
    bytes[offset] = b'5';
    let binary_start = 20 + json_len + 8;
    let accessor_offset = |index: usize| {
        let accessor = &json["accessors"][index];
        let view = &json["bufferViews"][accessor["bufferView"].as_u64().unwrap() as usize];
        binary_start
            + view["byteOffset"].as_u64().unwrap_or(0) as usize
            + accessor["byteOffset"].as_u64().unwrap_or(0) as usize
    };
    let position = json["meshes"][0]["primitives"][0]["attributes"]["POSITION"]
        .as_u64()
        .unwrap() as usize;
    let offset = accessor_offset(position);
    let value = f32::from_le_bytes(bytes[offset..offset + 4].try_into().unwrap()) + 5.0;
    bytes[offset..offset + 4].copy_from_slice(&value.to_le_bytes());
    let input = json["animations"][0]["samplers"][0]["input"]
        .as_u64()
        .unwrap() as usize;
    let last = accessor_offset(input)
        + (json["accessors"][input]["count"].as_u64().unwrap() as usize - 1) * 4;
    let value = f32::from_le_bytes(bytes[last..last + 4].try_into().unwrap()) * 2.0;
    bytes[last..last + 4].copy_from_slice(&value.to_le_bytes());
    bytes
}

#[derive(Debug, PartialEq)]
struct SceneFingerprint {
    scene_head: Vec3,
    mesh_position: Vec3,
    animation_duration: f32,
    live_head: Vec3,
}
fn fingerprint(app: &mut App) -> SceneFingerprint {
    let world = app.world();
    let asset = world.resource::<CharacterAsset>();
    let gltf = world
        .resource::<Assets<Gltf>>()
        .get(asset.handle.as_ref().unwrap())
        .unwrap();
    let scene = world
        .resource::<Assets<WorldAsset>>()
        .get(&gltf.scenes[0])
        .unwrap();
    let scene_head = scene
        .world
        .iter_entities()
        .find(|entity| {
            entity
                .get::<Name>()
                .is_some_and(|name| name.as_str() == "head")
        })
        .unwrap()
        .get::<Transform>()
        .unwrap()
        .translation;
    let primitive = &world
        .resource::<Assets<bevy::gltf::GltfMesh>>()
        .get(&gltf.meshes[0])
        .unwrap()
        .primitives[0];
    let positions = world
        .resource::<Assets<Mesh>>()
        .get(&primitive.mesh)
        .unwrap()
        .attribute(Mesh::ATTRIBUTE_POSITION)
        .unwrap()
        .as_float3()
        .unwrap();
    let mesh_position = Vec3::from(positions[0]);
    let animation_duration = world
        .resource::<Assets<AnimationClip>>()
        .get(&gltf.animations[0])
        .unwrap()
        .duration();
    let world = app.world_mut();
    let mut joints = world.query_filtered::<(&Name, &Transform), With<CharacterPart>>();
    let live_head = joints
        .iter(world)
        .find(|(name, _)| name.as_str() == "head")
        .unwrap()
        .1
        .translation;
    SceneFingerprint {
        scene_head,
        mesh_position,
        animation_duration,
        live_head,
    }
}

fn drive_for(test: &mut Harness, duration: std::time::Duration) {
    let deadline = std::time::Instant::now() + duration;
    while std::time::Instant::now() < deadline {
        test.app.update();
        std::thread::sleep(std::time::Duration::from_millis(1));
    }
}

fn overlapping_open_schedule(attempt_b_first: bool) {
    let gates = Arc::new(ReadGates::default());
    let _release = ReleaseReadGates(gates.clone());
    let stale = stale_snapshot();
    let mut test = Harness::with_gates(Some(&stale), false, Some(gates.clone()));
    test.until(|_| gates.entered() == 1);
    test.dir
        .insert_asset(Path::new(&test.profile.asset_path), FIXTURE.to_vec());
    test.open(test.profile.clone());
    drive_for(&mut test, std::time::Duration::from_millis(100));
    if attempt_b_first && gates.entered() == 2 {
        // Red schedule: B publishes while A's retrieved snapshot is held.
        gates.release(1);
        test.ready();
        let accepted = fingerprint(&mut test.app);
        gates.release(0);
        test.until(|world| world.resource::<RuntimeStatus>().error.is_some());
        drive_for(&mut test, std::time::Duration::from_millis(50));
        assert_eq!(
            fingerprint(&mut test.app),
            accepted,
            "Rejected A overwrote B's live scene/mesh/animation assets"
        );
        panic!("B started before A retired; serialization must fence this schedule");
    }
    if attempt_b_first {
        // Green serialization must prevent B's attempted early completion.
        assert_eq!(gates.entered(), 1);
        assert!(test.app.world().resource::<CharacterAsset>().root.is_none());
        assert!(!test.app.world().resource::<RuntimeStatus>().ready);
    }
    gates.release(0);
    test.until(|_| gates.entered() == 2);
    drive_for(&mut test, std::time::Duration::from_millis(50));
    let status = test.app.world().resource::<RuntimeStatus>();
    assert!(
        status.error.is_none(),
        "Superseded A authorized the current generation's error: {status:?}"
    );
    assert!(!status.ready);
    assert!(test.app.world().resource::<CharacterAsset>().root.is_none());
    gates.release(1);
    test.ready();
    let accepted = fingerprint(&mut test.app);
    drive_for(&mut test, std::time::Duration::from_millis(50));
    assert_eq!(fingerprint(&mut test.app), accepted);
    assert_eq!(
        test.reads(),
        2,
        "One retrieval per open, with no duplicate B request"
    );
}

#[test]
fn same_path_overlapping_opens_a_first_never_publish_a_to_current_work() {
    overlapping_open_schedule(false);
}
#[test]
fn same_path_overlapping_opens_attempt_b_first_fences_stale_scene_mesh_animation() {
    overlapping_open_schedule(true);
}
#[test]
fn long_lived_ready_reader_failure_preserves_specific_error_until_recovery() {
    let mut test = Harness::new(Some(FIXTURE), false);
    test.ready();
    test.app.update();
    test.app
        .world_mut()
        .resource_mut::<CharacterAsset>()
        .elapsed = 31.0;
    test.dir.remove_asset(Path::new(&test.profile.asset_path));
    test.app
        .world()
        .resource::<AssetServer>()
        .reload(test.profile.asset_path.clone());
    test.until(|world| world.resource::<RuntimeStatus>().error.is_some());
    let error = test
        .app
        .world()
        .resource::<RuntimeStatus>()
        .error
        .clone()
        .unwrap();
    assert!(
        error.contains("Asset byte load failed"),
        "Terminal I/O error was replaced: {error}"
    );
    for _ in 0..20 {
        test.app.update();
        assert_eq!(
            test.app.world().resource::<RuntimeStatus>().error.as_ref(),
            Some(&error)
        );
        assert!(!test.app.world().resource::<RuntimeStatus>().ready);
    }
    test.dir
        .insert_asset(Path::new(&test.profile.asset_path), FIXTURE.to_vec());
    test.open(test.profile.clone());
    test.ready();
}

#[test]
fn pending_different_path_recovers_while_old_source_stays_held() {
    let gates = Arc::new(ReadGates::default());
    let _release = ReleaseReadGates(gates.clone());
    let mut test = Harness::with_gates(Some(&stale_snapshot()), false, Some(gates.clone()));
    test.until(|_| gates.entered() == 1);
    let mut other = test.profile.clone();
    other.asset_path = "fixtures/independent-character.glb".into();
    test.dir
        .insert_asset(Path::new(&other.asset_path), FIXTURE.to_vec());
    test.open(other);
    test.until(|_| gates.entered() == 2);
    gates.release(1);
    test.ready();
    let accepted = fingerprint(&mut test.app);
    assert!(!gates.0.lock().unwrap()[0].released.load(Ordering::SeqCst));
    gates.release(0);
    test.until(|world| world.resource::<CharacterAsset>().retiring.is_empty());
    drive_for(&mut test, std::time::Duration::from_millis(50));
    assert_eq!(fingerprint(&mut test.app), accepted);
    assert!(test.app.world().resource::<RuntimeStatus>().ready);
    assert!(test.app.world().resource::<RuntimeStatus>().error.is_none());
    assert_eq!(test.reads(), 2);
}

#[test]
fn superseded_reader_failure_unblocks_latest_same_path_open() {
    let gates = Arc::new(ReadGates::default());
    let _release = ReleaseReadGates(gates.clone());
    let mut test = Harness::with_gates(Some(FIXTURE), false, Some(gates.clone()));
    test.until(|_| gates.entered() == 1);
    test.open(test.profile.clone());
    gates.fail(0);
    test.until(|_| gates.entered() == 2);
    assert!(test.app.world().resource::<RuntimeStatus>().error.is_none());
    gates.release(1);
    test.ready();
    assert_eq!(test.reads(), 2);
}

#[test]
fn pending_same_path_opens_coalesce_to_latest_profile() {
    let gates = Arc::new(ReadGates::default());
    let _release = ReleaseReadGates(gates.clone());
    let mut test = Harness::with_gates(Some(&stale_snapshot()), false, Some(gates.clone()));
    test.until(|_| gates.entered() == 1);
    let mut wrong = test.profile.clone();
    wrong.asset_sha256 = "0".repeat(64);
    test.open(wrong);
    test.dir
        .insert_asset(Path::new(&test.profile.asset_path), FIXTURE.to_vec());
    test.open(test.profile.clone());
    drive_for(&mut test, std::time::Duration::from_millis(50));
    assert_eq!(gates.entered(), 1);
    gates.release(0);
    test.until(|_| gates.entered() == 2);
    gates.release(1);
    test.ready();
    assert_eq!(
        test.reads(),
        2,
        "Intermediate queued profile must not retrieve again"
    );
}

#[test]
fn ready_scene_is_retired_immediately_before_same_path_pending_open() {
    let gates = Arc::new(ReadGates::default());
    let _release = ReleaseReadGates(gates.clone());
    let mut test = Harness::with_gates(Some(FIXTURE), false, Some(gates.clone()));
    test.until(|_| gates.entered() == 1);
    gates.release(0);
    test.ready();
    test.dir
        .insert_asset(Path::new(&test.profile.asset_path), stale_snapshot());
    test.open(test.profile.clone());
    let world = test.app.world_mut();
    assert_eq!(
        world
            .query_filtered::<Entity, With<CharacterRoot>>()
            .iter(world)
            .count(),
        0
    );
    assert_eq!(
        world
            .query_filtered::<Entity, With<CharacterPart>>()
            .iter(world)
            .count(),
        0
    );
    test.until(|_| gates.entered() == 2);
    test.dir
        .insert_asset(Path::new(&test.profile.asset_path), FIXTURE.to_vec());
    test.open(test.profile.clone());
    gates.release(1);
    test.until(|_| gates.entered() == 3);
    assert!(test.app.world().resource::<RuntimeStatus>().error.is_none());
    assert!(test.app.world().resource::<CharacterAsset>().root.is_none());
    gates.release(2);
    test.ready();
    assert_eq!(test.reads(), 3);
}
