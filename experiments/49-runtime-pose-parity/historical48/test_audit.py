#!/usr/bin/env python3
"""Exercise the historical adapter's real CLI and unchanged child failure boundary."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
spec = importlib.util.spec_from_file_location('historical48_audit', HERE / 'audit.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def cli(repo):
    command = [sys.executable] + (['-O'] if sys.flags.optimize else [])
    command += [str(repo / HERE.relative_to(REPO) / 'audit.py'), '--repo-root', str(repo)]
    environment = dict(os.environ)
    environment.pop('PYTHONOPTIMIZE', None)
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    return subprocess.run(command, capture_output=True, text=True, env=environment,
                          timeout=30, check=False)


def main():
    started = time.monotonic()
    plan = adapter.preflight(REPO)
    cases = []
    with tempfile.TemporaryDirectory(prefix='nvwa-historical48-controls-') as directory:
        fixture = Path(directory) / 'repo'
        fixture.mkdir()
        # Start from the checked historical payload, then restore the two CURRENT sources.
        adapter.stage_snapshot(plan, fixture)
        policy = adapter.decode((HERE / 'POLICY.json').read_bytes())
        extra = set()
        for pin in policy['current_cohorts'].values():
            extra.add(pin['path'])
            cohort = adapter.decode(adapter.read(REPO, pin['path']))
            extra.update(cohort['files'])
            extra.update(cohort['snapshot_build']['source_files'])
        extra.update(adapter.SUBSTITUTIONS)
        for relative in extra:
            target = fixture / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(adapter.read(REPO, relative))
        material = fixture / HERE.relative_to(REPO)
        shutil.copytree(HERE, material, ignore=shutil.ignore_patterns('__pycache__', 'results', 'SHA256SUMS'))
        baseline = cli(fixture)
        require(baseline.returncode == 0, 'baseline CLI failed: ' + baseline.stderr)

        def mutation(name, edits, expected):
            originals = {}
            for relative, replacement in edits.items():
                path = fixture / relative
                originals[relative] = path.read_bytes()
                if replacement is None:
                    path.unlink()
                else:
                    path.write_bytes(replacement)
            try:
                red = cli(fixture)
                require(red.returncode != 0 and 'REJECT_HISTORICAL48:' in red.stderr
                        and expected in red.stderr, name + ' did not reject at intended gate: ' + red.stderr)
            finally:
                for relative, data in originals.items():
                    (fixture / relative).write_bytes(data)
            green = cli(fixture)
            require(green.returncode == 0, name + ' did not restore green: ' + green.stderr)
            cases.append({'name': name, 'red_exit': red.returncode,
                          'reason': red.stderr.strip(), 'restored_exit': green.returncode})

        material_relative = HERE.relative_to(REPO).as_posix()
        for entry in policy['substitutions']:
            archive = material_relative + '/' + entry['archive_path']
            mutation('corrupt archive ' + entry['repo_path'], {archive: b'corrupt\n'}, 'input identity changed')
            mutation('remove archive ' + entry['repo_path'], {archive: None}, 'missing input')
            mutation('change current ' + entry['repo_path'],
                     {entry['repo_path']: adapter.read(REPO, entry['repo_path']) + b'\n'}, 'input identity changed')
        mutation('change another of 52 inputs', {'Cargo.toml': adapter.read(REPO, 'Cargo.toml') + b'\n'},
                 'input identity changed: Cargo.toml')
        policy_path = material_relative + '/POLICY.json'
        def policy_mutation(name, edit, expected):
            changed = json.loads(json.dumps(policy))
            edit(changed)
            mutation(name, {policy_path: json.dumps(changed).encode()}, expected)
        policy_mutation('missing substitution', lambda p: p['substitutions'].pop(), 'exactly two')
        policy_mutation('extra substitution', lambda p: p['substitutions'].append(p['substitutions'][0]), 'exactly two')
        policy_mutation('duplicate substitution', lambda p: p['substitutions'].__setitem__(1, p['substitutions'][0]),
                        'missing, extra, or duplicate')
        policy_mutation('broaden substitution path', lambda p: p['substitutions'][0].__setitem__('repo_path', 'Cargo.toml'),
                        'missing, extra, or duplicate')
        policy_mutation('broaden current identity pin', lambda p: p['substitutions'][0]['current'].__setitem__('bytes', 0),
                        'policy pin changed')
        policy_mutation('broaden cohort identity pin', lambda p: p['current_cohorts']['native'].__setitem__('sha256', '0' * 64),
                        'policy pin changed')
        native = policy['current_cohorts']['native']['path']
        web = policy['current_cohorts']['web']['path']
        mutation('cross native and Web cohorts', {native: adapter.read(REPO, web), web: adapter.read(REPO, native)},
                 'input identity changed')
        runtime_verifier = adapter.RUNTIME + '/verify_evidence.py'
        mutation('change original verifier', {runtime_verifier: adapter.read(REPO, runtime_verifier) + b'\n'},
                 'input identity changed')
        current_probe_source = 'experiments/49-runtime-pose-parity/probe/src/lib.rs'
        mutation('change current49 build source', {current_probe_source: adapter.read(REPO, current_probe_source) + b'\n'},
                 'current cohort source changed')

        staged = Path(directory) / 'staged'
        staged.mkdir()
        adapter.stage_snapshot(plan, staged)
        for name, relative in [('staged historical source', 'Cargo.toml'),
                               ('staged historical artifact', next(iter(policy['artifacts'])))]:
            path = staged / relative
            original = path.read_bytes()
            path.write_bytes(original + b'\n')
            try:
                try:
                    adapter.run_staged(staged, optimized=bool(sys.flags.optimize))
                except adapter.Rejected as error:
                    require('original audit CLI exit 1: REJECT:' in str(error), name + ' rejected elsewhere')
                    reason = str(error)
                else:
                    raise RuntimeError(name + ' passed damaged original CLI')
            finally:
                path.write_bytes(original)
            require(adapter.run_staged(staged, optimized=bool(sys.flags.optimize))['status'] == 'PASS_RETAINED_AUDIT',
                    name + ' did not restore')
            cases.append({'name': name, 'red_exit': 1, 'reason': reason, 'restored_exit': 0})

        # Exercise the production child execution seam with a real OS subprocess exit.
        # The original scripts remain byte-exact; no monkeypatch/import of them occurs.
        shim = Path(directory) / 'fail-child'
        shim.write_text('#!' + sys.executable + '\nimport sys\nsys.stderr.write("forced child exit\\n")\nsys.exit(7)\n')
        shim.chmod(0o700)
        for check in ('audit', 'controls'):
            try:
                adapter.run_staged(staged, check, bool(sys.flags.optimize), shim)
            except adapter.Rejected as error:
                require('original ' + check + ' CLI exit 7: forced child exit' == str(error),
                        'child failure was not propagated')
                cases.append({'name': 'propagate ' + check + ' child nonzero', 'red_exit': 7,
                              'reason': str(error), 'restored_exit': 'NOT-RUN; original suites run separately'})
            else:
                raise RuntimeError(check + ' swallowed child failure')
    print(json.dumps({'status': 'PASS_HISTORICAL48_ADAPTER_CONTROLS',
                      'mode': 'optimized' if sys.flags.optimize else 'normal',
                      'cases': cases, 'case_count': len(cases),
                      'cli_mutation_red': sum(isinstance(c['restored_exit'], int) for c in cases),
                      'cli_restored_green': sum(c['restored_exit'] == 0 for c in cases),
                      'forced_child_nonzero': 2, 'original_26_case_suites': 'run separately via --check controls',
                      'duration_seconds': round(time.monotonic() - started, 3)}, sort_keys=True))


if __name__ == '__main__':
    main()
