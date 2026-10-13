#!/usr/bin/env python3
"""Root-leased sole Cargo writer with storage/deadline and protected-lock checks."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

REPO = Path(__file__).resolve().parents[2]
TARGET = Path("/Users/derekxwang/Development/incubator/Nvwa/nvwa/target")
LOCK_SHA = "457f603a78c6822b6dec754978c425ed6b61d4ed3acd0b856e606e180f5c4e73"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command or command[0] != "cargo" or not args.name.replace("-", "").isalnum():
        parser.error("named Cargo command required")
    if sha(REPO / "Cargo.lock") != LOCK_SHA:
        raise RuntimeError("protected root Cargo.lock changed before command")
    free = shutil.disk_usage(TARGET).free
    if free <= 32 * 1024**3:
        raise RuntimeError("root initial32GiB storage floor not met")
    evidence = REPO / ".work/m11-startup/compile" / args.name
    evidence.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ)
    env.update(CARGO_TARGET_DIR=str(TARGET), CARGO_BUILD_JOBS="1")
    began = time.monotonic()
    record = {"command": command, "cwd": str(REPO), "target": str(TARGET),
        "initial_free_bytes": free, "monotonic_start_ns": time.monotonic_ns(),
        "wall_start_ns": time.time_ns(), "root_lock_before": LOCK_SHA, "storage_samples": []}
    with (evidence / "stdout.log").open("x") as stdout, (evidence / "stderr.log").open("x") as stderr:
        child = subprocess.Popen(command, cwd=REPO, env=env, stdin=subprocess.DEVNULL,
            stdout=stdout, stderr=stderr, start_new_session=True)
        record.update(owned_pid=child.pid, owned_process_group=child.pid)
        (evidence / "started.json").write_text(json.dumps(record, indent=2) + "\n")
        print(json.dumps({"started": args.name, "owned_pid": child.pid, "initial_free_gib": round(free / 1024**3, 2)}), flush=True)
        last_update = -30
        abort = None
        while child.poll() is None:
            elapsed = time.monotonic() - began
            free = shutil.disk_usage(TARGET).free
            record["storage_samples"].append({"elapsed_seconds": elapsed, "free_bytes": free})
            if free < 8 * 1024**3 or elapsed > 1800:
                abort = "storage_below8GiB" if free < 8 * 1024**3 else "deadline30minutes"
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
                break
            if elapsed - last_update >= 30:
                lines = (evidence / "stderr.log").read_text(errors="replace").splitlines()
                print(json.dumps({"stage": args.name, "elapsed_seconds": round(elapsed, 1),
                    "free_gib": round(free / 1024**3, 2), "latest": lines[-1] if lines else None}), flush=True)
                last_update = elapsed
            time.sleep(2)
        record.update(exit_code=child.returncode, abort=abort, elapsed_seconds=time.monotonic() - began,
            root_lock_after=sha(REPO / "Cargo.lock"), final_free_bytes=shutil.disk_usage(TARGET).free)
    (evidence / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"finished": args.name, "exit_code": child.returncode, "abort": abort,
        "elapsed_seconds": round(record["elapsed_seconds"], 2), "root_lock_unchanged": record["root_lock_after"] == LOCK_SHA}), flush=True)
    if record["root_lock_after"] != LOCK_SHA:
        raise RuntimeError("protected root lock drift")
    return 1 if abort else child.returncode


if __name__ == "__main__":
    raise SystemExit(main())
