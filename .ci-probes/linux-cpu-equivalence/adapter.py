#!/usr/bin/env python3
"""Private preparation package. Default inspect is inert; execute needs later approval."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import time

PACKAGE = Path(__file__).resolve().parent
MUTATED = ('crates/nvwa-b1-adapter/src/motion.rs', 'crates/nvwa-runtime/src/b1.rs')


def remaining(deadline, cap=None):
    value = deadline-time.monotonic() if deadline is not None else 10
    if value <= 0:
        raise TimeoutError('total deadline exhausted; verification incomplete')
    return min(value, cap) if cap is not None else value


def sha(path, deadline=None):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while True:
            remaining(deadline)
            chunk = stream.read(65536)
            if not chunk:
                return digest.hexdigest()
            digest.update(chunk)


def read_json(name):
    return json.loads((PACKAGE / name).read_text())


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def git(root, *args, deadline=None):
    return subprocess.check_output(['git', '--no-optional-locks', '-C', str(root), *args], text=True, timeout=remaining(deadline, 10)).strip()


def verify_source(root, fresh=False, deadline=None):
    expected = read_json('SOURCE.json')
    if git(root, 'rev-parse', 'HEAD', deadline=deadline) != expected['head']:
        raise ValueError('checkout HEAD differs from pinned source')
    if git(root, 'rev-parse', 'HEAD^{tree}', deadline=deadline) != expected['tree']:
        raise ValueError('checkout tree identity differs')
    if git(root, 'status', '--porcelain', '--untracked-files=all', *(['--ignored'] if fresh else []), deadline=deadline):
        raise ValueError('checkout must be clean; initial run also refuses ignored inputs/caches')
    for relative, digest in expected['sha256'].items():
        path = root / relative
        if path.is_symlink() or sha(path, deadline) != digest:
            raise ValueError(f'missing/drifted source: {relative}')
    return expected


def verify_platform(system=None, machine=None, os_release=None):
    system = platform.system() if system is None else system
    machine = platform.machine() if machine is None else machine
    os_release = platform.freedesktop_os_release() if os_release is None else os_release
    if system != 'Linux' or machine != 'x86_64' or os_release.get('ID') != 'ubuntu' or os_release.get('VERSION_ID') != '24.04':
        raise ValueError('execution supports Ubuntu24.04 x86_64 only')


def environment(root, out, event_head=None, event_checkout=None):
    # Inherit only host tool lookup/home/locale. Do not inherit Cargo profile,
    # RUSTFLAGS, cache or GitHub identities from a surrounding process.
    env = {key: os.environ[key] for key in ('PATH', 'HOME', 'LANG', 'LC_ALL', 'RUSTUP_HOME') if key in os.environ}
    env.update(CARGO_TERM_COLOR='always', CARGO_INCREMENTAL='0',
               CARGO_PROFILE_DEV_DEBUG='0', CARGO_PROFILE_TEST_DEBUG='0',
               CARGO_BUILD_JOBS='1', CARGO_TARGET_DIR=str(root / 'target'),
               CARGO_HOME=str(out / 'cargo-home'), RUSTUP_TOOLCHAIN='1.95.0',
               GITHUB_WORKSPACE=str(root), RUNNER_TEMP=str(out / 'tmp'),
               NVWA_ADAPTER_DIR=str(PACKAGE), NVWA_TIMING_DIR=str(out / 'timing'),
               GITHUB_WORKFLOW='private-linux-cpu-feasibility', GITHUB_JOB='linux-cpu-feasibility')
    if event_head:
        env['NVWA_CI_HEAD_SHA'] = event_head
    if event_checkout:
        env['GITHUB_SHA'] = event_checkout
    return env


def toolchain_environment(product_env, deadline=None):
    # Rustup's existing installation home is distinct from dependency isolation.
    home = Path(product_env.get('HOME', ''))
    if not home.is_absolute() or not home.is_dir():
        raise ValueError('host HOME must be an absolute existing installation context')
    if product_env.get('RUSTUP_HOME') and not Path(product_env['RUSTUP_HOME']).is_absolute():
        raise ValueError('host RUSTUP_HOME must be absolute when explicitly supplied')
    raw_cargo_home = os.environ.get('CARGO_HOME')
    cargo_home = Path(raw_cargo_home) if raw_cargo_home else home / '.cargo'
    if not cargo_home.is_absolute() or not cargo_home.is_dir():
        raise ValueError('host Cargo installation home must already exist and be absolute')
    installed = cargo_home / 'bin/rustup'
    on_path = shutil.which('rustup', path=product_env.get('PATH', ''))
    if not installed.is_file() or not os.access(installed, os.X_OK) or not on_path:
        raise ValueError('host Cargo home lacks its existing executable rustup installation')
    if sha(installed.resolve(), deadline) != sha(Path(on_path).resolve(), deadline):
        raise ValueError('host Cargo home rustup bytes differ from PATH rustup')
    setup_env = dict(product_env, CARGO_HOME=str(cargo_home))
    return setup_env, {
        'cargo_home': str(cargo_home),
        'cargo_home_provenance': 'original CARGO_HOME' if raw_cargo_home else 'original HOME/.cargo default',
        'rustup_home': product_env.get('RUSTUP_HOME', str(home / '.rustup')),
        'rustup_home_provenance': 'original RUSTUP_HOME' if product_env.get('RUSTUP_HOME') else 'original HOME/.rustup default',
        'installation_rustup': str(installed), 'path_rustup': on_path,
        'installation_bytes_match_path': True,
        'limit': 'Static installation-path admission only; actual setup and product-context proxy readiness require later execution.'}


class ProcessFailure(RuntimeError):
    def __init__(self, message, group_quiescent):
        super().__init__(message)
        self.group_quiescent = group_quiescent


def group_exists(pid):
    try:
        os.killpg(pid, 0)
        return True
    except ProcessLookupError:
        return False


def quiesce(child, deadline):
    # kill(0) establishes group absence; leader wait alone does not.
    if group_exists(child.pid):
        for number in (signal.SIGTERM, signal.SIGKILL):
            remaining(deadline)
            try:
                os.killpg(child.pid, number)
            except ProcessLookupError:
                break
        while group_exists(child.pid):
            # Reap our direct child; adopted descendants may remain observable.
            try:
                child.wait(timeout=min(.02, remaining(deadline)))
            except subprocess.TimeoutExpired:
                pass
            time.sleep(min(.01, remaining(deadline)))
    child.wait(timeout=remaining(deadline))


def run_process(command, root, env, log, timeout, deadline=None):
    """No return/next step/restoration until owned group absence is observed."""
    started = time.monotonic()
    deadline = started + timeout if deadline is None else deadline
    if timeout <= 0:
        raise ProcessFailure('total budget exhausted', True)
    child = None
    with log.open('wb') as output:
        try:
            child = subprocess.Popen(command, cwd=root, env=env, stdout=output,
                                     stderr=subprocess.STDOUT, start_new_session=True)
            code = child.wait(timeout=min(timeout, remaining(deadline)))
            if group_exists(child.pid):
                quiesce(child, deadline)
                raise ProcessFailure('descendants survived process leader; stopped', True)
        except BaseException as error:
            if isinstance(error, ProcessFailure):
                raise
            if child is not None:
                try:
                    quiesce(child, deadline)
                except BaseException as cleanup:
                    raise ProcessFailure(f'{error}; group cleanup UNKNOWN: {cleanup}', False) from cleanup
            raise ProcessFailure(str(error), True) from error
    return {'argv': command, 'exit': code, 'seconds': time.monotonic() - started,
            'log': str(log), 'group_quiescent': True}


def reject_cargo_config(root, cargo_home):
    # Cargo reads cwd ancestors and CARGO_HOME even when env flags are clean.
    checked = []
    directories = [root, *root.parents]
    for directory in directories:
        for name in ('config', 'config.toml'):
            path = directory / '.cargo' / name
            checked.append(str(path))
            if path.exists() or path.is_symlink():
                raise ValueError(f'unreviewed effective Cargo configuration: {path}')
    for name in ('config', 'config.toml'):
        path = cargo_home / name
        checked.append(str(path))
        if path.exists() or path.is_symlink():
            raise ValueError(f'unreviewed Cargo home configuration: {path}')
    return {'status': 'ABSENT', 'checked': checked}


def tool_receipts(root, env, deadline=None):
    rows = {}
    for tool in ('bash', 'git', 'python3', 'rustup', 'cargo', 'rustc', 'shasum'):
        path = shutil.which(tool, path=env['PATH'])
        if not path:
            raise ValueError(f'required tool missing: {tool}; no install fallback')
        rows[tool] = {'path': path, 'resolved_path': str(Path(path).resolve()), 'sha256': sha(Path(path).resolve(), deadline)}
    return rows


def build_tool_receipts(root, setup_env, env, deadline):
    rows = {}
    def remaining():
        value = deadline-time.monotonic()-10
        if value <= 0:
            raise TimeoutError('total budget exhausted during tool identity collection')
        return min(5, value)
    for tool in ('cargo', 'rustc', 'rustfmt', 'clippy-driver'):
        path = subprocess.check_output(['rustup', 'which', '--toolchain', '1.95.0', tool], cwd=root, env=setup_env, text=True, timeout=remaining()).strip()
        version = subprocess.check_output([path, '--version'], cwd=root, env=setup_env, text=True, timeout=remaining()).strip()
        rows[tool] = {'path': path, 'sha256': sha(Path(path), deadline), 'version': version}
    if not rows['rustc']['version'].startswith('rustc 1.95.0 '):
        raise ValueError('unexpected Rust version')
    for tool in ('cargo', 'rustc'):
        actual = Path(shutil.which(tool, path=env['PATH'])).resolve()
        proxy = Path(shutil.which('rustup', path=env['PATH'])).resolve()
        if sha(actual, deadline) not in (rows[tool]['sha256'], sha(proxy, deadline)):
            raise ValueError(f'{tool} on PATH does not dispatch the pinned build tool')
        observed = subprocess.check_output([tool, '--version'], cwd=root, env=env, text=True, timeout=remaining()).strip()
        if observed != rows[tool]['version']:
            raise ValueError(f'{tool} on PATH has a different version')
    return {'tools': rows, 'discovery_environment_phase': 'toolchain',
            'cargo_rustc_proxy_validation_environment_phase': 'product'}


def verify_package(deadline=None):
    for relative, digest in read_json('PACKAGE-SHA256.json').items():
        if sha(PACKAGE / relative, deadline) != digest:
            raise ValueError(f'package drift: {relative}')


def execute(args):
    started = time.monotonic()
    plan = read_json('PLAN.json')
    deadline = started + plan['total_seconds']
    # This mode flag expresses intent; it does not supply human authorization.
    if sys.version_info < (3, 12):
        raise ValueError('execution requires Python3.12+ as python3 on PATH')
    if not args.disposable_checkout:
        raise ValueError('execute requires declared --disposable-checkout ownership')
    verify_platform()
    verify_package(deadline)
    original_source, out = args.source.resolve(strict=True), args.out.resolve()
    if out == original_source or original_source in out.parents or out in original_source.parents or out.exists():
        raise ValueError('run directory must be new and independent of source')
    source = verify_source(original_source, deadline=deadline)
    root = out / 'checkout'
    env = environment(root, out, args.event_head, args.event_checkout)
    config_disposition = reject_cargo_config(root, Path(env['CARGO_HOME']))
    setup_env, setup_provenance = toolchain_environment(env, deadline)
    tools = tool_receipts(root, env, deadline)
    out.mkdir(parents=True, exist_ok=False)
    (out / 'tmp').mkdir()
    (out / 'cargo-home').mkdir()
    originals = {}
    receipt = {'status': 'INCOMPLETE', 'source': source, 'checkout': str(root),
               'event_identity': {'declared_event_head': args.event_head, 'declared_event_checkout': args.event_checkout,
                                  'limit': 'Caller declarations only; no GitHub event authentication. Actual checkout identity is source.head/tree.'},
               'environments': {'product': env, 'toolchain': setup_env},
               'toolchain_home_provenance': setup_provenance, 'cargo_config': config_disposition, 'tools': tools,
               'tools_environment_phase': 'product', 'commands': [], 'excluded': plan['excluded'],
               'adapter_sha256': sha(Path(__file__), deadline), 'package_sha256': read_json('PACKAGE-SHA256.json')}
    code = 1
    previous = {}
    process_quiescent = True
    def stop(number, frame):
        raise InterruptedError(f'interrupted by signal {number}')
    try:
        for number in (signal.SIGINT, signal.SIGTERM):
            previous[number] = signal.signal(number, stop)
        write_json(out / 'receipt.json', receipt)
        # Only this newly-created clone is mutable. Never restore into caller source.
        clone = ['git', 'clone', '--no-local', '--no-hardlinks', '--depth', '1', '--no-tags', '--', str(original_source), str(root)]
        result = run_process(clone, original_source, env, out / 'clone.log', deadline-time.monotonic()-10, deadline=deadline)
        result['environment_phase'] = 'product'
        receipt['clone'] = result
        if result['exit']:
            raise ValueError('owned disposable clone failed; no fallback')
        verify_source(root, fresh=True, deadline=deadline)
        originals = {name: (root / name).read_bytes() for name in MUTATED}
        for step in plan['steps']:
            command = ['python3', '-B', str(root / 'scripts/ci-timing.py'), 'shell', str(PACKAGE / step['file'])]
            # Ten seconds remain for process cleanup, exact source restoration
            # and the original always-report. No retries or Mac fallback.
            step_budget = deadline - time.monotonic() - 10
            timeout = min(step_budget, step['timeout_seconds'] or step_budget)
            environment_phase = 'toolchain' if step['id'] == 'toolchain' else 'product'
            step_env = setup_env if environment_phase == 'toolchain' else env
            receipt['commands'].append({'id': step['id'], 'environment_phase': environment_phase, 'status': 'INCOMPLETE', 'argv': command, 'timeout_seconds': timeout})
            write_json(out / 'receipt.json', receipt)
            result = run_process(command, root, step_env, out / (step['id'] + '.log'), timeout, deadline=deadline)
            receipt['commands'][-1].update(result, status='COMPLETE')
            write_json(out / 'receipt.json', receipt)
            if result['exit']:
                raise ValueError(f"first failure: {step['id']} exited {result['exit']}")
            if step['id'] == 'toolchain':
                receipt['build_tools'] = build_tool_receipts(root, setup_env, env, deadline)
        summary = json.loads((out / 'tmp/nvwa-b1-motion-mutations/summary.json').read_text())
        if summary.get('passed') is not True or len(summary.get('cases', [])) != 3 or not all(c.get('semantic_test_failure') and c.get('restored_green') for c in summary['cases']):
            raise ValueError('missing complete original mutation witness summary')
        receipt['mutation_summary_sha256'] = sha(out / 'tmp/nvwa-b1-motion-mutations/summary.json', deadline)
        code = 0
    except (Exception, KeyboardInterrupt) as error:
        process_quiescent = getattr(error, 'group_quiescent', True)
        receipt['error'] = f'{type(error).__name__}: {error}'
    finally:
        receipt['process_group_quiescent'] = process_quiescent
        receipt['source_restored'] = 'UNKNOWN'
        receipt['always_timing_report'] = {'status': 'UNKNOWN', 'error': 'not attempted'}
        if process_quiescent:
            try:
                for name, original in originals.items():
                    remaining(deadline)
                    path = root / name
                    if path.read_bytes() != original:
                        remaining(deadline)
                        path.write_bytes(original)
                verify_source(root, deadline=deadline)
                receipt['source_restored'] = True
            except Exception as error:
                receipt['restoration_error'] = str(error)
                code = 1
            try:
                timeout = remaining(deadline, 5)
                result = run_process(['python3', '-B', str(root / 'scripts/ci-timing.py'), 'report'], root, env, out / 'timing-report.log', timeout, deadline=deadline)
                result['environment_phase'] = 'product'
                receipt['always_timing_report'] = result
                if result['exit']:
                    code = 1
            except Exception as error:
                receipt['always_timing_report'] = {'status': 'UNKNOWN', 'error': str(error)}
                receipt['process_group_quiescent'] = getattr(error, 'group_quiescent', True)
                code = 1
        else:
            receipt['restoration_error'] = 'group cleanup UNKNOWN; no source writes or further commands permitted'
            code = 1
        receipt.update(status='PASS' if code == 0 else 'FAIL', seconds=time.monotonic() - started,
                       limit='Only selected Linux CPU probe. No gate/cadence adoption, Mac or heavy matrix proof.')
        write_json(out / 'receipt.json', receipt)
        for number, handler in previous.items():
            signal.signal(number, handler)
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode')
    sub.add_parser('inspect')
    verify = sub.add_parser('verify-source')
    verify.add_argument('--checkout', type=Path, required=True)
    run = sub.add_parser('execute')
    run.add_argument('--source', type=Path, required=True, help='Read-only exact source; adapter creates its own mutable clone')
    run.add_argument('--out', type=Path, required=True)
    run.add_argument('--disposable-checkout', action='store_true')
    for flag in ('--event-head', '--event-checkout'):
        run.add_argument(flag, help='Optional independently supplied event identity; never inferred')
    args = parser.parse_args(argv)
    if args.mode in (None, 'inspect'):
        print(json.dumps(read_json('PLAN.json'), indent=2))
        return 0
    if args.mode == 'verify-source':
        print(json.dumps(verify_source(args.checkout.resolve()), indent=2))
        return 0
    return execute(args)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f'REFUSED: {error}', file=sys.stderr)
        sys.exit(2)
