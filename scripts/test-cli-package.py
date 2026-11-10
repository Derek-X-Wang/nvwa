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
        self.assertEqual(bundle["format"], "nvwa-standalone-cli")
        self.assertEqual(bundle["schema_version"], 1)
        self.assertEqual(bundle["asset_trees"], list(PACKAGER.ASSET_TREES))
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

    def test_discovered_v2_sets_apply_and_preserve_full_work_from_the_real_archive(self):
        original = self.home / "works/b1-character.nvwa.json"
        before = self.run_cli("inspect", original)
        contract = self.run_cli("describe-capabilities", original)["cli_contract"]["set_appearance"]
        self.assertEqual(contract["asset_set_id"], "mpfb-b1-cc0-appearance-v2")
        self.assertEqual(contract["current"], before["character"]["appearance"])
        self.assertEqual(len(contract["compatible_sets"]), 2)
        for index, selection in enumerate(contract["compatible_sets"]):
            self.assertEqual(len(selection), 7)
            self.assertEqual([selection[role] for role in ("skin", "eyes", "hair")], [True] * 3)
            envelope = {
                "command_id": f"compatible-{index}", "expected_revision": before["revision"],
                "command": {"type": "set_appearance", "character_id": before["character"]["id"], "appearance": selection},
            }
            command = self.cwd / f"compatible-{index}.json"
            command.write_text(json.dumps(envelope))
            output = self.cwd / f"compatible-work-{index}.json"
            saved = self.cwd / f"compatible-saved-{index}.json"
            self.run_cli("apply", original, command, output)
            self.run_cli("validate", output, self.assets)
            self.run_cli("save", output, saved)
            actual = self.run_cli("inspect", saved)
            expected = json.loads(json.dumps(before))
            expected["revision"] += 1
            expected["character"]["appearance"] = selection
            self.assertEqual(actual, expected)
            self.assertEqual(output.read_bytes(), saved.read_bytes())
        self.assertEqual(self.run_cli("inspect", original), before)

    def test_short01_descriptor_and_all_fourteen_payloads_authenticate_with_hair_and_eyes_off(self):
        document = self.run_cli("inspect", self.home / "works/b1-short01.nvwa.json")
        document["character"]["appearance"].update(eyes=False, hair=False)
        work = self.cwd / "short01-skin-only.json"
        work.write_text(json.dumps(document))
        self.run_cli("validate", work, self.assets)
        directory = self.assets / "appearances/mpfb-b1-cc0-v2-short01-v1"
        manifest = json.loads((directory / "manifest.json").read_bytes())
        self.assertEqual(len(manifest["files"]), 14)
        for relative in ["manifest.json", *manifest["files"]]:
            path = directory / relative
            original = path.read_bytes()
            try:
                path.write_bytes(bytes([original[0] ^ 1]) + original[1:])
                self.run_cli("validate", work, self.assets, error="asset_hash_mismatch")
            finally:
                path.write_bytes(original)
            self.run_cli("validate", work, self.assets)

    def test_contour_creator_discovery_edit_and_save_use_only_relocated_v3_assets(self):
        original = self.cwd / "created-contour.json"
        self.run_cli("new-character-contour", self.assets, original)
        self.run_cli("validate", original, self.assets)
        before = self.run_cli("inspect", original)
        caps = self.run_cli("describe-capabilities", original)
        self.assertEqual(before["schema_version"], 4)
        self.assertEqual(before["profile"]["id"], "nvwa-mpfb-b1-motion-v3")
        self.assertEqual(before["profile"]["backend"]["schema_version"], 4)
        self.assertEqual(len(caps["parameters"]), 9)
        self.assertEqual(before["character"]["parameters"]["cheek_fullness"], 0)
        cheek = caps["cli_contract"]["cheek_fullness"]
        self.assertTrue(cheek["supported"])
        self.assertEqual(cheek["range"], [-1, 1])
        self.assertEqual(cheek["default"], 0)
        self.assertEqual(caps["cli_contract"]["diagnostic_poses"]["targets"]["cheek_fullness"], [
            "cheek-volume-bilateral-decr", "cheek-volume-bilateral-incr",
        ])
        selections = caps["cli_contract"]["set_appearance"]["compatible_sets"]
        self.assertEqual({s["asset_set_id"] for s in selections}, {
            "mpfb-b1-cc0-appearance-v3", "mpfb-b1-cc0-appearance-v3-short01-v1",
        })
        self.assertEqual(len(selections), 2)
        for index, selection in enumerate(selections):
            self.assertEqual(selection["schema_version"], 3)
            for value in (-1, 0, 0.35, 1):
                with self.subTest(appearance=selection["asset_set_id"], cheek=value):
                    envelope = [
                        {"command_id": "contour-shape", "expected_revision": before["revision"],
                         "command": {"type": "set_parameters", "character_id": before["character"]["id"],
                                     "values": {"cheek_fullness": value, "head_width": 0.2}}},
                        {"command_id": "contour-appearance", "expected_revision": before["revision"] + 1,
                         "command": {"type": "set_appearance", "character_id": before["character"]["id"],
                                     "appearance": selection}},
                    ]
                    stem = f"contour-{index}-{value}"
                    command, edited, saved = [self.cwd / (stem + suffix) for suffix in ("-command.json", "-edited.json", "-saved.json")]
                    command.write_text(json.dumps(envelope))
                    self.run_cli("apply", original, command, edited)
                    self.run_cli("validate", edited, self.assets)
                    self.run_cli("save", edited, saved)
                    self.run_cli("validate", saved, self.assets)
                    expected = json.loads(json.dumps(before))
                    expected["revision"] += 2
                    expected["character"]["parameters"].update(cheek_fullness=value, head_width=0.2)
                    expected["character"]["appearance"] = selection
                    self.assertEqual(self.run_cli("inspect", saved), expected)
                    self.assertEqual(edited.read_bytes(), saved.read_bytes())
        self.assertEqual(self.run_cli("inspect", original), before)
        # The existing constructor retains the exact old profile and eight values.
        old = self.cwd / "created-old-character.json"
        self.run_cli("new-character", self.assets, old)
        self.run_cli("validate", old, self.assets)
        document = self.run_cli("inspect", old)
        shipped_old = self.run_cli("inspect", self.home / "works/b1-character.nvwa.json")
        self.assertEqual(document["profile"], shipped_old["profile"])
        self.assertEqual(len(document["character"]["parameters"]), 8)
        self.assertNotIn("cheek_fullness", document["character"]["parameters"])
        self.assertEqual(set(document["character"]["parameters"].values()), {0})

    def test_contour_targets_and_both_appearance_payload_sets_authenticate_without_source_fallback(self):
        document = self.run_cli("inspect", self.home / "works/b1-contour.nvwa.json")
        caps = self.run_cli("describe-capabilities", self.home / "works/b1-contour.nvwa.json")
        work = self.cwd / "contour-skin-only.json"
        for selection in caps["cli_contract"]["set_appearance"]["compatible_sets"]:
            selection.update(eyes=False, hair=False)
            document["character"]["appearance"] = selection
            work.write_text(json.dumps(document))
            self.run_cli("validate", work, self.assets)
            suffix = "-short01-v1" if selection["asset_set_id"].endswith("-short01-v1") else ""
            directory = self.assets / ("appearances/mpfb-b1-cc0-v3" + suffix)
            manifest = json.loads((directory / "manifest.json").read_bytes())
            self.assertEqual(len(manifest["files"]), 14 if suffix else 13)
            for relative in ["manifest.json", *manifest["files"]]:
                path = directory / relative
                original = path.read_bytes()
                try:
                    path.write_bytes(bytes([original[0] ^ 1]) + original[1:])
                    self.run_cli("validate", work, self.assets, error="asset_hash_mismatch")
                finally:
                    path.write_bytes(original)
                self.run_cli("validate", work, self.assets)
        for sign in ("decr", "incr"):
            path = self.assets / f"characters/mpfb-b1-v3/targets/cheek-volume-bilateral-{sign}.target"
            original = path.read_bytes()
            try:
                path.unlink()
                self.run_cli("validate", work, self.assets, error="asset_missing")
                rejected = self.cwd / f"missing-{sign}-contour.json"
                self.run_cli("new-character-contour", self.assets, rejected, error="asset_missing")
                self.assertFalse(rejected.exists())
                path.write_bytes(bytes([original[0] ^ 1]) + original[1:])
                self.run_cli("validate", work, self.assets, error="asset_hash_mismatch")
                self.run_cli("new-character-contour", self.assets, rejected, error="asset_hash_mismatch")
                self.assertFalse(rejected.exists())
                path.unlink()
                outside = self.cwd / f"outside-{sign}-target"
                outside.write_bytes(original)
                path.symlink_to(outside)
                self.run_cli("validate", work, self.assets, error="unsafe_asset_path")
            finally:
                if path.is_symlink():
                    path.unlink()
                path.write_bytes(original)
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
        for base, appearance, work, hair in (
            ("mpfb-b1-v1", "mpfb-b1-cc0-v1", "b1-appearance.nvwa.json", "short04"),
            ("mpfb-b1-v2", "mpfb-b1-cc0-v2", "b1-character.nvwa.json", "short04"),
            ("mpfb-b1-v2", "mpfb-b1-cc0-v2-short01-v1", "b1-short01.nvwa.json", "short01"),
        ):
            document = self.home / "works" / work
            paths = (
                self.assets / "characters" / base / "base.obj",
                self.assets / "characters" / base / "manifest.json",
                self.assets / "appearances" / appearance / "manifest.json",
                self.assets / "appearances" / appearance / "skins/young_caucasian_female2/young_lightskinned_female_diffuse2.png",
                self.assets / "appearances" / appearance / "eyes/materials/brown_eye.png",
                self.assets / "appearances" / appearance / f"hair/{hair}/{hair}_diffuse.png",
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
        output = self.cwd / "refused-package"
        for relative in (
            "appearances/mpfb-b1-cc0-v2/eyes/materials/brown_eye.png",
            "appearances/mpfb-b1-cc0-v2-short01-v1/provenance/makehuman_system_assets.json",
        ):
            payload = source / "assets" / relative
            original = payload.read_bytes()
            for action in ("missing", "corrupt"):
                with self.subTest(payload=relative, action=action):
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


    def test_lower_face_squaring_relocated_v4_range_appearance_and_pair_authentication(self):
        work = self.cwd / "lower-contour.json"
        self.run_cli("new-character-lower-contour", self.assets, work)
        before = self.run_cli("inspect", work)
        caps = self.run_cli("describe-capabilities", work)
        self.assertEqual(before["profile"]["backend"]["schema_version"], 5)
        self.assertEqual(before["profile"]["id"], "nvwa-mpfb-b1-motion-v4")
        self.assertEqual(len(caps["parameters"]), 10)
        self.assertEqual(caps["cli_contract"]["lower_face_squareness"]["range"], [0, 1])
        self.assertIn("rejected", caps["cli_contract"]["lower_face_squareness"]["negative"])
        command = self.cwd / "lower-contour-command.json"
        output = self.cwd / "lower-contour-edited.json"
        for value in [-1, .5, 1]:
            command.write_text(json.dumps({"command_id": "lower-edit", "expected_revision": before["revision"],
                "command": {"type": "set_parameters", "character_id": before["character"]["id"],
                            "values": {"lower_face_squareness": value}}}))
            if value < 0:
                output.write_bytes(b"preserve")
                self.run_cli("apply", work, command, output, error="out_of_range")
                self.assertEqual(output.read_bytes(), b"preserve")
            else:
                self.run_cli("apply", work, command, output)
                self.run_cli("validate", output, self.assets)
                self.assertEqual(self.run_cli("inspect", output)["character"]["parameters"]["lower_face_squareness"], value)
        for selection in caps["cli_contract"]["set_appearance"]["compatible_sets"]:
            self.assertEqual(selection["schema_version"], 4)
            command.write_text(json.dumps({"command_id": "lower-look", "expected_revision": before["revision"],
                "command": {"type": "set_appearance", "character_id": before["character"]["id"], "appearance": selection}}))
            self.run_cli("apply", work, command, output)
            self.run_cli("validate", output, self.assets)
            self.assertEqual(self.run_cli("inspect", output)["character"]["appearance"], selection)
        for suffix in ["decr", "incr"]:
            path = self.assets / f"characters/mpfb-b1-v4/targets/chin-bones-{suffix}.target"
            raw = path.read_bytes()
            try:
                path.unlink()
                self.run_cli("validate", work, self.assets, error="asset_missing")
                self.run_cli("new-character-contour", self.assets, self.cwd / "old-cheek-still-works.json")
                path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
                self.run_cli("validate", work, self.assets, error="asset_hash_mismatch")
            finally:
                path.write_bytes(raw)
            self.run_cli("validate", work, self.assets)

    def test_static_waist_relocated_profile_and_pair_authentication(self):
        work = self.cwd / "waist.json"
        self.run_cli("new-character-waist", self.assets, work)
        before = self.run_cli("inspect", work)
        self.assertEqual(before["profile"]["backend"]["schema_version"], 7)
        self.assertEqual(before["profile"]["id"], "nvwa-mpfb-b1-waist-v1")
        self.assertEqual(before["timeline"], [])
        caps = self.run_cli("describe-capabilities", work)
        self.assertEqual(caps["cli_contract"]["waist_circumference"]["range"], [-1, 1])
        self.assertFalse(caps["cli_contract"]["set_appearance"]["b1_cc0_supported"])
        for suffix in ["decr", "incr"]:
            path = self.assets / f"characters/mpfb-b1-v5/targets/measure-waist-circ-{suffix}.target"
            raw = path.read_bytes()
            try:
                path.unlink()
                self.run_cli("validate", work, self.assets, error="asset_missing")
                self.run_cli("new-character", self.assets, self.cwd / "waist-old-still-works.json")
                path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
                self.run_cli("validate", work, self.assets, error="asset_hash_mismatch")
            finally:
                path.write_bytes(raw)
            self.run_cli("validate", work, self.assets)

    def test_static_leg_profile_and_new_target_survive_relocation(self):
        work = self.cwd / "legs.json"
        self.run_cli("new-character-legs", self.assets, work)
        before = self.run_cli("inspect", work)
        self.assertEqual(before["profile"]["backend"]["schema_version"], 8)
        self.assertEqual(before["profile"]["id"], "nvwa-mpfb-b1-legs-v1")
        self.assertEqual(before["timeline"], [])
        caps = self.run_cli("describe-capabilities", work)
        self.assertTrue(caps["cli_contract"]["leg_shape"]["supported"])
        self.assertEqual(len(caps["parameters"]), 15)
        path = self.assets / "characters/mpfb-b1-v6/targets/measure-calf-circ-incr.target"
        raw = path.read_bytes()
        try:
            path.unlink()
            self.run_cli("validate", work, self.assets, error="asset_missing")
            self.run_cli("new-character-waist", self.assets, self.cwd / "prior-waist-still-works.json")
            path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
            self.run_cli("validate", work, self.assets, error="asset_hash_mismatch")
        finally:
            path.write_bytes(raw)
        self.run_cli("validate", work, self.assets)

    def test_static_upper_body_profile_and_new_target_survive_relocation(self):
        work = self.cwd / "upper-body.json"
        self.run_cli("new-character-upper-body", self.assets, work)
        before = self.run_cli("inspect", work)
        self.assertEqual(before["profile"]["backend"]["schema_version"], 9)
        self.assertEqual(before["profile"]["id"], "nvwa-mpfb-b1-upper-body-v1")
        self.assertEqual(before["timeline"], [])
        caps = self.run_cli("describe-capabilities", work)
        self.assertTrue(caps["cli_contract"]["upper_body_shape"]["supported"])
        self.assertEqual(len(caps["parameters"]), 18)
        path = self.assets / "characters/mpfb-b1-v7/targets/measure-upperarm-circ-incr.target"
        raw = path.read_bytes()
        try:
            path.unlink()
            self.run_cli("validate", work, self.assets, error="asset_missing")
            self.run_cli("new-character-legs", self.assets, self.cwd / "prior-leg-still-works.json")
            path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
            self.run_cli("validate", work, self.assets, error="asset_hash_mismatch")
        finally:
            path.write_bytes(raw)
        self.run_cli("validate", work, self.assets)

    def test_static_hip_contour_profile_and_new_target_survive_relocation(self):
        work = self.cwd / "hip-contour.json"
        self.run_cli("new-character-hip-contour", self.assets, work)
        before = self.run_cli("inspect", work)
        self.assertEqual(before["profile"]["backend"]["schema_version"], 10)
        self.assertEqual(before["profile"]["id"], "nvwa-mpfb-b1-hip-contour-v1")
        self.assertEqual(before["timeline"], [])
        caps = self.run_cli("describe-capabilities", work)
        self.assertTrue(caps["cli_contract"]["hip_contour_shape"]["supported"])
        self.assertEqual(len(caps["parameters"]), 20)
        path = self.assets / "characters/mpfb-b1-v8/targets/buttocks-volume-incr.target"
        raw = path.read_bytes()
        try:
            path.unlink()
            self.run_cli("validate", work, self.assets, error="asset_missing")
            self.run_cli("new-character-upper-body", self.assets, self.cwd / "prior-upper-still-works.json")
            path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
            self.run_cli("validate", work, self.assets, error="asset_hash_mismatch")
        finally:
            path.write_bytes(raw)
        self.run_cli("validate", work, self.assets)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True, help="Actual built native CLI")
    args, remaining = parser.parse_known_args()
    CLIPackageTests.binary = args.binary.resolve(strict=True)
    unittest.main(argv=[sys.argv[0], *remaining], verbosity=2)
