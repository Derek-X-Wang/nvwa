#!/usr/bin/env python3
"""Observe existing CI commands. No downloads, command splitting, or cache changes."""
import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import re
import threading
import signal
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ("cargo",)
BINDING = ("GITHUB_WORKFLOW", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_JOB", "GITHUB_SHA", "NVWA_CI_HEAD_SHA")
PHASES = {"dependency-fetch", "compilation-command", "cargo-test-mixed", "toolchain-setup",
          "script-control-mixed", "shell-mixed", "unknown"}


def source():
    def git(*args):
        return subprocess.check_output(["git", "--no-optional-locks", "-C", str(ROOT), *args], text=True).strip()
    return {"head": git("rev-parse", "HEAD"), "tree": git("rev-parse", "HEAD^{tree}"),
            "dirty": bool(git("status", "--porcelain", "--untracked-files=normal"))}


def phase(tool, args):
    operation = args[0] if args else ""
    if tool == "cargo":
        if operation == "fetch":
            return "dependency-fetch"
        if operation == "test":
            return "cargo-test-mixed"
        if operation in ("build", "check", "clippy"):
            return "compilation-command"
    if tool == "rustup":
        return "toolchain-setup"
    if tool in ("python3", "node"):
        return "script-control-mixed"
    if tool == "bash":
        return "shell-mixed"
    return "unknown"


def record_directory(environment):
    if environment.get("NVWA_TIMING_DIR"):
        return Path(environment["NVWA_TIMING_DIR"])
    temporary = environment.get("RUNNER_TEMP", tempfile.gettempdir())
    return Path(temporary) / "nvwa-ci-timing" / environment.get("GITHUB_JOB", "local")


ANSI = re.compile(rb"\x1b\[[0-9;]*[A-Za-z]")


def cargo_streams(child):
    """Relay exact bytes on each stream; parse bounded copies, never child output."""
    observations = {"finished": [], "running": [], "test_results": [], "truncated": False}
    lock = threading.Lock()
    def relay(stream, target):
        pending = b""
        discarded_fragment = False
        try:
            while True:
                chunk = os.read(stream.fileno(), 65536)
                if not chunk:
                    break
                view = memoryview(chunk)
                while view:
                    count = os.write(target, view)
                    view = view[count:]
                pending += chunk
                lines = pending.split(b"\n")
                pending = lines.pop()
                for line in lines:
                    if discarded_fragment or len(line) > 65536:
                        observations["truncated"] = True
                        discarded_fragment = False
                        continue
                    line = ANSI.sub(b"", line)
                    event = None
                    if target == 2 and re.match(rb"^\s*Finished .+ target\(s\) in ", line):
                        event = ("finished", {"at_ns": time.monotonic_ns()})
                    elif target == 2 and re.match(rb"^\s*Running (?:unittests |tests/|.*\([^\n]+\))", line):
                        event = ("running", {"at_ns": time.monotonic_ns()})
                    else:
                        match = re.match(rb"^test result: (?:ok|FAILED)\..* finished in ([0-9]+(?:\.[0-9]+)?)s\s*$", line)
                        if target == 1 and match and math.isfinite(float(match[1])):
                            event = ("test_results", {"reported_seconds": float(match[1])})
                    if event:
                        with lock:
                            if sum(len(observations[key]) for key in ("finished", "running", "test_results")) >= 4096:
                                observations["truncated"] = True
                            else:
                                observations[event[0]].append(event[1])
                if len(pending) > 65536:
                    observations["truncated"] = True
                    discarded_fragment = True
                    pending = b""
            if pending or discarded_fragment:
                observations["truncated"] = True
        except OSError as error:
            # Closing this input lets Cargo observe a broken output pipe. Record
            # relay failures separately; never print observer data into its logs.
            with lock:
                observations["relay_error"] = type(error).__name__
        finally:
            stream.close()
    threads = [threading.Thread(target=relay, args=(child.stdout, 1)),
               threading.Thread(target=relay, args=(child.stderr, 2))]
    for thread in threads:
        thread.start()
    return observations, threads


def cargo_evidence(observations, started, ended, code):
    # Arrival times are stream observations, not CPU timing. libtest's own
    # durations are rounded and cover only binaries which print result lines.
    results = observations["test_results"]
    evidence = {"libtest_reported_seconds": sum(r["reported_seconds"] for r in results) if results and not observations.get("truncated") else None,
                "libtest_result_lines": len(results), "marker_stream_truncated": observations.get("truncated", False), "preparation_seconds": None,
                "execution_envelope_seconds": None, "status": "unknown"}
    finished = observations["finished"]
    running = observations["running"]
    if code == 0 and not observations.get("relay_error") and not observations.get("truncated") and finished and running and finished[0]["at_ns"] <= running[0]["at_ns"]:
        boundary = running[0]["at_ns"]
        evidence.update(preparation_seconds=(boundary-started)/1e9,
                        execution_envelope_seconds=(ended-boundary)/1e9, status="observed")
    evidence["relay_error"] = observations.get("relay_error")
    evidence["limit"] = "Preparation includes implicit resolution/fetch and launch; execution envelope can include doctest compilation. Marker arrival times are approximate. Missing/failed/truncated boundaries are unknown. Libtest durations are rounded partial coverage, not an additive phase total."
    return evidence


def observe(command, environment, directory, tool=None):
    """Inherit streams, cwd and environment; add only parent observation identity."""
    identifier = uuid.uuid4().hex
    child_environment = dict(environment, NVWA_TIMING_PARENT=identifier)
    tool = tool or Path(command[0]).name
    started = time.monotonic_ns()
    scope = "workspace/root"
    if tool == "cargo" and "--manifest-path" in command:
        index = command.index("--manifest-path")
        if index+1 < len(command):
            manifest = Path(command[index+1])
            candidate = manifest if manifest.is_absolute() else Path.cwd()/manifest
            try:
                scope = str(candidate.relative_to(ROOT))
            except ValueError:
                scope = "outside-workspace (argv digest only)"
    row = {"schema": 1, "id": identifier, "parent": environment.get("NVWA_TIMING_PARENT"),
           "source": json.loads(environment["NVWA_TIMING_SOURCE"]),
           "binding": {name: environment.get(name) for name in BINDING},
           "tool": tool, "cargo_scope": scope if tool == "cargo" else None, "operation": command[1] if len(command) > 1 and tool == "cargo" else None,
           "argv_sha256": hashlib.sha256(json.dumps(command).encode()).hexdigest(),
           "phase": phase(tool, command[1:]), "start_ns": started,
           "pid": os.getpid(), "status": "incomplete"}
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (identifier + ".json")
    # A killed/timed-out wrapper leaves an explicit incomplete observation.
    path.write_text(json.dumps(row) + "\n")
    previous = {}
    child = None
    try:
        is_cargo = tool == "cargo"
        child = subprocess.Popen(command, env=child_environment,
                                 stdout=subprocess.PIPE if is_cargo else None,
                                 stderr=subprocess.PIPE if is_cargo else None)
        observations, threads = cargo_streams(child) if is_cargo else (None, [])
        def forward(number, frame):
            if child.poll() is None:
                child.send_signal(number)
        for number in (signal.SIGINT, signal.SIGTERM):
            previous[number] = signal.signal(number, forward)
        code = child.wait()
        for thread in threads:
            thread.join()
        if observations and observations.get("relay_error"):
            row["observer_error"] = observations["relay_error"]
            if code == 0:
                code = 125  # A forwarding failure cannot become a green check.
    except OSError as error:
        row["error"] = type(error).__name__
        code = 127 if isinstance(error, FileNotFoundError) else 126
        print(f"ci-timing: cannot start {tool}: {error}", file=sys.stderr)
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)
    row.update(end_ns=time.monotonic_ns(), exit_code=code, status="complete")
    if tool == "cargo" and child is not None:
        row["cargo_observations"] = cargo_evidence(observations, started, row["end_ns"], code)
    # Atomic replacement keeps readers from treating a torn final write as valid.
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(row) + "\n")
    temporary.replace(path)
    return code


def execute(command):
    environment = os.environ.copy()
    directory = record_directory(environment).absolute()
    environment["NVWA_TIMING_DIR"] = str(directory)
    environment["NVWA_TIMING_SOURCE"] = json.dumps(source())
    # Every entry point resolves the unmodified PATH once. Tool shims are scoped
    # to this process tree, including Cargo called from captured Python children.
    originals = {tool: shutil.which(tool) for tool in TOOLS}
    with tempfile.TemporaryDirectory(prefix="nvwa-ci-timing-shims-") as temporary:
        shim = Path(temporary)
        for tool, original in originals.items():
            if original is None:
                continue  # Missing tools retain their original command-not-found failure.
            path = shim / tool
            # Keep symlink spelling: ~/.cargo/bin/cargo may dispatch through rustup.
            code = "#!" + sys.executable + "\nimport os,sys\nos.execv(" + repr(sys.executable) + ", " + repr([sys.executable, "-B", str(Path(__file__).resolve()), "tool", tool, original]) + " + sys.argv[1:])\n"
            path.write_text(code)
            path.chmod(0o755)
        environment["PATH"] = str(shim) + os.pathsep + environment.get("PATH", "")
        label = None
        if command[:2] == ["bash", "-e"]:
            body = Path(command[2]).read_text().strip()
            if body.startswith("rustup toolchain install ") and "\n" not in body:
                label = "rustup"
        if command[0] == "cargo" and originals["cargo"]:
            command = [originals["cargo"], *command[1:]]
            label = "cargo"
        return observe(command, environment, directory, label)


def load_records(directory):
    if not directory.is_dir():
        raise ValueError("timing records missing")
    paths = sorted(directory.glob("*.json"))
    if not paths:
        raise ValueError("timing records missing")
    records = []
    for path in paths:
        try:
            row = json.loads(path.read_text(), parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite number")))
            if (not isinstance(row, dict) or type(row.get("schema")) is not int or row["schema"] != 1
                    or not isinstance(row.get("phase"), str) or row["phase"] not in PHASES):
                raise ValueError("invalid schema or phase")
            if row.get("status") != "complete":
                raise ValueError("incomplete command (cancellation/timeout or missing final record)")
            if type(row.get("exit_code")) is not int or type(row.get("start_ns")) is not int or type(row.get("end_ns")) is not int or row["start_ns"] < 0 or row["end_ns"] < row["start_ns"]:
                raise ValueError("invalid command interval/status")
            if (not isinstance(row.get("id"), str) or not re.fullmatch(r"[0-9a-f]{32}", row["id"])
                    or (row.get("parent") is not None and (not isinstance(row["parent"], str) or not re.fullmatch(r"[0-9a-f]{32}", row["parent"])))
                    or not isinstance(row.get("source"), dict) or not isinstance(row.get("binding"), dict)):
                raise ValueError("missing source/run identity")
            if any(not isinstance(row["source"].get(key), str) or not re.fullmatch(r"[0-9a-f]{40}", row["source"][key]) for key in ("head", "tree")) or type(row["source"].get("dirty")) is not bool:
                raise ValueError("invalid source identity")
            if set(row["binding"]) != set(BINDING) or any(value is not None and not isinstance(value, str) for value in row["binding"].values()):
                raise ValueError("invalid run identity")
            if row.get("observer_error"):
                raise ValueError("stream forwarding failed")
            evidence = row.get("cargo_observations", {})
            if not isinstance(evidence, dict):
                raise ValueError("invalid Cargo observations")
            for key in ("preparation_seconds", "execution_envelope_seconds", "libtest_reported_seconds"):
                value = evidence.get(key)
                if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
                    raise ValueError("invalid Cargo observation")
            records.append(row)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            raise ValueError(f"unusable timing record {path.name}: {error}") from error
    if len({r["id"] for r in records}) != len(records):
        raise ValueError("duplicate timing record identity")
    bindings = {(json.dumps(r["binding"], sort_keys=True), json.dumps(r["source"], sort_keys=True)) for r in records}
    if len(bindings) != 1:
        raise ValueError("records mix source/run/job identities")
    by_id = {r["id"]: r for r in records}
    for row in records:
        parent = row.get("parent")
        if parent:
            visited = {row["id"]}
            cursor = parent
            while cursor in by_id:
                if cursor in visited:
                    raise ValueError("timing parent cycle")
                visited.add(cursor)
                cursor = by_id[cursor].get("parent")
            if parent not in by_id:
                raise ValueError("timing parent record missing")
            ancestor = by_id[parent]
            if ancestor["start_ns"] > row["start_ns"] or ancestor["end_ns"] < row["end_ns"]:
                raise ValueError("child interval outside parent")
    return sorted(records, key=lambda row: (row["start_ns"], row["id"]))


def union_ns(intervals):
    total = 0
    end = -1
    for start, stop in sorted(intervals):
        total += max(0, stop - max(start, end))
        end = max(end, stop)
    return total


def summary(records):
    totals = {name: 0 for name in sorted(PHASES)}
    for row in records:
        children = [(child["start_ns"], child["end_ns"]) for child in records if child.get("parent") == row["id"]]
        # Parent envelopes include child commands; subtract their interval union.
        exclusive = row["end_ns"] - row["start_ns"] - union_ns(children)
        totals[row["phase"]] += exclusive / 1e9
    lines = ["## Existing command timing", "", "Exclusive observed command wall seconds (nested child intervals removed; concurrent siblings can overlap, so these are not an additive job total):", "", "| Category | Seconds |", "| --- | ---: |"]
    for name, seconds in totals.items():
        value = f"{seconds:.3f}" if any(r["phase"] == name for r in records) else "NOT OBSERVED"
        lines += [f"| {name} | {value} |"]
    cargo_tests = [r for r in records if r["phase"] == "cargo-test-mixed"]
    lines += ["", "Cargo test stream observations (inclusive; do not add to exclusive totals):", "", "| Command | Exit | Preparation s | Execution envelope s | libtest reported s | Coverage |", "| --- | ---: | ---: | ---: | ---: | --- |"]
    for row in cargo_tests:
        evidence = row.get("cargo_observations", {})
        def number(key):
            value = evidence.get(key)
            return "UNKNOWN" if value is None else f"{value:.3f}"
        lines += [f"| `{row['id'][:8]}` {row.get('cargo_scope', 'unknown')} | {row['exit_code']} | {number('preparation_seconds')} | {number('execution_envelope_seconds')} | {number('libtest_reported_seconds')} | {evidence.get('status', 'unknown')} |"]
    lines += ["", "Cargo stream boundaries are best effort. Preparation includes implicit resolution/fetch and launch; execution envelope may include doctest compilation. Failed/missing/truncated markers are UNKNOWN. Libtest values are rounded partial binary coverage and not additive totals.", "", "`cargo-test-mixed` includes compilation and test execution. Compilation commands may include dependency resolution/fetching unless offline; `dependency-fetch` is explicit fetch only. Script/control and shell wall include uninstrumented work and overhead. These categories are not pure CPU compilation or pure test time. Tool startup/observer overhead remains in the enclosing command.", "", f"Commands: {len(records)}; nonzero exits: {sum(r['exit_code'] != 0 for r in records)} (expected mutation reds are retained).", "", "Source/run/job binding: `" + json.dumps({"source": records[0]["source"], "binding": records[0]["binding"]}, sort_keys=True) + "`", ""]
    return "\n".join(lines)


def report(directory, summary_path=None):
    try:
        records = load_records(directory)
        current = {name: os.environ.get(name) for name in BINDING}
        if records[0]["binding"] != current:
            raise ValueError("records do not match this source/run/attempt/job")
        output = summary(records)
        for row in records:
            print("NVWA_CI_TIMING " + json.dumps(row, sort_keys=True))
        code = 0
    except ValueError as error:
        output = f"## Existing command timing\n\nUNKNOWN / incomplete: {error}. No phase totals claimed.\n"
        code = 1
    print(output)
    if summary_path:
        with Path(summary_path).open("a") as stream:
            stream.write(output + "\n")
    return code


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("missing metadata timestamp")
    return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))


def queue_report(metadata, records=None):
    """Use completed GH REST run/jobs metadata, not inferred scheduler reasons."""
    run = metadata["run"]
    jobs = metadata["jobs"]
    created = timestamp(run["created_at"])
    portable = [j for j in jobs if j["name"] == "Core, CLI, and diagnostic controls"]
    if len(portable) != 1:
        raise ValueError("expected one portable job in one run attempt")
    gate = timestamp(portable[0]["completed_at"])
    names = {"Core, CLI, and diagnostic controls": False, "macOS CPU tests and Wasm compile check": True,
             "macOS B1 source regression and viewer checks": True}
    if len(jobs) != 3 or {j["name"] for j in jobs} != set(names):
        raise ValueError("unexpected job inventory")
    if (type(run.get("id")) is not int or run["id"] <= 0
            or type(run.get("run_attempt")) is not int or run["run_attempt"] <= 0
            or any(type(job.get("id")) is not int or job["id"] <= 0 for job in jobs)
            or len({job["id"] for job in jobs}) != len(jobs)):
        raise ValueError("invalid or duplicate run/attempt/job ID")
    rows = []
    for job in jobs:
        if job.get("run_id") != run["id"] or job.get("run_attempt") != run["run_attempt"] or job.get("head_sha") != run["head_sha"]:
            raise ValueError("job metadata does not match source/run/attempt")
        start = timestamp(job["started_at"])
        completed = timestamp(job["completed_at"])
        if completed < start:
            raise ValueError("job completes before starting")
        ready = max(created, gate) if names[job["name"]] else created
        if start < ready:
            raise ValueError("job starts before dependency gate")
        job_created = timestamp(job["created_at"])
        if job_created < created or start < job_created:
            raise ValueError("invalid job creation/start order")
        job_key = {"Core, CLI, and diagnostic controls": "portable",
                   "macOS CPU tests and Wasm compile check": "native-and-wasm",
                   "macOS B1 source regression and viewer checks": "b1-source-regression"}[job["name"]]
        rows.append({"job": job["name"], "job_key": job_key, "job_id": job["id"], "run_id": run["id"],
                     "attempt": run["run_attempt"], "head_sha": run["head_sha"],
                     "run_created_at": run["created_at"], "job_created_at": job["created_at"],
                     "job_started_at": job["started_at"], "job_completed_at": job["completed_at"],
                     "dependency_gate_seconds": (ready - created).total_seconds(),
                     "eligible_to_creation_seconds": max(0, (job_created-ready).total_seconds()),
                     "created_before_gate_seconds": max(0, (ready-job_created).total_seconds()),
                     "created_to_started_seconds": (start-job_created).total_seconds(),
                     "ready_to_started_seconds": (start - max(ready, job_created)).total_seconds(),
                     "limit": "Observed metadata gaps; scheduler/provisioning/concurrency causes unknown."})
    for record in records or []:
        binding = record["binding"]
        if (binding.get("GITHUB_RUN_ID") != str(run["id"])
                or binding.get("GITHUB_RUN_ATTEMPT") != str(run["run_attempt"])
                or binding.get("NVWA_CI_HEAD_SHA") != run["head_sha"]):
            raise ValueError("timing event head/run/attempt differs from metadata")
        matches = [row for row in rows if row["job_key"] == binding.get("GITHUB_JOB")]
        if len(matches) != 1:
            raise ValueError("timing job key cannot join metadata job ID")
        row = matches[0]
        row["timing_records_joined"] = row.get("timing_records_joined", 0)+1
        row["checkout_sha"] = record["source"]["head"]
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    shell = sub.add_parser("shell")
    shell.add_argument("script")
    run = sub.add_parser("run")
    run.add_argument("command", nargs=argparse.REMAINDER)
    tool = sub.add_parser("tool")
    tool.add_argument("name", choices=TOOLS)
    tool.add_argument("executable")
    tool.add_argument("arguments", nargs=argparse.REMAINDER)
    result = sub.add_parser("report")
    result.add_argument("--directory", type=Path)
    queue = sub.add_parser("queue")
    queue.add_argument("metadata", type=Path, help='JSON object with REST "run" and "jobs" values')
    queue.add_argument("--records", type=Path, action="append", default=[], help="join one or more job record directories")
    args = parser.parse_args()
    if args.mode == "shell":
        return execute(["bash", "-e", args.script])
    if args.mode == "run":
        command = args.command[1:] if args.command[:1] == ["--"] else args.command
        if not command:
            parser.error("run needs a command")
        return execute(command)
    if args.mode == "tool":
        return observe([args.executable, *args.arguments], os.environ, record_directory(os.environ), args.name)
    if args.mode == "report":
        return report(args.directory or record_directory(os.environ), os.environ.get("GITHUB_STEP_SUMMARY"))
    records = [row for directory in args.records for row in load_records(directory)]
    for row in queue_report(json.loads(args.metadata.read_text()), records):
        print(json.dumps(row, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        result = main()
        if result < 0:
            # Python callers must observe the original negative signal status.
            # All receipts and execute()'s temporary shims are finalized first.
            number = -result
            if number not in (signal.SIGKILL, signal.SIGSTOP):
                signal.signal(number, signal.SIG_DFL)
            os.kill(os.getpid(), number)
        sys.exit(result)
    except (ValueError, OSError, KeyError) as error:
        print(f"ci-timing: {error}", file=sys.stderr)
        sys.exit(1)
