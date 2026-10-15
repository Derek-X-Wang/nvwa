"""Bounded POSIX command ownership for the integration-only model-free driver."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


class OwnedCommandError(RuntimeError):
    def __init__(self, message, receipt):
        super().__init__(message)
        self.receipt = receipt


class _Cancelled(BaseException):
    pass


def _persist(path, receipt):
    Path(path).write_text(json.dumps(receipt, indent=2) + "\n")


def _group_members(pgid):
    query = subprocess.run(["ps", "-eo", "pid=,pgid=,stat="],
                           capture_output=True, text=True, timeout=1, check=True)
    return [{"pid": int(pid), "state": state}
            for line in query.stdout.splitlines()
            for pid, group, state in [line.split()]
            if int(group) == pgid]


def _cleanup(child):
    result = {"signals_attempted": [], "errors": [], "leader_reaped": False,
              "owned_group_exit_verified": False}
    for sig in (signal.SIGTERM, signal.SIGKILL):
        result["signals_attempted"].append(signal.Signals(sig).name)
        try:
            os.killpg(child.pid, sig)
        except ProcessLookupError:
            pass
        except Exception as error:
            result["errors"].append(f"signal {sig}: {error}")
        if sig == signal.SIGTERM:
            time.sleep(0.15)
    try:
        child.wait(timeout=1)
        result["leader_reaped"] = True
    except Exception as error:
        result["errors"].append(f"leader reap: {error}")
    result["leader_exit_code"] = child.returncode
    until = time.monotonic() + 1
    while True:
        try:
            members = _group_members(child.pid)
            result["remaining_members"] = members
            result["owned_live_group_absent"] = not any(
                not row["state"].startswith("Z") for row in members)
            if not members:
                result["owned_group_exit_verified"] = True
                break
        except Exception as error:
            result["errors"].append(f"group inspection: {error}")
            break
        if time.monotonic() >= until:
            break
        time.sleep(0.02)
    result["status"] = ("verified_absent" if result["owned_group_exit_verified"]
                        and result["leader_reaped"] else "cleanup_unconfirmed")
    return result


def run_owned(args, cwd, env, log_path, receipt_path, timeout):
    """Own/reap the whole child group even if wait, log, receipt or signals fail.

    Signals during spawning/teardown/persistence are deferred. After cleanup and
    attempted final receipt persistence the first pending signal is redelivered
    with its default action, preserving actual SIGINT/SIGTERM exit semantics.
    """
    args = [str(arg) for arg in args]
    receipt = {"argv": args, "pid": None, "timed_out": False,
               "pending_signals": [], "errors": []}
    interruptible = False
    child, log, error = None, None, None
    old_handlers = {}

    def cancelled(signum, _frame):
        receipt["pending_signals"].append(signum)
        if interruptible:
            raise _Cancelled()

    started = time.monotonic()
    for sig in (signal.SIGINT, signal.SIGTERM):
        old_handlers[sig] = signal.signal(sig, cancelled)
    try:
        log = Path(log_path).open("w")
        child = subprocess.Popen(args, cwd=cwd, env=env, stdout=log,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        receipt["pid"] = child.pid
        interruptible = True
        if receipt["pending_signals"]:
            raise _Cancelled()
        # A genuine persistence failure here is after spawn and must clean up.
        _persist(receipt_path, receipt)
        child.wait(timeout=timeout)
    except subprocess.TimeoutExpired as caught:
        receipt["timed_out"] = True
        error = caught
    except BaseException as caught:
        error = caught
    finally:
        interruptible = False
        if child is not None:
            try:
                receipt["cleanup"] = _cleanup(child)
            except BaseException as caught:
                # Never promote cleanup exceptions into verified absence.
                receipt["cleanup"] = {"status": "cleanup_unconfirmed",
                                      "owned_group_exit_verified": False,
                                      "error": repr(caught)}
        if log is not None:
            try:
                log.close()
            except BaseException as caught:
                receipt["errors"].append(f"log close: {caught!r}")
                error = error or caught
        receipt["exit_code"] = child.returncode if child is not None else None
        receipt["elapsed_seconds"] = time.monotonic() - started
        if error is not None:
            receipt["error"] = type(error).__name__ + ": " + str(error)
        try:
            # If cancellation arrives while a receipt is being serialized or
            # written, persist the updated queue before restoring signal action.
            # Bound retries so a signal storm cannot prevent owned cleanup exit.
            for _attempt in range(3):
                count = len(receipt["pending_signals"])
                _persist(receipt_path, receipt)
                if len(receipt["pending_signals"]) == count:
                    break
            else:
                raise RuntimeError("Signal queue changed during all final receipt writes")
        except BaseException as caught:
            receipt["errors"].append(f"receipt persistence: {caught!r}")
            error = error or caught
            # Failure remains visible even when no durable path is writable.
            print("OWNED_COMMAND_RECEIPT " + json.dumps(receipt), file=sys.stderr, flush=True)
        finally:
            for sig, handler in old_handlers.items():
                signal.signal(sig, handler)
    if receipt["pending_signals"]:
        sig = receipt["pending_signals"][0]
        signal.signal(sig, signal.SIG_DFL)
        os.kill(os.getpid(), sig)
        raise SystemExit(128 + sig)
    cleanup = receipt.get("cleanup", {})
    if error is not None or receipt["exit_code"] != 0 or cleanup.get("status") != "verified_absent":
        raise OwnedCommandError("Owned command failed or cleanup is unconfirmed", receipt)
    return receipt
