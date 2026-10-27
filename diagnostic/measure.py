"""One monotonic guard owner; catchable interruption never kills cleanup owner.
The unchanged guard alone retains and cleans the detached driver process group.
"""
import time
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
HERE=Path(__file__).resolve().parent
GUARD=None
LAUNCHING=False
PENDING_SIGNALS=set()
LAUNCH_SIGNALS=set()


def interrupted(signum,frame):
    # Do not raise during Popen acquisition or wait. The same terminal signal
    # may already have reached the guard. Relaying it could interrupt its TERM
    # grace/cleanup twice. Defer interruption until the existing guard deadline;
    # retain its only cleanup authority and classify this release as failed.
    PENDING_SIGNALS.add(signum)
    if LAUNCHING:
        LAUNCH_SIGNALS.add(signum)


def main():
    global GUARD,LAUNCHING
    if sys.argv != [str(Path(__file__)), '--release-one-guard']:
        raise SystemExit('one absolute-path guard release only')
    output=HERE/'EXTERNAL.json'
    if output.exists(): raise SystemExit('existing external receipt; no retry')
    env=dict(os.environ);env.pop('PYTHONPATH',None);env.pop('PYTHONOPTIMIZE',None)
    env['PYTHONDONTWRITEBYTECODE']='1'
    command=['/usr/bin/python3','-B',str(HERE/'guard.py'),'--release-one-driver']
    signal.signal(signal.SIGINT,interrupted)
    signal.signal(signal.SIGTERM,interrupted)
    epoch_start=time.time_ns()
    before=time.monotonic_ns()
    error=None
    try:
        # Single explicit handle acquisition; no context manager/run() exception
        # cleanup can SIGKILL the sole driver-group owner. Catchable signals are
        # recorded without raising, including this launch-to-handle window.
        LAUNCHING=True
        try:
            GUARD=subprocess.Popen(command,env=env,cwd=HERE)
        finally:
            LAUNCHING=False
        GUARD.wait(timeout=max(.001,60-(time.monotonic_ns()-before)/1e9))
    except Exception as failure:
        error={'type':type(failure).__name__,'message':str(failure)}
        # Never hard-kill/terminate the guard. Its existing57/59.5s policy still
        # owns the driver PGID. If the OS prevents exit by60s, preserve unknown
        # cleanup/exit as failure without extending the observation envelope.
    exit_code=GUARD.poll() if GUARD is not None else None
    known_exit=GUARD is not None and exit_code is not None
    after=time.monotonic_ns()
    completed=(known_exit and exit_code==0 and not error and not PENDING_SIGNALS
               and 0<=after-before<=60000000000)
    record={'status':'COMPLETE_EXTERNAL_EVIDENCE_PROVISIONAL' if completed else 'FAIL_OR_INCOMPLETE',
            'start_monotonic_ns':before,'finish_monotonic_ns':after if known_exit else None,
            'observed_until_monotonic_ns':after,'external_wall_seconds':(after-before)/1e9 if known_exit else None,
            'guard_pid':GUARD.pid if GUARD is not None else None,'guard_exit_code':exit_code,
            'guard_exit_observed':known_exit,'cleanup_authority':'guard retains sole driver PGID; consult guard receipt',
            'signals_observed':sorted(PENDING_SIGNALS),'signals_during_launch':sorted(LAUNCH_SIGNALS),
            'interruption_policy':'defer catchable interruption through existing guard bounds; never relay duplicate signal or kill guard',
            'error':error,'start_epoch_ns':epoch_start,'finish_epoch_ns':time.time_ns(),
            'authority':'Provisional monotonic guard creation-through-reaped-exit; interruption or unknown exit is failure'}
    with output.open('x') as f:
        json.dump(record,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
    # A signal during record/fsync also prevents success. Missing/failed writes
    # likewise cannot produce a successful owner exit.
    return 0 if completed and not PENDING_SIGNALS else 1

if __name__=='__main__': raise SystemExit(main())
