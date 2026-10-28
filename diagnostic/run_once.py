#!/usr/bin/env python3
"""External, one-shot Ubuntu acceptance. Run only after independent review."""
import ast
import collections
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
PLAN = HERE / 'plan.json'
RESULT = HERE / 'attempt'


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def source_hashes(root, plan):
    # Explicit local inputs only. Target assertions authenticate their own
    # historical/source content. This is not a claim to hash system dependencies.
    paths = {root / rel for rel in ('scripts/portable-checks.json',
             'scripts/check-portable.py', 'scripts/ci-timing.py')}
    for experiment in plan['experiments']:
        directory = root / 'experiments' / experiment
        for path in directory.rglob('*'):
            if not any(x in path.parts for x in ('target', '__pycache__', '.git', 'node_modules')) and path.is_file():
                paths.add(path)
    frozen = root / 'experiments/73-high-poly-eyes/FROZEN-INPUTS.json'
    paths.update(root / rel for rel in json.loads(frozen.read_text()))
    # Rig119 adds files beyond the original manifest. Use the source literal,
    # never import the target validator to discover them.
    tree = ast.parse((root / 'experiments/73-high-poly-eyes/frozen_context.py').read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'RIG119_SUPPLEMENTS' for t in node.targets):
            paths.update(root / rel for rel in ast.literal_eval(node.value))
    # Fixed complete input closure; original discovery logic remains above.
    paths.update(root / rel for rel in json.loads((HERE / 'SOURCE-INVENTORY.json').read_text())['files'])
    return {str(path.relative_to(root)): digest(path) for path in sorted(paths)}


def suite_evidence(stderr, experiment, plan):
    text = stderr.decode('utf-8', errors='strict')
    expected = list(plan['original_test_methods'][experiment])
    if experiment == '73-high-poly-eyes':
        expected.append(plan['new_method'])
    found = re.findall(r'^test_\S+ \(([^)]+)\)', text, re.M)
    require(collections.Counter(found) == collections.Counter(expected), 'missing/extra/duplicate unittest method IDs')
    summaries = re.findall(r'^Ran (\d+) tests? in [^\n]+\n\nOK\s*$', text, re.M)
    require(summaries == [str(len(expected))], 'missing exact successful suite tally; skips are not acceptance')
    return {'methods': len(found), 'method_ids': found}


def gate_evidence(stderr, mode, ledger):
    text = stderr.decode('utf-8', errors='strict')
    events = []
    summaries = []
    decoder = json.JSONDecoder()
    # unittest -v can print its method prefix before the first event on a line.
    for line in text.splitlines():
        for key, target in [('source_gate_event', events), ('source_gate_subprocess_observations', summaries)]:
            marker = '{"' + key + '":'
            offset = line.find(marker)
            if offset >= 0:
                record, end = decoder.raw_decode(line[offset:])
                require(not line[offset + end:].strip(), 'trailing text on evidence JSON')
                item = record[key]
                if key == 'source_gate_event' and item.get('phase') in ('parser', 'cleanup'):
                    item = dict(item, id=f"{item.get('mode')}/{item.get('method')}/{item.get('id')}")
                target.append(item)
    calls = [row for row in ledger['calls'] if row['mode'] == mode]
    wanted = []
    for row in calls:
        wanted.extend([(row['id'], 'attempt'), (row['id'], 'timeout' if row['outcome'] == 'expected_timeout' else 'return')])
        if row['local_id'] == 'SETUP':
            wanted.extend([(f"{mode}/{row['method']}/P{number:03d}", 'parser') for number in range(1, 129)])
        if row['local_id'] == 'T01':
            wanted.append((row['id'], 'cleanup'))
    require([(e.get('id'), e.get('phase')) for e in events] == wanted, 'source-gate event IDs/phases/order differ from frozen complete ledger')
    by_id = {row['id']: row for row in calls}
    returncodes = collections.Counter()
    for event in events:
        require(event.get('mode') == mode, 'wrong telemetry mode')
        phase = event['phase']
        if phase == 'parser':
            require(event.get('result') == 'pass', 'missing passed parser control')
            continue
        if phase == 'cleanup':
            require(event.get('result') == 'absent' and type(event.get('pid')) is int and event['pid'] > 0, 'T01 absence evidence missing')
            continue
        row = by_id[event['id']]
        for key in ('method', 'ordinal_in_mode', 'adapter', 'expected_context', 'written_fixture_base_context', 'consumer_expected_context_argument'):
            require(event.get(key) == row[key], 'source-gate metadata mismatch: ' + key)
        require(event.get('requested_outcome') == row['outcome'], 'source-gate requested outcome mismatch')
        if phase == 'attempt':
            require(event.get('timeout') == 30, 'source-gate original timeout changed/missing')
            cwd = event.get('cwd')
            argv = event.get('argv')
            require(isinstance(cwd, str) and isinstance(argv, list) and argv, 'launch argv/cwd missing')
            planned = [str(Path(cwd) / value[len('<scratch>/'):]) if value.startswith('<scratch>/') else value for value in row['argv']]
            planned[0] = argv[0]  # Exact interpreter path is preserved as observed.
            require(argv == planned, 'source-gate argv differs from frozen launch shape')
        elif phase == 'return':
            require(type(event.get('returncode')) is int and isinstance(event.get('stdout'), str) and isinstance(event.get('stderr'), str), 'full captured return evidence missing')
            returncodes[str(event['returncode'])] += 1
        elif phase == 'timeout':
            require(event.get('stdout') is None or isinstance(event.get('stdout'), str), 'partial timeout stdout missing')
            require(isinstance(event.get('stderr'), str), 'partial timeout stderr missing')
    require(len(summaries) == 1 and summaries[0].get('mode') == mode, 'one mode summary required')
    summary = summaries[0]
    for key, value in {'requested_outcomes': {'positive': 250, 'rejection': 260},
                       'actual_return_codes': dict(returncodes), 'completed_calls': 529,
                       'attempted_calls': 530, 'confirmed_starts': 530,
                       'nonsignalled_returns': 528, 'signal_returns': 1, 'timeouts': 1,
                       'adapter_starts': {'new': 521, 'legacy': 9},
                       'direct_control_outcomes': {'positive': 10, 'expected_rejection': 1,
                           'unexpected_error': 6, 'cli_usage64': 1, 'expected_signal': 1,
                           'expected_timeout': 1}}.items():
        require(summary.get(key) == value, 'source summary mismatch: ' + key)
    require(sum(int(code) >= 0 for code in returncodes.elements()) == 528 and
            sum(int(code) < 0 for code in returncodes.elements()) == 1,
            'actual event signal/non-signal counts disagree')
    return {'planned_calls': len(calls), 'attempts': 530, 'completed_process_returns': 529,
            'expected_timeouts': 1, 'parser_controls': 128, 'cleanup_absence_observations': 1,
            'actual_return_codes_from_events': dict(returncodes), 'source_summary': summaries[0]}


def group_alive(pgid):
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    return True


def cleanup(child, hard_deadline, events):
    # Every launched command owns a new session/process group. All real children
    # used by these test paths inherit that group. No name-based/PID-file killing.
    began = time.monotonic()
    for number, until in ((signal.SIGINT, began + 3), (signal.SIGTERM, began + 6), (signal.SIGKILL, hard_deadline)):
        if not group_alive(child.pid):
            break
        os.killpg(child.pid, number)
        events.append({'signal': number, 'pgid': child.pid, 'at_monotonic': time.monotonic()})
        while time.monotonic() < min(until, hard_deadline):
            child.poll()  # Reap the direct child, without treating that as tree cleanup.
            if not group_alive(child.pid):
                break
            time.sleep(min(0.05, max(0, min(until, hard_deadline) - time.monotonic())))
    child.poll()
    return child.returncode is not None and not group_alive(child.pid)


def budget_signal(number, frame):
    raise TimeoutError('enclosing budget cleanup reserve reached; STOP')


def main():
    if sys.argv[1:] != ['--run-once']:
        raise SystemExit('Usage: python3 -B run_once.py --run-once (no dry-run or retry)')
    setup = json.loads((HERE / 'SETUP.json').read_text())
    total_start = setup['job_start_monotonic']
    RESULT.mkdir()  # Existing directory means this allowance was already consumed.
    state = {'status': 'STOP/PARTIAL', 'total_start_monotonic': total_start,
             'total_deadline_monotonic': total_start + 900, 'commands': []}
    active = None
    group_deadline = None
    exit_code = 1
    signal.signal(signal.SIGALRM, budget_signal)
    signal.signal(signal.SIGTERM, budget_signal)
    signal.setitimer(signal.ITIMER_REAL, max(0.001, total_start + 890 - time.monotonic()))
    try:
        plan = json.loads(PLAN.read_text())
        root = HERE.parent / plan['source_root']
        require(root.is_dir(), 'source checkout absent')
        require(not any(os.environ.get(k) for k in ('PYTHONPATH', 'PYTHONHOME')), 'ambient Python import injection is outside this runner contract')
        capture_names = ('NVWA73_REAL_CAPTURE', 'NVWA76_REAL_CAPTURE')
        require(not any(name in os.environ for name in capture_names), 'optional real-capture inputs must be ABSENT for fixed-package acceptance')
        state['optional_real_capture_environment'] = {name: 'ABSENT' for name in capture_names}
        for name, expected in plan['pinned_inputs_sha256'].items():
            require(digest(HERE.parent / name) == expected, 'frozen input hash changed: ' + name)
        catalogue = json.loads((root / 'scripts/portable-checks.json').read_text())
        group = next(g for g in catalogue if g['name'] == plan['group_name'])
        require(group['run'] == plan['catalogue_body'], 'catalogue body changed')
        require(re.search(r'^for experiment in (.*); do$', group['run'], re.M).group(1).split() == plan['experiments'], 'catalogue experiment order changed')
        guard = (root / 'experiments/73-high-poly-eyes/test_frozen_inputs.py').read_text()
        require('NVWA73_LOCAL_GROUP_DEADLINE' in guard, 'required pre-T01 shared-deadline guard missing')
        ledger_path = next(HERE.parent / p for p in plan['pinned_inputs_sha256'] if p.endswith('/complete-ledger.json'))
        ledger = json.loads(ledger_path.read_text())
        commands = [(['node', '--version'], None, None)]
        for experiment in plan['experiments']:
            for mode in ('normal', 'optimized'):
                argv = ['python3', '-B'] + (['-O'] if mode == 'optimized' else [])
                argv += ['-m', 'unittest', 'discover', '-s', 'experiments/' + experiment, '-p', 'test_*.py', '-v', '-f']
                commands.append((argv, experiment, mode))
        require(len(commands) == 21, 'unexpected command count')
        temporary = RESULT / 'tmp'
        temporary.mkdir()
        environment = os.environ.copy()
        environment['PATH'] = '/usr/bin:/bin:' + environment.get('PATH', '')
        require(sys.implementation.name == 'cpython' and sys.version_info[:3] == (3, 12, 3), 'requires preinstalled CPython 3.12.3')
        require(Path(sys.executable).resolve() == Path('/usr/bin/python3').resolve(), 'launch runner with preinstalled /usr/bin/python3')
        tools = {}
        for tool in ('python3', 'node'):
            spelling = shutil.which(tool, path=environment['PATH'])
            require(spelling is not None, 'missing required interpreter: ' + tool)
            resolved = Path(spelling).resolve()
            tools[tool] = {'path': spelling, 'resolved': str(resolved), 'sha256': digest(resolved)}
        require(Path(tools['python3']['resolved']) == Path(sys.executable).resolve(), 'nested python3 differs from runner interpreter')
        state['interpreters'] = tools
        state['python_version'] = sys.version
        state['runner_executable'] = sys.executable
        state['setup_identity'] = setup
        require(time.monotonic() < total_start + 120, 'shared setup120 admission expired before group')
        environment.update(TMPDIR=str(temporary), RUNNER_TEMP=str(temporary))
        group_start = time.monotonic()
        group_deadline = min(group_start + 300, total_start + 900)
        environment['NVWA73_LOCAL_GROUP_DEADLINE'] = repr(group_deadline)
        signal.setitimer(signal.ITIMER_REAL, max(0.001, group_deadline - 10 - time.monotonic()))
        state.update(group_start_monotonic=group_start, group_deadline_monotonic=group_deadline,
                     abort_cleanup_start_monotonic=group_deadline - 10,
                     deadline_environment=environment['NVWA73_LOCAL_GROUP_DEADLINE'], planned_commands=commands,
                     caps_seconds=plan['caps_seconds'], local_only_change=plan['local_only_change'])
        initial_hashes = source_hashes(root, plan)
        write(RESULT / 'input-hashes.json', {'runner_sha256': digest(Path(__file__)), 'plan_sha256': digest(PLAN), 'source': initial_hashes, 'pins': plan['pinned_inputs_sha256']})
        for index, (argv, experiment, mode) in enumerate(commands, 1):
            require(time.monotonic() < group_deadline - 10, 'group cleanup reserve reached before next command')
            stdout = RESULT / f'{index:02d}.stdout.log'
            stderr = RESULT / f'{index:02d}.stderr.log'
            row = {'index': index, 'argv': argv, 'experiment': experiment, 'mode': mode,
                   'status': 'launch_attempt', 'start_monotonic': time.monotonic(), 'cleanup': []}
            state['commands'].append(row)
            write(RESULT / 'status.json', state)
            with stdout.open('xb') as out, stderr.open('xb') as err:
                active = subprocess.Popen(argv, cwd=root, env=environment, stdout=out, stderr=err, start_new_session=True)
                row.update(pid=active.pid, pgid=active.pid, status='running')
                try:
                    active.wait(timeout=max(0, group_deadline - 10 - time.monotonic()))
                except subprocess.TimeoutExpired:
                    row['status'] = 'outer_timeout'
                    signal.setitimer(signal.ITIMER_REAL, 0)
                    row['process_group_cleanup_observed'] = cleanup(active, group_deadline, row['cleanup'])
                    row['returncode'] = active.returncode
                    active = None
                    raise RuntimeError('whole-group cleanup reserve reached; no retry')
                row.update(returncode=active.returncode, end_monotonic=time.monotonic())
                require(not group_alive(active.pid), 'command returned with surviving process group')
                active = None
            require(row['returncode'] == 0, 'command failed; no retry')
            if experiment:
                row['suite_evidence'] = suite_evidence(stderr.read_bytes(), experiment, plan)
                if experiment == '73-high-poly-eyes':
                    row['gate_evidence'] = gate_evidence(stderr.read_bytes(), mode, ledger)
            row.update(status='passed', stdout_sha256=digest(stdout), stderr_sha256=digest(stderr))
            require(time.monotonic() < group_deadline - 10, 'group cleanup reserve reached during evidence review')
            write(RESULT / 'status.json', state)
        final_hashes = source_hashes(root, plan)
        write(RESULT / 'final-input-hashes.json', final_hashes)
        require(final_hashes == initial_hashes, 'source input bytes changed during run')
        require(time.monotonic() < group_deadline and time.monotonic() < total_start + 900, 'enclosing deadline reached')
        state['status'] = 'COMPLETE_UBUNTU_GROUP_REQUIRES_RAW_RECONCILIATION'
        exit_code = 0
    except BaseException as error:
        signal.setitimer(signal.ITIMER_REAL, 0)
        if state['commands'] and state['commands'][-1]['status'] not in ('passed', 'outer_timeout'):
            state['commands'][-1]['status'] = 'failed_or_incomplete'
        state['stop_reason'] = type(error).__name__ + ': ' + str(error)
        if active is not None:
            state['commands'][-1]['process_group_cleanup_observed'] = cleanup(active, min(group_deadline or total_start + 900, total_start + 900), state['commands'][-1]['cleanup'])
            state['commands'][-1]['returncode'] = active.returncode
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        for row in state['commands']:
            for stream in ('stdout', 'stderr'):
                path = RESULT / f"{row['index']:02d}.{stream}.log"
                if path.exists():
                    row[stream + '_sha256'] = digest(path)
        state['end_monotonic'] = time.monotonic()
        state['total_elapsed_seconds'] = state['end_monotonic'] - total_start
        if state['end_monotonic'] >= total_start + 900 or (group_deadline is not None and state['end_monotonic'] >= group_deadline):
            state['status'] = 'STOP/PARTIAL'
            state['stop_reason'] = 'enclosing deadline reached, including final evidence hashing'
            exit_code = 1
        if 'group_start_monotonic' in state:
            state['group_elapsed_seconds'] = state['end_monotonic'] - state['group_start_monotonic']
        write(RESULT / 'status.json', state)
        print(json.dumps({'status': state['status'], 'status_file': str(RESULT / 'status.json'),
                          'total_elapsed_seconds': state['total_elapsed_seconds']}), flush=True)
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
