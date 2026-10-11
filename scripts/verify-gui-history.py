#!/usr/bin/env python3
"""Compare native GUI saves against one drag and one undo from an M1 baseline."""

from __future__ import annotations

import argparse
import json
import math
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_BASELINE = (
    Path(__file__).resolve().parent.parent / "docs/evidence/m1/web-sequence.nvwa.json"
)


def read_document(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def differences(left: Any, right: Any, prefix: str = "$") -> list[str]:
    if type(left) is not type(right):
        return [f"{prefix}: type differs"]
    if isinstance(left, dict):
        paths = []
        for key in sorted(left.keys() | right.keys()):
            if key not in left or key not in right:
                paths.append(f"{prefix}.{key}: key missing on one side")
            else:
                paths.extend(differences(left[key], right[key], f"{prefix}.{key}"))
        return paths
    if isinstance(left, list):
        if len(left) != len(right):
            return [f"{prefix}: list length {len(left)} != {len(right)}"]
        paths = []
        for index, (a, b) in enumerate(zip(left, right)):
            paths.extend(differences(a, b, f"{prefix}[{index}]"))
        return paths
    if left != right:
        return [f"{prefix}: {left!r} != {right!r}"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--after-drag", type=Path, required=True)
    parser.add_argument("--after-undo", type=Path, required=True)
    parser.add_argument("--parameter", default="jaw_width")
    parser.add_argument("--expected-value", type=float, default=0.70)
    parser.add_argument("--tolerance", type=float, default=0.01)
    args = parser.parse_args()

    try:
        baseline = read_document(args.baseline)
        after_drag = read_document(args.after_drag)
        after_undo = read_document(args.after_undo)
        revision = baseline["revision"]
        parameters = baseline["character"]["parameters"]
        starting_value = parameters[args.parameter]
        actual_value = after_drag["character"]["parameters"][args.parameter]
        if not all(math.isfinite(float(v)) for v in (starting_value, actual_value)):
            raise ValueError("slider values must be finite numbers")
        if abs(float(actual_value) - args.expected_value) > args.tolerance:
            raise ValueError(
                f"drag value {actual_value!r} is outside "
                f"{args.expected_value} ± {args.tolerance}"
            )
        if actual_value == starting_value:
            raise ValueError("drag did not change the selected parameter")

        expected_drag = deepcopy(baseline)
        expected_drag["revision"] = revision + 1
        expected_drag["character"]["parameters"][args.parameter] = actual_value
        drag_diffs = differences(expected_drag, after_drag)
        if drag_diffs:
            raise ValueError(
                "post-drag whole-document mismatch:\n  " + "\n  ".join(drag_diffs)
            )

        expected_undo = deepcopy(baseline)
        expected_undo["revision"] = revision + 2
        undo_diffs = differences(expected_undo, after_undo)
        if undo_diffs:
            raise ValueError(
                "post-undo whole-document mismatch:\n  " + "\n  ".join(undo_diffs)
            )

        print(
            "PASS: one parameter changed in exactly one revision; "
            "undo restored the full baseline document at the next revision."
        )
        print(
            f"baseline revision={revision}; drag revision={revision + 1}, "
            f"{args.parameter}={actual_value}; undo revision={revision + 2}, "
            f"{args.parameter}={starting_value}"
        )
        return 0
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
