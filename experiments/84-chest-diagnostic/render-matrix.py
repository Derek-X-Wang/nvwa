#!/usr/bin/env python3
"""Produce a bounded production-fit chest candidate matrix from one exact CLI.

Every render goes through Nvwa's normal B1 source authentication, Humentity
morph, body/sportsuit fitting, diagnostic pose and published CPU frame. The
candidate overlay and part/shading choices are *diagnostic*, not game sliders.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import subprocess


def call(*args: str) -> dict:
    result = subprocess.run(args, text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(f"{args[1]} failed: {result.stderr}")
    return json.loads(result.stdout)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidates", default="neutral,point-100,point-upper-100,cup-35,cup-55,cup-firm-55")
    parser.add_argument("--poses", default="neutral,shoulder")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    cli = str(args.cli.resolve(strict=True))
    assets = str(args.assets.resolve(strict=True))
    candidates = args.candidates.split(",")
    poses = args.poses.split(",")
    if not candidates or not set(candidates) <= {"neutral", "point-100", "point-upper-100", "cup-35", "cup-55", "cup-firm-55", "firm-lift-soft", "firm-lift-strong", "cup35-lift-soft"}:
        raise ValueError("unknown candidate")
    if not poses or not set(poses) <= {"neutral", "shoulder"}:
        raise ValueError("unsupported pose")
    work_path = output / "base-v10.nvwa.json"
    call(cli, "new-character-chest-placement", assets, str(work_path))
    baseline = json.loads(work_path.read_text())
    assert all(value == 0 for value in baseline["character"]["parameters"].values())
    identity = {"cli_sha256": hashlib.sha256(Path(cli).read_bytes()).hexdigest(), "work_profile": baseline["profile"]}
    (output / "run-identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    default_receipt = call(
        cli, "render", str(work_path), "--assets", assets,
        "--output", str(output / "parity-default"), "--width", "512", "--height", "512",
    )["receipt"]
    diagnostic_receipt = call(
        cli, "render", str(work_path), "--assets", assets,
        "--output", str(output / "parity-diagnostic-neutral"), "--width", "512", "--height", "512",
        "--diagnostic-candidate", "neutral", "--diagnostic-part", "combined",
        "--diagnostic-style", "silhouette",
    )["receipt"]
    for key in ("geometry_sha256", "png_sha256", "pixels_sha256"):
        if default_receipt[key] != diagnostic_receipt[key]:
            raise AssertionError(f"neutral diagnostic changes published default {key}")
    rows = []
    for pose in poses:
        for candidate in candidates:
            for view, angle in (("front", 0), ("three-quarter", 45), ("side", 90)):
                work = json.loads(json.dumps(baseline))
                work["stage"]["camera"].update({"azimuth_degrees": angle, "elevation_degrees": 0,
                                                 "distance": 1.65, "target_height": 1.35, "fov_degrees": 36})
                work["character"]["diagnostic_pose"] = pose
                name = f"{pose}-{candidate}-{view}"
                scene = output / f"{name}.nvwa.json"
                scene.write_text(json.dumps(work, indent=2) + "\n")
                call(cli, "validate", str(scene), assets)
                for part in ("body", "garment", "combined"):
                    folder = output / f"{name}-{part}"
                    response = call(cli, "render", str(scene), "--assets", assets,
                                    "--output", str(folder), "--width", "768", "--height", "768",
                                    "--diagnostic-candidate", candidate,
                                    "--diagnostic-part", part, "--diagnostic-style", "shaded")
                    receipt = response["receipt"]
                    assert receipt["diagnostic"]["candidate"] == candidate
                    assert receipt["diagnostic"]["part"] == part
                    assert receipt["executable_sha256"] == identity["cli_sha256"]
                    rows.append((pose, candidate, view, part, folder.name,
                                 receipt["geometry_sha256"], receipt["png_sha256"]))
                    print(folder.name, receipt["png_sha256"][:12], flush=True)
    cards = []
    for pose, candidate, view, part, folder, _, _ in rows:
        title = f"{pose} / {candidate} / {view} / {part}"
        cards.append(f'<figure><img src="{html.escape(folder)}/actual.png" alt="{html.escape(title)}"><figcaption>{html.escape(title)} · <a href="{html.escape(folder)}/receipt.json">receipt</a></figcaption></figure>')
    (output / "index.html").write_text('<!doctype html><html><head><meta charset="utf-8"><title>Nvwa chest diagnostic</title><style>body{font:14px system-ui;background:#e8eaed;color:#20242a}main{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}figure{margin:0;background:white;padding:8px}img{width:100%}figcaption{padding:6px}a{color:#3458ac}</style></head><body><h1>Nvwa production-fit chest diagnostics</h1><p>Three columns repeat body, fitted garment, combined. Flat shading only; screenshots cannot certify garment intersection, PBR or animation.</p><main>' + ''.join(cards) + '</main></body></html>')
    (output / "matrix.json").write_text(json.dumps({"identity": identity, "baseline_parity": True, "rows": rows}, indent=2) + "\n")
    print("Review:", output / "index.html")


if __name__ == "__main__":
    main()
