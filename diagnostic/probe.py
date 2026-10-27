"""One authorized eight-child diagnostic. No import-time gate execution."""
import time
START_NS = time.monotonic_ns()
import os
import sys
import signal
import json
import hashlib
import re
import shutil
import subprocess
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1] / 'source'
EXP_REL = Path('experiments/73-high-poly-eyes')
PINNED_PYTHON = Path('/usr/bin/python3')
CONTRACT = HERE / 'CONTRACT.json'
CONTRACT_SHA256 = '3a411b774321e5c0a432b23f23abd5c472d4203551fec65769b930177a7d4cbc'
HARD_SECONDS = 60
WORK_SECONDS = 50
SCHEDULE = [('positive', 'normal'), ('positive', 'optimized'),
            ('earlyreject', 'normal'), ('earlyreject', 'optimized'),
            ('positive', 'optimized'), ('positive', 'normal'),
            ('earlyreject', 'optimized'), ('earlyreject', 'normal')]
RUN = HERE / 'run'
LIVE = None
PHASE = 'work'
EMERGENCY_FD = None


class ProbeAbort(Exception):
    pass


def elapsed():
    return (time.monotonic_ns() - START_NS) / 1e9


def stop_live():
    global LIVE
    if LIVE is not None:
        try:
            LIVE.kill()
        except ProcessLookupError:
            pass
        LIVE.communicate(timeout=max(.01, min(2, HARD_SECONDS - elapsed() - .25)))
        LIVE = None


def deadline_alarm(signum, frame):
    global PHASE
    if PHASE == 'work':
        PHASE = 'finalizing'
        signal.setitimer(signal.ITIMER_REAL, max(.001, HARD_SECONDS - elapsed()))
        raise ProbeAbort('50-second work cutoff; reserve cleanup/receipt inside 60 seconds')
    if LIVE is not None:
        try:
            LIVE.kill()
        except ProcessLookupError:
            pass
    if EMERGENCY_FD is not None:
        os.write(EMERGENCY_FD, b'HARD 60 SECOND DEADLINE: FAIL; cleanup/receipt may be incomplete\n')
    os._exit(124)


def work_remaining():
    value = WORK_SECONDS - elapsed()
    if value <= 0:
        raise ProbeAbort('work cutoff reached')
    return value


def metadata(path):
    if path.is_symlink() or not path.is_file():
        raise ProbeAbort('source/fixture is not a regular file: ' + str(path))
    raw = path.read_bytes()
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def inventory(root):
    result = {}
    for path in sorted(root.rglob('*')):
        work_remaining()
        if path.is_symlink():
            raise ProbeAbort('unexpected copied fixture symlink: ' + str(path))
        if path.is_file():
            result[str(path.relative_to(root))] = metadata(path)
    return result


def validate_output(returncode, output, case):
    reasons = []
    # The source method uses the singular spelling. Never require "Ran 1 tests".
    summary = re.findall(r'^Ran 1 test in [0-9]+(?:\.[0-9]+)?s$', output, re.MULTILINE)
    if len(summary) != 1 or 'Ran 1 test' not in output:
        reasons.append('missing/duplicate singular Ran 1 test summary')
    if 'skipped' in output or 'ERROR' in output:
        reasons.append('skip or ERROR marker present')
    if case == 'positive':
        if returncode != 0 or '\nOK\n' not in output or 'FAILED' in output:
            reasons.append('positive did not meet original gate success contract')
    elif (returncode != 1 or 'FAILED (failures=1)' not in output
          or 'FROZEN-INPUTS.json' not in output
          or 'FROZEN-INPUTS.json must not be empty' not in output):
        reasons.append('earlyreject did not meet expected exit-1/FAILED/empty-manifest contract')
    return reasons


def parse_events(path, row):
    events = []
    for line in path.read_text().splitlines():
        event, label, stamp, pid, detail = line.split('\t')
        events.append({'event': event, 'label': label, 'monotonic_ns': int(stamp),
                       'pid': int(pid), 'detail': detail})
    expected_order = [('observer_start', 'sitecustomize'), ('observer_ready', 'setup_ns'),
                      ('module_exec', 'test_prepare.py'), ('module_entry', 'test_prepare.py'),
                      ('module_exec', 'frozen_context.py'), ('module_entry', 'frozen_context.py'),
                      ('module_return', 'frozen_context.py'), ('module_exec', 'cpu_probe.py'),
                      ('module_entry', 'cpu_probe.py'), ('module_return', 'cpu_probe.py'),
                      ('gate_entry', 'selected_gate'), ('gate_exit', 'selected_gate'),
                      ('process_atexit', 'child'), ('observer_stats', 'callback_body_ns'),
                      ('observer_stats', 'audit_calls'), ('observer_stats', 'exec_callbacks'),
                      ('observer_stats', 'unwind_callbacks'), ('observer_stats', 'events_before_footer_end')]
    if [(x['event'], x['label']) for x in events] != expected_order:
        raise ProbeAbort('observer boundary count/order mismatch')
    if [x['monotonic_ns'] for x in events] != sorted(x['monotonic_ns'] for x in events):
        raise ProbeAbort('observer event timestamps not monotonic')
    def one(event, label=None):
        found = [x for x in events if x['event'] == event and (label is None or x['label'] == label)]
        if len(found) != 1:
            raise ProbeAbort(f'row {row["index"]}: expected one {event}/{label}, found {len(found)}')
        return found[0]
    start = one('observer_start')
    ready = one('observer_ready')
    module = one('module_exec', 'test_prepare.py')
    entry = one('gate_entry')
    leave = one('gate_exit')
    end = one('process_atexit')
    for name in ['frozen_context.py', 'cpu_probe.py']:
        a = one('module_entry', name)
        b = one('module_return', name)
        if not (module['monotonic_ns'] <= a['monotonic_ns'] <= b['monotonic_ns'] <= entry['monotonic_ns']):
            raise ProbeAbort('module boundary order mismatch: ' + name)
    if start['detail'] != ('1' if row['mode'] == 'optimized' else '0'):
        raise ProbeAbort('child observed optimization mode mismatch')
    if leave['detail'] != ('return' if row['case'] == 'positive' else 'AssertionError'):
        raise ProbeAbort('child gate exit kind mismatch')
    stamps = [row['parent_before_launch_ns'], start['monotonic_ns'], ready['monotonic_ns'],
              module['monotonic_ns'], entry['monotonic_ns'], leave['monotonic_ns'],
              end['monotonic_ns'], row['parent_after_return_ns']]
    if stamps != sorted(stamps) or {x['pid'] for x in events} != {row['pid']}:
        raise ProbeAbort('child timestamp order or pid identity mismatch')
    row['events'] = events
    row['phase_seconds'] = {
        'parent_launch_to_observer_start': (stamps[1] - stamps[0]) / 1e9,
        'observer_start_to_ready': (stamps[2] - stamps[1]) / 1e9,
        'observer_ready_to_script_exec': (stamps[3] - stamps[2]) / 1e9,
        'script_exec_to_gate_entry': (stamps[4] - stamps[3]) / 1e9,
        'selected_gate_bracket': (stamps[5] - stamps[4]) / 1e9,
        'gate_exit_to_process_atexit': (stamps[6] - stamps[5]) / 1e9,
        'atexit_to_parent_return': (stamps[7] - stamps[6]) / 1e9,
        'parent_child_total': (stamps[7] - stamps[0]) / 1e9,
    }
    row['observer_stats'] = {x['label']: int(x['detail']) for x in events if x['event'] == 'observer_stats'}
    row['observer_setup_ns'] = int(ready['detail'])


def main():
    global LIVE, PHASE, EMERGENCY_FD
    if sys.argv != [str(Path(__file__)), '--release-eight-children']:
        raise SystemExit('release only with --release-eight-children; never use to self-test')
    from admission import runtime_identity, authenticate_source
    identity = runtime_identity()
    if sys.flags.optimize:
        raise SystemExit('requires normal parent mode')
    if Path(sys.executable).resolve() != PINNED_PYTHON.resolve() or not sys.dont_write_bytecode:
        raise SystemExit('requires pinned interpreter and -B')
    if hashlib.sha256(CONTRACT.read_bytes()).hexdigest() != CONTRACT_SHA256:
        raise SystemExit('reviewed contract bytes changed')
    RUN.mkdir()  # An existing run prevents accidental repetition.
    EMERGENCY_FD = os.open(RUN / 'hard-budget.log', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    signal.signal(signal.SIGALRM, deadline_alarm)
    signal.setitimer(signal.ITIMER_REAL, max(.001, WORK_SECONDS - elapsed()))
    receipt = {'status': 'FAIL', 'claim': 'instrumented selected-child diagnostic only; not full-suite acceptance',
               'authority': 'PROVISIONAL child evidence only; root guard must verify driver exit, final timing, cleanup and owned group absence',
               'runtime_identity': identity, 'python': sys.executable, 'version': sys.version, 'source': str(SOURCE),
               'contract_sha256': CONTRACT_SHA256, 'max_children': 8,
               'start_monotonic_ns': START_NS, 'schedule': SCHEDULE, 'children': [],
               'limits': {'aggregate_seconds': 60, 'work_seconds': 50, 'per_child_seconds': 30},
               'errors': [], 'cleanup_complete': False, 'no_live_child': False}
    control = None
    fixture = None
    source_before = {}
    initial_fixture = {}
    try:
        authenticate_source(SOURCE)
        source_exp = SOURCE / EXP_REL
        original = (source_exp / 'FROZEN-INPUTS.json').read_bytes()
        inputs = json.loads(original)
        if len(inputs) != 309:
            raise ProbeAbort('expected immutable baseline309')
        extras = ['crates/nvwa-b1-adapter/src/prepared.rs', 'scripts/b1-prepared-source-inventory.json']
        helper_names = ['test_frozen_inputs.py', 'test_prepare.py', 'cpu_probe.py', 'frozen_context.py',
                        'source-context-closeout-v1.json', 'source-context-hair79-short01-v1.json',
                        'source-context-rig119-v1.json', 'FROZEN-INPUTS.json']
        names = set(inputs) | set(extras) | {str(EXP_REL / name) for name in helper_names}
        for directory in ['fixtures', 'compat-fixtures-rig119']:
            for path in (source_exp / directory).rglob('*'):
                if path.is_symlink():
                    raise ProbeAbort('source fixture symlink: ' + str(path))
                if path.is_file():
                    names.add(str(path.relative_to(SOURCE)))
        for name in sorted(names):
            work_remaining()
            source_before[name] = metadata(SOURCE / name)
        if source_before != json.loads((HERE / 'INPUT-INVENTORY.json').read_text())['files']:
            raise ProbeAbort('consumed source set differs from frozen337 allowlist')
        (RUN / 'source-before.json').write_text(json.dumps(source_before, indent=2, sort_keys=True) + '\n')
        # Invoke the exact unchanged setUpClass, with no setUp/test/gate/tearDownClass.
        # TMPDIR changes only where its existing TemporaryDirectory is created.
        temporary = RUN / 'temporary'
        temporary.mkdir()
        os.environ['TMPDIR'] = str(temporary)
        import tempfile
        if Path(tempfile.gettempdir()) != temporary:
            raise ProbeAbort('tempfile cache does not use owned runtime directory')
        spec = importlib.util.spec_from_file_location('nvwa73_probe_fixture_control', source_exp / 'test_frozen_inputs.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        control = module.FrozenInputGate
        control.setUpClass()
        fixture = control.root
        if not fixture.is_relative_to(temporary):
            raise ProbeAbort('fixture escaped owned runtime directory')
        manifest = control.exp / 'FROZEN-INPUTS.json'
        manifest.write_bytes(original)
        initial_fixture = inventory(fixture)
        selected = dict(control.all_contexts)[module.PRODUCT]
        if len(selected) != 309:
            raise ProbeAbort('expected product309 baseline from original setUpClass')
        for name, expected in selected.items():
            if initial_fixture.get(name) != expected:
                raise ProbeAbort('baseline source identity mismatch: ' + name)
        for name in extras:
            if (fixture / name).exists():
                raise ProbeAbort('setUpClass did not remove rig119 supplement: ' + name)
        for name, expected in initial_fixture.items():
            if name not in selected and expected != source_before.get(name):
                raise ProbeAbort('copied helper/fixture bytes differ from source: ' + name)
        receipt['fixture_source_count'] = len(selected)
        receipt['fixture_files'] = initial_fixture
        receipt['fixture_preparation_seconds'] = elapsed()
        for index, (case, mode) in enumerate(SCHEDULE, 1):
            work_remaining()
            manifest.write_bytes(original if case == 'positive' else b'{}')
            events_path = RUN / f'child-{index:02d}.events.tsv'
            events_path.touch(mode=0o600, exist_ok=False)
            command = [sys.executable, '-B']
            if mode == 'optimized':
                command.append('-O')
            command += [str(control.exp / 'test_prepare.py'), 'SourceContract.test_frozen_source_inputs', '-v']
            env = dict(os.environ)
            removed = [key for key in env if key.startswith('PYTHON')]
            for key in removed:
                env.pop(key)
            env.update({'PYTHONPATH': str(HERE / 'observer'), 'PYTHONDONTWRITEBYTECODE': '1',
                        'PYTHONNOUSERSITE': '1', 'NVWA73_GATE_OBSERVER': 'exp73-eight-child-v1',
                        'NVWA73_GATE_TARGET': str(control.exp / 'test_prepare.py'),
                        'NVWA73_GATE_EVENTS': str(events_path)})
            row = {'index': index, 'case': case, 'mode': mode, 'argv': command,
                   'cwd': str(fixture), 'removed_python_env_names': sorted(removed),
                   'manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest()}
            receipt['children'].append(row)
            # The timeout includes Popen startup by subtracting elapsed launch time.
            before = time.monotonic_ns()
            row['parent_before_launch_ns'] = before
            LIVE = subprocess.Popen(command, cwd=fixture, env=env, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            row['pid'] = LIVE.pid
            try:
                timeout = min(30 - (time.monotonic_ns() - before) / 1e9, work_remaining())
                if timeout <= 0:
                    raise ProbeAbort('child launch exhausted its deadline')
                stdout, stderr = LIVE.communicate(timeout=timeout)
                row['parent_after_return_ns'] = time.monotonic_ns()
                row['returncode'] = LIVE.returncode
                LIVE = None
            except BaseException:
                # Preserve partial raw output on a timeout, then fail without retry.
                if LIVE is not None:
                    try:
                        LIVE.kill()
                    except ProcessLookupError:
                        pass
                    stdout, stderr = LIVE.communicate(timeout=max(.01, min(2, HARD_SECONDS - elapsed() - .25)))
                    row['parent_after_return_ns'] = time.monotonic_ns()
                    row['returncode'] = LIVE.returncode
                    LIVE = None
                    (RUN / f'child-{index:02d}.stdout').write_bytes(stdout)
                    (RUN / f'child-{index:02d}.stderr').write_bytes(stderr)
                raise
            (RUN / f'child-{index:02d}.stdout').write_bytes(stdout)
            (RUN / f'child-{index:02d}.stderr').write_bytes(stderr)
            reasons = validate_output(row['returncode'], (stdout + stderr).decode('utf-8'), case)
            row['outcome_errors'] = reasons
            if reasons:
                raise ProbeAbort(f'row {index}: ' + '; '.join(reasons))
            parse_events(events_path, row)
            row['validated'] = True
        counts = {(case, mode): sum(x['case'] == case and x['mode'] == mode and x.get('validated', False)
                                    for x in receipt['children'])
                  for case in ('positive', 'earlyreject') for mode in ('normal', 'optimized')}
        receipt['all_eight_outcomes_validated'] = (len(receipt['children']) == 8
                                                  and set(counts.values()) == {2}
                                                  and len({x['pid'] for x in receipt['children']}) == 8)
        if not receipt['all_eight_outcomes_validated']:
            raise ProbeAbort('not exactly two validated fresh children in each of four cells')
    except BaseException as error:
        receipt['errors'].append(type(error).__name__ + ': ' + str(error))
    finally:
        PHASE = 'finalizing'
        signal.setitimer(signal.ITIMER_REAL, max(.001, HARD_SECONDS - elapsed()))
        try:
            stop_live()
            receipt['no_live_child'] = LIVE is None
            if fixture is not None and fixture.exists():
                (fixture / EXP_REL / 'FROZEN-INPUTS.json').write_bytes(original)
                # Source/copy integrity is finalization, inside the 60s aggregate.
                # inventory() has a work cutoff, so compare here without that cutoff.
                after = {}
                for path in sorted(fixture.rglob('*')):
                    if path.is_symlink():
                        raise ProbeAbort('final fixture contains symlink')
                    if path.is_file():
                        after[str(path.relative_to(fixture))] = metadata(path)
                receipt['fixture_preserved'] = after == initial_fixture
                if not receipt['fixture_preserved']:
                    receipt['errors'].append('copied source changed beyond switched/restored FROZEN-INPUTS.json')
            authenticate_source(SOURCE)
            source_after = {name: metadata(SOURCE / name) for name in source_before}
            receipt['source_preserved'] = bool(source_before) and source_after == source_before
            if not receipt['source_preserved']:
                receipt['errors'].append('observed source bytes changed')
        except BaseException as error:
            receipt['errors'].append('finalization: ' + type(error).__name__ + ': ' + str(error))
        finally:
            try:
                if control is not None:
                    control.doClassCleanups()
                    if control.tearDown_exceptions:
                        receipt['errors'].append('unittest class cleanup recorded errors')
                temporary = RUN / 'temporary'
                if temporary.exists():
                    shutil.rmtree(temporary)
                receipt['cleanup_complete'] = not temporary.exists() and LIVE is None
            except BaseException as error:
                receipt['errors'].append('cleanup: ' + type(error).__name__ + ': ' + str(error))
        receipt['elapsed_before_receipt_seconds'] = elapsed()
        receipt['actual_started_gate_children'] = sum('pid' in row for row in receipt['children'])
        receipt['actual_returned_gate_children'] = sum('parent_after_return_ns' in row for row in receipt['children'])
        if (not receipt['errors'] and receipt.get('all_eight_outcomes_validated')
                and receipt['cleanup_complete'] and receipt['no_live_child']
                and receipt.get('source_preserved') and receipt.get('fixture_preserved')):
            # This is deliberately never a PASS artifact. Final timing/fsync or
            # process shutdown can still fail after this receipt is durable.
            receipt['status'] = 'COMPLETED_CHILD_EVIDENCE_PROVISIONAL'
        with (RUN / 'RECEIPT.json').open('x') as output:
            output.write(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
            output.flush()
            os.fsync(output.fileno())
        with (RUN / 'FINAL-ELAPSED.txt').open('x') as output:
            output.write(f'{elapsed():.9f}\n')
            output.flush()
            os.fsync(output.fileno())
        os.close(EMERGENCY_FD)
        EMERGENCY_FD = None
        signal.setitimer(signal.ITIMER_REAL, 0)
    print(json.dumps({'status': receipt['status'], 'actual_gate_children': receipt['actual_started_gate_children'],
                      'elapsed_seconds': elapsed(), 'receipt': str(RUN / 'RECEIPT.json')}))
    return 0 if receipt['status'] == 'COMPLETED_CHILD_EVIDENCE_PROVISIONAL' else 1


if __name__ == '__main__':
    raise SystemExit(main())
