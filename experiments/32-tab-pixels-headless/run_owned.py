#!/usr/bin/env python3
"""Future exclusive-GPU run guard. Never run until root-approved frozen inputs."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
GUARD = HERE.parent / '30-startup-profile/sample_owned_pid.py'
GUARD_SHA = '83185b1713123a203b38de42477d10b44d6a440a8cd93a14498842cabe6cafda'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    if hashlib.sha256(GUARD.read_bytes()).hexdigest() != GUARD_SHA:
        parser.error('unchanged reviewed guard source identity mismatch')
    spec = importlib.util.spec_from_file_location('unchanged_owned_guard', GUARD)
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    freeze = json.loads(args.freeze.read_text())
    if freeze.get('root_approved') is not True or freeze.get('exclusive_gpu_granted') is not True:
        parser.error('root-approved freeze and exclusive GPU lease required')
    for row in freeze['inputs']:
        if guard.sha(row['path']) != row['sha256']:
            parser.error('frozen input mismatch: ' + row['path'])
    binary = Path(freeze['binary']['path'])
    if not binary.is_absolute() or guard.sha(binary) != freeze['binary']['sha256']:
        parser.error('frozen executable identity mismatch')
    evidence = args.evidence.resolve(strict=True)
    if not evidence.is_relative_to(REPO / '.work/m11-startup/headless32') or any(evidence.iterdir()):
        parser.error('empty exact private32 evidence directory required')
    output = evidence / 'pixels'
    output.mkdir()
    rows = [guard.receipt('before_owned_popen', binary=str(binary), binary_sha256=freeze['binary']['sha256'])]
    child = None
    frozen = None
    status = 'blocked'
    error = None
    started = time.monotonic()
    with (evidence / 'stdout.log').open('x') as stdout, (evidence / 'stderr.log').open('x') as stderr:
        try:
            env = {**os.environ, 'NVWA_PIXEL_OUTPUT': str(output)}
            child = subprocess.Popen([str(binary)], cwd=REPO, env=env, stdin=subprocess.DEVNULL,
                                     stdout=stdout, stderr=stderr, start_new_session=True)
            # Direct Popen ownership is registered before inspection can fail.
            rows.append(guard.receipt('owned_popen_spawned', pid=child.pid, parent_pid=os.getpid()))
            inspection = guard.inspect(child.pid)
            rows.append(guard.receipt('initial_owned_inspection', inspection=inspection))
            if inspection['state'] == 'live':
                identity = inspection['identity']
                if identity['ppid'] == os.getpid() and Path(identity['comm']).resolve() == binary.resolve():
                    frozen = {**identity, 'binary': str(binary), 'binary_sha256': freeze['binary']['sha256']}
            # Inspection errors cannot abandon the mandatory bounded deadline.
            while child.poll() is None and time.monotonic() - started < 50:
                time.sleep(0.1)
        except Exception as exc:
            error = repr(exc)
            rows.append(guard.receipt('exception_mandatory_cleanup_follows', error=error))
        finally:
            try:
                if child is not None and child.poll() is None:
                    if frozen is None:
                        inspection = guard.inspect(child.pid)
                        rows.append(guard.receipt('cleanup_identity_reinspection', inspection=inspection))
                        if inspection['state'] == 'live':
                            identity = inspection['identity']
                            if identity['ppid'] == os.getpid() and Path(identity['comm']).resolve() == binary.resolve():
                                frozen = {**identity, 'binary': str(binary), 'binary_sha256': freeze['binary']['sha256']}
                    if frozen is None:
                        rows.append(guard.receipt('cleanup_blocked_identity_unknown', pid=child.pid))
                    else:
                        status = guard.stop_exact(frozen, rows, reap=child.poll)
                if child is not None:
                    child.poll()
                    if child.returncode is not None:
                        status = 'exit_verified'
                        rows.append(guard.receipt('owned_child_waitpid_exit_verified', pid=child.pid, exit_code=child.returncode))
            except Exception as exc:
                error = repr(exc)
                status = 'blocked'
                rows.append(guard.receipt('cleanup_blocked_exception', error=error))
            result = {'status': status, 'error': error, 'pid': child.pid if child else None,
                      'exit_code': child.returncode if child else None, 'identity': frozen,
                      'elapsedSeconds': time.monotonic() - started, 'guardDeadlineSeconds': 50,
                      'gpu_result': 'NOT-VALIDATED: independently run unchanged literal checker and inspect images',
                      'observations': rows}
            (evidence / 'process-receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    return 0 if status == 'exit_verified' and not error and child.returncode == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
