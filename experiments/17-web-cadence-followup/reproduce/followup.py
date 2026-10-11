#!/usr/bin/env python3
"""Frozen-bundle identity, finite collection gate, and bounded exact-owner server lifecycle."""
import argparse
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
REPO = EXPERIMENT.parent.parent
PRIMARY = Path(os.environ['NVWA_PRIMARY_CHECKOUT']).resolve() if os.environ.get('NVWA_PRIMARY_CHECKOUT') else Path(subprocess.check_output(['git','rev-parse','--path-format=absolute','--git-common-dir'],cwd=REPO,text=True).strip()).parent
RAW = REPO / '.work/perf27/raw'
OLD = REPO / 'experiments/16-web-build-ab/evidence'
ORDER = ['A1', 'B1', 'B2', 'A2', 'A3', 'B3', 'B4', 'A4', 'A5', 'B5']
ATTEMPTS = [{'label':label,'workload':workload} for label in ORDER for workload in ('idle','finite')]
BUNDLES = {'A': PRIMARY / '.work/m1-1/baseline/web', 'B': PRIMARY / '.work/m1-1/web-size/web'}
PRODUCT = ['/index.html', '/nvwa_studio.js', '/nvwa_studio_bg.wasm', '/assets/fixtures/nvwa-humanoid.glb']
WORK = '/works/m1-sequence.nvwa.json'

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')

def digest(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def inventory(root):
    return {str(p.relative_to(root)): digest(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file()}

def seals(output):
    names = ['PROTOCOL.md','COLLECTION.md','followup.py','server.py','check-followup.py']
    save(output, {n:digest((HERE/n).read_bytes()) for n in names})

def attempt(label, workload):
    path = RAW / 'attempt-ledger.jsonl'
    previous = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    expected = ATTEMPTS[len(previous)] if len(previous) < len(ATTEMPTS) else None
    if expected != {'label':label,'workload':workload}:
        raise SystemExit('Attempt must follow frozen order; no replacement/additional attempt')
    row = {'ordinal':len(previous)+1,'label':label,'workload':workload,'epoch_seconds':time.time(),'monotonic_seconds':time.monotonic()}
    RAW.mkdir(parents=True,exist_ok=True)
    with path.open('a') as stream:
        stream.write(json.dumps(row,sort_keys=True)+'\n'); stream.flush(); os.fsync(stream.fileno())
    print(json.dumps(row))

def cadence_passes(a, b):
    return b <= a * 1.1

def ledger_checks(ledger):
    ordered = [{k:r.get(k) for k in ('label','workload')} for r in ledger] == ATTEMPTS
    chronological = all(a.get('epoch_seconds',0) < b.get('epoch_seconds',0) and a.get('monotonic_seconds',0) < b.get('monotonic_seconds',0) for a,b in zip(ledger,ledger[1:]))
    numbered = [r.get('ordinal') for r in ledger] == list(range(1,21))
    return ordered and chronological and numbered

def endpoint_checks(dom):
    failures = []
    if dom.get('visibility') != 'visible':
        failures.append('document visibility unavailable or not visible')
    if dom.get('focus') is not True:
        failures.append('document focus unavailable or not focused')
    if dom.get('canvas') != {'width':1280,'height':720}:
        failures.append('canvas dimensions')
    if dom.get('browser_visible') is not True:
        failures.append('browser not visibly presented or observation unavailable')
    return failures

def pair_result(a, b, valid):
    pair = {'valid':valid,'passes':False}
    if all(isinstance(v,(int,float)) and math.isfinite(v) and v > 0 for v in (a,b)):
        metric_passes = cadence_passes(a,b)
        pair.update(A_p95_ms=a,B_p95_ms=b,change_percent=100*(b/a-1),descriptive_cadence_within_10_percent=metric_passes)
        pair['passes'] = valid and metric_passes
    return pair

def identity(output):
    manifests = {a: json.loads((OLD / ('baseline-manifest.json' if a == 'A' else 'candidate-manifest.json')).read_text()) for a in BUNDLES}
    trees = {a: inventory(p) for a, p in BUNDLES.items()}
    failures = []
    for arm, manifest in manifests.items():
        for row in manifest['files']:
            name = row['path']
            if trees[arm].get(name) != row['decoded']:
                failures.append(f'{arm}:{name}:decoded')
            if 'encoded' in row:
                if trees[arm].get(name + '.gz') != row['encoded']:
                    failures.append(f'{arm}:{name}:encoded')
                if gzip.decompress((BUNDLES[arm] / (name + '.gz')).read_bytes()) != (BUNDLES[arm] / name).read_bytes():
                    failures.append(f'{arm}:{name}:gzip pairing')
    generated = {'nvwa_studio.js', 'nvwa_studio.js.gz', 'nvwa_studio_bg.wasm', 'nvwa_studio_bg.wasm.gz', 'nvwa_studio.d.ts', 'nvwa_studio_bg.wasm.d.ts', 'size-report.json'}
    static = {n: trees['A'].get(n) == trees['B'].get(n) for n in set(trees['A']) | set(trees['B']) if n not in generated}
    failures.extend('static:' + n for n, equal in static.items() if not equal)
    freeze = json.loads((OLD / 'freeze-before.json').read_text())
    source = {n: digest(subprocess.check_output(['git', 'show', freeze['source_head'] + ':' + n], cwd=REPO)) for n in freeze['input_paths']}
    if source != freeze['source']:
        failures.append('frozen source manifest')
    current = {n: digest((REPO / n).read_bytes()) for n in freeze['input_paths'] if (REPO / n).is_file()}
    result = {'bundles': trees, 'static_equality': static, 'frozen_source': source, 'source_base': freeze['source_head'], 'current_worker_checkout_source': current, 'failures': failures, 'status': 'PASS' if not failures else 'FAIL', 'paths': {a: str(p) for a, p in BUNDLES.items()}}
    save(output, result)
    print(json.dumps({'status': result['status'], 'failures': failures}))
    return not failures

def owner(pid):
    result = subprocess.run(['ps', '-p', str(pid), '-o', 'pid=,pgid=,lstart=,command='], text=True, capture_output=True)
    if result.returncode == 0:
        return result.stdout.strip()
    # macOS ps reports status1 with empty stdout/stderr when no PID matches.
    if result.returncode == 1 and not result.stdout.strip() and not result.stderr.strip():
        return ''
    raise RuntimeError(f'ps ownership observation failed: status{result.returncode}: {result.stderr.strip()}')

def reclaim_spawned(process, grace=3):
    """A live unreaped Popen child cannot have its PID reused; bound metadata-failure cleanup."""
    running = process.poll() is None
    if running:
        if os.getpgid(process.pid) != process.pid:
            raise RuntimeError('New owned child has unexpected process group; no signal sent')
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=grace)
    else:
        process.wait(timeout=grace)
    return {'pid': process.pid, 'direct_child_reaped': True, 'exit_code': process.returncode, 'group_absent': group_absent(process.pid)}

def spawn_with_record(command, stream, state, lease, lifetime=120):
    process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
    record = {'pid': process.pid, 'lease': lease, 'command': command, 'automatic_timeout_seconds': lifetime}
    try:
        time.sleep(.2)
        if process.poll() is not None:
            raise RuntimeError(f'Owned server failed at startup: exit{process.returncode}')
        record['process_identity'] = owner(process.pid)
        if not record['process_identity']:
            raise RuntimeError('Owned server disappeared during identity observation')
        record['status'] = 'STARTED'
        save(state, record)
        return record
    except BaseException as exc:
        record['status'] = 'FAILED_START'
        record['error'] = f'{type(exc).__name__}: {exc}'
        record['cleanup'] = reclaim_spawned(process)
        if not state.exists():
            save(state, record)
        else:
            save(state.with_name(state.stem + '-startup-error.json'), record)
        raise

def stop_owned(record, grace=3):
    """Called by actual server stop and offline lifecycle checks; never kill unmatched PIDs."""
    pid = record['pid']
    observed = owner(pid)
    if not observed:
        return {'pid': pid, 'already_absent': True, 'group_absent': group_absent(pid)}
    if observed != record['process_identity'] or os.getpgid(pid) != pid:
        raise RuntimeError('Owned server process identity mismatch; no signal sent')
    os.killpg(pid, signal.SIGTERM)
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline and not group_absent(pid):
        time.sleep(0.05)
    escalated = not group_absent(pid)
    if escalated:
        os.killpg(pid, signal.SIGKILL)
        deadline = time.monotonic() + grace
        while time.monotonic() < deadline and not group_absent(pid):
            time.sleep(0.05)
    return {'pid': pid, 'identity_matched': True, 'term_sent': True, 'kill_escalated': escalated, 'group_absent': group_absent(pid)}

def group_absent(pgid):
    # ps excludes zombie rows, whose kernel cleanup cannot run a server or renderer.
    lines = subprocess.check_output(['ps', '-axo', 'pgid=,stat='], text=True).splitlines()
    return not any(int(line.split()[0]) == pgid and not line.split()[1].startswith('Z') for line in lines if line.split())

def start(label, lease):
    if label not in ORDER or not lease:
        raise SystemExit('Expected planned label and root GPU lease')
    RAW.mkdir(parents=True, exist_ok=True)
    state = RAW / f'{label}-owner.json'
    if state.exists() or (RAW / f'{label}-requests.jsonl').exists():
        raise SystemExit('Run already attempted; replacement forbidden')
    command = [sys.executable, '-B', str(HERE / 'server.py'), '--bundle', str(BUNDLES[label[0]]), '--port', '9201', '--arm', label[0], '--log', str(RAW / f'{label}-requests.jsonl')]
    with (RAW / f'{label}-server.log').open('x') as stream:
        record = spawn_with_record(command, stream, state, lease)
    print(json.dumps(record))

def requests(label, workload):
    rows = [json.loads(l) for l in (RAW / f'{label}-requests.jsonl').read_text().splitlines() if l]
    groups = []
    for r in rows:
        if r['client_kind'] != 'browser-candidate':
            continue
        if r['path'] in ('/', '/index.html'):
            groups.append([])
        if not groups:
            raise ValueError('Resource before document')
        groups[-1].append(r)
    if len(groups) != 2:
        raise ValueError(f'Expected 2 navigations, observed {len(groups)}')
    selected = groups[0 if workload == 'idle' else 1]
    expected = PRODUCT + ([WORK] if workload == 'finite' else [])
    manifest = json.loads((OLD / ('baseline-manifest.json' if label[0] == 'A' else 'candidate-manifest.json')).read_text())
    specs = {'/' + r['path']: r for r in manifest['files']}
    errors = []
    for name in expected:
        found = [r for r in selected if ('/index.html' if r['path'] == '/' else r['path']) == name]
        if len(found) != 1:
            errors.append(f'{name}:count{len(found)}')
            continue
        r = found[0]
        if not (r['status'] == 200 and not r['transfer_error'] and r['content_encoding'] == 'gzip' and r['cache_control'] == 'no-store' and r['body_bytes_written'] == specs[name]['encoded']['bytes'] == int(r['content_length'])):
            errors.append(f'{name}:response invariant')
    if workload == 'idle' and any(r['path'] == WORK for r in selected):
        errors.append('idle unexpectedly requested Work')
    target = '/?benchmark=1' + ('&player=1&work=works%2Fm1-sequence.nvwa.json' if workload == 'finite' else '')
    if selected[0]['request_target'] != target:
        errors.append('document target')
    ua = list({r['user_agent'] for r in selected})
    if len(ua) != 1 or 'Chrome/155.0.0.0' not in ua[0]:
        errors.append('browser version/UA')
    return {'rows': selected, 'errors': errors, 'user_agents': ua, 'first_screen_bytes': sum(r['body_bytes_written'] for r in selected if ('/index.html' if r['path'] == '/' else r['path']) in PRODUCT)}

def runtime_checks(runtime, workload):
    expected = {'ready': True, 'error': None, 'timeout': False, 'capture_callback': True, 'joints': 18, 'skins': 9, 'meshes': 9, 'morph_weights': 4, 'players': 1, 'morph_nodes': 1, 'frame_sample_count': 600, 'frame_timing_kind': 'main_loop_cadence_not_gpu_timestamp', 'physical_window': {'width': 1280, 'height': 720, 'scale_factor': 1.0}, 'mode': 'studio' if workload == 'idle' else 'player', 'timeline_count': 1 if workload == 'idle' else 3, 'document_revision': 0 if workload == 'idle' else 1, 'playing': workload == 'idle', 'completed': workload == 'finite', 'clip': 'idle' if workload == 'idle' else 'turn', 'interaction_busy': False}
    if workload == 'finite':
        expected['animation_seconds'] = 9.0
    failures = [k for k, v in expected.items() if runtime.get(k) != v]
    if runtime.get('gpu', {}).get('backend') != 'BrowserWebGpu':
        failures.append('gpu.backend')
    p95 = runtime.get('frame_ms_p95')
    if not isinstance(p95, (float, int)) or not math.isfinite(p95) or p95 <= 0:
        failures.append('frame_ms_p95')
    return failures

def summarize(output):
    results = []
    failures = []
    user_agents = set()
    ledger_path = RAW / 'attempt-ledger.jsonl'
    ledger = [json.loads(line) for line in ledger_path.read_text().splitlines()] if ledger_path.exists() else []
    ledger_valid = ledger_checks(ledger)
    if not ledger_valid:
        failures.append({'attempt_ledger':'incomplete, reordered, or nonchronological'})
    before_path,after_path = [HERE/'evidence'/f'seal-{phase}.json' for phase in ('before','after')]
    before_seal = json.loads(before_path.read_text()) if before_path.exists() else None
    after_seal = json.loads(after_path.read_text()) if after_path.exists() else None
    seal_unchanged = before_seal is not None and before_seal == after_seal
    if not seal_unchanged:
        failures.append({'protocol_script_identity':'changed'})
    for label in ORDER:
        for workload in ('idle', 'finite'):
            row = {'label': label, 'workload': workload, 'errors': []}
            try:
                logs = json.loads((RAW / f'{label}-{workload}-console.json').read_text())
                if len(logs) >= 1000:
                    row['errors'].append('console capture saturated')
                evidence = [r for r in logs if 'NVWA_EVIDENCE ' in r['message']]
                if len(evidence) != 1:
                    raise ValueError(f'Expected 1 runtime report, observed {len(evidence)}')
                runtime, _ = json.JSONDecoder().raw_decode(evidence[0]['message'].split('NVWA_EVIDENCE ', 1)[1])
                row['runtime'] = runtime
                row['errors'].extend(runtime_checks(runtime, workload))
                errors = [r for r in logs if r['level'] == 'error']
                if errors:
                    row['errors'].append('console errors')
                req = requests(label, workload)
                row['requests'] = req
                row['errors'].extend(req['errors'])
                entries = [i for i,r in enumerate(ledger) if r['label'] == label and r['workload'] == workload]
                if len(entries) != 1:
                    row['errors'].append('attempt ledger identity')
                else:
                    position = entries[0]
                    epoch = req['rows'][0]['epoch_seconds']
                    if not (ledger[position]['epoch_seconds'] <= epoch and (position+1 == len(ledger) or epoch < ledger[position+1]['epoch_seconds'])):
                        row['errors'].append('navigation outside chronological attempt interval')
                user_agents.update(req['user_agents'])
                for endpoint in ('before', 'after'):
                    dom = json.loads((RAW / f'{label}-{workload}-{endpoint}-dom.json').read_text())
                    row[endpoint + '_dom'] = dom
                    row['errors'].extend(endpoint + ':' + failure for failure in endpoint_checks(dom))
                if not (RAW / f'{label}-{workload}.png').is_file():
                    row['errors'].append('missing screenshot')
                if not (RAW / f'{label}-{workload}-process-before.txt').is_file() or not (RAW / f'{label}-{workload}-process-after.txt').is_file():
                    row['errors'].append('missing competing workload snapshot')
                cleanup = json.loads((RAW/f'{label}-cleanup.json').read_text())
                if not cleanup['group_absent']:
                    row['errors'].append('owned server cleanup incomplete')
                exceptional = list(RAW.glob(f'{label}-{workload}*error*.json'))
                if exceptional:
                    row['exception_files'] = {p.name:p.read_text() for p in exceptional}
                    row['errors'].append('retained executor exception')
            except (ValueError, OSError, KeyError, TypeError) as exc:
                row['errors'].append(str(exc))
            if row['errors']:
                failures.append({'label': label, 'workload': workload, 'errors': row['errors']})
            results.append(row)
    pairs = []
    for workload in ('idle', 'finite'):
        for i in range(1, 6):
            a, b = [next(r for r in results if r['label'] == f'{arm}{i}' and r['workload'] == workload) for arm in ('A', 'B')]
            av, bv = [r.get('runtime',{}).get('frame_ms_p95') for r in (a,b)]
            pair = {'pair':i,'workload':workload,**pair_result(av,bv,not a['errors'] and not b['errors'])}
            pairs.append(pair)
    identity_before = json.loads((HERE / 'evidence/identity-before.json').read_text())
    identity_after = json.loads((HERE / 'evidence/identity-after.json').read_text())
    unchanged = all(identity_before[k] == identity_after[k] for k in ('bundles', 'static_equality', 'frozen_source')) and not identity_before['failures'] and not identity_after['failures']
    size = 100 * (1 - 18034148 / 20539196)
    eligible = not failures and len(user_agents) == 1 and unchanged and size >= 10 and all(p['passes'] for p in pairs)
    report = {'verdict': 'ELIGIBLE_FOR_INDEPENDENT_REVIEW' if eligible else 'DEFER', 'order': ORDER, 'attempt_ledger':ledger,'attempt_order_valid':ledger_valid,'protocol_script_identity_unchanged':seal_unchanged,'runs': results, 'pairs': pairs, 'failures': failures, 'identity_unchanged': unchanged, 'user_agents': sorted(user_agents), 'size_reduction_percent': size, 'size_passes': size >= 10, 'limits': ['Finite recent600 frames include completed held pose after9s; no motion-only claim', 'Endpoint visibility/focus only; continuous visibility/focus NOT-RUN', 'Cadence is Rust main loop, not GPU/display time', 'Navigation timing, cold cache, browser memory and browser body receipt NOT-RUN', 'Five pairs per workload; no causal or significance claim']}
    save(output, report)
    print(json.dumps({'verdict': report['verdict'], 'pairs': pairs, 'failures': failures, 'identity_unchanged': unchanged}, indent=2))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    for name in ('identity', 'summarize','seal'):
        p = sub.add_parser(name); p.add_argument('--output', type=Path, required=True)
    p = sub.add_parser('start'); p.add_argument('--label', required=True); p.add_argument('--lease', required=True)
    p = sub.add_parser('stop'); p.add_argument('--label', required=True)
    p = sub.add_parser('attempt'); p.add_argument('--label',required=True); p.add_argument('--workload',choices=('idle','finite'),required=True)
    args = parser.parse_args()
    if args.action == 'identity':
        if not identity(args.output): raise SystemExit(1)
    elif args.action == 'summarize': summarize(args.output)
    elif args.action == 'seal': seals(args.output)
    elif args.action == 'attempt': attempt(args.label,args.workload)
    elif args.action == 'start': start(args.label, args.lease)
    else:
        record = json.loads((RAW / f'{args.label}-owner.json').read_text())
        result = stop_owned(record)
        save(RAW / f'{args.label}-cleanup.json', result)
        print(json.dumps(result))
        if not result['group_absent']: raise SystemExit(1)

if __name__ == '__main__':
    main()
