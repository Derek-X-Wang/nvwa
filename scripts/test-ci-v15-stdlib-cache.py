#!/usr/bin/env python3
"""Focused controls for the CI-only stdlib cache boundary."""
import importlib.util
import marshal
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location("test_" + name, SCRIPTS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CACHE = load("ci-v15-stdlib-cache")
HISTORY = load("check-v15-history")
HOSTED = {
    "GITHUB_ACTIONS": "true", "GITHUB_JOB": "portable-eye", "RUNNER_OS": "Linux",
    "RUNNER_ENVIRONMENT": "github-hosted",
}


class Boundary(unittest.TestCase):
    def test_opt_in_is_only_the_full_hosted_replay(self):
        full = SimpleNamespace(offline=False, normal_only=False, cohort=None)
        self.assertTrue(HISTORY.ci_prewarm_enabled(full, HOSTED))
        self.assertFalse(HISTORY.ci_prewarm_enabled(full, {}))
        for key in HOSTED:
            with self.subTest(missing=key):
                self.assertFalse(HISTORY.ci_prewarm_enabled(full, {k:v for k,v in HOSTED.items() if k != key}))
            with self.subTest(changed=key):
                self.assertFalse(HISTORY.ci_prewarm_enabled(full, dict(HOSTED, **{key: "other"})))
        for flag, value in (("offline", True), ("normal_only", True), ("cohort", "73"), ("cohort", "72")):
            with self.subTest(flag=flag):
                self.assertFalse(HISTORY.ci_prewarm_enabled(SimpleNamespace(**(vars(full) | {flag: value})), HOSTED))

    def test_lifecycle_preserves_the_original_callset_and_never_dispatches_after_failure(self):
        modes = ([], ["-O"])
        cohorts = (HISTORY.EXP72, HISTORY.EXP73)
        for effect in (False, True):
            with tempfile.TemporaryDirectory() as path, self.subTest(fails=effect):
                scratch = Path(path).resolve()
                prefix = scratch / "stdlib-bytecode-cache"
                with patch.object(HISTORY, "materialize", return_value={"archive": "verified"}) as export, \
                        patch.object(HISTORY, "prewarm_stdlib", return_value=prefix,
                                     side_effect=HISTORY.ReplayError("cache verification failed") if effect else None) as warm, \
                        patch.object(HISTORY, "current_context") as current, patch.object(HISTORY, "dispatch") as dispatch, \
                        patch.object(HISTORY, "protected_experiments", return_value={x: set() for x in cohorts}):
                    if effect:
                        with self.assertRaisesRegex(HISTORY.ReplayError, "cache verification failed"):
                            HISTORY.replay(ROOT, modes, ROOT, scratch, cohorts, prewarm=True)
                        current.assert_not_called()
                        dispatch.assert_not_called()
                    else:
                        HISTORY.replay(ROOT, modes, ROOT, scratch, cohorts, prewarm=True)
                        self.assertEqual([c.args for c in current.call_args_list],
                                         [(ROOT, flags, exp, prefix) for exp in cohorts for flags in modes])
                        self.assertEqual([(c.args[2], c.args[3], len(c.args[4]), c.args[6])
                                          for c in dispatch.call_args_list],
                                         [(exp, flags, 14 if exp==HISTORY.EXP72 else 58, prefix)
                                          for exp in cohorts for flags in modes])
                    export.assert_called_once_with(ROOT, ROOT, scratch / "tree")
                    warm.assert_called_once_with(ROOT, scratch)

    def test_changed_symlink_and_untrusted_parent_helper_never_executes(self):
        with tempfile.TemporaryDirectory() as path, patch.object(HISTORY.subprocess, "check_output") as child:
            live = Path(path).resolve()
            helper = live / HISTORY.STDLIB_CACHE_HELPER
            helper.parent.mkdir()
            trusted = SCRIPTS / helper.name
            helper.write_bytes(trusted.read_bytes() + b"\n")
            with self.assertRaisesRegex(HISTORY.ReplayError, "helper identity"):
                HISTORY.prewarm_stdlib(live, live)
            helper.unlink()
            helper.symlink_to(trusted)
            with self.assertRaisesRegex(HISTORY.ReplayError, "ordinary checkout file"):
                HISTORY.prewarm_stdlib(live, live)
            helper.unlink()
            helper.parent.rmdir()
            helper.parent.symlink_to(SCRIPTS, target_is_directory=True)
            with self.assertRaisesRegex(HISTORY.ReplayError, "ordinary checkout file"):
                HISTORY.prewarm_stdlib(live, live)
            child.assert_not_called()


class CacheFaults(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name).resolve()
        self.prefix = self.root / "private"
        self.prefix.mkdir(mode=0o700)
        self.src = self.root / "stdlib.py"
        self.raw = b"assert 1 == 2\nstate = 9\n"
        self.src.write_bytes(self.raw)
        self.file = self.prefix / "module.pyc"
        self.payload = CACHE.cache_payload(self.raw, self.src, 0)
        self.file.write_bytes(self.payload)
        self.file.chmod(0o600)
        self.expected = {self.file: CACHE.sha(self.payload)}
        self.sources = {self.src: CACHE.sha(self.raw)}

    def readback(self):
        CACHE.validate_cache(self.prefix, self.expected, self.sources, os.geteuid())

    def test_complete_payload_and_explicit_optimization(self):
        normal = marshal.loads(self.payload[16:])
        optimized = marshal.loads(CACHE.cache_payload(self.raw, self.src, 1)[16:])
        self.assertEqual(self.payload[4:8], CACHE.CHECKED_HASH_FLAGS)
        self.assertEqual(self.payload[8:16], importlib.util.source_hash(self.raw))
        self.assertEqual(normal.co_filename, str(self.src))
        with self.assertRaises(AssertionError):
            exec(normal)
        namespace = {}
        exec(optimized, namespace)
        self.assertEqual(namespace["state"], 9)
        self.readback()

    def test_false_compiled_payload_stale_source_and_extra_files_fail_closed(self):
        # The source-hash header of the forged payload is byte-for-byte correct.
        self.file.write_bytes(self.payload[:-1] + bytes([self.payload[-1] ^ 1]))
        with self.assertRaisesRegex(ValueError, "changed compiled cache payload"):
            self.readback()
        self.file.write_bytes(self.payload)
        self.src.write_bytes(self.raw.replace(b"9", b"8"))
        with self.assertRaisesRegex(ValueError, "stdlib source changed"):
            self.readback()
        self.src.write_bytes(self.raw)
        extra = self.prefix / "shadow.pyc"
        extra.write_bytes(self.payload)
        with self.assertRaisesRegex(ValueError, "unexpected cache entry"):
            self.readback()
        extra.unlink()
        self.readback()

    def test_cache_path_refuses_links_missing_or_nonprivate_state(self):
        target = self.root / "valid-original.pyc"
        target.write_bytes(self.payload)
        self.file.unlink()
        self.file.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "unexpected cache entry"):
            self.readback()
        self.file.unlink()
        os.link(target, self.file)
        self.file.chmod(0o600)
        with self.assertRaisesRegex(ValueError, "unexpected cache entry"):
            self.readback()
        self.file.unlink()
        with self.assertRaisesRegex(ValueError, "incomplete stdlib cache"):
            self.readback()
        target.rename(self.file)
        self.prefix.chmod(0o755)
        with self.assertRaisesRegex(ValueError, "cache root must stay private"):
            self.readback()
        self.prefix.chmod(0o700)
        self.readback()

    def test_cache_ancestry_refuses_symlinks_and_writable_parents(self):
        link = self.root / "alias"
        link.symlink_to(self.prefix, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "noncanonical directory"):
            CACHE.validate_ancestry(link, scratch=True)
        with self.assertRaisesRegex(ValueError, "untrusted directory owner"):
            CACHE.validate_ancestry(self.prefix, scratch=True, owners={-1})
        self.root.chmod(0o777)
        try:
            with self.assertRaisesRegex(ValueError, "unsafe directory ancestry"):
                self.readback()
        finally:
            self.root.chmod(0o700)
        self.readback()


class ActualCompiler(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "linux" and sys.implementation.name == "cpython",
                         "CI cache supports Linux CPython only")
    def test_real_isolated_compile_and_import_in_both_modes(self):
        with tempfile.TemporaryDirectory() as path:
            scratch = Path(path).resolve()
            untrusted = scratch / "untrusted"
            untrusted.mkdir()
            (untrusted / "sitecustomize.py").write_text("raise RuntimeError('unexpected site hook')\n")
            with patch.dict(os.environ, {"PYTHONPATH": str(untrusted), "PYTHONPYCACHEPREFIX": str(untrusted),
                                        "PYTHONOPTIMIZE": "2"}):
                prefix = HISTORY.prewarm_stdlib(ROOT, scratch)
            self.assertTrue(prefix.is_dir())
            self.assertFalse((scratch / "empty-bytecode-cache").exists())
            self.assertFalse(list(untrusted.rglob("*.pyc")))
            self.assertFalse(any(set(f.parts) & {"site-packages", "dist-packages"}
                                 for f in prefix.rglob("*.pyc")))
            for flags in ([], ["-O"]):
                with self.subTest(flags=flags):
                    result = subprocess.run(
                        [sys.executable, "-B", *flags, "-v", "-c", "import pathlib, unittest"],
                        cwd=scratch, env=dict(HISTORY.clean_env(), PYTHONPYCACHEPREFIX=str(prefix)),
                        check=True, text=True, capture_output=True,
                    )
                    matches = [line for line in result.stderr.splitlines()
                               if str(prefix) in line and " matches " in line]
                    self.assertTrue(any("/pathlib" in line for line in matches), result.stderr[-4000:])
                    self.assertTrue(all(("opt-1.pyc" in line) == bool(flags) for line in matches))
                    self.assertFalse(any(str(untrusted) in line or str(ROOT) in line for line in matches))


if __name__ == "__main__":
    unittest.main(verbosity=2)
