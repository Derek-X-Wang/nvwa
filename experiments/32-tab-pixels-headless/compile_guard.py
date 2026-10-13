#!/usr/bin/env python3
"""Experiment32 sole Cargo writer: mandatory cleanup under a900-second deadline."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

REPO = Path(__file__).resolve().parents[2]
TARGET = Path('/Users/derekxwang/Development/incubator/Nvwa/nvwa/target')
LOCK_SHA = '457f603a78c6822b6dec754978c425ed6b61d4ed3acd0b856e606e180f5c4e73'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def group_absence(pgid):
    try:
        os.killpg(pgid, 0)
        return False
    except ProcessLookupError:
        return True
    except OSError:
        return None


def inspect_group(pgid):
    """Bounded kernel/ps observations; errors never mean absence."""
    absence = group_absence(pgid)
    if absence is True:
        return {'state': 'confirmed_absent'}
    if absence is None:
        return {'state': 'unknown', 'reason': 'kernel_group_query_failed'}
    try:
        row = subprocess.run(['/bin/ps', '-ww', '-g', str(pgid), '-o',
                              'pid=,ppid=,pgid=,lstart=,comm='],
                             capture_output=True, text=True, timeout=0.3)
        if row.returncode != 0 or row.stderr.strip() or not row.stdout.strip():
            return {'state': 'unknown', 'reason': 'ps_error_or_empty', 'returncode': row.returncode}
        members = []
        for line in row.stdout.splitlines():
            values = line.split(None, 8)
            if len(values) != 9 or int(values[2]) != pgid:
                return {'state': 'unknown', 'reason': 'malformed_group_identity'}
            pid = int(values[0])
            if os.getpgid(pid) != pgid or os.getsid(pid) != pgid:
                return {'state': 'unknown', 'reason': 'not_owned_new_session'}
            members.append({'pid': pid, 'ppid': int(values[1]), 'pgid': pgid,
                            'kernel_start': ' '.join(values[3:8]), 'binary': values[8]})
        return {'state': 'live', 'members': members}
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        return {'state': 'unknown', 'reason': repr(error)}


def same_member(previous, current):
    return all(previous[k] == current[k] for k in ('pid', 'pgid', 'kernel_start', 'binary'))


def cleanup(child, rows):
    """Bounded owned group TERM/KILL and direct-child waitpid proof."""
    pgid = child.pid
    registered = {}
    for signum, label in [(signal.SIGTERM, 'TERM'), (signal.SIGKILL, 'KILL')]:
        child.poll()
        observed = inspect_group(pgid)
        rows.append({'cleanupInspection': observed, 'phase': label})
        if observed['state'] == 'confirmed_absent':
            child.poll()
            return 'exit_verified' if child.returncode is not None else 'blocked_waitpid_unknown'
        if observed['state'] != 'live':
            return 'blocked_group_identity_unknown'
        members = observed['members']
        # The unreaped direct child pins the new session while alive. After it
        # exits, escalation addresses only registered stable survivor identities.
        leader = next((x for x in members if x['pid'] == child.pid), None)
        if child.returncode is None and leader and leader['ppid'] == os.getpid():
            for member in members:
                try:
                    member = {**member, 'binary_sha256': sha(member['binary'])}
                except OSError:
                    return 'blocked_member_binary_unknown'
                previous = registered.get(member['pid'])
                if previous is not None and (not same_member(previous, member)
                                            or previous['binary_sha256'] != member['binary_sha256']):
                    return 'blocked_member_identity_changed'
                registered[member['pid']] = member
        else:
            for member in members:
                previous = registered.get(member['pid'])
                if previous is None or not same_member(previous, member):
                    return 'blocked_unregistered_survivor'
        for member in members:
            if sha(member['binary']) != registered[member['pid']]['binary_sha256']:
                return 'blocked_member_binary_changed'
        try:
            os.killpg(pgid, signum)
        except ProcessLookupError:
            child.poll()
            return 'exit_verified' if group_absence(pgid) is True and child.returncode is not None else 'blocked_signal_race'
        rows.append({'signalSent': label, 'ownedGroup': pgid, 'registeredMembers': list(registered.values())})
        until = time.monotonic() + 2
        while time.monotonic() < until:
            child.poll()
            if group_absence(pgid) is True:
                return 'exit_verified' if child.returncode is not None else 'blocked_waitpid_unknown'
            time.sleep(0.05)
    child.poll()
    return 'exit_verified' if group_absence(pgid) is True and child.returncode is not None else 'blocked_group_exit_unknown'


def run_command(command, evidence, *, cwd=REPO, target=TARGET, deadline=900,
                disk_usage=shutil.disk_usage, writer=write_json, cancellation=None, emit=print):
    """Production-called seam; tests use real owned CPU children, never Cargo/GPU."""
    cancellation = cancellation if cancellation is not None else {'signal': None}
    evidence = Path(evidence)
    if sha(REPO / 'Cargo.lock') != LOCK_SHA:
        raise RuntimeError('protected root lock changed before command')
    free = disk_usage(target).free
    if free <= 32 * 1024**3:
        raise RuntimeError('initial32GiB storage floor not met')
    evidence.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, CARGO_TARGET_DIR=str(target), CARGO_BUILD_JOBS='1')
    began = time.monotonic()
    record = {'command': command, 'cwd': str(cwd), 'target': str(target), 'deadlineSeconds': deadline,
              'initial_free_bytes': free, 'root_lock_before': LOCK_SHA, 'monotonic_start_ns': time.monotonic_ns(),
              'wall_start_ns': time.time_ns(), 'storage_samples': [], 'cleanup_observations': [],
              'abort': None, 'errors': [], 'cleanup': 'no_child_spawned'}
    child, stdout, stderr = None, None, None
    try:
        stdout = (evidence / 'stdout.log').open('x')
        stderr = (evidence / 'stderr.log').open('x')
        child = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                 stdout=stdout, stderr=stderr, start_new_session=True)
        # Register before every fallible post-Popen operation.
        record.update(owned_pid=child.pid, owned_process_group=child.pid)
        writer(evidence / 'started.json', record)
        emit(json.dumps({'started': evidence.name, 'owned_pid': child.pid,
                         'initial_free_gib': round(free / 1024**3, 2)}), flush=True)
        last_update = -30
        while child.poll() is None:
            elapsed = time.monotonic() - began
            if cancellation['signal'] is not None:
                record['abort'] = 'cancel_signal_' + str(cancellation['signal'])
                break
            free = disk_usage(target).free
            record['storage_samples'].append({'elapsed_seconds': elapsed, 'free_bytes': free})
            if free < 8 * 1024**3 or elapsed > deadline:
                record['abort'] = 'storage_below8GiB' if free < 8 * 1024**3 else 'deadline15minutes'
                break
            if elapsed - last_update >= 30:
                lines = (evidence / 'stderr.log').read_text(errors='replace').splitlines()
                emit(json.dumps({'stage': evidence.name, 'elapsed_seconds': round(elapsed, 1),
                                 'free_gib': round(free / 1024**3, 2), 'latest': lines[-1] if lines else None}), flush=True)
                last_update = elapsed
            time.sleep(min(2, max(0.02, deadline / 10)))
    except BaseException as error:
        record['errors'].append(repr(error))
        if isinstance(error, KeyboardInterrupt):
            record['abort'] = 'KeyboardInterrupt'
    finally:
        # No post-spawn storage/log/receipt exception bypasses owned cleanup.
        if child is not None:
            try:
                record['cleanup'] = cleanup(child, record['cleanup_observations'])
                record['exit_code'] = child.returncode
            except BaseException as error:
                record['cleanup'] = 'blocked_cleanup_exception'
                record['errors'].append(repr(error))
        for stream in (stdout, stderr):
            if stream is not None:
                try:
                    stream.close()
                except BaseException as error:
                    record['errors'].append(repr(error))
        record['elapsed_seconds'] = time.monotonic() - began
        try:
            record['root_lock_after'] = sha(REPO / 'Cargo.lock')
            record['final_free_bytes'] = disk_usage(target).free
        except BaseException as error:
            record['errors'].append(repr(error))
        record['status'] = 'PASS' if (record['cleanup'] == 'exit_verified' and not record['abort']
                            and not record['errors'] and record.get('exit_code') == 0
                            and record.get('root_lock_after') == LOCK_SHA) else 'FAIL'
        try:
            writer(evidence / 'result.json', record)
        except BaseException as error:
            record['status'] = 'FAIL'
            record['errors'].append('final_receipt_write_failed: ' + repr(error))
            try:
                write_json(evidence / 'receipt-write-failure.json', record)
            except BaseException:
                pass
        try:
            emit(json.dumps({'finished': evidence.name, 'status': record['status'], 'cleanup': record['cleanup'],
                             'exit_code': record.get('exit_code'), 'abort': record['abort'],
                             'errors': record['errors'], 'elapsed_seconds': round(record['elapsed_seconds'], 2)}), flush=True)
        except BaseException:
            pass
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command and args.command[0] == '--' else args.command
    if not command or command[0] != 'cargo' or not args.name.replace('-', '').isalnum():
        parser.error('named Cargo command required')
    cancellation = {'signal': None}
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda received, _frame: cancellation.update(signal=received))
    record = run_command(command, REPO / '.work/m11-startup/compile' / args.name, cancellation=cancellation)
    return 0 if record['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
