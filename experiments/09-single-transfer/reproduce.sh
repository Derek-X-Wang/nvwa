#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
# Keep this workload separate from Studio, native release and Web artifacts.
export CARGO_BUILD_JOBS="${CARGO_BUILD_JOBS:-2}"
export CARGO_TARGET_DIR="${NVWA_SINGLE_TRANSFER_TARGET_DIR:-target/single-glb-transfer}"
cargo fmt -p nvwa-runtime -- --check
cargo test -p nvwa-runtime --lib --locked --offline -- --test-threads=1
cargo clippy -p nvwa-runtime --lib --tests --locked --offline -- -D warnings
