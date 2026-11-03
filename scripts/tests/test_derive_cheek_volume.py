#!/usr/bin/env python3
"""Independent four-source witness and bounded B1 V3 asset checks."""

import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "assets/characters/mpfb-b1-v3"
SOURCE = BASE / "provenance/source/data/targets/cheek"
SPEC = importlib.util.spec_from_file_location("cheek_derivation", ROOT / "scripts/derive-cheek-volume.py")
DERIVE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DERIVE)

# Independent source identities; expected rows below come from these originals,
# never the product target catalogue, derivation parser, or derived output.
ORIGINALS = {
    "l-cheek-volume-decr.target.gz": (787, "202ff036e39abea154e0896ad34641184c5e8b77610dca9e1e8e4ce4a5db1bc4", 3015, "d88cedb8d78e4ac0009d83e425245cb8f584c064b9c3be3419d167d1c22b3539", 194, 152),
    "r-cheek-volume-decr.target.gz": (765, "ea12455c7a85e7b3b5e6e4882b4b68823a00bcaef4ea048cc49be452a139c1bc", 2670, "ca0576cfb9a49216f6844a97d6347eaf662b56b1c165f5938661c91d1d04d617", 194, 152),
    "l-cheek-volume-incr.target.gz": (1274, "75bf330b96d0036c46f779ed003782c7380c77dd06c14fd80f1fa20a5093fee1", 4150, "7a47a6a0121657092266df2a27ec6e134462642fd3f781ee47daeec40d1426fd", 229, 210),
    "r-cheek-volume-incr.target.gz": (1288, "4df3e61e843c2d3381ef534e90d347b6b8ea763428d69eba8ef2ed5ab0affb8c", 4086, "95e57c5e1313c118d5e3c4e43ec3d0dd9952957e5ba1bcbed1c8027d40940e43", 229, 210),
}
GENERATED = {
    "decr": (5685, "aeab40d480502a05d4be4a9d9b9589212bbddf4a2da7f2418bc4ffc4fed2a487", 388, 304),
    "incr": (8236, "3eba8dad1ee2d2bf01cb49f1cd50a50cae7a947b37f556405bf173fa26053a84", 458, 420),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def independent_rows(data):
    rows = {}
    for line in data.decode("ascii").splitlines():
        # This independent parser retains source strings and validates geometry.
        match = re.fullmatch(r"([0-9]+)\s+(\S+)\s+(\S+)\s+(\S+)", line)
        if match is None:
            raise ValueError("invalid source row")
        tokens = match.groups()
        vertex = int(tokens[0])
        if vertex in rows or not 0 <= vertex < 19158:
            raise ValueError("duplicate or out-of-range source ID")
        if not all(math.isfinite(float(token)) for token in tokens[1:]):
            raise ValueError("nonfinite source displacement")
        rows[vertex] = tokens
    return rows


def independent_sources():
    result = {}
    for name, expected in ORIGINALS.items():
        compressed = (SOURCE / name).read_bytes()
        if (len(compressed), digest(compressed)) != expected[:2]:
            raise ValueError("compressed source identity mismatch")
        expanded = gzip.decompress(compressed)
        if (len(expanded), digest(expanded)) != expected[2:4]:
            raise ValueError("expanded source identity mismatch")
        rows = independent_rows(expanded)
        nonzero = sum(any(float(v) != 0 for v in r[1:]) for r in rows.values())
        if (len(rows), nonzero) != expected[4:]:
            raise ValueError("source row counts mismatch")
        result[name] = rows
    return result


def check_full_union(sign, data):
    sources = independent_sources()
    left = sources[f"l-cheek-volume-{sign}.target.gz"]
    right = sources[f"r-cheek-volume-{sign}.target.gz"]
    if set(left).intersection(right):
        raise ValueError("source sides overlap")
    expected = dict(left)
    expected.update(right)
    actual = independent_rows(data)
    if actual != expected:
        raise ValueError("not the full source union with unchanged tokens")
    if list(actual) != sorted(expected):
        raise ValueError("source rows are not sorted")
    if not data.endswith(b"\n"):
        raise ValueError("missing final LF")
    nonzero = sum(any(float(v) != 0 for v in r[1:]) for r in actual.values())
    if (len(actual), nonzero) != GENERATED[sign][2:]:
        raise ValueError("union row counts mismatch")
    if (len(data), digest(data)) != GENERATED[sign][:2]:
        raise ValueError("generated identity mismatch")


class CheekVolumeDerivation(unittest.TestCase):
    def test_four_originals_and_both_full_union_outputs(self):
        originals = independent_sources()
        self.assertEqual(len(originals), 4)
        for sign in ("decr", "incr"):
            data = (BASE / f"targets/cheek-volume-bilateral-{sign}.target").read_bytes()
            check_full_union(sign, data)
        DERIVE.run(SOURCE, BASE / "targets")

    def test_independent_witness_rejects_wrong_side_missing_row_and_sign_swap(self):
        originals = independent_sources()
        decr = (BASE / "targets/cheek-volume-bilateral-decr.target").read_bytes()
        incr = (BASE / "targets/cheek-volume-bilateral-incr.target").read_bytes()
        left = originals["l-cheek-volume-decr.target.gz"]
        wrong_side = b"".join((" ".join(r) + "\n").encode() for r in left.values())
        mutations = {
            "wrong-side-only": wrong_side,
            "missing-row": b"\n".join(decr.splitlines()[:-1]) + b"\n",
            "sign-swap": incr,
        }
        for name, data in mutations.items():
            with self.subTest(mutation=name), self.assertRaisesRegex(ValueError, "full source union"):
                check_full_union("decr", data)

    def test_independent_witness_rejects_half_amplitude_and_extra_scales(self):
        for sign in ("decr", "incr"):
            source = (BASE / f"targets/cheek-volume-bilateral-{sign}.target").read_text("ascii")
            for factor in (0.5, 0.1, 2.0):
                lines = []
                for line in source.splitlines():
                    tokens = line.split()
                    lines.append(tokens[0] + " " + " ".join(str(float(t) * factor) for t in tokens[1:]))
                with self.subTest(sign=sign, scale=factor), self.assertRaisesRegex(ValueError, "full source union"):
                    check_full_union(sign, ("\n".join(lines) + "\n").encode())

    def test_independent_witness_rejects_numeric_reformatting_and_zero_stripping(self):
        data = (BASE / "targets/cheek-volume-bilateral-decr.target").read_bytes()
        no_zero = b"\n".join(line for line in data.splitlines() if any(float(t) != 0 for t in line.split()[1:])) + b"\n"
        reformatted = data.replace(b".004", b"0.004", 1)
        for mutation in (no_zero, reformatted):
            with self.assertRaisesRegex(ValueError, "full source union"):
                check_full_union("decr", mutation)

    def test_mismatched_compressed_source_hash_prevents_any_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            tmp = Path(temporary)
            shutil.copytree(SOURCE, tmp / "source")
            path = tmp / "source/l-cheek-volume-decr.target.gz"
            data = bytearray(path.read_bytes())
            data[-1] ^= 1
            path.write_bytes(data)
            output = tmp / "output"
            with self.assertRaisesRegex(ValueError, "compressed: SHA256 mismatch"):
                DERIVE.run(tmp / "source", output, True)
            self.assertFalse(output.exists())

    def test_mismatched_expanded_hash_prevents_any_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            tmp = Path(temporary)
            shutil.copytree(SOURCE, tmp / "source")
            name = "l-cheek-volume-decr.target.gz"
            path = tmp / "source" / name
            expanded = gzip.decompress(path.read_bytes()).replace(b"-.004", b"-.005", 1)
            compressed = gzip.compress(expanded, mtime=0)
            path.write_bytes(compressed)
            expected = list(DERIVE.SOURCES[name])
            expected[:2] = [len(compressed), digest(compressed)]
            with patch.dict(DERIVE.SOURCES, {name: tuple(expected)}):
                with self.assertRaisesRegex(ValueError, "expanded: SHA256 mismatch"):
                    DERIVE.run(tmp / "source", tmp / "output", True)
            self.assertFalse((tmp / "output").exists())

    def test_existing_unique_output_is_never_overwritten_on_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)
            sentinel = out / "cheek-volume-bilateral-incr.target"
            sentinel.write_bytes(b"unique existing output\n")
            with self.assertRaisesRegex(ValueError, "refusing overwrite"):
                DERIVE.run(SOURCE, out, True)
            self.assertEqual(sentinel.read_bytes(), b"unique existing output\n")
            self.assertEqual(list(out.iterdir()), [sentinel])

    def test_write_then_check_is_deterministic_and_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "targets"
            DERIVE.run(SOURCE, out, True)
            before = {p.name: p.read_bytes() for p in out.iterdir()}
            DERIVE.run(SOURCE, out, True)
            DERIVE.run(SOURCE, out)
            self.assertEqual({p.name: p.read_bytes() for p in out.iterdir()}, before)
            for sign in ("decr", "incr"):
                check_full_union(sign, before[f"cheek-volume-bilateral-{sign}.target"])

    def test_base_manifest_preserves_all_25_old_payloads_and_cap(self):
        old = ROOT / "assets/characters/mpfb-b1-v2"
        legacy = json.loads((old / "manifest.json").read_bytes())
        new = json.loads((BASE / "manifest.json").read_bytes())
        self.assertEqual(set(new), {"format", "schema_version", "asset_id", "common_manifest_sha256", "adapter_receipt_sha256", "files"})
        self.assertEqual(new["schema_version"], 1)
        self.assertEqual(new["asset_id"], "mpfb-hm08-game-engine-female-sportsuit01-v3")
        self.assertEqual(len(legacy["files"]), 25)
        self.assertEqual(len(new["files"]), 27)
        self.assertLess(sum(f["bytes"] for f in new["files"]), 8 * 1024 * 1024)
        self.assertEqual(new["adapter_receipt_sha256"], legacy["adapter_receipt_sha256"])
        for entry in legacy["files"]:
            self.assertIn(entry, new["files"])
            self.assertEqual((old / entry["path"]).read_bytes(), (BASE / entry["path"]).read_bytes())
        for entry in new["files"]:
            data = (BASE / entry["path"]).read_bytes()
            self.assertEqual((len(data), digest(data)), (entry["bytes"], entry["sha256"]))
        inventory = (BASE / "provenance/runtime-payloads.json").read_bytes()
        self.assertEqual(digest(inventory), new["common_manifest_sha256"])
        self.assertEqual(json.loads(inventory)["files"], new["files"])

    def test_both_appearances_bind_new_base_and_preserve_payload_bytes(self):
        base_sha = digest((BASE / "manifest.json").read_bytes())
        for suffix, count in (("", 13), ("-short01-v1", 14)):
            old = ROOT / ("assets/appearances/mpfb-b1-cc0-v2" + suffix)
            new = ROOT / ("assets/appearances/mpfb-b1-cc0-v3" + suffix)
            legacy = json.loads((old / "manifest.json").read_bytes())
            manifest = json.loads((new / "manifest.json").read_bytes())
            self.assertEqual(manifest["schema_version"], 3)
            self.assertEqual(manifest["asset_set_id"], "mpfb-b1-cc0-appearance-v3" + suffix)
            self.assertEqual(manifest["base_asset_id"], "mpfb-hm08-game-engine-female-sportsuit01-v3")
            self.assertEqual(manifest["base_manifest_sha256"], base_sha)
            self.assertEqual(manifest["files"], legacy["files"])
            self.assertEqual(len(manifest["files"]), count)
            for path, meta in manifest["files"].items():
                data = (new / path).read_bytes()
                self.assertEqual(data, (old / path).read_bytes())
                self.assertEqual((len(data), digest(data)), (meta["bytes"], meta["sha256"]))
            binding = json.loads((new / "BASE-BINDING.json").read_bytes())
            self.assertEqual(binding["base_manifest_sha256"], base_sha)
            self.assertEqual(binding["legacy_appearance_manifest_sha256"], digest((old / "manifest.json").read_bytes()))

    def test_receipt_pins_sources_recipe_and_actual_outputs(self):
        receipt = json.loads((BASE / "provenance/cheek-volume-derivation.json").read_bytes())
        self.assertEqual(receipt["source"]["commit"], "d0a32e57a7f915cb2f2b95410e2117648c7bbb7e")
        self.assertEqual(receipt["recipe"]["script_sha256"], digest((ROOT / "scripts/derive-cheek-volume.py").read_bytes()))
        self.assertEqual(len(receipt["sources"]), 4)
        for source in receipt["sources"]:
            name = Path(source["source_relative"]).name
            self.assertEqual((source["compressed_bytes"], source["compressed_sha256"], source["expanded_bytes"], source["expanded_sha256"], source["stored_rows"], source["nonzero_rows"]), ORIGINALS[name])
            self.assertEqual((BASE / source["retained_path"]).read_bytes(), (SOURCE / name).read_bytes())
            self.assertTrue(source["url"].startswith("https://raw.githubusercontent.com/makehumancommunity/mpfb2/" + receipt["source"]["commit"] + "/"))
        for entry in receipt["outputs"]:
            data = (BASE / entry["path"]).read_bytes()
            self.assertEqual((len(data), digest(data)), (entry["bytes"], entry["sha256"]))
        old = ROOT / "assets/characters/mpfb-b1-v2"
        for path in [p.relative_to(old) for p in (old / "licenses").rglob("*") if p.is_file()]:
            self.assertEqual((BASE / path).read_bytes(), (old / path).read_bytes())
        self.assertEqual((BASE / "provenance/parameter-source-receipt.json").read_bytes(), (old / "provenance/parameter-source-receipt.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
