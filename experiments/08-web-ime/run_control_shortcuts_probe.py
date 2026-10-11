#!/usr/bin/env python3
"""Test exact production key transport against cached pinned egui; no Cargo build."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile

own = Path(__file__).resolve().parent
root = own.parent.parent
parser = argparse.ArgumentParser()
parser.add_argument("--stage", choices=("red", "green"), required=True)
parser.add_argument("--source", type=Path, default=root / "crates/nvwa-studio/src/web_input.rs")
args = parser.parse_args()
deps = root / "target/debug/deps"
fingerprints = root / "target/debug/.fingerprint"
production = args.source.resolve()
candidates = []
for info in fingerprints.glob("bevy_egui-*/lib-bevy_egui.json"):
    rlib = deps / ("libbevy_egui-" + info.parent.name.split("-")[-1] + ".rlib")
    if rlib.is_file():
        candidates.append((rlib.stat().st_mtime, info, rlib))
if not candidates:
    sys.exit("NOT-RUN: no cached bevy_egui rlib; this runner does not rebuild dependencies")
_, info, library = max(candidates)
data = json.loads(info.read_text())
egui_fingerprint = next(row[3] for row in data["deps"] if row[1] == "egui")
egui_candidates = []
for directory in fingerprints.glob("egui-*"):
    hash_file = directory / "lib-egui"
    rlib = deps / ("libegui-" + directory.name.split("-")[-1] + ".rlib")
    if hash_file.is_file() and rlib.is_file():
        if int.from_bytes(bytes.fromhex(hash_file.read_text()), "little") == egui_fingerprint:
            egui_candidates.append(rlib)
if len(egui_candidates) != 1:
    sys.exit(f"NOT-RUN: expected one coherent egui artifact, found {egui_candidates}")
libraries = {"bevy_egui": library, "egui": egui_candidates[0]}
versions = {}
for crate, path in libraries.items():
    dependency_file = deps / (path.name.removeprefix("lib").removesuffix(".rlib") + ".d")
    versions[crate] = sorted(set(re.findall("/" + crate + r"-([0-9]+\.[0-9]+\.[0-9]+)/", dependency_file.read_text())))
if versions != {"bevy_egui": ["0.42.0"], "egui": ["0.36.2"]}:
    sys.exit(f"NOT-RUN: cached artifact versions differ from pinned dependencies: {versions}")
source = production.read_text()
with tempfile.TemporaryDirectory(prefix="nvwa-control-shortcuts-") as temporary:
    temporary = Path(temporary)
    wrapper = temporary / "production.rs"
    wrapper.write_text("mod production {\n" + source + "\n}\n")
    binary = temporary / "control-shortcuts-tests"
    command = ["rustc", "--test", "--edition=2024", "-C", "debuginfo=0", str(wrapper),
               "-L", "dependency=" + str(deps), "--extern", "bevy_egui=" + str(library),
               "-o", str(binary)]
    run_command = [str(binary), "--nocapture"]
    metadata = {
        "stage": args.stage,
        "rustc": subprocess.check_output(["rustc", "--version"], text=True).strip(),
        "versions_verified_from_dep_info": versions,
        "fingerprint": str(info),
        "features": data["features"],
        "linked_rlibs": {crate: {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for crate, path in libraries.items()},
        "sources_sha256": {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in (production, Path(__file__).resolve())},
        "compile_command": shlex.join(command),
        "run_command": shlex.join(run_command),
        "temporary_directory_removed_on_exit": str(temporary),
    }
    (own / f"control-shortcuts-{args.stage}-artifacts.json").write_text(json.dumps(metadata, indent=2) + "\n")
    compiled = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log = "COMPILE " + shlex.join(command) + "\nRUN " + shlex.join(run_command) + "\n" + compiled.stdout
    status = compiled.returncode
    if status == 0:
        tested = subprocess.run(run_command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log += tested.stdout
        status = tested.returncode
    log += f"\nEXIT {status}\n"
    print(log, end="")
    (own / f"control-shortcuts-{args.stage}-output.txt").write_text(log)
sys.exit(status)
