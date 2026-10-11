#!/usr/bin/env python3
"""Exercise the real stage helper with owned Python descendants; never run Cargo/GPU."""
import contextlib
import importlib.util
import io
import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import time
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("run_stage", HERE / "run-stage.py")
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


def fixture(mode, folder):
    folder = pathlib.Path(folder)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    if mode == "descendant":
        (folder / "child-ready").write_text(str(os.getpid()))
        while True:
            time.sleep(1)
    child = subprocess.Popen([sys.executable, str(pathlib.Path(__file__).resolve()), "fixture", "descendant", str(folder)])
    deadline = time.monotonic() + 3
    while not (folder / "child-ready").exists():
        if time.monotonic() >= deadline:
            raise RuntimeError("descendant did not start")
        time.sleep(0.01)
    (folder / "owned-pids.json").write_text(json.dumps({"parent": os.getpid(), "child": child.pid, "group": os.getpgrp()}))
    if mode == "failure":
        sys.exit(7)  # Leave a real TERM-ignoring child for the helper to reclaim.
    while True:
        time.sleep(1)


def wrapper(mode, folder):
    stage.ROOT = pathlib.Path(folder)
    real_popen, real_run = subprocess.Popen, stage.run_owned
    def replace_only_cargo(command, *args, **kwargs):
        # Substitute the build command, not its wait, group, signal or cleanup behavior.
        if command[0] == "cargo":
            command = [sys.executable, str(pathlib.Path(__file__).resolve()), "fixture", mode, str(stage.ROOT)]
        return real_popen(command, *args, **kwargs)
    def elapsed_timeout(*args, **kwargs):
        if mode == "timeout":
            kwargs["timeout"] = 0.25
        return real_run(*args, **kwargs)
    with mock.patch.object(stage.subprocess, "Popen", replace_only_cargo), mock.patch.object(stage, "run_owned", elapsed_timeout), mock.patch.object(sys, "argv", ["run-stage.py", "tests", "--lease", "STUB"]):
        stage.main()


def prepare_stub(folder):
    workspace = folder / "generated"
    workspace.mkdir(parents=True)
    for relative in ["crates/nvwa-studio/src/lib.rs", "crates/nvwa-studio/src/editor_layout.rs", "Cargo.lock", "crates/nvwa-studio/Cargo.toml"]:
        path = workspace / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("known source\n")


def checks():
    results = {}
    with contextlib.nullcontext(tempfile.mkdtemp(prefix="stage-descendant-check-", dir=stage.ROOT)) as directory:
        root = pathlib.Path(directory)
        for mode, send, expected in [("timeout", None, 124), ("term", signal.SIGTERM, 143),
            ("int", signal.SIGINT, 130), ("failure", None, 7)]:
            folder = root / mode
            prepare_stub(folder)
            started = time.monotonic()
            process = subprocess.Popen([sys.executable, str(pathlib.Path(__file__).resolve()), "wrapper", mode, str(folder)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
            owned = None
            try:
                deadline = time.monotonic() + 5
                while not (folder / "owned-pids.json").exists():
                    if process.poll() is not None or time.monotonic() > deadline:
                        raise AssertionError("live descendant fixture did not start")
                    time.sleep(0.01)
                owned = json.loads((folder / "owned-pids.json").read_text())
                if send is not None:
                    os.kill(process.pid, send)  # Deliver a real signal while helper waits.
                stdout, stderr = process.communicate(timeout=12)
                elapsed = time.monotonic() - started
                result = json.loads((folder / "logs/tests.json").read_text())
                assert process.returncode == expected, (mode, stdout, stderr)
                assert result["exit_code"] == expected and len(result["source_sha256"]) == 4
                assert elapsed < 10.0
                assert not stage.group_exists(owned["group"]), owned
                assert "absence verified after bounded cleanup" in (folder / "logs/tests.log").read_text()
                results[mode] = {"status": result["status"], "exit_code": expected, "elapsed_seconds": elapsed,
                    "real_term_ignoring_descendant": True, "group_absence_verified": True}
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=3)
                if owned and stage.group_exists(owned["group"]):
                    os.killpg(owned["group"], signal.SIGKILL)
        # Ordinary exception after Popen also reaches the same production cleanup.
        owned = []
        real_popen = subprocess.Popen
        def capture(*args, **kwargs):
            process = real_popen(*args, **kwargs)
            owned.append(process)
            return process
        class FailingLog:
            def fileno(self):
                return sink.fileno()
            def write(self, _text):
                raise RuntimeError("owned log exception")
            def flush(self):
                pass
        with (root / "exception.log").open("w") as sink, mock.patch.object(stage.subprocess, "Popen", capture):
            try:
                stage.run_owned([sys.executable, "-c", "import time;time.sleep(60)"], root, dict(os.environ), FailingLog())
            except RuntimeError as error:
                assert str(error) == "owned log exception"
            else:
                raise AssertionError("expected real post-Popen logging exception")
        assert owned[0].poll() is not None and not stage.group_exists(owned[0].pid)
        results["ordinary_exception"] = {"group_absence_verified": True}
        # Source-change gate uses actual main and hashes, with no build invocation.
        folder = root / "source-change"
        prepare_stub(folder)
        old_root = stage.ROOT
        stage.ROOT = folder
        def change_source(*args):
            (folder / "generated/Cargo.lock").write_text("changed source\n")
            return 0
        try:
            with mock.patch.object(sys, "argv", ["run-stage.py", "tests", "--lease", "STUB"]), mock.patch.object(stage, "run_owned", side_effect=change_source), contextlib.redirect_stdout(io.StringIO()):
                try:
                    stage.main()
                except SystemExit as exit:
                    assert exit.code == 125
            result = json.loads((folder / "logs/tests.json").read_text())
            assert result["status"] == "source_changed" and "artifact" not in result
            results["source_changed"] = "fails before artifact preservation"
        finally:
            stage.ROOT = old_root
    (stage.ROOT / "logs/helper-checks.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "fixture":
        fixture(sys.argv[2], sys.argv[3])
    elif len(sys.argv) > 1 and sys.argv[1] == "wrapper":
        wrapper(sys.argv[2], sys.argv[3])
    else:
        checks()
