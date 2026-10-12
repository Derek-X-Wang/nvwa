# Bounded CI candidate

This experiment proposes automatic PR and `main` checks for the current Rust
workspace. The root orchestrator authorized adoption into `.github/workflows/ci.yml`.
That file now contains this candidate. Hosted execution and publication are
owned by the root orchestrator.

The candidate has two jobs:

| Job | Standard runner | Checks | Timeout |
| --- | --- | --- | --- |
| Portable | `ubuntu-24.04`, x64 | Rust format; strict core/CLI Clippy; core/CLI tests; bounded CPU diagnostic controls | 15 minutes |
| Native and Wasm | `macos-14`, ARM64 | All workspace CPU tests; normal native workspace check; actual studio Wasm library compile check | 45 minutes |

Use the local equivalent from the repository:

```sh
# Cargo commands require the parent's local compile token.
CARGO_BUILD_JOBS=2 bash experiments/27-ci-baseline/check.sh portable
CARGO_BUILD_JOBS=2 bash experiments/27-ci-baseline/check.sh native
CARGO_BUILD_JOBS=2 bash experiments/27-ci-baseline/check.sh wasm
bash experiments/27-ci-baseline/check.sh diagnostics
```

`native` refuses hosts other than macOS ARM64. `wasm` checks Rust compilation;
it does not produce JS bindings, package assets, start a browser, or run Wasm.
All Cargo build/test/check commands use `--locked`; each script invocation checks
that `Cargo.lock` stays identical. No script installs tools or changes machine
configuration. Diagnostics use committed fixtures/captures, synthetic controls
and temporary directories. They collect no new browser or native evidence. The HTTP
boundary suite briefly opens its own loopback socket on an OS-assigned port.

The hosted candidate installs exactly the repository's Rust `1.95.0` through the
runner's existing `rustup`. It disables incremental compilation and debug info
in development/test profiles to reduce cold-build storage, uses one Mac Cargo
worker and two Ubuntu workers, and cancels superseded runs. Local validation used
the existing cache and default debug profiles. Hosted cold-build time, memory,
disk, Linux execution, and the reduced-debug combination remain unverified.

Security is narrow: `pull_request` and `main` push only, `contents: read`, no
other token scopes, no cache steps, checkout credentials not retained,
official checkout pinned to a verified full commit SHA, and no cache/artifact
upload, secret, release, deploy, signing, privileged trigger, matrix, nightly,
fuzzing or GPU lane. See [REPORT.md](REPORT.md) for evidence and official sources.

PARTIAL — local workspace 103 Rust tests, portable 27 Rust tests, format, strict
core/CLI Clippy, normal native and Wasm checks, 77 diagnostic tests and 2 collector controls passed.
Hosted Actions, rendered UI, original DPR pixels and physical IME remain NOT-RUN.
