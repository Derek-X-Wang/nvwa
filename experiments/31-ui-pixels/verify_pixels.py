#!/usr/bin/env python3
"""Independent literal reference; reads PNG pixels, never selected UI state."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib

# Literal reference geometry for fixed40px margin,100x26 tabs and8px spacing.
# Interiors exclude rounded edges and the center text. No runtime-derived ROIs.
REFERENCES = {
    "normal-shape": [(48, 47, 60, 56, (17, 61, 113)), (156, 47, 168, 56, (149, 37, 71))],
    "normal-profile": [(48, 47, 60, 56, (149, 37, 71)), (156, 47, 168, 56, (17, 61, 113))],
}


def decode_rgb8(path):
    data = path.read_bytes()
    if not 0 < len(data) <= 16 * 1024 * 1024 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("missing/empty/non-PNG/oversized actual capture")
    pos, header, bodies, ended = 8, None, [], False
    while pos < len(data):
        if pos + 12 > len(data):
            raise ValueError("truncated PNG chunk")
        size = struct.unpack_from(">I", data, pos)[0]
        kind = data[pos + 4:pos + 8]
        end = pos + 12 + size
        if end > len(data):
            raise ValueError("truncated PNG body")
        body = data[pos + 8:pos + 8 + size]
        if zlib.crc32(kind + body) & 0xffffffff != struct.unpack_from(">I", data, end - 4)[0]:
            raise ValueError("PNG CRC mismatch")
        if kind == b"IHDR":
            if header is not None or len(body) != 13:
                raise ValueError("ambiguous IHDR")
            header = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            bodies.append(body)
        elif kind == b"IEND":
            if body or end != len(data):
                raise ValueError("invalid IEND or trailing PNG bytes")
            ended = True
        pos = end
    if header != (1280, 720, 8, 2, 0, 0, 0) or not ended or not bodies:
        raise ValueError(f"expected non-interlaced1280x720 RGB8; got {header}")
    width, height = header[:2]
    stride, expected_bytes = width * 3, (width * 3 + 1) * height
    decoder = zlib.decompressobj()
    raw = decoder.decompress(b"".join(bodies), expected_bytes + 1)
    if len(raw) != expected_bytes or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise ValueError("wrong PNG decompressed byte count")
    rows, previous = [], bytearray(stride)
    for y in range(height):
        offset = y * (stride + 1)
        filtering = raw[offset]
        row = bytearray(raw[offset + 1:offset + 1 + stride])
        if filtering not in range(5):
            raise ValueError("unknown PNG filter")
        for x in range(stride):
            left = row[x - 3] if x >= 3 else 0
            above = previous[x]
            upper_left = previous[x - 3] if x >= 3 else 0
            predictor = 0
            if filtering == 1:
                predictor = left
            elif filtering == 2:
                predictor = above
            elif filtering == 3:
                predictor = (left + above) // 2
            elif filtering == 4:
                p = left + above - upper_left
                distances = (abs(p - left), abs(p - above), abs(p - upper_left))
                predictor = (left, above, upper_left)[distances.index(min(distances))]
            row[x] = (row[x] + predictor) & 255
        rows.append(bytes(row))
        previous = row
    return data, rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("png", type=Path)
    parser.add_argument("--case", choices=REFERENCES, required=True)
    args = parser.parse_args()
    try:
        data, rows = decode_rgb8(args.png)
        observations = []
        for x0, y0, x1, y1, expected in REFERENCES[args.case]:
            pixels = [tuple(rows[y][x * 3:x * 3 + 3]) for y in range(y0, y1) for x in range(x0, x1)]
            errors = [max(abs(a - b) for a, b in zip(pixel, expected)) for pixel in pixels]
            observations.append({"region": [x0, y0, x1, y1], "literal_expected_rgb": expected,
                "pixel_count": len(pixels), "maximum_channel_error": max(errors),
                "within_fixed_tolerance2": all(error <= 2 for error in errors)})
        passed = all(item["within_fixed_tolerance2"] for item in observations)
        print(json.dumps({"pass": passed, "png": str(args.png), "sha256": hashlib.sha256(data).hexdigest(),
            "case": args.case, "width": 1280, "height": 720, "observations": observations}, sort_keys=True))
        return 0 if passed else 1
    except (OSError, ValueError, zlib.error, struct.error) as error:
        print(json.dumps({"pass": False, "error": str(error), "png": str(args.png)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
