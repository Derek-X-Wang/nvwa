#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
profile="${1:-release}"
case "$profile" in
  release) profile_args=(--release);;
  dev) profile_args=(); profile=debug;;
  *) echo "Usage: bash scripts/build-web.sh [release|dev]" >&2; exit 2;;
esac
tool=".tools/wasm-bindgen/wasm-bindgen-0.2.129-aarch64-apple-darwin/wasm-bindgen"
if [[ ! -x "$tool" ]]; then
  echo "Run python3 scripts/install-web-tools.py first (or set up wasm-bindgen 0.2.129)." >&2
  exit 1
fi
CARGO_BUILD_JOBS="${CARGO_BUILD_JOBS:-3}" cargo build -p nvwa-studio --lib --target wasm32-unknown-unknown --locked "${profile_args[@]}"
mkdir -p dist/web/assets/fixtures dist/web/works
mkdir -p dist/web/licenses/fonts
artifact_root="${CARGO_TARGET_DIR:-target}"
"$tool" --target web --out-dir dist/web "$artifact_root/wasm32-unknown-unknown/$profile/nvwa_studio.wasm"
cp web/index.html dist/web/index.html
cp assets/character.profile.json dist/web/assets/
cp assets/fixtures/nvwa-humanoid.glb assets/fixtures/LICENSE.txt assets/fixtures/provenance-manifest.json dist/web/assets/fixtures/
cp examples/m1-sequence.nvwa.json dist/web/works/
cp assets/fonts/OFL.txt assets/fonts/NOTICE.md assets/fonts/PROVENANCE.json dist/web/licenses/fonts/
python3 scripts/bundle-sizes.py
