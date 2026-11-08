use nvwa_core::{CharacterProfile, SceneDocument, TimelineClip};
use serde_json::{Value, json};
use std::{path::Path, process::Command};

fn cli(args: &[&Path]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_nvwa-cli"))
        .args(args)
        .output()
        .expect("run production CLI")
}

fn success(output: std::process::Output) -> Value {
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(output.stderr.is_empty());
    serde_json::from_slice(&output.stdout).expect("response JSON")
}

fn rejected(output: std::process::Output, code: &str) {
    assert_eq!(output.status.code(), Some(1));
    assert!(output.stdout.is_empty());
    let diagnostic: Value = serde_json::from_slice(&output.stderr).expect("error JSON");
    assert_eq!(diagnostic["code"], code);
}

#[test]
fn discovers_and_queries_a_finite_b1_work_without_modifying_it() {
    let dir = std::env::temp_dir().join(format!("nvwa-motion-query-{}", std::process::id()));
    std::fs::create_dir(&dir).unwrap();
    let work = dir.join("input.nvwa.json");
    let assets = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../assets");
    let mut doc = SceneDocument::from_profile(CharacterProfile::b1_motion()).unwrap();
    doc.timeline = vec![TimelineClip {
        id: "knee".into(),
        clip_id: "b1_knee_flex_v1".into(),
        start_seconds: 0.0,
        duration_seconds: 4.0,
        speed: 1.0,
        looping: false,
    }];
    let original = doc.to_json().unwrap();
    std::fs::write(&work, &original).unwrap();

    let caps = success(cli(&["describe-capabilities".as_ref(), &work]));
    assert_eq!(caps["cli_contract"]["motion_query"]["work_supported"], true);
    assert_eq!(
        caps["cli_contract"]["motion_query"]["available"],
        cfg!(feature = "motion-query")
    );
    let request: [&Path; 6] = [
        "motion-query".as_ref(),
        &work,
        &assets,
        "0".as_ref(),
        "0.05".as_ref(),
        "0.05".as_ref(),
    ];
    if cfg!(feature = "motion-query") {
        let summary = success(cli(&request));
        let mut expanded_request = request.to_vec();
        expanded_request.push("--samples".as_ref());
        let mut expanded = success(cli(&expanded_request));
        let samples = expanded.as_object_mut().unwrap().remove("samples").unwrap();
        assert_eq!(samples.as_array().unwrap().len(), 2);
        assert_eq!(expanded, summary);
        assert_eq!(
            summary["work"]["sha256"],
            nvwa_core::appearance_sha256(original.as_bytes())
        );
        assert_eq!(
            summary["feet"]["left"]["near_floor_s"],
            json!([[0.0, 0.05]])
        );
        assert_eq!(summary["anomalies"], json!([]));
        let mut too_many = request;
        too_many[4] = "4".as_ref();
        too_many[5] = "0.001".as_ref();
        rejected(cli(&too_many), "motion_query_range");
    } else {
        rejected(cli(&request), "motion_query_unavailable");
    }
    assert_eq!(std::fs::read_to_string(&work).unwrap(), original);
    std::fs::remove_dir_all(dir).unwrap();
}
