"""Fetch only the human-approved bill, excluding the superseded Blender DMG."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
STAGE = ROOT / '.work/character-approved-20261016'
REPORT = Path(__file__).resolve().parent
MANIFEST = ROOT / 'experiments/53-character-comparison/downloads/manifest.json'
APPROVED_SHA = '234584fae55334e4a7a20f76e4aecd88e604200789b75d0e7ac7d4c67328b4ce'
assert hashlib.sha256(MANIFEST.read_bytes()).hexdigest() == APPROVED_SHA
approval = json.loads((STAGE / 'authorization.json').read_text())
amendment = json.loads((STAGE / 'blender-homebrew-amendment.json').read_text())
assert approval['approved_manifest_sha256'] == APPROVED_SHA
assert amendment['remaining_approved_manifest_sha256'] == APPROVED_SHA
assert amendment['supersedes_download_item'].startswith('blender-reference')
manifest = json.loads(MANIFEST.read_text())
UA = {'User-Agent': 'Nvwa-approved-character-sample/1.0', 'Accept-Encoding': 'identity'}


def now():
    return datetime.now(timezone.utc).isoformat()


def write_receipt(name, data):
    target = REPORT / (name + '.json')
    temporary = target.with_suffix('.json.part')
    temporary.write_text(json.dumps(data, indent=2) + '\n')
    temporary.replace(target)


def fetch(url, destination, size, sha256=None, git_blob_sha1=None, reuse=None):
    if not url.startswith('https://'):
        raise ValueError('Approved downloads require HTTPS')
    destination.parent.mkdir(parents=True, exist_ok=True)
    started = now()
    actual_headers = None
    actual_url = url
    reused = False
    temporary = None
    try:
        if destination.exists():
            check_path = destination
            body = check_path.read_bytes()
            reused = True
            sha = hashlib.sha256(body).hexdigest()
            count = len(body)
        else:
            # This invocation owns only this fresh staging file. An interrupted
            # sibling .part is never a verification input or promotion candidate.
            descriptor, name = tempfile.mkstemp(prefix=destination.name + '.', suffix='.part', dir=destination.parent)
            os.close(descriptor)
            temporary = check_path = Path(name)
            if reuse:
                body = reuse.read_bytes()
                temporary.write_bytes(body)
                sha = hashlib.sha256(body).hexdigest()
                count = len(body)
                reused = True
            else:
                digest = hashlib.sha256()
                count = 0
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as response:
                    actual_url = response.url
                    if not actual_url.startswith('https://'):
                        raise ValueError('Approved download redirected outside HTTPS')
                    actual_headers = dict(response.headers)
                    with temporary.open('wb') as out:
                        while chunk := response.read(1024 * 1024):
                            count += len(chunk)
                            if count > size:
                                raise ValueError(f'Approved size exceeded: {destination.name}')
                            digest.update(chunk)
                            out.write(chunk)
                sha = digest.hexdigest()
        if count != size:
            raise ValueError(f'Approved size mismatch: {destination.name}: {count} != {size}')
        if sha256 and sha != sha256:
            raise ValueError(f'Approved SHA256 mismatch: {destination.name}')
        git_actual = None
        if git_blob_sha1:
            blob = check_path.read_bytes()
            git_actual = hashlib.sha1(b'blob ' + str(len(blob)).encode() + b'\0' + blob).hexdigest()
            if git_actual != git_blob_sha1:
                raise ValueError(f'Approved Git blob SHA1 mismatch: {destination.name}')
        if temporary is not None:
            temporary.replace(destination)
            temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {'url': url, 'resolved_url': actual_url, 'path': str(destination.relative_to(ROOT)),
            'bytes': count, 'sha256': sha, 'published_sha256': sha256,
            'git_blob_sha1': git_actual, 'expected_git_blob_sha1': git_blob_sha1,
            'reused_existing_or_review_license': reused, 'downloaded_bytes': 0 if reused else count,
            'response_headers': actual_headers, 'started_at': started, 'completed_at': now(),
            'status': 'verified'}


def archive(item):
    preflight = None
    if item['id'] == 'system-assets':
        with urllib.request.urlopen(urllib.request.Request(item['url'], headers=UA, method='HEAD'), timeout=30) as r:
            preflight = dict(r.headers)
        lowered = {k.lower(): v for k, v in preflight.items()}
        assert int(lowered['content-length']) == item['transfer_bytes']
        assert lowered['last-modified'] == item['head_last_modified']
        assert lowered['etag'] == item['head_etag']
        write_receipt('system-assets-head-preflight', {'status': 'matched-approved-metadata', 'headers': preflight, 'checked_at': now()})
    receipt = fetch(item['url'], STAGE / 'downloads' / item['filename'], item['transfer_bytes'], item.get('sha256'))
    receipt['id'] = item['id']
    receipt['preflight_headers'] = preflight
    receipt['upstream_published_digest_available'] = item.get('sha256') is not None
    write_receipt(item['id'] + '-download', receipt)
    print(item['id'], 'verified', receipt['bytes'], receipt['sha256'], flush=True)
    return receipt


def source():
    receipts = []
    for f in manifest['optional_B_items']['source']['files']:
        review_license = ROOT / 'experiments/53-character-comparison/downloads/licenses/humentity-LICENSE' if f['path'] == 'LICENSE' else None
        receipts.append(fetch(f['url'], STAGE / 'upstream/Humentity' / f['path'], f['size'], git_blob_sha1=f['git_blob_sha1'], reuse=review_license))
    data = {'id': 'humentity-source', 'status': 'verified', 'commit': manifest['optional_B_items']['source']['commit'],
            'files': receipts, 'bytes': sum(x['bytes'] for x in receipts),
            'downloaded_bytes': sum(x['downloaded_bytes'] for x in receipts), 'completed_at': now()}
    write_receipt('humentity-source-download', data)
    print('humentity-source verified', len(receipts), 'files', data['bytes'], flush=True)
    return data


def crates():
    receipts = []
    for c in manifest['optional_B_items']['known_missing_crates']:
        filename = c['id'] + '-' + c['version'] + '.crate'
        receipts.append(fetch(c['url'], STAGE / 'crates' / filename, c['transfer_bytes'], c['sha256']))
    data = {'id': 'known-crates', 'status': 'verified', 'files': receipts,
            'bytes': sum(x['bytes'] for x in receipts), 'completed_at': now()}
    write_receipt('known-crates-download', data)
    print('known-crates verified', data['bytes'], flush=True)
    return data


if __name__ == '__main__':
    jobs = [lambda item=item: archive(item) for item in manifest['common_items'] if item['id'] != 'blender-reference'] + [source, crates]
    results = []
    errors = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for future in as_completed([pool.submit(job) for job in jobs]):
            try:
                results.append(future.result())
            except Exception as exc:
                errors.append(repr(exc))
                print('BLOCKER', repr(exc), flush=True)
    total = sum(r['bytes'] for r in results)
    report = {'status': 'verified' if not errors else 'partial', 'approved_manifest_sha256': APPROVED_SHA,
              'blender_original_dmg_skipped': True, 'root_owned_homebrew_upgrade': True,
              'content_bytes': total, 'approved_non_blender_content_bytes': 327316919,
              'results': results, 'errors': errors, 'completed_at': now(),
              'archives_extracted': False, 'code_executed': False}
    if not errors:
        assert total == 327316919
    write_receipt('download-receipt', report)
    raise SystemExit(bool(errors))
