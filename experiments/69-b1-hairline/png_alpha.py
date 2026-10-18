"""Bounded stdlib decoder for the authenticated existing RGBA8 source PNG."""
from collections import Counter
import hashlib
import struct
import zlib

def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def paeth(a, b, c):
    p = a+b-c
    errors = (abs(p-a), abs(p-b), abs(p-c))
    return (a, b, c)[errors.index(min(errors))]


def unfilter_row(kind, row, previous, stride=4):
    require(kind in range(5) and len(row) == len(previous), "PNG row domain")
    result = bytearray(row)
    for i in range(len(result)):
        left = result[i-stride] if i >= stride else 0
        up, corner = previous[i], previous[i-stride] if i >= stride else 0
        prediction = (0, left, up, (left+up)//2, paeth(left, up, corner))[kind]
        result[i] = (result[i]+prediction) & 255
    return result


def rgba_png(raw):
    require(raw[:8] == b"\x89PNG\r\n\x1a\n", "PNG signature")
    offset, chunks, header, filters = 8, [], None, Counter()
    while offset < len(raw):
        size, = struct.unpack_from(">I", raw, offset)
        kind, data = raw[offset+4:offset+8], raw[offset+8:offset+8+size]
        require(len(data) == size and offset+12+size <= len(raw), "PNG chunk bounds")
        checksum, = struct.unpack_from(">I", raw, offset+8+size)
        require(zlib.crc32(kind+data) == checksum, "PNG chunk CRC")
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", data)
        elif kind == b"IDAT":
            chunks.append(data)
        elif kind == b"IEND":
            require(offset+12+size == len(raw), "PNG trailing data")
            break
        offset += 12+size
    require(header and header[2:] == (8, 6, 0, 0, 0), "only noninterlaced RGBA8 supported")
    width, height = header[:2]
    require(0 < width <= 2048 and 0 < height <= 2048, "bounded image dimensions")
    decoded = zlib.decompress(b"".join(chunks))
    row_bytes = width*4
    require(len(decoded) == height*(row_bytes+1), "PNG decoded byte count")
    previous, pixels = bytearray(row_bytes), bytearray()
    for y in range(height):
        start = y*(row_bytes+1)
        kind = decoded[start]
        filters[kind] += 1
        previous = unfilter_row(kind, decoded[start+1:start+1+row_bytes], previous)
        pixels.extend(previous)
    return width, height, bytes(pixels), dict(filters)


