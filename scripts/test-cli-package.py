"""Exercise the actual CLI against a relocated, extracted final distribution.

Run after building: python3 -B scripts/test-cli-package.py --binary target/debug/nvwa-cli
No download, GPU, server, Rust compilation or GUI is started by this check.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("nvwa_cli_packager", REPO / "scripts/package-cli.py")
PACKAGER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKAGER)


class CLIPackageTests(unittest.TestCase):
    binary = None

    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="nvwa-cli-distribution-")
        cls.scratch = Path(cls.temporary.name).resolve()
        cls.output = cls.scratch / "build/nvwa-cli"
        cls.receipt = PACKAGER.package(cls.binary, cls.output)
        cls.archive = Path(cls.receipt["archive"])
        cls.unpacked = cls.scratch / "unpacked"
        cls.unpacked.mkdir()
        with tarfile.open(cls.archive) as archive:
            archive.extractall(cls.unpacked, filter="data")
        # Remove the assembled directory and move the extracted directory.
        # Every executable/asset path below comes only from this final archive.
        shutil.rmtree(cls.output)
        cls.home = cls.scratch / "relocated package with spaces"
        (cls.unpacked / "nvwa-cli").rename(cls.home)
        cls.cli = cls.home / "bin/nvwa-cli"
        cls.assets = cls.home / "assets"
        cls.cwd = cls.scratch / "unrelated working directory"
        cls.cwd.mkdir()

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def run_cli(self, *arguments, error=None):
        result = subprocess.run(
            [str(self.cli), *map(str, arguments)], cwd=self.cwd,
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "CARGO_MANIFEST_DIR": "/nonexistent/nvwa-source"},
        )
        if error is None:
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            return json.loads(result.stdout)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "")
        diagnostic = json.loads(result.stderr)
        self.assertEqual(diagnostic["code"], error, diagnostic)
        return diagnostic

    def test_actual_archive_inventory_and_notices_are_complete(self):
        bundle = json.loads((self.home / "BUNDLE.json").read_text())
        files = {str(p.relative_to(self.home)) for p in self.home.rglob("*") if p.is_file()}
        self.assertEqual(files, set(bundle["files"]) | {"BUNDLE.json"})
        self.assertTrue(os.access(self.cli, os.X_OK))
        self.assertFalse(any(p.is_symlink() for p in self.home.rglob("*")))
        for relative, record in bundle["files"].items():
            content = (self.home / relative).read_bytes()
            self.assertEqual(len(content), record["bytes"], relative)
            self.assertEqual(hashlib.sha256(content).hexdigest(), record["sha256"], relative)
        for relative in PACKAGER.ASSET_TREES:
            source = REPO / "assets" / relative
            actual = self.assets / relative
            expected_files = {str(p.relative_to(source)) for p in source.rglob("*") if p.is_file()}
            self.assertEqual(expected_files, {str(p.relative_to(actual)) for p in actual.rglob("*") if p.is_file()})
            self.assertIn("licenses/CC0-1.0.txt", expected_files)
            for name in expected_files:
                self.assertEqual((source / name).read_bytes(), (actual / name).read_bytes())
        self.assertIn("not_declared", bundle["notice_status"]["first_party_license"])
        self.assertIn("not_audited", bundle["notice_status"]["dependency_license_coverage"])

    def test_all_shipped_works_authenticate_from_the_relocated_archive(self):
        for name in PACKAGER.WORKS:
            with self.subTest(work=name):
                work = self.home / "works" / name
                before = work.read_bytes()
                self.run_cli("validate", work, self.assets)
                self.assertEqual(work.read_bytes(), before)
                if name.startswith("b1-"):
                    document = self.run_cli("inspect", work)
                    appearance = document["character"]["appearance"]
                    self.assertEqual([appearance[role] for role in ("skin", "eyes", "hair")], [True] * 3)

    def test_creators_and_discovered_appearance_apply_use_only_packaged_assets(self):
        for verb in ("new-b1", "new-b1-motion", "new-character"):
            with self.subTest(creator=verb):
                work = self.cwd / f"{verb}.json"
                self.run_cli(verb, self.assets, work)
                caps = self.run_cli("describe-capabilities", work)
                examples = caps["cli_contract"]["command_examples"]
                envelope = next(e for e in examples if e["command"]["type"] == "set_appearance")
                # Obtain the supported identity/hash from discovery, then select
                # all three roles. No copied or newly invented descriptor pin.
                contract = caps["cli_contract"]["set_appearance"]
                selection = {
                    "type": "b1_cc0",
                    **{key: contract[key] for key in ("schema_version", "asset_set_id", "asset_set_sha256")},
                    "skin": True, "eyes": True, "hair": True,
                }
                envelope["command"]["appearance"] = selection
                command = self.cwd / f"{verb}-command.json"
                command.write_text(json.dumps(envelope))
                edited = self.cwd / f"{verb}-appearance.json"
                self.run_cli("apply", work, command, edited)
                self.run_cli("validate", edited, self.assets)
                actual = self.run_cli("inspect", edited)
                self.assertEqual(actual["character"]["appearance"], selection)
                self.assertEqual(actual["schema_version"], 4)
        work = self.cwd / "original-glb.json"
        self.run_cli("new", self.assets / "character.profile.json", work)
        self.run_cli("validate", work, self.assets)

    def test_preexisting_base_only_distribution_layout_still_fails(self):
        old = self.cwd / "old-base-only-assets"
        old.mkdir()
        shutil.copytree(self.assets / "characters", old / "characters")
        work = self.home / "works/b1-character.nvwa.json"
        diagnostic = self.run_cli("validate", work, old, error="asset_missing")
        self.assertIn("appearances", diagnostic["message"])
        self.run_cli("validate", work, self.assets)
        self.run_cli("validate", work, error="asset_root_required")
        self.run_cli("validate", work, self.home, error="asset_missing")

    def test_removed_corrupt_and_symlinked_payloads_reject_then_restore(self):
        for base, appearance, work in (
            ("mpfb-b1-v1", "mpfb-b1-cc0-v1", "b1-appearance.nvwa.json"),
            ("mpfb-b1-v2", "mpfb-b1-cc0-v2", "b1-character.nvwa.json"),
        ):
            document = self.home / "works" / work
            paths = (
                self.assets / "characters" / base / "base.obj",
                self.assets / "characters" / base / "manifest.json",
                self.assets / "appearances" / appearance / "manifest.json",
                self.assets / "appearances" / appearance / "skins/young_caucasian_female2/young_lightskinned_female_diffuse2.png",
                self.assets / "appearances" / appearance / "eyes/materials/brown_eye.png",
                self.assets / "appearances" / appearance / "hair/short04/short04_diffuse.png",
            )
            for path in paths:
                with self.subTest(payload=str(path.relative_to(self.assets))):
                    original = path.read_bytes()
                    try:
                        path.unlink()
                        self.run_cli("validate", document, self.assets, error="asset_missing")
                        path.write_bytes(bytes([original[0] ^ 1]) + original[1:])
                        self.run_cli("validate", document, self.assets, error="asset_hash_mismatch")
                        path.unlink()
                        outside = self.cwd / "identical-outside-payload"
                        outside.write_bytes(original)
                        path.symlink_to(outside)
                        self.run_cli("validate", document, self.assets, error="unsafe_asset_path")
                    finally:
                        if path.is_symlink():
                            path.unlink()
                        path.write_bytes(original)
                    self.run_cli("validate", document, self.assets)

    def test_payload_authentication_includes_roles_that_are_off(self):
        document = json.loads((self.home / "works/b1-character.nvwa.json").read_text())
        document["character"]["appearance"].update(eyes=False, hair=False)
        work = self.cwd / "skin-only.json"
        work.write_text(json.dumps(document))
        self.run_cli("validate", work, self.assets)
        hair = self.assets / "appearances/mpfb-b1-cc0-v2/hair/short04/short04_diffuse.png"
        original = hair.read_bytes()
        try:
            hair.write_bytes(bytes([original[0] ^ 1]) + original[1:])
            self.run_cli("validate", work, self.assets, error="asset_hash_mismatch")
        finally:
            hair.write_bytes(original)
        self.run_cli("validate", work, self.assets)

    def test_packager_refuses_existing_outputs_and_source_symlinks(self):
        with self.assertRaisesRegex(ValueError, "must both be new"):
            PACKAGER.package(self.binary, self.output)
        destination = self.cwd / "existing-directory"
        destination.mkdir()
        sentinel = destination / "keep"
        sentinel.write_text("preserved")
        with self.assertRaisesRegex(ValueError, "must both be new"):
            PACKAGER.package(self.binary, destination)
        self.assertEqual(sentinel.read_text(), "preserved")
        source = self.cwd / "source-with-symlink"
        source.mkdir()
        (source / "payload").symlink_to(self.cli)
        with self.assertRaisesRegex(ValueError, "Expected regular package input"):
            PACKAGER.copy_tree(source, self.cwd / "copy-destination")

    def test_packager_refuses_incomplete_or_corrupt_inputs_before_publication(self):
        source = self.cwd / "incomplete-source"
        shutil.copytree(self.assets, source / "assets")
        shutil.copytree(self.home / "works", source / "examples")
        PACKAGER.copy_file(self.home / "README.md", source / "docs/CLI-STANDALONE.md")
        PACKAGER.copy_file(self.home / "docs/cli-authoring.md", source / "docs/agents/cli-authoring.md")
        shutil.copytree(self.home / "notices/build-inputs", source, dirs_exist_ok=True)
        payload = source / "assets/appearances/mpfb-b1-cc0-v2/eyes/materials/brown_eye.png"
        original = payload.read_bytes()
        output = self.cwd / "refused-package"
        for action in ("missing", "corrupt"):
            with self.subTest(action=action):
                if action == "missing":
                    payload.unlink()
                else:
                    payload.write_bytes(bytes([original[0] ^ 1]) + original[1:])
                with self.assertRaisesRegex(ValueError, "Packaged Work does not authenticate"):
                    PACKAGER.package(self.binary, output, repo=source)
                self.assertFalse(output.exists())
                self.assertFalse(output.with_name(output.name + ".tar.gz").exists())
                self.assertFalse(list(output.parent.glob(".nvwa-cli-*")))
                payload.write_bytes(original)

    def test_late_destination_collisions_preserve_foreign_data_and_publish_nothing(self):
        for target in ("archive", "directory"):
            for kind in ("file", "directory"):
                with self.subTest(target=target, kind=kind):
                    parent = self.cwd / f"late-{target}-{kind}"
                    parent.mkdir()
                    output = parent / "nvwa-cli"
                    archive = parent / "nvwa-cli.tar.gz"
                    foreign = archive if target == "archive" else output
                    with subprocess.Popen(
                        [sys.executable, "-B", str(REPO / "scripts/package-cli.py"),
                         "--binary", str(self.binary), "--output", str(output)],
                        cwd=self.cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    ) as process:
                        try:
                            deadline = time.monotonic() + 10
                            while not list(parent.glob(".nvwa-cli-*")):
                                if process.poll() is not None or time.monotonic() >= deadline:
                                    self.fail("Packager did not reach its post-preflight staging window")
                                time.sleep(0.005)
                            # Freeze this exact child in the observed staging
                            # window. The collision is in place before it can
                            # proceed to either publication operation.
                            process.send_signal(signal.SIGSTOP)
                            _, status = os.waitpid(process.pid, os.WUNTRACED)
                            self.assertTrue(os.WIFSTOPPED(status))
                            # A real independent writer wins the destination
                            # after the production process's initial checks.
                            sentinel = b"foreign concurrent writer: preserve these exact bytes\n"
                            if kind == "directory":
                                foreign.mkdir()
                                marker = foreign / "sentinel"
                            else:
                                marker = foreign
                            marker.write_bytes(sentinel)
                            process.send_signal(signal.SIGCONT)
                            stdout, stderr = process.communicate(timeout=30)
                        finally:
                            if process.poll() is None:
                                process.kill()
                                process.communicate()
                    observed = {
                        "exit": process.returncode, "stdout": stdout, "stderr": stderr,
                        "package_directory_exists": output.is_dir(),
                        "foreign_sentinel_preserved": marker.is_file() and marker.read_bytes() == sentinel,
                    }
                    self.assertEqual(process.returncode, 1, observed)
                    self.assertTrue(observed["foreign_sentinel_preserved"], observed)
                    # Only the foreign collision may remain. In particular a
                    # failed archive publication must roll back our directory.
                    other = output if target == "archive" else archive
                    self.assertFalse(other.exists(), observed)
                    self.assertEqual(set(parent.iterdir()), {foreign}, observed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True, help="Actual built native CLI")
    args, remaining = parser.parse_known_args()
    CLIPackageTests.binary = args.binary.resolve(strict=True)
    unittest.main(argv=[sys.argv[0], *remaining], verbosity=2)
