#!/usr/bin/env python3
"""Assert retention discovery through the real CLI's public JSON output."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cli", type=Path)
    parser.add_argument("--save-output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    scene_path = root / "examples/default.nvwa.json"
    original = scene_path.read_bytes()
    scene = json.loads(original)

    def run(*arguments):
        result = subprocess.run([str(args.cli.resolve()), *map(str, arguments)], capture_output=True, text=True, timeout=5)
        assert result.returncode == 0, (arguments, result.returncode, result.stderr)
        return result.stdout

    capabilities = json.loads(run("describe-capabilities", scene_path))
    assert set(capabilities) == set(scene["profile"]) | {"editor_retention"}
    for key, value in scene["profile"].items():
        assert capabilities[key] == value, f"Existing profile capability changed: {key}"
    retention = capabilities["editor_retention"]
    assert retention["limits"] == {
        "history_snapshots": 128,
        "history_bytes": 16 * 1024 * 1024,
        "retry_entries": 1024,
        "retry_bytes": 8 * 1024 * 1024,
    }
    assert retention["session_local"] is True
    assert retention["persisted_in_document"] is False
    assert retention["eviction"] == "fifo"
    assert retention["duplicate_reads_refresh_retention"] is False
    assert retention["retained_identical_envelope"] == "duplicate"
    assert retention["retained_conflicting_id"] == "command_id_conflict"
    assert retention["expired_original_envelope"] == "revision_conflict"
    assert retention["expired_id_reuse"] == "allowed_with_current_revision_and_valid_command"
    assert retention["oversized_snapshot"] == "clear_destination_history_without_rejecting_edit"
    assert retention["oversized_retry_entry"] == "evict_all_older_entries_then_expire_without_rejecting_edit"
    assert retention["byte_accounting"] == {
        "history": "sum_of_compact_scene_document_json_bytes",
        "retry": "sum_of_compact_envelope_result_tuple_json_bytes",
        "excludes": ["live_document", "temporary_candidates", "allocation_overhead"],
    }
    inspected = json.loads(run("inspect", scene_path))
    assert inspected == scene
    assert "editor_retention" not in inspected
    help_output = run("help")
    assert "Commands: set_parameters, set_scale, set_timeline, undo, redo." in help_output
    assert scene_path.read_bytes() == original
    if args.save_output:
        with args.save_output.open("x") as output:
            output.write(json.dumps(capabilities, indent=2) + "\n")
    print(json.dumps({"result": "passed", "preserved_profile_keys": sorted(scene["profile"]), "limits": retention["limits"], "scene_sha256": hashlib.sha256(original).hexdigest(), "cli_sha256": hashlib.sha256(args.cli.read_bytes()).hexdigest()}, indent=2))


if __name__ == "__main__":
    main()
