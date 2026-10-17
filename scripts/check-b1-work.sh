#!/usr/bin/env bash
# Bounded, offline product verification. No GPU, models, or tool downloads.
set -euo pipefail
cd "$(dirname "$0")/.."
export CARGO_BUILD_JOBS="${CARGO_BUILD_JOBS:-2}"
export CARGO_PROFILE_DEV_DEBUG=0
export CARGO_PROFILE_TEST_DEBUG=0
python3 -B scripts/verify-b1-inputs.py
python3 -B scripts/test-b1-inputs.py
python3 -B -O scripts/test-b1-inputs.py
cargo fmt -p nvwa-core -p nvwa-cli -p nvwa-runtime -p nvwa-studio -p nvwa-b1-adapter --check
cargo clippy -p nvwa-core -p nvwa-cli --all-targets --locked --offline -- -D warnings
cargo test --workspace --locked --offline -- --test-threads=1
cargo check --workspace --locked --offline
cargo build -p nvwa-cli -p nvwa-studio --locked --offline
python3 scripts/package-native.py --profile debug
python3 -B scripts/verify-b1-inputs.py --asset-root dist/Nvwa.app/Contents/Resources/assets/characters/mpfb-b1-v1
bash scripts/build-web.sh dev
python3 -B scripts/verify-b1-inputs.py --asset-root dist/web/assets/characters/mpfb-b1-v1
if [[ -n "${B1_VERIFY_EXPORT:-}" ]]; then
  [[ ! -e "$B1_VERIFY_EXPORT" ]] || { echo 'Export destination must be new' >&2; exit 2; }
  mkdir -p "$B1_VERIFY_EXPORT"
  cp -R dist/Nvwa.app dist/web "$B1_VERIFY_EXPORT/"
  cp target/debug/nvwa-cli "$B1_VERIFY_EXPORT/"
  python3 - "$B1_VERIFY_EXPORT" <<'PY'
import hashlib, json, sys
from pathlib import Path
root = Path.cwd()
files = [root/'Cargo.toml', root/'Cargo.lock']
for directory in ['crates', 'vendor', 'assets', 'scripts', 'web']:
    files += [p for p in (root/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
receipt = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
(Path(sys.argv[1])/'build-inputs-sha256.json').write_text(json.dumps(receipt, indent=2)+'\n')
PY
fi
echo 'PASS: workspace tests, native package, and Web build; graphical launch remains separate.'
