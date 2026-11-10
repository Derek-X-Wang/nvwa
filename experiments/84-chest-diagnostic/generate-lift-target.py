#!/usr/bin/env python3
"""Exploratory smooth adult torso morph corrections, not production assets.

The spatial envelope has mirror symmetry and fades to zero before the torso,
shoulder and back boundaries. It is an art-direction experiment only. Do not
ship it without actual skin/garment/pose and visual acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


def smooth(a: float, b: float, value: float) -> float:
    t = max(0.0, min(1.0, (value - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def load_vertices(path: Path):
    return [tuple(float(x) for x in line.split()[1:4])
            for line in path.open() if line.startswith("v ")]


def make_target(vertices, strength: float):
    rows = []
    max_delta = 0.0
    for index, (x, y, z) in enumerate(vertices[:13380]):
        ax = abs(x)
        envelope = (
            smooth(0.015, 0.055, ax)
            * (1.0 - smooth(0.13, 0.20, ax))
            * smooth(0.25, 0.33, y)
            * (1.0 - smooth(0.49, 0.57, y))
            * smooth(0.05, 0.12, z)
        )
        if envelope < 1e-5:
            continue
        # Metres in the checked-in OBJ. Nvwa scales .target displacements by 0.1.
        lift_y = strength * envelope * 0.011
        recontour_z = strength * envelope * (
            -0.010 + 0.030 * smooth(0.31, 0.45, y)
        )
        if not all(math.isfinite(v) for v in (lift_y, recontour_z)):
            raise ValueError("non-finite target")
        max_delta = max(max_delta, math.hypot(lift_y, recontour_z))
        rows.append(f"{index} 0 {lift_y * 10:.7f} {recontour_z * 10:.7f}\n")
    return "".join(rows), max_delta


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite: {args.output}")
    vertices = load_vertices(args.base)
    if len(vertices) != 19158:
        raise ValueError("unexpected B1 source topology")
    args.output.mkdir(parents=True)
    records = []
    for name, strength in (("custom-lift-soft", 1.0), ("custom-lift-strong", 1.5)):
        data, max_delta = make_target(vertices, strength)
        path = args.output / f"{name}.target"
        path.write_text(data)
        records.append({"name": name, "strength": strength, "rows": len(data.splitlines()),
                        "sha256": hashlib.sha256(data.encode()).hexdigest(),
                        "max_source_body_delta_m": max_delta})
    (args.output / "provenance.json").write_text(json.dumps({
        "base_obj_sha256": hashlib.sha256(args.base.read_bytes()).hexdigest(),
        "status": "exploratory_derived_morph_not_production",
        "design": "mirror-symmetric smooth front torso envelope; shift lower contour inward, upper contour forward, mild vertical lift",
        "records": records,
    }, indent=2) + "\n")
    print(json.dumps(records))


if __name__ == "__main__":
    main()
