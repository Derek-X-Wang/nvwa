#!/usr/bin/env python3
"""Strict single-run9203 reconciliation. No listener, browser or renderer is started."""
import argparse
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
E24 = HERE.parent / '24-http-cold-startup'
WORK = 'works/canonical-work.nvwa.json'
WORK_SHA = 'cacf849f0918648a1a970452d0c33f195c5ad89fd7f6d9e58669d587d0789768'
META = 'assets/fixtures/nvwa-humanoid.glb.meta'
SUCCESS = ('index.html', 'startup-diagnostics.js', 'nvwa_studio.js',
           'nvwa_studio_bg.wasm', WORK, 'assets/fixtures/nvwa-humanoid.glb')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify(capture, manifest, requests, packet, frozen_receipt):
    """Validate all raw rows; the two exact404 dispositions are explicit results."""
    packet = Path(packet)
    root = REPO / '.work/m11-startup/frozen-web-baseline'
    run = capture.get('runId')
    require(isinstance(run, str) and re.fullmatch(r'[0-9a-f]{32}', run), 'bad run identity')
    prefix = f'/run/{run}/'
    origin = 'http://127.0.0.1:9203'
    target = prefix + 'index.html?benchmark=1&work=' + WORK
    require(capture.get('url') == origin + target, 'exact9203 canonical Work URL mismatch')
    require(manifest.get('schema') == 'nvwa-http-startup-manifest-v1'
            and manifest.get('bind') == '127.0.0.1' and manifest.get('port') == 9203
            and manifest.get('runIds') == [run] and manifest.get('runLimit') == 1
            and manifest.get('cacheControl') == 'no-store'
            and manifest.get('root') == str(root), 'manifest scope/run mismatch')
    require(frozen_receipt['base'] == '045d8abc685760d09ba05afec0e40a811a282d1f'
            and frozen_receipt['root'] == str(root)
            and frozen_receipt['canonical_work_sha256'] == WORK_SHA, 'baseline receipt mismatch')
    frozen = manifest['frozenFiles']
    require(set(frozen) == set(frozen_receipt['reused_frozen_files']) | {WORK, WORK + '.gz'},
            'frozen member inventory mismatch')
    for name, expected in frozen_receipt['reused_frozen_files'].items():
        require(frozen[name] == expected, 'frozen manifest identity changed: ' + name)
    for name, expected in frozen.items():
        path = root / name
        require(not path.is_symlink() and path.resolve().is_relative_to(root), 'frozen path escapes root')
        data = path.read_bytes()
        require(len(data) == expected['bytes'] and digest(data) == expected['sha256'],
                'frozen bytes/hash mismatch: ' + name)
        if name.endswith('.gz'):
            require(digest(gzip.decompress(data)) == frozen[name[:-3]]['sha256'], 'gzip identity mismatch')
    require(frozen[WORK]['sha256'] == WORK_SHA, 'canonical Work hash mismatch')
    work = json.loads((root / WORK).read_text())
    require(work['schema_version'] == 1 and work['revision'] == 3
            and [(x['clip_id'], x['start_seconds'], x['duration_seconds']) for x in work['timeline']]
            == [('idle', 0, 3), ('wave', 3, 3), ('turn', 6, 3)], 'canonical Work revision/timeline mismatch')
    diagnostics = manifest['diagnostics']
    for name, key in [('wrapper.html', 'wrapperSha256'), ('collector.js', 'collectorSha256')]:
        require(digest((packet / name).read_bytes()) == diagnostics[key], 'diagnostic hash mismatch: ' + name)
    require(digest((E24 / 'server.py').read_bytes()) == diagnostics['serverSourceSha256'],
            'retained server source changed')
    require(digest((E24 / 'collector.js').read_bytes()) == diagnostics['collectorSha256'],
            'retained collector source changed')
    expected_wrapper = (root / 'index.html').read_text().replace(
        '<head>', '<head>\n  <script src="./startup-diagnostics.js"></script>', 1).encode()
    require(digest(expected_wrapper) == diagnostics['wrapperSha256'], 'wrapper is not exact documented insertion')
    require(manifest['adapter']['sha256'] == digest((HERE / 'web_control_server.py').read_bytes()),
            'launch adapter changed')

    # Explicit9203/Work checks above precede this in-memory normalization.
    # Only capture URL is normalized for the original finite-number/structure
    # checks. Original9201 source and recorded inputs remain unchanged.
    structural = deepcopy(capture)
    structural['url'] = structural['url'].replace('127.0.0.1:9203', '127.0.0.1:9201', 1)
    validate = load_module('retained_structure', E24 / 'check_capture.py').validate
    structure = validate(structural, run)
    require(capture.get('ended') is True and 120000 <= capture['snapshotAtMs'] <= 121000,
            'collector did not end at bounded120s')
    limit = capture.get('resourceTimingLimit', {})
    require(limit.get('entriesBeyondLimit') == 0 and limit.get('browserBufferFullEvents') == 0,
            'resource timing incomplete')

    # Replay only pure response routing, with no Experiment constructor,
    # evidence mutation, socket, listener or new server process.
    server = load_module('retained_response', E24 / 'server.py')
    response = object.__new__(server.Experiment)
    response.run_ids = [run]
    response.files = frozen
    response.export_diagnostics = {name: None for name in diagnostics['exportDiagnostics']}
    missing = {}
    for name, path in [('favicon.ico', '/favicon.ico'), (META, prefix + META)]:
        status, data, mime, encoding, response_run, member = response.response('GET', path, '')
        require(status == 404 and encoding == 'identity', 'retained404 route changed')
        missing[name] = {'status': status, 'body': data, 'encoding': encoding,
                         'run': response_run, 'member': member, 'target': path}
    require(missing['favicon.ico']['body'] == b'unknown run prefix\n'
            and missing[META]['body'] == b'not a served runtime member\n', 'exact404 bytes changed')
    require(META not in frozen and META + '.gz' not in frozen, 'frozen metadata cannot be absent')
    expected_names = set(SUCCESS) | {META, 'favicon.ico'}
    ledger = {}
    for row in requests:
        require(row.get('schema') == 'nvwa-http-request-v1' and row.get('method') == 'GET', 'unexpected request schema/method')
        name = 'favicon.ico' if row.get('target') == '/favicon.ico' else row.get('member')
        require(name in expected_names and name not in ledger, 'unexpected or duplicated ledger row: ' + str(name))
        require(row.get('cacheControl') == 'no-store' and row.get('interrupted') is None,
                'cached/interrupted response: ' + str(name))
        if name in missing:
            expected = missing[name]
            require(row.get('target') == expected['target'] and row.get('runId') == expected['run']
                    and row.get('member') == expected['member'] and row.get('status') == 404
                    and row.get('contentEncoding') == 'identity'
                    and row.get('responseBodySha256') == digest(expected['body'])
                    and row.get('declaredBodyBytes') == len(expected['body'])
                    and row.get('bodyBytesWritten') == len(expected['body']), 'exact404 mismatch: ' + name)
        else:
            expected_target = target if name == 'index.html' else prefix + name
            require(row.get('target') == expected_target and row.get('runId') == run
                    and row.get('status') == 200, 'request target/run/status mismatch: ' + name)
            encoding = row.get('contentEncoding')
            require(encoding in ('identity', 'gzip'), 'unknown encoding')
            if name in ('index.html', 'startup-diagnostics.js'):
                require(encoding == 'identity', 'diagnostic encoding changed')
                body = (packet / ('wrapper.html' if name == 'index.html' else 'collector.js')).read_bytes()
                expected_hash, size = digest(body), len(body)
            else:
                selected = name + ('.gz' if encoding == 'gzip' else '')
                require(selected in frozen, 'unfrozen response')
                expected_hash, size = frozen[selected]['sha256'], frozen[selected]['bytes']
            require(row.get('responseBodySha256') == expected_hash
                    and row.get('declaredBodyBytes') == size and row.get('bodyBytesWritten') == size,
                    'response hash/size mismatch: ' + name)
        ledger[name] = row
    require(set(ledger) == expected_names, 'missing exact ledger member')
    timings = {}
    for row in capture['navigation'] + capture['resources']:
        url = urlsplit(row['name'])
        require(url.scheme == 'http' and url.netloc == '127.0.0.1:9203' and not url.fragment,
                'timing origin mismatch')
        name = 'favicon.ico' if url.path == '/favicon.ico' else url.path.removeprefix(prefix)
        require(name in expected_names and name != META and name not in timings, 'unexpected/duplicated timing entry')
        require(row['name'] == origin + ledger[name]['target'], 'timing URL differs from ledger')
        actual = ledger[name]
        require(row.get('responseStatus') == actual['status'], 'timing response status mismatch')
        require(row['transferSize'] > 0 and row['transferSize'] >= row['encodedBodySize'] > 0
                and row['encodedBodySize'] == actual['bodyBytesWritten'], 'transfer/body timing mismatch')
        decoded = frozen[name]['bytes'] if name not in ('index.html', 'startup-diagnostics.js', 'favicon.ico') else actual['bodyBytesWritten']
        require(row['decodedBodySize'] == decoded, 'decoded identity size mismatch')
        timings[name] = row
    require(set(timings) == set(SUCCESS) | {'favicon.ico'}, 'timing inventory mismatch')
    return {'status': 'PASS', 'runId': run, 'structure': structure,
            'ledgerGetCount': len(ledger), 'successfulRunGetCount': len(SUCCESS),
            'browserTimingEntryCount': len(timings), 'successfulBodyBytesWritten': sum(ledger[x]['bodyBytesWritten'] for x in SUCCESS),
            'allLedgerBodyBytesWritten': sum(x['bodyBytesWritten'] for x in ledger.values()),
            'browserEncodedBodyBytes': sum(x['encodedBodySize'] for x in timings.values()),
            'browserDecodedBodyBytes': sum(x['decodedBodySize'] for x in timings.values()),
            'browserReportedTransferBytes': sum(x['transferSize'] for x in timings.values()),
            'explicit404Dispositions': [{'name': name, 'target': x['target'], 'status': x['status'],
                'bodyBytes': len(x['body']), 'bodySha256': digest(x['body']),
                'bodyAscii': x['body'].decode(), 'browserTimingPresent': name in timings,
                'reason': 'exact retained out-of-run response' if name == 'favicon.ico' else
                'exact optional Bevy metadata fallback; actual GLB200 separately required'} for name, x in missing.items()],
            'canonicalWorkSha256': WORK_SHA, 'canonicalWorkRevision': 3, 'timelineCount': 3,
            'claim': 'exact baseline fresh-prefix/no-store HTTP ledger and browser size reconciliation',
            'limits': ['server successful body writes exclude headers and are not client receipt',
                'browser transferSize is browser-reported, not packet capture',
                'optional metadata404 has no browser resource entry; retained ledger bytes accounted',
                'Bevy TimeReal, browser Performance and host clocks have distinct origins',
                'physical first presentation/cold browser/GPU memory NOT-RUN']}


def load_packet(packet):
    packet = Path(packet)
    return (json.loads((packet / 'browser.json').read_text()), json.loads((packet / 'manifest.json').read_text()),
            [json.loads(x) for x in (packet / 'requests.jsonl').read_text().splitlines() if x], packet,
            json.loads((REPO / '.work/m11-startup/web-baseline-freeze.json').read_text()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify(*load_packet(args.packet))
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, 'FAIL ' + str(error) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
