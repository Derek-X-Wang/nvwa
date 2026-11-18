#!/usr/bin/env python3
"""Render fixed-camera body-only evidence for the local hand-size candidate."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import subprocess
from pathlib import Path

VIEWS = {"front": 0.0, "quarter": 45.0, "side": 90.0}
CASES = {
    "v9-zero": ("new-character-arm-proportions", 0.0, 0.0),
    "v11-zero": ("new-character-hand-size", 0.0, 0.0),
    "left-minus": ("new-character-hand-size", -1.0, 0.0),
    "left-plus": ("new-character-hand-size", 1.0, 0.0),
    "right-minus": ("new-character-hand-size", 0.0, -1.0),
    "right-plus": ("new-character-hand-size", 0.0, 1.0),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str]) -> dict:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"exit {result.returncode}: {command}\n{result.stderr}")
    return json.loads(result.stdout)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size", type=int, default=1536)
    args = parser.parse_args()
    if not 512 <= args.size <= 2048:
        parser.error("--size must be 512..2048")
    cli = args.cli.resolve(strict=True)
    assets = args.assets.resolve(strict=True)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for case, (creator, left, right) in CASES.items():
        original = output / f"{case}-created.nvwa.json"
        run([str(cli), creator, str(assets), str(original)])
        source = json.loads(original.read_bytes())
        source["character"]["parameters"].update(
            {key: value for key, value in (("left_hand_size", left), ("right_hand_size", right))
             if key in source["character"]["parameters"]})
        for view, azimuth in VIEWS.items():
            work = json.loads(json.dumps(source))
            work["stage"]["camera"].update({"azimuth_degrees": azimuth,
                "elevation_degrees": 0.0, "distance": 3.8,
                "target_height": 0.95, "fov_degrees": 36.0})
            work_path = output / f"{case}-{view}.nvwa.json"
            work_path.write_text(json.dumps(work, indent=2) + "\n")
            folder = output / f"{case}-{view}"
            run([str(cli), "render", str(work_path), "--assets", str(assets),
                "--output", str(folder), "--width", str(args.size),
                "--height", str(args.size), "--mode", "body-reference"])
            receipt = json.loads((folder / "receipt.json").read_text())
            if (receipt["mode"] != "body_reference"
                    or len(receipt["parts"]) != 1
                    or receipt["parts"][0][0] != "body"
                    or receipt["work_sha256"] != digest(work_path)
                    or receipt["executable_sha256"] != digest(cli)
                    or receipt["png_sha256"] != digest(folder / "actual.png")):
                raise RuntimeError(f"invalid body-only receipt: {folder}")
            rows.append({"case": case, "view": view,
                         "work": work_path.name, "folder": folder.name,
                         "png_sha256": receipt["png_sha256"],
                         "geometry_sha256": receipt["geometry_sha256"]})
            print(case, view, receipt["png_sha256"][:12], flush=True)
    manifest = {"schema": 1, "status": "local_hand_size_candidate_not_artistic_acceptance",
                "cli_sha256": digest(cli), "asset_root": str(assets),
                "size": args.size, "camera": {"distance": 3.8,
                    "target_height": 0.95, "fov_degrees": 36.0, "elevation_degrees": 0.0},
                "rows": rows,
                "limits": ["static_body_only", "not_3d_export", "no_prop_grip_or_motion_acceptance"]}
    (output / "matrix.json").write_text(json.dumps(manifest, indent=2) + "\n")
    figures = []
    for row in rows:
        label = html.escape(f"{row['case']} / {row['view']}")
        folder = html.escape(row["folder"])
        figures.append(f'<figure><img src="{folder}/actual.png" alt="{label}">'
                       f'<figcaption>{label}</figcaption></figure>')
    (output / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>Hand size body review</title>'
        '<style>body{font:14px system-ui;background:#e8eaed;color:#20242a}'
        'main{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}'
        'figure{margin:0;background:#fff;padding:8px}img{width:100%}</style>'
        '<h1>Hand size body-only trial</h1><p>Fixed camera. Static, unapproved shape candidate.</p>'
        '<main>' + ''.join(figures) + '</main>')


if __name__ == "__main__":
    main()
