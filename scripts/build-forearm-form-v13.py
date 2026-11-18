#!/usr/bin/env python3
"""Rebuild the B1 v13 forearm-fat extension from pinned MPFB targets."""
from __future__ import annotations

import gzip
import hashlib
import json
import shutil
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "assets/characters/mpfb-b1-v12"
NEW = ROOT / "assets/characters/mpfb-b1-v13"
COMMIT = "d0a32e57a7f915cb2f2b95410e2117648c7bbb7e"
SOURCE_BASE = f"https://raw.githubusercontent.com/makehumancommunity/mpfb2/{COMMIT}/src/mpfb/data/targets/arms"
ASSET_ID = "mpfb-hm08-game-engine-female-sportsuit01-v13"
STEMS = ("l-lowerarm-fat", "r-lowerarm-fat")
EXPECTED_SHA256 = {
    "l-lowerarm-fat-decr": "276b3b03ac90cfa41e23335d50e29f0f64b267e9d596830f27b8fd3dc4f90e20",
    "l-lowerarm-fat-incr": "595bd2f8ef99dd63f1001788a53fd2d2c4c9de8c0065273fdce4d07f29826f7a",
    "r-lowerarm-fat-decr": "915aba8c9d0818a17183a0d61ed547f011d3173c8bd66b652ef19ffb017d0e75",
    "r-lowerarm-fat-incr": "a1d9c0d62c75c81e819534681b6f2dd8c94139c9e75e3d2e84bb0b46436bd6fc",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dump(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def main() -> None:
    if NEW.exists():
        raise SystemExit(f"generated directory already exists: {NEW}")
    shutil.copytree(OLD, NEW)
    old_manifest = OLD / "manifest.json"
    old_payloads = OLD / "provenance/runtime-payloads.json"
    shutil.copyfile(old_manifest, NEW / "provenance/legacy-v12-manifest.json")
    shutil.copyfile(old_payloads, NEW / "provenance/legacy-v12-runtime-payloads.json")
    (NEW / "provenance/README.md").write_text(
        "# Forearm-fat target extension (v13)\n\n"
        "This profile extends merged v12 and preserves all 61 earlier runtime payloads byte for byte. "
        "The separate v10 chest-placement experiment remains on visual hold and is not inherited.\n\n"
        "`forearm-form-target-source.json` pins four CC0 MPFB source targets at one commit. "
        "Each shipped bilateral target concatenates the left and right expanded source rows "
        "sorted by vertex ID; the two ID sets are disjoint and no displacement is edited. "
        "The runtime applies its usual single 0.1 displacement scale. The signed weight is relative, not a measurement "
        "of anatomical forearm circumference or muscle mass.\n\n"
        "Body-only static views and saved poses can check shape and continuity. Grip, clothing fit, "
        "continuous animation and artistic quality require separate acceptance.\n"
    )
    records = []
    expanded_by_direction = {"decr": [], "incr": []}
    for stem in STEMS:
        for direction in ("decr", "incr"):
            name = f"{stem}-{direction}"
            url = f"{SOURCE_BASE}/{name}.target.gz"
            compressed = urllib.request.urlopen(url, timeout=30).read()
            if digest(compressed) != EXPECTED_SHA256[name]:
                raise ValueError(f"pinned source hash mismatch: {name}")
            expanded = gzip.decompress(compressed)
            rows = [line for line in expanded.decode("utf-8").splitlines()
                    if line and not line.startswith("#")]
            indices = [int(line.split()[0]) for line in rows]
            if not indices or min(indices) < 0 or max(indices) >= 19158:
                raise ValueError(f"unexpected target index range: {name}")
            raw_path = NEW / "provenance/source/data/targets/arms" / f"{name}.target.gz"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(compressed)
            expanded_by_direction[direction].append(expanded)
            records.append({
                "parameter": "forearm_fullness", "name": name, "license": "CC0-1.0",
                "source_url": url, "source_bytes": len(compressed),
                "source_sha256": digest(compressed), "expanded_bytes": len(expanded),
                "expanded_sha256": digest(expanded), "rows": len(rows),
                "id_range": [min(indices), max(indices)],
            })
    compositions = []
    for direction, parts in expanded_by_direction.items():
        rows = [line for part in parts for line in part.decode("utf-8").splitlines()
                if line and not line.startswith("#")]
        indices = [int(line.split()[0]) for line in rows]
        if len(set(indices)) != len(indices):
            raise ValueError(f"left/right forearm target vertices overlap: {direction}")
        combined = ("\n".join(sorted(rows, key=lambda line: int(line.split()[0]))) + "\n").encode()
        target = NEW / "targets" / f"forearm-fat-{direction}.target"
        target.write_bytes(combined)
        compositions.append({"name": target.name, "bytes": len(combined),
                             "sha256": digest(combined), "rows": len(rows),
                             "sources": [f"{stem}-{direction}" for stem in STEMS]})
    dump(NEW / "provenance/forearm-form-target-source.json", {
        "source_commit": COMMIT, "license": "CC0-1.0", "files": records,
        "compositions": compositions,
        "unit": "source_rows_concatenated_runtime_loader_scales_once_by_0.1",
    })
    old_files = [NEW / item["path"] for item in json.loads(old_manifest.read_text())["files"]]
    new_files = [NEW / "targets" / f"forearm-fat-{direction}.target"
                 for direction in ("decr", "incr")]
    for path in (NEW / "manifest.json", NEW / "provenance/runtime-payloads.json"):
        document = json.loads(path.read_text())
        document["asset_id"] = ASSET_ID
        document["files"] = [
            {"bytes": len(data := file.read_bytes()), "license": "CC0-1.0",
             "path": str(file.relative_to(NEW)), "sha256": digest(data)}
            for file in sorted([*old_files, *new_files])
        ]
        dump(path, document)
    print(f"created {NEW} with {len(records)} pinned target sources")
    print("manifest_sha256", digest((NEW / "manifest.json").read_bytes()))


if __name__ == "__main__":
    main()
