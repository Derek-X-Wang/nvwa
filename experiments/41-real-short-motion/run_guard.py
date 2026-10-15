#!/usr/bin/env python3
"""Owned-process CPU run guard. Default only describes; inference needs approval.

This polling watchdog is not a kernel-enforced memory allocation cap.
The low-cost control mode never loads provider/model files.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIVATE = ROOT / '.work/m2-provider'
PROFILE = '(version 1)(allow default)(deny network*)'


def group_rss(pgid):
    result = subprocess.run(['/bin/ps', '-g', str(pgid), '-o', 'pid=,pgid=,rss='],
                            capture_output=True, text=True, timeout=2)
    # BSD ps uses rc1 for both a clean no-match and errors. A diagnostic at
    # any exit status is uncertainty, never evidence that the group is absent.
    if result.stderr:
        raise RuntimeError(f'owned process-group RSS diagnostic: {result.stderr.rstrip()}')
    if result.returncode == 1:
        if result.stdout != '':
            raise RuntimeError('RSS query returned records with no-match status')
        return []
    if result.returncode != 0:
        raise RuntimeError('owned process-group RSS query failed')
    if not result.stdout:
        raise RuntimeError('RSS query returned empty successful output')
    members = []
    seen = set()
    for line in result.stdout.splitlines():
        match = re.fullmatch(r'\s*([0-9]+)\s+([0-9]+)\s+([0-9]+)\s*', line)
        if match is None:
            raise RuntimeError('RSS query returned a malformed record')
        pid, group, kib = map(int, match.groups())
        if pid <= 0 or group <= 0 or group != pgid or pid in seen:
            raise RuntimeError('RSS query returned an invalid, duplicate, or unowned record')
        seen.add(pid)
        members.append({'pid': pid, 'rss_bytes': kib * 1024})
    return members


def signal_group(pgid, sig):
    try:
        os.killpg(pgid, sig)
    except ProcessLookupError:
        pass


def teardown(child, receipt, inspect=None):
    """Bounded owned-group cleanup; failed inspection is never group absence.

    TERM/KILL use the session/group created by this guard, even after its leader
    exits. Cancellation is recorded and deferred until the receipt is written.
    """
    inspect = group_rss if inspect is None else inspect
    receipt['cleanup_errors'] = []
    receipt['cleanup_signals'] = []
    receipt['owned_group_exit_verified'] = False

    def attempt(label, action):
        try:
            return True, action()
        except BaseException as error:
            receipt['cleanup_errors'].append({'stage': label, 'type': type(error).__name__, 'error': str(error)})
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                receipt['reason'] = 'cancelled'
            return False, None

    def send(sig):
        receipt['cleanup_signals'].append(int(sig))
        return attempt('signal_' + sig.name, lambda: signal_group(child.pid, sig))

    # A dead leader does not imply that its descendants exited. Always TERM
    # the owned group, then escalate if inspection is unavailable or nonempty.
    send(signal.SIGTERM)
    attempt('leader_term_wait', lambda: child.wait(timeout=.3))
    observed, remaining = attempt('inspect_after_term', lambda: inspect(child.pid))
    if not observed or remaining:
        if observed:
            receipt['remaining_members_after_term'] = remaining
        send(signal.SIGKILL)
    attempt('leader_kill_wait', lambda: child.wait(timeout=1))
    # Retry only within a finite deadline. This also lets reaped descendants
    # disappear from ps; inspection errors are preserved individually.
    deadline = time.monotonic() + .5
    while True:
        observed, remaining = attempt('inspect_final', lambda: inspect(child.pid))
        if observed and not remaining:
            receipt['owned_group_exit_verified'] = True
            break
        if not observed or time.monotonic() >= deadline:
            receipt['cleanup_uncertainty'] = 'owned group absence could not be verified'
            break
        attempt('cleanup_poll_delay', lambda: time.sleep(.05))
    if not receipt['owned_group_exit_verified']:
        # Last KILL is independent of inspection/wait success. Do not claim that
        # sending a signal proves exit, and do not wait forever on a stuck task.
        send(signal.SIGKILL)
        if receipt['reason'] != 'cancelled':
            receipt['reason'] = 'cleanup_unconfirmed'
    receipt['returncode'] = child.returncode


def guarded(argv, output, *, seconds=600, rss_stop=7 * 2**30):
    output.mkdir(parents=True, exist_ok=False)
    # No inherited account tokens, proxies, or provider credentials.
    env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'C'}
    env.update(KIMODO_BACKEND='cpu', KIMODO_THREADS='4', KIMODO_TEXT_LAYER_CHUNK='1',
               KIMODO_TEXT_RESIDENT_LIMIT_MIB='1024', KIMODO_PROFILE='1',
               HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', OMP_NUM_THREADS='4',
               VECLIB_MAXIMUM_THREADS='4')
    receipt = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'argv': argv, 'wall_stop_seconds': seconds, 'rss_stop_bytes': rss_stop,
               'rss_note': 'sampled process-group sum, 100ms polling; not an allocation hard cap',
               'samples': [], 'reason': 'starting', 'deferred_cancel_signals': []}
    started = time.monotonic()
    child = None
    previous_signals = {}

    def cancel(signum, _frame):
        raise KeyboardInterrupt(f'cancel signal {signum}')

    def defer_cancel(signum, _frame):
        receipt['reason'] = 'cancelled'
        # Keep receipt keys stable even if a signal arrives during JSON encoding.
        if len(receipt['deferred_cancel_signals']) < 16:
            receipt['deferred_cancel_signals'].append(signum)

    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            previous_signals[sig] = signal.signal(sig, cancel)
        with (output / 'stdout.txt').open('w') as stdout, (output / 'stderr.txt').open('w') as stderr:
            child = subprocess.Popen(['/usr/bin/sandbox-exec', '-p', PROFILE, *argv], env=env,
                                     stdout=stdout, stderr=stderr, cwd=ROOT, start_new_session=True)
            receipt.update(pid=child.pid, pgid=child.pid, reason='exited')
            while child.poll() is None:
                members = group_rss(child.pid)
                rss = sum(member['rss_bytes'] for member in members)
                elapsed = time.monotonic() - started
                receipt['samples'].append({'seconds': elapsed, 'rss_bytes': rss, 'members': members})
                if rss >= rss_stop:
                    receipt['reason'] = 'resource_limit'
                    break
                if elapsed >= seconds:
                    receipt['reason'] = 'time_limit'
                    break
                time.sleep(0.1)
    except BaseException as error:
        receipt['reason'] = 'cancelled' if isinstance(error, (KeyboardInterrupt, SystemExit)) else 'guard_error'
        receipt['error'] = str(error)
    finally:
        # Defer real cancellation across every teardown and persistence step.
        # Non-signal BaseExceptions are caught by teardown's bounded attempts.
        try:
            for sig in previous_signals:
                signal.signal(sig, defer_cancel)
            if child is not None:
                teardown(child, receipt)
        except BaseException as error:
            receipt.setdefault('cleanup_errors', []).append({'stage': 'teardown', 'type': type(error).__name__, 'error': str(error)})
            receipt['reason'] = 'cancelled' if isinstance(error, (KeyboardInterrupt, SystemExit)) else 'cleanup_unconfirmed'
            receipt['owned_group_exit_verified'] = False
            # Last-resort escalation remains independent of failed inspection.
            if child is not None:
                try:
                    signal_group(child.pid, signal.SIGKILL)
                    child.wait(timeout=1)
                except BaseException as last_error:
                    receipt['cleanup_errors'].append({'stage': 'last_resort', 'type': type(last_error).__name__, 'error': str(last_error)})
        finally:
            receipt['elapsed_seconds'] = time.monotonic() - started
            receipt['max_sampled_group_rss_bytes'] = max((s['rss_bytes'] for s in receipt['samples']), default=0)
            try:
                (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
            except BaseException as error:
                receipt['receipt_write_error'] = f'{type(error).__name__}: {error}'
                print(json.dumps(receipt), file=sys.stderr)
            finally:
                for sig, handler in previous_signals.items():
                    signal.signal(sig, handler)
    return receipt


def controls(receipt_name='guard-controls.json'):
    base = PRIVATE / ('guard-controls-' + uuid.uuid4().hex[:8])
    base.mkdir(parents=True)
    rows = {}
    for name, command, seconds, memory in [
        ('network', [sys.executable, '-B', '-c', 'import socket,errno; s=socket.socket(); rc=s.connect_ex(("127.0.0.1",9)); print(rc); assert rc==errno.EPERM'], 2, 2**30),
        ('timeout', [sys.executable, '-B', '-c', 'import time; time.sleep(60)'], .15, 2**30),
        ('memory', [sys.executable, '-B', '-c', 'import time; data=bytearray(32*1024*1024); time.sleep(60)'], 2, 24 * 2**20),
        ('group', [sys.executable, '-B', '-c', 'import subprocess,sys,signal,time; p=subprocess.Popen([sys.executable,"-B","-c","import time; time.sleep(60)"]); signal.signal(signal.SIGTERM, lambda *args: (p.wait(),sys.exit(0))); time.sleep(60)'], .25, 2**30),
        ('force_kill', [sys.executable, '-B', '-c', 'import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)'], .15, 2**30),
    ]:
        rows[name] = guarded(command, base / name, seconds=seconds, rss_stop=memory)
    assert rows['network']['returncode'] == 0
    assert rows['timeout']['reason'] == 'time_limit'
    assert rows['memory']['reason'] == 'resource_limit'
    assert max(len(s['members']) for s in rows['group']['samples']) >= 2
    assert rows['force_kill']['returncode'] == -signal.SIGKILL
    assert all(r.get('owned_group_exit_verified') for r in rows.values())
    (HERE / 'evidence' / receipt_name).write_text(json.dumps(rows, indent=2) + '\n')
    print(json.dumps({name: {k: value[k] for k in ['reason', 'returncode', 'elapsed_seconds', 'max_sampled_group_rss_bytes', 'owned_group_exit_verified']} for name, value in rows.items()}, indent=2))


def run(approval):
    if not approval.strip():
        raise SystemExit('An explicit authorization receipt identifier is required')
    from float_prerequisite import verify_float_prerequisite
    float_receipt = verify_float_prerequisite()
    proposal = json.loads((HERE / 'proposal.json').read_text())
    models = PRIVATE / 'approved-models'
    for artifact in proposal['artifacts']:
        file = models / Path(artifact['path']).name
        if not file.is_file() or file.is_symlink() or file.stat().st_size != artifact['bytes']:
            raise SystemExit(f'Exact authorized local artifact unavailable: {file}')
        with file.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != artifact['sha256']:
                raise SystemExit(f'Artifact hash mismatch: {file}')
    binary = PRIVATE / 'runtime/build-cpu/kmd-generate'
    expected = json.loads((HERE / 'evidence/help-receipt.json').read_text())['binary_sha256']
    if hashlib.sha256(binary.read_bytes()).hexdigest() != expected:
        raise SystemExit('Reviewed provider executable changed')
    libraries = json.loads((HERE / 'evidence/built-library-hashes.json').read_text())
    for library in libraries:
        path = ROOT / library['path']
        if path.is_symlink() or path.stat().st_size != library['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest() != library['sha256']:
            raise SystemExit(f'Reviewed runtime library changed: {path}')
    work = PRIVATE / ('genuine-run-' + uuid.uuid4().hex[:12])
    work.mkdir()
    prompt = work / 'prompt.txt'
    prompt.write_text(proposal['prompt'] + '\n')
    output = work / 'raw'
    command = [str(binary), str(models / 'kimodo-soma-rp-v1.1-f32.gguf'), str(models / 'Llama-3-Kimodo-Q4_K_M.gguf'),
               str(prompt), '90', '25', '42', str(output)]
    receipt = guarded(command, work / 'process')
    receipt['authorization_receipt'] = approval
    receipt['float_prerequisite'] = float_receipt
    receipt['request'] = {k: proposal[k] for k in ['code_revision', 'ggml_revision', 'artifacts', 'prompt', 'seed', 'frames', 'fps', 'diffusion_steps', 'text_cfg', 'constraint_cfg']}
    receipt['prompt_file_sha256'] = hashlib.sha256(prompt.read_bytes()).hexdigest()
    receipt['binary_sha256'] = expected
    receipt['libraries'] = libraries
    receipt['raw_provenance'] = []
    admitted = receipt['reason'] == 'exited' and receipt.get('returncode') == 0
    admitted &= (work / 'process/stdout.txt').read_text() == proposal['success_stdout']
    for spec in proposal['raw_outputs']:
        path = output / spec['name']
        if not path.is_file() or path.is_symlink() or path.stat().st_size != spec['bytes']:
            admitted = False
            continue
        raw = path.read_bytes()
        receipt['raw_provenance'].append({'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
    receipt['raw_complete'] = admitted
    receipt['normalized_motion'] = 'NOT-RUN; requires separate schema, numeric, axis, and provenance admission'
    (work / 'generation-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(work)
    if not admitted:
        raise SystemExit('Provider failed/limited/cancelled or raw output incomplete; no normalized success')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--controls', action='store_true')
    parser.add_argument('--approved-run', metavar='AUTHORIZATION_RECEIPT')
    args = parser.parse_args()
    if args.controls:
        controls()
    elif args.approved_run:
        signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(SystemExit('cancelled')))
        run(args.approved_run)
    else:
        print((HERE / 'proposal.json').read_text())
