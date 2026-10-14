#!/usr/bin/env python3
"""Sequential real-renderer controls. Requires exclusive GPU scheduling token."""
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIVATE = ROOT / '.work/m12-retarget'
binary = PRIVATE / 'Nvwa-retarget.app/Contents/MacOS/Nvwa'
environment = dict(os.environ, RUST_LOG='info', NVWA_ASSET_ROOT=str(PRIVATE / 'assets'))
receipts = []
for variant, mode in [('reference', 'rest'), ('naive', 'rest'), ('corrected', 'rest'),
                      ('reference', 'wave'), ('naive', 'wave')]:
    label = f'{variant}-{mode}-smoke'
    args = [str(binary), '--player', '--benchmark', '--work',
            str(PRIVATE / f'works/{variant}-{mode}.nvwa.json'),
            '--smoke', '--smoke-seconds', '1', '--timeout', '30',
            '--capture', str(HERE / f'screens/{label}.png')]
    log = HERE / f'{label}.log'
    with log.open('w') as output:
        process = subprocess.Popen(args, cwd=ROOT, env=environment, stdout=output, stderr=subprocess.STDOUT)
        try:
            code = process.wait(timeout=40)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            raise
    receipt = {'variant': variant, 'mode': mode, 'pid': process.pid,
               'args': args, 'exit_code': code, 'log': str(log)}
    receipts.append(receipt)
    (HERE / 'smoke-processes.json').write_text(json.dumps(receipts, indent=2)+'\n')
    assert code == 0, receipt
print(json.dumps(receipts, indent=2))
