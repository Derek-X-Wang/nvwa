#!/usr/bin/env python3
"""Run core/CLI checks sequentially without replacing retained experiment logs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
SOURCES = [
    "crates/nvwa-core/src/lib.rs",
    "crates/nvwa-core/src/bounded_history_tests.rs",
    "crates/nvwa-core/src/asset.rs",
    "crates/nvwa-core/tests/transactions.rs",
    "crates/nvwa-core/Cargo.toml",
    "Cargo.toml",
    "Cargo.lock",
    "examples/default.nvwa.json",
    "crates/nvwa-cli/src/main.rs",
    "crates/nvwa-cli/tests/offline.rs",
    "crates/nvwa-cli/Cargo.toml",
    "docs/adr/0005-portable-document-and-commands.md",
    "crates/nvwa-cli/src/lib.rs",
    "crates/nvwa-cli/tests/sequence.rs",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--target-dir", type=Path)
    args = parser.parse_args()
    output = args.output_dir or Path(tempfile.mkdtemp(prefix="nvwa-history-evidence-"))
    output.mkdir(parents=True, exist_ok=True)
    target = args.target_dir or Path(tempfile.mkdtemp(prefix="nvwa-history-target-"))
    env = {**os.environ, "CARGO_BUILD_JOBS": "2", "CARGO_TARGET_DIR": str(target.resolve())}
    checks = [
        ("tests", ["cargo", "test", "-p", "nvwa-core", "-p", "nvwa-cli", "--locked", "--", "--nocapture"]),
        ("capability-probe", [sys.executable, str(ROOT / "experiments/10-bounded-history/capability_probe.py"), str(target / "debug" / ("nvwa-cli.exe" if os.name == "nt" else "nvwa-cli"))]),
        ("clippy", ["cargo", "clippy", "-p", "nvwa-core", "-p", "nvwa-cli", "--all-targets", "--locked", "--", "-D", "warnings"]),
        ("fmt", ["rustfmt", "--edition", "2024", "--check", *SOURCES[:2], "crates/nvwa-cli/src/main.rs"]),
    ]
    evidence = {
        "source_sha256": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in SOURCES},
        "rustc": subprocess.check_output(["rustc", "--version"], text=True).strip(),
        "cargo": subprocess.check_output(["cargo", "--version"], text=True).strip(),
        "target_dir": str(target.resolve()),
        "checks": [],
    }
    for name, command in checks:
        log = output / f"{name}-output.txt"
        if log.exists():
            raise SystemExit(f"Refusing to overwrite retained evidence: {log}")
        start = time.monotonic()
        with log.open("w") as stream:
            result = subprocess.run(command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT)
        evidence["checks"].append({"command": command, "exit": result.returncode, "seconds": round(time.monotonic() - start, 3), "log": str(log.resolve())})
        print(f"{name}: exit={result.returncode}; log={log.resolve()}", flush=True)
        if result.returncode != 0:
            break
    (output / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"Evidence: {output.resolve()}; cleanup owner must remove target: {target.resolve()}")
    return max(check["exit"] != 0 for check in evidence["checks"])


if __name__ == "__main__":
    raise SystemExit(main())
