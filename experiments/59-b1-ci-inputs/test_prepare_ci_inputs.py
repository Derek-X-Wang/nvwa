"""Portable controls exercise the actual extractor, not a parallel fake gate."""
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("portable_ci_inputs", HERE / "prepare_ci_inputs.py")
extractor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extractor)


def archive_fixture(*, name="file.txt", content=b"original", kind=tarfile.REGTYPE, mode=0o644,
                    mtime=0, duplicate=False):
    raw = io.BytesIO()
    with gzip.GzipFile(fileobj=raw, filename="", mode="wb", mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as tar:
            item = tarfile.TarInfo(name)
            item.size = len(content) if kind == tarfile.REGTYPE else 0
            item.mode, item.mtime, item.type = mode, mtime, kind
            item.linkname = "../escape" if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE) else ""
            tar.addfile(item, io.BytesIO(content) if item.isfile() else None)
            if duplicate:
                tar.addfile(item, io.BytesIO(content) if item.isfile() else None)
    payload = raw.getvalue()
    manifest = {"schema_version": 1, "archive_bytes": len(payload),
                "archive_sha256": hashlib.sha256(payload).hexdigest(),
                "file_count": 1, "expanded_file_bytes": len(content),
                "files": [{"path": "file.txt", "sha256": hashlib.sha256(content).hexdigest(),
                           "bytes": len(content), "mode": "0644", "role": "control-original",
                           "license": "CC0-1.0", "provenance": {"kind": "original synthetic control"}}]}
    return payload, manifest


class ExtractorControls(unittest.TestCase):
    def setUp(self):
        parent = ROOT / ".work/b1-ci-inputs/controls"
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=parent)
        self.folder = Path(self.temp.name)
        self.output = self.folder / "new-output"

    def tearDown(self):
        self.temp.cleanup()

    def reject(self, data, manifest, message):
        with self.assertRaisesRegex(extractor.InputError, message):
            extractor.extract_verified(data, manifest, self.output)
        self.assertFalse(self.output.exists())

    def test_real_bundle_positive_all93_hashes_and_modes(self):
        result = extractor.prepare(self.output)
        self.assertEqual(result["files"], 93)
        manifest = json.loads((HERE / "manifest.json").read_text())
        for entry in manifest["files"]:
            path = self.output / entry["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), entry["sha256"])
            self.assertEqual(path.stat().st_mode & 0o777, 0o644)
        sampled = json.loads((self.output / "regression/reference.json").read_text())
        self.assertEqual(len(sampled["cases"]), 40)
        self.assertTrue(all(len(case["bones"]) == 53 for case in sampled["cases"]))
        self.assertTrue({18712, 18989, 7633} <= set(sampled["sampling"]["body_source_ids"]))
        self.assertIn("NOT FULL CHARACTER ACCEPTANCE", sampled["scope"])

    def test_archive_tamper_rejected(self):
        data, manifest = archive_fixture()
        data = data[:20] + bytes([data[20] ^ 1]) + data[21:]
        self.reject(data, manifest, "SHA256")

    def test_member_content_hash_rejected(self):
        data, manifest = archive_fixture()
        manifest["files"][0]["sha256"] = "0" * 64
        self.reject(data, manifest, "member content SHA256")

    def test_path_traversal_tar_rejected(self):
        data, manifest = archive_fixture(name="../escape")
        self.reject(data, manifest, "unsafe archive path")
        self.assertFalse((self.folder / "escape").exists())

    def test_absolute_tar_path_rejected(self):
        self.reject(*archive_fixture(name="/escape"), "unsafe archive path")

    def test_windows_separator_rejected(self):
        self.reject(*archive_fixture(name="dir\\escape"), "unsafe archive path")

    def test_manifest_traversal_rejected(self):
        data, manifest = archive_fixture()
        manifest["files"][0]["path"] = "../escape"
        self.reject(data, manifest, "unsafe archive path")

    def test_tar_symlink_rejected(self):
        self.reject(*archive_fixture(kind=tarfile.SYMTYPE), "links/nonregular")

    def test_tar_hardlink_rejected(self):
        self.reject(*archive_fixture(kind=tarfile.LNKTYPE), "links/nonregular")

    def test_tar_device_rejected(self):
        self.reject(*archive_fixture(kind=tarfile.CHRTYPE), "links/nonregular")

    def test_duplicate_member_rejected(self):
        self.reject(*archive_fixture(duplicate=True), "duplicate archive")

    def test_wrong_permission_rejected(self):
        self.reject(*archive_fixture(mode=0o777), "permission mismatch")

    def test_nonzero_time_rejected(self):
        self.reject(*archive_fixture(mtime=1), "ownership/time")

    def test_existing_output_and_sentinel_preserved(self):
        self.output.mkdir()
        sentinel = self.output / "sentinel"
        sentinel.write_text("keep")
        with self.assertRaisesRegex(extractor.InputError, "already exists"):
            extractor.prepare(self.output)
        self.assertEqual(sentinel.read_text(), "keep")

    def test_output_symlink_and_target_preserved(self):
        target = self.folder / "target"
        target.mkdir()
        (target / "sentinel").write_text("keep")
        self.output.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(extractor.InputError, "already exists"):
            extractor.prepare(self.output)
        self.assertEqual((target / "sentinel").read_text(), "keep")

    def test_output_parent_symlink_rejected(self):
        target = self.folder / "target"
        target.mkdir()
        link = self.folder / "link"
        link.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(extractor.InputError, "symlink ancestor"):
            extractor.prepare(link / "new")
        self.assertEqual(list(target.iterdir()), [])

    def copied_cli(self):
        copy_dir = self.folder / "copied-cli"
        copy_dir.mkdir()
        for name in ("prepare_ci_inputs.py", "manifest.json", "approved-inputs.tar.gz"):
            shutil.copyfile(HERE / name, copy_dir / name)
        return copy_dir

    def test_real_cli_rejects_manifest_tamper_without_output(self):
        copied = self.copied_cli()
        path = copied / "manifest.json"
        path.write_bytes(path.read_bytes() + b" ")
        result = subprocess.run([sys.executable, str(copied / "prepare_ci_inputs.py"), "--out", str(self.output)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("pinned manifest SHA256 mismatch", result.stderr)
        self.assertFalse(self.output.exists())

    def test_real_cli_rejects_archive_tamper_without_output(self):
        copied = self.copied_cli()
        path = copied / "approved-inputs.tar.gz"
        path.write_bytes(path.read_bytes()[:-1] + b"X")
        result = subprocess.run([sys.executable, str(copied / "prepare_ci_inputs.py"), "--out", str(self.output)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("archive SHA256 mismatch", result.stderr)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
