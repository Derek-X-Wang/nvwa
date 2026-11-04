//! Match scene framing to the area left by the actual Studio/Player controls.
use super::{UiInputGuard, egui};
use bevy::prelude::*;
use nvwa_runtime::SceneCamera;

#[derive(Clone, Copy, Debug)]
pub(super) struct SceneViewport {
    pub canvas: egui::Rect,
    pub scene: egui::Rect,
}

pub(super) fn fit_scene_camera(
    guard: Res<UiInputGuard>,
    mut cameras: Query<&mut Camera, With<SceneCamera>>,
) {
    let sub_view = guard.scene_view.and_then(|view| {
        let scene = view.scene.intersect(view.canvas);
        if !view.canvas.is_finite()
            || !scene.is_finite()
            || view.canvas.width() <= 0.0
            || view.canvas.height() <= 0.0
            || scene.width() <= 0.0
            || scene.height() <= 0.0
        {
            return None;
        }
        // SubCameraView uses ratios, not physical pixels. Retain fractional
        // egui points with 1/64-point units, independent of window DPI.
        let units = 64.0;
        let full_size = (Vec2::new(scene.width(), scene.height()) * units)
            .round()
            .as_uvec2();
        let size = (Vec2::new(view.canvas.width(), view.canvas.height()) * units)
            .round()
            .as_uvec2();
        if full_size.min_element() == 0 || size.min_element() == 0 {
            return None;
        }
        Some(bevy::camera::SubCameraView {
            full_size,
            size,
            offset: Vec2::new(
                view.canvas.min.x - scene.min.x,
                view.canvas.min.y - scene.min.y,
            ) * units,
        })
    });
    for mut camera in &mut cameras {
        if camera.sub_camera_view != sub_view {
            camera.sub_camera_view = sub_view;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        CharacterInteraction, EditorState, EditorUiSession, PlatformIo, Playback, PlayerSession,
        RuntimeStatus, StageViewOverride, StudioUi, draw_editor_ui, draw_player,
    };
    use bevy::{
        asset::AssetEvent,
        render::{camera::camera_system, texture::ManualTextureViews},
        window::{PrimaryWindow, WindowCreated, WindowResized, WindowScaleFactorChanged},
    };
    use nvwa_core::{CharacterProfile, SceneDocument, StageCamera};

    fn production_ui(size: Vec2, player: bool) -> (UiInputGuard, SceneDocument) {
        let ctx = egui::Context::default();
        let mut editor = EditorState::default();
        editor
            .replace(
                SceneDocument::from_profile(
                    CharacterProfile::from_json(include_str!(
                        "../../../assets/character.profile.json"
                    ))
                    .unwrap(),
                )
                .unwrap(),
            )
            .unwrap();
        let before = editor.document().unwrap().clone();
        let retained = editor.editor.as_ref().unwrap().retention_stats();
        let mut state = StudioUi::default();
        let mut playback = Playback {
            clip_id: "idle".into(),
            ..default()
        };
        let mut io = PlatformIo::default();
        let mut guard = UiInputGuard::default();
        let mut view = StageViewOverride::default();
        for _ in 0..2 {
            ctx.run_ui(
                egui::RawInput {
                    screen_rect: Some(egui::Rect::from_min_size(
                        egui::Pos2::ZERO,
                        egui::vec2(size.x, size.y),
                    )),
                    ..default()
                },
                |ui| {
                    if player {
                        draw_player(
                            ui.ctx(),
                            &RuntimeStatus {
                                ready: true,
                                ..default()
                            },
                            &CharacterInteraction::default(),
                            PlayerSession {
                                editor: &editor,
                                playback: &mut playback,
                                state: &mut state,
                                io: &mut io,
                                guard: &mut guard,
                                view: &mut view,
                            },
                        );
                    } else {
                        draw_editor_ui(
                            ui.ctx(),
                            &RuntimeStatus {
                                ready: true,
                                ..default()
                            },
                            &CharacterInteraction::default(),
                            EditorUiSession {
                                editor: &mut editor,
                                playback: &mut playback,
                                state: &mut state,
                                io: &mut io,
                                guard: &mut guard,
                            },
                        )
                        .unwrap();
                    }
                },
            )
            .drop_without_applying_deltas();
        }
        assert_eq!(editor.document(), Some(&before));
        assert_eq!(editor.editor.as_ref().unwrap().retention_stats(), retained);
        (guard, before)
    }
    fn camera_app(size: Vec2, dpi: f32, guard: UiInputGuard, settings: &StageCamera) -> App {
        let azimuth = settings.azimuth_degrees.to_radians();
        let elevation = settings.elevation_degrees.to_radians();
        let target = Vec3::Y * settings.target_height;
        let eye = target
            + Vec3::new(
                azimuth.sin() * elevation.cos(),
                elevation.sin(),
                azimuth.cos() * elevation.cos(),
            ) * settings.distance;
        let transform = Transform::from_translation(eye).looking_at(target, Vec3::Y);
        let mut app = App::new();
        app.add_message::<WindowResized>()
            .add_message::<WindowCreated>()
            .add_message::<WindowScaleFactorChanged>()
            .add_message::<AssetEvent<Image>>()
            .init_resource::<Assets<Image>>()
            .init_resource::<ManualTextureViews>()
            .insert_resource(guard)
            .add_systems(Update, (fit_scene_camera, camera_system).chain());
        app.world_mut().spawn((
            PrimaryWindow,
            Window {
                resolution: bevy::window::WindowResolution::new(
                    (size.x * dpi) as u32,
                    (size.y * dpi) as u32,
                )
                .with_scale_factor_override(dpi),
                ..default()
            },
        ));
        app.world_mut().spawn((
            SceneCamera,
            Camera3d::default(),
            Projection::Perspective(PerspectiveProjection {
                fov: settings.fov_degrees.to_radians(),
                near: 0.05,
                ..default()
            }),
            transform,
            GlobalTransform::from(transform),
        ));
        app.update();
        app
    }
    fn assert_points_and_picking(app: &mut App, points: &[Vec3], label: &str) {
        let rect = app
            .world()
            .resource::<UiInputGuard>()
            .scene_view
            .unwrap()
            .scene;
        let world = app.world_mut();
        let (camera, transform) = world
            .query_filtered::<(&Camera, &GlobalTransform), With<SceneCamera>>()
            .single(world)
            .unwrap();
        assert!(
            camera.viewport.is_none(),
            "egui retains a full-window camera viewport"
        );
        for &point in points {
            let projected = camera.world_to_viewport(transform, point).unwrap();
            assert!(
                rect.contains(egui::pos2(projected.x, projected.y)),
                "{label}: world{point:?} projects{projected:?} outside actual scene{rect:?}"
            );
            let ray = camera.viewport_to_world(transform, projected).unwrap();
            let distance = (point - ray.origin).length();
            let reconstructed = ray.origin + *ray.direction * distance;
            assert!(
                reconstructed.abs_diff_eq(point, 1e-4),
                "{label}: picking ray diverged from rendered point {point:?}: {reconstructed:?}"
            );
        }
    }
    #[test]
    fn full_body_head_and_feet_fit_real_studio_player_rect_and_pick_correctly() {
        // Conservative world bounds from the original fixture's authored head
        // and feet, independent of panel sizes and projection implementation.
        let points: Vec<_> = [-0.25, 0.25]
            .into_iter()
            .flat_map(|x| {
                [(0.0, -0.20), (0.0, 0.15), (1.90, -0.19), (1.90, 0.19)]
                    .into_iter()
                    .map(move |(y, z)| Vec3::new(x, y, z))
            })
            .collect();
        for (size, player, dpi) in [
            (Vec2::new(1280.0, 720.0), false, 1.0),
            (Vec2::new(1024.0, 768.0), false, 1.0),
            (Vec2::new(1280.0, 720.0), true, 1.0),
            (Vec2::new(1280.0, 720.0), false, 2.0),
        ] {
            let (guard, document) = production_ui(size, player);
            let mut app = camera_app(size, dpi, guard, &document.stage.camera);
            assert_points_and_picking(
                &mut app,
                &points,
                &format!("player={player} size={size:?} dpi={dpi}"),
            );
        }
    }
    #[test]
    fn detail_preset_keeps_fixture_head_inside_available_scene() {
        // Original fixture construction: head center1.65, half-height0.225;
        // include a small remesh/pose margin and the nose/ear depth bounds.
        let points: Vec<_> = [-0.22, 0.22]
            .into_iter()
            .flat_map(|x| {
                [1.425, 1.89]
                    .into_iter()
                    .flat_map(move |y| [-0.19, 0.19].into_iter().map(move |z| Vec3::new(x, y, z)))
            })
            .collect();
        for (size, player) in [
            (Vec2::new(1280.0, 720.0), false),
            (Vec2::new(1024.0, 768.0), false),
            (Vec2::new(1280.0, 720.0), true),
        ] {
            let (guard, _) = production_ui(size, player);
            let mut app = camera_app(size, 1.0, guard, &StageCamera::detail());
            assert_points_and_picking(
                &mut app,
                &points,
                &format!("detail player={player} size={size:?}"),
            );
        }
    }
}
