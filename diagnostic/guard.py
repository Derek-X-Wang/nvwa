"""Root's one-shot lifecycle/accounting guard. Never launches on import."""
import time
START_NS = time.monotonic_ns()
import os
import sys
import json
import signal
import hashlib
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
PINNED_PYTHON = Path('/usr/bin/python3')
FROZEN = json.loads((HERE / 'FROZEN.json').read_text())
GUARD_RUN = HERE / 'guard-run'
DRIVER = None
EMERGENCY_FD = None
LAUNCHING = False
PENDING_SIGNALS = []


class GuardAbort(Exception):
    pass


def elapsed():
    return (time.monotonic_ns() - START_NS) / 1e9


def group_exists():
    if DRIVER is None:
        return False
    try:
        os.killpg(DRIVER.pid, 0)
        return True
    except ProcessLookupError:
        return False


def kill_group(sig):
    if DRIVER is not None:
        try:
            os.killpg(DRIVER.pid, sig)
        except ProcessLookupError:
            pass


def hard_alarm(signum, frame):
    if LAUNCHING:
        PENDING_SIGNALS.append(signum)
        return
    try:
        kill_group(signal.SIGKILL)
        if EMERGENCY_FD is not None:
            os.write(EMERGENCY_FD, b'GUARD DEADLINE: FAIL/INCOMPLETE; root must verify owned group cleanup\n')
    finally:
        os._exit(124)


def interrupted(signum, frame):
    if LAUNCHING:
        PENDING_SIGNALS.append(signum)
        return
    raise GuardAbort('guard interrupted by signal ' + str(signum))


def hashes():
    return {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in FROZEN}


def main():
    global DRIVER, EMERGENCY_FD, LAUNCHING
    if sys.argv != [str(Path(__file__)), '--release-one-driver']:
        raise SystemExit('root release only with --release-one-driver; no self-test or retry')
    from admission import runtime_identity, check_setup
    identity = runtime_identity()
    setup_admission = check_setup()
    # Leave 0.5s for interpreter shutdown/root observation inside the 60s cap.
    # Root's measured invocation wall time is the final accounting authority.
    signal.signal(signal.SIGALRM, hard_alarm)
    signal.setitimer(signal.ITIMER_REAL, max(.001, 59.5 - elapsed()))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    GUARD_RUN.mkdir()  # Exclusive barrier; never reset either runtime directory.
    EMERGENCY_FD = os.open(GUARD_RUN / 'hard-budget.log', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    result = {'status': 'FAIL_OR_INCOMPLETE', 'start_monotonic_ns': START_NS,
              'acceptance': 'Root must observe guard exit 0 and complete invocation wall <=60s; this artifact alone is not PASS',
              'runtime_identity': identity, 'setup_admission': setup_admission, 'independent_measurement_limit_seconds': 60,
              'frozen_hashes': FROZEN, 'checks': {}, 'errors': []}
    result['guard_sha256_before'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    command = [str(PINNED_PYTHON), '-B', str(HERE / 'probe.py'), '--release-twenty-four-children']
    result['driver_command'] = command
    try:
        if (HERE / 'run').exists() or hashes() != FROZEN:
            raise GuardAbort('existing driver run or changed frozen artifacts; no launch')
        env = dict(os.environ)
        env.pop('PYTHONOPTIMIZE', None)
        env.pop('PYTHONPATH', None)
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        with (GUARD_RUN / 'driver.stdout').open('xb') as out, (GUARD_RUN / 'driver.stderr').open('xb') as err:
            result['before_driver_launch_ns'] = time.monotonic_ns()
            # Keep all installed signal handlers from abandoning a spawned
            # driver before its sole process handle and PGID are retained.
            LAUNCHING = True
            try:
                DRIVER = subprocess.Popen(command, env=env, cwd=HERE, stdout=out, stderr=err,
                                          start_new_session=True)
                result['owned_driver_pgid'] = DRIVER.pid
            finally:
                LAUNCHING = False
            if PENDING_SIGNALS:
                if signal.SIGALRM in PENDING_SIGNALS:
                    hard_alarm(signal.SIGALRM, None)
                interrupted(PENDING_SIGNALS[0], None)
            DRIVER.wait(timeout=max(.001, 57 - elapsed()))
            result['after_driver_return_ns'] = time.monotonic_ns()
            result['driver_exit_code'] = DRIVER.returncode
        if DRIVER.returncode != 0:
            raise GuardAbort('driver did not exit 0')
        # These fields are produced only after the driver's original raw-outcome
        # validation. The guard checks completion, not a second test validator.
        run = HERE / 'run'
        evidence = json.loads((run / 'RECEIPT.json').read_text())
        final_elapsed = float((run / 'FINAL-ELAPSED.txt').read_text())
        children = evidence['children']
        result['checks'] = {
            'driver_exited_zero': DRIVER.returncode == 0,
            'provisional_evidence_complete': evidence['status'] == 'COMPLETED_CHILD_EVIDENCE_PROVISIONAL',
            'all_twenty_four_outcomes': (evidence.get('all_twenty_four_outcomes_validated') is True
                                   and len(children) == 24
                                   and evidence.get('actual_started_gate_children') == 24
                                   and evidence.get('actual_returned_gate_children') == 24
                                   and all(row.get('validated') is True and row.get('outcome_errors') == []
                                           for row in children)),
            'all_raw_artifacts_present': all((run / f'child-{i:02d}.raw.json').is_file()
                                             for i in range(1, 25)),
            'no_observer_event_artifacts': evidence.get('no_observer_event_artifacts') is True and not list(run.rglob('*.events.tsv')),
            'source_and_copy_preserved': evidence.get('source_preserved') is True and evidence.get('fixture_preserved') is True,
            'cleanup_complete': evidence.get('cleanup_complete') is True and not (run / 'temporary').exists(),
            'driver_reported_no_live_child': evidence.get('no_live_child') is True,
            'final_timing_present_and_bounded': 0 <= evidence['elapsed_before_receipt_seconds'] <= final_elapsed < 60,
            'driver_no_errors': evidence.get('errors') == [],
            'no_emergency_markers': (run / 'hard-budget.log').read_bytes() == b'',
            'frozen_artifacts_preserved': hashes() == FROZEN,
            'guard_source_preserved': hashlib.sha256(Path(__file__).read_bytes()).hexdigest() == result['guard_sha256_before'],
            'owned_process_group_absent': not group_exists(),
        }
        result['driver_final_elapsed_seconds'] = final_elapsed
        if not all(result['checks'].values()):
            raise GuardAbort('required completion check failed')
    except BaseException as error:
        result['errors'].append(type(error).__name__ + ': ' + str(error))
    finally:
        # Any remaining group is owned by this single driver release, including
        # a gate launched before the driver's LIVE assignment was interrupted.
        try:
            if group_exists():
                result['errors'].append('owned group remained; forced cleanup required')
                kill_group(signal.SIGTERM)
                grace_end = min(time.monotonic() + 2, START_NS / 1e9 + 59)
                while group_exists() and time.monotonic() < grace_end:
                    if DRIVER is not None:
                        DRIVER.poll()
                    time.sleep(min(.02, max(.001, grace_end - time.monotonic())))
                if group_exists():
                    kill_group(signal.SIGKILL)
            if DRIVER is not None:
                DRIVER.wait(timeout=max(.001, 59.25 - elapsed()))
            result['no_live_owned_group'] = not group_exists()
            if not result['no_live_owned_group']:
                result['errors'].append('owned process group still observable after cleanup')
        except BaseException as error:
            result['errors'].append('cleanup: ' + type(error).__name__ + ': ' + str(error))
        result['observed_seconds_before_final_record'] = elapsed()
        result['measurement_remaining_before_final_record_seconds'] = 60 - elapsed()
        if not result['errors'] and all(result['checks'].values()) and result.get('no_live_owned_group') and elapsed() < 59.5:
            result['status'] = 'COMPLETE_EVIDENCE_REQUIRES_GUARD_EXIT_ZERO'
        with (GUARD_RUN / 'ROOT-RESULT.json').open('x') as output:
            output.write(json.dumps(result, indent=2, sort_keys=True) + '\n')
            output.flush()
            os.fsync(output.fileno())
        emergency_fd = EMERGENCY_FD
        EMERGENCY_FD = None
        os.close(emergency_fd)
    # Keep the deadline active through printing/interpreter shutdown. Neither
    # this record nor the driver's provisional receipt authorizes standalone PASS.
    print(json.dumps({'status': result['status'], 'guard_elapsed_seconds': elapsed(),
                      'root_result': str(GUARD_RUN / 'ROOT-RESULT.json')}))
    return 0 if result['status'] == 'COMPLETE_EVIDENCE_REQUIRES_GUARD_EXIT_ZERO' else 1


if __name__ == '__main__':
    raise SystemExit(main())
