#!/usr/bin/env python3
"""Fail-closed boundaries for one same-source native compiled-target experiment."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
MARKER = '.nvwa-native-cache-trial.json'
CAP = 4 * 1024**3
CARGO_ENV = {'CARGO_BUILD_JOBS': '1', 'CARGO_INCREMENTAL': '0',
             'CARGO_PROFILE_DEV_DEBUG': '0', 'CARGO_PROFILE_TEST_DEBUG': '0',
             'CARGO_TERM_COLOR': 'always'}
CASES = ['omit-authored-arm-pose', 'stale-garment-upload', 'omit-authored-foot-counterrotation']
ASSERTIONS = {CASES[0]: 'assertion failed: part_position_deltas(&rest, &middle)',
              CASES[1]: 'assertion failed: part_position_deltas(&rest, &middle)',
              CASES[2]: 'actual moving foot dips below floor:'}
TESTS = {CASES[0]: 'b1::tests::actual_motion_clock_changes_bones_and_both_uploaded_meshes_without_refit',
         CASES[1]: 'b1::tests::actual_motion_clock_changes_bones_and_both_uploaded_meshes_without_refit',
         CASES[2]: 'b1::tests::authored_knee_counterrotation_keeps_actual_early_and_full_cycle_feet_above_floor'}
# matrix.rs: 3 torsos x 3 jaws x 2 clips x 33 times, then 8 seeks and
# 1 pause per neutral-recipe clip. run_matrix.py checks all non-complete
# events; its final complete marker increments only the stream total.
MATRIX_GRID = 3 * 3 * 2 * 33
MATRIX_CHECKED = MATRIX_GRID + 2 * (8 + 1)
MATRIX_STREAM = MATRIX_CHECKED + 1
MATRIX_COVERAGE = {'expected': MATRIX_GRID, 'observed': MATRIX_GRID, 'missing': [],
                   'deep_keyframes_expected': 3 * 2 * 5,
                   'deep_keyframes_observed': 3 * 2 * 5,
                   'complete': True, 'body_variants': 3, 'face_settings': 3}



def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def git(root, *args):
    return subprocess.check_output(['git', '--no-optional-locks', '-C', str(root), *args]).decode().strip()


def selected(root, env):
    phase = json.loads((root / 'experiments/83-native-cache-trial/phase.json').read_text())
    require(phase == {'phase': phase.get('phase')} and phase['phase'] in ['off', 'trial', 'adopted'], 'invalid phase selector')
    # adopted remains inactive until a separate reviewed policy change after data.
    return (phase['phase'] == 'trial' and env.get('GITHUB_EVENT_NAME') == 'pull_request'
            and env.get('GITHUB_REPOSITORY') == 'Derek-X-Wang/nvwa'
            and env.get('TRIAL_HEAD_REPOSITORY') == env.get('GITHUB_REPOSITORY')
            and env.get('TRIAL_HEAD_REF') == 'codex/native-cache-trial')


def target_path(root, env):
    target = root / 'target'
    require(env.get('CARGO_TARGET_DIR') == str(target), 'target must be the existing root target path')
    require(not target.is_symlink(), 'target symlink rejected')
    return target


def empty_target(target):
    require(not target.is_symlink(), 'fresh target symlink rejected')
    require(not target.exists() or (target.is_dir() and not any(target.iterdir())), 'fresh target must be absent or empty')


def source(root, env):
    require(not git(root, 'status', '--porcelain', '--untracked-files=no'), 'tracked source or lockfiles changed')
    head = git(root, 'rev-parse', 'HEAD')
    require(head == env.get('GITHUB_SHA'), 'checkout differs from immutable workflow SHA')
    return {'sha': head, 'tree': git(root, 'rev-parse', 'HEAD^{tree}')}


def identity(root, env):
    require(selected(root, env), 'trial is not authorized for this phase/event/repository/branch')
    for key, value in CARGO_ENV.items():
        require(env.get(key) == value, 'native build environment differs: '+key)
    # Do not allow unrecorded Cargo/Rust overrides. Existing native lane has none.
    extra = {k: v for k, v in env.items() if k.startswith(('CARGO_', 'RUST'))
             and k not in {*CARGO_ENV, 'CARGO_TARGET_DIR', 'CARGO_HOME', 'RUSTUP_HOME', 'RUSTUP_TOOLCHAIN'}}
    require(not extra, 'unexpected Cargo/Rust environment override: '+','.join(sorted(extra)))
    require(env.get('RUNNER_OS') == 'macOS' and env.get('RUNNER_ARCH') == 'ARM64', 'expected macOS ARM64 runner')
    require(env.get('ImageOS') and env.get('ImageVersion'), 'runner image identity missing')
    uname = {name: subprocess.check_output(['uname', flag], text=True).strip()
             for name, flag in [('system', '-s'), ('machine', '-m')]}
    require(uname == {'system': 'Darwin', 'machine': 'arm64'}, 'actual host must be Darwin arm64')
    rustc = subprocess.check_output(['rustc', '-vV'], text=True)
    cargo = subprocess.check_output(['cargo', '--version'], text=True).strip()
    require(rustc.startswith('rustc 1.95.0 ') and cargo.startswith('cargo 1.95.0 '), 'pinned Rust toolchain mismatch')
    # Full tracked tree covers every manifest/lock/config/workflow and command source.
    files = git(root, 'ls-files', '-z').split('\0')
    config = {p: sha((root / p).read_bytes()) for p in files if p and
              (Path(p).name in ['Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml', 'rust-toolchain']
               or p.startswith(('.cargo/', '.github/workflows/', 'scripts/')))}
    return {**source(root, env), 'rustc': rustc, 'cargo': cargo,
            'os': env['RUNNER_OS'], 'arch': env['RUNNER_ARCH'], 'image_os': env['ImageOS'],
            'image_version': env['ImageVersion'], 'uname': uname, 'build_env': CARGO_ENV,
            'rustup_toolchain': env.get('RUSTUP_TOOLCHAIN'), 'config_sha256': sha(encoded(config))}


def key_for(value, env):
    require(all(env.get(k, '').isdigit() and int(env[k]) > 0 for k in ['GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT']), 'invalid run/attempt')
    return 'nvwa-native-trial-v1-'+value['sha']+'-'+value['tree']+'-'+sha(encoded(value))+'-'+env['GITHUB_RUN_ID']+'-'+env['GITHUB_RUN_ATTEMPT']


def public_cold_miss(key):
    # Repository-wide prefix absence covers every scope visible to restore. No
    # token, alternate endpoint, ref filter, pagination or fallback is permitted.
    url = 'https://api.github.com/repos/Derek-X-Wang/nvwa/actions/caches?'+urllib.parse.urlencode({'key': key})
    request = urllib.request.Request(url, headers={
        'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'nvwa-native-cache-trial',
    })
    with urllib.request.urlopen(request, timeout=30) as response:
        require(type(response.status) is int and response.status == 200 and response.geturl() == url, 'cold cache lookup requires unredirected HTTP 200')
        body = response.read(65537)
    require(len(body) <= 65536, 'cold cache lookup response exceeds bound')
    data = json.loads(body)
    require(type(data) is dict and set(data) == {'total_count', 'actions_caches'}
            and type(data['total_count']) is int and data['total_count'] == 0
            and type(data['actions_caches']) is list and data['actions_caches'] == [],
            'cold cache lookup must prove zero repository-wide key-prefix matches')
    return {'lane': 'cold', 'key': key, 'query_key': key, 'http_status': 200,
            'total_count': 0, 'actions_caches_count': 0, 'miss_verified': True,
            'scope': 'repository-wide-key-prefix', 'transport': 'anonymous-public-rest'}


def exact_receipt(lane, hit, primary, matched, key):
    require(lane in ['warm', 'persisted'], 'cold miss requires independently verified public REST lookup')
    require(primary == key, 'cache primary key mismatch/missing')
    require(hit == 'true' and matched == key, 'exact persisted cache hit required; cold fallback forbidden')


def target_measurement(target, lane):
    """Stat every owned entry without following links or hashing file contents."""
    measurement = {'logical_bytes': 0, 'files': 0, 'symlinks': 0,
                   'directories': 0, 'entries': 0, 'complete': False}
    started = time.monotonic()
    try:
        require(target.is_dir() and not target.is_symlink(), 'target directory missing/unsafe')
        def scan_error(error):
            raise error
        for parent, directories, files in os.walk(target, followlinks=False, onerror=scan_error):
            for name in directories + files:
                path = Path(parent) / name
                measurement['entries'] += 1
                require(measurement['entries'] <= 1_000_000 and time.monotonic()-started <= 30,
                        'target stat scan bound exceeded; full logical size unknown')
                item = path.lstat()
                if stat.S_ISDIR(item.st_mode):
                    measurement['directories'] += 1
                else:
                    measurement['logical_bytes'] += item.st_size
                    if stat.S_ISLNK(item.st_mode):
                        measurement['symlinks'] += 1
                    else:
                        require(stat.S_ISREG(item.st_mode), 'unsupported target entry')
                        measurement['files'] += 1
        measurement['complete'] = True
    finally:
        # A failed scan is explicitly partial. Gate/cap failures occur only
        # after this receipt; oversize scans still retain the entire total.
        emit('target-size', {'lane': lane, **measurement})
    return measurement


def validate_matrix(matrix):
    require(type(matrix) is dict and matrix.get('passed') is True
            and type(matrix.get('probe_exit')) is int and matrix['probe_exit'] == 0
            and matrix.get('probe_complete_marker') is True
            and type(matrix.get('records')) is int and matrix['records'] == MATRIX_STREAM
            and type(matrix.get('passing_records')) is int and matrix['passing_records'] == MATRIX_CHECKED
            and type(matrix.get('failures')) is list and matrix['failures'] == [],
            'actual complete motion matrix event contract required')
    coverage = matrix.get('coverage')
    require(type(coverage) is dict and set(coverage) == set(MATRIX_COVERAGE),
            'actual complete motion matrix coverage schema required')
    require(all(type(coverage[key]) is type(expected) and coverage[key] == expected
                for key, expected in MATRIX_COVERAGE.items()),
            'actual complete motion matrix coverage contract required')


def inventory(target, marker_name=MARKER):
    require(target.is_dir() and not target.is_symlink(), 'target directory missing/unsafe')
    rows, size = [], 0
    for path in sorted(target.rglob('*')):
        relative = path.relative_to(target).as_posix()
        if relative == marker_name:
            continue
        mode = path.lstat().st_mode
        if stat.S_ISDIR(mode):
            continue
        if stat.S_ISLNK(mode):
            link = os.readlink(path)
            try:
                resolved = path.resolve(strict=True)
            except (OSError, RuntimeError) as error:
                raise ValueError('target symlink is unresolved or loops') from error
            require(resolved.is_relative_to(target.resolve(strict=True)), 'target symlink escapes cache')
            require(resolved.is_file(), 'target directory symlinks unsupported')
            rows.append([relative, 'link', link])
        else:
            require(stat.S_ISREG(mode), 'unsupported target entry')
            size += path.stat().st_size
            require(size <= CAP, 'logical target exceeds 4 GiB cap')
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024**2), b''):
                    digest.update(chunk)
            rows.append([relative, stat.S_IMODE(mode), path.stat().st_size, digest.hexdigest()])
    require(rows, 'empty compiled target cannot be saved/restored')
    require(size + 65536 <= CAP, 'logical target including receipt exceeds 4 GiB cap')
    return {'logical_bytes': size, 'entries': len(rows), 'sha256': sha(encoded(rows))}


def gates(root, temporary):
    mutation = json.loads((temporary / 'nvwa-b1-motion-mutations/summary.json').read_text())
    require(mutation.get('passed') is True and [c['name'] for c in mutation['cases']] == CASES, 'all three semantic mutation cases required')
    semantic_receipts = []
    for case in mutation['cases']:
        require(case.get('semantic_test_failure') is True and case.get('red_exit') == 101
                and case.get('restored_green') is True and case.get('restored_exit') == 0
                and case.get('before_sha256') == case.get('restored_sha256')
                and case.get('mutant_sha256') != case.get('before_sha256')
                and sha((root / case['source']).read_bytes()) == case['restored_sha256'], 'mutation semantic red/restored green/source mismatch')
        name = case['name']
        command = ['cargo', 'test', '--workspace', '--lib', '--locked', '--offline',
                   TESTS[name], '--', '--exact', '--test-threads=1', '--nocapture']
        require(case.get('command') == command and case.get('intended_assertion') == ASSERTIONS[name],
                'semantic witness command/assertion differs')
        logs = {}
        for suffix in ['red', 'restored-green']:
            filename = name+'-'+suffix+'.log'
            path = temporary / 'nvwa-b1-motion-mutations' / filename
            require(path.stat().st_size <= 32 * 1024**2, 'mutation log exceeds receipt bound')
            raw = path.read_bytes()
            require(mutation.get('hashes', {}).get(filename) == sha(raw), 'mutation log receipt hash differs/missing')
            logs[suffix] = raw.decode(errors='replace')
        red, green = logs['red'], logs['restored-green']
        require('running 1 test' in red and TESTS[name] in red and ASSERTIONS[name] in red
                and 'test result: FAILED. 0 passed; 1 failed' in red and 'error[E' not in red
                and 'test result: ok. 1 passed; 0 failed' in green, 'retained semantic red/restored green logs disagree')
        semantic_receipts.append({'name': name, 'test': TESTS[name], 'intended_assertion': ASSERTIONS[name],
                                  'intended_assertion_observed': True, 'red_exit': case['red_exit'],
                                  'red_one_failed_test_observed': True, 'restored_exit': case['restored_exit'],
                                  'restored_one_passed_test_observed': True, 'source_restored_sha256': case['restored_sha256'],
                                  'red_log_sha256': mutation['hashes'][name+'-red.log'],
                                  'restored_log_sha256': mutation['hashes'][name+'-restored-green.log']})
    matrix = json.loads((temporary / 'nvwa-b1-motion-matrix/summary.json').read_text())
    validate_matrix(matrix)
    return {'mutations': mutation, 'semantic_receipts': semantic_receipts, 'matrix': matrix}


def emit(name, value):
    print('NVWA_NATIVE_CACHE '+json.dumps({'stage': name, **value}, sort_keys=True), flush=True)


def output(values):
    with Path(os.environ['GITHUB_OUTPUT']).open('a') as stream:
        for key, value in values.items():
            stream.write(f'{key}={value}\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['prepare', 'cold-miss', 'receipt', 'finish'])
    parser.add_argument('--lane', choices=['cold', 'warm', 'persisted'], required=True)
    args = parser.parse_args()
    env = os.environ
    start = time.monotonic()
    if args.stage == 'prepare' and args.lane == 'cold' and not selected(ROOT, env):
        output({'enabled': 'false'})
        return
    measured = None
    if args.stage == 'finish':
        require(selected(ROOT, env), 'trial is not authorized for this phase/event/repository/branch')
        measured = target_measurement(target_path(ROOT, env), args.lane)
        require(measured['logical_bytes'] <= CAP, 'full logical target exceeds 4 GiB cap')
    value = identity(ROOT, env)
    target = target_path(ROOT, env)
    key = key_for(value, env)
    if args.stage == 'prepare':
        empty_target(target)
        if args.lane == 'warm':
            require(env.get('TRIAL_EXPECTED_KEY') == key, 'producer source/toolchain/image/config differs')
        output({'enabled': 'true', 'key': key})
        emit('prepare', {'lane': args.lane, 'key': key, 'identity': value})
    elif args.stage == 'cold-miss':
        require(args.lane == 'cold', 'public miss lookup is cold only')
        empty_target(target)
        emit('cold-miss', public_cold_miss(key))
        empty_target(target)
    elif args.stage == 'receipt':
        exact_receipt(args.lane, env.get('TRIAL_HIT', ''), env.get('TRIAL_PRIMARY', ''), env.get('TRIAL_MATCHED', ''), key)
        record = {'lane': args.lane, 'key': key, 'hit': env.get('TRIAL_HIT', ''), 'matched_key': env.get('TRIAL_MATCHED', '')}
        if args.lane == 'warm':
            marker = json.loads((target / MARKER).read_text())
            require(marker == {'key': key, 'identity': value, 'inventory': inventory(target)}, 'restored target receipt/integrity mismatch')
            record['verified_inventory'] = marker['inventory']
        emit('receipt', record)
    else:
        evidence = gates(ROOT, Path(env['RUNNER_TEMP']))
        source(ROOT, env)
        marker = target / MARKER
        if args.lane == 'cold':
            require(not marker.exists() and not marker.is_symlink(), 'cold target receipt must be absent')
        saved = inventory(target)
        if args.lane == 'cold':
            payload = encoded({'key': key, 'identity': value, 'inventory': saved})
            size = {'marker_bytes': len(payload), 'marker_added_bytes': len(payload),
                    'full_saved_logical_bytes': measured['logical_bytes'] + len(payload)}
            emit('target-save-size', {'lane': args.lane, **size})
            require(size['full_saved_logical_bytes'] <= CAP, 'full logical target plus exact receipt exceeds 4 GiB cap')
            marker.write_bytes(payload)
        else:
            require(marker.is_file() and not marker.is_symlink(), 'warm target receipt missing/unsafe')
            size = {'marker_bytes': marker.stat().st_size, 'marker_added_bytes': 0,
                    'full_saved_logical_bytes': measured['logical_bytes']}
        emit('finish', {'lane': args.lane, 'key': key, 'inventory': saved, 'target_size': measured,
                        **size, 'gates': evidence, 'source_restored': True})
    emit('boundary-cost', {'stage_name': args.stage, 'lane': args.lane, 'seconds': time.monotonic()-start})


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print('FAIL: '+str(error), file=sys.stderr)
        sys.exit(1)
