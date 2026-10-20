"""Exercise the real observer with disposable command boundaries, never Cargo builds."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ci-timing.py"
spec = importlib.util.spec_from_file_location("ci_timing", SCRIPT)
timing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(timing)


def run_bodies(text):
    lines = text.splitlines(keepends=True)
    output = []
    for index, line in enumerate(lines):
        if line.startswith("        run: "):
            value = line.removeprefix("        run: ")
            if value == "|\n":
                body = []
                for following in lines[index+1:]:
                    if following.strip() and not following.startswith("          "):
                        break
                    body.append(following[10:] if following.strip() else "\n")
                value = "".join(body)
            output.append(value)
    return output


class Timing(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="nvwa-timing-control-")
        self.addCleanup(self.temporary.cleanup)
        self.temp = Path(self.temporary.name)
        self.bin = self.temp / "bin"
        self.bin.mkdir()
        self.directory = self.temp / "records"
        self.env = os.environ.copy()
        for name in list(self.env):
            if name.startswith("NVWA_TIMING_") or name in timing.BINDING or name == "GITHUB_STEP_SUMMARY":
                self.env.pop(name)
        self.env.update(NVWA_TIMING_DIR=str(self.directory), PATH=str(self.bin)+os.pathsep+os.environ["PATH"])

    def cargo(self, body):
        path = self.bin / "cargo"
        path.write_text("#!"+sys.executable+"\n"+body)
        path.chmod(0o755)
        return path

    def call(self, *args, **kwargs):
        return subprocess.run([sys.executable, "-B", str(SCRIPT), *args], env=self.env,
                              capture_output=True, **kwargs)

    def records(self):
        return timing.load_records(self.directory)

    def test_original_command_bodies_and_all_job_policies_are_frozen(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        bodies = run_bodies(workflow)
        additions = ["python3 -B scripts/check-portable.py ci-timing-contract\n",
                     "python3 -B scripts/ci-timing.py report\n"]
        retained = [body for body in bodies if body not in additions]
        # Entire original workflow run bodies at 6473b768; independent of the
        # current catalog and shell observer. No test, flag, mode or order may drop.
        self.assertEqual([hashlib.sha256(body.encode()).hexdigest() for body in retained], ORIGINAL_RUN_SHA256)
        self.assertEqual(len(bodies), len(retained)+4)
        self.assertEqual(workflow.count("if: ${{ always() }}\n        shell: bash\n"), 3)
        for literal, count in [("runs-on: ubuntu-24.04", 1), ("runs-on: macos-14", 2),
                               ("timeout-minutes: 15", 1), ("timeout-minutes: 60", 2),
                               ("needs: portable", 2), ("timeout-minutes: 3", 2),
                               ("timeout-minutes: 6", 1), ("timeout-minutes: 5", 1),
                               ("timeout-minutes: 12", 1), ("timeout-minutes: 20", 1)]:
            self.assertEqual(sum(line.strip() == literal for line in workflow.splitlines()), count, literal)
        self.assertIn("pull_request:\n  push:\n    branches: [main]", workflow)
        self.assertIn("NVWA_CI_HEAD_SHA: ${{ github.event.pull_request.head.sha || github.sha }}", workflow)
        self.assertIn("shell: python3 -B scripts/ci-timing.py shell {0}", workflow)
        for name in ["Core, CLI, and diagnostic controls", "macOS CPU tests and Wasm compile check", "macOS B1 source regression and viewer checks"]:
            self.assertEqual(workflow.count("name: "+name+"\n"),1)
        portable = workflow.split("  portable:\n", 1)[1].split("  native-and-wasm:\n", 1)[0]
        catalog = json.loads((ROOT / "scripts/portable-checks.json").read_text())
        self.assertEqual(run_bodies(portable),
                         ["rustup toolchain install 1.95.0 --profile minimal --component rustfmt --component clippy --target wasm32-unknown-unknown\n"]
                         + [f"python3 -B scripts/check-portable.py {group['name']}\n" for group in catalog]
                         + ["python3 -B scripts/ci-timing.py report\n"])
        self.assertNotIn("upload-artifact", workflow)

    def test_exact_argv_cwd_environment_captured_streams_and_nonzero_status(self):
        self.cargo("import json,os,sys\nassert sys.argv[1:]==['test','a b','--','--exact']\nassert os.getcwd()=="+repr(str(ROOT))+"\nassert os.environ['CONTROL_ENV']=='preserved'\nos.write(1,b'out\\x00bytes\\n')\nos.write(2,b'error\\xffbytes\\n')\nsys.exit(101)\n")
        self.env["CONTROL_ENV"] = "preserved"
        result = self.call("run", "--", "cargo", "test", "a b", "--", "--exact", cwd=ROOT)
        self.assertEqual(result.returncode, 101, result.stderr)
        self.assertEqual(result.stdout, b"out\x00bytes\n")
        self.assertEqual(result.stderr, b"error\xffbytes\n")
        rows = self.records()
        self.assertTrue(all(row["exit_code"] == 101 for row in rows))
        evidence = next(row["cargo_observations"] for row in rows if "cargo_observations" in row)
        self.assertEqual(evidence["status"], "unknown")
        self.assertIsNone(evidence["execution_envelope_seconds"])

    def test_large_both_pipe_streams_are_not_truncated_or_deadlocked(self):
        self.cargo("import os\nfor _ in range(128):\n os.write(1,b'x'*65536)\n os.write(2,b'y'*65536)\n")
        result = self.call("run", "--", "cargo", "fetch", timeout=20)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"x"*(128*65536))
        self.assertEqual(result.stderr, b"y"*(128*65536))

    def test_cargo_markers_partial_libtest_and_failed_or_missing_boundaries(self):
        self.cargo("import os,time\nos.write(2,b'  \\x1b[1mFinished\\x1b[0m `test` profile target(s) in 0.12s\\n')\ntime.sleep(.01)\nos.write(2,b'     Running unittests src/lib.rs (target/debug/deps/unit)\\n')\nos.write(1,b'test result: ok. 2 passed; 0 failed; finished in 0.03s\\n')\n")
        result = self.call("run", "--", "cargo", "test")
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = self.records()
        row = next(row for row in rows if "cargo_observations" in row and row["cargo_observations"]["status"] == "observed")
        self.assertAlmostEqual(row["cargo_observations"]["libtest_reported_seconds"], .03)
        self.assertGreater(row["cargo_observations"]["preparation_seconds"], 0)
        self.assertGreaterEqual(row["cargo_observations"]["execution_envelope_seconds"], 0)
        observations = {"finished": [{"at_ns": 5}], "running": [{"at_ns": 7}], "test_results": []}
        failed = timing.cargo_evidence(observations, 0, 10, 101)
        self.assertEqual(failed["status"], "unknown")
        self.assertIsNone(failed["preparation_seconds"])
        self.assertIsNone(timing.cargo_evidence({**observations, "running": []}, 0, 10, 0)["execution_envelope_seconds"])

    def test_truncated_line_suffix_and_marker_cap_are_unknown(self):
        self.cargo("import os\nos.write(2,b'x'*70000+b'   Finished `test` profile target(s) in 0.01s\\n')\nos.write(2,b'     Running unittests src/lib.rs (target/debug/deps/unit)\\n')\nos.write(1,b'test result: ok. 1 passed; finished in 0.01s\\n')\n")
        self.assertEqual(self.call("run", "--", "cargo", "test").returncode, 0)
        evidence = self.records()[0]["cargo_observations"]
        self.assertTrue(evidence["marker_stream_truncated"])
        self.assertEqual(evidence["status"], "unknown")
        self.assertIsNone(evidence["preparation_seconds"])
        self.assertIsNone(evidence["libtest_reported_seconds"])
        self.cargo("import os\nos.write(2,b'  Finished `test` profile target(s) in 0.01s\\n     Running unittests lib.rs (target/debug/deps/unit)\\n')\nos.write(1,b'test result: ok. 1 passed; finished in 0.01s\\n'*4200)\n")
        self.assertEqual(self.call("run", "--", "cargo", "test").returncode, 0)
        evidence = self.records()[-1]["cargo_observations"]
        self.assertTrue(evidence["marker_stream_truncated"])
        self.assertEqual(evidence["status"], "unknown")
        self.assertLessEqual(evidence["libtest_result_lines"], 4096)

    def test_nested_cargo_captured_by_python_and_shell_failure_stops_order(self):
        self.cargo("import os,sys\nos.write(1,b'captured cargo\\n')\nsys.exit(79)\n")
        script = self.temp / "step.sh"
        script.write_text("""python3 -c 'import subprocess; r=subprocess.run(["cargo","test"],capture_output=True); assert r.stdout==b"captured cargo\\n"; raise SystemExit(r.returncode)'
echo must-not-run
""")
        result = self.call("shell", str(script))
        self.assertEqual(result.returncode, 79, result.stderr)
        self.assertNotIn(b"must-not-run", result.stdout)
        rows = self.records()
        self.assertEqual({row["tool"] for row in rows}, {"bash", "cargo"})
        self.assertEqual(len(rows), 2)
        self.assertEqual(sum(row["parent"] is None for row in rows), 1)

    def test_no_python_or_node_shim_and_missing_cargo_is_never_rescued(self):
        self.env["PATH"] = str(self.bin)
        (self.bin / "git").symlink_to(shutil.which("git"))
        (self.bin / "bash").symlink_to(shutil.which("bash"))
        result = self.call("run", "--", "cargo", "test")
        self.assertEqual(result.returncode, 127)
        self.assertNotIn(b"Finished", result.stderr)
        self.assertEqual(timing.TOOLS, ("cargo",))

    def test_proxy_symlink_basename_is_preserved(self):
        original = self.cargo("import os,sys\nassert os.path.basename(sys.argv[0])=='cargo'\n")
        proxy = self.bin / "rustup"
        original.rename(proxy)
        original.symlink_to(proxy)
        result = self.call("run", "--", "cargo", "fetch")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_raw_and_wrapped_signal_statuses_match_for_python_and_shell(self):
        cargo = self.cargo("import os,signal\nos.write(1,b'signal-out\\n')\nos.write(2,b'signal-err\\n')\nos.kill(os.getpid(),signal.SIGTERM)\n")
        raw = subprocess.run([str(cargo), "test"], env=self.env, capture_output=True)
        wrapped = self.call("run", "--", "cargo", "test", timeout=10)
        self.assertEqual(raw.returncode, -signal.SIGTERM)
        self.assertEqual((wrapped.returncode,wrapped.stdout,wrapped.stderr),
                         (raw.returncode,raw.stdout,raw.stderr))
        self.assertIn(-signal.SIGTERM, [row["exit_code"] for row in self.records()])
        # Exercise the real PATH shim as consumed by a Python subprocess caller.
        consumer = "import subprocess,sys; r=subprocess.run(['cargo','test'],capture_output=True); print(r.returncode); sys.stdout.buffer.write(r.stdout); sys.stderr.buffer.write(r.stderr)"
        raw = subprocess.run([sys.executable,"-c",consumer],env=self.env,capture_output=True)
        wrapped = self.call("run", "--", sys.executable,"-c",consumer,timeout=10)
        self.assertEqual((wrapped.returncode,wrapped.stdout,wrapped.stderr),
                         (raw.returncode,raw.stdout,raw.stderr))
        self.assertIn(b"-15",wrapped.stdout)
        # Bash keeps its own shell-visible 128+signal convention.
        shell = self.temp / "signal.sh"
        shell.write_text("cargo test\n")
        raw = subprocess.run(["bash","-e",str(shell)],env=self.env,capture_output=True)
        wrapped = self.call("shell",str(shell),timeout=10)
        self.assertEqual(raw.returncode,128+signal.SIGTERM)
        self.assertEqual(wrapped.returncode,raw.returncode)
        self.assertIn(b"signal-out\n",wrapped.stdout)
        self.assertIn(b"signal-err\n",wrapped.stderr)
        self.cargo("import time\nprint('ready',flush=True)\ntime.sleep(60)\n")
        outcomes = []
        for command in [[str(cargo),"test"], [sys.executable,"-B",str(SCRIPT),"run","--","cargo","test"]]:
            process = subprocess.Popen(command,env=self.env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            self.assertEqual(process.stdout.readline(), b"ready\n")
            process.send_signal(signal.SIGTERM)
            stdout,stderr = process.communicate(timeout=10)
            outcomes.append((process.returncode,stdout,stderr))
        self.assertEqual(outcomes[0],outcomes[1])
        self.assertEqual(outcomes[1][0],-signal.SIGTERM)

    def test_exclusive_totals_union_overlapping_children(self):
        rows = [{"id": "parent", "parent": None, "start_ns": 0, "end_ns": 10_000_000_000,
                 "phase": "shell-mixed", "source": {}, "binding": {}, "exit_code": 0},
                {"id": "one", "parent": "parent", "start_ns": 1_000_000_000, "end_ns": 5_000_000_000,
                 "phase": "dependency-fetch", "exit_code": 0},
                {"id": "two", "parent": "parent", "start_ns": 3_000_000_000, "end_ns": 7_000_000_000,
                 "phase": "compilation-command", "exit_code": 0}]
        self.assertEqual(timing.union_ns([(1,5),(3,7),(9,10)]), 7)
        self.assertIn("| shell-mixed | 4.000 |", timing.summary(rows))
        # Child category sums can overlap each other. Reports state this bound;
        # never sum phase rows into a job total.

    def test_report_missing_corrupt_unknown_nonfinite_and_mixed_records_fail(self):
        self.assertEqual(self.call("report").returncode, 1)
        self.cargo("pass\n")
        self.assertEqual(self.call("run", "--", "cargo", "fetch").returncode, 0)
        rows = self.records()
        target = self.directory / (rows[0]["id"]+".json")
        original = target.read_text()
        bad = ["{", "[]", original.replace('"schema": 1', '"schema": 2')]
        for mutate in [lambda r:r.update(phase="unknown-new-phase"), lambda r:r.update(phase=[]),
                       lambda r:r.update(id=[]), lambda r:r.update(parent=[]), lambda r:r.update(end_ns=-1),
                       lambda r:r.update(status="incomplete"), lambda r:r.update(parent="absent"),
                       lambda r:r.update(parent=r["id"]), lambda r:r["source"].update(head="bad"),
                       lambda r:r.update(cargo_observations={"preparation_seconds":float("nan")}),
                       lambda r:r["binding"].update(GITHUB_RUN_ID="foreign")]:
            changed = copy.deepcopy(rows[0]); mutate(changed); bad.append(json.dumps(changed))
        for value in bad:
            target.write_text(value)
            result = self.call("report")
            self.assertEqual(result.returncode, 1, value)
            self.assertIn(b"UNKNOWN / incomplete", result.stdout)
            self.assertNotIn(b"| dependency-fetch |", result.stdout)
        target.write_text(original)
        summary = self.temp / "summary.md"
        self.env["GITHUB_STEP_SUMMARY"] = str(summary)
        result = self.call("report")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Existing command timing", summary.read_text())
        self.assertIn(b"NVWA_CI_TIMING ", result.stdout)

    def test_queue_cli_repeated_directories_require_one_full_source_per_job(self):
        run = {"id":123, "run_attempt":2, "head_sha":"e"*40,
               "created_at":"2026-10-20T00:00:00Z"}
        names = ["Core, CLI, and diagnostic controls", "macOS CPU tests and Wasm compile check",
                 "macOS B1 source regression and viewer checks"]
        jobs = [{"id":index+1, "name":name, "run_id":123, "run_attempt":2,
                 "head_sha":"e"*40, "created_at":"2026-10-20T00:00:00Z",
                 "started_at":"2026-10-20T00:00:03Z" if index == 0 else "2026-10-20T00:10:07Z",
                 "completed_at":"2026-10-20T00:10:00Z" if index == 0 else "2026-10-20T00:20:00Z"}
                for index,name in enumerate(names)]
        metadata = self.temp / "metadata.json"
        metadata.write_text(json.dumps({"run":run,"jobs":jobs}))
        first,second = self.temp/"first",self.temp/"second"
        first.mkdir(); second.mkdir()
        row = {"schema":1,"id":"1"*32,"parent":None,
               "source":{"head":"a"*40,"tree":"c"*40,"dirty":False},
               "binding":{name:None for name in timing.BINDING},
               "tool":"bash","phase":"shell-mixed","start_ns":1,"end_ns":2,
               "status":"complete","exit_code":0}
        row["binding"].update(GITHUB_WORKFLOW="Bounded CI",GITHUB_RUN_ID="123",
                              GITHUB_RUN_ATTEMPT="2",GITHUB_JOB="portable",
                              GITHUB_SHA="a"*40,NVWA_CI_HEAD_SHA="e"*40)
        (first/"row.json").write_text(json.dumps(row))
        other = copy.deepcopy(row); other["id"]="2"*32
        target = second/"row.json"
        def call(optimized):
            command = [sys.executable,"-B"]+(["-O"] if optimized else [])
            return subprocess.run(command+[str(SCRIPT),"queue",str(metadata),"--records",str(first),"--records",str(second)],
                                  env=self.env,capture_output=True)
        target.write_text(json.dumps(other))
        for optimized in (False,True):
            valid = call(optimized)
            self.assertEqual(valid.returncode,0,valid.stderr)
            joined = json.loads(valid.stdout.splitlines()[0])
            self.assertEqual(joined["timing_records_joined"],2)
            self.assertEqual(joined["checkout_sha"],"a"*40)
            self.assertNotEqual(joined["checkout_sha"],run["head_sha"])
        changes = [lambda r:r["source"].update(head="b"*40),
                   lambda r:r["source"].update(tree="d"*40),
                   lambda r:r["source"].update(dirty=True),
                   lambda r:r["binding"].update(GITHUB_SHA="b"*40)]
        for change in changes:
            changed=copy.deepcopy(other); change(changed)
            target.write_text(json.dumps(changed))
            # Each directory remains independently valid; the join must reject.
            self.assertEqual(len(timing.load_records(first)),1)
            self.assertEqual(len(timing.load_records(second)),1)
            for optimized in (False,True):
                rejected=call(optimized)
                self.assertEqual(rejected.returncode,1,rejected.stdout)
                self.assertEqual(rejected.stdout,b"")
                self.assertIn(b"source/checkout identities",rejected.stderr)
        target.write_text(json.dumps(other))
        for optimized in (False,True):
            self.assertEqual(call(optimized).returncode,0)
        # Valid records for a different job can have their own checkout identity.
        other["source"].update(head="b"*40,tree="d"*40)
        other["binding"].update(GITHUB_SHA="b"*40,GITHUB_JOB="native-and-wasm")
        target.write_text(json.dumps(other))
        for optimized in (False,True):
            self.assertEqual(call(optimized).returncode,0)

    def test_queue_dependency_gate_ready_gap_attempt_and_event_head(self):
        run = {"id": 123, "run_attempt": 2, "head_sha": "e"*40, "created_at": "2026-10-20T00:00:00Z"}
        names = ["Core, CLI, and diagnostic controls", "macOS CPU tests and Wasm compile check", "macOS B1 source regression and viewer checks"]
        jobs = [{"id": index+1, "name": name, "run_id":123, "run_attempt":2, "head_sha":"e"*40,
                 "created_at": "2026-10-20T00:00:00Z" if index == 0 else "2026-10-20T00:10:00Z",
                 "started_at":start, "completed_at": "2026-10-20T00:10:00Z" if index == 0 else "2026-10-20T00:20:00Z"}
                for index,(name,start) in enumerate(zip(names,["2026-10-20T00:00:03Z", "2026-10-20T00:10:07Z", "2026-10-20T00:10:15Z"]))]
        rows = timing.queue_report({"run":run,"jobs":jobs})
        self.assertEqual([r["dependency_gate_seconds"] for r in rows], [0,600,600])
        self.assertEqual([r["ready_to_started_seconds"] for r in rows], [3,7,15])
        self.assertEqual([r["created_to_started_seconds"] for r in rows], [3,7,15])
        self.assertEqual([r["job_key"] for r in rows], ["portable", "native-and-wasm", "b1-source-regression"])
        later = copy.deepcopy(jobs)
        later[1]["created_at"] = "2026-10-20T00:10:02Z"
        row = timing.queue_report({"run":run,"jobs":later})[1]
        self.assertEqual(row["eligible_to_creation_seconds"],2)
        self.assertEqual(row["ready_to_started_seconds"],5)
        for field,value in [("run_id",999),("run_attempt",1),("head_sha","different"),
                            ("started_at","2026-10-20T00:09:59Z")]:
            changed = copy.deepcopy(jobs); changed[1][field]=value
            with self.assertRaises(ValueError):
                timing.queue_report({"run":run,"jobs":changed})
        with self.assertRaises(ValueError):
            timing.queue_report({"run":run,"jobs":jobs+jobs[:1]})
        records = [{"binding": {"GITHUB_RUN_ID":"123", "GITHUB_RUN_ATTEMPT":"2",
                                "GITHUB_JOB":"native-and-wasm", "NVWA_CI_HEAD_SHA":"e"*40,
                                "GITHUB_SHA":"m"*40}, "source":{"head":"m"*40}}]
        self.assertEqual(timing.queue_report({"run":run,"jobs":jobs}, records)[1]["timing_records_joined"], 1)
        for key,value in [("GITHUB_RUN_ID","456"),("GITHUB_RUN_ATTEMPT","1"),
                          ("NVWA_CI_HEAD_SHA","m"*40),("GITHUB_JOB","unknown-job")]:
            changed=copy.deepcopy(records); changed[0]["binding"][key]=value
            with self.assertRaises(ValueError):
                timing.queue_report({"run":run,"jobs":jobs},changed)


ORIGINAL_RUN_SHA256 = ['2633535201ac85bcd48438d308efb8428304d1057586dad9a7f9fbbd358136d9', 'f768e45ccae4351531879991b96334d596198345e0cf895aa686160fdf97a333', 'e5855e8901a2d4a3895e2514bd8a0a8b0dc567510ab155a8436066dac7b8a3b5', '41b996d55dfefee65f945fd49cd1b06ec1dfbcd341430b414a2ca92e8d80494a', '2db8f9d36d7743978f990744869cb845e3c94c18ed6b0eb109ca663f8da61bbf', '0f5f49e2e13f0b23bbc5eca9f2a312e7f6c58fec2753d472756eed46a9c58f92', 'cfa41f09c43e82eafd4a1d65d9f2abe902fa906c8b3210fbd669715c4e5dc2a4', '50cd014ced45830a06ee19771c10ea1574f2c45f9d86aab2a11028c2548a4aa3', '65afc9eaa4b2a3d25c0397d3d8d2d9b8f601eb0c8f6b22b548c7f6b96ff2adfc', '64c2bd552d20cdee49ed761702c4f1d44752ca4e0fdf7c4fec783d5663b60b2f', '6604f190b1082829e17740678d7fdd79f889e57386af4f483c644d46522e8fc1', 'cc6684cfd471f8d5e1b43b215ef695297e77c2a95ad6cb8392bc2662adf74c8a', '2633535201ac85bcd48438d308efb8428304d1057586dad9a7f9fbbd358136d9', '04397b68162f4940de63e839b2a2fa43babcc760adf2156fc09168f0383085bc', 'ccd97d09c5bfd2a196ea3641b266aa452e4775926743a33723aadd5e2c190cbc', 'dc5d8e964ccbb6ffdc9bc1ad430b0b207624e4f43c79d0802b809a41464f214a', '69a46e3289cabf55b80263620a59e1615d721d18590c4d580e92c43266f21766', '2633535201ac85bcd48438d308efb8428304d1057586dad9a7f9fbbd358136d9', '6cdaa5b64e167420b8fdcd2f18d32b29fc6caa4ed039c5dd46e6ad1ce7ba8a13', '5a5831187c185e215376ce647c1d1695cdc8ad368923b954d53bc346946f638c', '8525fb5875a8685926f62522e6e527b5467c17ae110fa5116e28558620109c38', '3f4fc200cf25a55d7faa1d4943c54a75d277971ae095b7a6943f3e20db647411']

if __name__ == "__main__":
    unittest.main(verbosity=2)
