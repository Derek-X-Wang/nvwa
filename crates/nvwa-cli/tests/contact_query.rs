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
    for (command, key) in [
        ("contact-fit", "contact_fit"),
        ("contact-recheck", "contact_recheck"),
    ] {
        let caps = cli(&["describe-capabilities".as_ref(), &reopened], true);
        assert_eq!(
            caps["cli_contract"][key]["available"],
            cfg!(feature = "motion-query")
        );
        assert_eq!(caps["cli_contract"][key]["work_supported"], false);
        let help = Command::new(env!("CARGO_BIN_EXE_nvwa-cli"))
            .args([command, "--help"])
            .output()
            .unwrap();
        assert!(help.status.success());
        assert_eq!(
            String::from_utf8(help.stdout).unwrap().trim_end(),
            caps["cli_contract"][key]["usage"].as_str().unwrap()
        );
        if !cfg!(feature = "motion-query") {
            assert_eq!(
                cli(&[command.as_ref()], false)["code"],
                format!("{key}_unavailable")
            );
        }
    }
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

#[test]
#[cfg(feature = "motion-query")]
fn fit_and_recheck_the_accepted_iris_and_mora_first_drafts() {
    let crate_root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let assets = crate_root.join("../../assets");
    let scratch = std::env::temp_dir().join(format!("nvwa-contact-fit-{}", std::process::id()));
    fs::create_dir(&scratch).unwrap();
    for (role, accepted_sha, brackets) in [
        (
            "iris",
            "6fc2cea4b5091b0a0e3e1d0c4d9aaeb2cb2b3afbb0f654ce66a336dbb68d625b",
            [[3003, 3004], [3500, 3501]],
        ),
        (
            "mora",
            "5da679e027b86ad62f43ed4cda83267c768da72cdab8e9f83c811f54e830afec",
            [[2997, 2998], [3498, 3499]],
        ),
    ] {
        let case = crate_root.join("tests/fixtures/contact-fit").join(role);
        let start = case.join("start.nvwa.json");
        let reference = case.join("reference.nvwa.json");
        let accepted = case.join("accepted.nvwa.json");
        let before = [&start, &reference, &accepted].map(|path| fs::read(path).unwrap());
        assert_eq!(nvwa_core::appearance_sha256(&before[2]), accepted_sha);
        let caps = cli(&["describe-capabilities".as_ref(), &start], true);
        assert_eq!(caps["cli_contract"]["authored_motion"]["supported"], false);
        assert_eq!(
            caps["cli_contract"]["motion_query"]["work_supported"],
            false
        );
        assert_eq!(
            caps["cli_contract"]["set_timeline"]["command_supported"],
            false
        );
        let mut renamed = serde_json::from_slice::<Value>(&before[0]).unwrap()["timeline"].clone();
        renamed[0]["id"] = json!("renamed-reference");
        let rename = scratch.join("rename.json");
        fs::write(&rename, json!({"command_id":"rename", "expected_revision":serde_json::from_slice::<Value>(&before[0]).unwrap()["revision"],
            "command":{"type":"set_timeline","clips":renamed}}).to_string()).unwrap();
        let rejected = scratch.join("rejected.json");
        assert_eq!(
            cli(&["apply".as_ref(), &start, &rename, &rejected], false)["code"],
            "invalid_reference_motion"
        );
        assert!(!rejected.exists());
        for cmd in ["contact_fit", "contact_recheck"] {
            assert_eq!(caps["cli_contract"][cmd]["work_supported"], true);
        }
        let plan = cli(
            &[
                "contact-fit".as_ref(),
                &start,
                &assets,
                &reference,
                "2.50".as_ref(),
                "4.00".as_ref(),
                ".025".as_ref(),
                "--hand".as_ref(),
                "right".as_ref(),
            ],
            true,
        );
        let edit = scratch.join("edit.json");
        let draft = scratch.join(format!("{role}.json"));
        fs::write(&edit, serde_json::to_vec(&plan["commands"]).unwrap()).unwrap();
        cli(&["apply".as_ref(), &start, &edit, &draft], true);
        let mut proposed: Value = serde_json::from_slice(&fs::read(&draft).unwrap()).unwrap();
        let initial: Value = serde_json::from_slice(&before[0]).unwrap();
        let mut golden: Value = serde_json::from_slice(&before[2]).unwrap();
        // Compare pass-through data exactly. Fit angles can differ at floating-point
        // precision. Compare their changed joints and evaluate the resulting pose.
        let rotations = |v: &mut Value| v["reference_motion"]["rotations"].take();
        let actual_tracks = rotations(&mut proposed);
        let golden_tracks = rotations(&mut golden);
        assert_eq!(proposed, golden, "{role} edit scope");
        let original = initial["reference_motion"]["rotations"]
            .as_object()
            .unwrap();
        assert_eq!(actual_tracks.as_object().unwrap().len(), original.len());
        for (joint, track) in original {
            assert!(actual_tracks.get(joint).is_some());
            assert_eq!(
                actual_tracks[joint] != *track,
                golden_tracks[joint] != *track,
                "{role} {joint}"
            );
        }
        for work in [&accepted, &draft] {
            let receipt = cli(
                &[
                    "contact-recheck".as_ref(),
                    work,
                    &assets,
                    &start,
                    &reference,
                    "3.25".as_ref(),
                    "--hand".as_ref(),
                    "right".as_ref(),
                    "--sole".as_ref(),
                    "left".as_ref(),
                    "--support".as_ref(),
                    "right".as_ref(),
                ],
                true,
            );
            assert_eq!(receipt["status"], "passed", "{role} {receipt}");
            assert_eq!(
                receipt["saved"]["sha256"],
                nvwa_core::appearance_sha256(&fs::read(work).unwrap())
            );
            let timing = &receipt["contact_timing"];
            for (label, count) in [("stance", 0), ("reference", 1), ("saved", 1)] {
                assert_eq!(timing["guide"][label]["intervals"], count);
            }
            for (name, expected) in ["enter", "exit"].into_iter().zip(brackets) {
                let edge = &timing["edges"][name];
                assert_eq!(edge["saved_bracket_ms"], json!(expected), "{role} {name}");
                assert!(edge["worst_case_absolute_delta_ms"].as_f64().unwrap() <= 1000.0 / 24.0);
            }
            assert_eq!(
                receipt["landing"]["delta"]["landing_mm"],
                json!([0.0, 0.0, 0.0])
            );
            assert!(
                receipt["landing"]["checks"]
                    .as_object()
                    .unwrap()
                    .values()
                    .all(|v| v.as_bool() == Some(true))
            );
        }
        assert_eq!(
            before,
            [&start, &reference, &accepted].map(|path| fs::read(path).unwrap())
        );
    }
    fs::remove_dir_all(scratch).unwrap();
}
