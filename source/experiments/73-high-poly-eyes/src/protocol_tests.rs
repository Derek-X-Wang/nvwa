//! CPU integration only: actual production runtime/stage/propagation, no renderer/window.
use super::*;
use bevy::asset::{AssetApp, AssetMetaCheck};

#[derive(Resource)]
struct MirrorEnabled(bool);
#[derive(Resource, Default)]
struct StagePropagationWitness(bool);
fn observe_real_stage_before_global_propagation(world: &mut World) {
    if !world
        .resource::<EditorState>()
        .document()
        .is_some_and(|d| d.character.parameters.get("torso_length") == Some(&1.0))
    {
        return;
    }
    let waiting = world
        .iter_entities()
        .filter(|e| e.contains::<nvwa_runtime::SceneCamera>())
        .any(|e| {
            e.get::<Transform>()
                .zip(e.get::<GlobalTransform>())
                .is_some_and(|(local, global)| {
                    (local.translation.y - global.translation().y - 0.15).abs() < 1e-6
                })
        });
    if waiting {
        world.resource_mut::<StagePropagationWitness>().0 = true;
    }
}
fn mirror_enabled(gate: Res<MirrorEnabled>) -> bool {
    gate.0
}
fn harness() -> App {
    let mut app = App::new();
    nvwa_runtime::register_b1_asset_source(&mut app);
    app.add_plugins((
        MinimalPlugins,
        AssetPlugin {
            file_path: format!("{}/../../assets", env!("CARGO_MANIFEST_DIR")),
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
    .init_asset::<bevy::gltf::Gltf>()
    .init_resource::<GlobalAmbientLight>()
    .init_resource::<ClearColor>()
    .insert_resource(nvwa_runtime::StartupDocumentPolicy::WaitForOpen)
    .add_plugins(nvwa_runtime::NvwaRuntimePlugin)
    .insert_resource(MirrorEnabled(true))
    .configure_sets(
        PostUpdate,
        nvwa_runtime::RuntimeSystems::Mirror.run_if(mirror_enabled),
    );
    app.init_resource::<StagePropagationWitness>().add_systems(
        PostUpdate,
        observe_real_stage_before_global_propagation
            .after(nvwa_runtime::RuntimeSystems::Mirror)
            .before(bevy::transform::TransformSystems::Propagate),
    );
    install_bridge(&mut app);
    app.finish();
    app.cleanup();
    app
}
fn open(app: &mut App, id: &str, work: &str) {
    app.world_mut()
        .resource_mut::<Bridge>()
        .incoming
        .push_back(json!({"request_id":id,"action":"open","work_json":work}).to_string());
}
fn until(app: &mut App, predicate: impl Fn(&World) -> bool) {
    let start = std::time::Instant::now();
    while !predicate(app.world()) && start.elapsed().as_secs_f32() < 20. {
        app.update();
        std::thread::yield_now();
    }
    assert!(
        predicate(app.world()),
        "bounded CPU readiness failed: {} {:?}",
        app.world().resource::<Bridge>().report,
        app.world().resource::<RuntimeStatus>()
    );
}
fn ready(world: &World, id: &str) -> bool {
    let r = &world.resource::<Bridge>().report;
    r["request_id"] == id && r["phase"] == "ready" && r["current"] == true
}
fn camera_y(world: &World) -> f64 {
    camera_report(world)["global_transform"][13]
        .as_f64()
        .unwrap()
}

#[test]
fn open_waits_for_actual_requested_stage_and_propagation_then_later_camera_change_is_stale() {
    let mut app = harness();
    open(
        &mut app,
        "reg-short",
        include_str!("../works/short-front.nvwa.json"),
    );
    until(&mut app, |w| ready(w, "reg-short"));
    let pinned: Value =
        serde_json::from_str(include_str!("../works/reference-short-front.json")).unwrap();
    let short_y = pinned["camera"]["global_transform"][13].as_f64().unwrap();
    // Establish the initial short stage independently of the old producer's
    // potentially premature first Open acknowledgement, then take a held ack.
    until(&mut app, |w| {
        (camera_y(w) - short_y).abs() < 1e-6 && appearance_status(w).ready
    });
    app.world_mut().resource_mut::<Bridge>().incoming.push_back(json!({"request_id":"reg-short-held","action":"playback","seek_seconds":0.0,"playing":false}).to_string());
    until(&mut app, |w| ready(w, "reg-short-held"));
    for _ in 0..2 {
        app.update();
        assert!(ready(app.world(), "reg-short-held"));
    }

    open(
        &mut app,
        "reg-long",
        include_str!("../works/long-front.nvwa.json"),
    );
    // Observe the real production publication boundary: the new Work/body has
    // committed after Mirror/transform propagation, while the camera is still old.
    until(&mut app, |w| {
        w.resource::<EditorState>()
            .document()
            .is_some_and(|d| d.character.parameters.get("torso_length") == Some(&1.0))
            && appearance_status(w).ready
    });
    assert_eq!(
        camera_y(app.world()),
        short_y,
        "must exercise actual old-camera publication boundary"
    );
    assert_eq!(
        app.world().resource::<Bridge>().report["phase"],
        "pending",
        "old producer acknowledges before the requested stage camera propagates"
    );
    // Hold the real Mirror schedule for three real update epochs. Identical old
    // camera/identity samples must never satisfy the requested-stage proof.
    app.world_mut().resource_mut::<MirrorEnabled>().0 = false;
    for _ in 0..3 {
        app.update();
        assert_eq!(camera_y(app.world()), short_y);
        assert_eq!(app.world().resource::<Bridge>().report["phase"], "pending");
    }
    app.world_mut().resource_mut::<MirrorEnabled>().0 = true;
    until(&mut app, |w| ready(w, "reg-long"));
    assert!((camera_y(app.world()) - short_y - 0.15).abs() < 1e-6);
    assert!(
        app.world().resource::<StagePropagationWitness>().0,
        "actual stage local write must be observed before real global propagation"
    );
    for _ in 0..4 {
        app.update();
        assert!(ready(app.world(), "reg-long"));
    }
    // A later actual local camera mutation must propagate and invalidate the
    // acknowledgement through the unchanged production-called stale guard.
    let entity = app
        .world()
        .iter_entities()
        .find(|e| e.contains::<nvwa_runtime::SceneCamera>())
        .unwrap()
        .id();
    app.world_mut()
        .get_mut::<Transform>(entity)
        .unwrap()
        .translation
        .y += 0.01;
    app.update();
    let bridge = app.world().resource::<Bridge>();
    assert_eq!(bridge.report["phase"], "stale");
    assert_eq!(bridge.report["current"], false);
    assert_eq!(bridge.report["request_succeeded"], true);
    assert!(bridge.frame.is_none());
}
