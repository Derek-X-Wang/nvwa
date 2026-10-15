#!/usr/bin/env python3
"""Actual owned-child failure controls; no provider/model process."""
import json
import os
from pathlib import Path
import signal
import sys
from unittest.mock import patch
import uuid

import run_guard as guard
from float_prerequisite import RECEIPT, verify_float_prerequisite


def main(receipt_name='failure-controls.json'):
    base = guard.PRIVATE / ('failure-controls-' + uuid.uuid4().hex[:8])
    base.mkdir()
    rows = {}
    real_inspect = guard.group_rss
    real_signal = guard.signal_group
    ready = base / 'inspection-ready'
    command = [sys.executable, '-B', '-c',
               f'import os,signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); open({str(ready)!r},"w").write(str(os.getpid())); time.sleep(60)']

    def failed_inspection(pgid):
        if ready.exists():
            raise RuntimeError('CONTROL: owned-group ps inspection unavailable')
        return real_inspect(pgid)

    with patch.object(guard, 'group_rss', failed_inspection):
        rows['inspection_failure'] = guard.guarded(command, base / 'inspection', seconds=2)
    inspection = rows['inspection_failure']
    assert inspection['reason'] == 'cleanup_unconfirmed'
    assert not inspection['owned_group_exit_verified']
    assert signal.SIGKILL in inspection['cleanup_signals']
    assert inspection['returncode'] == -signal.SIGKILL
    assert (base / 'inspection/receipt.json').is_file()
    assert not real_inspect(inspection['pgid'])
    inspection['independent_post_control_group_absent'] = True

    # The leader waits until its descendant ignores TERM, then exits. Cleanup
    # must still signal this live group after the direct leader has exited.
    ready = base / 'descendant-ready'
    child_code = f'import os,signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); open({str(ready)!r},"w").write(str(os.getpid())); time.sleep(60)'
    leader_code = f'import subprocess,sys,time; p=subprocess.Popen([sys.executable,"-B","-c",{child_code!r}]);\nwhile not __import__("pathlib").Path({str(ready)!r}).exists(): time.sleep(.01)\n'
    rows['exited_leader'] = guard.guarded([sys.executable, '-B', '-c', leader_code], base / 'leader', seconds=2)
    leader = rows['exited_leader']
    assert leader['returncode'] == 0 and leader['remaining_members_after_term']
    assert signal.SIGKILL in leader['cleanup_signals'] and leader['owned_group_exit_verified']
    assert not real_inspect(leader['pgid'])

    def cancel_during_term(pgid, sig):
        real_signal(pgid, sig)
        if sig == signal.SIGTERM:
            os.kill(os.getpid(), signal.SIGTERM)

    with patch.object(guard, 'signal_group', cancel_during_term):
        rows['cancel_during_teardown'] = guard.guarded(
            [sys.executable, '-B', '-c', 'import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)'],
            base / 'cancel', seconds=.2)
    cancelled = rows['cancel_during_teardown']
    assert cancelled['reason'] == 'cancelled' and cancelled['deferred_cancel_signals'] == [signal.SIGTERM]
    assert cancelled['returncode'] == -signal.SIGKILL and cancelled['owned_group_exit_verified']
    assert (base / 'cancel/receipt.json').is_file() and not real_inspect(cancelled['pgid'])

    float_checks = {'valid': verify_float_prerequisite()}
    altered = json.loads(RECEIPT.read_text())
    altered['identity']['runtime']['binary_sha256'] = '0' * 64
    stale = base / 'stale-float-receipt.json'
    stale.write_text(json.dumps(altered))
    for name, path in [('missing', base / 'missing.json'), ('stale_runtime', stale)]:
        try:
            verify_float_prerequisite(path)
        except (FileNotFoundError, RuntimeError) as error:
            float_checks[name] = {'rejected': True, 'error': str(error)}
        else:
            raise AssertionError('Missing/stale C++ format prerequisite accepted')
    # Execute the actual run entrypoint with the prerequisite seam failing.
    # This must reject before any artifact/provenance/provider launch path.
    with patch('float_prerequisite.verify_float_prerequisite', side_effect=RuntimeError('CONTROL: missing format receipt')), patch.object(guard, 'guarded', side_effect=AssertionError('provider launch reached')):
        try:
            guard.run('CONTROL: no model/run authorization')
        except RuntimeError as error:
            assert str(error) == 'CONTROL: missing format receipt'
            float_checks['run_entrypoint'] = {'rejected_before_launch': True}
        else:
            raise AssertionError('Run entrypoint skipped float prerequisite')
    report = {'guard_controls': rows, 'float_checks': float_checks, 'no_model_or_provider_run': True}
    (guard.HERE / 'evidence' / receipt_name).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({name: {'reason': row['reason'], 'returncode': row['returncode'],
                             'owned_group_exit_verified': row['owned_group_exit_verified']} for name, row in rows.items()}, indent=2))


if __name__ == '__main__':
    main()
