use serde_json::{Value, json};
use std::{path::Path, process::Command};

fn cli(args: &[&Path]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_nvwa-cli"))
        .args(args)
        .output()
        .expect("run production CLI")
}

fn success(args: &[&Path]) -> Value {
    let output = cli(args);
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(output.stderr.is_empty());
    serde_json::from_slice(&output.stdout).expect("response JSON")
}

fn rejected(args: &[&Path], code: &str) {
    let output = cli(args);
    assert_eq!(output.status.code(), Some(1));
    assert!(output.stdout.is_empty());
    let error: Value = serde_json::from_slice(&output.stderr).expect("error JSON");
    assert_eq!(error["code"], code);
}

fn timeline_edit(expected_revision: u64, duration: f64) -> Value {
    json!({"command_id":"run-and-hold", "expected_revision":expected_revision,
        "command":{"type":"set_timeline",
            "clips":[{"id":"run", "clip_id":nvwa_core::B1_RUN_CLIP_ID, "start_seconds":0,
                "duration_seconds":duration, "speed":1, "looping":false}]}})
}

#[test]
fn queries_actual_scene_travel_and_hold_using_the_work_scale() {
    let dir = std::env::temp_dir().join(format!("nvwa-travel-query-{}", std::process::id()));
    std::fs::create_dir(&dir).unwrap();
    let source = dir.join("source.nvwa.json");
    let commands = dir.join("commands.json");
    let work = dir.join("run.nvwa.json");
    let assets = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../assets");
    success(&["new-character-running".as_ref(), &assets, &source]);
    std::fs::write(
        &commands,
        serde_json::to_vec(&json!([
            {"command_id":"scale", "expected_revision":0,
                "command":{"type":"set_scale", "character_id":"character-1", "scale":1.25}},
            timeline_edit(1, 5.0),
        ]))
        .unwrap(),
    )
    .unwrap();
    success(&["apply".as_ref(), &source, &commands, &work]);
    let original = std::fs::read(&work).unwrap();

    let caps = success(&["describe-capabilities".as_ref(), &work]);
    let travel = &caps["cli_contract"]["travel_query"];
    assert_eq!(travel["work_supported"], true);
    assert_eq!(travel["available"], cfg!(feature = "motion-query"));
    assert_eq!(
        caps["cli_contract"]["motion_query"]["work_supported"],
        false
    );
    let request: [&Path; 6] = [
        "travel-query".as_ref(),
        &work,
        &assets,
        "0".as_ref(),
        "5".as_ref(),
        "1".as_ref(),
    ];
    if cfg!(feature = "motion-query") {
        let summary = success(&request);
        let mut expanded_request = request.to_vec();
        expanded_request.push("--samples".as_ref());
        let mut expanded = success(&expanded_request);
        let samples = expanded.as_object_mut().unwrap().remove("samples").unwrap();
        assert_eq!(expanded, summary);
        assert_eq!(summary["work"]["revision"], 2);
        assert_eq!(
            summary["work"]["sha256"],
            nvwa_core::appearance_sha256(&original)
        );
        assert_eq!(summary["space"], "stage_world_xyz");
        assert_eq!(summary["sampling"]["count"], 6);
        assert_eq!(summary["start"], samples[0]);
        assert_eq!(summary["end"], samples[5]);
        assert_eq!(samples[4]["source_t_s"], json!(4.0));
        assert_eq!(samples[5]["source_t_s"], json!(4.0));
        for part in ["body", "garment"] {
            assert_eq!(summary["displacement_metres"][part], json!([0.0, 0.0, 2.5]));
            assert_eq!(samples[0]["positions_metres"][part][2], json!(0.0));
            assert_eq!(samples[2]["positions_metres"][part][2], json!(1.25));
            assert_eq!(
                samples[4]["positions_metres"][part],
                samples[5]["positions_metres"][part]
            );
        }
        let mut foot_request = request;
        foot_request[0] = "motion-query".as_ref();
        rejected(&foot_request, "motion_query_unsupported_work");
        let mut oversized = request;
        oversized[5] = "0.001".as_ref();
        rejected(&oversized, "travel_query_range");

        let mut beyond_end = request;
        beyond_end[4] = "5.0000001".as_ref();
        rejected(&beyond_end, "travel_query_range");

        // The binary f32 representations round down for 5.1 and up for 5.3.
        for (duration, end, beyond) in [(5.1, "5.1", "5.1000001"), (5.3, "5.3", "5.3000001")] {
            let decimal_work = dir.join(format!("decimal-{end}.nvwa.json"));
            std::fs::write(
                &commands,
                serde_json::to_vec(&timeline_edit(2, duration)).unwrap(),
            )
            .unwrap();
            success(&["apply".as_ref(), &work, &commands, &decimal_work]);
            let mut decimal = request;
            decimal[1] = &decimal_work;
            decimal[3] = end.as_ref();
            decimal[4] = end.as_ref();
            let endpoint = success(&decimal);
            assert_eq!(endpoint["sampling"]["count"], 1);
            assert_eq!(endpoint["end"]["t_s"], json!(duration));
            let returned_time = endpoint["end"]["t_s"].to_string();
            decimal[3] = Path::new(&returned_time);
            decimal[4] = Path::new(&returned_time);
            assert_eq!(success(&decimal)["end"], endpoint["end"]);
            assert_eq!(endpoint["end"]["source_t_s"], json!(4.0));
            decimal[4] = beyond.as_ref();
            rejected(&decimal, "travel_query_range");
        }
    } else {
        rejected(&request, "travel_query_unavailable");
    }
    let oversized_character = dir.join("oversized.nvwa.json");
    std::fs::write(
        &commands,
        serde_json::to_vec(&json!({"command_id":"oversized", "expected_revision":2,
            "command":{"type":"set_scale","character_id":"character-1","scale":101}}))
        .unwrap(),
    )
    .unwrap();
    success(&["apply".as_ref(), &work, &commands, &oversized_character]);
    let caps = success(&["describe-capabilities".as_ref(), &oversized_character]);
    assert_eq!(
        caps["cli_contract"]["travel_query"]["work_supported"],
        false
    );
    if cfg!(feature = "motion-query") {
        let mut out_of_scale = request;
        out_of_scale[1] = &oversized_character;
        rejected(&out_of_scale, "travel_query_unsupported_work");
    }
    assert_eq!(std::fs::read(&work).unwrap(), original);
    std::fs::remove_dir_all(dir).unwrap();
}
