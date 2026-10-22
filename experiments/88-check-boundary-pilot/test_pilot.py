#!/usr/bin/env python3
"""Real local CLI/payload controls; no Rust production mutation or runtime."""
import argparse
import contextlib
import copy
import gzip
import io
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import pilot as p

parser = argparse.ArgumentParser()
parser.add_argument("--captures", required=True, type=Path)
parser.add_argument("--mac-v1-frame", required=True, type=Path)
parser.add_argument("--mac-v2-frame", required=True, type=Path)
parser.add_argument("--out", required=True, type=Path, help="new private control evidence directory")
args, remaining = parser.parse_known_args()
sys.argv = [sys.argv[0], *remaining]
if args.out.exists():
    parser.error("refuse to overwrite prior controls")
args.out.mkdir(parents=True)
CASE = "t+1__b1_arm_rehearsal_v1__k16.json.gz"


class Controls(unittest.TestCase):
    serial = 0

    def cli(self, action, options):
        Controls.serial += 1
        out = args.out / f"{Controls.serial:02}-{action}.json"
        with contextlib.redirect_stdout(io.StringIO()):
            code = p.main([action, "--out", str(out), *options])
        report = json.loads(out.read_text())
        self.assertEqual(code, report["exit_code"])
        self.assertEqual(report["full_current_runtime"], "NOT_VERIFIED_RIG_ORACLE")
        return code, report

    def geometry(self, fault=None, case=CASE):
        options = ["--captures", str(args.captures), "--case", case]
        if fault:
            options += ["--control-fault", fault]
        return self.cli("geometry", options)

    def test_missing_historical_blocks_without_replay(self):
        code, report = self.cli("historical", ["--frame", str(args.out / "absent-original.gz")])
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "BLOCKED_MISSING_HISTORICAL_INPUT")
        self.assertTrue(report["replay"].startswith("NOT-RUN"))
        self.assertEqual(report["completed_frame_count"], 0)

    def test_known_same_scalar_mac_frames_and_linux_are_not_historical(self):
        for path in (args.mac_v1_frame, args.mac_v2_frame, args.captures / CASE):
            with self.subTest(frame_sha256=p.digest(path)):
                code, report = self.cli("historical", ["--frame", str(path)])
                self.assertEqual(code, 1)
                self.assertEqual(report["failure_stage"], "historical_admission")
                self.assertIn("substitutes are prohibited", report["error"])
                self.assertTrue(report["replay"].startswith("NOT-RUN"))

    def test_corrupt_input_does_not_reach_geometry(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / CASE).write_bytes(b"not a gzip")
            code, report = self.cli("geometry", ["--captures", str(folder), "--case", CASE])
            self.assertEqual(code, 1)
            self.assertEqual(report["failure_stage"], "admission")
            self.assertEqual(report["attempted_cases"], [])

    def test_strict_decoder_and_decoded_bound(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "control.gz"
            for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e9999}'):
                path.write_bytes(gzip.compress(raw))
                with self.assertRaises(ValueError):
                    p.read_frame(path)
            path.write_bytes(gzip.compress(b" " * 1000))
            with patch.object(p, "MAX_INPUT", 100):
                with self.assertRaisesRegex(p.Rejected, "decoded input"):
                    p.read_frame(path)

    def test_unadmitted_jaw_cohort_is_not_fabricated(self):
        code, report = self.cli("geometry", ["--captures", str(args.captures), "--case", "t+1__jaw+1__arm2.json.gz"])
        self.assertEqual(code, 1)
        self.assertEqual(report["failure_stage"], "admission")
        self.assertEqual(report["completed_frame_count"], 0)

    def test_full_available_cohort_missing_or_extra_case_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            code, report = self.cli("geometry", ["--captures", str(folder)])
            self.assertEqual(code, 1)
            self.assertIn("directory inventory differs", report["error"])
            (folder / "unadmitted.json.gz").write_bytes(b"control")
            code, report = self.cli("geometry", ["--captures", str(folder)])
            self.assertEqual(code, 1)
            self.assertEqual(report["completed_frame_count"], 0)

    def test_binding_faults_reach_independent_expected_case_then_restore(self):
        before = p.digest(args.captures / CASE)
        for fault in ("recipe", "time", "profile"):
            with self.subTest(fault=fault):
                code, report = self.geometry(fault)
                self.assertEqual(code, 1)
                self.assertEqual(report["failure_stage"], "binding")
                self.assertEqual(len(report["attempted_cases"]), 1)
                self.assertIsNotNone(report["attempted_cases"][0]["derived_payload_sha256"])
        code, report = self.geometry()
        self.assertEqual(code, 0)
        self.assertEqual(report["completed_frame_count"], 1)
        self.assertEqual(p.digest(args.captures / CASE), before)

    def test_numerical_faults_reach_effective_validator_then_restore(self):
        before = p.digest(args.captures / CASE)
        messages = {"rest": "source/fitted-rest", "upload": "LBS/upload", "weights": "normalized weight", "support": "bone support"}
        for fault, message in messages.items():
            with self.subTest(fault=fault):
                code, report = self.geometry(fault)
                self.assertEqual(code, 1)
                self.assertEqual(report["failure_stage"], "numerical_reconstruction")
                self.assertIn(message, report["error"])
                self.assertEqual(report["input_kind"], "DERIVED_PAYLOAD_CONTROL_NOT_PRODUCTION_MUTATION")
                self.assertEqual(report["attempted_cases"][0]["admitted_template_sha256"], before)
        code, report = self.geometry()
        self.assertEqual(code, 0)
        self.assertEqual(report["frames"][0]["expected"], p.load_catalogue()["available_current_frames"][CASE]["expected"])
        self.assertEqual(p.digest(args.captures / CASE), before)

    def test_zero_recipe_and_time_faults_reject_through_cli_then_restore(self):
        case = "t+0__b1_arm_rehearsal_v1__k00.json.gz"
        before = p.digest(args.captures / case)
        original, expected = p.admit_current(args.captures / case, case, p.load_catalogue())
        self.assertEqual(expected["torso_length"], 0)
        self.assertEqual(expected["seconds"], 0)
        for fault in ("recipe", "time"):
            with self.subTest(fault=fault):
                self.assertNotEqual(p.payload_fault(original, fault), original)
                code, report = self.geometry(fault, case)
                self.assertEqual(code, 1)
                self.assertEqual(report["failure_stage"], "binding")
                self.assertEqual(report["attempted_cases"][0]["expected"], expected)
                self.assertIsNotNone(report["attempted_cases"][0]["derived_payload_sha256"])
                self.assertEqual(self.geometry(case=case)[0], 0)
        self.assertEqual(p.digest(args.captures / case), before)

    def test_exact_cross_pose_rest_identity_faults_then_restore_same_validator(self):
        catalogue = p.load_catalogue()
        validator = p.GeometryValidator(catalogue)
        original, expected = p.admit_current(args.captures / CASE, CASE, catalogue)
        other_case = "t+1__b1_arm_rehearsal_v1__k00.json.gz"
        other, other_expected = p.admit_current(args.captures / other_case, other_case, catalogue)
        before = {case: p.digest(args.captures / case) for case in (CASE, other_case)}
        with self.assertRaises(p.Rejected) as initial_failure:
            validator.validate(p.payload_fault(original, "rest"), expected)
        self.assertEqual(initial_failure.exception.stage, "numerical_reconstruction")
        self.assertEqual(validator.rest_identities, {})
        validator.validate(original, expected)
        self.assertNotEqual(expected["seconds"], other_expected["seconds"])
        validator.validate(other, other_expected)
        evidence = []
        for fault in ("sub_bound_rest", "common_placement", "rest_normal", "raw_weight_scale", "bone_local_rest"):
            with self.subTest(fault=fault):
                altered = copy.deepcopy(other)
                garment = next(part for part in altered["snapshot"]["parts"] if part["name"] == "garment")
                if fault == "common_placement":
                    for part in altered["snapshot"]["parts"]:
                        for field in ("model_to_world", "display_transform"):
                            part[field][12] += 10
                elif fault == "bone_local_rest":
                    altered["snapshot"]["bones"][0]["local_rest"][12] += 1e-6
                else:
                    for index, sid in enumerate(garment["source_ids"]):
                        if sid != 246:
                            continue
                        if fault == "sub_bound_rest":
                            garment["rest_positions"][index][0] += 2e-8
                        elif fault == "rest_normal":
                            garment["rest_normals"][index][0] += .01
                        elif fault == "raw_weight_scale":
                            for row in garment["full_joint_influences"][index]:
                                row[1] *= 2
                # Discriminate the added contract from existing numerical bounds:
                # these derived payloads pass as an initial state, but must fail
                # against the authenticated earlier pose in the persistent batch.
                p.GeometryValidator(catalogue).validate(altered, other_expected)
                with self.assertRaises(p.Rejected) as caught:
                    validator.validate(altered, other_expected)
                self.assertEqual(caught.exception.stage, "cross_pose_rest_identity")
                validator.validate(other, other_expected)
                validator.validate(original, expected)
                evidence.append({"fault": fault, "expected": other_expected,
                    "admitted_template_sha256": before[other_case],
                    "derived_payload_sha256": p.sha(json.dumps(altered, sort_keys=True, separators=(",", ":")).encode()),
                    "initial_numeric_validation": "PASS_WITHOUT_PRIOR_REST_IDENTITY",
                    "persistent_batch_rejection": caught.exception.stage, "same_validator_restoration": "PASS"})
        # A changed caller-owned record must not alter the frozen baseline.
        original["snapshot"]["bones"][0]["local_rest"][12] += 1
        restored, _ = p.admit_current(args.captures / CASE, CASE, catalogue)
        validator.validate(restored, expected)
        self.assertEqual(len(validator.rest_identities), 1)
        for case, digest in before.items():
            self.assertEqual(p.digest(args.captures / case), digest)
        (args.out / "cross-pose-payload-controls.json").write_text(json.dumps({
            "pilot_py_sha256": p.digest(p.__file__), "test_pilot_py_sha256": p.digest(__file__),
            "baseline_case": CASE, "different_pose_case": other_case,
            "source_closure": catalogue["closure"], "controls": evidence,
            "scope": "derived payload controls through actual persistent GeometryValidator; not Rust production mutations",
            "full_current_runtime": "NOT_VERIFIED_RIG_ORACLE"}, indent=2) + "\n")

    def test_exact_topology_fault_rejected_then_restore(self):
        code, report = self.geometry("topology")
        self.assertEqual(code, 1)
        self.assertEqual(report["failure_stage"], "topology")
        self.assertEqual(len(report["attempted_cases"]), 1)
        self.assertEqual(self.geometry()[0], 0)

    def test_existing_output_is_never_replaced(self):
        path = args.out / "prior.json"
        path.write_text("preserved")
        with self.assertRaisesRegex(p.Rejected, "refuse to overwrite"):
            p.main(["historical", "--frame", "absent.gz", "--out", str(path)])
        self.assertEqual(path.read_text(), "preserved")


if __name__ == "__main__":
    started = time.monotonic()
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
    (args.out / "unittest.log").write_text(log.getvalue())
    summary = {"tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
               "skipped": len(result.skipped), "successful": result.wasSuccessful(), "python_optimization": sys.flags.optimize,
               "elapsed_seconds": time.monotonic()-started, "compilation": "N/A_STDLIB_PYTHON",
               "pilot_py_sha256": p.digest(p.__file__), "test_pilot_py_sha256": p.digest(__file__),
               "catalogue_sha256": p.digest(p.HERE / "catalogue.json"),
               "scope": "local CLI and derived payload/admission controls; no production Rust faults"}
    (args.out / "test-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(log.getvalue(), end="")
    raise SystemExit(0 if result.wasSuccessful() and result.testsRun > 0 else 1)
