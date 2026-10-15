"""Actual integration comparison and owned CPU-process regression controls."""
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

import mapping_comparison as mapping
import owned_command

HERE = Path(__file__).resolve().parent


class Comparison(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.output = Path(self.temp.name) / "output"
        shutil.copytree(mapping.REFERENCE, self.output)
        for name in ("mapping-manifest.json", "metrics.json"):
            shutil.copyfile(mapping.BASELINE / name, self.output / name)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, value):
        path = self.output / name
        path.write_text(json.dumps(value, sort_keys=True) + "\n")
        if name not in ("mapping-manifest.json", "metrics.json"):
            manifest = mapping.load(self.output / "mapping-manifest.json")
            manifest["files"][name] = {"bytes": path.stat().st_size,
                                       "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            (self.output / "mapping-manifest.json").write_text(json.dumps(manifest))

    def pair(self, change):
        stem = "77-asymmetric-calibrated"
        raw = mapping.load(self.output / (stem + ".raw.json"))
        change(raw)
        self.write(stem + ".raw.json", raw)
        envelope = mapping.load(self.output / (stem + ".normalized.json"))
        envelope.update(copy.deepcopy(raw))
        envelope["provenance"]["raw_sha256"] = hashlib.sha256(
            (self.output / (stem + ".raw.json")).read_bytes()).hexdigest()
        self.write(stem + ".normalized.json", envelope)

    def check(self):
        return mapping.compare_mapping(self.output)

    def test_all_36_files_and_18_bindings(self):
        self.assertEqual(self.check()["portable_files_verified"], 36)
        self.assertEqual(self.check()["pairs_verified"], 18)

    def test_last_bit_rounding_with_recomputed_real_file_hashes_is_accepted(self):
        def rounding(raw):
            old = raw["local_rotations_xyzw"][5][3][0]
            raw["local_rotations_xyzw"][5][3][0] = math.nextafter(old, math.inf)
        self.pair(rounding)
        metrics = mapping.load(self.output / "metrics.json")
        key = "wrong_xyz_sign_position_error_m"
        metrics[key] = math.nextafter(metrics[key], math.inf)
        self.write("metrics.json", metrics)
        self.check()

    def test_material_numeric_mutation_with_honest_hashes_is_rejected(self):
        self.pair(lambda raw: raw["local_rotations_xyzw"][5][3].__setitem__(0, .125))
        with self.assertRaisesRegex(ValueError, "Numeric"):
            self.check()

    def test_shape_mutation_is_rejected(self):
        self.pair(lambda raw: raw["local_rotations_xyzw"][0].pop())
        with self.assertRaisesRegex(ValueError, "Shape"):
            self.check()

    def test_boolean_cannot_replace_numeric_schema_version(self):
        self.pair(lambda raw: raw.__setitem__("schema_version", True))
        with self.assertRaisesRegex(ValueError, "Type"):
            self.check()

    def test_unknown_field_is_rejected(self):
        self.pair(lambda raw: raw.__setitem__("unexpected", None))
        with self.assertRaisesRegex(ValueError, "Keys"):
            self.check()

    def test_nonfinite_is_rejected_even_with_honest_manifest(self):
        self.pair(lambda raw: raw["root_translations_m"][0].__setitem__(0, float("nan")))
        with self.assertRaisesRegex(ValueError, "Nonfinite"):
            self.check()

    def test_provenance_and_raw_binding_mutations_are_rejected(self):
        name = "source77-rest.normalized.json"
        envelope = mapping.load(self.output / name)
        envelope["provenance"]["provider"] = "pretend"
        self.write(name, envelope)
        with self.assertRaises(ValueError):
            self.check()
        envelope["provenance"]["provider"] = None
        envelope["provenance"]["raw_sha256"] = "0" * 64
        self.write(name, envelope)
        with self.assertRaisesRegex(ValueError, "binding"):
            self.check()

    def test_manifest_hash_or_input_pin_mutation_is_rejected(self):
        manifest = mapping.load(self.output / "mapping-manifest.json")
        name = next(iter(manifest["files"]))
        manifest["files"][name]["sha256"] = "0" * 64
        self.write("mapping-manifest.json", manifest)
        with self.assertRaisesRegex(ValueError, "digest"):
            self.check()
        manifest = mapping.load(mapping.BASELINE / "mapping-manifest.json")
        manifest["script_sha256"] = "0" * 64
        self.write("mapping-manifest.json", manifest)
        with self.assertRaisesRegex(ValueError, "Value"):
            self.check()

    def test_every_generated_byte_is_bound_to_its_own_manifest(self):
        path = self.output / "source77-trajectory.raw.json"
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "digest"):
            self.check()

    def test_missing_file_is_rejected(self):
        (self.output / "source77-rest.raw.json").unlink()
        with self.assertRaisesRegex(ValueError, "file set"):
            self.check()

    def test_metric_mutation_and_duplicate_json_keys_are_rejected(self):
        metrics = mapping.load(self.output / "metrics.json")
        metrics["wrong_xyz_sign_position_error_m"] += .001
        self.write("metrics.json", metrics)
        with self.assertRaisesRegex(ValueError, "Numeric"):
            self.check()
        path = self.output / "metrics.json"
        data = path.read_bytes().rstrip()
        path.write_bytes(data[:-1] + b',"frames_per_case":11}')
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.check()


def payload(folder, leaf=False):
    folder = Path(folder)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    (folder / ("leaf.pid" if leaf else "leader.pid")).write_text(str(os.getpid()))
    if not leaf:
        subprocess.Popen([sys.executable, "-B", __file__, "--leaf", str(folder)])
    until = time.monotonic() + 12
    while time.monotonic() < until:
        time.sleep(.03)


def control(scenario, folder):
    folder = Path(folder)
    receipt = folder / "command.json"
    if scenario == "full_driver_sigint":
        import check_model_free
        bindir = folder / "bin"
        bindir.mkdir()
        cargo = bindir / "cargo"
        cargo.write_text("#!" + sys.executable + "\nimport os,sys\nos.execv(sys.executable," +
                         repr([sys.executable, "-B", str(Path(__file__).resolve()),
                               "--payload", str(folder)]) + ")\n")
        cargo.chmod(0o700)
        os.environ["PATH"] = str(bindir) + os.pathsep + os.environ["PATH"]
        check_model_free.PRIVATE = folder / "full-driver"
        check_model_free.main()
        return
    if scenario == "postspawn_failure":
        receipt.mkdir()  # Actual filesystem write failure after Popen.
    if scenario == "inspection_failure":
        def failing_inspection(_pgid):
            raise OSError("controlled inspection failure")
        owned_command._group_members = failing_inspection
    if scenario == "signal_during_teardown":
        original = owned_command._group_members
        def signalling_inspection(pgid):
            owned_command._group_members = original
            os.kill(os.getpid(), signal.SIGTERM)
            return original(pgid)
        owned_command._group_members = signalling_inspection
    if scenario in ("signal_during_persistence", "signal_after_persistence"):
        original_persist = owned_command._persist
        calls = []
        def signalling_persist(path, receipt):
            calls.append(path)
            if len(calls) == 2 and scenario == "signal_during_persistence":
                os.kill(os.getpid(), signal.SIGTERM)
            original_persist(path, receipt)
            if len(calls) == 2 and scenario == "signal_after_persistence":
                os.kill(os.getpid(), signal.SIGTERM)
        owned_command._persist = signalling_persist
    try:
        owned_command.run_owned([sys.executable, "-B", __file__, "--payload", str(folder)],
                                HERE, dict(os.environ), folder / "command.log", receipt,
                                5 if scenario in ("sigint", "sigterm") else .7)
    except owned_command.OwnedCommandError as error:
        print(json.dumps(error.receipt), flush=True)
        raise SystemExit(2)


class Lifecycle(unittest.TestCase):
    def exercise(self, scenario, sig=None):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            child = subprocess.Popen([sys.executable, "-B", __file__, "--control", scenario, temporary],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                     start_new_session=True)
            pgid = None
            try:
                if sig:
                    until = time.monotonic() + 4
                    while not (folder / "leaf.pid").exists() and time.monotonic() < until:
                        if child.poll() is not None:
                            break
                        time.sleep(.02)
                    self.assertTrue((folder / "leaf.pid").exists(), "real descendant did not start")
                    os.kill(child.pid, sig)
                stdout, stderr = child.communicate(timeout=10)
                if scenario == "full_driver_sigint":
                    receipts = list((folder / "full-driver").glob("run-*/build.command.json"))
                    self.assertEqual(len(receipts), 1)
                    result = json.loads(receipts[0].read_text())
                elif scenario == "postspawn_failure":
                    result = json.loads(stdout)
                    self.assertIn("OWNED_COMMAND_RECEIPT", stderr)
                else:
                    result = json.loads((folder / "command.json").read_text())
                pgid = result["pid"]
                self.assertTrue(result["cleanup"]["leader_reaped"])
                self.assertEqual(result["cleanup"]["signals_attempted"], ["SIGTERM", "SIGKILL"])
                self.assertFalse([row for row in owned_command._group_members(pgid)
                                  if not row["state"].startswith("Z")], result)
                if sig:
                    self.assertEqual(child.returncode, -sig, stderr)
                    self.assertEqual(result["pending_signals"][0], sig)
                elif scenario in ("signal_during_teardown", "signal_during_persistence", "signal_after_persistence"):
                    self.assertEqual(child.returncode, -signal.SIGTERM)
                    self.assertEqual(result["pending_signals"], [signal.SIGTERM])
                else:
                    self.assertEqual(child.returncode, 2, stderr)
                if scenario == "inspection_failure":
                    self.assertEqual(result["cleanup"]["status"], "cleanup_unconfirmed")
                    self.assertFalse(result["cleanup"]["owned_group_exit_verified"])
                if scenario == "timeout":
                    self.assertTrue(result["timed_out"])
            finally:
                if pgid is None and (folder / "leader.pid").exists():
                    pgid = int((folder / "leader.pid").read_text())
                if pgid:
                    try:
                        os.killpg(pgid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                if child.poll() is None:
                    child.kill()
                    child.communicate()

    def test_actual_sigint_with_term_ignoring_descendant(self):
        self.exercise("sigint", signal.SIGINT)

    def test_actual_sigterm_with_term_ignoring_descendant(self):
        self.exercise("sigterm", signal.SIGTERM)

    def test_actual_timeout_with_term_ignoring_descendant(self):
        self.exercise("timeout")

    def test_actual_postspawn_receipt_failure(self):
        self.exercise("postspawn_failure")

    def test_actual_signal_deferred_during_teardown_and_receipt(self):
        self.exercise("signal_during_teardown")

    def test_actual_signal_deferred_during_final_receipt_persistence(self):
        self.exercise("signal_during_persistence")

    def test_actual_signal_after_receipt_write_is_persisted_before_exit(self):
        self.exercise("signal_after_persistence")

    def test_actual_successful_command_is_reaped_and_receipted(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            receipt = owned_command.run_owned([sys.executable, "-c", "pass"], HERE,
                                              dict(os.environ), folder / "log", folder / "receipt.json", 3)
            self.assertEqual(receipt["exit_code"], 0)
            self.assertEqual(receipt["cleanup"]["status"], "verified_absent")
            self.assertEqual(json.loads((folder / "receipt.json").read_text()), receipt)

    def test_failed_inspection_keeps_uncertainty_after_real_kill(self):
        self.exercise("inspection_failure")

    def test_actual_driver_sigint_uses_owned_command_seam(self):
        self.exercise("full_driver_sigint", signal.SIGINT)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] in ("--payload", "--leaf"):
        payload(sys.argv[2], leaf=sys.argv[1] == "--leaf")
    elif len(sys.argv) == 4 and sys.argv[1] == "--control":
        control(sys.argv[2], sys.argv[3])
    else:
        unittest.main(verbosity=2)
