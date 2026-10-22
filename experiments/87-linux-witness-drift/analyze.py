#!/usr/bin/env python3
"""Offline, read-only triangle differential. No assertion or runtime correction."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "experiments/70-b1-garment-defect"), str(ROOT / "experiments/85-current19-shoulder-refit")]
import diagnose as d
import current19 as c

EXPECTED = {"torso_length": 1.0, "jaw_drop": 0.0, "clip_id": "b1_arm_rehearsal_v1", "seconds": 2.0}
FRAME = "t+1__b1_arm_rehearsal_v1__k16.json.gz"
PINNED = {"linux": "cf74fade5f05e05da4166a5e1607709ca2377b5752a5e4259dc072afd0998825",
          "mac-v1": "50b87505309402b8f8724863dc9d0f209d77b5c44391bb17f4c9f74803f847e7",
          "mac-v2": "3ea67240c55e1be81abee8cd4665e312d3d4342962731fad105f7c157ba8ffd9"}
ORIGINAL_SCALAR = 22.0056357384


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_file(path, row):
    d.require(Path(path).is_file(), "provenance file missing")
    d.require(Path(path).stat().st_size == row["bytes"] and digest(path) == row["sha256"], "provenance hash/length mismatch")


def scalar_signal(value):
    """Use the unchanged original unittest six-place assertion, without a waiver."""
    try:
        unittest.TestCase().assertAlmostEqual(value, ORIGINAL_SCALAR, places=6)
        return {"passed": True, "expected": ORIGINAL_SCALAR, "places": 6}
    except AssertionError as error:
        return {"passed": False, "expected": ORIGINAL_SCALAR, "places": 6, "failure": str(error)}


def geometry(rest, posed):
    denominator = d.area([rest[i] for i in d.CORE])
    numerator = d.area([posed[i] for i in d.CORE])
    d.require(denominator > 1e-12, "degenerate fitted-rest triangle")
    return {"numerator_m2": numerator, "denominator_m2": denominator, "ratio": numerator / denominator}


def extract(record, source):
    snapshot = record["snapshot"]
    part = next(p for p in snapshot["parts"] if p["name"] == "garment")
    d.require(d.triangles(part) == source.triangles and d.triangles(part)[200] == list(d.CORE), "garment topology mismatch")
    d.check_bones(snapshot["bones"], EXPECTED["clip_id"], EXPECTED["seconds"])
    rest = d.unique(part, "rest_positions", 1797)
    posed = d.unique(part, "positions", 1797)
    weights = d.unique(part, "full_joint_influences", 1797)
    return {"record": record, "part": part, "rest": rest, "posed": posed, "weights": weights, "bones": snapshot["bones"]}


def load_linux(path, source):
    d.require(digest(path) == PINNED["linux"], "wrong Linux frame hash")
    record, _ = d.read_record(path)
    analysis = d.analyze(record, source, EXPECTED)
    value = extract(record, source)
    d.require(geometry(value["rest"], value["posed"])["ratio"] == analysis["geometry"]["posed_over_fitted_rest_area"], "minimal/full analyzer mismatch")
    value["provenance"] = {"label": "linux", "frame_sha256": digest(path), "schema": record["kind"],
                           "identity_limit": "source/run binding is retained in the original experiment86 CI archive, not inferred from this filename"}
    value["full_source_analysis"] = analysis["reconstruction"]
    return value


def load_mac(directory, label, source):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    identity_row = manifest["receipts"]["identity"]
    check_file(directory / identity_row["path"], identity_row)
    identity = json.loads((directory / identity_row["path"]).read_text())
    rows = [r for r in manifest["cases"] if r["path"] == "keyframes/" + FRAME]
    d.require(len(rows) == 1, "Mac provenance selected frame missing/duplicate")
    path = directory / rows[0]["path"]
    check_file(path, rows[0])
    d.require(digest(path) == PINNED[label], "wrong Mac frame hash")
    record, _ = d.read_record(path)
    d.require(record["run_id"] == identity["run_id"] == manifest["run_id"], "mixed capture provenance")
    c.validate_record(record, identity["run_id"])
    d.require(record["request"]["parameters"] == {"torso_length": 1.0, "jaw_drop": 0.0}
              and record["request"]["clip_id"] == EXPECTED["clip_id"] and record["request"]["seconds"] == 2.0,
              "wrong independently expected Mac frame")
    value = extract(record, source)
    value["provenance"] = {"label": label, "frame_sha256": digest(path), "manifest_sha256": digest(directory / "manifest.json"),
                           "identity_sha256": identity_row["sha256"], "schema": record["kind"], "source_head_claim": identity["source_head"],
                           "source_dirty_paths_claim": identity["source_dirty_paths"], "binary_claim": identity["binary"],
                           "target_claim": identity["target"], "toolchain_claim": identity["toolchain"],
                           "identity_limit": "historical current19 capsule; source-head labels do not audit the compiled source closure; different producer from experiment60 CI"}
    return value


def replay(rest, weights, bones):
    return {i: d.lbs(rest[i], weights[i], bones) for i in d.CORE}


def f32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


def replay_f32(rest, weights, bones):
    """Source-shaped model, not a fresh execution of Rust or its compiler.

    PreparedSkin::new normalizes each row with an ordered f32 sum.
    blend_skin_matrix accumulates weighted matrices. transform_point3 applies
    x, then y, then z, then translation. Each operation below rounds to f32.
    """
    result = {}
    for i in d.CORE:
        total = 0.0
        for _, weight in weights[i]:
            total = f32(total + weight)
        matrix = [0.0] * 16
        for joint, weight in weights[i]:
            normalized = f32(weight / total)
            matrix = [f32(a + f32(b * normalized)) for a,b in zip(matrix, bones[joint]["skin"])]
        point = []
        for axis in range(3):
            value = f32(matrix[axis] * rest[i][0])
            value = f32(f32(matrix[4 + axis] * rest[i][1]) + value)
            value = f32(f32(matrix[8 + axis] * rest[i][2]) + value)
            point.append(f32(matrix[12 + axis] + value))
        result[i] = point
    return result


def compare(left, right):
    """Swap one captured component group in the same independent f64 replay."""
    base = geometry(left["rest"], left["posed"])
    actual = geometry(right["rest"], right["posed"])
    common = {"rest": left["rest"], "weights": left["weights"], "bones": left["bones"]}
    replay_base = geometry(left["rest"], replay(**common))
    swaps = {}
    for component in common:
        selected = dict(common)
        selected[component] = right[component]
        swaps[component] = geometry(selected["rest"], replay(**selected))
    individual = {}
    for i in d.CORE:
        points = dict(left["posed"])
        points[i] = right["posed"][i]
        individual[str(i)] = {"coordinate_delta_m": [b-a for a,b in zip(left["posed"][i], right["posed"][i])],
                              "only_this_upload_replaced": geometry(left["rest"], points)}
    fields = {}
    for key in left["bones"][0]:
        a, b = [v[key] for v in left["bones"]], [v[key] for v in right["bones"]]
        fields[key] = {"changed_bones": sum(x != y for x,y in zip(a,b))}
        if isinstance(a[0], list):
            fields[key]["max_component_delta"] = max(abs(x-y) for row_a,row_b in zip(a,b) for x,y in zip(row_a,row_b))
            fields[key]["changed_f32_components"] = sum(struct.pack("<f", x) != struct.pack("<f", y)
                                                         for row_a,row_b in zip(a,b) for x,y in zip(row_a,row_b))
    per_bone = {}
    for index, (a,b) in enumerate(zip(left["bones"], right["bones"])):
        if a["skin"] != b["skin"] and any(index in dict(left["weights"][i]) for i in d.CORE):
            bones = list(left["bones"])
            bones[index] = dict(a, skin=b["skin"])
            per_bone[a["name"]] = geometry(left["rest"], replay(left["rest"], left["weights"], bones))["ratio"] - replay_base["ratio"]
    f32_left = replay_f32(left["rest"], left["weights"], left["bones"])
    f32_swapped = replay_f32(left["rest"], left["weights"], right["bones"])
    return {"left_geometry": base, "right_geometry": actual, "ratio_delta": actual["ratio"]-base["ratio"],
            "numerator_delta_m2": actual["numerator_m2"]-base["numerator_m2"],
            "denominator_delta_m2": actual["denominator_m2"]-base["denominator_m2"],
            "exact_full_array_equal": {key: left["part"][key] == right["part"][key]
                                       for key in ("source_ids", "indices", "rest_positions", "full_joint_influences")},
            "bones": fields, "individual_core_upload_swaps": individual,
            "independent_f64_replay_baseline": replay_base, "independent_f64_component_swaps": swaps,
            "source_shaped_f32_replay": {"left": geometry(left["rest"], f32_left),
                                          "only_bones_swapped": geometry(left["rest"], f32_swapped),
                                          "left_upload_exact": all(f32_left[i] == left["posed"][i] for i in d.CORE),
                                          "swapped_upload_exact_right": all(f32_swapped[i] == right["posed"][i] for i in d.CORE),
                                          "core_upload_changed_f32_components": sum(struct.pack("<f", x) != struct.pack("<f", y)
                                              for i in d.CORE for x,y in zip(left["posed"][i], right["posed"][i]))},
            "individual_skin_matrix_ratio_deltas": per_bone,
            "causal_limit": "The rounded-f32 model can explain the captured upload delta by changing only captured skin matrices. It does not identify why the matrices differ, the executed machine instructions, compiler behavior or an OS/architecture cause."}


def historical_trace(path):
    report = json.loads(Path(path).read_text())
    selected = [row for row in report["frames"] if row["expected"] == EXPECTED]
    d.require(len(selected) == 1, "historical report selected case missing/duplicate")
    row = selected[0]
    rest = {p["source_id"]: p["fitted_rest_m"] for p in row["core_trace"]}
    posed = {p["source_id"]: p["actual_upload_m"] for p in row["core_trace"]}
    return {"report_sha256": digest(path), "input_sha256_claim": row["input_sha256"], "geometry": geometry(rest, posed),
            "core_trace": row["core_trace"], "identity_limit": "retained report trace only; original full capture not authenticated here"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--linux", required=True, type=Path)
    p.add_argument("--mac-v1", required=True, type=Path)
    p.add_argument("--mac-v2", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    d.require(not a.out.exists(), "refuse to overwrite prior diagnosis")
    source = d.Source(ROOT / "assets/characters/mpfb-b1-v1")
    values = {"linux": load_linux(a.linux, source), "mac-v1": load_mac(a.mac_v1, "mac-v1", source),
              "mac-v2": load_mac(a.mac_v2, "mac-v2", source)}
    result = {"schema_version": 1, "analyzer_sha256": digest(__file__), "source_manifest_sha256": source.hashes["manifest.json"],
              "case": EXPECTED, "core_source_ids": list(d.CORE), "frames": {},
              "comparisons": {"mac-v1_to_linux": compare(values["mac-v1"], values["linux"]),
                              "mac-v1_to_mac-v2": compare(values["mac-v1"], values["mac-v2"])},
              "historical": historical_trace(ROOT / "experiments/70-b1-garment-defect/evidence/final-retained30/report.json"),
              "scope": "Offline replay of preserved arrays only. Original CI remains FAIL. No source/test/tolerance fix, fresh runtime, GUI, GPU or architecture attribution."}
    for label, value in values.items():
        g = geometry(value["rest"], value["posed"])
        result["frames"][label] = {"provenance": value["provenance"], "geometry": g, "original_scalar_assertion": scalar_signal(g["ratio"]),
                                   "core": [{"source_id": i, "rest_m": value["rest"][i], "upload_m": value["posed"][i],
                                             "weights": value["weights"][i]} for i in d.CORE]}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({label: v["geometry"] for label,v in result["frames"].items()}, indent=2))


if __name__ == "__main__":
    main()
