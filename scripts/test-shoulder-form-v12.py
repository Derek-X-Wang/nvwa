#!/usr/bin/env python3
"""Offline v12 provenance, bilateral composition and v11 byte-preservation check."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "assets/characters"
OLD = ROOT / "mpfb-b1-v11"
NEW = ROOT / "mpfb-b1-v12"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    old_manifest = json.loads((OLD / "manifest.json").read_text())
    new_manifest = json.loads((NEW / "manifest.json").read_text())
    assert new_manifest["asset_id"] == "mpfb-hm08-game-engine-female-sportsuit01-v12"
    assert len(old_manifest["files"]) == 59 and len(new_manifest["files"]) == 61
    new_files = {file["path"]: file for file in new_manifest["files"]}
    for file in old_manifest["files"]:
        assert new_files[file["path"]] == file
        assert (OLD / file["path"]).read_bytes() == (NEW / file["path"]).read_bytes()
    for file in new_manifest["files"]:
        data = (NEW / file["path"]).read_bytes()
        assert len(data) == file["bytes"] and digest(data) == file["sha256"]
    source = json.loads((NEW / "provenance/shoulder-form-target-source.json").read_text())
    assert source["source_commit"] == "d0a32e57a7f915cb2f2b95410e2117648c7bbb7e"
    assert len(source["files"]) == 4 and len(source["compositions"]) == 2
    source_rows = {}
    for file in source["files"]:
        name = file["name"]
        compressed = (NEW / "provenance/source/data/targets/arms" / f"{name}.target.gz").read_bytes()
        expanded = gzip.decompress(compressed)
        assert len(compressed) == file["source_bytes"] and digest(compressed) == file["source_sha256"]
        assert len(expanded) == file["expanded_bytes"] and digest(expanded) == file["expanded_sha256"]
        rows = [line for line in expanded.decode().splitlines() if line and not line.startswith("#")]
        assert len(rows) == file["rows"]
        source_rows[name] = rows
    for composition in source["compositions"]:
        name = composition["name"]
        rows = [line for stem in composition["sources"] for line in source_rows[stem]]
        indices = [int(line.split()[0]) for line in rows]
        assert len(indices) == len(set(indices))
        expected = ("\n".join(sorted(rows, key=lambda line: int(line.split()[0]))) + "\n").encode()
        actual = (NEW / "targets" / name).read_bytes()
        assert actual == expected and digest(actual) == composition["sha256"]
        assert len(rows) == composition["rows"] and len(actual) == composition["bytes"]
    print("v11 preserved; 61 v12 payloads and two exact bilateral shoulder targets verified")


if __name__ == "__main__":
    main()
