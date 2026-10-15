#!/usr/bin/env python3
"""Integration-only offline controls. Never prepare/download/run a provider."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from mapping_comparison import compare_mapping
from owned_command import OwnedCommandError, run_owned

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EVIDENCE = ROOT / "docs/evidence/m2-authored-controls"
PRIVATE = ROOT / ".work/m2-model-free-ci"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen_inputs():
    for row in json.loads((EVIDENCE / "frozen-inputs.json").read_text())["files"]:
        path = ROOT / row["path"]
        if path.stat().st_size != row["bytes"] or digest(path) != row["sha256"]:
            raise RuntimeError(f"Frozen experiment changed: {row['path']}")


def boundary(binary, temporary):
    # Run the frozen executable tests with integration-owned output/cache paths.
    # Loading the module does not run its __main__ block or modify its source.
    spec = importlib.util.spec_from_file_location("frozen_boundary", HERE / "test_boundary.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.BINARY = Path(binary)
    module.PRIVATE = Path(temporary)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(module.Boundary)
    if suite.countTestCases() != 19:
        raise RuntimeError("Expected all 19 frozen CLI boundary tests")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


def main():
    if sys.flags.optimize:
        raise RuntimeError("Python assertions must be enabled for mapping controls")
    frozen_inputs()
    PRIVATE.mkdir(parents=True, exist_ok=True)
    session = Path(tempfile.mkdtemp(prefix="run-", dir=PRIVATE))
    target = PRIVATE / "target"
    env = dict(os.environ, CARGO_TARGET_DIR=str(target), CARGO_BUILD_JOBS="2",
               CARGO_NET_OFFLINE="true", CARGO_INCREMENTAL="0")
    env.pop("PYTHONOPTIMIZE", None)
    deadline = time.monotonic() + 300
    receipts = []

    def run(name, args, seconds):
        started = time.monotonic()
        try:
            receipt = run_owned(args, ROOT, env, session / (name + ".log"),
                                session / (name + ".command.json"),
                                max(0.01, min(seconds, deadline - started)))
        except OwnedCommandError as error:
            receipts.append(dict(error.receipt, name=name))
            (session / "commands.json").write_text(json.dumps(receipts, indent=2) + "\n")
            raise
        receipts.append(dict(receipt, name=name))
        (session / "commands.json").write_text(json.dumps(receipts, indent=2) + "\n")
        print((session / (name + ".log")).read_text(), end="", flush=True)

    try:
        run("build", ["cargo", "build", "--manifest-path", HERE / "Cargo.toml",
                      "--locked", "--offline", "--jobs", "2"], 180)
        run("boundary", [sys.executable, "-B", __file__, "--boundary",
                         target / "debug/nvwa-motion-import-experiment", session], 60)
        run("integration-controls", [sys.executable, "-B", HERE / "test_model_free.py"], 30)
        contract_dir = ROOT / ".work/m2-mapping-inputs"
        contract_dir.mkdir(parents=True, exist_ok=True)
        contract = contract_dir / "CONTRACT.md"
        if contract.exists():
            if contract.read_bytes() != (HERE / "CONTRACT.md").read_bytes():
                raise RuntimeError("Refusing to replace an existing different mapping contract")
        else:
            with contract.open("xb") as out:
                out.write((HERE / "CONTRACT.md").read_bytes())
        mapping = ROOT / "experiments/43-rig-mapping"
        output = session / "mapping"
        run("mapping", [sys.executable, "-B", mapping / "spike.py", "--out", output], 30)
        comparison = compare_mapping(output)
        (session / "mapping-comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")
        print(f"PASS: offline importer build, 19 CLI boundary tests, authored mapping/negative controls; {session}")
    finally:
        frozen_inputs()


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--boundary":
        sys.exit(boundary(sys.argv[2], sys.argv[3]))
    if len(sys.argv) != 1:
        raise SystemExit("Usage: python3 -B experiments/42-motion-import/check_model_free.py")
    main()
