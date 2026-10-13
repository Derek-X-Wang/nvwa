#!/usr/bin/env python3
"""Task-owned .app executable. Only cua launches this fixed, verified bundle."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def launch():
    config_path = Path(__file__).resolve().parent.parent / "Resources" / "launch.json"
    config = json.loads(config_path.read_text())
    if config.get("approved_frozen") is not True:
        raise RuntimeError("source-only bundle: root-approved freeze and GPU lease required")
    for member in config["frozen_inputs"]:
        path = Path(member["path"])
        if not path.is_absolute() or sha(path) != member["sha256"]:
            raise RuntimeError("frozen input changed: " + str(path))
    binary = Path(config["binary"])
    if sha(binary) != config["binary_sha256"]:
        raise RuntimeError("frozen executable mismatch")
    evidence = Path(config["evidence"])
    if not evidence.is_absolute() or not evidence.is_dir():
        raise RuntimeError("exact root-created evidence directory required")
    # Exclusive creation makes a replay fail before any new renderer starts.
    guard = os.open(evidence / "launch-once.guard", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(guard)
    stdout = os.open(evidence / "stdout.log", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    stderr = os.open(evidence / "stderr.log", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.dup2(stdout, 1)
    os.dup2(stderr, 2)
    os.close(stdout)
    os.close(stderr)
    os.chdir(config["cwd"])
    env = dict(os.environ)
    env.update(config["environment"])
    record = {"boundary": "bundle_launcher_before_exec", "pid": os.getpid(),
        "ppid": os.getppid(), "wall_time_ns": time.time_ns(),
        "clock": "host_time_monotonic_ns", "monotonic_ns": time.monotonic_ns(),
        "binary": str(binary), "binary_sha256": config["binary_sha256"],
        "argv": [str(binary), *config["arguments"]], "cwd": str(Path.cwd()),
        "case": config["case"], "bundle": str(config_path.parent.parent.parent)}
    identity_query = subprocess.run(["/bin/ps", "-ww", "-p", str(os.getpid()),
        "-o", "pid=,lstart="], capture_output=True, text=True, timeout=0.3)
    if identity_query.returncode != 0 or identity_query.stderr.strip():
        (evidence / "launcher-blocked.json").write_text(json.dumps({
            "status": "blocked", "reason": "launcher_identity_query_failed",
            "pid": os.getpid(), "returncode": identity_query.returncode,
            "stderr": identity_query.stderr, "renderer_started": False}, indent=2) + "\n")
        raise RuntimeError("bounded launcher identity query failed; renderer not started")
    identity = identity_query.stdout.strip().split(None, 1)
    if len(identity) != 2 or int(identity[0]) != os.getpid():
        raise RuntimeError("exact launcher kernel identity unavailable")
    record["kernel_start_identity"] = " ".join(identity[1].split())
    def save_record():
        temporary = evidence / "launcher.json.tmp"
        temporary.write_text(json.dumps(record, indent=2) + "\n")
        temporary.replace(evidence / "launcher.json")
    save_record()
    # All apps, including pixels, need an external pre-schedule watchdog.
    helper = subprocess.Popen([sys.executable, "-B", config["sampler"],
        "--evidence", str(evidence)], stdin=subprocess.DEVNULL,
        stdout=2, stderr=2, start_new_session=True)
    record["sampler_pid"] = helper.pid
    save_record()
    print("NVWA_LAUNCHER " + json.dumps(record), flush=True)
    # Keep the LaunchServices PID across Python -> exact Rust executable.
    os.execve(binary, [str(binary), *config["arguments"]], env)


def main():
    try:
        launch()
    except Exception as error:
        # os.execve never returns on success. All errors here precede Rust
        # launch; any already-created watchdog observes this launcher exit.
        config_path = Path(__file__).resolve().parent.parent / "Resources" / "launch.json"
        try:
            config = json.loads(config_path.read_text())
            evidence = Path(config["evidence"])
            if evidence.is_absolute() and evidence.is_dir():
                (evidence / "launcher-blocked.json").write_text(json.dumps({
                    "status": "blocked", "pid": os.getpid(), "error": repr(error),
                    "renderer_started": False, "guard_if_started_must_verify_launcher_exit": True}, indent=2) + "\n")
        except Exception:
            pass
        print("NVWA_LAUNCHER_BLOCKED " + repr(error), file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
