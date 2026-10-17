#!/usr/bin/env python3
"""Authenticate the one approved local archive, then prepare its fixed appearance subset."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import struct
import zipfile
import zlib

ARCHIVE_SIZE = 280737770
ARCHIVE_SHA256 = 'b542127a8e25547c7c29c19f2d1d2adb9a664c80396ecd694095dbc8028a0107'
# Exact source identities, independently rechecked against the approved ZIP.
MEMBERS = {
 'skins/young_caucasian_female2/young_caucasian_female2.mhmat': (1465, '8934dd8d8f3beccc1b212c12116a88b3a88d6265e0a5c8fe42eb62e3fb281ab6'),
 'skins/young_caucasian_female2/young_lightskinned_female_diffuse2.png': (3724137, '8d1fb3ceedf142fad32a3504eca1feb4539aecca6de66acde1514b9a61fc7ba0'),
 'eyes/low-poly/low-poly.mhclo': (1344, '68582e28e9176cba7cfcf35208f671b6201b8d1bc95c32decff61a3160ec34d8'),
 'eyes/low-poly/low-poly.obj': (6604, '783fe1e6331162c876520b4c2bed7a8ca06354ca15497e8ebd68bb1b59f4d3de'),
 'eyes/materials/brown.mhmat': (1247, '4abad93ce50541c08127721e77bce035640c9f16bed16cd0f5524b1cd5908465'),
 'eyes/materials/brown_eye.png': (610817, '4659691c7295ad6206c78b003e5fd0e5f91dcd53032fa914a229bb48cabe424b'),
 'hair/short04/short04.mhclo': (59195, 'd60640aa4c4ffce1aa269647ba436b6ee0bb21bb948f927b84e27a48d2107157'),
 'hair/short04/short04.obj': (55152, '676964a133ee35ffcea1195382bf75542da7a298931e4001bc7b0d7b707225de'),
 'hair/short04/short04.mhmat': (1316, '7a3ac74db8478aa0afdb8a596c6fe3997d1a8a09d12211d70e8f1e9f0b7e0e97'),
 'hair/short04/short04_diffuse.png': (2308132, '0bef7fc0e403db5a40fabb2111ebfa6f7e8158e204c6e56b8da98e9ef527846e'),
}
PACK = 'packs/makehuman_system_assets.json'
PACK_ID = (39220, 'e86f1572432cfd062f372adddba4eb7c2e2e31280e96c29291a970320e0a5df0')
CC0_ID = (6962, 'f6089cba01cb570a24712b41ab8a586ccd3cc5ef53dc266ca50b95c288956d2c')
PNG_EXPECTED = {
 'skins/young_caucasian_female2/young_lightskinned_female_diffuse2.png': (2048, 2048, 2),
 'eyes/materials/brown_eye.png': (1024, 1024, 6),
 'hair/short04/short04_diffuse.png': (2048, 2048, 6),
}
REPO = Path(__file__).resolve().parents[3]
CC0_SOURCE = REPO / 'assets/characters/mpfb-b1-v1/licenses/CC0-1.0.txt'


def check(ok, message):
    if not ok:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def safe_name(name):
    check(bool(name) and '\\' not in name and '\x00' not in name, 'unsafe archive path')
    p = PurePosixPath(name)
    check(not p.is_absolute() and all(x not in ('', '.', '..') for x in name.rstrip('/').split('/')) and ':' not in name, 'unsafe archive path')


def authenticate(stream, archive_identity, selected):
    """No extraction; reusable seam permits tiny adversarial ZIP controls in tests."""
    stream.seek(0, 2)
    check(stream.tell() == archive_identity[0], 'archive size mismatch')
    stream.seek(0)
    check(hashlib.file_digest(stream, 'sha256').hexdigest() == archive_identity[1], 'archive SHA256 mismatch')
    stream.seek(0)
    with zipfile.ZipFile(stream) as archive:
        infos = archive.infolist()
        check(len(infos) <= 4096, 'archive member count bound')
        names = [i.filename for i in infos]
        check(len(names) == len(set(names)), 'duplicate archive member')
        for info in infos:
            safe_name(info.filename)
            mode = info.external_attr >> 16
            check(not stat.S_ISLNK(mode), 'archive symlink')
            check(not info.flag_bits & 1, 'encrypted archive member')
        payload = {}
        for name, (size, expected_hash) in selected.items():
            safe_name(name)
            check(name in names, 'missing allowlisted member: '+name)
            info = archive.getinfo(name)
            mode = info.external_attr >> 16
            check(not info.is_dir() and (not stat.S_IFMT(mode) or stat.S_ISREG(mode)), 'nonregular selected member')
            check(0 < size <= 4*1024*1024 and info.file_size == size, 'member size mismatch: '+name)
            with archive.open(info) as member:
                data = member.read(size+1)
            check(len(data) == size and digest(data) == expected_hash, 'member bytes/SHA256 mismatch: '+name)
            payload[name] = data
        return payload


def paeth(a, b, c):
    p = a+b-c
    da, db, dc = abs(p-a), abs(p-b), abs(p-c)
    return a if da <= db and da <= dc else b if db <= dc else c


def inspect_png(data, expected):
    """Strict RGB/RGBA8 noninterlaced decode, bounded before zlib allocation."""
    check(len(data) <= 4*1024*1024 and data[:8] == b'\x89PNG\r\n\x1a\n', 'PNG signature/size')
    pos, chunks, compressed, header, ended, idat_ended = 8, [], bytearray(), None, False, False
    while pos < len(data):
        check(len(chunks) < 4096 and pos+12 <= len(data), 'PNG truncated/chunk bound')
        size, kind = struct.unpack('>I4s', data[pos:pos+8])
        check(size <= 4*1024*1024 and pos+12+size <= len(data), 'PNG truncated chunk')
        body = data[pos+8:pos+8+size]
        crc = struct.unpack('>I', data[pos+8+size:pos+12+size])[0]
        check(zlib.crc32(kind+body) & 0xffffffff == crc, 'PNG CRC mismatch')
        check(all(65 <= b <= 90 or 97 <= b <= 122 for b in kind), 'PNG invalid chunk name')
        if not chunks:
            check(kind == b'IHDR' and size == 13, 'PNG first IHDR')
        if kind == b'IHDR':
            check(header is None and size == 13, 'PNG duplicate/invalid IHDR')
            header = struct.unpack('>IIBBBBB', body)
            w, h, depth, color, compression, filtering, interlace = header
            check((w, h, color) == expected and 0 < w <= 2048 and 0 < h <= 2048, 'PNG dimensions/color bound')
            check(depth == 8 and color in (2, 6) and compression == filtering == interlace == 0, 'PNG unsupported format')
        elif kind == b'IDAT':
            check(not idat_ended, 'PNG noncontiguous IDAT')
            compressed.extend(body)
            check(len(compressed) <= 4*1024*1024, 'PNG compressed bound')
        elif kind == b'IEND':
            check(size == 0 and compressed, 'PNG invalid IEND')
            ended = True
        else:
            check(kind[0] & 32 and kind != b'tRNS', 'PNG unsupported critical/transparency chunk')
            if compressed:
                idat_ended = True
        chunks.append(kind.decode('ascii'))
        pos += size+12
        if ended:
            break
    check(ended and pos == len(data), 'PNG missing IEND/trailing bytes')
    channels = 3 if color == 2 else 4
    stride = w*channels
    required = (stride+1)*h
    check(required <= 16*1024*1024+2048, 'PNG decoded bound')
    decoder = zlib.decompressobj()
    raw = decoder.decompress(compressed, required+1)
    check(len(raw) == required and decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail, 'PNG zlib size/truncation/trailing stream')
    pixels = bytearray(stride*h)
    previous = bytearray(stride)
    filters = Counter()
    for y in range(h):
        start = y*(stride+1)
        kind = raw[start]
        check(kind <= 4, 'PNG unsupported row filter')
        filters[kind] += 1
        row = bytearray(raw[start+1:start+1+stride])
        if kind:
            for x in range(stride):
                a = row[x-channels] if x >= channels else 0
                b = previous[x]
                c = previous[x-channels] if x >= channels else 0
                predictor = a if kind == 1 else b if kind == 2 else (a+b)//2 if kind == 3 else paeth(a, b, c)
                row[x] = (row[x]+predictor) & 255
        pixels[y*stride:(y+1)*stride] = row
        previous = row
    alpha = Counter(pixels[3::4]) if channels == 4 else Counter({255: w*h})
    return {'width': w, 'height': h, 'bit_depth': 8, 'color_type': color, 'channels': channels, 'interlaced': False, 'decoded_bytes': len(pixels), 'decoded_sha256': digest(pixels), 'row_filters': dict(sorted(filters.items())), 'alpha': {'source': 'decoded channel' if channels == 4 else 'implicit opaque RGB', 'minimum': min(alpha), 'maximum': max(alpha), 'zero_pixels': alpha[0], 'opaque_pixels': alpha[255], 'partial_pixels': sum(n for a,n in alpha.items() if 0<a<255), 'at_or_above_128_pixels': sum(n for a,n in alpha.items() if a >= 128), 'histogram': {str(a): n for a,n in sorted(alpha.items())}}}


def prepare(archive_path):
    fd = os.open(archive_path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        check(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), 'archive is not regular')
        payload = authenticate(stream, (ARCHIVE_SIZE, ARCHIVE_SHA256), {**MEMBERS, PACK: PACK_ID})
    metadata = json.loads(payload.pop(PACK))
    items = {key: metadata[key] for key in ('young_caucasian_female2', 'brown', 'short04')}
    check(all(v['license'] == 'CC0' and v['author'] == 'makehuman_system' for v in items.values()), 'selected metadata licence/author mismatch')
    notice = CC0_SOURCE.read_bytes()
    check((len(notice), digest(notice)) == CC0_ID, 'full CC0 notice identity mismatch')
    png = {name: inspect_png(payload[name], expected) for name, expected in PNG_EXPECTED.items()}
    check(sum(map(len,payload.values())) == 6769409, 'exact10 payload total')
    payload['licenses/CC0-1.0.txt'] = notice
    payload['provenance/selected-items.json'] = encoded(items)
    receipt = {'schema_version': 1, 'scope': 'Isolated experiment62;10 approved source payloads plus selected metadata/full CC0. Only skin is intended for first rendering slice; eyes/hair preparation only. No production admission.', 'archive': {'name': 'makehuman_system_assets_cc0.zip', 'size': ARCHIVE_SIZE, 'sha256': ARCHIVE_SHA256}, 'package_metadata_source': {'member': PACK, 'size': PACK_ID[0], 'sha256': PACK_ID[1]}, 'source_payload_count': 10, 'source_payload_bytes': 6769409, 'outputs': {name: {'size': len(data), 'sha256': digest(data)} for name,data in sorted(payload.items())}, 'png': png, 'decoder_policy': 'Strict PNG RGB/RGBA8 noninterlaced, CRC/all scanlines decoded, max2048x2048/4MiB file/16MiB pixels, no tRNS/arbitrary execution. Fixed preview sRGB intent; metadata/shader parity not claimed.'}
    payload['asset-manifest.json'] = encoded(receipt)
    return payload, receipt


def publish(output, payload):
    output = Path(os.path.abspath(output))
    for ancestor in (output, *output.parents):
        check(not ancestor.is_symlink(), 'output symlink/ancestor')
    check(not output.exists(), 'output must not exist')
    # All source authentication and PNG decoding completed before first write.
    for name in payload:
        safe_name(name)
    output.mkdir(parents=True, exist_ok=False)
    for name, data in sorted(payload.items(), key=lambda item: (item[0] == 'asset-manifest.json', item[0])):
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)


def verify_existing(output, payload):
    output = Path(os.path.abspath(output))
    check(output.is_dir(), 'verification output missing')
    for ancestor in (output, *output.parents):
        check(not ancestor.is_symlink(), 'verification symlink/ancestor')
    objects = list(output.rglob('*'))
    check(all(not p.is_symlink() and (p.is_dir() or p.is_file()) for p in objects), 'verification nonregular/symlink')
    files = {str(p.relative_to(output)): p for p in objects if p.is_file()}
    check(set(files) == set(payload), 'verification exact file set mismatch')
    for name, data in payload.items():
        check(files[name].stat().st_size == len(data) and files[name].read_bytes() == data, 'verification bytes mismatch: '+name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--verify', action='store_true', help='Authenticate/decode again and require existing output byte identity; write nothing')
    args = parser.parse_args()
    payload, receipt = prepare(args.archive)
    if args.verify:
        verify_existing(args.output, payload)
    else:
        publish(args.output, payload)
    print(json.dumps({'source_payloads': receipt['source_payload_count'], 'source_bytes': receipt['source_payload_bytes'], 'manifest_sha256': digest(payload['asset-manifest.json']), 'output_files': len(payload), 'mode': 'verify' if args.verify else 'prepare'}, sort_keys=True))


if __name__ == '__main__':
    main()
