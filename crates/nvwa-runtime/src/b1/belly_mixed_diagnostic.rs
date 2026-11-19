// Local, ignored differential diagnostic. The original strict test remains unchanged.
use super::*;
use serde_json::{Value, json};

const SOURCE_REST_REFERENCE_M: f64 = 1e-6;

#[derive(Default)]
struct Delta {
    rows: usize,
    components: usize,
    changed_rows: usize,
    changed_components: usize,
    maximum_abs: f64,
    maximum_row_l2: f64,
}

impl Delta {
    fn add_row(&mut self, left: &Value, right: &Value) {
        let left = left.as_array().expect("published numeric row");
        let right = right.as_array().expect("published numeric row");
        assert_eq!(left.len(), right.len(), "numeric row width");
        self.rows += 1;
        let mut sum = 0.0;
        for (l, r) in left.iter().zip(right) {
            let l = l.as_f64().expect("finite published component");
            let r = r.as_f64().expect("finite published component");
            assert!(l.is_finite() && r.is_finite());
            let d = (l - r).abs();
            assert!(d.is_finite());
            self.components += 1;
            self.changed_components += (d != 0.0) as usize;
            self.maximum_abs = self.maximum_abs.max(d);
            sum += d * d;
        }
        self.changed_rows += (sum != 0.0) as usize;
        self.maximum_row_l2 = self.maximum_row_l2.max(sum.sqrt());
    }

    fn report(&self) -> Value {
        json!({"rows":self.rows,"components":self.components,
               "changed_rows":self.changed_rows,"changed_components":self.changed_components,
               "max_abs":self.maximum_abs,"max_row_l2":self.maximum_row_l2})
    }
}

struct Capture {
    frame: Value,
    shape_weights: BTreeMap<&'static str, f32>,
}

fn capture(app: &mut App, doc: &SceneDocument) -> Capture {
    open_ready(app, doc.clone());
    let world = app.world();
    let active = world.resource::<B1Runtime>().active.as_ref().unwrap();
    assert!(active.selection == Selection::from_doc(doc));
    let templates = world.resource::<Assets<CharacterTemplate>>();
    let template = templates.get(&active.template).expect("active template");
    assert_eq!(template.shapes.len(), 1);
    let shape = &template.shapes[0];
    assert!(shape.helper_deltas.is_some(), "published baked template");
    let shape_weights: BTreeMap<_, _> = shape.morphs.iter().map(|(&key, &value)| (key, value)).collect();
    assert!(!shape_weights.contains_key(nvwa_core::B1_BELLY_SHAPE_TARGET.increase));
    let frame = b1_frame_snapshot(world).unwrap();
    assert_eq!(frame["diagnostic_pose"], json!("neutral"));
    Capture { frame, shape_weights }
}

fn compare(recipe: &str, comparison: &str, i: usize, left: &Capture, right: &Capture) {
    assert_eq!(left.shape_weights, right.shape_weights, "actual signed weights {comparison} {i}");
    let parts = |f: &Value| f.as_array().expect("published rows").len();
    let left_parts = &left.frame["parts"];
    let right_parts = &right.frame["parts"];
    assert_eq!(parts(left_parts), parts(right_parts));
    let mut reports = Vec::new();
    let mut influences_exact = true;
    for index in 0..parts(left_parts) {
        let l = &left_parts[index];
        let r = &right_parts[index];
        for key in ["name", "source_ids", "indices"] {
            // No assert_eq! here: it would dump potentially large buffers on failure.
            assert!(!l[key].is_null() && l[key] == r[key], "exact {key} {comparison} {i} part {index}");
        }
        assert!(!l["full_joint_influences"].is_null() && !r["full_joint_influences"].is_null());
        let part_influences_exact = l["full_joint_influences"] == r["full_joint_influences"];
        influences_exact &= part_influences_exact;
        let mut fields = serde_json::Map::new();
        for field in ["rest_positions", "positions"] {
            let la = l[field].as_array().unwrap();
            let ra = r[field].as_array().unwrap();
            assert!(!la.is_empty());
            assert_eq!(la.len(), ra.len(), "{field} vertex count");
            let mut delta = Delta::default();
            for (left, right) in la.iter().zip(ra) {
                delta.add_row(left, right);
            }
            fields.insert(field.into(), delta.report());
        }
        reports.push(json!({"part":l["name"],"indices":parts(&l["indices"]),
                            "source_ids":parts(&l["source_ids"]),"position_deltas":fields,
                            "full_influences_exact":part_influences_exact}));
    }
    let left_bones = left.frame["bones"].as_array().unwrap();
    let right_bones = right.frame["bones"].as_array().unwrap();
    assert_eq!(left_bones.len(), 53);
    assert_eq!(right_bones.len(), 53);
    for (l, r) in left_bones.iter().zip(right_bones) {
        assert_eq!(l["name"], r["name"]);
        assert_eq!(l["parent"], r["parent"]);
    }
    let mut bones = serde_json::Map::new();
    for field in ["rest", "posed", "inverse_bind", "local_rest", "local_posed", "skin",
                  "canonical_rest", "canonical_posed", "frame_gauge"] {
        let mut delta = Delta::default();
        for (l, r) in left_bones.iter().zip(right_bones) {
            assert_eq!(l[field].is_null(), r[field].is_null(), "{field} presence");
            if !l[field].is_null() {
                delta.add_row(&l[field], &r[field]);
            }
        }
        bones.insert(field.into(), delta.report());
    }
    println!("B1_BELLY_MIXED_DIAGNOSTIC {}", json!({
        "recipe": recipe, "comparison": comparison, "iteration": i,
        "topology_source_ids_exact": true, "full_influences_exact": influences_exact,
        "active_weights_exact": true, "active_weights": left.shape_weights,
        "model_rest_reference_m_diagnostic_only": SOURCE_REST_REFERENCE_M,
        "parts": reports, "bone_matrices": bones
    }));
}

#[test]
#[ignore = "explicit isolated diagnostic only; strict regression stays active and unchanged"]
fn belly_mixed_replay_diagnostic() {
    for recipe in ["neutral", "mixed"] {
        let mut old = SceneDocument::from_profile(
            nvwa_core::CharacterProfile::b1_character_chest_placement(),
        ).unwrap();
        let mut zero = SceneDocument::from_profile(
            nvwa_core::CharacterProfile::b1_character_belly_shape(),
        ).unwrap();
        for doc in [&mut old, &mut zero] {
            doc.character.diagnostic_pose = Some("neutral".into());
            if recipe == "mixed" {
                for (key, value) in [
                    ("waist_circumference", 0.3),
                    ("bust_circumference", 0.2),
                    ("hip_depth", 0.2),
                    ("breast_spacing", 0.4),
                    ("breast_vertical_position", -0.3),
                ] {
                    doc.character.parameters.insert(key.into(), value);
                }
            }
        }

        // Same runtime, explicitly reopened and baked each time, not the last live frame.
        let (mut app, dir, _) = motion_app();
        fill_version(&dir, B1AssetVersion::V10);
        fill_version(&dir, B1AssetVersion::V15);
        let base_v10 = capture(&mut app, &old);
        let base_v15 = capture(&mut app, &zero);
        compare(recipe, "same-app-v10-to-v15", 0, &base_v10, &base_v15);
        for i in 1..=3 {
            let next_v10 = capture(&mut app, &old);
            compare(recipe, "same-app-v10-reload", i, &base_v10, &next_v10);
            let next_v15 = capture(&mut app, &zero);
            compare(recipe, "same-app-v15-reload", i, &base_v15, &next_v15);
            compare(recipe, "same-app-v10-to-v15", i, &next_v10, &next_v15);
        }
        drop(app);

        // No V10/V15 extension handles are shared across these runtime worlds.
        let (mut app, dir, _) = motion_app();
        fill_version(&dir, B1AssetVersion::V10);
        let fresh_v10 = capture(&mut app, &old);
        compare(recipe, "fresh-app-v10-replay", 0, &base_v10, &fresh_v10);
        drop(app);
        let (mut app, dir, _) = motion_app();
        fill_version(&dir, B1AssetVersion::V15);
        let fresh_v15 = capture(&mut app, &zero);
        compare(recipe, "fresh-app-v15-replay", 0, &base_v15, &fresh_v15);
        compare(recipe, "fresh-app-v10-to-v15", 0, &fresh_v10, &fresh_v15);
    }
}
