#!/usr/bin/env python3
"""Append diagnostic DOM UI to a new disposable copy of an existing Web dist."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def install(source, destination):
    source = source.resolve(strict=True)
    destination = destination.resolve()
    if not source.is_dir():
        raise ValueError("source must be a Web dist directory")
    if destination.exists() or destination.is_relative_to(source):
        raise ValueError("destination must be a new path outside the source dist")
    required = [source / name for name in ["index.html", "nvwa_studio.js", "nvwa_studio_bg.wasm"]]
    if any(not path.is_file() for path in required):
        raise ValueError("source lacks index.html or unchanged nvwa_studio JS/Wasm bundle")
    if any(path.is_symlink() for path in source.rglob("*")):
        raise ValueError("source symlinks are unsupported; provide a self-contained dist copy")
    original = (source / "index.html").read_bytes()
    marker = b"</body>"
    if original.count(marker) != 1:
        raise ValueError("index.html must contain exactly one </body> insertion boundary")
    for name in ["viewport-boundary.js", "viewport-boundary-manifest.json"]:
        if (source / name).exists():
            raise ValueError(f"source already contains diagnostic output: {name}")
    local = Path(__file__).resolve().parent
    panel = (local / "diagnostic-panel.html").read_bytes()
    collector = (local / "collector.js").read_bytes()
    files = sorted(path for path in source.rglob("*") if path.is_file())
    before = {str(path.relative_to(source)): sha256(path) for path in files}
    shutil.copytree(source, destination)
    patched_html = original.replace(marker, panel + b"\n" + marker)
    (destination / "index.html").write_bytes(patched_html)
    intentionally_changed = ["index.html"]
    sidecar = destination / "index.html.gz"
    if sidecar.is_file():
        # Gzip-preferring servers must serve the same diagnostic page. mtime=0
        # avoids recording wall time and makes the gzip bytes repeatable.
        sidecar.write_bytes(gzip.compress(patched_html, compresslevel=9, mtime=0))
        if gzip.decompress(sidecar.read_bytes()) != patched_html:
            raise RuntimeError("patched HTML gzip mismatch; do not serve this output")
        intentionally_changed.append("index.html.gz")
    (destination / "viewport-boundary.js").write_bytes(collector)
    verified = {name: sha256(destination / name) == digest for name, digest in before.items()
                if name not in intentionally_changed}
    if not all(verified.values()):
        raise RuntimeError("copied bundle hash mismatch; do not serve this output")
    manifest = {
        "schemaVersion": 2,
        "sourceDist": str(source), "disposableDist": str(destination),
        "sourceFileSha256": before,
        "diagnosticIndexSha256": sha256(destination / "index.html"),
        "diagnosticIndexGzipSha256": sha256(sidecar) if sidecar.is_file() else None,
        "indexGzipRegenerated": sidecar.is_file(),
        "indexGzipDecompressesToDiagnosticIndex": True if sidecar.is_file() else None,
        "intentionallyChangedSourceFiles": intentionally_changed,
        "diagnosticCollectorSha256": sha256(destination / "viewport-boundary.js"),
        "allOtherSourceFilesUnchanged": all(verified.values()),
        "unchangedFileCount": len(verified),
        "change": "Append diagnostic-panel.html before </body>; regenerate existing index.html.gz with mtime=0; add collector JS and this manifest",
    }
    (destination / "viewport-boundary-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"disposableDist": str(destination), "allOtherSourceFilesUnchanged": True,
                      "intentionallyChangedSourceFiles": intentionally_changed,
                      "indexGzipRegenerated": sidecar.is_file(),
                      "wasmSha256": before["nvwa_studio_bg.wasm"], "unchangedFileCount": len(verified)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    arguments = parser.parse_args()
    install(arguments.source, arguments.destination)
