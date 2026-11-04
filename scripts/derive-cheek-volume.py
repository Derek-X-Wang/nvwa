#!/usr/bin/env python3
"""Derive only the two B1 V3 bilateral cheek leaves from four pinned originals.

Rows are a sorted disjoint union. All four original numeric tokens survive.
No arithmetic, unit conversion, zero filtering, or mirrored synthesis is used.
The default checks existing outputs; --write creates missing files exclusively.
"""

import argparse
import gzip
import hashlib
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "assets/characters/mpfb-b1-v3"
COMMIT = "d0a32e57a7f915cb2f2b95410e2117648c7bbb7e"
# compressed bytes/hash, expanded bytes/hash, stored rows, nonzero rows, ID range
SOURCES = {
    "l-cheek-volume-decr.target.gz": (787, "202ff036e39abea154e0896ad34641184c5e8b77610dca9e1e8e4ce4a5db1bc4", 3015, "d88cedb8d78e4ac0009d83e425245cb8f584c064b9c3be3419d167d1c22b3539", 194, 152, (6968, 11942)),
    "r-cheek-volume-decr.target.gz": (765, "ea12455c7a85e7b3b5e6e4882b4b68823a00bcaef4ea048cc49be452a139c1bc", 2670, "ca0576cfb9a49216f6844a97d6347eaf662b56b1c165f5938661c91d1d04d617", 194, 152, (192, 5339)),
    "l-cheek-volume-incr.target.gz": (1274, "75bf330b96d0036c46f779ed003782c7380c77dd06c14fd80f1fa20a5093fee1", 4150, "7a47a6a0121657092266df2a27ec6e134462642fd3f781ee47daeec40d1426fd", 229, 210, (6826, 11944)),
    "r-cheek-volume-incr.target.gz": (1288, "4df3e61e843c2d3381ef534e90d347b6b8ea763428d69eba8ef2ed5ab0affb8c", 4086, "95e57c5e1313c118d5e3c4e43ec3d0dd9952957e5ba1bcbed1c8027d40940e43", 229, 210, (42, 5341)),
}
OUTPUTS = {
    "decr": (5685, "aeab40d480502a05d4be4a9d9b9589212bbddf4a2da7f2418bc4ffc4fed2a487", 388, 304),
    "incr": (8236, "3eba8dad1ee2d2bf01cb49f1cd50a50cae7a947b37f556405bf173fa26053a84", 458, 420),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identity(data, length, digest, label):
    require(len(data) == length, f"{label}: byte length mismatch")
    require(hashlib.sha256(data).hexdigest() == digest, f"{label}: SHA256 mismatch")


def source_rows(directory):
    result = {}
    for name, expected in SOURCES.items():
        compressed = (directory / name).read_bytes()
        identity(compressed, expected[0], expected[1], name + " compressed")
        expanded = gzip.decompress(compressed)
        identity(expanded, expected[2], expected[3], name + " expanded")
        rows = {}
        nonzero = 0
        for line in expanded.splitlines():
            tokens = line.split()
            require(len(tokens) == 4, f"{name}: expected four tokens")
            vertex = int(tokens[0])
            require(0 <= vertex < 19158, f"{name}: vertex outside base range")
            require(vertex not in rows, f"{name}: duplicate vertex")
            values = [float(token) for token in tokens[1:]]
            require(all(math.isfinite(value) for value in values), f"{name}: nonfinite displacement")
            nonzero += any(value != 0 for value in values)
            rows[vertex] = tokens
        require(len(rows) == expected[4], f"{name}: stored row count mismatch")
        require(nonzero == expected[5], f"{name}: nonzero row count mismatch")
        require((min(rows), max(rows)) == expected[6], f"{name}: ID range mismatch")
        result[name] = rows
    return result


def derive(directory):
    sources = source_rows(directory)  # Authenticate all four before deriving either.
    result = {}
    for sign, expected in OUTPUTS.items():
        left = sources[f"l-cheek-volume-{sign}.target.gz"]
        right = sources[f"r-cheek-volume-{sign}.target.gz"]
        require(left.keys().isdisjoint(right), f"{sign}: source ID sets overlap")
        rows = left | right
        require(len(rows) == expected[2], f"{sign}: union row count mismatch")
        payload = b"".join(b" ".join(rows[vertex]) + b"\n" for vertex in sorted(rows))
        identity(payload, expected[0], expected[1], sign + " derived")
        result[f"cheek-volume-bilateral-{sign}.target"] = payload
    return result


def run(source_dir, output_dir, write=False):
    payloads = derive(source_dir)
    # Validate every existing destination before writing any missing destination.
    for name, payload in payloads.items():
        path = output_dir / name
        require(not path.is_symlink(), f"{name}: destination is a symlink")
        if path.exists():
            require(path.read_bytes() == payload, f"{name}: existing output differs; refusing overwrite")
        elif not write:
            raise ValueError(f"{name}: missing output (use --write to create)")
    if write:
        output_dir.mkdir(parents=True, exist_ok=True)
        for name, payload in payloads.items():
            path = output_dir / name
            if not path.exists():
                with path.open("xb") as stream:
                    stream.write(payload)
    return payloads


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=BASE / "provenance/source/data/targets/cheek")
    parser.add_argument("--output-dir", type=Path, default=BASE / "targets")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        payloads = run(args.source_dir, args.output_dir, args.write)
    except (ValueError, OSError, EOFError) as error:
        parser.exit(1, f"cheek derivation failed: {error}\n")
    for name, payload in payloads.items():
        print(f"{name} {len(payload)} {hashlib.sha256(payload).hexdigest()}")


if __name__ == "__main__":
    main()
