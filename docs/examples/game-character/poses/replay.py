#!/usr/bin/env python3
"""Create editable B1 pose Works and matched front and side PNGs via nvwa-cli."""
import argparse
import json
from pathlib import Path
import subprocess

SHAPES = {
    "a": {"head_width": 1, "hip_width": 0.7, "torso_length": 0.4},
    "b": {"head_width": -0.65, "hip_width": -1, "torso_length": -0.65},
}
VIEWS = {"front": 0, "side": 90}
POSES = ("shoulder", "combined")
CAMERA = {"elevation_degrees": 0, "distance": 3.4, "target_height": 0.95, "fov_degrees": 36}


def read_json(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="fresh output directory")
    args = parser.parse_args()

    cli = args.cli.resolve(strict=True)
    assets = Path(__file__).resolve().parents[4] / "assets"
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    works, commands, renders = (out / folder for folder in ("works", "commands", "renders"))
    for folder in (works, commands, renders):
        folder.mkdir()

    def run(*arguments):
        return subprocess.run(
            [str(cli), *map(str, arguments)], check=True, text=True, stdout=subprocess.PIPE
        ).stdout

    def apply(source, label, edits):
        revision = read_json(source)["revision"]
        payload = [
            {"command_id": f"{label}-{index}", "expected_revision": revision + index, "command": edit}
            for index, edit in enumerate(edits)
        ]
        request = commands / f"{label}.json"
        request.write_text(json.dumps(payload, indent=2) + "\n")
        result = works / f"{label}.nvwa.json"
        run("apply", source, request, result)
        run("validate", result, assets)
        return result

    base = works / "base.nvwa.json"
    run("new-character", assets, base)
    capabilities = json.loads(run("describe-capabilities", base))
    if not capabilities.get("cpu_render", {}).get("compiled"):
        parser.exit(1, "Build nvwa-cli with --features cpu-render to render the pose references.\n")
    if capabilities["id"] != "nvwa-mpfb-b1-motion-v2":
        parser.exit(1, "This example needs the eight-control B1 character profile.\n")
    character = capabilities["character_id"]
    stage = read_json(base)["stage"]

    for shape, recipe in SHAPES.items():
        neutral = apply(base, f"character-{shape}", [
            {"type": "set_parameters", "character_id": character, "values": recipe},
            {"type": "set_diagnostic_pose", "character_id": character, "pose_id": "neutral"},
        ])
        for pose in POSES:
            for view, azimuth in VIEWS.items():
                label = f"{shape}-{pose}-{view}"
                camera = {**CAMERA, "azimuth_degrees": azimuth}
                work = apply(neutral, label, [
                    {"type": "set_diagnostic_pose", "character_id": character, "pose_id": pose},
                    {"type": "set_stage", "stage": {**stage, "camera": camera}},
                ])
                capture = renders / label
                run("render", work, "--assets", assets, "--output", capture,
                    "--width", 1024, "--height", 1024, "--mode", "body-reference",
                    "--subdivision", "level1")
                print(capture / "actual.png")


if __name__ == "__main__":
    main()
