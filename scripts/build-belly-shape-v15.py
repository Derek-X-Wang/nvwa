#!/usr/bin/env python3
"""Rebuild opt-in V15 from unchanged V10 and one pinned CC0 target."""
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys

SOURCE_COMMIT = "d0a32e57a7f915cb2f2b95410e2117648c7bbb7e"
SOURCE_PATH = "src/mpfb/data/targets/stomach/stomach-pregnant-incr.target.gz"
RAW_SHA = "52534e8d144d8bd492a471c78058f06428ab449569c578c6354580ee66d7a4d0"
TARGET_SHA = "67e282738b06bb01860c84b7dd1c823bce5e65f9053cc6db55f65f941360be7b"
PREDECESSOR_SHA = "d03bc6aac15f936bb8aad8c5e0133d13b259db17c224c8264c086861b2b1990a"
TARGET = "targets/stomach-pregnant-incr.target"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, value):
    path.write_bytes((json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def main():
    if len(sys.argv) not in (2, 3):
        raise SystemExit("Usage: build-belly-shape-v15.py SOURCE.target.gz [NEW-DIRECTORY]")
    assets = Path(__file__).resolve().parents[1] / "assets/characters"
    old = assets / "mpfb-b1-v10"
    new = Path(sys.argv[2]) if len(sys.argv) == 3 else assets / "mpfb-b1-v15"
    if new.exists():
        raise SystemExit(f"refusing to overwrite {new}")
    raw = Path(sys.argv[1]).read_bytes()
    if digest(raw) != RAW_SHA:
        raise SystemExit("unexpected compressed source digest")
    expanded = gzip.decompress(raw)
    if digest(expanded) != TARGET_SHA:
        raise SystemExit("unexpected expanded target digest")
    old_manifest = (old / "manifest.json").read_bytes()
    if digest(old_manifest) != PREDECESSOR_SHA:
        raise SystemExit("unexpected predecessor manifest digest")
    manifest = json.loads(old_manifest)
    for record in manifest["files"]:
        data = (old / record["path"]).read_bytes()
        if (len(data), digest(data)) != (record["bytes"], record["sha256"]):
            raise SystemExit(f"unexpected predecessor payload: {record['path']}")
    shutil.copytree(old, new)
    (new / TARGET).write_bytes(expanded)
    (new / "provenance/legacy-v10-manifest.json").write_bytes(old_manifest)
    shutil.copyfile(old / "provenance/runtime-payloads.json",
                    new / "provenance/legacy-v10-runtime-payloads.json")
    (new / "provenance/README.md").write_text(
        "# Experimental static belly shape (V15)\n\n"
        "Shipped V10 payloads are byte-identical. This adds only one unmodified "
        "CC0 MPFB gzip expansion. See belly-shape-target-source.json for source "
        "identity. The runtime loader scales MPFB deltas by 0.1 once. This is "
        "a unitless visual strength, not gestational or medical data.\n",
        encoding="utf-8",
    )
    source = new / "provenance/source/data/targets/stomach/stomach-pregnant-incr.target.gz"
    source.parent.mkdir(parents=True)
    source.write_bytes(raw)
    dump(new / "provenance/belly-shape-target-source.json", {
        "source_commit": SOURCE_COMMIT,
        "source_url": f"https://raw.githubusercontent.com/makehumancommunity/mpfb2/{SOURCE_COMMIT}/{SOURCE_PATH}",
        "source_sha256": RAW_SHA,
        "expanded_sha256": TARGET_SHA,
        "license": "CC0-1.0",
        "predecessor_manifest_sha256": PREDECESSOR_SHA,
        "parameter": "belly_shape_strength",
        "max_authored_target_weight": 0.25,
    })
    manifest["asset_id"] = "mpfb-hm08-game-engine-female-sportsuit01-v15"
    manifest["files"].append({"path": TARGET, "bytes": len(expanded), "sha256": TARGET_SHA, "license": "CC0-1.0"})
    manifest["files"].sort(key=lambda row: row["path"])
    dump(new / "manifest.json", manifest)
    inventory_path = new / "provenance/runtime-payloads.json"
    inventory = json.loads(inventory_path.read_bytes())
    inventory["asset_id"] = manifest["asset_id"]
    inventory["files"] = manifest["files"]
    dump(inventory_path, inventory)
    print(digest((new / "manifest.json").read_bytes()))


if __name__ == "__main__":
    main()
