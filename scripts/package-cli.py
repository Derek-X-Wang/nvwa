"""Package a locally built CLI with its complete, already-approved asset root.

Standard library only. This does not download, build, sign, or approve a release.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

REPO = Path(__file__).resolve().parent.parent
ASSET_TREES = (
    "characters/mpfb-b1-v1",
    "characters/mpfb-b1-v2",
    "appearances/mpfb-b1-cc0-v1",
    "appearances/mpfb-b1-cc0-v2",
    "appearances/mpfb-b1-cc0-v2-short01-v1",
)
ASSET_FILES = (
    "character.profile.json",
    "fixtures/nvwa-humanoid.glb",
    "fixtures/LICENSE.txt",
    "fixtures/provenance-manifest.json",
)
WORKS = (
    "m1-sequence.nvwa.json",
    "b1-appearance.nvwa.json",
    "b1-character.nvwa.json",
    "b1-short01.nvwa.json",
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_file(source, destination):
    if source.is_symlink() or not source.is_file():
        raise ValueError(f"Expected regular package input: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    destination.chmod(0o644)


def copy_tree(source, destination):
    if source.is_symlink() or not source.is_dir():
        raise ValueError(f"Expected package input directory: {source}")
    for path in sorted(source.rglob("*")):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ValueError(f"Expected regular package input: {path}")
        if path.is_file():
            copy_file(path, destination / path.relative_to(source))


def identity(path):
    metadata = path.lstat()
    return metadata.st_dev, metadata.st_ino


def publish(stage, packed, output, archive):
    """Reserve a new directory, then commit its archive without replacement.

    mkdir and hard-link creation both fail atomically on any existing name.
    Stage and destinations share a parent/filesystem. Only this attempt's
    reserved directory can be removed on a failed publication. No check-then-
    rename may replace either final destination.
    """
    output.mkdir(mode=0o755)
    owned = identity(output)
    try:
        # These children move only into our exclusively reserved namespace.
        for child in stage.iterdir():
            child.rename(output / child.name)
        # The final operation is a no-clobber commit. An unsupported hard-link
        # filesystem also fails safely; there is deliberately no rename fallback.
        os.link(packed, archive)
    except BaseException:
        if identity(output) != owned:
            raise ValueError("Publication failed and output ownership changed; foreign output was preserved")
        shutil.rmtree(output)
        raise


def package(binary, output, repo=REPO):
    """Refuse replacement and publish a fresh complete directory and tar.gz.

    The archive has one top-level directory named after output. Its contents
    and inventory have no dependency on the repository after extraction.
    """
    if output.is_symlink():
        raise ValueError(f"Output already exists: {output}")
    output = output.resolve()
    archive = output.with_name(output.name + ".tar.gz")
    if output.exists() or archive.exists() or archive.is_symlink():
        raise ValueError("Output directory and archive must both be new")
    for relative in ASSET_TREES:
        if output.is_relative_to((repo / "assets" / relative).resolve()):
            raise ValueError("Output must be outside packaged source asset trees")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".nvwa-cli-", dir=output.parent) as temporary:
        stage = Path(temporary) / output.name
        stage.mkdir()
        copy_file(binary, stage / "bin/nvwa-cli")
        (stage / "bin/nvwa-cli").chmod(0o755)
        for relative in ASSET_TREES:
            copy_tree(repo / "assets" / relative, stage / "assets" / relative)
        for relative in ASSET_FILES:
            copy_file(repo / "assets" / relative, stage / "assets" / relative)
        for name in WORKS:
            copy_file(repo / "examples" / name, stage / "works" / name)
        copy_file(repo / "docs/CLI-STANDALONE.md", stage / "README.md")
        copy_file(repo / "docs/agents/cli-authoring.md", stage / "docs/cli-authoring.md")
        # Preserve exact declared build inputs, without claiming that a lockfile
        # is an audit of linked code or proof of the supplied binary's origin.
        for relative in ("Cargo.lock", "Cargo.toml", "crates/nvwa-core/Cargo.toml", "crates/nvwa-cli/Cargo.toml"):
            copy_file(repo / relative, stage / "notices/build-inputs" / relative)
        # The actual binary owns authentication. Do not replace its independent
        # descriptor/payload pins with the packaging inventory below.
        for name in WORKS:
            checked = subprocess.run(
                [str(stage / "bin/nvwa-cli"), "validate", str(stage / "works" / name), str(stage / "assets")],
                cwd=temporary, capture_output=True, text=True, timeout=30,
            )
            if checked.returncode:
                raise ValueError(f"Packaged Work does not authenticate: {name}: {checked.stderr.strip()}")
        inventory = {
            "format": "nvwa-standalone-cli",
            "schema_version": 1,
            "asset_root": "assets",
            "binary": "bin/nvwa-cli",
            "asset_trees": list(ASSET_TREES),
            "notice_status": {
                "assets": "original_license_and_provenance_files_retained",
                "first_party_license": "not_declared_owner_decision_before_public_release",
                "dependency_license_coverage": "not_audited_no_public_release_approval",
            },
            "files": {
                str(path.relative_to(stage)): {"bytes": path.stat().st_size, "sha256": digest(path)}
                for path in sorted(stage.rglob("*")) if path.is_file()
            },
        }
        (stage / "BUNDLE.json").write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n")
        packed = Path(temporary) / "bundle.tar.gz"
        with packed.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
                with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as tar:
                    for path in [stage, *sorted(stage.rglob("*"))]:
                        info = tar.gettarinfo(str(path), arcname=str(Path(output.name) / path.relative_to(stage)))
                        info.mtime = 0
                        info.uid = info.gid = 0
                        info.uname = info.gname = ""
                        info.mode = 0o755 if path.is_dir() or path == stage / "bin/nvwa-cli" else 0o644
                        if path.is_file():
                            with path.open("rb") as source:
                                tar.addfile(info, source)
                        else:
                            tar.addfile(info)
        # Compute the receipt before publication, so a receipt read error cannot
        # turn successful publication into a reported publication failure.
        result = {
            "directory": str(output),
            "archive": str(archive),
            "archive_bytes": packed.stat().st_size,
            "archive_sha256": digest(packed),
            "files": len(inventory["files"]) + 1,
            "uncompressed_bytes": sum(path.stat().st_size for path in stage.rglob("*") if path.is_file()),
        }
        publish(stage, packed, output, archive)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=["debug", "release"], default="release")
    parser.add_argument("--binary", type=Path, help="Built native CLI; default: target/<profile>/nvwa-cli")
    parser.add_argument("--output", type=Path, default=REPO / "dist/nvwa-cli", help="New directory; also writes <output>.tar.gz")
    args = parser.parse_args()
    binary = args.binary or REPO / "target" / args.profile / "nvwa-cli"
    try:
        result = package(binary, args.output)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(1, f"CLI packaging failed: {error}\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
