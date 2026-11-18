#!/usr/bin/env python3
"""Rebuild the B1 v14 upper-arm muscle extension from pinned MPFB targets."""
from __future__ import annotations

import gzip
import hashlib
import json
import shutil
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "assets/characters/mpfb-b1-v13"
NEW = ROOT / "assets/characters/mpfb-b1-v14"
COMMIT = "d0a32e57a7f915cb2f2b95410e2117648c7bbb7e"
SOURCE_BASE = f"https://raw.githubusercontent.com/makehumancommunity/mpfb2/{COMMIT}/src/mpfb/data/targets/arms"
ASSET_ID = "mpfb-hm08-game-engine-female-sportsuit01-v14"
STEMS = ("l-upperarm-muscle", "r-upperarm-muscle")
EXPECTED_SHA256 = {
    "l-upperarm-muscle-decr": "691dc28fce16e395a249fab3e04315ea6a1f3cdac896f92e49f06af7bcb41968",
    "l-upperarm-muscle-incr": "2b1ae2af00eabddadc298fd22b8af17966f13e65931636b36c2d77d2b9540dcd",
    "r-upperarm-muscle-decr": "e984b93fea1f7dd817e9b0c156e5d28c51cc473b5729f5b71caf33a5d8c8360b",
    "r-upperarm-muscle-incr": "24f3486b3fe48bb8127f48c2eae53e48930c32b7ae2a221ec2c9afafc60b453d",
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
    shutil.copyfile(old_manifest, NEW / "provenance/legacy-v13-manifest.json")
    shutil.copyfile(old_payloads, NEW / "provenance/legacy-v13-runtime-payloads.json")
    (NEW / "provenance/README.md").write_text(
        "# Upper-arm muscle target extension (v14)\n\n"
        "This profile extends merged v13 and preserves all 63 earlier runtime payloads byte for byte. "
        "The separate v10 chest-placement experiment remains on visual hold and is not inherited.\n\n"
        "`upper-arm-muscle-target-source.json` pins four CC0 MPFB source targets at one commit. "
        "Each shipped bilateral target concatenates the left and right expanded source rows "
        "sorted by vertex ID; the two ID sets are disjoint and no displacement is edited. "
        "The runtime applies its usual single 0.1 displacement scale. The signed weight is relative, not a measurement "
        "of anatomical upper-arm girth or measured muscle mass.\n\n"
        "Body-only static views and saved poses can check shape and continuity. Elbow transition, clothing fit, "
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
                "parameter": "upper_arm_muscle_fullness", "name": name, "license": "CC0-1.0",
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
            raise ValueError(f"left/right upper-arm target vertices overlap: {direction}")
        combined = ("\n".join(sorted(rows, key=lambda line: int(line.split()[0]))) + "\n").encode()
        target = NEW / "targets" / f"upperarm-muscle-{direction}.target"
        target.write_bytes(combined)
        compositions.append({"name": target.name, "bytes": len(combined),
                             "sha256": digest(combined), "rows": len(rows),
                             "sources": [f"{stem}-{direction}" for stem in STEMS]})
    dump(NEW / "provenance/upper-arm-muscle-target-source.json", {
        "source_commit": COMMIT, "license": "CC0-1.0", "files": records,
        "compositions": compositions,
        "unit": "source_rows_concatenated_runtime_loader_scales_once_by_0.1",
    })
    old_files = [NEW / item["path"] for item in json.loads(old_manifest.read_text())["files"]]
    new_files = [NEW / "targets" / f"upperarm-muscle-{direction}.target"
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
