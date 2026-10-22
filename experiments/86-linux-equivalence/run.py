#!/usr/bin/env python3
"""Bounded same-source Linux replay of the two baseline macOS CI inventories.

`plan` reads only. `run` executes commands, including ordinary Cargo dependency
downloads. It requires a separate, disposable checkout at the frozen baseline.
No graphical, GPU, desktop, or browser acceptance is inferred from this replay.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import signal
import subprocess
import sys
import time

BASE_SHA = "baa0b6bbda0d9709f0fab37c9e7d962fd8d926c1"
BASE_TREE = "f14ea4fa6ea749fdd06c36e0fca5d622feb5bb95"
CI_SHA256 = "f05fab4054cd9b2909b4724c53b89397c2e875b863d631ea46a073e969c365b3"
DRIVER_SHA256 = "a3e450f1e6f6033fc9506862d476033b2b642f0c0a1e49520228d940e9ac438a"
LANES = {
    "native-and-wasm": [
        "Run workspace CPU tests",
        "Check appearance quality and production acceptance bridges",
        "Check B1 production-source mutation witnesses",
        "Execute the actual B1 continuous motion matrix",
    ],
    "b1-source-regression": [
        "Prepare pinned B1 inputs without asset or tool downloads",
        "Execute real B1 source and sampled pose regression",
        "Check the same B1 viewer for native and Web",
        "Compile the actual Web target",
    ],
}
# Explicit exclusions concern platform cache policy or runner provisioning only.
EXCLUSIONS = {
    "Install repository Rust version": "provisioned by experiment workflow; record installed versions",
    "Report existing command timing": "replaced by per-command retained logs and elapsed times",
    "Prepare main-only native seed": "macOS cache policy",
    "Verify main restore or safely prepare complete cold fallback": "macOS cache policy",
    "Prepare bounded native cache trial": "macOS cache policy",
    "Measure cold exact-key miss": "macOS cache policy",
    "Verify restored sources, all gates and target cap": "macOS cache policy",
    "Assert real persisted exact hit": "macOS cache policy",
    "Verify main seed gates and complete logical size": "macOS cache policy",
    "Record verified persistence or explicit cache service failure": "macOS cache policy",
}
NATIVE_DRIVER = "bash experiments/27-ci-baseline/check.sh native"
HARN_ROOT = Path(__file__).resolve().parents[2]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def git(source, *args):
    return subprocess.check_output(["git", "-C", str(source), *args]).decode().strip()


def source_identity(source):
    require(git(source, "rev-parse", "--show-toplevel") == str(source), "source must be checkout root")
    require(git(source, "rev-parse", "HEAD") == BASE_SHA, "source HEAD differs from frozen baseline")
    require(git(source, "rev-parse", "HEAD^{tree}") == BASE_TREE, "source tree differs from frozen baseline")
    require(not git(source, "status", "--porcelain", "--untracked-files=no"), "source tracked files are dirty")
    entries = subprocess.check_output(["git", "-C", str(source), "ls-files", "--stage", "-z"])
    files = {}
    for entry in entries.split(b"\0"):
        if not entry:
            continue
        metadata, relative = entry.split(b"\t", 1)
        mode, blob, stage = metadata.decode().split()
        require(stage == "0" and mode != "160000", "unmerged entries/submodules are unsupported")
        name = os.fsdecode(relative)
        path = source / name
        data = os.fsencode(os.readlink(path)) if path.is_symlink() else path.read_bytes()
        files[name] = {"mode": mode, "blob": blob, "sha256": sha(data)}
    return {"head": BASE_SHA, "tree": BASE_TREE, "tracked_files": files,
            "tracked_locks": {p: value["sha256"] for p, value in files.items() if p.endswith("Cargo.lock")}}


def extract_run_steps(text, lane):
    """Deliberately narrow parser for the pinned workflow; no YAML dependency.

    The whole-file digest is checked before parsing, so unsupported YAML edits
    cannot silently become a smaller inventory.
    """
    require(sha(text.encode()) == CI_SHA256, "baseline ci.yml extraction drift")
    match = re.search(r"^  " + re.escape(lane) + r":\n(.*?)(?=^  [A-Za-z0-9_-]+:|\Z)", text, re.M | re.S)
    require(match is not None, "baseline lane missing")
    steps = []
    for block in re.split(r"(?=^      - )", match.group(1), flags=re.M)[1:]:
        name = re.match(r"      - name: (.+)\n", block)
        run = re.search(r"^        run: (.+)\n", block, re.M)
        if run is None:
            require(re.match(r"      - uses: ", block) is not None or "        uses: actions/cache/" in block,
                    "unsupported non-run CI step")
            continue
        require(name is not None, "unnamed CI run step")
        value = run.group(1)
        if value == "|":
            body = block[run.end():]
            lines = []
            for line in body.splitlines():
                if not line.startswith("          "):
                    break
                line = line[10:]
                if line and not line.startswith("#"):
                    lines.append(line)
            commands = lines
        else:
            commands = [value]
        require(bool(commands), "empty CI run body")
        timeout = re.search(r"^        timeout-minutes: ([0-9]+)$", block, re.M)
        steps.append({"name": name.group(1), "commands": commands,
                      "timeout_seconds": int(timeout.group(1)) * 60 if timeout else None})
    selected = [step for step in steps if step["name"] in LANES[lane]]
    require([step["name"] for step in selected] == LANES[lane], "selected CI step order/inventory drift")
    require(all(step["name"] in LANES[lane] or step["name"] in EXCLUSIONS for step in steps),
            "unmapped CI run step")
    return selected, [{"name": step["name"], "reason": EXCLUSIONS[step["name"]]}
                      for step in steps if step["name"] in EXCLUSIONS]


def category(command):
    if command.startswith("cargo fetch ") or command.startswith(("mkdir ", "python3 -B experiments/59-", "python3 -B experiments/57-", "python3 -B experiments/58-b1-desktop-web/prepare")):
        return "dependency_or_input_preparation"
    if command.startswith(("cargo check ", "cargo build ", "cargo fmt ")) or command.endswith("check.sh wasm"):
        return "compile_or_format"
    return "test_including_any_incremental_compile"


def make_plan(source, lane):
    ci = (source / ".github/workflows/ci.yml").read_text()
    require(sha((source / "experiments/27-ci-baseline/check.sh").read_bytes()) == DRIVER_SHA256,
            "baseline driver drift")
    selected, exclusions = extract_run_steps(ci, lane)
    stages = []
    for step in selected:
        env = {}
        if step["name"] == "Execute real B1 source and sampled pose regression":
            env = {"B1_CI_INPUTS": "$RUNNER_TEMP/nvwa-b1-seed", "CARGO_PROFILE_DEV_OPT_LEVEL": "1",
                   "CARGO_PROFILE_TEST_OPT_LEVEL": "1"}
        for command in step["commands"]:
            expanded = ["cargo test --workspace --locked", "cargo check --workspace --locked"] if command == NATIVE_DRIVER else [command]
            for actual in expanded:
                stages.append({"step": step["name"], "baseline_command": command, "command": actual,
                               "category": category(actual), "env": env,
                               "timeout_seconds": 3600, "step_timeout_seconds": step["timeout_seconds"]})
    # Mac Cargo's first native test fetches implicitly. Make that dependency time
    # visible separately, using the same locked manifests and both target graphs.
    manifests = ["Cargo.toml"]
    existing_fetches = []
    for stage in stages:
        tokens = shlex.split(stage["command"])
        if "--manifest-path" in tokens:
            manifest = tokens[tokens.index("--manifest-path") + 1]
            if manifest not in manifests:
                manifests.append(manifest)
            if tokens[:2] == ["cargo", "fetch"]:
                existing_fetches.append(manifest)
    prep = [{"step": "Explicit locked dependency preparation", "baseline_command": None,
             "command": "cargo fetch --locked --manifest-path " + manifest,
             "category": "dependency_or_input_preparation", "env": {}, "timeout_seconds": 900}
            for manifest in manifests if manifest not in existing_fetches]
    stages = prep + stages
    for number, stage in enumerate(stages, 1):
        stage["id"] = f"{number:02}"
    return {"schema_version": 1, "lane": lane, "arm": "strict", "source_head": BASE_SHA,
            "source_tree": BASE_TREE, "baseline_ci_sha256": CI_SHA256, "stages": stages,
            "excluded_run_steps": exclusions,
            "native_wrapper_mapping": {NATIVE_DRIVER: ["cargo test --workspace --locked", "cargo check --workspace --locked"]},
            "native_wrapper_exclusion": "Darwin/arm64 host guard only; tracked-byte and every tracked lock check retained by harness",
            "build_flag_changes": [],
            "dependency_manifests": manifests,
            "dependency_download_scope": "Locked Cargo registry dependencies for existing native and wasm graphs; Rust components are workflow provisioning",
            "feature_path": "nvwa-studio -> bevy_egui 0.42.0 -> bevy_winit 0.19.1 default -> x11 -> winit/x11 (offline cargo tree verified on Mac; Linux compile NOT-RUN)",
            "limits": ["CPU source tests and native/Wasm compilation only; graphics, browser, GPU and platform UX NOT-RUN",
                       "No skipped or substituted tests; command nonzero stops lane and keeps remaining stages NOT-RUN",
                       "Cargo test wall time includes its incremental compilation; no invented compile/test time split",
                       "Explicit cargo fetch can download locked registry packages; no asset or model download step",
                       "x11 feature arm not implemented; strict graph already includes bevy_winit default x11 via bevy_egui"]}


def validate_witnesses(out, lane):
    temp = out / "runtime"
    if lane == "native-and-wasm":
        mutations = json.loads((temp / "nvwa-b1-motion-mutations/summary.json").read_text())
        require(mutations.get("passed") is True and len(mutations.get("cases", [])) == 3, "three mutation witnesses missing")
        expected_logs = set()
        for case in mutations["cases"]:
            require(case.get("semantic_test_failure") is True and case.get("restored_green") is True,
                    "semantic red/restored green witness missing")
            require(case["before_sha256"] == case["restored_sha256"], "mutation source restoration mismatch")
            expected_logs.update((case["name"] + "-red.log", case["name"] + "-restored-green.log"))
        require(set(mutations.get("hashes", {})) == expected_logs and len(expected_logs) == 6,
                "six mutation red/green log hashes required")
        verify_file_hashes(temp / "nvwa-b1-motion-mutations", mutations["hashes"])
        matrix = json.loads((temp / "nvwa-b1-motion-matrix/summary.json").read_text())
        require(matrix.get("passed") is True and matrix.get("passing_records") == 594 and matrix.get("records") == 595,
                "actual 594-frame matrix missing/incomplete")
        require(matrix.get("probe_complete_marker") is True and matrix.get("coverage", {}).get("complete") is True,
                "matrix coverage/completion witness missing")
        frame = temp / "nvwa-b1-motion-matrix/keyframes/t+1__b1_arm_rehearsal_v1__k16.json.gz"
        require(frame.is_file() and frame.stat().st_size > 0, "real garment frame missing")
        matrix_root = temp / "nvwa-b1-motion-matrix"
        hashes = json.loads((matrix_root / "SHA256SUMS.json").read_text())
        verify_file_hashes(matrix_root, hashes)
        require(set(hashes) == set(file_hashes(matrix_root)) - {"SHA256SUMS.json"}, "matrix file inventory changed")
        require(sum(name.startswith("keyframes/") and name.endswith(".json.gz") for name in hashes) == 30,
                "30 retained deep matrix frames required")
    else:
        viewer = json.loads((temp / "nvwa-b1-viewer-runtime/native-runtime.json").read_text())
        require(viewer.get("native_actual_source_headless") is True and viewer.get("native_graphical_executed") is False,
                "actual headless viewer witness missing")


def file_hashes(root):
    require(root.is_dir() and not root.is_symlink(), "witness directory missing/unsafe")
    files = {}
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink(), "witness symlink rejected")
        if path.is_file():
            files[str(path.relative_to(root))] = sha(path.read_bytes())
    return files


def verify_file_hashes(root, hashes):
    require(bool(hashes), "empty witness file hashes")
    for name, digest in hashes.items():
        relative = Path(name)
        require(not relative.is_absolute() and ".." not in relative.parts, "unsafe witness file path")
        path = root / relative
        require(path.is_file() and not path.is_symlink(), "witness file missing/unsafe: " + name)
        require(sha(path.read_bytes()) == digest, "witness file hash mismatch: " + name)


def test_counts(log):
    counts = re.findall(r"test result: (?:ok|FAILED)\. (\d+) passed; (\d+) failed;", log)
    passed = sum(int(row[0]) for row in counts)
    failed = sum(int(row[1]) for row in counts)
    return {"passed": passed, "failed": failed, "executed": passed + failed}


def finalize(source, out, report):
    try:
        current = source_identity(source)
        require(current == report["initial_source_identity"], "initial/final tracked source bytes or locks differ")
        report["source_integrity"] = "VERIFIED"
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        report["source_integrity"] = "FAILED"
        report["integrity_error"] = str(error)
    report["stage_logs"] = "NOT-RUN"
    try:
        require(bool(report["results"]), "no executed stage logs")
        for result in report["results"]:
            verify_file_hashes(out, {result["log"]: result["log_sha256"]})
            if result["command"].startswith("cargo test "):
                counts = test_counts((out / result["log"]).read_text(errors="replace"))
                result["test_counts"] = counts
                require(counts["executed"] > 0, "Cargo test invocation executed zero tests: " + result["id"])
            if "witness_file_hashes" in result:
                viewer_root = out / "runtime/nvwa-b1-viewer-runtime"
                verify_file_hashes(viewer_root, result["witness_file_hashes"])
                require(file_hashes(viewer_root) == result["witness_file_hashes"], "viewer witness file inventory changed")
        report["stage_logs"] = "VERIFIED"
    except (ValueError, KeyError, OSError) as error:
        report["stage_logs"] = "FAILED"
        report["stage_log_error"] = str(error)
    complete = bool(report["plan"]["stages"]) and len(report["results"]) == len(report["plan"]["stages"]) and all(row.get("exit_code") == 0 for row in report["results"])
    report["witnesses"] = "NOT-RUN"
    if complete and report["source_integrity"] == "VERIFIED" and report["stage_logs"] == "VERIFIED":
        try:
            if report["plan"]["lane"] == "b1-source-regression":
                require(any(row.get("witness_file_hashes") for row in report["results"]), "viewer producer file hashes missing")
            validate_witnesses(out, report["plan"]["lane"])
            report["witnesses"] = "VERIFIED"
        except (ValueError, KeyError, OSError) as error:
            report["witnesses"] = "FAILED"
            report["witness_error"] = str(error)
    report["passed"] = complete and report["source_integrity"] == "VERIFIED" and report["stage_logs"] == "VERIFIED" and report["witnesses"] == "VERIFIED"
    report["status"] = "VERIFIED_CPU_AND_COMPILE_EQUIVALENCE" if report["passed"] else "NOT_EQUIVALENT_OR_INCOMPLETE"
    report["not_run_stage_ids"] = [stage["id"] for stage in report["plan"]["stages"] if stage["id"] not in {row["id"] for row in report["results"]}]
    report["elapsed_seconds_by_category"] = {kind: sum(row["elapsed_seconds"] for row in report["results"] if row["category"] == kind)
                                              for kind in {stage["category"] for stage in report["plan"]["stages"]}}
    write_json(out / "report.json", report)
    return 0 if report["passed"] else 1


def execute_stage(stage, source, out, env, remaining):
    command_env = dict(env)
    command_env.update({key: value.replace("$RUNNER_TEMP", env["RUNNER_TEMP"]) for key, value in stage["env"].items()})
    start = time.monotonic()
    log = out / (stage["id"] + ".log")
    process = None
    exit_code = None
    failure = None
    try:
        with log.open("xb") as stream:
            process = subprocess.Popen(["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", stage["command"]],
                                       cwd=source, env=command_env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            exit_code = process.wait(timeout=min(stage["timeout_seconds"], remaining))
    except (subprocess.TimeoutExpired, InterruptedError) as error:
        failure = type(error).__name__
    finally:
        if process is not None:
            # Also terminate any surviving grandchildren after a command exits.
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
    result = {"id": stage["id"], "command": stage["command"], "category": stage["category"],
            "env": stage["env"], "exit_code": exit_code, "failure": failure,
            "elapsed_seconds": time.monotonic() - start, "log": log.name,
            "log_sha256": sha(log.read_bytes())}
    if stage["command"].startswith("cargo test "):
        result["test_counts"] = test_counts(log.read_text(errors="replace"))
    if exit_code == 0 and stage["command"].startswith("python3 -B -O experiments/58-b1-desktop-web/verify_native.py "):
        result["witness_file_hashes"] = file_hashes(out / "runtime/nvwa-b1-viewer-runtime")
    return result


def execute_with_deadlines(stage, source, out, env, global_deadline, step_deadlines):
    """All commands from an original CI step consume its one shared deadline."""
    now = time.monotonic()
    remaining = global_deadline - now
    require(remaining > 0, "total run time budget exhausted")
    step_timeout = stage.get("step_timeout_seconds")
    if step_timeout is not None:
        deadline = step_deadlines.setdefault(stage["step"], now + step_timeout)
        step_remaining = deadline - now
        require(step_remaining > 0, "original CI step time budget exhausted: " + stage["step"])
        remaining = min(remaining, step_remaining)
    result = execute_stage(stage, source, out, env, remaining)
    result["effective_timeout_seconds"] = min(stage["timeout_seconds"], remaining)
    result["original_step_timeout_seconds"] = step_timeout
    return result


def run(source, out, plan, max_seconds):
    require(platform.system() == "Linux", "run requires actual Linux; use plan/tests on other hosts")
    require(sys.version_info >= (3, 12), "source controls require Python >= 3.12")
    require(source != HARN_ROOT, "source must be separate from harness checkout")
    require(not out.exists(), "output already exists; never overwrite evidence")
    require(not out.is_relative_to(source), "output must be outside frozen source checkout")
    identity = source_identity(source)
    out.mkdir(parents=True)
    (out / "runtime").mkdir()
    report = {"schema_version": 1, "plan": plan, "initial_source_identity": identity,
              "host": {"system": platform.system(), "machine": platform.machine(), "python": sys.version},
              "harness_identity": {"head": git(HARN_ROOT, "rev-parse", "HEAD"),
                                   "run_py_sha256": sha(Path(__file__).read_bytes())},
              "results": [], "passed": False, "source_integrity": "NOT-RUN"}
    write_json(out / "plan.json", plan)
    write_json(out / "report.json", report)
    env = os.environ.copy()
    env.update({"GITHUB_WORKSPACE": str(source), "RUNNER_TEMP": str(out / "runtime"),
                "CARGO_TARGET_DIR": str(out / "target"), "CARGO_BUILD_JOBS": "1", "CARGO_INCREMENTAL": "0",
                "CARGO_TERM_COLOR": "never", "CARGO_PROFILE_DEV_DEBUG": "0", "CARGO_PROFILE_TEST_DEBUG": "0"})
    # Fail closed on inherited build flags/features or alternate toolchains.
    for name in ("RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "RUSTC_WRAPPER", "RUSTC_WORKSPACE_WRAPPER", "RUSTUP_TOOLCHAIN", "CARGO_BUILD_TARGET"):
        require(not env.get(name), "unexpected inherited build override: " + name)
    report["execution_environment"] = {key: env[key] for key in env if key.startswith("CARGO_") or key in ("GITHUB_WORKSPACE", "RUNNER_TEMP")}
    start = time.monotonic()
    step_deadlines = {}
    try:
        for stage in plan["stages"]:
            print(stage["id"] + " " + stage["command"], flush=True)
            result = execute_with_deadlines(stage, source, out, env, start + max_seconds, step_deadlines)
            report["results"].append(result)
            write_json(out / "report.json", report)
            if result["exit_code"] != 0:
                break
    except (ValueError, OSError, InterruptedError) as error:
        report["runner_error"] = str(error)
    finally:
        report["total_elapsed_seconds"] = time.monotonic() - start
        status = finalize(source, out, report)
    return status


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "run", "finalize"))
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--lane", choices=tuple(LANES))
    parser.add_argument("--arm", choices=("strict",), default="strict")
    parser.add_argument("--max-seconds", type=int, default=3480)
    args = parser.parse_args(argv)
    source, out = args.source.resolve(), args.out.resolve()
    require(0 < args.max_seconds <= 3480, "run budget must be 1..3480 seconds, leaving workflow artifact time")
    if args.action == "finalize":
        return finalize(source, out, json.loads((out / "report.json").read_text()))
    require(args.lane is not None, "--lane required for plan/run")
    source_identity(source)
    plan = make_plan(source, args.lane)
    if args.action == "plan":
        print(json.dumps(plan, indent=2))
        return 0
    def interrupted(signum, frame):
        raise InterruptedError("interrupted by signal " + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    return run(source, out, plan, args.max_seconds)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print("LINUX_EQUIVALENCE_REJECTED: " + str(error), file=sys.stderr)
        raise SystemExit(2)
