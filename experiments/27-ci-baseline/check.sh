#!/usr/bin/env bash
# Run from any directory. Cargo runs require the parent's local compile token.
set -euo pipefail
cd "$(dirname "$0")/../.."
export CARGO_BUILD_JOBS="${CARGO_BUILD_JOBS:-1}"
lock_before=$(shasum -a 256 Cargo.lock)
verify_lock() {
  local status=$?
  if [[ "$(shasum -a 256 Cargo.lock)" != "$lock_before" ]]; then
    echo 'FAIL: Cargo.lock changed during check' >&2
    status=1
  fi
  exit "$status"
}
trap verify_lock EXIT
case "${1:-}" in
  portable)
    cargo fmt --all --check
    cargo clippy -p nvwa-core -p nvwa-cli --all-targets --locked -- -D warnings
    cargo test -p nvwa-core -p nvwa-cli --locked
    ;;
  native)
    [[ "$(uname -s)" == Darwin && "$(uname -m)" == arm64 ]] || {
      echo 'This candidate native lane requires macOS arm64.' >&2; exit 2;
    }
    cargo test --workspace --locked
    cargo check --workspace --locked
    ;;
  wasm)
    cargo check -p nvwa-studio --lib --target wasm32-unknown-unknown --locked
    ;;
  diagnostics)
    # These use committed fixtures/captures and synthetic controls.
    # They collect no new browser or native evidence.
    python3 -B experiments/20-scale-boundary/test_geometry.py
    python3 -B experiments/22-fixed-css-dpr/test_controls.py
    node experiments/22-fixed-css-dpr/test_collector.js
    python3 -B experiments/23-ime-event-provenance/test_checker.py
    node experiments/23-ime-event-provenance/test_collector.cjs
    python3 -B experiments/24-http-cold-startup/test_boundary.py
    node --test experiments/25-screenshot-export/export-probe.test.cjs
    ;;
  *) echo 'Usage: bash experiments/27-ci-baseline/check.sh portable|native|wasm|diagnostics' >&2; exit 2;;
esac
