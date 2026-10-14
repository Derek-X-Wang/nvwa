#!/usr/bin/env python3
"""Record one real CLI call; contains no authoring choices or workflow sequence."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if len(sys.argv) < 4:
        raise SystemExit("usage: record.py STEP /absolute/nvwa-cli COMMAND [ARGS...]")
    step, binary, *args = sys.argv[1:]
    directory = pathlib.Path(__file__).resolve().parent
    receipts = directory / "receipts" / step
    receipts.mkdir(parents=True, exist_ok=False)
    before = {}
    for index, arg in enumerate(args):
        path = pathlib.Path(arg)
        if path.is_file() and path.suffix == ".json":
            content = path.read_bytes()
            snapshot = f"argument-{index}.before.json"
            (receipts / snapshot).write_bytes(content)
            before[arg] = {"sha256": digest(path), "snapshot": snapshot}
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result = subprocess.run([binary, *args], capture_output=True, check=False)
    (receipts / "stdout.txt").write_bytes(result.stdout)
    (receipts / "stderr.txt").write_bytes(result.stderr)
    after = {}
    for index, arg in enumerate(args):
        path = pathlib.Path(arg)
        if path.is_file() and path.suffix == ".json":
            snapshot = f"argument-{index}.after.json"
            (receipts / snapshot).write_bytes(path.read_bytes())
            after[arg] = {"sha256": digest(path), "snapshot": snapshot}
    record = {
        "step": step,
        "started_utc": started,
        "finished_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cwd": str(pathlib.Path.cwd()),
        "argv": [binary, *args],
        "binary_sha256": digest(pathlib.Path(binary)),
        "exit_code": result.returncode,
        "stdout": "stdout.txt",
        "stderr": "stderr.txt",
        "json_arguments_before": before,
        "json_arguments_after": after,
        "tool_route": "Codex Desktop native collaboration worker -> functions.exec -> exec_command -> Python subprocess -> production nvwa-cli",
        "authoring_decisions": "made_by_LLM_between_separately_recorded_calls",
    }
    (receipts / "invocation.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"step": step, "exit_code": result.returncode, "receipt": str(receipts)}))
    sys.stdout.flush()
    sys.stdout.buffer.write(result.stdout)
    sys.stdout.flush()
    sys.stderr.buffer.write(result.stderr)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
