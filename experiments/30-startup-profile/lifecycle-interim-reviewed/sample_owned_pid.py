#!/usr/bin/env python3
"""External guard for every fixed bundle; profiling remains independently gated."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inspect(pid):
    output = subprocess.run(["/bin/ps", "-ww", "-p", str(pid), "-o",
        "pid=,ppid=,rss=,lstart=,comm="], capture_output=True, text=True).stdout.strip()
    if not output:
        return None
    values = output.split(None, 8)
    if len(values) != 9 or int(values[0]) != pid:
        raise RuntimeError("ambiguous process identity")
    return {"pid": int(values[0]), "ppid": int(values[1]), "rss_kib": int(values[2]),
        "kernel_start_identity": " ".join(values[3:8]), "comm": values[8]}


def same_owned(identity, frozen, verify_hash=False):
    matches = identity is not None and identity["pid"] == frozen["pid"] and \
        identity["kernel_start_identity"] == frozen["kernel_start_identity"] and \
        Path(identity["comm"]).resolve() == Path(frozen["binary"]).resolve()
    return matches and (not verify_hash or sha(frozen["binary"]) == frozen["binary_sha256"])


def receipt(boundary, **fields):
    return {"boundary": boundary, "clock": "host_time_monotonic_ns",
        "monotonic_ns": time.monotonic_ns(), "wall_time_ns": time.time_ns(), **fields}


def stop_exact(frozen, rows, grace=2.0, reap=None):
    """No signal without identity; recheck hash before each escalation."""
    def observe():
        if reap: reap()
        return inspect(frozen["pid"])
    live = observe()
    if live is None:
        rows.append(receipt("target_exit_verified_before_cleanup", pid=frozen["pid"]))
        return "exit_verified"
    if not same_owned(live, frozen, verify_hash=True):
        rows.append(receipt("cleanup_blocked_identity_not_proven", pid=frozen["pid"], observed=live))
        return "blocked"
    try:
        os.kill(frozen["pid"], signal.SIGTERM)
    except ProcessLookupError:
        if observe() is None:
            rows.append(receipt("target_exit_verified_during_SIGTERM_race", pid=frozen["pid"]))
            return "exit_verified"
        rows.append(receipt("cleanup_blocked_SIGTERM_race_identity", pid=frozen["pid"]))
        return "blocked"
    rows.append(receipt("SIGTERM_sent_after_exact_frozen_identity_check", **live))
    until = time.monotonic() + grace
    while time.monotonic() < until:
        observed = observe()
        if observed is None:
            rows.append(receipt("target_exit_verified_after_SIGTERM", pid=frozen["pid"]))
            return "exit_verified"
        if not same_owned(observed, frozen):
            rows.append(receipt("cleanup_blocked_identity_changed_after_SIGTERM", observed=observed))
            return "blocked"
        time.sleep(0.05)
    observed = observe()
    if observed is None:
        rows.append(receipt("target_exit_verified_after_SIGTERM", pid=frozen["pid"]))
        return "exit_verified"
    if not same_owned(observed, frozen, verify_hash=True):
        rows.append(receipt("cleanup_blocked_identity_not_proven_before_SIGKILL", observed=observed))
        return "blocked"
    try:
        os.kill(frozen["pid"], signal.SIGKILL)
    except ProcessLookupError:
        if observe() is None:
            rows.append(receipt("target_exit_verified_during_SIGKILL_race", pid=frozen["pid"]))
            return "exit_verified"
        rows.append(receipt("cleanup_blocked_SIGKILL_race_identity", pid=frozen["pid"]))
        return "blocked"
    rows.append(receipt("SIGKILL_sent_after_reverified_same_frozen_identity", **observed))
    until = time.monotonic() + grace
    while time.monotonic() < until:
        if observe() is None:
            rows.append(receipt("target_exit_verified_after_SIGKILL", pid=frozen["pid"]))
            return "exit_verified"
        time.sleep(0.05)
    rows.append(receipt("cleanup_blocked_exit_not_verified", pid=frozen["pid"]))
    return "blocked"


def run_guard(args):
    frozen = json.loads((args.evidence / "launcher.json").read_text())
    if frozen["pid"] <= 1 or not Path(frozen["binary"]).is_absolute() or sha(frozen["binary"]) != frozen["binary_sha256"]:
        raise RuntimeError("invalid exact launcher freeze receipt")
    rows = [receipt("external_guard_started", pid=frozen["pid"], case=frozen["case"],
        kernel_start_identity=frozen["kernel_start_identity"], binary=frozen["binary"],
        binary_sha256=frozen["binary_sha256"], deadline_seconds=args.deadline)]
    deadline_ns = frozen["monotonic_ns"] + int(args.deadline * 1e9)
    marker_seen, profilers, status = False, [], "running"
    while time.monotonic_ns() < deadline_ns:
        observed = inspect(frozen["pid"])
        if observed is None:
            rows.append(receipt("target_exit_verified", pid=frozen["pid"], exit_code="NOT-OBSERVABLE by child watchdog"))
            status = "exit_verified"
            break
        if observed["kernel_start_identity"] != frozen["kernel_start_identity"]:
            rows.append(receipt("guard_blocked_kernel_identity_changed", observed=observed))
            status = "blocked"
            break
        # Launcher->Rust exec can be in progress. It never authorizes signals to
        # an interpreter or another executable. Hash only at start/signals;
        # repeated whole-binary hashing would disturb the measurement.
        if same_owned(observed, frozen):
            if frozen["case"] in ("native-1", "native-2"):
                rows.append(receipt("rss_sample", **observed))
            if not marker_seen:
                for line in (args.evidence / "stderr.log").read_text(errors="replace").splitlines():
                    if line.startswith("NVWA_STARTUP_PROBE "):
                        marker = json.loads(line.removeprefix("NVWA_STARTUP_PROBE "))
                        if marker.get("pid") == frozen["pid"] and marker.get("boundary") == "before_build_app":
                            marker_seen = True
                            rows.append(receipt("real_rust_startup_marker_verified", **observed))
                            break
                if marker_seen and frozen["case"] == "native-2":
                    for name, command in [
                        ("sample", ["/usr/bin/sample", str(frozen["pid"]), "4", "1", "-file", str(args.evidence / "sample.txt")]),
                        ("vmmap", ["/usr/bin/vmmap", "-summary", str(frozen["pid"])]),
                    ]:
                        log = (args.evidence / (name + "-command.log")).open("x")
                        child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
                        identity = inspect(child.pid)
                        child_freeze = None if identity is None else {**identity, "binary": identity["comm"], "binary_sha256": sha(identity["comm"])}
                        profilers.append((name, child, log, child_freeze))
                        rows.append(receipt("profiler_started", profiler=name, profiler_pid=child.pid, target_pid=frozen["pid"], command=command))
        time.sleep(0.1)
    else:
        rows.append(receipt("owned_run_deadline_reached", pid=frozen["pid"], marker_seen=marker_seen))
        status = stop_exact(frozen, rows, args.grace)
    if not marker_seen and frozen["case"].startswith("native-"):
        rows.append(receipt("profiling_NOT_RUN_no_rust_marker_guard_still_applied", pid=frozen["pid"]))
    for name, child, log, child_freeze in profilers:
        if child.poll() is None:
            if child_freeze is None:
                rows.append(receipt("profiler_cleanup_blocked_identity_unavailable", profiler=name, profiler_pid=child.pid))
                status = "blocked"
            elif stop_exact(child_freeze, rows, args.grace, reap=child.poll) == "blocked":
                status = "blocked"
        try:
            child.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            status = "blocked"
        rows.append(receipt("profiler_exit_observation", profiler=name, profiler_pid=child.pid, exit_code=child.poll()))
        log.close()
    result = {"status": status, "target_pid": frozen["pid"], "marker_seen": marker_seen, "observations": rows}
    (args.evidence / "process-observations.json").write_text(json.dumps(result, indent=2) + "\n")
    print("NVWA_EXTERNAL_GUARD " + json.dumps({"status": status, "target_pid": frozen["pid"], "marker_seen": marker_seen}), flush=True)
    return 0 if status == "exit_verified" else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--deadline", type=float, default=54.0)
    parser.add_argument("--grace", type=float, default=2.0)
    args = parser.parse_args()
    if not args.evidence.is_absolute() or not 0 < args.deadline <= 54 or not 0 < args.grace <= 2:
        parser.error("absolute evidence, deadline<=54s and per-signal grace<=2s required")
    try:
        return run_guard(args)
    except Exception as error:
        # A failed identity read or permission error never authorizes a signal.
        result = {"status": "blocked", "error": repr(error),
            "observations": [receipt("guard_blocked_exception_no_further_signals", error_type=type(error).__name__)]}
        (args.evidence / "process-observations.json").write_text(json.dumps(result, indent=2) + "\n")
        print("NVWA_EXTERNAL_GUARD " + json.dumps(result), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
