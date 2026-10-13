#!/usr/bin/env python3
"""Create owned app scaffolds, or freeze them after root grants identities and leases."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import shutil
import stat
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PRIVATE = REPO / ".work/m11-startup"
BASE = "045d8abc685760d09ba05afec0e40a811a282d1f"


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", type=Path)
    args = parser.parse_args()
    freeze = json.loads(args.freeze.read_text()) if args.freeze else None
    if freeze:
        if freeze.get("root_approved") is not True or freeze.get("base") != BASE:
            parser.error("root approval and exact baseline required")
        for member in freeze["frozen_inputs"]:
            if sha(member["path"]) != member["sha256"]:
                raise ValueError("frozen input mismatch: " + member["path"])
        for name in ("startup_binary", "pixel_binary"):
            if sha(freeze[name]["path"]) != freeze[name]["sha256"]:
                raise ValueError("compiled binary mismatch: " + name)
        if not freeze.get("resolved_features_verified"):
            raise ValueError("actual dependency/feature comparison required before freezing")
        frozen = PRIVATE / "frozen"
        frozen.mkdir(parents=True, exist_ok=True)
        for name in ("startup_binary", "pixel_binary"):
            destination = frozen / Path(freeze[name]["path"]).name
            if destination.exists():
                if sha(destination) != freeze[name]["sha256"]:
                    raise ValueError("refuse changed frozen binary overwrite")
            else:
                shutil.copy2(freeze[name]["path"], destination)
            freeze[name]["frozen_path"] = str(destination)
    launcher = HERE / "bundle_launcher.py"
    sampler = HERE / "sample_owned_pid.py"
    results = []
    for case, basename in [("native-1", "NvwaStartup1"), ("native-2", "NvwaStartup2"), ("pixels", "NvwaTabPixels")]:
        bundle = PRIVATE / "apps" / (basename + ".app")
        macos, resources = bundle / "Contents/MacOS", bundle / "Contents/Resources"
        macos.mkdir(parents=True, exist_ok=True)
        resources.mkdir(parents=True, exist_ok=True)
        evidence = PRIVATE / "captures" / case
        evidence.mkdir(parents=True, exist_ok=True)
        if any(evidence.iterdir()):
            raise ValueError("refuse preparing a bundle whose evidence was used: " + str(evidence))
        script = macos / "NvwaExperiment"
        # LaunchServices does not inherit the terminal's PATH. Pin this installed
        # interpreter, and retain its path/hash in the bundle manifest.
        script.write_text(launcher.read_text().replace("#!/usr/bin/env python3", "#!" + sys.executable, 1))
        script.chmod(script.stat().st_mode | stat.S_IXUSR)
        info = {"CFBundleIdentifier": "dev.nvwa.experiment.m11.base045d8ab." + case.replace("-", ""),
            "CFBundleName": basename, "CFBundleDisplayName": basename,
            "CFBundleExecutable": "NvwaExperiment", "CFBundlePackageType": "APPL",
            "CFBundleVersion": "1", "CFBundleShortVersionString": "0.1.0",
            "NSHighResolutionCapable": True}
        with (bundle / "Contents/Info.plist").open("wb") as stream:
            plistlib.dump(info, stream)
        config = {"approved_frozen": bool(freeze), "case": case, "cwd": str(REPO),
            "evidence": str(evidence), "frozen_inputs": [dict(row) for row in freeze["frozen_inputs"]] if freeze else [],
            "sampler": str(sampler), "environment": {}, "arguments": [],
            "binary": None, "binary_sha256": None}
        if freeze:
            binary = freeze["pixel_binary" if case == "pixels" else "startup_binary"]
            config.update(binary=binary["frozen_path"], binary_sha256=binary["sha256"])
            config["frozen_inputs"] += [{"path": str(sampler), "sha256": sha(sampler)},
                {"path": str(launcher), "sha256": sha(launcher)}]
            if case == "pixels":
                config["environment"] = {"NVWA_PIXEL_OUTPUT": str(evidence)}
            else:
                config["environment"] = {"NVWA_ASSET_ROOT": freeze["asset_root"]}
                config["arguments"] = ["--work", freeze["canonical_work"], "--benchmark", "--smoke",
                    "--smoke-seconds", "12", "--timeout", "55", "--capture", str(evidence / "character.png")]
        (resources / "launch.json").write_text(json.dumps(config, indent=2) + "\n")
        results.append({"case": case, "bundle": str(bundle), "evidence": str(evidence), "launch_permitted": False,
            "python_interpreter": sys.executable, "python_interpreter_sha256": sha(sys.executable),
            "fixed_launcher_sha256": sha(script), "launch_configuration_sha256": sha(resources / "launch.json"),
            "freeze_prepared": bool(freeze), "next_gate": "root exclusive GPU/UI lease"})
    (PRIVATE / "BUNDLE-MANIFEST.json").write_text(json.dumps({"base": BASE, "bundles": results}, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
