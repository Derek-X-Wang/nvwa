use serde_json::{Value, json};
use std::{fs, path::Path, process::Command};

fn cli(args: &[&Path], success: bool) -> Value {
    let output = Command::new(env!("CARGO_BIN_EXE_nvwa-cli"))
        .env_remove("NVWA_B1_LEVEL1_DISPLAY")
        .args(args)
        .output()
        .unwrap();
    assert_eq!(
        output.status.success(),
        success,
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    serde_json::from_slice(if success {
        &output.stdout
    } else {
        &output.stderr
    })
    .unwrap()
}

#[test]
fn stage_contact_roundtrip_and_visible_index_brackets() {
    let dir = std::env::temp_dir().join(format!("nvwa-contact-{}", std::process::id()));
    fs::create_dir(&dir).unwrap();
    let source = dir.join("source.json");
    let edit = dir.join("command.json");
    let saved = dir.join("saved.json");
    let reopened = dir.join("reopened.json");
    let assets = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../assets");
    cli(&["new-character-running".as_ref(), &assets, &source], true);
    let original = fs::read(&source).unwrap();
    let work = cli(&["inspect".as_ref(), &source], true);
    assert!(work["stage"].get("contact_target").is_none());
    cli(&["save".as_ref(), &source, &reopened], true);
    assert_eq!(fs::read(&reopened).unwrap(), original);
    let target = json!({"id":"switch","position_metres":[0.5202625,1.6023508,2.1880093],"radius_metres":0.015});
    let cmd = |target: Value, speed: f64| {
        let mut stage = work["stage"].clone();
        stage["contact_target"] = target;
        json!([
            {"command_id":"place","expected_revision":0,"command":{"type":"set_stage","stage":stage}},
            {"command_id":"move","expected_revision":1,"command":{"type":"set_timeline","clips":[
                {"id":"travel","clip_id":nvwa_core::B1_RUN_CLIP_ID,"start_seconds":0,"duration_seconds":4,"speed":1,"looping":false},
                {"id":"arm","clip_id":"b1_arm_rehearsal_v1","start_seconds":4.5,"duration_seconds":2,"speed":speed,"looping":false}
            ]}}
        ])
    };
    let apply = |target: Value, speed: f64, success: bool| {
        fs::write(&edit, cmd(target, speed).to_string()).unwrap();
        cli(&["apply".as_ref(), &source, &edit, &saved], success)
    };
    for bad in [
        Value::Null,
        json!({"id":"x","position_metres":[0,0],"radius_metres":1}),
        json!({"id":"","position_metres":[0,0,0],"radius_metres":1}),
        json!({"id":"x","position_metres":[0,0,0],"radius_metres":0}),
        json!({"id":"x","position_metres":[0,0,0],"radius_metres":1,"extra":false}),
    ] {
        apply(bad, 0.75, false);
        assert!(!saved.exists());
    }
    apply(target.clone(), 0.75, true);
    cli(&["save".as_ref(), &saved, &reopened], true);
    let inspect = cli(&["inspect".as_ref(), &reopened], true);
    assert_eq!(inspect["stage"]["contact_target"], target);
    let mut legacy = inspect.clone();
    legacy["schema_version"] = json!(3);
    let legacy_path = dir.join("legacy-with-target.json");
    fs::write(&legacy_path, legacy.to_string()).unwrap();
    let invalid = cli(&["inspect".as_ref(), &legacy_path], false);
    assert!(
        invalid["message"]
            .as_str()
            .unwrap()
            .contains("contact target requires Work schema 4")
    );
    assert_eq!(fs::read(&saved).unwrap(), fs::read(&reopened).unwrap());
    let caps = cli(&["describe-capabilities".as_ref(), &reopened], true);
    assert_eq!(
        caps["cli_contract"]["contact_query"]["work_supported"],
        true
    );
    let query = |path: &Path, expand: bool, success: bool| {
        let mut args: Vec<&Path> = vec![
            "contact-query".as_ref(),
            path,
            &assets,
            "6".as_ref(),
            "6.5".as_ref(),
            "0.04166666666666667".as_ref(),
        ];
        if expand {
            args.push("--samples".as_ref());
        }
        cli(&args, success)
    };
    if cfg!(feature = "motion-query") {
        assert_eq!(
            query(&source, false, false)["code"],
            "contact_target_absent"
        );
        let overlay = Command::new(env!("CARGO_BIN_EXE_nvwa-cli"))
            .env("NVWA_B1_LEVEL1_DISPLAY", "1")
            .args([
                "contact-query".as_ref(),
                reopened.as_path(),
                assets.as_path(),
                "6.5".as_ref(),
                "6.5".as_ref(),
                "0.01".as_ref(),
            ])
            .output()
            .unwrap();
        assert_eq!(overlay.status.code(), Some(1));
        assert!(overlay.stdout.is_empty());
        let diagnostic: Value = serde_json::from_slice(&overlay.stderr).unwrap();
        assert_eq!(diagnostic["code"], "contact_query_unsupported_display");
        assert!(diagnostic["message"].as_str().unwrap().contains("Level 1"));
        let baseline = query(&reopened, false, true);
        assert!(baseline.get("samples").is_none());
        assert_eq!(baseline["start"]["inside"], false);
        assert_eq!(baseline["end"]["inside"], true);
        assert_eq!(baseline["nearest"]["t_s"], 6.5);
        assert_eq!(
            baseline["changes"],
            json!([{"event":"enter","bracket_s":[6.4166665,6.4583335]}])
        );
        apply(target.clone(), 0.85, true);
        let raised = query(&saved, true, true);
        assert_eq!(raised["samples"].as_array().unwrap().len(), 13);
        assert_eq!(raised["end"]["inside"], false);
        assert_eq!(
            raised["changes"],
            json!([{"event":"enter","bracket_s":[6.2083335,6.25]},
            {"event":"exit","bracket_s":[6.2916665,6.3333335]}])
        );
        let mut offset = target;
        offset["position_metres"][0] = json!(1.0202625);
        apply(offset, 0.85, true);
        let missed = query(&saved, false, true);
        assert_eq!(missed["changes"], json!([]));
        assert_eq!(missed["nearest"]["inside"], false);
    } else {
        assert_eq!(
            query(&reopened, false, false)["code"],
            "contact_query_unavailable"
        );
    }
    assert_eq!(fs::read(&source).unwrap(), original);
    fs::remove_dir_all(dir).unwrap();
}
