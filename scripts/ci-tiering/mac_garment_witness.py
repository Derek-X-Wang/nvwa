#!/usr/bin/env python3
"""Retain one actual native Mac source2 frame for the original garment controls."""
import argparse
import gzip
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


EXPECTED = {"torso_length": 1.0, "jaw_drop": 0.0,
            "clip_id": "b1_arm_rehearsal_v1", "seconds": 2.0, "k": 16}


def capture(binary, asset_root, frame):
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise ValueError('actual Darwin arm64 runner required for Mac garment witness')
    if not asset_root.is_dir() or not binary.is_file() or frame.exists():
        raise ValueError('missing native binary/assets or preexisting witness frame')
    env = os.environ.copy()
    env['B1_60_ASSET_ROOT'] = str(asset_root.resolve())
    records = []
    with subprocess.Popen([str(binary.resolve()), '--garment-witness-only'],
                          stdout=subprocess.PIPE, text=True, env=env) as child:
        for line in child.stdout:
            if not line.startswith('B1_60 '):
                continue
            records.append(json.loads(line[6:]))
            if len(records) > 2:
                child.terminate()
                raise ValueError('extra native witness records')
        if child.wait() != 0:
            raise ValueError('native witness producer failed')
    if (len(records) != 2 or records[0].get('kind') != 'matrix'
            or records[0].get('request') != EXPECTED
            or not isinstance(records[0].get('snapshot'), dict)
            or records[1] != {"kind": "witness-complete", "samples": 1}):
        raise ValueError('missing, incomplete or misbound native witness')
    with gzip.open(frame, 'xt') as out:
        json.dump(records[0], out, allow_nan=False)
    print('Captured one actual Darwin arm64 source2 frame; original Mac garment controls follow.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--binary', required=True, type=Path)
    parser.add_argument('--asset-root', required=True, type=Path)
    parser.add_argument('--frame', required=True, type=Path)
    args = parser.parse_args()
    try:
        capture(args.binary, args.asset_root, args.frame)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(f'Mac garment witness failed: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
