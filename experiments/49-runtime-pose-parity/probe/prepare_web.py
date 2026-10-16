#!/usr/bin/env python3
"""Stage the already-built Web diagnostic using the existing pinned tool."""
from pathlib import Path
import hashlib
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[3]
PROBE = Path(__file__).resolve().parent
TOOL = Path('/Users/derekxwang/Development/incubator/Nvwa/nvwa/.tools/wasm-bindgen/wasm-bindgen-0.2.129-aarch64-apple-darwin/wasm-bindgen')
WASM = ROOT / '.work/runtime-pose-build/wasm32-unknown-unknown/debug/nvwa_runtime_pose_probe.wasm'
STAGE = ROOT / '.work/runtime-pose-web'
STAGE.mkdir(exist_ok=True)
subprocess.run([str(TOOL), '--target', 'web', '--out-dir', str(STAGE), str(WASM)], check=True)
for source, relative in [
    (ROOT / 'experiments/48-genuine-fixture-work/artifacts/genuine44-calibrated47.nvwa.json', 'works/genuine44-calibrated47.nvwa.json'),
    (ROOT / 'experiments/48-genuine-fixture-work/artifacts/assets/generated/genuine44-calibrated47.glb', 'assets/generated/genuine44-calibrated47.glb')]:
    target = STAGE / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    if hashlib.sha256(source.read_bytes()).digest() != hashlib.sha256(target.read_bytes()).digest():
        raise SystemExit('staged source bytes differ: '+relative)
shutil.copy2(PROBE / 'index.html', STAGE / 'index.html')
print(STAGE)
