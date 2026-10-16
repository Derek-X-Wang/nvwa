//! The production stage mirror, shared by native/Web Studio and Player.
use super::{EditorState, RuntimeStatus, SceneCamera};
use bevy::ecs::system::SystemParam;
use bevy::{
    core_pipeline::{prepass::DepthPrepass, tonemapping::Tonemapping},
    light::{CascadeShadowConfig, CascadeShadowConfigBuilder, DirectionalLightShadowMap},
    pbr::ContactShadows,
    prelude::*,
};
use nvwa_core::{StageCamera, StageLight, StageQuality, StageSettings};

#[derive(Component)]
struct KeyLight;
#[derive(Component)]
struct FillLight;
#[derive(Component)]
struct StageFloor;

/// Player-only temporary orbit. Opening another Work always clears it.
#[derive(Resource, Default)]
pub struct StageViewOverride {
    camera: Option<StageCamera>,
    generation: u64,
}
impl StageViewOverride {
    pub fn camera<'a>(&'a self, editor: &'a EditorState) -> Option<&'a StageCamera> {
        self.camera
            .as_ref()
            .filter(|_| self.generation == editor.document_generation)
            .or_else(|| editor.visible_document().map(|d| &d.stage.camera))
    }
    pub fn set(&mut self, editor: &EditorState, camera: StageCamera) -> Result<(), String> {
        camera.validate().map_err(|e| e.to_string())?;
        self.generation = editor.document_generation;
        self.camera = Some(camera);
        Ok(())
    }
    pub fn reset(&mut self) {
        self.camera = None;
    }
}

fn color(rgb: [f32; 3]) -> Color {
    Color::srgb(rgb[0], rgb[1], rgb[2])
}
fn orbit(azimuth: f32, elevation: f32) -> Vec3 {
    let (azimuth, elevation) = (azimuth.to_radians(), elevation.to_radians());
    Vec3::new(
        azimuth.sin() * elevation.cos(),
        elevation.sin(),
        azimuth.cos() * elevation.cos(),
    )
}
fn camera_transform(camera: &StageCamera, scale: f32) -> Transform {
    let target = Vec3::Y * camera.target_height * scale;
    Transform::from_translation(
        target + orbit(camera.azimuth_degrees, camera.elevation_degrees) * camera.distance * scale,
    )
    .looking_at(target, Vec3::Y)
}
fn light_transform(light: &StageLight) -> Transform {
    Transform::from_translation(orbit(light.azimuth_degrees, light.elevation_degrees))
        .looking_at(Vec3::ZERO, Vec3::Y)
}

pub(super) fn setup_environment(
    mut commands: Commands,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
) {
    let stage = StageSettings::default();
    commands.insert_resource(ClearColor(color(stage.background_color_srgb)));
    commands.insert_resource(GlobalAmbientLight::default());
    commands.insert_resource(DirectionalLightShadowMap { size: 2048 });
    commands.spawn((
        SceneCamera,
        Camera3d::default(),
        Tonemapping::Reinhard,
        Msaa::Sample4,
        camera_transform(&stage.camera, 1.0),
    ));
    commands.spawn((
        KeyLight,
        DirectionalLight::default(),
        CascadeShadowConfigBuilder {
            num_cascades: 1,
            minimum_distance: 0.05,
            maximum_distance: 40.0,
            ..default()
        }
        .build(),
        light_transform(&stage.key_light),
    ));
    commands.spawn((
        FillLight,
        DirectionalLight::default(),
        light_transform(&stage.fill_light),
    ));
    commands.spawn((
        StageFloor,
        Visibility::Inherited,
        Mesh3d(meshes.add(Plane3d::default().mesh().size(200.0, 200.0))),
        MeshMaterial3d(materials.add(StandardMaterial {
            base_color: color(stage.floor.color_srgb),
            perceptual_roughness: 0.88,
            metallic: 0.0,
            ..default()
        })),
        Transform::IDENTITY,
    ));
}

#[derive(SystemParam)]
pub(super) struct StageMirror<'w, 's> {
    cameras: Query<
        'w,
        's,
        (
            Entity,
            &'static mut Transform,
            &'static mut Projection,
            &'static mut Msaa,
        ),
        (With<SceneCamera>, Without<KeyLight>, Without<FillLight>),
    >,
    key: Query<
        'w,
        's,
        (
            &'static mut DirectionalLight,
            &'static mut Transform,
            &'static mut CascadeShadowConfig,
        ),
        (With<KeyLight>, Without<SceneCamera>, Without<FillLight>),
    >,
    fill: Query<
        'w,
        's,
        (&'static mut DirectionalLight, &'static mut Transform),
        (With<FillLight>, Without<SceneCamera>, Without<KeyLight>),
    >,
    floor: Query<
        'w,
        's,
        (
            &'static MeshMaterial3d<StandardMaterial>,
            &'static mut Visibility,
        ),
        With<StageFloor>,
    >,
}

pub(super) fn apply_stage(
    mut commands: Commands,
    editor: Res<EditorState>,
    mut view: ResMut<StageViewOverride>,
    mut mirror: StageMirror,
    mut materials: ResMut<Assets<StandardMaterial>>,
    mut clear: ResMut<ClearColor>,
    mut ambient: ResMut<GlobalAmbientLight>,
    mut shadow_map: ResMut<DirectionalLightShadowMap>,
    mut prior: Local<Option<(StageSettings, u64, f32)>>,
    mut status: ResMut<RuntimeStatus>,
) {
    let Some(document) = editor.visible_document() else {
        return;
    };
    if view.generation != editor.document_generation {
        view.reset();
    }
    let mut stage = document.stage.clone();
    if let Some(camera) = &view.camera {
        stage.camera = camera.clone();
    }
    if prior.as_ref().is_some_and(|(previous, generation, scale)| {
        previous == &stage
            && *generation == editor.document_generation
            && *scale == document.character.scale
    }) {
        status.stage_error = None;
        return;
    }
    // Restrict only runtime conversion precision, never the portable scale contract.
    // This fixed stage is not an arbitrary-coordinate-world renderer.
    let scale = document.character.scale;
    if !(0.001..=100.0).contains(&scale) {
        status.stage_error = Some(format!(
            "Stage camera cannot represent character scale {scale}; supported presentation scale is 0.001..=100. Work is unchanged."
        ));
        return;
    }
    let camera = camera_transform(&stage.camera, scale);
    let near = 0.05 * scale;
    let far = 250.0 * scale;
    if !camera.translation.is_finite()
        || !camera.rotation.is_finite()
        || !near.is_finite()
        || !far.is_finite()
        || near <= 0.0
        || far <= near
    {
        status.stage_error =
            Some("Stage camera conversion is nonfinite; Work is unchanged.".into());
        return;
    }
    status.stage_error = None;
    clear.0 = color(stage.background_color_srgb);
    ambient.color = color(stage.ambient.color_srgb);
    ambient.brightness = stage.ambient.brightness;
    shadow_map.size = match stage.quality {
        StageQuality::Low => 1024,
        StageQuality::Balanced => 2048,
        StageQuality::High => 4096,
    };
    let shadows = stage.floor.shadows && stage.quality != StageQuality::Low;
    let contact = shadows && stage.quality == StageQuality::High;
    for (mut light, mut transform, mut cascades) in &mut mirror.key {
        light.color = color(stage.key_light.color_srgb);
        light.illuminance = stage.key_light.illuminance_lux;
        light.shadow_maps_enabled = shadows;
        light.contact_shadows_enabled = contact;
        // Tight cascade and modest normal bias keep contact near the feet.
        light.shadow_depth_bias = 0.02 * scale;
        light.shadow_normal_bias = 0.6;
        *transform = light_transform(&stage.key_light);
        *cascades = CascadeShadowConfigBuilder {
            num_cascades: 1,
            minimum_distance: 0.05 * scale,
            maximum_distance: 40.0 * scale,
            ..default()
        }
        .build();
    }
    for (mut light, mut transform) in &mut mirror.fill {
        light.color = color(stage.fill_light.color_srgb);
        light.illuminance = stage.fill_light.illuminance_lux;
        light.shadow_maps_enabled = false;
        light.contact_shadows_enabled = false;
        *transform = light_transform(&stage.fill_light);
    }
    for (handle, mut visibility) in &mut mirror.floor {
        *visibility = if stage.floor.visible {
            Visibility::Inherited
        } else {
            Visibility::Hidden
        };
        if let Some(mut material) = materials.get_mut(&handle.0) {
            material.base_color = color(stage.floor.color_srgb);
        }
    }
    for (entity, mut transform, mut projection, mut msaa) in &mut mirror.cameras {
        *transform = camera;
        if let Projection::Perspective(perspective) = &mut *projection {
            perspective.fov = stage.camera.fov_degrees.to_radians();
            perspective.near = near;
            perspective.far = far;
        }
        *msaa = if stage.quality == StageQuality::Low {
            Msaa::Off
        } else {
            Msaa::Sample4
        };
        if contact {
            commands.entity(entity).insert(ContactShadows {
                linear_steps: 16,
                thickness: 0.04 * scale,
                length: 0.25 * scale,
            });
        } else {
            commands
                .entity(entity)
                .remove::<(ContactShadows, DepthPrepass)>();
        }
    }
    *prior = Some((stage, editor.document_generation, scale));
}

#[cfg(test)]
mod tests {
    use super::*;
    use nvwa_core::{CharacterProfile, Command, SceneDocument};
    fn app() -> App {
        let mut app = App::new();
        app.init_resource::<Assets<Mesh>>()
            .init_resource::<Assets<StandardMaterial>>()
            .init_resource::<EditorState>()
            .init_resource::<RuntimeStatus>()
            .init_resource::<StageViewOverride>()
            .add_systems(Startup, setup_environment)
            .add_systems(Update, apply_stage);
        let document = SceneDocument::from_profile(
            CharacterProfile::from_json(include_str!("../../../assets/character.profile.json"))
                .unwrap(),
        )
        .unwrap();
        app.world_mut()
            .resource_mut::<EditorState>()
            .replace(document)
            .unwrap();
        app.update();
        app
    }
    #[test]
    fn production_mirror_applies_lights_camera_floor_and_quality_profiles() {
        let mut app = app();
        for (quality, size, msaa, shadows, contact) in [
            (StageQuality::Low, 1024, Msaa::Off, false, false),
            (StageQuality::Balanced, 2048, Msaa::Sample4, true, false),
            (StageQuality::High, 4096, Msaa::Sample4, true, true),
        ] {
            let mut stage = StageSettings::black_space();
            stage.quality = quality;
            stage.camera = StageCamera::detail();
            stage.floor.color_srgb = [0.2, 0.3, 0.4];
            app.world_mut()
                .resource_mut::<EditorState>()
                .apply(Command::SetStage {
                    stage: stage.clone(),
                })
                .unwrap();
            app.update();
            assert_eq!(
                app.world().resource::<ClearColor>().0,
                color(stage.background_color_srgb)
            );
            assert_eq!(
                app.world().resource::<GlobalAmbientLight>().brightness,
                95.0
            );
            assert_eq!(
                app.world().resource::<DirectionalLightShadowMap>().size,
                size
            );
            let world = app.world_mut();
            let (light, transform) = world
                .query_filtered::<(&DirectionalLight, &Transform), With<KeyLight>>()
                .single(world)
                .unwrap();
            assert_eq!(light.illuminance, 12000.0);
            assert_eq!(light.color, color(stage.key_light.color_srgb));
            assert_eq!(light.shadow_maps_enabled, shadows);
            assert_eq!(light.contact_shadows_enabled, contact);
            assert_eq!(*transform, light_transform(&stage.key_light));
            let fill = world
                .query_filtered::<&DirectionalLight, With<FillLight>>()
                .single(world)
                .unwrap();
            assert_eq!(fill.illuminance, 4500.0);
            assert!(!fill.shadow_maps_enabled);
            let (transform, projection, samples, contacts, depth) = world
                .query_filtered::<(
                    &Transform,
                    &Projection,
                    &Msaa,
                    Option<&ContactShadows>,
                    Option<&DepthPrepass>,
                ), With<SceneCamera>>()
                .single(world)
                .unwrap();
            assert_eq!(*transform, camera_transform(&stage.camera, 1.0));
            assert_eq!(*samples, msaa);
            assert_eq!(contacts.is_some(), contact);
            assert_eq!(depth.is_some(), contact);
            let Projection::Perspective(p) = projection else {
                panic!("perspective camera")
            };
            assert_eq!(p.fov, 30.0_f32.to_radians());
            let (handle,transform)=world.query_filtered::<(&MeshMaterial3d<StandardMaterial>,&Transform),With<StageFloor>>().single(world).unwrap();
            assert_eq!(transform.translation.y, 0.0);
            assert_eq!(
                world
                    .resource::<Assets<StandardMaterial>>()
                    .get(&handle.0)
                    .unwrap()
                    .base_color,
                color([0.2, 0.3, 0.4])
            );
        }
        let mut stage = StageSettings::default();
        stage.floor.visible = false;
        stage.floor.shadows = false;
        stage.quality = StageQuality::High;
        app.world_mut()
            .resource_mut::<EditorState>()
            .apply(Command::SetStage { stage })
            .unwrap();
        app.update();
        let world = app.world_mut();
        assert_eq!(
            *world
                .query_filtered::<&Visibility, With<StageFloor>>()
                .single(world)
                .unwrap(),
            Visibility::Hidden
        );
        assert!(
            !world
                .query_filtered::<&DirectionalLight, With<KeyLight>>()
                .single(world)
                .unwrap()
                .shadow_maps_enabled
        );
    }
    #[test]
    fn stage_preview_cancel_commit_and_player_override_preserve_work() {
        let mut app = app();
        let initial = app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .clone();
        for brightness in [300.0, 500.0, 700.0] {
            let mut stage = initial.stage.clone();
            stage.ambient.brightness = brightness;
            app.world_mut()
                .resource_mut::<EditorState>()
                .preview_stage(stage)
                .unwrap();
            app.update();
            assert_eq!(
                app.world().resource::<GlobalAmbientLight>().brightness,
                brightness
            );
            assert_eq!(
                app.world().resource::<EditorState>().document(),
                Some(&initial)
            );
        }
        app.world_mut()
            .resource_mut::<EditorState>()
            .cancel_preview();
        app.update();
        assert_eq!(
            app.world().resource::<GlobalAmbientLight>().brightness,
            initial.stage.ambient.brightness
        );
        app.world_mut()
            .resource_mut::<EditorState>()
            .preview_stage(StageSettings::black_space())
            .unwrap();
        app.world_mut()
            .resource_mut::<EditorState>()
            .commit_preview()
            .unwrap();
        app.update();
        assert_eq!(
            app.world()
                .resource::<EditorState>()
                .document()
                .unwrap()
                .revision,
            1
        );
        app.world_mut()
            .resource_mut::<EditorState>()
            .apply(Command::Undo)
            .unwrap();
        app.update();
        assert_eq!(
            app.world()
                .resource::<EditorState>()
                .document()
                .unwrap()
                .stage,
            initial.stage
        );
        let prior = app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .clone();
        app.world_mut()
            .resource_scope(|world, mut view: Mut<StageViewOverride>| {
                view.set(world.resource::<EditorState>(), StageCamera::detail())
                    .unwrap()
            });
        app.update();
        assert_eq!(
            app.world().resource::<EditorState>().document(),
            Some(&prior)
        );
        app.world_mut()
            .resource_mut::<EditorState>()
            .replace(prior.clone())
            .unwrap();
        app.update();
        assert!(app.world().resource::<StageViewOverride>().camera.is_none());
    }
}

#[cfg(test)]
mod scale_tests {
    use super::*;
    use nvwa_core::{CharacterProfile, Command, SceneDocument};
    #[test]
    fn normalized_camera_scales_and_extreme_scale_error_are_on_production_path() {
        let mut app = App::new();
        app.init_resource::<Assets<Mesh>>()
            .init_resource::<Assets<StandardMaterial>>()
            .init_resource::<EditorState>()
            .init_resource::<RuntimeStatus>()
            .init_resource::<StageViewOverride>()
            .add_systems(Startup, setup_environment)
            .add_systems(Update, apply_stage);
        let document = SceneDocument::from_profile(
            CharacterProfile::from_json(include_str!("../../../assets/character.profile.json"))
                .unwrap(),
        )
        .unwrap();
        app.world_mut()
            .resource_mut::<EditorState>()
            .replace(document)
            .unwrap();
        let mut stage = StageSettings::default();
        stage.quality = StageQuality::High;
        app.world_mut()
            .resource_mut::<EditorState>()
            .apply(Command::SetStage { stage })
            .unwrap();
        for scale in [0.001, 0.5, 1.0, 2.0, 100.0] {
            app.world_mut()
                .resource_mut::<EditorState>()
                .apply(Command::SetScale {
                    character_id: "character-1".into(),
                    scale,
                })
                .unwrap();
            app.update();
            assert!(
                app.world()
                    .resource::<RuntimeStatus>()
                    .stage_error
                    .is_none()
            );
            let world = app.world_mut();
            let (transform, projection) = world
                .query_filtered::<(&Transform, &Projection), With<SceneCamera>>()
                .single(world)
                .unwrap();
            assert_eq!(
                *transform,
                camera_transform(&StageCamera::full_body(), scale)
            );
            let Projection::Perspective(p) = projection else {
                panic!("perspective")
            };
            assert_eq!(p.near, 0.05 * scale);
            assert_eq!(p.far, 250.0 * scale);
            let (key, cascades) = world
                .query_filtered::<(&DirectionalLight, &CascadeShadowConfig), With<KeyLight>>()
                .single(world)
                .unwrap();
            assert!(key.shadow_maps_enabled);
            assert!(key.contact_shadows_enabled);
            assert_eq!(key.shadow_depth_bias, 0.02 * scale);
            assert_eq!(cascades.minimum_distance, 0.05 * scale);
            assert_eq!(cascades.bounds, vec![40.0 * scale]);
            // The full-body subject distance must remain inside the cascade,
            // including both accepted rendering-scale boundaries.
            assert!(cascades.minimum_distance < 3.8 * scale && cascades.bounds[0] > 3.8 * scale);
            let contact = world
                .query_filtered::<&ContactShadows, With<SceneCamera>>()
                .single(world)
                .unwrap();
            assert_eq!(contact.length, 0.25 * scale);
            assert_eq!(contact.thickness, 0.04 * scale);
        }
        let old_transform = *app
            .world_mut()
            .query_filtered::<&Transform, With<SceneCamera>>()
            .single(app.world())
            .unwrap();
        for extreme in [f32::MAX, f32::MIN_POSITIVE] {
            app.world_mut()
                .resource_mut::<EditorState>()
                .apply(Command::SetScale {
                    character_id: "character-1".into(),
                    scale: extreme,
                })
                .unwrap();
            app.update();
            assert!(
                app.world()
                    .resource::<RuntimeStatus>()
                    .stage_error
                    .as_deref()
                    .unwrap()
                    .contains("Work is unchanged")
            );
            assert_eq!(
                app.world()
                    .resource::<EditorState>()
                    .document()
                    .unwrap()
                    .character
                    .scale,
                extreme
            );
            let world = app.world_mut();
            let transform = world
                .query_filtered::<&Transform, With<SceneCamera>>()
                .single(world)
                .unwrap();
            assert_eq!(*transform, old_transform);
            assert!(transform.translation.is_finite());
            assert!(transform.rotation.is_finite());
        }
        app.world_mut()
            .resource_mut::<EditorState>()
            .apply(Command::SetScale {
                character_id: "character-1".into(),
                scale: 1.0,
            })
            .unwrap();
        app.update();
        assert!(
            app.world()
                .resource::<RuntimeStatus>()
                .stage_error
                .is_none()
        );
    }
}
