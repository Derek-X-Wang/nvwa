#!/usr/bin/env python3
"""Rebuild the bounded B1 v11 per-hand size extension from pinned MPFB data."""
from __future__ import annotations

import gzip
import hashlib
import json
import shutil
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "assets/characters/mpfb-b1-v9"
NEW = ROOT / "assets/characters/mpfb-b1-v11"
COMMIT = "d0a32e57a7f915cb2f2b95410e2117648c7bbb7e"
SOURCE_BASE = f"https://raw.githubusercontent.com/makehumancommunity/mpfb2/{COMMIT}/src/mpfb/data/targets/hands"
ASSET_ID = "mpfb-hm08-game-engine-female-sportsuit01-v11"
TARGETS = {
    "left_hand_size": "l-hand-scale",
    "right_hand_size": "r-hand-scale",
}
EXPECTED_SHA256 = {
    "l-hand-scale-decr": "731f85efa15d887902d5cc65528a41439370f87f5d78cf4a454344dab5c1beaf",
    "l-hand-scale-incr": "6b274978f762b5ed3ae9101615194c139e260b506f0ca24c47c1a6589b7715f5",
    "r-hand-scale-decr": "8a0a3e246efb9e3640fabd02c75085e3bc2bf57d20b736e0a98819302a72c83c",
    "r-hand-scale-incr": "33d4f09b9c7cf1559503dde7b4e40f882a2bb81ec9bc71324c9edbe3655cda34",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dump(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def main() -> None:
    if NEW.exists():
        raise SystemExit(f"remove existing generated directory first: {NEW}")
    shutil.copytree(OLD, NEW)
    old_manifest = OLD / "manifest.json"
    old_payloads = OLD / "provenance/runtime-payloads.json"
    shutil.copyfile(old_manifest, NEW / "provenance/legacy-v9-manifest.json")
    shutil.copyfile(old_payloads, NEW / "provenance/legacy-v9-runtime-payloads.json")
    (NEW / "provenance/README.md").write_text(
        "# Per-hand size target source extension (v11)\n\n"
        "The v11 identity and backend schema 13 avoid the separate, unmerged v10 chest-placement experiment. This hand profile derives from v9 and does not imply chest-placement inheritance.\n\n"
        "`hand-size-target-source.json` pins four CC0 MPFB source target files at the fixed commit. "
        "Each shipped target is the byte-exact gzip expansion of its included source. "
        "`scripts/build-hand-size-v11.py` authenticates compressed SHA256 before expansion. "
        "No target amplitudes or vertex IDs are edited; the existing runtime loader scales source coordinates by 0.1 once.\n\n"
        "Left and right controls are independent signed relative weights, not centimetres or a measured hand circumference. "
        "The preceding v9 manifest and payload list are preserved. All prior runtime payloads remain byte-identical. "
        "Hand shape, prop grip, sleeve fit, and continuous motion require separate visual acceptance.\n"
    )
    records = []
    for parameter, stem in TARGETS.items():
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
            raw_path = NEW / "provenance/source/data/targets/hands" / f"{name}.target.gz"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(compressed)
            (NEW / "targets" / f"{name}.target").write_bytes(expanded)
            records.append({
                "parameter": parameter, "name": name, "license": "CC0-1.0",
                "source_url": url, "source_bytes": len(compressed),
                "source_sha256": digest(compressed), "expanded_bytes": len(expanded),
                "expanded_sha256": digest(expanded), "rows": len(rows),
                "id_range": [min(indices), max(indices)],
            })
    dump(NEW / "provenance/hand-size-target-source.json", {
        "source_commit": COMMIT, "license": "CC0-1.0", "files": records,
        "unit": "unmodified_MPFB_source_target_runtime_loader_scales_once_by_0.1",
    })
    old_files = [NEW / item["path"] for item in json.loads(old_manifest.read_text())["files"]]
    new_files = [NEW / "targets" / f"{stem}-{direction}.target"
                 for stem in TARGETS.values() for direction in ("decr", "incr")]
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
