#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
profile="${1:-release}"
case "$profile" in
  release) profile_args=(--release);;
  dev) profile_args=(); profile=debug;;
  *) echo "Usage: bash scripts/build-web.sh [release|dev]" >&2; exit 2;;
esac
tool="${NVWA_WASM_BINDGEN:-.tools/wasm-bindgen/wasm-bindgen-0.2.129-aarch64-apple-darwin/wasm-bindgen}"
if [[ ! -x "$tool" ]]; then
  echo "Run python3 scripts/install-web-tools.py first (or set up wasm-bindgen 0.2.129)." >&2
  exit 1
fi
CARGO_BUILD_JOBS="${CARGO_BUILD_JOBS:-3}" cargo build -p nvwa-studio --lib --target wasm32-unknown-unknown --locked "${profile_args[@]}"
mkdir -p dist/web/assets/fixtures dist/web/works
mkdir -p dist/web/licenses/fonts
mkdir -p dist/web/licenses/craft-ui
artifact_root="${CARGO_TARGET_DIR:-target}"
"$tool" --target web --out-dir dist/web "$artifact_root/wasm32-unknown-unknown/$profile/nvwa_studio.wasm"
cp web/index.html dist/web/index.html
cp assets/character.profile.json dist/web/assets/
mkdir -p dist/web/assets/characters dist/web/licenses/b1
cp -R assets/characters/mpfb-b1-v1 dist/web/assets/characters/
for dependency in humentity bevy_obj wobj; do
  mkdir -p "dist/web/licenses/b1/$dependency"
  for notice in "vendor/$dependency"/LICENSE*; do
    [[ -f "$notice" ]] && cp "$notice" "dist/web/licenses/b1/$dependency/"
  done
  if [[ -d "vendor/$dependency/licenses" ]]; then
    cp -R "vendor/$dependency/licenses" "dist/web/licenses/b1/$dependency/"
  fi
done
cp assets/fixtures/nvwa-humanoid.glb assets/fixtures/LICENSE.txt assets/fixtures/provenance-manifest.json dist/web/assets/fixtures/
cp examples/m1-sequence.nvwa.json dist/web/works/
cp assets/fonts/OFL.txt assets/fonts/NOTICE.md assets/fonts/PROVENANCE.json dist/web/licenses/fonts/
mkdir -p dist/web/licenses/appearance
cp assets/appearances/mpfb-b1-cc0-v1/SOURCE.json assets/appearances/mpfb-b1-cc0-v1/manifest.json dist/web/licenses/appearance/
cp -R assets/appearances/mpfb-b1-cc0-v1/licenses assets/appearances/mpfb-b1-cc0-v1/provenance dist/web/licenses/appearance/
cp licenses/craft-ui/LICENSE-MIT.txt dist/web/licenses/craft-ui/
python3 scripts/bundle-sizes.py
if [[ -n "${NVWA_WEB_EXPORT:-}" ]]; then
  python3 -B scripts/verify-b1-inputs.py --asset-root dist/web/assets/characters/mpfb-b1-v1
  python3 - "$NVWA_WEB_EXPORT" <<'PY'
import hashlib
import json
from pathlib import Path
import shutil
import sys

destination = Path(sys.argv[1])
if destination.exists():
    raise SystemExit('Web export destination must be new')
destination.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree('dist/web', destination)
files = [Path('Cargo.toml'), Path('Cargo.lock')]
for directory in ['crates', 'vendor', 'assets', 'scripts', 'web']:
    files += [p for p in Path(directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
receipt = {
    'source_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)},
    'wasm_sha256': hashlib.sha256((destination/'nvwa_studio_bg.wasm').read_bytes()).hexdigest(),
    'scope': 'Compiled Web package; browser launch and functional validation remain separate',
}
(destination/'build-receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
PY
fi
