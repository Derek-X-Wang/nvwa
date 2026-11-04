#!/usr/bin/env python3
"""Execute three bounded production-source faults in an owned disposable checkout.

Do not use on a human editing checkout. Each exact source is restored in finally;
the commands still compile and execute the real production-plugin regression.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def digest(value):
    return hashlib.sha256(value).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--disposable-checkout', action='store_true', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    # Match the preceding workspace test feature union. Selecting runtime alone
    # rebuilds a second Bevy graph before the exact semantic witness can run.
    command_prefix = [
        'cargo', 'test', '--workspace', '--lib', '--locked', '--offline',
    ]
    movement_test = 'b1::tests::actual_motion_clock_changes_bones_and_both_uploaded_meshes_without_refit'
    movement_assertion = 'assertion failed: part_position_deltas(&rest, &middle)'
    cases = [
        ('omit-authored-arm-pose', 'crates/nvwa-b1-adapter/src/motion.rs', [
            ('degrees: 45.0 * amplitude,', 'degrees: 0.0 * amplitude,'),
            ('degrees: 75.0 * amplitude,', 'degrees: 0.0 * amplitude,'),
        ], movement_test, movement_assertion),
        ('stale-garment-upload', 'crates/nvwa-runtime/src/b1.rs', [
            ('for (handle, frame) in active.display_meshes.iter().zip(frames) {',
             'for (handle, frame) in active.display_meshes.iter().zip(frames).take(1) {'),
        ], movement_test, movement_assertion),
        ('omit-authored-foot-counterrotation', 'crates/nvwa-b1-adapter/src/motion.rs', [
            ('degrees: -65.0 * amplitude,', 'degrees: 0.0 * amplitude,'),
        ], 'b1::tests::authored_knee_counterrotation_keeps_actual_early_and_full_cycle_feet_above_floor',
         'actual moving foot dips below floor:'),
    ]
    results = []
    for name, relative, replacements, test_name, intended_assertion in cases:
        command = command_prefix + [test_name, '--', '--exact', '--test-threads=1', '--nocapture']
        path = root / relative
        original = path.read_bytes()
        mutated = original.decode()
        for before, after in replacements:
            if mutated.count(before) != 1:
                raise ValueError(f'{name}: source seam must occur exactly once: {before}')
            mutated = mutated.replace(before, after)
        try:
            path.write_text(mutated)
            red = subprocess.run(command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            (out / (name + '-red.log')).write_bytes(red.stdout)
            text = red.stdout.decode(errors='replace')
            witnessed = (
                red.returncode == 101
                and 'running 1 test' in text
                and 'test result: FAILED. 0 passed; 1 failed' in text
                and test_name in text
                and intended_assertion in text
                and 'error[E' not in text
            )
            result = {
                'name': name, 'source': relative, 'before_sha256': digest(original),
                'mutant_sha256': digest(mutated.encode()), 'command': command,
                'red_exit': red.returncode, 'semantic_test_failure': witnessed,
                'intended_assertion': intended_assertion,
            }
        finally:
            path.write_bytes(original)
        if path.read_bytes() != original:
            raise ValueError(f'{name}: restoration failed')
        green = subprocess.run(command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (out / (name + '-restored-green.log')).write_bytes(green.stdout)
        green_text = green.stdout.decode(errors='replace')
        result.update({
            'restored_sha256': digest(path.read_bytes()), 'restored_exit': green.returncode,
            'restored_green': green.returncode == 0 and 'test result: ok. 1 passed; 0 failed' in green_text,
        })
        results.append(result)
        (out / 'summary.json').write_text(json.dumps({'cases': results}, indent=2) + '\n')
        if not result['semantic_test_failure'] or not result['restored_green']:
            raise ValueError(f'{name}: expected semantic red and restored green; inspect retained logs')
    summary = {'passed': True, 'cases': results, 'scope': 'Real Rust production seams; no graphics/GPU',
               'hashes': {p.name: digest(p.read_bytes()) for p in out.glob('*.log')}}
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
