#!/usr/bin/env python3
"""Replay only the fixed public text/metadata inventory; never download models."""
import datetime
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def main():
    output = ROOT / '.work/m2-provider/sources'
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, url in json.loads((HERE / 'evidence/source-index.json').read_text()).items():
        assert url.startswith(('https://raw.githubusercontent.com/', 'https://api.github.com/', 'https://huggingface.co/'))
        assert not any(s in url.lower() for s in ['.gguf', '.safetensors', '.pt', '.pth', '.bin', '.npz', '.pkl'])
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Nvwa-public-text-preflight/1'}), timeout=20) as response:
            data = response.read(2_097_153)
            if len(data) > 2_097_152:
                raise ValueError('public text response exceeds 2 MiB')
            data.decode('utf-8')
            rows.append({'file': name, 'url': url, 'status': response.status, 'bytes': len(data),
                         'sha256': hashlib.sha256(data).hexdigest(),
                         'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()})
        (output / name).write_bytes(data)
    (output / 'replayed-receipts.json').write_text(json.dumps(rows, indent=2) + '\n')
    print(f'{len(rows)} text responses collected; no model payload requested')


if __name__ == '__main__':
    main()
