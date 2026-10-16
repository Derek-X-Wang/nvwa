"""Offline, pinned, strict archive extraction. Requires Python's standard library only."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import sys
import tarfile

HERE = Path(__file__).resolve().parent
MANIFEST_SHA256 = "925688915e0ff918ba9c373c3aba39a5dbc1d4b93cabb65a3b51398fdfab3bcb"


class InputError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InputError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_name(name):
    require(isinstance(name, str) and name and not name.startswith("/") and "\\" not in name and ":" not in name,
            "unsafe archive path")
    require(all(part not in ("", ".", "..") for part in name.split("/")), "unsafe archive path")
    require("\0" not in name, "unsafe archive path")
    return name


def safe_new_output(path):
    path = Path(path).absolute()
    require(".." not in path.parts, "output traversal rejected")
    require(not path.exists() and not path.is_symlink(), "output already exists")
    require(path.parent.is_dir(), "output parent must already exist")
    for ancestor in (path, *path.parents):
        require(not ancestor.is_symlink(), "output symlink or symlink ancestor rejected")
    return path


def extract_verified(archive, manifest, output):
    """Real extraction seam. Production CLI additionally pins the manifest bytes."""
    output = safe_new_output(output)
    require(manifest.get("schema_version") == 1, "unsupported manifest schema")
    require(len(archive) == manifest["archive_bytes"] and len(archive) < 10_000_000, "archive size mismatch")
    require(digest(archive) == manifest["archive_sha256"], "archive SHA256 mismatch")
    expected = {}
    for entry in manifest["files"]:
        name = safe_name(entry["path"])
        require(name not in expected, "duplicate manifest path")
        require(entry["mode"] == "0644" and 0 <= entry["bytes"] <= 10_000_000, "unsafe manifest metadata")
        require(entry.get("license") and entry.get("provenance") and entry.get("role"), "missing file provenance")
        expected[name] = entry
    require(len(expected) == manifest["file_count"], "manifest file count mismatch")
    require(sum(entry["bytes"] for entry in expected.values()) == manifest["expanded_file_bytes"] <= 20_000_000,
            "expanded size mismatch")
    # Validate every byte before creating output. Never use tar.extract/all.
    payloads = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
            for member in bundle:
                name = safe_name(member.name)
                require(member.isfile() and not member.issym() and not member.islnk(), "archive links/nonregular members rejected")
                require(not member.pax_headers, "pax headers rejected")
                require(name in expected and name not in payloads, "unexpected or duplicate archive member")
                entry = expected[name]
                require(member.size == entry["bytes"] and member.mode == 0o644, "member size/permission mismatch")
                require(member.uid == member.gid == member.mtime == 0 and member.uname == member.gname == "",
                        "noncanonical archive ownership/time")
                data = bundle.extractfile(member).read(entry["bytes"] + 1)
                require(len(data) == entry["bytes"] and digest(data) == entry["sha256"], "member content SHA256 mismatch")
                payloads[name] = data
    except (tarfile.TarError, OSError, EOFError) as error:
        raise InputError("invalid archive: " + str(error)) from error
    require(set(payloads) == set(expected), "missing archive member")
    require(list(payloads) == sorted(payloads), "noncanonical member order")
    # All content is authenticated. Exclusive root + regular-file creation
    # prevents collisions; input and parent symlinks were rejected above.
    output.mkdir(mode=0o755, exist_ok=False)
    for name, data in payloads.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(target, flags, 0o644)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
        target.chmod(0o644)
        require(stat.S_ISREG(target.lstat().st_mode), "output must remain a regular file")
    return {"status": "portable_inputs_prepared", "files": len(payloads),
            "archive_sha256": manifest["archive_sha256"], "output": str(output),
            "candidate_build_executed": False, "regression_scope": "sampled CI only; full acceptance unchanged"}


def prepare(output):
    manifest_path, archive_path = HERE / "manifest.json", HERE / "approved-inputs.tar.gz"
    for path in (manifest_path, archive_path):
        require(path.is_file() and not path.is_symlink(), "input missing or symlinked")
    manifest_bytes = manifest_path.read_bytes()
    require(digest(manifest_bytes) == MANIFEST_SHA256, "pinned manifest SHA256 mismatch")
    return extract_verified(archive_path.read_bytes(), json.loads(manifest_bytes), output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.out), sort_keys=True))
    except (InputError, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        print("CI_INPUT_REJECTED: " + str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
