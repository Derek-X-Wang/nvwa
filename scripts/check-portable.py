#!/usr/bin/env python3
"""Run the shared hosted portable groups, from this script's checkout."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "scripts/portable-checks.json"
CI_DEFAULTS = {
    "CARGO_TERM_COLOR": "always",
    "CARGO_INCREMENTAL": "0",
    "CARGO_PROFILE_DEV_DEBUG": "0",
    "CARGO_PROFILE_TEST_DEBUG": "0",
    "CARGO_BUILD_JOBS": "2",
}


def identity(invocation_cwd):
    def git(*args):
        return subprocess.check_output(
            ["git", "--no-optional-locks", "-C", str(ROOT), *args], text=True
        ).strip()

    if Path(git("rev-parse", "--show-toplevel")).resolve() != ROOT:
        raise ValueError("runner must live at its Git checkout's scripts/check-portable.py")
    head = git("rev-parse", "HEAD")
    branch = git("branch", "--show-current") or "(detached)"
    dirty = bool(git("status", "--porcelain", "--untracked-files=normal"))
    print(f"Portable checks: checkout={ROOT}", flush=True)
    print(f"Invocation cwd: {invocation_cwd}", flush=True)
    print(f"HEAD: {head}; branch: {branch}; dirty: {'yes' if dirty else 'no'}", flush=True)
    print("Identity only: ignored caches and tool versions are not authenticated.", flush=True)


def run(groups, environment):
    for group in groups:
        print(f"\n[{group['name']}] {group['title']}", flush=True)
        # Keep each hosted step's shell body and failure boundary intact. Nothing
        # is evaluated in Python, so loops, quoting and interpreter failures keep
        # their original Bash behavior.
        result = subprocess.run(
            ["bash", "--noprofile", "--norc", "-e", "-c", group["run"]],
            cwd=ROOT, env=environment,
        )
        if result.returncode:
            return result.returncode if result.returncode > 0 else 128 - result.returncode
    return 0


def main():
    catalog = json.loads(CATALOG.read_text())
    if not isinstance(catalog, list) or not catalog:
        raise ValueError("invalid portable catalog: expected a nonempty list")
    seen = set()
    for group in catalog:
        if not isinstance(group, dict) or any(
            not isinstance(group.get(field), str) or not group[field].strip()
            for field in ["name", "title", "run"]
        ):
            raise ValueError("invalid portable catalog: each group needs name, title and run")
        name = group["name"]
        if name in seen or name == "all" or any(character.isspace() for character in name):
            raise ValueError(f"invalid portable catalog group name: {name!r}")
        seen.add(name)
    names = [group["name"] for group in catalog]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("groups", nargs="*", help="all, or named groups (catalog order)")
    parser.add_argument("--list", action="store_true", help="list groups without executing")
    args = parser.parse_args()
    if args.list:
        for group in catalog:
            print(f"{group['name']}: {group['title']}")
        return 0
    if not args.groups or any(name not in names + ["all"] for name in args.groups):
        parser.error("choose all or named groups; use --list to see the catalog")
    if "all" in args.groups and args.groups != ["all"]:
        parser.error("all must be used alone")
    selected = [group for group in catalog if "all" in args.groups or group["name"] in args.groups]
    identity(Path.cwd())
    environment = os.environ.copy()
    for name, value in CI_DEFAULTS.items():
        environment.setdefault(name, value)
    # CI supplies its existing runner temp. Local invocation gets one temporary
    # seed directory for the complete run, with the same path shared by all groups.
    if "RUNNER_TEMP" in environment:
        temporary = Path(environment["RUNNER_TEMP"])
        if not temporary.is_absolute() or not temporary.is_dir():
            raise ValueError("RUNNER_TEMP must name an existing absolute directory")
        return run(selected, environment)
    with tempfile.TemporaryDirectory(prefix="nvwa-portable-") as temporary:
        environment["RUNNER_TEMP"] = temporary
        return run(selected, environment)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        sys.exit(1)
