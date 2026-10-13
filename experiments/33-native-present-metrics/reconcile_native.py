"""Validate actual callback data without converting readiness into display."""
import argparse
import json
import math
from pathlib import Path

def rows(text):
    result = []
    for line in text.splitlines():
        for prefix in ('NVWA_METAL_PROBE ', 'NVWA_NATIVE_PROBE '):
            if line.startswith(prefix):
                result.append(json.loads(line[len(prefix):]))
    return result

def display_interval(row):
    """Apple Metal host seconds vs measured CA/monotonic bracket, not wall/Instant."""
    ca = row['ca_host_seconds']
    display = row['presented_host_seconds']
    before, after = row['callback_monotonic_before_ns'], row['callback_monotonic_after_ns']
    assert all(math.isfinite(x) for x in (ca, display)) and ca > 0 and display > 0
    assert before > 0 and after >= before
    difference_ns = (display - ca) * 1_000_000_000
    return [before + difference_ns, after + difference_ns]

def reconcile(text, pid):
    data = rows(text)
    assert data and pid > 1
    assert all(row['pid'] == pid for row in data), 'mixed process identities'
    gpu, displays, invalid_gpu, invalid_display = [], [], [], []
    for row in data:
        if row['event'] == 'command_completed':
            start, end = row['gpu_start_host_seconds'], row['gpu_end_host_seconds']
            valid = (row['status_raw'] == 4 and math.isfinite(start) and math.isfinite(end)
                     and start > 0 and end >= start)
            assert row['valid_completed_gpu_span'] == valid, 'raw GPU validity disagreement'
            target = gpu if valid else invalid_gpu
            target.append({**row, 'duration_ms': (end - start) * 1000 if valid else None})
        elif row['event'] == 'drawable_presented_callback':
            time = row['presented_host_seconds']
            valid = math.isfinite(time) and time > 0
            assert row['valid_presented_time'] == valid, 'raw display validity disagreement'
            target = displays if valid else invalid_display
            target.append({**row, 'converted_CLOCK_MONOTONIC_interval_ns': display_interval(row) if valid else None})
    first = min(displays, key=lambda row: row['presented_host_seconds'], default=None)
    return {
        'status': 'PARTIAL', 'pid': pid,
        'first_observed_valid_drawable': first,
        'first_registered_drawable_callback_valid': any(row['index'] == 1 for row in displays),
        'valid_gpu_command_samples': gpu, 'invalid_gpu_command_samples': invalid_gpu,
        'invalid_display_callbacks': invalid_display,
        'gpu_sample_scope': 'Selected actual submitted command buffers; no summing overlapping durations or inference of frame latency',
        'clock_scope': 'Metal/CA system-mach host seconds calibrated per callback to CLOCK_MONOTONIC bracket; wall time and process Instant not subtracted',
        'first_character_pixels': 'NOT-RUN until exact capture hashes and pixel inspection are supplied',
        'fully_cold_OS_Metal_shader_state': 'NOT-RUN',
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument('log', type=Path); p.add_argument('--pid', type=int, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    result = reconcile(a.log.read_text(), a.pid)
    a.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key: result[key] for key in ('status','pid','first_registered_drawable_callback_valid','first_character_pixels')}))
if __name__ == '__main__': main()
