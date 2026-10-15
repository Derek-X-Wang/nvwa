#!/usr/bin/env python3
"""Portable retained-evidence tamper controls; never runs the Rust binary."""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile


def main():
    source = pathlib.Path(__file__).resolve().parent
    repo = source.parent.parent
    with tempfile.TemporaryDirectory(prefix="nvwa-m12-audit-") as temp:
        copied_repo = pathlib.Path(temp)
        copied = copied_repo / "experiments/38-agent-cli"
        shutil.copytree(source, copied)
        manifest = json.loads((source / "accepted-run/source-manifest.json").read_text())
        for relative in manifest["sources"]:
            destination = copied_repo / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(repo / relative, destination)
        def check(expected_success):
            result = subprocess.run([sys.executable, "-B", str(copied / "verify.py")], capture_output=True)
            assert (result.returncode == 0) == expected_success, result.stderr.decode()
        check(True)
        mutations = [
            (copied_repo / "crates/nvwa-cli/src/main.rs", b"changed accepted source\n"),
            (copied / "accepted-run/receipts/04-stale-timeline/stderr.txt", b'{"code":"pretend_success"}\n'),
            (copied / "accepted-run/appearance.commands.json", b'{}\n'),
            (copied / "receipts/02-discover/stdout.txt", b'{}\n'),
            (copied / "accepted-run/agent-nine-second.nvwa.json", b'{}\n'),
        ]
        for path, altered in mutations:
            original = path.read_bytes()
            path.write_bytes(altered)
            check(False)
            path.write_bytes(original)
            check(True)
    print(json.dumps({"portable_baseline": "passed", "tamper_rejected_and_restored": len(mutations),
                      "scope": "source_receipts_commands_historical_snapshot_final_work", "binary_model_network": "not_used"}, indent=2))


if __name__ == "__main__":
    main()
