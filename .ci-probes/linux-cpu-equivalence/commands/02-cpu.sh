bash "$NVWA_ADAPTER_DIR/native-linux.sh" "$GITHUB_WORKSPACE"
# Product packages are formatted in portable. --all here also visits
# admitted vendor path dependencies whose exact bytes must be retained.
cargo fmt --manifest-path experiments/49-runtime-pose-parity/probe/Cargo.toml --package nvwa-runtime-pose-probe --check
cargo fmt --manifest-path experiments/50-upper-arm-neutral-ab/probe/Cargo.toml --package nvwa-runtime-pose-probe --check
cargo check --manifest-path experiments/49-runtime-pose-parity/probe/Cargo.toml --lib --locked --offline
cargo check --manifest-path experiments/50-upper-arm-neutral-ab/probe/Cargo.toml --lib --locked --offline
