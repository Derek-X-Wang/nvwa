"""Real libproc boundary controls. Does not launch Nvwa or touch GPU."""
import json
import os
from pathlib import Path
import subprocess
import sys

binary = Path(sys.argv[1]).resolve()
def query(*args):
    return subprocess.run([str(binary), *map(str, args)], capture_output=True, text=True, timeout=2)
before_run = query(os.getpid())
assert before_run.returncode == 0, before_run.stderr
before = json.loads(before_run.stdout)
identity = [before["pid"], before["birth_sec"], before["birth_usec"]]
checked = query(*identity)
assert checked.returncode == 0 and json.loads(checked.stdout)["expected_birth_checked"]
wrong = query(identity[0], identity[1] + 1, identity[2])
assert wrong.returncode == 4 and not wrong.stdout and "expected-birth-mismatch" in wrong.stderr
invalid = query(1)
assert invalid.returncode == 2 and not invalid.stdout
allocation = bytearray(32 * 1024 * 1024)
for offset in range(0, len(allocation), 4096):
    allocation[offset] = 123
after_run = query(*identity)
assert after_run.returncode == 0, after_run.stderr
after = json.loads(after_run.stdout)
assert after["sample_begin_ns"] <= after["sample_end_ns"]
assert after["rss_bytes"] - before["rss_bytes"] > 24 * 1024 * 1024, (before, after)
assert after["physical_footprint_bytes"] - before["physical_footprint_bytes"] > 24 * 1024 * 1024, (before, after)
assert after["kernel_lifetime_max_physical_footprint_bytes"] >= after["physical_footprint_bytes"]
print(json.dumps({"status": "VERIFIED", "controls": ["real-self-PID-birth", "expected-birth-mismatch-refuses-output", "pid1-rejected", "32MiB-real-page-touch-increases-RSS-and-footprint", "raw-monotonic-bracket", "kernel-reported-lifetime-max"], "before": before, "after": after}, indent=2))
