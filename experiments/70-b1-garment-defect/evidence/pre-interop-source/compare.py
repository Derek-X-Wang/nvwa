#!/usr/bin/env python3
"""Compare two actual same-request experiment60 records; CPU evidence only."""
import argparse
import json
from pathlib import Path
from diagnose import Source, analyze, component_error, point, read_record, require, sha, unique, CLIPS
import diagnose


def compare(left, right, source, expected):
    # Analyze both independently first; two identically stale/corrupt records cannot pass.
    a, b = analyze(left, source, expected), analyze(right, source, expected)
    lp = next(p for p in left["snapshot"]["parts"] if p["name"] == "garment")
    rp = next(p for p in right["snapshot"]["parts"] if p["name"] == "garment")
    local = stage = rest = 0.0
    for field in ("positions", "rest_positions"):
        x, y = unique(lp, field, 1797), unique(rp, field, 1797)
        error = max(component_error(x[i], y[i]) for i in x)
        if field == "positions":
            local = error
            stage = max(component_error(point(lp["display_transform"], x[i]), point(rp["display_transform"], y[i])) for i in x)
        else:
            rest = error
    lb, rb = left["snapshot"]["bones"], right["snapshot"]["bones"]
    require([x["name"] for x in lb] == [x["name"] for x in rb], "bone order differs")
    bones = max(component_error(x["skin"], y["skin"]) for x, y in zip(lb, rb))
    require(local <= 1e-5 and stage <= 1e-5 and rest <= 1e-5 and bones <= 1e-4, "CPU parity failed")
    return {"expected": expected, "left_identity": a["identity"], "right_identity": b["identity"], "garment_source_vertices": 1797, "maximum_local_position_difference_m": local, "maximum_stage_position_difference_m": stage, "maximum_rest_difference_m": rest, "maximum_skin_matrix_difference": bones, "left_geometry": a["geometry"], "right_geometry": b["geometry"], "parity_verified": True, "scope": "actual CPU records only; not GPU, pixels, collision or garment quality acceptance"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--left", type=Path, required=True)
    parser.add_argument("--right", type=Path, required=True)
    parser.add_argument("--torso", type=float, required=True)
    parser.add_argument("--jaw", type=float, required=True)
    parser.add_argument("--clip", choices=CLIPS, required=True)
    parser.add_argument("--seconds", type=float, required=True)
    parser.add_argument("--out", type=Path, required=True, help="new JSON report, never overwrite")
    args = parser.parse_args()
    left, lh = read_record(args.left)
    right, rh = read_record(args.right)
    source = Source(args.asset_root)
    result = compare(left, right, source, {"torso_length": args.torso, "jaw_drop": args.jaw, "clip_id": args.clip, "seconds": args.seconds})
    result.update({"left_input_sha256": lh, "right_input_sha256": rh, "source_manifest_sha256": source.hashes["manifest.json"], "unchanged_fk_support_sha256": source.support_hashes, "analyzer_sha256": sha(Path(diagnose.__file__).read_bytes()), "comparator_sha256": sha(Path(__file__).read_bytes())})
    with args.out.open("x") as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"parity_verified": True, "garment_quality": "HOLD"}))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, IndexError, OSError) as error:
        print(json.dumps({"parity_verified": False, "error": str(error)}))
        raise SystemExit(2)
