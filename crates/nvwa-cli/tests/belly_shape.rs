use nvwa_core::*;
use serde_json::{Value, json};
use std::{
    path::{Path, PathBuf},
    process::Command,
};

fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../assets")
}
fn run(args: &[&Path]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_nvwa-cli"))
        .args(args)
        .output()
        .unwrap()
}
fn success(args: &[&Path]) -> Value {
    let output = run(args);
    assert!(output.status.success(), "{}", String::from_utf8_lossy(&output.stderr));
    serde_json::from_slice(&output.stdout).unwrap()
}
fn temp() -> PathBuf {
    static SEQ: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    let path = std::env::temp_dir().join(format!(
        "nvwa-belly-shape-{}-{}",
        std::process::id(),
        SEQ.fetch_add(1, std::sync::atomic::Ordering::Relaxed)
    ));
    std::fs::create_dir(&path).unwrap();
    path
}

#[test]
fn belly_shape_cli_creates_discovers_validates_and_saves_real_work() {
    let dir = temp();
    let initial = dir.join("initial.json");
    success(&["new-character-belly-shape".as_ref(), &root(), &initial]);
    let doc = SceneDocument::from_json(&std::fs::read_to_string(&initial).unwrap()).unwrap();
    assert_eq!(doc.profile, CharacterProfile::b1_character_belly_shape());
    assert_eq!(doc.character.parameters[B1_BELLY_SHAPE_TARGET.id], 0.0);
    success(&["validate".as_ref(), &initial, &root()]);
    let caps = success(&["describe-capabilities".as_ref(), &initial]);
    assert_eq!(caps["cli_contract"]["belly_shape"]["max_authored_target_weight"], 0.25);
    assert_eq!(caps["cli_contract"]["chest_placement_shape"]["supported"], true);
    assert_eq!(caps["cli_contract"]["set_appearance"]["b1_cc0_supported"], false);
    #[cfg(feature = "cpu-render")]
    assert_eq!(caps["cpu_render"]["current_work_supported"], true);
    let request = dir.join("request.json");
    let changed = dir.join("changed.json");
    let rejected = dir.join("rejected.json");
    for v in [1.0, 1.01] {
        std::fs::write(
            &request,
            json!({"command_id":"belly","expected_revision":doc.revision,"command":{"type":"set_parameters","character_id":doc.character.id,"values":{"belly_shape_strength":v,"waist_circumference":0.5}}}).to_string(),
        )
        .unwrap();
        if v <= 1.0 {
            success(&["apply".as_ref(), &initial, &request, &changed]);
        } else {
            assert!(!run(&["apply".as_ref(), &initial, &request, &rejected]).status.success());
            assert!(!rejected.exists());
        }
    }
    success(&["validate".as_ref(), &changed, &root()]);
    let saved = SceneDocument::from_json(&std::fs::read_to_string(&changed).unwrap()).unwrap();
    assert_eq!(saved.character.parameters[B1_BELLY_SHAPE_TARGET.id], 1.0);
    assert_eq!(saved.character.parameters["waist_circumference"], 0.5);
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn absent_or_corrupt_belly_asset_never_writes_work() {
    let dir = temp();
    let assets = dir.join("assets");
    let version = B1AssetVersion::V15;
    let manifest = B1AssetManifest::from_bytes_for(version, version.manifest_bytes()).unwrap();
    let parent = Path::new(version.manifest_path()).parent().unwrap();
    let belly = "targets/stomach-pregnant-incr.target";
    for path in std::iter::once("manifest.json").chain(manifest.files.iter().map(|f| f.path.as_str())) {
        if path == belly {
            continue;
        }
        let dest = assets.join(parent).join(path);
        std::fs::create_dir_all(dest.parent().unwrap()).unwrap();
        std::fs::copy(root().join(parent).join(path), dest).unwrap();
    }
    let output_path = dir.join("rejected.json");
    for expected in ["asset_missing", "invalid_asset"] {
        let output = run(&["new-character-belly-shape".as_ref(), &assets, &output_path]);
        assert_eq!(output.status.code(), Some(1));
        assert_eq!(serde_json::from_slice::<Value>(&output.stderr).unwrap()["code"], expected);
        assert!(!output_path.exists());
        if expected == "asset_missing" {
            std::fs::write(assets.join(parent).join(belly), b"broken").unwrap();
        }
    }
    std::fs::remove_dir_all(dir).unwrap();
}
