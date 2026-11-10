#!/usr/bin/env python3
"""Rebuild the bounded B1 v8 hip and buttocks extension from pinned MPFB data."""
from __future__ import annotations

import gzip
import hashlib
import json
import shutil
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "assets/characters/mpfb-b1-v7"
NEW = ROOT / "assets/characters/mpfb-b1-v8"
COMMIT = "d0a32e57a7f915cb2f2b95410e2117648c7bbb7e"
SOURCE_BASE = f"https://raw.githubusercontent.com/makehumancommunity/mpfb2/{COMMIT}/src/mpfb/data/targets"
ASSET_ID = "mpfb-hm08-game-engine-female-sportsuit01-v8"
TARGETS = {
    "hip_depth": ("hip", "hip-scale-depth"),
    "buttocks_volume": ("buttocks", "buttocks-volume"),
}
EXPECTED_SHA256 = {
    "hip-scale-depth-decr": "20bb79ee3c2dbbba40448219cf1b4627825c9f67e662021e1e78abecdf4948d3",
    "hip-scale-depth-incr": "6d655dc583249178a53f729254b704fab4f3a83f4b5a666a7c49d5f7904148dd",
    "buttocks-volume-decr": "e7752ede368fb2b16c2a61fb1a2c57d70493e8cd5689574e3dc2dc22bd74ca1f",
    "buttocks-volume-incr": "44d10afed96b0c29df25d7abe8c2e2f9eb50ad6c1906e2de7ab91612b39177e9",
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
    shutil.copyfile(old_manifest, NEW / "provenance/legacy-v7-manifest.json")
    shutil.copyfile(old_payloads, NEW / "provenance/legacy-v7-runtime-payloads.json")
    (NEW / "provenance/README.md").write_text(
        "# Static hip and buttocks target source extension (v8)\n\n"
        "`hip-contour-target-source.json` records four new targets from the pinned MPFB 2.0.18 source. The compressed CC0 source bytes are under `source/data/targets/{hip,buttocks}/`; each shipped `.target` is its exact gzip expansion. `scripts/build-hip-contour-v8.py` verifies fixed compressed SHA256 values before expansion. No amplitudes, IDs, signs or zeros were edited. Only CC0 target data was imported, not addon program code. The existing runtime loader converts source coordinates by 0.1 once.\n\n"
        "The two new controls select the original increase or decrease endpoint with a nonnegative magnitude. These are unitless, relative shape weights, not centimetres, measured anatomical dimensions or equal perceptual steps. Fitted skeleton, clothing and leg/hip poses need actual runtime examination.\n\n"
        "`legacy-v7-manifest.json` and `legacy-v7-runtime-payloads.json` preserve the immediate predecessor. All 45 v7 runtime payloads are byte-identical in v8. `runtime-payloads.json` and `../manifest.json` enumerate the current 49-file runtime set. The older provenance files remain historical evidence for prior extensions; their counts and hashes do not describe the v8 set.\n\n"
        "All prior quality HOLDs remain. A static silhouette or successful asset check alone does not approve garment quality, animation or character art.\n"
    )

    source_records = []
    for parameter, (folder, stem) in TARGETS.items():
        for direction in ("decr", "incr"):
            name = f"{stem}-{direction}"
            url = f"{SOURCE_BASE}/{folder}/{name}.target.gz"
            compressed = urllib.request.urlopen(url, timeout=30).read()
            if digest(compressed) != EXPECTED_SHA256[name]:
                raise ValueError(f"pinned source hash mismatch: {name}")
            expanded = gzip.decompress(compressed)
            text = expanded.decode("utf-8")
            rows = [line for line in text.splitlines() if line and not line.startswith("#")]
            indices = [int(line.split()[0]) for line in rows]
            if not indices or min(indices) < 0 or max(indices) >= 19158:
                raise ValueError(f"unexpected target index range: {name}")
            raw_path = NEW / "provenance/source/data/targets" / folder / f"{name}.target.gz"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(compressed)
            target_path = NEW / "targets" / f"{name}.target"
            target_path.write_bytes(expanded)
            source_records.append({
                "parameter": parameter,
                "name": name,
                "license": "CC0-1.0",
                "source_url": url,
                "source_bytes": len(compressed),
                "source_sha256": digest(compressed),
                "expanded_bytes": len(expanded),
                "expanded_sha256": digest(expanded),
                "rows": len(rows),
                "id_range": [min(indices), max(indices)],
            })

    dump(NEW / "provenance/hip-contour-target-source.json", {
        "source_commit": COMMIT,
        "license": "CC0-1.0",
        "files": source_records,
        "unit": "unmodified_MPFB_source_target_runtime_loader_scales_once_by_0.1",
    })
    original_manifest = json.loads(old_manifest.read_text())
    for path in (NEW / "manifest.json", NEW / "provenance/runtime-payloads.json"):
        document = json.loads(path.read_text())
        document["asset_id"] = ASSET_ID
        document["files"] = [
            {
                "bytes": len(file.read_bytes()),
                "license": "CC0-1.0",
                "path": str(file.relative_to(NEW)),
                "sha256": digest(file.read_bytes()),
            }
            for file in sorted([*map(lambda entry: NEW / entry["path"], original_manifest["files"]),
                                *(NEW / "targets" / f"{folder[1]}-{direction}.target"
                                  for folder in TARGETS.values() for direction in ("decr", "incr"))])
        ]
        dump(path, document)
    print(f"created {NEW} with {len(source_records)} verified target sources")
    print("manifest_sha256", digest((NEW / "manifest.json").read_bytes()))


if __name__ == "__main__":
    main()
