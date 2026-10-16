#!/usr/bin/env python3
"""Stage the already-built Web diagnostic with an explicitly supplied pinned tool."""
from pathlib import Path
import argparse
import hashlib
import os
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[3]
PROBE = Path(__file__).resolve().parent
PINNED_WASM_BINDGEN = '0.2.129'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wasm-bindgen', type=Path, required=True,
                        help='existing executable wasm-bindgen 0.2.129; never installed or downloaded')
    parser.add_argument('--wasm', type=Path,
                        default=ROOT / '.work/runtime-pose-build/wasm32-unknown-unknown/debug/nvwa_runtime_pose_probe.wasm',
                        help='already-built probe Cargo Wasm artifact')
    parser.add_argument('--stage', type=Path, default=ROOT / '.work/runtime-pose-web',
                        help='owned static-site output directory')
    args = parser.parse_args()
    tool = args.wasm_bindgen.resolve()
    wasm = args.wasm.resolve()
    stage = args.stage.resolve()
    if not tool.is_file() or not os.access(tool, os.X_OK):
        parser.error('existing executable wasm-bindgen tool not found; supply --wasm-bindgen; no installation is attempted')
    try:
        version = subprocess.run([str(tool), '--version'], capture_output=True, text=True, check=False)
    except OSError:
        parser.error('could not execute supplied wasm-bindgen; no installation is attempted')
    if version.returncode != 0 or version.stdout.strip() != 'wasm-bindgen ' + PINNED_WASM_BINDGEN:
        parser.error('supplied wasm-bindgen must report exactly wasm-bindgen ' + PINNED_WASM_BINDGEN)
    if not wasm.is_file():
        parser.error('already-built probe Wasm artifact not found; supply --wasm')
    stage.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(tool), '--target', 'web', '--out-dir', str(stage), str(wasm)], check=True)
    for source, relative in [
        (ROOT / 'experiments/48-genuine-fixture-work/artifacts/genuine44-calibrated47.nvwa.json', 'works/genuine44-calibrated47.nvwa.json'),
        (ROOT / 'experiments/48-genuine-fixture-work/artifacts/assets/generated/genuine44-calibrated47.glb', 'assets/generated/genuine44-calibrated47.glb')]:
        target = stage / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if hashlib.sha256(source.read_bytes()).digest() != hashlib.sha256(target.read_bytes()).digest():
            raise SystemExit('staged source bytes differ: ' + relative)
    shutil.copy2(PROBE / 'index.html', stage / 'index.html')
    print(stage)


if __name__ == '__main__':
    main()
