"""Static runtime and frozen-source admission. No observer dispatch or gate call."""
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
SOURCE_SHA = 'eb90badc63fd12753224f1691e8a57b3848241e8'


def runtime_identity():
    if (sys.implementation.name != 'cpython' or sys.platform != 'linux'
            or not (3, 12) <= sys.version_info[:2] <= (3, 14)
            or platform.machine() != 'x86_64' or sys.flags.optimize
            or not sys.dont_write_bytecode
            or Path(sys.executable).resolve() != Path('/usr/bin/python3').resolve()):
        raise RuntimeError('requires preinstalled /usr/bin/python3 Linux x64 CPython3.12-3.14 normal -B')
    monitoring = sys.monitoring
    for name in ('get_tool', 'use_tool_id', 'register_callback', 'set_events', 'set_local_events'):
        if not callable(getattr(monitoring, name, None)):
            raise RuntimeError('required sys.monitoring symbol missing: ' + name)
    for name in ('PY_START', 'PY_RETURN', 'PY_UNWIND'):
        if not isinstance(getattr(monitoring.events, name, None), int):
            raise RuntimeError('required monitoring event missing: ' + name)
    if monitoring.get_tool(monitoring.PROFILER_ID) is not None:
        raise RuntimeError('profiler tool slot occupied')
    binary = Path('/usr/bin/python3').resolve()
    return {'requested_executable': '/usr/bin/python3', 'resolved_executable': str(binary),
            'executable_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
            'version': sys.version, 'flags': repr(sys.flags), 'machine': platform.machine(),
            'uname': list(platform.uname()),
            'image': {key: os.environ.get(key) for key in ('ImageOS', 'ImageVersion', 'RUNNER_OS', 'RUNNER_ARCH')},
            'monitoring_check': 'symbols and unused PROFILER_ID only; no dispatch smoke test'}


def git(root, *args):
    from acquire import read_git
    return read_git(root,*args)


def authenticate_source(root):
    expected = json.loads((HERE / 'INPUT-INVENTORY.json').read_text())
    if git(root, 'rev-parse', 'HEAD') != SOURCE_SHA:
        raise RuntimeError('source HEAD mismatch')
    patterns=''.join('/'+name+'\n' for name in sorted(expected['files']))
    if (git(root,'config','--local','--get','core.sparseCheckout')!='true'
        or git(root,'config','--local','--get','core.sparseCheckoutCone')!='false'
        or (root/'.git/info/sparse-checkout').read_text()!=patterns):
        raise RuntimeError('exact rooted non-cone sparse state mismatch')
    actual = {}
    for path in sorted(root.rglob('*')):
        name = path.relative_to(root).as_posix()
        if name == '.git' or name.startswith('.git/'):
            continue
        if path.is_symlink():
            raise RuntimeError('source symlink: ' + name)
        if path.is_file():
            data = path.read_bytes()
            actual[name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    if len(actual) != 337 or actual != expected['files']:
        raise RuntimeError('sparse working-tree file set/hash/size differs from frozen337')
    if sum(x['bytes'] for x in actual.values()) != 55045771:
        raise RuntimeError('source size mismatch')
    return {'head': SOURCE_SHA, 'count': len(actual), 'bytes': 55045771,
            'inventory_sha256': hashlib.sha256((HERE / 'INPUT-INVENTORY.json').read_bytes()).hexdigest()}


def check_setup():
    setup = json.loads((Path(os.environ['RUNNER_TEMP']) / 'exp73-setup.json').read_text())
    now = time.time()
    spent = (time.monotonic_ns() - setup['monotonic_ns']) / 1e9
    if not 0 <= spent < 120 or now > setup['queue_expires_epoch']:
        raise RuntimeError('shared setup120s or absolute admission expiry exceeded')
    # 120+60+60=240 leaves 60s margin within the job300s outer ceiling.
    if 300 - spent < 180:
        raise RuntimeError('insufficient job time for measurement/export/margin')
    return {'setup': setup, 'setup_elapsed_seconds': spent}


if __name__ == '__main__':
    if sys.argv[1:] != ['--setup-admission']:
        raise SystemExit('setup admission only')
    record = check_setup()
    def setup_expired(signum, frame):
        raise TimeoutError('shared120s setup deadline expired during admission')
    signal.signal(signal.SIGALRM, setup_expired)
    signal.setitimer(signal.ITIMER_REAL, max(.001,120-record['setup_elapsed_seconds']))
    record['runtime'] = runtime_identity()
    record['source'] = authenticate_source(HERE.parents[1] / 'source')
    record['tooling_sha'] = git(HERE.parent, 'rev-parse', 'HEAD')
    if record['tooling_sha'] != os.environ['GITHUB_SHA']:
        raise RuntimeError('tooling commit mismatch')
    # Full source hashing is charged to the same setup allowance.
    record['setup_after_admission'] = check_setup()
    (HERE / 'SETUP.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    signal.setitimer(signal.ITIMER_REAL,0)
