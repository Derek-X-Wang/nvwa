#!/usr/bin/env python3
"""Offline provenance and predecessor-byte check for the local hand candidate."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "assets/characters"
OLD = ROOT / "mpfb-b1-v9"
NEW = ROOT / "mpfb-b1-v11"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    old_manifest = json.loads((OLD / "manifest.json").read_text())
    new_manifest = json.loads((NEW / "manifest.json").read_text())
    assert new_manifest["asset_id"] == "mpfb-hm08-game-engine-female-sportsuit01-v11"
    assert len(old_manifest["files"]) == 55 and len(new_manifest["files"]) == 59
    new_files = {file["path"]: file for file in new_manifest["files"]}
    for file in old_manifest["files"]:
        assert new_files[file["path"]] == file
        assert (OLD / file["path"]).read_bytes() == (NEW / file["path"]).read_bytes()
    for file in new_manifest["files"]:
        data = (NEW / file["path"]).read_bytes()
        assert len(data) == file["bytes"] and digest(data) == file["sha256"]
    source = json.loads((NEW / "provenance/hand-size-target-source.json").read_text())
    assert len(source["files"]) == 4
    indices = {}
    for file in source["files"]:
        name = file["name"]
        compressed = (NEW / "provenance/source/data/targets/hands" / f"{name}.target.gz").read_bytes()
        target = (NEW / "targets" / f"{name}.target").read_bytes()
        assert digest(compressed) == file["source_sha256"]
        assert gzip.decompress(compressed) == target
        assert digest(target) == file["expanded_sha256"]
        indices[name] = {int(line.split()[0]) for line in target.decode().splitlines()
                         if line and not line.startswith("#")}
    for sign in ("decr", "incr"):
        assert not indices[f"l-hand-scale-{sign}"] & indices[f"r-hand-scale-{sign}"]
    print("v9 preserved; 59 v11 payloads and four disjoint pinned hand targets verified")


if __name__ == "__main__":
    main()
