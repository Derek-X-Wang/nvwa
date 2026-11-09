#!/usr/bin/env python3
"""Real Mac CLI file/asset smoke, not a window/Metal/rendering claim."""
import argparse
import json
from pathlib import Path
import platform
import subprocess
import tempfile


def run_smoke(binary, assets):
    """Platform-neutral CLI semantics; only main certifies the Darwin host."""
    binary, assets = binary.resolve(), assets.resolve()
    with tempfile.TemporaryDirectory(prefix='nvwa-mac-smoke-') as d:
        root = Path(d)
        work = root / 'work.json'

        def run(*args, error=None):
            r = subprocess.run([str(binary), *map(str, args)], capture_output=True,
                               text=True, timeout=30, cwd=root)
            if error is None:
                if r.returncode != 0 or r.stderr:
                    raise ValueError('CLI success contract failed: '+r.stderr)
                return json.loads(r.stdout)
            if r.returncode != 1 or r.stdout:
                raise ValueError('negative CLI did not reject cleanly')
            diagnostic = json.loads(r.stderr)
            if diagnostic.get('code') != error:
                raise ValueError('wrong CLI refusal: '+r.stderr)
            return diagnostic

        created = run('new-character-waist', assets, work)
        if created.get('asset_checked') is not True:
            raise ValueError('creation did not authenticate assets')
        before = work.read_bytes()
        run('validate', work, assets)
        observed = run('inspect', work)
        if observed['profile']['id'] != 'nvwa-mpfb-b1-waist-v1' or observed['timeline']:
            raise ValueError('unexpected actual Work identity')
        missing = root / 'missing-assets'
        missing.mkdir()
        run('validate', work, missing, error='asset_missing')
        run('validate', work, error='asset_root_required')
        rejected = root / 'rejected.json'
        run('new-character-waist', missing, rejected, error='asset_missing')
        if rejected.exists():
            raise ValueError('failed creation wrote a Work')
        saved = root / 'saved.json'
        run('save', work, saved)
        run('validate', saved, assets)
        reopened = run('inspect', saved)
        if reopened != observed or work.read_bytes() != before or json.loads(saved.read_bytes()) != json.loads(before):
            raise ValueError('Work changed across validation/save')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--binary', type=Path, required=True)
    p.add_argument('--assets', type=Path, required=True)
    a = p.parse_args()
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise SystemExit('Mac smoke requires real Darwin arm64')
    run_smoke(a.binary, a.assets)
    print('PASS: actual Darwin CLI creation, full asset validation, exact missing-root refusals and save/reopen semantics; no UI/Metal/render claim')


if __name__ == '__main__':
    main()
