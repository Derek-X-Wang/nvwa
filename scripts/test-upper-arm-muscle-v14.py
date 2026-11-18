#!/usr/bin/env python3
"""Offline v14 source, composition, tamper and v13 preservation controls."""
from __future__ import annotations

import gzip
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "assets/characters"
OLD = ROOT / "mpfb-b1-v13"
NEW = ROOT / "mpfb-b1-v14"
MANIFEST_SHA256 = "bc842dd32317fdec1ba548c1acfe8bf2e66f465f4a20ebf36beceb2fdbf0b6d1"
SOURCE_SHA256 = {
    "l-upperarm-muscle-decr": "691dc28fce16e395a249fab3e04315ea6a1f3cdac896f92e49f06af7bcb41968",
    "l-upperarm-muscle-incr": "2b1ae2af00eabddadc298fd22b8af17966f13e65931636b36c2d77d2b9540dcd",
    "r-upperarm-muscle-decr": "e984b93fea1f7dd817e9b0c156e5d28c51cc473b5729f5b71caf33a5d8c8360b",
    "r-upperarm-muscle-incr": "24f3486b3fe48bb8127f48c2eae53e48930c32b7ae2a221ec2c9afafc60b453d",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def verify(old: Path, new: Path) -> None:
    old_manifest = json.loads((old / "manifest.json").read_text())
    new_manifest_bytes = (new / "manifest.json").read_bytes()
    require(digest(new_manifest_bytes) == MANIFEST_SHA256, "v14 manifest pin changed")
    new_manifest = json.loads(new_manifest_bytes)
    require(new_manifest["asset_id"] == "mpfb-hm08-game-engine-female-sportsuit01-v14", "v14 asset identity changed")
    require(len(old_manifest["files"]) == 63 and len(new_manifest["files"]) == 65, "runtime file count changed")
    new_files = {file["path"]: file for file in new_manifest["files"]}
    require(len(new_files) == 65, "duplicate runtime file path")
    for file in old_manifest["files"]:
        require(new_files.get(file["path"]) == file, f"v13 file descriptor changed: {file['path']}")
        require((old / file["path"]).read_bytes() == (new / file["path"]).read_bytes(),
                f"v13 file bytes changed: {file['path']}")
    for file in new_manifest["files"]:
        data = (new / file["path"]).read_bytes()
        require(len(data) == file["bytes"] and digest(data) == file["sha256"],
                f"runtime payload changed: {file['path']}")
    source = json.loads((new / "provenance/upper-arm-muscle-target-source.json").read_text())
    require(source["source_commit"] == "d0a32e57a7f915cb2f2b95410e2117648c7bbb7e",
            "upstream source commit changed")
    require(len(source["files"]) == 4 and len(source["compositions"]) == 2,
            "source inventory changed")
    source_rows = {}
    for file in source["files"]:
        name = file["name"]
        require(name in SOURCE_SHA256 and name not in source_rows, f"unknown or duplicate source: {name}")
        compressed = (new / "provenance/source/data/targets/arms" / f"{name}.target.gz").read_bytes()
        require(digest(compressed) == SOURCE_SHA256[name] == file["source_sha256"],
                f"upstream source hash changed: {name}")
        expanded = gzip.decompress(compressed)
        require(len(compressed) == file["source_bytes"] and len(expanded) == file["expanded_bytes"]
                and digest(expanded) == file["expanded_sha256"], f"source bytes changed: {name}")
        rows = [line for line in expanded.decode().splitlines() if line and not line.startswith("#")]
        require(len(rows) == file["rows"], f"source row count changed: {name}")
        source_rows[name] = rows
    require(set(source_rows) == set(SOURCE_SHA256), "source inventory omitted a pinned target")
    vertices = [tuple(map(float, line.split()[1:4]))
                for line in (new / "base.obj").read_text().splitlines() if line.startswith("v ")]
    require(len(vertices) == 19158, "base vertex count changed")
    require({part["name"] for part in source["compositions"]} == {
        "upperarm-muscle-decr.target", "upperarm-muscle-incr.target"},
        "bilateral target inventory changed")
    for composition in source["compositions"]:
        name = composition["name"]
        rows = [line for stem in composition["sources"] for line in source_rows[stem]]
        indices = [int(line.split()[0]) for line in rows]
        require(len(indices) == len(set(indices)), f"bilateral source IDs overlap: {name}")
        expected = ("\n".join(sorted(rows, key=lambda line: int(line.split()[0]))) + "\n").encode()
        actual = (new / "targets" / name).read_bytes()
        require(actual == expected and digest(actual) == composition["sha256"],
                f"bilateral composition changed: {name}")
        require(len(rows) == composition["rows"] and len(actual) == composition["bytes"],
                f"bilateral composition length changed: {name}")
        body_ids = [index for index in indices if index < 13380]
        require(len(body_ids) > 400, f"too few upper-arm body vertices: {name}")
        require(any(vertices[index][0] < -0.15 for index in body_ids)
                and any(vertices[index][0] > 0.15 for index in body_ids),
                f"bilateral upper arms missing: {name}")
        require(all(abs(vertices[index][0]) >= 0.13
                    and 0.34 <= vertices[index][1] <= 0.54 for index in body_ids),
                f"source rows leave upper-arm region: {name}")


def expect_rejection(old: Path, new: Path, label: str) -> None:
    try:
        verify(old, new)
    except (ValueError, OSError, EOFError, gzip.BadGzipFile):
        return
    raise ValueError(f"tampered {label} was accepted")


def main() -> None:
    verify(OLD, NEW)
    with tempfile.TemporaryDirectory(prefix="nvwa-v14-source-control-") as temporary:
        trial = Path(temporary) / "v14"
        shutil.copytree(NEW, trial)
        target = trial / "targets/upperarm-muscle-incr.target"
        original = target.read_bytes()
        target.write_bytes(original + b"# altered\n")
        expect_rejection(OLD, trial, "runtime target")
        target.write_bytes(original)
        source = trial / "provenance/source/data/targets/arms/l-upperarm-muscle-incr.target.gz"
        source.write_bytes(source.read_bytes() + b"altered")
        expect_rejection(OLD, trial, "compressed upstream source")
    print("v13 preserved; 65 v14 payloads, exact paired sources and both tamper controls verified")


if __name__ == "__main__":
    main()
