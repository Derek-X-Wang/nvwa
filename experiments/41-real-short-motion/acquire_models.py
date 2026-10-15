#!/usr/bin/env python3
"""NOT AUTHORIZED YET: acquire exactly three proposal artifacts after approval.

The flag records actual human authorization obtained outside this script. It is
not permission by itself. No credentials, terms acceptance, retries, or fallback.
"""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approved-download', required=True, metavar='AUTHORIZATION_RECEIPT')
    args = parser.parse_args()
    if not args.approved_download.strip():
        raise SystemExit('Explicit prior authorization must be recorded')
    proposal = json.loads((HERE / 'proposal.json').read_text())
    output = ROOT / '.work/m2-provider/approved-models'
    output.mkdir(parents=True, exist_ok=True)
    receipts = []
    for artifact in proposal['artifacts']:
        target = output / Path(artifact['path']).name
        if target.exists():
            raise SystemExit(f'Refusing to overwrite {target}')
        partial = target.with_suffix('.partial')
        count = 0
        digest = hashlib.sha256()
        # ProxyHandler({}) avoids reading account-specific proxy configuration.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(artifact['download_url_after_approval_only'], timeout=30) as response, partial.open('xb') as stream:
            while data := response.read(1 << 20):
                count += len(data)
                if count > artifact['bytes']:
                    raise ValueError('Response exceeds explicitly approved artifact size')
                digest.update(data)
                stream.write(data)
        if count != artifact['bytes'] or digest.hexdigest() != artifact['sha256']:
            raise ValueError('Artifact bytes/hash mismatch; partial retained, no retry')
        partial.rename(target)
        receipts.append(artifact | {'local_path': str(target), 'verified_bytes': count, 'verified_sha256': digest.hexdigest()})
        (output / 'acquisition-receipt.json').write_text(json.dumps({'authorization_receipt': args.approved_download, 'artifacts': receipts}, indent=2) + '\n')
    print(f'Verified {sum(r["verified_bytes"] for r in receipts)} exact model bytes; inference not started')


if __name__ == '__main__':
    main()
