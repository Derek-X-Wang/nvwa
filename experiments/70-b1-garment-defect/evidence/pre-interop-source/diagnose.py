#!/usr/bin/env python3
"""Bounded source/upload audit for one shoulder triangle; no garment correction."""
import argparse
import gzip
import hashlib
import json
import math
import re
import sys
from pathlib import Path

# Reuse the existing independently authored clip/FK/gauge guard unchanged.
# The new source-fit/weight/LBS reconstruction below does not call product math.
SUPPORT = Path(__file__).resolve().parents[1] / "60-b1-continuous-motion"
sys.path.insert(0, str(SUPPORT))
from checker import check_bones

CORE = (246, 244, 182)
CLIPS = ("b1_arm_rehearsal_v1", "b1_knee_flex_v1")
ASSET_ID = "mpfb-hm08-game-engine-female-sportsuit01-v1"
MANIFEST_SHA = "abcdbc26e03431c740c5fce98de22902089f985823a3c655db2416d042d62b18"
PROFILE = "nvwa-mpfb-b1-motion-v1"
MAX_INPUT = 64 * 1024 * 1024
# Independent f64 replay versus retained f32 arrays, not appearance thresholds.
REST_EPS = 1e-6
WEIGHT_EPS = 1e-6
UPLOAD_EPS = 1e-5  # Existing experiment60 independent-LBS numeric bound.


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def vector(value):
    require(isinstance(value, list) and len(value) == 3 and all(map(finite, value)), "invalid XYZ")
    return value


def integer(value, low, high):
    require(isinstance(value, int) and not isinstance(value, bool) and low <= value < high, "invalid index")
    return value


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def read_record(path):
    path = Path(path)
    require(path.stat().st_size <= MAX_INPUT, "compressed/input size limit")
    raw = path.read_bytes()
    if path.suffix == ".gz":
        with gzip.open(path, "rb") as stream:
            decoded = stream.read(MAX_INPUT + 1)
    else:
        decoded = raw
    require(len(decoded) <= MAX_INPUT, "decoded input size limit")
    data = json.loads(decoded, object_pairs_hook=pairs, parse_constant=lambda x: require(False, "nonfinite JSON"))
    return data, sha(raw)


def delta(a, b):
    return [x - y for x, y in zip(a, b)]


def norm(value):
    return math.sqrt(sum(x * x for x in value))


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def area(points):
    a, b, c = points
    return norm(cross(delta(b, a), delta(c, a))) / 2


def component_error(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


def point(matrix, position):
    require(isinstance(matrix, list) and len(matrix) == 16 and all(map(finite, matrix)), "invalid column-major matrix")
    require(component_error(matrix[3::4], [0, 0, 0, 1]) < 1e-6, "non-affine matrix")
    return [sum(matrix[c * 4 + r] * position[c] for c in range(3)) + matrix[12 + r] for r in range(3)]


def normalize(row):
    require(bool(row) and all(finite(w) and w > 0 for _, w in row), "invalid final-positive row")
    total = sum(w for _, w in row)
    require(finite(total) and total > 0, "invalid row sum")
    require(len({j for j, _ in row}) == len(row), "duplicate joint")
    return [(j, w / total) for j, w in row]


def lbs(rest, row, bones):
    result = [0.0, 0.0, 0.0]
    for joint, weight in normalize(row):
        integer(joint, 0, len(bones))
        transformed = point(bones[joint]["skin"], rest)
        for axis in range(3):
            result[axis] += transformed[axis] * weight
    return result


def transfer(row, names, weights):
    """Signed helper aggregation first, retain every positive final bone, normalize."""
    result = []
    for joint, name in enumerate(names):
        bone = weights[name]
        value = sum(bone.get(helper, 0.0) * coeff for helper, coeff in zip(row["helpers"], row["coefficients"]))
        if value > 0:
            result.append((joint, value))
    return normalize(result)


def fit_row(row, cage, scales):
    return [sum(cage[h][a] * w for h, w in zip(row["helpers"], row["coefficients"])) + scales[a] * row["offset_m"][a] for a in range(3)]


def parse_mapping(text):
    rows, axes = [], {}
    section = False
    for line in text.splitlines():
        tokens = line.split()
        if not tokens or tokens[0].startswith("#"):
            continue
        if tokens[0] in ("x_scale", "y_scale", "z_scale"):
            a = ("x_scale", "y_scale", "z_scale").index(tokens[0])
            require(len(tokens) == 4 and a not in axes, "invalid source scale rule")
            axes[a] = (int(tokens[1]), int(tokens[2]), float(tokens[3]))
        if tokens[:2] == ["verts", "0"]:
            section = True
            continue
        if tokens[0] == "delete_verts":
            break
        if section:
            require(len(tokens) == 9, "expected admitted nine-column MHCLO row")
            coefficients = list(map(float, tokens[3:6]))
            total = sum(coefficients)
            require(abs(total) > 2 ** -23, "zero signed coefficient sum")
            rows.append({"helpers": list(map(int, tokens[:3])), "coefficients": [x / total for x in coefficients], "offset_m": list(map(float, tokens[6:9]))})
    require(len(rows) == 1797 and set(axes) == {0, 1, 2}, "source MHCLO coverage")
    return rows, axes


def parse_obj(text):
    vertices, triangles = [], []
    for line in text.splitlines():
        tokens = line.split()
        if not tokens:
            continue
        if tokens[0] == "v":
            vertices.append(list(map(float, tokens[1:4])))
        elif tokens[0] == "f":
            face = [int(x.split("/")[0]) - 1 for x in tokens[1:]]
            for j in range(1, len(face) - 1):
                triangles.append([face[0], face[j], face[j + 1]])
    require(len(vertices) == 1797, "source OBJ vertex coverage")
    return vertices, triangles


class Source:
    def __init__(self, root):
        self.root = Path(root)
        raw = (self.root / "manifest.json").read_bytes()
        require(sha(raw) == MANIFEST_SHA, "source manifest SHA mismatch")
        manifest = json.loads(raw)
        require(manifest["asset_id"] == ASSET_ID, "wrong source asset")
        self.hashes = {"manifest.json": sha(raw)}
        for entry in manifest["files"]:
            name = entry["path"]
            require(not Path(name).is_absolute() and ".." not in Path(name).parts, "unsafe manifest name")
            data = (self.root / name).read_bytes()
            require(len(data) == entry["bytes"] and sha(data) == entry["sha256"], "source bytes mismatch: " + name)
            self.hashes[name] = sha(data)
        self.mapping, self.axes = parse_mapping((self.root / "garment/female_sportsuit01.mhclo").read_text())
        self.vertices, self.triangles = parse_obj((self.root / "garment/female_sportsuit01.obj").read_text())
        raw_weights = json.loads((self.root / "weights.game_engine.json").read_text())["weights"]
        self.weights = {name: {int(vertex): float(weight) for vertex, weight in rows if weight > 0} for name, rows in raw_weights.items()}
        self.rig = json.loads((self.root / "rig.game_engine.json").read_text())
        self.support_hashes = {str(Path("experiments/60-b1-continuous-motion") / name): sha((SUPPORT / name).read_bytes()) for name in ("checker.py", "geometry.py")}


def unique(part, key, count):
    require(len(part["source_ids"]) == len(part[key]), "source/array coverage mismatch")
    result = {}
    for source, value in zip(part["source_ids"], part[key]):
        integer(source, 0, count)
        if key != "full_joint_influences":
            vector(value)
        if source in result:
            require(value == result[source], "inconsistent duplicate source value: " + key)
        result[source] = value
    require(set(result) == set(range(count)), "incomplete source coverage: " + key)
    return result


def triangles(part):
    indices, ids = part["indices"], part["source_ids"]
    require(bool(indices) and len(indices) % 3 == 0, "invalid triangle coverage")
    return [[ids[integer(i, 0, len(ids))] for i in indices[k:k + 3]] for k in range(0, len(indices), 3)]


def cyclic(tri):
    return min(tuple(tri[i:] + tri[:i]) for i in range(3))


def validate_binding(record, expected):
    snapshot, request = record["snapshot"], record["request"]
    require(record.get("kind") in ("matrix", "studio"), "unknown capture record kind")
    if record["kind"] == "studio":
        require(request.get("action") == "sample" and isinstance(request.get("request_id"), str) and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", request["request_id"]), "invalid exact Studio sample request")
    require(snapshot["profile_id"] == PROFILE and snapshot["asset_id"] == ASSET_ID, "wrong profile/asset")
    require(len(snapshot["bones"]) == 53 and len({b["name"] for b in snapshot["bones"]}) == 53, "actual53 bone coverage")
    require(snapshot["mode"] == "motion", "non-motion capture")
    for key in ("torso_length", "jaw_drop"):
        require(finite(expected[key]) and -1 <= expected[key] <= 1 and finite(request[key]) and finite(snapshot["parameters"][key]) and request[key] == expected[key] and snapshot["parameters"][key] == expected[key], "stale requested shape: " + key)
    require(expected["clip_id"] in CLIPS and request["clip_id"] == expected["clip_id"], "wrong requested clip")
    seconds = expected["seconds"]
    require(finite(seconds) and 0 <= seconds <= 4 and finite(request["seconds"]) and request["seconds"] == seconds, "wrong requested seconds")
    sample = snapshot["sample"]
    require(sample["clip_id"] == expected["clip_id"] and sample["timeline_id"] == "probe-entry", "stale actual clip/entry")
    require(sample["playing"] is False, "capture must be held")
    for field in ("source_seconds", "position_seconds"):
        require(finite(sample[field]) and abs(sample[field] - seconds) <= 1e-6, "stale actual time: " + field)
    integer(sample["serial"], 1, 2 ** 63)
    for field in ("generation", "revision"):
        integer(snapshot[field], 0, 2 ** 63)
    if record.get("kind") == "matrix":
        k = integer(request["k"], 0, 33)
        require(seconds == k / 8, "stale matrix index")
    require(len(snapshot["parts"]) == 2 and {p["name"] for p in snapshot["parts"]} == {"body", "garment"}, "actual two-part coverage")
    return snapshot


def region_metrics(rest, posed, ts, region, core):
    result = {}
    for label, subset in [("all_incident", ts), ("mixed_boundary", [t for t in ts if any(i not in region for i in t)]), ("non_core", [t for t in ts if not any(i in core for i in t)])]:
        ratios = [(area([posed[i] for i in t]) / area([rest[i] for i in t]), t) for t in subset if area([rest[i] for i in t]) > 1e-12]
        value, tri = max(ratios)
        result[label] = {"triangles": len(subset), "max_area_over_same_frame_rest": value, "max_triangle": tri}
    return result


def analyze(record, source, expected):
    s = validate_binding(record, expected)
    body = next(p for p in s["parts"] if p["name"] == "body")
    garment = next(p for p in s["parts"] if p["name"] == "garment")
    require({b["name"]: b["parent"] for b in s["bones"]} == {name: row["parent"] or None for name, row in source.rig.items()}, "source/actual rig hierarchy mismatch")
    _, fk_error, head_error, bind_error = check_bones(s["bones"], expected["clip_id"], expected["seconds"])
    point(body["display_transform"], [0, 0, 0])
    require(component_error(body["display_transform"], garment["display_transform"]) <= 1e-6, "body/garment global placement mismatch")
    cage = unique(body, "rest_positions", 19158)
    rest = unique(garment, "rest_positions", 1797)
    posed = unique(garment, "positions", 1797)
    influences = unique(garment, "full_joint_influences", 1797)
    ts = triangles(garment)
    require([cyclic(t) for t in ts] == [cyclic(t) for t in source.triangles], "source/upload topology mismatch")
    require(ts[200] == list(CORE), "selected triangle200 changed")
    scales = []
    for axis in range(3):
        low, high, reference = source.axes[axis]
        require(abs(reference) > 1e-12, "zero source scale reference")
        scales.append((cage[high][axis] - cage[low][axis]) / reference)
    names = [b["name"] for b in s["bones"]]
    require(set(names) == set(source.weights), "source/actual bone-name mismatch")
    fitted = {i: fit_row(row, cage, scales) for i, row in enumerate(source.mapping)}
    source_rows = {i: transfer(row, names, source.weights) for i, row in enumerate(source.mapping)}
    rest_error = max(component_error(fitted[i], rest[i]) for i in rest)
    row_error = 0.0
    for i in rest:
        a, b = dict(source_rows[i]), dict(normalize(influences[i]))
        require(set(a) == set(b), "source/upload final-positive bone support mismatch")
        row_error = max(row_error, max(abs(a[j] - b[j]) for j in a))
    reconstructed = {i: lbs(rest[i], influences[i], s["bones"]) for i in rest}
    source_reconstructed = {i: lbs(fitted[i], source_rows[i], s["bones"]) for i in rest}
    upload_error = max(component_error(reconstructed[i], posed[i]) for i in rest)
    source_upload_error = max(component_error(source_reconstructed[i], posed[i]) for i in rest)
    require(rest_error <= REST_EPS, "source/fitted-rest reconstruction mismatch")
    require(row_error <= WEIGHT_EPS, "source/upload normalized weight mismatch")
    require(upload_error <= UPLOAD_EPS and source_upload_error <= UPLOAD_EPS, "independent LBS/upload mismatch")
    core = set(CORE)
    region = {i for t in ts if core.intersection(t) for i in t}
    selected = [t for t in ts if region.intersection(t)]
    rest_area, posed_area = area([rest[i] for i in CORE]), area([posed[i] for i in CORE])
    raw_area = area([source.vertices[i] for i in CORE])
    require(rest_area > 1e-12 and raw_area > 1e-12, "degenerate target rest/raw triangle")
    trace = []
    for i in CORE:
        trace.append({"source_id": i, "mapping": source.mapping[i], "normalized_weights": {names[j]: w for j, w in source_rows[i]}, "raw_obj_m": source.vertices[i], "fitted_rest_m": rest[i], "actual_upload_m": posed[i], "replayed_upload_m": reconstructed[i], "actual_stage_m": point(garment["display_transform"], posed[i])})
    return {"expected": expected, "identity": {"generation": s["generation"], "revision": s["revision"], "character_entity": s["character_entity"], "garment_entity": garment["display_entity"], "mesh_handle": garment["mesh_handle"], "sample": s["sample"]}, "geometry": {"source_triangle": list(CORE), "display_triangle": 200, "raw_obj_area_m2": raw_area, "fitted_rest_area_m2": rest_area, "actual_posed_area_m2": posed_area, "posed_over_fitted_rest_area": posed_area / rest_area, "fitted_rest_over_raw_obj_area": rest_area / raw_area, "actual_edge_lengths_m": [norm(delta(posed[CORE[j]], posed[CORE[(j + 1) % 3]])) for j in range(3)]}, "reconstruction": {"all_source_vertices": 1797, "authored_fk_max_component_error": fk_error, "authored_joint_head_max_component_error_m": head_error, "rest_inverse_bind_identity_error": bind_error, "rest_max_component_error_m": rest_error, "normalized_weight_max_component_error": row_error, "actual_weight_lbs_max_component_error_m": upload_error, "source_fit_weight_lbs_max_component_error_m": source_upload_error, "maximum_positive_bones_per_vertex": max(map(len, source_rows.values())), "signed_mapping_rows": sum(any(w < 0 for w in row["coefficients"]) for row in source.mapping)}, "region": {"source_ids": sorted(region), "incident_triangles": len(selected), "metrics": region_metrics(rest, posed, selected, region, core)}, "scale_ratios": scales, "core_trace": trace, "scope": "same-frame CPU source/upload reconstruction; not GPU, collision, penetration depth, visual approval or a candidate fix"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", type=Path, required=True)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--captures", type=Path, help="existing experiment60 30 deep keyframes")
    selection.add_argument("--frame", type=Path, help="one experiment60 native/Web record (.json or .gz)")
    parser.add_argument("--torso", type=float)
    parser.add_argument("--jaw", type=float)
    parser.add_argument("--clip", choices=CLIPS)
    parser.add_argument("--seconds", type=float)
    parser.add_argument("--fail-on-shoulder-stretch", action="store_true", help="exit3 if any target area/rest exceeds fixed diagnostic10; not quality acceptance")
    parser.add_argument("--out", type=Path, required=True, help="new output directory; never overwrite")
    args = parser.parse_args()
    source = Source(args.asset_root)
    if args.frame:
        require(all(x is not None for x in (args.torso, args.jaw, args.clip, args.seconds)), "single frame requires independently specified torso/jaw/clip/seconds")
        inputs = [(args.frame, {"torso_length": args.torso, "jaw_drop": args.jaw, "clip_id": args.clip, "seconds": args.seconds})]
    else:
        inputs = [(args.captures / f"t{torso:+g}__{clip}__k{k:02}.json.gz", {"torso_length": torso, "jaw_drop": 0.0, "clip_id": clip, "seconds": k / 8}) for torso in (-1.0, 0.0, 1.0) for clip in CLIPS for k in (0, 8, 16, 24, 32)]
    args.out.mkdir(parents=True, exist_ok=False)
    results = []
    failures = []
    for path, expected in inputs:
        try:
            record, digest = read_record(path)
            result = analyze(record, source, expected)
            result["input_sha256"] = digest
            result["input_name"] = path.name
            results.append(result)
        except (ValueError, KeyError, TypeError, IndexError, OSError) as error:
            failures.append({"input_name": path.name, "expected": expected, "error": str(error)})
    stretch = [r["expected"] for r in results if r["geometry"]["posed_over_fitted_rest_area"] > 10]
    output = {"schema_version": 1, "source_manifest_sha256": MANIFEST_SHA, "source_file_sha256": source.hashes, "analyzer_sha256": sha(Path(__file__).read_bytes()), "unchanged_fk_support_sha256": source.support_hashes, "frames": results, "failures": failures, "expected_frames": len(inputs), "reconstruction_verified": len(results) == len(inputs) and not failures, "diagnostic_stretch_over10": stretch, "diagnostic_threshold_scope": "fixed historical symptom selector; not appearance acceptance", "candidate": "NONE; source-limited diagnosis, no correction applied", "garment_quality": "HOLD", "scope": "bounded same-frame CPU evidence only; old captures do not prove current-head runtime or pixels"}
    (args.out / "report.json").write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"reconstruction_verified": output["reconstruction_verified"], "frames": len(results), "failures": len(failures), "garment_quality": "HOLD"}))
    if not output["reconstruction_verified"]:
        return 2
    return 3 if args.fail_on_shoulder_stretch and stretch else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, TypeError, IndexError, OSError) as error:
        print(json.dumps({"reconstruction_verified": False, "error": str(error)}))
        raise SystemExit(2)
