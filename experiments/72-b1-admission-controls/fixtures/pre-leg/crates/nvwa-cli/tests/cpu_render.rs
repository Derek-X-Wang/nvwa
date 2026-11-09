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
