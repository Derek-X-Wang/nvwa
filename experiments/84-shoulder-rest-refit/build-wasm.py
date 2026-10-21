#!/usr/bin/env python3
"""Build the single CPU-only Wasm producer offline and retain its real inputs."""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments/84-shoulder-rest-refit/replay'))
import collect_wasm as capture


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--target-dir', type=Path, required=True)
    parser.add_argument('--bindgen', type=Path, required=True)
    parser.add_argument('--run-id-file', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    before = capture.wasm_build_source_files(ROOT)
    (args.out / 'source-before.json').write_text(json.dumps(before, indent=2) + '\n')
    command = ['cargo', 'build', '--offline', '--locked', '--target',
               'wasm32-unknown-unknown', '--manifest-path',
               'experiments/84-shoulder-rest-refit/wasm-replay/Cargo.toml', '--lib']
    env = os.environ.copy()
    env.update(CARGO_NET_OFFLINE='true', CARGO_BUILD_JOBS='1',
               CARGO_TARGET_DIR=str(args.target_dir.resolve()))
    subprocess.run(command, cwd=ROOT, env=env, check=True)
    bindgen_command = [str(args.bindgen.resolve()),
                       str(args.target_dir.resolve() / 'wasm32-unknown-unknown/debug/nvwa_shoulder_wasm_replay.wasm'),
                       '--target', 'web', '--out-dir', str(args.out.resolve() / 'pkg')]
    subprocess.run(bindgen_command, cwd=ROOT, check=True)
    after = capture.wasm_build_source_files(ROOT)
    (args.out / 'source-after.json').write_text(json.dumps(after, indent=2) + '\n')
    if before != after:
        raise ValueError('Actual frozen compiler inputs changed during build')
    receipt = dict(schema_version=1, kind='nvwa84-completed-cpu-wasm-build-v1',
                   target='wasm32-unknown-unknown', status='PASS_COMPLETED_BUILD',
                   exit_code=0, build_run_id=args.run_id_file.read_text().strip(),
                   source_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                   source_files=before, source_files_sha256=capture.original.inventory_digest(before),
                   toolchain={tool: subprocess.check_output([executable, '--version'], cwd=ROOT, text=True).strip()
                              for tool, executable in [('rustc', 'rustc'), ('cargo', 'cargo'),
                                                       ('wasm_bindgen', str(args.bindgen.resolve()))]},
                   host=dict(system=platform.system(), machine=platform.machine()),
                   command=command, bindgen_command=bindgen_command,
                   artifacts=capture.artifact_files(args.out / 'pkg'))
    (args.out / 'build-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(dict(status=receipt['status'], build_run_id=receipt['build_run_id'],
                          source_files=len(before), artifacts=len(receipt['artifacts']))))


if __name__ == '__main__':
    main()
