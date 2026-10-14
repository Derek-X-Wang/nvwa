#!/usr/bin/env python3
"""Synthetic differential process probe; not an adaptive-agent authoring run."""
import hashlib
import json
import os
import pathlib
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    old, revised = map(pathlib.Path, sys.argv[1:])
    directory = pathlib.Path(__file__).resolve().parent
    evidence = directory / "process-probe"
    evidence.mkdir(exist_ok=False)
    experiment = directory.parent
    root = experiment.parent.parent
    initial = experiment / "initial.nvwa.json"
    original_input = sha(initial)
    final = experiment / "agent-nine-second.nvwa.json"
    final_before = sha(final)
    results = []
    for label, binary, expected_exit in [("original", old, 101), ("revised", revised, 1)]:
        for verb in ["new", "apply", "save"]:
            saved = evidence / f"{label}-{verb}.nvwa.json"
            arguments = {
                "new": [str(root / "assets/character.profile.json"), str(saved)],
                "apply": [str(initial), str(experiment / "appearance.commands.json"), str(saved)],
                "save": [str(initial), str(saved)],
            }[verb]
            argv = [str(binary), verb, *arguments]
            reader, writer = os.pipe()
            os.close(reader)
            try:
                completed = subprocess.run(argv, stdout=writer, stderr=subprocess.PIPE, check=False)
            finally:
                os.close(writer)
            stderr = evidence / f"{label}-{verb}.stderr"
            stderr.write_bytes(completed.stderr)
            output = json.loads(saved.read_text())
            assert completed.returncode == expected_exit
            assert output["revision"] == (1 if verb == "apply" else 0)
            assert sha(initial) == original_input
            if label == "revised":
                error = json.loads(completed.stderr)
                assert error["code"] == "stdout_write"
                assert "inspect" in error["message"]
                assert b"panicked" not in completed.stderr
            else:
                assert b"failed printing to stdout" in completed.stderr
            results.append({
                "label": label, "argv": argv, "binary_sha256": sha(binary),
                "stdout": "actual_pipe_reader_closed_before_process_start_no_consumer",
                "stderr": stderr.name, "exit_code": completed.returncode,
                "output": saved.name, "output_revision": output["revision"],
                "output_sha256": sha(saved), "original_input_unchanged": True,
            })
    # Read-only production calls confirm current discovery and the exact same work.
    for verb in ["describe-capabilities", "inspect", "validate"]:
        argv = [str(revised), verb, str(final)]
        if verb == "validate":
            argv.append(str(root / "assets"))
        completed = subprocess.run(argv, capture_output=True, check=False)
        (evidence / f"revised-{verb}.stdout").write_bytes(completed.stdout)
        (evidence / f"revised-{verb}.stderr").write_bytes(completed.stderr)
        assert completed.returncode == 0 and not completed.stderr
        results.append({"label": "revised", "argv": argv, "binary_sha256": sha(revised), "exit_code": 0,
                        "stdout": f"revised-{verb}.stdout", "stderr": f"revised-{verb}.stderr"})
    assert sha(final) == final_before == "e33356b490cb8d6c01118958c3d22409f4546cfa6164a7d69d496be292eb25cc"
    report = {"scope": "synthetic_real_process_transport_probe_not_agent_proof", "cwd": str(pathlib.Path.cwd()),
              "calls": results, "final_work_sha256": final_before, "final_work_unchanged": True}
    (evidence / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"calls": len(results), "original_closed_stdout_exit": 101,
                      "revised_closed_stdout_exit": 1, "new_save_apply_outputs_already_committed": True,
                      "final_work_sha256": final_before}, indent=2))


if __name__ == "__main__":
    main()
