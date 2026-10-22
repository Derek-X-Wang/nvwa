# B1 的 Mac 大版本节点命令清单

2026-10-22，Derek 已接受 B1 日常 CI 迁移到 Ubuntu 24.04，以及下述 Mac 覆盖减少。57/58 的 Mac 编译、测试、无窗口执行和全部十个 Mac-hosted Wasm 编译检查保留在既有较大版本或发布节点验收中。本附件不新增周期作业，不改变其他 Mac 作业的频率，也不自动安排额外配对实验。

## 覆盖边界

日常 B1 使用 Linux x86_64。既有 Mac native 作业继续验证产品 workspace 和其原有原生控制，但不替代 57/58 的独立依赖图。迁移后，每次 PR/main 不再证明 57/58 的 Apple SDK、arm64 编译／链接、sampled 测试、八个 viewer library tests、viewer build/check 与实际无窗口执行；也不再证明十个 Wasm target 的 Mac 编译主机兼容性。Wasm 目标和断言保持原样。

这份命令清单证明编译与无窗口行为。Metal/GPU、真实窗口、输入法、剪贴板、焦点、DPI、打包／签名与性能按[桌面验收政策](verification.md)另行记录。#112 的原 Linux 衣物精确断言仍为 FAIL，后续优化模式路径 NOT-RUN；#3 继续阻塞，#4 保留测量缺口。完成本清单不能提升这些结论。

## 执行与完成条件

在较大版本或发布节点，用该版本的干净 Mac arm64 checkout 执行。先确认所需工具、依赖获取和编译资源已获授权。使用固定 Rust 1.95.0、原锁文件和原 feature；不得用已有产品 workspace 编译代替独立图。超过五分钟的检查按全局资源政策安排。保留实际版本 SHA/tree、Mac/SDK/工具链身份、全部命令退出状态和原锁文件前后哈希；缺依赖或命令失败时停止并保留失败，后续各段标为 NOT-RUN。核对所选版本的命令变更已独立审查；本附件不把 BAA 命令清单自动当作以后所有依赖图的验证。

在仓库根目录，设置 `GITHUB_WORKSPACE` 为该 checkout 的绝对路径，`RUNNER_TEMP` 为本次验收专用的新绝对临时目录，`CARGO_TARGET_DIR=$GITHUB_WORKSPACE/target`。使用新 checkout 的独立 target；不复用其他作业的 target。本地 `NVWA_CI_HEAD_SHA` 记录所选实际 commit，`NVWA_TIMING_DIR` 指向本次外部证据目录中的新目录。环境保持 `CARGO_BUILD_JOBS=1`、`CARGO_INCREMENTAL=0`、`CARGO_PROFILE_DEV_DEBUG=0`、`CARGO_PROFILE_TEST_DEBUG=0`、`CARGO_TERM_COLOR=always`。记录并清理会改变验证语义的继承 compiler wrapper、flags、build target、profile 或 B1 控制变量。以下六个原命令体分别写入外部证据目录的 `00.sh` 至 `05.sh`，按顺序用已有 `python3 -B scripts/ci-timing.py shell /absolute/evidence/NN.sh` 执行；它使用原 Bash `-e`。前段成功后再执行后段。只有 sampled/runtime 段额外设置 `CARGO_PROFILE_DEV_OPT_LEVEL=1`、`CARGO_PROFILE_TEST_OPT_LEVEL=1` 及 `B1_CI_INPUTS=$RUNNER_TEMP/nvwa-b1-seed`；在该段结束时还原，建议以只含这三个局部变量的 subshell 执行该段。

依次执行原 provisioning、一组九条辅助 locked fetch、原输入准备及两条 generated-graph fetch。辅助 fetch 保留完整顺序；生成图仍在准备完成后获取。无论成功或失败，监督执行者均用 `python3 -B scripts/ci-timing.py report --directory "$NVWA_TIMING_DIR"` 保留原 always-run report 的作用，并保留首个命令失败退出状态；报告成功不能覆盖失败。保留完整 timing 原始记录。取消或外部超时留下不完整记录时报告 UNKNOWN。

00 — 原工具链 provisioning：

```sh
rustup toolchain install 1.95.0 --profile minimal --component rustfmt --component clippy --target wasm32-unknown-unknown
```

01 — 九条辅助 fetch：

```sh
cargo fetch --locked --manifest-path Cargo.toml
cargo fetch --locked --manifest-path experiments/49-runtime-pose-parity/probe/Cargo.toml
cargo fetch --locked --manifest-path experiments/50-upper-arm-neutral-ab/probe/Cargo.toml
cargo fetch --locked --manifest-path experiments/60-b1-continuous-motion/Cargo.toml
cargo fetch --locked --manifest-path experiments/65-b1-appearance-quality/preview/Cargo.toml
cargo fetch --locked --manifest-path experiments/66-b1-appearance-work/Cargo.toml
cargo fetch --locked --manifest-path experiments/68-b1-eye-render-diagnosis/Cargo.toml
cargo fetch --locked --manifest-path experiments/71-b1-character-parameters/Cargo.toml
cargo fetch --locked --manifest-path experiments/79-shoulder-pose-corrective/Cargo.toml
```

02 — 原输入准备：

```sh
mkdir -p .work
python3 -B experiments/59-b1-ci-inputs/prepare_ci_inputs.py --out "$RUNNER_TEMP/nvwa-b1-seed"
python3 -B experiments/57-b1-pose-runtime/prepare.py --ci-inputs "$RUNNER_TEMP/nvwa-b1-seed"
python3 -B experiments/58-b1-desktop-web/prepare.py --ci-inputs "$RUNNER_TEMP/nvwa-b1-seed"
cargo fetch --locked --manifest-path experiments/57-b1-pose-runtime/adapter/Cargo.toml
cargo fetch --locked --manifest-path experiments/58-b1-desktop-web/Cargo.toml
```

03 — 仅此段设置上述 OPT_LEVEL 和 B1_CI_INPUTS，然后执行原 source/runtime 命令体：

```sh
cargo fmt --manifest-path experiments/57-b1-pose-runtime/adapter/Cargo.toml --package b1-pose-adapter --check
cargo fmt --manifest-path experiments/58-b1-desktop-web/Cargo.toml --package b1-desktop-web --check
# Run the original adapter integration test through the viewer graph;
# this shares its real Bevy features instead of compiling a third stack.
cargo test --manifest-path experiments/58-b1-desktop-web/Cargo.toml --package b1-pose-adapter --test sampled --locked --offline -- --nocapture
cargo test --manifest-path experiments/58-b1-desktop-web/Cargo.toml --lib --locked --offline
cargo build --manifest-path experiments/58-b1-desktop-web/Cargo.toml --bin b1-desktop-web --locked --offline
python3 -B -O experiments/58-b1-desktop-web/verify_native.py --binary "$CARGO_TARGET_DIR/debug/b1-desktop-web" --asset-root "$GITHUB_WORKSPACE/.work/b1-pose-viewer/site/assets" --out "$RUNNER_TEMP/nvwa-b1-viewer-runtime"
```

04 — 还原局部环境后，执行原 viewer native/Web check：

```sh
cargo check --manifest-path experiments/58-b1-desktop-web/Cargo.toml --locked --offline
cargo check --manifest-path experiments/58-b1-desktop-web/Cargo.toml --lib --target wasm32-unknown-unknown --locked --offline
```

05 — 其余九个原 Web target 检查：

```sh
bash experiments/27-ci-baseline/check.sh wasm
cargo check --manifest-path experiments/49-runtime-pose-parity/probe/Cargo.toml --lib --target wasm32-unknown-unknown --locked --offline
cargo check --manifest-path experiments/50-upper-arm-neutral-ab/probe/Cargo.toml --lib --target wasm32-unknown-unknown --locked --offline
cargo check --manifest-path experiments/60-b1-continuous-motion/Cargo.toml --lib --target wasm32-unknown-unknown --locked --offline
cargo check --manifest-path experiments/65-b1-appearance-quality/preview/Cargo.toml --lib --target wasm32-unknown-unknown --locked --offline
cargo check --manifest-path experiments/66-b1-appearance-work/Cargo.toml --lib --target wasm32-unknown-unknown --locked --offline
cargo check --manifest-path experiments/68-b1-eye-render-diagnosis/Cargo.toml --lib --target wasm32-unknown-unknown --locked --offline
cargo check --manifest-path experiments/71-b1-character-parameters/Cargo.toml --lib --target wasm32-unknown-unknown --locked --offline
cargo check --manifest-path experiments/79-shoulder-pose-corrective/Cargo.toml --lib --target wasm32-unknown-unknown --locked --offline
```

核对完成条件：

- 九条辅助 fetch 与原 23 条命令全部实际完成，且失败状态未被吞掉；工具链 provisioning 单独记录。锁文件及源码保持原身份。
- 两次 Cargo test 分别实际执行一个 sampled 测试（内部 40 个 sampled 用例）与八个 viewer library tests。空测试或仅编译不算完成。
- 保留 `$RUNNER_TEMP/nvwa-b1-viewer-runtime` 的实际 Mac 无窗口收据、恢复／致命错误边界控制及相应日志。`verify_native.py` 原单次 `python3 -B -O` 保持原样；缺输入、收据或失败控制均不算完成。
- 十个 Wasm 编译目标逐一完成：viewer58、studio（原 `check.sh wasm`）、49、50、60、65、66、68、71、79。它们证明编译，浏览器内执行与画面另记。
- 每层分别用 `VERIFIED / PARTIAL / NOT-RUN` 记录；未执行的 Mac 节点检查标为 `NOT-RUN（按策略延后）`。日常 Linux CI、历史 pilot、桌面人工验收与本清单互不替代。

本附件保留原命令参数、locked/offline、test filter 和 profile。root studio wrapper 原本没有 `--offline`；此处没有补加。若需要新系统包、重试、增加预算或放宽断言，停止并重新确认范围。
