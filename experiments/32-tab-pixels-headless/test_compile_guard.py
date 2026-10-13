#!/usr/bin/env python3
"""Real owned CPU children exercise the production-called compile guard seam."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import threading
import time

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('compile_guard_under_test', HERE / 'compile_guard.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
BASE = HERE.parents[1] / '.work/m11-startup/headless32/compile-controls-final'
BASE.mkdir(exist_ok=False)
results = []


def quiet(*args, **kwargs):
    pass


def run(name, command=None, **options):
    result = guard.run_command(command or ['/bin/sleep', '10'], BASE / name,
                               deadline=0.3, emit=quiet, **options)
    pid = result.get('owned_pid')
    absent = guard.group_absence(pid) if pid else None
    return result, absent


def record(name, result, absent, status, extra=None):
    assert result['status'] == status, (name, result)
    assert result['cleanup'] == 'exit_verified', (name, result)
    assert absent is True, (name, result, absent)
    results.append({'case': name, 'expectedStatus': status, 'result': result,
                    'ownedGroupConfirmedAbsentESRCH': absent, **(extra or {})})


result, absent = run('normal', ['/bin/sleep', '0.05'])
record('normal', result, absent, 'PASS')

calls = 0

def storage_failure(path):
    global calls
    calls += 1
    if calls == 2:
        raise OSError('injected post-Popen storage inspection failure matching root red')
    return shutil.disk_usage(path)


result, absent = run('storage-io-failure', disk_usage=storage_failure)
assert any('post-Popen storage inspection failure' in x for x in result['errors'])
record('storage-io-failure', result, absent, 'FAIL')


def started_failure(path, data):
    if path.name == 'started.json':
        path.mkdir()
    guard.write_json(path, data)


result, absent = run('started-receipt-real-io-failure', writer=started_failure)
assert any('IsADirectoryError' in x for x in result['errors'])
record('started-receipt-real-io-failure', result, absent, 'FAIL')


def log_failure(path, data):
    guard.write_json(path, data)
    if path.name == 'started.json':
        log = path.parent / 'stderr.log'
        log.unlink()
        log.mkdir()


result, absent = run('log-read-real-io-failure', writer=log_failure)
assert any('IsADirectoryError' in x for x in result['errors'])
record('log-read-real-io-failure', result, absent, 'FAIL')


def final_failure(path, data):
    if path.name == 'result.json':
        path.mkdir()
    guard.write_json(path, data)


result, absent = run('final-receipt-real-io-failure', ['/bin/sleep', '0.05'], writer=final_failure)
assert any('final_receipt_write_failed' in x for x in result['errors'])
assert (BASE / 'final-receipt-real-io-failure/receipt-write-failure.json').is_file()
record('final-receipt-real-io-failure', result, absent, 'FAIL')

result, absent = run('deadline')
assert result['abort'] == 'deadline15minutes'
record('deadline', result, absent, 'FAIL')

result, absent = run('ignore-term-kill', [sys.executable, '-c',
    'import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(30)'])
assert any(x.get('signalSent') == 'KILL' for x in result['cleanup_observations'])
record('ignore-term-kill', result, absent, 'FAIL')


def interrupted(path, data):
    if path.name == 'started.json':
        raise KeyboardInterrupt('post-Popen cancellation control')
    guard.write_json(path, data)


result, absent = run('keyboardinterrupt', writer=interrupted)
assert result['abort'] == 'KeyboardInterrupt'
record('keyboardinterrupt', result, absent, 'FAIL')

cancellation = {'signal': None}
old_handler = signal.getsignal(signal.SIGTERM)
signal.signal(signal.SIGTERM, lambda received, _frame: cancellation.update(signal=received))
timer = threading.Timer(0.1, lambda: os.kill(os.getpid(), signal.SIGTERM))
timer.start()
try:
    result, absent = run('actual-sigterm-cancel', cancellation=cancellation)
finally:
    timer.join(timeout=1)
    signal.signal(signal.SIGTERM, old_handler)
assert result['abort'] == 'cancel_signal_15'
record('actual-sigterm-cancel', result, absent, 'FAIL')

# Unknown remains blocked/no signal/no false exit. Restore live inspection and
# independently clean the same test-owned child; never hide the original result.
original_inspect = guard.inspect_group
guard.inspect_group = lambda _pg: {'state': 'unknown', 'reason': 'injected bounded inspection error'}
result, absent = run('unknown-no-false-success')
guard.inspect_group = original_inspect
assert result['status'] == 'FAIL' and result['cleanup'] == 'blocked_group_identity_unknown' and absent is False
assert not any('signalSent' in x for x in result['cleanup_observations'])
class OwnedTestChild:
    pid = result['owned_pid']
    returncode = None
    def poll(self):
        found, status = os.waitpid(self.pid, os.WNOHANG)
        if found:
            self.returncode = os.waitstatus_to_exitcode(status)
        return self.returncode
child = OwnedTestChild()
cleanup_rows = []
cleanup = guard.cleanup(child, cleanup_rows)
assert cleanup == 'exit_verified' and guard.group_absence(child.pid) is True
results.append({'case': 'unknown-no-false-success', 'expectedStatus': 'FAIL', 'result': result,
                'noSignalWithoutProof': True, 'separateControlCleanup': cleanup_rows,
                'ownedGroupConfirmedAbsentESRCH': True})

receipt = {'status': 'PASS', 'controls': results, 'count': len(results),
           'guardSha256': guard.sha(HERE / 'compile_guard.py'), 'testSha256': guard.sha(Path(__file__)),
           'cargoOrRendererStarted': False, 'remainingOwnedProcesses': []}
(HERE / 'COMPILE-GUARD-CONTROLS.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'status': 'PASS', 'count': len(results), 'guardSha256': receipt['guardSha256']}))
