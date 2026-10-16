"""Validate and freeze identities of actual Blender outputs; no geometry synthesis."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def value_sha(value):
    return hashlib.sha256(json.dumps(value, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def write(path, data):
    with path.open("x") as stream:
        json.dump(data, stream, allow_nan=False, indent=2)
        stream.write("\n")


def vector_stats(vectors, length, *, tangent=False):
    assert len(vectors) == length
    zero = 0
    max_unit_error = 0.0
    for vector in vectors:
        assert len(vector) == (4 if tangent else 3) and all(math.isfinite(value) for value in vector)
        norm = math.sqrt(sum(value * value for value in vector[:3]))
        zero += norm == 0
        if norm:
            max_unit_error = max(max_unit_error, abs(norm - 1))
        if tangent:
            assert vector[3] in (-1.0, 1.0)
    return {"vectors": length, "zero_vectors": zero, "max_nonzero_unit_length_error": max_unit_error}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    run = args.run.resolve()
    assert run.is_relative_to(root / ".work/b1-pose-reference")
    summary_path = run / "summary.json"
    summary = json.loads(summary_path.read_text())
    assert summary["status"] == "actual_mpfb_pose_reference_complete"
    assert len(summary["cases"]) == 40 and not summary["graphics_executed"]
    driver = Path(__file__).with_name("pose_reference.py")
    pose_path = Path(__file__).resolve().parents[1] / "poses.json"
    common_path = root / ".work/character-approved-20261016/common-sample.json"
    assert sha(driver) == summary["driver_sha256"]
    assert sha(pose_path) == summary["pose_sha256"]
    assert sha(common_path) == summary["common_sha256"]
    common = json.loads(common_path.read_text())
    poses = json.loads(pose_path.read_text())["poses"]
    expected = {(case["case_id"], pose["pose_id"]) for case in common["cases"] for pose in poses}
    assert {(case["recipe_id"], case["pose_id"]) for case in summary["cases"]} == expected
    actual = set()
    records = []
    weight_hashes = {"body": set(), "garment": set()}
    maxima = {"basis": 0.0, "recurrence": 0.0, "rest_reproduction": 0.0,
              "full_weight_lbs_body": 0.0, "full_weight_lbs_garment": 0.0}
    normal_max = tangent_max = 0.0
    normal_zero = tangent_zero = 0
    for entry in summary["cases"]:
        path = run / entry["path"]
        assert path.parent == run and sha(path) == entry["sha256"]
        data = json.loads(path.read_text())
        assert data["case_id"] == entry["case_id"] and data["case_id"] not in actual
        actual.add(data["case_id"])
        for field in ("common_sha256", "driver_sha256", "pose_sha256", "source_sha256s"):
            assert data[field] == summary[field]
        assert len(data["bones"]) == 53
        bone_names = {bone["name"] for bone in data["bones"]}
        assert len(bone_names) == 53
        for bone in data["bones"]:
            assert bone["parent"] is None or bone["parent"] in bone_names
            for field in ("matrix_local", "matrix_pose", "matrix_basis", "skin_matrix"):
                matrix = bone[field]
                assert len(matrix) == 4 and all(len(row) == 4 for row in matrix)
                assert all(math.isfinite(value) for row in matrix for value in row)
        stats = {}
        for kind, prefix, count, corners in (("body", "", 19158, 73944), ("garment", "garment_", 1797, 6872)):
            positions, rest = data[prefix + "positions"], data[("garment_rest_positions" if prefix else "rest_positions")]
            assert len(positions) == len(rest) == count and data[prefix + "source_ids"] == list(range(count))
            for vectors in (positions, rest):
                assert all(len(vector) == 3 and all(math.isfinite(value) for value in vector) for vector in vectors)
            weights = data[kind + "_weights"]
            assert len(weights) == count and all(row for row in weights)
            assert all(0 <= bone_id < 53 and math.isfinite(weight) and weight > 0
                       for row in weights for bone_id, weight in row)
            assert not data[kind + "_weight_summary"]["truncated"]
            assert not data[kind + "_weight_summary"]["renormalized"]
            weight_hashes[kind].add(value_sha(weights))
            normal_stats = vector_stats(data[prefix + "normals"], count)
            tangent_stats = vector_stats(data[prefix + "tangents"], corners, tangent=True)
            assert len(data[prefix + "loop_source_ids"]) == corners
            assert all(0 <= source_id < count for source_id in data[prefix + "loop_source_ids"])
            assert normal_stats["zero_vectors"] == tangent_stats["zero_vectors"] == 0
            assert normal_stats["max_nonzero_unit_length_error"] < 1e-5
            assert tangent_stats["max_nonzero_unit_length_error"] < 1e-5
            normal_max = max(normal_max, normal_stats["max_nonzero_unit_length_error"])
            tangent_max = max(tangent_max, tangent_stats["max_nonzero_unit_length_error"])
            normal_zero += normal_stats["zero_vectors"]
            tangent_zero += tangent_stats["zero_vectors"]
            displacement = max(abs(pos[axis] - base[axis]) for pos, base in zip(positions, rest) for axis in range(3))
            if data["pose_id"] == "neutral":
                assert displacement < 1e-5
            else:
                assert displacement > .001, (data["case_id"], kind, displacement)
            stats[kind] = {"normals": normal_stats, "tangents": tangent_stats, "max_displacement_from_rest": displacement,
                           "weights_sha256": value_sha(weights), "source_ids_sha256": value_sha(data[prefix + "source_ids"]),
                           "positions_sha256": value_sha(positions), "normals_sha256": value_sha(data[prefix + "normals"]),
                           "tangents_sha256": value_sha(data[prefix + "tangents"])}
        maxima["basis"] = max(maxima["basis"], data["convention_metrics"]["basis_max_component"])
        maxima["recurrence"] = max(maxima["recurrence"], data["convention_metrics"]["pose_recurrence_max_component"])
        maxima["rest_reproduction"] = max(maxima["rest_reproduction"], *data["rest_reproduction_max_component"].values())
        for kind in ("body", "garment"):
            maxima["full_weight_lbs_" + kind] = max(maxima["full_weight_lbs_" + kind],
                                                  data["diagnostic_full_weight_lbs_vs_evaluated"][kind]["max_component"])
        records.append({"case_id": data["case_id"], "recipe_id": data["recipe_id"], "recipe": data["recipe"],
                        "pose_id": data["pose_id"], "path": path.relative_to(root).as_posix(),
                        "sha256": entry["sha256"], "bytes": entry["bytes"], "stats": stats})
    assert all(len(values) == 1 for values in weight_hashes.values())
    args.out.mkdir(parents=True, exist_ok=True)
    frozen = {"schema_version": 1, "status": "actual_mpfb_pose_reference_frozen", "common_sha256": summary["common_sha256"],
              "pose_sha256": summary["pose_sha256"], "driver_sha256": summary["driver_sha256"],
              "source_sha256s": summary["source_sha256s"], "audited_source_receipt_sha256s": summary["audited_source_receipt_sha256s"],
              "reference_summary_path": summary_path.relative_to(root).as_posix(), "reference_summary_sha256": sha(summary_path),
              "command": summary["command"], "blender_version": summary["blender_version"], "mpfb_version": summary["mpfb_version"],
              "mpfb_build": summary["mpfb_build"], "body_weight_summary": summary["body_weight_summary"],
              "garment_weight_summary": summary["garment_weight_summary"], "body_modifiers": summary["body_modifiers"],
              "garment_modifiers": summary["garment_modifiers"], "cases": records,
              "conventions": {"matrices": "row-major arrays, column vectors, Blender Z-up metres",
                              "deformation": "matrix_pose @ inverse(matrix_local)",
                              "pose": "bone-local matrix_basis postrotation; original source rolls retained",
                              "body_capture": "full cage before active clothing visibility MASK modifiers; restored",
                              "weights": "original untruncated and unnormalized deform vertex-group values",
                              "normal": "evaluated mesh-local; inverse-transpose world transform then normalize",
                              "tangent": "evaluated UV-corner xyz+bitangent sign; linear world transform then normalize"},
              "graphics_executed": False, "candidate_comparison_executed": False}
    write(args.out / "manifest.json", frozen)
    report = {"schema_version": 1, "status": "reference_complete", "cases": len(records), "recipes": 8, "poses": 5,
              "manifest_sha256": sha(args.out / "manifest.json"), "driver_sha256": sha(driver),
              "freeze_driver_sha256": sha(Path(__file__)), "pose_sha256": sha(pose_path),
              "common_sha256": sha(common_path), "maxima": maxima,
              "normals": {"zero_vectors_all_cases": normal_zero, "max_unit_length_error": normal_max},
              "tangents": {"zero_vectors_all_cases": tangent_zero, "max_unit_length_error": tangent_max},
              "body_vertices_per_case": 19158, "garment_vertices_per_case": 1797, "bones_per_case": 53,
              "full_weight_coverage": True, "all_helpers_retained": True,
              "runtime_comparison": "NOT-RUN by reference worker; independently owned by 57",
              "graphics": "NOT-RUN; CPU depsgraph only", "elapsed_seconds_blender": summary["elapsed_seconds"]}
    write(args.out / "summary.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
