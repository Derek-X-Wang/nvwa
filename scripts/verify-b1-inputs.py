"""Verify the admitted production B1 inputs without tools, network, or rendering."""
import argparse
import hashlib
import json
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def regular(path):
    require(path.is_file() and not path.is_symlink(), f"Not a regular input: {path}")
    return path.read_bytes()


def verify_assets(root):
    manifest_bytes = regular(root / "manifest.json")
    require(digest(manifest_bytes) == "abcdbc26e03431c740c5fce98de22902089f985823a3c655db2416d042d62b18", "B1 manifest identity changed")
    manifest = json.loads(manifest_bytes)
    require(len(manifest["files"]) == 13, "B1 file set changed")
    total = 0
    for entry in manifest["files"]:
        path = root / entry["path"]
        require(not any(p.is_symlink() for p in path.parents), "Asset symlink ancestor")
        data = regular(path)
        require(len(data) == entry["bytes"] and digest(data) == entry["sha256"], f"B1 asset changed: {entry['path']}")
        total += len(data)
    for notice in ["CC0-1.0.txt", "MPFB-LICENSE.md", "SOURCE-NOTICE.md", "provenance.json"]:
        require(len(regular(root / "licenses" / notice)) > 0, f"Missing B1 notice: {notice}")
    require(total == 5_725_107, "B1 input total changed")
    return total


def verify_source(repo):
    inventory_bytes = regular(repo / "scripts/b1-source-inventory.json")
    require(digest(inventory_bytes) == "bd86d7c597a464eb1b5ab484e3343c70b2fa0986a4c37d9dec3a8875dc90c5e0", "Admitted source inventory changed")
    inventory = json.loads(inventory_bytes)["files"]
    # Version2 admits only the reviewed cached skinning extension and authored
    # motion definitions. The version1 full inventory remains frozen evidence.
    # This is a pinned overlay, never a regenerated inventory or a broad ignore.
    extension_bytes = regular(repo / "scripts/b1-motion-source-inventory.json")
    require(digest(extension_bytes) == "9f1c722aafaa932aa6094ece5b390f7e494c90ab0166dc9deecefa70b61f4cf4", "Admitted motion source extension changed")
    extension = json.loads(extension_bytes)
    require(set(extension) == {"format", "schema_version", "base_inventory_sha256", "files"}, "Motion extension fields changed")
    require(extension["format"] == "nvwa-b1-motion-source-extension" and extension["schema_version"] == 2, "Unsupported motion source extension")
    require(extension["base_inventory_sha256"] == digest(inventory_bytes), "Motion extension baseline mismatch")
    allowed = {"crates/nvwa-b1-adapter/src/lib.rs", "crates/nvwa-b1-adapter/src/motion.rs"}
    require(set(extension["files"]) == allowed, "Motion extension must contain exactly the two reviewed adapter files")
    expected = dict(inventory)
    for path, entry in extension["files"].items():
        require(set(entry) == {"base_sha256", "bytes", "sha256"}, f"Motion extension entry fields changed: {path}")
        require(entry["base_sha256"] == inventory.get(path), f"Motion extension source baseline mismatch: {path}")
        data = regular(repo / path)
        require(type(entry["bytes"]) is int and entry["bytes"] > 0 and len(data) == entry["bytes"] and digest(data) == entry["sha256"], f"Admitted motion source changed: {path}")
        expected[path] = entry["sha256"]
    actual_files = {str(p.relative_to(repo)): digest(regular(p))
                    for directory in ["vendor/humentity", "vendor/bevy_obj", "vendor/wobj", "crates/nvwa-b1-adapter"]
                    for p in (repo / directory).rglob("*") if p.is_file() or p.is_symlink()}
    require(actual_files == expected, "Full admitted source file set or bytes changed")
    vendor = repo / "vendor/humentity"
    provenance = json.loads(regular(vendor / "NVWA-PROVENANCE.json"))
    actual = {str(p.relative_to(vendor)): digest(regular(p)) for p in (vendor / "src").rglob("*") if p.is_file()}
    require(actual == provenance["production_source_code_files"], "Admitted Humentity source inventory changed")
    baseline = provenance["source_code_files"]
    require(set(actual) == set(baseline), "Frozen source file set changed")
    require([name for name in actual if actual[name] != baseline[name]] == ["src/lib.rs"], "Unexpected change outside lazy scheduling registration")
    require(provenance["frozen_source_code_tree_sha256"] == "1c75796828d3af9311ac9bf6f8e8777a77d66838e598544aff7377b908c8a6e8", "Frozen baseline identity changed")
    require(digest(regular(vendor / "production-lazy-resource-scheduling.patch")) == "5e9ff7181f83d87213c37f2b185e2a4b5cbd17bfe6ce37f07a76703137de6dc2", "Lazy scheduling patch changed")
    # The admitted tree digest is relative to src/, while the provenance keys
    # are relative to the package and therefore carry a src/ prefix.
    tree = "".join(f"{name.removeprefix('src/')}\0{sha}\n" for name, sha in sorted(actual.items()))
    require(digest(tree.encode()) == "1638145da5417a7257aa686a7c6d8f96c747c3840c4a2894153155195872038c", "Production source tree changed")
    adapter = repo / "crates/nvwa-b1-adapter"
    data = regular(adapter / "src/lib.rs")
    require(digest(data[:16629]) == "cf130be4e01f869a95b84d088fdf3c8ba9aa2f7dc89b63ec4056eae286aacb8b", "CPU algorithm prefix changed")
    require(digest(regular(adapter / "src/poses.json")) == "8e51c044841eb1c6cb96d583ca927cceb51ddf7d0729f4526f61777c8b7adab2", "Authored poses changed")
    for dependency in ["bevy_obj", "wobj"]:
        for license_name in ["LICENSE-MIT", "LICENSE-APACHE"]:
            require(len(regular(repo / "vendor" / dependency / license_name)) > 0, "Missing dependency license")
    require(len(regular(vendor / "LICENSE")) > 0 and len(regular(vendor / "licenses/Apache-2.0.txt")) > 0, "Missing Humentity license")
    return len(actual)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", type=Path, help="Verify a packaged characters/mpfb-b1-v1 directory too")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parent.parent
    source_count = verify_source(repo)
    total = verify_assets(repo / "assets/characters/mpfb-b1-v1")
    if args.asset_root:
        verify_assets(args.asset_root)
    print(json.dumps({"source_files": source_count, "raw_files": 13, "raw_bytes": total, "packaged_inputs_checked": args.asset_root is not None}))


if __name__ == "__main__":
    main()
