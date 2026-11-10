#![cfg(feature = "cpu-render")]
//! Real CLI, assets and CPU runtime; no browser, display server or mock mesh.
use nvwa_core::{CharacterAppearance, CharacterProfile, SceneDocument};
use serde_json::Value;
use std::{
    path::{Path, PathBuf},
    process::{Command, Output},
};
struct Trial(PathBuf);
impl Trial {
    fn new() -> Self {
        static NEXT_DIR: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
        let sequence = NEXT_DIR.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        let n = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let path =
            std::env::temp_dir().join(format!("nvwa-cpu-{}-{n}-{sequence}", std::process::id()));
        std::fs::create_dir(&path).unwrap();
        Self(path)
    }
    fn work(&self, name: &str, doc: &SceneDocument) -> PathBuf {
        let path = self.0.join(format!("{name}.json"));
        std::fs::write(&path, doc.to_json().unwrap()).unwrap();
        path
    }
}
impl Drop for Trial {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}
fn assets() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../assets")
}
fn render(work: &Path, root: &Path, out: &Path) -> Output {
    Command::new(env!("CARGO_BIN_EXE_nvwa-cli"))
        .args([
            "render".as_ref(),
            work,
            "--assets".as_ref(),
            root,
            "--output".as_ref(),
            out,
            "--width".as_ref(),
            "320".as_ref(),
            "--height".as_ref(),
            "320".as_ref(),
        ])
        .env_remove("DISPLAY")
        .env_remove("WAYLAND_DISPLAY")
        .output()
        .unwrap()
}
fn render_body(work: &Path, root: &Path, out: &Path) -> Output {
    Command::new(env!("CARGO_BIN_EXE_nvwa-cli"))
        .args([
            "render".as_ref(),
            work,
            "--assets".as_ref(),
            root,
            "--output".as_ref(),
            out,
            "--width".as_ref(),
            "320".as_ref(),
            "--height".as_ref(),
            "320".as_ref(),
            "--mode".as_ref(),
            "body-reference".as_ref(),
        ])
        .env_remove("DISPLAY")
        .env_remove("WAYLAND_DISPLAY")
        .output()
        .unwrap()
}
fn success(output: Output) -> Value {
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(output.stderr.is_empty());
    serde_json::from_slice::<Value>(&output.stdout).unwrap()["receipt"].clone()
}
fn reject(output: Output, code: &str) {
    assert_eq!(output.status.code(), Some(1));
    assert!(output.stdout.is_empty());
    let e: Value = serde_json::from_slice(&output.stderr).unwrap();
    assert_eq!(e["code"], code, "{e}");
}
fn neutral() -> SceneDocument {
    let mut doc = SceneDocument::from_profile(CharacterProfile::b1_character()).unwrap();
    doc.timeline.clear();
    doc.stage.camera.azimuth_degrees = 0.0;
    doc.stage.camera.elevation_degrees = 0.0;
    doc
}
#[test]
fn real_cpu_export_repeats_preserves_work_and_obeys_saved_camera_shape_and_pose() {
    let t = Trial::new();
    let mut doc = neutral();
    let work = t.work("front", &doc);
    let before = std::fs::read(&work).unwrap();
    let front = success(render(&work, &assets(), &t.0.join("front")));
    let repeat = success(render(&work, &assets(), &t.0.join("repeat")));
    assert_eq!(front["png_sha256"], repeat["png_sha256"]);
    assert_eq!(front["geometry_sha256"], repeat["geometry_sha256"]);
    assert_eq!(front["parts"].as_array().unwrap().len(), 2);
    assert!(front["covered_pixels"].as_u64().unwrap() > 100);
    assert_eq!(std::fs::read(&work).unwrap(), before);
    assert_eq!(
        std::fs::read(t.0.join("front/work.nvwa.json")).unwrap(),
        before
    );
    let original = std::fs::read(t.0.join("front/actual.png")).unwrap();
    reject(
        render(&work, &assets(), &t.0.join("front")),
        "output_exists",
    );
    assert_eq!(
        std::fs::read(t.0.join("front/actual.png")).unwrap(),
        original
    );
    doc.stage.camera.azimuth_degrees = 90.0;
    let side = success(render(&t.work("side", &doc), &assets(), &t.0.join("side")));
    assert_eq!(front["geometry_sha256"], side["geometry_sha256"]);
    assert_ne!(front["png_sha256"], side["png_sha256"]);
    assert_eq!(side["camera"]["azimuth_degrees"], 90.0);
    doc.stage.camera.azimuth_degrees = 0.0;
    doc.character.parameters.insert("hip_width".into(), 1.0);
    let wide = success(render(&t.work("wide", &doc), &assets(), &t.0.join("wide")));
    assert_ne!(front["geometry_sha256"], wide["geometry_sha256"]);
    assert_ne!(front["png_sha256"], wide["png_sha256"]);
    doc.character.diagnostic_pose = Some("knee".into());
    let knee = success(render(&t.work("knee", &doc), &assets(), &t.0.join("knee")));
    assert_ne!(wide["geometry_sha256"], knee["geometry_sha256"]);
    assert_ne!(wide["png_sha256"], knee["png_sha256"]);
}

#[test]
fn body_reference_restores_clothing_hidden_body_across_views_and_pose() {
    let t = Trial::new();
    let mut doc = neutral();
    doc.stage.camera.distance = 4.2;
    doc.stage.camera.target_height = 0.95;
    let front_work = t.work("body-front", &doc);
    let combined = success(render(&front_work, &assets(), &t.0.join("combined-front")));
    let front = success(render_body(&front_work, &assets(), &t.0.join("body-front")));
    assert_eq!(combined["mode"], "silhouette");
    assert_eq!(combined["parts"].as_array().unwrap().len(), 2);
    assert_eq!(front["mode"], "body_reference");
    assert_eq!(front["parts"].as_array().unwrap().len(), 1);
    assert_eq!(front["parts"][0][0], "body");
    assert_eq!(front["parts"][0][1], combined["parts"][0][1]);
    assert!(front["parts"][0][2].as_u64().unwrap() > combined["parts"][0][2].as_u64().unwrap());
    assert!(front["covered_pixels"].as_u64().unwrap() > 100);
    assert_ne!(front["png_sha256"], combined["png_sha256"]);
    assert_eq!(
        front["body_topology"],
        "full_fitted_body_restored_clothing_hidden_triangles_same_skinned_frame"
    );
    assert_eq!(
        std::fs::read(&front_work).unwrap(),
        std::fs::read(t.0.join("body-front/work.nvwa.json")).unwrap()
    );
    reject(
        render_body(&front_work, &assets(), &t.0.join("body-front")),
        "output_exists",
    );

    let mut views = std::collections::BTreeSet::new();
    views.insert(front["png_sha256"].as_str().unwrap().to_owned());
    let mut side_png = None;
    for (name, azimuth) in [("quarter", 45.0), ("side", 90.0), ("back", 180.0)] {
        doc.stage.camera.azimuth_degrees = azimuth;
        let work = t.work(&format!("body-{name}"), &doc);
        let image = success(render_body(
            &work,
            &assets(),
            &t.0.join(format!("body-{name}")),
        ));
        assert_eq!(image["parts"].as_array().unwrap().len(), 1);
        assert_eq!(image["parts"][0][2], front["parts"][0][2]);
        assert_eq!(image["camera"]["azimuth_degrees"], azimuth);
        assert!(image["covered_pixels"].as_u64().unwrap() > 100);
        if name == "side" {
            side_png = Some(image["png_sha256"].clone());
        }
        views.insert(image["png_sha256"].as_str().unwrap().to_owned());
    }
    assert!(
        views.len() >= 3,
        "body reference views should retain distinct perspectives"
    );
    doc.stage.camera.azimuth_degrees = 90.0;
    doc.character.diagnostic_pose = Some("knee".into());
    let knee = success(render_body(
        &t.work("body-knee", &doc),
        &assets(),
        &t.0.join("body-knee"),
    ));
    assert_eq!(knee["parts"].as_array().unwrap().len(), 1);
    assert_ne!(Some(knee["png_sha256"].clone()), side_png);
}

#[test]
fn body_reference_shows_waist_hip_and_leg_recipe_without_garment() {
    let t = Trial::new();
    let mut doc =
        SceneDocument::from_profile(CharacterProfile::b1_character_hip_contour()).unwrap();
    doc.stage.camera.distance = 4.2;
    doc.stage.camera.target_height = 0.95;
    doc.stage.camera.elevation_degrees = 0.0;
    let zero_parameters = doc.character.parameters.clone();
    for (view, azimuth) in [("front", 0.0), ("side", 90.0), ("back", 180.0)] {
        doc.stage.camera.azimuth_degrees = azimuth;
        let zero = success(render_body(
            &t.work(&format!("{view}-zero"), &doc),
            &assets(),
            &t.0.join(format!("{view}-zero")),
        ));
        for (key, value) in [
            ("waist_circumference", -1.0),
            ("hip_depth", 1.0),
            ("buttocks_volume", 1.0),
            ("thigh_girth", 1.0),
            ("calf_girth", 1.0),
        ] {
            doc.character.parameters.insert(key.into(), value);
        }
        let shaped = success(render_body(
            &t.work(&format!("{view}-shaped"), &doc),
            &assets(),
            &t.0.join(format!("{view}-shaped")),
        ));
        assert_eq!(zero["parts"].as_array().unwrap().len(), 1);
        assert_eq!(shaped["parts"].as_array().unwrap().len(), 1);
        assert_eq!(zero["parts"][0][2], shaped["parts"][0][2]);
        assert_ne!(
            zero["png_sha256"], shaped["png_sha256"],
            "{view} body proportions must be visible"
        );
        doc.character.parameters = zero_parameters.clone();
    }
}
#[test]
fn unsupported_work_and_corrupt_assets_never_publish_output() {
    let t = Trial::new();
    let doc = SceneDocument::from_profile(CharacterProfile::b1_character()).unwrap();
    let out = t.0.join("rejected");
    reject(
        render(&t.work("motion", &doc), &assets(), &out),
        "unsupported_render",
    );
    assert!(!out.exists());
    let mut doc = neutral();
    doc.character.appearance =
        CharacterAppearance::b1_cc0_for(&doc.profile.backend, true, true, true).unwrap();
    reject(
        render(&t.work("appearance", &doc), &assets(), &out),
        "unsupported_render",
    );
    assert!(!out.exists());
    let doc = neutral();
    let work = t.work("static", &doc);
    let root = t.0.join("bad-assets");
    let manifest_path = root.join(&doc.profile.asset_path);
    std::fs::create_dir_all(manifest_path.parent().unwrap()).unwrap();
    let good = assets().join(&doc.profile.asset_path);
    std::fs::copy(&good, &manifest_path).unwrap();
    let manifest: Value = serde_json::from_slice(&std::fs::read(&good).unwrap()).unwrap();
    for file in manifest["files"].as_array().unwrap() {
        let relative = file["path"].as_str().unwrap();
        let target = manifest_path.parent().unwrap().join(relative);
        std::fs::create_dir_all(target.parent().unwrap()).unwrap();
        std::fs::copy(good.parent().unwrap().join(relative), target).unwrap();
    }
    let body = manifest_path.parent().unwrap().join("base.obj");
    let mut corrupted = std::fs::read(&body).unwrap();
    corrupted[0] ^= 1;
    std::fs::write(body, corrupted).unwrap();
    let failure = render(&work, &root, &out);
    assert_eq!(failure.status.code(), Some(1));
    assert!(failure.stdout.is_empty());
    assert!(!out.exists());
    let error: Value = serde_json::from_slice(&failure.stderr).unwrap();
    assert!(
        error["message"].as_str().unwrap().contains("hash")
            || error["message"].as_str().unwrap().contains("SHA"),
        "{error}"
    );
}

#[test]
fn static_waist_real_front_side_extremes_repeat_and_mixed_recipe() {
    let t = Trial::new();
    let mut doc = SceneDocument::from_profile(CharacterProfile::b1_character_waist()).unwrap();
    doc.stage.camera.elevation_degrees = 0.0;
    let mut zero_geometry = None;
    for (label, azimuth) in [("front", 0.0), ("side", 90.0)] {
        doc.stage.camera.azimuth_degrees = azimuth;
        let mut images = std::collections::BTreeSet::new();
        for (tier, value) in [("small", -1.0), ("zero", 0.0), ("large", 1.0)] {
            doc.character
                .parameters
                .insert("waist_circumference".into(), value);
            let name = format!("{label}-{tier}");
            let work = t.work(&name, &doc);
            let result = success(render(&work, &assets(), &t.0.join(&name)));
            assert!(result["covered_pixels"].as_u64().unwrap() > 100);
            assert_eq!(result["parts"].as_array().unwrap().len(), 2);
            assert!(images.insert(result["png_sha256"].as_str().unwrap().to_string()));
            if tier == "zero" {
                if let Some(ref previous) = zero_geometry {
                    assert_eq!(&result["geometry_sha256"], previous);
                }
                zero_geometry = Some(result["geometry_sha256"].clone());
                let repeated = success(render(
                    &work,
                    &assets(),
                    &t.0.join(format!("{name}-repeat")),
                ));
                assert_eq!(result["png_sha256"], repeated["png_sha256"]);
            }
        }
    }
    doc.character.parameters.insert("hip_width".into(), -0.5);
    doc.character.parameters.insert("torso_length".into(), 0.5);
    let mixed = success(render(
        &t.work("mixed", &doc),
        &assets(),
        &t.0.join("mixed"),
    ));
    assert_ne!(Some(mixed["geometry_sha256"].clone()), zero_geometry);
}

#[test]
fn static_waist_zero_preserves_legacy_zero_silhouette() {
    let t = Trial::new();
    let old = neutral();
    let mut new = SceneDocument::from_profile(CharacterProfile::b1_character_waist()).unwrap();
    new.stage = old.stage.clone();
    let legacy = success(render(
        &t.work("legacy-zero", &old),
        &assets(),
        &t.0.join("legacy-zero"),
    ));
    let waist = success(render(
        &t.work("waist-zero", &new),
        &assets(),
        &t.0.join("waist-zero"),
    ));
    assert_eq!(legacy["png_sha256"], waist["png_sha256"]);
    assert_eq!(legacy["covered_pixels"], waist["covered_pixels"]);
}

#[test]
fn static_leg_controls_change_actual_front_and_side_silhouettes_and_knee_pose_renders() {
    let t = Trial::new();
    let mut old = SceneDocument::from_profile(CharacterProfile::b1_character_waist()).unwrap();
    old.stage.camera.elevation_degrees = 0.0;
    let mut doc = SceneDocument::from_profile(CharacterProfile::b1_character_legs()).unwrap();
    doc.stage = old.stage.clone();
    for (view, azimuth) in [("front", 0.0), ("side", 90.0)] {
        old.stage.camera.azimuth_degrees = azimuth;
        doc.stage.camera.azimuth_degrees = azimuth;
        let predecessor = success(render(
            &t.work(&format!("v5-{view}"), &old),
            &assets(),
            &t.0.join(format!("v5-{view}")),
        ));
        let zero = success(render(
            &t.work(&format!("v6-{view}-zero"), &doc),
            &assets(),
            &t.0.join(format!("v6-{view}-zero")),
        ));
        assert_eq!(
            predecessor["geometry_sha256"], zero["geometry_sha256"],
            "zero must retain v5 geometry in {view}"
        );
        assert_eq!(
            predecessor["png_sha256"], zero["png_sha256"],
            "zero must retain v5 silhouette in {view}"
        );
        for key in [
            "thigh_length",
            "lower_leg_length",
            "thigh_girth",
            "calf_girth",
        ] {
            for (sign, value) in [("decr", -1.0), ("incr", 1.0)] {
                doc.character.parameters.insert(key.into(), value);
                let name = format!("{view}-{key}-{sign}");
                let changed = success(render(&t.work(&name, &doc), &assets(), &t.0.join(&name)));
                assert_ne!(
                    zero["geometry_sha256"], changed["geometry_sha256"],
                    "{name} must deform actual mesh"
                );
                assert_ne!(
                    zero["png_sha256"], changed["png_sha256"],
                    "{name} must change visible silhouette"
                );
                assert_eq!(changed["parts"].as_array().unwrap().len(), 2);
                assert!(changed["covered_pixels"].as_u64().unwrap() > 100);
                doc.character.parameters.insert(key.into(), 0.0);
            }
        }
    }
    doc.character.parameters.insert("thigh_length".into(), 0.5);
    doc.character
        .parameters
        .insert("lower_leg_length".into(), -0.5);
    doc.character.parameters.insert("thigh_girth".into(), 0.5);
    doc.character.parameters.insert("calf_girth".into(), -0.5);
    let mixed = success(render(
        &t.work("leg-mixed", &doc),
        &assets(),
        &t.0.join("leg-mixed"),
    ));
    doc.character.diagnostic_pose = Some("knee".into());
    let bent = success(render(
        &t.work("leg-mixed-knee", &doc),
        &assets(),
        &t.0.join("leg-mixed-knee"),
    ));
    assert_ne!(mixed["geometry_sha256"], bent["geometry_sha256"]);
    assert_ne!(mixed["png_sha256"], bent["png_sha256"]);
}

#[test]
fn static_upper_body_controls_change_actual_mesh_and_shoulder_elbow_pose_render() {
    let t = Trial::new();
    let mut visible = std::collections::BTreeMap::new();
    let mut old = SceneDocument::from_profile(CharacterProfile::b1_character_legs()).unwrap();
    old.stage.camera.elevation_degrees = 0.0;
    let mut doc = SceneDocument::from_profile(CharacterProfile::b1_character_upper_body()).unwrap();
    doc.stage = old.stage.clone();
    for (view, azimuth) in [("front", 0.0), ("side", 90.0)] {
        old.stage.camera.azimuth_degrees = azimuth;
        doc.stage.camera.azimuth_degrees = azimuth;
        let predecessor = success(render(
            &t.work(&format!("v6-{view}"), &old),
            &assets(),
            &t.0.join(format!("v6-{view}")),
        ));
        let zero = success(render(
            &t.work(&format!("v7-{view}-zero"), &doc),
            &assets(),
            &t.0.join(format!("v7-{view}-zero")),
        ));
        assert_eq!(
            predecessor["geometry_sha256"], zero["geometry_sha256"],
            "v7 zero geometry must retain v6 in {view}"
        );
        assert_eq!(
            predecessor["png_sha256"], zero["png_sha256"],
            "v7 zero image must retain v6 in {view}"
        );
        for key in ["bust_circumference", "shoulder_span", "upper_arm_girth"] {
            for (sign, value) in [("decr", -1.0), ("incr", 1.0)] {
                doc.character.parameters.insert(key.into(), value);
                let name = format!("{view}-{key}-{sign}");
                let changed = success(render(&t.work(&name, &doc), &assets(), &t.0.join(&name)));
                assert_ne!(
                    zero["geometry_sha256"], changed["geometry_sha256"],
                    "{name} must change mesh"
                );
                if zero["png_sha256"] != changed["png_sha256"] {
                    visible.insert(key, true);
                }
                assert!(changed["covered_pixels"].as_u64().unwrap() > 100);
                doc.character.parameters.insert(key.into(), 0.0);
            }
        }
    }
    for key in ["bust_circumference", "shoulder_span", "upper_arm_girth"] {
        assert_eq!(
            visible.get(key),
            Some(&true),
            "{key} must be visible in front or side view"
        );
    }
    doc.character
        .parameters
        .insert("bust_circumference".into(), 0.5);
    doc.character.parameters.insert("shoulder_span".into(), 0.5);
    doc.character
        .parameters
        .insert("upper_arm_girth".into(), 0.5);
    let neutral = success(render(
        &t.work("upper-mixed", &doc),
        &assets(),
        &t.0.join("upper-mixed"),
    ));
    for pose in ["shoulder", "elbow"] {
        doc.character.diagnostic_pose = Some(pose.into());
        let changed = success(render(
            &t.work(&format!("upper-mixed-{pose}"), &doc),
            &assets(),
            &t.0.join(format!("upper-mixed-{pose}")),
        ));
        assert_ne!(neutral["geometry_sha256"], changed["geometry_sha256"]);
    }
}

#[test]
fn upper_body_export_is_discoverable_as_supported() {
    let trial = Trial::new();
    let doc = SceneDocument::from_profile(CharacterProfile::b1_character_upper_body()).unwrap();
    let work = trial.work("v7-discovery", &doc);
    let output = Command::new(env!("CARGO_BIN_EXE_nvwa-cli"))
        .args(["describe-capabilities".as_ref(), work.as_path()])
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let capabilities: Value = serde_json::from_slice(&output.stdout).unwrap();
    let exporter = &capabilities["cpu_render"];
    assert_eq!(exporter["compiled"], true);
    assert_eq!(exporter["current_work_supported"], true);
    assert!(
        exporter["profiles"]
            .as_array()
            .unwrap()
            .iter()
            .any(|id| id.as_str() == Some(doc.profile.id.as_str()))
    );
    assert!(exporter["usage"].as_str().unwrap().contains("upper-body"));
}

#[test]
fn hip_contour_controls_change_actual_front_side_and_back_render() {
    let trial = Trial::new();
    let mut previous =
        SceneDocument::from_profile(CharacterProfile::b1_character_upper_body()).unwrap();
    let mut doc =
        SceneDocument::from_profile(CharacterProfile::b1_character_hip_contour()).unwrap();
    previous.stage.camera.elevation_degrees = 0.0;
    doc.stage = previous.stage.clone();
    let mut visible = std::collections::BTreeMap::new();
    for (view, azimuth) in [("front", 0.0), ("side", 90.0), ("back", 180.0)] {
        previous.stage.camera.azimuth_degrees = azimuth;
        doc.stage.camera.azimuth_degrees = azimuth;
        let old = success(render(
            &trial.work(&format!("v7-{view}"), &previous),
            &assets(),
            &trial.0.join(format!("v7-{view}")),
        ));
        let zero = success(render(
            &trial.work(&format!("v8-{view}-zero"), &doc),
            &assets(),
            &trial.0.join(format!("v8-{view}-zero")),
        ));
        assert_eq!(
            old["geometry_sha256"], zero["geometry_sha256"],
            "{view} zero geometry"
        );
        assert_eq!(old["png_sha256"], zero["png_sha256"], "{view} zero image");
        for key in ["hip_depth", "buttocks_volume"] {
            for (sign, value) in [("decr", -1.0), ("incr", 1.0)] {
                doc.character.parameters.insert(key.into(), value);
                let name = format!("v8-{view}-{key}-{sign}");
                let changed = success(render(
                    &trial.work(&name, &doc),
                    &assets(),
                    &trial.0.join(&name),
                ));
                assert_ne!(
                    zero["geometry_sha256"], changed["geometry_sha256"],
                    "{name} must deform mesh"
                );
                if zero["png_sha256"] != changed["png_sha256"] {
                    visible.insert(key, true);
                }
                assert!(changed["covered_pixels"].as_u64().unwrap() > 100);
                doc.character.parameters.insert(key.into(), 0.0);
            }
        }
    }
    for key in ["hip_depth", "buttocks_volume"] {
        assert_eq!(
            visible.get(key),
            Some(&true),
            "{key} must change a visible silhouette"
        );
    }
    doc.character.parameters.insert("hip_depth".into(), 0.5);
    doc.character
        .parameters
        .insert("buttocks_volume".into(), 0.5);
    let neutral = success(render(
        &trial.work("v8-mixed", &doc),
        &assets(),
        &trial.0.join("v8-mixed"),
    ));
    doc.character.diagnostic_pose = Some("knee".into());
    let knee = success(render(
        &trial.work("v8-mixed-knee", &doc),
        &assets(),
        &trial.0.join("v8-mixed-knee"),
    ));
    assert_ne!(neutral["geometry_sha256"], knee["geometry_sha256"]);
}

#[test]
fn hip_contour_export_is_discoverable_as_supported() {
    let trial = Trial::new();
    let doc = SceneDocument::from_profile(CharacterProfile::b1_character_hip_contour()).unwrap();
    let work = trial.work("v8-discovery", &doc);
    let output = Command::new(env!("CARGO_BIN_EXE_nvwa-cli"))
        .args(["describe-capabilities".as_ref(), work.as_path()])
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let capabilities: Value = serde_json::from_slice(&output.stdout).unwrap();
    let exporter = &capabilities["cpu_render"];
    assert_eq!(exporter["current_work_supported"], true);
    assert!(
        exporter["profiles"]
            .as_array()
            .unwrap()
            .iter()
            .any(|id| id.as_str() == Some(doc.profile.id.as_str()))
    );
    assert!(exporter["usage"].as_str().unwrap().contains("hip-contour"));
}

#[test]
fn arm_proportions_change_actual_front_side_and_elbow_render() {
    let trial = Trial::new();
    let mut previous =
        SceneDocument::from_profile(CharacterProfile::b1_character_hip_contour()).unwrap();
    let mut doc =
        SceneDocument::from_profile(CharacterProfile::b1_character_arm_proportions()).unwrap();
    previous.stage.camera.elevation_degrees = 0.0;
    doc.stage = previous.stage.clone();
    let mut visible = std::collections::BTreeMap::new();
    for (view, azimuth) in [("front", 0.0), ("side", 90.0)] {
        previous.stage.camera.azimuth_degrees = azimuth;
        doc.stage.camera.azimuth_degrees = azimuth;
        let old = success(render(
            &trial.work(&format!("v8-{view}"), &previous),
            &assets(),
            &trial.0.join(format!("v8-{view}")),
        ));
        let zero = success(render(
            &trial.work(&format!("v9-{view}-zero"), &doc),
            &assets(),
            &trial.0.join(format!("v9-{view}-zero")),
        ));
        assert_eq!(
            old["geometry_sha256"], zero["geometry_sha256"],
            "{view} zero geometry"
        );
        assert_eq!(old["png_sha256"], zero["png_sha256"], "{view} zero image");
        for key in ["upper_arm_length", "forearm_length", "wrist_circumference"] {
            for (sign, value) in [("decr", -1.0), ("incr", 1.0)] {
                doc.character.parameters.insert(key.into(), value);
                let name = format!("v9-{view}-{key}-{sign}");
                let changed = success(render(
                    &trial.work(&name, &doc),
                    &assets(),
                    &trial.0.join(&name),
                ));
                assert_ne!(
                    zero["geometry_sha256"], changed["geometry_sha256"],
                    "{name} must deform mesh"
                );
                if zero["png_sha256"] != changed["png_sha256"] {
                    visible.insert(key, true);
                }
                assert!(changed["covered_pixels"].as_u64().unwrap() > 100);
                doc.character.parameters.insert(key.into(), 0.0);
            }
        }
    }
    for key in ["upper_arm_length", "forearm_length", "wrist_circumference"] {
        assert_eq!(
            visible.get(key),
            Some(&true),
            "{key} must change a visible silhouette"
        );
    }
    doc.character
        .parameters
        .insert("upper_arm_length".into(), 0.5);
    doc.character
        .parameters
        .insert("forearm_length".into(), 0.5);
    doc.character
        .parameters
        .insert("wrist_circumference".into(), 0.5);
    let neutral = success(render(
        &trial.work("v9-mixed", &doc),
        &assets(),
        &trial.0.join("v9-mixed"),
    ));
    doc.character.diagnostic_pose = Some("elbow".into());
    let elbow = success(render(
        &trial.work("v9-mixed-elbow", &doc),
        &assets(),
        &trial.0.join("v9-mixed-elbow"),
    ));
    assert_ne!(neutral["geometry_sha256"], elbow["geometry_sha256"]);
}

#[test]
fn arm_proportions_export_is_discoverable_as_supported() {
    let trial = Trial::new();
    let doc =
        SceneDocument::from_profile(CharacterProfile::b1_character_arm_proportions()).unwrap();
    let work = trial.work("v9-discovery", &doc);
    let output = Command::new(env!("CARGO_BIN_EXE_nvwa-cli"))
        .args(["describe-capabilities".as_ref(), work.as_path()])
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let capabilities: Value = serde_json::from_slice(&output.stdout).unwrap();
    let exporter = &capabilities["cpu_render"];
    assert_eq!(exporter["current_work_supported"], true);
    assert!(
        exporter["profiles"]
            .as_array()
            .unwrap()
            .iter()
            .any(|id| id.as_str() == Some(doc.profile.id.as_str()))
    );
    assert!(
        exporter["usage"]
            .as_str()
            .unwrap()
            .contains("arm-proportions")
    );
}
