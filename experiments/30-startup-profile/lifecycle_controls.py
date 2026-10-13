#!/usr/bin/env python3
"""Real owned headless process controls; no renderer/native-window evidence."""
import importlib.util
import json
from pathlib import Path
import select
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('production_guard', HERE / 'sample_owned_pid.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def main():
    output = ROOT / '.work/m11-startup/lifecycle-controls-final-v4'
    output.mkdir(parents=True, exist_ok=False)
    reports = []
    original_inspect = guard.inspect
    original_start_profilers = guard.start_profilers
    for name, case, mode in [
        ('ordinary-real-exit', 'pixels', 'exit'),
        ('native-no-marker', 'native-1', 'term'),
        ('pixel-pre-schedule-stall', 'pixels', 'term'),
        ('native-no-marker-ignore-term', 'native-2', 'kill'),
        ('partial-marker-guard-continues', 'native-1', 'partial'),
        ('wrong-kernel-identity-no-signal', 'pixels', 'identity'),
        ('inspection-failure-no-false-exit', 'pixels', 'ps-failure'),
        ('inspection-timeout-no-false-exit', 'pixels', 'ps-timeout'),
        ('partial-profiler-inspection-fault', 'native-2', 'profiler-fault'),
    ]:
        evidence = output / name
        evidence.mkdir()
        code = 'import signal,time; '
        if mode == 'kill': code += 'signal.signal(signal.SIGTERM,signal.SIG_IGN); '
        code += 'print("READY",flush=True); time.sleep(' + ('.15' if mode == 'exit' else '5') + ')'
        dummy = subprocess.Popen([sys.executable, '-c', code], stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if not select.select([dummy.stdout], [], [], 1)[0] or dummy.stdout.readline().strip() != 'READY':
            raise RuntimeError('owned dummy handshake failed')
        observation = original_inspect(dummy.pid)
        assert observation['state'] == 'live', observation
        identity = observation['identity']
        frozen = {**identity, 'binary': identity['comm'], 'binary_sha256': guard.sha(identity['comm']),
            'monotonic_ns': time.monotonic_ns(), 'case': case}
        actual = dict(frozen)
        if mode == 'identity': frozen['kernel_start_identity'] += ' deliberate-wrong-birth'
        (evidence / 'launcher.json').write_text(json.dumps(frozen))
        (evidence / 'stderr.log').write_text('NVWA_STARTUP_PROBE {"boundary":' if mode == 'partial' else '')
        if mode == 'profiler-fault':
            (evidence / 'stderr.log').write_text('NVWA_STARTUP_PROBE ' + json.dumps({'pid':dummy.pid,'boundary':'before_build_app'}) + '\n')
        reaper = threading.Thread(target=dummy.wait, daemon=True)
        reaper.start()
        def failure_runner(_command, **options):
            return subprocess.run(['/usr/bin/false'], **options)
        def timeout_runner(_command, **options):
            options['timeout'] = 0.05
            return subprocess.run([sys.executable, '-c', 'import time;time.sleep(.5)'], **options)
        if mode == 'ps-failure': guard.inspect = lambda pid: original_inspect(pid, runner=failure_runner)
        if mode == 'ps-timeout': guard.inspect = lambda pid: original_inspect(pid, runner=timeout_runner)
        if mode == 'profiler-fault':
            def injected_profiler_start(evidence, frozen, children, rows):
                def child_inspection_failure(pid):
                    if pid != dummy.pid: raise RuntimeError('deliberate inspection fault after owned child registration')
                    return original_inspect(pid)
                guard.inspect = child_inspection_failure
                try:
                    original_start_profilers(evidence, frozen, children, rows,
                        commands=[('headless-owned-control', ['/bin/sleep','5'])])
                finally:
                    guard.inspect = original_inspect
            guard.start_profilers = injected_profiler_start
        try:
            returned = guard.run_guard(SimpleNamespace(evidence=evidence, deadline=.35, grace=.2))
        finally:
            guard.inspect = original_inspect
            guard.start_profilers = original_start_profilers
        result = json.loads((evidence / 'process-observations.json').read_text())
        negative = mode in ('identity', 'ps-failure', 'ps-timeout')
        boundaries = [row['boundary'] for row in result['observations']]
        cleanup = []
        if negative:
            assert returned == 1 and result['status'] == 'blocked', result
            assert not any('sent_after' in row or 'target_exit_verified' in row for row in boundaries), boundaries
            assert original_inspect(dummy.pid)['state'] == 'live', 'unknown/identity case must remain unsignaled'
            assert guard.stop_exact(actual, cleanup, grace=.2, reap=dummy.poll) == 'exit_verified'
        else:
            assert returned == 0 and result['status'] == 'exit_verified', result
            if mode == 'kill': assert any(row.startswith('SIGKILL_sent') for row in boundaries)
            if mode in ('term', 'partial'): assert any(row.startswith('SIGTERM_sent') for row in boundaries)
            if mode == 'profiler-fault':
                assert 'optional_profiler_error_guard_continues' in boundaries
                assert result['owned_profiler_cleanup_verified']
                assert any(row['boundary']=='profiler_exit_observation' and row['exit_code'] is not None for row in result['observations'])
        reaper.join(timeout=1)
        assert not reaper.is_alive()
        assert original_inspect(dummy.pid)['state'] == 'confirmed_absent'
        report = {'case': name, 'pass': True, 'real_owned_dummy_pid': dummy.pid,
            'dummy_exit_code': dummy.returncode, 'guard_returncode': returned,
            'marker_seen': result['marker_seen'], 'guard_status': result['status'],
            'cleanup_receipts': cleanup, 'dummy_and_reaper_exit_verified': True,
            'no_renderer_or_window': True}
        (evidence / 'control-result.json').write_text(json.dumps(report, indent=2) + '\n')
        reports.append(report)
    result = {'source_sha256': guard.sha(HERE / 'sample_owned_pid.py'), 'python': sys.executable,
        'all_pass': all(row['pass'] for row in reports), 'controls': reports,
        'renderer': 'NOT-RUN', 'remaining_owned_dummy_processes': []}
    (HERE / 'LIFECYCLE-CONTROLS.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'all_pass': result['all_pass'], 'controls': len(reports), 'source_sha256': result['source_sha256'], 'renderer':'NOT-RUN'}))


if __name__ == '__main__':
    main()
