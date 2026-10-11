#!/usr/bin/env python3
"""Compile a tiny native test crate using exact production reducer and real cached egui."""
import hashlib
import json
import shlex
from pathlib import Path
import subprocess
import sys

own = Path(__file__).resolve().parent
root = own.parent.parent
metadata = json.loads((own / "linked-artifacts.json").read_text())
source = (root / "crates/nvwa-studio/src/web_input.rs").read_text()
source = "mod production {\n" + source + "\n" + (own / "rework-regressions.rs").read_text() + "\n}\n"
(own / "rework-source.rs").write_text(source)
library = metadata["linked_rlibs"]["bevy_egui"]["path"]
command = ["rustc", "--test", "--edition=2024", "-C", "debuginfo=0", str(own / "rework-source.rs"),
           "-L", "dependency=" + str(root / "target/debug/deps"), "--extern", "bevy_egui=" + library,
           "-o", str(own / "rework-tests")]
run_command = [str(own / "rework-tests"), "--nocapture"]
record = {
    "rustc": subprocess.check_output(["rustc", "--version"], text=True).strip(),
    "versions_verified_from_dep_info": metadata["versions_verified_from_dep_info"],
    "fingerprint": metadata["fingerprint"],
    "features": metadata["features"],
    "linked_rlibs": {name: {"path": item["path"], "sha256": hashlib.sha256(Path(item["path"]).read_bytes()).hexdigest()} for name, item in metadata["linked_rlibs"].items()},
    "sources_sha256": {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in [root / "crates/nvwa-studio/src/web_input.rs", root / "crates/nvwa-studio/src/lib.rs", own / "rework-regressions.rs"]},
    "compile_command": shlex.join(command),
    "run_command": shlex.join(run_command),
}
(own / "rework-linked-artifacts.json").write_text(json.dumps(record, indent=2) + "\n")
print("COMMAND", shlex.join(command), flush=True)
compiled = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
log = compiled.stdout
if compiled.returncode == 0:
    tested = subprocess.run(run_command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log += tested.stdout
    status = tested.returncode
else:
    status = compiled.returncode
print(log, end="")
(own / "rework-output.txt").write_text("COMPILE " + shlex.join(command) + "\nRUN " + shlex.join(run_command) + "\n" + log + f"\nEXIT {status}\n")
sys.exit(status)
