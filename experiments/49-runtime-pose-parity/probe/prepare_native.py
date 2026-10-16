#!/usr/bin/env python3
"""Package the already-built diagnostic. Does not build or launch any app."""
from pathlib import Path
import json
import hashlib
import tempfile
import plistlib
import shlex
import shutil

ROOT = Path(__file__).resolve().parents[3]
PROBE = Path(__file__).resolve().parent
BINARY = ROOT / '.work/runtime-pose-build/debug/nvwa-runtime-pose-probe'
if not BINARY.is_file():
    raise SystemExit('diagnostic binary missing')
APP = ROOT / '.work/runtime-pose-native/NvwaPoseProbe.app'
MACOS = APP / 'Contents/MacOS'
MACOS.mkdir(parents=True, exist_ok=True)
RESULTS = PROBE / 'results'
RESULTS.mkdir(exist_ok=True)
(ROOT / '.work/runtime-pose-logs').mkdir(parents=True, exist_ok=True)
shutil.copy2(BINARY, MACOS / 'probe-bin')
STAGE = Path(tempfile.mkdtemp(prefix='nvwa-pose-native-', dir='/tmp'))
inputs = [('experiments/48-genuine-fixture-work/artifacts/genuine44-calibrated47.nvwa.json', 'genuine.nvwa.json'),
          ('experiments/48-genuine-fixture-work/artifacts/assets/generated/genuine44-calibrated47.glb', 'assets/generated/genuine44-calibrated47.glb')]
staged = {}
for relative, target_relative in inputs:
    source, target = ROOT / relative, STAGE / target_relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    original = hashlib.sha256(source.read_bytes()).hexdigest()
    if hashlib.sha256(target.read_bytes()).hexdigest() != original:
        raise SystemExit('staged source bytes differ: '+relative)
    staged[relative] = original
(APP.parent / 'staging.json').write_text(json.dumps({'stage': str(STAGE), 'source_sha256': staged}, indent=2)+'\n')
q = lambda value: shlex.quote(str(value))
launcher = MACOS / 'NvwaPoseProbe'
launcher.write_text('#!/bin/sh\n'
    + 'export NVWA_ASSET_ROOT=' + q(STAGE / 'assets') + '\n'
    + 'export NVWA_POSE_OUTPUT=' + q(RESULTS / 'native.json') + '\n'
    + q(MACOS / 'probe-bin') + ' --work '
    + q(STAGE / 'genuine.nvwa.json')
    + ' > ' + q(ROOT / '.work/runtime-pose-logs/native.log') + ' 2>&1\n'
    + 'probe_exit=$?\nprintf \'%s\\n\' \"$probe_exit\" > ' + q(ROOT / '.work/runtime-pose-logs/native-exit-code.txt') + '\nexit \"$probe_exit\"\n')
launcher.chmod(0o755)
with (APP / 'Contents/Info.plist').open('wb') as file:
    plistlib.dump({'CFBundleIdentifier': 'dev.nvwa.pose-probe',
                  'CFBundleName': 'Nvwa Runtime Pose Probe',
                  'CFBundleExecutable': 'NvwaPoseProbe',
                  'CFBundlePackageType': 'APPL',
                  'CFBundleVersion': '1'}, file)
print(APP)
