#!/usr/bin/env python3
"""Reconcile a real startup snapshot with frozen hashes and actual HTTP body writes."""
import argparse
from collections import Counter
import json
import hashlib
from pathlib import Path
from urllib.parse import urlsplit

from check_capture import validate

CRITICAL = ('index.html', 'startup-diagnostics.js', 'nvwa_studio.js',
            'nvwa_studio_bg.wasm', 'assets/fixtures/nvwa-humanoid.glb')
OPTIONAL_META = 'assets/fixtures/nvwa-humanoid.glb.meta'
MISSING_BODY = b'not a served runtime member\n'


def verify(capture, manifest, requests, run):
    result = validate(capture, run)
    if manifest.get('cacheControl') != 'no-store' or run not in manifest.get('runIds', []):
        raise ValueError('manifest lacks matching no-store run')
    if manifest.get('bind') != '127.0.0.1' or manifest.get('port') != 9201:
        raise ValueError('server scope mismatch')
    prefix = f'/run/{run}/'
    matched = [row for row in requests if row.get('runId') == run]
    if not matched:
        raise ValueError('no actual requests for run')
    members = []
    optional_missing = []
    for row in matched:
        if row.get('method') != 'GET':
            continue
        target = urlsplit(row.get('target', '')).path
        name = row.get('member')
        if target != prefix + str(name):
            raise ValueError('request target/run mismatch')
        # Verified against installed bevy_asset0.19.1: wasm.rs read_meta creates
        # .meta URL and maps404 to NotFound; server/mod.rs1616-1628 selects
        # loader.default_meta(), then reads the actual asset. This exception
        # covers only that exact absent sidecar, never a GLB or arbitrary404.
        if name == OPTIONAL_META and row.get('status') == 404:
            frozen = manifest.get('frozenFiles', {})
            if name in frozen or name + '.gz' in frozen:
                raise ValueError('frozen metadata unexpectedly missing')
            if (row.get('cacheControl') != 'no-store' or row.get('interrupted')
                    or row.get('contentEncoding') != 'identity'
                    or row.get('declaredBodyBytes') != len(MISSING_BODY)
                    or row.get('bodyBytesWritten') != len(MISSING_BODY)
                    or row.get('responseBodySha256') != hashlib.sha256(MISSING_BODY).hexdigest()):
                raise ValueError('optional metadata404 response incomplete or changed')
            optional_missing.append({'member': name, 'status': 404,
                'bodyBytesWritten': row['bodyBytesWritten'], 'cacheControl': 'no-store',
                'reason': 'verified Bevy0.19.1 optional metadata NotFound selects loader default; actualGLB200 required separately',
                'browserTiming': 'no resource-timing transfer claim for optional404'})
            continue
        if row.get('status') != 200 or row.get('cacheControl') != 'no-store' or row.get('interrupted'):
            raise ValueError('failed, interrupted or cached response: ' + str(name))
        if row.get('bodyBytesWritten', 0) <= 0 or row.get('bodyBytesWritten') != row.get('declaredBodyBytes'):
            raise ValueError('incomplete response body: ' + str(name))
        encoding = row.get('contentEncoding')
        if encoding not in ('identity', 'gzip'):
            raise ValueError('unknown response encoding')
        if name == 'index.html':
            expected = manifest['diagnostics']['wrapperSha256']
        elif name == 'startup-diagnostics.js':
            expected = manifest['diagnostics']['collectorSha256']
        else:
            selected = str(name) + ('.gz' if encoding == 'gzip' else '')
            frozen = manifest.get('frozenFiles', {}).get(selected)
            if not frozen or row['declaredBodyBytes'] != frozen['bytes']:
                raise ValueError('not exact frozen response size: ' + str(name))
            expected = frozen['sha256']
        if row.get('responseBodySha256') != expected:
            raise ValueError('not exact frozen response hash: ' + str(name))
        members.append(name)
    counts = Counter(members)
    for name in CRITICAL:
        if counts[name] != 1:
            raise ValueError('critical asset requires one actual GET: ' + name)
    timing_members = []
    for row in capture['navigation'] + capture['resources']:
        url = urlsplit(row['name'])
        path = url.path
        if url.scheme != 'http' or url.netloc != '127.0.0.1:9201' or not path.startswith(prefix):
            raise ValueError('timing entry outside run prefix')
        name = path[len(prefix):]
        if name not in members:
            raise ValueError('timing lacks actual HTTP response: ' + name)
        # Positive body sizes alone can be provided for a cached resource. Require
        # positive transfer and a matching completed no-store body from this run.
        if row['transferSize'] <= 0 or row['encodedBodySize'] <= 0 or row['decodedBodySize'] <= 0:
            raise ValueError('unavailable/cached transfer timing: ' + name)
        actual = [item for item in matched if item.get('member') == name and item.get('method') == 'GET']
        if not any(item['bodyBytesWritten'] == row['encodedBodySize'] for item in actual):
            raise ValueError('timing encoded bytes differ from actual body: ' + name)
        if row['transferSize'] < row['encodedBodySize']:
            raise ValueError('transfer smaller than encoded body')
        if name not in ('index.html', 'startup-diagnostics.js'):
            identity = manifest['frozenFiles'].get(name)
            if not identity or row['decodedBodySize'] != identity['bytes']:
                raise ValueError('decoded bytes differ from frozen identity: ' + name)
        timing_members.append(name)
    for name in CRITICAL:
        if timing_members.count(name) != 1:
            raise ValueError('missing or duplicated critical resource timing: ' + name)
    limit = capture.get('resourceTimingLimit', {})
    if limit.get('entriesBeyondLimit', 0) or limit.get('browserBufferFullEvents', 0):
        raise ValueError('resource timing inventory incomplete')
    return {**result, 'actualGetRequests': len(members), 'criticalAssets': list(CRITICAL),
            'optionalMissingSidecars': optional_missing,
            'bodyBytesWritten': sum(row['bodyBytesWritten'] for row in matched),
            'claim': 'fresh-prefix HTTP no-store boundary with exact frozen response bodies',
            'exactFirstPresentation': 'NOT-RUN', 'browserGpuOsShaderCold': 'NOT-RUN'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--requests', type=Path, required=True)
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    try:
        result = verify(json.loads(args.capture.read_text()), json.loads(args.manifest.read_text()),
                        [json.loads(line) for line in args.requests.read_text().splitlines() if line], args.run)
    except (ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    print('PASS', json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
