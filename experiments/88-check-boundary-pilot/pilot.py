#!/usr/bin/env python3
"""Local, non-gating historical admission / archived v1 geometry pilot."""
import argparse
import copy
import datetime
import gzip
import hashlib
import importlib
import json
import math
from pathlib import Path
import platform
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CATALOGUE_SHA256 = "c3f0d91d735b032b4806c87f87f8f0c82965b0cd12abdb5c41ddbebee36648c3"
MAX_INPUT = 64 * 1024 * 1024


class Rejected(ValueError):
    def __init__(self, stage, message):
        self.stage = stage
        super().__init__(message)


def need(condition, stage, message):
    if not condition:
        raise Rejected(stage, message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(path):
    return sha(Path(path).read_bytes())


def strict_json(raw):
    def pairs(rows):
        result = {}
        for key, value in rows:
            need(key not in result, "decode", "duplicate JSON key")
            result[key] = value
        return result
    def number(text):
        value = float(text)
        need(math.isfinite(value), "decode", "nonfinite JSON number")
        return value
    def invalid(text):
        raise Rejected("decode", "nonfinite JSON constant")
    return json.loads(raw, object_pairs_hook=pairs, parse_float=number, parse_constant=invalid)


def read_frame(path):
    path = Path(path)
    need(path.is_file() and not path.is_symlink(), "admission", "frame is missing or not a regular file")
    need(path.stat().st_size <= MAX_INPUT, "decode", "compressed input exceeds bound")
    if path.suffix == ".gz":
        with gzip.open(path, "rb") as stream:
            raw = stream.read(MAX_INPUT + 1)
    else:
        raw = path.read_bytes()
    need(len(raw) <= MAX_INPUT, "decode", "decoded input exceeds bound")
    return strict_json(raw)


def load_catalogue():
    path = HERE / "catalogue.json"
    need(digest(path) == CATALOGUE_SHA256, "source_closure", "pilot catalogue changed")
    return strict_json(path.read_bytes())


def verify_closure(catalogue):
    for relative, expected in catalogue["closure"].items():
        path = ROOT / relative
        need(path.is_file() and not path.is_symlink() and digest(path) == expected,
             "source_closure", "pinned helper/source identity changed: " + relative)
    need(digest(ROOT / catalogue["asset_root"] / "manifest.json") == catalogue["asset_manifest_sha256"],
         "source_closure", "v1 asset manifest changed")


def load_helpers(catalogue):
    verify_closure(catalogue)
    sys.path.insert(0, str(ROOT / "experiments/84-shoulder-rest-refit/evaluation"))
    evaluator = importlib.import_module("evaluate_rest")
    module_paths = {
        "evaluate_rest": "experiments/84-shoulder-rest-refit/evaluation/evaluate_rest.py",
        "evaluate_patch": "experiments/81-shoulder-patch-corrective/evaluate_patch.py",
        "author_patch": "experiments/81-shoulder-patch-corrective/author_patch.py",
        "derive_target": "experiments/79-shoulder-pose-corrective/derive_target.py",
        "map_notch": "experiments/79-shoulder-pose-corrective/map_notch.py",
        "collect": "experiments/84-shoulder-rest-refit/replay/collect.py",
        "diagnose": "experiments/70-b1-garment-defect/diagnose.py",
        "checker": "experiments/60-b1-continuous-motion/checker.py",
        "geometry": "experiments/60-b1-continuous-motion/geometry.py",
    }
    for name, relative in module_paths.items():
        need(name in sys.modules and Path(sys.modules[name].__file__).resolve() == ROOT / relative,
             "source_closure", "unexpected imported helper: " + name)
    need(evaluator.SOURCE.resolve() == ROOT / catalogue["asset_root"], "source_closure", "helper is not v1-source-explicit")
    need(evaluator.REST_BOUND == 1e-7 and evaluator.POSED_BOUND == 1e-5,
         "source_closure", "existing numerical bounds changed")
    return evaluator, evaluator.corpus.diagnose


def expected_case(catalogue, name):
    need(name in catalogue["available_current_frames"], "admission", "case is outside the independent available30 catalogue")
    return catalogue["available_current_frames"][name]


def admit_current(path, name, catalogue):
    entry = expected_case(catalogue, name)
    need(Path(path).is_file() and not Path(path).is_symlink(), "admission", "current frame missing/unsafe")
    need(Path(path).stat().st_size <= MAX_INPUT, "decode", "compressed input exceeds bound")
    need(digest(path) == entry["sha256"], "admission", "current frame hash mismatch; payload controls must be explicitly derived after admission")
    return read_frame(path), entry["expected"]


def source_bone_order(rig):
    order = []
    def visit(name):
        need(name not in order, "topology", "source rig cycle")
        order.append(name)
        for child in sorted(n for n, row in rig.items() if row["parent"] == name):
            visit(child)
    roots = sorted(n for n, row in rig.items() if not row["parent"])
    need(len(roots) == 1, "topology", "source rig root differs")
    visit(roots[0])
    need(len(order) == len(rig), "topology", "source rig incomplete")
    return order


class GeometryValidator:
    """Actually called by geometry CLI and derived-payload controls alike."""
    def __init__(self, catalogue):
        self.catalogue = catalogue
        self.e, self.d = load_helpers(catalogue)
        self.source = self.d.Source(ROOT / catalogue["asset_root"])
        self.checker = self.e.corpus.Checker(ROOT / "assets", surfaces=False)
        self.mapping = self.e.parse_mapping((ROOT / catalogue["asset_root"] / "garment/female_sportsuit01.mhclo").read_bytes())
        self.topology = strict_json((ROOT / "experiments/85-current19-shoulder-refit/topology-reference.json").read_bytes())["parts"]
        self.bone_order = source_bone_order(self.source.rig)
        self.cache = {}
        self.rest_identities = {}
        self.source_identity = sha(json.dumps({"closure": catalogue["closure"],
            "asset_manifest": catalogue["asset_manifest_sha256"]}, sort_keys=True).encode())
        self.asset_hashes = self.source.hashes

    def validate(self, record, expected):
        # This pilot's available full captures and unchanged raw_cage helper
        # support jaw0 only. No inferred geometry for jaw endpoints or v2.
        need(set(expected) == {"torso_length", "jaw_drop", "clip_id", "seconds", "k"}
             and type(expected["torso_length"]) in (int, float) and expected["torso_length"] in (-1, 0, 1)
             and type(expected["jaw_drop"]) in (int, float) and expected["jaw_drop"] == 0,
             "binding", "unsupported independently expected v1/jaw0 recipe")
        try:
            need(record.get("kind") == "matrix", "binding", "only original experiment60 matrix schema admitted")
            snapshot = self.d.validate_binding(record, expected)
            need(set(snapshot["parameters"]) == {"torso_length", "jaw_drop"}, "binding", "broader profile parameters are not admitted")
            need(snapshot["backend"] == {"type": "b1_cpu", "schema_version": 2, "asset_id": self.d.ASSET_ID},
                 "binding", "unsupported character backend")
        except ValueError as error:
            if isinstance(error, Rejected):
                raise
            raise Rejected("binding", str(error)) from error
        parts = {part["name"]: part for part in snapshot["parts"]}
        names = [bone["name"] for bone in snapshot["bones"]]
        need(names == self.bone_order and {b["name"]: b["parent"] for b in snapshot["bones"]}
             == {n: row["parent"] or None for n, row in self.source.rig.items()}, "topology", "exact source bone support/order/parents differ")
        for name, count in (("body", 19158), ("garment", 1797)):
            part = parts[name]
            for field in ("source_ids", "indices"):
                expected_topology = self.topology[name][field]
                raw = json.dumps(part[field], separators=(",", ":"), allow_nan=False).encode()
                need(all(type(value) is int for value in part[field]) and len(part[field]) == expected_topology["length"]
                     and sha(raw) == expected_topology["sha256"], "topology", "exact integer topology differs: " + name + "/" + field)
            try:
                for field in ("positions", "rest_positions", "full_joint_influences"):
                    self.d.unique(part, field, count)
                need(all([joint for joint, _ in row] == sorted(joint for joint, _ in row)
                         for row in part["full_joint_influences"]), "topology", "full-positive influence row order differs")
            except ValueError as error:
                if isinstance(error, Rejected):
                    raise
                raise Rejected("topology", str(error)) from error
        # Preserve85's exact cross-pose contract without its v2 Baseline.
        # This detects changing rest state; it is not an absolute rig oracle.
        rest_identity = {"bones": [{key: bone[key] for key in (
            "name", "parent", "rest", "inverse_bind", "canonical_rest", "frame_gauge", "local_rest")}
            for bone in snapshot["bones"]], "parts": [{key: parts[name][key] for key in (
            "name", "source_ids", "indices", "rest_positions", "rest_normals", "full_joint_influences",
            "model_to_world", "display_transform")} for name in ("body", "garment")]}
        identity_key = (self.source_identity, snapshot["profile_id"],
                        tuple((key, expected[key]) for key in ("torso_length", "jaw_drop")))
        if identity_key in self.rest_identities:
            need(self.rest_identities[identity_key] == rest_identity, "cross_pose_rest_identity",
                 "exact fitted bone/rest/normal/weight/placement identity changed across poses")
        try:
            # Retain70's full signed-source/normalized-weight/upload checks,
            # and its conditional FK/gauge/IBM guards, without its exact scalar.
            garment_analysis = self.d.analyze(record, self.source, expected)
            skins, fk, heads, bind = self.e.corpus.check_bones(snapshot["bones"], expected["clip_id"], expected["seconds"])
            recipe = {key: expected[key] for key in ("torso_length", "jaw_drop")}
            cache_key = tuple(recipe.items())
            if cache_key not in self.cache:
                self.cache[cache_key] = self.e.reconstruct_source(self.mapping, recipe)[0]
            rest = self.cache[cache_key]
            checks = {}
            for name in ("body", "garment"):
                part = parts[name]
                checks[name] = self.e.check_baseline_part(part, [rest[name][sid] for sid in part["source_ids"]],
                                                        snapshot["bones"], self.checker, names, skins, name)
        except ValueError as error:
            raise Rejected("numerical_reconstruction", str(error)) from error
        if identity_key not in self.rest_identities:
            # Freeze only a fully successful frame; never alias mutable payloads.
            self.rest_identities[identity_key] = copy.deepcopy(rest_identity)
        return {"expected": expected, "parts": checks, "garment_signed_source": garment_analysis["reconstruction"],
                "conditional_fk": {"max_matrix_component_error": fk, "max_head_error_m": heads, "max_bind_identity_residual": bind},
                "area_ratio_diagnostic_only": garment_analysis["geometry"]["posed_over_fitted_rest_area"],
                "cross_pose_rest_identity": "EXACT_WITHIN_AUTHENTICATED_PROFILE_RECIPE_SOURCE_CLOSURE",
                "full_current_runtime": "NOT_VERIFIED_RIG_ORACLE"}


def payload_fault(record, name):
    """Derived payload control after valid admission; not a production mutant."""
    record = copy.deepcopy(record)
    garment = next(part for part in record["snapshot"]["parts"] if part["name"] == "garment")
    if name == "recipe":
        record["request"]["torso_length"] = 1 if record["request"]["torso_length"] == 0 else 0
    elif name == "time":
        sample = record["snapshot"]["sample"]
        sample["source_seconds"] = 1 if sample["source_seconds"] == 0 else 0
    elif name == "profile":
        record["snapshot"]["profile_id"] = "nvwa-mpfb-b1-motion-v2"
    elif name == "topology":
        garment["indices"][0], garment["indices"][1] = garment["indices"][1], garment["indices"][0]
    else:
        for index, sid in enumerate(garment["source_ids"]):
            if sid != 246:
                continue
            if name in ("rest", "upload"):
                garment["rest_positions" if name == "rest" else "positions"][index][0] += .01
            elif name == "weights":
                garment["full_joint_influences"][index][0][1] *= 1.5
            elif name == "support":
                garment["full_joint_influences"][index] = garment["full_joint_influences"][index][1:]
    return record


def historical(path, catalogue, source):
    expected = catalogue["historical"]
    result = {"status": "BLOCKED_MISSING_HISTORICAL_INPUT", "replay": "NOT-RUN_IDENTITY_ADMISSION_ONLY",
              "historical13": "preserved historical record; not re-executed", "current18": "unchanged suite; not executed by this pilot",
              "expected_input_sha256": expected["sha256"], "expected_case": expected["expected"]}
    if not path.exists():
        return result, 2
    need(path.is_file() and not path.is_symlink() and path.suffix == ".gz", "historical_admission", "historical input must be original regular gzip")
    need(path.stat().st_size <= MAX_INPUT, "historical_admission", "historical gzip exceeds bound")
    need(digest(path) == expected["sha256"], "historical_admission", "historical gzip identity differs; substitutes are prohibited")
    record = read_frame(path)
    source.d.validate_binding(record, expected["expected"])
    result["status"] = "PASS_HISTORICAL_IDENTITY_ADMISSION_ONLY"
    result["asset_manifest_sha256"] = source.asset_hashes["manifest.json"]
    return result, 0


def base_report(catalogue):
    return {"schema_version": 1, "kind": "local-non-gating-check-boundary-pilot", "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "catalogue_sha256": CATALOGUE_SHA256, "pilot_py_sha256": digest(__file__), "helper_closure": catalogue["closure"],
            "capture_source_commit": catalogue["source_commit"], "capture_source_tree": catalogue["source_tree"],
            "capture_run_id": catalogue["source_run_id"], "matrix_binary_sha256": catalogue["matrix_binary_sha256"],
            "analysis_python": sys.version, "python_optimization": sys.flags.optimize,
            "analysis_host": {"system": platform.system(), "machine": platform.machine()},
            "scope": "offline archived capture geometry only; no fresh production, platform, GPU, quality or gate acceptance",
            "full_current_runtime": "NOT_VERIFIED_RIG_ORACLE", "quality": "HOLD", "issue3": "BLOCKED", "issue4": "existing gaps retained",
            "original_linux_control": {"normal": "FAIL_18_CONTROLS_2_FAILURES", "optimized": "NOT-RUN"},
            "production_source_mutations": "NOT-PERFORMED_BY_THIS_PILOT"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("historical", "geometry"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--frame", type=Path)
    parser.add_argument("--captures", type=Path)
    parser.add_argument("--case", help="independent catalogue case name; omit for all available30")
    parser.add_argument("--control-fault", choices=("recipe", "time", "profile", "topology", "rest", "upload", "weights", "support"))
    args = parser.parse_args(argv)
    need(not args.out.exists(), "output", "refuse to overwrite existing evidence")
    catalogue = load_catalogue()
    report = base_report(catalogue)
    report["action"] = args.action
    report["frames"] = []
    report["attempted_cases"] = []
    if args.action == "historical":
        report["replay"] = "NOT-RUN_IDENTITY_ADMISSION_ONLY"
        report["historical13"] = "preserved historical record; not re-executed"
        report["current18"] = "unchanged suite; not executed by this pilot"
        report["capture_source_commit"] = None
        report["capture_source_tree"] = None
        report["capture_run_id"] = None
        report["matrix_binary_sha256"] = None
        report["historical_product_candidate_report_label"] = catalogue["historical"]["reported_product_candidate"]
        report["historical_provenance_limit"] = "original full input absent in available archive; no captured source/binary execution identity authenticated by this pilot"
    started = time.monotonic()
    code = 1
    try:
        validator = GeometryValidator(catalogue)
        report["asset_hashes"] = validator.asset_hashes
        if args.action == "historical":
            need(args.frame is not None and args.captures is None and args.case is None and args.control_fault is None,
                 "arguments", "historical requires only --frame and --out")
            result, code = historical(args.frame, catalogue, validator)
            report.update(result)
        else:
            need(args.captures is not None and args.frame is None, "arguments", "geometry requires --captures and optional independent --case")
            need(args.control_fault is None or args.case is not None, "arguments", "derived control requires one explicit case")
            cases = [args.case] if args.case else sorted(catalogue["available_current_frames"])
            if args.case is None:
                actual = {path.name for path in args.captures.glob("*.json.gz")}
                need(actual == set(cases), "admission", "full available30 directory inventory differs")
            report["expected_case_count"] = len(cases)
            report["input_kind"] = "DERIVED_PAYLOAD_CONTROL_NOT_PRODUCTION_MUTATION" if args.control_fault else "AUTHENTICATED_ARCHIVED_CAPTURE"
            report["control_fault"] = args.control_fault
            report["full_geometry_missing"] = catalogue["missing_full_geometry"]
            for case in cases:
                frame_started = time.monotonic()
                record, expected = admit_current(args.captures / case, case, catalogue)
                if args.control_fault:
                    record = payload_fault(record, args.control_fault)
                report["attempted_cases"].append({"case": case, "expected": expected,
                    "admitted_template_sha256": catalogue["available_current_frames"][case]["sha256"],
                    "derived_payload_sha256": sha(json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()) if args.control_fault else None})
                result = validator.validate(record, expected)
                result.update(case=case, input_sha256=catalogue["available_current_frames"][case]["sha256"], elapsed_seconds=time.monotonic()-frame_started)
                report["frames"].append(result)
            report["status"] = "PASS_LIMITED_CURRENT_GEOMETRY"
            code = 0
        verify_closure(catalogue)
        report["source_closure_after"] = "VERIFIED"
    except (Rejected, ValueError, KeyError, TypeError, OSError, EOFError) as error:
        code = 1
        report["status"] = "FAIL_HISTORICAL_ADMISSION" if args.action == "historical" else "FAIL_CURRENT_GEOMETRY"
        report["failure_stage"] = getattr(error, "stage", "input_or_schema")
        text = str(error) if not isinstance(error, OSError) else type(error).__name__
        for private_path in (ROOT, args.frame, args.captures, args.out):
            if private_path:
                text = text.replace(str(private_path), "<local-path>")
        report["error"] = text
    report["completed_frame_count"] = len(report["frames"])
    report["exit_code"] = code
    report["elapsed_seconds"] = time.monotonic()-started
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({key: report.get(key) for key in ("status", "failure_stage", "error", "completed_frame_count", "elapsed_seconds", "exit_code", "full_current_runtime")}))
    return code


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Rejected, OSError, ValueError) as error:
        print("PILOT_REJECTED: " + (str(error) if not isinstance(error, OSError) else type(error).__name__), file=sys.stderr)
        raise SystemExit(1)
