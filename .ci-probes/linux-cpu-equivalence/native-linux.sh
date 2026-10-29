#!/usr/bin/env bash
# Explicit private Linux adaptation. Original native wrapper remains Darwin-only.
set -euo pipefail
cd "$1"
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
[[ "$(uname -s)" == Linux && "$(uname -m)" == x86_64 ]] || {
  echo 'This private feasibility adapter requires Linux x86_64.' >&2; exit 2;
}
cargo test --workspace --locked
cargo check --workspace --locked
