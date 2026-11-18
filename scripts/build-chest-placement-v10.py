#!/usr/bin/env python3
"""Rebuild the bounded B1 v10 chest placement extension from pinned MPFB data."""
from __future__ import annotations

import gzip
import hashlib
import json
import shutil
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "assets/characters/mpfb-b1-v9"
NEW = ROOT / "assets/characters/mpfb-b1-v10"
COMMIT = "d0a32e57a7f915cb2f2b95410e2117648c7bbb7e"
SOURCE_BASE = f"https://raw.githubusercontent.com/makehumancommunity/mpfb2/{COMMIT}/src/mpfb/data/targets/breast"
ASSET_ID = "mpfb-hm08-game-engine-female-sportsuit01-v10"
TARGETS = {
    "breast_spacing": ("breast-dist-decr", "breast-dist-incr"),
    "breast_vertical_position": ("breast-trans-down", "breast-trans-up"),
}
EXPECTED_SHA256 = {
    "breast-dist-decr": "1a04a0bdcdb434f304bb831a92775e0abb3cf952b5bdb73a6ccc135cae1901cb",
    "breast-dist-incr": "c7fe9df66b8bd71a9ac323a553afaed9aeb224c11ffe1d0294376a57b9a90e36",
    "breast-trans-down": "456330713c14e1df41d9ac67b5c50e674b8fdcf8e07da6e770fcbeb1d88c4c4f",
    "breast-trans-up": "03e7e363f3bf6133ec5a9c97b0d9e661a5d9b043d9368558c1f804719f68446a",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def main() -> None:
    if NEW.exists():
        raise SystemExit(f"generated directory already exists: {NEW}")
    shutil.copytree(OLD, NEW)
    old_manifest = OLD / "manifest.json"
    old_payloads = OLD / "provenance/runtime-payloads.json"
    shutil.copyfile(old_manifest, NEW / "provenance/legacy-v9-manifest.json")
    shutil.copyfile(old_payloads, NEW / "provenance/legacy-v9-runtime-payloads.json")
    (NEW / "provenance/README.md").write_text(
        "# Static chest placement source extension (v10)\n\n"
        "Four CC0 MPFB 2.0.18 targets are fixed by compressed SHA256 in "
        "`scripts/build-chest-placement-v10.py`. `chest-placement-target-source.json` "
        "records the source URL and hashes. Each shipped target is the exact gzip "
        "expansion; the runtime scales MPFB coordinates by 0.1 once.\n\n"
        "The two signed controls are unitless authored target weights. For vertical "
        "position, negative selects `down` and positive selects `up`; no centimetre "
        "or physical measurement is implied. All 55 predecessor runtime payloads "
        "are byte-identical. Static rendering does not establish garment fit, "
        "full animation quality, or safety of extreme parameter combinations.\n"
    )
    records = []
    new_files = []
    for parameter, names in TARGETS.items():
        for name in names:
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
            raw = NEW / "provenance/source/data/targets/breast" / f"{name}.target.gz"
            raw.parent.mkdir(parents=True, exist_ok=True)
            raw.write_bytes(compressed)
            target = NEW / "targets" / f"{name}.target"
            target.write_bytes(expanded)
            new_files.append(target)
            records.append({
                "parameter": parameter, "name": name, "license": "CC0-1.0",
                "source_url": url, "source_bytes": len(compressed),
                "source_sha256": digest(compressed), "expanded_bytes": len(expanded),
                "expanded_sha256": digest(expanded), "rows": len(rows),
                "id_range": [min(indices), max(indices)],
            })
    dump(NEW / "provenance/chest-placement-target-source.json", {
        "source_commit": COMMIT, "license": "CC0-1.0", "files": records,
        "unit": "unmodified_MPFB_source_target_runtime_loader_scales_once_by_0.1",
    })
    old_files = [NEW / item["path"] for item in json.loads(old_manifest.read_text())["files"]]
    for path in (NEW / "manifest.json", NEW / "provenance/runtime-payloads.json"):
        value = json.loads(path.read_text())
        value["asset_id"] = ASSET_ID
        value["files"] = [
            {"bytes": file.stat().st_size, "license": "CC0-1.0",
             "path": str(file.relative_to(NEW)), "sha256": digest(file.read_bytes())}
            for file in sorted([*old_files, *new_files])
        ]
        dump(path, value)
    print(f"created {NEW} with {len(records)} fixed CC0 targets")
    print("manifest_sha256", digest((NEW / "manifest.json").read_bytes()))


if __name__ == "__main__":
    main()
