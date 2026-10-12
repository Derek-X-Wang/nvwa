"""Bounded local compile + named CPU test execution; no dependency/tool install."""
import hashlib
import json
import os
import re
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
STAGE = sys.argv[1]
assert STAGE in ('green', 'paint-mutant', 'restored-green')
source = ROOT / 'crates/nvwa-studio/src/editor_layout.rs'
expected_source = (OUT / 'editor_layout.candidate.rs').read_bytes()
if STAGE == 'paint-mutant':
    expected_source = expected_source.replace(b'let visuals = if selected {', b'let visuals = if !selected {', 1)
assert source.read_bytes() == expected_source, 'candidate source hash mismatch; refusing missing/stale test run'
source_sha = hashlib.sha256(expected_source).hexdigest()
env = os.environ.copy()
env['CARGO_BUILD_JOBS'] = '1'
command = ['cargo', 'test', '-p', 'nvwa-studio', '--lib', '--no-run', '--locked', '--message-format=json']
start = time.monotonic()
with (OUT / f'{STAGE}-compile.jsonl').open('w') as stdout, (OUT / f'{STAGE}-compile.log').open('w') as stderr:
    process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
    print(f'COMPILE stage={STAGE} pid={process.pid}', flush=True)
    try:
        result = process.wait(timeout=180)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        raise RuntimeError('bounded compile timeout')
assert result == 0, f'compile failed; inspect {STAGE}-compile.log'
executables = set()
for line in (OUT / f'{STAGE}-compile.jsonl').read_text().splitlines():
    row = json.loads(line)
    if row.get('reason') == 'compiler-artifact' and row.get('executable') and row.get('target', {}).get('name') == 'nvwa_studio' and row.get('profile', {}).get('test'):
        executables.add(row['executable'])
assert len(executables) == 1, f'missing/ambiguous studio executable: {executables}'
binary = executables.pop()
record = {'stage': STAGE, 'compile_command': command, 'compile_seconds': time.monotonic()-start,
          'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'binary': binary,
          'binary_sha256': hashlib.sha256(Path(binary).read_bytes()).hexdigest(), 'tests': []}
test_start = time.monotonic()
expected_names = {
    'paint': {
        'editor_layout::tests::ui_paint_oracle_selected_tabs_match_independent_table',
        'editor_layout::tests::ui_paint_oracle_missing_output_is_failure',
    },
    'state': {'editor_layout::tests::actual_studio_layout_controls_preserve_work_history_and_guard_focused_space'},
}
for label, test_filter in [('paint', 'ui_paint_oracle'), ('state', 'actual_studio_layout_controls_preserve_work_history_and_guard_focused_space')]:
    listing = subprocess.check_output([binary, test_filter, '--list'], cwd=ROOT, text=True, timeout=5)
    (OUT / f'{STAGE}-{label}.list').write_text(listing)
    names = {line.removesuffix(': test') for line in listing.splitlines() if line.endswith(': test')}
    assert names == expected_names[label], f'missing/ambiguous exact named tests: {names}'
    args = [binary, test_filter, '--nocapture', '--test-threads=1']
    with (OUT / f'{STAGE}-{label}.log').open('w') as log:
        result = subprocess.run(args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=max(1, 60-(time.monotonic()-test_start)))
    (OUT / f'{STAGE}-{label}.exit').write_text(str(result.returncode)+'\n')
    text = (OUT / f'{STAGE}-{label}.log').read_text()
    count = len(expected_names[label])
    assert re.search(rf'running {count} tests?\b', text), 'missing positive execution count'
    wanted_passed = count - 1 if STAGE == 'paint-mutant' and label == 'paint' else count
    wanted_failed = 1 if STAGE == 'paint-mutant' and label == 'paint' else 0
    assert re.search(rf'test result: (?:ok|FAILED)\. {wanted_passed} passed; {wanted_failed} failed;', text), 'unexpected exact test result count'
    record['tests'].append({'kind': label, 'command': args, 'exit': result.returncode, 'exact_names': sorted(names), 'passed': wanted_passed, 'failed': wanted_failed})
    print(f'TEST stage={STAGE} kind={label} exit={result.returncode}', flush=True)
record['test_seconds'] = time.monotonic()-test_start
(OUT / f'{STAGE}-result.json').write_text(json.dumps(record, indent=2)+'\n')
if STAGE == 'paint-mutant':
    assert record['tests'][0]['exit'] != 0, 'paint-only mutation unexpectedly green'
    assert 'paint-oracle fill mismatch' in (OUT/f'{STAGE}-paint.log').read_text(), 'red was not the named paint mismatch'
    assert record['tests'][1]['exit'] == 0, 'state control failed under paint-only mutation'
else:
    assert all(row['exit'] == 0 for row in record['tests']), 'expected green failed'
