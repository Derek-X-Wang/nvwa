#!/usr/bin/env python3
"""Package a separate default-fixture failure control; do not launch it."""
from pathlib import Path
import plistlib
import shlex
import shutil

ROOT = Path(__file__).resolve().parents[3]
PROBE = Path(__file__).resolve().parent
BINARY = ROOT / '.work/runtime-pose-build/debug/nvwa-runtime-pose-probe'
if not BINARY.is_file():
    raise SystemExit('diagnostic binary missing')
APP = ROOT / '.work/runtime-pose-native/NvwaPoseNegative.app'
MACOS = APP / 'Contents/MacOS'
MACOS.mkdir(parents=True, exist_ok=True)
(PROBE / 'results').mkdir(exist_ok=True)
(ROOT / '.work/runtime-pose-logs').mkdir(parents=True, exist_ok=True)
shutil.copy2(BINARY, MACOS / 'probe-bin')
q = lambda value: shlex.quote(str(value))
launcher = MACOS / 'NvwaPoseNegative'
launcher.write_text('#!/bin/sh\n'
    + 'export NVWA_ASSET_ROOT=' + q(ROOT / 'assets') + '\n'
    + 'export NVWA_POSE_OUTPUT=' + q(PROBE / 'results/native-negative.json') + '\n'
    + q(MACOS / 'probe-bin')
    + ' > ' + q(ROOT / '.work/runtime-pose-logs/native-negative.log') + ' 2>&1\n'
    + 'probe_exit=$?\nprintf \'%s\\n\' "$probe_exit" > '
    + q(ROOT / '.work/runtime-pose-logs/native-negative-exit-code.txt') + '\nexit "$probe_exit"\n')
launcher.chmod(0o755)
with (APP / 'Contents/Info.plist').open('wb') as file:
    plistlib.dump({'CFBundleIdentifier': 'dev.nvwa.pose-probe-negative',
                  'CFBundleName': 'Nvwa Runtime Pose Negative',
                  'CFBundleExecutable': 'NvwaPoseNegative',
                  'CFBundlePackageType': 'APPL', 'CFBundleVersion': '1'}, file)
print(APP)
