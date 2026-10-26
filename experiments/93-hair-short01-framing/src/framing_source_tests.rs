//! Two finite admissions and production-f32 camera/reference controls; no GPU.
use super::*;
use nvwa_core::SceneDocument;
use nvwa_runtime::{EditorState, StageViewOverride};

const WORKS: [&str; 2] = [
    include_str!("../works/plus-arms-framing160.nvwa.json"),
    include_str!("../works/plus-knee-framing160.nvwa.json"),
];
#[test]
fn only_explicit_framing_works_are_admitted() {
    for raw in WORKS {
        let mut work: Value = serde_json::from_str(raw).unwrap();
        assert!(allows_work_value(&work));
        assert_eq!(work["stage"]["camera"]["target_height"], json!(1.6));
        work["stage"]["camera"]["target_height"] = json!(1.61);
        assert!(!allows_work_value(&work));
    }
}
#[test]
fn framing_reference_matches_called_production_f32_camera_check() {
    let pinned: Value = serde_json::from_str(include_str!("../works/reference-plus-framing160.json")).unwrap();
    for raw in WORKS {
        let doc = SceneDocument::from_json(raw).unwrap();
        let mut editor = EditorState::default();
        editor.replace(doc).unwrap();
        let mut world = World::new();
        world.insert_resource(editor);
        world.insert_resource(StageViewOverride::default());
        let array: [f32; 16] = serde_json::from_value(pinned["camera"]["global_transform"].clone()).unwrap();
        let transform = Transform::from_matrix(Mat4::from_cols_array(&array));
        world.spawn((nvwa_runtime::SceneCamera, transform, GlobalTransform::from(transform), Projection::Perspective(PerspectiveProjection {
            fov: 30_f32.to_radians(), aspect_ratio: 1280. / 720., near: 0.05, far: 250., ..default()
        })));
        assert!(crate::open_stage_camera_is_current(&world));
    }
    let mut actual = pinned["camera"].clone();
    actual["viewport"] = actual["viewport_size_pixels"].clone();
    assert!(crate::pinned_camera_gate(&actual, &pinned).is_ok());
    actual["global_transform"][13] = json!(1.549719214439392_f64);
    assert!(crate::pinned_camera_gate(&actual, &pinned).is_err());
    actual["global_transform"][13] = json!(1.64971923828125_f64 + 0.00001);
    assert!(crate::pinned_camera_gate(&actual, &pinned).is_err());
}
