#!/usr/bin/env python3
"""Bind the exact source/input cohort and finished artifact; no history reads."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--platform', choices=['native', 'web'], required=True)
parser.add_argument('--artifact', type=Path, required=True)
parser.add_argument('--run-id', required=True)
parser.add_argument('--snapshot-receipt', type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[3]
probe = Path(__file__).resolve().parent
files = [root / 'Cargo.toml', root / 'Cargo.lock', root / 'rust-toolchain.toml', root / 'assets/character.profile.json', root / 'assets/fonts/NvwaSansSC-Regular.ttf']
for required in files:
    if not required.is_file():
        raise SystemExit('missing required build input: '+str(required.relative_to(root)))
for directory in [root / 'crates', probe]:
    files += [p for p in directory.rglob('*') if p.is_file()
              and p.suffix in {'.rs', '.toml', '.lock', '.py', '.md'}
              and 'results' not in p.relative_to(directory).parts
              and '__pycache__' not in p.relative_to(directory).parts]
files += [root / 'experiments/48-genuine-fixture-work/artifacts' / p
          for p in ['genuine44-calibrated47.nvwa.json', 'character.profile.json',
                    'assets/generated/genuine44-calibrated47.glb']]
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
result = {'schema_version': 1, 'platform': args.platform,
          'build_run_id': args.run_id,
          'rustc': subprocess.check_output(['rustc', '-Vv'], text=True).strip(),
          'cargo': subprocess.check_output(['cargo', '-V'], text=True).strip(),
          'files': {str(p.relative_to(root)): digest(p) for p in sorted(set(files))},
          'artifact': {'name': args.artifact.name,
                       'bytes': args.artifact.stat().st_size,
                       'sha256': digest(args.artifact)}}
snapshot = json.loads(args.snapshot_receipt.read_text())
if snapshot.get('status') != 'complete' or snapshot.get('exit_code') != 0:
    raise SystemExit('snapshot build did not complete')
for relative, expected in snapshot['source_files'].items():
    if digest(root / relative) != expected:
        raise SystemExit('snapshot/current source mismatch: '+relative)
if snapshot['artifact']['sha256'] != digest(args.artifact):
    raise SystemExit('snapshot/current artifact mismatch')
result['snapshot_build'] = snapshot
result['snapshot_matches_current'] = True
out = probe / 'results' / (args.platform + '-cohort.json')
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
print(out)
