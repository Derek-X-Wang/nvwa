#!/usr/bin/env python3
"""Offline verification of exact archived observations; no UI or dist required."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / 'experiments/24-http-cold-startup'))
from verify_capture import verify


def load(name):
    return json.loads((HERE / name).read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_runtime_evidence(rows, extracted):
    matching = [(i, row) for i, row in enumerate(rows)
                if 'NVWA_EVIDENCE ' in row.get('message', '')]
    assert len(matching) == 1, 'startup2 must have one attributed runtime record'
    index, row = matching[0]
    actual, _ = json.JSONDecoder().raw_decode(row['message'].split('NVWA_EVIDENCE ', 1)[1])
    assert extracted['source_entry_index'] == index, 'runtime entry attribution'
    assert extracted['source_timestamp'] == row['timestamp'], 'runtime timestamp attribution'
    assert extracted['source_url'] == row['url'], 'runtime URL attribution'
    assert extracted['evidence'] == actual, 'runtime extraction must equal preserved raw console'
    assert actual['clock'] == 'bevy_TimeReal_since_first_update', 'separate Bevy clock'
    assert actual['ready'] and actual['error'] is None and not actual['timeout'], 'actual ready state'
    assert actual['capture_callback'] and actual['first_asset_ready_seconds'] == 0.4248, 'actual milestones'
    assert actual['capture_callback_seconds'] == 15.4457, 'actual callback clock'
    assert actual['physical_window'] == {'width': 1280, 'height': 720, 'scale_factor': 1.0}, 'runtime geometry'
    assert (actual['meshes'], actual['joints'], actual['morph_weights']) == (9, 18, 4), 'runtime character'
    return actual


def png(name):
    data = (HERE / name).read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n', name
    offset, parts, compressed = 8, [], b''
    while offset < len(data):
        size = struct.unpack('>I', data[offset:offset + 4])[0]
        kind = data[offset + 4:offset + 8]
        body = data[offset + 8:offset + 8 + size]
        crc = struct.unpack('>I', data[offset + 8 + size:offset + 12 + size])[0]
        assert len(body) == size and zlib.crc32(kind + body) & 0xffffffff == crc, name
        parts.append(kind)
        if kind == b'IHDR':
            width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', body)
            assert (width, height, depth, compression, filtering, interlace) == (1280, 720, 8, 0, 0, 0), name
            assert color in (2, 6), name
        if kind == b'IDAT':
            compressed += body
        offset += size + 12
    assert parts[0] == b'IHDR' and parts[-1] == b'IEND' and offset == len(data), name
    raw = zlib.decompress(compressed)
    stride = width * (3 if color == 2 else 4) + 1
    assert len(raw) == stride * height and all(raw[row * stride] in range(5) for row in range(height)), name
    return {'file': name, 'bytes': len(data), 'width': width, 'height': height,
            'color': 'RGB' if color == 2 else 'RGBA', 'sha256': sha(HERE / name),
            'semantic_pixels': 'separately inspected by root; PNG syntax alone is not character proof'}


def main():
    manifest = load('MANIFEST.json')
    for row in manifest['entries']:
        path = HERE / row['file']
        assert path.resolve().is_relative_to(HERE) and path.stat().st_size == row['bytes'], row['file']
        assert sha(path) == row['sha256'], row['file']
    for name, expected in manifest['checker_files'].items():
        assert sha(REPO / name) == expected, name
    reuse = load('artifact-reuse.json')
    assert len(reuse['inputs']) == 31
    for name, row in reuse['inputs'].items():
        assert row['matches'] and sha(REPO / name) == row['sha256'], name
    server = load('http/manifest.json')
    for name in ('index.html', 'nvwa_studio.js', 'nvwa_studio_bg.wasm'):
        assert server['frozenFiles'][name]['sha256'] == reuse['artifacts']['dist/web/' + name]['sha256'], name
    requests = [json.loads(row) for row in (HERE / 'http/requests.jsonl').read_text().splitlines()]
    starts = [verify(load(f'startup-{i + 1}-browser.json'), server, requests, run)
              for i, run in enumerate(server['runIds'][:2])]
    assert load('startup-1-console.json') == [], 'startup1 console observation unavailable'
    extracted = load('startup-2-runtime-evidence.json')
    assert extracted['source'] == 'startup-2-console.json', 'runtime source attribution'
    assert extracted['source_sha256'] == sha(HERE / extracted['source']), 'raw console unchanged'
    runtime = verify_runtime_evidence(load(extracted['source']), extracted)
    assert f"/run/{server['runIds'][1]}/" in extracted['source_url'], 'startup2 case association'
    observation = load('startup-2-observation.json')
    assert observation['assetReadyClock'] == runtime['clock'], 'corrected observation clock'
    assert observation['firstAssetReadySeconds'] == runtime['first_asset_ready_seconds'], 'corrected readiness'
    assert observation['captureCallbackSeconds'] == runtime['capture_callback_seconds'], 'corrected callback'
    attempts = {}
    for case, wait in [('A', 30), ('B', 30), ('D', 30), ('C', 15)]:
        rows = load(f'export-{case}-final-records.json')
        assert rows[0]['case'] == case and rows[-1]['phase'] == 'probe-stopped', case
        hooks = next(i for i, row in enumerate(rows) if row['phase'] == 'hooks-ready')
        automatic = next((i, row) for i, row in enumerate(rows)
                         if row['phase'] == 'anchor-click-attempt' and row['automatic'])
        assert hooks < automatic[0] and automatic[1]['blobBytes'] > 0, case
        assert automatic[1]['anchorAttached'] == (case in ('B', 'D')), case
        if case == 'D':
            revoked = next(row for row in rows if row['phase'] == 'blob-url-revoked')
            assert revoked['delayFromRequestMs'] >= 1000, case
        if case == 'C':
            explicit = next(row for row in rows if row['phase'] == 'anchor-click-attempt' and not row['automatic'])
            assert explicit['source'] == 'real-canvas-toBlob' and explicit['blobType'] == 'image/png', case
            assert explicit['anchorAttached'] and explicit['activation']['isActive'], case
        outcome = load(f'export-{case}-download.json')
        assert outcome['event'] == f'no-event-within{wait}s' and not outcome.get('path'), case
        attempts[case] = 'bounded no-event observation; no global absence/causal claim'
    images = [png('startup-2-auto.png'), png('export-top-explicit.png')]
    assert all(row['color'] == 'RGB' for row in images), 'actual archived PNG color type'
    for outcome_name, image_name, stat_name, stamp_field in [
            ('startup-2-auto-download.json', 'startup-2-auto.png', 'startup-2-observation.json', 'downloadModifiedAt'),
            ('export-top-download.json', 'export-top-explicit.png', 'export-top-file-observation.json', 'modifiedUtc')]:
        outcome, stat = load(outcome_name), load(stat_name)
        assert outcome['event'] == 'observed' and outcome['path'], outcome_name
        assert outcome['waitStartedAt'] <= stat[stamp_field] <= outcome['waitCompletedAt'], outcome_name
        expected_size = stat.get('downloadBytes', stat.get('bytes'))
        assert (HERE / image_name).stat().st_size == expected_size, image_name
    print(json.dumps({'status': 'PASS', 'entries': len(manifest['entries']),
                      'production_inputs': 31, 'http_startups': starts,
                      'runtime_console': {'startup1': 'NOT-RUN: empty captured console',
                                          'startup2': {'clock': runtime['clock'],
                                                       'first_asset_ready_seconds': runtime['first_asset_ready_seconds'],
                                                       'capture_callback_seconds': runtime['capture_callback_seconds']}},
                      'iframe_attempts': attempts, 'actual_pngs': images,
                      'limits': ['HTTP cache boundary only', 'original DPR trigger NOT-RUN',
                                 'exact first presentation and full cold state NOT-RUN',
                                 'original top-level screenshot failure cause UNKNOWN']}, indent=2))


if __name__ == '__main__':
    main()
