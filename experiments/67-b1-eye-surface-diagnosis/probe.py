"""Small stdlib CPU ray candidates from existing captures; never GPU evidence."""
import argparse
import hashlib
import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONTACT_M = 1e-4
AREA2_MIN = 1e-14
PARALLEL_REL = 1e-12
BARY_EPS = 1e-9
RAY_MIN_M = 1e-9
TIE_M = 1e-8
BOUNDARY_EPS = 1e-7
TRIANGLE_ORDINALS = (0, 28, 56, 85)
SIDE_RANGES = {"source_left": (14598, 14669), "source_right": (14670, 14741)}
EXPECTED = {
    "native/sf": "9fb2027bb0f9f340157475a04f8d10ef6ad9d2895b7221da87f8b5603859f6e9",
    "native/lf": "8a2bb0cf92e82bfecedebab72266985a18b29df00a300bf18b6c0c22e6483717",
    "native/sq": "8a011ae05eba206e63dbe3df75cb79b7cd5e8fb0e3cae889dbe996479dd27024",
    "native/lq": "5803da8fab30cb9e5cfc7f46cb1e8cd1839897c52d6bbbe25d0f4334e53b6041",
    "web/sf": "35a0a550633813468caf757916498937bfad73361fd64cc166f3ce15228926b3",
    "web/lf": "12166598be7e93cc831371e0df949fbd4d6b6b24cb430d180af0fd2669f96c04",
    "web/sq": "50a2ae55af4686e35ab9e80424989a7cf79c8f1a90a58ae2cdef1a04c213c7fb",
    "web/lq": "dc25611ccde014d15374d6d1c56d35b82ea163ae093519f1cde4533a26fabc70",
}
BASE = "assets/characters/mpfb-b1-v1/base.obj"
EYE = "assets/appearances/mpfb-b1-cc0-v1/eyes/low-poly/low-poly.obj"
MAP = "assets/appearances/mpfb-b1-cc0-v1/eyes/low-poly/low-poly.mhclo"
SOURCE_FILES = (BASE, EYE, MAP,
    "assets/characters/mpfb-b1-v1/body.mhclo",
    "assets/characters/mpfb-b1-v1/vertex_groups.json",
    "crates/nvwa-runtime/src/b1.rs", "crates/nvwa-runtime/src/stage.rs",
    "experiments/65-b1-appearance-quality/preview/src/accessory.rs",
    "experiments/65-b1-appearance-quality/preview/src/lib.rs", "Cargo.lock")


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def semantic_sha(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":"),
                          allow_nan=False).encode())


def finite(values):
    return all(isinstance(x, (int, float)) and not isinstance(x, bool)
               and math.isfinite(x) for x in values)


def vec(v):
    require(isinstance(v, (list, tuple)) and len(v) == 3 and finite(v),
            "finite vec3 required")
    return tuple(v)


def sub(a, b):
    return tuple(a[i] - b[i] for i in range(3))


def dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def length(v):
    return math.sqrt(dot(v, v))


def unit(v):
    v = vec(v)
    n = length(v)
    require(n > RAY_MIN_M, "zero ray direction")
    return tuple(x / n for x in v)


def matrix(m):
    require(isinstance(m, (list, tuple)) and len(m) == 16 and finite(m),
            "finite column-major matrix required")
    require(max(abs(m[i]-v) for i, v in zip((3, 7, 11, 15), (0, 0, 0, 1))) < 1e-9,
            "affine matrix required")
    a, b, c = [tuple(m[j*4+i] for i in range(3)) for j in range(3)]
    det = dot(a, cross(b, c))
    require(abs(det) > 1e-12, "singular affine matrix")
    return tuple(m)


def point(m, p):
    return tuple(sum(m[j*4+i]*p[j] for j in range(3)) + m[12+i] for i in range(3))


def inverse_point(m, p):
    a, b, c = [tuple(m[j*4+i] for i in range(3)) for j in range(3)]
    det = dot(a, cross(b, c))
    q = sub(p, m[12:15])
    return tuple(dot(row, q)/det for row in (cross(b, c), cross(c, a), cross(a, b)))


def obj(text):
    positions, triangles, group, face_id = [], [], None, 0
    for line_no, line in enumerate(text.splitlines(), 1):
        fields = line.split()
        if not fields or fields[0].startswith("#"):
            continue
        if fields[0] == "v":
            positions.append(vec([float(x) for x in fields[1:]]))
        elif fields[0] == "g":
            group = " ".join(fields[1:])
        elif fields[0] == "f":
            require(len(fields) == 5, "source quad required")
            ids = [int(x.split("/")[0])-1 for x in fields[1:]]
            require(all(0 <= i < len(positions) for i in ids), "source vertex index range")
            for local, order in enumerate(((0, 1, 2), (0, 2, 3))):
                triangles.append({"source_vertex_ids": [ids[i] for i in order],
                    "source_face_ordinal": face_id, "source_obj_line": line_no,
                    "triangle_in_quad": local, "group": group})
            face_id += 1
    require(positions and triangles, "empty source OBJ")
    return positions, triangles


def eye_mapping(text):
    require("delete_verts" not in text, "unexpected eye deletion rule")
    lines = text.splitlines()
    start = lines.index("verts 0") + 1
    rows = [int(line.strip()) for line in lines[start:] if line.strip() and not line.startswith("#")]
    require(len(rows) == 96 and len(set(rows)) == 96, "96 unique direct eye rows required")
    require(all(any(lo <= i <= hi for lo, hi in SIDE_RANGES.values()) for i in rows),
            "eye row outside named helper domains")
    return rows


def selection(triangles, mapping):
    require(len(triangles) == 172, "172 source eye triangles required")
    result = []
    for side, (lo, hi) in SIDE_RANGES.items():
        side_vertices = sorted((helper, i) for i, helper in enumerate(mapping) if lo <= helper <= hi)
        side_triangles = [(i, t) for i, t in enumerate(triangles)
                          if all(lo <= mapping[j] <= hi for j in t["source_vertex_ids"])]
        require(len(side_vertices) == 48 and len(side_triangles) == 86,
                "expected fixed side coverage")
        for ordinal in TRIANGLE_ORDINALS:
            i, t = side_triangles[ordinal]
            ids = t["source_vertex_ids"]
            result.append({"probe_id": f"{side}/triangle-{ordinal}", "kind": "triangle_centroid",
                "side": side, "source_triangle_ordinal": i,
                "source_vertex_ids": ids, "helper_ids": [mapping[j] for j in ids]})
        for label, (helper, i) in zip(("min", "max"), (side_vertices[0], side_vertices[-1])):
            result.append({"probe_id": f"{side}/helper-{label}", "kind": "source_vertex",
                "side": side, "source_vertex_ids": [i], "helper_ids": [helper]})
    require(len(result) == 12, "fixed 12 probe selection required")
    return result


def indexed_mesh(positions, indices, labels):
    positions = [vec(p) for p in positions]
    require(len(indices) % 3 == 0 and len(labels) == len(indices)//3, "triangle label coverage")
    require(all(isinstance(i, int) and not isinstance(i, bool) and 0 <= i < len(positions)
                for i in indices), "render vertex index range")
    triangles = []
    for ordinal, label in enumerate(labels):
        ids = indices[ordinal*3:ordinal*3+3]
        a, b, c = [positions[i] for i in ids]
        e1, e2 = sub(b, a), sub(c, a)
        area = length(cross(e1, e2))
        require(area > AREA2_MIN, "degenerate triangle")
        triangles.append((a, e1, e2, PARALLEL_REL*length(e1)*length(e2),
                          {**label, "render_triangle_ordinal": ordinal}))
    return triangles


def intersect(origin, direction, triangle):
    a, e1, e2, det_eps, label = triangle
    p = cross(direction, e2)
    det = dot(e1, p)
    if abs(det) <= det_eps:
        return None
    tvec = sub(origin, a)
    u = dot(tvec, p)/det
    if u < -BARY_EPS or u > 1+BARY_EPS:
        return None
    q = cross(tvec, e1)
    v = dot(direction, q)/det
    if v < -BARY_EPS or u+v > 1+BARY_EPS:
        return None
    distance = dot(e2, q)/det
    if distance <= RAY_MIN_M:
        return None
    bary = [1-u-v, u, v]
    return {"ray_distance_m": distance, "barycentric": bary,
            "boundary": min(bary) <= BOUNDARY_EPS,
            "winding_normal_toward_camera": det > 0,
            "world_point_m": [origin[i]+distance*direction[i] for i in range(3)], **label}


def intersections(origin, direction, triangles):
    hits = [h for triangle in triangles if (h := intersect(origin, direction, triangle)) is not None]
    return sorted(hits, key=lambda h: (h["ray_distance_m"], h["render_triangle_ordinal"]))


def nearest(hits, front_only=False):
    hits = [h for h in hits if not front_only or h["winding_normal_toward_camera"]]
    if not hits:
        return None
    minimum = hits[0]["ray_distance_m"]
    return {"ray_distance_m": minimum,
            "ties": [h for h in hits if h["ray_distance_m"]-minimum <= TIE_M]}


def ordering(body, eyes):
    if body is None or eyes is None:
        return {"classification": "missing_intersection", "body_minus_eye_m": None}
    delta = body["ray_distance_m"] - eyes["ray_distance_m"]
    return {"classification": ("within_contact_band" if abs(delta) <= CONTACT_M else
                               "body_first" if delta < 0 else "eye_first"),
            "body_minus_eye_m": delta}


def source_mesh_labels(body, source_triangles):
    by_ids = {}
    for t in source_triangles:
        if t["group"] != "body":
            continue
        key = tuple(t["source_vertex_ids"])
        require(key not in by_ids, "duplicate body source triangle")
        by_ids[key] = t
    ids, indices = body["source_ids"], body["indices"]
    require(len(ids) == len(body["positions"]) == 22077, "expected complete body render vertices")
    require(len(indices) == 68676, "expected captured visible body index count")
    require(all(isinstance(i, int) and 0 <= i < 19158 for i in ids)
            and set(ids) == set(range(19158)), "complete body source coverage required")
    require(all(isinstance(i, int) and 0 <= i < len(ids) for i in indices), "body index range")
    labels = []
    for offset in range(0, len(indices), 3):
        key = tuple(ids[i] for i in indices[offset:offset+3])
        require(max(key) < 13380 and key in by_ids, "visible body source triangle mismatch")
        labels.append(by_ids[key])
    order = [(t["source_face_ordinal"], t["triangle_in_quad"]) for t in labels]
    require(order == sorted(set(order)), "body source ordered triangle subsequence required")
    return labels


def capture_record(raw, platform, group, sources, probes):
    key = f"{platform}/{group}"
    require(sha(raw) == EXPECTED[key], "exact raw envelope hash mismatch: " + key)
    envelope = json.loads(raw)
    frame, report = envelope["frame"], envelope["report"]
    require(envelope["request"] == frame["request"] == report["request"], "request correlation mismatch")
    require(frame["geometry_equal"] and frame["geometry_before_sha256"] == frame["geometry_after_sha256"],
            "captured geometry invariance required")
    require(frame["quality"]["selected"] == "frozen64", "reference material control required")
    sample = frame["snapshot"]["sample"]
    require(sample["clip_id"] == "b1_arm_rehearsal_v1" and sample["source_seconds"] == 2
            and sample["playing"] is False, "held source arm 2 seconds required")
    expected_shape = {"torso_length": -1.0, "jaw_drop": 0.0} if group[0] == "s" else {
        "torso_length": 1.0, "jaw_drop": 1.0}
    require(frame["snapshot"]["parameters"] == expected_shape, "capture shape mismatch")
    camera = frame["quality"]["scene_camera"]
    require(camera == frame["appearance"]["observation_camera"] == report["quality"]["scene_camera"],
            "actual camera records disagree")
    require(camera["active"] and camera["viewport_size_pixels"] == [1280, 720]
            and camera["msaa_samples"] == 4, "actual expected camera required")
    camera_matrix = matrix(camera["global_transform"])
    origin = camera_matrix[12:15]
    parts = frame["snapshot"]["parts"]
    body = next(p for p in parts if p["name"] == "body")
    eyes = next(p for p in frame["appearance"]["accessory_runtime"]["accessories"] if p["name"] == "eyes")
    placement = matrix(body["display_transform"])
    require(placement == matrix(eyes["display_transform"]), "body/eye actual placement mismatch")
    require(eyes["model_to_world_record_only"] == body["model_to_world"], "recorded skeleton basis mismatch")
    require(eyes["material"]["cull_mode"] == "Some(Back)" and eyes["material"]["alpha"] == "Mask(0.5)",
            "expected recorded eye material required")
    body_labels = source_mesh_labels(body, sources["base_triangles"])
    mapping = sources["mapping"]
    pairs = eyes["source_uv_pairs"]
    require(len(eyes["positions"]) == len(pairs) == 96 and len(eyes["indices"]) == 516,
            "expected eye render coverage")
    require(all(isinstance(p, list) and len(p) == 2 and all(isinstance(i, int) for i in p)
                and 0 <= p[0] < 96 and p[1] >= 0 for p in pairs), "eye pair domain")
    eye_positions = {}
    for i, pair in enumerate(pairs):
        src = pair[0]
        p = vec(eyes["positions"][i])
        require(src not in eye_positions or eye_positions[src] == p, "eye UV seam position disagreement")
        eye_positions[src] = p
    require(set(eye_positions) == set(range(96)), "full eye source coverage")
    require(all(isinstance(i, int) and 0 <= i < len(pairs) for i in eyes["indices"]), "eye index range")
    eye_ids = [[pairs[i][0] for i in eyes["indices"][j:j+3]] for j in range(0, 516, 3)]
    require(eye_ids == [t["source_vertex_ids"] for t in sources["eye_triangles"]],
            "exact source eye triangle order required")
    cage, posed_cage = {}, {}
    require(len(body["rest_positions"]) == len(body["source_ids"]), "rest cage coverage")
    for src, rest, posed in zip(body["source_ids"], body["rest_positions"], body["positions"]):
        rest, posed = vec(rest), vec(posed)
        require(src not in cage or (cage[src] == rest and posed_cage[src] == posed),
                "duplicated body source disagreement")
        cage[src], posed_cage[src] = rest, posed
    require(len(eyes["rest_model_m"]) == 96, "eye rest coverage")
    rest_error = max(abs(vec(eyes["rest_model_m"][i])[j]-cage[mapping[i]][j]) for i in range(96) for j in range(3))
    posed_error = max(abs(eye_positions[i][j]-posed_cage[mapping[i]][j]) for i in range(96) for j in range(3))
    require(rest_error == 0 and posed_error <= 1e-6, "eye/helper coordinate join mismatch")
    body_world = [point(placement, vec(p)) for p in body["positions"]]
    eye_world = [point(placement, vec(p)) for p in eyes["positions"]]
    recomputed_bounds = {"min": [min(p[j] for p in eye_world) for j in range(3)],
                         "max": [max(p[j] for p in eye_world) for j in range(3)]}
    bounds_error = max(abs(recomputed_bounds[k][j]-eyes["posed_stage_bounds_m"][k][j])
                       for k in ("min", "max") for j in range(3))
    require(bounds_error <= 1e-6, "actual eye stage bounds disagree with single display placement")
    body_tris = indexed_mesh(body_world, body["indices"], body_labels)
    eye_labels = [{**t, "helper_ids": [mapping[i] for i in t["source_vertex_ids"]]}
                  for t in sources["eye_triangles"]]
    eye_tris = indexed_mesh(eye_world, eyes["indices"], eye_labels)
    records = []
    for probe in probes:
        selected = [point(placement, eye_positions[i]) for i in probe["source_vertex_ids"]]
        target = tuple(sum(p[i] for p in selected)/len(selected) for i in range(3))
        view = inverse_point(camera_matrix, target)
        require(view[2] < -0.05, "probe behind camera or inside declared near distance")
        direction = unit(sub(target, origin))
        body_hits = intersections(origin, direction, body_tris)
        eye_hits = intersections(origin, direction, eye_tris)
        target_distance = length(sub(target, origin))
        require(any(abs(h["ray_distance_m"]-target_distance) <= 1e-7 for h in eye_hits),
                "selected eye point not recovered by ray")
        modes = {}
        for mode, front in (("two_sided", False), ("normal_toward_camera_only", True)):
            nb, ne = nearest(body_hits, front), nearest(eye_hits, front)
            modes[mode] = {"nearest_body": nb, "nearest_eye": ne, **ordering(nb, ne)}
        records.append({**probe, "world_target_m": target, "camera_view_target_m": view,
            "world_ray_unit_direction": direction, "target_ray_distance_m": target_distance,
            "selected_target_is_nearest_eye": abs(eye_hits[0]["ray_distance_m"]-target_distance) <= TIE_M,
            "all_positive_body_hit_distances_m": [h["ray_distance_m"] for h in body_hits],
            "all_positive_eye_hit_distances_m": [h["ray_distance_m"] for h in eye_hits], "modes": modes})
    return {"schema": "b1-eye-cpu-ray-candidates-v1", "capture": key,
        "scope": "sparse CPU geometry hypotheses; NOT GPU pixel ownership or quality acceptance",
        "source_envelope": {"sha256": sha(raw), "bytes": len(raw)},
        "request": envelope["request"], "sample": sample, "shape": expected_shape,
        "camera": camera, "body_display_transform": placement,
        "eye_display_transform": eyes["display_transform"],
        "model_to_world_record_not_applied_again": body["model_to_world"],
        "eye_material": eyes["material"],
        "coordinate_validation": {"rest_helper_max_component_error_m": rest_error,
            "posed_helper_max_component_error_m": posed_error,
            "recomputed_eye_stage_bounds_m": recomputed_bounds,
            "captured_eye_stage_bounds_max_component_error_m": bounds_error,
            "body_world_positions_semantic_sha256": semantic_sha(body_world),
            "eye_world_positions_semantic_sha256": semantic_sha(eye_world),
            "body_triangles": len(body_tris), "eye_triangles": len(eye_tris),
            "source_body_triangles_exact_ordered_subsequence": True,
            "source_eye_triangle_sequence_exact": True},
        "probes": records}


def load_sources(repo):
    _, base_triangles = obj((repo/BASE).read_text())
    eye_positions, eye_triangles = obj((repo/EYE).read_text())
    require(len(eye_positions) == 96, "96 original eye vertices required")
    mapping = eye_mapping((repo/MAP).read_text())
    return {"base_triangles": base_triangles, "eye_triangles": eye_triangles, "mapping": mapping}


def run(capture_root, output, repo=REPO):
    sources = load_sources(repo)
    probes = selection(sources["eye_triangles"], sources["mapping"])
    output.mkdir(parents=True, exist_ok=True)
    generated, summaries, all_records = [], [], []
    for key in EXPECTED:
        platform, group = key.split("/")
        name = (f"n65-{group}-reference-envelope.json" if platform == "native" else f"w65-{group}-reference.json")
        path = capture_root/".work"/"appearance79"/("quality-"+platform)/"captures"/name
        record = capture_record(path.read_bytes(), platform, group, sources, probes)
        all_records.append(record)
        counts = {mode: {label: 0 for label in ("body_first", "eye_first", "within_contact_band", "missing_intersection")}
                  for mode in ("two_sided", "normal_toward_camera_only")}
        for probe in record["probes"]:
            for mode, result in probe["modes"].items():
                counts[mode][result["classification"]] += 1
        summaries.append({"capture": key, "counts": counts,
            "selected_target_not_nearest_eye": sum(not p["selected_target_is_nearest_eye"] for p in record["probes"]),
            "two_sided_delta_range_m": [min(p["modes"]["two_sided"]["body_minus_eye_m"] for p in record["probes"]),
                                         max(p["modes"]["two_sided"]["body_minus_eye_m"] for p in record["probes"])]})
        filename = platform+"-"+group+"-probes.json"
        raw = encoded(record)
        (output/filename).write_bytes(raw)
        generated.append({"path": filename, "sha256": sha(raw), "bytes": len(raw)})
    candidates = {}
    for record in all_records:
        for p in record["probes"]:
            result = p["modes"]["two_sided"]
            if result["classification"] != "body_first":
                continue
            for hit in result["nearest_body"]["ties"]:
                key = (hit["source_face_ordinal"], hit["triangle_in_quad"])
                item = candidates.setdefault(key, {k: hit[k] for k in (
                    "source_face_ordinal", "source_obj_line", "triangle_in_quad", "source_vertex_ids")})
                item.setdefault("observations", []).append({"capture": record["capture"],
                    "probe_id": p["probe_id"], "body_minus_eye_m": result["body_minus_eye_m"],
                    "selected_target_is_nearest_eye": p["selected_target_is_nearest_eye"],
                    "body_hit_boundary": hit["boundary"]})
    candidate_record = {"scope": "nearest body-before-eye CPU ray candidates only; anatomical label and GPU ownership UNKNOWN",
        "candidates": [candidates[k] for k in sorted(candidates)],
        "corresponding_platform_probe_records_exact": {
            group: next(r for r in all_records if r["capture"] == "native/"+group)["probes"] ==
                   next(r for r in all_records if r["capture"] == "web/"+group)["probes"]
            for group in ("sf", "lf", "sq", "lq")}}
    raw = encoded(candidate_record)
    (output/"body-first-candidates.json").write_bytes(raw)
    generated.append({"path": "body-first-candidates.json", "sha256": sha(raw), "bytes": len(raw)})
    manifest = {"schema": "b1-eye-cpu-ray-candidates-manifest-v1",
        "scope": "8 existing references; 96 fixed rays; CPU geometry only; cause UNKNOWN",
        "numeric_policy": {"contact_band_m": CONTACT_M, "minimum_doubled_triangle_area_m2": AREA2_MIN,
            "parallel_relative_determinant": PARALLEL_REL, "barycentric_epsilon": BARY_EPS,
            "minimum_positive_ray_m": RAY_MIN_M, "nearest_tie_m": TIE_M,
            "boundary_barycentric_epsilon": BOUNDARY_EPS},
        "fixed_selection": probes, "summary": summaries, "files": generated,
        "sources": [{"path": name, "sha256": sha((repo/name).read_bytes()), "bytes": (repo/name).stat().st_size}
                    for name in SOURCE_FILES],
        "tools": [{"path": name, "sha256": sha((Path(__file__).parent/name).read_bytes())}
                  for name in ("probe.py", "test_probe.py", "README.md")]}
    (output/"manifest.json").write_bytes(encoded(manifest))
    print(json.dumps({"captures": len(summaries), "rays": len(summaries)*len(probes),
                      "summary": summaries}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.capture_root, args.output)
