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
for name in ['mpfb-b1-v1', 'mpfb-b1-v2']:
    shutil.copytree(root / 'assets/characters' / name, resources.parent / 'characters' / name, dirs_exist_ok=True)
b1_notices = contents / 'Resources/licenses/b1'
for name in ['humentity', 'bevy_obj', 'wobj']:
    source = root / 'vendor' / name
    destination = b1_notices / name
    destination.mkdir(parents=True, exist_ok=True)
    for notice in source.glob('LICENSE*'):
        if notice.is_file():
            shutil.copy2(notice, destination / notice.name)
    if (source / 'licenses').is_dir():
        shutil.copytree(source / 'licenses', destination / 'licenses', dirs_exist_ok=True)
font_notices = contents / 'Resources/licenses/fonts'
appearance_source = root / 'assets/appearances/mpfb-b1-cc0-v1'
appearance_notices = contents / 'Resources/licenses/appearance'
appearance_notices.mkdir(parents=True, exist_ok=True)
for name in ['SOURCE.json', 'manifest.json']:
    shutil.copy2(appearance_source / name, appearance_notices / name)
for name in ['licenses', 'provenance']:
    shutil.copytree(appearance_source / name, appearance_notices / name, dirs_exist_ok=True)
v2_appearance = root / 'assets/appearances/mpfb-b1-cc0-v2'
v2_notices = appearance_notices / 'v2'
v2_notices.mkdir(parents=True, exist_ok=True)
for name in ['SOURCE.json', 'manifest.json', 'BASE-BINDING.json']:
    shutil.copy2(v2_appearance / name, v2_notices / name)
for name in ['licenses', 'provenance']:
    shutil.copytree(v2_appearance / name, v2_notices / name, dirs_exist_ok=True)
font_notices.mkdir(parents=True, exist_ok=True)
for name in ['OFL.txt', 'NOTICE.md', 'PROVENANCE.json']:
    shutil.copy2(root / 'assets/fonts' / name, font_notices / name)
component_notices = contents / 'Resources/licenses/craft-ui'
component_notices.mkdir(parents=True, exist_ok=True)
shutil.copy2(root / 'licenses/craft-ui/LICENSE-MIT.txt', component_notices / 'LICENSE-MIT.txt')
works = contents / 'Resources/works'
works.mkdir(parents=True, exist_ok=True)
for name in ['m1-sequence.nvwa.json', 'b1-appearance.nvwa.json', 'b1-character.nvwa.json']:
    shutil.copy2(root / 'examples' / name, works / name)
with (contents / 'Info.plist').open('wb') as file:
    plistlib.dump({'CFBundleExecutable': 'Nvwa', 'CFBundleIdentifier': 'dev.nvwa.studio', 'CFBundleName': 'Nvwa', 'CFBundleDisplayName': 'Nvwa', 'CFBundlePackageType': 'APPL', 'CFBundleShortVersionString': '0.1.0', 'NSHighResolutionCapable': True}, file)
print(contents.parent)
print('Unsigned local build; signing/notarization and other OS distribution are unverified.')
