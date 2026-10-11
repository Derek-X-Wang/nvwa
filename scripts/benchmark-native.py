"""Run one real native renderer; retain timing limits and per-child peak RSS."""
from pathlib import Path
import argparse
import datetime
import json
import os
import platform
import resource
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument('--profile', choices=['debug', 'release'], default='release')
parser.add_argument('--seconds', type=float, default=15)
parser.add_argument('--label', default='native-release')
parser.add_argument('--work', type=Path, help='Load this work before measuring the real renderer')
parser.add_argument('--player', action='store_true', help='Measure the editor-free Player')
args = parser.parse_args()
root = Path(__file__).resolve().parent.parent
evidence = root / 'docs/evidence/performance'
evidence.mkdir(parents=True, exist_ok=True)
if not args.label.replace('-', '').replace('_', '').isalnum():
    raise SystemExit('Label must be a safe filename')
image = evidence / (args.label + '.png')
log = evidence / (args.label + '.log')
command = [str(root / 'target' / args.profile / 'nvwa-studio'), '--benchmark', '--smoke',
           '--smoke-seconds', str(args.seconds), '--capture', str(image), '--timeout', '90']
if args.work:
    command.extend(['--work', str(args.work.resolve(strict=True))])
if args.player:
    command.append('--player')
environment = dict(os.environ)
environment['RUST_LOG'] = 'info,wgpu=warn,naga=warn'
start_utc = datetime.datetime.now(datetime.timezone.utc)
started = time.perf_counter()
with log.open('w') as output:
    result = subprocess.run(command, cwd=root, env=environment, stdout=output,
                            stderr=subprocess.STDOUT, timeout=120)
wall_seconds = time.perf_counter() - started
lines = log.read_text().splitlines()
records = [json.loads(line.split('NVWA_EVIDENCE ', 1)[1])
           for line in lines if 'NVWA_EVIDENCE ' in line]
rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
report = {
    'command': command, 'exit_code': result.returncode,
    'process_start_utc': start_utc.isoformat(), 'process_total_wall_seconds': wall_seconds,
    'peak_child_rss_bytes': int(rss if platform.system() == 'Darwin' else rss * 1024),
    'memory_kind': 'child process peak RSS, not GPU or total unified allocation',
    'image': str(image.relative_to(root)), 'runtime': records[-1] if records else None,
    'concurrent_heavy_jobs': 'must be independently checked by operator',
}
if records:
    # The app clock starts at its first update. A real capture log gives a
    # process-relative visibility upper bound, including renderer initialization.
    line = next(line for line in reversed(lines) if 'NVWA_EVIDENCE ' in line)
    timestamp = line.split()[0]
    try:
        logged = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        report['process_visible_upper_bound_seconds'] = (logged - start_utc).total_seconds()
        report['visible_kind'] = 'actual screenshot completed, includes requested warmup; not exact first presentation'
    except ValueError:
        report['process_visible_upper_bound_seconds'] = None
(evidence / (args.label + '.json')).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
raise SystemExit(result.returncode if records else 1)
