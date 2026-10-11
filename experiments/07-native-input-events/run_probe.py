#!/usr/bin/env python3
"""Link only this probe against an existing, coherent Cargo artifact set.

No Cargo build, network access, dependency modification or clipboard operation.
Requires the pinned dependencies to have already been built by the project.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import shlex
import subprocess
import sys

OWN = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("--target-dir", type=Path, default=OWN.parent.parent / "target")
args = parser.parse_args()
target = args.target_dir.resolve()
fingerprints = target / "debug" / ".fingerprint"
deps = target / "debug" / "deps"

def artifact(crate, fingerprint):
    matches = []
    for directory in fingerprints.glob(crate + "-*"):
        hash_file = directory / ("lib-" + crate)
        rlib = deps / ("lib" + crate + "-" + directory.name.split("-")[-1] + ".rlib")
        if hash_file.is_file() and rlib.is_file():
            if int.from_bytes(bytes.fromhex(hash_file.read_text()), "little") == fingerprint:
                matches.append(rlib)
    if len(matches) != 1:
        raise RuntimeError(f"Expected one coherent {crate} artifact; found {matches}")
    return matches[0]

candidates = []
for info in fingerprints.glob("bevy_egui-*/lib-bevy_egui.json"):
    rlib = deps / ("libbevy_egui-" + info.parent.name.split("-")[-1] + ".rlib")
    if rlib.is_file():
        candidates.append((rlib.stat().st_mtime, info, rlib))
if not candidates:
    sys.exit("NOT-RUN: no compiled bevy_egui rlib; dependency rebuild is outside this bounded probe")
_, info, egui_rlib = max(candidates)
data = json.loads(info.read_text())
libraries = {"bevy_egui": egui_rlib}
for crate in ("bevy_ecs", "bevy_input", "egui"):
    row = next(row for row in data["deps"] if row[1] == crate)
    libraries[crate] = artifact(crate, row[3])
command = ["rustc", "--edition=2024", "-C", "opt-level=0", "-C", "debuginfo=0", str(OWN / "probe.rs"), "-L", "dependency=" + str(deps), "-o", str(OWN / "probe")]
for crate, path in libraries.items():
    if crate == "egui":
        continue  # Record transitive library, accessed through bevy_egui's reexport.
    command += ["--extern", crate + "=" + str(path)]
versions = {}
for crate, path in libraries.items():
    dependency_file = deps / (path.name.removeprefix("lib").removesuffix(".rlib") + ".d")
    versions[crate] = sorted(set(re.findall("/" + crate + r"-([0-9]+\.[0-9]+\.[0-9]+)/", dependency_file.read_text())))
expected_versions = {"bevy_egui": ["0.42.0"], "bevy_ecs": ["0.19.1"], "bevy_input": ["0.19.1"], "egui": ["0.36.2"]}
if versions != expected_versions:
    sys.exit(f"NOT-RUN: cached artifact versions do not match pinned source: {versions}")
metadata = {
    "rustc": subprocess.check_output(["rustc", "--version"], text=True).strip(),
    "versions_verified_from_dep_info": versions,
    "fingerprint": str(info),
    "features": data["features"],
    "linked_rlibs": {crate: {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for crate, path in libraries.items()},
    "compile_command": shlex.join(command),
    "run_command": str(OWN / "probe"),
}
(OWN / "linked-artifacts.json").write_text(json.dumps(metadata, indent=2) + "\n")
print(metadata["compile_command"], flush=True)
compiled = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
log = compiled.stdout
print(log, end="", flush=True)
if compiled.returncode:
    (OWN / "run-output.txt").write_text(log + f"\nNOT-RUN: rustc exit={compiled.returncode}; no dependency rebuild attempted\n")
    sys.exit(compiled.returncode)
ran = subprocess.run([str(OWN / "probe")], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
log += ran.stdout
print(ran.stdout, end="")
(OWN / "run-output.txt").write_text(log + f"\nEXIT {ran.returncode}\n")
sys.exit(ran.returncode)
