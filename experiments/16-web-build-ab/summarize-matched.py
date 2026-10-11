#!/usr/bin/env python3
"""Reconcile root's six matched pairs; never turn median success into a gate pass."""
import argparse
import json
from pathlib import Path
import statistics
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--evidence', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
if args.output.exists():
    raise SystemExit('Refuse to overwrite a prior measurement report')
root = args.evidence.resolve()
rows = []
request_summaries = []
for arm in ('A', 'B'):
    for repetition in (1, 2, 3):
        label = f'{arm}{repetition}'
        requests = [json.loads(line) for line in (root / f'{label}-browser-requests.jsonl').read_text().splitlines()]
        groups = []
        for request in requests:
            if request['client_kind'] != 'browser-candidate':
                continue
            if request['path'] in ('/', '/index.html'):
                groups.append([])
            if not groups:
                raise SystemExit(f'{label}: resource before document')
            groups[-1].append(request)
        if len(groups) != 2:
            raise SystemExit(f'{label}: expected exactly idle then finite navigation')
        for workload, group in zip(('idle', 'finite'), groups):
            if ('player=1' in group[0]['request_target']) != (workload == 'finite'):
                raise SystemExit(f'{label}: wrong workload navigation')
            sliced = root / f'{label}-{workload}-requests.jsonl'
            if sliced.exists():
                raise SystemExit(f'Refuse to overwrite {sliced}')
            sliced.write_text(''.join(json.dumps(item, sort_keys=True) + '\n' for item in group))
            summary_path = root / f'{label}-{workload}-server-summary.json'
            subprocess.run([sys.executable, str(Path(__file__).with_name('summarize-requests.py')),
                            '--log', str(sliced), '--output', str(summary_path)],
                           check=True, stdout=subprocess.DEVNULL)
            summary = json.loads(summary_path.read_text())
            expected = 20539196 if arm == 'A' else 18034148
            if summary['first_screen_body_bytes_written'] != expected:
                raise SystemExit(f'{label}: first-screen sum disagrees with frozen package')
            if workload == 'finite' and summary['player_body_bytes_written'] != expected + 523:
                raise SystemExit(f'{label}: player sum disagrees with frozen Work')
            request_summaries.append({'label': label, 'workload': workload, 'first_screen_body_bytes_written': expected,
                                      'player_body_bytes_written': summary['player_body_bytes_written']})
            logs = json.loads((root / f'{label}-{workload}-console.json').read_text())
            if len(logs) != 1:
                raise SystemExit(f'{label}: expected exactly one runtime report')
            payload = logs[0]['message'].split('NVWA_EVIDENCE ', 1)[1]
            runtime, _ = json.JSONDecoder().raw_decode(payload)
            checks = [runtime['ready'], runtime['error'] is None, not runtime['timeout'], runtime['capture_callback'],
                      runtime['joints'] == 18, runtime['skins'] == 9, runtime['meshes'] == 9,
                      runtime['morph_weights'] == 4, runtime['frame_sample_count'] == 600,
                      runtime['frame_timing_kind'] == 'main_loop_cadence_not_gpu_timestamp',
                      runtime['physical_window'] == {'width': 1280, 'height': 720, 'scale_factor': 1.0},
                      runtime['gpu']['backend'] == 'BrowserWebGpu',
                      runtime['mode'] == ('studio' if workload == 'idle' else 'player'),
                      runtime['timeline_count'] == (1 if workload == 'idle' else 3),
                      runtime['document_revision'] == (0 if workload == 'idle' else 1),
                      runtime['playing'] == (workload == 'idle'), runtime['completed'] == (workload == 'finite')]
            if workload == 'finite':
                checks.append(runtime['animation_seconds'] == 9.0 and runtime['clip'] == 'turn')
            if not all(checks):
                raise SystemExit(f'{label}-{workload}: runtime invariants failed')
            rows.append({'arm': arm, 'repetition': repetition, 'workload': workload, 'runtime': runtime,
                         'console_timestamp': logs[0]['timestamp']})
comparisons = []
violations = []
for workload in ('idle', 'finite'):
    selected = {arm: [r['runtime'] for r in rows if r['arm'] == arm and r['workload'] == workload] for arm in ('A', 'B')}
    pairs = []
    for i, (a, b) in enumerate(zip(selected['A'], selected['B']), 1):
        change = 100 * (b['frame_ms_p95'] / a['frame_ms_p95'] - 1)
        item = {'repetition': i, 'A_p95_ms': a['frame_ms_p95'], 'B_p95_ms': b['frame_ms_p95'], 'change_percent': change}
        pairs.append(item)
        if change > 10:
            violations.append({'workload': workload, **item})
    median = {arm: statistics.median(r['frame_ms_p95'] for r in selected[arm]) for arm in ('A', 'B')}
    comparisons.append({'workload': workload, 'pairs': pairs, 'median_p95_ms': median,
                        'median_change_percent': 100 * (median['B'] / median['A'] - 1)})
report = {'status': 'INCONCLUSIVE' if violations else 'CADENCE_GATE_PASS',
          'default_profile_recommendation': 'DEFER' if violations else 'eligible for independent review',
          'order': ['A1', 'B1', 'B2', 'A2', 'A3', 'B3'],
          'comparison_rule': 'Every matched pair must stay within10%; medians describe the sample and never override pair breaches',
          'size_gate': {'A_first_screen_gzip_bytes': 20539196, 'B_first_screen_gzip_bytes': 18034148,
                        'reduction_percent': 100 * (1 - 18034148 / 20539196), 'passes_10_percent': True},
          'comparisons': comparisons, 'pair_gate_breaches': violations, 'runs': rows,
          'http_summaries': request_summaries,
          'limits': {'cadence': 'Rust main loop, not GPU or display presentation',
                     'startup': 'first_asset_ready_seconds uses Bevy TimeReal since first update; navigation-to-ready NOT-RUN',
                     'browser_receipt': 'NOT-RUN; browser-UA request inventory/server writes; Python body receipts audited separately',
                     'cache': 'Fresh documents/no-store with existing Wasm/driver caches; cold-cache NOT-RUN',
                     'memory': 'Browser/GPU peak NOT-RUN',
                     'finite_window': 'Recent600 frames around15s includes active animation and held completed pose after9s; not motion-only cadence', 'statistical_power': 'Three matched repetitions per workload; variable samples, no causal or significance claim'}}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
print(json.dumps({k: report[k] for k in ('status', 'size_gate', 'comparisons', 'pair_gate_breaches')}, indent=2))
