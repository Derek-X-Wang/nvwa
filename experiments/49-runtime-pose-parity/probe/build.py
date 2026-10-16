#!/usr/bin/env python3
"""Run inside the Wefty snapshot; retain its actual build inputs and outcome."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument('--platform', choices=['native', 'web'], required=True)
parser.add_argument('--target-dir', type=Path, required=True)
parser.add_argument('--receipt', type=Path, required=True)
args = parser.parse_args()
if not args.target_dir.is_absolute() or not args.receipt.is_absolute():
    parser.error('owned target and receipt must be absolute')
root = Path(__file__).resolve().parents[3]
probe = Path(__file__).resolve().parent
files = [root / 'Cargo.toml', root / 'Cargo.lock',
         root / 'rust-toolchain.toml', root / 'assets/character.profile.json',
         root / 'assets/fonts/NvwaSansSC-Regular.ttf']
for required in files:
    if not required.is_file():
        raise SystemExit('missing required build input: '+str(required.relative_to(root)))
for directory in [root / 'crates', probe]:
    files += [p for p in directory.rglob('*') if p.is_file()
              and p.suffix in {'.rs', '.toml', '.lock', '.py', '.html'}
              and 'results' not in p.relative_to(directory).parts
              and '__pycache__' not in p.relative_to(directory).parts]
files += [root / 'experiments/48-genuine-fixture-work/artifacts' / p
          for p in ['genuine44-calibrated47.nvwa.json', 'character.profile.json',
                    'assets/generated/genuine44-calibrated47.glb']]
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
command = ['cargo', 'build', '--offline', '--locked', '--manifest-path',
           'experiments/49-runtime-pose-parity/probe/Cargo.toml', '-j', '2']
if args.platform == 'native':
    command += ['--bin', 'nvwa-runtime-pose-probe']
    artifact = args.target_dir / 'debug/nvwa-runtime-pose-probe'
else:
    command += ['--lib', '--target', 'wasm32-unknown-unknown']
    artifact = args.target_dir / 'wasm32-unknown-unknown/debug/nvwa_runtime_pose_probe.wasm'
record = {'schema_version': 1, 'platform': args.platform, 'command': command,
          'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'source_files': {str(p.relative_to(root)): digest(p) for p in sorted(set(files))},
          'rustc': subprocess.check_output(['rustc', '-Vv'], text=True).strip(),
          'cargo': subprocess.check_output(['cargo', '-V'], text=True).strip()}
args.receipt.parent.mkdir(parents=True, exist_ok=True)
start = time.monotonic()
environment = dict(os.environ, CARGO_TARGET_DIR=str(args.target_dir))
result = subprocess.run(command, cwd=root, env=environment)
record.update(duration_seconds=time.monotonic()-start, exit_code=result.returncode,
              status='complete' if result.returncode == 0 else 'failed')
if result.returncode == 0:
    record['artifact'] = {'name': artifact.name, 'bytes': artifact.stat().st_size,
                          'sha256': digest(artifact)}
args.receipt.write_text(json.dumps(record, indent=2, sort_keys=True)+'\n')
raise SystemExit(result.returncode)
