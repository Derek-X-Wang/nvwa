#!/usr/bin/env bash
set -euo pipefail
if [[ $# -lt 3 || $# -gt 4 ]]; then
  echo 'usage: run-common.sh ABS-COMMON-MANIFEST ABS-REFERENCE-DIR ABS-MHCLO [ABS-NEW-RUN-DIR]' >&2
  exit 2
fi
probe_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
repo_dir="$(cd -- "$probe_dir/../.." && pwd)"
run_dir="${4:-$probe_dir/.work/common-$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$probe_dir/.work"
mkdir "$run_dir"
export CARGO_NET_OFFLINE=true
export CARGO_BUILD_JOBS=1
export CARGO_TARGET_DIR="$probe_dir/target"
cargo build --locked --offline --manifest-path "$probe_dir/Cargo.toml" -j 1 2>&1 | tee "$run_dir/build.log"
python3 "$probe_dir/compile_common.py" --addon "$repo_dir/.work/character-approved-20261016/mpfb-addon" --reference-dir "$2" --manifest "$1" --garment "$3" --out "$run_dir/compiled" | tee "$run_dir/compile.log"
python3 "$probe_dir/compare_common.py" --compiled "$run_dir/compiled" --out "$run_dir/comparison" --tolerance 0.00001 | tee "$run_dir/comparison.log"
python3 "$probe_dir/check_common_failures.py" --compiled "$run_dir/compiled" --out "$run_dir/failure-controls" | tee "$run_dir/failure-controls.log"
python3 "$probe_dir/measure_continuity.py" --comparison "$run_dir/comparison" --out "$run_dir/continuity-summary.json" | tee "$run_dir/continuity.log"
