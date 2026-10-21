#!/usr/bin/env python3
"""One immutable native seed per compatibility digest; trusted main pushes only."""
import argparse
from email.message import Message
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
import shutil
import stat
import socket
import ssl
import subprocess
import sys
import time
import urllib.parse
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('native_trial_guards', Path(__file__).resolve().parents[1] / 'cache_trial.py')
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)
require, encoded, sha = shared.require, shared.encoded, shared.sha
REPO = 'Derek-X-Wang/nvwa'
REF = 'refs/heads/main'
MARKER = '.nvwa-native-main-seed-v1.json'
ACTION = '55cc8345863c7cc4c66a329aec7e433d2d1c52a9'
NATIVE = ['crates/', 'vendor/', 'assets/', 'examples/',
          'experiments/49-runtime-pose-parity/probe/', 'experiments/50-upper-arm-neutral-ab/probe/',
          'experiments/60-b1-continuous-motion/', 'experiments/65-b1-appearance-quality/preview/',
          'experiments/66-b1-appearance-work/', 'experiments/68-b1-eye-render-diagnosis/',
          'experiments/71-b1-character-parameters/', 'experiments/73-high-poly-eyes/',
          'experiments/79-shoulder-pose-corrective/', 'experiments/62-b1-appearance-preview/assets/']
GATE_RS = 'experiments/60-b1-continuous-motion/src/bin/matrix.rs'
SDK_SELECTION = {'SDKROOT', 'DEVELOPER_DIR', 'MACOSX_DEPLOYMENT_TARGET'}
NATIVE_ENV = ['SDKROOT', 'DEVELOPER_DIR', 'MACOSX_DEPLOYMENT_TARGET', 'CC', 'CXX', 'AR', 'RANLIB',
              'CFLAGS', 'CXXFLAGS', 'CPPFLAGS', 'LDFLAGS', 'PKG_CONFIG_PATH', 'PKG_CONFIG_SYSROOT_DIR',
              'PKG_CONFIG_LIBDIR', 'LIBRARY_PATH', 'CPATH', 'C_INCLUDE_PATH', 'CPLUS_INCLUDE_PATH']


def emit(stage, **value):
    print('NVWA_NATIVE_MAIN_CACHE '+json.dumps({'stage': stage, **value}, sort_keys=True), flush=True)


def selected(root, env):
    phase = json.loads((root / 'experiments/83-native-cache-trial/phase.json').read_text())
    require(phase in [{'phase': mode} for mode in ['off', 'trial', 'adopted']], 'invalid phase selector')
    if phase != {'phase': 'adopted'} or env.get('GITHUB_EVENT_NAME') != 'push' or env.get('GITHUB_REPOSITORY') != REPO or env.get('GITHUB_REF') != REF:
        return False
    path = Path(env['GITHUB_EVENT_PATH'])
    require(path.stat().st_size <= 1024**2, 'event payload exceeds bound')
    event = json.loads(path.read_text())
    return (event.get('ref') == REF and event.get('after') == env.get('GITHUB_SHA')
            and event.get('deleted') is False and event.get('repository', {}).get('full_name') == REPO
            and event.get('repository', {}).get('default_branch') == 'main'
            and event.get('repository', {}).get('fork') is False)


def checked_source(root, env):
    require(env.get('GITHUB_WORKSPACE') == str(root), 'workspace differs from checkout')
    return shared.source(root, env)


def query(argv):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=15, check=True)
    require(len(result.stdout) <= 65536, 'tool identity exceeds bound')
    value = result.stdout.strip()
    require(value, 'empty tool identity: '+argv[0])
    return value


def file_hash(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            digest.update(block)
    return digest.hexdigest()


def input_paths(root):
    paths = shared.git(root, 'ls-files', '-z').split('\0')
    selected_paths = []
    for name in paths:
        if not name:
            continue
        path = Path(name)
        special = path.name in ['Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml', 'rust-toolchain', 'build.rs'] or '/.cargo/' in '/'+name
        gate = name.startswith('scripts/') or name in ['.github/workflows/ci.yml', 'experiments/27-ci-baseline/check.sh', GATE_RS,
                                                       'experiments/83-native-cache-trial/phase.json']
        gate = gate or (name.startswith(('experiments/60-b1-continuous-motion/', 'experiments/70-b1-garment-defect/',
                                        'experiments/83-native-cache-trial/')) and path.suffix == '.py')
        if special or gate or (name.startswith(tuple(NATIVE)) and path.suffix != '.rs'):
            selected_paths.append(name)
    return sorted(selected_paths)


def environment(env):
    names = {*shared.CARGO_ENV, 'CARGO_TARGET_DIR', 'CARGO_HOME', 'RUSTUP_HOME', 'RUSTUP_TOOLCHAIN',
             'RUNNER_OS', 'RUNNER_ARCH', 'ImageOS', 'ImageVersion', *NATIVE_ENV}
    unexpected = [key for key in env if key.startswith(('CARGO_', 'RUST', 'CC_', 'CXX_', 'AR_', 'CFLAGS_', 'CXXFLAGS_', 'PKG_CONFIG_')) and key not in names]
    require(not unexpected, 'unsupported build environment override')
    return {key: env.get(key) for key in sorted(names)}


def compatibility(root, env):
    snapshot = environment(env)
    for key, expected in shared.CARGO_ENV.items():
        require(env.get(key) == expected, 'native environment mismatch: '+key)
    permitted = {*shared.CARGO_ENV, 'CARGO_TARGET_DIR', 'CARGO_HOME', 'RUSTUP_HOME', 'RUSTUP_TOOLCHAIN'}
    extra = [key for key in env if key.startswith(('CARGO_', 'RUST')) and key not in permitted]
    extra += [key for key in env if key.startswith(('CC_', 'CXX_', 'AR_', 'CFLAGS_', 'CXXFLAGS_', 'PKG_CONFIG_'))]
    require(not extra and not any(env.get(k) for k in NATIVE_ENV if k not in SDK_SELECTION), 'unsupported compiler/Cargo environment override')
    require(env.get('RUNNER_OS') == 'macOS' and env.get('RUNNER_ARCH') == 'ARM64', 'unsupported runner')
    require(env.get('ImageOS') and env.get('ImageVersion'), 'runner image identity missing')
    # Cargo searches ancestors and CARGO_HOME; do not silently accept outside config.
    cargo_home = Path(env.get('CARGO_HOME', str(Path.home() / '.cargo')))
    configs = [directory / '.cargo' / name for directory in [root, *root.parents] for name in ['config', 'config.toml']]
    configs += [cargo_home / name for name in ['config', 'config.toml']]
    require(not any(path.exists() or path.is_symlink() for path in configs), 'unreviewed Cargo config unsupported')
    rustc, cargo = query(['rustc', '-vV']), query(['cargo', '--version'])
    require(rustc.startswith('rustc 1.95.0 ') and cargo.startswith('cargo 1.95.0 '), 'pinned toolchain mismatch')
    require(query(['uname', '-s']) == 'Darwin' and query(['uname', '-m']) == 'arm64', 'actual runner mismatch')
    sdk = Path(query(['xcrun', '--sdk', 'macosx', '--show-sdk-path'])).resolve()
    sdk_root = env.get('SDKROOT')
    if sdk_root:
        requested = Path(sdk_root)
        require(requested.is_absolute() and requested.is_dir() and requested.resolve() == sdk,
                'SDKROOT does not select the queried macOS SDK')
    deployment = env.get('MACOSX_DEPLOYMENT_TARGET')
    require(not deployment or (len(deployment) <= 16 and re.fullmatch(r'[0-9]+(?:\.[0-9]+){0,2}', deployment)
                              and int(deployment.split('.')[0]) > 0), 'invalid deployment target version')
    developer = env.get('DEVELOPER_DIR')
    if developer:
        requested_developer = Path(developer)
        require(requested_developer.is_absolute() and requested_developer.is_dir(), 'DEVELOPER_DIR is not an existing absolute root')
        requested_developer = requested_developer.resolve()
        require(requested_developer.name == 'Developer' and sdk.is_relative_to(requested_developer / 'Platforms'),
                'DEVELOPER_DIR does not contain the queried SDK')
    sdk_metadata = {p.name: file_hash(p) for p in [sdk / 'SDKSettings.json', sdk / 'SDKSettings.plist',
                    sdk / 'System/Library/CoreServices/SystemVersion.plist'] if p.is_file()}
    require(sdk_metadata and any(name.startswith('SDKSettings.') for name in sdk_metadata), 'SDK metadata missing')
    tools, hashes = {}, {}
    for name in ['clang', 'clang++', 'ld', 'ar', 'ranlib', 'strip']:
        path = Path(query(['xcrun', '--find', name])).resolve()
        require(path.is_file(), 'compiler/linker missing')
        if developer:
            require(path.is_relative_to(requested_developer / 'Toolchains'), 'DEVELOPER_DIR does not contain the selected toolchain')
        if path not in hashes:
            hashes[path] = file_hash(path)
        tools[name] = {'name': path.name, 'sha256': hashes[path]}
    zstd = query(['zstd', '--version'])
    require('v1.' in zstd, 'unsupported archive compressor')
    for name in ['tar', 'zstd']:
        path = Path(shutil.which(name) or '')
        require(path.is_file(), 'archive runtime missing')
        tools[name] = {'sha256': file_hash(path.resolve())}
    records = []
    for name in input_paths(root):
        path = root / name
        require(path.is_file() and not path.is_symlink(), 'tracked compatibility input unsafe: '+name)
        records.append([name, stat.S_IMODE(path.stat().st_mode), file_hash(path)])
    return {'schema': 1, 'environment': snapshot, 'inputs_sha256': sha(encoded(records)), 'input_count': len(records),
            'rustc': rustc, 'cargo': cargo, 'rustup': query(['rustup', 'show', 'active-toolchain']),
            'image': [env['RUNNER_OS'], env['RUNNER_ARCH'], env['ImageOS'], env['ImageVersion']],
            'system': query(['sw_vers']), 'kernel': query(['uname', '-r']),
            'xcode': query(['xcodebuild', '-version']), 'developer': Path(query(['xcode-select', '-p'])).name,
            'sdk': [query(['xcrun', '--sdk', 'macosx', '--show-sdk-version']),
                    query(['xcrun', '--sdk', 'macosx', '--show-sdk-build-version']), sdk_metadata],
            'tools': tools, 'clang': query(['xcrun', 'clang', '--version']),
            'archive': [ACTION, query(['tar', '--version']), zstd, 'zstd-without-long', False],
            'python': sys.version, 'build_env': shared.CARGO_ENV,
            'native_env': {key: env.get(key) for key in NATIVE_ENV},
            'target': str(root / 'target'), 'rustup_toolchain': env.get('RUSTUP_TOOLCHAIN')}


def owned_target(root, env):
    require(root.is_absolute() and root.resolve() == root, 'workspace parent symlink rejected')
    target = shared.target_path(root, env)
    if target.exists():
        info = target.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_dev == root.stat().st_dev, 'target type/device unsafe')
    return target


def clean_target(root, env):
    target = owned_target(root, env)
    started = time.monotonic()
    # Descriptor-relative traversal never follows links, including a raced
    # directory replacement. Check deadline and same device before each entry.
    if target.exists():
        require(all(fn in os.supports_dir_fd for fn in [os.open, os.stat, os.unlink, os.rmdir])
                and hasattr(os, 'O_NOFOLLOW') and hasattr(os, 'O_DIRECTORY'), 'safe deletion unavailable')
        count = 0
        def remove(directory):
            nonlocal count
            for name in os.listdir(directory):
                count += 1
                require(count <= 1_000_000 and time.monotonic()-started < 30, 'target cleanup bound exceeded')
                item = os.stat(name, dir_fd=directory, follow_symlinks=False)
                require(item.st_dev == root.stat().st_dev, 'target cleanup device boundary rejected')
                if stat.S_ISDIR(item.st_mode):
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                    try:
                        actual = os.fstat(child)
                        require((actual.st_dev, actual.st_ino) == (item.st_dev, item.st_ino), 'target cleanup raced directory')
                        remove(child)
                    finally:
                        os.close(child)
                    os.rmdir(name, dir_fd=directory)
                else:
                    os.unlink(name, dir_fd=directory)
        parent = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            descriptor = os.open('target', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            try:
                remove(descriptor)
            finally:
                os.close(descriptor)
            os.rmdir('target', dir_fd=parent)
        finally:
            os.close(parent)
    require(time.monotonic()-started < 30, 'target cleanup exceeded bound')
    # A replacement after the descriptor-relative rmdir must never be
    # certified as empty. lstat detects even dangling/empty-directory links.
    owned_target(root, env)
    try:
        target.lstat()
    except FileNotFoundError:
        pass
    else:
        raise ValueError('fixed target reappeared after cleanup')
    shared.empty_target(target)
    return {'verified_empty': True, 'seconds': time.monotonic()-started}


def api_entry(key, version):
    url = 'https://api.github.com/repos/'+REPO+'/actions/caches?'+urllib.parse.urlencode({'key': key, 'ref': REF})
    request = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'nvwa-native-main-cache'})
    with urllib.request.urlopen(request, timeout=20) as response:
        require(response.status == 200 and response.geturl() == url, 'cache API HTTP/redirect failure')
        raw = response.read(65537)
    require(len(raw) <= 65536, 'cache API body exceeds bound')
    data = json.loads(raw)
    require(type(data) is dict and type(data.get('total_count')) is int
            and type(data.get('actions_caches')) is list, 'cache API schema unknown')
    require(data['total_count'] == len(data['actions_caches']) and data['total_count'] in [0, 1], 'ambiguous cache API result')
    if not data['actions_caches']:
        return None
    row = data['actions_caches'][0]
    require(type(row) is dict, 'cache API entry schema invalid')
    require(row.get('key') == key and row.get('ref') == REF and row.get('version') == version,
            'cache API key/ref/version differs')
    require(type(row.get('id')) is int and row['id'] > 0 and type(row.get('size_in_bytes')) is int
            and 0 < row['size_in_bytes'] <= shared.CAP, 'cache API ID/size invalid')
    return {name: row[name] for name in ['id', 'key', 'ref', 'version', 'size_in_bytes']}


def http_failure(error):
    # Never read remote error prose. These are facts, not a root-cause claim.
    receipt = {'known': False, 'reason': 'HTTPError', 'cause': 'http_error'}
    try:
        status = error.code
        if type(status) is int and 100 <= status <= 599:
            receipt['http_status'] = status
            receipt['cause'] = {401: 'http_unauthorized', 403: 'http_forbidden',
                                404: 'http_not_found', 429: 'http_rate_limited'}.get(
                                    status, 'http_server_error' if status >= 500 else 'http_error')
        diagnostics = {}
        if isinstance(error.headers, Message):
            fields = [('X-GitHub-Request-Id', 'request_id'),
                      ('X-RateLimit-Remaining', 'rate_limit_remaining'),
                      ('X-RateLimit-Reset', 'rate_limit_reset'), ('Retry-After', 'retry_after_seconds')]
            for header, field in fields:
                values = error.headers.get_all(header, [])
                if len(values) != 1 or type(values[0]) is not str:
                    continue
                value = values[0]
                if field == 'request_id':
                    if len(value) <= 64 and re.fullmatch(r'[A-Fa-f0-9]{1,16}(?::[A-Fa-f0-9]{1,16}){3,4}', value):
                        diagnostics[field] = value
                elif len(value) <= 19 and re.fullmatch(r'[0-9]+', value) and int(value) <= 2**63-1:
                    diagnostics[field] = int(value)
        if diagnostics:
            receipt['diagnostics'] = diagnostics
        return receipt
    finally:
        try:
            error.close()
        except Exception:
            pass  # A close failure cannot authorize saving or hide HTTP facts.


def transport_cause(error):
    if isinstance(error, TimeoutError):
        return 'timeout'
    if isinstance(error, ssl.SSLError):
        return 'tls_error'
    if isinstance(error, socket.gaierror):
        return 'dns_error'
    return 'transport_error'


def probe(key, version):
    try:
        return {'known': True, 'entry': api_entry(key, version)}
    except urllib.error.HTTPError as error:
        return http_failure(error)
    except urllib.error.URLError as error:
        return {'known': False, 'reason': 'URLError', 'cause': transport_cause(error.reason)}
    except OSError as error:
        return {'known': False, 'reason': 'OSError', 'cause': transport_cause(error)}
    except (ValueError, KeyError) as error:
        return {'known': False, 'reason': 'ValueError' if isinstance(error, ValueError) else 'KeyError',
                'cause': 'invalid_json' if isinstance(error, json.JSONDecodeError) else 'response_validation_error'}


def action(env, prefix):
    return {name: env.get(prefix+'_'+name.upper(), '') for name in ['outcome', 'hit', 'primary', 'matched']}


def exact(action_row, key):
    return action_row == {'outcome': 'success', 'hit': 'true', 'primary': key, 'matched': key}


def producer(source, env):
    require(all(type(env.get(name)) is str and env[name].isdigit() and int(env[name]) > 0
                for name in ['GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT']), 'invalid run/attempt identity')
    return {**source, 'repository': REPO, 'ref': REF, 'event': 'push',
            'run_id': env['GITHUB_RUN_ID'], 'run_attempt': env['GITHUB_RUN_ATTEMPT']}


def verify_restore(root, env, state):
    target = owned_target(root, env)
    row = action(env, 'MAIN_RESTORE')
    receipt = None
    reason = 'cache absence independently verified' if state['api']['known'] and state['api']['entry'] is None else 'unverified action/API restore'
    try:
        require(state['api']['known'] and state['api']['entry'] is not None and exact(row, state['key']), 'exact restore/API required')
        marker_path = target / MARKER
        require(marker_path.is_file() and not marker_path.is_symlink() and marker_path.stat().st_size <= 65536, 'main marker missing/unsafe')
        marker = json.loads(marker_path.read_text())
        require(type(marker) is dict and set(marker) == {'schema', 'key', 'compatibility', 'producer', 'inventory'}
                and type(marker['schema']) is int and marker['schema'] == 1 and marker['key'] == state['key']
                and marker['compatibility'] == state['compatibility'], 'main marker compatibility mismatch')
        origin = marker['producer']
        require(type(origin) is dict and set(origin) == set(state['consumer'])
                and origin.get('repository') == REPO and origin.get('ref') == REF and origin.get('event') == 'push'
                and all(type(origin.get(name)) is str and len(origin[name]) == 40
                        and all(c in '0123456789abcdef' for c in origin[name]) for name in ['sha', 'tree'])
                and all(type(origin.get(name)) is str and origin[name].isdigit() and int(origin[name]) > 0 for name in ['run_id', 'run_attempt']), 'main producer provenance missing')
        measured = shared.target_measurement(target, 'main-restore')
        require(measured['logical_bytes'] <= shared.CAP, 'restored target oversize')
        require(marker['inventory'] == shared.inventory(target, marker_name=MARKER), 'restored main inventory differs')
        receipt = probe(state['key'], state['version'])
        require(receipt == state['api'], 'cache API entry changed/unknown after restore')
        state.update(status='VERIFIED_RESTORE', producer=origin, restore=row)
        emit('restore', status=state['status'], action=row, api=receipt, producer=origin, consumer=state['consumer'])
        return
    except (OSError, ValueError, KeyError) as error:
        reason = str(error) if exact(row, state['key']) else reason
    cleanup = clean_target(root, env)
    state.update(status='CLEAN_FALLBACK', restore=row)
    emit('restore', status=state['status'], reason=reason, action=row, api=state['api'], cleanup=cleanup,
         consumer=state['consumer'], warm=False, **({'recheck_api': receipt} if receipt is not None else {}))


def finish(root, env, state):
    target = owned_target(root, env)
    measured = shared.target_measurement(target, 'main-finish')
    require(state['consumer'] == producer(checked_source(root, env), env), 'main cache consumer identity changed')
    require(measured['logical_bytes'] <= shared.CAP, 'full logical target exceeds cap')
    evidence = shared.gates(root, Path(env['RUNNER_TEMP']))
    checked_source(root, env)
    if state['status'] == 'VERIFIED_RESTORE':
        emit('finish', status='IMMUTABLE_SEED_CONSUMED_NO_SAVE', consumer=state['consumer'], target_size=measured, gates=evidence)
        return False
    require(state['status'] == 'CLEAN_FALLBACK', 'restore disposition missing')
    # Unknown service state and existing immutable entries must never be overwritten.
    if not state['api']['known'] or state['api']['entry'] is not None:
        emit('finish', status='NOT_PERSISTED_UNKNOWN_OR_EXISTING', api=state['api'], target_size=measured, gates=evidence)
        return False
    marker = target / MARKER
    require(not marker.exists() and not marker.is_symlink(), 'new main seed marker must be absent')
    inventory = shared.inventory(target, marker_name=MARKER)
    payload = encoded({'schema': 1, 'key': state['key'], 'compatibility': state['compatibility'],
                       'producer': state['consumer'], 'inventory': inventory})
    size = measured['logical_bytes'] + len(payload)
    emit('save-size', target_size=measured, marker_bytes=len(payload), full_saved_logical_bytes=size)
    require(len(payload) <= 65536 and size <= shared.CAP, 'full logical target plus exact marker exceeds cap')
    absent = probe(state['key'], state['version'])
    if not absent['known'] or absent['entry'] is not None:
        emit('finish', status='NOT_PERSISTED_ABSENCE_NOT_RECONFIRMED', api=absent)
        return False
    marker.write_bytes(payload)
    emit('finish', status='VERIFIED_ABSENT_SEED_READY', producer=state['consumer'], gates=evidence,
         inventory=inventory, full_saved_logical_bytes=size)
    return True


def persist(env, state):
    require(state.get('save_ready') is True, 'no verified save preparation')
    row = action(env, 'MAIN_PERSIST')
    receipt = probe(state['key'], state['version'])
    valid = (env.get('MAIN_SAVE_OUTCOME') == 'success' and exact(row, state['key'])
             and receipt['known'] and receipt['entry'] is not None)
    emit('persistence', status='VERIFIED_PERSISTED' if valid else 'NOT_PERSISTED_UNKNOWN',
         save_outcome=env.get('MAIN_SAVE_OUTCOME', ''), lookup=row, api=receipt, attempted_producer=state['consumer'], remote_producer='UNKNOWN_UNTIL_VERIFIED_RESTORE')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['prepare', 'restore', 'finish', 'persist'])
    args = parser.parse_args()
    env = os.environ
    started = time.monotonic()
    state_path = Path(env['RUNNER_TEMP']) / 'nvwa-native-main-seed-state.json'
    if args.stage == 'prepare':
        shared.output({'enabled': 'false'})
        if not selected(ROOT, env):
            emit('prepare', status='DISABLED_EVENT_OR_PHASE')
            return
        source = checked_source(ROOT, env)
        shared.empty_target(owned_target(ROOT, env))
        try:
            identity = compatibility(ROOT, env)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            emit('prepare', status='DISABLED_UNSUPPORTED_IDENTITY', reason=type(error).__name__+': '+str(error))
            return
        key = 'nvwa-native-main-seed-v1-'+sha(encoded(identity))
        # Official pinned cache getCacheVersion: paths | compression | salt1.0;
        # Darwin, crossOS false, zstd required. Bind API to this archive version.
        version = sha((str(ROOT / 'target')+'|zstd-without-long|1.0').encode())
        state = {'owner': [ROOT.stat().st_dev, ROOT.stat().st_ino], 'key': key, 'version': version, 'compatibility': identity,
                 'consumer': producer(source, env), 'api': probe(key, version), 'status': 'PREPARED'}
        state_path.write_bytes(encoded(state))
        shared.output({'enabled': 'true', 'key': key, 'restore': str(state['api']['known'] and state['api']['entry'] is not None).lower()})
        emit('prepare', status='PREPARED', key=key, version=version, compatibility=identity,
             consumer=state['consumer'], api=state['api'])
    else:
        require(selected(ROOT, env), 'main cache event/phase no longer authorized')
        require(state_path.is_file() and not state_path.is_symlink() and state_path.stat().st_size <= 131072, 'main state file missing/unsafe')
        state = json.loads(state_path.read_text())
        if args.stage != 'finish':
            require(state['consumer'] == producer(checked_source(ROOT, env), env), 'main cache consumer identity changed')
        require(state['owner'] == [ROOT.stat().st_dev, ROOT.stat().st_ino], 'owned checkout changed')
        require(state['compatibility']['environment'] == environment(env), 'build environment changed after preparation')
        require(state['key'] == 'nvwa-native-main-seed-v1-'+sha(encoded(state['compatibility']))
                and state['version'] == sha((str(ROOT / 'target')+'|zstd-without-long|1.0').encode()), 'key/archive version changed')
        if args.stage == 'restore':
            verify_restore(ROOT, env, state)
            state_path.write_bytes(encoded(state))
        elif args.stage == 'finish':
            state['save_ready'] = finish(ROOT, env, state)
            state_path.write_bytes(encoded(state))
            shared.output({'save': str(state['save_ready']).lower()})
        else:
            persist(env, state)
    emit('boundary-cost', stage_name=args.stage, seconds=time.monotonic()-started)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print('FAIL: '+str(error), file=sys.stderr)
        sys.exit(1)
