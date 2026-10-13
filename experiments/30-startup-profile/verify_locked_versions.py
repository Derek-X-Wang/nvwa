#!/usr/bin/env python3
"""Reject dependency/version/checksum drift from the unchanged root Cargo.lock."""
import argparse
import json
from pathlib import Path
import tomllib


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root-lock", type=Path, required=True)
    parser.add_argument("--experiment-lock", type=Path, required=True)
    args = parser.parse_args()
    root = tomllib.loads(args.root_lock.read_text())["package"]
    candidate = tomllib.loads(args.experiment_lock.read_text())["package"]
    known = {(row["name"], row["version"], row.get("source")): row for row in root}
    differences = []
    checked = 0
    for row in candidate:
        if row["name"] in ("nvwa-startup-profile-experiment", "nvwa-ui-pixels-experiment"):
            continue
        key = (row["name"], row["version"], row.get("source"))
        previous = known.get(key)
        if previous is None or previous.get("checksum") != row.get("checksum"):
            differences.append({"name": row["name"], "version": row["version"], "source": row.get("source"),
                "reason": "package absent from root or checksum changed"})
        else:
            checked += 1
    passed = bool(checked) and not differences
    print(json.dumps({"pass": passed, "exact_package_identities_checked": checked,
        "differences": differences, "features": "NOT-VERIFIED by lockfile; retain actual Cargo resolved graph separately"}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
