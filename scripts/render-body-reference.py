#!/usr/bin/env python3
"""Render reproducible full-body views from a saved static B1 Work.

The normal nvwa-cli authenticates and fits the body for each saved view. This
script only makes bounded Work copies and an HTML contact sheet; it does not
implement a second renderer or edit the input Work.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import subprocess
from pathlib import Path


VIEWS = {"front": 0.0, "quarter": 45.0, "side": 90.0, "back": 180.0}
POSES = {"neutral", "shoulder", "elbow", "knee", "combined"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--poses", default="neutral")
    parser.add_argument("--width", type=int, default=768)
    parser.add_argument("--height", type=int, default=768)
    parser.add_argument("--distance", type=float, default=4.2)
    parser.add_argument("--target-height", type=float, default=0.95)
    parser.add_argument("--fov", type=float, default=36.0)
    args = parser.parse_args()

    poses = args.poses.split(",")
    if not poses or len(poses) != len(set(poses)) or not set(poses) <= POSES:
        parser.error("--poses must contain unique supported pose IDs")
    if not (64 <= args.width <= 2048 and 64 <= args.height <= 2048):
        parser.error("image dimensions must each be 64..=2048")
    cli = args.cli.resolve(strict=True)
    work_path = args.work.resolve(strict=True)
    assets = args.assets.resolve(strict=True)
    source_bytes = work_path.read_bytes()
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    source = json.loads(source_bytes)
    cli_sha256 = digest(cli)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    source_copy = output / "source-work.nvwa.json"
    source_copy.write_bytes(source_bytes)
    rows = []
    asset_sha256 = None
    for pose in poses:
        for view, azimuth in VIEWS.items():
            work = json.loads(json.dumps(source))
            work["character"]["diagnostic_pose"] = pose
            work["stage"]["camera"].update({
                "azimuth_degrees": azimuth,
                "elevation_degrees": 0.0,
                "distance": args.distance,
                "target_height": args.target_height,
                "fov_degrees": args.fov,
            })
            name = f"{pose}-{view}"
            saved_work = output / f"{name}.nvwa.json"
            saved_work.write_text(json.dumps(work, indent=2) + "\n")
            folder = output / name
            command = [str(cli), "render", str(saved_work), "--assets", str(assets),
                       "--output", str(folder), "--width", str(args.width),
                       "--height", str(args.height), "--mode", "body-reference"]
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                raise RuntimeError(f"{name}: nvwa-cli exited {result.returncode}: {result.stderr}")
            receipt = json.loads((folder / "receipt.json").read_text())
            if (receipt["mode"] != "body_reference"
                    or len(receipt["parts"]) != 1
                    or receipt["parts"][0][0] != "body"
                    or receipt["work_sha256"] != digest(saved_work)
                    or receipt["executable_sha256"] != cli_sha256
                    or receipt["png_sha256"] != digest(folder / "actual.png")):
                raise RuntimeError(f"{name}: incomplete or inconsistent body reference receipt")
            if asset_sha256 is None:
                asset_sha256 = receipt["asset_sha256"]
            elif receipt["asset_sha256"] != asset_sha256:
                raise RuntimeError(f"{name}: asset bytes changed between views")
            rows.append({"pose": pose, "view": view, "work": saved_work.name,
                         "folder": name, "png_sha256": receipt["png_sha256"],
                         "geometry_sha256": receipt["geometry_sha256"]})
            print(name, receipt["png_sha256"][:12], flush=True)

    manifest = {"schema_version": 1, "mode": "body_reference",
                "source_work": source_copy.name, "source_work_sha256": source_sha256,
                "cli_sha256": cli_sha256, "asset_root": str(assets),
                "asset_sha256": asset_sha256, "width": args.width, "height": args.height,
                "camera": {"distance": args.distance, "target_height": args.target_height,
                           "fov_degrees": args.fov, "elevation_degrees": 0.0},
                "rows": rows,
                "limits": ["static_poses_only", "png_not_3d_model", "no_pbr_or_artistic_acceptance"]}
    (output / "matrix.json").write_text(json.dumps(manifest, indent=2) + "\n")
    figures = []
    for row in rows:
        title = html.escape(f"{row['pose']} / {row['view']}")
        folder = html.escape(row["folder"])
        figures.append(f'<figure><img src="{folder}/actual.png" alt="{title}">'
                       f'<figcaption>{title} · <a href="{folder}/receipt.json">receipt</a>'
                       f' · <a href="{html.escape(row["work"])}">Work</a></figcaption></figure>')
    (output / "index.html").write_text(
        '<!doctype html><html><head><meta charset="utf-8"><title>Nvwa body reference</title>'
        '<style>body{font:14px system-ui;background:#e8eaed;color:#20242a}'
        'main{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}'
        'figure{margin:0;background:#fff;padding:8px}img{width:100%}figcaption{padding:6px}'
        '</style></head><body><h1>Nvwa full-body reference</h1>'
        '<p>Body only. Fixed neutral shading; no clothing, PBR, or continuous animation.</p>'
        '<main>' + "".join(figures) + '</main></body></html>')
    print("Review:", output / "index.html")


if __name__ == "__main__":
    main()
