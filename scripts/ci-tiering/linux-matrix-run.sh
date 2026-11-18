#!/usr/bin/env bash
# Execute the exact Linux matrix and garment controls using this run's verified binary.
set -euo pipefail
cd "$(dirname "$0")/../.."
[[ "$(uname -s)" == Linux ]] || { echo 'This matrix lane requires Linux' >&2; exit 2; }
[[ "${EXPECTED_MATRIX_SHA256:-}" =~ ^[0-9a-f]{64}$ ]] || { echo 'Missing exact matrix digest' >&2; exit 2; }
binary="${CARGO_TARGET_DIR:?}/debug/matrix"
actual=$(sha256sum "$binary")
[[ "${actual%% *}" == "$EXPECTED_MATRIX_SHA256" ]] || { echo 'Matrix artifact digest mismatch' >&2; exit 1; }
chmod +x "$binary"
lock_before=$(sha256sum Cargo.lock)
verify_lock() {
  local status=$?
  [[ "$(sha256sum Cargo.lock)" == "$lock_before" ]] || { echo 'FAIL: Cargo.lock changed' >&2; status=1; }
  exit "$status"
}
trap verify_lock EXIT
python3 -B experiments/60-b1-continuous-motion/run_matrix.py --binary "$CARGO_TARGET_DIR/debug/matrix" --asset-root "$GITHUB_WORKSPACE/assets" --out "$RUNNER_TEMP/nvwa-b1-motion-matrix"
# Use this job's actual retained source2 frame. The garment controls
# require real source/upload data, not an invented portable fixture.
python3 -B scripts/ci-tiering/linux_garment_controls.py --asset-root assets/characters/mpfb-b1-v1 --frame "$RUNNER_TEMP/nvwa-b1-motion-matrix/keyframes/t+1__b1_arm_rehearsal_v1__k16.json.gz"
python3 -B -O scripts/ci-tiering/linux_garment_controls.py --asset-root assets/characters/mpfb-b1-v1 --frame "$RUNNER_TEMP/nvwa-b1-motion-matrix/keyframes/t+1__b1_arm_rehearsal_v1__k16.json.gz"

