#!/usr/bin/env python3
"""Bounded controls using explicitly supplied preserved frames; no runtime run."""
import argparse
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import analyze as a

parser = argparse.ArgumentParser()
parser.add_argument("--linux", required=True, type=Path)
parser.add_argument("--mac-v1", required=True, type=Path)
args, remaining = parser.parse_known_args()
sys.argv = [sys.argv[0], *remaining]


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = a.d.Source(a.ROOT / "assets/characters/mpfb-b1-v1")
        cls.linux = a.load_linux(args.linux, cls.source)
        cls.mac = a.load_mac(args.mac_v1, "mac-v1", cls.source)

    def test_three_points_retain_original_full_analyzer_red(self):
        value = a.geometry(self.linux["rest"], self.linux["posed"])
        self.assertFalse(a.scalar_signal(value["ratio"])["passed"])
        full = a.d.analyze(self.linux["record"], self.source, a.EXPECTED)
        self.assertEqual(value["ratio"], full["geometry"]["posed_over_fitted_rest_area"])
        self.assertTrue(a.scalar_signal(a.geometry(self.mac["rest"], self.mac["posed"])["ratio"])["passed"])

    def test_same_f32_model_reproduces_both_real_uploads(self):
        for value in (self.mac, self.linux):
            replay = a.replay_f32(value["rest"], value["weights"], value["bones"])
            self.assertEqual(replay, {i: value["posed"][i] for i in a.d.CORE})

    def test_changing_only_bones_reproduces_entire_scalar_delta(self):
        self.assertEqual(self.mac["part"]["rest_positions"], self.linux["part"]["rest_positions"])
        self.assertEqual(self.mac["part"]["full_joint_influences"], self.linux["part"]["full_joint_influences"])
        swapped = a.replay_f32(self.mac["rest"], self.mac["weights"], self.linux["bones"])
        self.assertEqual(a.geometry(self.mac["rest"], swapped), a.geometry(self.linux["rest"], self.linux["posed"]))

    def test_difference_survives_f32_bit_comparison(self):
        comparison = a.compare(self.mac, self.linux)
        self.assertGreater(comparison["bones"]["skin"]["changed_f32_components"], 0)
        self.assertGreater(comparison["source_shaped_f32_replay"]["core_upload_changed_f32_components"], 0)

    def test_missing_input_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                a.load_linux(Path(tmp) / "absent.json.gz", self.source)

    def test_wrong_frame_hash_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "wrong.json"
            path.write_text("{}")
            with self.assertRaisesRegex(ValueError, "wrong Linux frame hash"):
                a.load_linux(path, self.source)

    def test_changed_provenance_hash_rejected(self):
        with self.assertRaisesRegex(ValueError, "provenance hash/length"):
            a.check_file(args.linux, {"bytes": args.linux.stat().st_size, "sha256": "0" * 64})

    def test_stale_actual_sample_rejected_by_original_analyzer(self):
        record = copy.deepcopy(self.linux["record"])
        record["snapshot"]["sample"]["source_seconds"] = 0.0
        with self.assertRaisesRegex(ValueError, "stale actual time"):
            a.d.analyze(record, self.source, a.EXPECTED)

    def test_existing_output_refusal_is_explicit(self):
        # The script's CLI rejects replacement before loading any input.
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "prior.json"
            out.write_text("preserved")
            result = subprocess.run([sys.executable, "-B", str(Path(a.__file__)), "--linux", str(args.linux),
                                     "--mac-v1", str(args.mac_v1), "--mac-v2", str(args.mac_v1), "--out", str(out)],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b"refuse to overwrite", result.stderr)
            self.assertEqual(out.read_text(), "preserved")


if __name__ == "__main__":
    unittest.main()
