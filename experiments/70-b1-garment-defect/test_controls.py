#!/usr/bin/env python3
"""Mutation controls through the same analyzer used for actual-frame diagnosis."""
import argparse
import copy
import json
from pathlib import Path
import tempfile
import unittest
import sys
from diagnose import Source, adapt_input, analyze, lbs, read_record, sha, transfer, validate_binding
from compare import compare

parser = argparse.ArgumentParser()
parser.add_argument("--asset-root", type=Path, required=True)
parser.add_argument("--frame", type=Path, required=True, help="actual torso+1/jaw0/arm2 experiment60 record")
args, remaining = parser.parse_known_args()
sys.argv = [sys.argv[0], *remaining]
SOURCE = Source(args.asset_root)
RECORD, _ = read_record(args.frame)
EXPECTED = {"torso_length": 1.0, "jaw_drop": 0.0, "clip_id": "b1_arm_rehearsal_v1", "seconds": 2.0}


class Controls(unittest.TestCase):
    def synthetic68(self):
        # A derived adapter fixture, NOT an actual68 runtime capture.
        frame = {"request_id": "synthetic-68", "endpoint": "native", "full_base": copy.deepcopy(RECORD["snapshot"])}
        frame["full_base"]["sample"]["timeline_id"] = "arms"
        return frame

    def test_actual_retained_witness(self):
        result = analyze(RECORD, SOURCE, EXPECTED)
        self.assertAlmostEqual(result["geometry"]["posed_over_fitted_rest_area"], 22.0056357384, places=6)
        self.assertGreater(result["reconstruction"]["maximum_positive_bones_per_vertex"], 4)

    def test_stale_actual_time_rejected(self):
        record = copy.deepcopy(RECORD)
        record["snapshot"]["sample"]["source_seconds"] = 0
        with self.assertRaisesRegex(ValueError, "stale actual time"):
            validate_binding(record, EXPECTED)

    def test_relabelled_shape_rejected(self):
        record = copy.deepcopy(RECORD)
        record["request"]["jaw_drop"] = 1
        with self.assertRaisesRegex(ValueError, "stale requested shape"):
            validate_binding(record, EXPECTED)

    def test_boolean_numeric_shape_rejected(self):
        record = copy.deepcopy(RECORD)
        record["request"]["jaw_drop"] = False
        record["snapshot"]["parameters"]["jaw_drop"] = False
        with self.assertRaisesRegex(ValueError, "stale requested shape"):
            validate_binding(record, EXPECTED)

    def test_time_relabel_with_matching_metadata_rejected_by_fk(self):
        record = copy.deepcopy(RECORD)
        record["request"].update({"k": 8, "seconds": 1})
        record["snapshot"]["sample"].update({"source_seconds": 1, "position_seconds": 1})
        expected = dict(EXPECTED, seconds=1)
        with self.assertRaisesRegex(ValueError, "FK/gauge/head"):
            analyze(record, SOURCE, expected)

    def test_actual_upload_mutation_rejected(self):
        record = copy.deepcopy(RECORD)
        part = next(p for p in record["snapshot"]["parts"] if p["name"] == "garment")
        for source, p in zip(part["source_ids"], part["positions"]):
            if source == 246:
                p[0] += 0.01
        with self.assertRaisesRegex(ValueError, "LBS/upload mismatch"):
            analyze(record, SOURCE, EXPECTED)

    def test_top4_mutation_rejected(self):
        record = copy.deepcopy(RECORD)
        part = next(p for p in record["snapshot"]["parts"] if p["name"] == "garment")
        for i, row in enumerate(part["full_joint_influences"]):
            part["full_joint_influences"][i] = sorted(row, key=lambda item: -item[1])[:4]
        with self.assertRaisesRegex(ValueError, "bone support mismatch"):
            analyze(record, SOURCE, EXPECTED)

    def test_source_coefficient_mutation_rejected(self):
        source = copy.deepcopy(SOURCE)
        source.mapping[246]["coefficients"] = [1, 0, 0]
        with self.assertRaisesRegex(ValueError, "mismatch"):
            analyze(RECORD, source, EXPECTED)

    def test_signed_aggregation_not_coefficient_clipping(self):
        # 0.75*1 -0.25*0.4 =0.65; second bone's final aggregate is negative.
        row = {"helpers": [0, 1], "coefficients": [0.75, -0.25]}
        weights = {"a": {0: 1.0, 1: 0.4}, "b": {1: 1.0}, "c": {0: 0.2}}
        actual = dict(transfer(row, ["a", "b", "c"], weights))
        self.assertEqual(set(actual), {0, 2})
        self.assertAlmostEqual(actual[0], 0.65 / 0.8)
        self.assertAlmostEqual(actual[2], 0.15 / 0.8)

    def test_column_major_translation_once(self):
        matrix = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 2, 3, 4, 1]
        self.assertEqual(lbs([1, 2, 3], [(0, 1)], [{"skin": matrix}]), [3, 5, 7])

    def test_corrupt_source_manifest_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent, prefix=".control-") as tmp:
            Path(tmp, "manifest.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "manifest SHA mismatch"):
                Source(tmp)

    def test_nonfinite_and_duplicate_json_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent, prefix=".control-") as tmp:
            p = Path(tmp, "record.json")
            for text in ('{"x":NaN}', '{"x":1,"x":2}'):
                p.write_text(text)
                with self.assertRaises(ValueError):
                    read_record(p)

    def test_two_equally_stale_records_cannot_pass_parity(self):
        record = copy.deepcopy(RECORD)
        record["snapshot"]["sample"]["timeline_id"] = "wrong"
        with self.assertRaisesRegex(ValueError, "stale actual clip"):
            compare(record, record, SOURCE, EXPECTED)

    def test_explicit68_timeline_and_input_immutability(self):
        frame = self.synthetic68()
        before = json.dumps(frame, sort_keys=True)
        record = adapt_input(frame, "bridge68")
        self.assertNotIn("request", record)
        result = analyze(record, SOURCE, dict(EXPECTED, timeline_id="arms"))
        self.assertAlmostEqual(result["geometry"]["posed_over_fitted_rest_area"], 22.0056357384, places=6)
        self.assertEqual(before, json.dumps(frame, sort_keys=True))
        self.assertIn("NOT-CHECKED", result["input_binding"]["acknowledgement"])

    def test_default_timeline_does_not_relabel68(self):
        record = adapt_input(self.synthetic68(), "bridge68")
        with self.assertRaisesRegex(ValueError, "stale actual clip/entry"):
            analyze(record, SOURCE, EXPECTED)

    def test68_missing_full_base_rejected(self):
        with self.assertRaisesRegex(ValueError, "full_base snapshot missing"):
            adapt_input({"request_id": "synthetic-68", "base": RECORD["snapshot"]}, "bridge68")

    def test68_unready_and_mismatched_envelopes_rejected(self):
        for report, message in [({"phase": "error"}, "not acknowledged"), ({"phase": "ready", "acknowledged": True, "request_succeeded": True, "current": True, "request_id": "different"}, "capture ID mismatch")]:
            with self.assertRaisesRegex(ValueError, message):
                adapt_input({"frame": self.synthetic68(), "report": report}, "bridge68")

    def test68_positive_envelope_and_full_base_identity_mutation(self):
        # Synthetic protocol fixture only; no new68 runtime observation.
        frame = self.synthetic68()
        snapshot = frame["full_base"]
        frame["base"] = {k: copy.deepcopy(snapshot[k]) for k in ("generation", "revision", "character_entity", "backend", "parameters", "sample")}
        work_json = '{"synthetic_protocol_fixture":true}'
        work_sha = sha(work_json.encode())
        identity = {k: None for k in ("preview_sha256", "pending_open_sha256", "open_error", "runtime_error", "runtime_appearance_error", "appearance_error", "stage_error", "seek_request")}
        identity.update({"generation": snapshot["generation"], "revision": snapshot["revision"], "appearance_ready": True, "runtime_ready": True, "work_sha256": work_sha})
        frame.update({"identity": identity, "work_sha256": work_sha})
        report = {"phase": "ready", "acknowledged": True, "request_succeeded": True, "current": True, "request_id": frame["request_id"], "base": copy.deepcopy(frame["base"]), "captured_identity": copy.deepcopy(identity), "work_json": work_json, "work_sha256": work_sha}
        envelope = {"report": report, "frame": frame}
        result = adapt_input(envelope, "bridge68")
        self.assertIn("matching envelope", result["acknowledgement"])
        snapshot["generation"] += 1
        with self.assertRaisesRegex(ValueError, "compact/full base mismatch"):
            adapt_input(envelope, "bridge68")


if __name__ == "__main__":
    unittest.main()
