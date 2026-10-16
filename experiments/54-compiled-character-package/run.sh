#!/usr/bin/env bash
set -euo pipefail
probe_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
run_dir="${1:-$probe_dir/.work/run-$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$probe_dir/.work"
mkdir "$run_dir"
export CARGO_NET_OFFLINE=true
export CARGO_BUILD_JOBS=1
export CARGO_TARGET_DIR="$probe_dir/target"
cargo build --locked --offline --manifest-path "$probe_dir/Cargo.toml" -j 1 2>&1 | tee "$run_dir/build.log"
python3 "$probe_dir/check.py" --out "$run_dir/cases" | tee "$run_dir/controls.log"
