#!/usr/bin/env python3
"""Bounded, disposable M1.1 profile experiment. Build requires a root lease."""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
import urllib.request

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
WORK = REPO / '.work/m11-web'
SOURCE = WORK / 'source'
EVIDENCE = WORK / 'evidence'
CANDIDATE = WORK / 'candidate/web'
ROOT = Path(subprocess.check_output(['git', 'rev-parse', '--path-format=absolute', '--git-common-dir'], cwd=REPO, text=True).strip()).parent
BASELINE = ROOT / '.work/m1-1/baseline'
TOOL = ROOT / '.tools/wasm-bindgen/wasm-bindgen-0.2.129-aarch64-apple-darwin/wasm-bindgen'
HEAD = '11fc789e898119e0ed2b423f8a909dacb547f772'
FIRST_SCREEN = ['index.html', 'nvwa_studio.js', 'nvwa_studio_bg.wasm', 'assets/fixtures/nvwa-humanoid.glb']
PROFILE = '\n[profile.web-size]\ninherits = "release"\nopt-level = "s"\nlto = "thin"\ncodegen-units = 1\n'
STATIC = {
    'web/index.html': 'index.html',
    'assets/character.profile.json': 'assets/character.profile.json',
    'assets/fixtures/nvwa-humanoid.glb': 'assets/fixtures/nvwa-humanoid.glb',
    'assets/fixtures/LICENSE.txt': 'assets/fixtures/LICENSE.txt',
    'assets/fixtures/provenance-manifest.json': 'assets/fixtures/provenance-manifest.json',
    'examples/m1-sequence.nvwa.json': 'works/m1-sequence.nvwa.json',
    'assets/fonts/OFL.txt': 'licenses/fonts/OFL.txt',
    'assets/fonts/NOTICE.md': 'licenses/fonts/NOTICE.md',
    'assets/fonts/PROVENANCE.json': 'licenses/fonts/PROVENANCE.json',
}

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return {'bytes': path.stat().st_size, 'sha256': h.hexdigest()}

def blob(name):
    return subprocess.check_output(['git', 'show', HEAD + ':' + name], cwd=REPO)

def frozen_product():
    result = {}
    for name in tracked_inputs():
        data = blob(name)
        result[name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    return result

def tree(path):
    return {str(p.relative_to(path)): digest(p) for p in sorted(path.rglob('*')) if p.is_file()}

def save(name, data):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / name).write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')

def load(name):
    return json.loads((EVIDENCE / name).read_text())

def tracked_inputs():
    names = subprocess.check_output(['git', 'ls-tree', '-r', '-z', '--name-only', HEAD], cwd=REPO).decode().split('\0')
    roots = ('crates/', 'assets/', 'examples/', 'web/')
    return [n for n in names if n and (n.startswith(roots) or n in ('Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml'))]

def source_checks(approved=False):
    freeze = load('freeze-before.json')
    names = tracked_inputs()
    if names != freeze['input_paths']:
        raise SystemExit('Tracked input inventory changed')
    if sorted(tree(SOURCE)) != sorted(names):
        raise SystemExit('Generated input inventory changed')
    frozen = frozen_product()
    if frozen != freeze['source']:
        raise SystemExit('Frozen Git product inputs differ from recorded manifest')
    for name in names:
        if name == 'Cargo.toml' and approved:
            if (SOURCE / name).read_bytes() != blob(name) + PROFILE.encode():
                raise SystemExit('Generated manifest does not equal frozen manifest plus exact approved profile')
        elif digest(SOURCE / name) != freeze['source'][name]:
            raise SystemExit('Generated input changed: ' + name)
    if tree(BASELINE) != freeze['baseline']:
        raise SystemExit('Accepted baseline changed')
    if digest(TOOL) != freeze['wasm_bindgen']:
        raise SystemExit('Pinned wasm-bindgen binary changed')
    save('freeze-after.json', {'source_base': HEAD, 'source': frozen, 'generated': tree(SOURCE), 'baseline': tree(BASELINE), 'wasm_bindgen': digest(TOOL)})

def prepare(_):
    if SOURCE.exists():
        raise SystemExit('Generated source exists; refusing replacement')
    if not (BASELINE / 'nvwa-studio').is_file() or not (BASELINE / 'web/index.html').is_file() or not TOOL.is_file():
        raise SystemExit('Root must first freeze the verified accepted native/Web artifacts and supply pinned wasm-bindgen; rebuilding does not recreate a byte-identical accepted baseline')
    names = tracked_inputs()
    source = frozen_product()
    for name in names:
        target = SOURCE / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob(name))
    save('freeze-before.json', {'source_head': HEAD, 'primary_checkout': str(ROOT), 'input_paths': names, 'source': source, 'baseline': tree(BASELINE), 'wasm_bindgen': digest(TOOL), 'proposed_profile': PROFILE})
    source_checks()
    print('Prepared unchanged generated source. Root must append the exact proposed profile before build.')

def descendants_snapshot(pid):
    raw = subprocess.check_output(['ps', '-axo', 'pid=,ppid=,rss=,comm='], text=True, timeout=5)
    rows = []
    for line in raw.splitlines():
        parts = line.strip().split(None, 3)
        if len(parts) == 4:
            rows.append({'pid': int(parts[0]), 'ppid': int(parts[1]), 'rss_kib': int(parts[2]), 'command': parts[3]})
    owned = {pid}
    while True:
        grown = owned | {r['pid'] for r in rows if r['ppid'] in owned}
        if grown == owned:
            break
        owned = grown
    selected = [r for r in rows if r['pid'] in owned]
    return {'elapsed_epoch': time.time(), 'processes': selected, 'sum_rss_kib': sum(r['rss_kib'] for r in selected), 'vm_stat': subprocess.check_output(['vm_stat'], text=True, timeout=5)}

def group_alive(group):
    try:
        os.killpg(group, 0)
        return True
    except ProcessLookupError:
        return False

def stop_owned_group(process, grace=20):
    """The group was created by our own start_new_session=True Popen only."""
    notes = {'group': process.pid, 'term_sent': False, 'kill_sent': False}
    if group_alive(process.pid):
        try:
            os.killpg(process.pid, signal.SIGTERM)
            notes['term_sent'] = True
        except ProcessLookupError:
            pass
        deadline = time.monotonic() + grace
        while group_alive(process.pid) and time.monotonic() < deadline:
            process.poll()  # Reap the direct child while descendants receive TERM.
            time.sleep(min(.1, max(0, deadline - time.monotonic())))
        if group_alive(process.pid):
            try:
                os.killpg(process.pid, signal.SIGKILL)
                notes['kill_sent'] = True
            except ProcessLookupError:
                pass
    process.wait(timeout=5)
    settled = time.monotonic() + 2
    while group_alive(process.pid) and time.monotonic() < settled:
        time.sleep(.05)
    notes['direct_child_reaped'] = True
    notes['group_alive_after_cleanup'] = group_alive(process.pid)
    return notes

def run_owned(command, cwd, env, log, sample, timeout, result, interval=15, grace=20):
    """Production build and sleeper checks share this lifecycle boundary."""
    started = time.monotonic()
    process = None
    def terminate(signum, frame):
        raise SystemExit('Received termination signal ' + str(signum))
    previous_term = signal.signal(signal.SIGTERM, terminate)
    result.update(timed_out=False, interrupted=False, error=None, command=command)
    try:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        result['owned_pid'] = process.pid
        while process.poll() is None:
            sample(process.pid, time.monotonic() - started)
            if time.monotonic() - started > timeout:
                result['timed_out'] = True
                break
            try:
                process.wait(timeout=min(interval, max(.01, timeout - (time.monotonic() - started))))
            except subprocess.TimeoutExpired:
                pass
    except BaseException as exc:
        result['interrupted'] = isinstance(exc, (KeyboardInterrupt, SystemExit))
        result['error'] = {'type': type(exc).__name__, 'message': str(exc)}
        raise
    finally:
        # Ignore a repeated Ctrl-C while performing bounded cleanup, then restore it.
        previous = signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        try:
            if process is not None:
                result['cleanup'] = stop_owned_group(process, grace=grace)
                result['exit_code'] = process.returncode
                if result['cleanup']['group_alive_after_cleanup']:
                    raise RuntimeError('Owned process group still exists after bounded cleanup')
        except BaseException as cleanup_error:
            result['cleanup_error'] = {'type': type(cleanup_error).__name__, 'message': str(cleanup_error)}
            raise
        finally:
            signal.signal(signal.SIGINT, previous)
            signal.signal(signal.SIGTERM, previous_term)
            result['wall_seconds'] = time.monotonic() - started

def build(args):
    source_checks(approved=True)
    target = Path(args.target).resolve()
    if target != ROOT / 'target' or not args.lease:
        raise SystemExit('Explicit root-approved target and lease required')
    command = ['cargo', 'build', '--manifest-path', str(SOURCE / 'Cargo.toml'), '-p', 'nvwa-studio', '--lib', '--target', 'wasm32-unknown-unknown', '--profile', 'web-size', '--locked', '--offline']
    env = os.environ.copy()
    # Reject hidden compiler overrides that would make this a different experiment.
    for name in ('RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER'):
        if env.get(name):
            raise SystemExit('Unexpected compiler override: ' + name)
    env.update(CARGO_TARGET_DIR=str(target), CARGO_BUILD_JOBS=str(args.jobs))
    versions = {name: subprocess.check_output(cmd, cwd=SOURCE, text=True).strip() for name, cmd in [('rustc', ['rustc', '--version', '--verbose']), ('cargo', ['cargo', '--version']), ('wasm_bindgen', [str(TOOL), '--version'])]}
    metadata = {'lease': args.lease, 'command': command, 'target': str(target), 'jobs': args.jobs, 'timeout_seconds': args.timeout, 'versions': versions}
    metadata['primary_checkout'] = str(ROOT)
    save('build-start.json', metadata)
    try:
        with (EVIDENCE / 'build.log').open('w') as log, (EVIDENCE / 'memory.jsonl').open('w') as memory:
            def capture(pid, elapsed):
                observation = descendants_snapshot(pid)
                observation['elapsed_seconds'] = elapsed
                memory.write(json.dumps(observation) + '\n')
                memory.flush()
            run_owned(['/usr/bin/time', '-l'] + command, SOURCE, env, log, capture, args.timeout, metadata)
    except BaseException as exc:
        metadata.setdefault('error', {'type': type(exc).__name__, 'message': str(exc)})
        raise
    finally:
        try:
            source_checks(approved=True)
            metadata['freeze_after_verified'] = True
        except BaseException as freeze_error:
            metadata['freeze_after_verified'] = False
            metadata['freeze_error'] = {'type': type(freeze_error).__name__, 'message': str(freeze_error)}
            raise
        finally:
            save('build.json', metadata)
    print(json.dumps(metadata, indent=2))
    if metadata.get('exit_code') != 0 or metadata.get('timed_out'):
        raise SystemExit(1)

def gzip_file(path):
    out = io.BytesIO()
    with gzip.GzipFile(filename='', mode='wb', fileobj=out, compresslevel=9, mtime=0) as encoder:
        encoder.write(path.read_bytes())
    path.with_name(path.name + '.gz').write_bytes(out.getvalue())

def manifest(bundle):
    records = []
    for p in sorted(bundle.rglob('*')):
        if not p.is_file() or p.suffix == '.gz' or p.name in ('size-report.json', 'manifest.json'):
            continue
        item = {'path': str(p.relative_to(bundle)), 'decoded': digest(p)}
        encoded = p.with_name(p.name + '.gz')
        if encoded.exists():
            with gzip.open(encoded, 'rb') as stream:
                h = hashlib.sha256()
                size = 0
                for block in iter(lambda: stream.read(1 << 20), b''):
                    h.update(block)
                    size += len(block)
            if {'bytes': size, 'sha256': h.hexdigest()} != item['decoded']:
                raise SystemExit('gzip identity mismatch: ' + item['path'])
            item['encoded'] = digest(encoded)
            item['content_encoding'] = 'gzip'
        records.append(item)
    lookup = {r['path']: r for r in records}
    def transmitted(name):
        return lookup[name].get('encoded', lookup[name]['decoded'])['bytes']
    return {'files': records, 'first_screen_paths': FIRST_SCREEN, 'first_screen_encoded_bytes': sum(transmitted(n) for n in FIRST_SCREEN), 'player_encoded_bytes': sum(transmitted(n) for n in FIRST_SCREEN + ['works/m1-sequence.nvwa.json']), 'gzip_identity_verified': True, 'http_measurement': 'NOT-RUN; actual root-owned network body measurement required'}

def package(_):
    source_checks(approved=True)
    completed = load('build.json')
    if completed.get('exit_code') != 0 or completed.get('timed_out') or completed.get('error') or completed.get('cleanup_error') or not completed.get('freeze_after_verified') or completed.get('cleanup', {}).get('group_alive_after_cleanup', True):
        raise SystemExit('Successful bounded build required')
    if CANDIDATE.exists():
        raise SystemExit('Candidate exists; refusing overwrite')
    CANDIDATE.mkdir(parents=True)
    wasm = Path(completed['target']) / 'wasm32-unknown-unknown/web-size/nvwa_studio.wasm'
    save('pre-bindgen-wasm.json', digest(wasm))
    subprocess.run([str(TOOL), '--target', 'web', '--out-dir', str(CANDIDATE), str(wasm)], check=True)
    for source, name in STATIC.items():
        path = CANDIDATE / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SOURCE / source, path)
    # Carry the exact exchange fixture, if supplied in the frozen accepted bundle.
    exchange = BASELINE / 'web/works/exchanged.nvwa.json'
    if exchange.exists():
        shutil.copy2(exchange, CANDIDATE / 'works/exchanged.nvwa.json')
    # Preserve A's per-resource encoding policy; compression must not be a second variable.
    for p in sorted(CANDIDATE.rglob('*')):
        if p.is_file():
            accepted = BASELINE / 'web' / p.relative_to(CANDIDATE)
            accepted_gzip = accepted.with_name(accepted.name + '.gz')
            if accepted_gzip.exists():
                if p.read_bytes() == accepted.read_bytes():
                    shutil.copy2(accepted_gzip, p.with_name(p.name + '.gz'))
                else:
                    gzip_file(p)
    a, b = manifest(BASELINE / 'web'), manifest(CANDIDATE)
    save('baseline-manifest.json', a)
    save('candidate-manifest.json', b)
    for src, dest in STATIC.items():
        if digest(CANDIDATE / dest) != digest(BASELINE / 'web' / dest):
            raise SystemExit('Accepted static input differs: ' + dest)
    source_checks(approved=True)
    improvement = 1 - b['first_screen_encoded_bytes'] / a['first_screen_encoded_bytes']
    save('comparison.json', {'A_first_screen_encoded_bytes': a['first_screen_encoded_bytes'], 'B_first_screen_encoded_bytes': b['first_screen_encoded_bytes'], 'improvement_fraction': improvement, 'size_gate_10_percent': improvement >= .10, 'B_under_30MB_decimal': b['first_screen_encoded_bytes'] <= 30_000_000, 'verdict': 'INCONCLUSIVE pending root actual functionality/cadence measurements'})
    save('artifact-freeze.json', {'baseline': tree(BASELINE), 'candidate': tree(CANDIDATE)})
    print(json.dumps(load('comparison.json'), indent=2))

def audit_http(args):
    """Root-invoked wire-body audit; urllib deliberately does not decompress gzip."""
    bundle = Path(args.bundle).resolve()
    records = []
    for name in FIRST_SCREEN + ['works/m1-sequence.nvwa.json']:
        req = urllib.request.Request(args.url.rstrip('/') + '/' + name, headers={'Accept-Encoding': 'gzip', 'Cache-Control': 'no-cache', 'User-Agent': 'Nvwa-M1.1-Audit/1'})
        with urllib.request.urlopen(req, timeout=120) as response:
            body = response.read()
            encoding = response.headers.get('Content-Encoding')
            decoded = gzip.decompress(body) if encoding == 'gzip' else body
            if hashlib.sha256(decoded).hexdigest() != digest(bundle / name)['sha256']:
                raise SystemExit('HTTP decoded hash mismatch: ' + name)
            expected = bundle / (name + '.gz') if encoding == 'gzip' else bundle / name
            if hashlib.sha256(body).hexdigest() != digest(expected)['sha256']:
                raise SystemExit('HTTP encoded hash mismatch: ' + name)
            records.append({'path': name, 'content_encoding': encoding or 'identity', 'content_length': response.headers.get('Content-Length'), 'received_body_bytes': len(body), 'encoded_sha256': hashlib.sha256(body).hexdigest(), 'decoded_sha256': hashlib.sha256(decoded).hexdigest()})
    output = {'url': args.url, 'files': records, 'first_screen_received_body_bytes': sum(r['received_body_bytes'] for r in records if r['path'] in FIRST_SCREEN), 'player_received_body_bytes': sum(r['received_body_bytes'] for r in records), 'browser_download': 'NOT-RUN; this audit is explicit HTTP requests, not browser request inventory'}
    Path(args.output).write_text(json.dumps(output, indent=2, sort_keys=True) + '\n')
    print(json.dumps(output, indent=2))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ('prepare', 'package'):
        sub.add_parser(action)
    sub.add_parser('verify').add_argument('--approved-profile', action='store_true')
    b = sub.add_parser('build')
    b.add_argument('--target', required=True)
    b.add_argument('--lease', required=True)
    b.add_argument('--jobs', type=int, choices=(1, 2), default=1)
    b.add_argument('--timeout', type=int, default=2700)
    h = sub.add_parser('audit-http')
    h.add_argument('--url', required=True)
    h.add_argument('--bundle', required=True)
    h.add_argument('--output', required=True)
    args = parser.parse_args()
    if args.action == 'verify':
        source_checks(args.approved_profile)
    else:
        {'prepare': prepare, 'build': build, 'package': package, 'audit-http': audit_http}[args.action](args)

if __name__ == '__main__':
    main()
