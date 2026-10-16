"""Rebuild the portable bundle solely from already-approved retained local bytes.

This is a packaging tool, not a generator, network fetcher or candidate build.
It needs the retained private inputs; prepare_ci_inputs.py does not.
"""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STORE = ROOT / ".work/character-approved-20261016"
FULL_REFERENCE_SHA = "98ffb4b7947101bdd2107055beed866d7f040b33f699fb859c090c4c03242636"
COMMON_SHA = "2e8566a4f12de710ead88f6aa2d71fc44e0680761a4f2fdc48a844b6f3534ab7"
CRATES = {"bevy_obj-0.19.0": "894c100f4b3f147d67fab910e176e8c5453593abdfb894a94eb0c93661996dfa",
          "wobj-0.3.0": "28b34b5fbb60f0273c065bfadca18e2decf9e1cac4da09e0ce61b799c05ee631"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def safe(path):
    assert path and not path.startswith("/") and "\\" not in path and ":" not in path
    assert all(part not in ("", ".", "..") for part in path.split("/"))
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True, help="new packaging output directory")
    args = parser.parse_args()
    assert not args.out.exists() and not args.out.is_symlink()
    entries, payloads = [], {}

    def add(name, data, role, license_id, provenance):
        safe(name)
        assert name not in payloads and isinstance(data, bytes)
        payloads[name] = data
        entries.append({"path": name, "sha256": sha(data), "bytes": len(data), "mode": "0644",
                        "role": role, "license": license_id, "provenance": provenance})

    inventory_path = ROOT / "experiments/55-source-character-runtime/upstream-inventory.json"
    inventory = json.loads(inventory_path.read_text())
    assert inventory["candidate_commit"] == "286d33124648501535655a0de811cef55152b9fd"
    source = STORE / "upstream/Humentity"
    actual = {p.relative_to(source).as_posix() for p in source.rglob("*") if p.is_file()}
    assert actual == {entry["path"] for entry in inventory["files"]} and len(actual) == 45
    for entry in inventory["files"]:
        path = source / safe(entry["path"])
        assert path.is_file() and not path.is_symlink()
        data = path.read_bytes()
        assert len(data) == entry["size"]
        assert hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == entry["git_blob_sha1"]
        add("source/humentity/" + entry["path"], data, "original-upstream-source", "MIT OR Apache-2.0",
            {"repository": "https://github.com/emberlightstudios/Humentity", "commit": inventory["candidate_commit"],
             "upstream_path": entry["path"], "git_blob_sha1": entry["git_blob_sha1"]})
    for crate, expected in CRATES.items():
        archive = STORE / "crates" / (crate + ".crate")
        assert archive.is_file() and not archive.is_symlink()
        assert sha(archive.read_bytes()) == expected
        with tarfile.open(archive, "r:gz") as bundle:
            for entry in bundle:
                assert entry.isfile() and not entry.issym() and not entry.islnk()
                safe(entry.name)
                assert entry.name.startswith(crate + "/")
                data = bundle.extractfile(entry).read()
                add("crates/" + entry.name, data, "original-approved-crate-source", "MIT OR Apache-2.0",
                    {"registry": "https://crates.io", "crate": crate, "approved_archive_sha256": expected,
                     "archive_member": entry.name})
        for license_name in ("LICENSE-MIT", "LICENSE-APACHE"):
            assert "crates/" + crate + "/" + license_name in payloads
    # Preserve Humentity's original LICENSE. Its Apache section is a notice,
    # so also include the full standard Apache text already in an approved crate.
    add("licenses/Apache-2.0.txt", payloads["crates/bevy_obj-0.19.0/LICENSE-APACHE"],
        "supplemental-complete-license-text", "Apache-2.0",
        {"copied_from": "crates/bevy_obj-0.19.0/LICENSE-APACHE", "purpose": "full Apache license text supplement"})
    adapter_path = ROOT / "experiments/55-source-character-runtime/evidence/data-adapter.json"
    adapter = json.loads(adapter_path.read_text())
    assert adapter["common_manifest_sha256"] == COMMON_SHA
    derived = ROOT / "experiments/55-source-character-runtime/data"
    assert {p.relative_to(derived).as_posix() for p in derived.rglob("*") if p.is_file()} == set(adapter["derived_files"])
    for name, expected in adapter["derived_files"].items():
        path = derived / safe(name)
        assert path.is_file() and not path.is_symlink() and name != "macro.json"
        data = path.read_bytes()
        assert sha(data) == expected
        add("sample/" + name, data, "geometry-only-derived-input", "CC0-1.0",
            {"adapter_receipt_sha256": sha(adapter_path.read_bytes()), "derived_path": name,
             "common_manifest_sha256": COMMON_SHA, "conversion": adapter["conversions"]})
    reference_path = ROOT / "experiments/56-b1-pose-reference/reference/frozen/manifest.json"
    assert sha(reference_path.read_bytes()) == FULL_REFERENCE_SHA
    reference = json.loads(reference_path.read_text())
    body_ids = sorted(set(range(0, 19158, 307)) | {19157, 18712, 18989, 7633})
    garment_ids = sorted(set(range(0, 1797, 53)) | {1796, 1, 30, 73, 128, 255, 511, 1023})
    cases = []
    for entry in reference["cases"]:
        path = ROOT / entry["path"]
        assert sha(path.read_bytes()) == entry["sha256"]
        full = json.loads(path.read_text())
        case = {"case_id": full["case_id"], "recipe_id": full["recipe_id"], "recipe": full["recipe"],
                "pose_id": full["pose_id"], "pose": full["pose"], "full_case_sha256": entry["sha256"],
                "bones": full["bones"], "body_world": full["body_world"], "rig_world": full["rig_world"],
                "garment_world": full["garment_world"]}
        for kind, prefix, ids in (("body", "", body_ids), ("garment", "garment_", garment_ids)):
            case[kind] = {"source_ids": ids, "positions": [full[prefix + "positions"][index] for index in ids],
                          "rest_positions": [full[("garment_rest_positions" if prefix else "rest_positions")][index] for index in ids],
                          "normals": [full[prefix + "normals"][index] for index in ids],
                          "weights": [full[kind + "_weights"][index] for index in ids]}
        cases.append(case)
    assert len(cases) == 40
    regression = {"schema_version": 1, "scope": "SAMPLED CI REGRESSION ONLY; NOT FULL CHARACTER ACCEPTANCE",
                  "full_reference_manifest_sha256": FULL_REFERENCE_SHA,
                  "common_manifest_sha256": COMMON_SHA, "pose_sha256": reference["pose_sha256"],
                  "reference_driver_sha256": reference["driver_sha256"], "basis": "Blender Z-up metres; row-major matrices multiplying column vectors",
                  "sampling": {"body_source_ids": body_ids, "garment_source_ids": garment_ids,
                               "body_rule": "stride307 plus final vertex and known diagnostic worst IDs18712,18989,7633",
                               "garment_rule": "stride53 plus final vertex and fixed boundary IDs",
                               "all_53_rest_and_pose_bones": True, "full_gate_unchanged": True}, "cases": cases}
    add("regression/reference.json", canonical(regression), "sampled-executed-reference", "CC0-1.0",
        {"full_reference_manifest_sha256": FULL_REFERENCE_SHA, "method": "unchanged value selection from actual Blender outputs; no synthesis"})
    for path, name in ((inventory_path, "upstream-inventory.json"), (adapter_path, "data-adapter.json"),
                       (ROOT / "experiments/56-b1-pose-reference/poses.json", "poses.json")):
        add("provenance/" + name, path.read_bytes(), "provenance-metadata", "CC0-1.0",
            {"repository_path": path.relative_to(ROOT).as_posix()})
    # Canonical regular files only: no links, dirs, pax records, timestamps,
    # host paths or ownership; gzip has zero timestamp and no original filename.
    raw = io.BytesIO()
    with gzip.GzipFile(fileobj=raw, filename="", mode="wb", mtime=0, compresslevel=9) as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            for name in sorted(payloads):
                member = tarfile.TarInfo(name)
                member.size = len(payloads[name])
                member.mode, member.uid, member.gid, member.mtime = 0o644, 0, 0, 0
                member.uname = member.gname = ""
                archive.addfile(member, io.BytesIO(payloads[name]))
    data = raw.getvalue()
    assert len(data) < 10_000_000
    manifest = {"schema_version": 1, "archive": "approved-inputs.tar.gz", "archive_sha256": sha(data),
                "archive_bytes": len(data), "expanded_file_bytes": sum(len(value) for value in payloads.values()),
                "file_count": len(payloads), "source_commit": inventory["candidate_commit"],
                "common_manifest_sha256": COMMON_SHA, "full_reference_manifest_sha256": FULL_REFERENCE_SHA,
                "raw_source_boundary": "45 original Humentity files; two original approved crate source archives extracted unchanged",
                "derived_data_boundary": "only exact13 geometry-only55/data files; same data-adapter hashes; no GPL generator/code or macro.json",
                "reference_boundary": "sampled geometry, complete53 bone matrices across40 cases; CI regression only, full local gate unchanged",
                "tar_policy": "sorted regular files only,0644,uid=gid=mtime=0,empty uname/gname,no pax",
                "gzip_policy": "mtime=0,empty filename,compression9", "files": sorted(entries, key=lambda entry: entry["path"])}
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "approved-inputs.tar.gz").write_bytes(data)
    (args.out / "manifest.json").write_bytes(canonical(manifest))
    print(json.dumps({"archive_sha256": sha(data), "archive_bytes": len(data),
                      "manifest_sha256": sha(canonical(manifest)), "files": len(payloads),
                      "body_sample_ids": len(body_ids), "garment_sample_ids": len(garment_ids)}, indent=2))


if __name__ == "__main__":
    main()
