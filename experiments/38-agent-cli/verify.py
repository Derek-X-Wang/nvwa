#!/usr/bin/env python3
"""Portable stdlib audit of retained evidence; no binary/model/network execution."""
import hashlib
import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def audit_run(directory, manifest):
    steps = sorted((directory / "receipts").glob("[0-9][0-9]-*"))
    assert len(steps) == 9
    binary_hashes = set()
    for index, step in enumerate(steps, 1):
        receipt = read(step / "invocation.json")
        assert receipt["step"] == step.name
        assert receipt["exit_code"] == (1 if index == 4 else 0)
        binary_hashes.add(receipt["binary_sha256"])
        for phase in ["before", "after"]:
            for snapshot in receipt[f"json_arguments_{phase}"].values():
                content = (step / snapshot["snapshot"]).read_bytes()
                assert hashlib.sha256(content).hexdigest() == snapshot["sha256"]
        if index != 4:
            assert not (step / "stderr.txt").read_bytes()
            read(step / "stdout.txt")
    assert len(binary_hashes) == 1
    assert next(iter(binary_hashes)) == manifest["recorded_binary_sha256"]
    discovery = read(steps[1] / "stdout.txt")
    assert discovery["document_revision"] == 0
    assert discovery["character_id"] == "character-1"
    specs = {p["id"]: p for p in discovery["parameters"]}
    for name, value in [("jaw_width", 0.42), ("smile", 0.2)]:
        assert specs[name]["min"] <= value <= specs[name]["max"]
    failed = read(steps[3] / "invocation.json")
    assert not (steps[3] / "stdout.txt").read_bytes()
    assert read(steps[3] / "stderr.txt")["code"] == "revision_conflict"
    input_name = failed["argv"][2]
    assert failed["json_arguments_before"][input_name]["sha256"] == failed["json_arguments_after"][input_name]["sha256"]
    failed_output = failed["argv"][4]
    assert failed_output not in failed["json_arguments_before"]
    assert failed_output not in failed["json_arguments_after"]
    assert not (directory / "stale-output.nvwa.json").exists()
    inspected = read(steps[4] / "stdout.txt")
    corrected = read(directory / "corrected-timeline.commands.json")
    assert inspected["revision"] == corrected["expected_revision"] == 1
    assert read(steps[6] / "stdout.txt") == {"asset_checked": True, "revision": 2, "valid": True}
    final_path = directory / "agent-nine-second.nvwa.json"
    final = read(final_path)
    assert final == read(steps[8] / "stdout.txt") == read(directory / "authored.nvwa.json")
    assert final["revision"] == 2
    assert final["character"]["parameters"] == {"jaw_width": 0.42, "smile": 0.2, "nose_width": 0.0, "shoulder_width": 0.0}
    assert final["character"]["scale"] == 1.0
    assert [(c["clip_id"], c["start_seconds"], c["duration_seconds"], c["looping"]) for c in final["timeline"]] == [
        ("idle", 0.0, 3.0, False), ("wave", 3.0, 3.0, False), ("turn", 6.0, 3.0, False)
    ]
    assert max(c["start_seconds"] + c["duration_seconds"] for c in final["timeline"]) == 9.0
    # Bind retained command/output files to the calls, not just to expected values.
    for step_index, argument_index, filename, phase in [
        (0, 2, "initial.nvwa.json", "after"),
        (2, 2, "appearance.commands.json", "before"),
        (2, 3, "appearance.nvwa.json", "after"),
        (3, 2, "stale-timeline.commands.json", "before"),
        (5, 2, "corrected-timeline.commands.json", "before"),
        (5, 3, "authored.nvwa.json", "after"),
        (7, 2, "agent-nine-second.nvwa.json", "after"),
    ]:
        assert (directory / filename).read_bytes() == (steps[step_index] / f"argument-{argument_index}.{phase}.json").read_bytes()
    assert read(directory / "stale-timeline.commands.json")["expected_revision"] == 0
    assert read(directory / "appearance.commands.json")["expected_revision"] == 0
    final_hash = hashlib.sha256(final_path.read_bytes()).hexdigest()
    assert final_hash == "e33356b490cb8d6c01118958c3d22409f4546cfa6164a7d69d496be292eb25cc"
    return {
        "disposition": manifest["disposition"],
        "verified_process_receipts": len(steps),
        "recorded_binary_sha256": next(iter(binary_hashes)),
        "final_work_sha256": final_hash,
        "revision": 2,
        "timeline_seconds": 9,
        "stale_request_failed_without_output": True,
        "actual_agent_claim": "see_TASK_and_DECISIONS_not_inferred_from_this_audit",
        "gui_native_web": "NOT-RUN_by_cli_worker"
    }


def audit_sources(manifest):
    repo = ROOT.parent.parent
    for relative, expected in manifest["sources"].items():
        path = pathlib.Path(relative)
        assert not path.is_absolute() and ".." not in path.parts
        assert hashlib.sha256((repo / path).read_bytes()).hexdigest() == expected, f"source hash mismatch: {relative}"


def main():
    historical = read(ROOT / "historical-manifest.json")
    accepted = read(ROOT / "accepted-run/source-manifest.json")
    for manifest in [historical, accepted]:
        audit_sources(manifest)
    results = [audit_run(ROOT, historical), audit_run(ROOT / "accepted-run", accepted)]
    old_caps = read(ROOT / "receipts/02-discover/stdout.txt")["cli_contract"]
    current_caps = read(ROOT / "accepted-run/receipts/02-discover/stdout.txt")["cli_contract"]
    assert old_caps["stdio"]["error_stdout"] == "empty", "historical snapshot must remain original, not current API"
    assert current_caps["stdio"]["filesystem_and_response_delivery_atomic"] is False
    assert "may_be_partial" in current_caps["stdio"]["error_stdout"]
    assert "inspect" in current_caps["error_recovery"]["stdout_write"]
    probe = read(ROOT / "review-response/process-probe/results.json")
    for call in probe["calls"]:
        assert call["binary_sha256"] == (historical if call["label"] == "original" else accepted)["recorded_binary_sha256"]
        if "output" in call:
            directory = ROOT / "review-response/process-probe"
            assert hashlib.sha256((directory / call["output"]).read_bytes()).hexdigest() == call["output_sha256"]
            error = (directory / call["stderr"]).read_bytes()
            assert call["exit_code"] == (101 if call["label"] == "original" else 1)
            if call["label"] == "revised":
                assert json.loads(error)["code"] == "stdout_write"
            else:
                assert b"failed printing to stdout" in error
    assert len(probe["calls"]) == 9
    stderr_controls = read(ROOT / "review-response/stderr-controls.json")
    assert {item["control"] for item in stderr_controls} == {"closed_stderr_domain", "closed_stdout_and_stderr"}
    for item in stderr_controls:
        assert item["exit_code"] == 1
        assert item["binary_sha256"] == accepted["recorded_binary_sha256"]
        assert item["stderr"] == "unavailable_closed_pipe_not_observed_empty"
    assert (ROOT / "record.py").read_bytes() == (ROOT / "accepted-run/record.py").read_bytes()
    red = (ROOT / "review-response/red-tests.stdout").read_text()
    green = (ROOT / "review-response/final-tests.stdout").read_text()
    for test in ["closed_stderr_does_not_turn_a_domain_failure_into_a_panic", "closed_stdout_reports_transport_error_after_save_without_panicking"]:
        assert f"test {test} ... FAILED" in red
        assert f"test {test} ... ok" in green
    print(json.dumps({"portable_retained_evidence_audit": True, "runs": results,
                      "source_manifests_checked": 2, "transport_probe_calls_checked": 9,
                      "closed_stderr_controls_checked": len(stderr_controls),
                      "executes_binary_model_rust_network_or_source_acquisition": False,
                      "authorship_limit": "checks_retained_records_not_hosted_LLM_authorship_or_signed_attestation"}, indent=2))


if __name__ == "__main__":
    main()
