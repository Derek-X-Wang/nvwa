#!/usr/bin/env python3
"""Rebuild the bounded B1 v9 arm and wrist extension from pinned MPFB data."""
from __future__ import annotations

import gzip
import hashlib
import json
import shutil
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "assets/characters/mpfb-b1-v8"
NEW = ROOT / "assets/characters/mpfb-b1-v9"
COMMIT = "d0a32e57a7f915cb2f2b95410e2117648c7bbb7e"
SOURCE_BASE = f"https://raw.githubusercontent.com/makehumancommunity/mpfb2/{COMMIT}/src/mpfb/data/targets"
ASSET_ID = "mpfb-hm08-game-engine-female-sportsuit01-v9"
TARGETS = {
    "upper_arm_length": ("arms", "measure-upperarm-length"),
    "forearm_length": ("arms", "measure-lowerarm-length"),
    "wrist_circumference": ("hands", "measure-wrist-circ"),
}
EXPECTED_SHA256 = {
    "measure-upperarm-length-decr": "8f9b7a3494ce54b7560c10cf2ae5b350752a56c6918e28230b9035d43b139afc",
    "measure-upperarm-length-incr": "72890d3448778f6d25e3c9abd540582ad36598a832c28fd0b1e16073b1b3f962",
    "measure-lowerarm-length-decr": "c2ebdaf38b9fedc6db399039d95303adc6bc7614f007416f4ace0b573ecfd4c2",
    "measure-lowerarm-length-incr": "d725e5b7a35dad30a2a68fae52ea0efad72ed8ac77b186409a2cdc59d3e2368d",
    "measure-wrist-circ-decr": "3b6cbb6d8e4854c3d09fccc527174b02be1f32e8400cd7c7157361038d3cce21",
    "measure-wrist-circ-incr": "a765624157b4e061a62fc2e02b44b0021c38246fce5cb54bff4b3cfb2e67d42d",
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
    shutil.copyfile(old_manifest, NEW / "provenance/legacy-v8-manifest.json")
    shutil.copyfile(old_payloads, NEW / "provenance/legacy-v8-runtime-payloads.json")
    (NEW / "provenance/README.md").write_text(
        "# Static arm and wrist target source extension (v9)\n\n"
        "`arm-proportion-target-source.json` records six new targets from the pinned MPFB 2.0.18 source. The compressed CC0 source bytes are under `source/data/targets/{arms,hands}/`; each shipped `.target` is its exact gzip expansion. `scripts/build-arm-proportions-v9.py` verifies fixed compressed SHA256 values before expansion. No amplitudes, IDs, signs or zeros were edited. Only CC0 target data was imported, not addon program code. The existing runtime loader converts source coordinates by 0.1 once.\n\n"
        "The controls select increase/decrease endpoints with nonnegative magnitude. They are unitless relative weights, not centimetres or measured segment lengths. Fitted skeleton, sleeves, hands and elbow/wrist poses require actual runtime inspection.\n\n"
        "`legacy-v8-manifest.json` and `legacy-v8-runtime-payloads.json` preserve the immediate predecessor. All 49 v8 runtime payloads are byte-identical in v9. `runtime-payloads.json` and `../manifest.json` enumerate the current 55-file runtime set. Older provenance files remain historical evidence, not a description of the v9 set.\n\n"
        "Prior quality HOLDs remain. A static silhouette or asset check alone does not approve garment fit, hand prop interaction or animation.\n"
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
            rows = [line for line in expanded.decode("utf-8").splitlines()
                    if line and not line.startswith("#")]
            indices = [int(line.split()[0]) for line in rows]
            if not indices or min(indices) < 0 or max(indices) >= 19158:
                raise ValueError(f"unexpected target index range: {name}")
            raw_path = NEW / "provenance/source/data/targets" / folder / f"{name}.target.gz"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(compressed)
            target_path = NEW / "targets" / f"{name}.target"
            target_path.write_bytes(expanded)
            source_records.append({
                "parameter": parameter, "name": name, "license": "CC0-1.0",
                "source_url": url, "source_bytes": len(compressed),
                "source_sha256": digest(compressed), "expanded_bytes": len(expanded),
                "expanded_sha256": digest(expanded), "rows": len(rows),
                "id_range": [min(indices), max(indices)],
            })

    dump(NEW / "provenance/arm-proportion-target-source.json", {
        "source_commit": COMMIT, "license": "CC0-1.0", "files": source_records,
        "unit": "unmodified_MPFB_source_target_runtime_loader_scales_once_by_0.1",
    })
    original_manifest = json.loads(old_manifest.read_text())
    old_files = [NEW / item["path"] for item in original_manifest["files"]]
    new_files = [NEW / "targets" / f"{stem}-{direction}.target"
                 for _, stem in TARGETS.values() for direction in ("decr", "incr")]
    for path in (NEW / "manifest.json", NEW / "provenance/runtime-payloads.json"):
        document = json.loads(path.read_text())
        document["asset_id"] = ASSET_ID
        document["files"] = [
            {"bytes": len(file.read_bytes()), "license": "CC0-1.0",
             "path": str(file.relative_to(NEW)), "sha256": digest(file.read_bytes())}
            for file in sorted([*old_files, *new_files])
        ]
        dump(path, document)
    print(f"created {NEW} with {len(source_records)} verified target sources")
    print("manifest_sha256", digest((NEW / "manifest.json").read_bytes()))


if __name__ == "__main__":
    main()
