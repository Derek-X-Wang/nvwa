#!/usr/bin/env python3
"""Create a fresh, frozen experiment workspace; never mutate the source checkout."""
import argparse, hashlib, io, json, pathlib, subprocess, tarfile

BASE = "11fc789e898119e0ed2b423f8a909dacb547f772"
PIN = "5c874d51eeb3de70e735c8ce87a59a7dedd47675"
HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
DEFAULT = REPO / ".work/m11-ui/generated"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(root):
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob("*")) if p.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT)
    args = parser.parse_args()
    output = args.output.resolve()
    allowed = (REPO / ".work/m11-ui").resolve()
    if not output.is_relative_to(allowed):
        parser.error(f"output must be under task-owned {allowed}")
    if output.exists():
        parser.error(f"refusing to replace existing workspace: {output}")
    archive = subprocess.check_output(["git", "archive", BASE], cwd=REPO)
    output.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(output, filter="data")
    originals = manifest(output)
    overlay = HERE / "overlay"
    replacements = {}
    for source in sorted(overlay.rglob("*")):
        if source.is_file():
            relative = source.relative_to(overlay)
            target = output / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
            replacements[str(relative)] = {"original_sha256": originals.get(str(relative)), "overlay_sha256": sha(target)}
    # Cargo manifest and lock remain frozen until root integrates the approved dependency.
    result = {"base": BASE, "dependency_git_rev": PIN, "output": str(output),
              "original_files": originals, "overlay_files": replacements,
              "manifest_integration": "ROOT REQUIRED: add proposed craft-ui dependency and generate Cargo.lock before compilation"}
    (output.parent / (output.name + "-manifest.json")).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"workspace": str(output), "manifest": str(output.parent / (output.name + "-manifest.json")),
                      "files": len(originals), "overlays": list(replacements)}, indent=2))


if __name__ == "__main__":
    main()
