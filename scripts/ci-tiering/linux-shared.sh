#!/usr/bin/env bash
# Linux-specific shared evidence. Never remove/impersonate the Mac native guard.
set -euo pipefail
cd "$(dirname "$0")/../.."
[[ "$(uname -s)" == Linux ]] || { echo 'This shared lane requires Linux' >&2; exit 2; }
export CARGO_BUILD_JOBS="${CARGO_BUILD_JOBS:-1}"
lock_before=$(sha256sum Cargo.lock)
verify_lock() {
  local status=$?
  [[ "$(sha256sum Cargo.lock)" == "$lock_before" ]] || { echo 'FAIL: Cargo.lock changed' >&2; status=1; }
  exit "$status"
}
trap verify_lock EXIT
case "${1:-}" in
  fetch)
    cargo fetch --locked --manifest-path Cargo.toml
    cargo fetch --locked --manifest-path experiments/49-runtime-pose-parity/probe/Cargo.toml
    cargo fetch --locked --manifest-path experiments/50-upper-arm-neutral-ab/probe/Cargo.toml
    cargo fetch --locked --manifest-path experiments/60-b1-continuous-motion/Cargo.toml
    cargo fetch --locked --manifest-path experiments/65-b1-appearance-quality/preview/Cargo.toml
    cargo fetch --locked --manifest-path experiments/66-b1-appearance-work/Cargo.toml
    cargo fetch --locked --manifest-path experiments/68-b1-eye-render-diagnosis/Cargo.toml
    cargo fetch --locked --manifest-path experiments/71-b1-character-parameters/Cargo.toml
    cargo fetch --locked --manifest-path experiments/73-high-poly-eyes/Cargo.toml
    cargo fetch --locked --manifest-path experiments/79-shoulder-pose-corrective/Cargo.toml
    ;;
  check)
    cargo check --workspace --locked --features nvwa-cli/motion-query,bevy/x11
    ;;
  workspace)
    cargo test --workspace --locked --features nvwa-cli/motion-query,bevy/x11
    cargo test -p nvwa-cli --features cpu-render,motion-query --test cpu_render --locked --offline -- --test-threads=1
    # Product packages are formatted in portable. --all here also visits
    # admitted vendor path dependencies whose exact bytes must be retained.
    cargo fmt --manifest-path experiments/49-runtime-pose-parity/probe/Cargo.toml --package nvwa-runtime-pose-probe --check
    cargo fmt --manifest-path experiments/50-upper-arm-neutral-ab/probe/Cargo.toml --package nvwa-runtime-pose-probe --check
    cargo check --manifest-path experiments/49-runtime-pose-parity/probe/Cargo.toml --lib --locked --offline --features bevy/x11
    cargo check --manifest-path experiments/50-upper-arm-neutral-ab/probe/Cargo.toml --lib --locked --offline --features bevy/x11
    ;;
  bridges)
    cargo fmt --manifest-path experiments/65-b1-appearance-quality/preview/Cargo.toml --package b1-appearance-quality-preview --check
    cargo fmt --manifest-path experiments/66-b1-appearance-work/Cargo.toml --package b1-appearance-work --check
    cargo test --manifest-path experiments/65-b1-appearance-quality/preview/Cargo.toml --lib --locked --offline --features bevy/x11
    cargo test --manifest-path experiments/66-b1-appearance-work/Cargo.toml --lib --locked --offline --features bevy/x11
    cargo fmt --manifest-path experiments/68-b1-eye-render-diagnosis/Cargo.toml --package b1-eye-render-diagnosis --check
    cargo fmt --manifest-path experiments/71-b1-character-parameters/Cargo.toml --package b1-character-parameters --check
    cargo test --manifest-path experiments/68-b1-eye-render-diagnosis/Cargo.toml --lib --locked --offline --features bevy/x11
    cargo test --manifest-path experiments/71-b1-character-parameters/Cargo.toml --lib --locked --offline --features bevy/x11
    cargo fmt --manifest-path experiments/73-high-poly-eyes/Cargo.toml --package b1-high-poly-eyes --check
    cargo test --manifest-path experiments/73-high-poly-eyes/Cargo.toml --lib --locked --offline --features bevy/x11
    cargo fmt --manifest-path experiments/79-shoulder-pose-corrective/Cargo.toml --package b1-shoulder-source-corrective --check
    cargo test --manifest-path experiments/79-shoulder-pose-corrective/Cargo.toml --lib --locked --offline --features bevy/x11
    ;;
  matrix)
    cargo fmt --manifest-path experiments/60-b1-continuous-motion/Cargo.toml --package b1-continuous-probe --check
    cargo build --manifest-path experiments/60-b1-continuous-motion/Cargo.toml --bins --locked --offline --features bevy/x11
    python3 -B experiments/60-b1-continuous-motion/run_matrix.py --binary "$CARGO_TARGET_DIR/debug/matrix" --asset-root "$GITHUB_WORKSPACE/assets" --out "$RUNNER_TEMP/nvwa-b1-motion-matrix"
    # Use this job's actual retained source2 frame. The garment controls
    # require real source/upload data, not an invented portable fixture.
    python3 -B scripts/ci-tiering/linux_garment_controls.py --asset-root assets/characters/mpfb-b1-v1 --frame "$RUNNER_TEMP/nvwa-b1-motion-matrix/keyframes/t+1__b1_arm_rehearsal_v1__k16.json.gz"
    python3 -B -O scripts/ci-tiering/linux_garment_controls.py --asset-root assets/characters/mpfb-b1-v1 --frame "$RUNNER_TEMP/nvwa-b1-motion-matrix/keyframes/t+1__b1_arm_rehearsal_v1__k16.json.gz"
    ;;
  *) echo 'Usage: linux-shared.sh fetch|check|workspace|bridges|matrix' >&2; exit 2;;
esac
