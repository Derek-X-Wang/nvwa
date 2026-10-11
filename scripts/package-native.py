"""Package the locally built unsigned macOS application with its runtime assets."""
from pathlib import Path
import argparse
import plistlib
import shutil

parser = argparse.ArgumentParser()
parser.add_argument('--profile', choices=['debug', 'release'], default='release')
args = parser.parse_args()
root = Path(__file__).resolve().parent.parent
binary = root / 'target' / args.profile / 'nvwa-studio'
if not binary.is_file():
    raise SystemExit('Build native Studio before packaging')
contents = root / 'dist/Nvwa.app/Contents'
executable = contents / 'MacOS/Nvwa'
executable.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(binary, executable)
resources = contents / 'Resources/assets/fixtures'
resources.mkdir(parents=True, exist_ok=True)
for name in ['nvwa-humanoid.glb', 'LICENSE.txt', 'provenance-manifest.json']:
    shutil.copy2(root / 'assets/fixtures' / name, resources / name)
shutil.copy2(root / 'assets/character.profile.json', resources.parent / 'character.profile.json')
works = contents / 'Resources/works'
works.mkdir(parents=True, exist_ok=True)
shutil.copy2(root / 'examples/m1-sequence.nvwa.json', works / 'm1-sequence.nvwa.json')
with (contents / 'Info.plist').open('wb') as file:
    plistlib.dump({'CFBundleExecutable': 'Nvwa', 'CFBundleIdentifier': 'dev.nvwa.studio', 'CFBundleName': 'Nvwa', 'CFBundleDisplayName': 'Nvwa', 'CFBundlePackageType': 'APPL', 'CFBundleShortVersionString': '0.1.0', 'NSHighResolutionCapable': True}, file)
print(contents.parent)
print('Unsigned local build; signing/notarization and other OS distribution are unverified.')
