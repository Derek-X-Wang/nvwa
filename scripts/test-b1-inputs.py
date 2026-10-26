"""Real production B1 verifier mutation controls; all mutations use temporary copies."""
import contextlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

# Loading the production script must not add bytecode files to the source tree.
sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("nvwa_b1_input_verifier", REPO / "scripts/verify-b1-inputs.py")
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


@contextlib.contextmanager
def source_copy():
    """Copy only the admitted source roots and the production verifier inventory."""
    with tempfile.TemporaryDirectory(prefix="nvwa-b1-source-control-") as temporary:
        repo = Path(temporary).resolve()
        for relative in ["vendor", "crates/nvwa-b1-adapter"]:
            shutil.copytree(REPO / relative, repo / relative, symlinks=True)
        (repo / "scripts").mkdir()
        for name in ["b1-source-inventory.json", "b1-motion-source-inventory.json", "b1-prepared-source-inventory.json"]:
            shutil.copy2(REPO / "scripts" / name, repo / "scripts" / name)
        # Every negative case first proves that its complete copied input passes.
        VERIFIER.verify_source(repo)
        yield repo


@contextlib.contextmanager
def asset_copy():
    with tempfile.TemporaryDirectory(prefix="nvwa-b1-asset-control-") as temporary:
        root = Path(temporary).resolve() / "assets"
        shutil.copytree(REPO / "assets/characters/mpfb-b1-v1", root, symlinks=True)
        VERIFIER.verify_assets(root)
        yield root


def append(path, content=b"\n// B1 mutation control\n"):
    with path.open("ab") as output:
        output.write(content)


def rewrite_json(path, mutate):
    document = json.loads(path.read_text())
    mutate(document)
    path.write_text(json.dumps(document, indent=2) + "\n")


class B1InputControls(unittest.TestCase):
    def test_complete_copied_source_and_assets_pass(self):
        with source_copy() as repo, asset_copy() as root:
            self.assertGreater(VERIFIER.verify_source(repo), 0)
            self.assertEqual(VERIFIER.verify_assets(root), 5_725_107)

    def test_appended_adapter_code_after_old_prefix_is_rejected(self):
        with source_copy() as repo:
            append(repo / "crates/nvwa-b1-adapter/src/lib.rs", b"\npub fn unapproved_adapter_addition() {}\n")
            with self.assertRaises(ValueError):
                VERIFIER.verify_source(repo)

    def test_authored_motion_source_mutation_missing_and_identical_symlink_are_rejected(self):
        for action in ["mutation", "missing", "symlink"]:
            with self.subTest(action=action), source_copy() as repo:
                path = repo / "crates/nvwa-b1-adapter/src/motion.rs"
                if action == "mutation":
                    original = path.read_bytes()
                    self.assertEqual(original.count(b"degrees: 65.0 * amplitude,"), 1, "authored knee seam changed; update this control")
                    path.write_bytes(original.replace(b"degrees: 65.0 * amplitude,", b"degrees: 64.0 * amplitude,"))
                elif action == "missing":
                    path.unlink()
                else:
                    outside = repo / "outside-motion.rs"
                    path.rename(outside)
                    path.symlink_to(outside)
                with self.assertRaises(ValueError):
                    VERIFIER.verify_source(repo)

    def test_motion_extension_missing_corrupt_and_identical_symlink_are_rejected(self):
        for action in ["missing", "corrupt", "symlink"]:
            with self.subTest(action=action), source_copy() as repo:
                path = repo / "scripts/b1-motion-source-inventory.json"
                if action == "missing":
                    path.unlink()
                elif action == "corrupt":
                    append(path, b" ")
                else:
                    outside = repo / "outside-motion-inventory.json"
                    path.rename(outside)
                    path.symlink_to(outside)
                with self.assertRaises(ValueError):
                    VERIFIER.verify_source(repo)

    def test_motion_extension_cannot_admit_extra_files_or_rewrite_base_link(self):
        for action in ["extra", "missing", "wrong_schema", "wrong_base", "wrong_file_base"]:
            with self.subTest(action=action), source_copy() as repo:
                path = repo / "scripts/b1-motion-source-inventory.json"
                document = json.loads(path.read_bytes())
                if action == "extra":
                    document["files"]["vendor/humentity/src/lib.rs"] = dict(document["files"]["crates/nvwa-b1-adapter/src/lib.rs"])
                elif action == "missing":
                    del document["files"]["crates/nvwa-b1-adapter/src/motion.rs"]
                elif action == "wrong_schema":
                    document["schema_version"] = 3
                elif action == "wrong_base":
                    document["base_inventory_sha256"] = "0" * 64
                else:
                    document["files"]["crates/nvwa-b1-adapter/src/lib.rs"]["base_sha256"] = "0" * 64
                path.write_text(json.dumps(document, indent=2) + "\n")
                with self.assertRaises(ValueError):
                    VERIFIER.verify_source(repo)

    def test_prepared_extension_missing_corrupt_and_identical_symlink_are_rejected_then_restored(self):
        for action in ["missing", "corrupt", "symlink"]:
            with self.subTest(action=action), source_copy() as repo:
                path = repo / "scripts/b1-prepared-source-inventory.json"
                original = path.read_bytes()
                if action == "missing":
                    path.unlink()
                elif action == "corrupt":
                    append(path, b" ")
                else:
                    outside = repo / "outside-prepared-inventory.json"
                    path.rename(outside)
                    path.symlink_to(outside)
                # Use the real pinned verifier, including its manifest hash.
                with self.assertRaises(ValueError):
                    VERIFIER.verify_source(repo)
                if path.exists() or path.is_symlink():
                    path.unlink()
                path.write_bytes(original)
                self.assertGreater(VERIFIER.verify_source(repo), 0)

    def test_prepared_extension_wrong_links_schema_and_fields_are_rejected_then_restored(self):
        for action in ["wrong_base", "wrong_parent", "wrong_schema", "wrong_format", "extra_field", "missing_field"]:
            with self.subTest(action=action), source_copy() as repo:
                path = repo / "scripts/b1-prepared-source-inventory.json"
                original = path.read_bytes()
                document = json.loads(original)
                if action == "wrong_base":
                    document["base_inventory_sha256"] = "0" * 64
                elif action == "wrong_parent":
                    document["motion_inventory_sha256"] = document["base_inventory_sha256"]
                elif action == "wrong_schema":
                    document["schema_version"] = 2
                elif action == "wrong_format":
                    document["format"] = "nvwa-b1-motion-source-extension"
                elif action == "extra_field":
                    document["unapproved"] = True
                else:
                    del document["change"]
                path.write_text(json.dumps(document, indent=2) + "\n")
                with self.assertRaises(ValueError):
                    VERIFIER.verify_source(repo)
                path.write_bytes(original)
                self.assertGreater(VERIFIER.verify_source(repo), 0)

    def test_prepared_extension_exact_files_and_immediate_bases_are_pinned_then_restored(self):
        for action in ["extra", "missing", "old_lib_base", "wrong_readme_base", "nonabsent_prepared_base", "extra_entry_field", "missing_entry_field"]:
            with self.subTest(action=action), source_copy() as repo:
                path = repo / "scripts/b1-prepared-source-inventory.json"
                original = path.read_bytes()
                document = json.loads(original)
                entries = document["files"]
                lib = entries["crates/nvwa-b1-adapter/src/lib.rs"]
                prepared = entries["crates/nvwa-b1-adapter/src/prepared.rs"]
                if action == "extra":
                    entries["vendor/humentity/src/lib.rs"] = dict(lib)
                elif action == "missing":
                    del entries["crates/nvwa-b1-adapter/src/prepared.rs"]
                elif action == "old_lib_base":
                    # The immediate parent is V2, not the old V1 lib identity.
                    lib["base_sha256"] = json.loads((repo / "scripts/b1-source-inventory.json").read_bytes())["files"]["crates/nvwa-b1-adapter/src/lib.rs"]
                elif action == "wrong_readme_base":
                    entries["crates/nvwa-b1-adapter/README.md"]["base_sha256"] = None
                elif action == "nonabsent_prepared_base":
                    prepared["base_sha256"] = "0" * 64
                elif action == "extra_entry_field":
                    prepared["unapproved"] = True
                else:
                    del prepared["sha256"]
                path.write_text(json.dumps(document, indent=2) + "\n")
                with self.assertRaises(ValueError):
                    VERIFIER.verify_source(repo)
                path.write_bytes(original)
                self.assertGreater(VERIFIER.verify_source(repo), 0)

    def test_prepared_extension_byte_counts_are_pinned_then_restored(self):
        for byte_count in [0, -1, True, 24229.0, "24229", None, 24230]:
            with self.subTest(byte_count=byte_count), source_copy() as repo:
                path = repo / "scripts/b1-prepared-source-inventory.json"
                original = path.read_bytes()
                document = json.loads(original)
                document["files"]["crates/nvwa-b1-adapter/src/prepared.rs"]["bytes"] = byte_count
                path.write_text(json.dumps(document, indent=2) + "\n")
                with self.assertRaises(ValueError):
                    VERIFIER.verify_source(repo)
                path.write_bytes(original)
                self.assertGreater(VERIFIER.verify_source(repo), 0)

    def test_prepared_revision_each_source_mutation_missing_and_symlink_are_rejected_then_restored(self):
        for relative in ["crates/nvwa-b1-adapter/src/lib.rs", "crates/nvwa-b1-adapter/README.md", "crates/nvwa-b1-adapter/src/prepared.rs"]:
            for action in ["mutation", "missing", "symlink"]:
                with self.subTest(path=relative, action=action), source_copy() as repo:
                    path = repo / relative
                    original = path.read_bytes()
                    if action == "mutation":
                        data = bytearray(original)
                        data[-1] ^= 1
                        path.write_bytes(data)
                    elif action == "missing":
                        path.unlink()
                    else:
                        outside = repo / "outside-prepared-source"
                        path.rename(outside)
                        path.symlink_to(outside)
                    with self.assertRaises(ValueError):
                        VERIFIER.verify_source(repo)
                    if path.exists() or path.is_symlink():
                        path.unlink()
                    path.write_bytes(original)
                    self.assertGreater(VERIFIER.verify_source(repo), 0)

    def test_actual_pose_lookup_mutated_to_always_neutral_is_rejected(self):
        with source_copy() as repo:
            path = repo / "crates/nvwa-b1-adapter/src/poses.rs"
            source = path.read_text()
            lookup = ".find(|pose| pose.pose_id == pose_id)"
            self.assertEqual(source.count(lookup), 1, "production lookup seam changed; update this control")
            path.write_text(source.replace(lookup, '.find(|pose| pose.pose_id == "neutral")'))
            with self.assertRaises(ValueError):
                VERIFIER.verify_source(repo)

    def test_each_vendored_dependency_parser_change_is_rejected(self):
        for relative in ["vendor/bevy_obj/src/lib.rs", "vendor/bevy_obj/src/mesh.rs", "vendor/wobj/src/obj/parser.rs", "vendor/wobj/src/mtl/parser.rs"]:
            with self.subTest(path=relative), source_copy() as repo:
                append(repo / relative)
                with self.assertRaises(ValueError):
                    VERIFIER.verify_source(repo)

    def test_extra_source_files_in_each_admitted_root_are_rejected(self):
        for relative in ["vendor/humentity/src/unapproved.rs", "vendor/bevy_obj/src/unapproved.rs", "vendor/wobj/src/unapproved.rs", "crates/nvwa-b1-adapter/src/unapproved.rs"]:
            with self.subTest(path=relative), source_copy() as repo:
                (repo / relative).write_text("pub fn unapproved_source() {}\n")
                with self.assertRaises(ValueError):
                    VERIFIER.verify_source(repo)

    def test_missing_source_files_in_each_admitted_root_are_rejected(self):
        for relative in ["vendor/humentity/src/helpers.rs", "vendor/bevy_obj/src/mesh.rs", "vendor/wobj/src/obj/parser.rs", "crates/nvwa-b1-adapter/src/poses.rs"]:
            with self.subTest(path=relative), source_copy() as repo:
                (repo / relative).unlink()
                with self.assertRaises(ValueError):
                    VERIFIER.verify_source(repo)

    def test_non_rust_source_changes_are_rejected(self):
        with source_copy() as repo:
            append(repo / "vendor/humentity/src/gpu/crowd_skin.wgsl", b"\n// unapproved shader change\n")
            with self.assertRaises(ValueError):
                VERIFIER.verify_source(repo)

    def test_scheduling_patch_corruption_is_rejected(self):
        with source_copy() as repo:
            append(repo / "vendor/humentity/production-lazy-resource-scheduling.patch", b"\n# unapproved patch change\n")
            with self.assertRaises(ValueError):
                VERIFIER.verify_source(repo)

    def test_baseline_provenance_map_cannot_be_changed_behind_retained_tree_id(self):
        with source_copy() as repo:
            path = repo / "vendor/humentity/NVWA-PROVENANCE.json"
            # In the old gate this retains the same sole baseline/production
            # difference (src/lib.rs), while corrupting the claimed baseline.
            rewrite_json(path, lambda document: document["source_code_files"].__setitem__("src/lib.rs", "0" * 64))
            with self.assertRaises(ValueError):
                VERIFIER.verify_source(repo)

    def test_missing_and_corrupt_pinned_source_inventory_are_rejected(self):
        for action in ["missing", "corrupt"]:
            with self.subTest(action=action), source_copy() as repo:
                path = repo / "scripts/b1-source-inventory.json"
                if action == "missing":
                    path.unlink()
                else:
                    append(path, b" ")
                with self.assertRaises(ValueError):
                    VERIFIER.verify_source(repo)

    def test_source_symlink_to_identical_outside_bytes_is_rejected(self):
        with source_copy() as repo:
            path = repo / "crates/nvwa-b1-adapter/src/poses.rs"
            outside = repo / "outside-poses.rs"
            path.rename(outside)
            path.symlink_to(outside)
            with self.assertRaises(ValueError):
                VERIFIER.verify_source(repo)

    def test_dependency_directory_symlink_to_identical_source_is_rejected(self):
        with source_copy() as repo:
            path = repo / "vendor/wobj/src"
            outside = repo / "outside-wobj-source"
            path.rename(outside)
            path.symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                VERIFIER.verify_source(repo)

    def test_missing_and_corrupt_asset_manifest_are_rejected(self):
        for action in ["missing", "corrupt"]:
            with self.subTest(action=action), asset_copy() as root:
                path = root / "manifest.json"
                if action == "missing":
                    path.unlink()
                else:
                    append(path, b" ")
                with self.assertRaises(ValueError):
                    VERIFIER.verify_assets(root)

    def test_missing_and_corrupt_raw_asset_are_rejected(self):
        for action in ["missing", "corrupt"]:
            with self.subTest(action=action), asset_copy() as root:
                path = root / "targets/chin-jaw-drop-incr.target"
                if action == "missing":
                    path.unlink()
                else:
                    data = bytearray(path.read_bytes())
                    data[0] ^= 1
                    path.write_bytes(data)
                with self.assertRaises(ValueError):
                    VERIFIER.verify_assets(root)

    def test_raw_asset_symlink_to_identical_outside_bytes_is_rejected(self):
        with asset_copy() as root:
            path = root / "targets/chin-jaw-drop-incr.target"
            outside = root.parent / "outside-target"
            path.rename(outside)
            path.symlink_to(outside)
            with self.assertRaises(ValueError):
                VERIFIER.verify_assets(root)

    def test_asset_directory_symlink_to_identical_files_is_rejected(self):
        with asset_copy() as root:
            path = root / "targets"
            outside = root.parent / "outside-targets"
            path.rename(outside)
            path.symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                VERIFIER.verify_assets(root)

    def test_missing_license_notice_is_rejected(self):
        with asset_copy() as root:
            (root / "licenses/CC0-1.0.txt").unlink()
            with self.assertRaises(ValueError):
                VERIFIER.verify_assets(root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
