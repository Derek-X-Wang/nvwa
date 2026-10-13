"""Verify the archived packet and its source cohort without dist/.work access."""
import hashlib
import json
from pathlib import Path


def file_bytes(base, name):
    relative = Path(name)
    assert not relative.is_absolute() and ".." not in relative.parts, name
    path = base / relative
    assert path.is_file() and not path.is_symlink(), name
    assert path.resolve().is_relative_to(base.resolve()), name
    return path.read_bytes()


def verify(archive):
    archive = archive.resolve()
    root = archive.parents[2]
    manifest = json.loads(file_bytes(archive, "manifest.json"))
    assert manifest["schema"] == 1
    entries = manifest["archive_files"]
    names = [item["path"] for item in entries]
    assert len(names) == len(set(names)), "duplicate archived paths"
    actual = {str(p.relative_to(archive)) for p in archive.rglob("*") if p.is_file()}
    excluded = {"manifest.json", "ACCEPTANCE.md", "REVIEW.md"}
    assert actual == set(names) | (actual & excluded), "unlisted or missing archive file"
    for item in entries:
        data = file_bytes(archive, item["path"])
        assert len(data) == item["bytes"], item["path"]
        assert hashlib.sha256(data).hexdigest() == item["sha256"], item["path"]
    protected = manifest["accepted_product_inputs"]
    assert len(protected) == 524
    for item in protected:
        assert not item["path"].startswith((".work/", "dist/")), item["path"]
        data = file_bytes(root, item["path"])
        blob = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
        assert hashlib.sha1(blob).hexdigest() == item["accepted_git_blob"], item["path"]
    for item in manifest["experiment_sources"]:
        assert item["path"].startswith(("experiments/33-native-present-metrics/", "experiments/34-web-cold-metrics/"))
        assert hashlib.sha256(file_bytes(root, item["path"])).hexdigest() == item["sha256"], item["path"]
    return {"status": "PASS", "archive_files": len(entries), "accepted_product_inputs": len(protected),
            "experiment_sources": len(manifest["experiment_sources"]),
            "scope": "exact archived bytes/source cohort; measurement meaning reviewed separately"}


if __name__ == "__main__":
    print(json.dumps(verify(Path(__file__).parent), sort_keys=True))
