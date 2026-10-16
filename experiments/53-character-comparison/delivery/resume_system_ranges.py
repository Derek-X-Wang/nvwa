"""Resume only the approved archive remainder; reject changed or full responses."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import urllib.request
import socket

parser = argparse.ArgumentParser()
parser.add_argument('--original-root', type=Path, required=True)
args = parser.parse_args()
root = args.original_root.resolve()
stage = root / '.work/character-approved-20261016'
report = root / 'experiments/53-character-comparison/delivery'
manifest = json.loads((root / 'experiments/53-character-comparison/downloads/manifest.json').read_text())
item = next(x for x in manifest['common_items'] if x['id'] == 'system-assets')
prefix_receipt = json.loads((report / 'system-assets-prefix-receipt.json').read_text())
prefix = stage / 'downloads' / (item['filename'] + '.part')
prefix_length = prefix.stat().st_size
assert prefix_length == prefix_receipt['preserved_prefix_bytes']
assert hashlib.sha256(prefix.read_bytes()).hexdigest() == prefix_receipt['preserved_prefix_sha256']
total = item['transfer_bytes']
base_headers = {'User-Agent': 'Nvwa-approved-character-sample/1.0', 'Accept-Encoding': 'identity'}
requests = []


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def identity(headers):
    assert headers.get('ETag') == item['head_etag']
    assert headers.get('Last-Modified') == item['head_last_modified']


with urllib.request.urlopen(urllib.request.Request(item['url'], headers=base_headers, method='HEAD'), timeout=30) as r:
    identity(r.headers)
    assert int(r.headers['Content-Length']) == total


def receive(index, start, end):
    headers = dict(base_headers, Range=f'bytes={start}-{end}')
    headers['If-Range'] = item['head_etag']
    headers['If-Unmodified-Since'] = item['head_last_modified']
    destination = prefix.with_name(prefix.name + f'.range-{index}')
    assert not destination.exists(), 'Do not silently overwrite a range'
    receipt = {'index': index, 'start': start, 'end': end, 'requested_body_bytes': end-start+1,
               'request_headers': headers, 'started_at': timestamp(), 'received_body_bytes': 0}
    with urllib.request.urlopen(urllib.request.Request(item['url'], headers=headers), timeout=90) as r:
        receipt['status_code'] = r.status
        receipt['response_headers'] = dict(r.headers)
        assert r.status == 206, 'Refuse full response; body not consumed'
        assert r.headers['Content-Range'] == f'bytes {start}-{end}/{total}'
        assert int(r.headers['Content-Length']) == end-start+1
        identity(r.headers)
        digest = hashlib.sha256()
        with destination.open('xb') as out:
            while chunk := r.read(1024 * 1024):
                receipt['received_body_bytes'] += len(chunk)
                assert receipt['received_body_bytes'] <= end-start+1
                out.write(chunk)
                digest.update(chunk)
    assert receipt['received_body_bytes'] == end-start+1
    receipt.update({'sha256': digest.hexdigest(), 'path': str(destination.relative_to(root)),
                    'completed_at': timestamp(), 'status': 'verified-range-identity-and-length'})
    (report / f'system-assets-range-{index}.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print('range', index, 'verified', receipt['received_body_bytes'], flush=True)
    return receipt


remaining = total-prefix_length
with ThreadPoolExecutor(max_workers=4) as pool:
    futures = []
    for index in range(4):
        start = prefix_length + remaining*index//4
        end = prefix_length + remaining*(index+1)//4 - 1
        futures.append(pool.submit(receive, index, start, end))
    for future in as_completed(futures):
        requests.append(future.result())
requests.sort(key=lambda x: x['index'])
assert sum(x['received_body_bytes'] for x in requests) + prefix_length == total
assembled = stage / 'downloads' / (item['filename'] + '.assembled')
digest = hashlib.sha256()
count = 0
with assembled.open('xb') as out:
    for part in [prefix] + [root / x['path'] for x in requests]:
        with part.open('rb') as handle:
            while chunk := handle.read(1024 * 1024):
                count += len(chunk)
                digest.update(chunk)
                out.write(chunk)
assert count == total
destination = stage / 'downloads' / item['filename']
assert not destination.exists()
assembled.replace(destination)
receipt = {'id': 'system-assets', 'status': 'verified-size-and-frozen-local-sha256',
           'url': item['url'], 'path': str(destination.relative_to(root)), 'bytes': count,
           'sha256': digest.hexdigest(), 'upstream_published_digest_available': False,
           'prefix_bytes': prefix_length, 'range_requests': requests,
           'new_range_body_bytes': sum(x['received_body_bytes'] for x in requests),
           'original_get_plus_new_ranges_durable_body_bytes': count,
           'http_tls_socket_overhead_or_cancelled_inflight_bytes': 'not measured',
           'request_scope': 'same approved URL, four non-overlapping ranges; no new full GET',
           'hostname': socket.gethostname(), 'wefty_run_id': __import__('os').environ.get('WEFTY_RUN_ID'),
           'completed_at': timestamp(), 'code_executed': False}
(report / 'system-assets-download.json').write_text(json.dumps(receipt, indent=2)+'\n')
print('system-assets verified', count, digest.hexdigest(), flush=True)
