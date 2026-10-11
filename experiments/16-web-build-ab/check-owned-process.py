#!/usr/bin/env python3
"""Sleeper stubs exercise the same run_owned helper called by Cargo builds."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

spec = importlib.util.spec_from_file_location('experiment', Path(__file__).with_name('experiment.py'))
experiment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(experiment)
results = {}
experiment.WORK.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='owned-process-check-', dir=experiment.WORK) as scratch:
    folder = Path(scratch)
    # The descendant ignores TERM to exercise bounded KILL escalation.
    child = folder / 'child.py'
    child.write_text('import signal,time\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\ntime.sleep(120)\n')
    parent = folder / 'parent.py'
    parent.write_text('import subprocess,sys,time\nfrom pathlib import Path\np=subprocess.Popen([sys.executable,sys.argv[1]])\nPath(sys.argv[2]).write_text(str(p.pid))\ntime.sleep(120)\n')
    with (folder / 'normal.log').open('w') as log:
        result = {}
        experiment.run_owned([sys.executable, '-c', 'print("normal")'], folder, os.environ.copy(), log, lambda *_: None, 5, result, interval=.05, grace=.3)
        assert result['exit_code'] == 0 and not result['cleanup']['group_alive_after_cleanup']
        results['normal'] = result
    for label in ('interruption', 'snapshot_exception', 'timeout'):
        pidfile = folder / (label + '.pid')
        def sample(pid, elapsed):
            if not pidfile.exists():
                return
            time.sleep(.15)  # Let the child install its TERM handler.
            if label == 'interruption':
                raise KeyboardInterrupt('stub cancellation')
            if label == 'snapshot_exception':
                raise RuntimeError('stub snapshot failure')
        result = {}
        with (folder / (label + '.log')).open('w') as log:
            try:
                experiment.run_owned([sys.executable, str(parent), str(child), str(pidfile)], folder, os.environ.copy(), log, sample, .5 if label == 'timeout' else 5, result, interval=.05, grace=.3)
            except (KeyboardInterrupt, RuntimeError) as exc:
                assert label != 'timeout'
            else:
                assert label == 'timeout' and result['timed_out']
        assert pidfile.exists(), 'Descendant never started'
        descendant = int(pidfile.read_text())
        remaining = subprocess.run(['ps', '-p', str(descendant), '-o', 'pid=,stat=,command='], capture_output=True, text=True)
        assert remaining.returncode != 0, 'Descendant still exists: ' + remaining.stdout
        assert not experiment.group_alive(result['owned_pid']), 'Owned process group still exists'
        assert result['cleanup']['kill_sent'], 'TERM-ignoring descendant did not exercise KILL'
        result['descendant_pid'] = descendant
        result['descendant_gone'] = True
        results[label] = result
experiment.save('owned-process-checks.json', results)
print(json.dumps(results, indent=2))
