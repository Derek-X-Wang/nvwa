"""Collector unit/integration tests. All child processes are fake Python tools."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import zlib


spec = importlib.util.spec_from_file_location("measure_native", Path(__file__).with_name("measure_native.py"))
measure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(measure)


def png_data(black=True, width=1280, height=720):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    # RGBA alpha is white even for a black capture; only RGB establishes nonblack.
    row = b"\0" + (b"\0\0\0\xff" if black else b"\x10\x20\x30\xff") * width
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(row * height)) + chunk(b"IEND", b""))


class ParserTests(unittest.TestCase):
    def test_evidence_ansi_and_non_evidence(self):
        self.assertEqual(measure.parse_evidence('\x1b[32mINFO\x1b[0m NVWA_EVIDENCE {"ready":true}'), {"ready": True})
        self.assertIsNone(measure.parse_evidence("just a diagnostic"))

    def test_malformed_or_nonobject_evidence_rejected(self):
        for text in ("NVWA_EVIDENCE not-json", "NVWA_EVIDENCE []", 'NVWA_EVIDENCE {"ready":true} trailing'):
            with self.assertRaises(ValueError):
                measure.parse_evidence(text)

    def test_rss_identity_and_units(self):
        self.assertEqual(measure.parse_rss("100 99 4096\n", 100, 99), 4194304)
        self.assertIsNone(measure.parse_rss("100 98 4096", 100, 99))
        self.assertIsNone(measure.parse_rss("101 99 4096", 100, 99))
        self.assertIsNone(measure.parse_rss("", 100, 99))

    def test_runtime_requires_exact_boundary_identities(self):
        record = {"ready": True, "capture_callback": True, "error": None, "timeout": False,
                  "build_profile": "release", "document_revision": 9,
                  "physical_window": {"width": 1280, "height": 720, "scale_factor": 1},
                  "gpu": {"backend": "Metal"}, "meshes": 9, "skins": 9, "joints": 18,
                  "players": 1, "frame_timing_kind": "main_loop_cadence_not_gpu_timestamp"}
        self.assertEqual(measure.runtime_failures(record, 9), [])
        record["document_revision"] = 10
        record["physical_window"]["scale_factor"] = 2
        self.assertEqual(len(measure.runtime_failures(record, 9)), 2)


class CaptureTests(unittest.TestCase):
    def test_fresh_black_capture_is_valid_but_not_visual_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "capture.png"
            started = time.time_ns() - 1_000_000_000
            path.write_bytes(png_data())
            result = measure.inspect_png(path, started)
            self.assertTrue(result["valid_png"])
            self.assertTrue(result["fresh"])
            self.assertTrue(result["all_rgb_black"])
            self.assertEqual(result["visual_character_review"], "NOT-RUN")

    def test_nonblack_does_not_claim_character_or_first_frame(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "capture.png"
            path.write_bytes(png_data(black=False))
            result = measure.inspect_png(path, time.time_ns() + 1_000_000_000)
            self.assertTrue(result["valid_png"])
            self.assertFalse(result["fresh"])
            self.assertFalse(result["all_rgb_black"])
            self.assertEqual(result["visual_character_review"], "NOT-RUN")

    def test_truncated_crc_or_wrong_size_captures_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "capture.png"
            corrupt = bytearray(png_data())
            corrupt[20] ^= 1
            for data in (png_data()[:-4], corrupt, png_data(width=10, height=10)):
                path.write_bytes(data)
                self.assertFalse(measure.inspect_png(path, 0)["valid_png"])


class FakeProcessTests(unittest.TestCase):
    def collect(self, code, timeout=2):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            result = measure.collect_process([sys.executable, "-u", "-c", code], path, path,
                                             timeout, .05, dict(os.environ))
            return result, {item.name: item.read_bytes() for item in path.iterdir()}

    def test_nonzero_failure_and_both_raw_streams_retained(self):
        result, files = self.collect("import sys,time; print('out'); print('real failure',file=sys.stderr); time.sleep(.2); sys.exit(42)")
        self.assertEqual(result["exit_code"], 42)
        self.assertEqual(files["stdout.log"], b"out\n")
        self.assertEqual(files["stderr.log"], b"real failure\n")
        self.assertGreater(result["rss_sample_count"], 0)
        self.assertGreater(result["sampled_peak_child_rss_bytes"], 0)
        self.assertEqual(result["runtime_events"], [])
        self.assertLessEqual(result["spawn_call_monotonic_ns"], result["spawn_return_monotonic_ns"])
        self.assertLessEqual(result["spawn_return_monotonic_ns"], result["exit_observed_monotonic_ns"])

    def test_timeout_stops_only_the_owned_child_and_retains_log(self):
        result, files = self.collect("import time; print('started',flush=True); time.sleep(30)", timeout=.2)
        self.assertTrue(result["timed_out"])
        self.assertNotEqual(result["exit_code"], 0)
        self.assertEqual(result["termination"]["target_pid"], result["pid"])
        self.assertIn(b"started", files["stdout.log"])
        self.assertLess(result["total_wall_seconds_to_exit_observation"], 3)

    def test_malformed_event_retained_and_partial_no_newline_parsed(self):
        result, files = self.collect("import sys; print('NVWA_EVIDENCE broken',file=sys.stderr); sys.stdout.write('NVWA_EVIDENCE {\"ready\":true}')")
        self.assertEqual(len(result["malformed_evidence"]), 1)
        self.assertEqual(result["runtime_events"][0]["record"], {"ready": True})
        self.assertIn(b"broken", files["stderr.log"])

    def test_missing_executable_has_report_instead_of_exception(self):
        with tempfile.TemporaryDirectory() as folder:
            result = measure.collect_process([str(Path(folder) / "missing")], folder, folder, 1, .05, dict(os.environ))
            self.assertIsNone(result["exit_code"])
            self.assertTrue(result["collector_errors"])

    def test_sigterm_cancellation_retains_report_and_stops_owned_fake_child(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            marker = path / "child-started"
            child_code = f"from pathlib import Path; import time; Path({str(marker)!r}).write_text('started'); time.sleep(30)"
            module = Path(__file__).with_name("measure_native.py")
            runner_code = (f"import importlib.util,json,os,sys; from pathlib import Path; "
                f"spec=importlib.util.spec_from_file_location('collector',{str(module)!r}); "
                "m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); "
                f"r=m.collect_process([sys.executable,'-u','-c',{child_code!r}],{str(path)!r},{str(path)!r},10,.05,dict(os.environ)); "
                f"Path({str(path / 'cancel.json')!r}).write_text(json.dumps(r))")
            runner = subprocess.Popen([sys.executable, "-c", runner_code], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic() + 3
                while not marker.exists() and time.monotonic() < deadline and runner.poll() is None:
                    time.sleep(.01)
                self.assertTrue(marker.exists(), "fake child never started")
                runner.terminate()
                stdout, stderr = runner.communicate(timeout=4)
                self.assertEqual(runner.returncode, 0, (stdout, stderr))
                report = json.loads((path / "cancel.json").read_text())
                self.assertTrue(report["cancelled"])
                self.assertEqual(report["cancellation_signal"], signal.SIGTERM)
                self.assertEqual(report["termination"]["target_pid"], report["pid"])
                self.assertNotEqual(report["exit_code"], 0)
            finally:
                if runner.poll() is None:
                    runner.terminate()
                    runner.communicate(timeout=4)

    def test_cli_failure_report_keeps_exit_and_never_claims_mock_character(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "crates/nvwa-studio/src").mkdir(parents=True)
            (root / "assets/fixtures").mkdir(parents=True)
            source = root / "crates/nvwa-studio/src/lib.rs"
            source.write_text('fn parse_native_args( ' + " ".join(json.dumps(flag) for flag in measure.FLAGS) + ' fn parse_web_pairs(')
            fixture = root / "assets/fixtures/mock.glb"
            fixture.write_bytes(b"FAKE TEST INPUT; not a character asset")
            work = root / "mock.json"
            work.write_text(json.dumps({"revision": 9, "profile": {"id": "mock", "asset_path": "fixtures/mock.glb",
                "asset_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest()}, "character": {"id": "mock"}, "timeline": []}))
            child = root / "fake-child"
            child.write_text(f"#!{sys.executable}\nimport sys\nprint('Unknown launch argument: --benchmark',file=sys.stderr)\nsys.exit(42)\n")
            child.chmod(0o700)
            output = root / "run"
            with contextlib.redirect_stdout(io.StringIO()):
                code = measure.main(["--binary", str(child), "--source-root", str(root), "--work", str(work),
                    "--output", str(output), "--isolation-note", "fake collector test only", "--cache-note", "no renderer"])
            self.assertEqual(code, 42)
            report = json.loads((output / "report.json").read_text())
            self.assertEqual(report["status"], "FAILED")
            self.assertEqual(report["process"]["exit_code"], 42)
            self.assertEqual(report["environment_overrides"]["NVWA_ASSET_ROOT"], str(root.resolve() / "assets"))
            self.assertTrue(any("rejected launch flag" in reason for reason in report["failure_reasons"]))
            self.assertEqual(report["capture"]["visual_character_review"], "NOT-RUN")
            with self.assertRaises(FileExistsError):
                measure.main(["--binary", str(child), "--source-root", str(root), "--work", str(work),
                    "--output", str(output), "--isolation-note", "fake", "--cache-note", "fake"])


if __name__ == "__main__":
    unittest.main()
