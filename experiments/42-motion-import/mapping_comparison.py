"""Integration comparison against independently retained authored JSON bytes."""
import copy
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "docs/evidence/m2-authored-controls/mapping-reference"
BASELINE = ROOT / "experiments/43-rig-mapping"
# Metres/quaternion components and derived metrics may differ at binary64 last
# bits across libm/Python versions. Integers, types, structure and provenance do
# not receive this allowance. Frozen mapper assertions remain unchanged.
ATOL = 1e-13
RTOL = 1e-13


def load(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def nonfinite(value):
        raise ValueError(f"Nonfinite JSON number: {value}")

    return json.loads(Path(path).read_bytes(), object_pairs_hook=pairs,
                      parse_constant=nonfinite)


def compare(actual, expected, path="$", atol=ATOL, rtol=RTOL):
    if type(actual) is not type(expected):
        raise ValueError(f"Type differs at {path}")
    if isinstance(expected, dict):
        if actual.keys() != expected.keys():
            raise ValueError(f"Keys differ at {path}")
        for key in expected:
            compare(actual[key], expected[key], path + "/" + key, atol, rtol)
    elif isinstance(expected, list):
        if len(actual) != len(expected):
            raise ValueError(f"Shape differs at {path}")
        for index, (a, e) in enumerate(zip(actual, expected)):
            compare(a, e, path + "/" + str(index), atol, rtol)
    elif isinstance(expected, float):
        if (not math.isfinite(actual) or not math.isfinite(expected)
                or abs(actual - expected) > atol + rtol * abs(expected)):
            raise ValueError(f"Numeric difference at {path}: {actual} vs {expected}")
    elif actual != expected:
        raise ValueError(f"Value differs at {path}")


def file_check(path, row):
    if (type(row) is not dict or set(row) != {"bytes", "sha256"}
            or type(row["bytes"]) is not int or row["bytes"] < 0
            or type(row["sha256"]) is not str):
        raise ValueError(f"Invalid manifest entry: {path.name}")
    data = path.read_bytes()
    if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
        raise ValueError(f"File digest/size differs: {path.name}")


def compare_mapping(output, reference=REFERENCE, baseline=BASELINE):
    output, reference, baseline = Path(output), Path(reference), Path(baseline)
    expected = load(baseline / "mapping-manifest.json")
    actual = load(output / "mapping-manifest.json")
    names = set(expected["files"])
    if len(names) != 36 or set(actual["files"]) != names:
        raise ValueError("Expected all 36 raw/envelope manifest entries")
    if {p.name for p in output.iterdir()} != names | {"mapping-manifest.json", "metrics.json"}:
        raise ValueError("Generated file set differs")
    if {p.name for p in reference.iterdir()} != names:
        raise ValueError("Reference file set differs")
    for name in names:
        file_check(reference / name, expected["files"][name])
        file_check(output / name, actual["files"][name])
    actual_meta = {k: v for k, v in actual.items() if k != "files"}
    expected_meta = {k: v for k, v in expected.items() if k != "files"}
    compare(actual_meta, expected_meta, "manifest")
    for name in sorted(names):
        generated = load(output / name)
        golden = load(reference / name)
        if name.endswith(".normalized.json"):
            raw_name = name.replace(".normalized.json", ".raw.json")
            raw = load(output / raw_name)
            if generated["provenance"]["raw_sha256"] != actual["files"][raw_name]["sha256"]:
                raise ValueError(f"Raw/envelope digest binding differs: {name}")
            compare({k: v for k, v in generated.items() if k != "provenance"},
                    raw, "pair/" + name, atol=0, rtol=0)
            # The digest is allowed to vary only after its actual-byte binding
            # has been proved above; all other provenance stays exact.
            generated = copy.deepcopy(generated)
            generated["provenance"]["raw_sha256"] = golden["provenance"]["raw_sha256"]
        compare(generated, golden, name)
    compare(load(output / "metrics.json"), load(baseline / "metrics.json"), "metrics")
    return {"portable_files_verified": 36, "pairs_verified": 18,
            "atol": ATOL, "rtol": RTOL,
            "result": "PASS finite numeric tolerance; exact schema/pins/provenance"}
