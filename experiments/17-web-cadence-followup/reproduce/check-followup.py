#!/usr/bin/env python3
"""Offline checks of production-called cadence invariants and owned lifecycle, no server/GPU."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,help='Optional new exclusive evidence file; default stdout only')
args=parser.parse_args()
here = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('followup', here / 'followup.py')
f = importlib.util.module_from_spec(spec); spec.loader.exec_module(f)
old = f.REPO / 'docs/evidence/m1-1'
checks = []
for workload in ('idle', 'finite'):
    logs = json.loads((old / f'A1-{workload}-console.json').read_text())
    r, _ = json.JSONDecoder().raw_decode(logs[0]['message'].split('NVWA_EVIDENCE ', 1)[1])
    assert not f.runtime_checks(r, workload)
    for key, bad in [('frame_sample_count', 599), ('playing', not r['playing']), ('ready', False), ('joints', 17), ('frame_ms_p95', 0)]:
        mutated = dict(r, **{key: bad})
        assert key in f.runtime_checks(mutated, workload)
    checks.append(workload + ': valid report accepted; five invalid report variants rejected')
for ignore in (False, True):
    code = 'import time; time.sleep(20)' if not ignore else 'import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(20)'
    child = subprocess.Popen([sys.executable, '-c', code], start_new_session=True)
    import time
    time.sleep(.15)
    record = {'pid': child.pid, 'process_identity': f.owner(child.pid)}
    mismatch = dict(record, process_identity=record['process_identity'] + 'wrong')
    try:
        f.stop_owned(mismatch, .3)
        raise AssertionError('Mismatched identity accepted')
    except RuntimeError:
        assert child.poll() is None
    result = f.stop_owned(record, .3)
    child.wait(timeout=2)
    assert result['group_absent'] and result['kill_escalated'] == ignore
    checks.append({'lifecycle_ignore_TERM': ignore, **result, 'direct_child_reaped': True, 'mismatched_identity_rejected': True})
with tempfile.TemporaryDirectory() as directory:
    target = Path(directory) / 'exclusive.json'
    f.save(target, {'saved': True})
    try:
        f.save(target, {'saved': False})
        raise AssertionError('Overwrite accepted')
    except FileExistsError:
        assert json.loads(target.read_text()) == {'saved': True}
checks.append('Evidence overwrite rejected')
assert f.owner(99999) == ''
assert f.stop_owned({'pid':99999,'process_identity':'absent'})['group_absent']
child = subprocess.Popen([sys.executable, '-c', 'pass'], start_new_session=True)
record = {'pid':child.pid,'process_identity':f.owner(child.pid)}
child.wait(timeout=2)
assert f.stop_owned(record)['already_absent']
checks.append('Absent PID and exited/reaped child cleanup accepted; group absence observed')
assert f.cadence_passes(20,22)
assert not f.cadence_passes(20,22.000001)
checks.append('Exact10% boundary accepted; larger regression rejected')
ledger = [dict(row,ordinal=i+1,epoch_seconds=float(i),monotonic_seconds=float(i)) for i,row in enumerate(f.ATTEMPTS)]
assert f.ledger_checks(ledger)
reordered = list(ledger); reordered[0],reordered[2] = reordered[2],reordered[0]
assert not f.ledger_checks(reordered)
assert not f.ledger_checks(ledger[:-1])
bad_time = [dict(row) for row in ledger]; bad_time[1]['epoch_seconds'] = 0
assert not f.ledger_checks(bad_time)
checks.append('Complete ordered attempt ledger accepted; reordering/missing/nonchronological rejected')
unknown = {'visibility':'visible','focus':None,'focus_observation':'unavailable:DOM scope has no hasFocus','browser_visible':True,'ax_focus':'canvas observed by actual AX snapshot','canvas':{'width':1280,'height':720}}
assert f.endpoint_checks(unknown)
descriptive = f.pair_result(20,22,not f.endpoint_checks(unknown))
assert not descriptive['valid'] and not descriptive['passes'] and descriptive['A_p95_ms'] == 20 and descriptive['B_p95_ms'] == 22 and descriptive['descriptive_cadence_within_10_percent']
checks.append({'unknown_document_focus': 'invalid and strict gate cannot pass', 'descriptive_pair_preserved':descriptive})
with tempfile.TemporaryDirectory() as directory:
    real_owner = f.owner
    for scenario in ('startup_exit', 'metadata_failure'):
        state = Path(directory) / (scenario + '.json')
        if scenario == 'metadata_failure':
            def broken_owner(pid):
                raise RuntimeError('injected metadata observation failure')
            f.owner = broken_owner
        try:
            with (Path(directory) / (scenario + '.log')).open('x') as stream:
                code = 'raise SystemExit(7)' if scenario == 'startup_exit' else 'import time;time.sleep(20)'
                try:
                    f.spawn_with_record([sys.executable,'-c',code],stream,state,'offline-check')
                    raise AssertionError('Expected startup failure')
                except RuntimeError:
                    pass
            result = json.loads(state.read_text())
            assert result['status'] == 'FAILED_START' and result['cleanup']['direct_child_reaped'] and result['cleanup']['group_absent']
            checks.append({'scenario':scenario,'attempt_retained':True,**result['cleanup']})
        finally:
            f.owner = real_owner
if args.output:
    f.save(args.output, {'status': 'PASS', 'checks': checks, 'server_GPU': 'NOT-RUN'})
print(json.dumps(checks, indent=2))
