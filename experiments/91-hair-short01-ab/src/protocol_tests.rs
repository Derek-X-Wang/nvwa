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
        .is_some_and(|d| d.character.parameters.get("head_width") == Some(&1.0))
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
        include_str!("../works/default.nvwa.json"),
    );
    until(&mut app, |w| ready(w, "reg-short"));
    let pinned: Value =
        serde_json::from_str(include_str!("../works/reference-default.json")).unwrap();
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

    let mut next =
        SceneDocument::from_json(include_str!("../works/head-width-plus.nvwa.json")).unwrap();
    // A synthetic Open acknowledgement control changes stage height only.
    // It is not eligible for the frozen candidate capture matrix.
    next.stage.camera.target_height += 0.15;
    open(&mut app, "reg-long", &next.to_json().unwrap());
    // Observe the real production publication boundary: the new Work/body has
    // committed after Mirror/transform propagation, while the camera is still old.
    until(&mut app, |w| {
        w.resource::<EditorState>()
            .document()
            .is_some_and(|d| d.character.parameters.get("head_width") == Some(&1.0))
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

#[test]
fn retained_open_and_playback_errors_reject_actual_capture_settle() {
    for playback_failure in [false, true] {
        let mut app = harness();
        open(
            &mut app,
            "err-open",
            include_str!("../works/default.nvwa.json"),
        );
        until(&mut app, |w| ready(w, "err-open"));
        if playback_failure {
            app.world_mut().resource_mut::<Playback>().error =
                Some("retained playback failure".into());
        } else {
            app.world_mut().resource_mut::<EditorState>().open_error =
                Some("retained open failure".into());
        }
        app.world_mut()
            .resource_mut::<Bridge>()
            .incoming
            .push_back(json!({"request_id":"reject-capture","action":"capture"}).to_string());
        app.update();
        app.update();
        let r = &app.world().resource::<Bridge>().report;
        assert_eq!(r["phase"], "error");
        assert_eq!(r["current"], false);
        assert!(r["error"].as_str().unwrap().contains("retained"));
        assert!(app.world().resource::<Bridge>().frame.is_none());
    }
}

// This uses real raw-asset loading, production fitting and installed bridge
// schedules. The explicit viewport describes a CPU test camera; there is no
// window, renderer or GPU observation.
fn capture_harness() -> App {
    use bevy::camera::{CameraProjection, Viewport};
    let mut app = harness();
    open(
        &mut app,
        "image-open",
        include_str!("../works/default.nvwa.json"),
    );
    until(&mut app, |world| ready(world, "image-open"));
    let camera = app
        .world()
        .iter_entities()
        .find(|e| e.contains::<nvwa_runtime::SceneCamera>())
        .unwrap()
        .id();
    app.world_mut().get_mut::<Camera>(camera).unwrap().viewport = Some(Viewport {
        physical_position: UVec2::ZERO,
        physical_size: UVec2::new(1280, 720),
        depth: 0.0..1.0,
    });
    let mut projection = app.world_mut().get_mut::<Projection>(camera).unwrap();
    if let Projection::Perspective(p) = &mut *projection {
        p.update(1280., 720.);
    }
    drop(projection);
    app
}
fn capture_variant(app: &mut App, id: &str, variant: &str) {
    app.world_mut().resource_mut::<Bridge>().incoming.push_back(json!({"request_id":id,"action":"diagnostic","mode":"combined","palette":"textured","variant":variant}).to_string());
    until(app, |world| ready(world, id));
    assert!(app.world().resource::<Bridge>().frame.is_some());
    assert!(
        !FRAME.with(|f| f.borrow().is_empty()),
        "actual shared Web frame publisher must contain the established capture"
    );
}
fn hair_handles(world: &World) -> (Handle<Mesh>, Handle<Image>) {
    let material = world.resource::<Assets<StandardMaterial>>();
    let entity = world
        .iter_entities()
        .find(|e| {
            e.get::<Name>()
                .is_some_and(|n| n.as_str() == "B1 saved hair")
        })
        .unwrap();
    let mesh = entity.get::<Mesh3d>().unwrap().0.clone();
    let m = &entity.get::<MeshMaterial3d<StandardMaterial>>().unwrap().0;
    (
        mesh,
        material.get(m).unwrap().base_color_texture.clone().unwrap(),
    )
}
fn hair_arrays(world: &World, mesh: &Handle<Mesh>) -> Value {
    let m = world.resource::<Assets<Mesh>>().get(mesh).unwrap();
    let positions = match m.attribute(Mesh::ATTRIBUTE_POSITION) {
        Some(bevy::mesh::VertexAttributeValues::Float32x3(v)) => json!(v),
        _ => panic!("positions absent"),
    };
    let normals = match m.attribute(Mesh::ATTRIBUTE_NORMAL) {
        Some(bevy::mesh::VertexAttributeValues::Float32x3(v)) => json!(v),
        _ => panic!("normals absent"),
    };
    let uv = match m.attribute(Mesh::ATTRIBUTE_UV_0) {
        Some(bevy::mesh::VertexAttributeValues::Float32x2(v)) => json!(v),
        _ => panic!("UV absent"),
    };
    json!({"positions":positions,"normals":normals,"uv":uv,"indices":m.indices().unwrap().iter().collect::<Vec<_>>()})
}
#[test]
fn established_controller_capture_rejects_same_pixel_image_policy_mutations_and_clears_wire() {
    use bevy::image::ImageSampler;
    let mut app = capture_harness();
    capture_variant(&mut app, "image-a-baseline", "a_original");
    let (mesh, image) = hair_handles(app.world());
    let a_image = app
        .world()
        .resource::<Assets<Image>>()
        .get(&image)
        .unwrap()
        .clone();
    let a_arrays = hair_arrays(app.world(), &mesh);
    for (case, variant, mutation) in [
        ("a-sampler", "a_original", 0),
        ("b-sampler", "b_short01", 0),
        ("a-mip", "a_original", 1),
        ("b-mip", "b_short01", 1),
        ("a-view", "a_original", 2),
        ("b-view", "b_short01", 2),
    ] {
        capture_variant(&mut app, &format!("ready-{case}"), variant);
        let before = identity(app.world());
        let pixels = app
            .world()
            .resource::<Assets<Image>>()
            .get(&image)
            .unwrap()
            .data
            .clone();
        {
            let mut images = app.world_mut().resource_mut::<Assets<Image>>();
            let mut actual = images.get_mut(&image).unwrap();
            match mutation {
                0 => actual.sampler = ImageSampler::nearest(),
                1 => actual.texture_descriptor.mip_level_count = 2,
                _ => actual.texture_view_descriptor = Some(Default::default()),
            }
            assert_eq!(
                actual.data, pixels,
                "same original pixel bytes required for policy-only mutation"
            );
        }
        assert_ne!(
            identity(app.world()),
            before,
            "actual old-ready identity must observe the policy mutation"
        );
        app.update();
        let bridge = app.world().resource::<Bridge>();
        assert_eq!(bridge.report["phase"], "error", "{case}");
        assert_eq!(bridge.report["current"], false, "{case}");
        assert!(
            bridge.report["error"]
                .as_str()
                .unwrap()
                .contains("before restore"),
            "{case}: {}",
            bridge.report
        );
        assert!(bridge.frame.is_none(), "{case}");
        assert!(bridge.frame_export_key.is_empty(), "{case}");
        assert!(
            FRAME.with(|f| f.borrow().is_empty()),
            "actual shared transfer frame must be invalidated: {case}"
        );
        assert_eq!(
            REPORT.with(|r| serde_json::from_str::<Value>(&r.borrow()).unwrap())["current"],
            false,
            "{case}"
        );
        assert_eq!(
            app.world().resource::<Assets<Image>>().get(&image).unwrap(),
            &a_image,
            "exact original A image must be restored: {case}"
        );
        assert_eq!(
            hair_arrays(app.world(), &mesh),
            a_arrays,
            "exact original A mesh must be restored: {case}"
        );
    }
}
#[test]
fn steady_actual_controller_a_b_a_preserves_image_policy_and_restores_exact_a() {
    let mut app = capture_harness();
    capture_variant(&mut app, "steady-a1", "a_original");
    let (mesh, image) = hair_handles(app.world());
    let original = app
        .world()
        .resource::<Assets<Image>>()
        .get(&image)
        .unwrap()
        .clone();
    let arrays = hair_arrays(app.world(), &mesh);
    for _ in 0..3 {
        app.update();
        assert!(ready(app.world(), "steady-a1"));
    }
    capture_variant(&mut app, "steady-b", "b_short01");
    for _ in 0..3 {
        app.update();
        assert!(ready(app.world(), "steady-b"));
    }
    let current = app.world().resource::<Assets<Image>>().get(&image).unwrap();
    assert_eq!(
        candidate::image_policy(current),
        candidate::image_policy(&original)
    );
    assert_ne!(
        current.data, original.data,
        "B must actually bind its distinct source pixels"
    );
    assert_eq!(
        hair_arrays(app.world(), &mesh),
        arrays,
        "alpha-only B must preserve exact A source geometry"
    );
    capture_variant(&mut app, "steady-a2", "a_original");
    for _ in 0..3 {
        app.update();
        assert!(ready(app.world(), "steady-a2"));
    }
    assert_eq!(
        app.world().resource::<Assets<Image>>().get(&image).unwrap(),
        &original
    );
    assert_eq!(hair_arrays(app.world(), &mesh), arrays);
}
