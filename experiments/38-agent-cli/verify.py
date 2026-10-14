#!/usr/bin/env python3
"""Audit stored process receipts; this does not impersonate an adaptive agent."""
import hashlib
import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def main():
    steps = sorted((ROOT / "receipts").glob("[0-9][0-9]-*"))
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
    assert not (ROOT / "stale-output.nvwa.json").exists()
    inspected = read(steps[4] / "stdout.txt")
    corrected = read(ROOT / "corrected-timeline.commands.json")
    assert inspected["revision"] == corrected["expected_revision"] == 1
    assert read(steps[6] / "stdout.txt") == {"asset_checked": True, "revision": 2, "valid": True}
    final_path = ROOT / "agent-nine-second.nvwa.json"
    final = read(final_path)
    assert final == read(steps[8] / "stdout.txt") == read(ROOT / "authored.nvwa.json")
    assert final["revision"] == 2
    assert final["character"]["parameters"] == {"jaw_width": 0.42, "smile": 0.2, "nose_width": 0.0, "shoulder_width": 0.0}
    assert final["character"]["scale"] == 1.0
    assert [(c["clip_id"], c["start_seconds"], c["duration_seconds"], c["looping"]) for c in final["timeline"]] == [
        ("idle", 0.0, 3.0, False), ("wave", 3.0, 3.0, False), ("turn", 6.0, 3.0, False)
    ]
    assert max(c["start_seconds"] + c["duration_seconds"] for c in final["timeline"]) == 9.0
    print(json.dumps({
        "verified_process_receipts": len(steps),
        "binary_sha256": next(iter(binary_hashes)),
        "final_work_sha256": hashlib.sha256(final_path.read_bytes()).hexdigest(),
        "revision": 2,
        "timeline_seconds": 9,
        "stale_request_failed_without_output": True,
        "actual_agent_claim": "see_TASK_and_DECISIONS_not_inferred_from_this_audit",
        "gui_native_web": "NOT-RUN_by_cli_worker"
    }, indent=2))


if __name__ == "__main__":
    main()
