#!/usr/bin/env python3
"""Lightweight harness controls. No Cargo, downloads, CI or full compilation."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("linux_equivalence_run", Path(__file__).with_name("run.py"))
pilot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pilot)
ROOT = Path(__file__).resolve().parents[2]


class InventoryControls(unittest.TestCase):
    def test_all_baseline_commands_preserved_in_order_except_host_guard(self):
        for lane in pilot.LANES:
            selected, excluded = pilot.extract_run_steps((ROOT / ".github/workflows/ci.yml").read_text(), lane)
            expected = []
            for step in selected:
                for command in step["commands"]:
                    expected.extend(["cargo test --workspace --locked", "cargo check --workspace --locked"]
                                    if command == pilot.NATIVE_DRIVER else [command])
            plan = pilot.make_plan(ROOT, lane)
            actual = [stage["command"] for stage in plan["stages"] if stage["baseline_command"] is not None]
            self.assertEqual(expected, actual)
            self.assertTrue(excluded)
            self.assertEqual(plan["build_flag_changes"], [])

    def test_baseline_workflow_drift_rejected(self):
        ci = (ROOT / ".github/workflows/ci.yml").read_text()
        with self.assertRaisesRegex(ValueError, "extraction drift"):
            pilot.extract_run_steps(ci.replace("-- --nocapture", ""), "b1-source-regression")

    def test_no_optimization_or_matrix_or_mutation_omission(self):
        commands = [s["command"] for s in pilot.make_plan(ROOT, "native-and-wasm")["stages"]]
        self.assertEqual(sum("scripts/check-b1-motion-mutations.py --disposable-checkout" in c for c in commands), 1)
        self.assertEqual(sum("run_matrix.py" in c for c in commands), 1)
        self.assertEqual(sum("experiments/70-b1-garment-defect/test_controls.py" in c for c in commands), 2)
        self.assertEqual(sum(c.startswith("python3 -B -O experiments/70-") for c in commands), 1)
        self.assertFalse(any("--skip-surfaces" in c for c in commands))

    def test_wasm_and_sampled_args_retained(self):
        commands = [s["command"] for s in pilot.make_plan(ROOT, "b1-source-regression")["stages"]]
        self.assertEqual(sum("--target wasm32-unknown-unknown --locked --offline" in c for c in commands), 9)
        self.assertIn("bash experiments/27-ci-baseline/check.sh wasm", commands)
        self.assertEqual(sum("--package b1-pose-adapter --test sampled --locked --offline -- --nocapture" in c for c in commands), 1)
        self.assertFalse(any("--features" in c for c in commands))

    def test_every_manifest_fetched_once(self):
        for lane in pilot.LANES:
            plan = pilot.make_plan(ROOT, lane)
            fetched = [s["command"].split("--manifest-path ", 1)[1] for s in plan["stages"] if s["command"].startswith("cargo fetch ")]
            self.assertEqual(set(fetched), set(plan["dependency_manifests"]))
            self.assertEqual(len(fetched), len(set(fetched)))

    def test_original_ci_step_timeout_inventory(self):
        plan = pilot.make_plan(ROOT, "native-and-wasm")
        matrix = [s for s in plan["stages"] if s["step"] == "Execute the actual B1 continuous motion matrix"]
        mutations = [s for s in plan["stages"] if s["step"] == "Check B1 production-source mutation witnesses"]
        self.assertEqual(len(matrix), 5)
        self.assertTrue(all(s["step_timeout_seconds"] == 1200 for s in matrix))
        self.assertEqual([s["step_timeout_seconds"] for s in mutations], [720])

    def test_unmapped_run_step_fails_closed_even_after_digest_refresh(self):
        ci = (ROOT / ".github/workflows/ci.yml").read_text().replace(
            "      - name: Run workspace CPU tests", "      - name: New critical test\n        run: false\n      - name: Run workspace CPU tests", 1)
        with patch.object(pilot, "CI_SHA256", pilot.sha(ci.encode())):
            with self.assertRaisesRegex(ValueError, "unmapped CI run step"):
                pilot.extract_run_steps(ci, "native-and-wasm")


class RuntimeControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def report_fixture(self, command="printf control", log="control\n"):
        path = self.root / "01.log"
        path.write_text(log)
        return {"initial_source_identity": {}, "plan": {"lane": "native-and-wasm", "stages": [{"id": "01", "category": "test"}]},
                "results": [{"id": "01", "command": command, "category": "test", "elapsed_seconds": 0.1,
                             "exit_code": 0, "log": "01.log", "log_sha256": pilot.sha(path.read_bytes())}]}

    def test_real_nonzero_and_output_retained(self):
        stage = {"id": "01", "command": "printf real-failure; exit 7", "category": "test", "env": {}, "timeout_seconds": 2}
        result = pilot.execute_stage(stage, self.root, self.root, {"RUNNER_TEMP": str(self.root)}, 2)
        self.assertEqual(result["exit_code"], 7)
        self.assertEqual((self.root / "01.log").read_text(), "real-failure")
        self.assertEqual(result["log_sha256"], pilot.sha(b"real-failure"))

    def test_timeout_terminates_real_child(self):
        stage = {"id": "01", "command": "echo $$ > child.pid; exec sleep 60", "category": "test", "env": {}, "timeout_seconds": 0.05}
        result = pilot.execute_stage(stage, self.root, self.root, {"RUNNER_TEMP": str(self.root)}, 2)
        self.assertEqual(result["failure"], "TimeoutExpired")
        self.assertIsNone(result["exit_code"])
        pid = int((self.root / "child.pid").read_text())
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

    def test_next_command_consumes_shared_deadline_then_fresh_run_recovers(self):
        def stage(number, command):
            return {"id": number, "step": "original bounded CI step", "command": command,
                    "category": "test", "env": {}, "timeout_seconds": 2, "step_timeout_seconds": 0.5}
        env = {"RUNNER_TEMP": str(self.root)}
        deadlines = {}
        first = pilot.execute_with_deadlines(stage("01", "sleep 0.3"), self.root, self.root, env, time.monotonic() + 5, deadlines)
        second = pilot.execute_with_deadlines(stage("02", "sleep 0.3; printf incorrectly-refreshed"), self.root, self.root, env, time.monotonic() + 5, deadlines)
        self.assertEqual(first["exit_code"], 0)
        self.assertLess(second["effective_timeout_seconds"], 0.25)
        self.assertEqual(second["failure"], "TimeoutExpired")
        self.assertIsNone(second["exit_code"])
        self.assertNotIn("incorrectly-refreshed", (self.root / "02.log").read_text())
        # A separate run owns a fresh budget; its normal command sequence passes.
        recovery = {}
        for number in ("03", "04"):
            result = pilot.execute_with_deadlines(stage(number, "printf recovered"), self.root, self.root, env, time.monotonic() + 5, recovery)
            self.assertEqual(result["exit_code"], 0)
            self.assertIsNone(result["failure"])
        self.assertEqual(len(recovery), 1)

    def test_global_budget_still_caps_shared_step_budget(self):
        stage = {"id": "01", "step": "bounded step", "command": "sleep 60", "category": "test", "env": {},
                 "timeout_seconds": 60, "step_timeout_seconds": 60}
        result = pilot.execute_with_deadlines(stage, self.root, self.root, {"RUNNER_TEMP": str(self.root)}, time.monotonic() + 0.05, {})
        self.assertEqual(result["failure"], "TimeoutExpired")
        self.assertLessEqual(result["effective_timeout_seconds"], 0.05)

    def test_missing_witness_cannot_be_success(self):
        report = self.report_fixture()
        with patch.object(pilot, "source_identity", return_value={}):
            self.assertEqual(pilot.finalize(self.root, self.root, report), 1)
        self.assertFalse(report["passed"])
        self.assertEqual(report["witnesses"], "FAILED")

    def test_partial_success_cannot_be_complete(self):
        report = self.report_fixture()
        report["plan"]["stages"].append({"id": "02", "category": "test"})
        with patch.object(pilot, "source_identity", return_value={}):
            self.assertEqual(pilot.finalize(self.root, self.root, report), 1)
        self.assertEqual(report["not_run_stage_ids"], ["02"])
        self.assertEqual(report["witnesses"], "NOT-RUN")

    def test_final_integrity_error_blocks_success(self):
        report = {"initial_source_identity": {}, "plan": {"lane": "native-and-wasm", "stages": []}, "results": []}
        with patch.object(pilot, "source_identity", side_effect=ValueError("changed lock")):
            self.assertEqual(pilot.finalize(self.root, self.root, report), 1)
        self.assertEqual(report["source_integrity"], "FAILED")

    def test_cargo_zero_tests_rejected_but_mixed_workspace_allowed(self):
        empty = "test result: ok. 0 passed; 0 failed; 7 ignored; 0 measured; 0 filtered out\n"
        nonempty = "test result: ok. 3 passed; 0 failed; 1 ignored; 0 measured; 0 filtered out\n"
        for log, expected in ((empty, 1), (empty + nonempty + empty, 0)):
            report = self.report_fixture("cargo test --workspace --locked", log)
            with patch.object(pilot, "source_identity", return_value={}), patch.object(pilot, "validate_witnesses"):
                self.assertEqual(pilot.finalize(self.root, self.root, report), expected)
            self.assertEqual(report["results"][0]["test_counts"]["executed"], 0 if expected else 3)

    def test_deleted_or_corrupt_stage_logs_fail_finalization(self):
        for action in ("delete", "corrupt"):
            report = self.report_fixture()
            path = self.root / "01.log"
            if action == "delete":
                path.unlink()
            else:
                path.write_text("changed after execution")
            with patch.object(pilot, "source_identity", return_value={}), patch.object(pilot, "validate_witnesses"):
                self.assertEqual(pilot.finalize(self.root, self.root, report), 1)
            self.assertEqual(report["stage_logs"], "FAILED")

    def test_deleted_or_corrupt_producer_files_fail_hash_validation(self):
        # These temporary control files exercise the same hash validator used by
        # all six mutation logs, every matrix entry and the viewer snapshot.
        for relative in ("mutant-red.log", "mutant-restored-green.log", "keyframes/frame.json.gz", "live-report.json"):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"retained-control")
            hashes = {relative: pilot.sha(path.read_bytes())}
            pilot.verify_file_hashes(self.root, hashes)
            path.unlink()
            with self.assertRaisesRegex(ValueError, "missing"):
                pilot.verify_file_hashes(self.root, hashes)
            path.write_bytes(b"corrupted-control")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                pilot.verify_file_hashes(self.root, hashes)

    def test_viewer_snapshot_detects_deleted_file_at_finalize(self):
        viewer = self.root / "runtime/nvwa-b1-viewer-runtime"
        viewer.mkdir(parents=True)
        receipt = viewer / "native-runtime.json"
        receipt.write_text("control")
        report = self.report_fixture()
        report["results"][0]["witness_file_hashes"] = pilot.file_hashes(viewer)
        receipt.unlink()
        with patch.object(pilot, "source_identity", return_value={}):
            self.assertEqual(pilot.finalize(self.root, self.root, report), 1)
        self.assertEqual(report["stage_logs"], "FAILED")

    def matrix_fixture(self):
        # Tiny control-only files test retained-evidence integrity, without
        # generating or claiming a real production motion/mutation witness.
        mutations = self.root / "runtime/nvwa-b1-motion-mutations"
        matrix = self.root / "runtime/nvwa-b1-motion-matrix"
        mutations.mkdir(parents=True)
        (matrix / "keyframes").mkdir(parents=True)
        cases = []
        for number in range(3):
            name = "control-" + str(number)
            cases.append({"name": name, "semantic_test_failure": True, "restored_green": True,
                          "before_sha256": "control", "restored_sha256": "control"})
            for suffix in ("-red.log", "-restored-green.log"):
                (mutations / (name + suffix)).write_text("control only")
        mutation_summary = {"passed": True, "cases": cases, "hashes": pilot.file_hashes(mutations)}
        (mutations / "summary.json").write_text(json.dumps(mutation_summary))
        expected, frames = pilot.expected_matrix_cohorts()
        for name in frames:
            (matrix / name).write_bytes(b"control-only frame bytes")
        records = []
        for (kind, torso, jaw, clip, k, seconds), count in expected.items():
            records.extend([{"kind": kind, "technical_pass": True, "request": {"torso_length": torso,
                            "jaw_drop": jaw, "clip_id": clip, "k": k, "seconds": seconds}}] * count)
        (matrix / "metrics.jsonl").write_text("".join(json.dumps(record) + "\n" for record in records))
        (matrix / "summary.json").write_text(json.dumps({"passed": True, "probe_exit": 0, "passing_records": 612, "records": 613,
            "probe_complete_marker": True, "coverage": {"complete": True, "expected": 594, "observed": 594, "missing": [],
                                                        "deep_keyframes_expected": 30, "deep_keyframes_observed": 30}}))
        (matrix / "SHA256SUMS.json").write_text(json.dumps(pilot.file_hashes(matrix)))
        return mutations, matrix

    def test_matrix_and_six_mutation_logs_are_all_required(self):
        mutations, matrix = self.matrix_fixture()
        pilot.validate_witnesses(self.root, "native-and-wasm")
        bad_log = mutations / "control-0-red.log"
        bad_log.unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            pilot.validate_witnesses(self.root, "native-and-wasm")
        bad_log.write_text("control only")
        bad_frame = matrix / sorted(pilot.expected_matrix_cohorts()[1])[0]
        bad_frame.write_bytes(b"changed after producer")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            pilot.validate_witnesses(self.root, "native-and-wasm")
        bad_frame.unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            pilot.validate_witnesses(self.root, "native-and-wasm")

    def test_old_594_total_summary_is_rejected(self):
        _, matrix = self.matrix_fixture()
        summary = json.loads((matrix / "summary.json").read_text())
        summary.update(passing_records=594, records=595)
        with self.assertRaisesRegex(ValueError, "total record counts"):
            pilot.validate_matrix_records(matrix, summary)

    def test_matrix_manifest_missing_frame_hash_is_rejected(self):
        _, matrix = self.matrix_fixture()
        path = matrix / "SHA256SUMS.json"
        hashes = json.loads(path.read_text())
        del hashes[sorted(pilot.expected_matrix_cohorts()[1])[0]]
        path.write_text(json.dumps(hashes))
        with self.assertRaisesRegex(ValueError, "file inventory changed"):
            pilot.validate_witnesses(self.root, "native-and-wasm")

    def test_each_seek_pause_or_matrix_cohort_is_required(self):
        _, matrix = self.matrix_fixture()
        rows = (matrix / "metrics.jsonl").read_text().splitlines()
        summary = json.loads((matrix / "summary.json").read_text())
        for missing_kind in ("seek", "pause", "matrix"):
            index = next(i for i, line in enumerate(rows) if json.loads(line)["kind"] == missing_kind)
            (matrix / "metrics.jsonl").write_text("\n".join(rows[:index] + rows[index + 1:]) + "\n")
            with self.assertRaisesRegex(ValueError, "metric cohort"):
                pilot.validate_matrix_records(matrix, summary)

    def test_frozen_source_derives_all_record_kinds_and_deep_frames(self):
        records, frames = pilot.expected_matrix_cohorts()
        self.assertEqual(sum(count for key, count in records.items() if key[0] == "matrix"), 594)
        self.assertEqual(sum(count for key, count in records.items() if key[0] == "seek"), 16)
        self.assertEqual(sum(count for key, count in records.items() if key[0] == "pause"), 2)
        self.assertEqual(sum(records.values()), 612)
        self.assertEqual(len(frames), 30)

    def test_source_identity_rejects_real_tracked_drift(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / "Cargo.lock").write_text("frozen\n")
        subprocess.run(["git", "-C", str(self.root), "add", "Cargo.lock"], check=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Harness Control", "-c", "user.email=harness@example.invalid", "commit", "-qm", "control fixture"], check=True)
        head = pilot.git(self.root, "rev-parse", "HEAD")
        tree = pilot.git(self.root, "rev-parse", "HEAD^{tree}")
        with patch.object(pilot, "BASE_SHA", head), patch.object(pilot, "BASE_TREE", tree):
            identity = pilot.source_identity(self.root)
            self.assertIn("Cargo.lock", identity["tracked_locks"])
            (self.root / "Cargo.lock").write_text("changed\n")
            with self.assertRaisesRegex(ValueError, "dirty"):
                pilot.source_identity(self.root)

    def test_mac_cannot_be_reported_as_linux_runtime(self):
        with patch.object(pilot.platform, "system", return_value="Darwin"):
            with self.assertRaisesRegex(ValueError, "actual Linux"):
                pilot.run(self.root, self.root / "out", {}, 1)


if __name__ == "__main__":
    unittest.main()
