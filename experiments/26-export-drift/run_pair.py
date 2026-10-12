#!/usr/bin/env python3
"""Bounded, serial two-process fixture exports. Never publishes assets."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / '.work/export-drift'
PROTECTED = [*sorted((ROOT / 'assets').rglob('*')), *sorted((ROOT / 'tools/blender').glob('*.py')), *sorted((ROOT / 'experiments/01-character').glob('*'))]
PROTECTED = [path for path in PROTECTED if path.is_file()]
COMPARATOR = Path(__file__).with_name('compare.py')

def hashes():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in PROTECTED}

def run_comparison(left, right, output):
    subprocess.run([sys.executable, str(COMPARATOR), str(left), str(right), '--output', str(output)], check=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', default='control')
    parser.add_argument('--factory-startup', action='store_true')
    args = parser.parse_args()
    assert args.label.replace('-', '').isalnum(), 'Use a simple unique label'
    directory = PRIVATE / args.label
    directory.mkdir(parents=True, exist_ok=False)
    before = hashes()
    (directory / 'protected-before.json').write_text(json.dumps(before, indent=2) + '\n')
    result = {'factory_startup': args.factory_startup, 'runs': []}
    try:
        for idx in (1, 2):
            output = directory / f'run-{idx}'
            output.mkdir()
            command = ['/opt/homebrew/bin/blender', '-b', '-t', '2']
            if args.factory_startup:
                command.append('--factory-startup')
            command += ['--python-exit-code', '1', '--python', 'tools/blender/generate_fixture.py']
            env = dict(os.environ, NVWA_RENDER_PREVIEWS='0', NVWA_FIXTURE_OUTPUT=str(output))
            start = time.time()
            with (directory / f'run-{idx}.log').open('w') as log:
                proc = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
                entry = {'pid': proc.pid, 'argv': command, 'output': str(output.relative_to(ROOT)), 'started_unix': start}
                result['runs'].append(entry)
                (directory / 'processes.json').write_text(json.dumps(result, indent=2) + '\n')
                print(f'RUN {idx} PID {proc.pid}', flush=True)
                entry.update(exit_code=proc.wait(), elapsed_seconds=time.time()-start)
            (directory / 'processes.json').write_text(json.dumps(result, indent=2) + '\n')
            if entry['exit_code']:
                raise RuntimeError(f'Blender failed; inspect run-{idx}.log')
    finally:
        after = hashes()
        (directory / 'protected-after.json').write_text(json.dumps(after, indent=2) + '\n')
        assert before == after, 'Protected source or fixture files changed'
    run_comparison(directory / 'run-1', directory / 'run-2', directory / 'comparison.json')

if __name__ == '__main__':
    main()
