#!/usr/bin/env python3
"""Expected-red exact frozen production-source replay, no Cargo dependency build."""
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys

own = Path(__file__).resolve().parent
root = own.parents[2]
prior = json.loads((own.parent / "linked-artifacts.json").read_text())
source = own / "web_input.rs"
assert hashlib.sha256(source.read_bytes()).hexdigest() == "4db492ca19e7755a8849a1dd8a8146351afa57d37d718a95ac22e3a2462b24b5"
(own / "generated.rs").write_text("mod production {\n" + source.read_text() + "\n" + (own / "selection-regressions.rs").read_text() + "\n}\n")
command = ["rustc", "--test", "--edition=2024", "-C", "debuginfo=0", str(own / "generated.rs"), "-L", "dependency=" + str(root / "target/debug/deps"), "--extern", "bevy_egui=" + prior["linked_rlibs"]["bevy_egui"]["path"], "-o", str(own / "probe")]
run = [str(own / "probe"), "--nocapture"]
record = {"rustc": subprocess.check_output(["rustc", "--version"], text=True).strip(), "versions_verified_from_dep_info": prior["versions_verified_from_dep_info"], "fingerprint": prior["fingerprint"], "features": prior["features"], "linked_rlibs": {name: {"path": item["path"], "sha256": hashlib.sha256(Path(item["path"]).read_bytes()).hexdigest()} for name, item in prior["linked_rlibs"].items()}, "sources_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in [source, own / "lib.rs", own / "selection-regressions.rs"]}, "compile_command": shlex.join(command), "run_command": shlex.join(run)}
(own / "linked-artifacts.json").write_text(json.dumps(record, indent=2) + "\n")
compiled = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
log = "COMPILE " + shlex.join(command) + "\nRUN " + shlex.join(run) + "\n" + compiled.stdout
status = compiled.returncode
if not status:
    tested = subprocess.run(run, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log += tested.stdout
    status = tested.returncode
log += f"\nEXIT {status}\n"
(own / "run-output.txt").write_text(log)
print(log, end="")
sys.exit(status)
