#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
destination="${1:-dist/preview}"
tool="${NVWA_WASM_BINDGEN:-.tools/wasm-bindgen/wasm-bindgen-0.2.129-aarch64-apple-darwin/wasm-bindgen}"
if [[ -e "$destination" ]]; then
  echo 'Preview output must be a new directory.' >&2
  exit 1
fi
if [[ ! -x "$tool" ]]; then
  echo 'Set NVWA_WASM_BINDGEN to the existing wasm-bindgen 0.2.129 executable.' >&2
  exit 1
fi
if [[ "$("$tool" --version)" != 'wasm-bindgen 0.2.129' ]]; then
  echo 'Preview requires wasm-bindgen 0.2.129.' >&2
  exit 1
fi
CARGO_BUILD_JOBS="${CARGO_BUILD_JOBS:-2}" cargo build --offline --locked -p nvwa-studio \
  --example nvwa-preview --features manual-start --target wasm32-unknown-unknown
mkdir -p "$destination"
"$tool" --target web --out-name nvwa_preview --out-dir "$destination" \
  "${CARGO_TARGET_DIR:-target}/wasm32-unknown-unknown/debug/examples/nvwa-preview.wasm"
cp web/preview.html "$destination/preview.html"
python3 - "$destination" <<'PY'
import hashlib
import json
from pathlib import Path
import sys
destination = Path(sys.argv[1])
paths = [Path('Cargo.toml'), Path('Cargo.lock'), Path('scripts/build-preview-web.sh')]
for folder in ('crates', 'vendor', 'assets'):
    paths.extend(p for p in Path(folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
paths.append(Path('web/preview.html'))
receipt = {
    'scope': 'Compiled preview adapter, not a browser or visual acceptance',
    'source_sha256': {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)},
    'output_sha256': {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(destination.iterdir()) if p.is_file()},
}
(destination/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
PY
