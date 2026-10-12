#!/usr/bin/env python3
"""Check saved Work transitions and runtime canvas geometry records.

This checker validates JSON records. It does not drive a browser or infer
pointer alignment, IME success, a DPR transition, or a real tab transition.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


class CheckError(Exception):
    """A record failed a deterministic check."""


class PartialError(Exception):
    """A required evidence field is missing, so the claim is not run."""


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON number {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=_reject_constant,
            object_pairs_hook=_unique_object,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise CheckError(f"cannot read valid JSON from {path}: {error}") from error


def require_work(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CheckError(f"{label} must be a JSON object")
    missing = {"schema_version", "revision", "profile", "character", "timeline"} - value.keys()
    if missing:
        raise CheckError(f"{label} is not a complete Work; missing {sorted(missing)}")
    if type(value["schema_version"]) is not int or value["schema_version"] < 1:
        raise CheckError(f"{label}.schema_version must be a positive integer")
    if type(value["revision"]) is not int or value["revision"] < 0:
        raise CheckError(f"{label}.revision must be a non-negative integer")
    if not isinstance(value["profile"], dict):
        raise CheckError(f"{label}.profile must be an object")
    character = value["character"]
    if not isinstance(character, dict) or not isinstance(character.get("parameters"), dict):
        raise CheckError(f"{label}.character.parameters must be an object")
    if not isinstance(value["timeline"], list):
        raise CheckError(f"{label}.timeline must be an array")
    return value


def _parameter_number(work: dict[str, Any], name: str, label: str) -> int | float:
    parameters = work["character"]["parameters"]
    if name not in parameters:
        raise CheckError(f"{label} has no character parameter {name!r}")
    number = parameters[name]
    if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number):
        raise CheckError(f"{label}.character.parameters.{name} must be a finite number")
    return number


def _same_json(left: Any, right: Any) -> bool:
    """Compare JSON values without Python's bool/int or int/float coercions."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_same_json(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(_same_json(a, b) for a, b in zip(left, right))
    return left == right


def _differences(left: Any, right: Any, path: str = "") -> list[str]:
    if type(left) is not type(right):
        return [path or "$" ]
    if isinstance(left, dict):
        changed: list[str] = []
        for key in sorted(left.keys() | right.keys()):
            child = f"{path}.{key}" if path else key
            if key not in left or key not in right:
                changed.append(child)
            else:
                changed.extend(_differences(left[key], right[key], child))
        return changed
    if isinstance(left, list):
        if len(left) != len(right):
            return [path or "$" ]
        changed = []
        for index, (before, after) in enumerate(zip(left, right)):
            changed.extend(_differences(before, after, f"{path}[{index}]"))
        return changed
    return [] if left == right else [path or "$" ]


def _load_work(path: Path, label: str) -> dict[str, Any]:
    return require_work(load_json(path), label)


def check_edit(before_path: Path, after_path: Path, parameter: str) -> None:
    before = _load_work(before_path, "baseline")
    after = _load_work(after_path, "edited Work")
    before_value = _parameter_number(before, parameter, "baseline")
    after_value = _parameter_number(after, parameter, "edited Work")
    if before_value == after_value:
        raise CheckError(f"selected parameter {parameter!r} did not change")
    if after["revision"] <= before["revision"]:
        raise CheckError("edited Work revision must increase monotonically")
    expected = {"revision", f"character.parameters.{parameter}"}
    actual = set(_differences(before, after))
    if actual != expected:
        raise CheckError(
            "edited Work changed unexpected fields; "
            f"expected {sorted(expected)}, observed {sorted(actual)}"
        )
    print(
        "PASS work-edit: only the selected character parameter and revision changed "
        f"({parameter} {before_value} -> {after_value}; revision {before['revision']} -> {after['revision']})"
    )


def check_preserved(before_path: Path, after_path: Path, action: str) -> None:
    before = _load_work(before_path, "before Work")
    after = _load_work(after_path, "after Work")
    if not _same_json(before, after):
        raise CheckError(f"{action} action changed Work fields: {_differences(before, after)}")
    print(f"PASS work-{action}: complete Work is unchanged, including revision {before['revision']}")


def check_undo(base_path: Path, edited_path: Path, undo_path: Path, parameter: str) -> None:
    base = _load_work(base_path, "baseline")
    edited = _load_work(edited_path, "edited Work")
    undone = _load_work(undo_path, "undone Work")
    check_edit_values(base, edited, parameter)
    if undone["revision"] <= edited["revision"]:
        raise CheckError("Undo revision must increase monotonically after the edit")
    base_content = {key: value for key, value in base.items() if key != "revision"}
    undo_content = {key: value for key, value in undone.items() if key != "revision"}
    if not _same_json(base_content, undo_content):
        raise CheckError(
            "Undo did not restore all baseline content; "
            f"differences: {_differences(base_content, undo_content)}"
        )
    print(
        "PASS work-undo: all Work content matches baseline; revision advances "
        f"monotonically ({base['revision']} -> {edited['revision']} -> {undone['revision']})"
    )


def check_edit_values(base: dict[str, Any], edited: dict[str, Any], parameter: str) -> None:
    before_value = _parameter_number(base, parameter, "baseline")
    after_value = _parameter_number(edited, parameter, "edited Work")
    if before_value == after_value:
        raise CheckError(f"selected parameter {parameter!r} did not change before Undo")
    if edited["revision"] <= base["revision"]:
        raise CheckError("edited Work revision must increase monotonically before Undo")
    expected = {"revision", f"character.parameters.{parameter}"}
    actual = set(_differences(base, edited))
    if actual != expected:
        raise CheckError(
            "pre-Undo Work changed unexpected fields; "
            f"expected {sorted(expected)}, observed {sorted(actual)}"
        )


def _finite_number(record: dict[str, Any], path: str, label: str) -> float:
    current: Any = record
    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            raise PartialError(f"{label}.{path} is missing; geometry check is NOT-RUN")
        current = current[key]
    if isinstance(current, bool) or not isinstance(current, (int, float)) or not math.isfinite(current):
        raise CheckError(f"{label}.{path} must be finite numeric data")
    return float(current)


def _positive(value: float, name: str) -> None:
    if value <= 0:
        raise CheckError(f"{name} must be positive")


def _pixel_round(value: float) -> int:
    return math.floor(value + 0.5)


def _check_transition_claims(record: dict[str, Any]) -> bool:
    if "transition_claims" not in record:
        raise PartialError("transition_claims is missing; transition evidence is NOT-RUN")
    claims = record["transition_claims"]
    if not isinstance(claims, list):
        raise CheckError("transition_claims must be an array")
    for index, claim in enumerate(claims):
        label = f"transition_claims[{index}]"
        if not isinstance(claim, dict) or not isinstance(claim.get("claim"), str) or not claim["claim"].strip():
            raise CheckError(f"{label}.claim must be a non-empty string")
        if "observed_events" not in claim:
            raise PartialError(f"{label}.observed_events is missing; claim is NOT-RUN")
        events = claim["observed_events"]
        if not isinstance(events, list) or not events:
            raise PartialError(f"{label}.observed_events is empty; claim is NOT-RUN")
        for event_index, event in enumerate(events):
            event_label = f"{label}.observed_events[{event_index}]"
            if not isinstance(event, dict):
                raise CheckError(f"{event_label} must be an object")
            if not isinstance(event.get("event_name"), str) or not event["event_name"].strip():
                raise PartialError(f"{event_label}.event_name is missing; claim is NOT-RUN")
            if event.get("observed") is not True:
                raise PartialError(f"{event_label}.observed is not true; claim is NOT-RUN")
            source = event.get("source")
            if not isinstance(source, str) or not source.strip():
                raise PartialError(f"{event_label}.source is missing; claim is NOT-RUN")
            if "screenshot" in source.lower() or "image" in source.lower():
                raise CheckError(f"{event_label} uses screenshot/image evidence, not an observed runtime event")
    return bool(claims)


def check_geometry(path: Path) -> None:
    record = load_json(path)
    if not isinstance(record, dict):
        raise CheckError("geometry record must be a JSON object")
    source = record.get("observation_source")
    if source != "runtime_dom":
        if isinstance(source, str) and ("screenshot" in source.lower() or "image" in source.lower()):
            raise CheckError("tool screenshots/images are not runtime-DPI evidence")
        raise PartialError("observation_source must be runtime_dom; runtime geometry is NOT-RUN")

    css_width = _finite_number(record, "css_size.width", "geometry")
    css_height = _finite_number(record, "css_size.height", "geometry")
    x = _finite_number(record, "client_rect.x", "geometry")
    y = _finite_number(record, "client_rect.y", "geometry")
    rect_width = _finite_number(record, "client_rect.width", "geometry")
    rect_height = _finite_number(record, "client_rect.height", "geometry")
    physical_width = _finite_number(record, "physical_canvas.width", "geometry")
    physical_height = _finite_number(record, "physical_canvas.height", "geometry")
    dpr = _finite_number(record, "device_pixel_ratio", "geometry")
    for value, name in (
        (css_width, "css_size.width"),
        (css_height, "css_size.height"),
        (rect_width, "client_rect.width"),
        (rect_height, "client_rect.height"),
        (physical_width, "physical_canvas.width"),
        (physical_height, "physical_canvas.height"),
        (dpr, "device_pixel_ratio"),
    ):
        _positive(value, name)
    if type(record.get("physical_canvas", {}).get("width")) is not int or type(record["physical_canvas"]["height"]) is not int:
        raise CheckError("physical_canvas.width and height must be integer pixel counts")
    if not math.isfinite(x) or not math.isfinite(y):
        raise CheckError("client_rect.x and y must be finite")
    if not math.isclose(css_width, rect_width, rel_tol=0, abs_tol=1e-6) or not math.isclose(
        css_height, rect_height, rel_tol=0, abs_tol=1e-6
    ):
        raise CheckError("css_size must match client_rect width and height")
    relation = record.get("logical_relation")
    expected_relation = "physical_canvas = round(client_rect_css_size * device_pixel_ratio)"
    if relation != expected_relation:
        raise PartialError(f"logical_relation must explicitly equal {expected_relation!r}; geometry relation is NOT-RUN")
    expected_width = _pixel_round(rect_width * dpr)
    expected_height = _pixel_round(rect_height * dpr)
    if (physical_width, physical_height) != (expected_width, expected_height):
        raise CheckError(
            "physical_canvas dimensions disagree with the declared CSS x DPR relation; "
            f"expected {expected_width}x{expected_height}, observed {physical_width:g}x{physical_height:g}"
        )

    print(
        "PASS geometry consistency: finite positive CSS/clientRect, physical canvas and DPR; "
        f"declared relation gives {expected_width}x{expected_height} physical pixels"
    )
    claims_present = _check_transition_claims(record)
    if claims_present:
        print("PARTIAL transition claims: observed event records are present; claim semantics are not evaluated")
    else:
        print("NOT-RUN transitions: no claims supplied; pointer alignment, actual DPR change, IME and tab hide/show remain unverified")
    print("NOT-RUN pointer alignment: geometry ratios alone do not establish input alignment")
    print("NOT-RUN UI transition outcomes: actual DPR change, IME behavior and real tab hide/show are not inferred from geometry")
    print("NOT-RUN runtime-DPI transition: screenshots and canvas attributes alone do not establish an actual DPR change")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    edit = subparsers.add_parser("work-edit", help="check that an edit changes one selected parameter and revision")
    edit.add_argument("baseline", type=Path)
    edit.add_argument("edited", type=Path)
    edit.add_argument("--parameter", required=True)

    layout = subparsers.add_parser("work-layout", help="check that a layout-only action preserves the complete Work")
    layout.add_argument("before", type=Path)
    layout.add_argument("after", type=Path)
    layout.add_argument("--action", choices=("layout", "focus"), required=True)

    undo = subparsers.add_parser("work-undo", help="check one edit and complete-content restoration after Undo")
    undo.add_argument("baseline", type=Path)
    undo.add_argument("edited", type=Path)
    undo.add_argument("undone", type=Path)
    undo.add_argument("--parameter", required=True)

    geometry = subparsers.add_parser("geometry", help="check one runtime DOM geometry record")
    geometry.add_argument("record", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "work-edit":
            check_edit(args.baseline, args.edited, args.parameter)
        elif args.command == "work-layout":
            check_preserved(args.before, args.after, args.action)
        elif args.command == "work-undo":
            check_undo(args.baseline, args.edited, args.undone, args.parameter)
        elif args.command == "geometry":
            check_geometry(args.record)
        return 0
    except PartialError as error:
        print(f"PARTIAL / NOT-RUN: {error}", file=sys.stderr)
        return 2
    except CheckError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
