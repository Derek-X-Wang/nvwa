#!/usr/bin/env python3
"""Exact BSD ps response controls through the real guard inspection seam.

One actual TERM-ignoring owned child is used. Its query receives a captured BSD
diagnostic response after readiness; this does not claim ps actually failed for
that child. Independent ps and emergency cleanup always use the real tool.
"""
import json
import os
import signal
import subprocess
import sys
from unittest.mock import patch
import uuid

import run_guard as guard


def main():
    base = guard.PRIVATE / ('ps-controls-' + uuid.uuid4().hex[:8])
    base.mkdir()
    real_run = subprocess.run
    real_popen = subprocess.Popen
    report = {'production_seam': 'subprocess.run called by unmodified group_rss',
              'no_model_or_provider_run': True}
    observed = {}
    for name, pgid in [('clean_no_match', 99999), ('diagnostic_error', 2147483647)]:
        argv = ['/bin/ps', '-g', str(pgid), '-o', 'pid=,pgid=,rss=']
        result = real_run(argv, capture_output=True, text=True, timeout=2)
        observed[name] = {'argv': argv, 'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
    assert observed['clean_no_match'] == {'argv': observed['clean_no_match']['argv'], 'returncode': 1, 'stdout': '', 'stderr': ''}
    assert observed['diagnostic_error']['returncode'] == 1 and not observed['diagnostic_error']['stdout']
    assert observed['diagnostic_error']['stderr'] == 'ps: process group too large: 2147483647\n'
    report['actual_BSD_responses'] = observed
    ready = base / 'child-ready'
    owned = []

    def record_popen(argv, *args, **kwargs):
        child = real_popen(argv, *args, **kwargs)
        if argv[0] == '/usr/bin/sandbox-exec':
            owned.append(child)
        return child

    def actual_error_at_ps_seam(argv, *args, **kwargs):
        if argv[0] == '/bin/ps' and ready.exists():
            item = observed['diagnostic_error']
            return subprocess.CompletedProcess(argv, item['returncode'], item['stdout'], item['stderr'])
        return real_run(argv, *args, **kwargs)

    try:
        with patch.object(subprocess, 'Popen', record_popen), patch.object(subprocess, 'run', actual_error_at_ps_seam):
            result = guard.guarded([sys.executable, '-B', '-c',
                f'import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); open({str(ready)!r},"w").write("ready"); time.sleep(60)'],
                base / 'guard', seconds=.25)
        report['guard_receipt'] = result
        report['durable_guard_receipt_matches'] = json.loads((base / 'guard/receipt.json').read_text()) == result
        query = real_run(['/bin/ps', '-g', str(result['pgid']), '-o', 'pid=,pgid=,rss='],
                         capture_output=True, text=True, timeout=2)
        report['independent_after_guard'] = {'returncode': query.returncode, 'stdout': query.stdout, 'stderr': query.stderr}
    finally:
        # Also makes the red control safe against the old implementation.
        report['emergency_control_cleanup_needed'] = any(child.poll() is None for child in owned)
        for child in owned:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait(timeout=2)

    classes = [
        ('clean_no_match', 1, '', '', []),
        ('valid_rc0', 0, ' 123 777 4\n 124 777 0\n', '', [{'pid': 123, 'rss_bytes': 4096}, {'pid': 124, 'rss_bytes': 0}]),
        ('diagnostic_rc1', 1, '', observed['diagnostic_error']['stderr'], None),
        ('diagnostic_rc0', 0, '123 777 4\n', 'ps: diagnostic\n', None),
        ('rc1_with_records', 1, '123 777 4\n', '', None),
        ('rc0_empty', 0, '', '', None),
        ('malformed_rc0', 0, 'pid pgid rss\n', '', None),
        ('unowned_group', 0, '123 778 4\n', '', None),
        ('negative_rss', 0, '123 777 -1\n', '', None),
        ('zero_pid', 0, '0 777 4\n', '', None),
        ('duplicate_pid', 0, '123 777 4\n123 777 4\n', '', None),
        ('blank_record', 0, '123 777 4\n\n', '', None),
        ('unexpected_rc', 2, '', '', None),
    ]
    report['classification_controls'] = {}
    for name, code, stdout, stderr, expected in classes:
        response = subprocess.CompletedProcess(['/bin/ps'], code, stdout, stderr)
        with patch.object(subprocess, 'run', return_value=response):
            try:
                value = guard.group_rss(777)
                row = {'accepted': True, 'result': value, 'passed': expected is not None and value == expected}
            except (RuntimeError, ValueError) as error:
                row = {'accepted': False, 'error': str(error), 'passed': expected is None}
        report['classification_controls'][name] = row
    receipt = report['guard_receipt']
    passed = (receipt['reason'] == 'cleanup_unconfirmed' and not receipt['owned_group_exit_verified']
              and signal.SIGKILL in receipt['cleanup_signals'] and receipt['returncode'] == -signal.SIGKILL
              and report['durable_guard_receipt_matches'] and not report['emergency_control_cleanup_needed']
              and report['independent_after_guard'] == {'returncode': 1, 'stdout': '', 'stderr': ''}
              and all(row['passed'] for row in report['classification_controls'].values()))
    report['passed'] = passed
    (base / 'control-receipt.json').write_text(json.dumps(report, indent=2) + '\n')
    if passed:
        (guard.HERE / 'evidence/ps-classification-controls.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'passed': passed, 'guard_reason': receipt['reason'], 'owned_group_exit_verified': receipt['owned_group_exit_verified'],
                      'guard_returncode': receipt['returncode'], 'cleanup_signals': receipt['cleanup_signals'],
                      'emergency_control_cleanup_needed': report['emergency_control_cleanup_needed'], 'private_receipt': str(base / 'control-receipt.json')}, indent=2))
    assert passed, 'ps error classification failed; owned control child was independently cleaned'


if __name__ == '__main__':
    main()
