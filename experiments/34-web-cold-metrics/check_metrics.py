#!/usr/bin/env python3
"""Reconcile actual HTTP capture and CPU GPU-call boundaries; no display claim."""
import argparse
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlsplit, urlunsplit

from server import EXPECTED, HERE, WORK_MEMBER, WORK_SHA

CLOCK = 'Performance monotonic milliseconds since navigation timeOrigin'
FAVICON_BODY = b'unknown run prefix\n'
# Exact observed IAB Chrome155 Resource Timing value (19 body +300 estimate).
# This is producer-specific reconciliation, not measured wire header bytes.
FAVICON_TRANSFER_SIZE = 319
FAVICON_PRODUCER_UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36'
MEANINGS = {
    'first-production-queue-submit-return': 'CPU API returned after a production submit; commands may be uploads or offscreen; not GPU duration or display',
    'first-production-canvas-texture-return': 'CPU texture acquisition returned; not submit, present, compositor or visible pixels',
    'production-device-resolved-observed': 'promise reaction CPU observation; no GPU execution/display claim',
}


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError('invalid monotonic boundary')
    return value


def boundaries(capture):
    if capture.get('schema') != 'nvwa-web-perf-browser-v1' or capture.get('clock') != CLOCK:
        raise ValueError('schema/clock mismatch')
    stop = number(capture.get('snapshotAtMs'))
    startup = capture.get('startup', {})
    if startup.get('clock') != CLOCK or number(startup.get('snapshotAtMs')) > stop + 1:
        raise ValueError('startup clock mismatch')
    if capture.get('eventsDropped') != 0:
        raise ValueError('events lost')
    required_hooks = {'GPUAdapter.requestDevice', 'GPUQueue.submit', 'GPUCanvasContext.getCurrentTexture'}
    installed = [h.get('method') for h in capture.get('hooks', []) if h.get('installed') is True]
    if len(installed) != 3 or set(installed) != required_hooks:
        raise ValueError('required production hooks not installed')
    observed = []
    for event in capture.get('events', []):
        name = event.get('name')
        if name not in MEANINGS or event.get('meaning') != MEANINGS[name]:
            raise ValueError('unknown/failed production boundary')
        if event.get('clock') != CLOCK or number(event.get('atMs')) > stop:
            raise ValueError('mixed/future event clock')
        observed.append(name)
    for name in MEANINGS:
        if name not in observed:
            raise ValueError('missing production milestone: ' + name)
    devices = capture.get('devices')
    if not isinstance(devices, list) or not 1 <= len(devices) <= 8:
        raise ValueError('actual production device required')
    for device in devices:
        features = device.get('enabledFeatures')
        if not isinstance(features, list) or any(not isinstance(x, str) for x in features) or len(features) != len(set(features)):
            raise ValueError('enabled features malformed')
        if device.get('clock') != CLOCK or number(device.get('observedAtMs')) > stop:
            raise ValueError('device clock mismatch')
    claims = capture.get('claims', {})
    for name in ('firstPhysicalPresentation', 'gpuTimestampDuration', 'gpuMemory', 'browserProcessMemory', 'fullyCold'):
        if claims.get(name) != 'NOT-RUN':
            raise ValueError('unsupported claim: ' + name)
    heap = capture.get('jsHeap', {})
    samples = heap.get('samples')
    if not isinstance(samples, list) or len(samples) > 30:
        raise ValueError('heap samples missing/unbounded')
    if heap.get('status') != ('OBSERVED_SUBSET' if samples else 'NOT-RUN'):
        raise ValueError('heap status mismatch')
    for row in samples:
        if row.get('clock') != CLOCK or number(row.get('atMs')) > stop:
            raise ValueError('heap clock mismatch')
        for field in ('usedJSHeapSize', 'totalJSHeapSize', 'jsHeapSizeLimit'):
            value = number(row.get(field))
            if value != int(value):
                raise ValueError('fractional heap bytes')
    return {'cpuBoundaries': capture['events'], 'actualEnabledDeviceFeatures': devices,
        'gpuTimestampFeatureEnabled': any('timestamp-query' in d['enabledFeatures'] for d in devices),
        'claims': claims, 'jsHeap': heap}


def optional_favicon(startup, manifest, requests, run, attempt):
    """Only the observed exact outside-prefix favicon404 has an exception."""
    port = manifest.get('port')
    expected_url = f'http://127.0.0.1:{port}/favicon.ico'
    timings = [row for row in startup['resources'] if row.get('name') == expected_url]
    anchors = [i for i, row in enumerate(requests) if row.get('method') == 'GET'
        and row.get('runId') == run and row.get('member') == 'index.html' and row.get('attempt') == attempt]
    if len(anchors) != 1:
        raise ValueError('one actual navigation request anchor required')
    start = anchors[0]
    stop = next((i for i in range(start + 1, len(requests))
        if requests[i].get('method') == 'GET' and requests[i].get('member') == 'index.html'), len(requests))
    # Server log sequence scopes a favicon to this navigation attempt. No
    # subtraction or conversion between server/browser clocks is performed.
    rows = [row for row in requests[start + 1:stop]
        if row.get('method') == 'GET' and row.get('target') == '/favicon.ico']
    if any(row.get('method') == 'GET' and row.get('runId') is None and row.get('target') != '/favicon.ico'
            for row in requests[start + 1:stop]):
        raise ValueError('unexplained outside-prefix HTTP response')
    if not timings and not rows:
        return None
    if len(timings) != 1 or len(rows) != 1:
        raise ValueError('optional favicon requires one actual timing and matching server record')
    if startup.get('userAgent') != FAVICON_PRODUCER_UA:
        raise ValueError('favicon producer differs from observed IAB Chrome155 scope')
    source = HERE.parent / '24-http-cold-startup/server.py'
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    if (manifest.get('adapter', {}).get('baseServerSha256') != source_sha
            or manifest.get('diagnostics', {}).get('serverSourceSha256') != source_sha):
        raise ValueError('favicon response source identity mismatch')
    row, timing = rows[0], timings[0]
    if (row.get('status') != 404 or row.get('runId') is not None or row.get('member') is not None
            or row.get('attempt') != 0 or row.get('cacheControl') != 'no-store'
            or row.get('contentEncoding') != 'identity' or row.get('interrupted') is not None
            or row.get('declaredBodyBytes') != len(FAVICON_BODY)
            or row.get('bodyBytesWritten') != len(FAVICON_BODY)
            or row.get('responseBodySha256') != hashlib.sha256(FAVICON_BODY).hexdigest()):
        raise ValueError('optional favicon404 response identity/status/body mismatch')
    if timing.get('entryType') != 'resource' or timing.get('responseStatus') != 404:
        raise ValueError('optional favicon timing status/type mismatch')
    for field in ('startTime', 'duration', 'responseEnd', 'transferSize', 'encodedBodySize', 'decodedBodySize'):
        number(timing.get(field))
    if (timing['startTime'] > startup['snapshotAtMs'] or timing['responseEnd'] > startup['snapshotAtMs'] + 1
            or timing['responseEnd'] < timing['startTime']
            or abs(timing['startTime'] + timing['duration'] - timing['responseEnd']) > 1):
        raise ValueError('optional favicon timing clock mismatch')
    for field in ('fetchStart', 'requestStart', 'responseStart'):
        value = timing.get(field)
        if value is not None and number(value) > timing['responseEnd']:
            raise ValueError('optional favicon request boundary after responseEnd')
    if (timing['encodedBodySize'] != len(FAVICON_BODY) or timing['decodedBodySize'] != len(FAVICON_BODY)
            or timing['transferSize'] != FAVICON_TRANSFER_SIZE):
        raise ValueError('optional favicon exact resource size mismatch')
    startup['resources'].remove(timing)
    return {'member': '/favicon.ico', 'status': 404, 'bodyBytesWritten': len(FAVICON_BODY),
        'responseBodySha256': row['responseBodySha256'], 'responseSourceSha256': source_sha,
        'cacheControl': 'no-store', 'resourceTiming': timing,
        'producerUserAgentObserved': FAVICON_PRODUCER_UA,
        'transferSizeMeaning': 'exact observed IAB Chrome155 browser estimate319 =19 body +300 overhead estimate; not wire-header measurement or universal browser rule',
        'serverLogScope': 'after this navigation-index record and before the next navigation-index record',
        'meaning': 'one exact same-origin ordinary browser favicon404; separate optional response, included in totals'}


def verify(capture, manifest, requests, run, attempt=1):
    result = boundaries(capture)
    for member, expected in EXPECTED.items():
        frozen = manifest.get('frozenFiles', {}).get(member, {})
        if frozen.get('sha256') != expected:
            raise ValueError('wrong actual input identity: ' + member)
    if manifest['frozenFiles']['assets/fixtures/nvwa-humanoid.glb'].get('bytes') != 3827840:
        raise ValueError('wrong actual GLB size')
    work = manifest.get('frozenFiles', {}).get(WORK_MEMBER, {})
    if work.get('sha256') != WORK_SHA or work.get('bytes') != 1624:
        raise ValueError('wrong common Work identity')
    http = HERE.parent / '24-http-cold-startup'
    source = HERE / 'server.py'
    if manifest.get('adapter', {}).get('sourceSha256') != hashlib.sha256(source.read_bytes()).hexdigest():
        raise ValueError('unknown server source')
    expected_collector = (HERE / 'collector.js').read_bytes() + b'\n' + (HERE / 'gpu-boundaries.js').read_bytes()
    if manifest.get('adapter', {}).get('timestampVariant'):
        expected_collector += b'\n' + (HERE / 'timestamp-variant.js').read_bytes()
    if manifest.get('diagnostics', {}).get('collectorSha256') != hashlib.sha256(expected_collector).hexdigest():
        raise ValueError('unknown collector source')
    port = manifest.get('port')
    if port not in (9201, 9205):
        raise ValueError('unleased server port')
    startup = copy.deepcopy(capture['startup'])
    favicon = optional_favicon(startup, manifest, requests, run, attempt)
    query = parse_qs(urlsplit(startup['url']).query)
    if query.get('work') != [WORK_MEMBER] or query.get('benchmark') != ['1']:
        raise ValueError('explicit common Work/benchmark query required')
    geometry = startup.get('geometry', {})
    if geometry.get('viewportCss') != {'width': 1280, 'height': 720} or geometry.get('devicePixelRatio') != 1:
        raise ValueError('measured viewport/DPR differs from common contract')
    if geometry.get('canvasBacking') != {'width': 1280, 'height': 720}:
        raise ValueError('actual canvas backing differs from common physical viewport')
    # Existing experiment24 validates fixed9201. First check actual scope, then
    # use a transparent copy solely for its retained hash/body/cache checks.
    for row, field in [(startup, 'url')] + [(x, 'name') for x in startup['navigation'] + startup['resources']]:
        url = urlsplit(row[field])
        if url.scheme != 'http' or url.netloc != f'127.0.0.1:{port}':
            raise ValueError('actual timing scope mismatch')
        row[field] = urlunsplit((url.scheme, '127.0.0.1:9201', url.path, url.query, url.fragment))
    normalized_manifest = copy.deepcopy(manifest)
    normalized_manifest['port'] = 9201
    sys.path.insert(0, str(http))
    try:
        spec = importlib.util.spec_from_file_location('nvwa_24_verify', http / 'verify_capture.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        selected = [row for row in requests if row.get('attempt') == attempt]
        result['http'] = module.verify(startup, normalized_manifest, selected, run)
        actual_work = [r for r in selected if r.get('runId') == run and r.get('member') == WORK_MEMBER and r.get('method') == 'GET']
        timing_work = [r for r in startup['resources'] if urlsplit(r['name']).path == f'/run/{run}/' + WORK_MEMBER]
        if len(actual_work) != 1 or len(timing_work) != 1:
            raise ValueError('common Work requires actual response and resource timing')
    finally:
        sys.path.pop(0)
    result['actualPort'] = port
    result['attempt'] = attempt
    result['optionalFavicon'] = favicon
    result['http']['bodyBytesWrittenIncludingOptionalFavicon'] = result['http']['bodyBytesWritten'] + (favicon['bodyBytesWritten'] if favicon else 0)
    result['http']['optionalFaviconRequests'] = 1 if favicon else 0
    result['timestampVariant'] = timestamp_variant(capture.get('gpuTimestampVariant'), manifest.get('adapter', {}).get('timestampVariant', False))
    if result['timestampVariant'].get('records') and not result['gpuTimestampFeatureEnabled']:
        raise ValueError('GPU timestamps without actual enabled feature')
    result['scope'] = 'HTTP no-store exact-body reconciliation plus CPU production-call observations; no physical presentation or fully cold claim'
    return result


def timestamp_variant(variant, expected):
    if not expected:
        if variant is not None:
            raise ValueError('timestamp variant in baseline capture')
        return {'status': 'NOT-RUN', 'reason': 'unchanged-device baseline'}
    if not isinstance(variant, dict) or variant.get('schema') != 'nvwa-webgpu-timestamp-variant-v1' or variant.get('variant') is not True:
        raise ValueError('missing timestamp variant metadata')
    if number(variant.get('instrumentedEncoders')) > 8 or number(variant.get('passCount')) > 32:
        raise ValueError('unbounded timestamp query collection')
    records = variant.get('records')
    if not isinstance(records, list) or len(records) > 32:
        raise ValueError('unbounded timestamp records')
    for record in records:
        if record.get('clock') != 'WebGPU timestamp query nanoseconds; uncalibrated to navigation/CPU' or record.get('kind') not in ('render', 'compute'):
            raise ValueError('GPU timestamp clock/boundary mismatch')
        for name in ('startNs', 'endNs', 'durationNs'):
            value = record.get(name)
            if not isinstance(value, str) or not value.isdecimal():
                raise ValueError('malformed timestamp integer')
        if int(record['endNs']) - int(record['startNs']) != int(record['durationNs']):
            raise ValueError('GPU duration arithmetic mismatch')
    if variant.get('status') != ('OBSERVED_PASS_DURATION' if records and not variant.get('errors') else 'NOT-RUN'):
        raise ValueError('timestamp status mismatch')
    if records and not any(x.get('requested') is True for x in variant.get('featureRequests', [])):
        raise ValueError('GPU records without actual timestamp feature request')
    return variant


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', required=True, type=Path)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--requests', required=True, type=Path)
    parser.add_argument('--run', required=True)
    parser.add_argument('--attempt', type=int, choices=(1, 2), default=1)
    args = parser.parse_args()
    try:
        result = verify(json.loads(args.capture.read_text()), json.loads(args.manifest.read_text()),
            [json.loads(line) for line in args.requests.read_text().splitlines() if line], args.run, args.attempt)
    except (ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    print(json.dumps({'status': 'PASS_BOUNDED', **result}, indent=2))


if __name__ == '__main__':
    main()
