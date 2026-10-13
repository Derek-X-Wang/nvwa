#!/usr/bin/env python3
"""Mandatory bounded guard; optional profiling cannot abandon that guard."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import threading
import time


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def receipt(boundary, **fields):
    return {'boundary': boundary, 'clock': 'host_time_monotonic_ns',
        'monotonic_ns': time.monotonic_ns(), 'wall_time_ns': time.time_ns(), **fields}


def inspect(pid, runner=subprocess.run):
    """A bounded query with live / confirmed_absent / unknown outcomes."""
    try:
        result = runner(['/bin/ps', '-ww', '-p', str(pid), '-o',
            'pid=,ppid=,rss=,lstart=,comm='], capture_output=True, text=True, timeout=0.3)
        output = result.stdout.strip()
        if result.returncode == 0 and not result.stderr.strip() and output:
            values = output.split(None, 8)
            if len(values) != 9 or int(values[0]) != pid:
                return {'state': 'unknown', 'reason': 'malformed_ps_identity'}
            return {'state': 'live', 'identity': {'pid': int(values[0]), 'ppid': int(values[1]),
                'rss_kib': int(values[2]), 'kernel_start_identity': ' '.join(values[3:8]), 'comm': values[8]}}
        if result.returncode == 1 and not output and not result.stderr.strip():
            # ps alone never proves absence. An exact-PID kernel existence probe
            # must independently confirm ESRCH. Signal0 makes no state change.
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return {'state': 'confirmed_absent'}
            except PermissionError:
                return {'state': 'unknown', 'reason': 'kernel_existence_permission_error'}
            return {'state': 'unknown', 'reason': 'ps_empty_but_kernel_pid_exists'}
        return {'state': 'unknown', 'reason': 'ps_error_or_empty_output',
            'returncode': result.returncode, 'stderr': result.stderr}
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        return {'state': 'unknown', 'reason': type(error).__name__, 'error': repr(error)}


def same_owned(identity, frozen, verify_hash=False):
    matches = identity['pid'] == frozen['pid'] and \
        identity['kernel_start_identity'] == frozen['kernel_start_identity'] and \
        Path(identity['comm']).resolve() == Path(frozen['binary']).resolve()
    return matches and (not verify_hash or sha(frozen['binary']) == frozen['binary_sha256'])


def stop_exact(frozen, rows, grace=2.0, reap=None):
    """Unknown inspection is blocked, never exit proof or signal authority."""
    def query():
        if reap: reap()
        return inspect(frozen['pid'])
    for signum, name in [(signal.SIGTERM, 'SIGTERM'), (signal.SIGKILL, 'SIGKILL')]:
        observation = query()
        if observation['state'] == 'confirmed_absent':
            rows.append(receipt('target_exit_verified', pid=frozen['pid'], after_signal=name))
            return 'exit_verified'
        if observation['state'] != 'live':
            rows.append(receipt('cleanup_blocked_inspection_unknown', pid=frozen['pid'], inspection=observation))
            return 'blocked'
        identity = observation['identity']
        if not same_owned(identity, frozen, verify_hash=True):
            rows.append(receipt('cleanup_blocked_identity_not_proven', observed=identity))
            return 'blocked'
        try:
            os.kill(frozen['pid'], signum)
        except ProcessLookupError:
            checked = query()
            if checked['state'] == 'confirmed_absent':
                rows.append(receipt('target_exit_verified_during_signal_race', pid=frozen['pid']))
                return 'exit_verified'
            rows.append(receipt('cleanup_blocked_signal_race', inspection=checked))
            return 'blocked'
        rows.append(receipt(name + '_sent_after_exact_frozen_identity_check', **identity))
        until = time.monotonic() + grace
        while time.monotonic() < until:
            checked = query()
            if checked['state'] == 'confirmed_absent':
                rows.append(receipt('target_exit_verified_after_' + name, pid=frozen['pid']))
                return 'exit_verified'
            if checked['state'] != 'live' or not same_owned(checked['identity'], frozen):
                rows.append(receipt('cleanup_blocked_after_signal', inspection=checked))
                return 'blocked'
            time.sleep(0.05)
    rows.append(receipt('cleanup_blocked_exit_not_verified', pid=frozen['pid']))
    return 'blocked'


def marker_available(path, pid):
    """Incomplete/invalid log lines are retryable optional evidence."""
    try:
        with path.open('rb') as stream:
            stream.seek(max(0, path.stat().st_size - 1024 * 1024))
            lines = stream.read().decode(errors='replace').splitlines()
        for line in lines:
            if line.startswith('NVWA_STARTUP_PROBE '):
                try:
                    marker = json.loads(line.removeprefix('NVWA_STARTUP_PROBE '))
                except (json.JSONDecodeError, TypeError):
                    continue
                if marker.get('pid') == pid and marker.get('boundary') == 'before_build_app':
                    return True
    except OSError:
        pass
    return False


def start_profilers(evidence, frozen, children, rows, commands=None):
    if commands is None:
        commands = [
        ('sample', ['/usr/bin/sample', str(frozen['pid']), '4', '1', '-file', str(evidence / 'sample.txt')]),
        ('vmmap', ['/usr/bin/vmmap', '-summary', str(frozen['pid'])]),
        ]
    for name, command in commands:
        log = None
        spawned = False
        try:
            binary_hash = sha(command[0])
            log = (evidence / (name + '-command.log')).open('x')
            child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
            # Register ownership immediately. Any later inspection failure still
            # reaches the mandatory finally cleanup for this direct child.
            record = {'name': name, 'child': child, 'log': log, 'binary': command[0], 'sha256': binary_hash, 'frozen': None}
            children.append(record)
            spawned = True
            observation = inspect(child.pid)
            if observation['state'] == 'live':
                identity = observation['identity']
                if identity['ppid'] == os.getpid() and Path(identity['comm']).resolve() == Path(command[0]).resolve():
                    record['frozen'] = {**identity, 'binary': command[0], 'binary_sha256': binary_hash}
            rows.append(receipt('profiler_started', profiler=name, profiler_pid=child.pid, command=command, identity_observation=observation))
        except Exception as error:
            rows.append(receipt('optional_profiler_error_guard_continues', profiler=name, error=repr(error)))
            if log is not None and not spawned: log.close()


def cleanup_profiler(record, rows):
    child = record['child']
    try:
        if child.poll() is None:
            if record['frozen'] is None:
                observed = inspect(child.pid)
                if observed['state'] == 'live':
                    identity = observed['identity']
                    if identity['ppid'] == os.getpid() and Path(identity['comm']).resolve() == Path(record['binary']).resolve():
                        record['frozen'] = {**identity, 'binary': record['binary'], 'binary_sha256': record['sha256']}
            if record['frozen'] is None:
                record['cleanup'] = 'blocked'
                rows.append(receipt('profiler_cleanup_blocked_identity_unknown', profiler_pid=child.pid))
            else:
                record['cleanup'] = stop_exact(record['frozen'], rows, reap=child.poll)
        else:
            record['cleanup'] = 'exit_verified'
        child.poll()
        if child.returncode is not None:
            # A direct child's waitpid result is independent kernel exit proof.
            # ps can briefly see a zombie between an earlier poll and signal.
            # Never relabel that ps observation as absence; retain both receipts.
            record['cleanup'] = 'exit_verified'
            rows.append(receipt('owned_profiler_waitpid_exit_verified', profiler_pid=child.pid, exit_code=child.returncode))
        rows.append(receipt('profiler_exit_observation', profiler=record['name'], profiler_pid=child.pid, exit_code=child.returncode))
    except Exception as error:
        record['cleanup'] = 'blocked'
        rows.append(receipt('profiler_cleanup_blocked_exception', profiler_pid=child.pid, error=repr(error)))
    finally:
        record['log'].close()


def run_guard(args):
    frozen = json.loads((args.evidence / 'launcher.json').read_text())
    if frozen['pid'] <= 1 or not Path(frozen['binary']).is_absolute() or sha(frozen['binary']) != frozen['binary_sha256']:
        raise ValueError('invalid exact launcher freeze receipt')
    rows = [receipt('mandatory_external_guard_started', pid=frozen['pid'], case=frozen['case'], deadline_seconds=args.deadline)]
    children = []
    status = 'blocked'
    unknown_seen = False
    marker_seen = False
    profiling_attempted = False
    cleanup_attempted = False
    deadline_ns = frozen['monotonic_ns'] + int(args.deadline * 1e9)
    try:
        while time.monotonic_ns() < deadline_ns:
            observation = inspect(frozen['pid'])
            if observation['state'] == 'confirmed_absent':
                rows.append(receipt('target_exit_verified', pid=frozen['pid'], exit_code='NOT-OBSERVABLE by child watchdog'))
                status = 'exit_verified'
                break
            if observation['state'] == 'unknown':
                if not unknown_seen: rows.append(receipt('inspection_unknown_guard_continues_to_deadline', inspection=observation))
                unknown_seen = True
            else:
                identity = observation['identity']
                if identity['kernel_start_identity'] != frozen['kernel_start_identity']:
                    rows.append(receipt('guard_blocked_kernel_identity_changed', observed=identity))
                    break
                if same_owned(identity, frozen):
                    if frozen['case'].startswith('native-'): rows.append(receipt('rss_sample', **identity))
                    # Entire optional section is isolated from the mandatory guard.
                    try:
                        if not marker_seen:
                            marker_seen = marker_available(args.evidence / 'stderr.log', frozen['pid'])
                            if marker_seen: rows.append(receipt('real_rust_startup_marker_verified', **identity))
                        if marker_seen and frozen['case'] == 'native-2' and not profiling_attempted:
                            profiling_attempted = True
                            start_profilers(args.evidence, frozen, children, rows)
                    except Exception as error:
                        rows.append(receipt('optional_evidence_error_guard_continues', error=repr(error)))
            time.sleep(0.1)
        else:
            rows.append(receipt('owned_run_deadline_reached', pid=frozen['pid'], marker_seen=marker_seen))
            cleanup_attempted = True
            status = stop_exact(frozen, rows, args.grace)
    except Exception as error:
        unknown_seen = True
        rows.append(receipt('mandatory_guard_exception_final_deadline_cleanup_required', error=repr(error)))
    finally:
        # Even an unexpected optional/guard failure cannot skip this identity-safe
        # deadline/cleanup path. No signal without a fresh proven identity.
        if status != 'exit_verified' and not cleanup_attempted:
            while time.monotonic_ns() < deadline_ns:
                observed = inspect(frozen['pid'])
                if observed['state'] == 'confirmed_absent':
                    status = 'exit_verified'
                    rows.append(receipt('target_exit_verified_in_final_guard', pid=frozen['pid']))
                    break
                time.sleep(0.1)
            if status != 'exit_verified':
                cleanup_attempted = True
                try:
                    status = stop_exact(frozen, rows, args.grace)
                except Exception as error:
                    rows.append(receipt('mandatory_cleanup_blocked_exception', error=repr(error)))
                    status = 'blocked'
        threads = [threading.Thread(target=cleanup_profiler, args=(record, rows), daemon=True) for record in children]
        for thread in threads: thread.start()
        child_cleanup_until = time.monotonic() + 4.75
        for thread in threads: thread.join(timeout=max(0.0, child_cleanup_until - time.monotonic()))
        child_cleanup_verified = all(not thread.is_alive() for thread in threads) and all(record.get('cleanup') == 'exit_verified' for record in children)
        overall = 'exit_verified' if status == 'exit_verified' and child_cleanup_verified and not unknown_seen else 'blocked'
        result = {'status': overall, 'target_cleanup': status, 'target_pid': frozen['pid'], 'marker_seen': marker_seen,
            'inspection_unknown_seen': unknown_seen, 'owned_profiler_cleanup_verified': child_cleanup_verified,
            'observations': rows}
        (args.evidence / 'process-observations.json').write_text(json.dumps(result, indent=2) + '\n')
        print('NVWA_EXTERNAL_GUARD ' + json.dumps({key: result[key] for key in ['status','target_cleanup','target_pid','marker_seen']}), flush=True)
    return 0 if overall == 'exit_verified' else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--deadline', type=float, default=50.0)
    parser.add_argument('--grace', type=float, default=2.0)
    args = parser.parse_args()
    if not args.evidence.is_absolute() or not 0 < args.deadline <= 50 or not 0 < args.grace <= 2:
        parser.error('absolute evidence, deadline<=50s and per-signal grace<=2s required')
    try:
        return run_guard(args)
    except Exception as error:
        # Invalid/unreadable freeze receipt cannot authorize any target signal.
        path = args.evidence / 'process-observations.json'
        if not path.exists():
            path.write_text(json.dumps({'status':'blocked','error':repr(error),
                'observations':[receipt('guard_setup_blocked_no_proven_target', error_type=type(error).__name__)]}, indent=2)+'\n')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
