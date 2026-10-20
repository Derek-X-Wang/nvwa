"""Frozen extraction inventory and subprocess controls for the production runner."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "scripts/check-portable.py"
CATALOG = json.loads((ROOT / "scripts/portable-checks.json").read_text())
# SHA-256 of the exact run bodies in the portable job at b03e7a345f01f6f6e940a19cf63906bff807e719.
# Keep this independent of the catalog: a removed mode, argument or command fails.
BASELINE = {
    "source-cli": "edff5938fe77c44a43c3d950055c6820ae1db009280e4afdcc5447a0d53c4529",
    "cli-distribution": "2df083091c4ed42b4641f713a24a07aaa2eecfb14b0444685fbc18f9ebe593eb",
    "b1-inputs": "3774edece15a3e06a63533dae7fd2fa8f269de4c26606ed8bdea23772a5da5f9",
    "motion-comparator": "42e4d257568e6ce317cedf0fb345cc3d64f1e1f85b48d800454be758a61b38dc",
    "diagnostics": "a01087665cb2997e7729228523aa5e50e6e1615a64d4bfb66097720429872dd4",
    "appearance": "6f0751d18b2abccf7467efaa1023f3d540de8e6c9b18d8baf999d492b419e6a9",
    "eye-hair-parameters": "886991f86aa4653e49130cb0e78a707cd9fa7de7c3f1353919f3280b0b4cf75d",
    "authenticated-source": "16ed8dcfd404a549882172394676d01ee0b7398c37e859105bbff3b83d8b3c84",
    "offline-motion": "a9d1e57a0f33194cb29498e09d1c088a2de4f32a579666eec4355793267050eb",
    "frozen-upper-arm": "1cdddaad8dcc99a78b91ca9c5369f14a6217eb7aa0d4f38255124dfe162cd0fd",
}


class PortableChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="nvwa-check-runner-test-")
        self.addCleanup(self.temporary.cleanup)
        self.temp = Path(self.temporary.name).resolve()
        self.bin = self.temp / "bin"
        self.bin.mkdir()
        self.log = self.temp / "commands.log"
        self.env = os.environ.copy()
        for name in ["RUNNER_TEMP", "CARGO_TERM_COLOR", "CARGO_INCREMENTAL",
                     "CARGO_PROFILE_DEV_DEBUG", "CARGO_PROFILE_TEST_DEBUG", "CARGO_BUILD_JOBS"]:
            self.env.pop(name, None)
        self.env.update(PATH=str(self.bin), CHECK_LOG=str(self.log))
        (self.bin / "git").symlink_to(shutil.which("git"))
        # These replace external command boundaries, not the runner or its shell.
        # The production runner reads the real catalog and executes real Bash loops.
        shim = '''#!/bin/bash
tool=${0##*/}
if [[ "$tool" == bash && "$1" == --noprofile ]]; then exec /bin/bash "$@"; fi
printf '%s|%s|%s|%s|%s|%s|%s|%s|%s\\n' "$tool" "$*" "$PWD" "$RUNNER_TEMP" "$CARGO_BUILD_JOBS" "$CARGO_INCREMENTAL" "$CARGO_PROFILE_DEV_DEBUG" "$CARGO_PROFILE_TEST_DEBUG" "$CARGO_TERM_COLOR" >> "$CHECK_LOG"
if [[ "$tool" == "${FAIL_TOOL:-}" && "$*" == *"${FAIL_MATCH:-}"* ]]; then exit 79; fi
'''
        for name in ["bash", "cargo", "python3", "node", "mkdir"]:
            path = self.bin / name
            path.write_text(shim)
            path.chmod(0o755)

    def call(self, *groups, cwd=None, runner=RUNNER):
        return subprocess.run([sys.executable, "-B", str(runner), *groups],
                              cwd=cwd or ROOT, env=self.env, capture_output=True, text=True)

    def records(self):
        return [line.split("|") for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_exact_original_command_inventory_and_order(self):
        self.assertEqual([group["name"] for group in CATALOG], ["runner-contract", *BASELINE])
        self.assertEqual(CATALOG[0]["run"], "python3 -B scripts/test-portable-checks.py\npython3 -B -O scripts/test-portable-checks.py\n")
        for group in CATALOG[1:]:
            self.assertEqual(hashlib.sha256(group["run"].encode()).hexdigest(), BASELINE[group["name"]])

    def test_workflow_uses_every_group_once_and_preserves_timeouts(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        portable = workflow.split("  portable:\n", 1)[1].split("  native-and-wasm:\n", 1)[0]
        calls = [line.strip().removeprefix("run: ") for line in portable.splitlines()
                 if "python3 -B scripts/check-portable.py " in line]
        self.assertEqual(calls, [f"python3 -B scripts/check-portable.py {name}" for name in ["runner-contract", *BASELINE]])
        self.assertEqual(portable.count("timeout-minutes: 3"), 2)
        self.assertIn("timeout-minutes: 6", portable)
        self.assertIn("timeout-minutes: 5", portable)
        self.assertIn("python3 -B scripts/check-portable.py runner-contract", portable)

    def test_all_real_shell_groups_order_modes_defaults_and_local_temp_cleanup(self):
        result = self.call("all")
        self.assertEqual(result.returncode, 0, result.stderr)
        headings = [line.split("]", 1)[0][1:] for line in result.stdout.splitlines() if line.startswith("[")]
        self.assertEqual(headings, ["runner-contract", *BASELINE])
        records = self.records()
        self.assertEqual(records[0][:2], ["python3", "-B scripts/test-portable-checks.py"])
        self.assertEqual(records[1][:2], ["python3", "-B -O scripts/test-portable-checks.py"])
        self.assertEqual(records[2][:2], ["bash", "experiments/27-ci-baseline/check.sh portable"])
        self.assertEqual(records[3][:2], ["cargo", "build -p nvwa-cli --locked --offline"])
        self.assertTrue(all(row[2] == str(ROOT) for row in records))
        self.assertEqual({tuple(row[4:]) for row in records}, {("2", "0", "0", "0", "always")})
        temps = {row[3] for row in records}
        self.assertEqual(len(temps), 1)
        self.assertFalse(Path(temps.pop()).exists())
        for experiment in ["72-b1-admission-controls", "73-high-poly-eyes"]:
            for mode in ["-B", "-B -O"]:
                command = f"{mode} -m unittest discover -s experiments/{experiment} -p test_*.py -v"
                self.assertIn(["python3", command], [row[:2] for row in records])

    def test_selection_uses_catalog_order_and_preserves_inherited_environment_and_temp(self):
        self.env.update(RUNNER_TEMP=str(self.temp), CARGO_BUILD_JOBS="7")
        result = self.call("diagnostics", "cli-distribution", "diagnostics")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([row[0] for row in self.records()], ["cargo", "python3", "python3", "bash"])
        self.assertTrue(all(row[3:5] == [str(self.temp), "7"] for row in self.records()))
        self.assertTrue(self.temp.is_dir())

    def test_unknown_group_fails_before_any_command(self):
        for groups in [("typo",), (), ("all", "diagnostics")]:
            result = self.call(*groups)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertFalse(self.log.exists())

    def test_failure_stops_group_and_later_groups_with_original_status(self):
        self.env.update(FAIL_TOOL="python3", FAIL_MATCH="scripts/test-cli-package.py")
        result = self.call("cli-distribution", "b1-inputs")
        self.assertEqual(result.returncode, 79, result.stderr)
        self.assertEqual(len(self.records()), 2)
        self.assertNotIn("-O", self.records()[-1][1])

    def test_missing_node_and_python_are_errors_never_skipped(self):
        for tool in ["node", "python3"]:
            with self.subTest(tool=tool):
                original = (self.bin / tool).read_text()
                (self.bin / tool).unlink()
                if self.log.exists():
                    self.log.unlink()
                result = self.call("eye-hair-parameters")
                self.assertEqual(result.returncode, 127, result.stderr)
                self.assertIn(f"{tool}: command not found", result.stderr)
                self.assertEqual(len(self.records()), 0 if tool == "node" else 1)
                (self.bin / tool).write_text(original)
                (self.bin / tool).chmod(0o755)

    def test_missing_bash_fails(self):
        (self.bin / "bash").unlink()
        result = self.call("diagnostics")
        self.assertEqual(result.returncode, 1)
        self.assertIn("bash", result.stderr)

    def test_nested_and_outside_invocation_use_script_checkout(self):
        for cwd in [ROOT / "scripts", self.temp]:
            result = self.call("diagnostics", cwd=cwd)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"Invocation cwd: {cwd}", result.stdout)
            self.assertIn(f"checkout={ROOT}", result.stdout)
            self.assertEqual(self.records()[-1][2], str(ROOT))

    def test_detached_clean_and_dirty_identity_without_changing_checkout(self):
        repo = self.temp / "fixture"
        (repo / "scripts").mkdir(parents=True)
        for name in ["check-portable.py", "portable-checks.json"]:
            shutil.copy2(ROOT / "scripts" / name, repo / "scripts" / name)
        def git(*args):
            return subprocess.check_output([shutil.which("git"), "-C", str(repo), *args], text=True).strip()
        git("init", "-q")
        git("add", ".")
        git("-c", "user.name=Runner test", "-c", "user.email=runner@example.invalid",
            "-c", "commit.gpgsign=false", "commit", "-qm", "fixture")
        git("checkout", "--detach", "-q")
        head = git("rev-parse", "HEAD")
        for dirty in [False, True]:
            if dirty:
                (repo / "untracked").write_text("control")
            result = self.call("diagnostics", cwd=self.temp, runner=repo / "scripts/check-portable.py")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"HEAD: {head}; branch: (detached); dirty: {'yes' if dirty else 'no'}", result.stdout)
            self.assertEqual(git("rev-parse", "HEAD"), head)
            self.assertEqual(self.records()[-1][2], str(repo))

    def test_runner_outside_git_checkout_fails_before_commands(self):
        scripts = self.temp / "scripts"
        scripts.mkdir()
        for name in ["check-portable.py", "portable-checks.json"]:
            shutil.copy2(ROOT / "scripts" / name, scripts / name)
        result = self.call("diagnostics", runner=scripts / "check-portable.py")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.log.exists())

    def test_invalid_catalog_cannot_turn_all_into_a_green_noop(self):
        repo = self.temp / "fixture"
        scripts = repo / "scripts"
        scripts.mkdir(parents=True)
        shutil.copy2(RUNNER, scripts / RUNNER.name)
        valid = {"name": "control", "title": "Control", "run": "node --version\n"}
        (scripts / "portable-checks.json").write_text(json.dumps([valid]))
        def git(*args):
            subprocess.run([shutil.which("git"), "-C", str(repo), *args], check=True)
        git("init", "-q")
        git("add", ".")
        git("-c", "user.name=Runner test", "-c", "user.email=runner@example.invalid",
            "-c", "commit.gpgsign=false", "commit", "-qm", "fixture")
        # Prove this copied runner and checkout actually pass before mutations.
        result = self.call("all", runner=scripts / RUNNER.name)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.records()[0][0], "node")
        self.log.unlink()
        invalid = ["{", "[]", "{}", "null", json.dumps([valid, valid])]
        for field in ["name", "title", "run"]:
            for value in ["", "  ", None, 1]:
                invalid.append(json.dumps([{**valid, field: value}]))
            invalid.append(json.dumps([{key: value for key, value in valid.items() if key != field}]))
        for catalog in invalid:
            with self.subTest(catalog=catalog):
                (scripts / "portable-checks.json").write_text(catalog)
                result = self.call("all", runner=scripts / RUNNER.name)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn("FAIL:", result.stderr)
                self.assertFalse(self.log.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
