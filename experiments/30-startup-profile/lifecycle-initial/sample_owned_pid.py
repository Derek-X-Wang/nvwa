#!/usr/bin/env python3
"""Bounded exact-PID sampler. Wait for the real Rust startup marker before inspecting."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def stamp(boundary, **fields):
    return {"boundary": boundary, "clock": "host_time_monotonic_ns",
        "monotonic_ns": time.monotonic_ns(), "wall_time_ns": time.time_ns(), **fields}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--profile", action="store_true")
    parser.add_argument("--rss-only", action="store_true")
    args = parser.parse_args()
    if args.pid <= 1 or not args.evidence.is_absolute() or not args.binary.is_absolute() or args.profile == args.rss_only:
        parser.error("exact owned PID, absolute evidence and exactly one mode required")
    evidence = args.evidence
    began = time.monotonic()
    rows, children = [], []
    verified = False
    while time.monotonic() - began < 59:
        try:
            marker_lines = (evidence / "stderr.log").read_text(errors="replace").splitlines()
        except FileNotFoundError:
            marker_lines = []
        for line in marker_lines:
            if line.startswith("NVWA_STARTUP_PROBE "):
                marker = json.loads(line.removeprefix("NVWA_STARTUP_PROBE "))
                if marker.get("pid") == args.pid and marker.get("boundary") == "before_build_app":
                    verified = True
                    break
        if verified:
            rows.append(stamp("real_rust_startup_marker_verified", pid=args.pid))
            break
        check = subprocess.run(["/bin/ps", "-p", str(args.pid), "-o", "pid="], capture_output=True, text=True)
        if not check.stdout.strip():
            break
        time.sleep(0.02)
    if verified:
        def owned_process():
            result = subprocess.run(["/bin/ps", "-ww", "-p", str(args.pid), "-o", "pid=,ppid=,rss=,lstart=,comm="], capture_output=True, text=True)
            if not result.stdout.strip():
                return None
            values = result.stdout.strip().split(None, 8)
            if len(values) != 9 or int(values[0]) != args.pid or Path(values[8]).resolve() != args.binary.resolve():
                return None
            return {"pid": int(values[0]), "ppid": int(values[1]), "rss_kib": int(values[2]),
                "kernel_start_identity": " ".join(values[3:8]), "comm": values[8]}
        initial = owned_process()
        if initial is None:
            rows.append(stamp("profiling_NOT_RUN_owned_binary_not_live", pid=args.pid))
            (evidence / "process-observations.json").write_text(json.dumps(rows, indent=2) + "\n")
            return
        birth = initial["kernel_start_identity"]
        rows.append(stamp("exact_owned_binary_and_start_verified", **initial))
        if args.profile:
            for name, command in [
                ("sample", ["/usr/bin/sample", str(args.pid), "4", "1", "-file", str(evidence / "sample.txt")]),
                ("vmmap", ["/usr/bin/vmmap", "-summary", str(args.pid)]),
            ]:
                log = (evidence / (name + "-command.log")).open("x")
                child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
                children.append((name, child, log))
                rows.append(stamp("profiler_started", profiler=name, profiler_pid=child.pid, target_pid=args.pid, command=command))
        while time.monotonic() - began < 59:
            observed = owned_process()
            if observed is None or observed["kernel_start_identity"] != birth:
                rows.append(stamp("owned_pid_not_observed", pid=args.pid))
                break
            # ps RSS is resident KiB, sampled; no true peak or total GPU-memory claim.
            rows.append(stamp("rss_sample", **observed))
            time.sleep(0.1)
        else:
            # Root's finite60second owned-run deadline. Reverify exact executable
            # and kernel start identity immediately before this scoped cleanup.
            observed = owned_process()
            if observed is not None and observed["kernel_start_identity"] == birth:
                os.kill(args.pid, signal.SIGTERM)
                rows.append(stamp("owned_run_deadline_SIGTERM_sent", **observed))
    else:
        rows.append(stamp("profiling_NOT_RUN_no_verified_rust_marker", pid=args.pid))
    for name, child, log in children:
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.terminate()
            child.wait(timeout=5)
        rows.append(stamp("profiler_returned", profiler=name, profiler_pid=child.pid, exit_code=child.returncode))
        log.close()
    (evidence / "process-observations.json").write_text(json.dumps(rows, indent=2) + "\n")
    # Normal exit belongs to finite product smoke; only the authorized deadline
    # cleanup can terminate the freshly reverified exact owned process.


if __name__ == "__main__":
    main()
