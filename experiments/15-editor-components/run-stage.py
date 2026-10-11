#!/usr/bin/env python3
"""Run one leased check/build, clean up its processes, and preserve evidence/artifacts."""
import argparse
import hashlib
import json
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import time
import traceback

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
ROOT = REPO / ".work/m11-ui"


def primary_checkout():
    common = subprocess.check_output(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=REPO, text=True).strip()
    return pathlib.Path(common).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class StageInterrupted(Exception):
    def __init__(self, signum):
        self.signum = signum
        super().__init__(f"interrupted by signal {signum}")


def interrupt(signum, _frame):
    raise StageInterrupted(signum)


def group_exists(group):
    try:
        os.killpg(group, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # An EPERM probe does not prove absence; keep retrying within the bound.
        # Permission failure remains unknown/present; only ESRCH proves absence.
        return True


def cleanup_owned(process, grace=2.0, kill_wait=5.0):
    """Bounded cleanup of only this Popen's new group, including surviving children."""
    if group_exists(process.pid):
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
    deadline = time.monotonic() + grace
    while group_exists(process.pid) and time.monotonic() < deadline:
        process.poll()  # Reap the parent without an unbounded wait.
        time.sleep(0.02)
    if group_exists(process.pid):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
    deadline = time.monotonic() + kill_wait
    while group_exists(process.pid) and time.monotonic() < deadline:
        process.poll()
        time.sleep(0.02)
    process.poll()
    if process.poll() is None or group_exists(process.pid):
        raise RuntimeError(f"owned group cleanup unverified after bounded TERM/KILL: {process.pid}")


def run_owned(command, cwd, env, log, timeout=1800):
    process = subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        log.write(f"\nOwned process group {process.pid}: {command!r}\n")
        log.flush()
        return process.wait(timeout=timeout)
    finally:
        # Timeout, interruption, exception and success all reclaim this owned group.
        # Ignore further termination signals while finishing the bounded cleanup.
        previous = {sig: signal.signal(sig, signal.SIG_IGN) for sig in [signal.SIGINT, signal.SIGTERM, signal.SIGHUP]}
        try:
            cleanup_owned(process)
            log.write(f"Owned process group {process.pid}: absence verified after bounded cleanup\n")
            log.flush()
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)


def package_web(workspace, candidate, dest, tool, env, log):
    version = subprocess.check_output([str(tool), "--version"], text=True).strip()
    if version != "wasm-bindgen 0.2.129":
        raise RuntimeError(f"expected wasm-bindgen 0.2.129, got {version}")
    web = candidate / "web"
    code = run_owned([str(tool), "--target", "web", "--out-dir", str(web), str(dest)], workspace, env, log)
    if code:
        raise RuntimeError(f"wasm-bindgen failed: {code}")
    shutil.copy2(workspace / "web/index.html", web / "index.html")
    for rel in ["assets/character.profile.json", "assets/fixtures/nvwa-humanoid.glb", "assets/fixtures/LICENSE.txt", "assets/fixtures/provenance-manifest.json"]:
        target = web / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(workspace / rel, target)
    (web / "works").mkdir(exist_ok=True)
    shutil.copy2(workspace / "examples/m1-sequence.nvwa.json", web / "works/m1-sequence.nvwa.json")
    (web / "licenses/fonts").mkdir(parents=True, exist_ok=True)
    for rel in ["OFL.txt", "NOTICE.md", "PROVENANCE.json"]:
        shutil.copy2(workspace / "assets/fonts" / rel, web / "licenses/fonts" / rel)
    (web / "licenses/craft-ui").mkdir(parents=True, exist_ok=True)
    shutil.copy2(HERE / "licenses/craft-ui-MIT.txt", web / "licenses/craft-ui/LICENSE-MIT.txt")
    return {str(p.relative_to(web)): {"bytes": p.stat().st_size, "sha256": sha(p)} for p in sorted(web.rglob("*")) if p.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["tests", "native", "wasm"])
    parser.add_argument("--lease", required=True, help="Root-issued active build lease identifier")
    parser.add_argument("--name", help="Unique log suffix; existing logs are never overwritten")
    parser.add_argument("--target-dir", type=pathlib.Path, help="Shared target directory; default is the primary checkout target")
    parser.add_argument("--tool-path", type=pathlib.Path, help="Existing exact wasm-bindgen 0.2.129 executable; never installed here")
    parser.add_argument("--workspace", type=pathlib.Path, help="Prepared workspace under this experiment's .work/m11-ui; default generated")
    args = parser.parse_args()
    workspace = (args.workspace or ROOT / "generated").resolve()
    if not workspace.is_relative_to(ROOT.resolve()):
        parser.error(f"workspace must be under task-owned {ROOT}")
    logdir, candidate = ROOT / "logs", ROOT / "candidate"
    for directory in [logdir, candidate]:
        directory.mkdir(parents=True, exist_ok=True)
    name = args.name or args.stage
    logpath = logdir / (name + ".log")
    if logpath.exists():
        parser.error(f"refusing to overwrite log {logpath}")
    command = {"tests": ["cargo", "test", "--workspace", "--locked", "--offline"],
        "native": ["cargo", "build", "-p", "nvwa-studio", "--release", "--locked", "--offline"],
        "wasm": ["cargo", "build", "-p", "nvwa-studio", "--lib", "--release", "--target", "wasm32-unknown-unknown", "--locked", "--offline"]}[args.stage]
    known = ["crates/nvwa-studio/src/lib.rs", "crates/nvwa-studio/src/editor_layout.rs", "Cargo.lock", "crates/nvwa-studio/Cargo.toml"]
    started = time.monotonic()
    result = {"lease": args.lease, "stage": args.stage, "command": command, "exit_code": 1, "status": "started", "source_sha256": {},
        "workspace": str(workspace), "preparation_manifest": str(workspace.parent / (workspace.name + "-manifest.json"))}
    for sig in [signal.SIGTERM, signal.SIGHUP]:
        signal.signal(sig, interrupt)
    print(json.dumps({"stage": args.stage, "lease": args.lease, "command": command, "log": str(logpath)}), flush=True)
    with logpath.open("w") as log:
        try:
            primary = primary_checkout()
            target_dir = (args.target_dir or primary / "target").resolve()
            tool = (args.tool_path or primary / ".tools/wasm-bindgen/wasm-bindgen-0.2.129-aarch64-apple-darwin/wasm-bindgen").resolve()
            env = dict(os.environ, CARGO_TARGET_DIR=str(target_dir), CARGO_BUILD_JOBS="2")
            result["source_sha256"] = {rel: sha(workspace / rel) for rel in known}
            result["exit_code"] = run_owned(command, workspace, env, log)
            result["status"] = "passed" if result["exit_code"] == 0 else "failed"
            current = {rel: sha(workspace / rel) for rel in known}
            if current != result["source_sha256"]:
                result.update(exit_code=125, status="source_changed", final_source_sha256=current)
            if result["exit_code"] == 0 and args.stage != "tests":
                source = target_dir / ("release/nvwa-studio" if args.stage == "native" else "wasm32-unknown-unknown/release/nvwa_studio.wasm")
                dest = candidate / source.name
                shutil.copy2(source, dest)
                (candidate / "licenses/craft-ui").mkdir(parents=True, exist_ok=True)
                shutil.copy2(HERE / "licenses/craft-ui-MIT.txt", candidate / "licenses/craft-ui/LICENSE-MIT.txt")
                result["artifact"] = {"path": str(dest), "bytes": dest.stat().st_size, "sha256": sha(dest)}
                if args.stage == "wasm":
                    result["web_files"] = package_web(workspace, candidate, dest, tool, env, log)
        except subprocess.TimeoutExpired as error:
            result.update(exit_code=124, status="timeout", error=str(error))
        except KeyboardInterrupt:
            result.update(exit_code=130, status="interrupted", error="KeyboardInterrupt")
        except StageInterrupted as error:
            result.update(exit_code=128 + error.signum, status="interrupted", error=str(error))
        except Exception as error:
            result.update(exit_code=1, status="error", error=f"{type(error).__name__}: {error}")
            traceback.print_exc(file=log)
        finally:
            result["duration_seconds"] = time.monotonic() - started
            (logdir / (name + ".json")).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)
    print(logpath.read_text()[-7000:], flush=True)
    sys.exit(result["exit_code"])


if __name__ == "__main__":
    main()
