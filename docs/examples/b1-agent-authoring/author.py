#!/usr/bin/env python3
"""Create an offline B1 example through the real CLI; Python standard library only."""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cli", type=Path, help="path to nvwa-cli")
    parser.add_argument("asset_root", type=Path, help="complete filesystem assets root")
    parser.add_argument("output_dir", type=Path, help="new directory; any existing path is refused")
    args = parser.parse_args()
    cli = args.cli.resolve(strict=True)
    asset_root = args.asset_root.resolve(strict=True)
    output = args.output_dir.absolute()
    # Exclusive creation prevents reruns from overwriting an existing Work or receipt.
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "run.json", {
        "cli": str(cli), "cli_sha256": hashlib.sha256(cli.read_bytes()).hexdigest(),
        "asset_root": str(asset_root), "output_dir": str(output),
    })

    def call(*arguments):
        argv = [str(cli), *map(str, arguments)]
        result = subprocess.run(argv, cwd=output, capture_output=True, text=True)
        with (output / "calls.jsonl").open("a") as receipts:
            receipts.write(json.dumps({"argv": argv, "cwd": str(output),
                                       "exit_code": result.returncode,
                                       "stdout": result.stdout, "stderr": result.stderr}) + "\n")
        if result.returncode:
            raise RuntimeError(f"CLI failed ({result.returncode}): {arguments[0]}; inspect calls.jsonl and actual output before retrying")
        return json.loads(result.stdout)

    call("new-character", asset_root, "created.nvwa.json")
    discovered = call("describe-capabilities", "created.nvwa.json")
    write_json(output / "capabilities.json", discovered)
    contract = discovered["cli_contract"]
    if contract["schema_version"] != 1:
        raise ValueError("This example expects discovery contract schema 1")
    character_id = discovered["character_id"]
    revision = discovered["document_revision"]
    parameters = {
        "torso_length": 0.25, "jaw_drop": -0.20, "head_width": 0.15,
        "nose_width": -0.15, "mouth_width": 0.20, "chin_width": -0.25,
        "neck_width": 0.10, "hip_width": 0.20,
    }
    available = {parameter["id"]: parameter for parameter in discovered["parameters"]}
    for name, value in parameters.items():
        if not available[name]["min"] <= value <= available[name]["max"]:
            raise ValueError(f"Discovered range does not admit {name}={value}")
    appearance = next(item for item in contract["set_appearance"]["compatible_sets"]
                      if item["asset_set_id"] == "mpfb-b1-cc0-appearance-v2-short01-v1")
    source_clips = {clip["id"]: clip for clip in discovered["clips"]}
    arm = "b1_arm_rehearsal_v1"
    knee = "b1_knee_flex_v1"
    if any(source_clips[clip]["duration_seconds"] != 4.0 for clip in (arm, knee)):
        raise ValueError("This example requires the existing two four-second authored clips")
    clips = [{"id": f"rehearsal-{index + 1}", "clip_id": clip,
              "start_seconds": float(index * 4), "duration_seconds": 4.0,
              "speed": 1.0, "looping": False}
             for index, clip in enumerate((arm, knee, arm, knee, arm))]
    stage = copy.deepcopy(discovered["stage"])
    stage["background_color_srgb"] = [0.12, 0.17, 0.23]
    stage["floor"]["color_srgb"] = [0.32, 0.38, 0.44]
    stage["camera"]["azimuth_degrees"] = 24.0
    stage["camera"]["distance"] = 4.2
    stage["key_light"]["azimuth_degrees"] = -42.0
    stage["ambient"]["brightness"] = 220.0
    commands = []
    for suffix, command in (
        ("parameters", {"type": "set_parameters", "character_id": character_id, "values": parameters}),
        ("short01", {"type": "set_appearance", "character_id": character_id, "appearance": appearance}),
        ("stage", {"type": "set_stage", "stage": stage}),
        ("sequence", {"type": "set_timeline", "clips": clips}),
    ):
        commands.append({"command_id": f"b1-agent-{suffix}", "expected_revision": revision, "command": command})
        revision += 1
    write_json(output / "author.commands.json", commands)
    call("apply", "created.nvwa.json", "author.commands.json", "authored.nvwa.json")
    call("validate", "authored.nvwa.json", asset_root)
    call("save", "authored.nvwa.json", "first-saved.nvwa.json")
    call("validate", "first-saved.nvwa.json", asset_root)
    # Inspect the saved Work; use its actual revision in the next invocation.
    inspected = call("inspect", "first-saved.nvwa.json")
    write_json(output / "first-inspect.json", inspected)
    actual = json.loads((output / "first-saved.nvwa.json").read_text())
    # set_timeline replaces the whole list. Change only row 3's authored action.
    edited_clips = copy.deepcopy(actual["timeline"])
    edited_clips[2]["clip_id"] = knee
    edit = {"command_id": "b1-agent-row-3-knee", "expected_revision": actual["revision"],
            "command": {"type": "set_timeline", "clips": edited_clips}}
    write_json(output / "edit.command.json", edit)
    call("apply", "first-saved.nvwa.json", "edit.command.json", "edited.nvwa.json")
    call("validate", "edited.nvwa.json", asset_root)
    call("save", "edited.nvwa.json", "final-saved.nvwa.json")
    call("validate", "final-saved.nvwa.json", asset_root)
    final_inspect = call("inspect", "final-saved.nvwa.json")
    write_json(output / "final-inspect.json", final_inspect)
    print(json.dumps({"output_dir": str(output), "first_work": "first-saved.nvwa.json",
                      "final_work": "final-saved.nvwa.json", "duration_seconds": 20,
                      "final_revision": json.loads((output / "final-saved.nvwa.json").read_text())["revision"]}))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, StopIteration, RuntimeError) as error:
        print(f"authoring stopped: {error}", file=sys.stderr)
        sys.exit(1)
