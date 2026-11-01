# Bounded CI candidate

This experiment proposes automatic PR and `main` checks for the current Rust
workspace. The root orchestrator authorized adoption into `.github/workflows/ci.yml`.
That file now contains this candidate. Hosted execution and publication are
owned by the root orchestrator.

The candidate has two jobs:

| Job | Standard runner | Checks | Timeout |
| --- | --- | --- | --- |
| Portable | `ubuntu-24.04`, x64 | Rust format; strict core/CLI Clippy; core/CLI tests; bounded CPU diagnostic controls | 25 minutes |
| Native and Wasm | `macos-14`, ARM64 | All workspace CPU tests; normal native workspace check; actual studio Wasm library compile check | 45 minutes |

The earlier portable job cap was 20 minutes after the 15-minute cap interrupted
required nested cache controls. This finite five-minute increase preserves all
commands, modes, independent replays, step caps, cache policy and job dependencies.
It does not establish that 20 minutes is sufficient; historical run receipts retain
their original budgets and outcomes.

On 2026-11-01, Derek approved additional CI time. This bounded implementation
chooses a **20→25 minute** portable job cap from the retained timings below.
The new extra-time authorization supersedes the prior portable20 STOP only
for this finite allocation.
Same-tree PR run [41100580034](https://github.com/Derek-X-Wang/nvwa/actions/runs/41100580034)
completed portable in 988 seconds. Natural main run
[41148258038](https://github.com/Derek-X-Wang/nvwa/actions/runs/41148258038)
was cancelled at 1215 seconds with the 20-minute job timeout annotation; the final
frozen-upper-arm group had begun at 1188 seconds. Its retained 300-second step cap
plus that observed prefix totals 1488 seconds within the new 1500-second budget.
That group did not finish, so this is an allocation, not a speedup or completion
guarantee. Eye8/auth3/offline6/upper-arm5, native75, B1/warm60, cache-action4,
all commands, modes, runner labels, source contexts, dependencies and cache
behavior remain unchanged. The exact current portable25 policy restores the
historical15 bytes before unchanged workflow hashes. Fresh complete formal
PR/main CI is still required. Actual eye8 or portable25 budget exhaustion,
or a need to expand the budget, policy scope or verification framework,
triggers critical STOP and retains release HOLD. No automatic increase, job
split, case reduction or blind rerun of unchanged inputs is authorized.
Ordinary real feature failures retain the existing Goal's bounded fix/review
path, same-class two-attempt Astra escalation and boundary STOP rules. This
budget correction has a bounded eight-file policy scope. See
[verification policy](../../docs/agents/verification.md).

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
