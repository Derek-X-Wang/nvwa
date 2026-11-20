#!/usr/bin/env python3
"""Verify the two-file V15 vendor successor through the unchanged B1 gate."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
LEGACY = "scripts/verify-b1-inputs.py"
TEST = "scripts/test-b1-inputs.py"
ASSETS = "assets/characters/mpfb-b1-v1"
SCOPES = ("vendor/humentity", "vendor/bevy_obj", "vendor/wobj", "crates/nvwa-b1-adapter")
SINGLES = (LEGACY, TEST, "scripts/b1-source-inventory.json", "scripts/b1-motion-source-inventory.json")
EXPECTED = {
    "morphs.rs": [(23803, "1bf279cd0cbaddef818c20816e2260ed622a7429f8d072193af9dc10e979c356"),
                  (26720, "88446723b47c136a7d0bab3c56582e2cd1f8af1e8844ed0c87939eb349f5fafa")],
    "template.rs": [(10294, "4afbff7d3c09a57bf466be98189f280b2b1b918db56707e7071ebb5837b6331c"),
                    (10308, "2e8fb8878845706fa0979152b9fcb2c0bbc502468eacc1053c2d97abbffab639")],
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def regular(path):
    require(not any(p.is_symlink() for p in (path, *path.parents)) and path.is_file(),
            f"Not a regular successor input: {path}")
    return path.read_bytes()


def copy_verified_directory(source, dest):
    require(not any(p.is_symlink() for p in (source, *source.parents)) and source.is_dir(),
            f"Not a regular successor directory: {source}")
    for parent, children, files in os.walk(source, followlinks=False):
        for name in children:
            require(not (Path(parent) / name).is_symlink(), f"Symlink directory: {parent}/{name}")
        for name in files:
            mode = (Path(parent) / name).lstat().st_mode
            require(stat.S_ISREG(mode), f"Nonregular successor file: {parent}/{name}")
    shutil.copytree(source, dest)


def verify(root, replay, package=None, historical_test=False):
    # Authenticate original executable verification source before evaluating it.
    import hashlib
    sha = lambda data: hashlib.sha256(data).hexdigest()
    require(sha(regular(root / LEGACY)) == "2b490f17d4c07b8743cd5930e263fb7aaf336902302b9c4b761f19a197a03932",
            "Historical verifier bytes changed")
    require(sha(regular(root / TEST)) == "ab9e66b0873bf2d5481c6e7a8079474514cca6fac160d8316fba68c68152de9b",
            "Historical mutation tests changed")
    spec = importlib.util.spec_from_file_location("nvwa_b1_unchanged", root / LEGACY)
    legacy = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(legacy)
    for relative in SCOPES:
        copy_verified_directory(root / relative, replay / relative)
    for relative in SINGLES:
        dest = replay / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(regular(root / relative))
    for name, (before, after) in EXPECTED.items():
        file = replay / "vendor/humentity/src" / name
        data = regular(file)
        require((len(data), sha(data)) == after and (file.stat().st_mode & 0o111) == 0,
                f"V15 ordered source changed: {name}")
        data = regular(root / "scripts/b1-inputs-pre-v15" / name)
        require((len(data), sha(data)) == before, f"Archived predecessor changed: {name}")
        file.write_bytes(data)

    # Exactly two source snapshots are projected back; the unchanged strict
    # verification still sees live bytes of every other source and control.
    count = legacy.verify_source(replay)
    total = legacy.verify_assets(root / ASSETS)
    if package is not None:
        legacy.verify_assets(package.absolute())
    if historical_test:
        copy_verified_directory(root / ASSETS, replay / ASSETS)
        flags = ["-O"] if sys.flags.optimize else []
        subprocess.run([sys.executable, "-B", *flags, str(replay / TEST)], cwd=replay, check=True)
    return {"source_context": "B1-v15-opt-in-target-order-v1", "source_files": count,
            "raw_files": 13, "raw_bytes": total, "packaged_inputs_checked": package is not None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", type=Path, help="Verify actual packaged B1 V1 inputs too")
    parser.add_argument("--historical-test", action="store_true", help="Replay original mutation suite")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="nvwa-b1-v15-") as tmp:
        result = verify(ROOT, Path(tmp).resolve(), args.asset_root, args.historical_test)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
